import sys
from orchestrator.celery import app

if __name__ == '__main__':
    argv = sys.argv if len(sys.argv) > 1 else [__file__, '--loglevel=info']
    app.worker_main(argv=argv)
