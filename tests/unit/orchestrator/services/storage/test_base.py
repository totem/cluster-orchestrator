import datetime
from freezegun import freeze_time
from mock import MagicMock
from nose.tools import raises
import pytz
from conf.appconfig import JOB_STATE_NEW
from orchestrator.services.storage.base import AbstractStore
from tests.helper import dict_compare


NOW = datetime.datetime(2022, 01, 01, tzinfo=pytz.UTC)
NOW_NOTZ = datetime.datetime(2022, 01, 01)


class TestAbstractStore:

    def setup(self):
        self.store = AbstractStore()

    @raises(NotImplementedError)
    def test_update_job(self):
        self.store.update_job(MagicMock())

    @raises(NotImplementedError)
    def test_get_job(self):
        self.store.get_job('fake_id')

    @raises(NotImplementedError)
    def test_update_state(self):
        self.store.update_state('fake_id', 'PROMOTED')

    @raises(NotImplementedError)
    def test_get_health(self):
        self.store.health()

    @freeze_time(NOW_NOTZ)
    def test_add_event(self):
        # Given: Mock implementation for adding raw event
        self.store._add_raw_event = MagicMock()

        # When: I add event to the store
        self.store.add_event('MOCK_EVENT')

        # Then: Event gets added to the store
        self.store._add_raw_event.assert_called_once_with({
            'type': 'MOCK_EVENT',
            'component': 'orchestrator',
            'details': None,
            'date': NOW_NOTZ

        })

    @raises(NotImplementedError)
    def test_add_raw_event(self):
        self.store.add_event({})

    def test_setup(self):
        self.store.setup()
        # NOOP

    @raises(NotImplementedError)
    def test_filter_jobs(self):
        self.store.filter_jobs(owner='mock-owner', repo='mock-repo',
                               ref='mock-branch', state_in=[JOB_STATE_NEW])

    @freeze_time(NOW)
    def test_apply_modified_ts(self):

        # When: I apply modified timestamp for given deployemnt
        deployement = self.store.apply_modified_ts({
            'deployement': {
                'id': 'test'
            }
        })

        # Then: Modified timestamp is applied as expected
        dict_compare(deployement, {
            'deployement': {
                'id': 'test'
            },
            'modified': NOW
        })
