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

from mercury_agent.capabilities import capability
from mercury_agent.configuration import get_configuration
from mercury_agent.inspector import inspect
from mercury_agent.inspector.inspect import global_device_info
from mercury_agent.inspector.inspectors import health


@capability('inspector', description='Run inspector')
def inspector():
    """
    Manually run inspectors
    :return: results
    """
    return inspect.inspect()


@capability('check_hardware', description='Check hardware for errors')
def check_hardware():
    """
    Checks hardware for inconsistencies and defects. Returns a list of discovered critical errors.
    :return:
    """
    configuration = get_configuration().agent
    errors = []
    _health_data = health.system_health_inspector(global_device_info)
    if _health_data['corrected_hardware_event_count'] >= configuration.hardware.mce_threshold:
        errors.append(
            'MCE count is {} which is above the configured threshold of {}'.format(
                _health_data['corrected_hardware_event_count'],
                configuration.hardware.mce_threshold))

    return {
        'errors': errors,
        'error_count': len(errors)
    }
