import tests.fixture_setup
import os


import vendorize


class SourcesTestCase(tests.fixture_setup.ProcessorBaseTestCase):

    scenarios = [
        ('.', dict(part_data={'source': '.'}, type='local')),
        ('git', dict(part_data={
            'source': 'git@github.com:foo/bar.git'}, type='git')),
        ('git https', dict(part_data={
            'source': 'https://github.com/foo/bar.git'}, type='git')),
        ('git type', dict(part_data={
            'source': 'https://github.com/foo/bar',
            'source-type': 'git'}, type='git')),
        ('tar.xz', dict(part_data={'source': 'foo.tar.xz'}, type='tar')),
        ('tar.xz', dict(part_data={'source': 'foo.tar.xz'}, type='tar')),
        ('tar.gz', dict(part_data={'source': 'foo.tar.gz'}, type='tar')),
        ('tar.bz2', dict(part_data={'source': 'foo.tar.bz2'}, type='tar')),
    ]

    def setUp(self):
        super().setUp()
        self.part_source = vendorize.source.PartSource(
            self.part_data, os.getcwd(), [])

    def test_fetch(self):
        self.assertEqual(self.part_source.type, self.type)
