import copy
import json
import requests
from celery import chain, chord, group
from requests.exceptions import ConnectionError
from conf.appconfig import TASK_SETTINGS, \
    JOB_STATE_COMPLETE, JOB_STATE_NOOP, \
    DEFAULT_DEPLOYER_URL, CONFIG_PROVIDERS, LEVEL_FAILED, LEVEL_STARTED, \
    LEVEL_SUCCESS, TOTEM_ENV, JOB_STATE_FAILED, HOOK_STATUS_SUCCESS
from orchestrator.services import job as job_service
from orchestrator.celery import app
from orchestrator.services import config
from orchestrator.services.distributed_lock import LockService, \
    ResourceLockedException
from orchestrator.services.job import as_job_meta, create_job, \
    create_search_parameters, get_template_variables, as_notify_ctx, \
    as_callback_hook, prepare_job, check_ready
from orchestrator.services.storage.factory import get_store
from orchestrator.tasks import util
from orchestrator.tasks.exceptions import DeploymentFailed, HooksFailed
from orchestrator.tasks.notification import notify
from orchestrator.services.storage.base import \
    EVENT_DEPLOY_REQUESTED, EVENT_JOB_COMPLETE, \
    EVENT_JOB_FAILED, \
    EVENT_JOB_NOOP, EVENT_CALLBACK_HOOK, EVENT_UNDEPLOY_HOOK, \
    EVENT_PENDING_HOOK, \
    EVENT_SETUP_APPLICATION_COMPLETE, EVENT_UNDEPLOY_REQUESTED, \
    EVENT_COMMIT_IGNORED, EVENT_HOOK_IGNORED
from orchestrator.tasks.common import async_wait, ErrorHandlerTask
from orchestrator.util import dict_merge

__author__ = 'sukrit'

__all__ = ['handle_callback_hook', 'undeploy']


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
    template_vars = get_template_variables(owner, repo, ref, commit=commit,)
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
    notify.si(
        error,
        ctx=notify_ctx,
        level=LEVEL_FAILED,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']).delay()

    store = get_store()
    store.add_event(
        EVENT_JOB_FAILED, details={'job-error': util.as_dict(error)},
        search_params=search_params)
    if job_id:
        store.update_state(job_id, EVENT_JOB_FAILED)


@app.task
def _new_job(job_config, owner, repo, ref, hook_type, hook_name,
             hook_status=HOOK_STATUS_SUCCESS, hook_result=None, commit=None,
             force_deploy=None):
    notify_ctx = as_notify_ctx(
        owner, repo, ref, commit=commit, operation='handle_callback_hook')
    search_params = as_job_meta(owner, repo, ref, commit=commit)
    try:
        # Making create job sync call to get job-id
        job = create_job(job_config, owner, repo, ref, commit=commit,
                         force_deploy=force_deploy,
                         search_params=search_params)
    except BaseException as exc:
        _handle_job_error.si(exc, job_config, notify_ctx, search_params) \
            .delay()
        raise
    pass
    # Now that we have job, create search parameters using job
    search_params = create_search_parameters(job)
    search_params['meta-info']['git']['commit'] = commit
    job_id = job['meta-info']['job-id']
    notify_ctx = as_notify_ctx(
        owner, repo, ref, commit=commit, job_id=job_id,
        operation='handle_callback_hook')
    error_tasks = [
        _handle_job_error.s(job_config, notify_ctx, search_params, job_id)]

    job_commit = job['meta-info']['git']['commit']
    if commit and commit != job_commit:
        get_store().add_event(
            EVENT_COMMIT_IGNORED,
            details={
                'message': 'Commit: {} was superseded by {}'.format(
                    commit, job_commit),
                'commit': commit
            },
            search_params=search_params
        )
        return job

    if hook_type not in job['hooks'] or \
            hook_name not in job['hooks'][hook_type] or \
            not job['hooks'][hook_type][hook_name].get('enabled'):
        get_store().add_event(
            EVENT_HOOK_IGNORED,
            details={
                'message': 'Hook: {} with type {} is not configured/disabled '
                           'and will be ignored'.format(hook_name, hook_type),
                'hook_name': hook_name,
                'hook_type': hook_type
            },
            search_params=search_params
        )
        return job

    return (
        _handle_hook.si(job, hook_type, hook_name, hook_status=hook_status,
                        hook_result=hook_result, error_tasks=error_tasks,
                        force_deploy=force_deploy) |
        async_wait.s(
            default_retry_delay=TASK_SETTINGS['JOB_WAIT_RETRY_DELAY'],
            max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES'],
            error_tasks=error_tasks
        )
    ).delay()


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
    notify_ctx = as_notify_ctx(owner, repo, ref, commit=commit,
                               operation='handle_callback_hook')
    # Create default search parameters
    search_params = as_job_meta(owner, repo, ref, commit=commit)
    job_config = _load_job_config(owner, repo, ref, notify_ctx, search_params,
                                  commit=commit)

    # Create a notification for receiving webhook
    notify.si(
        {'message': 'Received webhook {0}/{1} with status {2}'.format(
            hook_type, hook_name, hook_status)},
        ctx=notify_ctx, level=LEVEL_STARTED,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()

    lock_name = '{}-{}-{}-{}'.format(TOTEM_ENV, owner, repo, ref)

    # Define error tasks to be executed when task fails. We will use it for
    # add_search_event,_using_lock tasks to update job state,
    # send notifications and update job events.

    get_store().add_event(EVENT_CALLBACK_HOOK,
                          details={
                              'hook': as_callback_hook(
                                  hook_name, hook_type, hook_status,
                                  force_deploy)
                          },
                          search_params=search_params)

    return (
        _using_lock.si(
            name=lock_name,
            do_task=(
                _new_job.si(
                    job_config, owner, repo, ref, hook_type, hook_name,
                    hook_status=hook_status, hook_result=hook_result,
                    commit=commit, force_deploy=force_deploy)
            ),
        )
    ).delay()


@app.task
def undeploy(owner, repo, ref):
    """
    Undeploys the application using git meta data.

    :return: Task Result for undeploy
    """
    search_params = as_job_meta(owner, repo, ref)
    notify_ctx = as_notify_ctx(owner, repo, ref, commit=None,
                               operation='undeploy')
    job_config = _load_job_config(owner, repo, ref, notify_ctx, search_params,
                                  commit=None)
    lock_name = '%s-%s-%s-%s' % (TOTEM_ENV, owner, repo, ref)
    error_tasks = [
        _handle_job_error.s(job_config, notify_ctx, search_params)]
    notify.si(
        {'message': 'Undeploy Application for {}-{}-{}'.format(
            owner, repo, ref)},
        ctx=notify_ctx, level=LEVEL_STARTED,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()

    store = get_store()
    store.add_event(EVENT_UNDEPLOY_HOOK, search_params=search_params,
                    error_tasks=error_tasks)
    return (
        _using_lock.si(
            name=lock_name,
            do_task=(
                _update_freeze_status.si(owner, repo, ref, True) |
                _undeploy_all.si(job_config, owner, repo, ref, notify_ctx,
                                 search_params=search_params) |
                async_wait.s(
                    default_retry_delay=TASK_SETTINGS['JOB_WAIT_RETRY_DELAY'],
                    max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES'],
                    error_tasks=error_tasks
                )
            ),
        )
    ).apply_async()


@app.task
def _update_freeze_status(owner, repo, ref, freeze=True):
    job_service.update_freeze_status(owner, repo, ref, freeze)


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


@app.task(base=ErrorHandlerTask)
def _handle_hook(job, hook_type, hook_name, hook_status, hook_result,
                 error_tasks=None, force_deploy=None):
    job_config = job['config']
    git_meta = job['meta-info']['git']
    search_params = create_search_parameters(job)

    builder_hooks = [name for name, hook_obj in job_config['hooks']['builder']
                     .items() if hook_obj['enabled']]
    store = get_store()

    if hook_type == 'scm-create':
        job_service.update_freeze_status(git_meta['owner'], git_meta['repo'],
                                         git_meta['ref'], False)
        store.add_event(EVENT_SETUP_APPLICATION_COMPLETE,
                        search_params=search_params)
        # Even though we unfreeze the application, we will consider this
        #  job to be noop as no deployment will be created.
        noop = True
    else:
        noop = job_service.is_frozen(git_meta['owner'], git_meta['repo'],
                                     git_meta['ref'])

    if not job_config['enabled'] or not builder_hooks or \
            not job_config['deployers'] or noop:
        return _handle_noop(job)

    job = prepare_job(job, hook_type, hook_name, hook_status, hook_result,
                      force_deploy=force_deploy)
    return _check_and_fire_deploy.si(job).delay()


def _handle_noop(job):
    job = copy.deepcopy(job)
    job_config = job['config']
    job['state'] = JOB_STATE_NOOP
    git = job['meta-info']['git']
    search_params = create_search_parameters(job)
    job_id = job['meta-info']['job-id']
    notify_ctx = as_notify_ctx(git['owner'], git['repo'], git['ref'],
                               commit=git['commit'],
                               job_id=job['meta-info']['job-id'],
                               operation='handle_noop')
    notify.si(
        {'message': 'No deployment requested (NOOP)'},
        ctx=notify_ctx, level=LEVEL_SUCCESS,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()
    store = get_store()
    store.update_state(job_id, JOB_STATE_NOOP)
    store.add_event(EVENT_JOB_NOOP, search_params=search_params)
    return job


@app.task
def _check_and_fire_deploy(job):
    """
    Validates pre-conditions for deploy (hook status returned successfully)
    and triggers deploy for enabled deployers.

    :param job: Dictionary containing job parameters
    :return: job or AsyncResult
    """
    # Check and fires deploy
    job_id = job['meta-info']['job-id']

    search_params = create_search_parameters(job)
    store = get_store()

    check = check_ready(job)
    if check.get('failed'):
        store.update_state(job_id, JOB_STATE_FAILED)
        raise HooksFailed(check['failed'])

    elif check['pending']:
        store.add_event(EVENT_PENDING_HOOK, details={
            'pending-hooks': check['pending']
        }, search_params=search_params)
        return job

    else:
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
    store = get_store()
    search_params = create_search_parameters(job)
    store.update_state(job_id, JOB_STATE_COMPLETE)
    store.add_event(EVENT_JOB_COMPLETE, search_params=search_params)
    return job


@app.task(bind=True,
          default_retry_delay=TASK_SETTINGS['DEPLOY_WAIT_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['DEPLOY_WAIT_RETRIES'])
def _deploy(self, job, deployer_name):
    job_config = job['config']
    deployer = job_config['deployers'][deployer_name]
    deployer_url = deployer.get('url', DEFAULT_DEPLOYER_URL)
    apps_url = '{}/apps'.format(deployer_url)
    headers = {
        'content-type': 'application/vnd.deployer.app.version.create.v1+json',
        'accept': 'application/vnd.deployer.task.v1+json'
    }
    meta_info = dict_merge(job['meta-info'], {
        'deployer': {
            'name': deployer_name,
            'url': deployer_url
        }
    })
    data = {
        'meta-info': meta_info,
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
        'response': {'raw': response.text},
        'status': response.status_code
    }
    store = get_store()
    store.add_event(EVENT_DEPLOY_REQUESTED, details=deploy_response,
                    search_params=search_params)
    if response.status_code in (502, 503):
        raise self.retry(exc=DeploymentFailed(deploy_response))

    if deploy_response['status'] >= 400:
        raise DeploymentFailed(deploy_response)

    git = job['meta-info']['git']
    notify_ctx = as_notify_ctx(git['owner'], git['repo'], git['ref'],
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


@app.task
def _undeploy_requested(job_config, owner, repo, ref, search_params,
                        notify_ctx):
    get_store().add_event(EVENT_UNDEPLOY_REQUESTED,
                          search_params=search_params)
    notify.si(
        {'message': 'Undeploy requested for for %s-%s-%s'.format(
            owner, repo, ref)},
        ctx=notify_ctx, level=LEVEL_SUCCESS,
        notifications=job_config.get('notifications'),
        security_profile=job_config['security']['profile']
    ).delay()


@app.task(default_retry_delay=TASK_SETTINGS['DEFAULT_RETRY_DELAY'],
          max_retries=TASK_SETTINGS['DEFAULT_RETRIES'])
def _undeploy_all(job_config, owner, repo, ref, notify_ctx,
                  search_params=None):
    deployers = job_config.get('deployers', {})

    return chord(
        group(
            _undeploy.si(job_config, owner, repo, ref, deployer_name)
            for deployer_name, deployer in deployers.items()
            if deployer.get('enabled') and deployer.get('url')
        ),
        _undeploy_requested.si(job_config, owner, repo, ref, search_params,
                               notify_ctx)
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
