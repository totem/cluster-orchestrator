import json
from flask import Flask
from mock import patch
from nose.tools import eq_
from conf.appconfig import MIME_JSON
from orchestrator.server import app
from orchestrator.views.github import authorize

import logging

logger = logging.getLogger(__name__)


class TestAuthorize:
    """
    Tests root api
    """

    mock_payload = {
        'test': 'test'
    }

    def _create_test_route(self):

        @self.app.route('/test', methods=['POST'])
        @authorize
        def test_route():
            return 'OK'

    def setup(self):
        self.app = Flask(__name__)
        self._create_test_route()
        self.client = self.app.test_client()

    @staticmethod
    def _assert_unauthorized(resp):
        eq_(resp.status_code, 401)
        eq_(resp.headers['Content-Type'], MIME_JSON)
        data = json.loads(resp.data.decode('UTF-8'))
        eq_(data['code'], 'UNAUTHORIZED')

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
        self._assert_unauthorized(resp)

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
        self._assert_unauthorized(resp)

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
                'X-Hub-Signature': '5bf6caadb33275bf0f740f204f6176deff9465e7'
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
        "deleted": false
    }'''

    def setup(self):
        self.client = app.test_client()

    @patch('orchestrator.tasks.job.start_job')
    def test_post(self, mock_start_job):
        """
        Should return accepted response when a valid github hook is posted.
        """

        # When I post to github endpoint
        resp = self.client.post(
            '/external/github',
            data=self.mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature': 'a5a580cce7bddd8dce4edff334361cd5c0c77968'
            }
        )
        logger.info('Response: %s', resp.data)
        eq_(resp.status_code, 202)
