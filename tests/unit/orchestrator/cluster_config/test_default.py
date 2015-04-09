from nose.tools import eq_
from conf.appconfig import CONFIG_PROVIDERS
from orchestrator.cluster_config.default import DefaultConfigProvider

__author__ = 'sukrit'


def test_load_for_no_path_specified():
    """
    Should load default config when no paths are specified
    """

    # Given: Instance of default provider
    provider = DefaultConfigProvider()

    # When: I load config for no paths specified
    config = provider.load('totem.yml')

    # Then: Default config gets loaded
    eq_(config, CONFIG_PROVIDERS['default']['config'])


def test_load_for_a_given_path():
    """
    Should return empty config when path is specified
    """

    # Given: Instance of default provider
    provider = DefaultConfigProvider()

    # When: I load config for no paths specified
    config = provider.load('totem.yml', 'local')

    # Then: Default config gets loaded
    eq_(config, {})
