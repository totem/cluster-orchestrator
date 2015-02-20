import flask
from flask.views import MethodView
from conf.appconfig import MIME_ROOT_V1, SCHEMA_ROOT_V1, MIME_JSON, MIME_HTML
import orchestrator
from orchestrator.views import hypermedia


class RootApi(MethodView):
    """
    Root API
    """

    @hypermedia.produces({
        MIME_ROOT_V1: SCHEMA_ROOT_V1,
        MIME_JSON: SCHEMA_ROOT_V1
    }, default=MIME_ROOT_V1)
    def get(self, **kwargs):
        """
        Gets the version for the Orchestrator API.

        :return: Flask Json Response containing version.
        """
        return flask.jsonify({'version': orchestrator.__version__})


def register(app, **kwargs):
    """
    Registers RootApi ('/')
    Only GET operation is available.

    :param app: Flask application
    :return: None
    """
    app.add_url_rule('/', view_func=RootApi.as_view('root'), methods=['GET'])
