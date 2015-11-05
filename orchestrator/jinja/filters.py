from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)

import re

__author__ = 'sukrit'

"""
Package that includes custom filters required for totem config processing
"""

USE_FILTERS = ('replace_regex', )


def replace_regex(input_str, find, replace):
    """
    Regex replace filter that replaces all occurrences of given regex match
    in a given string

    :param input_str: Input string on which replacement is to be performed
    :type input_str: str
    :param find: Regular expression string that needs to be used for
        find/replacement
    :type find: str
    :param replace: Regex replacement string
    :type replace: str
    :return: Regex replaced string
    :rtype: str
    """
    return re.sub(find, replace, input)


def apply_filters(env):
    """
    Applies filters on jinja env.

    :param env: Jinja environment
    :return:
    """

    for name in USE_FILTERS:
        env.filters[name] = globals()[name]
    return env
