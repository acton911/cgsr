import random
import subprocess
import threading
import time
from collections import deque
from threading import Thread
import requests
import serial
from icmplib import ping, multiping
from utils.functions.getpassword import getpass
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxETHError
from utils.functions.linux_api import LinuxAPI
import re


class LinuxETHManager(Exception):
    def __init__(self, at_port, dm_port, debug_port, rgmii_ethernet_name, rtl8125_ethernet_name, pc_ethernet_name,
                 phone_number, eth_test_mode):
        self.linux_api = LinuxAPI()
        self.at_port = at_port
        self.at_handler = ATHandle(self.at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.rgmii_ethernet_name = rgmii_ethernet_name
        self.pc_ethernet_name = pc_ethernet_name
        self.rtl8125_ethernet_name = rtl8125_ethernet_name
        self.debug_port = debug_port
        self.default_apns = None
        self.linux_api = LinuxAPI()
        self.phone_number = phone_number
        self.eth_test_mode = eth_test_mode
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.return_qgmr = self.at_handler.send_at('AT+QGMR', 0.6)
        self.eth_test_mode_list = {'2': 'RGMII8035\8211', '3': 'RTL8125', '4': 'RTL8168', '5': 'QCA8081'}
        self.gpio = GPIO()
        self.IS_BL_version = True if '_BL_' in self.return_qgmr else False
        self.Is_OCPU_version = True if 'OCPU' in self.return_qgmr else False

    def check_ipp_ant_default_and_set(self):

        ipp_nat_before = self.at_handler.send_at('AT+QMAP="IPPT_NAT"', 3)
        if '+QMAP: "IPPT_NAT",1' not in ipp_nat_before:
            raise LinuxETHError(f"查询默认是否启用NAT功能异常!{ipp_nat_before}")

        return_ipp_nat_set = self.at_handler.send_at('AT+QMAP="IPPT_NAT",0', 6)
        if "OK" not in return_ipp_nat_set:
            raise LinuxETHError(f'AT+QMAP="IPPT_NAT",0设置异常！：{return_ipp_nat_set}')

        ipp_nat_set = self.at_handler.send_at('AT+QMAP="IPPT_NAT"')
        if '+QMAP: "IPPT_NAT",0' not in ipp_nat_set:
            raise LinuxETHError(f"配置NAT功能后查询信息异常!{ipp_nat_set}")

    @staticmethod
    def rgmii_at_client_send_at(tool_path, at_commd):
        return_cops = subprocess.getoutput(f'/{tool_path} {at_commd}')
        all_logger.info(f'/{tool_path} {at_commd} : {return_cops}')
        return return_cops

    def two_way_dial_set(self, eth_test_mode):
        now_network_card_name = self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name
        # modprobe 8021q
        return_8021q = subprocess.getoutput('modprobe 8021q')
        all_logger.info('加载vlan模块modprobe 8021q:{}'.format(return_8021q))

        # ifconfig eth1 down
        ifconfig_down = subprocess.getoutput(f'ifconfig {now_network_card_name} down')
        all_logger.info(f'ifconfig {now_network_card_name} down :{ifconfig_down}')

        # ifconfig eth1 hw ether 00:0e:c6:67:78:01 up
        # ifconfig_up = subprocess.getoutput(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up')
        # all_logger.info(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up :{ifconfig_up}')

        # vconfig add eth1 2
        vconfig_up_2 = subprocess.getoutput(f'vconfig add {now_network_card_name} 2')
        all_logger.info(f'vconfig add {now_network_card_name} 2 :{vconfig_up_2}')

        # sudo ifconfig eth1.2 hw ether FF:FF:FF:FF:FF:FF up
        # sudo ifconfig eth1.3 up
        # sudo ifconfig eth1.4 up
        # ifconfig_up_2 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up')
        # all_logger.info(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up  :{ifconfig_up_2}')

        # ifconfig
        ifconfig_all_result = subprocess.getoutput(f'ifconfig -a')
        all_logger.info(f'ifconfig -a  :{ifconfig_all_result}')
        if f'{now_network_card_name}.2' not in ifconfig_all_result:
            raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

        # sudo udhcpc -i eth1
        # sudo udhcpc -i eth1.2
        # sudo udhcpc -i eth1.3
        # sudo udhcpc -i eth1.4
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}')
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}.2')

    def four_way_dial_set(self, eth_test_mode):
        now_network_card_name = self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name
        # modprobe 8021q
        return_8021q = subprocess.getoutput('modprobe 8021q')
        all_logger.info('加载vlan模块modprobe 8021q:{}'.format(return_8021q))

        # ifconfig eth1 down
        ifconfig_down = subprocess.getoutput(f'ifconfig {now_network_card_name} down')
        all_logger.info(f'ifconfig {now_network_card_name} down :{ifconfig_down}')

        # ifconfig eth1 hw ether 00:0e:c6:67:78:01 up
        ifconfig_up = subprocess.getoutput(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up')
        all_logger.info(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up :{ifconfig_up}')

        # vconfig add eth1 2
        # vconfig add eth1 3
        # vconfig add eth1 4
        vconfig_up_2 = subprocess.getoutput(f'vconfig add {now_network_card_name} 2')
        all_logger.info(f'vconfig add {now_network_card_name} 2 :{vconfig_up_2}')
        vconfig_up_3 = subprocess.getoutput(f'vconfig add {now_network_card_name} 3')
        all_logger.info(f'vconfig add {now_network_card_name} 3 :{vconfig_up_3}')
        vconfig_up_4 = subprocess.getoutput(f'vconfig add {now_network_card_name} 4')
        all_logger.info(f'vconfig add {now_network_card_name} 4 :{vconfig_up_4}')

        # sudo ifconfig eth1.2 hw ether FF:FF:FF:FF:FF:FF up
        # sudo ifconfig eth1.3 up
        # sudo ifconfig eth1.4 up
        ifconfig_up_2 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up')
        all_logger.info(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up  :{ifconfig_up_2}')
        ifconfig_up_3 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.3 up')
        all_logger.info(f'ifconfig add {now_network_card_name}.3 up :{ifconfig_up_3}')
        ifconfig_up_4 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.4 up')
        all_logger.info(f'ifconfig add {now_network_card_name}.4 up :{ifconfig_up_4}')

        # ifconfig
        ifconfig_all_result = subprocess.getoutput(f'ifconfig -a')
        all_logger.info(f'ifconfig -a  :{ifconfig_all_result}')
        if f'{now_network_card_name}.2' not in ifconfig_all_result or f'{now_network_card_name}.3' not in ifconfig_all_result or f'{now_network_card_name}.4' not in ifconfig_all_result:
            raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

        # sudo udhcpc -i eth1
        # sudo udhcpc -i eth1.2
        # sudo udhcpc -i eth1.3
        # sudo udhcpc -i eth1.4
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}')
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}.2')
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}.3')
        self.udhcpc_get_ip(network_name=f'{now_network_card_name}.4')

    def qmap_wwan_get_ip(self, ipv):
        all_logger.info(f'开始AT+QMAP="wwan"查询IPV{ipv}地址')
        return_value = self.send_at_error_try_again('AT+QMAP="wwan"', 3)
        return_ipv4 = ''.join(re.findall(r'\+.*"IPV4","(.*)"', return_value))
        all_logger.info(f'IPV4: {return_ipv4}')
        return_ipv6 = ''.join(re.findall(r'\+.*"IPV6","(.*)"', return_value))
        all_logger.info(f'IPV6: {return_ipv6}')
        if ipv == 4:
            return return_ipv4
        if ipv == 6:
            return return_ipv6

    def qmap_lan_get_ip(self):
        all_logger.info(f'开始AT+QMAP="lan"查询IP地址')
        return_value = self.at_handler.send_at('AT+QMAP="lan"', 3)
        return_ip = ''.join(re.findall(r'\+QMAP: "LAN",(.*)', return_value))
        all_logger.info(f'IPV4: {return_ip}')
        return return_ip

    def open_vlan(self, vlan_num):
        all_logger.info(f"开启vlan {vlan_num}")
        return_vlan_set = self.at_handler.send_at(f'at+qmap="vlan",{vlan_num},"enable"', 6)
        all_logger.info(f'at+qmap="vlan",{vlan_num},"enable": \r\n{return_vlan_set}')
        time.sleep(60)  # 第一次设置vlan模块可能会重启
        self.driver.check_usb_driver()
        time.sleep(5)
        return_vlan_check = self.at_handler.send_at('at+qmap="vlan"', 3)
        if f'+QMAP: "VLAN",{vlan_num}' not in return_vlan_check:
            raise LinuxETHError(f'检查vlan异常： {return_vlan_check} ,期望为+QMAP: "VLAN",{vlan_num}')

    def enter_eth_mode(self, eth_test_mode='0'):
        """
        eth_test_mode:根据具体测试机配备的PHY硬件类型来决定(resource中需要配置)
        0  随机RGMII8035\8211和RTL8125
        1  随机RGMII8035\8211和RTL8168
        2  随机RGMII8035\8211
        3  RTL8125
        4  RTL8168
        """
        eth_test_mode_list1 = {'2': 'RGMII', '3': 'RTL8125'}
        eth_test_mode_list2 = {'2': 'RGMII', '4': 'RTL8168'}
        if eth_test_mode == '0':  # 随机模式
            eth_test_mode = random.choice(list(eth_test_mode_list1.keys()))
            all_logger.info(f"当前为随机测试模式，本条case随机到的测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        if eth_test_mode == '1':  # 随机模式
            eth_test_mode = random.choice(list(eth_test_mode_list2.keys()))
            all_logger.info(f"当前为随机测试模式，本条case随机到的测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        time.sleep(10)
        all_logger.info(f"本条case测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        try:
            if eth_test_mode == '2':
                self.rgmii(status="enable", voltage=1)
                self.enter_eth_check('2')
            elif eth_test_mode == '3':
                self.enter_rtl_mode('8125')
                self.check_rtl_pci('8125')
                time.sleep(60)
                self.enter_eth_check('3')
            elif eth_test_mode == '4':
                self.enter_rtl_mode('8168')
                self.check_rtl_pci('8168')
                self.enter_eth_check('4')
            elif eth_test_mode == '5':
                self.enter_qca_mode()
                self.check_rtl_pci('8081')
                self.enter_eth_check('5')
            else:
                raise LinuxETHError("未知测试模式，请确认eth_test_mode参数值是否正确")
        finally:
            return eth_test_mode

    def enter_eth_check(self, eth_test_mode):
        """
        PHY模块灯被点亮，PC端本地连接状态为已连接无网络；可以ping通内网IP
        192.168.225.1
        """
        # wait 10 seconds
        all_logger.info("开始ping内网IP")
        time.sleep(10)

        ip = LinuxAPI.get_ip_address(self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name, ipv6_flag=False)
        try:
            ping_data = ping('192.168.225.1', count=20, interval=1, source=ip)
            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
            if ping_data.is_alive:
                all_logger.info('ping检查正常')
                return True
        except Exception as e:
            all_logger.info(e)
            all_logger.info('ping地址192.168.225.1失败')

    def exit_eth_mode(self, eth_test_mode):
        """
        eth_test_mode:
        1  RGMII
        2  RTL8125
        3  RTL8168
        """
        if eth_test_mode != '':
            all_logger.info(f"开始退出{self.eth_test_mode_list[eth_test_mode]}模式")
            if eth_test_mode == '2':
                self.rgmii(status="disable", voltage=1, check=False)
            elif eth_test_mode == '3':
                self.exit_rtl_mode()
            elif eth_test_mode == '4':
                self.exit_rtl_mode()
            elif eth_test_mode == '5':
                self.exit_rtl_mode()
        else:
            self.rgmii(status="disable", voltage=1)
            self.exit_rtl_mode()

        # 恢复内网
        s_0 = subprocess.getoutput(f'ifconfig {self.pc_ethernet_name} up')
        all_logger.info(f"ifconfig {self.pc_ethernet_name} up: {s_0}")
        self.udhcpc_get_ip(self.pc_ethernet_name)

    def enter_qca_mode(self):
        return_value = self.at_handler.send_at('AT+QCFG="pcie/mode",3', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError("QCA8081开启异常")

    def enter_rtl_mode(self, mode='8125'):
        """
        1. 执行AT+QCFG="data_interface",1,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",1 //启用RC模式（重启生效）
        3. 执行AT+QETH="eth_driver","r8125" //选择rtl8125驱动（重启生效）
        AT+QETH="eth_driver"
        +QETH: "eth_driver","r8125",0
        +QETH: "eth_driver","r8168",0

        OK
        """
        all_logger.info(f'enter rtl{mode} mode')
        all_logger.info('开始打开pcie net')
        return_value = self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError("打开pcie net异常")

        all_logger.info('开始启用RC模式')
        return_value = self.at_handler.send_at('AT+QCFG="pcie/mode",1', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError("启用RC模式异常")

        all_logger.info(f'选择rtl{mode}驱动')
        return_value = self.at_handler.send_at(f'AT+QETH="eth_driver","r{mode}"', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError(f"选择rtl{mode}驱动异常")

        # s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} up')
        # all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} up: {s}")

        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()

        s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} up')
        all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} up: {s}")

        self.driver.check_usb_driver()
        time.sleep(10)

    def exit_rtl_mode(self):
        """
        1. 执行AT+QCFG="data_interface",0,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",0 //启用RC模式（重启生效）
        """
        all_logger.info('exit rtl8125 mode')
        all_logger.info('开始关闭pcie net')
        return_value = self.at_handler.send_at('AT+QCFG="data_interface",0,0', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError("关闭pcie net异常")

        all_logger.info('开始关闭RC模式')
        return_value = self.at_handler.send_at('AT+QCFG="pcie/mode",0', 0.6)
        if 'OK' not in return_value:
            raise LinuxETHError("关闭RC模式异常")

        s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} down')
        all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} down: {s}")

        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(10)

    def reboot_module_vbat(self):
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()

    def qeth_attr_check(self):
        qeth_standard = ['+QETH: "rgmii",("enable","disable"),(0,1),(-1,0,1),(1-8)',
                         '+QETH: "ipptmac",<host_mac_addr>',
                         '+QETH: "mac_address",<rgmii_mac_addr>',
                         '+QETH: "speed",("0M","10M","100M","1000M")',
                         '+QETH: "an",("on","off")',
                         '+QETH: "mac_mode",(0,1)',
                         '+QETH: "eth_driver",<eth_driver>,(0,1)',
                         '+QETH: "eth_at",("enable","disable")',
                         '+QETH: "qps_port",(0,1),("USXGMII","XFI","RGMII","SGMII"),(10000,5000,2500,1000,100,10)',]
        all_logger.info('\nqeth_standard: \n{}'.format('\n'.join(qeth_standard)))

        qeth = self.at_handler.send_at("AT+QETH=?")
        qeth_regex = re.findall(r"(\+QETH:\s.*?)\s", qeth)
        all_logger.info('\nqeth_regex: \n{}'.format('\n'.join(qeth_regex)))

        a_b_diff = set(qeth_standard).difference(set(qeth_regex))
        b_a_diff = set(qeth_regex).difference(set(qeth_standard))
        if a_b_diff or b_a_diff:
            raise LinuxETHError(
                "AT+QETH=? Checked Error! Diff: {}, Plese Check".format(a_b_diff if a_b_diff else b_a_diff))

        return True

    def qmap_attr_check(self):
        """
        '+QMAP: "WWAN",(0,1),(1-42),<IP_family>,<IP_address>',
        '+QMAP: "DMZ",(0,1),(4,6),<IP_address>',
        '+QMAP: "GRE",(0,1),<IP_address>',
        '+QMAP: "LAN",<IP_address>',
        '+QMAP: "LANIP",<LAN_IP_start_address>,<LAN_IP_end_address>,<GW_IP_address>,<effect>',
        '+QMAP: "MAC_bind",(1-10),<MAC_address>,<IP_address>',
        '+QMAP: "VLAN",(2-255),("enable","disable"),(1-3,11-13)',
        '+QMAP: "MPDN_rule",(0-3),(1-16),(0,2-255),(0-3),(0,1),<IPPT_info>',
        '+QMAP: "IPPT_NAT",(0,1)',
        '+QMAP: "connect",(0-3),(0,1)',
        '+QMAP: "auto_connect",(0-3),(0,1),(1-16)',
        '+QMAP: "MPDN_status"',
        '+QMAP: "AP_rule",(0-3),(0-3)',
        '+QMAP: "SFE",("enable","disable")',
        '+QMAP: "domain",<domain_name>',
        '+QMAP: "DHCPV6DNS",("enable","disable")'

        OK
        """
        qeth_standard = ['+QMAP: "WWAN",(0,1),(1-42),<IP_family>,<IP_address>',
                         '+QMAP: "DMZ",(0,1),(4,6),<IP_address>',
                         '+QMAP: "GRE",(0,1),<IP_address>',
                         '+QMAP: "LAN",<IP_address>',
                         '+QMAP: "LANIP",<LAN_IP_start_address>,<LAN_IP_end_address>,<GW_IP_address>,<effect>',
                         '+QMAP: "MAC_bind",(1-10),<MAC_address>,<IP_address>',
                         '+QMAP: "VLAN",(2-255),("enable","disable"),(1-3,11-13)',
                         '+QMAP: "MPDN_rule",(0-3),(1-16),(0,2-255),(0-3),(0,1),<IPPT_info>',
                         '+QMAP: "IPPT_NAT",(0,1)',
                         '+QMAP: "connect",(0-3),(0,1)',
                         '+QMAP: "auto_connect",(0-3),(0,1),(1-16)',
                         '+QMAP: "MPDN_status"',
                         '+QMAP: "SFE",("enable","disable")',
                         '+QMAP: "domain",<domain_name>',
                         '+QMAP: "DHCPV6DNS",("enable","disable")']
        all_logger.info('\nqeth_standard: \n{}'.format('\n'.join(qeth_standard)))

        qeth = self.at_handler.send_at("AT+QMAP=?")
        qeth_regex = re.findall(r"(\+QMAP:\s.*?)\s", qeth)
        all_logger.info('\nqeth_regex: \n{}'.format('\n'.join(qeth_regex)))

        a_b_diff = set(qeth_standard).difference(set(qeth_regex))
        b_a_diff = set(qeth_regex).difference(set(qeth_standard))
        if a_b_diff or b_a_diff:
            raise LinuxETHError(
                "AT+QMAP=? Checked Error! Diff: {}, Plese Check".format(a_b_diff if a_b_diff else b_a_diff))

        return True

    def qdmz_attr_check(self):
        """
        AT+QDMZ=?
        '+QDMZ: (0,1),(4,6),<IP_address>'

        OK
        AT+QDMZ
        +QDMZ: 0,4
        +QDMZ: 0,6

        OK
        """
        qeth_standard = ['+QDMZ: (0,1),(4,6),<IP_address>']
        all_logger.info('\nqeth_standard: \n{}'.format('\n'.join(qeth_standard)))

        qeth = self.send_at_error_try_again("AT+QDMZ=?")
        qeth_regex = re.findall(r"(\+QDMZ:\s.*?)\s", qeth)
        all_logger.info('\nqeth_regex: \n{}'.format('\n'.join(qeth_regex)))

        a_b_diff = set(qeth_standard).difference(set(qeth_regex))
        b_a_diff = set(qeth_regex).difference(set(qeth_standard))
        if a_b_diff or b_a_diff:
            raise LinuxETHError(
                "AT+QDMZ=? Checked Error! Diff: {}, Plese Check".format(a_b_diff if a_b_diff else b_a_diff))

        return True

    def rgmii(self, status, voltage, mode='', profile_id='', parallel=(0, 0), check=True):
        """
                RGMII         status       voltage  mode   profile_id
        +QETH: "rgmii",("enable","disable"),(0,1),(-1,0,1),(1-8)
        status : ENABLE, DISABLE
        mode : 0 : COMMON-RGMII ; 1 : IPPassthrough
        voltage : default: 1: 2.5V ; 0, 1.8V
        """
        s_0 = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} up')
        all_logger.info(f"ifconfig {self.rgmii_ethernet_name} up: {s_0}")

        all_logger.info('wait 1 seconds')
        time.sleep(1)
        # set
        rgmii_at = f'AT+QETH="RGMII","{status}",{voltage}'
        if mode != '':
            rgmii_at += ',{}'.format(mode)
        if profile_id:
            rgmii_at += ',{}'.format(profile_id)
        rgmii_dial_result = self.at_handler.send_at(rgmii_at, timeout=30)

        # check
        if check:
            rgmii_check_result = self.at_handler.send_at('AT+QETH="RGMII"', 15)
            line_0 = '+QETH: "RGMII","{}",{},{}'.format(status.upper(), voltage,
                                                        '-1' if status.upper() == 'DISABLE' else mode)
            line_1 = '+QETH: "RGMII",{},{}'.format(0 if mode == '' or status.upper() == 'DISABLE' else 1, 1 if not profile_id else profile_id)
            line_2 = '+QETH: "RGMII",{},{}'.format(2 if parallel[0] else 0, parallel[1] if parallel[1] else 2)
            line_3 = '+QETH: "RGMII",0,3'
            line_4 = '+QETH: "RGMII",0,4'
            all_check_info_list = [line_0, line_1, line_2, line_3, line_4]
            all_logger.info("all_check_info_list: {}".format(all_check_info_list))
            for info in all_check_info_list:
                if info not in rgmii_check_result:
                    all_logger.error('AT+QETH="RGMII" not found {}.'.format(info))
                    raise LinuxETHError('AT+QETH="RGMII" not found {}.'.format(info))

        self.restart_eth_network_card()
        time.sleep(3)
        if status == "enable":
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip()
        if status == "disable":
            # 关闭网卡
            s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} down')
            all_logger.info(f"ifconfig {self.rgmii_ethernet_name} down: {s}")
        time.sleep(3)
        return rgmii_dial_result

    def restart_eth_network_card(self, eth_test_mode='2'):
        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} down')
        all_logger.info(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} down: {s}')

        all_logger.info('wait 5 seconds')  # 时间太少可能会导致获取不到ipv6地址
        time.sleep(5)

        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} up')
        all_logger.info(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} up: {s}')

    @staticmethod
    def check_ecm_driver(is_disappear=False):    # 检测ecm驱动
        """
        检测ECM拨号驱动是否正常加载或消失
        :param is_disappear: True: 检测ECM拨号正常消失；False: 检测ECM拨号正常加载
        :return:
        """
        check_cmd = subprocess.Popen('lsusb -t', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        check_time = time.time()
        all_logger.info("lsusb -t查询返回:\n")
        while True:
            time.sleep(0.001)
            check_cmd_val = check_cmd.stdout.readline().decode('utf-8', 'ignore')
            if check_cmd_val != '':
                all_logger.info(check_cmd_val)
            if 'cdc_ether' in check_cmd_val and not is_disappear:
                ifconfig_val = subprocess.run('ifconfig', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                if 'usb0' in ifconfig_val.stdout:
                    all_logger.info('ecm驱动检测成功')
                    check_cmd.terminate()
                    return True
                else:
                    all_logger.info(ifconfig_val)
                    check_cmd.terminate()
                    raise LinuxETHError('未检测到ecm驱动')
            if is_disappear and 'cdc_ether' not in check_cmd_val:
                all_logger.info('ecm驱动消失')
                check_cmd.terminate()
                return True
            if time.time() - check_time > 2:
                all_logger.info('未检测到ecm驱动')
                check_cmd.terminate()
                raise LinuxETHError('检测驱动超时')

    def mpdn_route_set(self, eth_test_mode, network_card_nums=2):
        """
        route set for mpdn
        """
        return_value0 = subprocess.getoutput('echo 1 > /proc/sys/net/ipv4/ip_forward')
        all_logger.info('echo 1 > /proc/sys/net/ipv4/ip_forward\n{}'.format(return_value0))
        time.sleep(1)
        return_value_all = subprocess.getoutput('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter')
        all_logger.info('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter\n{}'.format(return_value_all))
        time.sleep(1)
        return_value1 = subprocess.getoutput(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}/rp_filter")
        all_logger.info(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}/rp_filter : {return_value1}")
        time.sleep(1)
        for i in range(2, network_card_nums + 1):
            return_value2 = subprocess.getoutput(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}.{i}/rp_filter")
            all_logger.info(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}.{i}/rp_filter : {return_value2}")
            time.sleep(1)

    def check_mPDN_rule(self, vlan, apn, mac=''):
        """
        AT+QMAP="mPDN_rule"
        +QMAP: "MPDN_rule",0,0,0,0,0
        +QMAP: "MPDN_rule",1,0,0,0,0
        +QMAP: "MPDN_rule",2,0,0,0,0
        +QMAP: "MPDN_rule",3,0,0,0,0

        OK
        """
        return_value = self.send_at_error_try_again('AT+QMAP="mPDN_rule"', 60)
        all_logger.info(f'{return_value}')
        if apn and mac == '' and f'+QMAP: "MPDN_rule",0,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",0,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",1,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",1,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",2,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",2,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",3,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",3,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        else:
            raise LinuxETHError(f"vlan{vlan}、apn{apn}拨号规则检查异常!")

    def check_MPDN_status(self, vlan, apn, mac=''):
        """
        AT+QMAP="MPDN_status"
        +QMAP: "MPDN_status",0,0,0,0
        +QMAP: "MPDN_status",1,0,0,0
        +QMAP: "MPDN_status",2,0,0,0
        +QMAP: "MPDN_status",3,0,0,0

        OK
        """
        all_logger.info("等待10s拨号稳定")
        time.sleep(10)
        return_value = self.send_at_error_try_again('AT+QMAP="MPDN_status"', 60)
        all_logger.info(f'{return_value}')
        if mac == '' and f'+QMAP: "MPDN_status",0,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",0,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",1,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",1,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",2,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",2,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",3,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",3,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        else:
            raise LinuxETHError(f"vlan{vlan}、apn{apn}拨号状态检查异常!")

    def udhcpc_get_ip(self, eth_test_mode='2', network_name=''):
        # self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name
        now_network_name = (self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name) if network_name == '' else network_name
        all_logger.info(f"udhcpc -i {now_network_name}")
        process = subprocess.Popen(f'udhcpc -i {now_network_name}',
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   shell=True)
        t = threading.Timer(120, self.process_input)
        t.setDaemon(True)
        t.start()
        get_result = ''
        while process.poll() is None:
            value = process.stdout.readline().decode()
            if value:
                all_logger.info(value)
                get_result += value
        all_logger.info(get_result)

    @staticmethod
    def process_input():
        all_logger.info("killall udhcpc")
        subprocess.Popen("killall udhcpc", shell=True)

    def ip_passthrough_connect_check(self, eth_test_mode, try_times=3):
        # 重新获取ip
        self.restart_eth_network_card(eth_test_mode)
        self.udhcpc_get_ip(eth_test_mode)

        # get ipv4
        ipv4 = self.get_network_card_ipv4(eth_test_mode, www=True)
        # self.get_network_card_ipv6(eth_test_mode)

        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网是否正常")
        time.sleep(10)

        # check ipv4
        if ipv4.startswith('192.168') is True:
            raise LinuxETHError("IP Passthrough RGMII IPv4 start with 192.168.")

        retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
        all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
        if '0:0:0:0:0:0:0:0' in retunr_value:
            raise LinuxETHError("模块拨号获取IPV6地址失败！")

        # check connect ipv4
        for _ in range(try_times):
            try:
                self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name)
                break
            except Exception as e:
                all_logger.info(e)
                # 重新获取ip
                self.restart_eth_network_card(eth_test_mode)
                self.udhcpc_get_ip(eth_test_mode)
        else:
            raise LinuxETHError(f"尝试{try_times}次重新获取IP后ping失败")

        # check connect ipv6
        # self.linux_api.ping_get_connect_status(ipv6_flag=True, network_card_name=self.rgmii_ethernet_name)
        for i in range(10):
            ping6_result = self.eth_ping_ipv6()
            if ping6_result:
                break
            # 重新获取ip
            self.restart_eth_network_card(eth_test_mode)
            self.udhcpc_get_ip(eth_test_mode)
        else:
            raise LinuxETHError("尝试10次重新获取IP后ping失败")

    def common_connect_check(self, eth_test_mode):
        # 重新获取ip
        self.udhcpc_get_ip(eth_test_mode)

        # get ipv4
        ipv4 = self.get_network_card_ipv4(eth_test_mode, www=False)
        # self.get_network_card_ipv6(eth_test_mode)

        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网是否正常")
        time.sleep(10)

        retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
        all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
        if '0:0:0:0:0:0:0:0' in retunr_value:
            raise LinuxETHError("模块拨号获取IPV6地址失败！")

        # check ipv4
        if ipv4.startswith('192.168') is False:
            raise LinuxETHError("Common IPv4 not start with 192.168.")

        # check connect ipv4
        for _ in range(3):
            try:
                self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name)
                break
            except Exception as e:
                all_logger.info(e)
                # 重新获取ip
                self.restart_eth_network_card(eth_test_mode)
                self.udhcpc_get_ip(eth_test_mode)
        else:
            raise LinuxETHError("尝试3次重新获取IP后ping失败")

        # check connect ipv6
        # self.linux_api.ping_get_connect_status(ipv6_flag=True, network_card_name=self.rgmii_ethernet_name)
        for i in range(10):
            ping6_result = self.eth_ping_ipv6()
            if ping6_result:
                break
            # 重新获取ip
            self.restart_eth_network_card(eth_test_mode)
            self.udhcpc_get_ip(eth_test_mode)
        else:
            raise LinuxETHError("尝试10次重新获取IP后ping失败")

    @staticmethod
    def eth_ping_ipv6():
        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网ipv6是否正常")
        ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666', '240c::6666'], count=20, interval=1, family=6)
        for ping_data in ping_datas:
            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
            if ping_data.is_alive:
                all_logger.info('ping检查正常')
                return True
        else:
            all_logger.info('拨号后获取IP测试网络连接异常')
            return False
            # raise LinuxETHError('ping ipv6检查异常')

    def get_network_card_ipv4(self, eth_test_mode, www=False):
        out = None
        for i in range(30):
            out = subprocess.getoutput('ifconfig {} | grep "inet " | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            if out and www is False and out.startswith("192"):  # 如果是获取内网IP
                all_logger.info(f"IPv4 internal address is: {repr(out)}")
                return out
            elif out and www and out.startswith("192") is False:  # 如果是获取外网IP
                all_logger.info(f"IPv4 www address is: {repr(out)}")
                return out
            else:
                time.sleep(1)
                continue
        else:
            s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            all_logger.info(s)
            if www:
                raise LinuxETHError("IP Passthrough RGMII 拨号模式，未获取到公网IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))
            else:
                raise LinuxETHError("Common RGMII 拨号模式，未获取到192.168.开头的IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))

    def get_network_card_ipv6(self, eth_test_mode):
        for i in range(30):
            out = subprocess.getoutput('ifconfig {} | grep "inet6 24" | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            if out and out.startswith('24'):
                all_logger.info(f"IPv6 address is: {repr(out)}")
                return out
            else:
                time.sleep(1)
                continue
        else:
            s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            all_logger.info(s)
            raise LinuxETHError('Fail to get ipv6 address')

    def check_rtl_pci(self, mode):
        """
        Debug输入命令lspci检查RTL8125的PCI
        """
        # 启动线程
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()

        try:
            all_logger.info('wait 20 secs.')
            time.sleep(20)

            all_logger.info('check pci')
            data = debug_port.exec_command('lspci')
            all_logger.info('lspci data : {}'.format(data))
            if mode == '8125' and f'10ec:{mode}' not in data:
                raise LinuxETHError(
                    f"RTL{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            elif mode == '8168' and f'10ec:{mode}' not in data:  # todo 待根据实际log完善
                raise LinuxETHError(
                    f"RTL{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            elif mode == '8081' and f'10ec:{mode}' not in data:  # todo 待根据实际log完善
                raise LinuxETHError(
                    f"{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            else:
                all_logger.info(f'already find pci of PHY\r\n{data}"')
        finally:
            all_logger.info('check pci end')
            debug_port.close_debug()

    def get_value_debug(self, commond):
        """
        Debug输入命令后返回值
        """
        # 启动线程
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        data = ''
        try:
            all_logger.info('wait 20 secs.')
            time.sleep(20)

            all_logger.info(commond)
            data = debug_port.exec_command(commond)
            all_logger.info('denug data : {}'.format(data))

        finally:
            all_logger.info('check pci end')
            debug_port.close_debug()
            return data

    @staticmethod
    def speedtest(network_card='eth0'):
        for i in range(3):
            cache = ''
            s = subprocess.Popen('speedtest --accept-license -I {}'.format(network_card), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            all_logger.info('开始测速：speedtest --accept-license -I {}'.format(network_card))
            while s.poll() is None:
                time.sleep(0.001)
                data = s.stdout.readline().decode('utf-8', 'replace')
                if data:
                    all_logger.info('[SPEEDTEST] {}'.format(data))
                    cache += data
                    download_speed = ''.join(re.findall(r'ownload:\s+(\d+\.\d+) Mbps', cache))
                    if download_speed:
                        try:
                            s.communicate(timeout=0.1)
                        except subprocess.TimeoutExpired:
                            pass
                        s.terminate()
                        s.wait()
                        all_logger.info('Speedtest test download speed is {} Mbps'.format(int(float(download_speed))))
                        return int(float(download_speed))
        else:
            raise LinuxETHError("Fail to get max download speed via speedtest")

    def ipptmac_check_default(self):
        ipptmac = self.send_ipptmac()
        all_logger.info('ippt_mac: {}'.format(ipptmac))
        ipptmac_regex = re.findall(r'\S{2}:\S{2}:\S{2}:\S{2}:\S{2}:\S{2}', ipptmac)
        all_logger.info('ipptmac_regex: {}'.format(ipptmac_regex))
        if not ipptmac_regex or "OK" not in ipptmac:
            raise LinuxETHError("AT+QETH='ipptmac' return Error!")

    def ipptmac_set_check(self, eth_test_mode):
        all_logger.info('ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
        pc_ethernet_orig_mac = subprocess.getoutput('ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
        self.send_ipptmac(pc_ethernet_orig_mac)
        qeth_ipptmac = self.send_ipptmac()
        if pc_ethernet_orig_mac not in qeth_ipptmac:
            raise LinuxETHError("MAC code check failed after write MAC code.")

        self.at_handler.send_at("AT+CFUN=1,1")
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.at_handler.check_network()
        time.sleep(10)  # 避免太快返回error
        self.send_ipptmac()
        if pc_ethernet_orig_mac not in qeth_ipptmac:
            raise LinuxETHError("MAC code check failed after write and restart.")

    def eth_network_card_down(self, eth_test_mode):  # 禁用PHY网卡
        all_logger.info('eth_test_mode: {}'.format(eth_test_mode))
        now_network_card_name = self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name
        all_logger.info('now_network_card_name: {}'.format(now_network_card_name))
        # 恢复默认网卡
        ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(now_network_card_name))  # 启用本地网卡
        all_logger.info('ifconfig {} down\r\n{}'.format(now_network_card_name, ifconfig_down_value))

    def send_at_error_try_again(self, common_at, time_out_at=0.6):  # 部分指令很容易出现ERROR，但重试又正常
        all_logger.info(common_at)
        return_value_at = ''
        for i in range(10):  # 针对此指令容易返回error
            return_value_at = self.at_handler.send_at(common_at, time_out_at)
            if 'ERROR' not in return_value_at:
                return return_value_at
            time.sleep(1)
        else:
            all_logger.info(f'连续10次发送AT+QETH="ipptmac"失败： {return_value_at}')

    def send_ipptmac(self, ipptmac=''):
        qeth_ipptmac = ''
        for i in range(10):  # 针对此指令容易返回error
            if ipptmac == '':
                qeth_ipptmac = self.at_handler.send_at(f'AT+QETH="ipptmac"', 3)
            else:
                qeth_ipptmac = self.at_handler.send_at(f'AT+QETH="ipptmac",{ipptmac}', 3)
            if 'ERROR' not in qeth_ipptmac:
                return qeth_ipptmac
            time.sleep(1)
        else:
            raise LinuxETHError(f'连续10次发送AT+QETH="ipptmac"失败： {qeth_ipptmac}')

    def send_mpdn_rule(self, mpdn_rule=''):
        return_value = ''
        for i in range(10):  # 针对此指令容易返回error
            if mpdn_rule == '':
                return_value = self.at_handler.send_at(f'AT+qmap="mpdn_rule"', 60)
            else:
                return_value = self.at_handler.send_at(f'AT+qmap="mpdn_rule",{mpdn_rule}', 60)
            if 'ERROR' not in return_value:
                return return_value
            time.sleep(1)
        else:
            raise LinuxETHError(f'连续10次发送AT+qmap="mpdn_rule"失败： {return_value}')

    def store_default_apn(self):
        """
        get default apn.
        """
        cgdconts = self.at_handler.send_at("AT+CGDCONT?", 3)
        cgdconts = re.findall(r'\+CGDCONT:\s(\d+),"(.*?)","(.*?)"', cgdconts)
        self.default_apns = cgdconts

    def restore_default_apn(self):
        for apn in self.default_apns:
            self.at_handler.send_at('AT+CGDCONT={},"{}","{}"'.format(*apn), 3)

    def set_apn(self, path, apn=""):
        default_apn_str = str(self.default_apns).upper()
        if not apn:
            if 'CMNET' in default_apn_str:
                apn = "CTNET"
            elif '3GNET' in default_apn_str:
                apn = "CMNET"
            else:
                apn = "3GNET"

        self.at_handler.send_at(f'AT+CGDCONT={path},"IPV4V6","{apn}"', 3)
        time.sleep(3)
        cgdcont = self.at_handler.send_at('AT+CGDCONT?')
        all_logger.info(cgdcont)

    def at_get_mac_address(self):
        mac_address = self.send_at_error_try_again('AT+QETH="MAC_ADDRESS"', 3)
        mac_address_regex = ''.join(re.findall(r'\+QETH:\s"mac_address",(\S{2}:\S{2}:\S{2}:\S{2}:\S{2}:\S{2})', mac_address))
        all_logger.info("mac_address_regex: {}".format(mac_address_regex))
        if not mac_address_regex:
            raise LinuxETHError('AT+QETH="MAC_ADDRESS" fail to get mac address.')
        return mac_address_regex

    def sitch_fastboot_erase_rawdata(self):
        self.at_handler.send_at_without_check("AT+QFASTBOOT")

        # check fastboot devices
        start_time = time.time()
        while time.time() - start_time < 30:
            output = subprocess.getoutput("fastboot devices")
            if output != '':
                all_logger.info('Switch fastboot success! {}'.format(output))
                break
        else:
            raise LinuxETHError("Switch Fastboot mode failed.")

        all_logger.info('wait 3 seconds')
        time.sleep(3)

        erase = subprocess.getoutput('fastboot erase rawdata')
        all_logger.info('erase rawdata :{}'.format(repr(erase)))

    def fastboot_reboot(self):
        subprocess.getoutput("fastboot reboot")

        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.at_handler.check_network()

    def sim_det(self, is_open):
        """
        开启/关闭SIM卡热插拔功能
        :param is_open:是否开启热插拔功能 True:开启；False:关闭
        :return:
        """
        if is_open:
            self.at_handler.send_at('AT+QSIMDET=1,1', 10)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            time.sleep(5)
            if '1,1' in self.at_handler.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功开启热插拔功能')
            else:
                all_logger.info('开启热拔插功能失败')
                raise LinuxETHError('开启热拔插功能失败')
        else:
            self.at_handler.send_at('AT+QSIMDET=0,1', 10)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            time.sleep(5)
            if '0,1' in self.at_handler.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功关闭热插拔功能')
            else:
                all_logger.info('关闭热拔插功能失败')
                raise LinuxETHError('关闭热拔插功能失败')

    def check_simcard(self, is_ready):
        """
        检测当前SIM卡状态
        :param is_ready:期望当前卡状态是否正常。True:期望正常检测到卡；False:期望检测不到卡
        :return:
        """
        if is_ready:
            for i in range(3):
                cpin_value = self.at_handler.send_at('AT+CPIN?', 10)
                if 'READY' in cpin_value:
                    all_logger.info('当前SIM卡状态检测正常，可以检测到SIM卡')
                    return
                time.sleep(1)
            else:
                all_logger.info('当前SIM卡状态检测异常，无法识别到SIM卡')
        else:
            for i in range(3):
                cpin_value = self.at_handler.send_at('AT+CPIN?', 10)
                if 'READY' not in cpin_value:
                    all_logger.info('当前SIM卡状态检测正常，无法识别到SIM卡')
                    return
                time.sleep(1)
            else:
                all_logger.info('当前SIM卡状态检测异常，可以检测到SIM卡')

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

    def qmapwac_default_check(self):
        """
        检查qmapwac的默认值:
        at+QMAPWAC=?
        +QMAPWAC: (0,1)

        OK
        AT+QMAPWAC?
        +QMAPWAC: 0

        OK
        """
        all_logger.info('开始检查at+QMAPWAC=?默认值：')
        return_value = self.at_handler.send_at("at+QMAPWAC=?")
        if '+QMAPWAC: (0,1)' not in return_value:
            raise LinuxETHError('at+QMAPWAC=?默认值查询与预期不匹配！请检查:{}'.format(return_value))
        time.sleep(3)
        all_logger.info('{}'.format(return_value))
        all_logger.info('开始检查at+QMAPWAC?默认值：')
        return_value1 = self.at_handler.send_at("at+QMAPWAC?")
        if '+QMAPWAC: 0' not in return_value1:
            raise LinuxETHError('at+QMAPWAC?默认值查询与预期不匹配！请检查:{}'.format(return_value1))
        all_logger.info('{}'.format(return_value1))
        all_logger.info('默认值检查结束')
        return True

    def reset_usbnet_0(self):
        self.at_handler.send_at('AT+QCFG="USBNET",0', timeout=3)
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        all_logger.info('wait 10 seconds')
        time.sleep(10)


class DebugPort(Thread):

    def __init__(self, debug_port, name_qgmr_version):
        super().__init__()
        self.debug_port = serial.Serial(debug_port, baudrate=115200, timeout=0.8)
        self.debug_port.write('\r\n'.encode('utf-8'))
        self.debug_open_flag = True
        self.debug_read_flag = True
        self.dq = deque(maxlen=100)
        # 是否是OCPU版本
        self.Is_OCPU_version = True if 'OCPU' in name_qgmr_version else False

    def readline(self, port):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值：
        如果有值，读取直到\n；
        如果有值，超过1S，直接返回；
        如果没有值，返回 ''
        :param port: 已经打开的端口
        :return: buf:端口读取到的值；没有值返回 ''
        """
        buf = ''
        try:
            if port.in_waiting > 0:
                start_time = time.time()
                while True:
                    buf += port.read(1).decode('utf-8', 'replace')
                    if buf.endswith('\n'):
                        all_logger.info("DEBUG {} {}".format("RECV", repr(buf).replace("'", '')))
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > 1:
                        all_logger.info('{}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            all_logger.error('Fatal ERROR: {}'.format(error))
        finally:
            if buf:
                self.dq.append(buf)
            return buf

    def run(self):
        """
        自动登录debug port
        :return:
        """
        qid = ''
        while True:
            time.sleep(0.001)
            if self.debug_read_flag:
                res = self.readline(self.debug_port)
                if 'login:' in res:
                    self.debug_port.write('root\r\n'.encode('utf-8'))
                if 'quectel-ID' in res:
                    qid = ''.join(re.findall(r'quectel-ID : (\d+)', res))
                if 'Password:' in res:
                    if self.Is_OCPU_version:
                        passwd = 'oelinux123'
                    else:
                        passwd = getpass(qid)
                    all_logger.info(passwd)
                    self.debug_port.write('{}\r\n'.format(passwd).encode('utf-8'))
                if not self.debug_open_flag:
                    self.debug_port.close()
                    break

    def exec_command(self, cmd, timeout=1):
        """
        在debug口执行命令
        :param cmd: 需要执行的命令
        :param timeout: 检查命令的超时时间
        :return: None
        """
        self.debug_read_flag = False
        self.debug_port.write('{}\r\n'.format(cmd).encode('utf-8'))
        cache = ''
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.001)
            res = self.readline(self.debug_port)
            if res:
                cache += res
        self.debug_read_flag = True
        return cache

    def close_debug(self):
        """
        关闭DEBUG口，结束线程
        :return: None
        """
        all_logger.info('close_debug')
        self.debug_open_flag = False

    def ctrl_c(self):
        self.debug_port.write("\x03".encode())

    def get_latest_data(self, depth=10):
        return ''.join(list(self.dq)[-depth:])
