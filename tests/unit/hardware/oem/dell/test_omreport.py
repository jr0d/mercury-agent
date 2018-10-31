import os
import unittest

from mercury_agent.hardware.oem.dell import om_xml_deserializer as om


def read_resource(filename):
    with open(os.path.join(os.path.dirname(__file__),
                           'resources/' + filename), 'rb') as fp:
        return fp.read()


class TestOMXML(unittest.TestCase):
    def setUp(self):
        self.chassis_xml = read_resource('chassis.xml')

    def test_loader(self):
        xl = om.XLoader(self.chassis_xml)
        self.assertEqual(xl.root.tag, 'OMA')

    def test_chassis_chassis(self):
        xl = om.XLoader(self.chassis_xml)
        chassis = om.XMLChassisStatus(xl.root)
        self.assertEqual(chassis['processor']['status_string'], 'OK')
