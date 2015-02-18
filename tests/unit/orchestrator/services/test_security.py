from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from nose.tools import eq_, ok_
from mock import patch
from orchestrator.services.security import using_encryption_store, \
    decrypt_config

MOCK_BUCKET = 'mockbucket'
MOCK_PASSPHRASE = 'mock-passphrase'
MOCK_BASE = 'mock-base'


@patch.dict('orchestrator.services.security.ENCRYPTION', {
    'store': 's3',
    's3': {
        'bucket': MOCK_BUCKET,
        'base': MOCK_BASE,
    },
    'passphrase': MOCK_PASSPHRASE
})
def test_using_encryption_store_with_s3():

    # Given: Mock function wrapped with  using_encryption_store
    @using_encryption_store
    def mock_fn(*args, **kwargs):
        eq_(args, ('arg1', ))
        eq_(kwargs.get('arg2'), 'arg2')
        eq_(kwargs.get('passphrase'), MOCK_PASSPHRASE)
        store = kwargs.get('store')
        ok_(store is not None)
        eq_(store.bucket, MOCK_BUCKET)
        eq_(store.keys_base, MOCK_BASE)

    # When: I invoke mock_fn
    mock_fn('arg1', arg2='arg2')

    # Then: Function is called with expected args


@patch.dict('orchestrator.services.security.ENCRYPTION', {})
def test_using_encryption_store_with_no_provider():

    # Given: Mock function wrapped with  using_encryption_store
    @using_encryption_store
    def mock_fn(*args, **kwargs):
        store = kwargs.get('store')
        ok_(store is None)

    # When: I invoke mock_fn
    mock_fn('arg1', arg2='arg2')

    # Then: Function is called with no store set


@patch.dict('orchestrator.services.security.ENCRYPTION', {})
@patch('orchestrator.services.security.decrypt_obj')
def test_decrypt_config(m_decrypt_obj):

    # When: I invoke decrypt config
    decrypt_config({'mockkey': 'mockvalue'})

    # Then: decrypt_obj is called with expected parameters
    m_decrypt_obj.assert_called_once_with(
        {'mockkey': 'mockvalue'}, profile='default', store=None,
        passphrase=None)
