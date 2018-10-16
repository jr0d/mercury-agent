import logging
import multiprocessing
import time

from mercury.common.exceptions import MercuryCritical

from mercury_agent.capabilities import capability
from mercury_agent.backend_client import get_backend_client
from mercury_agent.hardware.drivers.drivers import get_subsystem_drivers
from mercury_agent.hardware.erase import os_level_erase as os_erase
from mercury_agent.inspector.inspect import global_device_info
from mercury_agent.inspector.inspectors.os_storage import os_storage_inspector
from mercury_agent.inspector.inspectors.raid import raid_inspector

log = logging.getLogger(__name__)

HARDWARE_ERASE_SUPPORTED = [
    "PERC H740P Adapter"
]


def update_inventory():
    backend_client = get_backend_client()
    raid_info = raid_inspector(global_device_info)
    os_storage_info = os_storage_inspector()
    mercury_id = global_device_info['mercury_id']

    log.debug('Configuration changed, updating inventory and cache')
    update = {'raid': raid_info, 'os_storage': os_storage_info}
    global_device_info.update(update)
    backend_client.update(mercury_id, update)


def get_raid_drivers():
    """ Get raid driver targets for erase operations """
    hw_erase_drivers = []
    os_erase_drivers = []

    for driver in get_subsystem_drivers('raid'):
        for idx, _ in enumerate(driver.devices):
            if (driver.handler.get_adapter_info(idx)['name'].strip()
                    in HARDWARE_ERASE_SUPPORTED):
                hw_erase_drivers.append(driver)
            else:
                os_erase_drivers.append(driver)

    return hw_erase_drivers, os_erase_drivers


def driver_clear_all(drivers):
    for driver in drivers:
        for idx, _ in enumerate(driver.devices):
            log.info('Clearing configuration [%s adapter: %s]',
                     driver.name, idx)
            driver.handler.clear_configuration(idx)
    update_inventory()


def driver_start_erase(drivers, method):
    for driver in drivers:
        for idx, _ in enumerate(driver.devices):
            log.info('Starting Hardware Erase [%s adapter: %s]',
                     driver.name, idx)
            driver.handler.start_erase(idx, 'all', method)


def _assemble_jbod(driver, adapter):
    unassigned = driver.handler.get_unassigned(adapter)
    for idx, drive in enumerate(unassigned):
        log.info('Creating RAID 0 on %s disk %s', driver.name, idx)
        driver.handler.create_logical_drive(adapter, level='0', drives=[idx])


def driver_assemble_jbod(drivers):
    for driver in drivers:
        for idx, _ in enumerate(driver.devices):
            _assemble_jbod(driver, idx)
    update_inventory()


def _erase_wrapper(target, method, results_queue):
    # TODO: Figure out solution for remote logging and mp
    # noinspection PyBroadException
    try:
        results_queue.put(os_erase.erase(target, method))
    except Exception as e:
        results_queue.put({
            'error': True,
            'data': 'An error occurred while erasing device: {} [{}]'.format(
                    target,
                    e)
        })


def _background_erase(target, method):
    log.info('Backgrounding erase job for %s', target)
    results_queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_erase_wrapper, args=(
        target, method, results_queue))
    p.start()
    return {
        'process': p,
        'queue': results_queue,
        'target': target,
        'result': None,
        'completed': False
    }


def _check_hw_erase_completed(drivers):
    in_progress = 0
    for driver in drivers:
        for idx, _ in enumerate(driver.devices):
            res = driver.handler.erase_in_progress(idx)
            if res:
                # TODO: MRC-119, for now, we'll blast a log message
                # Only works for storcli
                for drive in driver.handler.get_erase_status(idx):
                    log.info('HW drive erase: %s [%s%%]', drive['Drive-ID'],
                             drive['Progress%'])
                in_progress += 1
    return in_progress == 0


def _check_os_erase_completed(os_erase_tasks):
    incomplete_tasks = [
        task for task in os_erase_tasks if not task['completed']]
    for incomplete in incomplete_tasks:
        process = incomplete['process']
        queue = incomplete['queue']
        if not process.is_alive():
            incomplete['completed'] = True
            incomplete['result'] = queue.get(block=False)
            log.info('Drive wipe operation has completed on %s',
                     incomplete['target'])
    return len(incomplete_tasks) == 0


def loop_until_completed(hw_erase_drivers, os_erase_tasks, interval):
    hw_erase_complete = False if hw_erase_drivers else True
    os_erase_complete = False if os_erase_tasks else True
    while True:
        if not hw_erase_complete:
            hw_erase_complete = _check_hw_erase_completed(hw_erase_drivers)
        if not os_erase_complete:
            os_erase_complete = _check_os_erase_completed(os_erase_tasks)
        if hw_erase_complete and os_erase_complete:
            log.info('Background jobs completed!')
            break
        time.sleep(interval)


def _check_background_errors(os_erase_tasks):
    has_errors = False
    for task in os_erase_tasks:
        if task['result'].get('error'):
            has_errors = True
            log.error('Error erasing drive: %s', task)

    if has_errors:
        raise MercuryCritical('An error has occurred, the system has not been '
                              'erased')


@capability('erase',
            'Erase all data from local storage',
            timeout=0,
            serial=True)
def erase(method='fast'):
    """

    :param method:
    :return:
    """

    check_interval = 30

    log.info('Checking device for local storage')
    hw_method = 'simple' if method == 'fast' else 'standard'
    os_method = 'zero' if method == 'fast' else 'unsupported'
    hw_erase_drivers, os_erase_drivers = get_raid_drivers()

    # clear all RAID configurations
    log.info('Clearing all adapter RAID configurations')
    driver_clear_all(hw_erase_drivers + os_erase_drivers)

    # Start Hardware Erase
    if hw_erase_drivers:
        log.info('Initiating hardware erase on supported controllers')
        driver_start_erase(hw_erase_drivers, hw_method)

    # Assemble JBOD for wiping
    if os_erase_drivers:
        log.info('Assembling managed drives into JBOD')
        driver_assemble_jbod(os_erase_drivers)

    storage_devices = global_device_info['os_storage']

    # Wipe SSDs using TRIM
    ssd_results = []
    ssd_devices = [drive['udev']['DEVNAME'] for drive in storage_devices
                   if drive['media_type'] == 'ssd']
    for drive in ssd_devices:
        log.info('Preparing to TRIM erase SSDs')
        ssd_results.append(os_erase.erase(drive, 'ssd_trim'))

    # TODO: Add periodic status updates
    background_erase_tasks = []
    log.info('Initiating background wipe of remaining devices')
    for drive in [drive['udev']['DEVNAME'] for drive in storage_devices
                  if drive['media_type'] == 'disk']:
        background_erase_tasks.append(_background_erase(drive, os_method))

    loop_until_completed(hw_erase_drivers, background_erase_tasks,
                         check_interval)

    # clear all RAID configurations
    log.info('Clearing all adapter RAID configurations')
    driver_clear_all(hw_erase_drivers + os_erase_drivers)

    _check_background_errors(background_erase_tasks)
    log.info('System erase has completed')

    return {'report': {
        'ssd': ssd_results,
        'rotational': [t['result'] for t in background_erase_tasks]
    }}
