import logging

log = logging.getLogger(__name__)


class LSIWiper:

    def wipe(self):
        # TODO: Implement drive wipe
        # Reference: https://github.rackspace.com/OSDeployment/newton/blob/development/newton/
        #            hardware/wipers/lsi.py
        log.info('Started LSI drive wipe')
