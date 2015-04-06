from __future__ import absolute_import

import logging
from logging.handlers import SysLogHandler
from conf.appconfig import LOG_FORMAT, LOG_DATE, LOG_ROOT_LEVEL, TOTEM_ENV, \
    LOG_IDENTIFIER


def init_logging(name):
    app_logger = logging.getLogger(name)
    app_logger.setLevel(LOG_ROOT_LEVEL)
    if TOTEM_ENV == 'local':
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        app_logger.addHandler(handler)

    else:
        formatter = logging.Formatter(
            '{0}[%(process)d]: %(name)s: %(message)s'
            .format(LOG_IDENTIFIER))
        handler = logging.handlers.SysLogHandler(
            address='/dev/log',
            facility=SysLogHandler.LOG_DAEMON)
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        app_logger.addHandler(handler)
        app_logger.info('Logger initialized')
    return app_logger


def init_celery_logging(*args, **kwargs):
    init_logging('celery')
