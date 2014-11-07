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

SEARCH_SETTINGS = {
    'enabled': os.getenv('SEARCH_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'host': os.getenv('ELASTICSEARCH_HOST', '172.17.42.1'),
    'port': os.getenv('ELASTICSEARCH_PORT', '9200'),
    'default-index': 'orchestrator-%s' % os.getenv('CLUSTER_NAME', 'local')
}

CORS_SETTINGS = {
    'enabled': os.getenv('CORS_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'origins': os.getenv('CORS_ORIGINS', '*')
}

MIME_JSON = 'application/json'
MIME_ROOT_V1 = 'application/vnd.orch.root.v1+json'
MIME_HEALTH_V1 = 'application/vnd.totem.health.v1+json'

SCHEMA_ROOT_V1 = 'root-v1'
SCHEMA_HEALTH_V1 = 'health-v1'

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

    }
}

CONFIG_PROVIDER_LIST = os.getenv('CONFIG_PROVIDER_LIST', 's3,etcd,github')\
    .split(',')
