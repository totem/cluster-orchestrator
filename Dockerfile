FROM totem/python-base:2.7-trusty

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update --fix-missing && apt-get install -y \
    openssh-server \
    openssh-client \
    libffi-dev \
    gettext \
    libyaml-dev \
    nano

##SSH Server (To troubleshoot issues with discover)
RUN mkdir /var/run/sshd && \
    mkdir /root/.ssh && \
    chmod  500 /root/.ssh && \
    chown -R root:root /root/.ssh

#Syslog
RUN echo '$PreserveFQDN on' | cat - /etc/rsyslog.conf > /tmp/rsyslog.conf && \
    sudo mv /tmp/rsyslog.conf /etc/rsyslog.conf && \
    sed -i 's~^#\$ModLoad immark\(.*\)$~$ModLoad immark \1~' /etc/rsyslog.conf

#Confd
ENV CONFD_VERSION 0.6.2
RUN curl -L https://github.com/kelseyhightower/confd/releases/download/v$CONFD_VERSION/confd-${CONFD_VERSION}-linux-amd64 -o /usr/local/bin/confd && \
    chmod 555 /usr/local/bin/confd

#Etcdctl
ENV ETCDCTL_VERSION v0.4.6
RUN curl -L https://github.com/coreos/etcd/releases/download/$ETCDCTL_VERSION/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz -o /tmp/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz && \
    cd /tmp && gzip -dc etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz | tar -xof - && \
    cp -f /tmp/etcd-$ETCDCTL_VERSION-linux-amd64/etcdctl /usr/local/bin && \
    rm -rf /tmp/etcd-$ETCDCTL_VERSION-linux-amd64.tar.gz

# Supervisor and App dependencies
RUN pip install supervisor==3.1.2
ADD requirements.txt /opt/requirements.txt
RUN pip install -r /opt/requirements.txt

#Supervisor Config
RUN mkdir -p /var/log/supervisor
ADD bin/supervisord-wrapper.sh /usr/sbin/supervisord-wrapper.sh
RUN chmod +x /usr/sbin/supervisord-wrapper.sh && \
    ln -sf /etc/supervisor/supervisord.conf /etc/supervisord.conf

#Confd Defaults
ADD bin/confd-wrapper.sh /usr/sbin/confd-wrapper.sh
RUN chmod +x /usr/sbin/confd-wrapper.sh

#SSH Keys
ADD bin/decrypt-ssh-keys.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/decrypt-ssh-keys.sh

#Etc Config
ADD etc /etc

ADD . /opt/cluster-orchestrator
RUN pip install -r /opt/cluster-orchestrator/requirements.txt

EXPOSE 9400 22

WORKDIR /opt/cluster-orchestrator

ENTRYPOINT ["/usr/sbin/supervisord-wrapper.sh"]