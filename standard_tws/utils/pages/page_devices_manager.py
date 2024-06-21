import subprocess
from ..operate.base import BaseOperate
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial

# 设备管理器按钮：扫描检测硬件改动
scan_devices_icon = [{'title': '设备管理器'},
                     {'title': '扫描检测硬件改动'}]
# 关闭按钮
devices_close_button = [{'title': '设备管理器'},
                        {'title': "关闭", 'control_type': "Button"}]
# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageDevicesManager(BaseOperate):
    def __init__(self):
        super().__init__()

    @watchdog('打开设备管理器')
    def open_devices_manager(self):
        """
        打开设备管理器
        """
        all_logger.info('打开设备管理器')
        cmd = 'devmgmt.msc'

        subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

    @watchdog("获取scan_devices_icon")
    def element_scan_devices_icon(self):
        return self.find_element(scan_devices_icon)

    @watchdog("获取devices_close_button")
    def element_devices_close_button(self):
        return self.find_element(devices_close_button)
