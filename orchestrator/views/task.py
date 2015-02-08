import logging
import flask
from flask.views import MethodView
from conf.appconfig import TASK_SETTINGS, BOOLEAN_TRUE_VALUES
from orchestrator.views import task_client
from flask import request

logger = logging.getLogger(__name__)


class TaskApi(MethodView):
    """
    Api for task
    """

    def get(self, id=None):
        if not id:
            return flask.abort(404)
        else:
            wait = request.args.get('wait', 'false').strip().lower()
            wait = True if wait in BOOLEAN_TRUE_VALUES else False
            timeout = int(request.args.get(
                'timeout', TASK_SETTINGS['DEFAULT_GET_TIMEOUT']))
            response = task_client.ready(id, wait=wait, timeout=timeout)
            return flask.jsonify(response)


def register(app, **kwargs):
    app.add_url_rule('/tasks/<string:id>', view_func=TaskApi.as_view('tasks'),
                     methods=['GET'])
