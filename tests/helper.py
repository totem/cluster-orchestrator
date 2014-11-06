from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

__author__ = 'sukrit'
from nose.tools import ok_, eq_


def dict_compare(actual, expected, key_path='',):
    """
    :param actual:
    :param expected:
    :param nested_path:
    :return: None

    >>> dict_compare('A', 'B')
    Traceback (most recent call last):
    ...
    AssertionError: Actual 'A' != Expected 'B'  at path: ''

    >>> dict_compare({}, 'B')
    Traceback (most recent call last):
    ...
    AssertionError: Actual {} != Expected 'B'  at path: ''

    >>> dict_compare({}, {})
    True

    >>> dict_compare({'key1':'value1'}, {'key2':'value2'})
    Traceback (most recent call last):
    ...
    AssertionError: Key 'key1' was not expected at path: ''

    >>> dict_compare({'key1':'value1', 'key2': 'value2'},
    ... {'key2':'value2', 'key1': 'value1'})
    True

    >>> dict_compare({'key1':{'key1.1': 'value1.1', 'key1.2': 'value1.2'}},
    ... {'key1':{'key1.2': 'value1.2', 'key1.1': 'value1.1'}})
    True

    >>> dict_compare({'key1':'value1'}, {'key2':'value2', 'key1':'value1'})
    Traceback (most recent call last):
    ...
    AssertionError: Key 'key2' was not found in actual at path: ''

    >>> dict_compare({'key1':'value1'}, {'key1':'value2'})
    Traceback (most recent call last):
    ...
    AssertionError: Actual 'value1' != Expected 'value2'  at path: '.key1'

    """

    if isinstance(actual, dict) and isinstance(expected, dict):
        for key in actual:
            ok_(key in expected, 'Key \'%s\' was not expected at '
                                 'path: \'%s\'' % (key, key_path))
            dict_compare(actual[key], expected[key], '%s.%s' % (key_path, key))

        for key in expected:
            ok_(key in actual, 'Key \'%s\' was not found in actual at '
                               'path: \'%s\'' % (key, key_path))
    else:
        eq_(actual, expected, 'Actual %r != Expected %r  at path: \'%s\''
            % (actual, expected, key_path))
    return True
