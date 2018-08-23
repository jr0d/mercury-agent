import unittest

import mock

from mercury_agent.hardware.wipers.base import BaseWiper


class TestBaseWiper(unittest.TestCase):

    @mock.patch('mercury_agent.hardware.wipers.base.UDevHelper')
    @mock.patch('mercury_agent.hardware.wipers.base.run')
    def test_utility_exec(self, mock_run, mock_udev):
        BaseWiper().utility_exec("ls -a")
        mock_run.assert_called_once_with("ls -a", ignore_error=False, raise_exception=True)
