import logging
import json

from mercury.common.helpers import cli


log = logging.getLogger(__name__)


class StorcliException(Exception):
    """ Raised exclusively by Storcli classes """
    pass


class Storcli(object):
    """ Thin storcli/percli interface for querying PERC and MegaRAID adapters and creating simple arrays """

    span_arrays = [10, 50, 60]
    parity_arrays = [5, 6, 50, 60]

    def __init__(self, binary_path='storcli'):
        """ Constructor

        :param binary_path: Location (relative, in shell path, or absolute) of storcli binary
        """
        self.storecli_path = cli.find_in_path(binary_path)
        if not self.storecli_path:
            raise StorcliException('storcli binary is missing')

    def run(self, cmd, ignore_error=False):
        """ Run a storecli command

        :param cmd: A valid storcli command
        :param ignore_error: Do not raise an exception on non-zero return code
        :return: AttributeString
        """

        result = cli.run('{} {}'.format(self.storecli_path, cmd), ignore_error=ignore_error)
        if not ignore_error:
            if result.returncode:
                raise StorcliException('Command returned: {}, Error: {}'.format(
                    result.returncode, result))
        return result

    def run_json(self, cmd):
        """ Request json output from storecli and load the object it returns

        :param cmd: A valid storcli command
        :return: deserialized storcli output
        """

        try:
            loaded = json.loads(self.run(cmd + ' J'))
        except ValueError as decode_error:
            raise StorcliException('Problem processing output: {}'.format(decode_error))
        return loaded

    @property
    def controllers(self):
        """ Property used to fetch, format, and display Controller information
        :return: Controller info sans 'Command Status'
        :return type: list
        """
        output = self.run_json('/call show all')

        try:
            controllers = output['Controllers']
        except KeyError:
            raise StorcliException('Output is missing Controllers segment')

        return [c['Response Data'] for c in controllers]

    def get_enclosures(self, controller='all'):
        """ Returns enclosures in a flattened list
        :param controller: one or all controllers
        :return: List of enclosure objects
        """
        output = self.run_json('/c{}/eall show all'.format(controller))
        try:
            controllers = output['Controllers']
        except KeyError:
            raise StorcliException('Output is missing Controllers segment')

        return [c['Response Data'] for c in controllers]

    @staticmethod
    def check_command_status(data):
        if data['Command Status']['Status'] != 'Success':
            raise StorcliException('{}\n'.format(
                data['Command Status']['Description'],
                '\n'.join(data['Command Status']['Detailed Status'])))

    def get_disk_group(self, controller='all', disk_group='all'):
        """

        :param controller:
        :param disk_group:
        :return:
        """
        output = self.run_json('/c{}/d{} show all'.format(controller,
                                                          disk_group))

        controller_list = []
        for controller in output['Controllers']:
            self.check_command_status(controller)
            # Account for some crazy JSON schema
            controller_list.append(
                controller['Response Data']['Response Data']
            )

        return controller_list

    def delete(self, controller, virtual_drive='all'):
        """ Delete one or all virtual drives on a controller
        :param controller: Controller ID
        :param virtual_drive: Virtual Drive ID or 'all' (default all)
        :return:
        """
        return self.run('/c{} /v{} del force'.format(controller, virtual_drive))

    def add(self, controller, array_type, drives, size=None, pdperarray=None, pdcache=None,
            dimmerswitch=None, io_mode='direct', write_policy='wb', read_policy='ra',
            cachevd=False, stripe_size=None, spares=None, cached_bad_bbu=False, after_vd=None):
        """ Add a virtual drive

        :param controller: Controller ID
        :param array_type:  r[0|1|5|6|10|50|60]
        :param drives: Drives specified with as EncID:drive,...
        :param size: Size of a drive in MB or None for maximum
        :param pdperarray: Specifies the number of physical drives per array. The default
value is automatically chosen.(0 to 16)
        :param pdcache: Enables or disables PD cache. (on|off|default)
        :param dimmerswitch: Specifies the power-saving policy. Sets to default automatically.
 default: Logical device uses controller default power-saving policy.
 automatic (auto): Logical device power savings managed by firmware.
 none: No power-saving policy.
 maximum (max): Logical device uses maximum power savings.
 MaximumWithoutCaching (maxnocache): Logical device does not cache
 write to maximize power savings.
        :param io_mode: cached|direct
        :param write_policy:wb|rt
        :param read_policy:ra|rt
        :param cachevd: enables or disables cachecade device support
        :param stripe_size: stripe size ( the amount of data writen before moving to the next disk )
        :param spares: Numer drives allocated as hot spares
        :param cached_bad_bbu: Enable write caches even when the bbu is missing or discharged
        :param after_vd: Specify an existing VD to add this new vd behind
        :return: AttributeString of command output
        """

        command = '/c{controller} add vd type={array_type}{size}drives={drives}  ' \
                  '{write_policy} {read_policy} {io_mode} {stripe_size}{spares}' \
                  '{cache_bad_bbu}{after_vd}{pdperarray}'.format(
                    **{'controller': controller,
                       'array_type': array_type,
                       'drives': drives,
                       'size': size and ' size={} '.format(size) or ' ',
                       'write_policy': write_policy,
                       'read_policy': read_policy,
                       'io_mode': io_mode,
                       'pdperarray': pdperarray and 'pdperarray={} '.format(pdperarray) or '',
                       'pdcache': pdcache and 'pdcache={} '.format(pdcache) or '',
                       'dimmerswitch': dimmerswitch and 'dimmerswitch={} '.format(dimmerswitch) or '',
                       'cachevd': cachevd and 'cachevd ' or '',
                       'stripe_size': stripe_size and 'strip={} '.format(stripe_size) or '',
                       'spares': spares and 'spares={} '.format(spares) or '',
                       'cache_bad_bbu': cached_bad_bbu and 'cachebadbbu ' or '',
                       'after_vd': after_vd and 'aftervd={} '.format(after_vd) or ''
                       })

        for level in self.span_arrays:
            if str(level) in array_type:
                if not pdperarray:
                    raise StorcliException('Span depth (pdperarray) must be specified')
                break

        out = self.run(command)

        lines = [l.strip() for l in out.splitlines() if l.strip()]

        # command always returns zero on 'syntax' errors, so do some light
        # parsing to see if command succeeded
        for idx in range(len(lines)):
            if lines[idx].find('help -') == 0:
                error_output = '\n'.join(lines[:idx])
                raise StorcliException('Error creating ld, response:\n\n{}'.format(error_output))

        return out

    def add_hotspare(self, controller, enclosure, slot, disk_groups=None):
        """
        Set drive as a hot spare drive for the controller
        :param controller: The controller
        :param enclosure:
        :param slot:
        :param disk_groups:
        :return:
        """
        if disk_groups:
            dgs = ','.join(str(d) for d in disk_groups)
        else:
            dgs = None

        self.run('/c{}/e{}/s{} add hotsparedrive{}'.format(
            controller,
            enclosure,
            slot,
            dgs and ' DGs={}'.format(dgs) or ''
        ))

    def start_erase(self, controller, enclosure, slot, pattern='simple'):
        log.info('Scheduling erase [%s] operation on /c%s/e%s/s%s',
                 pattern, controller, enclosure, slot)
        data = self.run('/c{}/e{}/s{} start erase {} J'.format(
            controller,
            enclosure,
            slot,
            pattern
        ))['Controllers'][0]
        self.check_command_status(data)

    def stop_erase(self, controller, enclosure, slot):
        log.info('Cancelling erase operation on /c%s/e%s/s%s',
                 controller, enclosure, slot)
        data = self.run('/c{}/e{}/s{} stop erase J'.format(
            controller,
            enclosure,
            slot
        ))['Controllers'][0]
        self.check_command_status(data)
        return data['Response Data']

    def show_erase(self, controller, enclosure, slot):
        data = self.run('/c{}/e{}/s{} show erase J'.format(
            controller,
            enclosure,
            slot
        ))['Controllers'][0]
        self.check_command_status(data)
        return data['Response Data']
