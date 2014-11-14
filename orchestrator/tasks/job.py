import copy
import uuid
from celery import chain
from conf.appconfig import TASK_SETTINGS, JOB_SETTINGS, JOB_STATE_NEW, \
    JOB_STATE_SCHEDULED, JOB_STATE_DEPLOY_REQUESTED, JOB_STATE_NOOP
from conf.celeryconfig import CLUSTER_NAME
from orchestrator.celery import app
from orchestrator.etcd import using_etcd, safe_delete
from orchestrator.services import config
from orchestrator.services.distributed_lock import LockService, \
    ResourceLockedException
from orchestrator.tasks.search import index_job
from orchestrator.tasks.common import async_wait

__author__ = 'sukrit'


@app.task
def start_job(owner, repo, ref, scm_type='github', commit=None):
    """
    Start the Continuous Deployment job

    :return:
    """
    job_config = config.load_config(CLUSTER_NAME, owner, repo, ref)
    return _using_lock.si(
        name='%s-%s-%s-%s' % (CLUSTER_NAME, owner, repo, ref),
        do_task=(
            update_job_ttl.si(owner, repo, ref) |
            create_job.si(job_config, owner, repo, ref, scm_type) |
            async_wait.s(
                default_retry_delay=TASK_SETTINGS[
                    'JOB_WAIT_RETRY_DELAY'],
                max_retries=TASK_SETTINGS['JOB_WAIT_RETRIES']
            )
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


@app.task(bind=True)
@using_etcd
def create_job(self, job_config, owner, repo, ref, scm_type, commit=None,
               etcd_cl=None, etcd_base=None):
    job_base = _job_base_location(owner, repo, ref, etcd_base)

    # If we can not get branch, in that case we can not guarantee the
    # co-relation of ci jobs with builder, but hooks can still be received.
    commit = commit or ''

    try:
        state = etcd_cl.read(job_base+'/state').value
        job_id = etcd_cl.read(job_base+'/job-id').value
    except KeyError:
        state = JOB_STATE_NEW
        job_id = str(uuid.uuid4())

    job = _as_job(job_config, job_id, owner, repo, ref, scm_type, commit)

    if state in (JOB_STATE_NEW, JOB_STATE_SCHEDULED):

        scm_hooks = [name for name, hook in job_config['hooks']['scm'].items()
                     if hook['enabled']]

        builder_hooks = [name for name, hook in job_config['hooks']['builders']
                         .items() if hook['enabled']]

        if not scm_hooks or not builder_hooks or \
                (state in (JOB_STATE_NEW, JOB_STATE_SCHEDULED) and
                    scm_type not in scm_hooks):
            return _handle_noop.si(job)()

        else:
            # Reset/ Create the new job
            return _reset_job.si(job)()

    elif state == JOB_STATE_DEPLOY_REQUESTED:
        # Can not reset as deploy has started.  Let the current job get
        # processed before starting new one. Processed job does not mean
        # successful deployment. It simply means that deployer has acknowledged
        # the new deployment request.
        self.retry(exc=ValueError(
            'Job exists is in %s state. Can not create new '
            'job until existing one gets removed.'))


@app.task
@using_etcd
def _handle_noop(job, etcd_cl=None, etcd_base=None):
    job = copy.deepcopy(job)
    job['state'] = JOB_STATE_NOOP
    meta = job['meta-info']
    job_base = _job_base_location(meta['owner'], meta['repo'], meta['ref'],
                                  etcd_base)
    safe_delete(etcd_cl, job_base, recursive=True)
    return index_job.si(job, ret_value=job)


@app.task
def _reset_job(job):
    job = copy.deepcopy(job)
    job['state'] = JOB_STATE_SCHEDULED
    return (
        _save_job.si(job) |
        index_job.si(job, ret_value=job)
    )()


@app.task
@using_etcd
def _save_job(job, etcd_cl=None, etcd_base=None):
    meta = job['meta-info']
    job_config = job['config']
    job_base = _job_base_location(meta['owner'], meta['repo'], meta['ref'],
                                  etcd_base)
    etcd_cl.write(job_base+'/job-id', meta['job-id'])
    # We will now expect to receive callbacks for new commit.
    etcd_cl.write(job_base+'/commit', meta['commit'])
    ci_hooks = [name for name, hook in job_config['hooks']['ci']
                .items() if hook['enabled']]
    for ci_hook in ci_hooks:
        etcd_cl.write('%s/hooks/ci/%s/done' % (job_base, ci_hook),
                      False)
    etcd_cl.write(job_base+'/state', job['state'])


def _as_job(job_config, job_id,  owner, repo, ref, scm_type, commit=None):
    return {
        'config': copy.deepcopy(job_config),
        'meta-info': {
            'owner': owner,
            'repo': repo,
            'ref': ref,
            'commit': commit,
            'scm': scm_type,
            'job-id': job_id
        }
    }
