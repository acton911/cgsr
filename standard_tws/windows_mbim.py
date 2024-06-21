import sys
import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_mbim_manager import WindowsMBIMManager
from utils.functions.iperf import iperf
from utils.logger.logging_handles import all_logger
from utils.functions.windows_api import PINGThread
import traceback


class WindowsMBIM(WindowsMBIMManager):

    @startup_teardown(teardown=['page_mobile_broadband',
                                'close_mobile_broadband_page'])
    def test_windows_mbim_01_001(self):
        """
        MBIM网卡制造商/型号/固件/网络类型等显示正常
        """
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()
        self.page_mobile_broadband.this_page_down()
        self.page_mobile_broadband.click_copy_attributes_button()
        self.at_handler.get_and_compare_module_data()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_mbim_01_002(self):
        """
        SA网络下MBIM界面显示及拨号
        """
        self.at_handler.bound_network("SA")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.check_network_type_and_icon("SA")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_01_003(self):
        """
        重复连接+数传+断开连接10次
        """
        self.connect_and_disconnect_10_times()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_01_004(self):
        """
        拨号后指定带宽30M iperf连接五分钟
        """
        try:
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            ipv4 = self.windows_api.ping_get_connect_status()  # 检查ipv4网络
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            iperf(bind=ipv4, bandwidth='30M', times=300)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_02_001(self):
        """
        MBIM界面添加SIM PIN功能验证
        """
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disable_auto_connect()
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()
        self.page_mobile_broadband.this_page_down()
        self.page_mobile_broadband.this_page_down()
        self.page_mobile_broadband.click_set_sim_pin()
        self.page_mobile_broadband.input_sim_pin()
        self.page_mobile_broadband.click_save_sim_pin()
        self.page_mobile_broadband.close_mobile_broadband_page()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.windows_api.check_dial_init()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_unlock_sim_pin()
        self.page_main.input_sim_pin()
        self.page_main.click_sim_pin_ok_without_check()
        self.windows_api.press_esc()
        self.at_handler.check_network()
        self.page_main.click_network_icon()
        all_logger.info('wait 10 seconds')
        time.sleep(10)
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown()
    def test_windows_mbim_02_002(self):
        """
        SIM PIN状态下MBIM图标信号显示及信号值显示
        """
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.windows_api.check_dial_init()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.check_sim_pin_locked()
        self.page_main.click_unlock_sim_pin()
        self.page_main.input_sim_pin()
        self.page_main.click_sim_pin_ok_without_check()
        self.windows_api.press_esc()
        self.at_handler.check_network()

    @startup_teardown()
    def test_windows_mbim_02_003(self):
        """
        MBIM连接界面解PIN功能验证
        """
        try:
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.windows_api.check_dial_init()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_unlock_sim_pin()
            self.page_main.input_sim_pin()
            self.page_main.click_sim_pin_ok_without_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            self.page_main.click_network_icon()
            all_logger.info('wait 10 seconds')
            time.sleep(10)
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['at_handler',
                                'sin_pin_remove'])
    def test_windows_mbim_02_004(self):
        """
        MBIM界面删除SIM PIN功能验证
        """
        try:
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.windows_api.check_dial_init()
            self.page_mobile_broadband.open_mobile_broadband_page()
            self.page_mobile_broadband.click_advanced_operation()
            self.page_mobile_broadband.this_page_down()
            self.page_mobile_broadband.click_delete_sim_pin()
            self.page_mobile_broadband.input_delete_sim_pin()
            self.page_mobile_broadband.click_confirm_delete_sim_pin()
            self.page_mobile_broadband.close_mobile_broadband_page()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.windows_api.check_dial_init()
            self.at_handler.check_network()
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['remove_apn'])
    def test_windows_mbim_02_005(self):
        """
        添加合法有效接入点(APN),鉴权方式无,IP类型设置为默认
        """
        self.set_apn()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['remove_apn'])
    def test_windows_mbim_02_006(self):
        """
        添加合法有效接入点(APN),鉴权方式PAP,IP类型设置为IPV4
        """
        self.set_apn(login_type="PAP", ip_type="IPv4")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['remove_apn'])
    def test_windows_mbim_02_007(self):
        """
        添加合法有效接入点(APN),鉴权方式CHAP,IP类型设置为IPV6
        """
        self.set_apn(login_type="CHAP", ip_type="IPv6")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['remove_apn'])
    def test_windows_mbim_02_008(self):
        """
        添加合法有效接入点(APN),鉴权方式MS-CHAP V2,IP类型设置为IPV4V6
        """
        self.set_apn(login_type="MS-CHAP v2", ip_type="IPv4v6")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()  # 检查ipv4网络
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_mbim_02_009(self):
        """
        MBIM连接界面飞行模式图标功能测试
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_mbim_02_010(self):
        """
        MBIM连接界面手机网络图标功能测试
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            self.click_enable_mobile_network_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_mbim_02_011(self):
        """
        MBIM自动连接状态下启用再禁用飞行模式
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_mbim_02_012(self):
        """
        MBIM自动连接状态下禁用再启用手机网络
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.click_disable_mobile_network_and_check()
            self.click_enable_mobile_network_and_check()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['windows_api', 'press_esc'])
    def test_windows_mbim_02_013(self):
        """
        MBIM开机过程中MBIM图标加载时间以及状态变化
        """
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_dial_init_time()
        self.at_handler.check_network()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.check_network_type_and_icon()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_mbim_02_014(self):
        """
        固定LTE后MBIM界面显示及拨号
        """
        self.at_handler.bound_network("LTE")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.check_network_type_and_icon("LTE")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_mbim_02_015(self):
        """
        LTE拨号后指定带宽10M iperf连接五分钟
        """
        try:
            self.at_handler.bound_network("LTE")
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            ipv4 = self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            all_logger.info("wait 30 seconds")
            time.sleep(30)  # 如果立刻运行前几秒可能会断流
            iperf(bind=ipv4, bandwidth='10M', times=300)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_02_016(self):
        """
        模块重启后MBIM功能测试
        """
        try:
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status(flag=False)  # 检查ipv4网络
            self.windows_api.press_esc()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.windows_api.check_dial_init()
            self.at_handler.check_network()
            self.disable_auto_connect_find_connect_button()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            self.check_mbn()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_011(self):
        """
        来短信
        """
        # 进行拨号
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        # 进行接短信测试
        ping = None
        exc_type = None
        exc_value = None
        try:
            ping = PINGThread(times=150, flag=True)
            ping.setDaemon(True)
            ping.start()
            self.send_msg()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handler.send_at('AT+QNWPREFCFG="NR5G_DISABLE_MODE",0', 10)  # 打开SA网络
            ping.terminate()
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_012(self):
        """
        来电话
        """
        # 进行拨号
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.check_mbn()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        # 进行打电话测试
        ping = None
        exc_type = None
        exc_value = None
        try:
            ping = PINGThread(times=150, flag=True)
            ping.setDaemon(True)
            ping.start()
            self.hang_up_after_system_dial(10)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            ping.terminate()
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()

    def test_windows_mbim_03_001(self):
        """
        开启自动连接，禁用启用MBIM驱动
        """
        # 进行拨号
        exc_type = None
        exc_value = None
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_enable_auto_connect()
        self.check_mbim_connect()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        try:
            # 禁用MBIM驱动
            self.enable_disable_mbim_driver(True, self.mbim_driver_name)  # 禁用MBIM驱动
            # 启用MBIM驱动
            self.enable_disable_mbim_driver(False, self.mbim_driver_name)  # 启用MBIM驱动
            # 手机网络加载成功，拨号已连接，ping百度和pingIPV6成功
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.check_dial_init()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_mbim_03_002(self):
        """
        不开启自动连接，禁用启用MBIM驱动
        """
        # 进行拨号
        exc_type = None
        exc_value = None
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect_disconnect()
        try:
            # 禁用MBIM驱动
            self.enable_disable_mbim_driver(True, self.mbim_driver_name)  # 禁用MBIM驱动
            # 启用MBIM驱动
            self.enable_disable_mbim_driver(False, self.mbim_driver_name)  # 启用MBIM驱动
            # 手机网络加载成功，拨号已连接，ping百度和pingIPV6成功
            self.page_main.click_network_icon()  # 点击手机网络按钮
            self.page_main.click_network_details()  # 点击网络详情
            self.check_mbim_disconnect()  # 检查是否是断开连接状态
            self.mbim_connect()   # 进行MBIM拨号
            self.windows_api.ping_get_connect_status()   # ping包测试
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            # self.page_main.click_connect_button()
            # self.windows_api.ping_get_connect_status()
            # self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            # self.windows_api.press_esc()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()

    def test_windows_mbim_03_007(self):
        """
        MBIM自动连接状态下重启电脑
        """
        # 进行拨号
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
    def test_windows_mbim_04_002(self):
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
        'at_port': 'COM10',
        'dm_port': 'COM7',
        'mbim_driver_name': "RG500Q-EA",
        'ipv6_address': "2400:3200::1",
        'phone_number': '17333196097'
    }
    w = WindowsMBIM(**param_dict)
    # w.test_windows_mbim_01_001()
    # w.test_windows_mbim_01_002()
    # w.test_windows_mbim_01_003()
    # w.test_windows_mbim_01_004()
    # w.test_windows_mbim_02_001()
    # w.test_windows_mbim_02_002()
    # w.test_windows_mbim_02_003()
    # w.test_windows_mbim_02_004()
    # w.test_windows_mbim_02_005()
    # w.test_windows_mbim_02_006()
    # w.test_windows_mbim_02_007()
    # w.test_windows_mbim_02_008()
    # w.test_windows_mbim_02_009()
    # w.test_windows_mbim_02_010()
    # w.test_windows_mbim_02_011()
    # w.test_windows_mbim_02_012()
    # w.test_windows_mbim_02_013()
    # w.test_windows_mbim_02_014()
    # w.test_windows_mbim_02_015()
    # w.test_windows_mbim_02_016()
    # w.test_windows_mbim_03_001()
    # w.test_windows_mbim_03_002()
    # w.test_windows_mbim_04_002()
    # w.test_windows_mbim_03_011()
    # w.test_windows_mbim_03_012()
