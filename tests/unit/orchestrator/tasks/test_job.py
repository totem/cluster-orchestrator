from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from mock import patch
from nose.tools import eq_, raises
from requests import ConnectionError
from conf.appconfig import TASK_SETTINGS
from orchestrator.tasks.job import _undeploy_all, _undeploy, _deploy_all, \
    _deploy
from tests.helper import dict_compare

MOCK_OWNER = 'mock-owner'
MOCK_REPO = 'mock-repo'
MOCK_REF = 'mock-ref'
MOCK_JOB_ID = 'moc-job-id'


@patch('orchestrator.tasks.job.group')
def test_undeploy_all(m_group):
    """
    Should delete from all enabled deployers.
    """

    # Given: Job config for a job that needs to be undeployed
    job_config = {
        'deployers': {
            'deployer1': {
                'enabled': True,
                'url': 'http://deployer1'
            },
            'deployer2': {
                'enabled': False,
                'url': 'http://deployer2'
            },
            'deployer3': {
                'url': 'http://deployer3'
            },
            'deployer4': {
                'enabled': True,
            }
        }
    }

    # When: I undeploy all deployments for given job
    _undeploy_all(job_config, MOCK_OWNER, MOCK_REPO, MOCK_REF)

    # Then: Deployments get decommissioned
    eq_(m_group.call_count, 1)
    eq_(m_group.return_value.call_count, 1)
    eq_(next(m_group.call_args[0][0]),
        _undeploy.si(job_config, MOCK_OWNER, MOCK_REPO, MOCK_REF, 'deployer1'))


@patch('requests.delete')
def test_undeploy(m_delete):
    """
    Should undeploy job with given deployer name.
    """

    # Given: Job config for a job that needs to be undeployed
    job_config = {
        'deployers': {
            'deployer1': {
                'enabled': True,
                'url': 'http://deployer1'
            },
        }
    }

    # When: I undeploy deployments for given job and deployer
    _undeploy(job_config, MOCK_OWNER, MOCK_REPO, MOCK_REF, 'deployer1')

    # Then: Deployment is deleted as expected
    m_delete.assert_called_once_with(
        'http://deployer1/apps/mock-owner-mock-repo-mock-ref')


@raises(ConnectionError)
@patch('requests.delete')
def test_undeploy_with_retry(m_delete):
    """
    Should retry undeploy if delete fails due to connection error
    """

    # Given: Job config for a job that needs to be undeployed
    job_config = {
        'deployers': {
            'deployer1': {
                'enabled': True,
                'url': 'http://deployer1'
            },
        }
    }

    # And: Connection error during delete
    m_delete.side_effect = ConnectionError('Mock. Please ignore'), None

    # When: I undeploy deployments for given job and deployer
    _undeploy(job_config, MOCK_OWNER, MOCK_REPO, MOCK_REF, 'deployer1')

    # Then: ConnectionError is re-thrown
    # Not the best way to test this


@patch('orchestrator.tasks.job.group')
@patch('orchestrator.tasks.job.chord')
@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job._deploy')
def test_deploy_all(m_deploy, m_add_search_event, m_chord, m_group):
    """
    Should deploy to  all enabled deployers.
    """

    # Given: Job config for a job that needs to be deployed
    job_config = {
        'deployers': {
            'deployer1': {
                'enabled': True,
                'url': 'http://deployer1'
            },
            'deployer2': {
                'enabled': False,
                'url': 'http://deployer2'
            },
            'deployer3': {
                'url': 'http://deployer3'
            },
            'deployer4': {
                'enabled': True,
            }
        }
    }

    # And: Instance of job
    job = {
        'config': job_config
    }

    # When: I undeploy all deployments for given job
    _deploy_all(job)

    # Then: Deployments get decommissioned
    eq_(m_chord.call_count, 1)
    m_chord.return_value.apply_async.assert_called_once_with(
        interval=TASK_SETTINGS['DEPLOY_WAIT_RETRY_DELAY'])
    m_chord.assert_called_once_with(
        m_group.return_value, m_add_search_event.si.return_value)
    eq_(m_group.call_count, 1)
    eq_(next(m_group.call_args[0][0]), m_deploy.si.return_value)
    eq_(m_deploy.si.call_count, 1)
    dict_compare(m_deploy.si.call_args[0][0], {
        'config': job_config,
        'state': 'DEPLOY_REQUESTED'
    })


@patch('orchestrator.tasks.job._check_deploy_failed')
@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.requests')
def test_deploy(m_requests, m_add_search_event, m_check_deploy_failed):
    """
    Should successfully request deployment to cluster deployer.
    """
    # Given: Instance of job
    job = {
        'config': {
            'deployers': {
                'default': {
                    'enabled': True,
                    'proxy': {},
                    'templates': {},
                    'deployment': {},
                    'url': 'http://mockurl'
                }
            }
        },
        'meta-info': {
            'job-id': MOCK_JOB_ID
        },
    }

    # And: Mock instance for post for successful deploy
    m_requests.post.return_value.status_code = 202
    m_requests.post.return_value.json.return_value = {
        'task_id': 'mock-task-id'
    }

    # When: I deploy the job to a deployer with given name.
    _deploy(job, 'default')

    # Then: Job gets deployed successfully
    eq_(m_add_search_event.si.call_count, 1)
    eq_(m_add_search_event.si.call_args[0][0], 'DEPLOY_REQUESTED')
    expected_deploy_response = {
        'name': 'default',
        'url': 'http://mockurl/apps',
        'status': 202,
        'request': {
            'proxy': {},
            'templates': {},
            'deployment': {},
            'security': {},
            'meta-info': {
                'job-id': MOCK_JOB_ID
            }
        },
        'response': {
            'task_id': 'mock-task-id'
        }
    }
    dict_compare(m_add_search_event.si.call_args[1], {
        'details': expected_deploy_response,
        'search_params': {
            'meta-info': {
                'job-id': MOCK_JOB_ID
            }
        }
    })
    dict_compare(m_check_deploy_failed.si.call_args[0][0],
                 expected_deploy_response)
