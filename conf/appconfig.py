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
    'yoda_base': os.getenv('ETCD_YODA_BASE', '/yoda'),
}

SEARCH_SETTINGS = {
    'enabled': os.getenv('SEARCH_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'host': os.getenv('ELASTICSEARCH_HOST', '172.17.42.1'),
    'port': os.getenv('ELASTICSEARCH_PORT', '9200'),
    'default-index': 'cluster-deployer-%s' % os.getenv('CLUSTER_NAME', 'local')
}

CORS_SETTINGS = {
    'enabled': os.getenv('CORS_ENABLED', 'true').strip().lower() in
    BOOLEAN_TRUE_VALUES,
    'origins': os.getenv('CORS_ORIGINS', '*')
}

MIME_JSON = 'application/json'
MIME_ROOT_V1 = 'application/vnd.orch.root.v1+json'

SCHEMA_ROOT_V1 = 'root-v1'

API_MAX_PAGE_SIZE = 1000
API_DEFAULT_PAGE_SIZE = 10
