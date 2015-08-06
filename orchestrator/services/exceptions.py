import json
from orchestrator.exceptions import BusinessRuleViolation


class ConfigValueError(BusinessRuleViolation):

    def __init__(self, path, value, reason):
        self.path = path
        self.value = value
        self.reason = reason
        message = 'Error happened while parsing path:%s value:%s.  %s' % \
                  (path, value, reason)
        details = {
            'path': self.path,
            'value': self.value,
            'reason': self.reason
        }

        super(ConfigValueError, self).__init__(
            message, code='CONFIG_ERROR', details=details)


class ConfigValidationError(BusinessRuleViolation):

    def __init__(self, message, schema_path, schema):
        self.schema_path = schema_path
        self.schema = schema
        code = 'CONFIG_VALIDATION_ERROR'
        details = {
            'schema-path': self.schema_path,
            'schema': json.dumps(self.schema)
        }

        super(ConfigValidationError, self).__init__(
            message, code=code, details=details)


class ConfigParseError(BusinessRuleViolation):

    def __init__(self, error_msg, paths):
        self.paths = paths
        self.error_msg = error_msg
        message = 'Failed to parse configuration for paths: {0}. ' \
                  'Reason: {1}'.format(paths, error_msg)
        code = 'CONFIG_PARSE_ERROR'
        details = {
            'paths': self.paths
        }
        super(ConfigParseError, self).__init__(message, code=code,
                                               details=details)
