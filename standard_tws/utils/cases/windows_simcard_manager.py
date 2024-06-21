import re
import subprocess
from utils.pages.win11_page_main import Win11PageMain
from utils.pages.page_main import PageMain
from utils.pages.win11_page_mobile_broadband import Win11PageMobileBroadband
from utils.pages.page_mobile_broadband import PageMobileBroadband
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import MBIMError
from utils.functions.images import pic_compare
import time
import requests
import serial.tools.list_ports
import os
import sys


class WindowsSIMCARDManager:

    # SIM LOCK 图片路径
    path_to_sim_lock_pic = 'utils/images/sim_locked_signal'
    path_to_airplane_mode_pic = "utils/images/toolbar_airplane_mode"
    path_to_toolbar_network_pic = "utils/images/toolbar_network"
    mess_apn = 'asd123@!#'

    def __init__(self, phone_number, mbim_driver_name, ipv6_address, at_port=None, dm_port=None, ):
        self.is_win11 = True if sys.getwindowsversion()[2] >= 22000 else False
        if self.is_win11:
            all_logger.info("当前为win11")
            self.page_main = Win11PageMain()
            self.page_mobile_broadband = Win11PageMobileBroadband()
        else:
            all_logger.info("当前为win10")
            self.page_main = PageMain()
            self.page_mobile_broadband = PageMobileBroadband()
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.modify_port()  # 有时候切换拨号模式会导致端口变化
        self.windows_api = WindowsAPI()
        self.mbim_driver_name = mbim_driver_name
        self.ipv6_address = ipv6_address
        self.modify_port()  # 有时候切换拨号模式会导致端口变化
        self.reset_cfun1()
        self.at_handler.check_network()
        self.phone_number = phone_number

    def modify_port(self):
        """
        自动更新各路端口
        :return: None
        """
        for num, name, _ in serial.tools.list_ports.comports():
            if 'AT' in name and getattr(self.at_handler, '_at_port') != num:
                setattr(self.at_handler, '_at_port', num)
            if 'AT' in name and getattr(self.driver, '_at_port') != num:
                setattr(self.driver, '_at_port', num)
            if 'DM' in name and getattr(self.driver, '_dm_port') != num:
                setattr(self.driver, '_dm_port', num)

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        for _ in range(10):
            try:
                self.page_main.click_network_icon()
                self.page_main.click_network_details()
                disconnect_button = self.page_main.element_mbim_disconnect_button
                if disconnect_button.exists():
                    disconnect_button.click()
                self.page_main.click_disable_auto_connect()
                self.windows_api.press_esc()
                return True
            except Exception as e:
                all_logger.info(e)
            finally:
                self.windows_api.press_esc()
        else:
            raise MBIMError("取消自动拨号连接并取消拨号连续三次失败")

    def check_mbim_connect(self, auto_connect=False):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        num = 0
        timeout = 30
        connect_info = None
        already_connect_info = None
        while num <= timeout:
            connect_info = self.page_main.element_mbim_disconnect_button.exists()
            already_connect_info = self.page_main.element_mbim_already_connect_text.exists()
            if auto_connect is False:
                if connect_info and already_connect_info:
                    all_logger.info("MBIM已连接，等待10S")
                    time.sleep(10)
                    return True
            else:
                if already_connect_info:
                    all_logger.info("MBIM已连接，等待10S")
                    time.sleep(10)
                    return True
            num += 1
            time.sleep(1)
        info = '未检测到断开连接按钮，' if not connect_info and not auto_connect else '' + '未检测到已经连接信息' if not already_connect_info else ""
        raise MBIMError(info)

    def click_enable_airplane_mode_and_check(self):
        """
        点击飞行模式后检查是否是飞行模式。
        :return: None
        """
        flag = False

        all_logger.info("点击飞行模式按钮")
        self.page_main.element_airplane_mode_button.click_input()  # 点击飞行模式图标
        time.sleep(3)  # 等待mobile_network_button状态切换

        if self.page_main.element_airplane_mode_button.get_toggle_state() != 1:
            all_logger.error("进入飞行模式后飞行模式按钮的状态异常")
            flag = True
        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("进入飞行模式后手机网络按钮的状态异常")
            flag = True

        all_logger.info("检查网络是否是已关闭")
        already_closed_text = self.page_main.element_mobile_network_already_closed_text
        if not already_closed_text.exists():
            all_logger.error("进入飞行模式后网络状态异常")
            flag = True

        all_logger.info("检查状态栏网络图标是否是飞行模式按钮")
        pic_status = pic_compare(self.path_to_airplane_mode_pic)
        if not pic_status:
            all_logger.error("检查飞行模式图标失败")
            flag = False

        if flag:
            raise MBIMError("模块进入飞行模式检查失败")
        else:
            return True

    def click_disable_airplane_mode_and_check(self):
        """
        点击退出飞行模式后检查是否已经退出飞行模式。
        :return: None
        """
        flag = False

        # 判断飞行模式按钮的初始状态为按下
        if self.page_main.element_airplane_mode_button.get_toggle_state() == 0:
            all_logger.error("飞行模式按钮初始状态异常")
            flag = True

        all_logger.info("点击飞行模式按钮")
        self.page_main.element_airplane_mode_button.click_input()  # 点击飞行模式图标
        time.sleep(3)  # 等待mobile_network_button状态切换

        if self.page_main.element_airplane_mode_button.get_toggle_state() != 0:
            all_logger.error("退出飞行模式后飞行模式按钮的状态异常")
            flag = True
        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("退出飞行模式后手机网络按钮的状态异常")
            flag = True

        pic_status = pic_compare(self.path_to_toolbar_network_pic)
        if not pic_status:
            all_logger.error("检查状态栏网络图标失败")
            flag = False

        if flag:
            raise MBIMError("模块退出飞行模式检查失败")
        else:
            return True

    def check_cfun(self, cfun_check):
        all_logger.info('检查cfun值是否为{}'.format(cfun_check))
        return_value = self.at_handler.send_at('AT+CFUN?')
        cfun_current = ''.join(re.findall(r'\+CFUN:\s(\d)', return_value))
        if cfun_check != cfun_current:
            raise MBIMError('查询CFUN值与期望不一致：\r\n{}\r\n期望值为CFUN{}'.format(return_value, cfun_check))

    def reset_cfun1(self):
        self.at_handler.send_at("AT+CFUN=1", timeout=15)
        cfun = self.at_handler.send_at('AT+CFUN?')
        if '+CFUN: 1' not in cfun:
            self.at_handler.send_at("AT+CFUN=1", timeout=15)
