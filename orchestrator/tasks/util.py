from celery.result import ResultBase, AsyncResult, GroupResult
import orchestrator
from orchestrator.tasks.exceptions import TaskExecutionException

__author__ = 'sukrit'


def check_or_raise_task_exception(result):
    if isinstance(result, AsyncResult) and result.failed():
        if isinstance(result.result, TaskExecutionException):
            raise result.result
        else:
            raise TaskExecutionException(result.result, result.traceback)


def _check_error(result):
    if not result or not isinstance(result, AsyncResult):
        return
    check_or_raise_task_exception(result)
    _check_error(result.parent)


def simple_result(result):
    # DO not remove line below
    # Explanation: https://github.com/celery/celery/issues/2315
    orchestrator.celery.app.set_current()

    if isinstance(result, GroupResult):
        return simple_result(result.results)
    elif hasattr(result, '__iter__') and not isinstance(result, dict):
        return [simple_result(each_result)
                for each_result in result]
    elif isinstance(result, ResultBase):
        _check_error(result)
        if result.ready():
            check_or_raise_task_exception(result)
            return simple_result(result.result)
        else:
            raise TaskNotReadyException()
    return result


class TaskNotReadyException(Exception):
    """
    Exception corresponding to task that is not yet in ready state. This is
    useful for retrying celery task w/o blocking for task to be ready.
    """
    pass
