from functools import wraps
import sys
from etcd import client
from conf.appconfig import HEALTH_OK, HEALTH_FAILED, TOTEM_ETCD_SETTINGS
from orchestrator.elasticsearch import get_search_client


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


@_check
def _check_elasticsearch():
    """
    Checks elasticsearch health by querying info.
    """
    return get_search_client().info()


@_check
def _check_etcd():
    etcd_cl = client.Client(
        host=TOTEM_ETCD_SETTINGS['host'],
        port=TOTEM_ETCD_SETTINGS['port'])
    return {
        'machines': etcd_cl.machines,
        'leader': etcd_cl.leader,
    }


def get_health():
    return {
        'elasticsearch': _check_elasticsearch(),
        'etcd': _check_etcd()
    }
