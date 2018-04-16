from testtools.matchers import FileContains
from unittest.mock import patch
import click
import os
import textwrap


from tests import fixture_setup


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

    @patch('subprocess.check_call')
    def test_yaml_order(self, mock_check_call):
        contents = textwrap.dedent('''\
            name: test
            version: 1.0
            parts:
              foo:
                plugin: nil
            vendoring:
            - git.launchpad.net
            ''')
        with open(self.snapcraft_yaml, 'w') as f:
            f.write(contents)
        processor = self.make_processor(dry_run=False)

        vendored_snap_folder = os.path.join(processor.vendored_source, 'snap')
        os.makedirs(vendored_snap_folder, exist_ok=True)
        vendored_snapcraft_yaml = os.path.join(
            vendored_snap_folder, 'snapcraft.yaml')
        with open(vendored_snapcraft_yaml, 'w') as f:
            f.write(contents)

        processor.process_yaml('snap/snapcraft.yaml')
        self.assertThat(vendored_snapcraft_yaml, FileContains(contents))


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
