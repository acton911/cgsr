import re
import shutil
import sys
import time
import serial
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
import os
import traceback
import subprocess
from utils.functions.gpio import GPIO
import getpass


class TeardownManager:
    def __init__(self, **kwargs):
        # 参数处理
        self.version_upgrade = 1  # factory版本包，会被__update_args方法更新为系统下发的参数
        self.need_upgrade = True   # 默认需要升级，会被__update_args方法更新为TWS系统下发的参数
        self.__update_args(kwargs)  # 更新传参
        self.is_audio = True if 'AUDIO' in self.args.device_number.upper() else False  # noqa 判断是否是audio设备，如果设备名称包含audio则判定为audio设备
        # 实例化
        self.driver_handle = DriverChecker(self.at_port, self.dm_port)
        self.at_handle = ATHandle(self.at_port)
        self.gpio = GPIO()

    def __getattr__(self, item):
        return self.__dict__.get(item)

    def __update_args(self, kwargs):
        for k, v in kwargs.items():
            all_logger.info(f"{k}: {v}")
            if v == '':
                raise FatalError(f"\n系统参数 '{k}'\nrepr(k): {repr(k)}，值异常，请检查log ")
            setattr(self, k, v)

    @staticmethod
    def delete_files():
        all_logger.info("delete_files")
        script_temp_path = fr'C:\Users\{getpass.getuser()}\AppData\Local\Temp\script_temp' if os.name == 'nt' else '/tmp/script_temp'
        if os.path.exists(script_temp_path):
            all_logger.info(f"delete {script_temp_path}")
            shutil.rmtree(os.path.join(script_temp_path))
        # 因为目前exe或ubuntu文件会被占用，只会删除一个文件
        search_path = os.path.dirname(os.getcwd())  # 当前脚本运行目录的上一级目录
        all_logger.info(f"删除 {search_path} 文件夹所有.exe, .ubuntu, app.zip文件")
        for path, _, files in os.walk(search_path):
            for file in files:
                if file.endswith(('.ubuntu', '.exe', 'app.zip')):
                    file_path = os.path.join(path, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        all_logger.info(e)

    @staticmethod
    def delete_firmware_dir():
        """
        删除像Pretest、DFOTA的firmware文件夹。
        :return: None
        """
        search_path = os.path.dirname(os.getcwd())  # 当前脚本运行目录的上一级目录
        all_logger.info(f"cwd: {search_path}")
        for path, _, _ in os.walk(search_path):
            if path.endswith('firmware'):
                all_logger.info(f"删除firmware文件夹：{path}")
                try:
                    if os.name == 'nt':  # Windows用rd命令删除
                        s = subprocess.getoutput(f"rd /s /q {path}")
                        all_logger.info(f"s.output: {s}")
                    else:  # Linux用rm -rf删除
                        s = subprocess.getoutput(f'sudo rm -rf "{path}"')
                        all_logger.info(f"s.output: {s}")
                    break
                except Exception as e:
                    all_logger.error(e)
                    all_logger.error(traceback.format_exc())

    def reset_usbnet_0(self):
        # 非USBNET0，退出
        all_logger.info(f'当前端口列表为{self.driver_handle.get_port_list()}')
        usbnet = self.at_handle.send_at('AT+QCFG="USBNET"', timeout=3)
        if ',1' in usbnet:
            self.at_handle.send_at('AT+QCFG="USBNET",0', timeout=3)
            # 切换后重启
            self.at_handle.send_at("AT+CFUN=1,1", timeout=3)
            self.driver_handle.check_usb_driver_dis()
            self.driver_handle.check_usb_driver()
            all_logger.info("wait 60 seconds")
            time.sleep(60)

    def get_mbn_status(self):
        for i in range(20):
            self.at_handle.send_at('at+cgdcont?', timeout=15)
            mbn_status = self.at_handle.send_at('at+qmbncfg="list"', timeout=15)
            if 'OK' in mbn_status and ",0,1,1" in mbn_status:
                break
            time.sleep(3)
        else:
            all_logger.error('case执行结束后查询MBN列表异常')

    def reset_switch_4(self):
        if os.name == 'posix':
            all_logger.info("开始恢复switch_4设置")
            self.gpio.set_rtl_8125_low_level()
        else:
            all_logger.info('Windows暂不考虑该引脚')

    def sim_switch(self, port):
        """
        使用切卡器进行切卡操作
        :param port:
        :return:
        """
        all_logger.info(f'打开切卡器端口{port}进行SIMSWITCH操作')
        with serial.Serial(port, baudrate=115200, timeout=0) as _switch_port:
            _switch_port.setDTR(False)
            time.sleep(1)
            start_time = time.time()
            _switch_port.write("SIMSWITCH,1\r\n".encode('utf-8'))
            while time.time() - start_time < 3:
                value = _switch_port.readline().decode('utf-8')
                if value:
                    all_logger.info(value)
                if 'OK' in value:
                    break
        self.at_handle.send_at('AT+CFUN=0', 15)
        time.sleep(1)
        self.at_handle.send_at('AT+CFUN=1', 15)

    def change_slot(self):
        """
        测试后恢复切卡器卡槽至卡槽一
        :return:
        """
        switch_info = self.args.switcher
        all_logger.info(switch_info)
        switch_1_port = ''
        switch_2_port = ''
        if switch_info:     # 如果没有安装切卡器，就不做切卡器相关操作
            all_logger.info('恢复切卡器至卡槽一')
            if 'COM' in switch_info[0]:
                switch_1_port = ''.join(re.findall(r'COM\d+', switch_info[0]))
                switch_2_port = ''.join(re.findall(r'COM\d+', switch_info[1])) if len(switch_info) == 2 else None
            elif '/dev/tty' in switch_info[0]:
                switch_1_port = '/dev/ttyUSBSWITCHER'
            self.sim_switch(switch_1_port)
            if switch_2_port:
                self.sim_switch(switch_2_port)
            time.sleep(10)
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:       # Win11,默认为笔电项目，需要设置上报口为Modem  # pylint: disable=E1101
            self.at_handle.send_at('AT+QURCCFG="urcport","usbmodem"', 3)
        try:
            if '+QUIMSLOT: 2' in self.at_handle.send_at('AT+QUIMSLOT?', timeout=30):  # 如果当前是卡槽二，再执行切换卡槽方法
                self.at_handle.send_at('AT+QUIMSLOT=1', 15)
                time.sleep(5)
                self.at_handle.send_at('AT+CFUN=0', 15)
                time.sleep(3)
                self.at_handle.readline_keyword('PB DONE', timout=60, at_flag=True, at_cmd='AT+CFUN=1')
                if os.name == 'nt' and sys.getwindowsversion().build > 20000:       # Win11,默认为笔电项目，需要设置上报口为Modem  # pylint: disable=E1101
                    self.at_handle.send_at('AT+QURCCFG="URCPORT","USBAT"', 3)
                return
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:       # Win11,默认为笔电项目，需要恢复上报口为AT  # pylint: disable=E1101
                self.at_handle.send_at('AT+QURCCFG="URCPORT","USBAT"', 3)
