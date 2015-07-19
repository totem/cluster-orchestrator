import os

# Logging configuration
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(message)s'
LOG_DATE = '%Y-%m-%d %I:%M:%S %p'
LOG_ROOT_LEVEL = os.getenv('LOG_ROOT_LEVEL', 'INFO').upper()
LOG_IDENTIFIER = os.getenv('LOG_IDENTIFIER', 'cluster-orchestrator')

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "1", "on"}

API_PORT = int(os.getenv('API_PORT', '9400'))

TOTEM_ETCD_SETTINGS = {
    'base': os.getenv('ETCD_TOTEM_BASE', '/totem'),
    'host': os.getenv('ETCD_HOST', '172.17.42.1'),
    'port': int(os.getenv('ETCD_PORT', '4001')),
}

TOTEM_ENV = os.getenv('TOTEM_ENV', 'local')
CLUSTER_NAME = os.getenv('CLUSTER_NAME', TOTEM_ENV)
SEARCH_INDEX = os.getenv('SEARCH_INDEX', 'totem-{0}'.format(TOTEM_ENV))

SEARCH_SETTINGS = {
    'enabled': os.getenv('SEARCH_ENABLED', 'false').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'host': os.getenv('ELASTICSEARCH_HOST', '172.17.42.1'),
    'port': os.getenv('ELASTICSEARCH_PORT', '9200'),
    'default-index': SEARCH_INDEX
}

CORS_SETTINGS = {
    'enabled': os.getenv('CORS_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'origins': os.getenv('CORS_ORIGINS', '*')
}

MIME_JSON = 'application/json'
MIME_FORM_URL_ENC = 'application/x-www-form-urlencoded'
MIME_HTML = 'text/html'
MIME_TASK_V1 = 'application/vnd.orch.task.v1+json'
MIME_ROOT_V1 = 'application/vnd.orch.root.v1+json'
MIME_HEALTH_V1 = 'application/vnd.orch.health.v1+json'
MIME_GITHUB_HOOK_V1 = 'application/vnd.orch.github.hook.v1+json'
MIME_GENERIC_HOOK_V1 = 'application/vnd.orch.generic.hook.v1+json'
MIME_JOB_V1 = 'application/vnd.orch.job.v1+json'

SCHEMA_ROOT_V1 = 'root-v1'
SCHEMA_HEALTH_V1 = 'health-v1'
SCHEMA_GITHUB_HOOK_V1 = 'github-hook-v1'
SCHEMA_GENERIC_HOOK_V1 = 'generic-hook-v1'
SCHEMA_TRAVIS_HOOK_V1 = 'travis-hook-v1'
SCHEMA_JOB_V1 = 'job-v1'
SCHEMA_TASK_V1 = 'task-v1'

DEFAULT_DEPLOYER_URL = os.getenv('CLUSTER_DEPLOYER_URL',
                                 'http://localhost:9000')

API_MAX_PAGE_SIZE = 1000
API_DEFAULT_PAGE_SIZE = 10

HEALTH_OK = 'ok'
HEALTH_FAILED = 'failed'

LEVEL_FAILED = 1
LEVEL_FAILED_WARN = 2
LEVEL_SUCCESS = 3
LEVEL_STARTED = 4
LEVEL_PENDING = 5

ENCRYPTION = {
    'store': os.getenv('ENCRYPTION_STORE', None),
    's3': {
        'bucket': os.getenv('ENCRYPTION_S3_BUCKET', 'not-set'),
        'base': os.getenv('ENCRYPTION_S3_BASE', 'totem/keys'),
        },
    'passphrase': os.getenv('ENCRYPTION_PASSPHRASE', None),
}

DEFAULT_DEPLOYER_CONFIG = {
    'url': os.getenv('CLUSTER_DEPLOYER_URL', DEFAULT_DEPLOYER_URL),
    'enabled': True,
    'proxy': {},
    'templates': {
        'app': {
            'args': {}
        }
    },
    'deployment': {}
}

DEFAULT_HIPCHAT_TOKEN = os.getenv('HIPCHAT_TOKEN', '')
DEFAULT_GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

CONFIG_NAMES = os.getenv('CONFIG_NAMES', 'totem.yml,cluster-def.yml')\
    .split(',')
CONFIG_PROVIDERS = {
    's3': {
        'bucket':  os.getenv('CONFIG_S3_BUCKET', 'not_set'),
        'base': os.getenv('CONFIG_S3_BUCKET_BASE', 'totem/config'),
    },
    'etcd': {
        'base': os.getenv('ETCD_TOTEM_BASE', '/totem'),
        'host': os.getenv('ETCD_HOST', '172.17.42.1'),
        'port': int(os.getenv('ETCD_PORT', '4001')),
    },
    'effective': {
        'cache': {
            'enabled': os.getenv('CONFIG_CACHE_ENABLED', 'true').strip()
            .lower() in BOOLEAN_TRUE_VALUES,
            'ttl': int(os.getenv('CONFIG_CACHE_TTL', '120'))
        }
    },
    'github': {
        'token': os.getenv('GITHUB_TOKEN', None),
        'config_base': os.getenv('GITHUB_CONFIG_BASE', '/'),
    },
    'default': {
        'config': {
            'deployers': {
                'default': DEFAULT_DEPLOYER_CONFIG
            },
            'hooks': {
                'ci': {
                    'travis': {
                        'enabled': False,
                    }
                },
                'builders': {
                    'image-factory': {
                        'enabled': True,
                    }
                }
            },
            'enabled': False,
            'security': {
                'profile': 'default'
            },
            'notifications': {
                'hipchat': {
                    'enabled': os.getenv('HIPCHAT_ENABLED', 'false').strip()
                    .lower() in BOOLEAN_TRUE_VALUES,
                    'room': os.getenv('HIPCHAT_ROOM', 'not-set'),
                    'token': '',
                    'level': LEVEL_FAILED,
                    'colors': {
                        str(LEVEL_FAILED): 'red',
                        str(LEVEL_FAILED_WARN): 'red',
                        str(LEVEL_SUCCESS): 'green',
                        str(LEVEL_STARTED): 'yellow',
                        str(LEVEL_PENDING): 'yellow',
                    },
                    'url': 'https://api.hipchat.com'
                },
                'github': {
                    'enabled': os.getenv(
                        'GITHUB_NOTIFICATION_ENABLED', 'false')
                    .strip().lower() in BOOLEAN_TRUE_VALUES,
                    'token': '',
                    'level': LEVEL_PENDING
                }
            }
        }
    }
}

CONFIG_PROVIDER_LIST = os.getenv(
    'CONFIG_PROVIDER_LIST', 'etcd,default').split(',')

HOOK_SETTINGS = {
    'travis': {
        'token': os.getenv('TRAVIS_TOKEN', 'changeit'),
    },
    'secret': os.getenv('HOOK_SECRET', 'changeit'),
    'hint_secret_size': int(os.getenv('HOOK_SECRET_HINT', '2'))
}

TASK_SETTINGS = {
    'DEFAULT_GET_TIMEOUT': 600,
    'DEFAULT_RETRIES': 5,
    'DEFAULT_RETRY_DELAY': 10,
    'LOCK_RETRY_DELAY': 5,
    'LOCK_RETRIES': 20,
    'JOB_WAIT_RETRIES': 30,
    'JOB_WAIT_RETRY_DELAY': 10,
    'DEPLOY_WAIT_RETRY_DELAY': 20,
    'DEPLOY_WAIT_RETRIES': 10
}

JOB_SETTINGS = {
    'DEFAULT_TTL': 3600
}

JOB_STATE_NEW = 'NEW'
JOB_STATE_SCHEDULED = 'SCHEDULED'
JOB_STATE_COMPLETE = 'COMPLETE'
JOB_STATE_NOOP = 'NOOP'
JOB_STATE_FAILED = 'FAILED'

# Doc types for elastic search
DOC_TYPE_JOBS = 'jobs'
DOC_TYPE_EVENTS = 'events'

# Mongo Settings
MONGODB_USERNAME = os.getenv('MONODB_USERNAME', '')
MONGODB_PASSWORD = os.getenv('MONODB_PASSWORD', '')
MONGODB_HOST = os.getenv('MONGODB_HOST', '172.17.42.1')
MONGODB_PORT = int(os.getenv('MONGODB_PORT', '27017'))
MONGODB_DB = os.getenv('MONGODB_DB', 'totem')
MONGODB_AUTH = '{0}:{1}@'.format(MONGODB_USERNAME, MONGODB_PASSWORD) \
    if MONGODB_USERNAME else ''
MONGODB_DEFAULT_URL = 'mongodb://{0}{1}:{2}/{3}'.format(
    MONGODB_AUTH, MONGODB_HOST, MONGODB_PORT, MONGODB_DB)
MONGODB_URL = os.getenv('MONGODB_URL') or MONGODB_DEFAULT_URL
