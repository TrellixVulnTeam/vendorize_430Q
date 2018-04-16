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
from collections import OrderedDict
import contextlib
import importlib
import logging
import yaml
import os
from typing import Any, Dict, IO, List


import vendorize.git
import vendorize.log
import vendorize.source


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

        self.logger = vendorize.log.get_logger(__name__)
        if debug:
            self.logger.setLevel(logging.DEBUG)

        self.git = vendorize.git.Git()
        self.branches = {}  # type: dict

        if vendorize.util.host_not_vendorized(self.target, self.allowed_hosts):
            raise click.UsageError(
                '{!r} is not in the allowed hosts'.format(self.clone_url))

        self.vendored_source = os.path.join(
            self.project_folder, 'snap', 'vendoring', 'src')
        if not self.dry_run:
            os.makedirs(self.vendored_source, exist_ok=True)

    @contextlib.contextmanager
    def discover_snapcraft_yaml(self):
        # Known snapcraft.yaml file locations
        paths = ['snapcraft.yaml', '.snapcraft.yaml', 'snap/snapcraft.yaml']
        for path in paths:
            if os.path.exists(os.path.join(self.project_folder, path)):
                yield path
                return
        self.die('No snapcraft.yaml found')

    def process_yaml(self, path: str):
        if not self.dry_run and not os.listdir(self.vendored_source):
            self.copy_source(self.project_folder, self.vendored_source)

        if os.path.isabs(path):
            self.die('Path {!r} is not relative'.format(path))
        with open(os.path.join(self.project_folder, path)) as f:
            data = self.ordered_yaml_load(f)
            self.logger.info('Processing {!r}'.format(path))
            # Allowed hosts for this snap
            self.allowed_hosts = data.get('vendoring', self.allowed_hosts)
            data['vendoring'] = self.allowed_hosts
            parts = data['parts']
            with click.progressbar(data['parts'], label='Processing parts',
                                   item_show_func=lambda x: x) as bar:
                for part in bar:
                    self.process_part(part, parts[part], data)

        self.logger.info('Preparing project')
        if self.dry_run:
            return
        with open(os.path.join(self.vendored_source, path), 'w') as f:
            self.ordered_yaml_dump(data, f, default_flow_style=False)
            self.prepare_source(['master'], self.vendored_source,
                                commit='Vendor {}'.format(data['name']))
        for branch in self.branches:
            self.logger.debug('Uploading {!r}'.format(branch))
            if self.dry_run:
                continue
            self.git.upload_branch(self.branches[branch], branch, self.target)

    def ordered_yaml_load(self, stream: IO[str]) -> Dict[str, Any]:
        class OrderedSafeLoader(yaml.SafeLoader):
            pass

        def construct_mapping(loader: yaml.Loader, node: yaml.Node):
            loader.flatten_mapping(node)
            return OrderedDict(loader.construct_pairs(node))
        OrderedSafeLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            construct_mapping)
        return yaml.load(stream, OrderedSafeLoader)

    def ordered_yaml_dump(self, data: Dict[str, Any],
                          stream: IO[str], **kwargs) -> None:
        class OrderedDumper(yaml.SafeDumper):
            pass

        def dict_representer(dumper: yaml.Dumper, data: Dict[str, Any]):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                data.items())
        OrderedDumper.add_representer(OrderedDict, dict_representer)
        yaml.dump(data, stream, OrderedDumper, **kwargs)

    def process_part(self, part, part_data, data):
        source, source_copy = self.process_part_source(part, part_data)
        plugin = part_data.get('plugin')
        if plugin:
            part_processor = self.load_plugin(
                plugin, data, part, source.source, source_copy)
            if part_processor:
                # Plugins may modify the sources
                source.should_vendor = True
                if not self.dry_run:
                    part_processor.process()
            elif plugin not in ['copy', 'dump', 'nil']:
                self.die("No vendoring for {!r}".format(plugin))
        else:
            self.die("No vendoring for remote part {!r}".format(part))
        if source.should_vendor:
            repo, branch = self.prepare_source(
                [data['name'], part], source_copy,
                commit='Vendor {}'.format(part)).split('@')
            part_data['source'] = repo
            part_data['source-branch'] = branch
            if 'source-tag' in part_data:
                del part_data['source-tag']

    def process_part_source(self, part: str, part_data: dict) -> tuple:
        source = vendorize.source.PartSource(
            part_data, self.project_folder, self.allowed_hosts)
        self.logger.debug('Source: {!r}'.format(source.source))
        if source.type == 'local':
            source_copy = os.path.join(self.vendored_source, source.source)
        else:
            source_copy = os.path.join(self.project_folder,
                                       'parts', part, 'src')
            if not self.dry_run:
                source.fetch(source_copy)
        return source, source_copy

    def load_plugin(self, plugin: str, data: dict, part: str,
                    source: str, copy: str):
        with contextlib.suppress(ImportError):
            module = importlib.import_module('vendorize.plugins.' + plugin)
            for v in vars(module).values():
                if isinstance(v, type):
                    return v(self, part, data['parts'][part], source, copy)

    def die(self, message):
        raise click.ClickException(message)

    def copy_source(self, source: str, destination: str):
        self.logger.debug('Copying {!r} to {!r}'.format(source, destination))
        # If this is a git repository we can clone it efficiently
        if os.path.exists(os.path.join(source, '.git')):
            self.git.clone(source, destination)
        else:
            self.die('Cannot copy {!r}'.format(source))

    def prepare_source(self, path: list, copy: str,
                       *, init=False, commit: str=None):
        branch = '_'.join(path)
        self.logger.debug('Preparing {!r}'.format(copy))
        if not self.dry_run:
            self.git.prepare_branch(copy, branch, init=init, commit=commit)
        self.branches[branch] = copy
        return '{}@{}'.format(self.clone_url, branch)
