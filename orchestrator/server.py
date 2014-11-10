from flask import Flask
from flask.ext.cors import CORS
from conf.appconfig import CORS_SETTINGS
import orchestrator
from orchestrator.views import root, hypermedia, health, github, error, task

app = Flask(__name__)

hypermedia.register_schema_api(app).register_error_handlers(app)

if CORS_SETTINGS['enabled']:
    CORS(app, resources={'/*': {'origins': CORS_SETTINGS['origins']}})

for module in [error, root, health, github, task]:
    module.register(app)


@app.before_request
def set_current_app():
    # DO not remove line below
    # Explanation: https://github.com/celery/celery/issues/2315
    orchestrator.celery.app.set_current()
