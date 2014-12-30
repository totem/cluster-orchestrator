import os

# Logging configuration
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s %(message)s'
LOG_DATE = '%Y-%m-%d %I:%M:%S %p'
LOG_ROOT_LEVEL = os.getenv('LOG_ROOT_LEVEL', 'INFO').upper()

BOOLEAN_TRUE_VALUES = {"true", "yes", "y", "1", "on"}

API_PORT = int(os.getenv('API_PORT', '9400'))

TOTEM_ETCD_SETTINGS = {
    'base': os.getenv('ETCD_TOTEM_BASE', '/totem'),
    'host': os.getenv('ETCD_HOST', '172.17.42.1'),
    'port': int(os.getenv('ETCD_PORT', '4001')),
}

CLUSTER_NAME = os.getenv('CLUSTER_NAME', 'local')

SEARCH_SETTINGS = {
    'enabled': os.getenv('SEARCH_ENABLED', 'false').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'host': os.getenv('ELASTICSEARCH_HOST', '172.17.42.1'),
    'port': os.getenv('ELASTICSEARCH_PORT', '9200'),
    'default-index': 'orchestrator-%s' % CLUSTER_NAME
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

API_MAX_PAGE_SIZE = 1000
API_DEFAULT_PAGE_SIZE = 10

HEALTH_OK = 'ok'
HEALTH_FAILED = 'failed'

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
            'ttl': 120
        }
    },
    'github': {
        'token': os.getenv('GITHUB_TOKEN', None)
    },
    'default': {
        'config': {
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
            'deployer': {
                'url': os.getenv('CLUSTER_DEPLOYER_URL',
                                 'http://localhost:9000'),
                'proxy': {},
                'templates': {},
                'deployment': {}
            }
        }
    }
}

CONFIG_PROVIDER_LIST = os.getenv(
    'CONFIG_PROVIDER_LIST', 'etcd,github,default').split(',')

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
    'JOB_WAIT_RETRIES': 20,
    'JOB_WAIT_RETRY_DELAY': 2
}

JOB_SETTINGS = {
    'DEFAULT_TTL': 600
}

JOB_STATE_NEW = 'NEW'
JOB_STATE_SCHEDULED = 'SCHEDULED'
JOB_STATE_DEPLOY_REQUESTED = 'DEPLOY_REQUESTED'
JOB_STATE_NOOP = 'NOOP'
JOB_STATE_FAILED = 'FAILED'
