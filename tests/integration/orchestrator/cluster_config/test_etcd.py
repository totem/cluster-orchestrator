import etcd
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from nose.tools import eq_
from orchestrator.cluster_config.etcd import EtcdConfigProvider
from tests.helper import dict_compare

__author__ = 'sukrit'

MOCK_CONFIG = {
    'mockkey1': 'mockvalue1',
    'mockkey2': {
        'mockkey3': 'mockvalue3'
    }
}

MOCK_SERIALIZED_CONFIG = '''mockkey1: mockvalue1
mockkey2: {mockkey3: mockvalue3}
'''


class TestEtcdConfigProvider:
    """
    Integration tests for EtcdConfigProvide
    """

    @classmethod
    def setup_class(cls):
        cls.etcd_cl = etcd.Client()
        cls.config_base = '/totem-integration/config'

    @classmethod
    def teardown_class(cls):
        try:
            cls.etcd_cl.delete(cls.config_base, recursive=True)
        except KeyError:
            pass  # Ignore

    def setup(self):
        self.provider = EtcdConfigProvider(
            etcd_cl=self.etcd_cl,
            config_base='/totem-integration/config')

    def test_write_without_ttl(self):
        """
        should write config without ttl
        :return:
        """

        # When: I write config using provider
        self.provider.write(MOCK_CONFIG, 'cluster1', 'test_write_without_ttl')

        # Then: Config gets serialized as yaml and written to etcd
        record = self.etcd_cl.read(
            '/totem-integration/config/cluster1/test_write_without_ttl/'
            '.totem.yml')
        eq_(record.ttl, None)
        eq_(record.value, MOCK_SERIALIZED_CONFIG)

    def test_write_with_ttl(self):
        """
        should write config without ttl
        """

        # Given: Provider with ttl
        self.provider.ttl = 120

        # When: I write config using provider
        self.provider.write(MOCK_CONFIG, 'cluster1', 'test_write_with_ttl')

        # Then: Config gets serialized as yaml and written to etcd
        record = self.etcd_cl.read(
            '/totem-integration/config/cluster1/test_write_with_ttl/'
            '.totem.yml')
        eq_(record.ttl, self.provider.ttl)
        eq_(record.value, MOCK_SERIALIZED_CONFIG)

    def test_delete(self):
        """
        should delete existing config
        """

        # Given: Existing configuration
        self.etcd_cl.write(
            '/totem-integration/config/cluster1/test_delete/.totem.yml',
            MOCK_SERIALIZED_CONFIG)

        # When: I delete config using provider
        ret_value = self.provider.delete('cluster1', 'test_delete')

        # Then: Config gets deleted
        eq_(ret_value, True)

    def test_delete_non_existing(self):
        """
        should skip deletion of non existing key
        """

        # When: I delete config using provider
        ret_value = self.provider.delete('cluster1',
                                         'test_delete_non_existing')

        # Then: Config gets deleted
        eq_(ret_value, False)

    def test_load(self):
        """
        should load existing config
        """

        # Given: Existing configuration
        self.etcd_cl.write(
            '/totem-integration/config/cluster1/test_load/.totem.yml',
            MOCK_SERIALIZED_CONFIG)

        # When: I load config using provider
        ret_value = self.provider.load('cluster1', 'test_load')

        # Then: Config gets loaded
        dict_compare(ret_value, MOCK_CONFIG)

    def test_load_non_existing(self):
        """
        should return empty config when etcd key is not found
        """

        # When: I load config using provider
        ret_value = self.provider.load('cluster1',
                                       'test_load_non_existing')

        # Then: Config gets deleted
        eq_(ret_value, {})
