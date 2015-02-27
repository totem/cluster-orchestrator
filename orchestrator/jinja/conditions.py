from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)
import re

__author__ = 'sukrit'

"""
Defines all the filters used for jinja templates (config)
"""

USE_TESTS = ('starting_with', 'matching', )


def apply_conditions(env):
    """
    Applies filters on jinja env.

    :param env: Jinja environment
    :return:
    """

    for name in USE_TESTS:
        env.tests[name] = globals()[name]
    return env


def starting_with(value, prefix):
    """
    Filter to check if value starts with prefix
    :param value: Input source
    :type value: str
    :param prefix:
    :return: True if matches. False otherwise
    :rtype: bool
    """
    return str(value).startswith(str(prefix))


def matching(value, pattern, casesensitive=True):
    """
    Filter that performs a regex match

    :param value: Input source
    :type value: str
    :param pattern: Regex Pattern to be matched
    :return: True if matches. False otherwise
    :rtype: bool
    """
    flags = re.I if not casesensitive else 0
    return re.match(str(pattern), str(value), flags) is not None
