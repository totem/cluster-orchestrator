#!/bin/sh -e

HOST_IP="${HOST_IP:-$(/sbin/ip route|awk '/default/ { print $3 }')}"

export ETCD_HOST="${ETCD_HOST:-$HOST_IP}"
export ETCD_PORT="${ETCD_PORT:-4001}"
export ETCD_TOTEM_BASE="${ETCD_TOTEM_BASE:-/totem}"
export ETCD_YODA_BASE="${ETCD_YODA_BASE:-/yoda}"
export CELERY_GEVENT_EXECUTORS="${CELERY_GEVENT_EXECUTORS:-1}"
export CELERY_GEVENT_CONCURRENCY="${CELERY_GEVENT_CONCURRENCY:-50}"
export API_EXECUTORS="${API_EXECUTORS:-2}"
export GITHUB_TOKEN="${GITHUB_TOKEN}"
export CLUSTER_NAME="${CLUSTER_NAME:-local}"
export TOTEM_ENV="${TOTEM_ENV:-local}"
export QUAY_ORGANIZATION="${QUAY_ORGANIZATION:-totem}"
export QUAY_PREFIX="${QUAY_PREFIX:-totem-}"
export C_FORCE_ROOT=true
export AMQP_HOST="${AMQP_HOST:-$HOST_IP}"
export AMQP_PORT="${AMQP_PORT:-5672}"
export AMQP_USERNAME="${AMQP_USERNAME:-guest}"
export AMQP_PASSWORD="${AMQP_PASSWORD:-guest}"
export MONGODB_USERNAME="${MONGODB_USERNAME:-}"
export MONGODB_PASSWORD="${MONGODB_PASSWORD:-}"
export MONGODB_HOST="${MONGODB_HOST:-$HOST_IP}"
export MONGODB_PORT="${MONGODB_PORT:-27017}"
export MONGODB_DB="${MONGODB_DB}"
export MONGODB_AUTH_DB="${MONGODB_AUTH_DB}"
export BROKER_URL="${BROKER_URL}"
export CLUSTER_DEPLOYER_URL="${CLUSTER_DEPLOYER_URL:-http://$HOST_IP:9000}"
export ENCRYPTION_PASSPHRASE="${ENCRYPTION_PASSPHRASE:-changeit}"
export ENCRYPTION_S3_BUCKET="${ENCRYPTION_S3_BUCKET:-not-set}"
export ENCRYPTION_STORE="${ENCRYPTION_PROVIDER:-s3}"
export HIPCHAT_ENABLED="${HIPCHAT_ENABLED:-false}"
export HIPCHAT_TOKEN="${HIPCHAT_TOKEN}"
export HIPCHAT_ROOM="${HIPCHAT_ROOM:-not-set}"
export GITHUB_NOTIFICATION_ENABLED="${GITHUB_NOTIFICATION_ENABLED:-false}"
export LOG_IDENTIFIER="${LOG_IDENTIFIER:-cluster-orchestrator}"
export LOG_ROOT_LEVEL="${LOG_ROOT_LEVEL}"

envsubst  < /etc/supervisor/conf.d/supervisord.conf.template  > /etc/supervisor/conf.d/supervisord.conf

/usr/local/bin/supervisord -c /etc/supervisor/supervisord.conf

