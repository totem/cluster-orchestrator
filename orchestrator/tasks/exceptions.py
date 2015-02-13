class TaskExecutionException(Exception):
    """
    Exception wrapping the final exception returned by celery task execution.
    """

    def __init__(self, cause, traceback=None):
        try:
            dict_repr = cause.to_dict()
        except AttributeError:
            dict_repr = {}

        self.message = dict_repr.get('message', str(cause))
        self.code = dict_repr.get('code', 'INTERNAL')
        self.traceback = traceback
        self.details = dict_repr.get('details', None)
        super(TaskExecutionException, self).__init__(cause, traceback)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': self.details,
            'traceback': self.traceback
        }


class DeploymentFailed(Exception):

    def __init__(self, deploy_response):
        self.response = deploy_response or {}
        self.code = 'DEPLOY_REQUEST_FAILED'
        super(DeploymentFailed, self).__init__(deploy_response)

    def to_dict(self):
        resp = self.response
        return {
            'message': 'Deployment request failed for url:%s. '
                       'Status:%s Reason: %s' %
                       (resp.get('url'), resp.get('status'),
                        resp.get('response')),
            'code': self.code,
            'details': self.response
        }


class HooksFailed(Exception):

    def __init__(self, failed_hooks):
        self.message = 'Hooks returned failed status to orchestrator.  ' \
                       'Failed hooks: {0}. Check the logs for each failed ' \
                       'service to see more details'.format(failed_hooks)
        self.code = 'HOOKS_FAILED'
        self.failed_hooks = failed_hooks
        super(HooksFailed, self).__init__(failed_hooks)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': {
                'failed-hooks': self.failed_hooks
            }
        }
