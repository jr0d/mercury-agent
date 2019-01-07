import logging
import os

from multiprocessing import cpu_count


from mercury_agent.capabilities import capability
from mercury.common.helpers import cli


log = logging.getLogger(__name__)


class Stress(object):
    """
    Class for running our stress commands.
    """

    def __init__(self, stress_path="/usr/bin/stress"):
        """
        Make sure the stress binary is found
        """
        self.stress_path = stress_path
        if not os.path.exists(stress_path):
            raise Exception('Stress binary not found at '
                            '{}.'.format(self.stress_path))

    @staticmethod
    def get_system_memory():
        """
        Gets the amount of system memory in a server.
        """
        log.info('Getting the system memory')
        cmd = 'grep MemFree /proc/meminfo'
        result = cli.run(cmd)

        if not result.returncode:
            k = result.stdout.split()[1].strip()
            g = int(k)/1024/1024
            return '{}G'.format(int(g))

    def killall(self):
        """
        The way the stress binary behaves makes it hard to kill
        """
        log.error('Killing Stress Process.')
        os.system('killall stress')

    def cpu_stress(self, timeout):
        """
        Stress test the cpu on all cores.
        """
        log.info('Stress testing the cpu for %s seconds.' % timeout)
        cmd = '{0} --cpu {1} -t {2}'.format(self.stress_path,
                                            cpu_count(),
                                            timeout)
        log.info('Executing: {}'.format(cmd))
        result = cli.run(cmd)
        if result.returncode:
            self.killall()

    def memory_stress(self, timeout, amount=None):
        """
        Stress test the memory half of free memory.

        Amount should be in 1024K, 1024M, 1024G format.
        """

        # If we did not pass in a specific memory lets
        # try and run against all system memory, but if that
        # fails we default to 1024M.
        if not amount:
            amount = self.get_system_memory()
            if not amount:
                amount = '1024M'

        log.info('Stressing memory for %s seconds at %s.' %
                         (timeout, amount))
        cmd = '{0} --vm 1 --vm-bytes {1} --vm-hang 5 -t {2}'.format(
            self.stress_path, amount, timeout)
        log.info('Executing: {}'.format(cmd))
        result = cli.run(cmd)
        if result.returncode:
            self.killall()


@capability('memory_stress_test',
            description='Run stress on memory for specified amount of time',
            num_args=1, serial=False, timeout=3600)
def memory_stress_test(stress_seconds):
    """

    :param stress_seconds:
    :return:
    """
    log.info('Starting stress test on CPU and Memory for '
             '{} seconds'.format(stress_seconds))
    stress_tester = Stress()
    stress_tester.memory_stress(stress_seconds)


@capability('cpu_stress_test',
            description='Run stress on cpu for specified amount of time',
            num_args=1, serial=False, timeout=3600)
def cpu_stress_test(stress_seconds):
    """

    :param stress_seconds:
    :return:
    """
    log.info('Starting stress test on CPU and Memory for '
             '{} seconds'.format(stress_seconds))
    stress_tester = Stress()
    stress_tester.cpu_stress(stress_seconds)
