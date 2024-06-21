import os
from ..logger.logging_handles import all_logger
import serial.tools.list_ports
import glob
import time


class DriverChecker:
    def __init__(self, at_port, dm_port):
        self._at_port = at_port
        self._dm_port = dm_port

    def get_port_list(self):
        """
        获取当前电脑设备管理器中所有的COM口的列表
        :return: COM口列表，例如['COM3', 'COM4']
        """
        if os.name == 'nt':
            try:
                all_logger.debug('get_port_list')
                port_name_list = []
                ports = serial.tools.list_ports.comports()
                for port, _, _ in sorted(ports):
                    port_name_list.append(port)
                all_logger.debug(port_name_list)
                return port_name_list
            except TypeError:  # Linux偶现
                return self.get_port_list()
        else:
            ports = glob.glob('/dev/ttyUSB*')
            all_logger.info(ports)
            return ports

    def check_usb_driver(self):
        """
        检测驱动是否出现
        :return: True:检测到驱动；False：没有检测到驱动
        """
        all_logger.info('检测驱动加载')
        check_usb_driver_start_timestamp = time.time()
        timeout = 300
        while True:
            port_list = self.get_port_list()
            check_usb_driver_total_time = time.time() - check_usb_driver_start_timestamp
            if check_usb_driver_total_time < timeout:  # timeout S内
                if self._at_port in port_list and self._dm_port in port_list:  # 正常情况
                    all_logger.info('USB驱动{}加载成功!'.format(self._at_port))
                    time.sleep(0.1)  # 延迟0.1秒避免端口打开异常
                    return True
                elif self._dm_port in port_list and self._at_port not in port_list:  # 发现仅有DM口并且没有AT口
                    time.sleep(3)  # 等待3S口还是只有AT口没有DM口判断为DUMP，RG502QEAAAR01A01M4G出现两个口相差1秒
                    port_list = self.get_port_list()
                    if self._dm_port in port_list and self._at_port not in port_list:
                        all_logger.error('模块DUMP')
                        self.check_usb_driver()
                else:
                    time.sleep(0.1)  # 降低检测频率，减少CPU占用
            else:  # timeout秒驱动未加载
                all_logger.error("模块开机{}秒内USB驱动{}加载失败".format(timeout, self._at_port))
                all_logger.info(f'当前驱动列表为:{self.get_port_list()}，检测加载的端口为{self._at_port},{self._dm_port}')
                return False

    def check_usb_driver_dis(self):
        """
        检测某个COM口是否消失
        :return: None
        """
        all_logger.info('检测驱动消失')
        check_usb_driver_dis_start_timestamp = time.time()
        timeout = 300
        while True:
            port_list = self.get_port_list()
            check_usb_driver_dis_total_time = time.time() - check_usb_driver_dis_start_timestamp
            if check_usb_driver_dis_total_time < timeout:  # 300S内
                if self._at_port not in port_list and self._dm_port not in port_list:
                    all_logger.info('USB驱动{}掉口成功!'.format(self._at_port))
                    return True
                else:
                    time.sleep(0.1)
            else:
                all_logger.info('USB驱动{}掉口失败!'.format(self._at_port))
                all_logger.info(f'当前驱动列表为:{self.get_port_list()}，检测掉口的端口为{self._at_port},{self._dm_port}')
                return False
