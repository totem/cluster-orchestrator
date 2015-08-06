from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

import etcd
import yaml
from orchestrator.cluster_config.base import AbstractConfigProvider


class EtcdConfigProvider(AbstractConfigProvider):
    """
    Config provider that uses etcd as the backend
    """

    def __init__(self, etcd_cl=None, etcd_port=None, etcd_host=None,
                 config_base=None, ttl=None):
        """
        Initializes etcd client.

        :param etcd_cl:
        :param etcd_port:
        :param etcd_host:
        :return:
        """
        if not etcd_cl:
            self.etcd_cl = etcd.Client(
                host=etcd_host or 'localhost',
                port=etcd_port or 4001)
        else:
            self.etcd_cl = etcd_cl
        self.config_base = config_base or '/totem/config'
        self.ttl = ttl

    def _etcd_path(self, name, *paths):
        if paths:
            return '%s/%s/%s' % (self.config_base, '/'.join(paths),
                                 name)
        else:
            return '%s/%s' % (self.config_base, name)

    def write(self, name, config, *paths):
        raw = yaml.dump(config)
        self.etcd_cl.set(self._etcd_path(name, *paths), raw, ttl=self.ttl)

    def delete(self, name, *paths):
        try:
            self.etcd_cl.delete(self._etcd_path(name, *paths))
            return True
        except etcd.EtcdKeyNotFound:
            # Ignore as it is safe delete operation
            return False

    def load(self, name, *paths):
        try:
            raw = self.etcd_cl.read(self._etcd_path(name, *paths)).value
        except etcd.EtcdKeyNotFound:
            return dict()
        return yaml.load(raw)
