"""
Tests for job service
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import etcd
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
from celery.tests.case import patch
from nose.tools import eq_
from conf.appconfig import CLUSTER_NAME, TOTEM_ENV, \
    JOB_STATE_SCHEDULED, HOOK_STATUS_SUCCESS, HOOK_STATUS_PENDING, \
    HOOK_TYPE_BUILDER, HOOK_STATUS_FAILED
from orchestrator.services import job
from orchestrator.services.job import DEFAULT_FREEZE_TTL_SECONDS, \
    as_notify_ctx, as_callback_hook, create_job, get_template_variables, \
    create_search_parameters, get_build_image, prepare_job, check_ready
from orchestrator.services.storage.base import EVENT_NEW_JOB
from orchestrator.util import dict_merge
from tests.helper import dict_compare

__author__ = 'sukrit'

MOCK_OWNER = 'mock-owner'
MOCK_REPO = 'mock-repo'
MOCK_REF = 'mock-ref'
MOCK_JOB_ID = 'mock-job-id'
MOCK_COMMIT = 'mock-commit'
MOCK_COMMIT_NEW = 'mock-commit-new'
MOCK_OPERATION = 'mock-operation'

MOCK_HOOK_NAME = 'mock-hook'
MOCK_HOOK_TYPE = 'builder'
MOCK_HOOK_STATUS = HOOK_STATUS_SUCCESS

MOCK_EXISTING_JOB = {
    'hooks': {
        'ci': {
            'ci1': {
                'status': HOOK_STATUS_SUCCESS
            }
        },
        'builder': {
            'image-factory': {
                'status': HOOK_STATUS_PENDING
            }
        },
        'scm-push': {}
    },
    'state': 'NEW',
    'config': {
        'hooks': {
            'ci': {
                'ci1': {
                    'enabled': True
                }
            },
            'builder': {
                'image-factory': {
                    'enabled': True
                }
            }
        },
        'deployers': {
            'default': {
                'templates': {
                    'app': {
                        'args': {}
                    }
                }
            }
        }
    },
    'meta-info': {
        'git': {
            'repo': MOCK_REPO,
            'owner': MOCK_OWNER,
            'ref': MOCK_REF,
            'commit': MOCK_COMMIT,
            'commit-set': [MOCK_COMMIT]
        },
        'job-id': MOCK_JOB_ID
    }
}


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


@patch('etcd.Client')
def test_is_frozen_for_non_existing_key(m_etcd_cl):
    """
    Should return the frozen status of a given application
    """

    # Given: Application with existing frozen status
    m_etcd_cl.return_value.read.side_effect = etcd.EtcdKeyNotFound

    # When: I get the freeze status for existing application
    frozen = job.is_frozen(MOCK_OWNER, MOCK_REPO, MOCK_REF)

    # Then: Frozen status is returned
    eq_(frozen, False)


def test_notify_ctx():
    """
    Should return expected notification context
    """

    # When: I get notification ctx
    ctx = as_notify_ctx(MOCK_OWNER, MOCK_REPO, MOCK_REF, commit=MOCK_COMMIT,
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
    hook = as_callback_hook(MOCK_HOOK_NAME, MOCK_HOOK_TYPE, MOCK_HOOK_STATUS,
                            False)

    # Then: Expected ctx is returned
    dict_compare(hook, {
        'name': MOCK_HOOK_NAME,
        'status': MOCK_HOOK_STATUS,
        'type': MOCK_HOOK_TYPE,
        'force-deploy': False
    })


@patch('uuid.uuid4')
@patch('orchestrator.services.job.get_store')
def test_create_job(m_get_store, m_uuid4):
    # Given: Non existing job

    # And: Job id for new job
    m_uuid4.return_value = MOCK_JOB_ID

    # And: Non existing job
    m_get_store.return_value.filter_jobs.return_value = []

    # And: Mock config
    config = MOCK_EXISTING_JOB['config']

    # When: I create new job
    job = create_job(config, MOCK_OWNER, MOCK_REPO, MOCK_REF,
                     commit=MOCK_COMMIT, force_deploy=True)

    # Then: Job gets created as expected
    expected_job = dict_merge({
        'hooks': {
            'ci': {
                'ci1': {
                    'status': HOOK_STATUS_PENDING
                }
            },
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_PENDING
                }
            }
        },
        'force-deploy': True
    }, MOCK_EXISTING_JOB)
    dict_compare(job, expected_job)

    m_get_store.return_value.add_event.assert_called_once_with(
        EVENT_NEW_JOB,
        search_params={u'meta-info': {'job-id': MOCK_JOB_ID}},
        details=expected_job)


@patch('orchestrator.services.job.get_store')
def test_create_job_when_exists(m_get_store):
    # Given: Existing job
    existing_job = MOCK_EXISTING_JOB
    m_get_store.return_value.filter_jobs.return_value = [existing_job]

    # When: I create new job
    job = create_job(existing_job['config'], MOCK_OWNER, MOCK_REPO, MOCK_REF,
                     commit=MOCK_COMMIT_NEW)

    # Then: Job gets created as expected
    expected_job = dict_merge({
        'meta-info': {
            'git': {
                'commit': MOCK_COMMIT_NEW
            }
        },
        'hooks': {
            'ci': {
                'ci1': {
                    'status': HOOK_STATUS_PENDING
                }
            },
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_PENDING
                }
            }
        }
    }, existing_job)
    dict_compare(job, expected_job)

    m_get_store.return_value.add_event.assert_not_called()
    m_get_store.return_value.update_job.assert_called_once_with(expected_job)


@patch('orchestrator.services.job.get_store')
def test_create_job_when_exists_with_superseded_commit(m_get_store):
    # Given: Existing job with superseded commit
    existing_job = dict_merge({
        'meta-info': {
            'git': {
                'commit-set': [MOCK_COMMIT_NEW, MOCK_COMMIT]
            }
        }
    }, MOCK_EXISTING_JOB)
    m_get_store.return_value.filter_jobs.return_value = [existing_job]

    # When: I create new job
    job = create_job(existing_job['config'], MOCK_OWNER, MOCK_REPO, MOCK_REF,
                     commit=MOCK_COMMIT_NEW)

    # Then: Job gets created as expected
    expected_job = existing_job
    dict_compare(job, expected_job)

    m_get_store.return_value.add_event.assert_not_called()
    m_get_store.return_value.update_job.assert_not_called()


@patch('orchestrator.services.job.get_store')
def test_create_job_when_exists_with_no_commit_info(m_get_store):
    # Given: Existing job
    existing_job = MOCK_EXISTING_JOB
    m_get_store.return_value.filter_jobs.return_value = [existing_job]

    # When: I create new job with empty commit
    job = create_job(existing_job['config'], MOCK_OWNER, MOCK_REPO, MOCK_REF,
                     commit=None)

    # Then: Job gets created as expected
    expected_job = dict_merge({
        'hooks': {
            'ci': {
                'ci1': {
                    'status': HOOK_STATUS_PENDING
                }
            },
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_PENDING
                }
            }
        }
    }, existing_job)
    dict_compare(job, expected_job)

    m_get_store.return_value.add_event.assert_not_called()
    m_get_store.return_value.update_job.assert_not_called()


def test_template_variables():
    """
    Should return default template variables for job config
    """

    # When: I get template variables for given repository
    # owner, repo, ref and commit
    variables = get_template_variables(
        MOCK_OWNER, MOCK_REPO, 'feature_test', MOCK_COMMIT)

    # Then: Default variables for the config template are returned
    dict_compare(variables, {
        'owner': MOCK_OWNER,
        'repo': MOCK_REPO,
        'ref': 'feature_test',
        'commit': MOCK_COMMIT,
        'ref_number': 'test',
        'cluster': CLUSTER_NAME,
        'env': TOTEM_ENV
    })


def test_create_search_params():
    """
    Should return search parameters for given job
    :return:
    """

    params = create_search_parameters(MOCK_EXISTING_JOB, defaults={
        'meta-info': {
            'custom-key': 'custom-val'
        }
    })

    # Then: Search params are expected as expected
    dict_compare(params, {
        'meta-info': {
            'custom-key': 'custom-val',
            'git': MOCK_EXISTING_JOB['meta-info']['git'],
            'job-id': MOCK_JOB_ID
        }
    })


def test_get_build_image_for_non_builder_hook():

    # When: I get build image for non builder hook
    image = get_build_image('mock-hook', 'ci', HOOK_STATUS_SUCCESS, {})
    # Then: No image is returned
    eq_(image, None)


def test_get_build_image_for_failed_hook():

    # When: I get build image for failed builder hook
    image = get_build_image('mock-hook', 'builder', 'failed', {})

    # Then: No image is returned
    eq_(image, None)


def test_get_build_image_for_success_hook():

    # When: I get build image for builder hook
    image = get_build_image('mock-hook', 'builder', HOOK_STATUS_SUCCESS, {
        'image': 'mock-image'
    })

    # Then: Expected image is returned
    eq_(image, 'mock-image')


def test_get_build_image_for_quay_success_hook():

    # When: I get build image for builder hook
    image = get_build_image('quay', 'builder', HOOK_STATUS_SUCCESS, {
        'docker_url': 'quay.io/mockowner/mockrepo',
        'docker_tags': ['latest', 'develop']
    })

    # Then: Expected image is returned
    eq_(image, 'quay.io/mockowner/mockrepo:latest')


def test_get_build_image_for_quay_success_hook_without_tags():

    # When: I get build image for builder hook
    image = get_build_image('quay', 'builder', HOOK_STATUS_SUCCESS, {
        'docker_url': 'quay.io/mockowner/mockrepo',
    })

    # Then: Expected image is returned
    eq_(image, 'quay.io/mockowner/mockrepo')


@patch('orchestrator.services.job.get_store')
def test_prepare_job(m_get_store):

    # Given: Existing job
    existing_job = MOCK_EXISTING_JOB

    # When: I prepare existing job
    job = prepare_job(
        existing_job, HOOK_TYPE_BUILDER, 'image-factory',
        hook_status=HOOK_STATUS_SUCCESS,
        hook_result={
            'image': 'mock-image'
        })

    # Then: Job state and hook info gets updated as expected
    expected_job = dict_merge({
        'state': JOB_STATE_SCHEDULED,
        'hooks': {
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_SUCCESS
                }
            }
        },
        'config': {
            'deployers': {
                'default': {
                    'templates': {
                        'app': {
                            'args': {
                                'image': 'mock-image'
                            }
                        }
                    }
                }
            }
        }

    }, existing_job)

    dict_compare(job, expected_job)
    m_get_store.return_value.update_job.assert_called_once_with(expected_job)


@patch('orchestrator.services.job.get_store')
def test_prepare_job_for_non_configured_hook(m_get_store):

    # Given: Existing job
    existing_job = MOCK_EXISTING_JOB

    # When: I prepare existing job with non configured hook
    job = prepare_job(
        existing_job, HOOK_TYPE_BUILDER, 'fake-builder',
        hook_status=HOOK_STATUS_SUCCESS,
        hook_result={
            'image': 'mock-image'
        })

    # Then: Job state and hook info gets updated as expected
    expected_job = existing_job
    dict_compare(job, expected_job)
    m_get_store.return_value.update_job.assert_not_called()


def test_check_ready_for_force_deploy():

    # When: I check ready status for job with force-deploy
    status = check_ready(dict_merge({
        'force-deploy': True
    }, MOCK_EXISTING_JOB))

    # Then: Job has no failed / pending hooks
    dict_compare(status, {
        'pending': [],
        'failed': []
    })


def test_check_ready_for_successful_hooks():

    # When: I check ready status for job with successful hooks
    status = check_ready(dict_merge({
        'hooks': {
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_SUCCESS
                }
            }
        }
    }, MOCK_EXISTING_JOB))

    # Then: Job has no failed / pending hooks
    dict_compare(status, {
        'pending': [],
        'failed': []
    })


def test_check_ready_for_pending_hooks():

    # When: I check ready status for job with pending/failed hooks
    status = check_ready(dict_merge({
        'hooks': {
            'ci': {
                'ci1': {
                    'status': HOOK_STATUS_PENDING
                }
            },
            'builder': {
                'image-factory': {
                    'status': HOOK_STATUS_FAILED
                }
            }
        }
    }, MOCK_EXISTING_JOB))

    # Then: Job has no failed / pending hooks
    dict_compare(status, {
        'pending': ['ci1'],
        'failed': ['image-factory']
    })
