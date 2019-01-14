import re

from mercury.common.helpers import cli


invalid_charcaters = '.$ /\\\\'


class HPAsmException(Exception):
    pass


class HPASMCLI:
    def __init__(self, hpasmcli_path='hpasmcli'):
        """
        A class interface for the hpasmcli utility
        :param hpasmcli_path:
        """
        self.hpasmcli = cli.find_in_path(hpasmcli_path)

        if not self.hpasmcli:
            raise HPAsmException('Could not find hpasmcli binary')

    @staticmethod
    def fix_key_names(data):
        rgx = re.compile('[{}]'.format(invalid_charcaters))
        return rgx.sub('_', data.strip(invalid_charcaters).lower())

    @staticmethod
    def convert_digit(data):
        return int(data) if data.isdigit() else data

    def hpasm_run(self, command):
        result = cli.run('{} -s \'{}\''.format(self.hpasmcli, command))
        if result.returncode:
            raise HPAsmException('Error running command: {}'.format(command))
        return result

    def show_server(self):
        """
        Data is probably formatted like so:

            System        : ProLiant DL380 Gen9
            Serial No.    : TC51NR9952
            ROM version   : v2.60 (05/21/2018) P89
            UEFI Support  : Yes
            iLo present   : Yes
            Embedded NICs : 8
                NIC1 MAC: 38:63:bb:3f:4b:f4
                NIC2 MAC: 38:63:bb:3f:4b:f5
                NIC3 MAC: 38:63:bb:3f:4b:f6
                NIC4 MAC: 38:63:bb:3f:4b:f7
                NIC5 MAC: 8c:dc:d4:ad:d6:d0
                NIC6 MAC: 8c:dc:d4:ad:d6:d1
                NIC7 MAC: 68:05:ca:39:89:a0
                NIC8 MAC: 68:05:ca:39:89:a1

            Processor: 0
                Name         : Intel(R) Xeon(R) CPU E5-2630 v3 @ 2.40GHz
                Stepping     : 2
                Speed        : 2400 MHz
                Bus          : 100 MHz
                Core         : 8
                Thread       : 16
                Socket       : 1
                Level1 Cache : 512 KBytes
                Level2 Cache : 2048 KBytes
                Level3 Cache : 20480 KBytes
                Status       : Ok

            Processor: 1
                Name         : Intel(R) Xeon(R) CPU E5-2630 v3 @ 2.40GHz
                Stepping     : 2
                Speed        : 2400 MHz
                Bus          : 100 MHz
                Core         : 8
                Thread       : 16
                Socket       : 2
                Level1 Cache : 512 KBytes
                Level2 Cache : 2048 KBytes
                Level3 Cache : 20480 KBytes
                Status       : Ok

            Processor total  : 2

            Memory installed : 131072 MBytes
            ECC supported    : Yes
        """
        data = self.hpasm_run('SHOW SERVER')

        details = {}
        embedded_nics_context = False
        processor_context = False
        processor_index = -1
        for line in [_ for _ in data.splitlines() if _]:
            label, value = (_.strip() for _ in line.split(':', 1))
            label = self.fix_key_names(label)
            value = self.convert_digit(value)
            if embedded_nics_context or processor_context:
                if line[0] != '\t':
                    embedded_nics_context = processor_context = False

            if label == 'embedded_nics':
                details[label] = {'count': int(value), 'nics': []}
                embedded_nics_context = True
            elif label == 'processor':
                processor_context = True
                processor_index = value
                if processor_index == 0:
                    details['processors'] = [{}]
                else:
                    details['processors'].append({})
            elif embedded_nics_context:
                details['embedded_nics']['nics'].append({label: value})
            elif processor_context:
                details['processors'][processor_index][label] = value
            else:
                details[label] = value

        return details

    def show_dimm(self):
        """
        Example output:

            DIMM Configuration
            ------------------
            Processor #:                     1
            Module #:                     1
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     1
            Module #:                     4
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     1
            Module #:                     9
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     1
            Module #:                     12
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     2
            Module #:                     1
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     2
            Module #:                     4
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     2
            Module #:                     9
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

            Processor #:                     2
            Module #:                     12
            Present:                      Yes
            Form Factor:                  9h
            Memory Type:                  DDR4(1ah)
            Size:                         16384 MB
            Speed:                        2133 MHz
            Supports Lock Step:           No
            Configured for Lock Step:     No
            Status:                       Ok

        """
        data = self.hpasm_run('SHOW DIMM')

        # Knocks off the first three lines then splits on double \n
        segments = '\n'.join(data.splitlines()[3:]).split("\n\n")

        details = []
        for segment in segments:
            if segment:
                dimm_info = {}
                details.append(dimm_info)
                for line in segment.splitlines():
                    key, value = (_.strip() for _ in line.split(':', 1))
                    dimm_info[self.fix_key_names(key)] = self.convert_digit(value)
        return details

    def show_powersupply(self):
        data = self.hpasm_run('SHOW POWERSUPPLY')
        power_supplies = []
        ps_data = {}
        for line in [_ for _ in data.splitlines() if _]:
            if 'Power supply' in line:
                if ps_data:
                    power_supplies.append(ps_data)
                ps_data = {}
                continue
            key, value = (_.strip() for _ in line.split(':', 1))
            ps_data[self.fix_key_names(key)] = value
        power_supplies.append(ps_data)
        return power_supplies

    def clear_iml(self):
        return self.hpasm_run('CLEAR IML')
