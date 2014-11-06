from nose.tools import eq_

from orchestrator.util import dict_merge


__author__ = 'sukrit'

"""
Test for :mod: `deployer.util`
"""


def test_dict_merge():
    """
    should merge the two dictionaries
    """

    # Given: Dict obj that needs to be merged
    dict1 = {
        'key1': 'value1',
        'key2': {
            'key2.1': 'value2.1a'
        }
    }

    dict2 = {
        'key3': 'value3',
        'key2': {
            'key2.1': 'value2.1b',
            'key2.2': 'value2.2a'
        }
    }

    # When: I merge the two dictionaries
    merged_dict = dict_merge(dict1, dict2)

    # Then: Merged dictionary is returned
    eq_(merged_dict, {
        'key1': 'value1',
        'key2': {
            'key2.1': 'value2.1a',
            'key2.2': 'value2.2a'
        },
        'key3': 'value3',
    })
