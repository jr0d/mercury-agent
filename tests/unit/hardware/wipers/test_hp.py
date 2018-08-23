import time
import unittest

import mock

from mercury_agent.hardware.wipers.hp import HPWiper


class TestHPWiper(unittest.TestCase):

    def setUp(self):
        self.mock_udev = mock.Mock()
        self.patch_udev = mock.patch(
            'mercury_agent.hardware.wipers.base.UDevHelper', return_value=self.mock_udev
        )
        self.patch_udev.start()
        self.mock_hp_raid = mock.Mock()
        self.patch_hpssa = mock.patch(
            'mercury_agent.hardware.wipers.hp.HPSSA', return_value=self.mock_hp_raid
        )
        self.mock_hpssa = self.patch_hpssa.start()
        self.patch_config = mock.patch(
            'mercury_agent.hardware.wipers.hp.get_configuration',
            return_value=mock.Mock(
                agent=mock.Mock(
                    hardware=mock.Mock(raid=mock.Mock(clear_delay=10))
                )
            )
        )
        self.patch_config.start()
        self.hp_wiper = HPWiper()
        self.patch_time = mock.patch('mercury_agent.hardware.wipers.hp.time')
        self.mock_time = self.patch_time.start()

    def tearDown(self):
        self.patch_udev.stop()
        self.patch_hpssa.stop()
        self.patch_config.stop()
        self.patch_time.stop()

    def test_get_raid_clear_delay(self):
        result = self.hp_wiper.get_raid_clear_delay()
        self.assertEqual(result, 10)

    def test_check_adapter_status(self):
        self.mock_hp_raid.adapters = [{'name': 'adapter1'}]
        result = self.hp_wiper.check_adapter_status()
        self.assertEqual(len(result), 0)

    def test_check_adapter_status_error(self):
        error_adapter_name = 'adapter1'
        error_adapter_slot = 1
        error_adapter_state = 'ERROR'
        self.mock_hp_raid.adapters = [
            {'name': error_adapter_name, 'error': error_adapter_state,
                'slot': error_adapter_slot}
        ]
        result = self.hp_wiper.check_adapter_status()
        self.assertEqual(len(result), 1)
        expected_error_message = "Controller {} in slot {} is in an error state: {}".format(
            error_adapter_name, error_adapter_slot, error_adapter_state)
        self.assertEqual(result[0], expected_error_message)

    def test_delete_all_arrays(self):
        self.hp_wiper.delete_all_arrays()
        self.mock_hp_raid.clear_configuration.assert_called_once()
        self.mock_time.sleep.assert_called_once()

    def test_clear_devices(self):
        mock_utility_exec = mock.Mock()
        self.hp_wiper.utility_exec = mock_utility_exec

        self.hp_wiper.clear_devices()
        mock_utility_exec.assert_called_once_with(
            "/sbin/dmsetup remove_all --force")
        self.mock_time.sleep.assert_called_once()

    def test_create_array(self):
        self.mock_hp_raid.get_all_drives.return_value = [
            {'name': 'drive1', 'slot': 1}]
        self.mock_hp_raid.assemble_id.return_value = 'formatted-drive1'
        self.hp_wiper.create_array()
        self.mock_hp_raid.create.assert_called_once_with(
            1, 'formatted-drive1', 0)
        self.mock_time.sleep.assert_called_once()

    @mock.patch('mercury_agent.hardware.wipers.hp.multiprocessing')
    def test_fill_disks(self, mock_multiprocessing):
        self.mock_udev.discover_valid_storage_devices.return_value = [
            {'DEVNAME': 'udisk1', 'ID_VENDOR': 'HP'}]
        self.mock_time.time.return_value = time.time()
        mock_fill_disk = mock.Mock()
        self.hp_wiper.fill_disk = mock_fill_disk
        # patching is_alive to False in order to prevent the test/process from running forever
        mock_process = mock.Mock(is_alive=mock.Mock(return_value=False))
        mock_multiprocessing.Process.return_value = mock_process

        self.hp_wiper.fill_disks()

        mock_multiprocessing.Process.assert_called_once_with(
            target=mock_fill_disk, args=['udisk1', '4M']
        )
        self.assertEqual(len(self.hp_wiper.fill_processes), 1)

    def test_fill_disk(self):
        mock_utility_exec = mock.Mock()
        self.hp_wiper.utility_exec = mock_utility_exec

        self.hp_wiper.fill_disk(disk='udisk11', bs='4M')
        mock_utility_exec.assert_called_once_with(
            "dd if=/dev/zero of=%s bs=%s" % ('udisk11', '4M'), ignore_error=True
        )

    def test_wipe(self):
        mock_check_apater_status = mock.Mock(return_value=None)
        self.hp_wiper.check_adapter_status = mock_check_apater_status
        mock_delete_all_arrays = mock.Mock()
        self.hp_wiper.delete_all_arrays = mock_delete_all_arrays
        mock_clear_devices = mock.Mock()
        self.hp_wiper.clear_devices = mock_clear_devices
        mock_create_array = mock.Mock()
        self.hp_wiper.create_array = mock_create_array
        mock_fill_disks = mock.Mock()
        self.hp_wiper.fill_disks = mock_fill_disks
        mock_delete_all_arrays = mock.Mock()
        self.hp_wiper.delete_all_arrays = mock_delete_all_arrays

        self.hp_wiper.wipe()

        mock_check_apater_status.assert_called_once()
        self.assertEqual(mock_delete_all_arrays.call_count, 2)
        mock_clear_devices.assert_called_once()
        mock_create_array.assert_called_once()
        mock_fill_disks.assert_called_once()

    def test_wipe_adapter_status_errors(self):
        mock_check_apater_status = mock.Mock(return_value=['error1', 'error2'])
        self.hp_wiper.check_adapter_status = mock_check_apater_status
        self.assertRaises(Exception, self.hp_wiper.wipe)
