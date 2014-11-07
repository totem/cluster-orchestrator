from __future__ import (absolute_import, division,
                        print_function)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

from flask.views import MethodView
from conf.appconfig import MIME_HEALTH_V1, SCHEMA_HEALTH_V1, MIME_JSON, \
    HEALTH_OK
from orchestrator.services.health import get_health
from orchestrator.views import hypermedia
from orchestrator.views.util import build_response


class HealthApi(MethodView):
    """
    Health API
    """

    @hypermedia.produces(
        {
            MIME_HEALTH_V1: SCHEMA_HEALTH_V1,
            MIME_JSON: SCHEMA_HEALTH_V1
        }, default=MIME_HEALTH_V1)
    def get(self, **kwargs):
        """
        Health endpoint for Orchestrator

        :return: Flask Json Response containing version.
        """

        health = get_health()
        failed_checks = [
            health_status['status'] for health_status in health.values()
            if health_status['status'] != HEALTH_OK
        ]
        http_status = 200 if not failed_checks else 500
        return build_response(health, status=http_status)


def register(app, **kwargs):
    """
    Registers HealthApi ('/health')
    Only GET operation is available.

    :param app: Flask application
    :return: None
    """
    app.add_url_rule('/health', view_func=HealthApi.as_view('health'),
                     methods=['GET'])
