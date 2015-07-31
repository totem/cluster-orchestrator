FROM totem/python-base:2.7-trusty-b3

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update --fix-missing && apt-get install -y \
    gettext \
    libyaml-dev

#Etcdctl
ENV ETCDCTL_VERSION v0.4.6
RUN curl -L https://github.com/coreos/etcd/releases/download/$ETCDCTL_VERSION/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz -o /tmp/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz && \
    cd /tmp && gzip -dc etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz | tar -xof - && \
    cp -f /tmp/etcd-$ETCDCTL_VERSION-linux-amd64/etcdctl /usr/local/bin && \
    rm -rf /tmp/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz && \
    rm -rf /tmp/etcd-$ETCDCTL_VERSION-linux-amd64

# Supervisor and App dependencies
RUN pip install supervisor==3.1.2 supervisor-stdout
ADD requirements.txt /opt/requirements.txt
RUN pip install -r /opt/requirements.txt

#Supervisor Config
RUN mkdir -p /var/log/supervisor
ADD bin/supervisord-wrapper.sh /usr/sbin/supervisord-wrapper.sh
RUN chmod +x /usr/sbin/supervisord-wrapper.sh && \
    ln -sf /etc/supervisor/supervisord.conf /etc/supervisord.conf

#Etc Config
ADD etc /etc

ADD . /opt/cluster-orchestrator
RUN pip install -r /opt/cluster-orchestrator/requirements.txt

EXPOSE 9400

WORKDIR /opt/cluster-orchestrator

ENTRYPOINT ["/usr/sbin/supervisord-wrapper.sh"]