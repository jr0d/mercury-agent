"""
HP wipe drives implementation
"""
import logging
import functools
import time
import multiprocessing

from hpssa.hpssa import HPSSA

from mercury_agent.configuration import get_configuration
from mercury_agent.hardware.wipers.base import BaseWiper

log = logging.getLogger(__name__)


class HPRaidException(Exception):
    pass


def check_raid_exception(func):
    """
        Decor to catch HPRaidExceptions.
    """
    @functools.wraps(func)
    def _wrapped(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except HPRaidException as err:
            log.error('HPRaidException: {}-{}'.format(func.__name__, err))
            raise HPRaidException(err)
    return _wrapped


class HPWiper(BaseWiper):

    def __init__(self):
        super().__init__()
        self.hp_raid = HPSSA()
        self.fill_processes = list()

    def get_raid_clear_delay(self):
        return int(get_configuration().agent.hardware.raid.clear_delay)

    @check_raid_exception
    def check_adapter_status(self):
        log.info('Checking adapter status')
        errors = []
        for adapter in self.hp_raid.adapters:
            if 'error' in adapter:
                errors.append("Controller {} in slot {} is in an error state: {}".format(
                    adapter.get('name'), adapter.get('slot'), adapter.get('error')))

        return errors

    @check_raid_exception
    def delete_all_arrays(self):
        """
        deletes all raid array config
        """
        log.info('Deleting all arrays')
        self.hp_raid.clear_configuration()
        time.sleep(self.get_raid_clear_delay())

    def clear_devices(self):
        """
        Clears the Device Mapper
        """
        log.info('Clearing device mapper')
        self.utility_exec("/sbin/dmsetup remove_all --force")
        time.sleep(self.get_raid_clear_delay())

    @check_raid_exception
    def create_array(self, level=0):
        """
        create raid 0 with available drives
        """
        for drive in self.hp_raid.get_all_drives():
            formatted_drive = self.hp_raid.assemble_id(drive)
            log.info('Creating RAID {} using drive {}'.format(
                level, formatted_drive))
            self.hp_raid.create(drive['slot'], formatted_drive, level)
            time.sleep(self.get_raid_clear_delay())

    def fill_disks(self, bs='4M'):
        """
        Fill a disk with zeros
        """
        log.info('Filling disks')
        udisks = self.udev.discover_valid_storage_devices()
        devices = [udisk['DEVNAME'] for udisk in udisks if udisk.get('ID_VENDOR') == 'HP']

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

    def wipe(self):
        log.info('Started HP Drive wipe')
        errors = self.check_adapter_status()
        if errors:
            raise Exception('. '.join(errors))
        self.delete_all_arrays()
        self.clear_devices()
        self.create_array()
        self.fill_disks()
        self.delete_all_arrays()
        log.info('Completed HP Drive wipe')
