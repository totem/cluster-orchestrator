from functools import wraps
import sys
from etcd import client
from conf.appconfig import HEALTH_OK, HEALTH_FAILED, TOTEM_ETCD_SETTINGS, \
    SEARCH_SETTINGS
from orchestrator.elasticsearch import get_search_client
from orchestrator.tasks.common import ping
from orchestrator.util import timeout

HEALTH_TIMEOUT_SECONDS = 10


def _check(func):
    """
    Wrapper that creates a dictionary response  containing 'status' and
    'details'.
    where status can be
        'ok': If wrapped function returns successfully.
        'failed': If wrapped function throws error.
    details is:
        returned value from the wrapped function if no exception is thrown
        else string representation of exception when exception is thrown

    :param func: Function to be wrapped
    :return: dictionary output containing keys 'status' and 'details'
    :rtype: dict
    """

    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return {
                'status': HEALTH_OK,
                'details': func(*args, **kwargs)
            }
        except:
            return {
                'status': HEALTH_FAILED,
                'details': str(sys.exc_info()[1])
            }
    return inner


@timeout(HEALTH_TIMEOUT_SECONDS)
@_check
def _check_elasticsearch():
    """
    Checks elasticsearch health by querying info.
    """
    return get_search_client().info()


@timeout(HEALTH_TIMEOUT_SECONDS)
@_check
def _check_etcd():
    etcd_cl = client.Client(
        host=TOTEM_ETCD_SETTINGS['host'],
        port=TOTEM_ETCD_SETTINGS['port'])
    return {
        'machines': etcd_cl.machines,
        'leader': etcd_cl.leader,
    }


@timeout(HEALTH_TIMEOUT_SECONDS)
@_check
def _check_celery():
    """
    Checks health for celery integration using ping-pong task output.
    """
    output = ping.delay().get(timeout=HEALTH_TIMEOUT_SECONDS)
    return 'Celery ping:%s' % output


def get_health():
    """
    Gets the health of the all the external services.

    :return: dictionary with
        key: service name like etcd, celery, elasticsearch
        value: dictionary of health status
    :rtype: dict
    """

    health_status = {
        'etcd': _check_etcd(),
        'celery': _check_celery()
    }
    if SEARCH_SETTINGS['enabled']:
        health_status['elasticsearch'] = _check_elasticsearch()
    return health_status
