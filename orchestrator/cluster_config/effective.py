from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

from orchestrator.cluster_config.base import AbstractConfigProvider
from orchestrator.util import dict_merge

import logging

logger = logging.getLogger(__name__)


class MergedConfigProvider(AbstractConfigProvider):
    """
    Provider that merges the config from different providers and optionally
    caches it.
    """
    def __init__(self, *providers, **kwargs):
        """
        :param providers: List of Config providers.
        :param write_provider: Config provider for writing the config to. If
            None, then no write will be done.
        """
        self.providers = providers
        self.write_provider = kwargs.get('write_provider', None)

    def write(self, name, config, *paths):
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

    def delete(self, name, *paths):
        """
        Deletes config using write_provider (if set).

        :param paths: Nested path list where config needs to be written to.
        :return: None
        """
        # Delegate to write_provider if set. Else NOOP
        if self.write_provider:
            self.write_provider.delete(name, *paths)

    def load(self, name, *paths):
        """
        Loads config for given path list.

        :param paths: Path list used for loading the config.
        :return: Merged config from different providers.
        :rtype: dict
        """
        merged_config = {}

        def merge(current_config, provider, *merge_paths):
            return dict_merge(
                current_config,
                provider.load(name, *merge_paths))

        use_paths = list(paths)
        while True:
            for provider in self.providers:
                logger.info("loading config %s from provider %s with paths %s", name, provider, use_paths)
                merged_config = merge(merged_config, provider, *use_paths)
                logger.info("loaded config from provider %s", provider)
            if use_paths:
                use_paths.pop()
            else:
                break

        return merged_config
