"""
Test for Generic Exceptions for Orchestrator
"""
from nose.tools import eq_
from orchestrator.exceptions import OrchestratorError, BusinessRuleViolation
from tests.helper import dict_compare


def test_to_dict_for_orchestrator_error():
    # Given: Instance of OrchestratorError
    error = OrchestratorError('mockerror')

    # When: I create dict representation for exception
    result = error.to_dict()

    # Then: Expected representation is returned
    dict_compare(result, {
        'message': 'mockerror',
        'code': 'ORCHESTRATOR_ERROR',
        'details': {},
        'traceback': None
    })


def test_string_representation_for_orchestrator_error():
    # Given: Instance of OrchestratorError
    error = OrchestratorError('mockerror')

    # When: I get the string representation for the error
    result = str(error)

    # Then: Error message is returned
    eq_(result, 'mockerror')


def test_business_rule_violation():

    # When: I create instance of BusinessRuleViolation
    error = BusinessRuleViolation('mockerror')

    # Then: Error instance is initialized as expected
    eq_(error.code, 'BUSINESS_RULE_VIOLATION')
    eq_(error.message, 'mockerror')
    eq_(error.details, {})
