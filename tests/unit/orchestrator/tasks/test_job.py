from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import collections
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from mock import patch
import mock
from nose.tools import eq_, raises, assert_raises
from requests import ConnectionError
from conf.appconfig import TASK_SETTINGS, CLUSTER_NAME, JOB_STATE_SCHEDULED, \
    TOTEM_ENV, JOB_STATE_COMPLETE, JOB_STATE_NEW, CONFIG_PROVIDERS, \
    LEVEL_FAILED
from orchestrator.tasks.exceptions import HooksFailed
from orchestrator.tasks.job import _undeploy_all, _undeploy, _deploy_all, \
    _deploy, _notify_ctx, _create_job, _update_etcd_job, _job_complete, \
    _schedule_and_deploy, _template_variables, _handle_create_job, \
    _as_callback_hook, _handle_failed_hooks, _load_job_config, _release_lock, \
    _handle_job_error
from orchestrator.tasks.search import EVENT_JOB_COMPLETE, \
    EVENT_NEW_JOB, EVENT_JOB_FAILED
from orchestrator.util import dict_merge
from tests.helper import dict_compare

MOCK_OWNER = 'mock-owner'
MOCK_REPO = 'mock-repo'
MOCK_REF = 'mock-ref'
MOCK_JOB_ID = 'mock-job-id'
MOCK_COMMIT = 'mock-commit'
MOCK_OPERATION = 'mock-operation'

MOCK_HOOK_NAME = 'mock-hook'
MOCK_HOOK_TYPE = 'builder'
MOCK_HOOK_STATUS = 'success'


def test_notify_ctx():
    """
    Should return expected notification context
    """

    # When: I get notification ctx
    ctx = _notify_ctx(MOCK_OWNER, MOCK_REPO, MOCK_REF, commit=MOCK_COMMIT,
                      job_id=MOCK_JOB_ID, operation=MOCK_OPERATION)

    # Then: Expected ctx is returned
    dict_compare(ctx, {
        'owner': MOCK_OWNER,
        'repo': MOCK_REPO,
        'ref': MOCK_REF,
        'commit': MOCK_COMMIT,
        'cluster': CLUSTER_NAME,
        'env': TOTEM_ENV,
        'job-id': MOCK_JOB_ID,
        'operation': MOCK_OPERATION
    })


def test_as_callback_hook():
    """
    Should return expected callback info representation
    """

    # When: I get callback hook representation
    hook = _as_callback_hook(MOCK_HOOK_NAME, MOCK_HOOK_TYPE, MOCK_HOOK_STATUS,
                             False)

    # Then: Expected ctx is returned
    dict_compare(hook, {
        'name': MOCK_HOOK_NAME,
        'status': MOCK_HOOK_STATUS,
        'type': MOCK_HOOK_TYPE,
        'force-deploy': False
    })


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
    eq_(m_group.return_value.delay.call_count, 1)
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
@patch('orchestrator.tasks.job._job_complete')
@patch('orchestrator.tasks.job._deploy')
def test_deploy_all(m_deploy, m_job_complete, m_chord, m_group):
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
        m_group.return_value, m_job_complete.si.return_value)
    eq_(m_group.call_count, 1)
    eq_(next(m_group.call_args[0][0]), m_deploy.si.return_value)
    eq_(m_deploy.si.call_count, 1)
    dict_compare(m_deploy.si.call_args[0][0], {
        'config': job_config
    })


@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.requests')
@patch('orchestrator.tasks.job.notify')
def test_deploy(m_notify, m_requests, m_add_search_event):
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
            },
            'security': {
                'profile': 'default'
            }
        },
        'meta-info': {
            'job-id': MOCK_JOB_ID,
            'git': {
                'commit': 'mockcommit',
                'owner': 'mockowner',
                'repo': 'mockrepo',
                'ref': 'mockref'
            }
        },
    }

    # And: Mock instance for post for successful deploy
    m_requests.post.return_value.status_code = 202
    m_requests.post.return_value.headers.__getitem__.return_value = \
        'application/json'
    m_requests.post.return_value.json.return_value = {
        'task_id': 'mock-task-id'
    }

    # When: I deploy the job to a deployer with given name.
    deploy_response = _deploy(job, 'default')

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
            'security': job['config']['security'],
            'meta-info': job['meta-info'],
            'notifications': {}
        },
        'response': {
            'task_id': 'mock-task-id'
        }
    }
    dict_compare(m_add_search_event.si.call_args[1], {
        'details': expected_deploy_response,
        'search_params': {
            'meta-info': job['meta-info']
        }
    })
    dict_compare(deploy_response, expected_deploy_response)


@patch('uuid.uuid4')
def test_create_job(m_uuid4):
    # Given: Non existing job
    etcd_cl = mock.MagicMock()
    etcd_cl.read.side_effect = KeyError

    # And: Job id for new job
    m_uuid4.return_value = MOCK_JOB_ID

    # And: Mock config
    config = {
        'mockkey': 'mockvalue'
    }

    # When: I create new job
    job = _create_job(config, MOCK_OWNER, MOCK_REPO, MOCK_REF,
                      commit=MOCK_COMMIT, etcd_cl=etcd_cl, etcd_base='/mock',
                      force_deploy=True)

    # Then: Job gets created as expected
    dict_compare(job, {
        'hooks': {
            'ci': {},
            'builder': {}
        },
        'state': 'NEW',
        'config': config,
        'meta-info': {
            'git': {
                'repo': MOCK_REPO,
                'owner': MOCK_OWNER,
                'ref': MOCK_REF,
                'commit': MOCK_COMMIT
            },
            'job-id': MOCK_JOB_ID
        },
        'force-deploy': True
    })


def test_create_job_with_existing_id():
    # Given: Existing job
    etcd_cl = mock.MagicMock()
    EtcdObj = collections.namedtuple('EtcdObj', ['value'])
    etcd_cl.read.side_effect = [
        EtcdObj(value='MOCKSTATE'),
        EtcdObj(value=MOCK_JOB_ID),
    ]

    # And: Mock config
    config = {
        'mockkey': 'mockvalue'
    }

    # When: I create new job
    job = _create_job(config, MOCK_OWNER, MOCK_REPO, MOCK_REF,
                      commit=MOCK_COMMIT, etcd_cl=etcd_cl, etcd_base='/mock',
                      force_deploy=True)

    # Then: Job gets created as expected
    dict_compare(job, {
        'hooks': {
            'ci': {},
            'builder': {}
        },
        'state': 'MOCKSTATE',
        'config': config,
        'meta-info': {
            'git': {
                'repo': MOCK_REPO,
                'owner': MOCK_OWNER,
                'ref': MOCK_REF,
                'commit': MOCK_COMMIT
            },
            'job-id': MOCK_JOB_ID
        },
        'force-deploy': True
    })


def test_update_etcd_job_as_expected():
    """
    Should update etcd job as expected.
    """
    # Given: Job parameters
    job = {
        'meta-info': {
            'git': {
                'repo': MOCK_REPO,
                'owner': MOCK_OWNER,
                'ref': MOCK_REF,
                'commit': MOCK_COMMIT
            },
            'job-id': MOCK_JOB_ID
        },
        'state': JOB_STATE_SCHEDULED
    }

    # And: Mock etcd client
    etcd_cl = mock.MagicMock()
    etcd_base = '/mockbase'

    # When: I update etcd job
    ret_value = _update_etcd_job(job, etcd_cl=etcd_cl, etcd_base=etcd_base)

    # Then: Job state and id gets updated
    etcd_cl.write.assert_called_twice()
    etcd_cl.write.assert_any_call(
        '/mockbase/orchestrator/jobs/local/mock-owner/mock-repo/mock-ref/'
        'mock-commit/job-id', MOCK_JOB_ID)
    etcd_cl.write.assert_any_call(
        '/mockbase/orchestrator/jobs/local/mock-owner/mock-repo/mock-ref/'
        'mock-commit/state', JOB_STATE_SCHEDULED)
    dict_compare(ret_value, job)


@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.update_job_state')
def test_job_complete(m_update_job_state, m_add_search_event):
    """
    Should mark job state to complete
    """

    # Given: Job parameters
    job = {
        'meta-info': {
            'job-id': MOCK_JOB_ID
        },
        'state': JOB_STATE_SCHEDULED
    }

    # When: I mark the job as completed
    ret_value = _job_complete(job)

    # Then: Job is marked completed
    expected_job = dict_merge({'state': JOB_STATE_COMPLETE}, job)
    eq_(ret_value, m_update_job_state.si.return_value.__or__.return_value
        .delay.return_value)
    m_update_job_state.si.assert_called_once_with(MOCK_JOB_ID,
                                                  JOB_STATE_COMPLETE)
    m_add_search_event.si.assert_called_once_with(
        EVENT_JOB_COMPLETE,
        search_params={'meta-info': job['meta-info']},
        ret_value=expected_job)


@patch('orchestrator.tasks.job.update_job_state')
@patch('orchestrator.tasks.job._update_etcd_job')
@patch('orchestrator.tasks.job._update_hook_status')
@patch('orchestrator.tasks.job.index_job')
@patch('orchestrator.tasks.job._check_and_fire_deploy')
def test_schedule_and_deploy_job(
        m_check_and_fire_deploy, m_index_job, m_update_hook_status,
        m_update_etcd_job, m_update_job_state):
    """
    Should schedule the job for deploy
    """

    # Given: Job parameters
    job = {
        'meta-info': {
            'job-id': MOCK_JOB_ID
        }
    }

    # When: I schedule and deploy the given job
    ret_value = _schedule_and_deploy(job, 'builder', 'mock')

    # Then: Job is scheduled for deploy
    expected_job = dict_merge({'state': JOB_STATE_SCHEDULED}, job)
    expected_ret = m_update_job_state.si.return_value
    for cnt in range(3):
        expected_ret = expected_ret.__or__.return_value
    expected_ret = expected_ret.delay.return_value

    eq_(ret_value, expected_ret)
    m_update_job_state.si.assert_called_once_with(MOCK_JOB_ID,
                                                  JOB_STATE_SCHEDULED)
    m_update_etcd_job.si.assert_called_once_with(expected_job)
    m_update_hook_status.s.assert_called_once_with(
        'builder', 'mock', hook_status='success', hook_result=None)
    m_check_and_fire_deploy.s.assert_called_once_with()


def test_template_variables():
    """
    Should return default template variables for job config
    """

    # When: I get template variables for given repository
    # owner, repo, ref and commit
    vars = _template_variables(
        MOCK_OWNER, MOCK_REPO, 'feature_test', MOCK_COMMIT)

    # Then: Default variables for the config template are returned
    dict_compare(vars, {
        'owner': MOCK_OWNER,
        'repo': MOCK_REPO,
        'ref': 'feature_test',
        'commit': MOCK_COMMIT,
        'ref_number': 'test',
        'cluster': CLUSTER_NAME,
        'env': TOTEM_ENV
    })


@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.index_job')
def test_handle_create_job(m_index_job, m_add_search_event):
    """
    Should index job newly added job
    """

    # Given: Existing job
    job = {
        'meta-info': {
            'job-id': MOCK_JOB_ID
        },
        'state': JOB_STATE_NEW
    }

    # When: I handle create job
    _handle_create_job(job)

    # Then: Job gets indexed
    m_index_job.si.assert_called_once_with(job)
    m_add_search_event.si.assert_called_once_with(
        EVENT_NEW_JOB, details=job,
        search_params={'meta-info': job['meta-info']})


@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.index_job')
def test_handle_create_for_existing_job(m_index_job, m_add_search_event):
    """
    Should not index existing job
    """

    # Given: Existing job
    job = {
        'meta-info': {
            'job-id': MOCK_JOB_ID
        },
        'state': JOB_STATE_SCHEDULED
    }

    # When: I handle create job
    _handle_create_job(job)

    # Then: Job gets indexed
    eq_(m_index_job.si.call_count, 0)
    eq_(m_add_search_event.si.call_count, 0)


@raises(HooksFailed)
def test_handle_failed_hooks():
    """
    Should raise HooksFailed exception
    """

    # When: I handle failed hooks
    _handle_failed_hooks([])

    # Then: HooksFailed exception is raised


@patch('orchestrator.tasks.job.config.load_config')
def test_load_job_config(m_load_config):
    """
    Should load job config successfully.
    """

    # When: I load job config for given git parameters
    ret_value = _load_job_config(
        MOCK_OWNER, MOCK_REPO, MOCK_REF, {}, {}, commit=MOCK_COMMIT)

    # Then: Config is loaded as expected
    eq_(ret_value, m_load_config.return_value)
    m_load_config.assert_called_once_with(
        TOTEM_ENV, MOCK_OWNER, MOCK_REPO, MOCK_REF,
        default_variables={
            'ref_number': MOCK_REF,
            'repo': MOCK_REPO,
            'cluster': CLUSTER_NAME,
            'env': TOTEM_ENV,
            'owner': MOCK_OWNER,
            'commit': MOCK_COMMIT,
            'ref': MOCK_REF
        })


@patch('orchestrator.tasks.job._handle_job_error')
@patch('orchestrator.tasks.job.config.load_config')
def test_load_job_config_when_failed(m_load_config, m_handle_job_error):
    """
    Should handle failure when config fails to load
    """

    # Given: Invalid config
    error = RuntimeError('MockError')
    m_load_config.side_effect = error

    with assert_raises(RuntimeError) as raise_ctx:
        # When: I load job config for given git parameters
        _load_job_config(
            MOCK_OWNER, MOCK_REPO, MOCK_REF, {}, {}, commit=MOCK_COMMIT)

    # Then: Config fails to get loaded
    eq_(raise_ctx.exception, error)
    m_handle_job_error.si.assert_called_once_with(
        raise_ctx.exception, CONFIG_PROVIDERS['default']['config'], {}, {})
    m_handle_job_error.si.return_value.delay.assert_called_once_with()


@patch('orchestrator.tasks.job.LockService')
def test_release_lock(m_lock_service):
    """
    Should release the existing lock
    """

    # Given: Existing lock
    lock = mock.MagicMock()

    # When: I release the given lock
    _release_lock(lock)

    # Then: Lock gets released successfully
    m_lock_service.return_value.release.assert_called_once_with(lock)


@patch('orchestrator.tasks.job.group')
@patch('orchestrator.tasks.job.notify')
@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.update_job_state')
def test_handle_job_error_with_job_id(m_update_job_state, m_add_search_event,
                                      m_notify, m_group):
    """
    Should handle job error when job_id is given
    """
    # Given: Mock Error
    error = {
        'message': 'MockError'
    }

    # And: Mock Job Config
    job_config = {
        'notifications': {
            'github': {}
        },
        'security': {
            'profile': 'mockprofile'
        }
    }

    # And: Mock Notification Context
    notify_ctx = mock.MagicMock()

    # And: Mock Search Parameters
    search_params = mock.MagicMock()

    # When: I handle job error for given job_id
    ret_value = _handle_job_error(
        error, job_config, notify_ctx, search_params, job_id=MOCK_JOB_ID)

    # Then: Error is handled as expected
    eq_(ret_value, m_group.return_value.delay.return_value)
    m_group.assert_called_once_with([
        m_notify.s.return_value,
        m_add_search_event.si.return_value,
        m_update_job_state.si.return_value
    ])
    m_notify.s.assert_called_once_with(
        ctx=notify_ctx, level=LEVEL_FAILED,
        notifications=job_config['notifications'],
        security_profile=job_config['security']['profile'])
    m_add_search_event.si.assert_called_once_with(
        EVENT_JOB_FAILED, details={'job-error': error},
        search_params=search_params
    )


@patch('orchestrator.tasks.job.group')
@patch('orchestrator.tasks.job.notify')
@patch('orchestrator.tasks.job.add_search_event')
@patch('orchestrator.tasks.job.update_job_state')
def test_handle_job_error_without_job_id(
        m_update_job_state, m_add_search_event, m_notify, m_group):
    """
    Should handle job error when job_id is not provided
    """
    # Given: Mock Error
    error = {
        'message': 'MockError'
    }

    # And: Mock Job Config
    job_config = {
        'notifications': {
            'github': {}
        },
        'security': {
            'profile': 'mockprofile'
        }
    }

    # When: I handle job error for given job_id
    _handle_job_error(
        error, job_config, {}, {}, job_id=None)

    # Then: Job state is not updated
    eq_(m_update_job_state.si.call_count, 0)
