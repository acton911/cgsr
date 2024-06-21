#  import os
import sys
import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_mbim_manager import WindowsMBIMManager
from utils.functions.iperf import iperf
from utils.logger.logging_handles import all_logger
from utils.functions.windows_api import PINGThread
import traceback


class WindowsPCIEMBIM(WindowsMBIMManager):

    @startup_teardown()
    def test_windows_mbim_01_000(self):
        pass
        # win32api.MessageBox(0, '666', '888')
        """
        if sys.getwindowsversion()[2] >= 22000:
            print("yes")
        else:
            print("no")
        """
    # @startup_teardown(teardown=['page_mobile_broadband',
    #                             'close_mobile_broadband_page'])
    @startup_teardown()
    def test_windows_mbim_01_001(self):
        """
        MBIM网卡制造商/型号/固件/网络类型等显示正常
        https://docs.microsoft.com/zh-cn/windows-server/networking/technologies/netsh/netsh-mbn
        https://docs.microsoft.com/zh-cn/windows-hardware/drivers/mobilebroadband/get-the-imei-iccid-imsi-and-telephone-numbers-for-the-mobile-broadband-device
        """
        # self.page_mobile_broadband.open_mobile_broadband_page()
        # self.page_mobile_broadband.click_advanced_operation()
        # self.page_mobile_broadband.this_page_down()
        # self.page_mobile_broadband.click_copy_attributes_button()
        self.get_and_compare_module_data()

    # @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
    #                   teardown=['at_handler', 'reset_network_to_default'])
    @startup_teardown()
    def test_windows_mbim_01_002(self):
        """
        SA网络下MBIM界面显示及拨号
        """
        try:
            self.at_handler.bound_network("SA")
            # self.page_main.click_network_icon()
            # self.page_main.click_network_details()
            # self.page_main.click_connect_button()
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            # self.check_mbim_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            # self.windows_api.press_esc()
            # self.check_network_type_and_icon("SA")
            # self.page_main.click_network_icon()
            # self.page_main.click_network_details()
            # self.page_main.click_disconnect_button()
            # self.check_mbim_disconnect()
            # self.windows_api.press_esc()
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    # @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    @startup_teardown()
    def test_windows_mbim_01_003(self):
        """
        重复连接+数传+断开连接10次
        """
        try:
            self.connect_and_disconnect_10_times()
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    # @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    @startup_teardown()
    def test_windows_mbim_01_004(self):
        """
        拨号后指定带宽30M iperf连接五分钟
        """
        try:
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            ipv4 = self.windows_api.ping_get_connect_status()  # 检查ipv4网络
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            time.sleep(30)
            iperf(bind=ipv4, bandwidth='30M', times=300)
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    # @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    @startup_teardown()
    def test_windows_mbim_02_002(self):
        """
        MBIM界面添加SIM PIN功能验证
        """
        try:
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            time.sleep(3)
            self.page_main.click_disable_auto_connect()
            self.page_mobile_broadband.open_mobile_broadband_page()
            if self.is_win11:
                all_logger.info("当前为win11")
                self.page_mobile_broadband.this_page_down()
                # self.page_mobile_broadband.this_page_down()
                time.sleep(1)
                self.page_mobile_broadband.click_oprate_setting()  # win11系统
            else:
                all_logger.info("当前为win10")
                self.page_mobile_broadband.click_advanced_operation()  # win10系统
# 添加SIM PIN
            self.page_mobile_broadband.this_page_down()
            self.page_mobile_broadband.this_page_down()
            self.page_mobile_broadband.click_set_sim_pin()
            self.page_mobile_broadband.input_sim_pin()
            self.page_mobile_broadband.click_save_sim_pin()
            self.page_mobile_broadband.close_mobile_broadband_page()
#  重启模块test
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.readline_keyword('PB DONE', 50)
            self.at_handler.send_at('AT')
            time.sleep(5)
#  TO DO 检查信号值和状态显示
#  解PIN
            if self.is_win11:
                all_logger.info("当前为win11")
                self.page_mobile_broadband.open_mobile_broadband_page()
                self.page_mobile_broadband.click_sim_pin_connect_button()
                self.page_mobile_broadband.input_unclock_sim_pin()
                self.page_mobile_broadband.click_sim_pin_ok_without_check()
                time.sleep(3)
                self.page_mobile_broadband.close_mobile_broadband_page()
            else:
                all_logger.info("当前为win10")
                self.page_main.click_network_icon()
                self.page_main.click_network_details()
                self.page_main.click_unlock_sim_pin()
                self.page_main.input_sim_pin()
                self.page_main.click_sim_pin_ok_without_check()
                self.windows_api.press_esc()
            self.at_handler.check_network()
            time.sleep(5)
            """
            self.page_main.click_network_icon()
            all_logger.info('wait 10 seconds')
            time.sleep(10)
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            """
#  拨号，ping
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            """
            self.windows_api.press_esc()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_disconnect_button()
            self.check_mbim_disconnect()
            self.windows_api.press_esc()
            """
#  删除PIN 锁
            try:
                self.cfun0_1()
                # self.at_handler.check_network()
                self.page_mobile_broadband.open_mobile_broadband_page()
                if self.is_win11:
                    all_logger.info("当前为win11")
                    self.page_mobile_broadband.this_page_down()
                    self.page_mobile_broadband.this_page_down()
                    self.page_mobile_broadband.click_oprate_setting()  # win11系统
                else:
                    all_logger.info("当前为win10")
                    self.page_mobile_broadband.click_advanced_operation()  # win10系统
                self.page_mobile_broadband.this_page_down()
                self.page_mobile_broadband.click_delete_sim_pin()
                self.page_mobile_broadband.input_delete_sim_pin()
                self.page_mobile_broadband.click_confirm_delete_sim_pin()
                self.page_mobile_broadband.close_mobile_broadband_page()
                self.cfun0_1()
                self.at_handler.check_network()
                """
                self.disable_auto_connect_find_connect_button()
                self.page_main.click_connect_button()
                self.check_mbim_connect()
                """
                self.mbim_connect()
                self.check_mbim_connect_disconnect()
                self.windows_api.ping_get_connect_status()
                self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
                """
                self.windows_api.press_esc()
                self.check_network_type_and_icon()
                """
            finally:
                # self.disable_auto_connect_and_disconnect()
                self.mbim_disconnect()
                self.check_mbim_connect_disconnect(False)
        finally:
            # self.disable_auto_connect_and_disconnect()
            if self.is_win11:
                all_logger.info("当前为win11")
                self.page_mobile_broadband.this_page_down()
                self.page_mobile_broadband.this_page_down()
                self.page_mobile_broadband.click_oprate_setting()  # win11系统
            else:
                all_logger.info("当前为win10")
                self.page_mobile_broadband.click_advanced_operation()  # win10系统
            self.page_mobile_broadband.this_page_down()
            self.page_mobile_broadband.click_delete_sim_pin()
            self.page_mobile_broadband.input_delete_sim_pin()
            self.page_mobile_broadband.click_confirm_delete_sim_pin()
            self.page_mobile_broadband.close_mobile_broadband_page()
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    @startup_teardown()
    def test_windows_mbim_02_003(self):
        """
        SIM PIN状态下MBIM图标信号显示及信号值显示
        """
        self.cfun0_1()
        # self.at_handler.check_network()
        time.sleep(60)
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        if self.is_win11:
            all_logger.info("当前为win11系统")
            self.check_sim_pin_locked_win11()
            self.page_mobile_broadband.open_mobile_broadband_page()
            self.page_mobile_broadband.click_sim_pin_connect_button()
            self.page_mobile_broadband.input_unclock_sim_pin()
            self.page_mobile_broadband.click_sim_pin_ok_without_check()
            time.sleep(3)
            self.page_mobile_broadband.close_mobile_broadband_page()
        else:
            all_logger.info("当前为win10系统")
            self.check_sim_pin_locked()
            self.page_main.click_unlock_sim_pin()
            self.page_main.input_sim_pin()
            self.page_main.click_sim_pin_ok_without_check()
            self.windows_api.press_esc()
        self.at_handler.check_network()

    @startup_teardown()
    def test_windows_mbim_02_004(self):
        """
        MBIM连接界面解PIN功能验证
        """
        try:
            self.cfun0_1()
            # self.at_handler.check_network()
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_mobile_broadband.open_mobile_broadband_page()
                self.page_mobile_broadband.click_sim_pin_connect_button()
                self.page_mobile_broadband.input_unclock_sim_pin()
                self.page_mobile_broadband.click_sim_pin_ok_without_check()
                time.sleep(3)
                self.page_mobile_broadband.close_mobile_broadband_page()
            else:
                all_logger.info("当前为win10系统")
                self.page_main.click_network_icon()
                self.page_main.click_network_details()
                self.page_main.click_unlock_sim_pin()
                self.page_main.input_sim_pin()
                self.page_main.click_sim_pin_ok_without_check()
                self.windows_api.press_esc()
            self.at_handler.check_network()
            """
            self.page_main.click_network_icon()
            all_logger.info('wait 10 seconds')
            time.sleep(10)
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            """
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            """
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            """
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)
            # self.disable_auto_connect_and_disconnect()

    # @startup_teardown(teardown=['at_handler', 'sin_pin_remove'])
    def test_windows_mbim_02_005(self):
        """
        MBIM界面删除SIM PIN功能验证
        """
        try:
            self.cfun0_1()
            # self.at_handler.check_network()
            self.page_mobile_broadband.open_mobile_broadband_page()
            if self.is_win11:
                all_logger.info("当前为win11")
                self.page_mobile_broadband.this_page_down()
                self.page_mobile_broadband.this_page_down()
                self.page_mobile_broadband.click_oprate_setting()  # win11系统
            else:
                all_logger.info("当前为win10")
                self.page_mobile_broadband.click_advanced_operation()  # win10系统
            self.page_mobile_broadband.this_page_down()
            self.page_mobile_broadband.click_delete_sim_pin()
            self.page_mobile_broadband.input_delete_sim_pin()
            self.page_mobile_broadband.click_confirm_delete_sim_pin()
            self.page_mobile_broadband.close_mobile_broadband_page()
            self.cfun0_1()
            self.at_handler.check_network()
            """
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            """
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            """
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            """
        finally:
            # self.disable_auto_connect_and_disconnect()
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_mbim_02_010(self):
        """
        MBIM连接界面飞行模式图标功能测试
        """
        try:
            # self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            time.sleep(5)
            """
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            """
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            """
            self.windows_api.press_esc()
            time.sleep(5)
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
            """
        finally:
            # self.disable_auto_connect_and_disconnect()
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)
            time.sleep(5)

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_mbim_02_011(self):
        """
        MBIM连接界面手机网络图标功能测试
        """
        try:
            # self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            self.click_enable_mobile_network_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            """
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            """
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            """
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
            """
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)
            # self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_mbim_02_012(self):
        """
        MBIM自动连接状态下启用再禁用飞行模式
        """
        try:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.windows_api.press_esc()
            time.sleep(5)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_details()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_mbim_02_013(self):
        """
        MBIM自动连接状态下禁用再启用手机网络
        """
        try:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.windows_api.press_esc()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            self.click_enable_mobile_network_and_check()
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_details()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_mbim_02_014(self):
        """
        固定LTE后MBIM界面显示及拨号
        """
        self.at_handler.bound_network("LTE")
        time.sleep(5)
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.check_network_type_and_icon("LTE")
        time.sleep(5)
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()
        time.sleep(5)

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_mbim_02_015(self):
        """
        LTE拨号后指定带宽10M iperf连接五分钟
        """
        try:
            self.at_handler.bound_network("LTE")
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            ipv4 = self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            all_logger.info("wait 30 seconds")
            time.sleep(60)  # 如果立刻运行前几秒可能会断流
            iperf(bind=ipv4, bandwidth='10M', times=300)
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown()
    def test_windows_mbim_03_002(self):
        """
        1.电脑整机睡眠
        2.摇晃鼠标或者按电源键唤醒电脑
        3.点击电脑右下角连接网络
        """
        try:
            self.enter_modern_standby()
            time.sleep(5)  # 唤醒后，windows恢复正常
            self.at_handler.check_network()
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    @startup_teardown()
    def test_windows_mbim_03_003(self):
        """
        1.电脑整机休眠
        2.按电源键唤醒电脑
        3.点击电脑右下角连接网络
        """
        try:
            self.enter_S3_S4_sleep()
            time.sleep(120)  # 等待休眠唤醒后，windows恢复正常
            self.at_handler.check_network()
            self.mbim_connect()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_mbim_03_004(self):
        """
        MBIM自动连接状态下禁用再启用手机网络
        """
        try:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.windows_api.press_esc()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            self.click_enable_mobile_network_and_check()
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_details()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(startup=['enable_mobile_network'])
    def test_windows_mbim_03_005(self):
        """
        1. 设备管理器-网络适配器-禁用MBIM驱动
        2. 再启用MBIM驱动
        """
        try:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            all_logger.info("wait 10 seconds")
            time.sleep(10)
            self.windows_api.press_esc()
            self.enable_disable_mbim_driver(True, self.mbim_driver_name)  # 禁用驱动
            self.enable_disable_mbim_driver(False, self.mbim_driver_name)  # 启动驱动
            self.windows_api.check_dial_init()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_006(self):
        try:
            time.sleep(5)
            self.enable_disable_mbim_driver(True, self.mbim_driver_name)  # 禁用驱动
            self.enable_disable_mbim_driver(False, self.mbim_driver_name)  # 启动驱动
            self.windows_api.check_dial_init()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(60)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    def test_windows_mbim_03_011(self):
        """
        MBIM自动连接状态下重启电脑
        @return:
        """
        try:
            if not self.reboot.get_restart_flag():  # 代表还未进行重启
                self.page_main.click_network_icon()
                self.page_main.click_network_details()
                self.page_main.click_enable_auto_connect()
                self.windows_api.ping_get_connect_status()
                self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
                self.reboot.restart_computer()
            else:   # 已经重启过主机
                self.at_handler.check_network()
                self.windows_api.check_dial_init()
                self.check_mbim_connect(True)
                self.windows_api.ping_get_connect_status()
                self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_012(self):
        try:
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.enter_modern_standby(p=300)
            time.sleep(120)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_013(self):
        try:
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.enter_S3_S4_sleep(p=300)
            time.sleep(600)  # 等待休眠唤醒后，windows各项功能恢复正常
            self.at_handler.check_network()
            self.check_mbim_connect_disconnect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown()
    def test_windows_mbim_03_015(self):
        """
        来短信,来电话（data only不测试）
        """
        # 进行拨号
        """
        time.sleep(5)
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_enable_auto_connect()
        """
        self.mbim_connect()
        self.check_mbim_connect_disconnect()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        # 进行打电话，接短信测试

        self.at_handler.send_at('AT+QURCCFG="urcport","usbmodem"', 3)  # 设置上报口
        ping = None
        exc_type = None
        exc_value = None
        try:
            ping = PINGThread(times=150, flag=True)
            ping.setDaemon(True)
            ping.start()
            # self.hang_up_after_system_dial(10) data only不测试
            time.sleep(5)
            self.send_msg()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.mbim_disconnect()
            self.check_mbim_connect_disconnect(False)
            ping.terminate()
            # self.windows_api.press_esc()
            # self.disable_auto_connect_and_disconnect()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.at_handler.send_at('AT+QURCCFG="urcport","usbat"', 3)  # 设置上报口
        # self.windows_api.press_esc()
        # time.sleep(5)

    def test_windows_mbim_04_004(self):
        """
        WCDMA界面显示及拨号
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handler.bound_network("WCDMA")
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon("HSPA")
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_disconnect_button()
            self.check_mbim_disconnect()
            self.windows_api.press_esc()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            self.at_handler.reset_network_to_default()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()


if __name__ == '__main__':
    param_dict = {
        'at_port': 'COM3',
        'dm_port': 'COM5',
        'mbim_driver_name': 'Quectel RM520NGLAP #12',
        'ipv6_address': "2400:3200::1",
        'phone_number': '18656504506'
    }
    w = WindowsPCIEMBIM(**param_dict)

    # w.test_windows_mbim_01_000()

    # w.test_windows_mbim_01_001()  # P0
    # w.test_windows_mbim_01_002()  # P0
    # w.test_windows_mbim_01_003()  # P0
    # w.test_windows_mbim_01_004()  # P0

    # w.test_windows_mbim_02_002()  # p1 OK
    # w.test_windows_mbim_02_003()  # p1 OK
    # w.test_windows_mbim_02_004()  # p1 OK
    # w.test_windows_mbim_02_005()  # p1 OK
    # w.test_windows_mbim_02_010()  # p1 OK
    # w.test_windows_mbim_02_011()  # p1 OK
    # w.test_windows_mbim_02_012()  # p1 OK
    # w.test_windows_mbim_02_013()  # p1 OK
    # w.test_windows_mbim_02_014()  # p1 OK
    # w.test_windows_mbim_02_015()  # p1 OK 会出现断流111

    # w.test_windows_mbim_03_002()  # p2 待实现 OK
    # w.test_windows_mbim_03_003()  # p2 待实现 OK
    # w.test_windows_mbim_03_004()  # p2 OK
    # w.test_windows_mbim_03_005()  # p2 OK
    # w.test_windows_mbim_03_006()  # p2 OK
    # w.test_windows_mbim_03_012()  # p2 待实现  OK
    # w.test_windows_mbim_03_013()  # p2 待实现 OK
    # w.test_windows_mbim_03_015()  # p2 OK
    # w.test_windows_mbim_04_004()  # p3 OK
