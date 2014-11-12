import socket
import sys
from conf.appconfig import CLUSTER_NAME
from orchestrator.celery import app

if __name__ == '__main__':
    argv = list(sys.argv) if len(sys.argv) > 1 \
        else [__file__, '--loglevel=info']
    argv.append('-n orchestrator-%s@%s' % (CLUSTER_NAME, socket.gethostname()))
    app.worker_main(argv=argv)
