import copy
import json
import uuid
import requests
from os.path import basename, dirname
from celery import chain, chord, group, signature
from requests.exceptions import ConnectionError
from conf.appconfig import TASK_SETTINGS, JOB_SETTINGS, JOB_STATE_NEW, \
    JOB_STATE_SCHEDULED, JOB_STATE_COMPLETE, JOB_STATE_NOOP, \
    DEFAULT_DEPLOYER_URL, CONFIG_PROVIDERS, LEVEL_FAILED, LEVEL_STARTED, \
    LEVEL_SUCCESS, TOTEM_ENV, LEVEL_PENDING
from conf.celeryconfig import CLUSTER_NAME
from orchestrator.services import job as job_service
from orchestrator.celery import app
from orchestrator.etcd import using_etcd, safe_delete, get_or_insert
from orchestrator.services import config
from orchestrator.services.distributed_lock import LockService, \
    ResourceLockedException
from orchestrator.tasks import util
from orchestrator.tasks.exceptions import DeploymentFailed, HooksFailed
from orchestrator.tasks.notification import notify
from orchestrator.tasks.search import index_job, create_search_parameters, \
    add_search_event, EVENT_DEPLOY_REQUESTED, EVENT_JOB_COMPLETE, \
    EVENT_NEW_JOB, update_job_state, EVENT_ACQUIRED_LOCK, EVENT_JOB_FAILED, \
    EVENT_JOB_NOOP, EVENT_CALLBACK_HOOK, EVENT_UNDEPLOY_HOOK, \
    EVENT_PENDING_HOOK, \
    EVENT_SETUP_APPLICATION_COMPLETE, EVENT_UNDEPLOY_REQUESTED
from orchestrator.tasks.common import async_wait
from orchestrator.util import dict_merge

__author__ = 'sukrit'

__all__ = ['handle_callback_hook', 'undeploy']


def _template_variables(owner, repo, ref, commit=None):
    """
    Creates default template variables for job config.

    :param owner: Git repository owner
    :type owner: str
    :param repo: Git repository name
    :type repo: str
    :param ref: Git branch/tag
    :type ref: str
    :keyword commit: Git commit. (Default: None)
    :type commit: str
    :return: Template variables
    :rtype: dict
    """
    ref_number = ref.lower().replace('feature_', '').replace('patch_', '')
    commit = commit or 'na'
    return {
        'owner': owner,
        'repo': repo,
        'ref': ref,
        'commit': commit,
        'ref_number': ref_number,
        'cluster': CLUSTER_NAME,
        'env': TOTEM_ENV
    }


def _notify_ctx(owner, repo, ref, commit=None, job_id=None, operation=None):
    """
    Creates notification context.

    :param owner: Git repository owner
    :type owner: str
    :param repo: Git repository name
    :type repo: str
    :param ref: Git branch/tag
    :type ref: str
    :keyword commit: Git commit. (Default: None)
    :type commit: str
    :keyword job_id: Optional job identifier (Default: None)
    :type job_id: str
    :keyword operation: Optional operation name (Default: None)
    :type operation: str
    :return: Notification context
    :rtype: dict
    """
    return {
        'owner': owner,
        'repo': repo,
        'ref': ref,
        'commit': commit,
        'cluster': CLUSTER_NAME,
        'job-id': job_id,
        'operation': operation,
        'env': TOTEM_ENV
    }


def _as_callback_hook(hook_name, hook_type, hook_status, force_deploy):
    """
    Creates callback hook representation

    :param hook_name: Name of the hook (e.g.: image-factory)
    :type hook_name: str
    :param hook_type: Type of the hook ('ci' or 'builder')
    :type hook_type: str
    :param hook_status: Status of the hook ('failed' or 'success')
    :type hook_status: str
    :param hook_result: Result of the callback hook.
    :type hook_result: object
    :param force_deploy: Flag controlling Force deploy
    :type hook_result: bool
    :return:
    """
    return {
        'name': hook_name,
        'type': hook_type,
        'status': hook_status,
        'force-deploy': force_deploy
    }


def _load_job_config(owner, repo, ref, notify_ctx, search_params, commit=None):
    """
    Loads the job config for given git parameters

    :param owner: Git repository owner
    :type owner: str
    :param repo: Git repository name
    :type repo: str
    :param ref: Git branch/tag
    :type ref: str
    :param notify_ctx:
    :param search_params:
    :keyword commit: Git commit. (Default: None)
    :type commit: str
    :return: Job Config
    :rtype: dict
    """
    template_vars = _template_variables(owner, repo, ref, commit=commit,)
    try:
        return config.load_config(
            TOTEM_ENV, owner, repo, ref, default_variables=template_vars)
    except BaseException as exc:
        _handle_job_error.si(exc, CONFIG_PROVIDERS['default']['config'],
                             notify_ctx, search_params).delay()
        raise


@app.task
def _handle_job_error(error, job_config, notify_ctx, search_params,
                      job_id=None):
    """
    Handles the error during job creation, processing / undeploy.

    :param error: Error object (dictionary, exception or any object)
    :type error: object
    :param job_config: Job configuration
    :type job_config: dict
    :param notify_ctx: Notification context
    :type notify_ctx: dict
    :param search_params: Search parameters
    :type search_params: dict
    :keyword job_id: Job identifier (optional). Defaults to None. If specified
        job state would be set to failed.
    :type job_id: str
    :return:
    """
    tasks = [
        notify.s(
            ctx=notify_ctx,
            level=LEVEL_FAILED,
            notifications=job_config.get('notifications'),
            security_profile=job_config['security']['profile']),
        add_search_event.si(
            EVENT_JOB_FAILED, details={'job-error': util.as_dict(error)},
            search_params=search_params)
    ]
    if job_id:
        tasks.append(update_job_state.si(job_id, EVENT_JOB_FAILED))
    return group(tasks).delay(error)


@app.task
def handle_callback_hook(owner, repo, ref, hook_type, hook_name,
                         hook_status='success', hook_result=None, commit=None,
                         force_deploy=False):
    """
    Task that handles the processing of a callback hook from CI, SCM or builder

    :param owner: Git repository owner
    :type owner: str
    :param repo: Git repository name
    :type repo: str
    :param ref: Git branch/tag
    :type ref: str
    :param hook_type: Post hook type (ci or builder)
    :type hook_type: str
    :param hook_name: Name of the hook (e.g: image-factory, travis)
    :type hook_name: str
    :keyword hook_status: Status for the hook (success, failed)
    :type hook_status: str
    :keyword hook_result: Results associated with the hook. In case of builder
        hook type, the result contains the built container image url.
    :type hook_result: dict
    :keyword commit: Git commit. (Default: None)
    :type commit: str
    :keyword force_deploy: Flag controlling Force deploy
    :type hook_result: bool
    :return: Task result
    """
    job_config = CONFIG_PROVIDERS['default']['config']
    notify_ctx = _notify_ctx(owner, repo, ref, commit=commit,
                             operation='handle_callback_hook')

    # Create a notification for receiving webhook
    notify.si(
        {'message': 'Received webhook {0}/{1} with status {2}'.format(
            hook_type, hook_name, hook_status)},
        ctx=notify_ctx, level=LEVEL_STARTED,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()

    # Create default search parameters
    search_params = _job_meta(owner, repo, ref, commit=commit)
    job_config = _load_job_config(owner, repo, ref, notify_ctx, search_params,
                                  commit=None)

    try:
        # Making create job sync call to get job-id
        job = _create_job(job_config, owner, repo, ref, commit=commit,
                          force_deploy=force_deploy)
    except BaseException as exc:
        _handle_job_error.si(exc, job_config, notify_ctx, search_params)\
            .delay()
        raise

    # Now that we have job, create search parameters using job
    search_params = create_search_parameters(job)
    job_id = job['meta-info']['job-id']
    notify_ctx = _notify_ctx(owner, repo, ref, commit=commit, job_id=job_id,
                             operation='handle_callback_hook')
    lock_name = '%s-%s-%s-%s' % (TOTEM_ENV, owner, repo, ref)

    # Define error tasks to be executed when task fails. We will use it for
    # add_search_event,_using_lock tasks to update job state,
    # send notifications and update job events.
    error_tasks = [
        _handle_job_error.s(job_config, notify_ctx, search_params, job_id)]
    return (
        add_search_event.si(EVENT_CALLBACK_HOOK,
                            details={
                                'hook': _as_callback_hook(
                                    hook_name, hook_type, hook_status,
                                    force_deploy)
                            },
                            search_params=search_params,
                            error_tasks=error_tasks) |
        _using_lock.si(
            name=lock_name,
            do_task=(
                add_search_event.si(
                    EVENT_ACQUIRED_LOCK, details={'name': lock_name},
                    search_params=search_params) |
                _handle_create_job.si(job) |
                _update_job_ttl.si(owner, repo, ref, commit=commit) |
                _handle_hook.si(job, hook_type, hook_name,
                                hook_status=hook_status,
                                hook_result=hook_result) |
                async_wait.s(
                    default_retry_delay=TASK_SETTINGS['JOB_WAIT_RETRY_DELAY'],
                    max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES'],
                    error_tasks=error_tasks
                )
            ),
        )
    ).delay()


@app.task
def _handle_create_job(job):
    """
    Handles the creation of a job. A new job will be created id the state is
    'NEW'
    :param job: Job parameters
    :type job: dict
    :return: None
    """
    if job['state'] == JOB_STATE_NEW:
        # Index job only if state is new
        search_params = create_search_parameters(job)
        return (
            index_job.si(job) |
            add_search_event.si(EVENT_NEW_JOB, details=job,
                                search_params=search_params)
        ).delay()


@app.task
def undeploy(owner, repo, ref):
    """
    Undeploys the application using git meta data.

    :return: Task Result for undeploy
    """
    search_params = _job_meta(owner, repo, ref)
    notify_ctx = _notify_ctx(owner, repo, ref, commit=None,
                             operation='undeploy')
    job_config = _load_job_config(owner, repo, ref, notify_ctx, search_params,
                                  commit=None)
    lock_name = '%s-%s-%s-%s' % (TOTEM_ENV, owner, repo, ref)
    error_tasks = [
        _handle_job_error.s(job_config, notify_ctx, search_params)]
    return (
        notify.si(
            {'message': 'Undeploy Application for {}-{}-{}'.format(
                owner, repo, ref)},
            ctx=notify_ctx, level=LEVEL_STARTED,
            notifications=job_config.get('notifications'),
            security_profile=job_config['security']['profile']
        ) |
        add_search_event.si(EVENT_UNDEPLOY_HOOK, search_params=search_params,
                            error_tasks=error_tasks) |
        _using_lock.si(
            name=lock_name,
            do_task=(
                add_search_event.si(
                    EVENT_ACQUIRED_LOCK, details={'name': lock_name},
                    search_params=search_params) |
                _update_freeze_status.si(owner, repo, ref, True) |
                _undeploy_all.si(job_config, owner, repo, ref) |
                async_wait.s(
                    default_retry_delay=TASK_SETTINGS['JOB_WAIT_RETRY_DELAY'],
                    max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES'],
                    error_tasks=error_tasks
                ) |
                notify.si(
                    {'message': 'Undeploy requested for for %s-%s-%s'.format(
                        owner, repo, ref)},
                    ctx=notify_ctx, level=LEVEL_SUCCESS,
                    notifications=job_config.get('notifications'),
                    security_profile=job_config['security']['profile']
                ) |
                add_search_event.si(
                    EVENT_UNDEPLOY_REQUESTED, details={'name': lock_name},
                    search_params=search_params)
            ),
        )
    ).apply_async()


@app.task
def _update_freeze_status(owner, repo, ref, freeze=True):
    job_service.update_freeze_status(owner, repo, ref, freeze)


def _job_base_location(owner, repo, ref, etcd_base, commit=None):
    commit = commit or 'not_set'
    return '%s/orchestrator/jobs/%s/%s/%s/%s/commits/%s' % \
           (etcd_base, TOTEM_ENV, owner, repo, ref, commit)


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

    # Convert Serialized signatures
    do_task = signature(do_task)

    error_tasks = [signature(error_task) for error_task in error_tasks]
    cleanup_tasks = [signature(cleanup_task) for cleanup_task in cleanup_tasks]

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
    git_meta = job['meta-info']['git']
    notify_ctx = _notify_ctx(git_meta['owner'], git_meta['repo'],
                             git_meta['ref'], commit=None,
                             operation='handle_hook')
    notify_params = {
        'ctx': notify_ctx,
        'notifications': job_config.get('notifications'),
        'security_profile': job_config['security']['profile']
    }
    search_params = create_search_parameters(job)

    builder_hooks = [name for name, hook_obj in job_config['hooks']['builders']
                     .items() if hook_obj['enabled']]

    tasks = []
    if hook_type == 'scm-create':
        tasks += (
            notify.si(
                {'message': 'Setup Application for {}-{}-{}'.format(
                    git_meta['owner'], git_meta['repo'], git_meta['ref'])},
                level=LEVEL_PENDING,
                **notify_params
            ),
            _update_freeze_status.si(git_meta['owner'], git_meta['repo'],
                                     git_meta['ref'], False),
            add_search_event.si(EVENT_SETUP_APPLICATION_COMPLETE,
                                search_params=search_params),
            notify.si(
                {'message': 'Finished Application Setup for {}-{}-{}'.format(
                    git_meta['owner'], git_meta['repo'], git_meta['ref'])},
                level=LEVEL_SUCCESS,
                **notify_params
            ),
        )
        # Even though we unfreeze the application, we will consider this
        #  job to be noop as no deployment will be created.
        noop = True
    else:
        noop = job_service.is_frozen(
            git_meta['owner'], git_meta['repo'], git_meta['ref'])

    if not job_config['enabled'] or not builder_hooks or \
            not job_config['deployers'] or noop:
        tasks.append(_handle_noop.si(job))

    else:
        tasks.append(_schedule_and_deploy.si(
            job, hook_type, hook_name, hook_status=hook_status,
            hook_result=hook_result))
    return chain(tasks).delay()


@app.task
@using_etcd
def _handle_noop(job, etcd_cl=None, etcd_base=None):
    job = copy.deepcopy(job)
    job_config = job['config']
    job['state'] = JOB_STATE_NOOP
    git = job['meta-info']['git']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])
    search_params = create_search_parameters(job)
    job_id = job['meta-info']['job-id']

    safe_delete(etcd_cl, job_base, recursive=True)
    notify_ctx = _notify_ctx(git['owner'], git['repo'], git['ref'],
                             commit=git['commit'],
                             job_id=job['meta-info']['job-id'],
                             operation='handle_noop')
    notify.si(
        {'message': 'No deployment requested (NOOP)'},
        ctx=notify_ctx, level=LEVEL_SUCCESS,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()
    return (update_job_state.si(job_id, JOB_STATE_NOOP) |
            add_search_event.si(EVENT_JOB_NOOP, search_params=search_params,
                                ret_value=job)
            ).delay()


@app.task
@using_etcd
def _update_etcd_job(job, etcd_cl=None, etcd_base=None):
    """
    Create/update etcd job id and state for a given job.

    :param job: Dictionary containing job parameters
    :type job: dict
    :param etcd_cl: Etcd client for updating hook status in etcd.
    :param etcd_base: Etcd base for job
    :return: Input job for task chaining
    :rtype: dict
    """
    git = job['meta-info']['git']
    job_base = _job_base_location(
        git['owner'], git['repo'], git['ref'], etcd_base, commit=git['commit'])
    etcd_cl.write(job_base+'/job-id', job['meta-info']['job-id'])
    etcd_cl.write(job_base+'/state', job['state'])
    return job


@app.task
@using_etcd
def _update_hook_status(job, hook_type, hook_name, hook_status='success',
                        hook_result=None, etcd_cl=None, etcd_base=None):
    """
     Updates the hook results for the job and triggers the deploy for job.

    :param job: Dictionary containing job parameters
    :param hook_type: Post hook type (ci or builder)
    :param hook_name: Name of the hook (e.g: image-factory, travis)
    :keyword hook_status: Status for the hook (success, failed)
    :keyword hook_result: Results associated with the hook. In case of builder
        hook type, the result contains the built container image url.
    :keyword etcd_cl: Etcd client for updating hook status in etcd.
    :keyword etcd_base: Etcd base for job
    :return:
    """

    job = copy.deepcopy(job)
    job_config = job['config']
    ci_hooks = [name for name, hook_obj in job_config['hooks']['ci']
                .items() if hook_obj['enabled']]
    hook_result = hook_result or {}
    git = job['meta-info']['git']
    job_config = job['config']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])

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
    return job


@app.task
def _schedule_and_deploy(job, hook_type, hook_name, hook_status='success',
                         hook_result=None):
    """
    Prepares the job for deploy

    :param job: Dictionary containing job parameters
    :param hook_type: Post hook type (ci or builder)
    :param hook_name: Name of the hook (e.g: image-factory, travis)
    :param hook_status: Status for the hook (success, failed)
    :param hook_result: Results associated with the hook. In case of builder
        hook type, the result contains the built container image url.
    :return: AsyncResult
    """
    job = copy.deepcopy(job)
    job['state'] = JOB_STATE_SCHEDULED
    job_id = job['meta-info']['job-id']
    return (
        update_job_state.si(job_id, JOB_STATE_SCHEDULED) |
        _update_etcd_job.si(job) |
        _update_hook_status.s(hook_type, hook_name, hook_status=hook_status,
                              hook_result=hook_result) |
        _check_and_fire_deploy.s()
    ).delay()


@app.task
@using_etcd
def _check_and_fire_deploy(job, etcd_cl=None, etcd_base=None):
    """
    Validates pre-conditions for deploy (hook status returned successfully)
    and triggers deploy for enabled deployers.

    :param job: Dictionary containing job parameters
    :param etcd_cl: Etcd client for updating hook status in etcd.
    :param etcd_base: Etcd base for job
    :return: AsyncResult
    """
    # Check and fires deploy
    git = job['meta-info']['git']
    job_base = _job_base_location(git['owner'], git['repo'], git['ref'],
                                  etcd_base, commit=git['commit'])

    hooks = etcd_cl.read(job_base+'/hooks', recursive=True, consistent=True)
    failed_hooks = []
    search_params = create_search_parameters(job)

    # If it is force deploy, status check is ignored
    if not job['force-deploy']:
        for hook_obj in hooks.leaves:
            done_key = basename(hook_obj.key)
            if done_key == 'status':
                if hook_obj.value == 'pending':
                    # Hooks not yet completed. return
                    return add_search_event.si(
                        EVENT_PENDING_HOOK, details={
                            'hook': {
                                'name': basename(dirname(hook_obj.key))
                            }
                        }, search_params=search_params, ret_value=job).delay()
                elif hook_obj.value == 'failed':
                    failed_hooks.append(basename(dirname(hook_obj.key)))

    if failed_hooks:
        return (
            _delete.si(job_base, ret_value=job, recursive=True) |
            _handle_failed_hooks.si(failed_hooks)
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
    job_config = job['config']
    deployers = job_config.get('deployers', {})
    return chord(
        group(
            _deploy.si(job, deployer_name)
            for deployer_name, deployer in deployers.items()
            if deployer.get('enabled') and deployer.get('url')
        ),
        _job_complete.si(job),
    ).apply_async(interval=TASK_SETTINGS['DEPLOY_WAIT_RETRY_DELAY'])


@app.task
def _job_complete(job):
    job = copy.deepcopy(job)
    job_id = job['meta-info']['job-id']
    job['state'] = JOB_STATE_COMPLETE
    search_params = create_search_parameters(job)
    return (
        update_job_state.si(job_id, JOB_STATE_COMPLETE) |
        add_search_event.si(
            EVENT_JOB_COMPLETE, search_params=search_params,
            ret_value=job)
    ).delay()


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
        'security': job_config.get('security', {}),
        'notifications': job_config.get('notifications', {})
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
                             job_id=job['meta-info']['job-id'],
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
def _handle_failed_hooks(failed_hooks):
    raise HooksFailed(failed_hooks)


def _job_meta(owner, repo, ref, commit=None, job_id=None):
    return {
        'meta-info': {
            'git': {
                'owner': owner,
                'repo': repo,
                'ref': ref,
                'commit': commit
            },
            'job-id': job_id
        }
    }


def _as_job(job_config, job_id,  owner, repo, ref, state=JOB_STATE_SCHEDULED,
            commit=None, force_deploy=False):
    return dict_merge({
        'config': copy.deepcopy(job_config),
        'state': state,
        'hooks': {
            'ci': {},
            'scm-create': {},
            'scm-push': {},
            'builder': {}
        },
        'force-deploy': force_deploy
    }, _job_meta(owner, repo, ref, commit=commit, job_id=job_id))
