"""
Module for updating/searching elastic search.
"""
import copy
import datetime
from conf.appconfig import DEPLOYMENT_STATE_PROMOTED, \
    DEPLOYMENT_STATE_DECOMMISSIONED

from deployer.celery import app
from deployer.elasticsearch import deployment_search
from deployer.util import dict_merge


TYPE_JOBS = 'jobs'
TYPE_EVENTS = 'events'

EVENT_NEW_JOB = 'NEW_JOB'
EVENT_ACQUIRED_LOCK = 'ACQUIRED_LOCK'
EVENT_CI_SUCCESS = 'CI_SUCCESS'
EVENT_CI_FAILED = 'CI_FAILED'
EVENT_BUILDER_SUCCESS = 'BUILDER_SUCCESS'
EVENT_BUILDER_FAILED = 'BUILDER_FAILED'

@app.task
@deployment_search
def index_job(deployment, es=None, idx=None):
    """
    Creates a new deployment
    :param deployment: Dictionary containing deployment parameters
    """
    return es.index(idx, TYPE_DEPLOYMENTS, deployment, id=deployment['id'])


@app.task
@deployment_search
def update_deployment_state(id, state, ret_value=None, es=None, idx=None):
    """
    Updates the deployment state

    :param id: Id for the deployment
    :param state: State for the deployment
    :keyword ret_value: Value to be returned. If None, the updated search
     document is returned.
    """
    updated_doc = es.update(idx, TYPE_DEPLOYMENTS, id, body={
        'doc': {
            'state': state
        }
    })
    return ret_value or updated_doc


def create_search_parameters(deployment, defaults=None):
    """
    Creates search parameters for a given deployment.

    :param deployment: Dictionary containing deployment parameters.
    :type deployment: dict
    :return: Dictionary containing search parameters
    :rtype: dict
    """

    deployment = dict_merge(deployment or {}, defaults or {}, {
        'meta-info': {}
    })
    return {
        'meta-info': copy.deepcopy(deployment['meta-info']),
        'deployment': {
            'name': deployment['deployment']['name'],
            'version': deployment['deployment']['version'],
            'id': deployment['id']
        }
    }


@app.task
@deployment_search
def add_search_event(event_type, details=None, search_params={}, es=None,
                     idx=None):
    event_upd = copy.deepcopy(search_params)
    event_upd.update({
        'type': event_type,
        'details': details,
        'date': datetime.datetime.utcnow(),
    })
    return es.create(idx, TYPE_EVENTS, event_upd)


@deployment_search
def find_apps(es=None, idx=None):
    results = es.search(idx, doc_type=TYPE_DEPLOYMENTS, body={
        'size': 0,
        'aggs': {
            'apps': {
                'terms': {
                    'field': 'deployment.name'
                }
            }
        }
    })
    return [bucket['key'] for bucket in
            results['aggregations']['apps']['buckets']]


@app.task
@deployment_search
def get_promoted_deployments(name, version=None, es=None, idx=None):
    query = {
        # Not expecting more than 1000 promoted deployments for a given app
        'size': 1000,
        "fields": [],
        "filter": {
            "and": [
                {"term": {"deployment.name": name}},
                {"term": {"deployment.version": version}} if version else {},
                {"term": {"state": DEPLOYMENT_STATE_PROMOTED}}

            ]
        }
    }
    results = es.search(idx, TYPE_DEPLOYMENTS, body=query)

    return [hit['_id'] for hit in results['hits']['hits']]


@app.task
@deployment_search
def mark_decommissioned(ids, es=None, idx=None):
    if ids:
        body = list()
        for _id in ids:
            body += [
                {'update': {'_id': _id}},
                {'doc': {'state': DEPLOYMENT_STATE_DECOMMISSIONED}}
            ]
        return es.bulk(body, index=idx, doc_type=TYPE_DEPLOYMENTS)


@deployment_search
def find_deployments(name, version=None, page=0, size=10, es=None, idx=None):
    query = {
        "size": size,
        "from": page,
        "filter": {
            "and": [
                {"term": {"deployment.name": name}},
                {"term": {"deployment.version": version}} if version else {}
            ]
        }
    }
    results = es.search(idx, TYPE_DEPLOYMENTS, body=query)
    return [hit['_source'] for hit in results['hits']['hits']]
