"""
Provides distributed locking using Etcd Backed store
"""
import uuid

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


class LockService:
    """
    Locking Service for distributed processing to ensure that only one task is
    carried at a time. Locks are based on Optimistic locking , where resource
    tries to write to the store if the value does not exceed. If write is
    successful, lock is acquired else ResourceLockedException is thrown and
    application should retry to apply the lock.

    Locks expire after certain TTL (Default: 600s). So the processing must
    finish during this timeframe.
    """

    def __init__(self, etcd_cl=None, etcd_base=TOTEM_ETCD_SETTINGS['base'],
                 lock_base='/orchestrator/locks/apps', lock_ttl=600):
        """
        :param etcd_cl: Etcd Client instance. If None, a new client is created
            based on env settings.
        :type etcd_cl: etcd.Client
        :param etcd_base: Base Key for totem etcd. Defaults to /totem (From
            TOTEM_ETCD_SETTINGS
        :type etcd_base: str
        :param lock_base: Base folder to be used to store lock keys.
        :type lock_base: str
        :param lock_ttl: TTL for Locks in seconds. Defaults to 600s
        :type lock_ttl: int
        """
        self.etcd_cl = etcd_cl or get_etcd_client()
        self.etcd_base = etcd_base
        self.lock_base = lock_base
        self.lock_ttl = lock_ttl

    def apply_lock(self, app_name):
        """
        Applies lock for given application.

        :param app_name: Name of application/resource that needs to be locked
        :type app_name: str
        :return: Lock dictionary comprising of key, name and value. This dict
            is used to release the locks later
        :rtype: dict
        """
        lock_key = '%s%s/%s' % (self.etcd_base, self.lock_base, app_name)
        lock_value = uuid.uuid4()
        try:
            self.etcd_cl.write(lock_key, lock_value, ttl=self.lock_ttl,
                               prevExist=False)
        except KeyError:
            raise ResourceLockedException(name=app_name, key=lock_key)
        return {
            'key': lock_key,
            'name': app_name,
            'value': lock_value
        }

    def release(self, lock):
        """
        Release the lock created by apply_lock.

        :param lock: Lock dictionary created by apply_lock
        :type lock: dict
        """
        if lock:
            try:
                self.etcd_cl.delete(lock['key'], prevValue=lock['value'])
                return True
            except KeyError:
                return False
            except ValueError:
                return False
        else:
            return False


class ResourceLockedException(Exception):
    """
    Exception representing that resource is already locked.
    """

    def __init__(self, name, key):
        """
        :param name: Name of the resource that could not be locked
        :type name: str
        :param key: Resource key
        :type key: str
        :return: None
        """
        self.name = name
        self.key = key
        super(ResourceLockedException, self).__init__(name, key)

    def to_dict(self):
        """
        Creates dictionary representation for the exception

        :return: dictionary representation for the exception.
        :rtype: dict
        """
        return {
            'message': 'Resource %s with key %s is already locked.' %
                       (self.name, self.key),
            'code': 'RESOURCE_LOCKED',
            'details': {
                'name': self.name,
                'key': self.key
                }
        }
