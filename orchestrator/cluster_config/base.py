

class AbstractConfigProvider:
    """
    Abstract provider defining methods for loading and writing configuration.
    for upto 3 levels:

    root level:  Defaults for totem for all clusters.
    cluster level: Defaults for particular cluster.
    organization level: Defaults for particular organization
    repository: Defaults for particular repository
    ref level: Defaults for particular tag or a branch

    The implementation (like S3) must support multi level layout.
    """

    def not_supported(self):
        """
        Raises NotImplementedError with a message
        :return:
        """
        raise NotImplementedError(
            'Provider: %s does not support this operation' % self.__class__)

    def load(self, *paths):
        self.not_supported()

    def write(self, config, *paths):
        self.not_supported()
