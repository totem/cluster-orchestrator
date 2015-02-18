from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('orchestrator', 'templates'))


def render_template(template, *args, **kwargs):
    return env.get_template(template).render(*args, **kwargs)
