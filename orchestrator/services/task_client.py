"""
This module defines client service methods for celery result (for client
processing)

"""
from celery.result import ResultBase, AsyncResult
from conf.appconfig import TASK_SETTINGS
from orchestrator.tasks.exceptions import TaskExecutionException


class TaskClient:

    def __init__(self, celery_app):
        self.celery_app = celery_app

    def find_error_task(self, task, wait=False, raise_error=False,
                        timeout=TASK_SETTINGS['DEFAULT_GET_TIMEOUT']):
        if not task or not isinstance(task, ResultBase):
            return

        if isinstance(task, AsyncResult):
            if not task.ready() and wait:
                task.get(propagate=raise_error, timeout=timeout)
            if task.failed():
                return task
            elif task.status in ['PENDING'] and task.parent:
                while task.parent:
                    if task.parent.failed():
                        return task.parent
                    else:
                        task = task.parent
            else:
                return self.find_error_task(task.result)
        else:
            return

    def ready(self, id, wait=False, raise_error=False,
              timeout=TASK_SETTINGS['DEFAULT_GET_TIMEOUT']):
        status = 'READY'
        output = self.celery_app.AsyncResult(id)
        error_task = self.find_error_task(output, raise_error=raise_error,
                                          wait=wait, timeout=timeout)

        if error_task:
            output, status = \
                error_task.result, error_task.status
            if not isinstance(output, TaskExecutionException):
                output = TaskExecutionException(output, error_task.traceback)
        else:
            while isinstance(output, AsyncResult) and status is 'READY':
                if wait:
                    output.get(timeout=timeout, propagate=raise_error)
                if output.ready():
                    output = output.result
                else:
                    status = 'PENDING'
                    output = None
        if output:
            try:
                output = output.to_dict()
            except AttributeError:
                if not isinstance(output, dict) \
                        and not isinstance(output, list):
                    output = str(output)

        return {
            'status': status,
            'output': output
        }
