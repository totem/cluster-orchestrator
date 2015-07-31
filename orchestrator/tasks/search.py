"""
Module for updating/searching elastic search.

Deprecated
"""


def massage_config(config):
    """
    massages config for indexing.
    1. Removes encrypted parameters from indexing.
    2. Extracts raw parameter for value types.

    :param config: dictionary that needs to be massaged
    :type config: dict
    :return: massaged config
    :rtype: dict
    """

    if hasattr(config, 'items'):
        if 'value' in config:

            if config.get('encrypted', False):
                return ''
            else:
                return str(config.get('value'))
        else:
            return {
                k: massage_config(v) for k, v in config.items()
            }
    elif isinstance(config, (list, set, tuple)):
        return [massage_config(v) for v in config]
    else:
        return config
