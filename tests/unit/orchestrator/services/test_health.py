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


@patch('orchestrator.services.health.ping')
@patch('orchestrator.services.health.client')
def test_get_health(client, ping):
    """
    Should get the health status when elastic search is enabled
    """

    # Given: Operational external services"
    ping.delay().get.return_value = 'pong'
    EtcdInfo = namedtuple('Info', ('machines',))
    client.Client.return_value = EtcdInfo(['machine1'])

    # When: I get the health of external services
    health_status = health.get_health()

    # Then: Expected health status is returned
    dict_compare(health_status, {
        'etcd': {
            'status': HEALTH_OK,
            'details': {
                'machines': ['machine1']
            }
        },
        'celery': {
            'status': HEALTH_OK,
            'details': 'Celery ping:pong'
        },
    })


@patch('orchestrator.services.health.ping')
@patch('orchestrator.services.health.client')
def test_get_health_when_celery_is_disabled(client, ping):
    """
    Should get the health status when elastic search is enabled
    """

    # Given: Operational external services"
    EtcdInfo = namedtuple('Info', ('machines',))
    client.Client.return_value = EtcdInfo(['machine1'])

    # When: I get the health of external services
    health_status = health.get_health(check_celery=False)

    # Then: Expected health status is returned
    dict_compare(health_status, {
        'etcd': {
            'status': HEALTH_OK,
            'details': {
                'machines': ['machine1']
            }
        }
    })
