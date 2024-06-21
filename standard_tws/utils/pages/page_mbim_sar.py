from ..operate.base import BaseOperate
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial


# local file select
nv_config1 = [{'title': 'Quectel MBIM SAR Tool'},
               {'auto_id': "1053", 'control_type': "Edit"}]

# Init Context
Init_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "Init", 'control_type': "Button"}]

OpenDeviceSerives_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "OpenDeviceServices", 'control_type': "Button"}]

GetIsMbimReady_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetIsMbimReady", 'control_type': "Button"}]

# SAR NV
GetIsInSmartSarMode_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetIsInSmartSarMode", 'control_type': "Button"}]

DisableSmartSarMode_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "DisableSmartSarMode", 'control_type': "Button"}]

GetSarDiagEnable_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSarDiagEnable", 'control_type': "Button"}]

SetSarDiagEnable_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetSarDiagEnable", 'control_type': "Button"}]

# Reboot
SetDeviceReboot_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetDeviceReboot", 'control_type': "Button"}]

# Tradition SAR
GetLocalFileMD5_Tradition_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetLocalFileMD5", 'control_type': "Button", "auto_id": "1019"}]

GetSarNvMD5_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSarNvMD5", 'control_type': "Button"}]

SetSarValue_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetSarValue", 'control_type': "Button"}]

GetSarValue_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSarValue", 'control_type': "Button"}]

GetSarIndex_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSarIndex", 'control_type': "Button"}]

SetSarIndex_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetSarIndex", 'control_type': "Button"}]

SetSarIndex_number_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {"auto_id": "1060", 'control_type': "ComboBox"}]

# Smart SAR
GetLocalFileMD5_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetLocalFileMD5", 'control_type': "Button", "auto_id": "1058"}]

GetSmartSarNvMD5_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSmartSarNvMD5", 'control_type': "Button"}]

SetSmartSarValue_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetSmartSarValue", 'control_type': "Button"}]

GetSmartSarValue_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetSmartSarValue", 'control_type': "Button"}]

GetDprLevel_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "GetDprLevel", 'control_type': "Button"}]

SetDprLevel_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {'title': "SetDprLevel", 'control_type': "Button"}]

SetDprLevel_number_butoon = [{'title': 'Quectel MBIM SAR Tool'},
               {"auto_id": "1067", 'control_type': "ComboBox"}]

# MBIM SAR outlog
mbim_sar_outlog = [{'title': 'Quectel MBIM SAR Tool'},
                   {'class_name': "RichEdit20A"}]

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageMbimSar(BaseOperate):
    def __init__(self):
        super().__init__()

    """
    点击并输入
    """
    @watchdog("输入nv_config1")
    def input_nv_config1(self, nv_config_path):
        self.click_input_sth(nv_config1, nv_config_path)

    @property
    @watchdog("获取Init Context下Init按钮")
    def element_Init_butoon(self):
        return self.find_element(Init_butoon)

    @property
    @watchdog("获取mbim_sar_outlog")
    def element_mbim_sar_outlog(self):
        return self.find_element(mbim_sar_outlog)

    @property
    @watchdog("获取nv_config1")
    def element_nv_config1(self):
        return self.find_element(nv_config1)

    @property
    @watchdog("获取OpenDeviceSerives_butoon")
    def element_OpenDeviceSerives_butoon(self):
        return self.find_element(OpenDeviceSerives_butoon)

    @property
    @watchdog("获取GetIsMbimReady_butoon")
    def element_GetIsMbimReady_butoon(self):
        return self.find_element(GetIsMbimReady_butoon)

    @property
    @watchdog("获取GetIsInSmartSarMode_butoon")
    def element_GetIsInSmartSarMode_butoon(self):
        return self.find_element(GetIsInSmartSarMode_butoon)

    @property
    @watchdog("获取DisableSmartSarMode_butoon")
    def element_DisableSmartSarMode_butoon(self):
        return self.find_element(DisableSmartSarMode_butoon)

    @property
    @watchdog("获取GetLocalFileMD5_butoon")
    def element_GetLocalFileMD5_butoon(self):
        return self.find_element(GetLocalFileMD5_butoon)

    @property
    @watchdog("获取GetSmartSarNvMD5_butoon")
    def element_GetSmartSarNvMD5_butoon(self):
        return self.find_element(GetSmartSarNvMD5_butoon)

    @property
    @watchdog("获取GetSarDiagEnable_butoon")
    def element_GetSarDiagEnable_butoon(self):
        return self.find_element(GetSarDiagEnable_butoon)

    @property
    @watchdog("获取SetSarDiagEnable_butoon")
    def element_SetSarDiagEnable_butoon(self):
        return self.find_element(SetSarDiagEnable_butoon)

    @property
    @watchdog("获取SetSmartSarValue_butoon")
    def element_SetSmartSarValue_butoon(self):
        return self.find_element(SetSmartSarValue_butoon)

    @property
    @watchdog("获取GetSmartSarValue_butoon")
    def element_GetSmartSarValue_butoon(self):
        return self.find_element(GetSmartSarValue_butoon)

    @property
    @watchdog("获取SetDeviceReboot_butoon")
    def element_SetDeviceReboot_butoon(self):
        return self.find_element(SetDeviceReboot_butoon)

    @property
    @watchdog("获取GetLocalFileMD5_Tradition_butoon")
    def element_GetLocalFileMD5_Tradition_butoon(self):
        return self.find_element(GetLocalFileMD5_Tradition_butoon)

    @property
    @watchdog("获取GetSarNvMD5_butoon")
    def element_GetSarNvMD5_butoon(self):
        return self.find_element(GetSarNvMD5_butoon)

    @property
    @watchdog("获取SetSarValue_butoon")
    def element_SetSarValue_butoon(self):
        return self.find_element(SetSarValue_butoon)

    @property
    @watchdog("获取GetSarValue_butoon")
    def element_GetSarValue_butoon(self):
        return self.find_element(GetSarValue_butoon)

    @property
    @watchdog("获取GetSarIndex_butoon")
    def element_GetSarIndex_butoon(self):
        return self.find_element(GetSarIndex_butoon)

    @property
    @watchdog("获取SetSarIndex_butoon")
    def element_SetSarIndex_butoon(self):
        return self.find_element(SetSarIndex_butoon)

    @property
    @watchdog("获取SetSarIndex_number_butoon")
    def element_SetSarIndex_number_butoon(self):
        return self.find_element(SetSarIndex_number_butoon)

    @property
    @watchdog("获取GetDprLevel_butoon")
    def element_GetDprLevel_butoon(self):
        return self.find_element(GetDprLevel_butoon)

    @property
    @watchdog("获取SetDprLevel_butoon")
    def element_SetDprLevel_butoon(self):
        return self.find_element(SetDprLevel_butoon)

    @property
    @watchdog("获取SetDprLevel_number_butoon")
    def element_SetDprLevel_number_butoon(self):
        return self.find_element(SetDprLevel_number_butoon)
