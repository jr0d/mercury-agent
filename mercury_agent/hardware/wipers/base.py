import logging

from mercury.common.helpers.cli import run
from mercury_agent.inspector.hwlib.udev import UDevHelper

log = logging.getLogger(__name__)


class BaseWiper:

    def __init__(self):
        self.udev = UDevHelper()

    def utility_exec(self, command):
        """
        Simple executor for shell commands.
        """
        log.info('Executing: %s' % command)
        result = run(command, ignore_error=False, raise_exception=True)
        return result.stdout, result.stderr, result.returncode
