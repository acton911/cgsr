import re
import subprocess
from utils.operate.reboot_pc import Reboot
from utils.pages.page_main import PageMain
from utils.pages.page_mobile_broadband import PageMobileBroadband
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import MBIMError
from utils.functions.images import pic_compare
import time
import requests
import serial.tools.list_ports


class WindowsNDISManager:
    # SIM LOCK 图片路径
    path_to_sim_lock_pic = 'utils/images/sim_locked_signal'
    path_to_airplane_mode_pic = "utils/images/toolbar_airplane_mode"
    path_to_toolbar_network_pic = "utils/images/toolbar_network"
    mess_apn = 'asd123@!#'

    def __init__(self, ndis_driver_name, ipv6_address, phone_number, params_path, at_port=None, dm_port=None):
        self.page_main = PageMain()
        self.page_mobile_broadband = PageMobileBroadband()
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.modify_port()  # 有时候切换拨号模式会导致端口变化
        self.windows_api = WindowsAPI()
        self.ndis_driver_name = ndis_driver_name
        self.ipv6_address = ipv6_address
        self.at_handler.switch_to_ndis(ndis_driver_name)
        self.modify_port()  # 有时候切换拨号模式会导致端口变化
        self.reset_cfun1()
        self.at_handler.check_network()
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.phone_number = phone_number
        self.reboot = Reboot(at_port, dm_port, params_path)

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
            # _network = {  # 2：WCDMA显示HSPA+
            #     "2": "HSPA",
            #     "7": "LTE",
            #     "11": "5G",
            #     "13": "5G",
            # }
            operator = self.at_handler.get_operator()
            # current_network = self.at_handler.check_network()  # COPS Value
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            connect_info = self.page_main.element_connect_info
            data = repr(connect_info.wrapper_object()) if connect_info.exists() else ''

            # 检查运行商
            if operator not in data:
                self.windows_api.press_esc()
                all_logger.error("运营商名称不一致，{}—{}".format(operator, data))
                continue

            # # 检查当前网络
            # if _network[current_network] not in data:
            #     self.windows_api.press_esc()
            #     all_logger.error("网络名称不一致，{}—{}".format(_network[current_network], data))
            #     continue

            # # 如果指定检查的网络类型
            # if expect_network:
            #     expect_network_mapping = {
            #         "SA": "5G",
            #         "NSA": "5G",
            #         "LTE": "LTE",
            #         "WCDMA": "HSPA"
            #     }
            #     cops_mapping = {
            #         "NSA": "13",
            #         "SA": "11",
            #         "LTE": "7",
            #         "WCDMA": "2"
            #     }
            #     if expect_network_mapping[expect_network] not in data:
            #         all_logger.error("期望网络为{}，当前字符串{}".format(expect_network, data))
            #         self.windows_api.press_esc()
            #         continue
            #     if current_network != cops_mapping[expect_network]:
            #         all_logger.error("期望AT+COPS?值为{}，当前值为{}".format(cops_mapping[expect_network], current_network))
            #         self.windows_api.press_esc()
            #         continue
            self.windows_api.press_esc()
            return True
        else:
            self.windows_api.press_esc()
            raise MBIMError("网络运营商对比异常")

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
                    return True
            else:
                if already_connect_info:
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
        if time_used > 30:
            raise MBIMError("开机后NDIS功能的加载时间为{}S，大于{}S".format(round(time_used, 2), timeout))

    @staticmethod
    def enable_disable_mbim_driver(flag, mbim_driver_name):
        """
        禁用或者启用驱动。
        :param mbim_driver_name: mbim驱动的名称
        :param flag: True:禁用驱动，False：启用驱动。
        :return: None
        """
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
            time.sleep(0.001)
            proc.poll()

        all_logger.info(proc.stdout.read().decode('GBK', "ignore"))

        time.sleep(10)

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

    def connect_and_disconnect_10_times(self):
        """
        测试10次连接断开连接，检查是否正常
        :return: None
        """
        for i in range(1, 11):
            all_logger.info("{}进行第{}次连接{}".format("=" * 10, i, "=" * 10))
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_disconnect_button()
            self.check_mbim_disconnect()
            self.windows_api.press_esc()
            time.sleep(5)

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        disconnect_button = self.page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.page_main.click_disable_auto_connect()
        self.windows_api.press_esc()

    def set_apn(self, set_apn_name=True, apn_mode=0, login_type=None, ip_type=None, username=None, password=None):
        """
        设置 Windows端 APN
        :param set_apn_name: APN名称
        :param apn_mode: APN模式
        :param login_type: 登录类型
        :param ip_type: IP类型
        :param username: 用户名
        :param password: 密码
        :return: None
        """
        _apn_mapping = {
            "CMCC": "CMNET",
            "中国联通": "3GNET",
            "中国电信": "CTNET",
        }

        apn = _apn_mapping[self.at_handler.get_operator()]

        # 设置无效APN：属于CMNET，CTNET，3GNET，但是不是乱码
        illegal_apn_mapping = {
            'CMCC': "3GNET",
            '中国联通': "CMNET",
            '中国电信': "CMNET",
        }
        illegal_apn = illegal_apn_mapping[self.at_handler.get_operator()]

        # 设置乱码APN
        mess_apn = self.mess_apn

        if apn_mode == 0:
            apn = apn
        elif apn_mode == 1:
            apn = illegal_apn
        else:
            apn = mess_apn

        all_logger.info("打开高级选项")
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()

        all_logger.info("点击添加接入点")
        self.page_mobile_broadband.click_add_apn_button()

        all_logger.info("设置配置文件名称")
        self.page_mobile_broadband.element_profile_name_edit.set_text(apn)

        if set_apn_name:
            all_logger.info("设置接入点名称")
            self.page_mobile_broadband.element_access_point_name_edit.set_text(apn)

        if username:
            all_logger.info("设置用户名")
            self.page_mobile_broadband.element_access_point_username_edit.set_text(username)

        if password:
            all_logger.info("设置密码")
            self.page_mobile_broadband.element_access_point_password_edit.set_text(password)

        if login_type:  # 无、PAP、CHAP、MS-CHAP v2
            all_logger.info("设置登录模式")
            self.page_mobile_broadband.element_access_point_auth_type_combo_box.select(login_type)

        if ip_type:  # 默认、IPv4、IPv6、IPv4v6
            all_logger.info("设置IP类型")
            self.page_mobile_broadband.element_access_point_ip_type_combo_box.select(ip_type)

        all_logger.info("点击应用此配置文件")
        apply_config_checkbox = self.page_mobile_broadband.element_activate_apn_profile_checkbox
        if apply_config_checkbox.get_toggle_state() == 0:
            apply_config_checkbox.toggle()

        all_logger.info("保存设置")
        self.page_mobile_broadband.click_save_apn_button()

        all_logger.info("关闭设置界面")
        self.page_mobile_broadband.close_mobile_broadband_page()

        all_logger.info("打开高级选项")
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()

        all_logger.info("检查是否已应用")
        apn_data = repr(self.page_mobile_broadband.element_setting_page.ListBox.descendants())
        apn_data_regex = ''.join(re.findall(r"{}\s+已应用".format(apn), apn_data))
        all_logger.info("apn_regex：{}".format(apn_data_regex))
        if not apn_data_regex:
            raise MBIMError("APN设置后未正确应用")

        all_logger.info("关闭设置界面")
        self.page_mobile_broadband.close_mobile_broadband_page()

        time.sleep(3)
        return True

    def remove_apn(self):
        """
        删除所有的APN
        :return: None
        """
        all_logger.info("打开高级选项")
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()
        self.windows_api.wheel(-2)

        access_point_group = self.page_mobile_broadband.element_internet_access_point_group

        while True:
            cmcc_in_use = access_point_group.window(title_re=r".*CMNET.*已应用.*", control_type="ListItem")
            cu_in_use = access_point_group.window(title_re=r".*3GNET.*已应用.*", control_type="ListItem")
            ct_in_use = access_point_group.window(title_re=r".*CTNET.*已应用.*", control_type="ListItem")
            cmcc_in_active = access_point_group.window(title_re=r".*CMNET.*已激活.*", control_type="ListItem")
            cu_in_active = access_point_group.window(title_re=r".*3GNET.*已激活.*", control_type="ListItem")
            ct_in_active = access_point_group.window(title_re=r".*CTNET.*已激活.*", control_type="ListItem")
            cmcc_not_use = access_point_group.window(title_re=r".*CMNET.*未应用.*", control_type="ListItem")
            cu_not_use = access_point_group.window(title_re=r".*3GNET.*未应用.*", control_type="ListItem")
            ct_not_use = access_point_group.window(title_re=r".*CTNET.*未应用.*", control_type="ListItem")
            mess_apn = access_point_group.window(title_re=r"{}".format(self.mess_apn), control_type="ListItem")
            cmcc_in_use_exists = cmcc_in_use.exists()
            cu_in_use_exists = cu_in_use.exists()
            ct_in_use_exists = ct_in_use.exists()
            cmcc_in_active_exists = cmcc_in_active.exists()
            cu_in_active_exists = cu_in_active.exists()
            ct_in_active_exists = ct_in_active.exists()
            cmcc_not_use_exists = cmcc_not_use.exists()
            cu_not_use_exists = cu_not_use.exists()
            ct_not_use_exists = ct_not_use.exists()
            mess_apn_exists = mess_apn.exists()

            all_logger.info("点击应用的APN")

            if cmcc_in_use_exists:
                cmcc_in_use.click_input()
                cmcc_in_use = access_point_group.window(title="删除", control_type="Button")
                cmcc_in_use.click()

            if cu_in_use_exists:
                cu_in_use.click_input()
                cu_in_use = access_point_group.window(title="删除", control_type="Button")
                cu_in_use.click()

            if ct_in_use_exists:
                ct_in_use.click_input()
                ct_in_use = access_point_group.window(title="删除", control_type="Button")
                ct_in_use.click()

            if cmcc_in_active_exists:
                cmcc_in_active.click_input()
                cmcc_in_active = access_point_group.window(title="删除", control_type="Button")
                cmcc_in_active.click()

            if ct_in_active_exists:
                ct_in_active.click_input()
                ct_in_active = access_point_group.window(title="删除", control_type="Button")
                ct_in_active.click()

            if cu_in_active_exists:
                cu_in_active.click_input()
                cu_in_active = access_point_group.window(title="删除", control_type="Button")
                cu_in_active.click()

            if cmcc_not_use_exists:
                cmcc_not_use.click_input()
                cmcc_not_use = access_point_group.window(title="删除", control_type="Button")
                cmcc_not_use.click()

            if cu_not_use_exists:
                cu_not_use.click_input()
                cu_not_use = access_point_group.window(title="删除", control_type="Button")
                cu_not_use.click()

            if ct_not_use_exists:
                ct_not_use.click_input()
                ct_not_use = access_point_group.window(title="删除", control_type="Button")
                ct_not_use.click()

            if mess_apn_exists:
                mess_apn.click_input()
                mess_apn = access_point_group.window(title="删除", control_type="Button")
                mess_apn.click()

            if not cmcc_in_use_exists and not cu_in_use_exists and not ct_in_use_exists and \
                not cmcc_in_active_exists and not cu_in_active_exists and not ct_in_active_exists and \
                    not cmcc_not_use_exists and not ct_not_use_exists and not cu_not_use_exists and not mess_apn_exists:
                break

        all_logger.info("关闭设置界面")
        self.page_mobile_broadband.close_mobile_broadband_page()

    def check_default_apn(self):
        """
        检查当前的APN是否为默认的APN
        :return: None
        """
        all_logger.info("打开高级选项")
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()

        internet_access_point_group = self.page_mobile_broadband.element_internet_access_point_group
        all_logger.info("检查默认接入点为已应用")

        apn_in_use = internet_access_point_group.window(
            title_re=r"默认接入点\s+已应用.*", control_type="ListItem")
        apn_in_use_exists = apn_in_use.exists()

        if not apn_in_use_exists:
            raise MBIMError("未检查到默认接入点已应用")

        self.page_mobile_broadband.close_mobile_broadband_page()

    def hang_up_after_system_dial(self, wait_time):
        """
        系统拨号n秒后主动挂断
        :param wait_time: 系统拨号持续时长
        :return:
        """
        content = {"exec_type": 1,
                   "payload": {
                       "phone_number": self.phone_number,
                       "hang_up_after_dial": wait_time
                   },
                   "request_id": "10011"}
        all_logger.info(f'hang_up_after_system_dial.content: {content}')
        dial_request = requests.post(self.url, json=content)
        dial_request.raise_for_status()
        all_logger.info(dial_request.json())
        self.at_handler.readline_keyword('RING', timout=300)
        self.at_handler.readline_keyword('NO CARRIER', timout=300)
        all_logger.info('wait 10 seconds')
        time.sleep(10)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handler.send_at('AT+CPMS="ME","ME","ME"', 10)    # 指定存储空间
        self.at_handler.send_at('AT+CMGD=0,4', 10)   # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86{}'.format(self.phone_number),
                   },
                   "request_id": "10011"}
        all_logger.info(f'send_msg.content: {content}')
        msg_request = requests.post(self.url, json=content)
        msg_request.raise_for_status()
        all_logger.info(msg_request.json())
        self.at_handler.readline_keyword('+CMTI', timout=300)
        all_logger.info('wait 10 seconds')
        time.sleep(10)
