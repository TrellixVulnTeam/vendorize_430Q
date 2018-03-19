import click
import os

import vendorize


_ALLOWED_HOSTS = [
    'launchpad.net', 'keyserver.ubuntu.com', 'bazaar.launchpad.net',
    'git.launchpad.net', 'api.launchpad.net', 'api.snapcraft.io',
    'search.apps.ubuntu.com', 'archive.ubuntu.com', 'security.ubuntu.com'
    ]


@click.command()
@click.version_option(version='0.1')
@click.option('--dry-run', '-n', is_flag=True, help='Just verify what to do')
@click.option('--debug', '-d', is_flag=True, help='Debug')
@click.argument('project_folder',
                type=click.Path(exists=True), default=os.getcwd())
@click.option('target_branch', '-t', default=None, help='Target branch')
@click.option('host', '-h', default=_ALLOWED_HOSTS, help='Allowed host',
              multiple=True)
def run(dry_run, debug, project_folder, target_branch, host):
    os.chdir(project_folder)
    processor = vendorize.Processor(
        project_folder=os.path.abspath(project_folder),
        target=target_branch,
        dry_run=dry_run, debug=debug,
        allowed_hosts=list(host)
        )
    with processor.discover_snapcraft_yaml() as f:
        processor.process_yaml(f)


if __name__ == '__main__':
    run(prog_name='vendorize')
