import unittest

import mock

from subprocess import PIPE
from mercury_agent.hardware.raid.interfaces.megaraid.megacli import (
    LSIRaid, LSIRaidException, clear_lsi
)


class TestLSIRaidInit(unittest.TestCase):

    @mock.patch('mercury_agent.hardware.raid.interfaces.megaraid.megacli.os.path.isfile')
    @mock.patch.object(LSIRaid, "refresh")
    def test_init(self, mock_refresh, mock_os_ispath):
        mock_os_ispath.return_value = True
        lsi_raid = LSIRaid()
        mock_refresh.assert_called_once()
        self.assertEqual(lsi_raid.adapter, 0)
        self.assertEqual(lsi_raid.megacli_bin, '/usr/sbin/megacli')

    @mock.patch.object(LSIRaid, 'count_virtual_disks')
    @mock.patch.object(LSIRaid, 'get_adapter_raw')
    @mock.patch.object(LSIRaid, 'get_enclosure_id')
    @mock.patch.object(LSIRaid, 'get_virtual_disks')
    @mock.patch.object(LSIRaid, 'get_physical_disks')
    @mock.patch.object(LSIRaid, '__init__', return_value=None)
    def test_refresh(self, mock_init, mock_get_physical_disks, mock_get_virtual_disks,
                     mock_get_enclosure_id, mock_get_adapter_raw, mock_count_virtual_disks):
        lsi_raid = LSIRaid().refresh()
        mock_get_physical_disks.assert_called_once()
        mock_get_virtual_disks.assert_called_once()
        mock_get_enclosure_id.assert_called_once()
        mock_get_adapter_raw.assert_called_once()
        mock_count_virtual_disks.assert_called_once()


class TestLSIRaid(unittest.TestCase):

    def setUp(self):
        self.patch_os = mock.patch(
            'mercury_agent.hardware.raid.interfaces.megaraid.megacli.os.path.isfile'
        )
        self.patch_os.start()
        self.patch_refresh = mock.patch.object(LSIRaid, "refresh")
        self.patch_refresh.start()
        self.patch_time = mock.patch(
            'mercury_agent.hardware.raid.interfaces.megaraid.megacli.time')
        self.patch_time.start()

    def tearDown(self):
        self.patch_os.stop()
        self.patch_refresh.stop()
        self.patch_time.stop()

    @mock.patch('mercury_agent.hardware.raid.interfaces.megaraid.megacli.Popen')
    def test_megacli(self, mock_popen):
        mock_communicte = mock.Mock(return_value=('output', None))
        mock_popen.return_value = mock.Mock(
            poll=mock.Mock(return_value=1),
            communicate=mock_communicte,
            returncode=0
        )
        cmd = '-AdpAllInfo -aall'
        out, err, ret = LSIRaid().megacli(cmd)
        expected_cmd = ['/usr/sbin/megacli'] + cmd.split()
        mock_popen.assert_called_once_with(
            expected_cmd + ['-NoLog'], stdout=PIPE, stderr=PIPE, bufsize=1048567
        )
        self.assertEqual(out, 'output')
        self.assertEqual(err, None)
        self.assertEqual(ret, 0)

    @mock.patch.object(LSIRaid, "megacli", return_value=('a1\na2\n', None, 0))
    def test_get_adapter_raw(self, mock_megacli):
        result = LSIRaid().get_adapter_raw()
        mock_megacli.assert_called_once_with('-AdpAllInfo -aall')
        self.assertEqual(result, ['a1', 'a2'])

    @mock.patch.object(LSIRaid, "megacli", return_value=(None, 'error', -1))
    def test_get_adapter_raw_error(self, mock_megacli):
        self.assertRaises(LSIRaidException, LSIRaid().get_adapter_raw)

    @mock.patch.object(LSIRaid, "megacli", return_value=('success', None, 0))
    def test_clear_config(self, mock_megacli):
        LSIRaid().clear_config()
        mock_megacli.assert_called_once_with('-CfgClr -aall')

    @mock.patch.object(LSIRaid, "megacli", return_value=('success', None, 0))
    def test_init_logical_drives(self, mock_megacli):
        LSIRaid().init_logical_drives()
        mock_megacli.assert_called_once_with('-LDInit -Start -LALL -aall')

    @mock.patch.object(LSIRaid, "megacli", return_value=('success', None, 0))
    def test_clear_foreign_configs(self, mock_megacli):
        LSIRaid().clear_foreign_configs()
        mock_megacli.assert_called_once_with('-CfgForeign -Clear -a0')

    @mock.patch.object(LSIRaid, "megacli", return_value=('Adapter:4', None, 0))
    def test_count_physical_disks(self, mock_megacli):
        result = LSIRaid().count_physical_disks()
        mock_megacli.assert_called_once_with('-PDGetNum -a0')
        self.assertEqual(result, 4)

    @mock.patch.object(LSIRaid, "megacli", return_value=('Adapter:4', None, 0))
    def test_count_virtual_disks(self, mock_megacli):
        result = LSIRaid().count_virtual_disks()
        mock_megacli.assert_called_once_with('-LDGetNum -a0')
        self.assertEqual(result, 4)

    @mock.patch.object(LSIRaid, "megacli", return_value=('Device ID:12345', None, 0))
    def test_get_enclosure_id(self, mock_megacli):
        result = LSIRaid().get_enclosure_id()
        mock_megacli.assert_called_once_with('-EncInfo -a0')
        self.assertEqual(result, 12345)

    @mock.patch.object(LSIRaid, "count_physical_disks", return_value=2)
    @mock.patch.object(LSIRaid, "megacli")
    def test_get_physical_disks(self, mock_megacli, mock_count_physical_disks):
        fake_list = ('Adapter #0\nDevice Id:1\nSlot Number:1\nFirmware state:active\nDevice Id:2'
                     '\nSlot Number:2\nFirmware state:active\n')
        mock_megacli.return_value = (fake_list, None, 0)
        result = LSIRaid().get_physical_disks()
        mock_count_physical_disks.assert_called_once()
        mock_megacli.assert_called_once_with('-PdList -a0')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIsInstance(item, dict)
            self.assertIn('device_id', item)
            self.assertIn(item['device_id'], [1, 2])
            self.assertIn('slot_number', item)
            self.assertIn(item['slot_number'], [1, 2])
            self.assertIn('state', item)
            self.assertEqual(item['state'], 'active')

    @mock.patch.object(LSIRaid, "megacli")
    def test_get_virtual_disk_members(self, mock_megacli):
        fake_list = ('Virtual Drive vhd vid1\nDevice Id:12345')
        mock_megacli.return_value = (fake_list, None, 0)
        result = LSIRaid().get_virtual_disk_members('vid1', 1)
        mock_megacli.assert_called_once_with('-LDPDInfo -a0')
        self.assertEqual(result, [12345])

    @mock.patch.object(LSIRaid, "get_virtual_disk_members")
    @mock.patch.object(LSIRaid, "count_virtual_disks", return_value=1)
    @mock.patch.object(LSIRaid, "megacli")
    def test_get_virtual_disks(self, mock_megacli, mock_count_virtual_disks, mock_get_members):
        fake_list = (
            'Virtual Drive:1\n'
            'RAID Level:level-1,level-5\n'
            'Number Of Drives:1\n'
            'Span Depth:4\n'
        )
        mock_megacli.return_value = (fake_list, None, 0)
        mock_get_members.return_value = [12345]
        result = LSIRaid().get_virtual_disks()
        mock_count_virtual_disks.assert_called_once()
        mock_megacli.assert_called_once_with('-LdInfo -Lall -a0')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        expected_keys = ['id', 'raid_level',
                         'drive_count', 'span_depth', 'phys_ids']
        self.assertEqual(len(result[0].keys()), len(expected_keys))
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[0]['raid_level'], (1, 5))
        self.assertEqual(result[0]['drive_count'], 1)
        self.assertEqual(result[0]['span_depth'], 4)
        self.assertEqual(result[0]['phys_ids'], [12345])

    @mock.patch('mercury_agent.hardware.raid.interfaces.megaraid.megacli.LSIRaid')
    def test_clear_lsi(self, mock_lsi_raid):
        clear_lsi(mock_lsi_raid)
        mock_lsi_raid.clear_config.assert_called_once_with(None)
        mock_lsi_raid.clear_foreign_configs.assert_called_once_with(None)
        mock_lsi_raid.refresh.assert_called_once()

