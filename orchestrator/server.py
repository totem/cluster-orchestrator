from flask import Flask
from flask.ext.cors import CORS
from conf.appconfig import CORS_SETTINGS
from orchestrator.views import root, hypermedia

app = Flask(__name__)

hypermedia.register_schema_api(app).register_error_handlers(app)

if CORS_SETTINGS['enabled']:
    CORS(app, resources={'/*': {'origins': CORS_SETTINGS['origins']}})

for module in [root]:
    module.register(app)