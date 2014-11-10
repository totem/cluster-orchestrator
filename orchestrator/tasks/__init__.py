from orchestrator.celery import app

__author__ = 'sukrit'


@app.task
def backend_cleanup():
    app.tasks['celery.backend_cleanup']()
