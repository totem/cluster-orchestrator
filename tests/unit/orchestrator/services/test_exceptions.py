from orchestrator.services.exceptions import ConfigValueError, \
    ConfigValidationError
from tests.helper import dict_compare

__author__ = 'sukrit'


def test_to_dict_for_config_value_error():
    # Given: Instance of ConfigValueError
    error = ConfigValueError('/mockpath', 'mockvalue', 'mockreason')

    # When: I create dict representation for exception
    result = error.to_dict()

    # Then: Expected representation is returned
    dict_compare(result, {
        'message': 'Error happened while parsing path:/mockpath '
                   'value:mockvalue.  mockreason',
        'code': 'CONFIG_ERROR',
        'details': {
            'path': '/mockpath',
            'value': 'mockvalue',
            'reason': 'mockreason'
        }
    })


def test_to_dict_for_config_validation_error():
    # Given: Instance of ConfigValidationError
    error = ConfigValidationError('mockmessage', '/mockpath', 'mockschema')

    # When: I create dict representation for exception
    result = error.to_dict()

    # Then: Expected representation is returned
    dict_compare(result, {
        'message': 'mockmessage',
        'code': 'CONFIG_VALIDATION_ERROR',
        'details': {
            'schema-path': '/mockpath',
            'schema': 'mockschema'
        }
    })
