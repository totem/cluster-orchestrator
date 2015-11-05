from jinja2 import environment
from nose.tools import eq_
from orchestrator.jinja import filters


class TestJinjaFilters:

    def setup(self):
        self.env = environment.get_spontaneous_environment()
        filters.apply_filters(self.env)

    def test_regex_replace(self):
        # Given: Jinja template using starting_with
        template = \
            '{{ "mock_a$b$c%d^host" | replace_regex("[^A-Za-z0-9-]","-") }}'

        # When: I render template
        ret_value = self.env.from_string(template).render()

        # Then: Template is rendered as expected
        eq_(ret_value, 'mock-a-b-c-d-host')
