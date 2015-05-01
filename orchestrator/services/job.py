"""
Services related to job in orchestrator.
All services defined here are synchronous in nature
"""

import etcd
from conf.appconfig import TOTEM_ENV, BOOLEAN_TRUE_VALUES
from orchestrator.etcd import using_etcd

__author__ = 'sukrit'

DEFAULT_FREEZE_TTL_SECONDS = 86400


def _app_jobs_base(owner, repo, ref, etcd_base):
    """
    Gets the base location for all jobs for a given application

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :param etcd_base:
    :return:
    """
    return '%s/orchestrator/jobs/%s/%s/%s/%s/%s' % \
           (etcd_base, TOTEM_ENV, owner, repo, ref)


@using_etcd
def update_freeze_status(
        owner, repo, ref, freeze=True, ttl=DEFAULT_FREEZE_TTL_SECONDS,
        etcd_cl=None, etcd_base=None):
    """
    Freezes/Unfreezes all jobs for application identified by
    SCM Repository owner, name and ref for certain time.
    During freeze, no jobs will be executed

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :keyword freeze: Should application be frozen for further deploys ?
    :type freeze: bool
    :keyword ttl: Time to live for application freeze (defined in seconds)
    :type ttl: int
    :keyword etcd_cl: Etcd client
    :type etcd_cl: etcd.Client
    :keyword etcd_base: Etcd base
    :type etcd_base: str
    :return: None
    """
    app_base = _app_jobs_base(owner, repo, ref, etcd_base)
    etcd_cl.write(app_base + '/frozen', freeze, ttl=ttl)


@using_etcd
def is_frozen(owner, repo, ref, etcd_cl=None, etcd_base=None):
    """
    Freezes all jobs for application identified by SCM Repository owner,
    name and ref for certain time. During freeze, no jobs will be executed

    :param owner: SCM Repository owner
    :type owner: str
    :param repo: SCM Repository name
    :type repo: str
    :param ref: SCM Repository Ref (tag or branch)
    :type ref: str
    :keyword ttl: Time to live for application freeze (defined in seconds)
    :type ttl: int
    :keyword etcd_cl: Etcd client
    :type etcd_cl: etcd.Client
    :keyword etcd_base: Etcd base
    :type etcd_base: str
    :return: None
    """
    app_base = _app_jobs_base(owner, repo, ref, etcd_base)
    try:
        return etcd_cl.read(app_base + '/frozen').value in BOOLEAN_TRUE_VALUES
    except KeyError:
        # Key is not found. Application is not frozen
        return False