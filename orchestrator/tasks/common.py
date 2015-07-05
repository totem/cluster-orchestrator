from celery import Task, group, signature
from conf.appconfig import TASK_SETTINGS
from orchestrator.celery import app
from orchestrator.tasks.util import simple_result, TaskNotReadyException


class ErrorHandlerTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        error_tasks = kwargs.get('error_tasks')
        if error_tasks:
            if not isinstance(error_tasks, list):
                error_tasks = [error_tasks]
            error_tasks = [signature(error_task) for error_task in error_tasks]
            group(*error_tasks).delay(exc)


@app.task(bind=True, base=ErrorHandlerTask)
def async_wait(self, result,
               default_retry_delay=TASK_SETTINGS['DEFAULT_RETRY_DELAY'],
               max_retries=TASK_SETTINGS['DEFAULT_RETRIES'],
               ret_value=None, error_tasks=None):
    """
    Performs asynchronous wait for result. It uses retry approach for result
    to be available rather calling get() . This way the trask do not directly
    wait for wach other

    :param result: Result to be evaluated.
    :param default_retry_delay: Delay between retries.
    :param max_retries: Maximum no. of retries to wait for result
    :param ret_value: If None, evaluated result is returned else ret_value is
        returned
    :return: ret_value or evaluated result
    """

    try:
        result = simple_result(result)
    except TaskNotReadyException as exc:
        raise self.retry(exc=exc,
                         countdown=default_retry_delay,
                         max_retries=max_retries)
    return ret_value if ret_value is not None else result


@app.task
def ping():
    return 'pong'
