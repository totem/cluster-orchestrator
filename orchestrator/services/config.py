from repoze.lru import lru_cache
from conf.appconfig import CONFIG_PROVIDERS, CONFIG_PROVIDER_LIST
from orchestrator.cluster_config.effective import MergedConfigProvider
from orchestrator.cluster_config.etcd import EtcdConfigProvider

__author__ = 'sukrit'


@lru_cache(1)
def get_providers():
    """
    Gets the list of all available config providers

    :return: Provider list
    :rtype: list
    """
    for provider_type in CONFIG_PROVIDER_LIST:
        provider_type = provider_type.strip()
        if provider_type in CONFIG_PROVIDERS:
            yield provider_type
    yield 'effective'


def _get_effective_config_provider():
    """
    Gets the effective config provider.

    :return: Effective Config provider.
    :rtype: orchestrator.cluster_config.effective.MergedConfigProvider
    """
    providers = list()
    for provider_type in get_providers():
        if provider_type != 'effective':
            providers += get_provider(provider_type)

    if CONFIG_PROVIDERS['effective']['cache']['enabled']:
        cache_provider = get_provider(
            'etcd', ttl=CONFIG_PROVIDERS['effective']['cache']['ttl'])
    else:
        cache_provider = None
    return MergedConfigProvider(providers, cache_provider=cache_provider)


def _get_etcd_provider(ttl=None):
    """
    Gets the etcd config provider.

    :keyword ttl: time to live in seconds
    :type ttl: number
    :return: Instance of EtcdConfigProvider
    :rtype: EtcdConfigProvider
    """
    return EtcdConfigProvider(
        etcd_host=CONFIG_PROVIDERS['etcd']['host'],
        etcd_port=CONFIG_PROVIDERS['etcd']['port'],
        config_base=CONFIG_PROVIDERS['etcd']['base']+'/config',
    )


@lru_cache(10)
def get_provider(provider_type, *args, **kwargs):
    """
    Factory method to create config provider instance.
    :param provider_type:
    :type provider_type: str
    :param args: Arguments for the provider
    :param kwargs: Keyword arguments for the provider.
    :return: AbstractConfigProvider instance.
    :rtype: AbstractConfigProvider
    """
    if provider_type == 'etcd' and provider_type in CONFIG_PROVIDERS:
        return _get_etcd_provider(*args, **kwargs)
    if provider_type == 'effective':
        return _get_effective_config_provider(*args, **kwargs)


def load_config(*paths, provider_type='effective'):
    """
    Loads config for given path and provider type.

    :param paths: Tuple consisting of nested level path
    :type paths: tuple
    :keyword provider_type: Type of provider
    :type provider_type: str
    :return: Parsed configuration
    :rtype: dict
    """
    provider = get_provider(provider_type)
    return provider.load(*paths)


def write_config(config, *paths, provider_type='etcd'):
    """
    Writes config for given path

    :param config: Dictionary based configuration
    :type config: dict
    :param provider_type: Type of provider
    :type provider_type: str
    :return: None
    """
    provider = get_provider(provider_type)
    if provider:
        provider.write(config)
