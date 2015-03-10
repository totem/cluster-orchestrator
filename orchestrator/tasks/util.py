import socket
from celery.exceptions import ChordError
from celery.result import ResultBase, AsyncResult, GroupResult
import orchestrator
from orchestrator.tasks.exceptions import TaskExecutionException
from orchestrator.util import retry

__author__ = 'sukrit'


def check_or_raise_task_exception(result):
    if isinstance(result, GroupResult):
        for result in result.results:
            check_or_raise_task_exception(result)
    elif isinstance(result, AsyncResult) and result.failed():
        if isinstance(result.result, TaskExecutionException):
            raise result.result
        elif isinstance(result.result, ChordError):
            check_or_raise_task_exception(result.parent)
        else:
            raise TaskExecutionException(result.result, result.traceback)


def _check_error(result):
    if not result or not isinstance(result, AsyncResult):
        return
    check_or_raise_task_exception(result)
    _check_error(result.parent)


@retry(10, delay=5, backoff=1, except_on=(IOError, socket.error))
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


def as_dict(error):
    """
    Creates a dictionary representation for a given error.

    :param error: Object representing error
    :type error: dict or object
    """
    if isinstance(error, dict):
        return error
    elif getattr(error, 'to_dict', None):
        obj_dict = error.to_dict()
        return obj_dict
    else:
        return {
            'message': repr(error),
            'code': 'INTERNAL'
        }


class TaskNotReadyException(Exception):
    """
    Exception corresponding to task that is not yet in ready state. This is
    useful for retrying celery task w/o blocking for task to be ready.
    """
    pass
