"""
Tasks for notification
"""
import json

import time
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, filter, map, zip)

import requests

from conf.appconfig import CONFIG_PROVIDERS, \
    DEFAULT_HIPCHAT_TOKEN, LEVEL_FAILED, DEFAULT_GITHUB_TOKEN, \
    LEVEL_FAILED_WARN, LEVEL_STARTED, LEVEL_SUCCESS, LEVEL_PENDING
from orchestrator import templatefactory
from orchestrator.celery import app
from orchestrator.services.security import decrypt_config
from orchestrator.tasks import util

import logging
logger = logging.getLogger('orchestrator.tasks.notification')


@app.task
def notify(obj, ctx=None, level=LEVEL_FAILED,
           notifications=None, security_profile='default'):
    """
    Handles notification or job failure.

    :return: None
    """
    notifications = notifications or \
        CONFIG_PROVIDERS['default']['config']['notifications']

    enabled_notifications = {
        name: notification for name, notification in notifications.items()
        if notification.get('enabled') and level <=
        notification.get('level', LEVEL_FAILED) and
        globals().get('notify_%s' % name)
    }
    for name, notification in enabled_notifications.items():
        globals().get('notify_%s' % name).si(
            obj, ctx, level, notification, security_profile).delay()


@app.task
def notify_hipchat(obj, ctx, level, config, security_profile):
    logger.info('Ignorning hipchat notification')

@app.task
def notify_slack(obj, ctx, level, config, security_profile):
    logger.info('Sending notification to slack')
    config = decrypt_config(config, profile=security_profile)
    ctx.setdefault('github', True)
    url = config.get('url')
    notification = util.as_dict(obj)
    notification['channel'] = config.get('channel')
    notification['date'] = int(time.time())
    msg = templatefactory.render_template(
        'slack.json.jinja', notification=notification, ctx=ctx,
        level=level)
    headers = {
        'content-type': 'application/json',
    }
    if url:
        requests.post(url, data=msg, headers=headers)\
            .raise_for_status()
    logger.info('Sent notification to slack')


@app.task
def notify_github(obj, ctx, level, config, security_profile):
    logger.info('Ignorning github notification')
