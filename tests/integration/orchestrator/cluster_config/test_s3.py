from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import os
import boto
from boto.s3.key import Key
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from nose.plugins.attrib import attr
from nose.tools import eq_
from orchestrator.cluster_config.s3 import S3ConfigProvider
from tests.helper import dict_compare
from tests.integration.orchestrator.cluster_config import MOCK_CONFIG, \
    MOCK_SERIALIZED_CONFIG

__author__ = 'sukrit'

S3_TEST_BUCKET = os.getenv('S3_TEST_BUCKET', 'totem-integration')
S3_CONFIG_BASE = 'totem-%s/config' % (os.getenv('USER'))


@attr(s3='true')
class TestS3ConfigProvider:
    """
    Integration tests for S3ConfigProvide
    """

    @classmethod
    def teardown_class(cls):
        bucket = boto.connect_s3().get_bucket(S3_TEST_BUCKET)
        for key in bucket.list(prefix=S3_CONFIG_BASE):
            key.delete()

    def setup(self):
        self.provider = S3ConfigProvider(S3_TEST_BUCKET,
                                         config_base=S3_CONFIG_BASE)

    def test_write(self):
        """
        should write config to s3
        """

        # When: I write config using provider
        self.provider.write('totem.yml', MOCK_CONFIG, 'cluster1', 'test_write')

        # Then: Config gets serialized as yaml and written to s3
        key = self.provider._s3_bucket().get_key(
            '/%s/cluster1/test_write/totem.yml' % (S3_CONFIG_BASE))
        eq_(key is not None, True)
        eq_(key.get_contents_as_string().decode(), MOCK_SERIALIZED_CONFIG)

    def test_load(self):
        """
        Should read config from s3
        """

        # Given: Existing config
        key = Key(self.provider._s3_bucket())
        key.key = '/%s/cluster1/test_load/totem.yml' % (S3_CONFIG_BASE)
        key.set_contents_from_string(MOCK_SERIALIZED_CONFIG)

        # When: I load config using provider
        ret_value = self.provider.load('totem.yml', 'cluster1', 'test_load')

        # Then: Config gets loaded
        dict_compare(ret_value, MOCK_CONFIG)

    def test_delete(self):
        """
        Should delete config from s3
        """

        # Given: Existing config
        key = Key(self.provider._s3_bucket())
        key.key = '/%s/cluster1/test_delete/totem.yml' % (S3_CONFIG_BASE)
        key.set_contents_from_string(MOCK_SERIALIZED_CONFIG)

        # When: I load config using provider
        ret_value = self.provider.delete('totem.yml', 'cluster1',
                                         'test_delete')

        # Then: Config gets loaded
        eq_(ret_value, True)
        check_key = self.provider._s3_bucket().get_key(key.key)
        eq_(check_key is None, True)
