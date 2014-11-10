"""
Github hooks
"""
from __future__ import (absolute_import, division,
                        print_function)
import functools
from flask import request
from flask.views import MethodView
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from conf.appconfig import GITHUB_HOOK, MIME_GITHUB_HOOK_V1, \
    SCHEMA_GITHUB_HOOK_V1, MIME_JSON, MIME_JOB_V1
from orchestrator.views import hypermedia
import hmac
from hashlib import sha1
from orchestrator.views.error import raise_error
from orchestrator.views.util import accepted


def _get_digest(msg, secret=None):
    secret = secret or GITHUB_HOOK['secret']
    return hmac.new(secret, msg, sha1).hexdigest()


def authorize(func):
    """
    Function wrapper for authorizing github web hooks

    :param func: Function to be wrapped
    :return: Wrapped function
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        expected_digest = _get_digest(request.data)
        actual_digest = request.headers.get('X-Hub-Signature', '')
        if actual_digest != expected_digest:
            hint_secret_size = max(0, min((GITHUB_HOOK['hint_secret_size'],
                                           len(expected_digest))))
            echo_digest = expected_digest[0:hint_secret_size] + \
                '*' * (len(expected_digest)-hint_secret_size)
            status = 401
            raise_error(**{
                'code': 'UNAUTHORIZED',
                'status': status,
                'message': 'Expecting X-Hub-Signature to be : [%s] but '
                           'found: [%s]. The signature must be hexadecimal '
                           'HMAC SHA1 Digest of request JSON using '
                           'pre-configured orchestrator secret'
                           % (echo_digest, actual_digest)
            })
        else:
            return func(*args, **kwargs)
    return wrapped


class GithubHookApi(MethodView):
    """
    API for github hook
    """

    @authorize
    @hypermedia.consumes(
        {
            MIME_GITHUB_HOOK_V1: SCHEMA_GITHUB_HOOK_V1,
            MIME_JSON: SCHEMA_GITHUB_HOOK_V1
        })
    @hypermedia.produces(
        {
            MIME_JOB_V1: SCHEMA_GITHUB_HOOK_V1,
            MIME_JSON: SCHEMA_GITHUB_HOOK_V1
        }, default=MIME_JOB_V1)
    def post(self, **kwargs):
        """
        API for Github Post hook (JSON format only). The authorization is
        carried out by using X-Hub-Signature which essentially contains the
        SHA HMAC (using hexdigest) of the payload using pre-configured
        secret.

        :return: Flask Json Response containing version.
        """
        return accepted(output={})


def register(app, **kwargs):
    """
    Registers HealthApi ('/health')
    Only GET operation is available.

    :param app: Flask application
    :return: None
    """
    app.add_url_rule('/external/github',
                     view_func=GithubHookApi.as_view('github'),
                     methods=['POST'])
