import unittest

import mock

from mercury_agent.procedures.hardware_wiper import wiper


class TestWiper(unittest.TestCase):

    @mock.patch('mercury_agent.procedures.hardware_wiper.get_subsystem_drivers')
    def test_lsi_wiper(self, mock_get_raid_drivers):
        mock_hp_handler = mock.Mock()
        mock_hp_raid = mock.Mock(handler=mock_hp_handler)
        mock_lsi_handler = mock.Mock()
        mock_megaraid = mock.Mock(handler=mock_lsi_handler)
        mock_get_raid_drivers.return_value = [mock_hp_raid, mock_megaraid]

        wiper()

        mock_hp_handler.wipe.assert_called_once()
        mock_lsi_handler.wipe.assert_called_once()
