import sys
import time
import traceback
import subprocess
from utils.functions.decorators import startup_teardown
from utils.cases.windows_netlight_manager import WindowsNetLightManager
from utils.logger.logging_handles import all_logger
from utils.functions.linux_api import LinuxAPI, QuectelCMThread


class WindowsNetLight(WindowsNetLightManager):

    def test_netlight_01_001(self):
        """
        RM系列测试
        未插sim卡，确认网络灯的状态
        """
        if self.module_typerm():    # 判断若是RG项目则直接返回
            return True
        try:
            self.open_hot_plug()    # 开启热插拔
            self.gpio.set_sim1_det_low_level()
            time.sleep(20)
            self.check_wwanled_alwaysdown()
        finally:
            self.gpio.set_sim1_det_high_level()  # 恢复引脚

    def test_netlight_01_002(self):
        """
        RM系列测试
        未插sim卡，开机初始化后，执行at+cfun=1等操作，确认网络灯的状态
        """
        if self.module_typerm():  # 判断若是RG项目则直接返回
            return True
        try:
            self.gpio.set_sim1_det_low_level()
            time.sleep(10)
            self.at_handle.send_at('AT+CFUN=1', 10)
            time.sleep(10)
            self.check_wwanled_alwaysdown()
        finally:
            self.gpio.set_sim1_det_high_level()  # 恢复引脚

    def test_netlight_02_001(self):
        """
        RM系列测试
        插入sim卡，开机后，确认网络灯的状态
        """
        if self.module_typerm():  # 判断若是RG项目则直接返回
            return True
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        time.sleep(20)
        self.at_handle.check_network()
        self.check_wwanled_alwaysbright()

    def test_netlight_02_002(self):
        """
        RM系列测试
        插入sim卡，开机初始化到出现cpin ready，再执行at+cfun=1，确认网络灯的状态
        """
        if self.module_typerm():  # 判断若是RG项目则直接返回
            return True
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        time.sleep(20)
        self.at_handle.send_at('AT+CFUN=1', 10)
        time.sleep(20)
        self.at_handle.check_network()
        self.check_wwanled_alwaysbright()

    def test_netlight_02_003(self):
        """
        RM系列测试
        执行at+cfun=0，确认网络灯的状态
        """
        if self.module_typerm():  # 判断若是RG项目则直接返回
            return True
        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=0', 10)
            time.sleep(20)
            self.check_wwanled_alwaysdown()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 10)

    def test_netlight_02_004(self):
        """
        RM系列测试
        执行at+cfun=4，确认网络灯的状态
        """
        if self.module_typerm():  # 判断若是RG项目则直接返回
            return True
        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=4', 10)
            time.sleep(20)
            self.check_wwanled_alwaysdown()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 10)

    def test_netlight_03_001(self):
        """
        RG系列测试
        插SIM卡，模块重启后，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        time.sleep(20)
        self.check_and_set_pcie_data_interface()
        self.at_handle.send_at('AT+QCFG="USBNET",0', timeout=3)
        self.modprobe_driver()
        self.load_wwan_driver()
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=60)
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()
        self.at_handle.check_network()
        time.sleep(10)
        self.check_modelight_alwaysbright()

    def test_netlight_04_001(self):
        """
        RG系列测试
        不插SIM卡开机初始化后（不进行任何操作），确认网络灯的状态
        需打开热插拔功能
        """
        if self.module_typerg():
            return True
        try:
            self.open_hot_plug()
            self.gpio.set_sim1_det_low_level()
            time.sleep(20)
            self.check_modelight_alwaysdown()
        finally:
            self.gpio.set_sim1_det_high_level()

    def test_netlight_04_002(self):
        """
        RG系列测试
        不插卡
        开机初始化后,执行at+cfun=0，确认网络灯的状态
        执行at+cfun=1（进入搜网状态），确认网络灯的状态
        """
        if self.module_typerg():
            return True
        try:
            self.gpio.set_sim1_det_low_level()
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=0', 10)
            time.sleep(10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysdown()
            self.at_handle.send_at('AT+CFUN=1', 10)
            time.sleep(10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_longdownshortbright()
        finally:
            self.gpio.set_sim1_det_high_level()

    def test_netlight_04_003(self):
        """
        RG系列测试
        不插SIM卡
        在搜网状态下，执行at+cfun=4，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        try:
            self.gpio.set_sim1_det_low_level()
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=4', 10)
            time.sleep(10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysdown()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 10)
            self.gpio.set_sim1_det_high_level()

    def test_netlight_04_004(self):
        """
        RG系列测试
        不插SIM卡
        搜网状态下,拨打紧急电话  ATD112;确认网络灯的状态
        之后使用ATH挂断电话,确认网络灯状态
        """
        if self.module_typerg():
            return True
        try:
            self.gpio.set_sim1_det_low_level()
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=1', 10)
            self.at_handle.send_at('ATD112;', 10)
            time.sleep(4)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysbright()
            self.at_handle.send_at('ATH', 10)
            time.sleep(10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_longdownshortbright()
        finally:
            self.gpio.set_sim1_det_high_level()

    def test_netlight_05_002(self):
        """
        RG系列测试
        插入SIM卡
        开机后 执行at+cfun=0，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        try:
            self.gpio.set_sim1_det_high_level()
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.send_at('AT+CFUN=0', 10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysdown()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 10)

    def test_netlight_05_003(self):
        """
        RG系列测试
        插入SIM卡
        开机后 执行at+cfun=4，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(10)
            self.at_handle.send_at('AT+CFUN=4', 10)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysdown()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 10)

    def test_netlight_05_004(self):
        """
        RG系列测试
        插入SIM卡
        模块开机，搜网状态驻网成功，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(20)
            self.at_handle.check_network()
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        finally:
            self.load_qmi_wwan_q_drive()

    @startup_teardown()
    def test_netlight_06_001(self):
        """
        RG系列测试
        插入SIM卡
        联通卡固定网WCDMA only找网方式下找网拨号，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        self.at_handle.bound_network('WCDMA')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_modelight_alwaysbright()
            self.check_statuslight_blink()
            time.sleep(5)
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_netlight_06_002(self):
        """
        RG系列测试
        插入SIM卡
        联通卡固定网LTE only找网方式下找网拨号，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        self.at_handle.bound_network('LTE')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_modelight_alwaysbright()
            self.check_statuslight_blink()
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_netlight_06_003(self):
        """
        RG系列测试
        插入SIM卡
        联通卡固定网NSA only找网方式下找网拨号，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_modelight_alwaysbright()
            self.check_statuslight_blink()
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_netlight_06_004(self):
        """
        RG系列测试
        插入SIM卡
        联通卡固定网SA only找网方式下找网拨号，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        self.at_handle.bound_network('SA')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_modelight_alwaysbright()
            self.check_statuslight_blink()
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_netlight_06_006(self):
        """
        RG系列测试
        ATD打正常电话，然后挂断，确认网络灯的状态
        """
        if self.module_typerg():
            return True

        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(10)
            self.at_handle.send_at('AT+CFUN=1', 10)
            self.at_handle.send_at('ATD112;', 10)
            time.sleep(4)
            self.check_modelight_alwaysdown()
            self.check_statuslight_alwaysbright()
            self.at_handle.send_at('ATH', 10)
        finally:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(10)
