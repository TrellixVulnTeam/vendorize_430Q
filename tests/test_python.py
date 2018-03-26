import textwrap


import fixture_setup


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
        self.processor = self.make_processor()
        self.plugin = self.processor.load_plugin(
            self.part_data['plugin'], self.data, 'test',
            self.part_data.get('source', '.'))
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

    def test_process(self):
        self.plugin.process()
        self.assertEqual(self.part_data['python-packages'], self.branches)
