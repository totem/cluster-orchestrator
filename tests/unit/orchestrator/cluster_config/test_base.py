from orchestrator.cluster_config.base import AbstractConfigProvider
from nose.tools import raises

__author__ = 'sukrit'


class TestAbstractConfigProvider:
    """
    Tests MergedConfigProvider
    """

    def setup(self):
        self.provider = AbstractConfigProvider()

    @raises(NotImplementedError)
    def test_load(self):
        """
        Should raise NotImplementedError
        """

        # When I invoke the root endpoint
        self.provider.load('path1')

        # Then: NotImplementedError is raised

    @raises(NotImplementedError)
    def test_write(self):
        """
        Should raise NotImplementedError
        """

        # When I invoke the root endpoint
        self.provider.write({}, 'path1')

        # Then: NotImplementedError is raised

    @raises(NotImplementedError)
    def test_delete(self):
        """
        Should raise NotImplementedError
        """

        # When I invoke the root endpoint
        self.provider.delete('path1')

        # Then: NotImplementedError is raised
