from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from orchestrator.tasks.search import massage_config
from tests.helper import dict_compare


def test_massage_config():
    """
    Should massage configuration as required by search.
    """

    # Given: Configuration that needs to be massaged.
    config = {
        'key1': 'value1',
        'key2': {
            'value': 'value2',
            'encrypted': True
        },
        'key3': [
            {
                'key3.1': {
                    'value': 'value3.1'
                }
            }
        ]
    }

    # When: I massage the config
    result = massage_config(config)

    # Then: Config gets massaged as expected
    dict_compare(result, {
        'key1': 'value1',
        'key2': '',
        'key3': [
            {
                'key3.1': 'value3.1'
            }
        ]
    })
