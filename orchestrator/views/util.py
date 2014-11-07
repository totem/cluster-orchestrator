import copy
import functools
import json

from flask import jsonify, Response, request

from conf.appconfig import MIME_JSON, API_DEFAULT_PAGE_SIZE


def build_response(output, status=200, mimetype=MIME_JSON, headers={}):
    """
    Utility method to build the Json response with custom mimetype, status code
    and response headers

    :param output: Json Serializable object
    :param status: Http Status code
    :type status: int
    :param mimetype: Response mimetype.
    :type mimetype: str
    :param headers: Response headers (key, value)
    :type headers: dict
    :return: Tuple consisting of Flask Response, Status Code and Http Headers
    """
    if isinstance(output, list):
        resp = Response(json.dumps(output))
    else:
        resp = jsonify(output)
    resp.mimetype = mimetype
    return resp, status, headers


def created(output, mimetype=MIME_JSON, location=None, status=201, headers={}):
    headers = copy.deepcopy(headers or {})
    if location:
        headers.setdefault('Location', location)
    return build_response(output, status=status, mimetype=mimetype,
                          headers=headers)


def deleted(status=204, mimetype=MIME_JSON, headers={}):
    headers = copy.deepcopy(headers or {})
    return build_response('', status=status, mimetype=mimetype,
                          headers=headers)


def use_paging(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            size = int(request.args.get('size', API_DEFAULT_PAGE_SIZE))
            size = max(0, min(API_DEFAULT_PAGE_SIZE, size))
        except ValueError:
            size = API_DEFAULT_PAGE_SIZE

        try:
            page = int(request.args.get('page', 0))
            page = max(0, page)
        except ValueError:
            page = 0

        kwargs.setdefault('page', page)
        kwargs.setdefault('size', size)
        return func(*args,  **kwargs)
    return inner
