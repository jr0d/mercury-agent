import logging
from mercury.common.helpers import cli

from mercury_agent.configuration import get_configuration
from mercury_agent.hardware import platform_detection
from mercury_agent.hardware.oem.hp import hpasmcli
from mercury_agent.hardware.general import mcelog
from mercury_agent.inspector.inspectors import expose_late

log = logging.getLogger(__name__)


def _qc_hp(_oem_details, log_error):
    _oem_details['target'] = 'HP'
    hpasm = hpasmcli.HPASMCLI(
        get_configuration().agent.hardware.oem.hp.hpasmcli_path)
    _oem_details['server'] = hpasm.show_server()
    _oem_details['dimm'] = hpasm.show_dimm()
    _oem_details['power_supplies'] = hpasm.show_powersupply()

    for i, proc in enumerate(_oem_details['server'].get('processors', [])):
        if proc['status'] != 'Ok':
            log_error(
                'Processor {} is not in a nominal state. Reported state: {}'.format(
                    i, proc['status']))

    for dimm in _oem_details.get('dimm', []):
        if dimm['status'] != 'Ok':
            log_error(
                'DIMM module {} on CPU controller {} is not in a nominal state. '
                'Reporting state: {}'.format(
                    dimm['module_#'], dimm['processor_#'], dimm['status']))

    for i, power_supply in enumerate(_oem_details.get('power_supplies')):
        if power_supply['condition'] != 'Ok':
            log_error(
                'Power supply {} is not in a nominal state. Condition: {}'.format(
                    i, power_supply['condition']))


# noinspection PyTypeChecker
@expose_late('system_health')
def system_health_inspector(device_info):
    agent_configuration = get_configuration().agent
    _health = {
        'corrected_hardware_event_count': mcelog.count_logged_events(),
        'system_uptime': cli.run('uptime -s', ignore_error=True).strip(),
        'has_errors': False,
        'errors': []
    }

    def log_error(msg):
        log.error(msg)
        _health['has_errors'] = True
        _health['errors'].append(msg)

    if (_health['corrected_hardware_event_count']
            >= agent_configuration.hardware.mce_threshold):
        log_error('Hardware event count is {} which exceeds the threshold of {}'.format(
            _health['corrected_hardware_event_count'],
            agent_configuration.hardware.mce_threshold))

    # OEM Checks here
    _oem_details = {}
    _health['oem_details'] = _oem_details

    if platform_detection.is_hp(device_info.get('dmi', {})):
        _qc_hp(_oem_details, log_error)

    return _health


if __name__ == '__main__':
    from pprint import pprint

    pprint(system_health_inspector({}))
