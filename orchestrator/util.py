"""
General utility methods
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

import copy


def dict_merge(*dictionaries):
    """
    Performs nested merge of multiple dictionaries. The values from
    dictionaries appearing first takes precendence

    :param dictionaries: List of dictionaries that needs to be merged.
    :return: merged dictionary
    :rtype
    """

    merged_dict = {}

    def merge(source, defaults):
        # Nested merge requires both source and defaults to be dictionary
        if isinstance(source, dict) and isinstance(defaults, dict):
            for key, value in defaults.items():
                if key not in source:
                    # Key not found in source : Use the defaults
                    source[key] = value
                else:
                    # Key found in source : Recursive merge
                    source[key] = merge(source[key], value)
        return source

    for merge_with in dictionaries:
        merged_dict = merge(merged_dict, copy.deepcopy(merge_with or {}))

    return merged_dict
