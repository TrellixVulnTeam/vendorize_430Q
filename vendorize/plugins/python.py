import os
import pip
import setuptools


import vendorize.processor


class Python:
    def __init__(self, processor: vendorize.processor.Processor,
                 part: str, data: dict, source: str) -> None:
        self.processor = processor
        self.part = part
        self.data = data
        self.source = source

        if os.getenv('SNAP_NAME') == 'vendorize':
            # Override user agent to avoid pip searching /etc for release files
            pip.download.user_agent = lambda: 'pip/{}'.format(pip.__version__)

    def process(self):
        source_copy = os.path.join(self.processor.project_folder,
                                   'parts', self.part)
        branches = []
        python_packages = self.data.get('python-packages', [])
        requirements = self.data.get('requirements')
        if requirements:
            if self.processor.host_not_vendorized(requirements):
                if self.debug:
                    self.processor.die(
                        'External requirements are not supported')
            with open(os.path.join(
                    self.processor.project_folder, requirements)) as r:
                for line in r:
                    package = line.strip().split()[-1]
                    python_packages.append(package)
        for package in self.packages_from_setup_py():
            python_packages.append(package)
        if python_packages:
            python_cache = os.path.join(source_copy, 'python-packages')
            for package in python_packages:
                branch = self.upload_python_package(
                    [self.part, 'python_packages', package], python_cache)
                branches.append(branch)
        return branches

    def upload_python_package(self, path: list, python_cache: str):
        url = path[-1]
        if '://' in url:
            if '#egg=' in url:
                package = url.split('#egg=')[1]
            else:
                self.processor.die('Unkown package syntax {!r}'.format(url))
        else:
            package = url
        path[-1] = package
        copy = os.path.join(python_cache, package)
        if not self.processor.dry_run:
            if not os.path.exists(copy):
                os.makedirs(copy)
            pip.main(['download', '-d', copy, url])
        return self.processor.prepare_source(
            path, copy, init=True, commit='Vendor {}'.format(package))

    def packages_from_setup_py(self):
        setup_py = os.path.join(self.processor.project_folder,
                                self.source, 'setup.py')
        if not os.path.exists(setup_py):
            return []

        # Try and use setuptools to get install_requires
        def setup(*args, **kwargs):
            globals()['metadata'] = kwargs
        setuptools.setup = setup
        try:
            setup_py_code = open(setup_py).read()
            exec(setup_py_code)
            metadata = globals()['metadata']
            return metadata.get('install_requires', [])
        except Exception as e:
            self.processor.die(
                'Failed to parse {!r}: {}'.format(setup_py, e))
