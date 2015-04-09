from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from mock import patch
import nose
from orchestrator.cluster_config.github import GithubConfigProvider, \
    GithubFetchException
from tests.helper import dict_compare
from nose.tools import eq_

__author__ = 'sukrit'


class TestGuthubConfigProvider:

    def setup(self):
        self.provider = GithubConfigProvider()

    def test_init_when_no_parameters_passed(self):
        """
        Should initialize GithubConfigProvider with default values
        """
        eq_(self.provider.config_base, '/')
        eq_(self.provider.auth, None)

    def test_init(self):
        """
        Should initialize GithubConfigProvider with provided values
        """
        # When:  I initialize GithubConfigProvider with provided values
        provider = GithubConfigProvider(token='MOCK_TOKEN', config_base='/f1/')
        eq_(provider.config_base, '/f1/')
        eq_(provider.auth, ('MOCK_TOKEN', 'x-oauth-basic'))

    @patch('requests.get')
    def test_load_for_partial_path(self, m_get):
        """
        Should return empty config from GithubConfigProvider for partial path
        """

        # When: I load config using provider
        ret_value = self.provider.load(
            'totem.yml', 'totem', 'cluster-orchestrator')

        # Then: Config gets loaded
        dict_compare(ret_value, {})

    @patch('requests.get')
    def test_load_for_full_path(self, m_get):
        """
        Should read config from github
        """
        # Given: Existing config
        m_get.return_value.status_code = 200
        m_get.return_value.json.return_value = {
            'content': 'dmFyaWFibGVzOiB7fQ=='
        }

        # When: I load config using provider
        ret_value = self.provider.load(
            'totem.yml', 'local', 'totem', 'cluster-orchestrator', 'develop')

        # Then: Config gets loaded
        dict_compare(ret_value, {'variables': {}})

    @patch('requests.get')
    def test_load_for_non_existing_path(self, m_get):
        """
        Should return empty config when config is not found in github
        """
        # Given: Existing config
        m_get.return_value.status_code = 404

        # When: I load config using provider
        ret_value = self.provider.load(
            'totem.yml', 'totem', 'cluster-orchestrator', 'develop')

        # Then: EmptyConfig gets loaded
        dict_compare(ret_value, {})

    @patch('requests.get')
    def test_load_when_github_fetch_fails_with_raw_text(self, m_get):
        """
        Should read config from github
        """
        # Given: Existing config
        m_get.return_value.status_code = 500
        m_get.return_value.headers = {}
        m_get.return_value.text = 'mock error'

        # When: I load config using provider
        with nose.tools.assert_raises(GithubFetchException) as cm:
            self.provider.load(
                'totem.yml', 'local', 'totem', 'cluster-orchestrator',
                'develop')

        # Then: Expected exception is raised
        dict_compare(cm.exception.response, {
            'url': 'https://api.github.com/repos/totem/cluster-orchestrator/'
                   'contents/totem.yml',
            'status': 500,
            'response': {
                'raw': 'mock error'
            }
        })


class TestGithubFetchException():

    def test_init_with_empty_response(self):
        """
        Should initialize using empty github response
        """

        # When: I initialize with empty response
        exc = GithubFetchException()

        # Then: Default value are assigned to exception fields
        eq_(exc.response, {})

    def test_init(self):
        """
        Should initialize using provided github response
        """

        # When: I initialize with empty response
        exc = GithubFetchException(github_response={
            'response': {
                'message': 'mock error',
            },
            'url': 'mock url',
            'status': 500
        })

        # Then: Expected response is returned
        eq_(exc.message, 'Failed to fetch config from github using '
                         'url:mock url. Status:500. Reason: mock error')

    def test_str_representation(self):
        """
        Should return string representation
        """

        # Given: Existing exception instance
        exc = GithubFetchException()

        # When: I return string representation
        rep = str(exc)

        # Then: Expected string representation is returned.
        eq_(rep, exc.message)

    def test_to_dict_representation(self):
        """
        Should return dict representation for GithubFetchException
        """

        # Given: Existing instance of GithubFetchException
        exc = GithubFetchException(github_response={
            'response': {
                'message': 'mock error',
            },
            'url': 'mock url',
            'status': 500
        })

        # When: I return string representation
        rep = exc.to_dict()

        # Then: Expected string representation is returned.
        dict_compare(rep, {
            'message': 'Failed to fetch config from github using url:mock url.'
                       ' Status:500. Reason: mock error',
            'code': 'GITHUB_CONFIG_FETCH_FAILED',
            'details': exc.response
        })
