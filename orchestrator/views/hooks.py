import functools
import hmac
from os.path import basename
from flask import request
from flask.views import MethodView
from conf.appconfig import HOOK_SETTINGS, MIME_GENERIC_HOOK_V1, \
    SCHEMA_GENERIC_HOOK_V1, MIME_JSON, MIME_JOB_V1, SCHEMA_JOB_V1, \
    SCHEMA_TASK_V1, MIME_TASK_V1, MIME_GITHUB_HOOK_V1, SCHEMA_GITHUB_HOOK_V1
from orchestrator.views import hypermedia, task_client
from orchestrator.views.error import raise_error
from hashlib import sha1
from orchestrator.tasks.job import handle_callback_hook, undeploy
from orchestrator.views.util import created_task, created, build_response


def authorize(sig_header='X-Hook-Signature'):
    """
    Function wrapper for authorizing web hooks

    :param func: Function to be wrapped
    :return: Wrapped function
    """

    def decorated(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            expected_digest = _get_digest(request.data)
            actual_digest = request.headers.get(sig_header, '')
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
                               'found: [%s]. The signature must be hexadecimal'
                               ' HMAC SHA1 Digest of request JSON using '
                               'pre-configured orchestrator secret'
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


class GenericPostHookApi(MethodView):
    """
    API for post hook for orchestrator. The post hook is invoked from CI/image
    builder services to update the status of the build.

    """

    @authorize('X-Hook-Signature')
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
            request_data['name'], commit=git['commit'],
            hook_status=request_data['status'],
            hook_result=request_data['result'])
        if accept_mimetype == MIME_JOB_V1:
            result = task_client.ready(result.id, wait=True, raise_error=True)
            job = result['output']
            location = '/jobs/%s' % (job['meta-info']['job-id'])
            # location = url_for(
            #     '.versions', name=deployment['deployment']['name'],
            #     version=deployment['deployment']['version'])
            return created(job, location=location)
        else:
            return created_task(result)


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
        if request_data['deleted']:
            ref = basename(request_data['ref'])
            owner = request_data['repository']['owner']['name']
            repo = request_data['repository']['name']
            task = undeploy.delay(owner, repo, ref)
            return created_task(task)
        else:
            return build_response('', status=204)


def register(app, **kwargs):
    """
    Registers Hooks API (generic, github, travis)

    :param app: Flask application
    :return: None
    """
    app.add_url_rule('/external/hooks/generic',
                     view_func=GenericPostHookApi.as_view('generic-hook'),
                     methods=['POST'])
    app.add_url_rule('/external/hooks/github',
                     view_func=GithubHookApi.as_view('github'),
                     methods=['POST'])
