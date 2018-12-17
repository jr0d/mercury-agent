import unittest

import mock
from mercury.common.helpers.cli import CLIResult

from mercury_agent.hardware.oem.hp import hpasmcli


class TestHPASMCLI(unittest.TestCase):
    show_server_data = '\n\nSystem        : ProLiant DL380 Gen9\nSerial No.    : TC51NR9952\n' \
               'ROM version   : v2.60 (05/21/2018) P89\nUEFI Support  : Yes\niLo ' \
               'present   : Yes\nEmbedded NICs : 8\n\tNIC1 MAC: 38:63:bb:3f:4b:f4\n\t' \
               'NIC2 MAC: 38:63:bb:3f:4b:f5\n\tNIC3 MAC: 38:63:bb:3f:4b:f6\n\tNIC4 MAC: ' \
               '38:63:bb:3f:4b:f7\n\tNIC5 MAC: 8c:dc:d4:ad:d6:d0\n\tNIC6 MAC: ' \
               '8c:dc:d4:ad:d6:d1\n\tNIC7 MAC: 68:05:ca:39:89:a0\n\tNIC8 MAC: 68:05:ca:39:89:a1' \
               '\n\nProcessor: 0\n\tName         : Intel(R) Xeon(R) CPU E5-2630 v3 @ 2.40GHz' \
               '\n\tStepping     : 2\n\tSpeed        : 2400 MHz\n\tBus          : 100 MHz\n\tCore' \
               '         : 8\n\tThread       : 16\n\tSocket       : 1\n\tLevel1 Cache : ' \
               '512 KBytes\n\tLevel2 Cache : 2048 KBytes\n\tLevel3 Cache : 20480 KBytes\n\t' \
               'Status       : Ok\n\nProcessor: 1\n\tName         : ' \
               'Intel(R) Xeon(R) CPU E5-2630 v3 @ 2.40GHz\n\tStepping     : 2\n\t' \
               'Speed        : 2400 MHz\n\tBus          : 100 MHz\n\tCore         : 8\n\t' \
               'Thread       : 16\n\tSocket       : 2\n\tLevel1 Cache : 512 KBytes\n\t' \
               'Level2 Cache : 2048 KBytes\n\tLevel3 Cache : 20480 KBytes\n\tStatus       : Ok' \
               '\n\nProcessor total  : 2\n\nMemory installed : 131072 MBytes\nECC ' \
               'supported    : Yes\n\n\n'
    show_dimm_data = """
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
    show_power_supply_data = '\nPower supply #1\n\tPresent  : Yes\n\tRedundant: Yes' \
                             '\n\tCondition: Ok\n\tHotplug  : Supported\n\tPower    : 110 ' \
                             'Watts\nPower supply #2\n\tPresent  : Yes\n\tRedundant: Yes' \
                             '\n\tCondition: Ok\n\tHotplug  : Supported\n\tPower    : 100 Watts\n\n'

    def setUp(self):
        self.mock_cli_patch = mock.patch('mercury_agent.hardware.oem.hp.hpasmcli.cli')
        self.mock_cli = self.mock_cli_patch.start()
        self.mock_cli.find_in_path = mock.Mock(return_value='/bin/bash')

    def tearDown(self):
        self.mock_cli_patch.stop()

    def test_show_server(self):
        self.mock_cli.run = mock.Mock(return_value=CLIResult(
            self.show_server_data, '', 0))

        hpasm = hpasmcli.HPASMCLI()
        details = hpasm.show_server()

        self.assertEqual(len(details['processors']), 2)
        self.assertEqual(details['system'], 'ProLiant DL380 Gen9')

    def test_show_dimmm(self):
        self.mock_cli.run = mock.Mock(return_value=CLIResult(
            self.show_dimm_data, '', 0))
        hpasm = hpasmcli.HPASMCLI()
        details = hpasm.show_dimm()

        self.assertEqual(details[-1]['processor_#'], 2)

    def test_show_power_supply(self):
        self.mock_cli.run = mock.Mock(return_value=CLIResult(
            self.show_power_supply_data, '', 0))

        hpasm = hpasmcli.HPASMCLI()
        power_supplies = hpasm.show_powersupply()
        for ps in power_supplies:
            self.assertEqual(ps['condition'], 'Ok')
