from mock import MagicMock
from nose.tools import eq_
from orchestrator.tasks.exceptions import DeploymentFailed, HooksFailed, \
    TaskExecutionException
from tests.helper import dict_compare


def test_deployment_failed_with_raw_text_response():
    # When: i create Instance of DeploymentFailed exception
    exc = DeploymentFailed({
        'response': {
            'raw': 'MockError'
        },
        'url': 'MockUrl',
        'status': 'MockStatus'
    })

    # Then: DeploymentFailed instance gets created as expected
    eq_(exc.code, 'DEPLOY_REQUEST_FAILED')
    eq_(exc.message, 'Deployment request failed for url:MockUrl. '
                     'Status:MockStatus Reason: MockError')


def test_deployment_failed_with_message_in_response():
    # When: i create Instance of DeploymentFailed exception
    exc = DeploymentFailed({
        'response': {
            'message': 'MockError'
        },
        'url': 'MockUrl',
        'status': 'MockStatus'
    })

    # Then: DeploymentFailed instance gets created as expected
    eq_(exc.code, 'DEPLOY_REQUEST_FAILED')
    eq_(exc.message, 'Deployment request failed for url:MockUrl. '
                     'Status:MockStatus Reason: MockError')


def test_deployment_failed_with_no_message_in_response():
    # When: i create Instance of DeploymentFailed exception
    exc = DeploymentFailed({
        'response': {
            'mockerror': 'mockerror'
        },
        'url': 'MockUrl',
        'status': 'MockStatus'
    })

    # Then: DeploymentFailed instance gets created as expected
    eq_(exc.code, 'DEPLOY_REQUEST_FAILED')
    eq_(exc.message, 'Deployment request failed for url:MockUrl. '
                     'Status:MockStatus '
                     'Reason: {\'mockerror\': \'mockerror\'}')


def test_deployment_failed_to_dict():
    # Given: Instance of DeploymentFailed exception
    deploy_response = {
        'response': {
            'message': 'mockerror'
        },
        'url': 'MockUrl',
        'status': 'MockStatus'
    }
    exc = DeploymentFailed(deploy_response)

    # When: I invoke to_dict on exception instance
    output = exc.to_dict()

    # Then: Expected response is returned
    dict_compare(output, {
        'message': 'Deployment request failed for url:MockUrl. '
                   'Status:MockStatus Reason: mockerror',
        'code': 'DEPLOY_REQUEST_FAILED',
        'details': deploy_response
    })


def test_to_dict_for_hooks_failed():
    # Given: Instance of HooksFailed exception
    failed_hooks = ['builder']
    exc = HooksFailed(failed_hooks)

    # When: I invoke to_dict on exception instance
    output = exc.to_dict()

    # Then: Expected response is returned
    dict_compare(output, {
        'message': 'Hooks returned failed status to orchestrator.  '
                   'Failed hooks: [\'builder\']. Check the logs for each '
                   'failed service to see more details',
        'code': 'HOOKS_FAILED',
        'details': {
            'failed-hooks':failed_hooks
        }
    })


def test_to_dict_for_task_execution_exception():
    # Given: Instance of TaskExecutionException
    cause = MagicMock()
    cause.to_dict.return_value = {
        'code': 'MOCK_CODE',
        'message': 'MockError'
    }
    exc = TaskExecutionException(cause)

    # When: I invoke to_dict on exception instance
    output = exc.to_dict()

    # Then: Expected response is returned
    dict_compare(output, {
        'message': 'MockError',
        'code': 'MOCK_CODE',
        'details': None,
        'traceback': None
    })


def test_task_execution_exception_init_with_cause_having_dict_repr():
    # Given: Mock cause with to_dict representation
    cause = MagicMock()
    cause.to_dict.return_value = {
        'code': 'MOCK_CODE',
        'message': 'MockError'
    }

    # When: I create instance of TaskExecutionException
    exc = TaskExecutionException(cause)

    # Then: Exception object is initialized as expected
    eq_(exc.message, 'MockError')
    eq_(exc.code, 'MOCK_CODE')
    eq_(exc.details, None)
    eq_(exc.traceback, None)


def test_task_execution_exception_init_with_cause_not_having_dict_repr():
    # Given: Mock cause with to_dict representation
    cause = 'MockError'

    # When: I create instance of TaskExecutionException
    exc = TaskExecutionException(cause)

    # Then: Exception object is initialized as expected
    eq_(exc.message, 'MockError')
    eq_(exc.code, 'INTERNAL')
    eq_(exc.details, None)
    eq_(exc.traceback, None)