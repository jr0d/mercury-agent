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

from mercury.common.configuration import MercuryConfiguration


log = logging.getLogger(__name__)

# Helpers
AGENT_CONFIG_FILE = 'mercury-agent.yaml'


__configuration = {}


def parse_options():
    configuration = MercuryConfiguration(
        'mercury-agent',
        AGENT_CONFIG_FILE,
        description='The Mercury Agent'
    )

    configuration.add_option('agent.bind_address',
                             help_string='The interface and port for socket '
                                         'binding',
                             default='tcp://127.0.0.1:9003'),

    configuration.add_option('agent.pong_bind_address',
                             help_string='Interface and port for the pong'
                                         'service',
                             default='tcp://127.0.0.1:9004')

    configuration.add_option('agent.dhcp_ip_source',
                             help_string='The method of determining dhcp_ip',
                             default='simple',
                             one_of=['simple', 'udhcpd', 'routing_table'])

    configuration.add_option('agent.remote.backend_url',
                             help_string='The ZeroMQ URL of the backend '
                                         'service',
                             required=True)

    configuration.add_option('agent.remote.log_service_url',
                             help_string='Optional logging service zURL')

    configuration.add_option('agent.hardware.raid.storcli_path',
                             cli_argument='--storcli_path',
                             env_variable='STORCLI_PATH',
                             default='storcli64')

    configuration.add_option('agent.hardware.raid.hpssacli_path',
                             cli_argument='--hpssacli_path',
                             env_variable='HPSSACLI_PATH',
                             default='hpssacli')

    configuration.add_option('agent.local_ip',
                             cli_argument='--local-ip',
                             env_variable='MERCURY_AGENT_ADDRESS',
                             help_string='The address which will be advertised'
                                         'to the backend for communication with'
                                         'this agent')
    configuration.add_option('agent.pong_log_level',
                             cli_argument='--pong-log-level',
                             default='ERROR',
                             help_string='The pong process log level')

    configuration.add_option('agent.hardware.obm.racadm_path',
                             cli_argument='--racadm-path',
                             env_variable='RACADM_PATH',
                             help_string='The location of the racadm binary',
                             default='racadm')

    configuration.add_option('agent.hardware.megacli_bin',
                             help_string='megacli binary',
                             default='/usr/local/sbin/megacli')

    configuration.add_option('agent.hardware.mce_threshold',
                             help_string='The maximum number of corrected machine '
                                         'check exceptions which can occur before '
                                         'an error is raised',
                             default=20,
                             special_type=int)

    configuration.add_option('agent.hardware.oem.hp.hpasmcli_path',
                             help_string='The path of the hpasmcli binary',
                             env_variable='HPASMCLI_PATH',
                             default='hpasmcli')

    return configuration.scan_options()


def get_configuration():
    global __configuration
    if not __configuration:
        __configuration = parse_options()
    return __configuration
