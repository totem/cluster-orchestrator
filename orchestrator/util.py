"""
General utility methods
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import errno
from functools import wraps
import os
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)

import copy
import signal


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


class TimeoutError(Exception):
    """
    Error corresponding to timeout of a function use with @timeout annotation.
    """
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    """
    Decorator that applies timeout for a dunction

    :param seconds: Timeout in seconds. Defaults to 10s.
    :param error_message: Error message corresponding to timeout.
    :return: decorated function
    """
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, _handle_timeout)
                signal_disabled = False
            except ValueError:
                # Possibly running in debug mode. Timeouts will be ignored
                signal_disabled = True
                pass

            if not signal_disabled:
                signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                if not signal_disabled:
                    signal.alarm(0)
            return result

        return wrapper
    return decorator
