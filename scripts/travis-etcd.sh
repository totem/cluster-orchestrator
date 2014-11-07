#!/bin/bash -ex
curl -L  https://github.com/coreos/etcd/releases/download/v0.4.6/etcd-v0.4.6-linux-amd64.tar.gz -o etcd-v0.4.6-linux-amd64.tar.gz
tar xzvf etcd-v0.4.6-linux-amd64.tar.gz
cd etcd-v0.4.6-linux-amd64
./etcd &