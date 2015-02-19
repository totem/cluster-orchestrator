from mock import patch, MagicMock
from nose.tools import eq_
from conf.appconfig import SEARCH_SETTINGS
from orchestrator.tasks import notification
from orchestrator.tasks.notification import LEVEL_ERROR


@patch('orchestrator.tasks.notification.notify_hipchat')
def test_notify_when_disabled(m_notify_hipchat):
    # Given: Disabled notifications
    notifications = {
        'hipchat': {
            'enabled': False
        }
    }

    # When: I invoke notify
    notification.notify('mockerror', notifications=notifications)

    # Then: No notifications are sent
    m_notify_hipchat.si.assert_not_called()


@patch('orchestrator.tasks.notification.notify_hipchat')
def test_notify_when_level_not_enabled(m_notify_hipchat):
    # Given: Enabled hipchat notifications with level error
    notifications = {
        'hipchat': {
            'enabled': True,
            'level': notification.LEVEL_ERROR
        }
    }

    # When: I invoke notify using level warn
    notification.notify('mockwarn', level=notification.LEVEL_WARN,
                        notifications=notifications)

    # Then: No notifications are sent
    m_notify_hipchat.si.assert_not_called()


@patch('orchestrator.tasks.notification.notify_hipchat')
def test_notify_when_notification_type_not_found(m_notify_hipchat):
    # Given: Enabled hipchat notifications with level error
    notifications = {
        'invalid': {
            'enabled': True,
            'level': notification.LEVEL_ERROR
        }
    }

    # When: I invoke notify
    notification.notify('mockerror', notifications=notifications)

    # Then: No notifications are sent
    m_notify_hipchat.si.assert_not_called()


@patch('orchestrator.tasks.notification.notify_hipchat')
def test_notify(m_notify_hipchat):
    # Given: Enabled hipchat notifications with level error
    notifications = {
        'hipchat': {
            'enabled': True,
            'level': notification.LEVEL_ERROR
        }
    }

    # When: I invoke notify using level warn
    notification.notify('mockerror', notifications=notifications)

    # Then: Hipchat notification is sent
    m_notify_hipchat.si.assert_called_once()


def test_as_dict_for_dictionary_type():
    """
    Should return the input dictionary
    """
    # Given: Input dictionary
    input = {
        'mockkey': 'mockvalue'
    }

    # When: I invoke _as_dict with dict type
    output = notification._as_dict(input)

    # Then: Input dictionary is returned
    eq_(output, input)


def test_as_dict_for_obj_with_to_dict_method():
    """
    Should return the dict representation
    """
    # Given: Input Object
    input = MagicMock()
    input.to_dict.return_value = {
        'mockkey': 'mockvalue'
    }

    # When: I invoke _as_dict with dict type
    output = notification._as_dict(input)

    # Then: Dictionary representation is returned
    eq_(output, {
        'mockkey': 'mockvalue'
    })


def test_as_dict_for_obj_with_no_to_dict_method():
    """
    Should return the dict representation
    """
    # Given: Input object
    input = 'test'

    # When: I invoke _as_dict with dict type
    output = notification._as_dict(input)

    # Then: Dictionary representation is returned
    eq_(output, {
        'code': 'INTERNAL',
        'message': repr(input)
    })


@patch('orchestrator.tasks.notification.requests')
@patch('orchestrator.tasks.notification.templatefactory')
@patch('orchestrator.tasks.notification.json')
def test_notify_hipchat(m_json, m_templatefactory, m_requests):
    """
    Should send hipchat notification
    :return:
    """
    # Given: Template factory that renders html template for notification
    m_templatefactory.render_template.return_value = 'mockmsg'

    # And: Mock implementation for jsonify (for validating data)
    m_json.dumps.side_effect = lambda data: data

    # When: I send message using hipchat
    notification.notify_hipchat(
        'Mock', {}, LEVEL_ERROR,
        {'token': 'mocktoken', 'room': 'mockroom'},
        'default')

    # Then: Notification gets send successfully
    m_requests.post.assert_called_once_with(
        'https://api.hipchat.com/v2/room/mockroom/notification',
        headers={
            'content-type': 'application/json',
            'Authorization': 'Bearer mocktoken'},
        data={
            'color': 'gray',
            'message': 'mockmsg',
            'notify': True,
            'message_format': 'html'
        })

    m_templatefactory.render_template.assert_called_once_with(
        'hipchat.html',
        notification={'message': "'Mock'", 'code': 'INTERNAL'},
        ctx={'search': SEARCH_SETTINGS, 'github': True},
        level=LEVEL_ERROR,
    )
