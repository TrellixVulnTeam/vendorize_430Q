import click
import os
import subprocess


import vendorize.util


class Git:
    def __init__(self) -> None:
        name = os.getenv('REAL_NAME')
        email = os.getenv('EMAIL_ADDRESS')
        if not (name and email):
            name = None
            email = None
            try:
                name = subprocess.check_output([
                    'git', 'config', 'user.name']).decode()
                email = subprocess.check_output([
                    'git', 'config', 'user.email']).decode()
            except subprocess.CalledProcessError:
                # Values are not set in git
                pass
        if name and email:
            self.name = name
            self.email = email
        else:
            raise click.ClickException(
                'You need to set REAL_NAME and EMAIL_ADDRESS')

        try:
            os.listdir('/home/{}/.ssh'.format(os.getenv('USER')))
        except PermissionError:
            if os.getenv('SNAP_NAME') == 'vendorize':
                raise click.ClickException(
                    'Please run "sudo snap connect {}:ssh-keys"'.format(
                        os.getenv('SNAP_NAME')))
            else:
                raise click.ClickException('No SSH configuration found')

    def clone(self, source: str, folder: str, branch: str=None):
        try:
            cmd = ['git', 'clone', '--recursive', source, folder]
            if branch:
                cmd += ['--branch', branch]
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            raise click.ClickException(' '.join(e.cmd))

    def prepare_branch(self, folder: str, branch: str,
                       *, init=False, commit: str=None):
        try:
            with vendorize.util.chdir(folder):
                if init:
                    subprocess.check_call(['git', 'init'])
                subprocess.check_call(['git', 'checkout', '-B', branch])
                if commit:
                    self.set_identity()
                    subprocess.check_call(['git', 'add', '--all'])
                    subprocess.check_call(['git', 'commit', '--allow-empty',
                                           '-m', commit])
        except subprocess.CalledProcessError as e:
            raise click.ClickException(' '.join(e.cmd))

    def upload_branch(self, folder: str, branch: str, target: str):
        try:
            with vendorize.util.chdir(folder):
                subprocess.check_call(['git', 'push', '-u',
                                       target, branch])
        except subprocess.CalledProcessError as e:
            raise click.ClickException(' '.join(e.cmd))

    def set_identity(self):
        subprocess.check_call(['git', 'config', '--global',
                               'user.name', self.name])
        subprocess.check_call(['git', 'config', '--global',
                               'user.email', self.email])
