import datetime
import os
import re
import sys
import time
import glob
import serial
import shutil
import subprocess
import serial.tools.list_ports
from utils.exception.exceptions import WindowsLaptopUpgradeonoffError
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.pages.page_qpst import Qpst


class LaptopUpgradeOnOff:
    def __init__(self, at_port, dm_port, sahara_port, firmware_path, ati, csub,
                 prev_firmware_path, prev_ati, prev_csub):
        self.at_port = at_port
        self.dm_port = dm_port
        self.sahara_port = sahara_port
        self.firmware_path = firmware_path
        self.at_handler = ATHandle(self.at_port)
        self.driver_check = DriverChecker(self.at_port, self.dm_port)
        self.ati = ati
        self.csub = csub
        self.prev_firmware_path = prev_firmware_path
        self.prev_ati = prev_ati
        self.prev_csub = prev_csub
        time.sleep(1)

    def check_efuse_status(self):
        status_value = self.at_handler.send_at('AT+QTEST="efuse/pcie"')
        if '1' not in status_value:
            raise WindowsLaptopUpgradeonoffError('当前模块非efuse模块,请烧录')
        all_logger.info(f'当前模块为efuse模块,查询值为{status_value}')

    def check_hwid_value(self):
        """
        检查HWID值
        """
        value = self.at_handler.send_at('AT+QPCIE="ID"')
        if '0x1004,0x1eac,0x3003,0x1eac' not in value:
            all_logger.info('HWID检查异常')
            raise WindowsLaptopUpgradeonoffError('HWID检查异常')
        else:
            all_logger.info('HWID检查正常')

    @staticmethod
    def adb_check_hwid():
        """
        adb指令检查hwid值
        """
        s = subprocess.Popen("powershell adb shell", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        s.stdin.write(b'devmem 0x786070\r\n')
        s.stdin.write(b'devmem 0x7801D8\r\n')
        s.stdin.write(b'devmem 0x7801DC\r\n')
        s.stdin.write(b'devmem 0x7801D0\r\n')
        s.stdin.write(b'quit()\r\n')
        s.stdin.close()
        st = time.time()
        out_cache = ''
        check_value_list = ['0x0000002B', '0x1EAC1004', '0x1EAC0000', '0x18018000']
        while True:
            out = s.stdout.readline()
            if out != b'':
                out = f'"{datetime.datetime.now()}":{out.decode("utf-8")}'
                out_cache += out
            if time.time() - st > 5:
                s.terminate()
                s.wait()
                break
        for i in check_value_list:
            if i not in out_cache:
                all_logger.info(f'发送adb指令检查hwid返回值异常:具体返回值为{out_cache}')
                raise WindowsLaptopUpgradeonoffError(f'发送adb指令检查hwid返回值异常:具体返回值为{out_cache}')
        else:
            all_logger.info('adb检查hwid正常')

    def cfun1_1(self):
        """
        检测cfun11重启功能
        :return:
        """
        self.at_handler.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handler.check_urc()
        time.sleep(30)

    @staticmethod
    def check_adb_devices_connect():
        """
        检查adb devices是否有设备连接
        :return: True:adb devices已经发现设备
        """
        adb_check_start_time = time.time()
        while True:
            # 发送adb devices
            subprocess.run('adb kill-server')
            adb_value = repr(os.popen('adb devices').read())
            all_logger.info(adb_value)
            devices_online = ''.join(re.findall(r'\\n(.*)\\tdevice', adb_value))
            devices_offline = ''.join(re.findall(r'\\n(.*)\\toffline', adb_value))
            if devices_online != '' or devices_offline != '':  # 如果检测到设备
                all_logger.info('已检测到adb设备')  # 写入log
                return True
            elif time.time() - adb_check_start_time > 100:  # 如果超时
                raise WindowsLaptopUpgradeonoffError("adb超时未加载")
            else:  # 既没有检测到设备，也没有超时，等1S
                time.sleep(1)

    def check_dump_log(self):
        """
        检查是否已存在dumplog，若已存在需先删除
        :return:
        """
        # 首先看下qpst文件夹下有无dumplog，有的话删除
        path = r'C:\ProgramData\Qualcomm\QPST\Sahara'
        if os.path.exists(path):
            pass
        else:
            os.mkdir(r'C:\ProgramData\Qualcomm\QPST\Sahara')
        for f in os.listdir(path):
            if f'Port_{self.dm_port}' in f:
                dump_path = os.path.join(path, f'Port_{self.dm_port}')
                shutil.rmtree(dump_path)
                all_logger.info('已删除之前存在dumplog')

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
            return glob.glob('/dev/ttyUSB*')

    def set_modem_value(self, modem, ap):
        """
        设置modemrstlevel和aprstlevel值并输入AT+QTEST="DUMP",1指令
        :param modem: modem设置值
        :param ap: ap设置值
        :return:
        """
        self.at_handler.send_at(f'AT+QCFG="ModemRstLevel",{modem}', timeout=10)
        self.at_handler.send_at(f'AT+QCFG="ApRstLevel",{ap}', timeout=10)
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _at_port:
            _at_port.write(b'AT+QTEST="DUMP",1\r\n')
            all_logger.info('发送AT+QTEST="DUMP",1指令')
        if modem == 1 and ap == 1:  # 模块仅Modem重启，USB口不会消失，USB口有RDY上报，此后模块正常注网
            self.at_handler.check_urc()
            time.sleep(5)
            self.at_handler.send_at('AT+CFUN?', 10)
            self.at_handler.check_network()
        if modem == 0 and ap == 1:  # 模块只是会重启
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handler.check_urc()
            time.sleep(5)
            self.at_handler.send_at('AT+CFUN?', 10)
            self.at_handler.check_network()
        if modem == 0 and ap == 0:  # 模块只剩一个DM口
            for i in range(10):
                if self.dm_port not in self.get_port_list() and self.at_port not in self.get_port_list() \
                        and self.sahara_port in self.get_port_list():
                    all_logger.info('模块已进入dump')
                    return True
                all_logger.info(f'当前端口情况为{self.get_port_list()}')
                time.sleep(5)
            else:
                raise WindowsLaptopUpgradeonoffError('模块Dump后端口异常')

    def qpst(self):
        """
        打开qpst抓dumplog
        :return:
        """
        exc_type = None
        exc_value = None
        q = None
        try:
            q = Qpst()
            q.click_add_port()
            q.input_port(self.sahara_port)
            time.sleep(10)  # 等一会再去检查是否有dumplog
            path = r'C:\ProgramData\Qualcomm\QPST\Sahara'
            for i in range(10):
                for f in os.listdir(path):
                    if f'Port_{self.sahara_port}' not in f:
                        time.sleep(5)
                        continue
                    else:
                        all_logger.info('已获取到dump_log存在')
                        return True
            else:
                raise WindowsLaptopUpgradeonoffError('模块进入dump后未获取dumplog')
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            q.close_qpst()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def back_dump_value(self):
        """
        恢复dump指令到默认值11
        :return:
        """
        self.at_handler.send_at('AT+QCFG="ModemRstLevel",1', 10)
        self.at_handler.send_at('AT+QCFG="ApRstLevel",1', 10)
