"""
Provider for default Job Config.
"""
from conf.appconfig import CONFIG_PROVIDERS
from orchestrator.cluster_config.base import AbstractConfigProvider


class DefaultConfigProvider(AbstractConfigProvider):
    """
    Default Config provider that loads the configuration from appconfig.
    This provider reads static config and does not support delete / write.
    """

    def load(self, name, *paths):
        """
        Load the default configuration

        :param paths: Paths is ignored by this provider.
        :return: Parsed Dictionary based config
        """
        if not len(paths):
            return CONFIG_PROVIDERS['default']['config']
        else:
            return {}
