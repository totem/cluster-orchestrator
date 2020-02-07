from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import base64
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
import requests
import yaml
import logging
from orchestrator.cluster_config.base import AbstractConfigProvider

logger = logging.getLogger(__name__)

class GithubConfigProvider(AbstractConfigProvider):
    """
    Config provider that fetches totem config from a given repository
    """

    def __init__(self, token=None, config_base='/'):
        """
        :keyword token: Optional github API token for authentication. Needed if
            private repositories are getting deployed.
        :type token: str
        """
        self.auth = (token, 'x-oauth-basic') if token else None
        self.config_base = config_base

    def _github_fetch(self, owner, repo, ref, name):
        """
        Fetches the raw totem config for a given owner, repo, ref and name.

        :param owner: Repository owner / organization
        :type owner: str
        :param repo: Repository name
        :type repo: str
        :param ref: Branch/tag
        :type ref: str
        :param name: Name of totem config (totem.yml)
        :type name: str
        :return: Raw totem config
        :rtype: str
        :raises GithubFetchException: If fetch fails
        """
        path_params = {
            'owner': owner,
            'repo': repo,
            'path': self.config_base + name
        }
        query_params = {
            'ref': ref
        }
        hub_url = 'https://api.github.com/repos/{owner}/{repo}/contents' \
                  '{path}'.format(**path_params)
        logger.info("_github_fetch: requests.get(%s, params=%s)", hub_url, query_params)
        resp = requests.get(hub_url, params=query_params, auth=self.auth)
        logger.info("_github_fetch: response status_code: %s", resp.status_code)
        if resp.status_code == 200:
            return base64.decodestring(resp.json()[u'content'])
        elif resp.status_code == 404:
            logger.info("config file %s not found", hub_url)
            return None
        else:
            logger.error("error fetching config from github %s: %s", hub_url, resp.text)
            hub_response = {
                'url': hub_url,
                'response': resp.json() if 'json' in resp.headers.get(
                    'content-type', {}) else {'raw': resp.text},
                'status': resp.status_code
            }
            raise GithubFetchException(hub_response)

    def load(self, name, *paths):
        """
        Loads the config for given paths. Github provider only supports
        fetch for full path with (owner, repo, and ref). If partial path is
        provided, an empty config is returned

        :param name: Name of the config file.
        :param paths: Paths used for loading config (owner, repo, and ref):
        :type paths: tuple
        :return: Totem config as dictionary
        :rtype: dict
        """
        logger.info("attempting to load config from github for %s %s", name, paths)
        if len(paths) < 4:
            return {}
        else:
            owner, repo, ref = paths[1:4]
        raw = self._github_fetch(owner, repo, ref, name)
        if raw:
            return yaml.load(raw)
        else:
            return {}


class GithubFetchException(Exception):
    """
    Exception thrown if github provider fails to fetch the config.
    """

    def __init__(self, github_response=None):
        """
        :param github_response: Dictionary representation of github response
            comprising of url, status, raw response, json response.
        :type github_response: dict
        :return:
        """
        self.response = github_response or {}
        self.code = 'GITHUB_CONFIG_FETCH_FAILED'
        resp = self.response.get('response', {})
        reason = resp.get('message', None) or \
            resp.get('raw', None) or \
            str(resp)
        self.message = 'Failed to fetch config from github using url:{0}. ' \
                       'Status:{1}. Reason: {2}'.format(
                           self.response.get('url'),
                           self.response.get('status'), reason)
        super(GithubFetchException, self).__init__(github_response)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': self.response
        }

    def __str__(self):
        return self.message
