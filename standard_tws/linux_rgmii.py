from utils.functions.decorators import startup_teardown
from utils.cases.linux_rgmii_manager import LinuxRGMIIManager
import time
from utils.logger.logging_handles import all_logger
from utils.functions.debug_exec import DebugPort
from utils.exception.exceptions import LinuxRGMIIError
from utils.functions.linux_api import PINGThread
import os
import sys
import subprocess
from utils.functions.iperf import iperf
import traceback


class LinuxRGMII(LinuxRGMIIManager):

    @startup_teardown(startup=['set_usbnet_0'])
    def test_linux_rgmii_01_001(self):
        self.qeth_attr_check()

    @startup_teardown()
    def test_linux_rgmii_01_002(self):
        self.qeth_check_default()

    @startup_teardown()
    def test_linux_rgmii_01_003(self):
        self.rgmii(status="enable", voltage=1)  # only open Common RGMII
        try:
            # 此处不调用linux_api的ping_get_connect_status，因为ping了特殊的IP地址
            ipv4 = self.get_ipv4_with_timeout()
            ping = subprocess.getoutput("ping 192.168.225.1 -c 10 -I {}".format(ipv4))
            all_logger.info(ping)
            if '100% packet loss' in ping:
                raise LinuxRGMIIError("fail to ping 192.168.225.1")
        finally:
            self.rgmii(status="disable", voltage=1)  # close common RGMII

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_004(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=0)  # Common
            self.common_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=0)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_005(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=0)  # Common
            self.common_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=0)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_006(self):
        self.at_handler.bound_network('SA')
        try:
            self.rgmii(status="enable", voltage=1, mode=0)  # Common
            self.common_connect_check()
            iperf(bandwidth='30M', times=300)
        finally:
            self.rgmii(status="disable", voltage=1, mode=0)  # Common

    @startup_teardown()
    def test_linux_rgmii_01_007(self):
        self.ipptmac_check_default()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_008(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)  # IPPassthrough
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown()
    def test_linux_rgmii_01_009(self):
        self.ipptmac_set_check()
        self.at_handler.check_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_010(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_01_011(self):
        self.at_handler.bound_network('SA')
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
            iperf(bandwidth='30M', times=300)
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_001(self):
        seq = 2
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_002(self):
        seq = 3
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_003(self):
        seq = 4
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_004(self):
        seq = 5
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_005(self):
        seq = 6
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_006(self):
        seq = 7
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_007(self):
        seq = 8
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_rgmii_02_008(self):
        seq = 1
        self.set_apn(seq)
        try:
            self.rgmii(status="enable", voltage=1, mode=1, profile_id=seq)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1, profile_id=seq)

    @startup_teardown()
    def test_linux_rgmii_02_009(self):
        debug_port = DebugPort(self.debug_port)
        debug_port.setDaemon(True)
        debug_port.start()

        try:
            old_mac = self.at_get_mac_address()
            all_logger.info('old MAC address is : {}'.format(old_mac))
            self.sitch_fastboot_erase_rawdata()
            erase_status = debug_port.get_latest_data()
            all_logger.info('erase status: {}'.format(erase_status))
            if 'block error' in erase_status:
                raise LinuxRGMIIError('erase rawdata failed: {}'.format(erase_status))
            self.fastboot_reboot()

            all_logger.info("wait 20 seconds.")
            time.sleep(20)

            # check mac
            new_mac = self.at_get_mac_address()
            debug_mac = debug_port.exec_command("ifconfig bridge0 | grep HWaddr")
            all_logger.info('\nold_mac: {}\nnew_mac: {}\ndebug_mac: {}'.format(old_mac, new_mac, debug_mac))
            if new_mac not in debug_mac:
                raise LinuxRGMIIError('AT+QETH="MAC_ADDRESS" MAC not equal to debug port bridge0 mac.')

            all_logger.info('\nold MAC address: {}\nnew MAC address: {}'.format(old_mac, new_mac))
            if old_mac == new_mac:
                raise LinuxRGMIIError('MAC address not change after erase rawdata partition.')

            self.rgmii(status="enable", voltage=1, mode=1)  # Common
            self.ip_pass_through_connect_check()

        finally:
            self.rgmii(status="disable", voltage=1, mode=1)
            debug_port.close_debug()

    @startup_teardown(startup=['at_handler', 'set_sim_pin'],
                      teardown=['at_handler', 'sin_pin_remove'])
    def test_linux_rgmii_02_010(self):
        self.at_handler.send_at('AT+CFUN=0', 15)
        time.sleep(5)
        self.at_handler.send_at("AT+CFUN=1", 15)
        data = self.rgmii(status="enable", voltage=1, mode=1, check=False)
        if "ERROR"  in data:
            raise LinuxRGMIIError("RMGII return Error after SIM lock")
        self.at_handler.at_unlock_sim_pin(1234)
        self.at_handler.check_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_02_011(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)  # Common
            self.ip_pass_through_connect_check()
            self.rgmii(status="disable", voltage=1, check=False)
            self.rgmii(status="enable", voltage=1, check=False)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)  # Common

    @startup_teardown()
    def test_linux_rgmii_02_012(self):
        self.rgmii(status="enable", voltage=1, mode=1)

        try:
            self.ip_pass_through_connect_check()
            self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name, flag=False)

            #all_logger.info('ifconfig {} down'.format(self.rgmii_ethernet_name))
            #os.popen('ifconfig {} down'.format(self.rgmii_ethernet_name)).read()
            #all_logger.info('wait 3 seconds')
           # time.sleep(3)
            #all_logger.info('ifconfig {} up'.format(self.rgmii_ethernet_name))
           # os.popen('ifconfig {} up'.format(self.rgmii_ethernet_name)).read()


            self.restart_rgmii_network_card()
            all_logger.info('wait 10 seconds')
            time.sleep(10)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_02_013(self):
        try:
            for i in range(10):
                self.rgmii(status="enable", voltage=1, mode=1)
                self.ip_pass_through_connect_check()
                self.at_handler.send_at('AT+CFUN=1,1', 3)
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                self.at_handler.check_urc()
                self.at_handler.check_network()
                time.sleep(5)
                self.restart_rgmii_network_card()# 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
                self.print_ip()
                all_logger.info('wait 5 seconds')
                time.sleep(5)
                self.restart_rgmii_network_card()
                self.print_ip()
                time.sleep(5)
                self.restart_rgmii_network_card()
                time.sleep(5)
                self.ip_pass_through_connect_check()
                self.rgmii(status="disable", voltage=1, mode=1)
        finally:
            all_logger.info('禁用启用10次已完成')

    @startup_teardown()
    def test_linux_rgmii_02_014(self):
        self.rgmii(status="enable", voltage=1, mode=1)

        try:
            self.ip_pass_through_connect_check()

            self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name, flag=False)

            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(5)
            self.restart_rgmii_network_card()  # 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
            self.print_ip()
            all_logger.info('wait 5 seconds')
            time.sleep(5)
            self.restart_rgmii_network_card()
            self.print_ip()
            time.sleep(5)
            self.restart_rgmii_network_card()
            self.print_ip()
            time.sleep(5)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_03_001(self):
        self.dmz_default_check()

    @startup_teardown()
    def test_linux_rgmii_03_004(self):
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            ipv4 = self.get_network_card_ipv4(www=True)
            set_dmz = self.at_handler.send_at('AT+QDMZ=1,4,{}'.format(ipv4), 3)
            if 'OK' not in set_dmz:
                raise LinuxRGMIIError("fail to set IPv4 DMZ")
            get_dmz = self.at_handler.send_at('AT+QDMZ', 3)
            if '1,4,{}'.format(ipv4) not in get_dmz:
                raise LinuxRGMIIError("fail to check DMZ after set")

            ipv6 = self.get_network_card_ipv6()
            if '\n' in ipv6:
                ipv6 = ipv6.split("\n")[0]
            set_dmz = self.at_handler.send_at('AT+QDMZ=1,6,{}'.format(ipv6), 3)
            if 'OK' not in set_dmz:
                raise LinuxRGMIIError("fail to set IPv6 DMZ")
            get_dmz = self.at_handler.send_at('AT+QDMZ', 3)
            if '1,6,{}'.format(ipv6) not in get_dmz:
                raise LinuxRGMIIError("fail to check DMZ after set")

            qdmz = self.at_handler.send_at('AT+QDMZ=0', 3)
            if 'OK' not in qdmz:
                raise LinuxRGMIIError("fail to reset DMZ USE AT+QDMZ=0")

            self.dmz_default_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_03_005(self):
        self.at_handler.cfun()
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
            self.at_handler.cfun0()

            all_logger.info("wait 5 seconds")
            time.sleep(5)

            self.at_handler.cfun1()
            self.at_handler.check_network()

            all_logger.info("wait 10 seconds")
            time.sleep(10)
            self.ip_pass_through_connect_check()

            self.at_handler.cfun4()

            all_logger.info("wait 5 seconds")
            time.sleep(5)

            self.at_handler.cfun1()
            self.at_handler.check_network()

            all_logger.info("wait 10 seconds")
            time.sleep(10)
            self.ip_pass_through_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_03_007(self):
        # 进行打电话，接短信测试
        self.at_handler.bound_network('LTE')
        ping = None
        exc_type = None
        exc_value = None
        try:
            # 拨号并检查
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            # 后台ping，并且拨通电话
            ping = PINGThread(times=150, network_card_name=self.rgmii_ethernet_name)
            ping.setDaemon(True)
            ping.start()
            self.hang_up_after_system_dial(10)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if ping:
                ping.terminate()
            self.rgmii(status="disable", voltage=1, mode=1)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.at_handler.bound_network('SA')

    @startup_teardown()
    def test_linux_rgmii_03_009(self):
        # 进行打电话，接短信测试
        self.at_handler.bound_network('LTE')
        ping = None
        exc_type = None
        exc_value = None
        try:
            # 拨号并检查
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            # 后台ping，并且发送短信
            ping = PINGThread(times=150, network_card_name=self.rgmii_ethernet_name)
            ping.setDaemon(True)
            ping.start()
            self.send_msg()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if ping:
                ping.terminate()
            self.rgmii(status="disable", voltage=1, mode=1)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.at_handler.bound_network('SA')

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_04_001(self):
        self.at_handler.bound_5G_network()
        try:
            self.rgmii(status="enable", voltage=1, mode=0)  # Common
            self.common_connect_check()
        finally:
            self.rgmii(status="disable", voltage=1, mode=0)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_04_002(self):
        self.at_handler.bound_network('NSA')
        try:
            self.rgmii(status="enable", voltage=1, mode=0)  # Common
            self.common_connect_check()
            iperf(bandwidth='30M', times=300)
        finally:
            self.rgmii(status="disable", voltage=1, mode=0)  # Common

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_04_003(self):
        self.at_handler.bound_network('NSA')
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
            iperf(bandwidth='30M', times=300)
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_rgmii_04_008(self):
        self.qeth_an_check_default()

    @startup_teardown()
    def test_linux_rgmii_04_009(self):
        try:
            self.at_handler.check_network()
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            self.qeth_speed_check_default()
            speed = self.ethtool_get_speed()
            all_logger.info('ethtool get {} speed is {}'.format(self.rgmii_ethernet_name, speed))
            if speed != 1000:
                raise LinuxRGMIIError("eth0 speed check failed.")
            speed = self.speedtest(self.rgmii_ethernet_name)
            if speed < 100:
                raise LinuxRGMIIError('eth0 speed 1000Mbps but speedtest speed is {} Mbps'.format(speed))
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_04_010(self):
        try:
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()
            self.at_handler.send_at('AT+CFUN=1,1', 3)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(5)
            self.restart_rgmii_network_card() # 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
            self.print_ip()
            all_logger.info('wait 5 seconds')
            time.sleep(5)
            self.restart_rgmii_network_card()
            self.print_ip()
            time.sleep(5)
            self.restart_rgmii_network_card()
            time.sleep(5)
            self.ip_pass_through_connect_check()
            speed = self.ethtool_get_speed()
            all_logger.info('ethtool get {} speed is {}'.format(self.rgmii_ethernet_name, speed))
            if speed != 1000:
                raise LinuxRGMIIError("eth0 speed check failed.")
            speed = self.speedtest(self.rgmii_ethernet_name)
            if speed < 100:
                raise LinuxRGMIIError('eth0 speed 1000Mbps but speedtest speed is {} Mbps'.format(speed))
        finally:
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_04_011(self):
        try:
            aim_speed = 100
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            self.ethtool_set_speed(aim_speed)
            self.qeth_dm_check_default()

            self.at_handler.send_at('AT+CFUN=1,1', 3)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(5)
            self.restart_rgmii_network_card()  # 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
            all_logger.info('wait 5 seconds')
            time.sleep(5)
            self.restart_rgmii_network_card()
            time.sleep(5)
            self.restart_rgmii_network_card()
            time.sleep(5)
            self.ip_pass_through_connect_check()
            speed = self.ethtool_get_speed()
            all_logger.info('ethtool get {} speed is {}'.format(self.rgmii_ethernet_name, speed))
            if speed != aim_speed:
                raise LinuxRGMIIError("eth0 speed check failed.")

            speed = self.speedtest(self.rgmii_ethernet_name)
            if speed > aim_speed:
                raise LinuxRGMIIError('eth0 speed is {} Mbps but speedtest download speed is {} Mbps'.format(aim_speed, speed))
        finally:
            self.ethtool_set_speed(1000)
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_04_012(self):
        try:
            aim_speed = 10
            self.rgmii(status="enable", voltage=1, mode=1)
            self.ip_pass_through_connect_check()

            self.ethtool_set_speed(aim_speed)
            self.qeth_dm_check_default()

            self.at_handler.send_at('AT+CFUN=1,1', 3)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(5)
            self.restart_rgmii_network_card()  # 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
            all_logger.info('wait 5 seconds')
            time.sleep(5)
            self.restart_rgmii_network_card()
            time.sleep(5)
            self.restart_rgmii_network_card()
            time.sleep(5)
            self.ip_pass_through_connect_check()
            speed = self.ethtool_get_speed()
            all_logger.info('ethtool get {} speed is {}'.format(self.rgmii_ethernet_name, speed))
            if speed != aim_speed:
                raise LinuxRGMIIError("eth0 speed check failed.")

            speed = self.speedtest(self.rgmii_ethernet_name)
            if speed > aim_speed:
                raise LinuxRGMIIError('eth0 speed is {} Mbps but speedtest download speed is {} Mbps'.format(aim_speed, speed))
        finally:
            self.ethtool_set_speed(1000)
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_04_013(self):
        try:
            an = self.at_handler.send_at('AT+QETH="an","off"', 3)
            if 'OK' not in an:
                raise LinuxRGMIIError('AT+QETH="an","off" not return OK.')

            speed = self.at_handler.send_at('AT+QETH="SPEED"', 3)
            if "1000" not in speed:
                raise LinuxRGMIIError('AT+QETH="SPEED"  speed is not 1000 Mbps.')

            self.rgmii(status="enable", voltage=1, mode=1)
           # self.ip_pass_through_connect_check()

            self.ethtool_set_speed(1000)

            all_logger.info('wait 10 seconds')
            time.sleep(10)

            speed = self.ethtool_get_speed()
            if speed != 1000:
                raise LinuxRGMIIError('ethtool set speed to 1000 Mbps failed.')

            self.speedtest(self.rgmii_ethernet_name)
            if speed < 100:
                raise LinuxRGMIIError('eth0 speed is 1000 Mbps but speedtest download speed is {} Mbps'.format(speed))
        finally:
            self.ethtool_set_speed_autonegoff(100)
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown()
    def test_linux_rgmii_04_014(self):
        try:
            aim_speed = 100
            self.eth_set_get_speed(aim_speed)

            self.rgmii(status="enable", voltage=1, mode=1)

            self.ethtool_set_speed_autonegoff(aim_speed)

            all_logger.info('wait 10 seconds')
            time.sleep(10)

            #self.ip_pass_through_connect_check()

            speed = self.ethtool_get_speed()
            if speed != aim_speed:
                raise LinuxRGMIIError('ethtool set speed to 1000 Mbps failed.')

            self.speedtest(self.rgmii_ethernet_name)
            if speed > aim_speed:
                raise LinuxRGMIIError('eth0 speed is {} Mbps but speedtest download speed is {} Mbps'.format(aim_speed, speed))
        finally:
            self.ethtool_set_speed_autonegoff(10)
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown(teardown=['eth_set_get_speed_1000'])
    def test_linux_rgmii_04_015(self):
        try:
            aim_speed = 10
            self.eth_set_get_speed(aim_speed)

            self.rgmii(status="enable", voltage=1, mode=1)

            self.ethtool_set_speed_autonegoff(aim_speed)

            all_logger.info('wait 10 seconds')
            time.sleep(10)

           # self.ip_pass_through_connect_check()

            speed = self.ethtool_get_speed()
            if speed != aim_speed:
                raise LinuxRGMIIError('ethtool set speed to 1000 Mbps failed.')

            self.speedtest(self.rgmii_ethernet_name)
            if speed > aim_speed:
                raise LinuxRGMIIError('eth0 speed is {} Mbps but speedtest download speed is {} Mbps'.format(aim_speed, speed))
        finally:
            self.ethtool_set_speed_autonegon(1000)
            self.eth_speed_reset()
            self.rgmii(status="disable", voltage=1, mode=1)

    @startup_teardown(teardown=['reset_usbnet_0'])
    def test_linux_rgmii_04_016(self):
        self.at_handler.send_at('AT+QCFG="USBNET",1', timeout=3)
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        all_logger.info('wait 10 seconds')
        time.sleep(10)  # 停一会再发指令，否则会返回ERROR
        self.at_handler.check_network()
        self.modprobe_driver()
        self.check_ecm_driver()
        self.linux_api.ping_get_connect_status(network_card_name='usb0')
        try:
            data = self.rgmii(status="enable", voltage=1, mode=1,check=False)
            if "ERROR"  in data:
                raise LinuxRGMIIError("RMGII not return Error after ECM")
            all_logger.info("运行正常")
            time.sleep(10)
           # self.at_handler.send_at('at+qeth="RGMII","enable",1,1,5', timeout=30)
          #  all_logger.info("wait 10 seconds")
           # time.sleep(10)
            self.ip_pass_through_connect_check()
            self.linux_api.ping_get_connect_status(network_card_name='usb0')
          #  self.at_handler.send_at('at+qeth="RGMII","disable",1,1,5', timeout=30)
        finally:
            self.linux_api.ping_get_connect_status(network_card_name='usb0')
            self.rgmii(status="disable", voltage=1, mode=1)


if __name__ == "__main__":
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB0',
        'pc_ethernet_name': 'enp1s0',  # 系统内网网卡
        'rgmii_ethernet_name': 'eno1',  # rgmii 网线连接的网卡名称
        'phone_number': '15256905471'
    }
    linux_rgmii = LinuxRGMII(**param_dict)
    # linux_rgmii.test_linux_rgmii_01_001()
    # linux_rgmii.test_linux_rgmii_01_002()
    # linux_rgmii.test_linux_rgmii_01_003()
    # linux_rgmii.test_linux_rgmii_01_004()
    # linux_rgmii.test_linux_rgmii_01_005()
    # linux_rgmii.test_linux_rgmii_01_006()
    # linux_rgmii.test_linux_rgmii_01_007()
    # linux_rgmii.test_linux_rgmii_01_008()
    # linux_rgmii.test_linux_rgmii_01_009()
    # linux_rgmii.test_linux_rgmii_01_010()
    # linux_rgmii.test_linux_rgmii_01_011()
    # linux_rgmii.test_linux_rgmii_02_001()
    # linux_rgmii.test_linux_rgmii_02_002()
    # linux_rgmii.test_linux_rgmii_02_003()
    # linux_rgmii.test_linux_rgmii_02_004()
    # linux_rgmii.test_linux_rgmii_02_005()
    # linux_rgmii.test_linux_rgmii_02_006()
    # linux_rgmii.test_linux_rgmii_02_007()
    # linux_rgmii.test_linux_rgmii_02_008()
    # linux_rgmii.test_linux_rgmii_02_009()
    # linux_rgmii.test_linux_rgmii_02_010()
    # linux_rgmii.test_linux_rgmii_02_011()
    # linux_rgmii.test_linux_rgmii_02_012()
    # linux_rgmii.test_linux_rgmii_02_013()
    # linux_rgmii.test_linux_rgmii_02_014()
    # linux_rgmii.test_linux_rgmii_03_001()
    # linux_rgmii.test_linux_rgmii_03_004()
    # linux_rgmii.test_linux_rgmii_03_005()
    # linux_rgmii.test_linux_rgmii_03_007()
    # linux_rgmii.test_linux_rgmii_03_009()
    # linux_rgmii.test_linux_rgmii_04_002()
    # linux_rgmii.test_linux_rgmii_04_003()
    # linux_rgmii.test_linux_rgmii_04_008()
    # linux_rgmii.test_linux_rgmii_04_009()
    # linux_rgmii.test_linux_rgmii_04_010()
    # linux_rgmii.test_linux_rgmii_04_011()
    # linux_rgmii.test_linux_rgmii_04_012()
    # linux_rgmii.test_linux_rgmii_04_013()
    # linux_rgmii.test_linux_rgmii_04_014()
    # linux_rgmii.test_linux_rgmii_04_015()
    # linux_rgmii.test_linux_rgmii_04_016()

    all_logger.info('End test.')
