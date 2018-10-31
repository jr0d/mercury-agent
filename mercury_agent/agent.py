# Copyright 2015 Jared Rodriguez (jared.rodriguez@rackspace.com)
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import time

from mercury.common.clients.rpc.backend import BackEndClient
from mercury.common.exceptions import MercuryCritical, MercuryGeneralException

from mercury_agent.capabilities import runtime_capabilities
from mercury_agent.configuration import get_configuration
from mercury_agent.pong import spawn_pong_process
from mercury_agent.register import get_dhcp_ip, register
from mercury_agent.remote_logging import MercuryLogHandler
from mercury_agent.rpc import AgentService

from mercury_agent.inspector import inspect

# Async Inspectors

from mercury_agent.inspector.inspectors.async_inspectors.lldp import \
    LLDPInspector


log = logging.getLogger(__name__)


RETRY_SECONDS = 15


class Agent(object):
    def __init__(self, configuration, logger):
        """

        :param configuration:
        """
        self.configuration = configuration
        self.agent_bind_address = configuration.agent.service_bind_address
        self.pong_bind_address = configuration.agent.pong_bind_address

        self.rpc_backend_url = self.configuration.agent.remote.backend_url
        self.log_handler = logger

        if not self.rpc_backend_url:
            raise MercuryCritical('Missing rpc backend in local configuration')

        self.backend = BackEndClient(self.rpc_backend_url,
                                     linger=0,
                                     response_timeout=10,
                                     rcv_retry=3)

    def run(self, dhcp_ip_method='simple'):
        # TODO: Add other mechanisms for enumerating the devices public ip
        log.debug('Agent: %s, Pong: %s' % (self.agent_bind_address,
                                           self.pong_bind_address))

        log.info('Running inspectors')

        device_info = inspect.inspect()

        log.info('Registering device inventory for MercuryID {}'.format(
            device_info['mercury_id']))

        log.info('Starting pong service')
        spawn_pong_process(self.pong_bind_address)

        log.info('Registering device')

        local_ip = get_dhcp_ip(device_info, method=dhcp_ip_method)

        # TODO: enumerate ipv6 addresses
        local_ipv6 = None

        while True:
            result = register(
                self.backend,
                device_info,
                local_ip,
                local_ipv6,
                runtime_capabilities)

            if result.get('error'):
                log.info('Registration was not successful, retrying...')
                time.sleep(RETRY_SECONDS)
                continue

            log.info('Device has been registered successfully')
            break

        # LogHandler

        log.info('Injecting MercuryID for remote logging')
        self.log_handler.set_mercury_id(device_info['mercury_id'])
        log.info('Injection completed')

        # AsyncInspectors
        try:
            LLDPInspector(device_info, self.backend).inspect()
        except MercuryGeneralException as mge:
            log.error(
                'Caught recoverable exception running async inspector: '
                '{}'.format(mge))

        log.info('Starting agent rpc service: %s' % self.agent_bind_address)

        agent_service = AgentService(self.agent_bind_address,
                                     self.rpc_backend_url)
        agent_service.start()


def setup_logging(configuration):
    logging.basicConfig(level=configuration.logging.level,
                        format=configuration.logging.format)

    fh = logging.FileHandler(configuration.agent.log_file)

    fh.setLevel(configuration.logging.level)
    formatter = logging.Formatter(configuration.logging.format)
    fh.setFormatter(formatter)

    mercury_logger = logging.getLogger('mercury_agent')
    mercury_logger.addHandler(fh)
    mercury_logger.info('Starting Agent')

    # Quiet these down
    logging.getLogger('mercury_agent.pong').setLevel(
        configuration.agent.pong_log_level)
    logging.getLogger('hpssa._cli').setLevel(logging.ERROR)

    # Configure the remote logging handler
    mh = MercuryLogHandler(configuration.agent.remote.log_service_url)
    mercury_logger.addHandler(mh)

    # Return this so that we can inject the mercury_id once we have it
    return mh


def main():
    configuration = get_configuration()
    mercury_handler = setup_logging(configuration)
    agent = Agent(configuration, mercury_handler)
    agent.run(configuration.agent.dhcp_ip_source)


if __name__ == '__main__':
    main()
