import copy
import datetime
import pytz
from orchestrator.util import dict_merge

__author__ = 'sukrit'

"""
Module containing methods for storing job/other information in persist
storage like mongo
"""

EVENT_NEW_JOB = 'NEW_JOB'
EVENT_ACQUIRED_LOCK = 'ACQUIRED_LOCK'
EVENT_CALLBACK_HOOK = 'CALLBACK_HOOK'
EVENT_UNDEPLOY_HOOK = 'UNDEPLOY_HOOK'
EVENT_UNDEPLOY_REQUESTED = 'UNDEPLOY_REQUESTED'
EVENT_SETUP_APPLICATION_COMPLETE = 'SETUP_APPLICATION_COMPLETE'
EVENT_DEPLOY_REQUESTED = 'DEPLOY_REQUESTED'
EVENT_JOB_COMPLETE = 'JOB_COMPLETE'
EVENT_JOB_FAILED = 'JOB_FAILED'
EVENT_COMMIT_IGNORED = 'COMMIT_IGNORED'
EVENT_HOOK_IGNORED = 'HOOK_IGNORED'
EVENT_JOB_NOOP = 'JOB_NOOP'
EVENT_PENDING_HOOK = 'PENDING_HOOK'


class AbstractStore:

    @staticmethod
    def apply_modified_ts(job):
        return dict_merge(
            {
                'modified': datetime.datetime.now(tz=pytz.UTC)
            }, job)

    def not_supported(self):
        """
        Raises NotImplementedError with a message
        :return:
        """
        raise NotImplementedError(
            'Store: {} does not support this operation'.format(self.__class__))

    def update_job(self, job):
        """
        Creates/updates a job

        :param job: Dictionary containing job information
        :type job: dict
        :return: None
        """
        self.not_supported()

    def filter_jobs(self, owner=None, repo=None, ref=None, commit=None,
                    state_in=None):
        """
        Filter jobs by owner, repo , ref , commit

        :keyword owner: Repository Owner
        :type owner: str
        :keyword repo: Repository name
        :type repo: str
        :keyword ref: Branch/Tag name
        :type ref: str
        :keyword commit: SHA Commit ID
        :type commit: str
        :keyword state_in: Valid job states
        :type commit: str
        :return: List of filtered jobs where each job is represented as a dict
        :rtype: list
        """
        self.not_supported()

    def get_job(self, job_id):
        """
        Gets job by given id
        :param job_id: Job id
        :type job_id: str
        :return: Job dictionary
        :rtype: dict
        """
        self.not_supported()

    def update_state(self, job_id, state):
        """
        Update the state of given job
        :param job_id: Job id
        :type job_id: str
        :param state: State of the job (e.g. PROMOTED, NEW, etc)
        :type state: str
        :return: None
        """
        self.not_supported()

    def add_event(self, event_type, details=None, search_params=None):
        """
        Adds event to event store
        :param event_type: Type of event
        :type event_type: str
        :keyword details: Details associated with event
        :type details: dict
        :keyword search_params: Additional meta-info associated with event
        :type search_params: dict
        :return: None
        """
        event_upd = copy.deepcopy(search_params or {})
        event_upd.update({
            'type': event_type,
            'details': details,
            'date': datetime.datetime.utcnow(),
            'component': 'orchestrator'
        })
        self._add_raw_event(event_upd)

    def _add_raw_event(self, event):
        """
        Adds raw event to store.
        :param event: Event Details
        :type event: dict
        :return: None
        """
        self.not_supported()

    def setup(self):
        """
        Setup the store prior to use.
        :return: None
        """
        # No Setup needed by default
        pass

    def health(self):
        self.not_supported()
