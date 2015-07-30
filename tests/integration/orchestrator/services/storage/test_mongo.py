import copy
import datetime
from freezegun import freeze_time
import pymongo
from conf.appconfig import JOB_STATE_NEW, JOB_STATE_COMPLETE, JOB_STATE_FAILED
from orchestrator.services.storage.mongo import create
from nose.tools import ok_, eq_
from orchestrator.util import dict_merge
from tests.helper import dict_compare

__author__ = 'sukrit'


"""
Integration test for mongo storage. These requires mongo instance running
"""

NOW = datetime.datetime(2022, 01, 01)
NOW_JOB2 = datetime.datetime(2022, 02, 01)


EXISTING_JOBS = {
    'job-1': {
        'templates': {
            'app': {
                'args': {}
            }
        },
        'state': JOB_STATE_NEW,
        'meta-info': {
            'job-id': 'job-1',
            'git': {
                'owner': 'owner1',
                'repo': 'repo1',
                'ref': 'ref1',
                'commit': 'commit1',
                'commit-set': ['commit1']
            }
        },
        '_expiry': NOW,
        'modified': NOW,
        'hooks': {
            'ci': {
                'test1': {
                    'status': 'success'
                }
            }
        }
    },
    'job-2': {
        'state': JOB_STATE_COMPLETE,
        'meta-info': {
            'job-id': 'job-2',
            'git': {
                'owner': 'owner2',
                'repo': 'repo2',
                'ref': 'ref2',
                'commit': 'commit2',
                'commit-set': ['commit2']
            }
        },
        'hooks': {
            'ci': {
                'test-ci': {
                    'status': 'success'
                }
            },
            'builer': {
                'test-builder': {
                    'status': 'success',
                    'image': 'test'
                }
            }
        },
        '_expiry': NOW_JOB2,
        'modified': NOW_JOB2
    }
}


class TestMongoStore():

    @classmethod
    def setup(cls):
        cls.store = create(
            job_coll='orch-jobs-integration-store',
            event_coll='orch-events-integration-store'
        )
        cls.store._jobs.drop()
        cls.store._events.drop()
        cls.store.setup()
        requests = [pymongo.InsertOne(copy.deepcopy(deployment)) for deployment
                    in EXISTING_JOBS.values()]
        cls.store._jobs.bulk_write(requests)

    def _get_raw_document_without_internal_id(self, job_d):
        job = self.store._jobs.find_one(
            {'meta-info.job-id': job_d},
            projection={'_id': False}
        )
        return job

    def test_store_setup(self):

        # When I get the index informatiom
        # Note: Setup was already called
        indexes = self.store._jobs.index_information()

        # Indexes are created as expected
        for idx in ('created_idx', 'identity_idx', 'git_idx',
                    'expiry_idx'):
            ok_(idx in indexes, '{} was not created'.format(idx))

    @freeze_time(NOW)
    def test_find_or_create_job_for_existing_job(self):
        # When:  I execute find or create for existing job
        job = self.store.find_or_create_job({
            'meta-info': {
                'git': EXISTING_JOBS['job-1']['meta-info']['git'],
                'job-id': 'find-create-job-id'
            },
            'state': JOB_STATE_NEW
        })

        # Then: Existing job is returned
        expected_job = copy.deepcopy(EXISTING_JOBS['job-1'])
        del(expected_job['_expiry'])
        dict_compare(job, expected_job)

    @freeze_time(NOW)
    def test_find_or_create_job_for_non_existing_job(self):
        # Given: Job that needs to be created
        job = {
            'meta-info': {
                'git': {
                    'owner': 'find-create-owner',
                    'repo': 'find-create-repo',
                    'ref': 'find-create-ref',
                    'commit': 'find-create-commit'
                },
                'job-id': 'find-create-job-id'
            },
            'state': JOB_STATE_NEW
        }

        # When:  I execute find or create for non existing job
        created_job = self.store.find_or_create_job(job)

        # Then: Existing job is returned
        expected_job = copy.deepcopy(job)
        expected_job['modified'] = NOW
        dict_compare(created_job, expected_job)

    @freeze_time(NOW)
    def test_find_or_create_job_for_no_running_job(self):
        # Given: Job that needs to be created
        job = {
            'meta-info': {
                'git': EXISTING_JOBS['job-2']['meta-info']['git'],
                'job-id': 'find-create-job-id'
            },
            'state': JOB_STATE_NEW
        }

        # When:  I execute find or create for non existing job
        created_job = self.store.find_or_create_job(job)

        # Then: Existing job is returned
        expected_job = copy.deepcopy(job)
        expected_job['modified'] = NOW
        dict_compare(created_job, expected_job)

    def test_get_job(self):

        # When I get existing job
        job = self.store.get_job('job-1')

        # Expected Deployment is returned
        expected_job = copy.deepcopy(EXISTING_JOBS['job-1'])
        del(expected_job['_expiry'])
        dict_compare(job, expected_job)

    @freeze_time(NOW)
    def test_update_state(self):

        # When: I promote state for existing job
        self.store.update_state('job-1', JOB_STATE_FAILED)

        # Then: Deployment state is changed to promoted and set to never expire
        job = self._get_raw_document_without_internal_id(
            'job-1')
        expected_job = dict_merge({
            '_expiry': NOW,
            'modified': NOW,
            'state': JOB_STATE_FAILED
        }, EXISTING_JOBS['job-1'])
        dict_compare(job, expected_job)

    @freeze_time(NOW)
    def test_reset_hooks(self):

        # Given: Reset hooks
        hooks = {
            'ci': {
                'test1': {
                    'status': 'pending'
                }
            }
        }

        # When: I reset hooks for existing job
        self.store.reset_hooks('job-1', hooks, commit='commit1!')

        # Then: Deployment state is changed to promoted and set to never expire
        job = self._get_raw_document_without_internal_id('job-1')
        expected_job = dict_merge({
            '_expiry': NOW,
            'modified': NOW,
            'hooks': hooks,
            'meta-info': {
                'git': {
                    'commit': 'commit1!',
                    'commit-set': ['commit1', 'commit1!']
                }
            }
        }, EXISTING_JOBS['job-1'])
        dict_compare(job, expected_job)

    @freeze_time(NOW)
    def test_update_hook(self):

        # When: I update hooks for existing job
        self.store.update_hook('job-1', 'ci', 'test2', 'failed',
                               image='mockimage')

        # Then: Deployment state is changed to promoted and set to never expire
        job = self._get_raw_document_without_internal_id('job-1')
        expected_job = dict_merge({
            '_expiry': NOW,
            'modified': NOW,
            'hooks': {
                'ci': {
                    'test2': {
                        'status': 'failed'
                    }
                }
            },
            'templates': {
                'app': {
                    'args': {
                        'image': 'mockimage'
                    }
                }
            }
        }, EXISTING_JOBS['job-1'])
        dict_compare(job, expected_job)

    @freeze_time(NOW)
    def test_reset_hooks_without_commit(self):

        # Given: Reset hooks
        hooks = {
            'ci': {
                'test1': {
                    'status': 'pending'
                }
            }
        }

        # When: I reset hooks for existing job
        self.store.reset_hooks('job-1', hooks)

        # Then: Job hooks get reset
        job = self._get_raw_document_without_internal_id('job-1')
        expected_job = dict_merge({
            'hooks': hooks,
        }, EXISTING_JOBS['job-1'])
        dict_compare(job, expected_job)

    def test_health(self):

        # When: I fetch the health state of the store
        health = self.store.health()

        # Then: Expected health instance is returned
        for key in ('nodes', 'primary', 'secondaries', 'collections'):
            ok_(key in health)

    @freeze_time(NOW)
    def test_add_event(self):

        # When: I add event to mongo store
        self.store.add_event(
            'MOCK_EVENT',
            details={'mock': 'details'},
            search_params={
                'meta-info': {
                    'mock': 'search'
                }
            })

        # Then: Event gets added as expected
        event = self.store._events.find_one({'type': 'MOCK_EVENT'})
        del(event['_id'])
        dict_compare(event, {
            'component': 'orchestrator',
            'type': 'MOCK_EVENT',
            'date': NOW,
            'meta-info': {
                'mock': 'search'
            },
            'details': {
                'mock': 'details'
            }
        })

    def test_filter_all_jobs(self):
        # When: I filter jobs from the store
        jobs = self.store.filter_jobs()

        # Then: All jobs are returned
        eq_(len(jobs), 2)
        dict_compare(jobs[0], EXISTING_JOBS['job-1'])
        dict_compare(jobs[1], EXISTING_JOBS['job-2'])

    def test_filter_jobs_by_criteria(self):
        # When: I filter jobs from the store
        jobs = self.store.filter_jobs(
            owner=EXISTING_JOBS['job-1']['meta-info']['git']['owner'],
            repo=EXISTING_JOBS['job-1']['meta-info']['git']['repo'],
            ref=EXISTING_JOBS['job-1']['meta-info']['git']['ref'],
            commit=EXISTING_JOBS['job-1']['meta-info']['git']['commit']
        )

        # Then: All jobs are returned
        eq_(len(jobs), 1)
        dict_compare(jobs[0], EXISTING_JOBS['job-1'])
