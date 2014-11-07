from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

import functools
from orchestrator.cluster_config.base import AbstractConfigProvider
from orchestrator.util import dict_merge


class MergedConfigProvider(AbstractConfigProvider):
    """
    Provider that merges the config from different providers and optionally
    caches it.
    """
    def __init__(self, *providers, cache_provider=None, write_provider=None):
        """
        :param providers: List of Config providers.
        :keyword cache_provider: Config provider for caching the effective
            config.
        :param write_provider: Config provider for writing the config to. If
            None, then no write will be done.
        """
        self.providers = providers
        self.cache_provider = cache_provider
        self.write_provider = write_provider

    def _cached_config(self, func):
        """
        Wrapper for caching the config if cache_provider is provided. If not,
        it skips caching.
        :param func: Function to be wrapped.
        :return: Wrapped function.
        """
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if not self.cache_provider:
                return func(*args, **kwargs)
            else:
                config = self.cache_provider.load(*args, **kwargs) or \
                    func(*args, **kwargs)
                self.cache_provider.write(config, *args)
                return config
        return inner

    def write(self, config, *paths):
        """
        Writes config using write_provider (if set).

        :param config: Dictionary based config. (This will be serialized to
            Yaml by the underlying provider.
        :param paths: Nested path list where config needs to be written to.
        :return: None
        """
        # Delegate to write_provider if set. Else NOOP
        if self.write_provider:
            self.write_provider.write(config, *paths)

    def delete(self, *paths):
        """
        Deletes config using write_provider (if set).

        :param paths: Nested path list where config needs to be written to.
        :return: None
        """
        # Delegate to write_provider if set. Else NOOP
        if self.write_provider:
            self.write_provider.delete(*paths)

    def load(self, *paths):
        """
        Loads config for given path list.

        :param paths: Path list used for loading the config.
        :return: Merged config from different providers.
        :rtype: dict
        """

        @self._cached_config
        def cached(*paths):
            merged_config = {}

            def merge(current_config, *merge_paths):
                return dict_merge(
                    current_config,
                    *(provider.load(*merge_paths)
                      for provider in self.providers))
                pass

            use_paths = list(paths)
            while use_paths:
                merged_config = merge(merged_config, *use_paths)
                use_paths.pop()

            return merged_config
        return cached(*paths)
