import logging

from mercury_agent.capabilities import capability
from mercury_agent.inspector.inspect import global_device_info
from mercury_agent.hardware import platform_detection
from mercury_agent.hardware.drivers.drivers import get_subsystem_drivers


log = logging.getLogger(__name__)


@capability('wiper', 'Wipe data from drive(s)', no_return=True, timeout=14400)
def wiper():
    """
    Wipe data from the drives
    """
    for driver in get_subsystem_drivers('raid'):
        # TODO: fork a management process (for monitoring tasks) and a process for each
        #       wipe() operation
        driver.handler.wipe()

    # TODO: Using further hardware introspection, wipe devices with no RAID controllers

    log.info('Completed data wipe from the drives')
