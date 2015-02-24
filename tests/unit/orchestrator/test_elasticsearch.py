from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from elasticsearch import RequestError
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from mock import patch
from nose.tools import eq_, raises
from orchestrator.elasticsearch import orch_search, create_index_mapping


ENABLED_SEARCH_SETTINGS = {
    'enabled': True,
    'host': 'mockhost',
    'port': 10001,
    'default-index': 'mock-index'
}


@orch_search
def mock_fn(mock_input, ret_value=None, es=None, idx=None):
    return ret_value


@orch_search
def mock_fn_no_positional_args(es=None, idx=None, ret_value=None):
    return ret_value


@patch('orchestrator.elasticsearch.Elasticsearch')
def test_orch_search_when_disabled(m_es):
    """
    Should bypass search when disabled (by default)
    :return:
    """

    # When: I invoke function wrapped with orch_search
    ret_value = mock_fn('mock-input')

    # Then: Function call is bypassed
    eq_(m_es.called, False)
    eq_(ret_value, 'mock-input')


@patch('orchestrator.elasticsearch.Elasticsearch')
def test_orch_search_with_no_positional_args(m_es):
    """
    Should bypass search when disabled (by default)
    :return:
    """

    # When: I invoke function wrapped with orch_search
    ret_value = mock_fn_no_positional_args(ret_value='mock-ret')

    # Then: Function call is bypassed
    eq_(m_es.called, False)
    eq_(ret_value, 'mock-ret')


@patch('orchestrator.elasticsearch.Elasticsearch')
def test_orch_search_with_no_ret_value(m_es):
    """
    Should bypass search when disabled (by default)
    :return:
    """

    # When: I invoke function wrapped with orch_search
    ret_value = mock_fn_no_positional_args()

    # Then: Function call is bypassed
    eq_(m_es.called, False)
    eq_(ret_value, None)


@patch('orchestrator.elasticsearch.Elasticsearch')
@patch.dict('orchestrator.elasticsearch.SEARCH_SETTINGS',
            ENABLED_SEARCH_SETTINGS)
def test_orch_search_when_enabled(m_es):
    """
    Should invoke function when search is enabled
    :return:
    """

    # When: I invoke function wrapped with orch_search
    ret_value = mock_fn('mock-input', ret_value='mock-output')

    # Then: Function gets called as expected
    m_es.assert_called_once_with(hosts='mockhost', port=10001)
    eq_(ret_value, 'mock-output')


@patch('builtins.open')
@patch('orchestrator.elasticsearch.Elasticsearch')
@patch.dict('orchestrator.elasticsearch.SEARCH_SETTINGS',
            ENABLED_SEARCH_SETTINGS)
def test_create_index_mapping_for_existing_index(m_es, m_open):

    # Given: Existing index
    m_es.return_value.indices.exists.return_value = True

    # When: I create index mapping
    create_index_mapping()

    # Then: Indexes are not re-created
    eq_(m_es.return_value.indices.create.called, False)


@patch('json.load')
@patch('builtins.open')
@patch('orchestrator.elasticsearch.Elasticsearch')
@patch.dict('orchestrator.elasticsearch.SEARCH_SETTINGS',
            ENABLED_SEARCH_SETTINGS)
def test_create_index_mapping_for_non_existing_index(m_es, m_open, m_load):

    # Given: Non Existing index
    m_es.return_value.indices.exists.return_value = False

    # And: Existing mapping file
    m_load.return_value = {
        'key': 'value'
    }

    # When: I create index mapping
    create_index_mapping()

    # Then: Indexes are not re-created
    m_es.return_value.indices.create.assert_called_once_with(
        'mock-index', body={'key': 'value'})


@patch('json.load')
@patch('builtins.open')
@patch('orchestrator.elasticsearch.Elasticsearch')
@patch.dict('orchestrator.elasticsearch.SEARCH_SETTINGS',
            ENABLED_SEARCH_SETTINGS)
def test_create_index_mapping_for_failed_index_existing(m_es, m_open, m_load):

    # And: Non Existing index
    m_es.return_value.indices.exists.return_value = False

    # And: Existing mapping file
    m_load.return_value = {
        'key': 'value'
    }

    # And: Index already exists when index creation call is made
    mock_error = RequestError()
    mock_error.args = (400, '*****IndexAlreadyExistsException*****', '')

    m_es.return_value.indices.create.side_effect = mock_error

    # When: I create index mapping
    create_index_mapping()

    # Then: No error is raised


@raises(RequestError)
@patch('json.load')
@patch('builtins.open')
@patch('orchestrator.elasticsearch.Elasticsearch')
@patch.dict('orchestrator.elasticsearch.SEARCH_SETTINGS',
            ENABLED_SEARCH_SETTINGS)
def test_create_index_mapping_for_error_during_creation(m_es, m_open, m_load):

    # And: Non Existing index
    m_es.return_value.indices.exists.return_value = False

    # And: Existing mapping file
    m_load.return_value = {
        'key': 'value'
    }

    # And: Index creation fails du to internal error
    mock_error = RequestError()
    mock_error.args = (500, '*****InternalError*****', '')

    m_es.return_value.indices.create.side_effect = mock_error

    # When: I create index mapping
    create_index_mapping()

    # Then: RequestError is raised
