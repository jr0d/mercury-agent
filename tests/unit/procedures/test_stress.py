import mock

from mercury.common.helpers.cli import CLIResult
from mercury_agent.procedures.stress import Stress

from tests.unit import base


class TestStress(base.MercuryAgentUnitTest):

    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_memory_stress(self, mock_cli):
        mock_cli.find_in_path.return_value = '/usr/bin/stress'
        s = Stress()
        s.memory_stress = mock.Mock()
        s.memory_stress.assert_called_with(seconds=60)
        mock_cli.find_in_path.return_value = None

    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_cpu_stress(self, mock_cli):
        mock_cli.find_in_path.return_value = '/usr/bin/stress'
        s = Stress()
        s.cpu_stress = mock.Mock()
        s.cpu_stress.assert_called_with(seconds=60)
        mock_cli.find_in_path.return_value = None

    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_get_system_memory(self, mock_cli):
        mock_cli.run.return_value = CLIResult('', '', 0)
        mock_cli.find_in_path.return_value = '/proc/meminfo'
        s = Stress()

        assert s.get_system_memory() == '1234G'
        mock_cli.run.return_value = CLIResult('1234G', '', 0)

    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_kill_all(self, mock_cli):
        mock_cli.run.return_value = CLIResult('', '', 0)
        s = Stress()

        assert s.killall() == ''

