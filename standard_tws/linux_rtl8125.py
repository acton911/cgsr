import subprocess
from utils.cases.linux_rtl8125_manager import LinuxRTL8125Manager
import time
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxRTL8125Error
from utils.functions.iperf import iperf
from utils.functions.decorators import startup_teardown


class LinuxRTL8125(LinuxRTL8125Manager):

    @startup_teardown()
    def test_linux_rtl8125_1(self):
        """
        默认值确认
        """
        try:
            time.sleep(60)  # 防止发AT口还未加载、发AT不生效等问题发生
            self.driver.check_usb_driver()
            self.qmapwac_default_check()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()

    @startup_teardown()
    def test_linux_rtl8125_2(self):
        """
        测试RTL8125驱动加载及自动拨号
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            self.check_rtl8125_pci()
            self.check_network_card()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()

            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            self.cfun04_check_network()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_3(self):
        """
        拨号，打流30M 5分钟
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_4(self):
        """
        模组重启后自动拨号
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            all_logger.info('开始重启拨号测试')
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_5(self):
        """
        解PIN后自动拨号
        """
        try:
            self.driver.check_usb_driver()
            self.at_handler.send_at('AT+CLCK="SC",1,"1234"')
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(20)
            self.cfun04_check_network()
            self.at_handler.send_at('AT+CPIN=1234')
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"')
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"')
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_6(self):
        """
        RTL8125 CFUN0/1切换拨号
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(20)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            self.at_handler.send_at('AT+CFUN=0', 0.6)
            self.cfun04_check_network()
            self.at_handler.send_at('AT+CFUN=1', 0.6)
            time.sleep(20)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.at_handler.send_at('AT+CFUN=1', 0.6)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_7(self):
        """
        RTL8125 CFUN4/1切换拨号
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(20)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            self.at_handler.send_at('AT+CFUN=4', 0.6)
            self.cfun04_check_network()
            self.at_handler.send_at('AT+CFUN=1', 0.6)
            time.sleep(20)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.at_handler.send_at('AT+CFUN=1', 0.6)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_8(self):
        """
        来电来短信测试
        """
        try:
            self.driver.check_usb_driver()
            self.enter_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(30)
            self.at_handler.check_network()
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            time.sleep(60)
            self.ping_status_rtl8125()
            self.hang_up_after_system_dial(wait_time=10)
            self.ping_status_rtl8125()
            self.send_msg()
            self.ping_status_rtl8125()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_9(self):
        """
        硬件加速开启的基线需要验证
        开mPDN-vlan下，后面2路同时测试速率之和不能比第一路单独测速低很多，验证多路加速功能有效
        """
        try:
            self.enter_rtl8125_mode()
            self.at_handler.send_at("AT+QMAPWAC=0", 0.6)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)
            self.at_handler.check_network()
            self.check_rtl8125_pci()

            self.mpdn_set_3_way_apn()
            self.mpdn_query_vlan_activations()
            time.sleep(5)
            self.mpdn_add_2_vlan_enable()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(15)
            self.mpdn_query_vlan_activations()

            self.mpdn_query_rule()
            self.mpdn_set_3_rule(self.get_trl8125_mac_address())
            time.sleep(20)
            self.mpdn_query_rule()
            rule_status = self.mpdn_check_status()
            if rule_status == '0':
                raise LinuxRTL8125Error('Three-way does not have all dials!')

            self.mpdn_add_2_pc_vlan()

            self.mpdn_pc_get_ip_connect()
            self.mpdn_route_set()
            self.mpdn_ping_check_3_way()

            s0 = self.speedtest(network_card=self.rtl8125_ethernet_name)
            s1 = self.speedtest(network_card='{}.1'.format(self.rtl8125_ethernet_name))
            s2 = self.speedtest(network_card='{}.2'.format(self.rtl8125_ethernet_name))
            if s0 < s1 + s2:
                raise LinuxRTL8125Error('速率异常，第1路速率小于第2路和第3路速率之和，请确认！')
            else:
                all_logger.info('第1路速率大于第2路和第3路速率之和，正常！')
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)

    @startup_teardown()
    def test_linux_rtl8125_10(self):
        """
        关闭多路拨号
        """
        try:
            self.mpdn_del_rule()
            self.mpdn_query_rule()

            self.mpdn_dis_vlan()
            self.mpdn_query_vlan_activations()
        finally:
            # disable_network_card(self.rtl8125_ethernet_name)
            # enable_network_card_and_check(self.pc_ethernet_name)
            self.exit_rtl8125_mode()
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)


if __name__ == "__main__":
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB0',
        'pc_ethernet_name': 'eth0',
        'phone_number': '17356527952',
    }

    LinuxRTL8125 = LinuxRTL8125(**param_dict)
    LinuxRTL8125.test_linux_rtl8125_1()
    LinuxRTL8125.test_linux_rtl8125_2()
    LinuxRTL8125.test_linux_rtl8125_3()
    LinuxRTL8125.test_linux_rtl8125_4()
    LinuxRTL8125.test_linux_rtl8125_5()
    LinuxRTL8125.test_linux_rtl8125_6()
    LinuxRTL8125.test_linux_rtl8125_7()
    LinuxRTL8125.test_linux_rtl8125_8()
    LinuxRTL8125.test_linux_rtl8125_9()
    LinuxRTL8125.test_linux_rtl8125_10()

    """
    params_dict = param_dict
    func = 'test_linux_rtl8125_1'
    exec("LinuxRTL8125(**{}).{}()".format(params_dict, func))
    """
