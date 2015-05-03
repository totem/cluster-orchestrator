from datetime import datetime
import logging
import traceback
from flask import request, make_response
import flask
from werkzeug.exceptions import HTTPException
from orchestrator.exceptions import BusinessRuleViolation
from orchestrator.services.exceptions import ConfigValueError
from orchestrator.tasks.exceptions import TaskExecutionException

logger = logging.getLogger(__name__)


def as_flask_error(error=None, message=None, details=None, traceback=None,
                   status=500, code='INTERNAL', timestamp=None):
    return flask.jsonify({
        'path': request.path,
        'url': request.url,
        'method': request.method,
        'message': message or str(error),
        'details': details,
        'traceback': traceback,
        'status': status,
        'code': code,
        'timestamp': timestamp or datetime.utcnow()
    }, status=status), status


def raise_error(message, details=None, traceback=None, status=500,
                code='INTERNAL'):
    """
    Creates error response by raising HTTPException

    :param output: dictionary wrapping exception parameters
    :param mimetype: MIMETYPE for the ouput.
    :param status: Http Status code.
    :param headers: Dictionary containing additional response headers
    :raises: HTTPException containing wrapped flask response.
    """
    resp = make_response(
        as_flask_error(
            message=message, details=details, traceback=traceback,
            status=status, code=code))
    raise HTTPException(response=resp)


def register(app, **kwargs):

    @app.errorhandler(404)
    def page_not_found(error):
        return as_flask_error(error, **{
            'message': 'The given resource:%s is not found on server'
                       % request.path,
            'code': 'NOT_FOUND',
            'status': 404
        })

    @app.errorhandler(TaskExecutionException)
    def task_error(error):
        return as_flask_error(error, **{
            'code': error.code,
            'message': error.message,
            'details': error.details,
            'traceback': error.traceback,
            'status': 500,
        })

    @app.errorhandler(BusinessRuleViolation)
    def business_rule_violation(error):
        return as_flask_error(error, **{
            'code': error.code,
            'message': error.message,
            'details': error.to_dict()['details'],
            'status': 422,
            })

    @app.errorhandler(Exception)
    @app.errorhandler(500)
    def internal(error):
        logger.exception('Unknown error happened while serving request.')
        trace = traceback.format_exc()
        try:
            details = error.to_dict()
        except AttributeError:
            details = None
        return as_flask_error(error, **{
            'code': 'INTERNAL',
            'details': details,
            'traceback': trace,
            'status': 500,
        })

    @app.errorhandler(406)
    def not_acceptable(error):
        return as_flask_error(error, **{
            'code': 'NOT_ACCEPTABLE',
            'status': 406
        })

    @app.errorhandler(415)
    def invalid_media_type(error):
        return as_flask_error(error, **{
            'code': 'INVALID_MEDIA_TYPE',
            'status': 415
        })
