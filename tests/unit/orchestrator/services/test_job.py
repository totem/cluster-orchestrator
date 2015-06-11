"""
Tests for job service
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from celery.tests.case import patch
from nose.tools import eq_
from orchestrator.services import job
from orchestrator.services.job import DEFAULT_FREEZE_TTL_SECONDS

__author__ = 'sukrit'

MOCK_OWNER = 'mock-owner'
MOCK_REPO = 'mock-repo'
MOCK_REF = 'mock-ref'


def test_app_jobs_base():
    """
    Should return application jobs base location for given set of inputs
    """

    # When: I get the base location for all the jobs for a given application
    location = job._app_jobs_base(MOCK_OWNER, MOCK_REPO, MOCK_REF,
                                  '/mock-etcd')

    # Then: Expected location is returned
    eq_(location, '/mock-etcd/orchestrator/jobs/local/mock-owner/mock-repo/'
                  'mock-ref')


@patch('etcd.Client')
def test_update_freeze_status(m_etcd_cl):
    """
    Should update the freeze status for a given application
    """

    # When: I update the freeze status for given application
    job.update_freeze_status(MOCK_OWNER, MOCK_REPO, MOCK_REF, freeze=False)

    # Then: Status gets updated as expected
    m_etcd_cl.return_value.write.assert_called_once_with(
        '/totem/orchestrator/jobs/local/mock-owner/mock-repo/mock-ref/frozen',
        False, ttl=DEFAULT_FREEZE_TTL_SECONDS
    )


@patch('etcd.Client')
def test_is_frozen(m_etcd_cl):
    """
    Should return the frozen status of a given application
    """

    # Given: Application with existing frozen status
    m_etcd_cl.return_value.read.return_value.value = 'true'

    # When: I get the freeze status for existing application
    frozen = job.is_frozen(MOCK_OWNER, MOCK_REPO, MOCK_REF)

    # Then: Frozen status is returned
    eq_(frozen, True)
