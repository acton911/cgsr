from ctypes.wintypes import DWORD, LPCWSTR, LPDWORD
from ctypes.wintypes import WORD
from ctypes.wintypes import BYTE
from ctypes.wintypes import BOOL
from ctypes.wintypes import HWND
from ctypes.wintypes import PULONG
from ctypes.wintypes import PDWORD
from ctypes.wintypes import LPVOID
from ctypes.wintypes import HKEY
import ctypes

setupapi = ctypes.windll.LoadLibrary("setupapi")
advapi32 = ctypes.windll.LoadLibrary("Advapi32")


class Port:
    def __init__(self, num, desc, hwid):
        self.num = num
        self.desc = desc
        self.hwid = hwid

    def __repr__(self):
        return "Port({}, {}, {})".format(self.num, self.desc, self.hwid)

    def __getitem__(self, item):
        if isinstance(item, str) and hasattr(self, item):
            return getattr(self, item)
        elif isinstance(item, int):
            if item == 0:
                return self.num
            elif item == 1:
                return self.desc
            elif item == 2:
                return self.hwid
            else:
                raise IndexError("Port only support indexing 0, 1, 2")
        else:
            raise TypeError("Fail to get property from Port.")


# Structures
class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', DWORD),
        ('Data2', WORD),
        ('Data3', WORD),
        ('Data4', BYTE * 8)
    ]

    def __str__(self):
        return "{{{:08x}-{:04x}-{:04x}-{}-{}}}".format(
            self.Data1,
            self.Data2,
            self.Data3,
            ''.join(["{:02x}".format(d) for d in self.Data4[:2]]),
            ''.join(["{:02x}".format(d) for d in self.Data4[2:]]),
        )

    def __getitem__(self, item):
        return getattr(self, item)


class SP_DEVINFO_DATA(ctypes.Structure):  # noqa
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', PULONG)
    ]


# error check
def error_check(result, func, args):
    if not result:
        raise ctypes.WinError()
    return result


# Definition of args
PBYTE = LPBYTE = ctypes.c_void_p
PCWSTR = ctypes.c_wchar_p
DIGCF_PRESENT = 0x00000002  # SetupDiGetClassDevsW param
DICS_FLAG_GLOBAL = 0x00000001  # SetupDiOpenDevRegKey
DIREG_DEV = 0x00000001  # SetupDiOpenDevRegKey
SPDRP_LOCATION_PATHS = 0x00000023  # SetupDiGetDeviceRegistryPropertyW
SPDRP_FRIENDLYNAME = 0x0000000C  # SetupDiGetDeviceRegistryPropertyW
SPDRP_HARDWAREID = 0x00000001  # SetupDiGetDeviceRegistryPropertyW
SPDRP_DEVICEDESC = 0x00000000

# functions
RegQueryValueExW = advapi32.RegQueryValueExW
RegQueryValueExW.argtypes = [HKEY, LPCWSTR, LPDWORD, LPDWORD, LPBYTE, LPDWORD]
RegQueryValueExW.restype = ctypes.wintypes.LONG

RegCloseKey = advapi32.RegCloseKey
RegCloseKey.argtypes = [HKEY]
RegCloseKey.restype = DWORD

SetupDiClassGuidsFromNameW = setupapi.SetupDiClassGuidsFromNameW
SetupDiClassGuidsFromNameW.argtypes = [PCWSTR, ctypes.POINTER(GUID), DWORD, PDWORD]
SetupDiClassGuidsFromNameW.restype = BOOL
SetupDiClassGuidsFromNameW.errcheck = error_check

SetupDiGetClassDevsW = setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevsW.argtypes = [ctypes.POINTER(GUID), PCWSTR, HWND, DWORD]
SetupDiGetClassDevsW.restype = HWND
SetupDiGetClassDevsW.errcheck = error_check

SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.argtypes = [LPVOID, DWORD, ctypes.POINTER(SP_DEVINFO_DATA)]
SetupDiEnumDeviceInfo.restype = BOOL

SetupDiOpenDevRegKey = setupapi.SetupDiOpenDevRegKey
SetupDiOpenDevRegKey.argtypes = [LPVOID, ctypes.POINTER(SP_DEVINFO_DATA), DWORD, DWORD, DWORD, DWORD]
SetupDiOpenDevRegKey.restype = HKEY
SetupDiOpenDevRegKey.errcheck = error_check

SetupDiGetDeviceRegistryPropertyW = setupapi.SetupDiGetDeviceRegistryPropertyW
SetupDiGetDeviceRegistryPropertyW.argtypes = [LPVOID, ctypes.POINTER(SP_DEVINFO_DATA), DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryPropertyW.restype = BOOL

SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [LPVOID]
SetupDiDestroyDeviceInfoList.restype = BOOL


def get_network_card_names():
    network_card_name_list = []
    net_GUIDs = (GUID * 8)()
    net_required_size = DWORD()
    SetupDiClassGuidsFromNameW(
        'Net',
        net_GUIDs,
        ctypes.sizeof(net_GUIDs),
        ctypes.pointer(net_required_size)
    )

    GUIDs = net_GUIDs[:net_required_size.value]

    for guid in GUIDs:
        gid = SetupDiGetClassDevsW(
            ctypes.pointer(guid),
            None,
            None,
            DIGCF_PRESENT
        )
        dev_info = SP_DEVINFO_DATA()
        dev_info.cbSize = ctypes.sizeof(dev_info)

        index = 0
        while SetupDiEnumDeviceInfo(gid, index, ctypes.pointer(dev_info)):
            index += 1

            friendly_name_buffer = ctypes.create_unicode_buffer(250)
            SetupDiGetDeviceRegistryPropertyW(
                gid,
                ctypes.pointer(dev_info),
                SPDRP_FRIENDLYNAME,
                None,
                ctypes.pointer(friendly_name_buffer),
                ctypes.sizeof(friendly_name_buffer) - 1,
                None,
            )
            network_card_name_list.append(friendly_name_buffer.value)
        SetupDiDestroyDeviceInfoList(gid)
    return network_card_name_list


def get_ports_hardware_id():
    # Get Ports GUIDs
    ports_GUIDs = (GUID * 8)()
    ports_required_size = DWORD()
    SetupDiClassGuidsFromNameW(
        'Ports',
        ports_GUIDs,
        ctypes.sizeof(ports_GUIDs),
        ctypes.byref(ports_required_size)
    )

    # Get Modem GUIDs
    modem_GUIDs = (GUID * 8)()
    modem_required_size = DWORD()
    SetupDiClassGuidsFromNameW(
        'Modem',
        modem_GUIDs,
        ctypes.sizeof(modem_GUIDs),
        ctypes.pointer(modem_required_size)
    )

    # Modem GUIDs and Ports GUIDS
    GUIDs = ports_GUIDs[:ports_required_size.value] + modem_GUIDs[:modem_required_size.value]

    for guid in GUIDs:
        gid = SetupDiGetClassDevsW(
            ctypes.pointer(guid),
            None,
            None,
            DIGCF_PRESENT
        )
        dev_info = SP_DEVINFO_DATA()
        dev_info.cbSize = ctypes.sizeof(dev_info)

        index = 0
        while SetupDiEnumDeviceInfo(gid, index, ctypes.pointer(dev_info)):
            index += 1

            hkey = SetupDiOpenDevRegKey(
                gid,
                ctypes.pointer(dev_info),
                DICS_FLAG_GLOBAL,
                0,
                DIREG_DEV,
                0x00000001
            )

            port_name_buffer = ctypes.create_unicode_buffer(250)
            RegQueryValueExW(
                hkey,
                "PortName",
                None,
                None,
                ctypes.byref(port_name_buffer),
                ctypes.wintypes.ULONG(ctypes.sizeof(port_name_buffer) - 1)
            )
            RegCloseKey(hkey)

            desc_buffer = ctypes.create_unicode_buffer(250)
            SetupDiGetDeviceRegistryPropertyW(
                gid,
                ctypes.pointer(dev_info),
                SPDRP_DEVICEDESC,
                None,
                ctypes.pointer(desc_buffer),
                ctypes.sizeof(desc_buffer) - 1,
                None,
            )

            hardware_id_buffer = ctypes.create_unicode_buffer(250)
            SetupDiGetDeviceRegistryPropertyW(
                gid,
                ctypes.pointer(dev_info),
                SPDRP_HARDWAREID,
                None,
                ctypes.pointer(hardware_id_buffer),
                ctypes.sizeof(hardware_id_buffer) - 1,
                None,
            )
            yield Port(port_name_buffer.value, desc_buffer.value, hardware_id_buffer.value)
        SetupDiDestroyDeviceInfoList(gid)


def ports():
    return list(get_ports_hardware_id())


if __name__ == '__main__':
    # get_network_card_names()
    print(ports())
