from __future__ import absolute_import
from celery import Celery

app = Celery(__name__)
app.config_from_object('conf.celeryconfig')
