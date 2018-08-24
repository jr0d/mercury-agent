import logging

from multiprocessing import cpu_count
from os import system, path

from mercury_agent.capabilities import capability
from mercury.common.helpers import cli


# Request the Stress binary
# http://people.seas.harvard.edu/~apw/stress/
STRESS = '/usr/bin/stress'


def get_logger(label='PyStress Logger'):
    """
    Create and returns simple Logger
    """
    fmt = '%(asctime)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=fmt)
    logger = logging.getLogger(label)
    logger.setLevel(getattr(logging, 'INFO'))
    return logger


class Stress(object):
    """
    Class for running our stress commands.
    """

    def __init__(self, logger=None):
        """
        Make sure the stress binary is found
        """
        if not path.exists(STRESS):
            raise Exception('Stress binary not found at {}.'.format(STRESS))

        if logger is None:
            self.logger = get_logger()
        else:
            self.logger = logger

    def get_system_memory(self):
        """
        Gets the amount of system memory in a server.
        """
        self.logger.info('Getting the system memory')
        cmd = 'grep MemFree /proc/meminfo'
        result = cli.run(cmd)

        if not result.stderr:
            k = result.split()[1]
            g = int(k)/1024/1024
            return '{}G'.format(g)

    def killall(self):
        """
        The way the stress binary behaves makes it hard to kill
        """
        self.logger.error('Killing Stress Process.')
        system('killall stress')

    @staticmethod
    def get_number_of_cpu_cores():
        """
        Gets the number of cores on a machine.
        """
        return cpu_count()

    def cpu_stress(self, timeout):
        """
        Stress test the cpu on all cores.
        """
        self.logger.info('Stress testing the cpu for %s seconds.' % timeout)
        cmd = '{0} --cpu {1} -t {2}'.format(STRESS,
                                            self.get_number_of_cpu_cores(),
                                            timeout)
        self.logger.info('Executing: {}'.format(cmd))
        return cli.run(cmd)

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

        self.logger.info('Stressing memory for %s seconds at %s.' %
                         (timeout, amount))
        cmd = '{0} --vm 1 --vm-bytes {1} --vm-hang 5 -t {2}'.format(STRESS,
                                                                   amount,
                                                                   timeout)
        self.logger.info('Executing: {}'.format(cmd))
        return cli.run(cmd)

    def log_stress_result(self, result):
        """
        logging stress results.
        """
        if result.returncode == 0:
            for line in result.split('\n'):
                if line:
                    self.logger.info(line)
        else:
            for line in result.stderr.split('\n'):
                if line:
                    self.logger.error(line)
            self.killall()

    def start(self, seconds=900):
        """
        Start the stress processes and run for a number of seconds.
        """

        self.logger.info('Running Stress for {} seconds'.format(seconds))

        self.log_stress_result(self.cpu_stress(timeout=seconds))

        self.log_stress_result(self.memory_stress(timeout=seconds))


@capability('stress_test',
            description='Run stress on chassis for specified amount of time',
            kwarg_names=['stress_seconds'], serial=False, timeout=3600)
def stress_test(stress_seconds=60):
    log = get_logger()
    log.info('Starting stress test on CPU and Memory for '
             '{} seconds'.format(stress_seconds))
    stress_tester = Stress(logger=log)
    stress_tester.start(stress_seconds)
