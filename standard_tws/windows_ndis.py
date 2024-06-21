import sys
import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_ndis_manager import WindowsNDISManager
from utils.functions.iperf import iperf
from utils.logger.logging_handles import all_logger
from utils.functions.windows_api import PINGThread
import traceback


class WindowsNDIS(WindowsNDISManager):

    @startup_teardown(teardown=['page_mobile_broadband',
                                'close_mobile_broadband_page'])
    def test_windows_ndis_01_001(self):
        """
        ndis网卡制造商/型号/固件/网络类型等显示正常
        """
        self.page_mobile_broadband.open_mobile_broadband_page()
        self.page_mobile_broadband.click_advanced_operation()
        self.page_mobile_broadband.this_page_down()
        self.page_mobile_broadband.click_copy_attributes_button()
        self.at_handler.get_and_compare_module_data()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_ndis_01_002(self):
        """
        SA网络下ndis界面显示及拨号
        """
        self.at_handler.bound_network("SA")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
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
    def test_windows_ndis_01_003(self):
        """
        重复连接+数传+断开连接10次
        """
        self.connect_and_disconnect_10_times()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_01_004(self):
        """
        拨号后指定带宽30M iperf连接五分钟
        """
        try:
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            ipv4 = self.windows_api.ping_get_connect_status()  # 检查ipv4网络
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            iperf(bind=ipv4, bandwidth='30M', times=300)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_02_001(self):
        """
        ndis界面添加SIM PIN功能验证
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
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        self.windows_api.press_esc()
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        self.check_mbim_disconnect()
        self.windows_api.press_esc()

    @startup_teardown()
    def test_windows_ndis_02_002(self):
        """
        SIM PIN状态下ndis图标信号显示及信号值显示
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
    def test_windows_ndis_02_003(self):
        """
        ndis连接界面解PIN功能验证
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
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['at_handler',
                                'sin_pin_remove'])
    def test_windows_ndis_02_004(self):
        """
        ndis界面删除SIM PIN功能验证
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
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_ndis_02_005(self):
        """
        ndis连接界面飞行模式图标功能测试
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
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def test_windows_ndis_02_006(self):
        """
        ndis连接界面手机网络图标功能测试
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
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_ndis_02_007(self):
        """
        ndis自动连接状态下启用再禁用飞行模式
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
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
    def test_windows_ndis_02_008(self):
        """
        ndis自动连接状态下禁用再启用手机网络
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
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
    def test_windows_ndis_02_009(self):
        """
        NDIS开机过程中NDIS图标加载时间以及状态变化
        """
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_dial_init_time()
        self.at_handler.check_network()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
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
    def test_windows_ndis_02_010(self):
        """
        固定LTE后NDIS界面显示及拨号
        """
        self.at_handler.bound_network("LTE")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
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
    def test_windows_ndis_02_011(self):
        """
        LTE拨号后指定带宽10M iperf连接五分钟
        """
        try:
            self.at_handler.bound_network("LTE")
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
            ipv4 = self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            all_logger.info("wait 30 seconds")
            time.sleep(30)  # 如果立刻运行前几秒可能会断流
            iperf(bind=ipv4, bandwidth='10M', times=300)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_02_012(self):
        """
        模块重启后NDIS功能测试
        """
        try:
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.check_mbim_connect()
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
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
            self.check_network_type_and_icon()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_ndis_03_001(self):
        """
        MBIM自动连接状态下禁用再启用手机网络
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
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

    @startup_teardown(startup=['enable_mobile_network'])
    def test_windows_ndis_03_002(self):
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            all_logger.info("wait 10 seconds")
            time.sleep(10)
            self.windows_api.press_esc()
            self.enable_disable_mbim_driver(True, self.ndis_driver_name)  # 禁用驱动
            self.enable_disable_mbim_driver(False, self.ndis_driver_name)  # 启动驱动
            self.windows_api.check_dial_init()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_03_003(self):
        try:
            self.enable_disable_mbim_driver(True, self.ndis_driver_name)  # 禁用驱动
            self.enable_disable_mbim_driver(False, self.ndis_driver_name)  # 启动驱动
            self.windows_api.check_dial_init()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_connect_button()
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_03_009(self):
        """
        NDIS自动连接状态下重启电脑
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
            else:  # 已经重启过主机
                self.at_handler.check_network()
                self.windows_api.check_dial_init()
                self.check_mbim_connect(True)
                self.windows_api.ping_get_connect_status()
                self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_03_013(self):
        """
        来电话
        """
        # 进行拨号
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        # 进行打电话，接短信测试
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

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'])
    def test_windows_ndis_03_014(self):
        """
        来短信
        """
        # 进行拨号
        self.at_handler.bound_network("LTE")
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_connect_button()
        self.check_mbim_connect()
        self.windows_api.ping_get_connect_status()
        self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
        # 接短信测试
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
            ping.terminate()
            self.windows_api.press_esc()
            self.disable_auto_connect_and_disconnect()
            self.at_handler.bound_network('SA')
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.windows_api.press_esc()


if __name__ == '__main__':
    param_dict = {
        'at_port': 'COM10',
        'dm_port': 'COM7',
        'ndis_driver_name': "Quectel*Wireless*Ethernet*",
        'ipv6_address': "2400:3200::1",
        'phone_number': '15256905471'
    }
    w = WindowsNDIS(**param_dict)
    # w.test_windows_ndis_01_001()
    # w.test_windows_ndis_01_002()
    # w.test_windows_ndis_01_003()
    # w.test_windows_ndis_01_004()
    # w.test_windows_ndis_02_001()
    # w.test_windows_ndis_02_002()
    # w.test_windows_ndis_02_003()
    # w.test_windows_ndis_02_004()
    # w.test_windows_ndis_02_005()
    # w.test_windows_ndis_02_006()
    # w.test_windows_ndis_02_007()
    # w.test_windows_ndis_02_008()
    # w.test_windows_ndis_02_009()
    # w.test_windows_ndis_02_010()
    # w.test_windows_ndis_02_011()
    # w.test_windows_ndis_02_012()
    # w.test_windows_ndis_03_001()
    # w.test_windows_ndis_03_002()
    # w.test_windows_ndis_03_003()
    # w.test_windows_ndis_03_013()
