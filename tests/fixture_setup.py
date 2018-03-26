import testscenarios
import testtools
import os
import tempfile
import yaml


import vendorize.processor


class ProcessorBaseTestCase(testscenarios.WithScenarios, testtools.TestCase):

    def setUp(self):
        super().setUp()

        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(tempfile.mkdtemp(dir=os.environ.get('TMPDIR')))

        # Create test snap
        os.makedirs(os.path.join(os.getcwd(), 'snap'))
        self.data = {
            'name': 'test',
            'version': '0.1',
            'parts': {
                'test': {
                    'plugin': 'nil',
                }
            },
        }
        self.part_data = self.data['parts']['test']
        self.snapcraft_yaml = os.path.join(
            os.getcwd(), 'snap', 'snapcraft.yaml')
        with open(self.snapcraft_yaml, 'w') as snapcraft_yaml_file:
            yaml.dump(self.data, snapcraft_yaml_file,
                      default_flow_style=False)

    def make_processor(self, *,
                       target='git+ssh://git.launchpad.net/~user/test',
                       allowed_hosts=['git.launchpad.net'],
                       dry_run=True):
        return vendorize.processor.Processor(
            project_folder=os.getcwd(),
            target=target,
            allowed_hosts=allowed_hosts,
            dry_run=dry_run,
            debug=False)
