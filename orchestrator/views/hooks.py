import functools
import hmac
import re
import logging
from os.path import basename
from flask import request
from flask.views import MethodView
from conf.appconfig import HOOK_SETTINGS, MIME_GENERIC_HOOK_V1, \
    SCHEMA_GENERIC_HOOK_V1, MIME_JSON, MIME_JOB_V1, SCHEMA_JOB_V1, \
    SCHEMA_TASK_V1, MIME_TASK_V1, MIME_GITHUB_HOOK_V1, SCHEMA_GITHUB_HOOK_V1, \
    MIME_FORM_URL_ENC, SCHEMA_TRAVIS_HOOK_V1
from orchestrator.exceptions import BusinessRuleViolation
from orchestrator.views import hypermedia, task_client
from orchestrator.views.error import raise_error
from hashlib import sha1, sha256
from orchestrator.tasks.job import handle_callback_hook, undeploy
from orchestrator.views.util import created_task, created, build_response

logger = logging.getLogger('orchestrator.views.hooks')


def authorize(sig_header='X-Hook-Signature'):
    """
    Function wrapper for authorizing web hooks

    :return: Wrapped function
    """

    def decorated(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            expected_digest = _get_digest(request.data)
            actual_digest = re.sub('^sha1=(.*)', '\\1',
                                   request.headers.get(sig_header, ''))
            if actual_digest != expected_digest:
                hint_secret_size = max(
                    0, min((HOOK_SETTINGS['hint_secret_size'],
                            len(expected_digest))))
                echo_digest = expected_digest[0:hint_secret_size] + \
                    '*' * (len(expected_digest)-hint_secret_size)
                status = 401
                raise_error(**{
                    'code': 'UNAUTHORIZED',
                    'status': status,
                    'message': 'Expecting %s to be : [%s] but '
                               'found: [%s]. The signature must be '
                               'hexadecimalHMAC SHA1 Digest of request JSON '
                               'using pre-configured orchestrator secret'
                               % (sig_header, echo_digest, actual_digest)
                })
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorated


def _get_digest(msg, secret=None):
    secret = secret or HOOK_SETTINGS['secret']
    return hmac.new(secret.encode('utf-8'), msg, sha1) \
        .hexdigest()


class GenericInternalPostHookApi(MethodView):
    """
    API for post hook for orchestrator. The post hook is invoked from CI/image
    builder services to update the status of the build.

    """

    @hypermedia.consumes(
        {
            MIME_GENERIC_HOOK_V1: SCHEMA_GENERIC_HOOK_V1,
            MIME_JSON: SCHEMA_GENERIC_HOOK_V1
        })
    @hypermedia.produces(
        {
            MIME_JOB_V1: SCHEMA_JOB_V1,
            MIME_JSON: SCHEMA_TASK_V1,
            MIME_TASK_V1: SCHEMA_TASK_V1
        }, default=MIME_TASK_V1)
    def post(self, request_data=None, accept_mimetype=None, **kwargs):
        """
        API for Generic Orchestrator Post hook (JSON format only).
        The authorization is carried out by using X-Hook-Signature which
        essentially contains the SHA HMAC (using hexdigest) of the payload
        using pre-configured secret.

        :return: Flask Json Response containing version.
        """
        git = request_data['git']
        request_data.setdefault('result', None)
        result = handle_callback_hook.delay(
            git['owner'], git['repo'], git['ref'], request_data['type'],
            request_data['name'], commit=git.get('commit'),
            hook_status=request_data['status'],
            hook_result=request_data['result'],
            force_deploy=request_data.get('force-deploy', False))
        if accept_mimetype == MIME_JOB_V1:
            result = task_client.ready(result.id, wait=True, raise_error=True)
            job = result['output']
            job.setdefault('meta-info', {
                'job-id': 'NA'
            })
            location = '/jobs/%s' % (job['meta-info']['job-id'])
            return created(job, location=location)
        else:
            return created_task(result)

    @hypermedia.produces(
        {
            MIME_JSON: SCHEMA_TASK_V1,
            MIME_TASK_V1: SCHEMA_TASK_V1
        }, default=MIME_TASK_V1)
    def delete(self, **kwargs):
        owner = request.args.get('owner', '')
        repo = request.args.get('repo', '')
        ref = request.args.get('ref', '')
        if not repo or not owner or not ref:
            raise BusinessRuleViolation(
                'DELETE can only be performed for a given ref(branch/tag) '
                'for a repository. Ensure that valid owner, repo and commit '
                'parameters are passed as part of query parameters')

        return created_task(
            undeploy.si(owner, repo, ref).delay())


class GenericPostHookApi(GenericInternalPostHookApi):
    """
    API for post hook for orchestrator that accepts signed hook.
    """

    @authorize('X-Hook-Signature')
    def post(self, *args, **kwargs):
        return super(GenericPostHookApi, self).post(*args, **kwargs)


class GithubHookApi(MethodView):
    """
    API for github hook
    """

    @authorize('X-Hub-Signature')
    @hypermedia.consumes(
        {
            MIME_GITHUB_HOOK_V1: SCHEMA_GITHUB_HOOK_V1,
            MIME_JSON: SCHEMA_GITHUB_HOOK_V1
        })
    @hypermedia.produces(
        {
            MIME_JSON: SCHEMA_TASK_V1
        }, default=MIME_JSON)
    def post(self, request_data=None, **kwargs):
        """
        API for Github Post hook (JSON format only). The authorization is
        carried out by using X-Hub-Signature which essentially contains the
        SHA HMAC (using hexdigest) of the payload using pre-configured
        secret.

        :return: Flask Json Response containing version.
        """
        owner = request_data['repository']['owner'].get('name') or \
            request_data['repository']['owner'].get('login')
        repo = request_data['repository']['name']
        if request.headers.get('X-GitHub-Event') == 'delete':
            ref = basename(request_data['ref'])
            task = undeploy.delay(owner, repo, ref)
            return created_task(task)
        elif request.headers.get('X-GitHub-Event') == 'push' and \
                request_data.get('ref') and \
                not request_data.get('deleted'):
            ref = basename(request_data['ref'])
            commit = request_data['after']
            task = handle_callback_hook.delay(
                owner, repo, ref, 'scm-push', 'github-push', commit=commit)
            return created_task(task)
        elif request.headers.get('X-GitHub-Event') == 'create' and \
                request_data.get('ref_type') == 'branch' and \
                request_data.get('ref'):
            ref = basename(request_data['ref'])
            task = handle_callback_hook.delay(
                owner, repo, ref, 'scm-create', 'github-create')
            return created_task(task)
        else:
            # Ignore all other hooks
            return build_response('', status=204)


class TravisHookApi(MethodView):
    """
    API To handle post hooks from Travis.
    """

    @staticmethod
    def _get_travis_digest(owner, repo,
                           token=HOOK_SETTINGS['travis']['token']):
        msg = '%s/%s%s' % (owner, repo, token)
        return sha256(msg.encode('utf-8')).hexdigest()

    @staticmethod
    def _assert_digest(expected_digest, actual_digest, owner, repo):
        if actual_digest != expected_digest:
            hint_secret_size = max(
                0, min((HOOK_SETTINGS['hint_secret_size'],
                        len(expected_digest))))
            echo_digest = expected_digest[0:hint_secret_size] + \
                '*' * (len(expected_digest)-hint_secret_size)
            status = 401
            msg = 'Expecting Authorization header to be : [%s] but ' \
                'found: [%s]. The signature must be hexadecimal' \
                ' SHA256 Digest of %s/%s{TRAVIS_TOKEN}.' \
                % (echo_digest, actual_digest, owner, repo)
            logger.warn(msg)
            raise_error(**{
                'code': 'UNAUTHORIZED',
                'status': status,
                'message': msg
            })

    @hypermedia.consumes(
        {
            MIME_FORM_URL_ENC: SCHEMA_TRAVIS_HOOK_V1
        })
    @hypermedia.produces(
        {
            MIME_JSON: SCHEMA_TASK_V1,
            MIME_TASK_V1: SCHEMA_TASK_V1
        }, default=MIME_TASK_V1)
    def post(self, request_data=None, accept_mimetype=None, **kwargs):
        owner = request_data['repository']['owner_name']
        repo = request_data['repository']['name']
        build_type = request_data['type']

        if build_type != 'push':
            # No job is created for non push request
            return build_response('', status=204)

        # Authorize token
        actual_digest = request.headers.get('Authorization', '')
        expected_digest = self._get_travis_digest(owner, repo)
        self._assert_digest(expected_digest, actual_digest, owner, repo)
        ref = request_data['branch']
        commit = request_data.get('commit')
        status = 'success' if request_data['status'] == 0 else 'failed'
        request_data.setdefault('result', None)
        result = handle_callback_hook.delay(
            owner, repo, ref, 'ci', 'travis', commit=commit,
            hook_status=status, hook_result=request_data)

        # Asynchronously handle the task creation.
        return created_task(result)


def register(app, **kwargs):
    """
    Registers Hooks API (generic, github, travis)

    :param app: Flask application
    :return: None
    """
    app.add_url_rule('/external/hooks/generic',
                     view_func=GenericPostHookApi.as_view('generic-hook'),
                     methods=['POST'])
    app.add_url_rule('/hooks/generic',
                     view_func=GenericInternalPostHookApi.as_view(
                         'generic-internal-hook'), methods=['POST', 'DELETE'])

    app.add_url_rule('/external/hooks/github',
                     view_func=GithubHookApi.as_view('github'),
                     methods=['POST'])
    app.add_url_rule('/hooks/github',
                     view_func=GithubHookApi.as_view('github-internal'),
                     methods=['POST'])

    app.add_url_rule('/external/hooks/travis',
                     view_func=TravisHookApi.as_view('travis'),
                     methods=['POST'])
    app.add_url_rule('/hooks/travis',
                     view_func=TravisHookApi.as_view('travis-internal'),
                     methods=['POST'])
