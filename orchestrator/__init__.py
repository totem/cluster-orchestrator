import logging
from conf.appconfig import LOG_FORMAT, LOG_DATE, LOG_ROOT_LEVEL

__version__ = '0.1.9'
__author__ = 'sukrit'

logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=LOG_ROOT_LEVEL)
logging.getLogger('boto').setLevel(logging.INFO)
