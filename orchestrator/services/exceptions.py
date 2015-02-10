

class ConfigValueError(Exception):

    def __init__(self, path, value, reason):
        self.path = path
        self.value = value
        self.message = 'Error happened while parsing path:%s value:%s.  %s' % \
                       (path, value, reason)
        self.reason = reason
        self.code = 'CONFIG_ERROR'
        super(ConfigValueError, self).__init__(path, value, reason)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': {
                'path': self.path,
                'value': self.value,
                'reason': self.reason
            }
        }

    def __str__(self):
        return self.message


class ConfigValidationError(Exception):

    def __init__(self, message, schema_path, schema):
        self.message = message
        self.schema_path = schema_path
        self.schema = schema
        self.code = 'CONFIG_VALIDATION_ERROR'
        super(ConfigValidationError, self).__init__(message, schema_path,
                                                    schema)

    def to_dict(self):
        return {
            'message': self.message,
            'code': self.code,
            'details': {
                'schema-path': self.schema_path,
                'schema': self.schema
            }
        }
