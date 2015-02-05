from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from mock import patch
from nose.tools import eq_, raises
from conf.appconfig import DEFAULT_DEPLOYER_URL
from orchestrator.cluster_config.effective import MergedConfigProvider
from orchestrator.cluster_config.etcd import EtcdConfigProvider
from orchestrator.cluster_config.s3 import S3ConfigProvider
import orchestrator.services.config as service
from orchestrator.services.errors import ConfigProviderNotFound
from tests.helper import dict_compare

__author__ = 'sukrit'


@patch.dict('orchestrator.services.config.CONFIG_PROVIDERS', {
    'provider1': {},
    'provider3': {}
})
@patch('orchestrator.services.config.CONFIG_PROVIDER_LIST')
def test_get_providers(mock_provider_list):
    """
    Should get the list of available providers
    """
    # Given: Existing config provider list"

    mock_provider_list.__iter__.return_value = ['provider1', 'provider2']

    # When: I fetch provider list
    providers = service.get_providers()

    # Then: Expected provider list is returned
    eq_(list(providers), ['provider1', 'effective'])


@raises(ConfigProviderNotFound)
def test_get_provider_when_not_found():
    """
    Should raise ConfigProviderNotFound when provider is not found
    """

    # When: I fetch provider that does not exists
    service.get_provider('invalid')

    # Then: ConfigProviderNotFound is raised


@patch.dict('orchestrator.services.config.CONFIG_PROVIDERS', {
    'etcd': {
        'host': 'mockhost',
        'port': 10000,
        'base': '/mock'
    }
})
@patch('orchestrator.services.config.CONFIG_PROVIDER_LIST')
def test_get_etcd_provider(mock_provider_list):
    """
    Should return etcd provider
    """
    # Given: Existing config provider list"
    mock_provider_list.__contains__.return_value = True
    mock_provider_list.__iter__.return_value = ['etcd']

    # When: I fetch provider that does not exists
    provider = service.get_provider('etcd')

    # Then: Etcd Config Provider is returned
    eq_(isinstance(provider, EtcdConfigProvider), True)
    eq_(provider.etcd_cl.host, 'mockhost')
    eq_(provider.etcd_cl.port, 10000)
    eq_(provider.config_base, '/mock/config')
    eq_(provider.ttl, None)


@patch.dict('orchestrator.services.config.CONFIG_PROVIDERS', {
    's3': {
        'bucket': 'mockbucket',
        'base': '/mock'
    }
})
@patch('orchestrator.services.config.CONFIG_PROVIDER_LIST')
def test_get_s3_provider(mock_provider_list):
    """
    Should return s3 provider
    """
    # Given: Existing config provider list"
    mock_provider_list.__contains__.return_value = True
    mock_provider_list.__iter__.return_value = ['s3']

    # When: I fetch provider that does not exists
    provider = service.get_provider('s3')

    # Then: Etcd Config Provider is returned
    eq_(isinstance(provider, S3ConfigProvider), True)
    eq_(provider.bucket, 'mockbucket')
    eq_(provider.config_base, '/mock')


@patch.dict('orchestrator.services.config.CONFIG_PROVIDERS', {
    'etcd': {
        'host': 'mockhost',
        'port': 10000,
        'base': '/mock'
    },
    'effective': {
        'cache': {
            'enabled': True,
            'ttl': 300
        }
    }
})
@patch('orchestrator.services.config.CONFIG_PROVIDER_LIST')
def test_get_effective_provider(mock_provider_list):
    """
    Should return effective provider
    :return:
    """

    """
    Should return effective provider provider
    """
    # Given: Existing config provider list"
    mock_provider_list.__contains__.return_value = True
    mock_provider_list.__iter__.return_value = ['effective', 'default']

    # When: I fetch provider that does not exists
    provider = service.get_provider('effective')

    # Then: Etcd Config Provider is returned
    eq_(isinstance(provider, MergedConfigProvider), True)
    eq_(len(provider.providers), 1)


def test_evaluate_value():
    """
    Should evaluate value by parsing templates.
    :return:
    """

    # Given: Object that needs to be evaluated
    obj = {
        'str-key': '{{ var1 }}',
        'int-key': 2,
        'nested-key': {
            'nested-key1': {
                'value': '{{ var1 }}',
                'template': True
            }
        },
        'list-key': [
            'list-value1',
            {
                'value': '\n\n{{ var2 }}\n\n',
            }
        ],
        'value-key': {
            'value': '{{ var1 }}',
            'encrypted': True,
            'template': True
        }
    }

    # And: variables that needs to be applied
    variables = {
        'var1': 'var1-value',
        'var2': 'var2-value'
    }

    # When: I evaluate object
    result = service.evaluate_value(obj, variables)

    # Then: Expected result with evaluated values is returned

    dict_compare(result, {
        'str-key': '{{ var1 }}',
        'int-key': 2,
        'nested-key': {
            'nested-key1': 'var1-value'
        },
        'list-key': [
            'list-value1',
            'var2-value',
        ],
        'value-key': {
            'value': 'var1-value',
            'encrypted': True
        }
    })


def test_evaluate_variables():
    """
    Should evaluate config variables
    :return: None
    """

    # Given: Variables that needs to be expanded
    variables = {
        'var1': {
            'value': True
        },
        'var2': {
            'value': '{{var1}}-var2value',
            'template': True,
            'priority': 2,
        },
        'var3': {
            'value': '{{default1}}-var3value',
            'template': True,
            'priority': 1,
        },
        'var4': False
    }

    # When: I evaluate the config
    result = service.evaluate_variables(variables, {
        'default1': 'default1value'
    })

    # Then: Expected config is returned
    dict_compare(result, {
        'var1': 'true',
        'var2': 'true-var2value',
        'var3': 'default1value-var3value',
        'default1': 'default1value',
        'var4': 'false'
    })


def test_evaluate_config_with_no_deployers():
    """
    Should evaluate config as expected
    :return: None
    """

    # Given: Config that needs to be evaluated
    config = {
        'variables': {
            'var1': 'value1',
            'var2': {
                'value': '{{var1}}-var2value',
                'template': True,
                'priority': 2,
            },
        },
        'key1': {
            'value': 'test-{{var1}}-{{var2}}-{{var3}}',
            'template': True
        }
    }

    # When: I evaluate the config
    result = service.evaluate_config(config, {
        'var1': 'default1',
        'var2': 'default2',
        'var3': 'default3'
    })

    # Then: Expected config is returned
    dict_compare(result, {
        'key1': 'test-value1-value1-var2value-default3',
        'deployers': {}
    })


def test_evaluate_config_with_deployers():
    """
    Should evaluate config as expected
    :return: None
    """

    # Given: Config that needs to be evaluated
    config = {
        'variables': {
            'var1': 'value1',
            'var2': {
                'value': '{{var1}}-var2value',
                'template': True,
                'priority': 2,
                },
            },
        'key1': {
            'value': 'test-{{var1}}-{{var2}}-{{var3}}',
            'template': True
        },
        'deployers': {
            'default': {},
            'deployer2': {
                'url': 'deployer2-url',
                'enabled': True
            },
            'deployer3': {
                'enabled': False
            }
        }
    }

    # When: I evaluate the config
    result = service.evaluate_config(config, {
        'var1': 'default1',
        'var2': 'default2',
        'var3': 'default3'
    })

    # Then: Expected config is returned
    dict_compare(result, {
        'key1': 'test-value1-value1-var2value-default3',
        'deployers': {
            'default': {
                'url': DEFAULT_DEPLOYER_URL,
                'enabled': True,
                'proxy': {},
                'templates': {
                    'app': {
                        'args': {}
                    }
                },
                'deployment': {}
            },
            'deployer2': {
                'url': 'deployer2-url',
                'enabled': True,
                'proxy': {},
                'templates': {
                    'app': {
                        'args': {}
                    }
                },
                'deployment': {}
            },
            'deployer3': {
                'enabled': False
            }
        }
    })


def test_transform_string_values():
    """
    Should transform string values inside config as expected.
    :return:
    """

    # Given: Config that needs to be transformed
    config = {
        'key1': 'value1',
        'port': 1212,
        'enabled': 'true',
        'nested-port-key': {
            'port': u'2321',
            'nodes': u'12',
            'min-nodes': '13',
            'enabled': 'false'
        },
        'array-config': [
            {
                'port': '123',
                'nodes': '13',
                'min-nodes': '14',
                'enabled': False
            },
            'testval'
        ],
        'null-key': None
    }

    # When: I transform string values in config
    result = service.transform_string_values(config)

    # Then: Transformed config is returned
    dict_compare(result, {
        'key1': 'value1',
        'port': 1212,
        'enabled': True,
        'nested-port-key': {
            'port': 2321,
            'nodes': 12,
            'min-nodes': 13,
            'enabled': False
        },
        'array-config': [
            {
                'port': 123,
                'nodes': 13,
                'min-nodes': 14,
                'enabled': False
            },
            'testval'
        ],
        'null-key': None
    })
