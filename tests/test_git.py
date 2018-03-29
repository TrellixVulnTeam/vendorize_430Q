import fixture_setup
from unittest.mock import patch, call


class GitTestCase(fixture_setup.ProcessorBaseTestCase):

    def setUp(self):
        super().setUp()
        self.git = self.make_processor().git

    @patch('subprocess.check_call')
    def test_clone(self, mock_check_call):
        self.git.clone('source', 'folder')
        mock_check_call.assert_has_calls([
            call(['git', 'clone', '--recursive', 'source', 'folder'])
        ])
