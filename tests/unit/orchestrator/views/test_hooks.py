import json
from flask import Flask
from mock import patch
from nose.tools import eq_
from conf.appconfig import MIME_JSON, MIME_FORM_URL_ENC, MIME_GENERIC_HOOK_V1, \
    MIME_JOB_V1
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
        "after": "7700ca29dd050d9adacc0803f866d9b539513535"
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
                'sha1=4fbcf3609119853c2d2e52ed266f7dc37ab1e278',
                'X-GitHub-Event': 'delete'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 202)

    @patch('orchestrator.views.hooks.undeploy')
    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post_for_non_delete_request(self, m_undeploy, m_callback_hook):
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
                    'sha1=4fbcf3609119853c2d2e52ed266f7dc37ab1e278',
                'X-GitHub-Event': 'push'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 202)

    @patch('orchestrator.views.hooks.undeploy')
    def test_post_with_owner_login_in_payload(self, mock_start_job):
        """
        Should return accepted response when a valid github hook is posted.
        """

        # Given: Mock payload

        mock_payload = '''{
            "repository": {
                "name": "mock_repo",
                "owner": {
                    "login": "mock_owner"
                }
            },
            "ref": "refs/heads/mock-ref",
            "after": "7700ca29dd050d9adacc0803f866d9b539513535"
        }'''

        # When I post to github endpoint
        resp = self.client.post(
            '/external/hooks/github',
            data=mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature':
                'sha1=06d41f5ec61e43fa7c0410c9c6ca9e32e5624e14',
                'X-GitHub-Event': 'delete'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 202)

    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post_for_create_branch_event(self, m_handle_callback_hook):
        """
        Should return accepted response when a valid github create branch event
        is posted
        """

        # Given: Mock payload

        mock_payload = '''{
            "ref_type": "branch",
            "repository": {
                "name": "mock_repo",
                "owner": {
                    "login": "mock_owner"
                }
            },
            "ref": "develop"
        }'''

        # When I post to github endpoint
        resp = self.client.post(
            '/external/hooks/github',
            data=mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature':
                    'sha1=029893cc480a1e399a9af18c833a35182bc2d80f',
                'X-GitHub-Event': 'create'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 202)
        m_handle_callback_hook.apply_async.assert_called_once_with(
            (u'mock_owner', u'mock_repo', u'develop', u'scm-create',
             u'github-create'), countdown=10)

    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post_for_create_non_branch_event(self, m_handle_callback_hook):
        """
        Should return expected response when a valid github create repo event
        is posted
        """

        # Given: Mock payload

        mock_payload = '''{
            "ref_type": "repository",
            "repository": {
                "name": "mock_repo",
                "owner": {
                    "login": "mock_owner"
                }
            }
        }'''

        # When I post to github endpoint
        resp = self.client.post(
            '/external/hooks/github',
            data=mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hub-Signature':
                    'sha1=2b100de728c7a0614923b63887024e26afbfa2b9',
                'X-GitHub-Event': 'create'
            }
        )
        logger.info('Response: %s', resp.data)

        # Then: Expected response is returned
        eq_(resp.status_code, 204)
        m_handle_callback_hook.delay.assert_not_called()


class TestTravisHookApi:

    mock_payload = '''{
        "repository": {
            "owner_name": "mock_owner",
            "name": "mock_name"
        },
        "branch": "mock_branch",
        "commit": "mock_commit",
        "status": 0,
        "type" : "push"
    }'''

    mock_pr_payload = '''{
        "repository": {
            "owner_name": "mock_owner",
            "name": "mock_name"
        },
        "branch": "mock_branch",
        "commit": "mock_commit",
        "status": 0,
        "type" : "pull-request"
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
    def test_post_for_pr(self, mock_callback):
        """
        Should return accepted response when a valid travis hook is posted for
        PR
        """

        # When I post to travis hook endpoint
        resp = self.client.post(
            '/external/hooks/travis',
            data={
                'payload': self.mock_pr_payload
            },
            headers={
                'Content-Type': MIME_FORM_URL_ENC,
                'Authorization': 'e33bdc56114cb51a638356dd967d53ff01793fb959e7'
                                 '993f345e2e523da0c5dd'
            }
        )

        # Then: Expected No processing is done
        logger.info('Response: %s', resp.data)
        eq_(resp.status_code, 204)
        dict_compare(resp.data.decode('UTF-8'), '')
        mock_callback.delay.assert_not_called()

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


class TestGenericInternalPostHookApi:

    def setup(self):
        self.client = app.test_client()

    @staticmethod
    def _create_mock_payload():
        return {
            'git': {
                'owner': 'totem',
                'repo': 'totem-demo',
                'ref': 'master',
                'commit': '87c4419d3e278036055ca2cd022583e0397d3a5d'
            },
            'type': 'scm-create',
            'name': 'github-create',
            'status': 'success',
            'force-deploy': False
        }

    @patch('orchestrator.views.hooks.handle_callback_hook')
    def test_post(self, m_handle_callback_hook):
        """
        Should return accepted response when a valid github hook is posted.
        """
        # Given: Valid JSON Payload for posting to the hook
        mock_payload = self._create_mock_payload()

        # And: Mock Callback hook handler
        m_handle_callback_hook.delay.return_value = 'mock_task_id'

        # When I post to generic interal hook
        resp = self.client.post(
            '/hooks/generic',
            data=json.dumps(mock_payload),
            headers={
                'Content-Type': MIME_GENERIC_HOOK_V1
            }
        )

        # Then: Expected response is returned
        eq_(resp.status_code, 202)
        data = json.loads(resp.data.decode('UTF-8'))
        dict_compare(data, {
            'task_id': 'mock_task_id'
        })

    @patch('orchestrator.views.hooks.handle_callback_hook')
    @patch('orchestrator.views.hooks.task_client')
    def test_post_synchronous(self, m_task_client, m_handle_callback_hook):
        """
        Should return accepted response when a valid github hook is posted.
        """
        # Given: Valid JSON Payload for posting to the hook
        mock_payload = self._create_mock_payload()

        # And: Mock Callback hook handler
        m_handle_callback_hook.delay.return_value.id = 'mock_task_id'
        mock_job = {
            'meta-info': {
                'job-id': 'mock_job_id'
            }

        }
        m_task_client.ready.return_value = {
            'output': mock_job
        }

        # When I post to generic interal hook
        resp = self.client.post(
            '/hooks/generic',
            data=json.dumps(mock_payload),
            headers={
                'Content-Type': MIME_GENERIC_HOOK_V1,
                'Accept': MIME_JOB_V1
            }
        )

        # Then: Created job is returned
        eq_(resp.status_code, 201)
        data = json.loads(resp.data.decode('UTF-8'))
        dict_compare(data, mock_job)
        eq_(resp.headers['Location'], 'http://localhost/jobs/mock_job_id')

    @patch('orchestrator.views.hooks.undeploy')
    def test_delete(self, m_undeploy):
        """
        Should return accepted response when a valid github hook is posted.
        """

        # Given: Mock undeploy handler
        m_undeploy.si.return_value.delay.return_value = 'mock_task_id'

        # And: Existing Repository and job for given branch
        owner = 'totem'
        repo = 'totem-demo'
        ref = 'master'

        # When I fire delete request
        resp = self.client.delete(
            '/hooks/generic?owner={0}&repo={1}&ref={2}'.format(
                owner, repo, ref),
        )

        # Then: Created job is returned
        eq_(resp.status_code, 202)
        data = json.loads(resp.data.decode('UTF-8'))
        dict_compare(data, {
            'task_id': 'mock_task_id'
        })

    @patch('orchestrator.views.hooks.undeploy')
    def test_delete_with_no_query_params(self, m_undeploy):
        """
        Should return accepted response when a valid github hook is posted.
        """

        # Given: Mock undeploy handler
        m_undeploy.si.return_value.delay.return_value = 'mock_task_id'

        # When I fire delete request
        resp = self.client.delete('/hooks/generic')

        # Then: Created job is returned
        eq_(resp.status_code, 422)
        data = json.loads(resp.data.decode('UTF-8'))
        eq_(data['code'], 'BUSINESS_RULE_VIOLATION')


class TestGenericPostHookApi:

    mock_payload = '''{
        "git": {
            "owner": "totem",
            "repo": "totem-demo",
            "ref": "master",
            "commit": "87c4419d3e278036055ca2cd022583e0397d3a5d"
        },
        "type": "builder",
        "name": "imagefactory",
        "status": "success"
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

        # When I post to external generic hook endpoint
        resp = self.client.post(
            '/external/hooks/generic',
            data=self.mock_payload,
            headers={
                'Content-Type': MIME_JSON,
                'X-Hook-Signature': '559ddad4d2d59957cb674cb66a358084cf9d3cd9'
            }
        )

        # Then: Expected response is returned
        logger.info('Response: %s', resp.data)
        eq_(resp.status_code, 202)
        data = json.loads(resp.data.decode('UTF-8'))
        dict_compare(data, {
            'task_id': 'mock_task_id'
        })
