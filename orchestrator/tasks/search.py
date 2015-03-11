"""
Module for updating/searching elastic search.
"""
import copy
import datetime
from conf.appconfig import DOC_TYPE_JOBS, DOC_TYPE_EVENTS

from orchestrator.celery import app
from orchestrator.elasticsearch import orch_search
from orchestrator.tasks.common import ErrorHandlerTask
from orchestrator.util import dict_merge


EVENT_NEW_JOB = 'NEW_JOB'
EVENT_ACQUIRED_LOCK = 'ACQUIRED_LOCK'
EVENT_CALLBACK_HOOK = 'CALLBACK_HOOK'
EVENT_UNDEPLOY_HOOK = 'UNDEPLOY_HOOK'
EVENT_DEPLOY_REQUESTED = 'DEPLOY_REQUESTED'
EVENT_JOB_COMPLETE = 'JOB_COMPLETE'
EVENT_JOB_FAILED = 'JOB_FAILED'
EVENT_JOB_NOOP = 'JOB_NOOP'
EVENT_PENDING_HOOK = 'PENDING_HOOK'


def massage_config(config):
    """
    massages config for indexing.
    1. Removes encrypted parameters from indexing.
    2. Extracts raw parameter for value types.

    :param config: dictionary that needs to be massaged
    :type config: dict
    :return: massaged config
    :rtype: dict
    """

    if hasattr(config, 'items'):
        if 'value' in config:

            if config.get('encrypted', False):
                return ''
            else:
                return str(config.get('value'))
        else:
            return {
                k: massage_config(v) for k, v in config.items()
            }
    elif isinstance(config, (list, set, tuple)):
        return [massage_config(v) for v in config]
    else:
        return config


@app.task
@orch_search
def index_job(job, ret_value=None, es=None, idx=None):
    """
    Creates a new deployment index.

    :param deployment: Dictionary containing deployment parameters
    :type deployment: dict
    """
    es.index(idx, DOC_TYPE_JOBS, massage_config(job),
             id=job['meta-info']['job-id'])
    return ret_value or job


@app.task
@orch_search
def update_job_state(id, state, ret_value=None, es=None, idx=None):
    """
    Updates the job state

    :param id: Id for the job
    :param state: State for the job
    :keyword ret_value: Value to be returned. If None, the updated search
     document is returned.
    """
    updated_doc = es.update(idx, DOC_TYPE_JOBS, id, body={
        'doc': {
            'state': state
        }
    })
    return ret_value or updated_doc


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
            'job-id': 'not_set'
        }
    })
    return {
        'meta-info': copy.deepcopy(job['meta-info'])
    }


@app.task(base=ErrorHandlerTask)
@orch_search
def add_search_event(event_type, details=None, search_params={}, es=None,
                     idx=None, ret_value=None, next_task=None,
                     error_tasks=None):
    """
    Adds search event for the job in elasticsearch.

    :param event_type:
    :param details:
    :param search_params:
    :param es:
    :param idx:
    :return:
    """
    event_upd = copy.deepcopy(search_params)
    event_upd.update({
        'type': event_type,
        'details': massage_config(details),
        'date': datetime.datetime.utcnow(),
        'component': 'orchestrator'
    })
    es.create(idx, DOC_TYPE_EVENTS, event_upd)
    return ret_value
