"""
Module for updating/searching elastic search.
"""
import copy
import datetime

from orchestrator.celery import app
from orchestrator.elasticsearch import orch_search
from orchestrator.util import dict_merge


TYPE_JOBS = 'jobs'
TYPE_EVENTS = 'events'

EVENT_NEW_JOB = 'NEW_JOB'
EVENT_ACQUIRED_LOCK = 'ACQUIRED_LOCK'
EVENT_CI_SUCCESS = 'CI_SUCCESS'
EVENT_CI_FAILED = 'CI_FAILED'
EVENT_BUILDER_SUCCESS = 'BUILDER_SUCCESS'
EVENT_BUILDER_FAILED = 'BUILDER_FAILED'


@app.task
@orch_search
def index_job(deployment, es=None, idx=None):
    """
    Creates a new deployment
    :param deployment: Dictionary containing deployment parameters
    """
    return es.index(idx, TYPE_JOBS, deployment, id=deployment['id'])


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
    updated_doc = es.update(idx, TYPE_JOBS, id, body={
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


@app.task
@orch_search
def add_search_event(event_type, details=None, search_params={}, es=None,
                     idx=None):
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
        'details': details,
        'date': datetime.datetime.utcnow(),
    })
    return es.create(idx, TYPE_EVENTS, event_upd)
