from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import json

from parser import ParserError
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from jsonschema import ValidationError
from mock import patch
from nose.tools import eq_, raises
from conf.appconfig import DEFAULT_DEPLOYER_URL
from orchestrator.cluster_config.effective import MergedConfigProvider
from orchestrator.cluster_config.etcd import EtcdConfigProvider
from orchestrator.cluster_config.github import GithubConfigProvider
from orchestrator.cluster_config.s3 import S3ConfigProvider
from orchestrator.services import config
from orchestrator.services.errors import ConfigProviderNotFound
from orchestrator.services.exceptions import ConfigValidationError, \
    ConfigParseError
from tests.helper import dict_compare

import orchestrator.services.config as service


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
    'github': {
        'token': 'mocktoken',
        'config_base': '/mock'
    }
})
@patch('orchestrator.services.config.CONFIG_PROVIDER_LIST')
def test_get_github_provider(mock_provider_list):
    """
    Should return github provider
    """
    # Given: Existing config provider list"
    mock_provider_list.__contains__.return_value = True
    mock_provider_list.__iter__.return_value = ['github']

    # When: I fetch provider that does not exists
    provider = service.get_provider('github')

    # Then: Etcd Config Provider is returned
    eq_(isinstance(provider, GithubConfigProvider), True)
    eq_(provider.auth, ('mocktoken', 'x-oauth-basic'))
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


def test_evaluate_value_with_nested_variables():
    """
    Should evaluate value by parsing templates.
    :return:
    """

    # Given: Object that needs to be evaluated
    obj = {
        'variables': {
            'var2': {
                'value': '{{ var2 }}-modified'
            }
        },
        'str-key': '{{ var1 }}',
        'int-key': 2,
        'nested-key': {
            'nested-key1': {
                'value': '{{ var1 }}',
                'template': True
            },
            'variables': {
                'var1': {
                    'value': '{{ var1 }}-modified'
                }
            },
            'nested-key-2': {},
            '__defaults__': {
                'default1': {
                    'value': '{{ var1 }} ',
                    'template': True
                }
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
            'nested-key1': 'var1-value-modified',
            'nested-key-2': {
                'default1': 'var1-value-modified'
            },
        },
        'list-key': [
            'list-value1',
            'var2-value-modified',
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
        'defaults': {},
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
                'enabled': True,
                'deployer-name': {
                    'value': '{{deployer}}'
                }
            },
            'deployer3': {
                'enabled': {
                    'value': '{{ False }}'
                }
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
                'deployer-name': 'deployer2',
                'deployment': {}
            }
        }
    })


@patch('orchestrator.services.config.validate')
@patch('orchestrator.services.config.open')
@patch('repoze.lru.lru_cache')
def test_validate_schema_for_successful_validation(m_lru_cache, m_open,
                                                   m_validate):

    # Given: Existing schema
    m_open.return_value.__enter__().read.return_value = '''{
    "title": "Schema for Job Config",
    "id": "#generic-hook-v1",
    "properties": {
        "mock": {
            "$ref": "${base_url}/link/config#/properties/mock"
        }
    }
}'''
    # And: Validator that succeeds validation
    m_validate.return_value = None

    # And: Config that needs to be validated
    config = {
        'mock-obj': 'mock-value'
    }

    # When: I validate against existing schema
    ret_value = service.validate_schema(config)

    # Then: Validation succeeds
    dict_compare(ret_value, config)
    dict_compare(m_validate.call_args[0][0], config)


@raises(ConfigValidationError)
@patch('orchestrator.services.config.validate')
@patch('orchestrator.services.config.open')
def test_validate_schema_for_failed_validation(m_open, m_validate):

        # Given: Existing schema
        schema = '''{
        "title": "Schema for Job Config",
        "id": "#generic-hook-v1"
}'''
        m_open().__enter__().read.return_value = schema

        # And: Validator that succeeds validation
        m_validate.side_effect = ValidationError('MockError',
                                                 schema=json.loads(schema))

        # And: Config that needs to be validated
        config = {
            'mock-obj': 'mock-value'
        }

        # When: I validate against existing schema
        service.validate_schema(config)

    # Then: ConfigValidationError is raised


def test_transform_string_values():
    """
    Should transform string values inside config as expected.
    :return:
    """

    # Given: Config that needs to be transformed
    config = {
        'key1': 'value1',
        'port': 1212,
        'enabled': 'True',
        'nested-port-key': {
            'port': u'2321',
            'nodes': u'12',
            'min-nodes': '13',
            'enabled': 'False',
            'force-ssl': 'true'
        },
        'array-config': [
            {
                'port': '123',
                'nodes': '13',
                'min-nodes': '14',
                'attempts': '10',
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
            'enabled': False,
            'force-ssl': True
        },
        'array-config': [
            {
                'port': 123,
                'nodes': 13,
                'min-nodes': 14,
                'attempts': 10,
                'enabled': False
            },
            'testval'
        ],
        'null-key': None
    })


@patch('orchestrator.services.config.get_provider')
@patch('orchestrator.services.config.validate_schema')
def test_load_config(m_validate_schema, m_get_provider):
    """
    Should load config successfully
    :return:
    """
    # Given: Existing valid config
    cfg1 = {
        'mockkey': 'mockvalue',
        8080: 'number-key',
        'deployers': {
            'deployer1': {
                'enabled': False,
                'variables': {}
            },
            'deployer2': {
                'enabled': True,
                'variables': {}
            }
        },
    }
    cfg2 = {
        'mockkey2': 'mockvalue2',
        'deployers': {
            'deployer1': {
                'variables': {
                    'deployer_url': 'deployer1-url1',
                },
                'url': {
                    'value': '{{deployer_url}}'
                }
            },
            'deployer2': {
                'variables': {
                    'deployer_url': 'deployer2-url1',
                },
                'url': {
                    'value': '{{deployer_url}}'
                }
            }
        },
        'environment': {
            'env1': 'val1'
        }
    }
    m_get_provider.return_value.load.side_effect = [cfg1, cfg2]
    m_validate_schema.side_effect = lambda vcfg, schema_name=None: vcfg

    # When: I load the config
    loaded_config = config.load_config('mockpath1', 'mockpath2')

    # Then: Config gets loaded as expected
    dict_compare(loaded_config, {
        'mockkey': 'mockvalue',
        'mockkey2': 'mockvalue2',
        '8080': 'number-key',
        'deployers': {
            'deployer2': {
                'templates': {
                    'app': {
                        'args': {}
                    },
                },
                'proxy': {},
                'deployment': {},
                'url': 'deployer2-url1',
                'enabled': True
            }
        },
        'environment': {
            'env1': {
                'value': 'val1',
                'encrypted': False
            }
        }
    })


@raises(ConfigParseError)
@patch('orchestrator.services.config.get_provider')
@patch('orchestrator.services.config.validate_schema')
def test_load_config_when_config_is_invalid(m_validate_schema, m_get_provider):
    """
    Should raise ConfigParseError when configuration is invalid
    :return:
    """
    # Given: Existing valid config
    m_get_provider.return_value.load.side_effect = ParserError('Mock')
    m_validate_schema.side_effect = lambda vcfg, schema_name=None: vcfg

    # When: I load the config
    config.load_config('mockpath1', 'mockpath2')

    # Then: ConfigParseError is raised


def test_normalize_config():
    """
    Should normalize the config containing environment variables
    """
    # Given: Existing config that needs to be normalized
    input_config = {
        'environment': {
            'var1': 'value1',
            'var2': 2,
            'var3': True,
            'var4': {
                'value': 'value4'
            },
            'var5': {

            },
            'var6': {
                'value': 'value6',
                'encrypted': True
            }
        },
        'nested': {
            'environment': {
                'var7': 'value7',
            }
        },
        'other': {
            'test-key': 'test-val'
        },
        'direct-string': 'value',
        'direct-int': 1
    }

    # When: I normalize the config
    normalized_config = dict(service.normalize_config(input_config))

    # Then: Config gets normalized as expected
    dict_compare(normalized_config, {
        'environment': {
            'var1': {
                'value': 'value1',
                'encrypted': False
            },
            'var2': {
                'value': '2',
                'encrypted': False
            },
            'var3': {
                'value': 'True',
                'encrypted': False
            },
            'var4': {
                'value': 'value4',
                'encrypted': False
            },
            'var5': {
                'value': '',
                'encrypted': False
            },
            'var6': {
                'value': 'value6',
                'encrypted': True
            }
        },
        'nested': {
            'environment': {
                'var7': {
                    'value': 'value7',
                    'encrypted': False
                }
            }
        },
        'other': {
            'test-key': 'test-val'
        },
        'direct-string': 'value',
        'direct-int': 1
    })
