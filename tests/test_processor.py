import click
import os


import fixture_setup


class ProcessorTestCase(fixture_setup.ProcessorBaseTestCase):

    def test_target_not_vendorized(self):
        self.assertRaises(click.UsageError,
                          self.make_processor, allowed_hosts=[])

    def test_discover_snapcraft_yaml(self):
        with self.make_processor().discover_snapcraft_yaml() as path:
            self.assertEqual(path, 'snap/snapcraft.yaml')

    def test_no_snapcraft_yaml(self):
        def discover_snapcraft_yaml():
            with self.make_processor().discover_snapcraft_yaml():
                pass

        os.remove(self.snapcraft_yaml)
        self.assertRaises(click.ClickException, discover_snapcraft_yaml)

    def test_process_yaml(self):
        self.make_processor().process_yaml('snap/snapcraft.yaml')


class PartTestCase(fixture_setup.ProcessorBaseTestCase):

    def test_process_part(self):
        self.make_processor().process_part(
            'test', self.data['parts']['test'], self.data)

    def test_process_part_unvendored_source(self):
        self.part_data['source'] = 'https://github.com/foo/bar.git'
        self.make_processor().process_part(
            'test', self.part_data, self.data)
        self.assertEqual(self.part_data['source'],
                         'https://git.launchpad.net/~user/test')
        self.assertEqual(self.part_data['source-branch'], 'test_test')
