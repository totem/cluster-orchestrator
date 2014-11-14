from __future__ import absolute_import
from functools import wraps
import etcd
from conf.appconfig import TOTEM_ETCD_SETTINGS

__author__ = 'sukrit'


def get_etcd_client():
    """
    Gets the Etcd Client instance using host and port defined in
    TOTEM_ETCD_SETTINGS

    :return: Instance of etcd.Client
    :rtype: etcd.Client
    """
    return etcd.Client(host=TOTEM_ETCD_SETTINGS['host'],
                       port=TOTEM_ETCD_SETTINGS['port'])


def using_etcd(func):
    """
    Function wrapper that automatically passes etcd to
    wrapped function.

    :param func: Function to be wrapped
    :return: Wrapped function.
    """
    @wraps(func)
    def outer(*args, **kwargs):
        kwargs.setdefault('etcd_cl', get_etcd_client())
        kwargs.setdefault('etcd_base', TOTEM_ETCD_SETTINGS['base'])
        return func(*args, **kwargs)
    return outer


def safe_delete(etcd_cl, key, **kwargs):
    """
    Performs safe deleteion of a given etcd key.

    :param func:
    :param key:
    :param kwargs:
    :return:
    """

    try:
        etcd_cl.delete(key, **kwargs)
    except KeyError:
        # Ignore non existent key
        pass
