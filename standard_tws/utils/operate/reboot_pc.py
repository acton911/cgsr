import datetime
import os
import pickle
import re
import time

import serial

from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from tapp_constructor import constructor
from utils.logger.logging_handles import all_logger, at_logger


class Reboot:
    def __init__(self, at_port, dm_port, params_path):
        self.at_port = at_port
        self.dm_port = dm_port
        self.params_path = params_path
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)

    def send_at_pcie(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _at_port:
            for _ in range(1, 5):  # 连续5次发送AT返回空，并且每次检测到口还在，则判定为AT不通
                at_start_timestamp = time.time()
                _at_port.write('{}\r\n'.format(at_command).encode('utf-8'))
                at_logger.info('Send: {}'.format(at_command))
                return_value_cache = ''
                while True:
                    # AT端口值获取
                    time.sleep(0.001)  # 减小CPU开销
                    return_value = _at_port.readline().decode('utf-8')
                    if return_value != '':
                        return_value_cache += '{}'.format(return_value)
                        if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                            return return_value_cache
                        if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                            at_logger.error('{}指令返回ERROR'.format(at_command))
                            return return_value_cache
                    # 超时等判断
                    current_total_time = time.time() - at_start_timestamp
                    out_time = time.time()
                    if current_total_time > timeout:
                        if return_value_cache and at_command in return_value_cache:
                            at_logger.error('{}命令执行超时({}S)'.format(at_command, timeout))
                            while True:
                                time.sleep(0.001)  # 减小CPU开销
                                return_value = _at_port.readline().decode('utf-8')
                                if return_value != '':
                                    return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                                if time.time() - out_time > 3:
                                    return return_value_cache
                        elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                            at_logger.error('{}命令执行返回格式错误，未返回AT指令本身'.format(at_command))
                            return return_value_cache
                        else:
                            at_logger.error('{}命令执行{}S内无任何回显'.format(at_command, timeout))
                            time.sleep(0.5)
                            break
            else:
                at_logger.error('连续10次执行{}命令无任何回显，AT不通'.format(at_command))
                while True:
                    time.sleep(1)

    def check_pcie_status(self, device_number):
        """
        :param device_number: 设备名称，用来判断是否为PCIE设备
        如果是PCIE设备，需要确保重启前PCIE识别正常
        """
        if 'PCIE' in device_number:
            lspci_value = os.popen('lspci').read()
            if self.at_port == '/dev/mhi_DUN':
                data_interface_value = self.send_at_pcie('AT+QCFG="DATA_INTERFACE"', 10)
            else:
                data_interface_value = self.at_handle.send_at('AT+QCFG="DATA_INTERFACE"', 10)
            if 'Qualcomm Device 0306' not in lspci_value or '"data_interface",1,0' not in data_interface_value:
                if self.at_port == '/dev/mhi_DUN':
                    self.send_at_pcie('AT+QCFG="DATA_INTERFACE",1,0', 10)
                    self.send_at_pcie('AT+CFUN=1,1', 15)
                    self.driver_check.check_usb_driver_dis()
                    self.driver_check.check_usb_driver()
                    time.sleep(20)
                else:
                    self.at_handle.send_at('AT+QCFG="DATA_INTERFACE",1,0', 10)
                    self.at_handle.send_at('AT+CFUN=1,1', 15)
                    self.driver_check.check_usb_driver_dis()
                    self.driver_check.check_usb_driver()
                    self.at_handle.readline_keyword('PB DONE', timout=15)
                all_logger.info(os.popen('lspci').read())
            else:
                all_logger.info('当前PCIE设备识别正常，且指令设置正确，无需变动')

    def restart_computer(self, test_times=1):
        """
        进行主机重启操作
        @param test_times: 记录当前重启的次数
        @return:
        """
        # 第一步，解析下发参数，获取重启方法所需参数值
        try:
            with open(self.params_path, 'rb') as p:
                # original_setting
                original_setting = pickle.load(p).test_setting
                if not isinstance(original_setting, dict):
                    original_setting = eval(original_setting)
                all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
                # case_setting
                case_setting = pickle.load(p)
                all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
                # script_context
                script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
                all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
        except SyntaxError:
            raise Exception("\n系统参数解析异常：\n原始路径: \n {}".format(repr(self.params_path)))

        # 第二步，实例化TestOperation类，之后赋值restart方法需要的参数，方便之后调用
        con = constructor.TestOperation()
        # 赋值restart方法所需参数
        constructor.current_test_case = {"id_case": case_setting['id_case']}
        constructor.main_task_id = original_setting['task_id']

        # 第三步，进行重启
        # Windows下重启前关闭QualcommPackageManager工具，该工具会阻止电脑重启
        if os.name == 'nt':
            all_logger.info(os.popen('taskkill /f /t /im QualcommPackageManager*').read())
            all_logger.info(os.popen('taskkill /f /t /im QuectelLogCollectTool*').read())
        else:   # ubuntu系统下，检查当前是否是PCIE设备，是的话，需要保证重启前模块是PCIE状态
            self.check_pcie_status(original_setting['res'][0]['device_number'])
        all_logger.info('开始重启整机')
        con.restart(testtimes=test_times)    # 重启

    def get_restart_flag(self):
        """
        获取restarted_flag参数，判断当前是重启前还是重启后
        @return:
        """
        try:
            with open(self.params_path, 'rb') as p:
                # original_setting
                original_setting = pickle.load(p).test_setting
                if not isinstance(original_setting, dict):
                    original_setting = eval(original_setting)
                all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
                # case_setting
                case_setting = pickle.load(p)
                all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
                # script_context
                script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
                all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
        except SyntaxError:
            raise Exception("\n系统参数解析异常：\n原始路径: \n {}".format(repr(self.params_path)))
        restarted_flag = False
        try:
            if case_setting['restarted']:
                restarted_flag = True
        except Exception:   # noqa
            pass
        return restarted_flag
