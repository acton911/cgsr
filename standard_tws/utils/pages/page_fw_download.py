from ..operate.base import BaseOperate
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial


# Button：输入SIM卡PIN码后下一步的按钮
login_ok_button = [{'title': 'Input Line Number'},
                   {'class_name': "Button", 'title': "OK"}]

login_ok_button_2 = [{'title_re': 'MT'},
                     {'title': 'Input Line Number'},
                     {'class_name': "Button", 'title': "OK"}]

# Button：Settings按钮
settings_button = [{'title_re': 'FW_Download*', "found_index": 0},
                   {"class_name": "Button", 'title': "Settings"}]

# Button：passwd OK按钮
passwd_ok_button = [{'title_re': 'FW_Download*', "found_index": 0},
                    {"title": "Password"},
                    {'class_name': "Button", 'title': 'OK'}]

# Button: reset_after
reset_after_download_button = [{'title_re': 'FW_Download*', "found_index": 0},
                               {"title": "Multiple Ports DL Tool Settings"},
                               {'class_name': "Button", 'title': 'Reset After DL For Firehose Mode'}]

# Button: Settings页面OK按钮
settings_ok_button = [{'title_re': 'FW_Download*', "found_index": 0},
                      {"title": "Multiple Ports DL Tool Settings"},
                      {'class_name': "Button", 'auto_id': '1'}]

# Button: Load FW Files
load_fw_files = [{'title_re': 'FW_Download*', "found_index": 0},
                 {"class_name": "Button", 'title': "Load FW Files"}]

# Button: 确认MBN路径按钮
mbn_ok_button = [{'title_re': 'FW_Download*', "found_index": 0},
                 {"class_name": "Button", 'auto_id': "1"}]

# Button：第一路下载button
first_download_button = [{'title_re': 'FW_Download*', "found_index": 0},
                         {"class_name": "Button", 'auto_id': "1055"}]

# Edit：passwd
passwd_edit = [{'title_re': "FW_Download*", "found_index": 0},
               {"title": "Password"},
               {'class_name': "Edit"}]

# Edit: First download edit
first_download_edit = [{'title_re': 'FW_Download*', "found_index": 0},
                       {"title": "Multiple Ports DL Tool Settings"},
                       {'class_name': "Edit", 'auto_id': '1239'}]

# Edit：MBN路径EDIT
mbn_path_edit = [{'title_re': 'FW_Download*', "found_index": 0},
                 {'class_name': 'Edit', 'auto_id': '1148'}]

# ComboBox：Operation Mode
operation_mode_combobox = [{'title_re': 'FW_Download*', "found_index": 0},
                           {"title": "Multiple Ports DL Tool Settings"},
                           {'class_name': "ComboBox", 'title': 'Operation Mode:'}]

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageFWDownload(BaseOperate):
    def __init__(self):
        super().__init__()

    @property
    @watchdog("获取登录确认按钮")
    def element_login_ok_button(self):
        return self.find_element(login_ok_button)

    @property
    @watchdog("获取登录确认按钮2")
    def element_login_ok_button_2(self):
        return self.find_element(login_ok_button_2)

    @property
    @watchdog("获取settings按钮")
    def element_settings_button(self):
        return self.find_element(settings_button)

    @property
    @watchdog("获取密码输入界面")
    def element_passwd_edit(self):
        return self.find_element(passwd_edit)

    @property
    @watchdog("获取passwd OK按钮")
    def element_passwd_ok_button(self):
        return self.find_element(passwd_ok_button)

    @property
    @watchdog("获取下载模式ComboBox")
    def element_operation_mode_combobox(self):
        return self.find_element(operation_mode_combobox)

    @property
    @watchdog("获取reset after download button")
    def element_reset_after_down_button(self):
        return self.find_element(reset_after_download_button)

    @property
    @watchdog("获取第一路下载口Edit")
    def element_first_download_edit(self):
        return self.find_element(first_download_edit)

    @property
    @watchdog("获取设置页面OK按钮")
    def element_settings_ok_button(self):
        return self.find_element(settings_ok_button)

    @property
    @watchdog("获取load fw files 按钮")
    def element_load_fw_files(self):
        return self.find_element(load_fw_files)

    @property
    @watchdog("获取MBN path Edit")
    def element_mbn_path_edit(self):
        return self.find_element(mbn_path_edit)

    @property
    @watchdog("获取MBN确认按钮")
    def element_mbn_ok_button(self):
        return self.find_element(mbn_ok_button)

    @property
    @watchdog("获取第一路下载按钮")
    def element_first_download_button(self):
        return self.find_element(first_download_button)
