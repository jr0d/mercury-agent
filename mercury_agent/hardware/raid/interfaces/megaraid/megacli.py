import os
import time
import logging

from subprocess import Popen, PIPE

log = logging.getLogger(__name__)



class LSIRaidException(Exception):
    """ Raised exclusively by Megacli classes """
    pass


class LSIRaidTimeoutException(LSIRaidException, OSError):
    pass


def clear_lsi(lsi_raid, adapter=None, wait_period=10):
    # TODO: If adapter is blank, attempt to only clear controllers
    # we know about to potentially not blow away controllers Core doesn't
    # want us to!
    wait_period = wait_period if wait_period >= 1 else 1

    log.info('Clearing config')
    lsi_raid.clear_config(adapter)

    log.info('Clearing foreign configs, if present')
    lsi_raid.clear_foreign_configs(adapter)
    time.sleep(wait_period)

    log.info('Refreshing RAID Controller')
    lsi_raid.refresh()


class LSIRaid(object):
    adapter = None

    def __init__(self, megacli_bin='/usr/sbin/megacli', adapter=0, use_sudo=False):

        self.adapter = adapter
        self.megacli_bin = megacli_bin
        if not os.path.isfile(self.megacli_bin):
            raise LSIRaidException('megacli binary is missing')
        self.use_sudo = use_sudo
        self.pdisks, self.vdisks, self.enclosure, self.raw_adapter_info, \
            self.clear = None, None, None, None, None
        self.refresh()

    def refresh(self):
        self.pdisks = self.get_physical_disks(self.adapter)
        self.vdisks = self.get_virtual_disks(self.adapter)
        self.enclosure = self.get_enclosure_id(self.adapter)
        self.raw_adapter_info = self.get_adapter_raw()

        self.clear = not self.count_virtual_disks()

    def megacli(self, args, bufsize=1048567, timeout=300):
        """
        Execute a MegaCLI system command with a timeout of 300 seconds approx.
        """
        timeout = timeout if timeout >= 1 else 1
        cmd = [self.megacli_bin] + args.split()
        if self.use_sudo:
            cmd = ['sudo'] + cmd
        cmd += ['-NoLog']
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, bufsize=bufsize)
        for _ in range(1, 10 * timeout):
            if p.poll() is not None:
                out, err = p.communicate()
                ret = p.returncode
                return out, err, ret
            time.sleep(0.1)
        raise LSIRaidTimeoutException('Command took too long to execute: '
                                      '{} {}'.format(self.megacli_bin, args))

    def get_adapter_raw(self, adapter='all'):
        out, err, ret = self.megacli('-AdpAllInfo -a{0}'.format(
            adapter or self.adapter))
        if ret:
            raise LSIRaidException(
                ('Could not get adapter info - {0}: '
                 '{1} {2}').format(ret, out, err))
        return out.splitlines()

    def clear_config(self, adapter=None):
        _adapter = 'all' if adapter is None else adapter
        return self.megacli('-CfgClr -a{0}'.format(_adapter))

    def init_logical_drives(self, adapter=None):
        _adapter = 'all' if adapter is None else adapter
        return self.megacli('-LDInit -Start -LALL -a{0}'.format(_adapter))

    def clear_foreign_configs(self, adapter=None):
        _adapter = 0 if adapter is None else adapter
        return self.megacli('-CfgForeign -Clear -a{0}'.format(_adapter))

    def count_physical_disks(self):
        out, err, ret = self.megacli('-PDGetNum -a{0}'.format(self.adapter))
        for line in out.splitlines():
            if 'Adapter' in line:
                return int(line.split(':')[1].strip())
        return 0

    def count_virtual_disks(self):
        out, err, ret = self.megacli('-LDGetNum -a{0}'.format(self.adapter))
        for line in out.splitlines():
            if 'Adapter' in line:
                return int(line.split(':')[1].strip())
        return 0

    def create_array(self, raid_level, drives):
        out = '-CfgLDAdd -r' + str(raid_level)
        array_list = ['{}:{}'.format(self.enclosure, x) for x in drives]
        array_out = ' [{}]'.format(','.join(array_list))
        out = '{} {} WB RA Cached -a{}'.format(out, array_out, self.adapter)
        sout, err, ret = self.megacli(out)
        if ret:
            return dict(error=True, command=out, stdout=sout, stderr=err)
        return dict(error=False, command=out, stdout=sout, stderr=err)

    def get_enclosure_id(self, adapter=0):
        out, err, ret = self.megacli('-EncInfo -a{0}'.format(adapter))
        for line in out.splitlines():
            if 'Device ID' in line:
                try:
                    return int(line.split(':')[1].strip())
                except ValueError:
                    continue
        # this is a kludge, when no enclosure is found
        return ""

    def get_physical_disks(self, adapter=0):
        disks = list()
        count = 0
        num = self.count_physical_disks()
        if not num:
            return dict()

        out, err, ret = self.megacli('-PdList -a{0}'.format(adapter))
        options = {
            'Device Id': 'device_id',
            'Enclosure Device ID': 'enclosure',
            'Slot Number': 'slot_number',
            'Media Error Count': 'media_errors',
            'Other Error Count': 'other_errors',
            'Predictive Failure Count': 'predictive_errors',
        }

        def raise_err(key):
            if key == 'Enclosure Device ID':
                enc_out, enc_err, _ = self.megacli(
                    '-EncInfo -a{}'.format(adapter))
                raise LSIRaidException(
                    "Could not read from controller, please make sure it is "
                    "seated correctly: {} {}".format(enc_out, enc_err))
            raise LSIRaidException("Error reading raid information for "
                                   "'{}' from megacli".format(key))
        count = 1
        for x in range(0, num):
            disk = dict()
            for line in out.splitlines()[count:]:
                count += 1
                for key, value in options.items():
                    if key in line:
                        try:
                            disk[value] = int(line.split(':')[1].strip())
                        except (ValueError, IndexError):
                            raise_err(key)
                        else:
                            break
                else:
                    if 'Raw Size' in line:
                        disk['size'] = float(line.split(
                            ':')[1].split()[0].strip())
                    elif 'Firmware state' in line:
                        disk['state'] = line.split(':', 1)[1]
                        break

            disks.append(disk)

        disks.sort(key=lambda d: '%05d:%05d' % (d['device_id'],
                                                d['slot_number']))
        return disks

    def get_virtual_disk_members(self, vid, num):
        out, err, ret = self.megacli('-LDPDInfo -a{0}'.format(self.adapter))
        count = 0
        pos = 0
        pds = list()
        for line in out.splitlines():
            if 'Virtual Drive:' in line:
                if int(line.split()[2].strip()) == vid:
                    pos = out.splitlines().index(line)
                    break

        for line in out.splitlines()[pos:]:
            if 'Device Id' in line:
                pds.append(int(
                    line.split(':')[1].strip()))
                count += 1
            if count == num:
                break
        return pds

    def get_virtual_disks(self, adapter=0):
        vdisks = list()
        count = 0
        num = self.count_virtual_disks()
        if not num:
            return dict()

        out, err, ret = self.megacli('-LdInfo -Lall -a{0}'.format(adapter))
        for x in range(0, num):
            vd = dict()
            for line in out.splitlines()[count:]:
                if 'Virtual Drive:' in line:
                    vd['id'] = int(line.split(':')[1].split()[0].strip())
                    count += 1
                    continue

                if 'RAID Level' in line:
                    primary = int(line.split(':')[1].split(',')[0].split('-')[1])
                    secondary = int(line.split(':')[1].split(',')[1].split('-')[1])
                    vd['raid_level'] = (primary, secondary)
                    count += 1
                    continue

                if 'Number Of Drives' in line:
                    vd['drive_count'] = int(line.split(':')[1].split()[0].strip())
                    count += 1
                    continue

                if 'Span Depth' in line:
                    vd['span_depth'] = int(line.split(':')[1].split()[0].strip())
                    count += 1
                    break
                count += 1

            phys_ids = self.get_virtual_disk_members(
                        vd.get('id'),
                        vd.get('drive_count'))
            vd['phys_ids'] = phys_ids
            vdisks.append(vd)

        return vdisks
