from celery import chain
from conf.appconfig import TASK_SETTINGS, JOB_SETTINGS, JOB_STATE_NEW, \
    JOB_STATE_SCHEDULED, JOB_STATE_DEPLOY_REQUESTED
from conf.celeryconfig import CLUSTER_NAME
from orchestrator.celery import app
from orchestrator.etcd import using_etcd
from orchestrator.services import config
from orchestrator.services.distributed_lock import LockService, \
    ResourceLockedException

__author__ = 'sukrit'

SUPPORTED_HOOK_TYPES = ('ci', 'builder')


@app.task
def start_job(owner, repo, ref, commit=None):
    """
    Start the Continuous Deployment job

    :return:
    """
    job_config = config.load_config(CLUSTER_NAME, owner, repo, ref)
    return _using_lock.si(
        name='%s-%s-%s-%s' % (CLUSTER_NAME, owner, repo, ref),
        do_task=(
            update_job_ttl.si(owner, repo, ref) |
            create_job.si(job_config, owner, repo, ref)
        )
    ).apply_async()


def _job_base_location(owner, repo, ref, etcd_base):
    return '%s/orchestrator/jobs/%s/%s/%s/%s' % \
           (etcd_base, CLUSTER_NAME, owner, repo, ref)


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
        self.retry(exc=lock_error)

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
def update_job_ttl(owner, repo, ref, ttl=None, etcd_cl=None, etcd_base=None):
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
    job_base = _job_base_location(owner, repo, ref, etcd_base)

    def update_ttl(prev_exist=True):
        etcd_cl.write(job_base, None, ttl=ttl, dir=True, prevExist=prev_exist)
    try:
        update_ttl(True)
    except KeyError:
        # Job does not exists. Lets create a new one
        update_ttl(False)


@app.task
@using_etcd
def create_job(job_config, owner, repo, ref, commit=None, etcd_cl=None,
               etcd_base=None):
    job_base = _job_base_location(owner, repo, ref, etcd_base)

    try:
        state = etcd_cl.read(job_base+'/state').value
    except KeyError:
        state = JOB_STATE_NEW

    if state == JOB_STATE_NEW:
        for hook_type in SUPPORTED_HOOK_TYPES:
            if hook_type in job_config and job_config[hook_type]['enabled']:
                etcd_cl.write('%s/%s/expect' % (job_base, hook_type), 1)
        etcd_cl.write('%s/state' % job_base, 'SCHEDULED')

    elif state == JOB_STATE_SCHEDULED:
        for hook_type in SUPPORTED_HOOK_TYPES:
            if hook_type in job_config and job_config[hook_type]['enabled']:
                expected = etcd_cl.read('%s/%s/expect' %
                                        (job_base, hook_type), 1).value + 1
                etcd_cl.write('%s/%s/expect' % (job_base, hook_type), expected,
                              prevValue=expected-1)

    elif state == JOB_STATE_DEPLOY_REQUESTED:
        pass


@app.task
def load_config(*paths):
    """
    Loads the totem config using given paths

    :param paths:
    :return:
    """
    return config.load_config(paths)
