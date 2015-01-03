from datetime import timedelta
import os
from ast import literal_eval

from celery.schedules import crontab
from kombu import Queue

CLUSTER_NAME = os.getenv('CLUSTER_NAME', 'local')

MESSAGES_TTL = 7200

# Broker and Queue Settings
BROKER_URL = os.getenv('BROKER_URL', 'amqp://guest:guest@localhost:5672/')
CELERY_DEFAULT_QUEUE = 'orchestrator-%s-default' % CLUSTER_NAME
CELERY_QUEUES = (
    Queue(CELERY_DEFAULT_QUEUE, routing_key='default',
          queue_arguments={'x-message-ttl': MESSAGES_TTL}),
)
CELERY_DEFAULT_EXCHANGE = 'orchestrator-%s' % CLUSTER_NAME
CELERY_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_RESULT_BACKEND = 'amqp'
CELERY_RESULT_EXCHANGE = 'orchestrator-%s-results' % CLUSTER_NAME
CELERY_IMPORTS = ('orchestrator.tasks', 'orchestrator.tasks.job',
                  'orchestrator.tasks.common', 'celery.task')
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_ALWAYS_EAGER = literal_eval(os.getenv('CELERY_ALWAYS_EAGER', 'False'))
CELERY_CHORD_PROPAGATES = True

CELERY_STORE_ERRORS_EVEN_IF_IGNORED = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_IGNORE_RESULT = False
CELERYD_TASK_SOFT_TIME_LIMIT = 300
CELERYD_TASK_TIME_LIMIT = 330
CELERY_SEND_TASK_SENT_EVENT = True
CELERY_TASK_RESULT_EXPIRES = timedelta(hours=6)
CELERY_RESULT_PERSISTENT = True

# Remote Management
CELERYD_POOL_RESTARTS = True

# Queue Settings
CELERY_QUEUE_HA_POLICY = 'all'

# GLobal Settings
CELERY_TIMEZONE = 'UTC'

# Task releated settings
CELERY_ACKS_LATE = True
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    'max_retries': 30,
    'interval_step': 1,
    'interval_max': 10
}

# Celery Beat settings
CELERYBEAT_SCHEDULE = {
    'celery.task.backend_cleanup': {
        'task': 'orchestrator.tasks.backend_cleanup',
        'schedule': crontab(hour="*/2", minute="0"),
        'args': (),
    }
}
