import re
import subprocess
from utils.pages.win11_page_main import Win11PageMain
from utils.pages.page_main import PageMain
from utils.pages.win11_page_mobile_broadband import Win11PageMobileBroadband
from utils.pages.page_mobile_broadband import PageMobileBroadband
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import MBIMError
from utils.functions.images import pic_compare
import time
import serial.tools.list_ports
import os
import sys


class WindowsLaptopSimcardManager:
    # SIM LOCK 图片路径
    path_to_sim_lock_pic = 'utils/images/sim_locked_signal'
    path_to_airplane_mode_pic = "utils/images/toolbar_airplane_mode"
    path_to_toolbar_network_pic = "utils/images/toolbar_network"
    mess_apn = 'asd123@!#'

    def __init__(self, mbim_driver_name, ipv6_address, phone_number, at_port=None, dm_port=None, ):
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

    def check_cfun(self, cfun_check='1'):
        all_logger.info('检查cfun值是否为{}'.format(cfun_check))
        return_value = self.at_handler.send_at('AT+CFUN?')
        cfun_current = ''.join(re.findall(r'\+CFUN:\s(\d)', return_value))
        if cfun_check != cfun_current:
            raise MBIMError('查询CFUN值与期望不一致：\r\n{}\r\n期望值为CFUN{}'.format(return_value, cfun_check))

    def reset_cfun1(self):
        cfun = self.at_handler.send_at('AT+CFUN?')
        if '+CFUN: 1' not in cfun:
            self.at_handler.send_at("AT+CFUN=1", timeout=15)

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

    def disable_auto_connect_find_connect_button(self):
        """
        windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            status = self.page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
            time.sleep(3)
        else:
            raise MBIMError("未发现连接按钮")

    def check_network_type_and_icon(self, expect_network=None):
        """
        检查拨号界面的网络类型是否跟AT+COPS?查询一致。
        :param expect_network: 期望的网络类型，默认可以没有，取值 SA/NSA/LTE/WCDMA
        :return: None
        """
        all_logger.info("对比连接信息")
        for i in range(10):
            time.sleep(3)
            _network = {  # 2：WCDMA显示HSPA+
                "2": "HSPA",
                "7": "LTE",
                "11": "5G",
                "13": "5G",
            }
            operator = self.at_handler.get_operator()
            current_network = self.at_handler.check_network()  # COPS Value
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            connect_info = self.page_main.element_connect_info
            data = repr(connect_info.wrapper_object()) if connect_info.exists() else ''

            # 检查运行商
            if operator not in data:
                self.windows_api.press_esc()
                all_logger.error("运营商名称不一致，{}—{}".format(operator, data))
                continue

            # 检查当前网络
            if _network[current_network] not in data:
                self.windows_api.press_esc()
                all_logger.error("网络名称不一致，{}—{}".format(_network[current_network], data))
                continue

            # 如果指定检查的网络类型
            if expect_network:
                expect_network_mapping = {
                    "SA": "5G",
                    "NSA": "5G",
                    "LTE": "LTE",
                    "WCDMA": "HSPA"
                }
                cops_mapping = {
                    "NSA": "13",
                    "SA": "11",
                    "LTE": "7",
                    "WCDMA": "2"
                }
                if expect_network_mapping[expect_network] not in data:
                    all_logger.error("期望网络为{}，当前字符串{}".format(expect_network, data))
                    self.windows_api.press_esc()
                    continue
                if current_network != cops_mapping[expect_network]:
                    all_logger.error("期望AT+COPS?值为{}，当前值为{}".format(cops_mapping[expect_network], current_network))
                    self.windows_api.press_esc()
                    continue
            self.windows_api.press_esc()
            return True
        else:
            self.windows_api.press_esc()
            raise MBIMError("网络运营商对比异常")

    def get_gmi(self):
        gmi = self.at_handler.send_at('AT+GMI')
        gmi_regex = ''.join(re.findall(r'GMI\W+(\w+)', gmi))
        if gmi_regex:
            return gmi_regex
        else:
            return False

    def mbim_connect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        for i in range(10):
            data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
            all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

            profile_name = ''.join(re.findall(r'---\s+(.*)', data2))
            time.sleep(5)
            os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
            all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
            time.sleep(5)

            data3 = os.popen(
                'netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name)).read()
            all_logger.info(
                'netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name))
            time.sleep(5)
            if '失败' not in data3:
                break
        else:
            raise MBIMError("连接拨号失败！\r\n{}".format(data3))
        time.sleep(10)

    def mbim_disconnect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        time.sleep(5)
        os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
        time.sleep(10)

    def check_mbim_connect_disconnect(self, connect=True):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

        profile_name = ''.join(re.findall(r'---\s+(.*)', data2))

        # netsh mbn show profilestate interface="手机网络" name="EFAE6521-9049-451C-84A0-72CDE3D6372D"
        data3 = os.popen(
            'netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name)).read()
        all_logger.info('netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name))
        if not connect and '已连接' in data3:
            raise MBIMError("异常！当前没有断开连接！\r\n{}".format(data3))
        elif connect and '断开连接' in data3:
            raise MBIMError("异常！当前没有连接！\r\n{}".format(data3))

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

    def check_mbim_disconnect(self):
        """
        检查mbim是否是断开连接状态
        :return: None
        """
        num = 0
        timeout = 30
        connect_info = None
        already_connect_info = None
        while num <= timeout:
            connect_info = self.page_main.element_mbim_connect_button.exists()
            already_connect_info = self.page_main.element_mbim_already_disconnect_text.exists()
            if connect_info and already_connect_info:
                return True
            num += 1
            time.sleep(1)
        info = '未检测到连接按钮，' if not connect_info else '' + '未检测到已经断开连接信息' if not already_connect_info else ""
        raise MBIMError(info)

    def check_sim_pin_locked_win11(self):
        """
        检查SIM PIN是否是Locked状态
        :return: None
        """
        sim_pin_status = self.page_main.element_sim_pin_locked_text.exists()
        if not sim_pin_status:
            raise MBIMError("未找到SIM PIN 已锁定Text")
        pic_status = pic_compare(self.path_to_sim_lock_pic)
        if not pic_status:
            raise MBIMError('SIM 卡锁定图标对比失败')
        # connect_info = repr(self.page_main.element_connect_info.wrapper_object())
        # if '手机网络' not in connect_info:
        #     raise MBIMError("未检测到手机网络描述")

    def check_sim_pin_locked(self):
        """
        检查SIM PIN是否是Locked状态
        :return: None
        """
        sim_pin_status = self.page_main.element_sim_pin_locked_text.exists()
        if not sim_pin_status:
            raise MBIMError("未找到SIM PIN 已锁定Text")
        pic_status = pic_compare(self.path_to_sim_lock_pic)
        if not pic_status:
            raise MBIMError('SIM 卡锁定图标对比失败')
        connect_info = repr(self.page_main.element_connect_info.wrapper_object())
        if '手机网络' not in connect_info:
            raise MBIMError("未检测到手机网络描述")

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

    def click_disable_mobile_network_and_check(self):
        """
        点击禁用手机网络图标然后检查。
        :return: None
        """
        flag = False

        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("手机网络按钮初始状态异常")
            flag = True

        all_logger.info("点击按钮关闭手机网络")
        self.page_main.element_mobile_network_button.click_input()
        time.sleep(3)

        if not self.page_main.element_mobile_network_already_closed_text.exists():
            all_logger.error("关闭手机网络后状态异常")
            flag = True

        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("点击禁用手机网络后手机网络图标检查异常")
            flag = True

        if flag:
            return MBIMError("点击禁用手机网络图标后状态检查失败")
        else:
            return True

    def click_enable_mobile_network_and_check(self):
        """
        点击启用手机网络图标然后检查。
        :return: None
        """
        flag = False

        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("手机网络按钮初始状态异常")
            flag = True

        # mbim_logger.error("点击按钮开启手机网络")
        self.page_main.element_mobile_network_button.click_input()
        time.sleep(3)

        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("开启手机网络后按钮状态异常")
            flag = True

        if flag:
            return MBIMError("点击启用手机网络图标后状态检查失败")
        else:
            return True

    def disable_airplane_mode(self):
        """
        禁止飞行模式，用于case前置条件。
        :return: None
        """
        self.page_main.click_network_icon()
        if self.page_main.element_airplane_mode_button.get_toggle_state() != 0:
            self.page_main.element_airplane_mode_button.click()
            time.sleep(5)
        self.windows_api.press_esc()

    def enable_mobile_network(self):
        """
        启用手机网络，用于case前置条件
        :return: None
        """
        self.page_main.click_network_icon()
        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            self.page_main.element_mobile_network_button.click()
            time.sleep(5)
        self.windows_api.press_esc()

    def check_dial_init_time(self, timeout=15):
        """
        检查驱动加载时间，如果超时，则触发异常
        :param timeout: 超时时间
        :return: None
        """
        time_used = self.windows_api.check_dial_init()
        if time_used > 40:
            raise MBIMError("开机后MBIM功能的加载时间为{}S，大于{}S".format(round(time_used, 2), timeout))

    @staticmethod
    def enable_disable_mbim_driver(flag, mbim_driver_name):
        """
        禁用或者启用驱动。
        :param mbim_driver_name: mbim驱动的名称
        :param flag: True:禁用驱动，False：启用驱动。
        :return: None
        """
        mbim_driver_name = mbim_driver_name.replace(" ", "' '")
        all_logger.info('{}驱动{}'.format("禁用" if flag else "启用", mbim_driver_name))
        cmd = 'powershell "Get-PnpDevice -FriendlyName "{}" -status "OK" | disable-pnpdevice -Confirm:$True"'.format(
            mbim_driver_name) if flag else \
            'powershell "Get-PnpDevice -FriendlyName "{}" -status "Error" | enable-pnpdevice -Confirm:$Ture"'.format(
                mbim_driver_name)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

        proc.stdin.write(b"A\n")
        proc.stdin.flush()
        proc.stdin.close()

        while proc.returncode is None:
            proc.poll()

        all_logger.info(proc.stdout.read().decode('GBK', "ignore"))

        time.sleep(3)

    def cfun0(self):
        """
        发送CFUN0
        :return: None
        """
        cfun0_data = self.at_handler.send_at("AT+CFUN=0", timeout=15)
        if 'OK' not in cfun0_data:
            raise MBIMError("CFUN0发送后未返回OK")
        time.sleep(10)

    def cfun4(self):
        """
        发送CFUN4
        :return: None
        """
        cfun4_data = self.at_handler.send_at("AT+CFUN=4", timeout=15)
        if 'OK' not in cfun4_data:
            raise MBIMError("CFUN4发送后未返回OK")
        time.sleep(10)

    def cfun1(self):
        """
        发送CFUN1，主要用作Case的teardown。
        :return: None
        """
        all_logger.info("发送CFUN1恢复初始状态")  # 恢复状态
        self.at_handler.send_at("AT+CFUN=1", timeout=15)
        self.at_handler.check_network()

    def cfun0_1(self):
        """
        发送CFUN0,CFUN=1
        :return: None
        """
        cfun0_data = self.at_handler.send_at("AT+CFUN=0", timeout=15)
        if 'OK' not in cfun0_data:
            raise MBIMError("CFUN0发送后未返回OK")
        time.sleep(10)
        cfun1_data = self.at_handler.send_at("AT+CFUN=1", timeout=15)
        if 'OK' not in cfun1_data:
            raise MBIMError("CFUN1发送后未返回OK")
        time.sleep(10)

    def cfun0_check(self):
        """
        发送CFUN0后检查
        :return: None
        """
        flag = False

        all_logger.info("检查信号图标")
        self.page_main.click_network_icon()
        self.page_main.element_network_details.click_input()
        pic_status = pic_compare(self.path_to_sim_lock_pic)
        if not pic_status:
            all_logger.error("检查SIM锁定图标图标失败")
            flag = True

        all_logger.info("检查网络是否是已关闭")
        already_closed_text = self.page_main.element_mobile_network_already_closed_text
        if not already_closed_text.exists():
            all_logger.error("发送CFUN0后网络状态异常")
            flag = True

        all_logger.info("检查网络是否有mbim连接按钮")
        already_closed_text = self.page_main.element_mbim_connect_button
        if already_closed_text.exists():
            all_logger.error("发送CFUN0后网络状态异常")
            flag = True

        connect_info = repr(self.page_main.element_connect_info.wrapper_object())
        if '手机网络' not in connect_info:
            all_logger.error("未检测到文字：手机网络")
            flag = True

        if flag:
            raise MBIMError("发送CFUN0后检查失败")
        else:
            return True

    def cfun4_check(self):
        """
        发送CFUN4后检查
        :return: None
        """
        flag = False

        all_logger.info("检查信号图标")
        self.page_main.click_network_icon()
        self.page_main.element_network_details.click_input()
        pic_status = pic_compare(self.path_to_sim_lock_pic)
        if not pic_status:
            all_logger.error("检查SIM锁定图标图标失败")
            flag = True

        all_logger.info("检查网络是否是已关闭")
        already_closed_text = self.page_main.element_mobile_network_already_closed_text
        if not already_closed_text.exists():
            all_logger.error("发送CFUN4后网络状态异常")
            flag = True

        all_logger.info("检查网络是否有mbim连接按钮")
        already_closed_text = self.page_main.element_mbim_connect_button
        if already_closed_text.exists():
            all_logger.error("发送CFUN4后网络状态异常")
            flag = True

        operator_mapping = {
            "CMCC": "CMCC",
            "中国联通": "UNICOM",
            "中国电信": "中国电信"
        }  # 设置AT+CFUN=4的时候MBIM拨号面板显示的字符串
        operator = self.at_handler.get_operator()
        connect_info = repr(self.page_main.element_connect_info.wrapper_object())
        if operator_mapping[operator] not in connect_info:
            all_logger.error("未检测到文字：{}".format(operator))
            flag = True

        if flag:
            raise MBIMError("发送CFUN4后检查失败")
        else:
            return True

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
