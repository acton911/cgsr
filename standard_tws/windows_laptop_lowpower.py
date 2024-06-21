import sys
import time
from utils.functions.windows_api import PINGThread
from utils.logger.logging_handles import all_logger
from utils.cases.windows_laptop_lowpower_manager import WindowsLapTopLowPowerManager
import traceback
from utils.functions.decorators import startup_teardown


class WindowsLapTopLowPower(WindowsLapTopLowPowerManager):
    @startup_teardown()
    def windows_laptop_low_power_01_001(self):
        """
        笔电未插卡情况下，模块可以进入D3_COLD，刷新设备管理器唤醒正常（没有引脚无法实现掉卡）
        :return:
        """
        # self.check_qsclk(0)
        all_logger.info('打开设备管理器')
        self.page_devices_manager.open_devices_manager()
        all_logger.info('关闭设备管理器')
        self.close_devices_page()
        # time.sleep(1)
        # all_logger.info("点击扫描检测硬件改动")
        # for i in range(10):
        #     self.page_devices_manager.element_scan_devices_icon().click()

        # self.page_main.click_network_icon()
        # self.page_main.element_airplane_mode_button.click_input()

        # self.enable_disable_device(True, "CMIOT USB AT Port*")
        # self.enable_disable_pcie_ports(False, self.pcie_ports)

    @startup_teardown()
    def windows_laptop_low_power_01_002(self):
        """
        电脑飞行模式下(相当于模块CFUN4)，模块可以进入D3_COLD，刷新设备管理器唤醒正常:
        1.电脑设置飞行模式
        2.等待5s，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.刷新设备管理器唤醒模块，模块退出lowpower
        4.不执行任何操作，等待5s，模块再次进入D3_COLD_STATE
        """
        exc_type = None
        exc_value = None
        try:
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            all_logger.info('电脑设置飞行模式')
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.windows_api.press_esc()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(120)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(60)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            all_logger.info('电脑退出飞行模式')
            self.page_main.click_network_icon()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            time.sleep(3)
            self.disable_airplane_mode()
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_01_003(self):
        """
        NETWORK DISCONNECT下，模块可以进入D3_COLD，通过刷新设备管理器唤醒正常:
        1.MBIM未连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.刷新设备管理器唤醒模块，查看电源状态，期望推出睡眠
        4.不执行任何操作，等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            # all_logger.info('NETWORK DISCONNECT')
            # self.disable_auto_connect_and_disconnect()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_01_004(self):
        """
        NETWORK DISCONNECT下，模块可以进入D3_COLD，通过建立连接唤醒正常:
        1.MBIM未连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.建立连接，查看电源状态，期望推出睡眠
        4.断开连接，等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            # all_logger.info('NETWORK DISCONNECT')
            # self.disable_auto_connect_and_disconnect()
            # all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info("建立连接")
            self.mbim_connect_and_check()
            # self.windows_api.check_dial_init()
            # self.dial()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('断开连接')
            self.mbim_disconnect_and_check()
            # self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_01_005(self):
        """
        NETWORK DISCONNECT下，模块可以进入D3_COLD，来SMS短信被动唤醒正常:(编写后暂未调试验证)
        1.MBIM未连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.来SMS短信，查看电源状态，期望推出睡眠
        4.等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",lte', 10)  # 切换到lte防止收不到短信
            self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
            self.at_handle.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            # all_logger.info('NETWORK DISCONNECT')
            # self.disable_auto_connect_and_disconnect()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info("来SMS短信")
            self.send_msg()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False, sleep=False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto', 10)  # 切回到auto
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_01_006(self):
        """
        1.进行MBIM连接
        2.电脑整机睡眠，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.通过Power Tool查看当前耗流(观察1min)
        4.主动通过键盘鼠标或者电源键唤醒电脑，查看电源状态
        5.电脑再次整机睡眠，查看电源状态
        6.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            time.sleep(5)
            all_logger.info("建立连接")
            self.mbim_connect_and_check()
            time.sleep(15)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('笔电进入modern standby')
            self.enter_modern_standby()
            time.sleep(15)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            all_logger.info('断开连接')
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_01_007(self):
        """
        1.进行MBIM连接
        2.整机睡眠，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.模块来短信
        4.整机睡眠，查看电源状态
        5.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",lte', 10)  # 切换到lte防止收不到短信
            self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
            self.at_handle.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
            self.at_handle.check_network()
            self.close_all_ports()
            time.sleep(5)
            all_logger.info("建立连接")
            self.mbim_connect_and_check()
            time.sleep(15)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('笔电进入modern standby')
            self.enter_modern_standby()
            all_logger.info("来SMS短信")
            self.send_msg()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False, sleep=False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            all_logger.info('断开连接')
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto', 10)  # 切回到auto
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_002(self):
        """
        1.笔电插卡，网络固定LTE
        2.电脑整机睡眠，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.通过Power Tool查看当前耗流(观察1min)
        4.主动通过键盘鼠标或者电源键唤醒电脑，查看电源状态
        5.电脑再次整机睡眠，查看电源状态
        6.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.bound_network("LTE")
            self.at_handle.check_network()
            self.close_all_ports()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('笔电进入modern standby')
            self.enter_modern_standby()
            time.sleep(15)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False, sleep=False)
            all_logger.info('等待5s')
            all_logger.info('笔电再次进入modern standby')
            self.enter_modern_standby()
            time.sleep(15)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto', 10)  # 切回到auto
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_003(self):
        """
        1.电脑设置飞行模式
        2.电脑整机睡眠，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.通过Power Tool查看当前耗流(观察1min)
        4.主动通过键盘鼠标或者电源键唤醒电脑，查看电源状态
        5.电脑再次整机睡眠，查看电源状态
        6.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.close_all_ports()
            all_logger.info('电脑设置飞行模式')
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.windows_api.press_esc()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('笔电进入modern standby')
            self.enter_modern_standby()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('笔电再次进入modern standby')
            self.enter_modern_standby()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            all_logger.info('电脑退出飞行模式')
            self.page_main.click_network_icon()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            time.sleep(3)
            self.disable_airplane_mode()
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_004(self):
        """
        1.MBIM未连接
        2.电脑整机睡眠，进入DEBUG口查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        3.通过Power Tool查看当前耗流(观察1min)
        4.主动通过键盘鼠标或者电源键唤醒电脑，查看电源状态
        5.电脑再次整机睡眠，查看电源状态
        6.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            self.mbim_disconnect_and_check()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('笔电进入modern standby')
            self.enter_modern_standby()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('笔电再次进入modern standby')
            self.enter_modern_standby()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_005(self):
        """
        NETWORK CONNECT下，模块可以进入D3_COLD，通过刷新设备管理器唤醒正常:
        1.进行MBIM连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.刷新设备管理器唤醒模块，查看电源状态，期望推出睡眠
        4.不执行任何操作，等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            self.mbim_connect_and_check()
            # all_logger.info('NETWORK CONNECT')
            # self.windows_api.check_dial_init()
            # self.dial()
            time.sleep(60)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('打开设备管理器')
            self.page_devices_manager.open_devices_manager()
            all_logger.info('刷新设备管理器')
            self.page_devices_manager.element_scan_devices_icon().click()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_006(self):
        """
        NETWORK CONNECT下，模块可以进入D3_COLD，通过访问网页唤醒正常:
        1.进行MBIM连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.通过PING 网址唤醒模块，查看电源状态, 期望推出睡眠
        4.停止数传，不执行任何操作，等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            self.mbim_connect_and_check()
            # all_logger.info('NETWORK CONNECT')
            # self.windows_api.check_dial_init()
            # ping = PINGThread(times=150, flag=True)
            # ping.setDaemon(True)
            # self.dial()
            time.sleep(60)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info('通过PING网址唤醒模块')
            self.windows_api.ping_get_connect_status()
            # ping.start()
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False)
            # ping.terminate()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            # ping.terminate()
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_007(self):
        """
        NETWORK CONNECT下，模块可以进入D3_COLD，来SMS短信被动唤醒正常:
        1.进行MBIM连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.来SMS短信，查看电源状态，期望推出睡眠
        4.等待5s，模块再次进入D3_COLD_STATE，期望再次进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",lte', 10)  # 切换到lte防止收不到短信
            self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
            self.at_handle.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            self.mbim_connect_and_check()
            # all_logger.info('NETWORK CONNECT')
            # self.windows_api.check_dial_init()
            # self.dial()
            time.sleep(60)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info("来SMS短信")
            self.send_msg()
            all_logger.info('进入DEBUG口查看，期望已退出睡眠')
            self.debug_check(False, sleep=False)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto', 10)  # 切回到auto
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_008(self):
        """
        NETWORK CONNECT下，模块可以进入D3_COLD，拨号不会断开:
        1.进行MBIM连接
        2.等待5s，进入DEBUG口查看电源状态，期望进入睡眠
        3.观察10min，看拨号是否会断开
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            # self.enable_disable_pcie_ports(True, self.pcie_ports)
            self.mbim_connect_and_check()
            # all_logger.info('NETWORK CONNECT')
            # self.windows_api.check_dial_init()
            # ping = PINGThread(times=150, flag=True)
            # ping.setDaemon(True)
            # self.dial()
            time.sleep(60)
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
            all_logger.info("等待10分钟")
            time.sleep(600)
            all_logger.info("等待10分钟后再次检测拨号是否正常")
            self.windows_api.ping_get_connect_status()
            # ping.start()
            time.sleep(5)
            # ping.terminate()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            # ping.terminate()
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            # self.enable_disable_pcie_ports(False, self.pcie_ports)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_low_power_02_009(self):
        """
        1.电脑整机休眠
        2.唤醒电脑
        3.MBIM拨号
        4.电脑再次整机休眠，查看电源状态cat /sys/kernel/debug/mhi_sm/stats
        5.观察睡眠时的耗流
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.close_all_ports()
            all_logger.info('笔电进入S4休眠')
            self.enter_S3_S4_sleep()
            time.sleep(120)  # 等待PC恢复正常
            self.mbim_connect_and_check()
            all_logger.info('等待5s')
            time.sleep(5)
            all_logger.info('笔电再次进入S4休眠')
            self.enter_S3_S4_sleep()
            time.sleep(60)
            all_logger.info('进入DEBUG口查看，期望已经入睡眠')
            self.debug_check(True)
            all_logger.info('等待300s待其稳定')
            time.sleep(300)  # 等待PC恢复正常
            all_logger.info('开始检查睡眠后耗流值')
            self.get_current_volt()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.mbim_disconnect_and_check()
            self.open_all_ports()
            time.sleep(3)
            self.disable_low_power_registry()
            # self.close_lowpower()
            all_logger.info('关闭设备管理器')
            self.close_devices_page()
            self.windows_api.press_esc()
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    params_dict = {
        "at_port": 'COM3',
        "dm_port": 'COM5',
        "nema_port": 'COM4',
        "debug_port": 'COM14',
        "mbim_pcie_driver_name": 'Quectel RM520NGLAP',
        "phone_number": '18656504506',
        "power_port": 'COM13'
    }
    # 18110921823
    # 13225513715
    test = WindowsLapTopLowPower(**params_dict)
    # test.windows_laptop_low_power_01_001()  # 调试
    # test.windows_laptop_low_power_01_002()  # p0
    # test.windows_laptop_low_power_01_003()  # p0
    # test.windows_laptop_low_power_01_004()  # p0
    # test.windows_laptop_low_power_01_005()  # p0
    # test.windows_laptop_low_power_01_006()  # p0
    # test.windows_laptop_low_power_01_007()  # p0

    test.windows_laptop_low_power_02_002()  # p1 ok
    # test.windows_laptop_low_power_02_003()  # p1 ok
    # test.windows_laptop_low_power_02_004()  # p1 ok
    # test.windows_laptop_low_power_02_005()  # P1 ok
    # test.windows_laptop_low_power_02_006()  # P1 ok
    # test.windows_laptop_low_power_02_007()  # P1 ok
    # test.windows_laptop_low_power_02_008()  # P1 ok
    # test.windows_laptop_low_power_02_009()  # P1 ok

    """
    P0：
    Lowpower(PCIE)_SDX55-01-002
    Lowpower(PCIE)_SDX55-01-003
    Lowpower(PCIE)_SDX55-01-004
    Lowpower(PCIE)_SDX55-01-005
    Lowpower(PCIE)_SDX55-01-006
    Lowpower(PCIE)_SDX55-01-007

    P1：
    Lowpower(PCIE)_SDX55-02-002
    Lowpower(PCIE)_SDX55-02-003
    Lowpower(PCIE)_SDX55-02-004
    Lowpower(PCIE)_SDX55-02-005
    Lowpower(PCIE)_SDX55-02-006
    Lowpower(PCIE)_SDX55-02-007
    Lowpower(PCIE)_SDX55-02-008
    Lowpower(PCIE)_SDX55-02-009
    """
