from hyperschema.hypermedia import HyperMedia
import orchestrator
from orchestrator.services.task_client import TaskClient

__author__ = 'sukrit'

hypermedia = HyperMedia()
task_client = TaskClient(orchestrator.celery.app)
