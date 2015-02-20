import copy
import json
import uuid
import requests
from os.path import basename, dirname
from celery import chain, chord, group
from requests.exceptions import ConnectionError
from conf.appconfig import TASK_SETTINGS, JOB_SETTINGS, JOB_STATE_NEW, \
    JOB_STATE_SCHEDULED, JOB_STATE_DEPLOY_REQUESTED, JOB_STATE_NOOP, \
    DEFAULT_DEPLOYER_URL, CONFIG_PROVIDERS, LEVEL_FAILED, LEVEL_STARTED, \
    LEVEL_SUCCESS
from conf.celeryconfig import CLUSTER_NAME
from orchestrator.celery import app
from orchestrator.etcd import using_etcd, safe_delete, get_or_insert
from orchestrator.services import config
from orchestrator.services.distributed_lock import LockService, \
    ResourceLockedException
from orchestrator.tasks.exceptions import DeploymentFailed, HooksFailed
from orchestrator.tasks.notification import notify
from orchestrator.tasks.search import index_job, create_search_parameters, \
    add_search_event, EVENT_DEPLOY_REQUESTED, EVENT_DEPLOY_REQUEST_COMPLETE
from orchestrator.tasks.common import async_wait
from orchestrator.util import dict_merge

__author__ = 'sukrit'


def _template_variables(owner, repo, ref, commit=None):
    ref_number = ref.lower().replace('feature_', '').replace('patch_', '')
    commit = commit or 'na'
    return {
        'owner': owner,
        'repo': repo,
        'ref': ref,
        'commit': commit,
        'ref_number': ref_number,
        'cluster': CLUSTER_NAME
    }


def _notify_ctx(owner, repo, ref, commit=None, job_id=None, operation=None):
    return {
        'owner': owner,
        'repo': repo,
        'ref': ref,
        'commit': commit,
        'cluster': CLUSTER_NAME,
        'job-id': job_id,
        'operation': operation
    }


@app.task
def handle_callback_hook(owner, repo, ref, hook_type, hook_name,
                         hook_status='success', hook_result=None, commit=None,
                         force_deploy=False):
    template_vars = _template_variables(owner, repo, ref, commit=commit,)
    job_config = CONFIG_PROVIDERS['default']['config']
    notify_ctx = _notify_ctx(owner, repo, ref, commit=commit,
                             operation='handle_callback_hook')
    notify.si(
        {'message': 'Received webhook {0}/{1} with status {2}'.format(
            hook_type, hook_name, hook_status)},
        ctx=notify_ctx, level=LEVEL_STARTED,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()

    try:
        job_config = config.load_config(
            CLUSTER_NAME, owner, repo, ref, default_variables=template_vars)
        # Making create job sync call to get job-id
        job = _create_job(job_config, owner, repo, ref, commit=commit,
                          force_deploy=force_deploy)
    except BaseException as exc:
        notify.si(exc, ctx=notify_ctx,
                  level=LEVEL_FAILED,
                  notifications=job_config.get('notifications'),
                  security_profile=job_config['security']['profile'],
                  ).delay()
        raise

    return _using_lock.si(
        name='%s-%s-%s-%s' % (CLUSTER_NAME, owner, repo, ref),
        do_task=(
            _update_job_ttl.si(owner, repo, ref, commit=commit) |
            _handle_hook.si(job, hook_type, hook_name, hook_status=hook_status,
                            hook_result=hook_result) |
            async_wait.s(
                default_retry_delay=TASK_SETTINGS['JOB_WAIT_RETRY_DELAY'],
                max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES'],
                error_task=notify.s(
                    ctx=_notify_ctx(owner, repo, ref, commit=commit,
                                    operation='handle_callback_hook',
                                    job_id=job['meta-info']['job-id']),
                    level=LEVEL_FAILED,
                    notifications=job_config.get('notifications'),
                    security_profile=job_config['security']['profile']
                )
            )
        ),
    ).delay()


@app.task
def undeploy(owner, repo, ref):
    """
    Undeploys the application using git meta data.

    :return: None
    """
    template_vars = _template_variables(owner, repo, ref)
    try:
        job_config = config.load_config(
            CLUSTER_NAME, owner, repo, ref, default_variables=template_vars)
    except BaseException as exc:
        notify.si(exc, ctx=_notify_ctx(owner, repo, ref, commit=None,
                                       operation='undeploy'),
                  level=LEVEL_FAILED,
                  notifications=job_config.get('notifications'),
                  security_profile=job_config['security']['profile']).delay()
        raise

    return _using_lock.si(
        name='%s-%s-%s-%s' % (CLUSTER_NAME, owner, repo, ref),
        do_task=_undeploy_all.si(job_config, owner, repo, ref)
    ).apply_async()


def _job_base_location(owner, repo, ref, etcd_base, commit=None):
    commit = commit or 'not_set'
    return '%s/orchestrator/jobs/%s/%s/%s/%s/%s' % \
           (etcd_base, CLUSTER_NAME, owner, repo, ref, commit)


@app.task(bind=True, default_retry_delay=TASK_SETTINGS['LOCK_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['LOCK_RETRIES'])
def _using_lock(self, name, do_task, cleanup_tasks=None,
                error_tasks=None):
    """
    Applies lock for the deployment

    :return: Lock object (dictionary)
    :rtype: dict
    """
    try:
        lock = LockService().apply_lock(name)
    except ResourceLockedException as lock_error:
        raise self.retry(exc=lock_error)

    _release_lock_s = _release_lock.si(lock)
    cleanup_tasks = cleanup_tasks or []
    if not isinstance(cleanup_tasks, list):
        cleanup_tasks = [cleanup_tasks]

    error_tasks = error_tasks or []
    if not isinstance(error_tasks, list):
        error_tasks = [error_tasks]

    error_tasks.append(_release_lock_s)
    cleanup_tasks.append(_release_lock_s)

    return (
        do_task
    ).apply_async(
        link=chain(cleanup_tasks),
        link_error=chain(error_tasks)
    )


@app.task
def _release_lock(lock):
    """
    Releases lock acquired during deletion or creation.

    :param lock: Lock dictionary
    :type lock: dict
    :return: True: If lock was released.
            False: Otherwise
    """
    return LockService().release(lock)


@app.task
@using_etcd
def _update_job_ttl(owner, repo, ref, commit=None, ttl=None, etcd_cl=None,
                    etcd_base=None):
    """
    Updates the job ttl.

    :param owner: SCM Owner/Organization for the job.
    :param repo: SCM Repository
    :param ref: SCM branch or tag
    :param ttl: Time to live in seconds for job to be ready for deployment).
        TTL is updated whenever hook is received.
    :keyword etcd_cl: Optional Etcd Client. Default value is initialized using
        wrapper using_etcd
    :keyword etcd_base: Optional Etcd base location. Default value is
        initialized using wrapper using_etcd
    :return: None
    """
    ttl = ttl or JOB_SETTINGS['DEFAULT_TTL']
    job_base = _job_base_location(owner, repo, ref, etcd_base, commit=commit)

    def update_ttl(prev_exist=True):
        etcd_cl.write(job_base, None, ttl=ttl, dir=True, prevExist=prev_exist)
    try:
        update_ttl(True)
    except KeyError:
        # Job does not exists. Lets create a new one
        update_ttl(False)


@using_etcd
def _create_job(job_config, owner, repo, ref, commit=None, etcd_cl=None,
                etcd_base=None, force_deploy=False):
    commit = commit or 'not_set'
    job_base = _job_base_location(owner, repo, ref, etcd_base, commit=commit)
    try:
        state = etcd_cl.read(job_base+'/state').value
        job_id = etcd_cl.read(job_base+'/job-id').value
    except KeyError:
        state = JOB_STATE_NEW
        job_id = str(uuid.uuid4())
    return _as_job(job_config, job_id, owner, repo, ref, commit=commit,
                   state=state, force_deploy=force_deploy)


@app.task
def _handle_hook(job, hook_type, hook_name, hook_status, hook_result):
    job_config = job['config']

    builder_hooks = [name for name, hook_obj in job_config['hooks']['builders']
                     .items() if hook_obj['enabled']]

    if not job_config['enabled'] or not builder_hooks:
        return _handle_noop.si(job).delay()

    else:
        # Reset/ Create the new job
        return _update_job.si(job, hook_type, hook_name,
                              hook_status=hook_status,
                              hook_result=hook_result).delay()


@app.task
@using_etcd
def _handle_noop(job, etcd_cl=None, etcd_base=None):
    job = copy.deepcopy(job)
    job_config = job['config']
    job['state'] = JOB_STATE_NOOP
    git = job['meta-info']['git']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])
    safe_delete(etcd_cl, job_base, recursive=True)
    notify_ctx = _notify_ctx(git['owner'], git['repo'], git['ref'],
                             commit=git['commit'],
                             operation='handle_noop')
    notify.si(
        {'message': 'No deployment requested (NOOP)'},
        ctx=notify_ctx, level=LEVEL_SUCCESS,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()
    return index_job.si(job, ret_value=job).delay()


@app.task
def _update_job(job, hook_type, hook_name, hook_result=None,
                hook_status='success'):
    job = copy.deepcopy(job)
    job['state'] = JOB_STATE_SCHEDULED
    return (
        _update_etcd_job.si(job, hook_type, hook_name, hook_result=hook_result,
                            hook_status=hook_status) |
        _check_and_fire_deploy.s()
    ).delay()


@app.task
@using_etcd
def _update_etcd_job(job, hook_type, hook_name, hook_status='success',
                     hook_result=None, etcd_cl=None, etcd_base=None):
    job = copy.deepcopy(job)
    hook_result = hook_result or {}
    git = job['meta-info']['git']
    job_config = job['config']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])
    etcd_cl.write(job_base+'/job-id', job['meta-info']['job-id'])

    ci_hooks = [name for name, hook_obj in job_config['hooks']['ci']
                .items() if hook_obj['enabled']]

    # Update done status for all CI Hooks. Set value to True, if current
    # hook matches, else update to False (if existing value is not found)
    for ci_hook in ci_hooks:
        if hook_type == 'ci' and ci_hook == hook_name:
            etcd_cl.write('%s/hooks/ci/%s/status' % (job_base, ci_hook),
                          hook_status)
            job['hooks']['ci'][ci_hook] = {
                'status': hook_status
            }
        else:
            # Set value to 'pending' if not already set
            status = get_or_insert(
                etcd_cl, '%s/hooks/ci/%s/status' % (job_base, ci_hook),
                'pending')
            job['hooks']['ci'][ci_hook] = {
                'status': status
            }

    def _update_job(job_status, image):
        job['hooks']['builder'] = {
            'status': job_status,
        }
        if image:
            job['hooks']['builder']['image'] = image
            for deployer in job['config']['deployers'].values():
                deployer['templates']['app']['args']['image'] = image

    if hook_type == 'builder' and hook_name in job_config['hooks']['builders']:
        etcd_cl.write('%s/hooks/builder/status' % job_base, hook_status)
        if hook_status == 'success':
            image = hook_result.get('image', '')
            etcd_cl.write('%s/hooks/builder/image' % job_base, image)
        else:
            image = ''
        _update_job(hook_status, image)
    else:
        # Set value to False if not already set
        status = get_or_insert(etcd_cl, '%s/hooks/builder/status' % job_base,
                               'pending')
        image = get_or_insert(etcd_cl, '%s/hooks/builder/image' % job_base, '')
        _update_job(status, image)
    etcd_cl.write(job_base+'/state', job['state'])
    return index_job.si(job, ret_value=job).delay()


@app.task
@using_etcd
def _check_and_fire_deploy(job, etcd_cl=None, etcd_base=None):
    # Check and fires deploy
    git = job['meta-info']['git']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])

    hooks = etcd_cl.read(job_base+'/hooks', recursive=True, consistent=True)
    failed_hooks = []

    # If it is force deploy, status check is ignored
    if not job['force-deploy']:
        for hook_obj in hooks.leaves:
            done_key = basename(hook_obj.key)
            if done_key == 'status':
                if hook_obj.value == 'pending':
                    # Hooks not yet completed. return
                    return job
                elif hook_obj.value == 'failed':
                    failed_hooks.append(basename(dirname(hook_obj.key)))

    if failed_hooks:
        return (
            _delete.si(job_base, ret_value=job, recursive=True) |
            _failed.si(failed_hooks)
        ).delay()
    else:
        return (
            _delete.si(job_base, ret_value=job, recursive=True) |
            _deploy_all.si(job)
        ).delay()


@app.task
@using_etcd
def _delete(job_base, ret_value=None, etcd_cl=None, **kwargs):
    safe_delete(etcd_cl, job_base, recursive=True)
    return ret_value


@app.task
def _deploy_all(job):
    job = copy.deepcopy(job)
    job_config = job['config']
    job['state'] = JOB_STATE_DEPLOY_REQUESTED
    deployers = job_config.get('deployers', {})
    search_params = create_search_parameters(job)
    return chord(
        group(
            _deploy.si(job, deployer_name)
            for deployer_name, deployer in deployers.items()
            if deployer.get('enabled') and deployer.get('url')
        ),
        add_search_event.si(
            EVENT_DEPLOY_REQUEST_COMPLETE, search_params=search_params,
            ret_value=job),
    ).apply_async(interval=TASK_SETTINGS['DEPLOY_WAIT_RETRY_DELAY'])


@app.task(bind=True,
          default_retry_delay=TASK_SETTINGS['DEPLOY_WAIT_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['DEPLOY_WAIT_RETRIES'])
def _deploy(self, job, deployer_name):
    job_config = job['config']
    deployer = job_config['deployers'][deployer_name]
    apps_url = '%s/apps' % deployer.get('url', DEFAULT_DEPLOYER_URL)
    headers = {
        'content-type': 'application/vnd.deployer.app.version.create.v1+json',
        'accept': 'application/vnd.deployer.task.v1+json'
    }
    data = {
        'meta-info': job['meta-info'],
        'proxy': deployer['proxy'],
        'templates': deployer['templates'],
        'deployment': dict_merge(deployer['deployment']),
        'security': job_config.get('security', {})
    }
    try:
        response = requests.post(apps_url, data=json.dumps(data),
                                 headers=headers)
    except ConnectionError as error:
        raise self.retry(exc=error)

    search_params = create_search_parameters(job)
    deploy_response = {
        'name': deployer_name,
        'url': apps_url,
        'request': data,
        'response': response.json() if 'json' in
        response.headers['content-type'] else {'raw': response.text},
        'status': response.status_code
    }
    add_search_event.si(
        EVENT_DEPLOY_REQUESTED,
        details=deploy_response,
        search_params=search_params
    ).delay()
    if response.status_code in (502, 503):
        raise self.retry(exc=DeploymentFailed(deploy_response))

    if deploy_response['status'] >= 400:
        raise DeploymentFailed(deploy_response)

    git = job['meta-info']['git']
    notify_ctx = _notify_ctx(git['owner'], git['repo'], git['ref'],
                             commit=git['commit'],
                             operation='deploy')
    notify.si(
        {'message': 'Deployment for {0} requested successfully using url: {1}'
            .format(deployer_name, apps_url)},
        ctx=notify_ctx, level=LEVEL_SUCCESS,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()

    return deploy_response


@app.task(default_retry_delay=TASK_SETTINGS['DEFAULT_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['DEFAULT_RETRIES'])
def _undeploy_all(job_config, owner, repo, ref):
    deployers = job_config.get('deployers', {})
    return group(
        _undeploy.si(job_config, owner, repo, ref, deployer_name)
        for deployer_name, deployer in deployers.items()
        if deployer.get('enabled') and deployer.get('url')
    ).delay()


@app.task(bind=True, default_retry_delay=TASK_SETTINGS['DEFAULT_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['DEFAULT_RETRIES'])
def _undeploy(self, job_config, owner, repo, ref, deployer_name):
    app_name = '%s-%s-%s' % (owner, repo, ref)
    deployer = job_config['deployers'][deployer_name]
    app_url = '%s/apps/%s' % (
        deployer.get('url', DEFAULT_DEPLOYER_URL), app_name)
    try:
        requests.delete(app_url)
    except ConnectionError as error:
        raise self.retry(exc=error)


@app.task
def _failed(failed_hooks):
    raise HooksFailed(failed_hooks)


def _as_job(job_config, job_id,  owner, repo, ref, state=JOB_STATE_SCHEDULED,
            commit=None, force_deploy=False):
    return {
        'config': copy.deepcopy(job_config),
        'meta-info': {
            'git': {
                'owner': owner,
                'repo': repo,
                'ref': ref,
                'commit': commit
            },
            'job-id': job_id
        },
        'state': state,
        'hooks': {
            'ci': {},
            'builder': {}
        },
        'force-deploy': force_deploy
    }
