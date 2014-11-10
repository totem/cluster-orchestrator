import uuid
from conf.appconfig import CLUSTER_NAME
from orchestrator.services import config


def create_job(owner, repo, ref, commit=None):
    # Step1: load the config
    paths = [CLUSTER_NAME, owner, repo, ref]
    if commit:
        paths += commit
    job_config = config.load_config(paths)

    job = {
        "git": {
            "owner": owner,
            "repo": repo,
            "ref": ref,
            "commit": commit
        },
        "config": job_config,
        "id": str(uuid.uuid4())
    }
    return job