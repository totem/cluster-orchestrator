#!/bin/bash -le

cat <<END>> /etc/profile.d/cluster-deployer-env.sh
export ETCD_HOST='${ETCD_HOST:-172.17.42.1}'
export ETCD_PORT='${ETCD_PORT:-4001}'
export ETCD_TOTEM_BASE='${ETCD_TOTEM_BASE:-/totem}'
export ETCD_YODA_BASE='${ETCD_YODA_BASE:-/yoda}'
export CELERY_GEVENT_EXECUTORS='${CELERY_GEVENT_EXECUTORS:-1}'
export CELERY_GEVENT_CONCURRENCY='${CELERY_GEVENT_CONCURRENCY:-50}'
export API_EXECUTORS='${API_EXECUTORS:-2}'
export SSH_HOST_KEY='${SSH_HOST_KEY:-/root/.ssh/id_rsa}'
export SSH_PASSPHRASE='${SSH_PASSPHRASE}'
export GITHUB_TOKEN='${GITHUB_TOKEN}'
export ELASTICSEARCH_HOST='${ELASTICSEARCH_HOST:-172.17.42.1}'
export ELASTICSEARCH_PORT='${ELASTICSEARCH_PORT:-9200}'
export CLUSTER_NAME='${CLUSTER_NAME:-totem-local}'
export QUAY_ORGANIZATION='${QUAY_ORGANIZATION:-totem}'
export QUAY_PREFIX='${QUAY_PREFIX:-totem-}'
export SEARCH_ENABLED=${SEARCH_ENABLED:-false}
export C_FORCE_ROOT=true
export AMQP_HOST='${AMQP_HOST:-172.17.42.1}'
export AMQP_PORT='${AMQP_HOST:-5672}'
export AMQP_USERNAME='${AMQP_USERNAME:-guest}'
export AMQP_PASSWORD='${AMQP_PASSWORD:-guest}'
export BROKER_URL='${BROKER_URL}'
export CLUSTER_DEPLOYER_URL='${CLUSTER_DEPLOYER_URL:-http://172.17.42.1:9000}'
export ENCRYPTION_PASSPHRASE='${ENCRYPTION_PASSPHRASE:-changeit}'
export ENCRYPTION_S3_BUCKET='${ENCRYPTION_S3_BUCKET:-not-set}'
export ENCRYPTION_STORE='${ENCRYPTION_PROVIDER:-s3}'
export HIPCHAT_ENABLED='${HIPCHAT_ENABLED:-false}'
export HIPCHAT_TOKEN='${HIPCHAT_TOKEN:-not-set}'
export HIPCHAT_ROOM='${HIPCHAT_ROOM:-not-set}'
END

/bin/bash -le -c " envsubst  < /etc/supervisor/conf.d/supervisord.conf.template  > /etc/supervisor/conf.d/supervisord.conf; \
                    /usr/local/bin/supervisord -c /etc/supervisor/supervisord.conf"

