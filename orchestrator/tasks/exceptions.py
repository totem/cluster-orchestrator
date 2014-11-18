
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
        self.response = deploy_response
        super(DeploymentFailed, self).__init__(deploy_response)

    def to_dict(self):
        return {
            'message': 'Deployment request failed',
            'code': 'INTERNAL',
            'details': self.response
        }
