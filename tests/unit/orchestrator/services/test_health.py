from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from collections import namedtuple
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

from celery.tests.case import patch
from conf.appconfig import HEALTH_OK
from orchestrator.services import health
from tests.helper import dict_compare

__author__ = 'sukrit'


@patch.dict('orchestrator.services.health.SEARCH_SETTINGS', {
    'enabled': True
})
@patch('orchestrator.services.health.ping')
@patch('orchestrator.services.health.get_search_client')
@patch('orchestrator.services.health.client')
def test_get_health_when_elasticsearch_is_enabled(client, get_es, ping):
    """
    Should get the health status when elastic search is enabled
    """

    # Given: Operational external services"
    get_es().info.return_value = 'mock'
    EtcdInfo = namedtuple('Info', ('machines', 'leader'))
    client.Client.return_value = EtcdInfo(['machine1'], 'machine1')

    # When: I get the health of external services
    health_status = health.get_health()

    # Then: Expected health status is returned
    dict_compare(health_status, {
        'etcd': {
            'status': HEALTH_OK,
            'details': {
                'machines': ['machine1'],
                'leader': 'machine1'
            }
        },
        'elasticsearch': {
            'status': HEALTH_OK,
            'details': 'mock'
        }
    })


@patch.dict('orchestrator.services.health.SEARCH_SETTINGS', {
    'enabled': False
})
@patch('orchestrator.services.health.ping')
@patch('orchestrator.services.health.client')
def test_get_health_when_elasticsearch_is_disabled(client, ping):
    """
    Should get the health status when elastic search is enabled
    """

    # Given: Operational external services"
    EtcdInfo = namedtuple('Info', ('machines', 'leader'))
    client.Client.return_value = EtcdInfo(['machine1'], 'machine1')

    # When: I get the health of external services
    health_status = health.get_health()

    # Then: Expected health status is returned
    dict_compare(health_status, {
        'etcd': {
            'status': HEALTH_OK,
            'details': {
                'machines': ['machine1'],
                'leader': 'machine1'
            }
        }
    })


@patch.dict('orchestrator.services.health.SEARCH_SETTINGS', {
    'enabled': False
})
@patch('orchestrator.services.health.ping')
@patch('orchestrator.services.health.client')
def test_get_health_when_celery_is_enabled(client, ping):
    """
    Should get the health status when elastic search is enabled
    """

    # Given: Operational external services"
    ping.delay().get.return_value = 'pong'
    EtcdInfo = namedtuple('Info', ('machines', 'leader'))
    client.Client.return_value = EtcdInfo(['machine1'], 'machine1')

    # When: I get the health of external services
    health_status = health.get_health(check_celery=True)

    # Then: Expected health status is returned
    dict_compare(health_status, {
        'etcd': {
            'status': HEALTH_OK,
            'details': {
                'machines': ['machine1'],
                'leader': 'machine1'
            }
        },
        'celery': {
            'status': HEALTH_OK,
            'details': 'Celery ping:pong'
        },
    })
