import unittest
import subprocess


class StaticTestCase(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.paths = ['vendorize', 'tests']

    def run_checker(self, cmd):
        try:
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            self.fail('{}\n{}'.format(' '.join(e.cmd), e.output.decode()))

    def test_flake8(self):
        self.run_checker(['flake8', '--max-complexity=10'] + self.paths)

    def test_mypy(self):
        options = [
            '--ignore-missing-imports',
            '--follow-imports=silent',
        ]
        self.run_checker(['mypy'] + options + self.paths)

    def test_codespell(self):
        skip = '*.so*,*.snap,*.gpg,*.pyc,.git,parts,prime,stage'
        self.run_checker(['codespell', '-S', skip, '-q4'])
