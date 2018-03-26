import os
import subprocess


import vendorize.processor  # noqa: F401


class Git:
    def __init__(self, processor: 'vendorize.processor.Processor') -> None:
        self.processor = processor

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
            self.processor.die('You need to set REAL_NAME and EMAIL_ADDRESS')

        try:
            os.listdir('/home/{}/.ssh'.format(os.getenv('USER')))
        except PermissionError:
            if os.getenv('SNAP_NAME') == 'vendorize':
                self.processor.die(
                    'Please run "sudo snap connect {}:ssh-keys"'.format(
                        os.getenv('SNAP_NAME')))
            else:
                self.processor.die('No SSH configuration found')

    def clone(self, source: str, folder: str):
        try:
            subprocess.check_call(['git', 'clone', source, folder])
        except subprocess.CalledProcessError as e:
            self.processor.die('{}'.format(' '.join(e.cmd)))

    def prepare_branch(self, folder: str, branch: str,
                       *, init=False, commit: str=None):
        try:
            with self.processor.chdir(folder):
                if init:
                    subprocess.check_call(['git', 'init'])
                subprocess.check_call(['git', 'checkout', '-B', branch])
                if commit:
                    self.set_identity()
                    subprocess.check_call(['git', 'add', '--all'])
                    subprocess.check_call(['git', 'commit', '--allow-empty',
                                           '-m', commit])
        except subprocess.CalledProcessError as e:
            self.processor.die('{}'.format(' '.join(e.cmd)))

    def upload_branch(self, folder: str, branch: str):
        self.processor.logger.debug('Uploading {!r}'.format(branch))
        try:
            if not self.processor.dry_run:
                with self.processor.chdir(folder):
                    subprocess.check_call(['git', 'push', '-u',
                                           self.processor.target, branch])
        except subprocess.CalledProcessError as e:
            self.processor.die('{}'.format(' '.join(e.cmd)))

    def set_identity(self):
        subprocess.check_call(['git', 'config', '--global',
                               'user.name', self.name])
        subprocess.check_call(['git', 'config', '--global',
                               'user.email', self.email])
