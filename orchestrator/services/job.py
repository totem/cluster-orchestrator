"""
Services related to job in orchestrator.
All services defined here are synchronous in nature
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import copy
import uuid
import etcd
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from conf.appconfig import TOTEM_ENV, BOOLEAN_TRUE_VALUES, \
    JOB_STATE_SCHEDULED, JOB_STATE_NEW, CLUSTER_NAME, HOOK_STATUS_PENDING, \
    HOOK_STATUS_SUCCESS
from orchestrator.etcd import using_etcd
from orchestrator.services.storage.base import EVENT_NEW_JOB
from orchestrator.services.storage.factory import get_store
from orchestrator.util import dict_merge

__author__ = 'sukrit'

DEFAULT_FREEZE_TTL_SECONDS = 86400


def _app_jobs_base(owner, repo, ref, etcd_base):
    """
    Gets the base location for all jobs for a given application

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :param etcd_base:
    :return:
    """
    return '%s/orchestrator/jobs/%s/%s/%s/%s' % \
           (etcd_base, TOTEM_ENV, owner, repo, ref)


@using_etcd
def update_freeze_status(
        owner, repo, ref, freeze=True, ttl=DEFAULT_FREEZE_TTL_SECONDS,
        etcd_cl=None, etcd_base=None):
    """
    Freezes/Unfreezes all jobs for application identified by
    SCM Repository owner, name and ref for certain time.
    During freeze, no jobs will be executed

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :keyword freeze: Should application be frozen for further deploys ?
    :type freeze: bool
    :keyword ttl: Time to live for application freeze (defined in seconds)
    :type ttl: int
    :keyword etcd_cl: Etcd client
    :type etcd_cl: etcd.Client
    :keyword etcd_base: Etcd base
    :type etcd_base: str
    :return: None
    """
    app_base = _app_jobs_base(owner, repo, ref, etcd_base)
    etcd_cl.write(app_base + '/frozen', freeze, ttl=ttl)


@using_etcd
def is_frozen(owner, repo, ref, etcd_cl=None, etcd_base=None):
    """
    Freezes all jobs for application identified by SCM Repository owner,
    name and ref for certain time. During freeze, no jobs will be executed

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :keyword ttl: Time to live for application freeze (defined in seconds)
    :type ttl: int
    :keyword etcd_cl: Etcd client
    :type etcd_cl: etcd.Client
    :keyword etcd_base: Etcd base
    :type etcd_base: str
    :return: None
    """
    app_base = _app_jobs_base(owner, repo, ref, etcd_base)
    try:
        return etcd_cl.read(app_base + '/frozen').value in BOOLEAN_TRUE_VALUES
    except etcd.EtcdKeyNotFound:
        # Key is not found. Application is not frozen
        return False


def as_job_meta(owner, repo, ref, commit=None, job_id=None):
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


def reset_hook_status(job):
    job = copy.deepcopy(job)
    job_config = job['config']

    for hook_type, hooks in job_config['hooks'].items():
        for hookname, hook in hooks.items():
            if hook.get('enabled', False):
                job['hooks'][hook_type][hookname] = {
                    'status': HOOK_STATUS_PENDING
                }
    return job


def as_job(job_config, job_id,  owner, repo, ref, state=JOB_STATE_SCHEDULED,
           commit=None, force_deploy=False):
    job = dict_merge({
        'meta-info': {
            'git': {
                'commit-set': [commit] if commit else []
            }
        },
        'config': copy.deepcopy(job_config),
        'state': state,
        'hooks': {
            'ci': {},
            'scm-push': {},
            'builder': {},
            'scm-create': {}
        },
        'force-deploy': force_deploy
    }, as_job_meta(owner, repo, ref, commit=commit, job_id=job_id))
    return reset_hook_status(job)


def create_job(job_config, owner, repo, ref, commit=None, force_deploy=False,
               search_params=None):
    """
    Finds or creates a new orchestrator job.
    :param job_config:
    :param owner:
    :param repo:
    :param ref:
    :param commit:
    :param force_deploy:
    :param search_params:
    :return: job
    :rtype: dict
    """
    job_id = str(uuid.uuid4())
    store = get_store()
    existing_jobs = store.filter_jobs(
        owner=owner, repo=repo, ref=ref,
        state_in=[JOB_STATE_NEW, JOB_STATE_SCHEDULED])
    if existing_jobs:
        job = existing_jobs[0]
        if commit and commit not in job['meta-info']['git']['commit-set']:
            job['meta-info']['git']['commit-set'].append(commit)
            job['meta-info']['git']['commit'] = commit
            job = reset_hook_status(job)
            job['config'] = job_config
        else:
            # Skip modification to existing job
            return job

    else:
        job = as_job(job_config, job_id, owner, repo, ref, commit=commit,
                     state=JOB_STATE_NEW, force_deploy=force_deploy)
        search_params = dict_merge({
            'meta-info': {
                'job-id': job['meta-info']['job-id']
            }
        }, search_params)
        store.add_event(EVENT_NEW_JOB,
                        details={
                            'orchestrator-job': job
                        },
                        search_params=search_params)
    store.update_job(job)
    return job


def create_search_parameters(job, defaults=None):
    """
    Creates search parameters for a given job.

    :param deployment: Dictionary containing job parameters.
    :type deployment: dict
    :return: Dictionary containing search parameters
    :rtype: dict
    """

    job = dict_merge(job or {}, defaults or {}, {
        'meta-info': {
            'job-id': None
        }
    })
    return {
        'meta-info': copy.deepcopy(job['meta-info'])
    }


def get_template_variables(owner, repo, ref, commit=None):
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


def as_notify_ctx(owner, repo, ref, commit=None, job_id=None, operation=None):
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


def as_callback_hook(hook_name, hook_type, hook_status, force_deploy):
    """
    Creates callback hook representation

    :param hook_name: Name of the hook (e.g.: image-factory)
    :type hook_name: str
    :param hook_type: Type of the hook ('ci' or 'builder')
    :type hook_type: str
    :param hook_status: Status of the hook ('failed' or HOOK_STATUS_SUCCESS)
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


def prepare_job(job, hook_type, hook_name, hook_status=HOOK_STATUS_SUCCESS,
                hook_result=None, force_deploy=None, ):
    """
    Prepares job prior to deploy by updating hook status and updating the
    state.

    :param job: Job
    :type job: dict
    :param hook_type: Hook type (ci. scm-push, builder)
    :type hook_type: str
    :param hook_name: Name of the hook (imag-factory, travis, ...)
    :type hook_name: str
    :param hook_status: Status of hook (HOOK_STATUS_SUCCESS / 'failed')
    :type hook_status: str
    :keyword hook_result: Result of hook
    :type hook_result: dict
    :return: Updated job
    :rtype: dict
    """
    job = copy.deepcopy(job)
    store = get_store()

    if hook_type in job['hooks'] and hook_name in job['hooks'][hook_type]:
        job['state'] = JOB_STATE_SCHEDULED

        # Update hook status if we were expecting this hook
        job['hooks'][hook_type][hook_name] = {
            'status': hook_status
        }

        job['force-deploy'] = force_deploy or False

        # Check if image is associated with this hook
        image = get_build_image(hook_name, hook_type, hook_status,
                                hook_result)

        # If image is associated , update the image for the job
        if image:
            for deployer in job['config']['deployers'].values():
                deployer['templates']['app']['args']['image'] = image

        # Update the job
        store.update_job(job)
    return job


def get_build_image(hook_name, hook_type, hook_status, hook_result):
    """
    Determines the build image from hook info

    :param hook_name:
    :param hook_type:
    :param hook_status:
    :param hook_result:
    :return: image (non builder hook and failed hooks returns None)
    :rtype: str
    """
    if hook_type == 'builder' and hook_status == HOOK_STATUS_SUCCESS:
        if hook_name == 'quay':
            image_base_url = hook_result.get('docker_url')
            tags = hook_result.get('docker_tags')
            if tags:
                return '{}:{}'.format(image_base_url, tags[0])
            return image_base_url
        if hook_result:
            return hook_result.get('image')
    return None


def check_ready(job):
    """
    Checks if job is ready for deploy
    :return:
    """
    # Force deploy : Ignore hook statuses
    if job.get('force-deploy'):
        return {
            'failed': [],
            HOOK_STATUS_PENDING: []
        }

    failed_hooks = []
    pending_hooks = []
    for hook_type in ('ci', 'builder'):
        for hookname, hook in job['hooks'][hook_type].items():
            status = hook.get('status', HOOK_STATUS_PENDING)
            if status == HOOK_STATUS_PENDING:
                pending_hooks.append(hookname)
            elif status == 'failed':
                failed_hooks.append(hookname)
    return {
        'failed': failed_hooks,
        'pending': pending_hooks
    }
