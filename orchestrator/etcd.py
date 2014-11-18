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
    Performs safe deletion of a given etcd key.

    :param etcd_cl: Etcd Client
    :param key: Key to be deleted
    :param kwargs: Additional arguments for delete.
    :return: None
    """

    try:
        etcd_cl.delete(key, **kwargs)
    except KeyError:
        # Ignore non existent key
        pass


def get_or_insert(etcd_cl, key, value, **kwargs):
    """
    Performs atomic insert for a value if and only if it does not exists.
    If the value exists, no insert/update is performed.
    No exception is raised if value already exists.

    :param etcd_cl:
    :param key:
    :param value:
    :param kwargs:
    :return: None
    """
    try:
        etcd_cl.write(key, value, prevExist=False, **kwargs)
        return value
    except KeyError:
        # Ignore existing key.
        return etcd_cl.read(key, prevExist=True).value
