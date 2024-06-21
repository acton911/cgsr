from ..operate.base import BaseOperate
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial

# USB View 主界面
usb_view_main_page = [{'title_re': 'USB Device Viewer', 'control_type': "Window"}]

# Hub list
hub_list = [{'title': 'USB Device Viewer', 'control_type': "Window"},
            {'auto_id': "1000"}]

# Edit：端口详情
port_info_edit = [{'title': 'USB Device Viewer', 'control_type': "Window"},
                  {'class_name': 'Edit'}]


# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageUSBView(BaseOperate):
    def __init__(self):
        super().__init__()

    @property
    @watchdog("获取USB view主界面")
    def element_usb_view_main_page(self):
        return self.find_element(usb_view_main_page)

    @property
    @watchdog("获取登录确认按钮")
    def element_hub_list(self):
        return self.find_element(hub_list)

    @property
    @watchdog("获取Edit内容")
    def element_port_info_edit(self):
        return self.find_element(port_info_edit)

    # High speed USB Composite Device and Quectel USB Composite Device
    @watchdog("获取USB设备")
    def element_hub_usb(self, port_string):
        hub_usb = [
            {'title': 'USB Device Viewer'},
            {'title': port_string}
        ]
        return self.find_element(hub_usb)
