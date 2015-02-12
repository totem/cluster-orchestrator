"""
Tasks for notification
"""
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)
from hypchat import HypChat
from conf.appconfig import CONFIG_PROVIDERS, SEARCH_SETTINGS, \
    DEFAULT_HIPCHAT_TOKEN
from orchestrator import templatefactory
from orchestrator.celery import app
from orchestrator.services.security import decrypt_config


LEVEL_ERROR = 1
LEVEL_WARN = 2
LEVEL_INFO = 3
LEVEL_DEBUG = 4


@app.task
def notify(obj, ctx=None, level=LEVEL_ERROR, notifications=None,
           security_profile='default'):
    """
    Handles notification or job failure.

    :return: None
    """
    notifications = notifications or \
        CONFIG_PROVIDERS['default']['config']['notifications']

    enabled_notifications = {
        name: notification for name, notification in notifications.items()
        if notification.get('enabled') and level <=
        notification.get('level', LEVEL_ERROR) and
        globals().get('notify_%s' % name)
    }
    for name, notification in enabled_notifications.items():
        globals().get('notify_%s' % name).si(
            obj, ctx, level, notification, security_profile).delay()


def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    elif getattr(obj, 'to_dict', None):
        obj_dict = obj.to_dict()
        return obj_dict
    else:
        return {
            'message': repr(obj),
            'code': 'INTERNAL'
        }


@app.task
def notify_hipchat(obj, ctx, level, config, security_profile):
    config = decrypt_config(config, profile=security_profile)
    ctx.setdefault('github', True)
    ctx.setdefault('search', SEARCH_SETTINGS)
    hc = HypChat(config.get('token', '') or DEFAULT_HIPCHAT_TOKEN,
                 config.get('url'))
    msg = templatefactory.render_template(
        'hipchat.html', notification=_as_dict(obj), ctx=ctx, level=level)
    hc.get_room(config.get('room')).notification(
        msg, format='html', notify=True,
        color=config.get('colors', {}).get(level, 'gray'),
    )
