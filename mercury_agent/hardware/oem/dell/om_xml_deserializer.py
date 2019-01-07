from io import BytesIO
from lxml import etree


class XMLError(Exception):
    pass


class XLoader(object):
    def __init__(self, xml_data):
        self.xml_data = xml_data

    @property
    def root(self):
        return etree.parse(BytesIO(self.xml_data)).getroot()


class XMLAbout(dict):
    def __init__(self, oma):
        super(XMLAbout, self).__init__()
        about = oma.find('About')
        if about is None:
            raise XMLError('About element is missing.')

        self['components'] = list()
        for child in about:
            if child.tag == 'Component':
                self._add_component(child)
            else:
                self[child.tag] = child.text.strip()

    def _add_component(self, component):
        d = dict()
        for child in component:
            d[child.tag] = child.text.strip()
        self['components'].append(d)


class XMLChassisStatus(dict):
    status_translation = {
        1: "Unknown",
        2: "Ok",
        3: "Non-critical",
        4: "Critical"
    }

    # triple (tag, object list tag, description)
    element_list = [
        ('intrusion', 'IntrusionObj', 'IntrusionLoc'),
        ('voltages', 'VoltageObj', 'ProbeLocation'),
        ('temperatures', 'TemperatureObj', 'ProbeLocation'),
        ('fans', 'Redundancy', 'Fan System'),
        ('currents', 'CurrentObj', 'ProbeLocation'),
        ('powersupply', 'PowerSupplyObj', 'PSLocation'),
        ('powermonitoring', 'PowerConsumptionDataObj', 'Identifier'),
        ('processor', 'DevProcessorObj', 'Brand'),
        ('esmlog', 'LogObj', 'HardwareLog'),
        ('memory', 'MemDevObj', 'Memory'),
        ('batteries', 'BatteryObj', 'ProbeLocation'),
        ('sdcard', 'SDCard', 'SDCardLocation')
    ]

    computed_status_tag = 'computedobjstatus'
    objstatus_tag = 'objstatus'

    def __init__(self, root):
        super(XMLChassisStatus, self).__init__()
        parent = root[0]
        for tag, obj, obj_desc in self.element_list:
            element = parent.find(tag)
            if element is None:
                continue
            self[tag] = dict()
            status_element = element.find(self.computed_status_tag)
            self[tag]['status'] = int(status_element.text.strip())
            self[tag]['status_string'] = status_element.attrib.get('strval')
            self[tag]['sensors'] = list()

            sensor_elements = element.findall(obj)
            for sensor_element in sensor_elements:
                sensor_dict = dict()
                description_element = sensor_element.find(obj_desc)
                if description_element is not None:
                    sensor_dict['description'] = description_element.text
                else:
                    sensor_dict['description'] = obj_desc

                sensor_dict['status'] = sensor_element.find(self.objstatus_tag).text
                self[tag]['sensors'].append(sensor_dict)

    @property
    def errors(self):
        err = list()
        for tag in self:
            if self[tag]['status'] == 2:
                continue
            error_dict = self[tag]
            error_dict['component'] = tag
            err.append(error_dict)

        return err


class XMLVDisk(dict):
    vdisk_obj_tag = 'DCStorageObject'

    def __init__(self, oma):
        super(XMLVDisk, self).__init__()
        vdisk_element = oma.find('VirtualDisks')
        if vdisk_element is None:
            return

        obj_elements = vdisk_element.findall(self.vdisk_obj_tag)
        for obj in obj_elements:
            device_id = int(obj.find('DeviceID').text)
            self[device_id] = dict()
            self[device_id]['status'] = int(obj.find('ObjStatus').text)
            self[device_id]['state'] = int(obj.find('ObjState').text)
            self[device_id]['read_policy'] = int(obj.find('DefaultReadPolicy').text)
            self[device_id]['write_policy'] = int(obj.find('DefaultWritePolicy').text)
            self[device_id]['name'] = obj.find('Name').text


class XMLController(dict):
    controller_obj_tag = 'DCStorageObject'

    def __init__(self, oma):
        super(XMLController, self).__init__()
        controller_element = oma.find('Controllers')
        if controller_element is None:
            return
            # TODO: See what multiple controllers looks like
        obj_element = controller_element.find(self.controller_obj_tag)
        self['name'] = obj_element.find('Name').text
        self['status'] = int(obj_element.find('ObjStatus').text)
        self['state'] = int(obj_element.find('ObjState').text)


class XMLPDisk(dict):
    pdisk_obj_tag = 'DCStorageObject'

    def __init__(self, oma):
        super(XMLPDisk, self).__init__()
        pdisk_element = oma.find('ArrayDisks')
        obj_elements = pdisk_element.findall(self.pdisk_obj_tag)
        for obj in obj_elements:
            device_id = int(obj.find('DeviceID').text)
            self[device_id] = dict()
            self[device_id]['status'] = int(obj.find('ObjStatus').text)
            self[device_id]['state'] = int(obj.find('ObjState').text)
            self[device_id]['vendor'] = obj.find('Vendor').text
