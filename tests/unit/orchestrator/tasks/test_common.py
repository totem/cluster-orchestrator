from mock import MagicMock, patch
from nose.tools import eq_, raises
from orchestrator.tasks.common import ErrorHandlerTask, ping, async_wait
from orchestrator.tasks.util import TaskNotReadyException


@patch('orchestrator.tasks.common.group')
def test_on_failure_for_error_handler_task(m_group):
    """
    Should invoke error tasks as expected
    """
    # Given: Keyword args with error tasks
    kwargs = {
        'error_tasks': MagicMock()
    }
    # And: Mock Error
    exc = MagicMock(spec=BaseException)

    # When: I invoke on_failure with given keyword args
    ErrorHandlerTask().on_failure(exc, 'MockTaskId', [],
                                  kwargs, None)

    # Then: Error tasks are invoked as expected
    m_group.assert_called_once_with(kwargs['error_tasks'])
    m_group.return_value.delay.assert_called_once_with(exc)


@patch('orchestrator.tasks.common.group')
def test_on_failure_for_error_handler_task_with_no_error_tasks(m_group):
    """
    Should not invoke any tasks
    """
    # Given: Keyword args with no error tasks
    kwargs = {
        'error_tasks': []
    }
    # And: Mock Error
    exc = MagicMock(spec=BaseException)

    # When: I invoke on_failure with given keyword args
    ErrorHandlerTask().on_failure(exc, 'MockTaskId', [],
                                  kwargs, None)

    # Then: Error tasks are invoked as expected
    eq_(m_group.call_count, 0)


def test_ping():
    """
    Should return pong
    """

    # When: I invoke ping task
    ret_value = ping()

    # Then: 'pong' is returned
    eq_(ret_value, 'pong')


@patch('orchestrator.tasks.common.simple_result')
def test_async_wait(m_simple_result):
    # Given: Mock result
    result = {'mockkey': 'mockvalue'}
    m_simple_result.return_value = result

    # When: I perform async wait on mock result
    ret_value = async_wait(result)

    # Then: Expected return value is returned
    eq_(ret_value, result)
    m_simple_result.assert_called_once_with(result)


@patch('orchestrator.tasks.common.simple_result')
def test_async_wait_with_return_value_specified(m_simple_result):
    # Given: Mock result
    result = {'mockkey': 'mockvalue'}
    m_simple_result.return_value = result

    # When: I perform async wait on mock result
    ret_value = async_wait(result, ret_value='Mock')

    # Then: Expected return value is returned
    eq_(ret_value, 'Mock')
    m_simple_result.assert_called_once_with(result)


@patch('orchestrator.tasks.common.simple_result')
@raises(TaskNotReadyException)
def test_async_wait_when_task_is_not_ready(m_simple_result):
    # Given: Result is not ready
    m_simple_result.side_effect = TaskNotReadyException()
    result = MagicMock()

    # When: I perform async wait on mock result
    async_wait(result)

    # Then: TaskNotReadyException is re-raised
