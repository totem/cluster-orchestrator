from __future__ import absolute_import
from functools import wraps
import json
import logging
from elasticsearch import Elasticsearch, RequestError
from conf.appconfig import SEARCH_SETTINGS

MAPPING_LOCATION = './conf/index-mapping.json'
logger = logging.getLogger(__name__)


def orch_search(fun):
    """
    Function wrapper that automatically passes elastic search instance to
    wrapped function if search is enabled.
    If search is disabled, it skips the call to the search function and returns
    {"skip_search": True}

    :param fun: Function to be wrapped
    :return: Wrapped function.
    """
    @wraps(fun)
    def outer(*args, **kwargs):
        if SEARCH_SETTINGS['enabled']:
            kwargs.setdefault('es', get_search_client())
            kwargs.setdefault('idx', SEARCH_SETTINGS['default-index'])
            return fun(*args, **kwargs)
        else:
            logger.info('Elasticsearch is disabled. Skipping %s call',
                        fun.__name__)
            # Return ret_value if passed else return first argument
            # passed to the wrapped fn
            return kwargs.get('ret_value',
                              args[0] if len(args) >= 1 else None)
    return outer


def get_search_client():
    """
    Creates the elasticsearch client instance using SEARCH_SETTINGS

    :return: Instance of Elasticsearch
    :rtype: elasticsearch.Elasticsearch
    """
    return Elasticsearch(hosts=SEARCH_SETTINGS['host'],
                         port=SEARCH_SETTINGS['port'])


@orch_search
def create_index_mapping(es, idx):
    """
    Creates the elastic search index mapping (for the first time) when index
    does not exists.

    :param es:
    :param idx:
    :return:
    """
    if not es.indices.exists(idx):
        # Try to create index with default mappings

        with open(MAPPING_LOCATION, 'r') as file:
            body = json.load(file)
            try:
                es.indices.create(idx, body=body)
            except RequestError as error:
                if error.status_code == 400 and \
                        'IndexAlreadyExistsException' in error.error.decode():
                    logger.info(
                        'Index: %s already exists. Skip create..' % idx)
                else:
                    raise
