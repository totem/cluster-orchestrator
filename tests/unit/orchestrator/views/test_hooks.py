import json
from flask import Flask
from mock import patch
from nose.tools import eq_
from conf.appconfig import MIME_JSON, MIME_FORM_URL_ENC
from orchestrator.server import app
from orchestrator.views.hooks import authorize

import logging
from tests.helper import dict_compare

logger = logging.getLogger(__name__)


def _assert_unauthorized(resp):
    eq_(resp.status_code, 401)
    eq_(resp.headers['Content-Type'], MIME_JSON)
    data = json.loads(resp.data.decode('UTF-8'))
    eq_(data['code'], 'UNAUTHORIZED')


class TestAuthorize:
    """
    Tests root api
    """

    mock_payload = {
        'test': 'test'
    }

    def _create_test_route(self):

        @self.app.route('/test', methods=['POST'])
        @authorize()
        def test_route():
            return 'OK'

    def setup(self):
        self.app = Flask(__name__)
        self._create_test_route()
        self.client = self.app.test_client()

    def test_authorize_when_header_not_present(self):
        """
        Should return UNAUTHORIZED Error when X-Hub-Signature is not found
        """

        # When I invoke the test route endpoint
        resp = self.client.post(
            '/test',
            data=json.dumps(self.mock_payload),
            headers={
                'Content-Type': MIME_JSON
            })

        # Unauthorized response is returned
        _assert_unauthorized(resp)

    def test_authorize_when_signature_is_invalid(self):
        """
        Should return UNAUTHORIZED Error whe X-Hub-Signature is invalid
        """

        # When I invoke the test route endpoint
        resp = self.client.post(
            '/test',
            data=json.dumps(self.mock_payload),
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature': 'InvalidSignature'
            })

        # Unauthorized response is returned
        _assert_unauthorized(resp)

    def test_authorize_when_signature_is_valid(self):
        """
        Should return valid response when
        """

        # When I invoke the test route endpoint
        resp = self.client.post(
            '/test',
            data=json.dumps(self.mock_payload),
            headers={
                'Content-Type': MIME_JSON,
                'X-Hook-Signature': '5bf6caadb33275bf0f740f204f6176deff9465e7'
            })

        # Success response is returned
        eq_(resp.status_code, 200)


class TestGithubHookApi:

    mock_payload = '''{
        "repository": {
            "name": "mock_repo",
            "owner": {
                "name": "mock_owner"
            }
        },
        "ref": "refs/heads/mock-ref",
        "after": "7700ca29dd050d9adacc0803f866d9b539513535",
        "deleted": true
    }'''

    def setup(self):
        self.client = app.test_client()

    @patch('orchestrator.views.hooks.undeploy')
    def test_post(self, mock_start_job):
        """
        Should return accepted response when a valid github hook is posted.
        """

        # When I post to github endpoint
        resp = self.client.post(
            '/external/hooks/github',
            data=self.mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature':
                'sha1=2d7c671dfefb80b398b45d643ce6bded2ca07bd4',
                'X-GitHub-Event': 'delete'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 202)


class TestTravisHookApi:

    mock_payload = '''{
        "repository": {
            "owner_name": "mock_owner",
            "name": "mock_name"
        },
        "branch": "mock_branch",
        "commit": "mock_commit",
        "status": 0
    }'''

    def setup(self):
        self.client = app.test_client()

    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post(self, mock_callback):
        """
        Should return accepted response when a valid travis hook is posted.
        """

        # Given: Mock Implementation of handle_callback_hook
        mock_callback.delay.return_value = 'mock_task_id'

        # When I post to travis hook endpoint
        resp = self.client.post(
            '/external/hooks/travis',
            data={
                'payload': self.mock_payload
            },
            headers={
                'Content-Type': MIME_FORM_URL_ENC,
                'Authorization': 'e33bdc56114cb51a638356dd967d53ff01793fb959e7'
                                 '993f345e2e523da0c5dd'
            }
        )

        # Then: Expected response is returned
        logger.info('Response: %s', resp.data)
        eq_(resp.status_code, 202)
        data = json.loads(resp.data.decode('UTF-8'))
        dict_compare(data, {
            'task_id': 'mock_task_id'
        })

    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post_when_unauthorized(self, mock_callback):
        """
        Should return UNAUTHORIZED Error when Authorization is invalid
        """

        # Given: Mock Implementation of handle_callback_hook
        mock_callback.delay.return_value = 'mock_task_id'

        # When I post to travis hook endpoint
        resp = self.client.post(
            '/external/hooks/travis',
            data={
                'payload': self.mock_payload
            },
            headers={
                'Content-Type': MIME_FORM_URL_ENC,
                'Authorization': 'invalid_auth'
            }
        )

        # Then: Expected response is returned
        logger.info('Response: %s', resp.data)
        eq_(resp.status_code, 401)
        _assert_unauthorized(resp)
