#!/bin/bash -lex

cat <<END>> /etc/profile.d/cluster-deployer-env.sh
export ETCD_HOST='${ETCD_HOST:-172.17.42.1}'
export ETCD_PORT='${ETCD_PORT:-4001}'
export ETCD_TOTEM_BASE='${ETCD_TOTEM_BASE:-/totem}'
export ETCD_YODA_BASE='${ETCD_YODA_BASE:-/yoda}'
export API_EXECUTORS='${API_EXECUTORS:-2}'
export SSH_HOST_KEY='${SSH_HOST_KEY:-/root/.ssh/id_rsa}'
export SSH_PASSPHRASE='${SSH_PASSPHRASE}'
export GITHUB_TOKEN='${GITHUB_TOKEN}'
export ELASTICSEARCH_HOST='${ELASTICSEARCH_HOST:-172.17.42.1}'
export ELASTICSEARCH_PORT='${ELASTICSEARCH_PORT:-9200}'
export CLUSTER_NAME='${CLUSTER_NAME:-totem-local}'
export QUAY_ORGANIZATION='${QUAY_ORGANIZATION:-totem}'
export QUAY_PREFIX='${QUAY_PREFIX:-totem-}'
export SEARCH_ENABLED=true
END

/bin/bash -lex -c /usr/local/bin/supervisord

