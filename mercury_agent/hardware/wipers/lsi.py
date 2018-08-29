"""
LSI wipe drives implementation
"""
import multiprocessing
import logging
import functools
import time

from mercury_agent.hardware.raid.interfaces.megaraid.megacli import (
    LSIRaid, clear_lsi, LSIRaidException
)

from mercury_agent.configuration import get_configuration
from mercury_agent.hardware.wipers.base import BaseWiper

log = logging.getLogger(__name__)


def check_raid_exception(func):
    """
    Decor to catch LSIRaidExceptions.
    """
    @functools.wraps(func)
    def _wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except LSIRaidException as err:
            log.error('LSIRaidException: {}-{}'.format(func.__name__, err))
            raise LSIRaidException(err)
    return _wrapped


class LSIWiper(BaseWiper):

    def __init__(self, adapter=0):
        super().__init__()
        megacli_bin = get_configuration().agent.hardware.megacli_bin
        self.adapter = adapter
        self.lsi_raid = LSIRaid(megacli_bin=megacli_bin, adapter=self.adapter)

    def get_raid_clear_delay(self):
        return int(get_configuration().agent.hardware.raid.clear_delay)

    @check_raid_exception
    def clear_configs(self):
        """
        Clear all RAID configs.
        """
        log.info('Clearing configs')
        clear_lsi(self.lsi_raid, self.adapter)
        time.sleep(self.get_raid_clear_delay())

    def clear_devices(self):
        """
        Clears the Device Mapper
        """
        log.info("Clearing device mapper")
        self.utility_exec("/sbin/dmsetup remove_all --force")
        time.sleep(self.get_raid_clear_delay())

    @check_raid_exception
    def create_array(self, raid_level=0):
        """
        Create one large RAID 0 using all disk
        """
        log.info('Creating array(s)')
        disks = [i['device_id'] for i in self.lsi_raid.get_physical_disks()]

        for disk in disks:
            log.info('Creating RAID {0} using disk {1}'.format(
                raid_level, disk))
            res = self.lsi_raid.create_array(raid_level, [disk])
            time.sleep(self.get_raid_clear_delay())

            if res and res.get('error'):
                log.error('Had trouble running: %s' % res['command'])
                log.error('stdout:\n%s' % res['stdout'])
                log.error('stderr:\n%s' % res['stderr'])
                raise Exception('Trouble creating RAID array!')

    def fill_disks(self, bs='4M'):
        """
        Fill a disk with zeros
        """
        self.fill_processes = list()
        udisks = self.udev.discover_valid_storage_devices()
        devices = [udisk['DEVNAME'] for udisk in udisks if udisk.get('ID_VENDOR') == 'DELL']

        for device in devices:
            process = multiprocessing.Process(
                target=self.fill_disk, args=[device, bs])
            now = time.time()
            process.start()
            self.fill_processes.append(
                dict(device=device, process=process, started=now, completed=0)
            )

        while True:
            not_completed = [
                x for x in self.fill_processes if not x['completed']]
            if not not_completed:
                break
            for process in not_completed:
                if not process['process'].is_alive():
                    now = time.time()
                    process['completed'] = now
            time.sleep(.2)

        for process in self.fill_processes:
            elapsed = process['completed'] - process['started']
            log.info('Zero fill completed for %s in ~ %s seconds' %
                     (process['device'], round(elapsed, 2)))

    def fill_disk(self, disk, bs='16M'):
        log.info('Starting zero fill of %s' % disk)
        self.utility_exec("dd if=/dev/zero of=%s bs=%s" %
                          (disk, bs), ignore_error=True)

    @check_raid_exception
    def init_logical_drives(self):
        """
        Init the Logical Drives using lsi_raid
        """
        log.info('Running quick LD Initialization.')
        self.lsi_raid.init_logical_drives()

    def wipe(self):
        log.info('Started LSI drive wipe')
        self.clear_configs()
        self.clear_devices()
        self.create_array()
        self.fill_disks()
        self.init_logical_drives()
        self.clear_configs()
        self.clear_devices()
        log.info('Completed LSI drive Wipe')
