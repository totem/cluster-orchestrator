import json

from nose.tools import eq_, ok_

from orchestrator import templatefactory

"""
Tests for Slack Jinja templates
"""


def test_slack_template():
    """
    should render json output for slack API.
    """

    output = templatefactory.render_template(
        'slack.json.jinja',
        ctx={
            "env": "local",
            "operation": "test",
            "owner": "test-owner",
            "repo": "test-repo",
            "ref": "test-ref",
            "github": True,
            "job-id": "test-job"
        },
        notification={
            "message": "test message",
            "code": "CONFIG_VALIDATION_ERROR"
        }, level=1)
    slack_dict = json.loads(output)

    eq_(slack_dict.get("username"), "Orchestrator (local-test)")
    eq_(slack_dict.get("channel"), "#totem")
    ok_(slack_dict.get("text"))
    ok_(slack_dict.get("attachments"))
