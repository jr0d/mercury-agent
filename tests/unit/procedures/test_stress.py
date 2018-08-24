import mock

from mercury.common.helpers.cli import CLIResult
from mercury_agent.procedures.stress import Stress

from tests.unit import base


class TestStress(base.MercuryAgentUnitTest):

    @mock.patch('mercury_agent.hardware.raid.interfaces.megaraid.stress.cli')
    def stress_test(self, mock_cli):
        mock_cli.run.return_value = CLIResult('', '', 0)
        mock_cli.find_in_path.return_value = '/usr/bin/stress'

        s = Stress()

        assert s.start(seconds=60)


