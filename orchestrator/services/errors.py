__author__ = 'sukrit'


class ConfigProviderNotFound(Exception):

    def __init__(self, provider_type):
        self.provider_type = provider_type
        super(ConfigProviderNotFound, self).__init__(provider_type)
