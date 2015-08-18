import os

# Logging configuration
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(message)s'
LOG_DATE = '%Y-%m-%d %I:%M:%S %p'
LOG_ROOT_LEVEL = os.getenv('LOG_ROOT_LEVEL', '').upper() or 'INFO'
LOG_IDENTIFIER = os.getenv('LOG_IDENTIFIER', 'cluster-orchestrator')

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "1", "on"}

API_PORT = int(os.getenv('API_PORT', '9400'))

TOTEM_ETCD_SETTINGS = {
    'base': os.getenv('ETCD_TOTEM_BASE', '/totem'),
    'host': os.getenv('ETCD_HOST', '127.0.0.1'),
    'port': int(os.getenv('ETCD_PORT', '4001')),
}

TOTEM_ENV = os.getenv('TOTEM_ENV', 'local')
CLUSTER_NAME = os.getenv('CLUSTER_NAME', TOTEM_ENV)
GIT_COMMIT = os.getenv('GIT_COMMIT', 'latest')

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

SCM_TYPE_GITHUB = 'github'
SCM_TYPE_OTHER = 'other'

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
    'enabled': False,
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
        'base': TOTEM_ETCD_SETTINGS['base'],
        'host': TOTEM_ETCD_SETTINGS['host'],
        'port': TOTEM_ETCD_SETTINGS['port'],
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
            'scm': {
                'type': SCM_TYPE_GITHUB,
                'auth': {
                    'token': {
                        'value': '',
                        'encrypted': False
                    }
                }
            },
            'deployers': {
                '__defaults__': DEFAULT_DEPLOYER_CONFIG
            },
            'hooks': {
                'ci': {
                    'travis': {
                        'enabled': False,
                    }
                },
                'builder': {
                    'image-factory': {
                        'enabled': True,
                    }
                },
                'scm-push': {
                    'github-push': {
                        'enabled': True,
                    }
                },
                'scm-create': {
                    'github-create': {
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

# Hook status
HOOK_STATUS_SUCCESS = 'success'
HOOK_STATUS_PENDING = 'pending'
HOOK_STATUS_FAILED = 'failed'

# Hook Type
HOOK_TYPE_CI = 'ci'
HOOK_TYPE_BUILDER = 'builder'
HOOK_TYPE_SCM_PUSH = 'scm-push'

# Store Settings
DEFAULT_STORE_NAME = 'mongo'
DEFAULT_JOB_EXPIRY_SECONDS = 4 * 7 * 24 * 3600  # 4 weeks
JOB_EXPIRY_SECONDS = int(
    os.getenv('JOB_EXPIRY_SECONDS', DEFAULT_JOB_EXPIRY_SECONDS))

# Mongo Settings
MONGODB_USERNAME = os.getenv('MONGODB_USERNAME', '')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD', '')
MONGODB_HOST = os.getenv('MONGODB_HOST', '127.0.0.1')
MONGODB_PORT = int(os.getenv('MONGODB_PORT', '27017'))
MONGODB_DB = os.getenv('MONGODB_DB') or 'totem-{}'.format(TOTEM_ENV)
MONGODB_AUTH_DB = os.getenv('MONGODB_AUTH_DB') or MONGODB_DB
MONGODB_AUTH = '{0}:{1}@'.format(MONGODB_USERNAME, MONGODB_PASSWORD) \
    if MONGODB_USERNAME else ''
MONGODB_DEFAULT_URL = 'mongodb://{0}{1}:{2}/{3}'.format(
    MONGODB_AUTH, MONGODB_HOST, MONGODB_PORT, MONGODB_AUTH_DB)
MONGODB_URL = os.getenv('MONGODB_URL') or MONGODB_DEFAULT_URL

MONGODB_JOB_COLLECTION = os.getenv('MONGODB_JOB_COLLECTION') or \
    'orchestrator-jobs'
MONGODB_EVENT_COLLECTION = os.getenv('MONGODB_EVENT_COLLECTION') or \
    'events'
