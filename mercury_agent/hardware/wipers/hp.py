import logging

log = logging.getLogger(__name__)


class HPWiper:

    def wipe(self):
        # TODO: Implement drive wipe
        # Reference: https://github.rackspace.com/OSDeployment/newton/blob/development/
        #                    newton/hardware/wipers/hp.py
        log.info('Started HP Drive wipe')
