from mock import patch
from orchestrator.tasks import notification


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
