

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
        """
        Load config at given path.

        :param paths: Tuple consisting of nested level path
        :return: Parsed Config
        :rtype: dict
        :raise NotImplementedError: If provider does not support this method.
        """
        self.not_supported()

    def write(self, config, *paths):
        """
        Writes config at given path.

        :param config: Configuration
        :type config: dict
        :param paths: Nested level path
        :type paths: tuple
        :return: None
        :raise NotImplementedError: If provider does not support this method.
        """
        self.not_supported()

    def delete(self, *paths):
        """
        Performs safe delete of the configuration at given path.

        :param paths: Nested level path
        :type paths: tuple
        :return: None
        :raise NotImplementedError: If provider does not support this method.
        """
        self.not_supported()
