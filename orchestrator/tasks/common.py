from orchestrator.celery import app


@app.task
def ping():
    return 'pong'
