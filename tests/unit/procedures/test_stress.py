import mock

from mercury.common.helpers.cli import CLIResult
from mercury_agent.procedures.stress import Stress

from tests.unit import base


class TestStress(base.MercuryAgentUnitTest):

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_get_system_memory(self, mock_cli, mock_os):
        s = Stress()

        mock_cli.run = mock.Mock(return_value=CLIResult(
            'MemFree:          33554432 kB', '', 0))

        self.assertEqual(s.get_system_memory(), '32G')

    @mock.patch('mercury_agent.procedures.stress.os')
    def test_kill_all(self, mock_os):
        Stress()
        mock_os.system()

        mock_os.system.assert_called_once_with()
        mock_os.return_value = CLIResult('', '', 0)

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_memory_stress(self, mock_cli, mock_os):
        s = Stress()

        cmd = '{0} --vm 1 --vm-bytes {1} --vm-hang 5 -t {2}'.format(
            '/usr/bin/stress', '1024M', 5)
        mock_cli.run = mock.Mock()
        s.memory_stress(timeout=5)

        mock_cli.run.assert_called_with(cmd)

    @mock.patch('mercury_agent.procedures.stress.os')
    @mock.patch('mercury_agent.procedures.stress.cli')
    def test_cpu_stress(self, mock_os, mock_cli):
        s = Stress()
        s.cpu_stress(timeout=5)
