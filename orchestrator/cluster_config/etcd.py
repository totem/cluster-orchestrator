import etcd
import yaml
from orchestrator.cluster_config.base import AbstractConfigProvider


class EtcdConfigProvider(AbstractConfigProvider):
    """
    Config provider that uses etcd as the backend
    """

    def __init__(self, etcd_cl=None, etcd_port=None, etcd_host=None,
                 config_base=None, ttl=None, config_name='.totem.yml'):
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
        self.config_name = config_name

    def _etcd_path(self, *paths):
        return '%s/%s/%s' % (self.config_base, '/'.join(paths),
                             self.config_name)

    def write(self, config, *paths):
        raw = yaml.dump(config)
        self.etcd_cl.set(self._etcd_path(*paths), raw, ttl=self.ttl)

    def delete(self, *paths):
        try:
            self.etcd_cl.delete(self._etcd_path(*paths))
            return True
        except KeyError:
            # Ignore as it is safe delete operation
            return False

    def load(self, *paths):
        try:
            raw = self.etcd_cl.read(self._etcd_path(*paths)).value
        except KeyError:
            return dict()
        return yaml.load(raw)
