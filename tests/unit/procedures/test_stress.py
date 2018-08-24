import mock

from mercury_agent.procedures.stress import Stress

from tests.unit import base


class TestStress(base.MercuryAgentUnitTest):

    @mock.patch('mercury_agent.procedures.stress.cli')
    def stress_test(self, mock_cli):
        mock_cli.find_in_path.return_value = '/usr/bin/stress'
        s = Stress()
        assert s.start(seconds=60)
        mock_cli.find_in_path.return_value = None
