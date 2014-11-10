from __future__ import absolute_import
from celery import Celery
from celery.signals import celeryd_init
from orchestrator import elasticsearch

app = Celery(__name__)
app.config_from_object('conf.celeryconfig')


@celeryd_init.connect
def configure_search(**kwargs):
    """
    Creates the index mapping for elastic search on startup.
    If mappings already exists, this will be ignored

    :param kwargs:
    :return:
    """
    elasticsearch.create_index_mapping()
