import time
import unittest

import mock

from mercury_agent.hardware.wipers.lsi import LSIWiper


class TestLSIWiper(unittest.TestCase):

    def setUp(self):
        self.mock_udev = mock.Mock()
        self.patch_udev = mock.patch(
            'mercury_agent.hardware.wipers.base.UDevHelper', return_value=self.mock_udev
        )
        self.patch_udev.start()
        self.mock_lsi_raid = mock.Mock()
        self.patch_lsi_raid = mock.patch(
            'mercury_agent.hardware.wipers.lsi.LSIRaid', return_value=self.mock_lsi_raid
        )
        self.mock_lsi = self.patch_lsi_raid.start()
        self.patch_config = mock.patch(
            'mercury_agent.hardware.wipers.lsi.get_configuration',
            return_value=mock.Mock(
                agent=mock.Mock(
                    hardware=mock.Mock(
                        megacli_bin='/usr/local/sbin/megacli',
                        raid=mock.Mock(clear_delay=10)
                    )
                )
            )
        )
        self.patch_config.start()
        self.lsi_wiper = LSIWiper()
        self.patch_time = mock.patch('mercury_agent.hardware.wipers.lsi.time')
        self.mock_time = self.patch_time.start()

    def tearDown(self):
        self.patch_udev.stop()
        self.patch_lsi_raid.start()
        self.patch_config.stop()
        self.patch_time.stop()

    def test_get_raid_clear_delay(self):
        result = self.lsi_wiper.get_raid_clear_delay()
        self.assertEqual(result, 10)

    @mock.patch('mercury_agent.hardware.wipers.lsi.clear_lsi')
    def test_clear_configs(self, mock_clear_lsi):
        self.lsi_wiper.clear_configs()
        mock_clear_lsi.assert_called_once_with(
            self.mock_lsi_raid, self.lsi_wiper.adapter)

    def test_clear_devices(self):
        mock_utility_exec = mock.Mock()
        self.lsi_wiper.utility_exec = mock_utility_exec
        self.lsi_wiper.clear_devices()
        mock_utility_exec.assert_called_once_with(
            "/sbin/dmsetup remove_all --force")
        self.mock_time.sleep.assert_called_once()

    def test_create_array(self):
        self.mock_lsi_raid.get_physical_disks.return_value = [
            {'device_id': 'device1'}]
        self.mock_lsi_raid.create_array.return_value = {}
        self.lsi_wiper.create_array()
        self.mock_lsi_raid.create_array.assert_called_once_with(0, ['device1'])
        self.mock_time.sleep.assert_called_once()

    def test_create_array_error(self):
        self.mock_lsi_raid.get_physical_disks.return_value = [
            {'device_id': 'device1'}]
        self.mock_lsi_raid.create_array.return_value = {
            'error': 'ERROR', 'command': 'create_array', 'stdout': None, 'stderr': 'ERROR'
        }
        self.assertRaises(Exception, self.lsi_wiper.create_array)
        self.mock_lsi_raid.create_array.assert_called_once_with(0, ['device1'])
        self.mock_time.sleep.assert_called_once()

    @mock.patch('mercury_agent.hardware.wipers.lsi.multiprocessing')
    def test_fill_disks(self, mock_multiprocessing):
        self.mock_udev.discover_valid_storage_devices.return_value = [
            {'DEVNAME': 'udisk1', 'ID_VENDOR': 'DELL'}]
        self.mock_time.time.return_value = time.time()
        mock_fill_disk = mock.Mock()
        self.lsi_wiper.fill_disk = mock_fill_disk
        # patching is_alive to False in order to prevent the test/process from running forever
        mock_process = mock.Mock(is_alive=mock.Mock(return_value=False))
        mock_multiprocessing.Process.return_value = mock_process

        self.lsi_wiper.fill_disks()

        mock_multiprocessing.Process.assert_called_once_with(
            target=mock_fill_disk, args=['udisk1', '4M']
        )
        self.assertEqual(len(self.lsi_wiper.fill_processes), 1)

    def test_fill_disk(self):
        mock_utility_exec = mock.Mock()
        self.lsi_wiper.utility_exec = mock_utility_exec

        self.lsi_wiper.fill_disk(disk='udisk11', bs='4M')
        mock_utility_exec.assert_called_once_with(
            "dd if=/dev/zero of=%s bs=%s" % ('udisk11', '4M'), ignore_error=True
        )

    def test_init_logical_drives(self):
        self.lsi_wiper.init_logical_drives()
        self.mock_lsi_raid.init_logical_drives.assert_called_once()

    def test_wipe(self):
        mock_clear_configs = mock.Mock()
        self.lsi_wiper.clear_configs = mock_clear_configs
        mock_clear_devices = mock.Mock()
        self.lsi_wiper.clear_devices = mock_clear_devices
        mock_create_array = mock.Mock()
        self.lsi_wiper.create_array = mock_create_array
        mock_fill_disks = mock.Mock()
        self.lsi_wiper.fill_disks = mock_fill_disks
        mock_init_logical_drives = mock.Mock()
        self.lsi_wiper.init_logical_drives = mock_init_logical_drives

        self.lsi_wiper.wipe()
        self.assertEqual(mock_clear_configs.call_count, 2)
        self.assertEqual(mock_clear_devices.call_count, 2)
        mock_create_array.assert_called_once()
        mock_fill_disks.assert_called_once()
        mock_init_logical_drives.assert_called_once()
