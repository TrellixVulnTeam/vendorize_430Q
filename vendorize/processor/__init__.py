#!/usr/bin/env python3
# -*- mode: python; -*-
#
# Copyright 2018 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This package is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import click
# from launchpadlib.launchpad import Launchpad
import yaml
# import requests
from urllib.parse import urlparse
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from typing import List

# launchpad = Launchpad.login_anonymously(
#     'snapcraft-yaml-usage', 'production', version='devel')


class Processor:
    def __init__(self, *,
                 project_folder: str, target: str,
                 allowed_hosts: List[str],
                 dry_run: bool, debug: bool) -> None:
        self.project_folder = project_folder
        if not target:
            target = 'git+ssh://git.launchpad.net/~kalikiana'
        self.target = target
        self.allowed_hosts = allowed_hosts
        self.dry_run = dry_run
        self.debug = debug

    @contextmanager
    def discover_snapcraft_yaml(self):
        # Known snapcraft.yaml file locations
        paths = ['snapcraft.yaml', '.snapcraft.yaml', 'snap/snapcraft.yaml']
        for path in paths:
            if os.path.exists(os.path.join(self.project_folder, path)):
                yield path
                return
        self.die('No snapcraft.yaml found')

    def process_yaml(self, path):
        vendoring = os.path.join(self.project_folder, 'snap', 'vendoring')
        os.makedirs(vendoring, exist_ok=True)
        vendored_source = os.path.join(self.project_folder,
                                       'snap', 'vendoring', 'src')
        if not os.path.exists(vendored_source):
            os.makedirs(os.path.join(vendored_source, os.path.dirname(path)),
                        exist_ok=True)
            self.copy_source(self.project_folder, vendored_source)

        with open(path) as f:
            data = yaml.load(f)
            click.secho('Processing {!r}...'.format(path), fg='green')
            # Allowed hosts for this snap
            self.allowed_hosts = data.get('vendoring', self.allowed_hosts)
            data['vendoring'] = self.allowed_hosts
            parts = data['parts']
            with click.progressbar(data['parts'], label='Processing parts',
                                   item_show_func=lambda x: x) as bar:
                for part in bar:
                    self.process_part(part, parts[part], data)

        click.secho('Preparing project'.format(path), fg='green')
        if os.path.isabs(path):
            self.die('Path {!r} is not relative'.format(path))
        with open(os.path.join(vendored_source, path), 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
            self.upload_source([data['name']], vendored_source,
                               commit='Vendor {}'.format(data['name']))

    def process_part(self, part, part_data, data):
        source = part_data.get('source', '.')
        source_copy = os.path.join(self.project_folder,
                                   'parts', part, 'src')
        if self.host_not_vendorized(source):
            if self.debug:
                click.secho('Source: {!r}'.format(source), fg='blue')
            if not self.dry_run and not os.path.exists(source_copy):
                if False and 'git' in source:
                    os.makedirs(source_copy)
                    subprocess.check_call(['git', 'clone',
                                           source, source_copy])
                else:
                    os.chdir(self.project_folder)
                    subprocess.check_call(['snapcraft', 'pull', part])
            part_data['source'] = self.upload_source(
                [data['name'], part], source_copy)
        # FIXME: plugin is required BUT we're not parsing remote parts
        plugin = part_data.get('plugin', 'nil')
        if plugin in ['python', 'python2', 'python3']:
            part_data['python-packages'] = self.process_python(
                data, part, source,
                os.path.join(self.project_folder, 'parts', part))
        elif plugin not in ['copy', 'dump', 'nil']:
            self.die("No vendoring for {!r}".format(plugin))

    def die(self, message):
        print()
        click.secho('Error: {}'.format(message), fg='red')
        sys.exit(1)

    def copy_source(self, source, destination):
        os.makedirs(destination, exist_ok=True)
        with click.progressbar(os.listdir(path=source), label='Copying folder',
                               item_show_func=lambda x: x) as bar:
            for f in bar:
                # FIXME: Hack to avoid infinitely recursing into snap/vendoring
                if f == 'snap':
                    continue
                a = os.path.join(source, f)
                b = os.path.join(destination, f)
                if os.path.isdir(a):
                    shutil.copytree(a, b)
                else:
                    shutil.copy(a, b)

    def process_python(self, data, part, source, source_copy):
        branches = []
        part_data = data['parts'][part]
        python_packages = part_data.get('python-packages', [])
        requirements = part_data.get('requirements')
        if requirements:
            if self.host_not_vendorized(requirements):
                if self.debug:
                    # FIXME
                    click.secho('* Requirements need to be moved', fg='yellow')
            with open(requirements) as r:
                for line in r:
                    package = line.strip().split()[-1]
                    python_packages.append(package)
        self.packages_from_setup_py(os.path.join(source, 'setup.py'))
        if python_packages:
            python_cache = os.path.join(source_copy, 'python-packages')
            for package in python_packages:
                branch = self.upload_python_package(
                    [data['name'], part, 'python-packages', package],
                    os.path.join(python_cache, package))
                branches.append(branch)
        return branches

    def upload_python_package(self, path, copy):
        package = path[-1]
        if not self.dry_run:
            if not os.path.exists(copy):
                os.makedirs(copy)
            subprocess.check_call(['pip', 'download', '-d', copy, package])
            os.chdir(copy)
            subprocess.check_call(['git', 'init'])
        return self.upload_source(path, copy,
                                  commit='Vendor {}'.format(package))

    def upload_source(self, path, copy, commit=None):
        source_schema = '{}/{}'.format(self.target, path[0])
        branch = '_'.join(path)
        if self.debug:
            click.secho('* Uploading {!r} to {!r}'.format(copy, source_schema),
                        fg='yellow')
        if not self.dry_run:
            os.chdir(copy)
            subprocess.check_call(['git', 'checkout', '-B', branch])
            if commit:
                subprocess.check_call(['git', 'add', '--all'])
                subprocess.check_call(['git', 'commit', '--allow-empty',
                                       '-m', commit])
            subprocess.check_call(['git', 'push', '-u', source_schema, branch])
        return '{}@{}'.format(self.target, branch)

    def packages_from_setup_py(self, setup_py):
        if not os.path.exists(setup_py):
            return

        # Try using setuptools to get install_requires
        import setuptools

        def setup(*args, **kwargs):
            # FIXME
            print('setup: {!r}'.format(kwargs))
        setuptools.setup = setup
        try:
            setup_py_code = open(setup_py.read())
            exec(setup_py_code)
        except Exception as e:
            try:
                stripped_code = ''
                for line in open(setup_py):
                    if 'import' not in line:
                        stripped_code += line
            except Exception as e:
                # Fallback to manual scraping for install_requires
                import re
                packages = re.search(r"^install_requires=['\"]([^'\"]*)['\"]",
                                     setup_py_code, re.M)
                if packages:
                    click.secho(packages.group(1), fg='purple')
                else:
                    self.die('Failed to parse {!r}: {}'.format(setup_py, e))

    def host_not_vendorized(self, location):
        url = urlparse(location)
        host = url.netloc
        return host and host not in self.allowed_hosts
