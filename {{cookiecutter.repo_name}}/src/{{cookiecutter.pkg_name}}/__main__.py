{% if "cli" in cookiecutter.features.replace(',', ' ').split() -%}
# -*- coding: utf-8 -*-
# pylint: disable=bad-continuation
""" Command line interface.
"""
# Copyright ©  {{ cookiecutter.year }} {{ cookiecutter.full_name }} <{{ cookiecutter.email }}>
#
# ## LICENSE_SHORT ##
from __future__ import absolute_import, unicode_literals, print_function

import re

import click
from bunch import Bunch

from . import config


# Default name of the app, and its app directory
__app_name__ = '{{ cookiecutter.repo_name }}'
config.APP_NAME = __app_name__

# The `click` custom context settings
CONTEXT_SETTINGS = dict(
    obj=Bunch(cfg=None, quiet=False, verbose=False),  # namespace for custom stuff
    help_option_names=['-h', '--help'],
    auto_envvar_prefix=__app_name__.upper().replace('-', '_'),
)


# `--license` option decorator
def license_option(*param_decls, **attrs):
    """``--license`` option that prints license information and then exits."""
    def decorator(func):
        "decorator inner wrapper"
        def callback(ctx, _dummy, value):
            "click option callback"
            if not value or ctx.resilient_parsing:
                return

            from . import __doc__ as license_text
            license_text = re.sub(r"``([^`]+?)``", lambda m: click.style(m.group(1), bold=True), license_text)
            click.echo(license_text)
            ctx.exit()

        attrs.setdefault('is_flag', True)
        attrs.setdefault('expose_value', False)
        attrs.setdefault('is_eager', True)
        attrs.setdefault('help', 'Show the license and exit.')
        attrs['callback'] = callback
        return click.option(*(param_decls or ('--license',)), **attrs)(func)

    return decorator


# Main command (root)
@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(message=config.VERSION_INFO)
@license_option()
@click.option('-q', '--quiet', is_flag=True, default=False, help='Be quiet (show only errors).')
@click.option('-v', '--verbose', is_flag=True, default=False, help='Create extra verbose output.')
@click.option('-c', '--config', "config_paths", metavar='FILE',
              multiple=True, type=click.Path(), help='Load given configuration file(s).')
@click.pass_context
def cli(ctx, quiet=False, verbose=False, config_paths=None):  # pylint: disable=unused-argument
    """'{{ cookiecutter.repo_name }}' command line tool."""
    config.Configuration.from_context(ctx, config_paths)
    ctx.obj.quiet = quiet
    ctx.obj.verbose = verbose


# Import sub-commands to define them AFTER `cli` is defined
config.cli = cli
from . import commands as _  # noqa pylint: disable=unused-import, wrong-import-position

if __name__ == "__main__":  # imported via "python -m"?
    __package__ = '{{ cookiecutter.pkg_name }}'  # pylint: disable=redefined-builtin
    cli()  # pylint: disable=no-value-for-parameter
{% endif -%}
