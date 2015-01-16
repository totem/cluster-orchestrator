

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
