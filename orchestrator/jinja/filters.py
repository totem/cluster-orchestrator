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


def replace_regex(input, find, replace):
    """Regex replace filter"""
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
