# Copyright 2015 Jared Rodriguez (jared.rodriguez@rackspace.com)
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# Temporary baseline driver for LSI/PERC MegaRAID SAS adapters
# Next iteration will harness stor/percCLI which has JSON output capabilities

import logging

from size import Size

from mercury_agent.configuration import get_configuration

from mercury_agent.hardware import platform_detection
from mercury_agent.hardware.drivers import driver, PCIDriverBase
from mercury_agent.hardware.raid.abstraction.api import RAIDActions, \
    RAIDAbstractionException
from mercury_agent.hardware.raid.interfaces.megaraid.storcli import Storcli

log = logging.getLogger(__name__)


class MegaRAIDActions(RAIDActions):
    # Drives have many more statuses than we care about
    # This information will be preserved in extra
    drive_status_map = {
        'DHS': 'OK',  # Dedicated Hotspare
        'UGood': 'OK',
        'GHS': 'OK',  # Global Hotspare
        'UBad': 'Failed',
        'Onln': 'OK',
        'Offln': 'Failed'
    }

    logical_drive_map = {
        'Rec': 'RECOVERING',
        'Pdgd': 'DEGRADED',
        'dgrd': 'DEGRADED',
        'Optl': 'OK'
    }

    hotspare_map = {
        'DHS': 'dedicated',
        'GHS': 'global'
    }

    def __init__(self):
        """ MegaRAID support for RAID abstraction.
        This class is using the mercury native storcli interface. The interface is very thin.
        As such, vendor_info may need a little more cleanup in comparison to SmartArray
        """
        super(MegaRAIDActions, self).__init__()
        self.storcli = Storcli(binary_path=get_configuration().get(
            'agent', {}).get(
            'hardware', {}).get(
            'raid', {}).get(
            'storcli_path') or 'storcli')

    @staticmethod
    def get_vendor_info(adapter):
        """

        :param adapter:
        :return:
        """
        return {
            'general': adapter['Basics'],
            'version_info': adapter['Version'],
            'bus': adapter['Bus'],
            'status': adapter['Status'],
            'supported_adapter_ops': adapter['Supported Adapter Operations'],
            'supported_pd_ops': adapter['Supported PD Operations'],
            'supported_vd_ops': adapter['Supported VD Operations'],
            'bbu_info': adapter.get('BBU_Info')
        }

    @staticmethod
    def dash_is_none(value):
        """

        :param value:
        :return:
        """
        if value != '-':
            return value

    @staticmethod
    def get_controller_id(adapter_info):
        return adapter_info['vendor_info']['general']['Controller']

    def populate_logical_drives(self, disk_group, dg_info):
        """

        :param disk_group:
        :param dg_info:
        :return:
        """
        lds = []
        for vd in dg_info['VD LIST']:
            dg_id, vd_id = (int(x) for x in vd['DG/VD'].split('/'))
            if dg_id == disk_group:
                lds.append({
                    'level': int(vd['TYPE'].strip('RAID')),
                    'size': Size(vd['Size'], force_iec_values=True).bytes,
                    'status': self.logical_drive_map.get((vd['State']),
                                                         'UNKNOWN'),
                    'extra': {
                        'disk_group': dg_id,
                        'access': vd['Access'],
                        'consistency': vd['Consist'],
                        'cache': vd['Cache'],
                        'name': vd['Name'],
                        'vendor_state': vd['State']
                    }
                })

        return lds

    def format_physical_drive(self, pd):
        """

        :param pd:
        :return:
        """
        # DG JSON type is inconsistent
        disk_group = self.dash_is_none(pd['DG'])
        if isinstance(disk_group, str):
            disk_group = int(disk_group)

        return {
            'size': Size(pd['Size'], force_iec_values=True).bytes,
            'status': self.drive_status_map.get(pd['State'], 'UNKNOWN'),
            'type': pd['Med'],
            'extra': {
                'address': pd['EID:Slt'],
                'drive_id': pd['DID'],
                'model': pd['Model'],
                'disk_group': disk_group,
                'interface': pd['Intf'],
                'self_encrypted_drive':
                    pd['SED'] != 'N',
                'spun': pd['Sp'],
                'sector_size': Size(pd['SeSz'].lower()).bytes,
                'vendor_state': pd['State'],
                'spare_type': self.hotspare_map.get(pd['State'], None)
            }
        }

    def populate_physical_drives(self, disk_group, dg_info):
        """

        :param disk_group:
        :param dg_info:
        :return:
        """
        pds = []
        for pd in dg_info['DG Drive LIST']:
            if pd['DG'] == disk_group:
                pds.append(self.format_physical_drive(pd))

        return pds

    @staticmethod
    def populate_free_space(disk_group, dg_info):
        """

        :param disk_group:
        :param dg_info:
        :return:
        """
        free_space_details = dg_info.get('FREE SPACE DETAILS')

        if free_space_details:
            for fs in free_space_details:
                if fs['DG'] == disk_group:
                    return Size(fs['Size'], force_iec_values=True).bytes

        return 0

    def get_configuration(self, dg_info):
        """ Builds an array of storage array structures for use

        :param dg_info:
        :return:
        """
        arrays = []

        topology = dg_info['TOPOLOGY']

        # The JSON we are working with is horrid
        # Rather than nesting, disk group structures are signified by
        # containing a '-' in the Arr (Array) field. Further, I do not
        # believe there is a a mechanism to create more than one array
        # per disk group. In this abstraction, a disk group IS an array.
        dgs = [dg for dg in topology if dg['Arr'] == '-'
               and dg['Type'] != 'DRIVE']

        for dg in dgs:
            arrays.append({
                'logical_drives': self.populate_logical_drives(dg['DG'],
                                                               dg_info),
                'physical_drives': self.populate_physical_drives(dg['DG'],
                                                                 dg_info),
                'free_space': self.populate_free_space(dg['DG'],
                                                       dg_info),
                'extra': {
                    'disk_group': dg['DG'],
                    'background_task': dg['BT'] == 'yes',
                    'dimmer_switch': self.dash_is_none(dg['DS3'])
                }
            })

        return arrays

    @staticmethod
    def get_array_index_by_dg(arrays, dg):
        """

        :param arrays: Transformed arrays object
        :param dg: Disk group target
        :return:
        """
        cnt = 0
        for array in arrays:
            if array['extra']['disk_group'] == dg:
                return cnt
            cnt += 1
        return -1

    def get_spares(self, arrays, dg_info):
        """

        :param arrays:
        :param dg_info:
        :return:
        """
        drive_list = dg_info.get('UN-CONFIGURED DRIVE LIST')

        if not drive_list:
            return []

        spares = []

        for drive in drive_list:
            if drive['State'] in self.hotspare_map:
                spare = self.format_physical_drive(drive)

                disk_group = spare['extra']['disk_group']
                if disk_group is not None:
                    # DHS
                    spare['target'] = self.get_array_index_by_dg(arrays,
                                                                 disk_group)
                else:
                    spare['target'] = None

                spares.append(spare)

        return spares

    def get_unconfigured_drives(self, dg_info):
        """

        :param dg_info:
        :return:
        """
        drive_list = dg_info.get('UN-CONFIGURED DRIVE LIST')

        if not drive_list:
            return []

        drives = []

        for drive in drive_list:
            if drive['State'] not in self.hotspare_map:
                drives.append(self.format_physical_drive(drive))

        return drives

    def transform_configuration(self, controller):
        """

        :param controller:
        :return:
        """
        configuration = {
            'arrays': [],
            'spares': [],
            'unassigned': []
        }

        # The second controller specific read is necessary because
        # /call show all does not contain some necessary information.
        # Such as "UN-CONFIGURED DRIVE LIST"
        dg_info = self.storcli.get_disk_group(controller)[0]

        if dg_info.get('TOPOLOGY'):
            # A configuration exists on the adapter
            configuration['arrays'] = self.get_configuration(dg_info)
            configuration['spares'] = self.get_spares(configuration['arrays'],
                                                      dg_info)

        configuration['unassigned'] = self.get_unconfigured_drives(dg_info)

        return configuration

    @staticmethod
    def sort_drives(drives):
        drives.sort(key=lambda d: d['extra']['drive_id'])

    def transform_adapter_info(self, adapter_index):
        """
        Transforms Storcli.controllers[adapter_index] into standard form
        :param adapter_index:
        :return: Adapter details in standard from
        """
        try:
            adapter = self.storcli.controllers[adapter_index]
        except IndexError:
            raise RAIDAbstractionException('Controller does not exist')

        adapter_details = {
            'name': adapter['Basics']['Model'],
            'provider': 'megaraid',
            'vendor_info': self.get_vendor_info(adapter),
            'configuration': self.transform_configuration(adapter_index)
        }

        return adapter_details

    def create(self, adapter_info, level, drives=None, size=None, array=None):
        """

        :param adapter_info:
        :param level:
        :param drives:
        :param size:
        :param array:
        :return:
        """
        size_mb = size and round(size.megabytes) or None

        level = 'r{}'.format(level)

        target_drives = []
        for drive in drives:
            if drive['extra']['vendor_state'] != 'UGood':
                raise RAIDAbstractionException(
                    'Drive index: {}, address:{} is in a failed state, cannot '
                    'create array'.format(
                        drive['index'], drive['extra']['address']))

            target_drives.append(drive['extra']['address'])

        return self.storcli.add(
            controller=self.get_controller_id(adapter_info),
            array_type=level,
            drives=','.join(target_drives),
            size=size_mb
        )

    def delete_logical_drive(self, adapter, array, logical_drive):
        """

        :param adapter:
        :param array:
        :param logical_drive:
        :return:
        """
        adapter_info = self.get_adapter_info(adapter)
        controller_id = self.get_controller_id(adapter_info)

        arrays = adapter_info['configuration']['arrays']

        try:
            # ensure that the index exists
            assert len(arrays[array]['logical_drives']) >= logical_drive + 1
        except (IndexError, AssertionError):
            raise RAIDAbstractionException(
                'Logical Drive does not exist at {}:{}:{}'.format(
                    adapter, array, logical_drive)
            )
        return self.storcli.delete(controller=controller_id,
                                   virtual_drive=logical_drive)

    def clear_configuration(self, adapter):
        """

        :param adapter:
        :return:
        """
        return self.storcli.delete(controller=self.get_controller_id(
            self.get_adapter_info(adapter)), virtual_drive='all')

    def add_spares(self, adapter, drives, arrays=None):
        """

        :param adapter:
        :param drives:
        :param arrays:
        :return:
        """
        adapter_info = self.get_adapter_info(adapter)
        controller_id = self.get_controller_id(adapter_info)

        target_drives = self.get_drives_from_selection(adapter, drives)

        results = []
        dgs = []

        if arrays:
            for ary_index in arrays:
                try:
                    array = adapter_info['configuration']['arrays'][ary_index]
                except IndexError:
                    raise RAIDAbstractionException(
                        'Array {} does not exist'.format(ary_index))
                dgs.append(array['extra']['disk_group'])

        for drive in target_drives:
            enclosure, slot = (
                int(_) for _ in drive['extra']['address'].split(':'))
            results.append(
                self.storcli.add_hotspare(controller=controller_id,
                                          enclosure=enclosure,
                                          slot=slot,
                                          disk_groups=dgs)
            )

        return results

    def erase(self, adapter, drives, method='fast'):
        log.info(
            'Starting hardware erase on adapter: %s, drives: %s, method: %s',
            adapter, drives, method)

        adapter_info = self.get_adapter_info(adapter)
        controller_id = self.get_controller_id(adapter_info)

        if drives == 'all':
            self.storcli.start_erase(controller_id, 'all', 'all')
        else:
            enclosure_drive_map = {}
            target_drives = self.get_drives_from_selection(0, drives)
            for _drive in target_drives:
                enclosure, slot = (int(_) for _ in _drive['extra']['address'].split(':'))
                if enclosure not in enclosure_drive_map:
                    enclosure_drive_map[enclosure] = [slot]
                else:
                    enclosure_drive_map[enclosure].append(slot)

            for enclosure in enclosure_drive_map.keys():
                self.storcli.start_erase(
                    controller_id, enclosure, ','.join(enclosure_drive_map[enclosure]))

    def get_erase_status(self, adapter):
        log.info('Getting hardware erase status on adapter: %s, drives: %s',
                 adapter)
        adapter_info = self.get_adapter_info(adapter)
        controller_id = self.get_controller_id(adapter_info)

        return self.storcli.show_erase(controller_id, 'all', 'all')

    def erase_in_progress(self, adapter):
        log.info('Checking erase status')
        for drive in self.get_erase_status(adapter):
            if drive['Status'] == 'In Progress':
                return True
        return False


@driver()
class MegaRaidSASDriver(PCIDriverBase):
    name = 'megaraid_sas'  # named after the kernel module
    driver_type = 'raid'
    _handler = MegaRAIDActions
    wants = 'pci'

    @classmethod
    def probe(cls, pci_data):
        raid_pci_devices = platform_detection.get_raid_controllers(pci_data)
        owns = list()

        for device in raid_pci_devices:
            if cls.check(device):
                owns.append(device['slot'])
        return owns

    @classmethod
    def check(cls, pci_device):
        return pci_device['driver'] == cls.name

    def inspect(self):
        adapters = []

        for idx in range(len(self.devices)):
            adapters.append(self.handler.get_adapter_info(idx))

        return adapters
