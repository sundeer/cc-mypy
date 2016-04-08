#! /usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace, superfluous-parens
"""
    Cookiecutter post-gen hook.

    This gets called with no arguments, and with the project directory
    as the working directory. All templates are expanded and copied,
    and the post hook can add, modify, or delete files.

    Copyright (c) 2015 Juergen Hermann

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
from __future__ import absolute_import, unicode_literals, print_function

import io
import os
import sys
import json
import pprint
import shutil
import venv
import time
import configparser
from pathlib import Path
from fnmatch import fnmatchcase as globmatch
import pip
import pkg_resources


VERBOSE = True
DEBUG = False
NOSCAN_DIRS = set((
    '.git', '.svn', '.hg',
    '.env', '.venv', '.tox',
    'build', 'bin', 'lib', 'local', 'include', 'share', '*.egg-info',
))
KEEP_FILES = set(('__init__.py'))

# Map from short / file name to Trove name
LICENSES = {
    "Apache 2.0": "Apache Software License",
    "Artistic": "Artistic License",
    "BSD 2-clause": "BSD License",
    "BSD 3-clause": "BSD License",
    "BSD ISC": "BSD License",
    "CC0": "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication",
    "Eclipse": "License :: Other/Proprietary License",
    "GPLv2": "GNU General Public License v2 (GPLv2)",
    "GPLv2+": "GNU General Public License v2 or later (GPLv2+)",
    "GPLv3+": "GNU General Public License v3 or later (GPLv3+)",
    "LGPL v2": "GNU Lesser General Public License v2 (LGPLv2)",
    "LGPL v3": "GNU Lesser General Public License v3 (LGPLv3)",
    "MIT": "MIT License",
    "Mozilla v2.0": "Mozilla Public License 2.0 (MPL 2.0)",
    "Unlicense": "License :: Public Domain",
    "Internal": "License :: Other/Proprietary License",
}
LICENSE_OSI = "License :: OSI Approved :: "
LICENSE_MARKER = "## LICENSE_SHORT ##"
LICENSE_TROVE = "## LICENSE_TROVE ##"


def get_context():
    """Return context as a dict."""
    cookiecutter = None  # Make pylint happy
    return {{ cookiecutter | pprint }}


def walk_project():
    """Yield all files in the created project."""
    for path, dirs, files in os.walk(os.getcwd()):
        for dirname in dirs[:]:
            if any(globmatch(dirname, i) for i in NOSCAN_DIRS):
                dirs.remove(dirname)
        # sys.stderr.write(repr((files, dirs, path)) + '\n'); continue

        for filename in files:
            yield os.path.join(path, filename)


def replace_marker(filepath, marker, lines):
    """Replace given marker with provides lines."""
    # Read source file
    with io.open(filepath, 'r', encoding='utf-8') as handle:
        source_lines = handle.readlines()

    # Replace marker, and use any text before it as an indent string
    changed = False
    for idx, line in enumerate(source_lines):
        if line.rstrip().endswith(marker):
            line = line.rstrip().replace(marker, '')
            source_lines[idx] = '\n'.join((line + i).rstrip() for i in lines) + '\n'
            changed = True

    if changed:
        # Write back modified source
        with io.open(filepath, 'w', encoding='utf-8') as handle:
            handle.writelines(source_lines)

    return changed


def dump_context(context, filename):
    """Dump JSON context to given file."""
    with io.open(filename, 'w', encoding='ascii') as handle:
        data = json.dumps(context, indent=4, sort_keys=True, ensure_ascii=True)
        data = '\n'.join([i.rstrip() for i in data.splitlines()])
        handle.write(data + '\n')


def prune_empty_files():
    """ Prune any empty files left over from switched off features.

        Empty in this case also means "has just 1 or 2 bytes".
    """
    for filepath in walk_project():
        if os.path.getsize(filepath) <= 2 and os.path.basename(filepath) not in KEEP_FILES:
            if VERBOSE:
                sys.stderr.write("Removing {} byte sized '{}'...\n".format(
                    os.path.getsize(filepath), filepath
                ))
            os.unlink(filepath)


def copy_license(repo_dir, name):
    """Copy license file."""
    if repo_dir is None:
        sys.stderr.write(
            "Cannot access license files, is your 'cookiecutter' version too old? (need v1.1+)\n"
            "Search for '## LICENSE' in the generated files for unreplaced placeholders.\n"
            "\nTo install the necessary patches that make this work, use\n"
            "\n    pip install -e 'git+https://github.com/jhermann/cookiecutter.git"
                "@enriched-context-for-hooks#egg=cookiecutter'\n\n"
        )
        return

    filename = os.path.join(repo_dir, 'licenses', name.replace(' ', '_') + '.txt')
    trove_name = LICENSES.get(name, None)
    if trove_name:  # Known license?
        if '::' not in trove_name:
            trove_name = LICENSE_OSI + trove_name

        # Write main LICENSE file
        if VERBOSE:
            sys.stderr.write("Writing license file for '{}'... [{}]\n".format(name, trove_name,))
        shutil.copyfile(filename, "LICENSE")

        # Read in short license form for source files
        filename_short = os.path.join(repo_dir, 'licenses', 'short', name.replace(' ', '_') + '.txt')
        with io.open(filename_short, 'r', encoding='utf-8') as handle:
            license_short = handle.readlines()

        # Iterate over files and insert license notices
        count = 0
        for filepath in walk_project():
            if os.path.basename(filepath) == 'classifiers.txt':
                if replace_marker(filepath, LICENSE_TROVE, [trove_name + '\n']):
                    count += 1
            elif filepath.endswith('.py'):
                if replace_marker(filepath, LICENSE_MARKER, license_short):
                    count += 1

        if VERBOSE:
            sys.stderr.write("Rewrote {} source files with a license notice added.\n".format(count,))
    elif VERBOSE:
        sys.stderr.write("Unknown license '{}', I know about: {}\n".format(
            name, ', '.join(sorted(LICENSES.keys())),
        ))


# # Helpers
# project_root = os.path.abspath(os.path.dirname(__file__))
#
# def srcfile(*args):
#     "Helper for path building."
#     return os.path.join(*((project_root,) + args))
#
#
# def install_requirements(requirements):
#     # Load requirements files
#     requirements_files = dict(
#         dev     = 'dev-requirements.txt'
#     )
#     requires = {}
#     for key, filename in requirements_files.items():
#         requires[key] = []
#         if os.path.exists(srcfile(filename)):
#             with io.open(srcfile(filename), encoding='utf-8') as handle:
#                 for line in handle:
#                     line = line.strip()
#                     if line and not line.startswith('#') and ';' not in line:
#                         if any(line.startswith(i) for i in ('-e', 'http://', 'https://')):
#                             line = line.split('#egg=')[1]
#                         requires[key].append(line)
#                         print(requires[key])
#
#     setup(setup_requires=requires[requirements])


def create_venv():
    """Create a virtual environment"""
    env = venv.EnvBuilder(with_pip=True)
    repo_name = '{{cookiecutter.repo_name}}'
    env_dir = '.venv/{0}'.format(repo_name)
    env.create(env_dir)


def install_requirements(requirements_file):
    """Install requirements into virtual environment"""
    cwd = Path.cwd()
    base = cwd / '.venv/{{ cookiecutter.repo_name }}'
    target = base / 'lib/python3.5/site-packages'
    src = base / 'src'
    scripts = base / 'bin'
#
#     PYTHONPATH = str(scripts)
#     os.putenv('PYTHONPATH', PYTHONPATH )
#     # sys.path = []
#     # sys.path.append('')
#     # sys.path.append()
#
#     pip.main([
#         'install', '-r', requirements_file,
#         '-U'
#         # '--target', str(target),
#         # '--install-option', '--install-scripts={0}'.format(str(scripts)),
#         # '--src', str(src)
#     ])
#
    pip.main([
        'install', 'invoke',
        '--target', str(target),
        '--install-option', '--install-scripts={0}'.format(str(scripts))
    ])
#     #
#     # pip.main([
#     #     'install', 'git+https://github.com/jhermann/rituals.git',
#     #     '--target', str(target),
#     #     '--install-option', '--install-scripts={0}'.format(str(scripts))
#     # ])

def install_package(pkg):
    """Install package into virtual environment"""
    cwd = Path.cwd()
    base = cwd / '.venv/{{ cookiecutter.repo_name }}'
    target = base / 'lib/python3.5/site-packages'
    scripts = base / 'bin'

    pip.main([
        'install', pkg,
        '--target', str(target),
        '--install-option', '--install-scripts={0}'.format(str(scripts))
    ])

    # Fix the shebang in any console scripts created during package install.
    # This is a hack because I'm not sure how to install packages into the
    # new venv correctly.
    console_scripts = get_console_scripts(pkg)
    if console_scripts:
        for console_script in console_scripts:
            hack_shebang(console_script)


def get_console_scripts(pkg):
    """Given a package name installed into the new venv via pip, return a list
    of console scripts if any
    """
    cwd = Path.cwd()
    base = cwd / '.venv/{{ cookiecutter.repo_name }}'
    site_packages = base / 'lib/python3.5/site-packages'
    scripts = base / 'bin'

    egg_info_pattern = '{0}*.egg-info'.format(pkg)
    egg_info_dir = site_packages.glob(egg_info_pattern)
    entry_points_file = site_packages / next(egg_info_dir) / 'entry_points.txt'

    if entry_points_file.is_file():
        config = configparser.ConfigParser()
        config.read(str(entry_points_file))
        scripts = config['console_scripts']
        return list(scripts.keys())
    else:
        return None


def hack_shebang(pkg):
    """Correct the shebang for console script"""
    cwd = Path.cwd()
    base = cwd / '.venv/{{ cookiecutter.repo_name }}'
    scripts = base / 'bin'

    orig = scripts / Path(pkg)
    new = cwd / Path('temp')

    with orig.open(mode='r') as source:
        source.readline()
        with new.open(mode='w') as dest:
            dest.write('#!/usr/bin/env python\n')
            shutil.copyfileobj(source, dest)
    new.replace(orig)
    orig.chmod(0o500)



def run():
    """Main loop."""
    Undefined = None # pylint: disable=invalid-name, unused-variable
    repo_dir = None
    repo_dir = {{ repo_dir | pprint }}

    context = get_context()
    dump_context(context, 'project.d/cookiecutter.json')
    prune_empty_files()
    copy_license(repo_dir, context['license'])

    create_venv()

    install_package('invoke')


if __name__ == '__main__':
    run()
