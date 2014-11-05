__version__ = '0.1.0'
__author__ = 'sukrit'

import logging
from conf.appconfig import LOG_FORMAT, LOG_DATE, LOG_ROOT_LEVEL

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=LOG_ROOT_LEVEL)
