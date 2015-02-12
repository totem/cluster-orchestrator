"""
Tasks for notification
"""
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)
from hypchat import HypChat
from json2html import json2html
from conf.appconfig import CONFIG_PROVIDERS
from orchestrator.celery import app
from orchestrator.services.security import decrypt_config
from orchestrator.util import dict_merge


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


def as_notification_msg(obj, ctx=None):
    ctx = ctx or {}
    ctx.setdefault('component', 'orchestrator')
    if getattr(obj, 'to_dict', None):
        obj_dict = obj.to_dict()
        notify_obj = dict_merge(ctx, {
            'code': obj_dict.get('code', 'INTERNAL'),
            'message': obj_dict.get('message', str(obj))
        })
    else:
        notify_obj = dict_merge(ctx, {
            'message': obj.message if getattr(obj, 'message', None)
            else str(obj),
            'code': 'INTERNAL'
        })

    return json2html.convert(
        json=notify_obj)


@app.task
def notify_hipchat(obj, ctx, level, config, security_profile):
    config = decrypt_config(config, profile=security_profile)
    hc = HypChat(config['token'], config.get('url'))
    msg = as_notification_msg(obj, ctx)
    hc.get_room(config.get('room')).notification(
        msg, format='html', notify=True,
        color=config.get('colors', {}).get(level, 'gray'),
    )
