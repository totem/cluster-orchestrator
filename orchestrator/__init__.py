from __future__ import absolute_import
from celery.signals import setup_logging
import orchestrator.logger

__version__ = '0.3.7'
__author__ = 'sukrit'

orchestrator.logger.init_logging()
setup_logging.connect(orchestrator.logger.init_celery_logging)
