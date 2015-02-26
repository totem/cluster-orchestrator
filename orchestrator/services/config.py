import json
from parser import ParserError
from yaml.error import MarkedYAMLError
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)
import copy
import types
from jinja2 import TemplateSyntaxError
from jinja2.environment import get_spontaneous_environment
from jsonschema import validate, ValidationError
from repoze.lru import lru_cache
from conf.appconfig import CONFIG_PROVIDERS, CONFIG_PROVIDER_LIST, \
    BOOLEAN_TRUE_VALUES, DEFAULT_DEPLOYER_CONFIG, API_PORT, CONFIG_NAMES
from orchestrator.cluster_config.default import DefaultConfigProvider
from orchestrator.cluster_config.effective import MergedConfigProvider
from orchestrator.cluster_config.etcd import EtcdConfigProvider
from orchestrator.cluster_config.s3 import S3ConfigProvider
from orchestrator.jinja import tests
from orchestrator.services.errors import ConfigProviderNotFound
from orchestrator.services.exceptions import ConfigValueError, \
    ConfigValidationError, ConfigParseError
from orchestrator.util import dict_merge


__author__ = 'sukrit'


def get_providers():
    for provider_type in CONFIG_PROVIDER_LIST:
        provider_type = provider_type.strip()
        if provider_type in CONFIG_PROVIDERS:
            yield provider_type
    yield 'effective'


def _get_effective_provider():
    """
    Gets the effective config provider.

    :return: Effective Config provider.
    :rtype: orchestrator.cluster_config.effective.MergedConfigProvider
    """
    providers = list()
    for provider_type in get_providers():
        if provider_type != 'effective':
            provider = get_provider(provider_type)
            if provider:
                providers.append(provider)

    if CONFIG_PROVIDERS['effective']['cache']['enabled']:
        cache_provider = _get_etcd_provider(
            ttl=CONFIG_PROVIDERS['effective']['cache']['ttl'])
    else:
        cache_provider = None
    return MergedConfigProvider(*providers, cache_provider=cache_provider)


def _get_etcd_provider(ttl=None):
    """
    Gets the etcd config provider.

    :keyword ttl: time to live in seconds
    :type ttl: number
    :return: Instance of EtcdConfigProvider
    :rtype: EtcdConfigProvider
    """
    return EtcdConfigProvider(
        etcd_host=CONFIG_PROVIDERS['etcd']['host'],
        etcd_port=CONFIG_PROVIDERS['etcd']['port'],
        config_base=CONFIG_PROVIDERS['etcd']['base']+'/config',
        ttl=ttl
    )


def _get_s3_provider():
    """
    Gets S3 Config Provider

    :return: Instance of S3ConfigProvider
    :rtype: S3ConfigProvider
    """
    return S3ConfigProvider(
        bucket=CONFIG_PROVIDERS['s3']['bucket'],
        config_base=CONFIG_PROVIDERS['s3']['base']
    )


def _get_default_provider():
    return DefaultConfigProvider()


@lru_cache(1)
def _load_job_schema():
    """
    Helper function that loads given schema

    :param schema_name:
    :return:
    """
    base_url = 'http://localhost:%d' % API_PORT
    fname = 'schemas/job-config-v1.json'
    with open(fname) as file:
        data = file.read().replace('${base_url}', base_url)
        return json.loads(data)


def get_provider(provider_type):
    """
    Factory method to create config provider instance.

    :param provider_type:
    :type provider_type: str
    :param args: Arguments for the provider
    :param kwargs: Keyword arguments for the provider.
    :return: AbstractConfigProvider instance.
    :rtype: AbstractConfigProvider
    """
    if provider_type not in get_providers():
        raise ConfigProviderNotFound(provider_type)

    locator = '_get_%s_provider' % (provider_type)
    if locator in globals():
        return globals()[locator]()


def validate_schema(config):
    """
    Validates schema for given configuration.

    :param config: Config dictionary
    :type config: dict
    :return: config if validation passes
    :rtype: dict
    """
    schema = _load_job_schema()
    try:
        validate(config, schema)
    except ValidationError as ex:
        message = 'Failed to validate config against schema job-config-v1. ' \
                  'Reason: %s' % ex.message
        raise ConfigValidationError(message, '/'.join(ex.schema_path),
                                    ex.schema)
    return config


def load_config(*paths, **kwargs):
    """
    Loads config for given path and provider type.

    :param paths: Tuple consisting of nested level path
    :type paths: tuple
    :keyword default_variables: Variables to be applied during template
    evaluation
    :type default_variables: dict
    :keyword provider_type: Type of provider
    :type provider_type: str
    :keyword config_names: List of config names to be loaded. Defaults to
        CONFIG_NAMES defined in appconfig
    :type config_names: list
    :return: Parsed configuration
    :rtype: dict
    """
    default_variables = kwargs.get('default_variables', {})
    provider_type = kwargs.get('provider_type', 'effective')
    config_names = kwargs.get('config_names', CONFIG_NAMES)
    provider = get_provider(provider_type)
    try:
        unified_config = dict_merge(
            *[provider.load(name, *paths) for name in config_names])
        return evaluate_config(
            validate_schema(unified_config),
            default_variables)

    except (MarkedYAMLError, ParserError) as yaml_error:
        raise ConfigParseError(yaml_error, paths)


def write_config(name, config, *paths, **kwargs):
    """
    Writes config for given path

    :param config: Dictionary based configuration
    :type config: dict
    :param provider_type: Type of provider
    :type provider_type: str
    :return: None
    """
    provider_type = kwargs.get('provider_type', 'effective')
    provider = get_provider(provider_type)
    if provider:
        provider.write(name, config, *paths)


def _get_jinja_environment():
    """
    Creates Jinja env for evaluating config

    :return: Jinja Environment
    """
    env = get_spontaneous_environment()
    env.line_statement_prefix = '#'
    return tests.apply_tests(env)


def evaluate_template(template_value, variables={}):
    env = _get_jinja_environment()
    return env.from_string(str(template_value)).render(**variables).strip()


def evaluate_variables(variables, default_variables={}):

    merged_vars = dict_merge({}, default_variables)

    def get_sort_key(item):
        return item[1]['priority']

    def as_tuple(vars):
        for variable_name, variable_val in vars.items():
            variable_val = copy.deepcopy(variable_val)
            if not hasattr(variable_val, 'items'):
                variable_val = {
                    'value': variable_val,
                    'template': False,
                    'priority': 0
                }
            variable_val.setdefault('template', True)
            variable_val.setdefault('priority', 1)
            variable_val.setdefault('value', '')
            val = variable_val['value']
            if isinstance(val, bool):
                variable_val['value'] = str(val).lower()
            yield (variable_name, variable_val)

    def expand(var_name, var_value):
        try:
            merged_vars[var_name] = evaluate_template(
                var_value['value'], merged_vars) if var_value['template'] \
                else var_value['value']
        except Exception as exc:
            raise ConfigValueError('/variables/%s/' % var_name, var_value,
                                   str(exc))

    sorted_vars = sorted(as_tuple(variables), key=get_sort_key)
    for sorted_var_name, sorted_var_value in sorted_vars:
        expand(sorted_var_name, sorted_var_value)

    return merged_vars


def evaluate_value(value, variables={}, location='/'):
    """
    Renders tokenized values (using nested strategy)

    :param value: Value that needs to be evaluated (str , list, dict, int etc)
    :param variables: Variables to be used for Jinja2 templates
    :param identifier: Identifier used to identify tokenized values. Only str
        values that begin with identifier are evaluated.
    :return: Evaluated object.
    """
    value = copy.deepcopy(value)
    if hasattr(value, 'items'):
        if 'variables' in value:
            variables = evaluate_variables(value['variables'], variables)
            del(value['variables'])

        if 'value' in value:
            value.setdefault('encrypted', False)
            value.setdefault('template', True)
            if value['template']:
                try:
                    value['value'] = evaluate_template(value['value'],
                                                       variables)
                except TemplateSyntaxError as error:
                    raise ConfigValueError(location, value['value'],
                                           reason=error.message)
            del(value['template'])
            if not value['encrypted']:
                value = value['value']
            return value

        else:
            for each_k, each_v in value.items():
                value[each_k] = evaluate_value(each_v, variables,
                                               '%s%s/' % (location, each_k))
            return {
                each_k: evaluate_value(each_v, variables)
                for each_k, each_v in value.items()
            }

    elif isinstance(value, (list, tuple, set, types.GeneratorType)):
        return [evaluate_value(each_v, variables, '%s[]/' % (location, ))
                for each_v in value]

    return value.strip() if isinstance(value, (str,)) else value


def evaluate_config(config, default_variables={}, var_key='variables'):
    """
    Performs rendering of all template values defined in config. Also takes
    user defined variables nd default variables for substitution in the config
    .
    :param config:
    :param default_variables:
    :param var_key:
    :return: Evaluated config
    :rtype: dict
    """
    updated_config = copy.deepcopy(config)
    updated_config.setdefault(var_key, {})
    updated_config.setdefault('deployers', {})

    for deployer_name, deployer in updated_config.get('deployers').items():
        if deployer.get('enabled', True):
            updated_config['deployers'][deployer_name] = dict_merge(
                deployer, DEFAULT_DEPLOYER_CONFIG)
        else:
            del(updated_config['deployers'][deployer_name])
    return transform_string_values(
        evaluate_value(updated_config, default_variables))


def transform_string_values(config):
    """
    Transforms the string values to appropriate type in config

    :param config: dictionary configuration with evaluated template parameters
    :type config: dict
    :return: transformed config
    :rtype: dict
    """
    new_config = copy.deepcopy(config)

    # Convert 'enabled' keys to boolean
    def convert_enabled_keys(use_config, location='/'):
        if hasattr(use_config, 'items'):
            for each_k, each_v in use_config.items():
                try:
                    if each_v is None:
                        continue
                    elif each_k == 'enabled' and isinstance(each_v, str):
                        use_config[each_k] = each_v.lower() in \
                            BOOLEAN_TRUE_VALUES
                    elif each_k in ('port', 'nodes', 'min-nodes') and \
                            isinstance(each_v, str):
                        use_config[each_k] = int(each_v)
                    elif hasattr(each_v, 'items'):
                        convert_enabled_keys(each_v, '%s%s/' %
                                             (location, each_k))
                    elif isinstance(each_v,
                                    (list, tuple, set, types.GeneratorType)):
                        for idx, val in enumerate(each_v):
                            convert_enabled_keys(
                                val, '%s%s[%d]/' % (location, each_k, idx))
                except ValueError as error:
                    raise ConfigValueError(location + each_k, each_v,
                                           error.message)

    convert_enabled_keys(new_config)
    return new_config
