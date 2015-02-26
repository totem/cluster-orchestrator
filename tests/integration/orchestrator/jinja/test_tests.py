from jinja2 import environment
from nose.tools import eq_
from orchestrator.jinja import tests


class TestJinjaTests:

    def setup(self):
        self.env = environment.get_spontaneous_environment()
        tests.apply_tests(self.env)

    def test_starting_with(self):
        # Given: Jinja template using starting_with
        template = '{{ "mock_test" is starting_with "mock" }}'

        # When: I render template
        ret_value = self.env.from_string(template).render()

        # Then: Template is rendered as expected
        eq_(ret_value, 'True')

    def test_matching(self):
        # Given: Jinja template using starting_with
        template = '{{ "Mock_Test" is matching(".*test", False) }}'

        # When: I render template
        ret_value = self.env.from_string(template).render()

        # Then: Template is rendered as expected
        eq_(ret_value, 'True')
