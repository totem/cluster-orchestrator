import datetime
from pymongo import MongoClient
import pymongo
from pymongo.collection import ReturnDocument
import pytz
from conf.appconfig import MONGODB_URL, MONGODB_JOB_COLLECTION, \
    MONGODB_DB, MONGODB_EVENT_COLLECTION, \
    JOB_EXPIRY_SECONDS, JOB_STATE_SCHEDULED, JOB_STATE_NEW
from orchestrator.services.storage.base import AbstractStore

__author__ = 'sukrit'


def create(url=MONGODB_URL, dbname=MONGODB_DB,
           job_coll=MONGODB_JOB_COLLECTION,
           event_coll=MONGODB_EVENT_COLLECTION
           ):
    """
    Creates Instance of MongoStore
    :keyword url: MongoDB Connection String
    :type url: str
    :keyword dbname: MongoDB database name
    :type dbname: str
    :keyword job_coll: Orchestrator Job Collection name
    :type job_coll: str
    :keyword event_coll: Totem Event Collection name
    :type event_coll: str
    :return: Instance of MongoStore
    :rtype: MongoStore
    """
    return MongoStore(url, dbname, job_coll, event_coll)


class MongoStore(AbstractStore):
    """
    Mongo based implementation of store.
    """

    def __init__(self, url, dbname, job_coll, event_coll):
        self.client = MongoClient(url)
        self.dbname = dbname
        self.job_coll = job_coll
        self.event_coll = event_coll

    def setup(self):
        """
        Setup indexes for mongo store
        :return:
        """
        idxs = self._jobs.index_information()
        self._jobs.drop_indexes()
        if 'created_idx' not in idxs:
            self._jobs.create_index(
                [('date', pymongo.DESCENDING)],
                name='created_idx')

        if 'identity_idx' not in idxs:
            self._jobs.create_index(
                'meta-info.job-id', name='identity_idx', unique=True)

        if 'expiry_idx' not in idxs:
            self._jobs.create_index(
                [('_expiry', pymongo.DESCENDING)], name='expiry_idx',
                background=True, expireAfterSeconds=JOB_EXPIRY_SECONDS)

        if 'git_idx' not in idxs:
            self._jobs.create_index([
                ('meta-info.git.owner', pymongo.ASCENDING),
                ('meta-info.git.repo', pymongo.ASCENDING),
                ('meta-info.git.ref', pymongo.ASCENDING),
                ('meta-info.git.commit', pymongo.ASCENDING),

            ], name='git_idx')

    @property
    def _db(self):
        return self.client[self.dbname]

    @property
    def _jobs(self):
        """
        Gets the job collection reference
        :return: Job collection reference
        :rtype: pymongo.collection.Collection
        """
        return self._db[self.job_coll]

    @property
    def _events(self):
        """
        Gets the events collection reference
        :return: Event collection reference
        :rtype: pymongo.collection.Collection
        """
        return self._db[self.event_coll]

    def find_or_create_job(self, job):
        job = self.apply_modified_ts(job)
        job['_expiry'] = datetime.datetime.now(tz=pytz.UTC)
        git = job['meta-info']['git']
        return self._jobs.find_one_and_update(
            {
                'meta-info.git.owner': git['owner'],
                'meta-info.git.repo': git['repo'],
                'meta-info.git.ref': git['ref'],
                'state': {
                    '$in': [JOB_STATE_SCHEDULED, JOB_STATE_NEW]
                }
            },
            {
                '$setOnInsert': job,
            },
            projection={
                '_id': False,
                '_expiry': False
            },
            return_document=ReturnDocument.AFTER,
            upsert=True
        )

    def update_state(self, job_id, state):
        self._jobs.update_one(
            {
                'meta-info.job-id': job_id,
            },
            {
                '$set': {
                    'state': state,
                    'modified': datetime.datetime.now(tz=pytz.UTC),
                    '_expiry': datetime.datetime.now(tz=pytz.UTC)
                }
            }
        )

    def get_job(self, job_id):
        return self._jobs.find_one(
            {
                'meta-info.job-id': job_id,
            },
            projection={
                '_id': False,
                '_expiry': False
            }
        )

    def health(self):
        return {
            'type': 'mongo',
            'nodes': list(self.client.nodes),
            'primary': self.client.primary,
            'secondaries': list(self.client.secondaries),
            'collections': self._db.collection_names(
                include_system_collections=False)
        }

    def _add_raw_event(self, event):
        """
        Adds event to event store
        :param event:
        :return:
        """
        self._events.insert_one(event)

    def filter_jobs(self, owner=None, repo=None, ref=None, commit=None):
        u_filter = {}
        if owner:
            u_filter['meta-info.git.owner'] = owner

        if repo:
            u_filter['meta-info.git.repo'] = repo

        if ref:
            u_filter['meta-info.git.ref'] = ref

        if commit:
            u_filter['meta-info.git.commit'] = commit

        projection = {
            '_id': False
        }

        return [
            job for job in
            self._jobs.find(u_filter, projection=projection)
                .sort('modified')
        ]

    def reset_hooks(self, job_id, hooks, commit=None):
        update = {
            '$set': {
                'hooks': hooks
            },
        }
        if commit:
            update['$set']['meta-info.git.commit'] = commit
            update['$addToSet'] = {
                'meta-info.git.commit-set': commit
            }

        self._jobs.update_one({
            'meta-info.job-id': job_id
        }, update)

    def update_hook(self, job_id, hook_type, hook_name, hook_status,
                    image=None):
        hook_key = 'hooks.{}.{}'.format(hook_type, hook_name)
        update = {
            '$set': {
                hook_key: {
                    'status': hook_status
                }
            }
        }
        if image:
            update['$set']['templates.app.args'] = {
                'image': image
            }

        self._jobs.update_one({
            'meta-info.job-id': job_id
        }, update)
