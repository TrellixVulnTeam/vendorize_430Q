from unittest.mock import patch, call
import os
import textwrap


import fixture_setup
import vendorize.plugins.python


class PythonPartTestCase(fixture_setup.ProcessorBaseTestCase):

    scenarios = [
        ('no-packages', dict(packages=[], requirements=[], setup_py=None,
                             branches=[])),
        ('pypi-package', dict(packages=['foo'], requirements=[], setup_py=None,
                              branches=['{url}@test_python_packages_foo'])),
        ('requirements-pypi-package', dict(
            packages=[], requirements=['foo'], setup_py=None,
            branches=['{url}@test_python_packages_foo'])),
        ('requirements-git-package', dict(
            packages=[], setup_py=None,
            requirements=['-e git+https://githubcom/foo/bar#egg=bar'],
            branches=['{url}@test_python_packages_bar'])),
        ('setup.py-no-packages', dict(
            packages=[], requirements=[], setup_py=None,
            branches=[])),
        ('setup.py-pypi-package', dict(
            packages=[], requirements=[], setup_py=['foo'],
            branches=['{url}@test_python_packages_foo'])),
    ]

    def setUp(self):
        super().setUp()
        self.part_data['plugin'] = 'python'
        self.part_data['python-packages'] = self.packages
        self.processor = self.make_processor(dry_run=False)
        self.plugin = self.processor.load_plugin(
            self.part_data['plugin'], self.data, 'test',
            self.part_data.get('source', '.'))
        self.all_packages = self.packages + self.requirements
        if self.setup_py:
            self.all_packages += self.setup_py
        self.all_packages = self.all_packages
        self.branches = [branch.format(url=self.processor.clone_url)
                         for branch in self.branches]
        if self.requirements:
            with open('requirements.txt', 'w') as f:
                for requirement in self.requirements:
                    f.write('{}\n'.format(requirement))
            self.part_data['requirements'] = 'requirements.txt'
        if self.setup_py is not None:
            with open('setup.py', 'w') as f:
                if self.setup_py:
                    packages = ['"{}"'.format(p) for p in self.setup_py]
                    install_requires = ' install_requires=[{}],'.format(
                        ','.join(packages))
                else:
                    install_requires = ''
                f.write(textwrap.dedent('''
                    from setuptools import setup, find_packages
                    setup(name="test",
                          version="0.1",{}
                          packages=find_packages(exclude=["tests"]),
                    )
                    '''.format(install_requires)))

    def test_get_packages(self):
        self.assertEqual(self.plugin.get_packages(), self.all_packages)

    @patch.object(vendorize.git.Git, 'prepare_branch')
    @patch.object(vendorize.plugins.python.Python, 'download_packages')
    @patch('shutil.unpack_archive')
    @patch('os.path.isdir')
    @patch('os.listdir')
    def test_process(self, mock_listdir, mock_isdir,
                     mock_unpack, mock_download, mock_git):
        folders = [a for a in self.all_packages]
        non_git_packages = self.packages + (self.setup_py or [])
        for requirement in self.requirements:
            if '#egg=' not in requirement:
                non_git_packages.append(requirement)
            folders.append(requirement.split('#egg=')[-1])
        archives = ['{}.tar.gz'.format(a) for a in non_git_packages]
        mock_listdir.return_value = folders + archives
        mock_isdir.side_effect = lambda x: not x.endswith('.tar.gz')
        self.plugin.process()
        mock_download.assert_has_calls([call(self.all_packages)])
        mock_unpack.assert_has_calls([
            call(os.path.join(self.plugin.python_cache, archive),
                 self.plugin.python_cache) for archive in archives])
        self.assertEqual(self.part_data.get('requirements'), None)
