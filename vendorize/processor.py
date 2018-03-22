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
import contextlib
import importlib
import yaml
from urllib.parse import urlparse
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from typing import List


import vendorize.git


class Processor:
    def __init__(self, *,
                 project_folder: str, target: str,
                 allowed_hosts: List[str],
                 dry_run: bool, debug: bool) -> None:
        self.project_folder = project_folder
        self.target = target
        self.clone_url = target.replace('git+ssh://', 'https://')
        self.allowed_hosts = allowed_hosts
        self.dry_run = dry_run
        self.debug = debug

        self.git = vendorize.git.Git(self)
        self.branches = {}  # type: dict

        if self.host_not_vendorized(self.target):
            raise click.UsageError(
                '{!r} is not in the allowed hosts'.format(self.clone_url))

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
            self.prepare_source([data['name']], vendored_source,
                                commit='Vendor {}'.format(data['name']))
        for branch in self.branches:
            self.git.upload_branch(self.branches[branch], branch)

    def process_part(self, part, part_data, data):
        source = part_data.get('source', '.')
        source_copy = os.path.join(self.project_folder,
                                   'parts', part, 'src')
        if self.host_not_vendorized(source):
            if self.debug:
                click.secho('Source: {!r}'.format(source), fg='blue')
            if not self.dry_run and not os.path.exists(source_copy):
                if 'git' in source:
                    os.makedirs(source_copy)
                    self.git.clone(source, source_copy)
                elif os.getenv('SNAP_NAME') != 'vendorize':
                    os.chdir(self.project_folder)
                    subprocess.check_call(['snapcraft', 'pull', part])
                else:
                    self.die("Unsupported source {!r}".format(source))
            part_data['source'] = self.prepare_source(
                [data['name'], part], source_copy)
        plugin = part_data.get('plugin')
        if plugin:
            part_processor = self.load_plugin(plugin, data, part, source)
            if part_processor:
                part_data['python-packages'] = part_processor.process()
            elif plugin not in ['copy', 'dump', 'nil']:
                self.die("No vendoring for {!r}".format(plugin))
        else:
            self.die("No vendoring for remote parts")

    def load_plugin(self, plugin: str, data: dict, part: str, source: str):
        with contextlib.suppress(ImportError):
            module = importlib.import_module('vendorize.plugins.' + plugin)
            for v in vars(module).values():
                if isinstance(v, type):
                    return v(self, part, data['parts'][part], source)

    def die(self, message):
        print()
        click.secho('Error: {}'.format(message), fg='red')
        sys.exit(1)

    def copy_source(self, source, destination):
        os.makedirs(destination, exist_ok=True)
        with click.progressbar(os.listdir(path=source), label='Copying folder',
                               item_show_func=lambda x: x) as bar:
            for f in bar:
                if f == 'snap':
                    continue
                a = os.path.join(source, f)
                b = os.path.join(destination, f)
                if os.path.isdir(a):
                    shutil.copytree(a, b)
                else:
                    shutil.copy(a, b)

    def prepare_source(self, path: list, copy: str,
                       *, init=False, commit: str=None):
        branch = '_'.join(path)
        source_schema = '{}@{}'.format(self.clone_url, branch)
        if self.debug:
            click.secho('Preparing {!r}'.format(copy), fg='yellow')
        if not self.dry_run:
            self.git.prepare_branch(copy, branch, init=init, commit=commit)
        self.branches[branch] = copy
        return source_schema

    def host_not_vendorized(self, location):
        url = urlparse(location)
        host = url.netloc
        return host and host not in self.allowed_hosts
