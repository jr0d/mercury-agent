import logging

from pystress.api import Stress

from mercury_agent.capabilities import capability

log = logging.getLogger(__name__)


@capability('stress_test',
            description='Installs updates from provided packages',
            kwarg_names=['stress_seconds'], serial=False, timeout=3600)
def stress_test(stress_seconds=60):
    log.info('Starting stress test on CPU and Memory for '
             '{} seconds'.format(stress_seconds))
    stress_tester = Stress(logger=log)
    stress_tester.start(stress_seconds)
