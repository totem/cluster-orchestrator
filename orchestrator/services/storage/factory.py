import copy
import importlib
import os
from conf.appconfig import DEFAULT_STORE_NAME


class AbstractStorageFactory:

    def not_supported(self):
        """
        Raises NotImplementedError with a message
        :return:
        """
        raise NotImplementedError(
            'Factory: {} does not support this operation'
            .format(self.__class__))

    def register(self, name, store):
        self.not_supported()

    def get(self, name):
        self.not_supported()


class DefaultStorageFactory(AbstractStorageFactory):

    _defaut_providers = {
        'mongo': 'orchestrator.services.storage.mongo'
    }

    def __init__(self, init_cache=None):
        self._cache = copy.deepcopy(init_cache or {})

    def register(self, name, store):
        store.setup()
        self._cache[name] = store

    def get(self, name):
        if name in self._cache:
            return self._cache[name]
        else:
            env_var = 'STORE_{}'.format(name.upper())
            module = os.getenv(env_var, self._defaut_providers.get(name))
            if not module:
                raise NotImplementedError(
                    'No implementation store found for {name}. Please set '
                    'environment variable {env_var} to correct store '
                    'implementation'.format(name=name, env_var=env_var))
            store = importlib.import_module(module).create()
            self.register(name, store)
            return store


DEFAULT_FACTORY = DefaultStorageFactory()


def get_store(name=DEFAULT_STORE_NAME, factory=DEFAULT_FACTORY):
    """
    Gets store provider from factory
    :param factory:
    :param store_name:
    :return: Storage Provider
    :rtype: orchestrator.services.storage.base.AbstractStore
    """
    return factory.get(name)
