import json
from nose.tools import eq_
from conf.appconfig import MIME_ROOT_V1
import orchestrator
from orchestrator.server import app


class TestRootView:
    """
    Tests root api
    """

    def setup(self):
        self.client = app.test_client()

    def test_root(self):
        """
        Should set the Link header for root endpoint.
        """

        # When I invoke the root endpoint
        resp = self.client.get('/')

        # The Link header is set for the root endpoint
        eq_(resp.status_code, 200)
        eq_(resp.headers['Content-Type'], MIME_ROOT_V1)
        data = json.loads(resp.data.decode())
        eq_(data['version'], orchestrator.__version__)
