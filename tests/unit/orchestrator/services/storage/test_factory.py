from mock import patch, MagicMock
from nose.tools import ok_, raises
from orchestrator.services.storage.factory import get_store, \
    AbstractStorageFactory


@patch('orchestrator.services.storage.mongo.create')
def test_get_default_store(mock_create):
    # When: I get the default store from the factory
    store = get_store()

    # Then: Default store is returned
    ok_(store is not None, 'Store value is not none')


@patch('orchestrator.services.storage.mongo.create')
def test_get_default_store_from_cache(mock_create):
    # When: I get the default store from the factory twice
    get_store()
    store = get_store()

    # Then: Default store from cache is returned
    ok_(store is not None, 'Store value is not none')


@raises(NotImplementedError)
def test_get_non_existing_store():
    # When: I get the default store from the factory
    get_store(name='fakestore')


class TestAbstractStorageFactory:

    def setup(self):
        self.factory = AbstractStorageFactory()

    @raises(NotImplementedError)
    def test_get(self):
        self.factory.get('mystore')

    @raises(NotImplementedError)
    def test_register(self):
        self.factory.register('mystore', MagicMock())
