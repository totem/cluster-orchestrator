from mock import MagicMock
from nose.tools import eq_
from orchestrator.tasks import util


def test_as_dict_for_dictionary_type():
    """
    Should return the input dictionary
    """
    # Given: Input dictionary
    input = {
        'mockkey': 'mockvalue'
    }

    # When: I invoke as_dict with dict type
    output = util.as_dict(input)

    # Then: Input dictionary is returned
    eq_(output, input)


def test_as_dict_for_obj_with_to_dict_method():
    """
    Should return the dict representation
    """
    # Given: Input Object
    input = MagicMock()
    input.to_dict.return_value = {
        'mockkey': 'mockvalue'
    }

    # When: I invoke as_dict with dict type
    output = util.as_dict(input)

    # Then: Dictionary representation is returned
    eq_(output, {
        'mockkey': 'mockvalue'
    })


def test_as_dict_for_obj_with_no_to_dict_method():
    """
    Should return the dict representation
    """
    # Given: Input object
    input = 'test'

    # When: I invoke as_dict with dict type
    output = util.as_dict(input)

    # Then: Dictionary representation is returned
    eq_(output, {
        'code': 'INTERNAL',
        'message': repr(input)
    })
