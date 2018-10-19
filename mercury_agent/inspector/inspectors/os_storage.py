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

import logging

from press.helpers import parted

from mercury_agent.inspector.inspectors import inspector
from mercury_agent.inspector.hwlib.udev import UDevHelper

log = logging.getLogger(__name__)


def get_disk_type(dev):
    dev = dev.lstrip('/dev/')
    sysfs_rotational_path = f'/sys/block/{dev}/queue/rotational'
    try:
        return 'disk' if int(open(sysfs_rotational_path).read()) else 'ssd'
    except (IOError, OSError):
        log.warning('Could not parse sysfs for %s', dev)
        return 'unknown'


@inspector.expose('os_storage')
def os_storage_inspector():
    os_storage = []
    storage_devices = UDevHelper().discover_valid_storage_devices(
        fc_enabled=True, loop_enabled=False)
    for storage_device in storage_devices:
        device_info = {}
        udev_device = dict(list(storage_device.items()))
        # Requires root privilages
        try:
            device_info.update(**parted.PartedInterface(
                udev_device['DEVNAME']).device_info)
        except parted.PartedException:
            log.warning(
                'Could not parse disk label for %s. Got root?',
                udev_device['DEVNAME'])
        device_info['udev'] = udev_device
        if udev_device.get('ID_BUS') != 'fc':
            device_info['media_type'] = get_disk_type(udev_device['DEVNAME'])
        else:
            # Fibre channel!
            device_info['media_type'] = 'external'
        os_storage.append(device_info)
    return os_storage


if __name__ == '__main__':
    import json
    print(json.dumps(os_storage_inspector(), indent=2))
