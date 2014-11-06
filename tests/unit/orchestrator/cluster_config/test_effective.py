from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import copy
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
__author__ = 'sukrit'

from tests.helper import dict_compare
from orchestrator.cluster_config.base import AbstractConfigProvider
from orchestrator.cluster_config.effective import MergedConfigProvider
from nose.tools import eq_


class InMemoryProvider(AbstractConfigProvider):

    def __init__(self, init_cache=None):
        self.cache = copy.deepcopy(init_cache) if init_cache else {}

    def write(self, config, *paths):
        self.cache['/' + '/'.join(paths)] = copy.deepcopy(config)

    def load(self, *paths):
        return copy.deepcopy(self.cache.get('/' + '/'.join(paths), {}))


class TestMergedConfigProvider:
    """
    Tests MergedConfigProvider
    """

    def setup(self):
        self.cache_provider = InMemoryProvider()
        self.write_provider = InMemoryProvider()
        self.provider1 = InMemoryProvider(init_cache={
            '/': {
                'key1': 'provider1-1.0'
            },
            '/path1': {
                'key1': 'provider1-1.1',
                'key2': 'provider1-2.1'
            },
            '/path1/path2': {
                'key1': 'provider1-1.2',
                'key3': 'provider1-3.2'
            }
        })
        self.provider2 = InMemoryProvider(init_cache={
            '/': {},
            '/path1': {
                'key1': 'provider2-1.1',
                'key2': 'provider2-2.1',
                'key4': 'provider2-4.1',
            }
        })
        self.provider = MergedConfigProvider(
            self.provider1, self.provider2, cache_provider=self.cache_provider,
            write_provider=self.write_provider)

    def test_write(self):
        """
        Should set the Link header for root endpoint.
        """

        # When: When I try to write a config
        self.provider.write({}, 'path1', 'path2')

        # Then: Config is written using write provider
        eq_(self.write_provider.load('path1', 'path2'), {})

    def test_write_when_no_write_provider_specified(self):
        """
        Should perform no operation when no write provider is specified.
        """

        # Given: Merged Config provider with no write provider specified
        self.provider.write_provider = None

        # When: I write the config
        self.provider.write({}, 'path1', 'path2')

        # Then: No exception is raised

    def test_load_with_no_caching(self):
        # Given: Merged Config provider with no cache provider
        self.provider.cache_provider = None

        # When: I load config
        merged_config = self.provider.load('path1', 'path2')

        # Then: Merged config is returned
        dict_compare(merged_config, {
            'key1': 'provider1-1.2',
            'key2': 'provider1-2.1',
            'key3': 'provider1-3.2',
            'key4': 'provider2-4.1',
        })

    def test_load_with_caching(self):

        # When: I load config
        merged_config = self.provider.load('path1', 'path2')

        # Then: Merged config is returned
        expected_config = {
            'key1': 'provider1-1.2',
            'key2': 'provider1-2.1',
            'key3': 'provider1-3.2',
            'key4': 'provider2-4.1',
        }
        dict_compare(merged_config, expected_config)

        # And config gets cached
        dict_compare(self.cache_provider.load('path1', 'path2'),
                     expected_config)

    def test_load_with_cached_value(self):
        # Give: Cached Config
        cached_config = {
            'cached_key': 'cached_value'
        }
        self.cache_provider.write(cached_config, 'path1', 'path2')

        # When: I load config
        merged_config = self.provider.load('path1', 'path2')

        # Then: Cached config is returned
        dict_compare(merged_config, cached_config)
