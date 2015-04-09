from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from nose.plugins.attrib import attr
from orchestrator.cluster_config.github import GithubConfigProvider
from tests.helper import dict_compare
from tests.integration.orchestrator.cluster_config import MOCK_CONFIG

__author__ = 'sukrit'


@attr(github='true')
class TestGithubConfigProvider:
    """
    Integration tests for GithubConfigProvider
    """

    def setup(self):
        self.provider = GithubConfigProvider(
            config_base='/tests/integration/orchestrator/cluster_config/')

    def test_load(self):
        """
        Should read config from GithubConfigProvider
        """

        # When: I load config using provider
        ret_value = self.provider.load(
            'totem.yml', 'totem', 'cluster-orchestrator', 'develop')

        # Then: Config gets loaded
        dict_compare(ret_value, MOCK_CONFIG)
