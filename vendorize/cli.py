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
import os
import socket

import vendorize.processor


_ALLOWED_HOSTS = [
    'launchpad.net', 'keyserver.ubuntu.com', 'bazaar.launchpad.net',
    'git.launchpad.net', 'api.launchpad.net', 'api.snapcraft.io',
    'search.apps.ubuntu.com', 'archive.ubuntu.com', 'security.ubuntu.com'
    ]


def validate_repository(ctx, param, value):
    for prefix in ['git+ssh://']:
        if value.startswith(prefix):
            return value
    raise click.BadParameter('{} is not a recognized URL'.format(value))


def validate_host(ctx, param, value):
    for host in value:
        try:
            socket.gethostbyname(host)
        except socket.gaierror:
            raise click.BadParameter('{} is not a valid hostname'.format(host))
    return list(value)


@click.command()
@click.version_option(version='0.1')
@click.option('--dry-run', '-n', is_flag=True, help='Just verify what to do')
@click.option('--debug', '-d', is_flag=True, help='Debug')
@click.argument('target_repository', callback=validate_repository)
@click.argument('project_folder',
                type=click.Path(exists=True), default=os.getcwd())
@click.option('host', '-h', default=_ALLOWED_HOSTS, help='Allowed host',
              metavar='<hosts>', multiple=True, callback=validate_host)
def run(dry_run, debug, target_repository, project_folder, host):
    """Vendorize a snap and all its dependencies to a specified repository.

    \b
    Examples:
        vendorize git+ssh://git.launchpad.net/~user
        vendorize git+ssh://git.launchpad.net/~user mysnap
        vendorize -n git+ssh://git.launchpad.net/~user
        vendorize -n git+ssh://git.launchpad.net/~user
        vendorize -h git.launchpad.net git+ssh://git.launchpad.net/~user
    """

    processor = vendorize.processor.Processor(
        project_folder=os.path.abspath(project_folder),
        target=target_repository,
        dry_run=dry_run, debug=debug,
        allowed_hosts=host
        )
    with processor.discover_snapcraft_yaml() as f:
        processor.process_yaml(f)
