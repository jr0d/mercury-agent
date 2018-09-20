import mock

from mercury.common.helpers.cli import CLIResult
from mercury_agent.procedures.stress import Stress

from tests.unit import base


class TestStress(base.MercuryAgentUnitTest):

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_get_system_memory(self, mock_os, mock_cli):
        s = Stress()
        s.get_system_memory()

        mock_cli.run()

        mock_cli.run.assert_called_once()
        mock_cli.return_value = CLIResult('1G', '', 0)

    @mock.patch('mercury_agent.procedures.stress.os')
    def test_kill_all(self, mock_os):
        Stress()
        mock_os.system()

        mock_os.system.assert_called_once_with()
        mock_os.return_value = CLIResult('', '', 0)

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_memory_stress(self, mock_os, mock_cli):
        s = Stress()
        s.memory_stress(timeout=5)

        mock_cli.run()

        mock_cli.run.assert_called_once()

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_cpu_stress(self, mock_os, mock_cli):
        s = Stress()
        s.cpu_stress(timeout=5)

        mock_cli.run()

        mock_cli.run.assert_called_once()
