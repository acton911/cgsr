import subprocess
import requests
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxRTL8125Error
import re
import os
import time
import serial
from threading import Thread
from utils.functions.getpassword import getpass
from collections import deque
import threading


class LinuxRTL8125Manager:
    def __init__(self, at_port, dm_port, debug_port, rtl8125_ethernet_name, phone_number, pc_ethernet_name):
        self.linux_api = LinuxAPI()
        self.phone_number = phone_number
        self.at_port = at_port
        self.at_handler = ATHandle(self.at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.rtl8125_ethernet_name = rtl8125_ethernet_name  # RTL8125
        self.pc_ethernet_name = pc_ethernet_name  # local network
        self.debug_port = debug_port
        self.default_apns = None
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.return_qgmr = self.at_handler.send_at('AT+QGMR', 0.6)

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
                   "request_id": "10011"
                   }
        dial_request = requests.post(self.url, json=content)
        all_logger.info(dial_request.json())
        self.at_handler.readline_keyword('RING', timout=300)
        time.sleep(5)
        self.at_handler.readline_keyword('NO CARRIER', timout=300)
        time.sleep(5)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handler.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
        self.at_handler.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        self.at_handler.readline_keyword('+CMTI', timout=300)
        time.sleep(5)

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
            raise LinuxRTL8125Error("Fail to get max download speed via speedtest")

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
            raise LinuxRTL8125Error('at+QMAPWAC=?默认值查询与预期不匹配！请检查:{}'.format(return_value))
        time.sleep(3)
        all_logger.info('{}'.format(return_value))
        all_logger.info('开始检查at+QMAPWAC?默认值：')
        return_value1 = self.at_handler.send_at("at+QMAPWAC?")
        if '+QMAPWAC: 0' not in return_value1:
            raise LinuxRTL8125Error('at+QMAPWAC?默认值查询与预期不匹配！请检查:{}'.format(return_value1))
        all_logger.info('{}'.format(return_value1))
        all_logger.info('默认值检查结束')
        return True

    def set_ethernet_up(self):
        """
        ifconfig eth0 up
        """
        return_value = subprocess.getoutput('ifconfig {} up'.format(self.rtl8125_ethernet_name))
        all_logger.info('ifconfig {} up：{}'.format(self.rtl8125_ethernet_name, return_value))

    def set_ethernet_down(self):
        """
        ifconfig eth0 up
        """
        return_value = subprocess.getoutput('ifconfig {} down'.format(self.rtl8125_ethernet_name))
        all_logger.info('ifconfig {} down：{}'.format(self.rtl8125_ethernet_name, return_value))

    def udhcpc_get_ip(self, network_card_name):
        all_logger.info(f"udhcpc -i {network_card_name}")
        process = subprocess.Popen(f'udhcpc -i {network_card_name}',
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
        subprocess.Popen("killall udhcpc", shell=True)

    def ping_status_rtl8125(self):
        """
        ping after connect
        """
        all_logger.info('start PC ping test')
        for i in range(30):
            all_logger.info("获取IPv4地址")
            return_value = subprocess.getoutput('ifconfig')
            all_logger.info('ifconfig：\n{}'.format(return_value))
            # rerurn_ipv4_eth0 = subprocess.getoutput('ifconfig')
            # ipv4_eth0 = ''.join(re.findall(r'eth0: .*\n.*inet (\d+.\d+.\d+.\d+)', rerurn_ipv4_eth0))
            all_logger.info("ifconfig {} | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -n 1".format(self.rtl8125_ethernet_name))
            ipv4_eth0 = subprocess.getoutput("ifconfig {} | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -n 1".format(self.rtl8125_ethernet_name))
            all_logger.info('{}'.format(ipv4_eth0))
            if ipv4_eth0 and 'error' not in ipv4_eth0:
                all_logger.info('IP: {}'.format(ipv4_eth0))
                break
            time.sleep(1)
        else:
            all_logger.info(os.popen('ifconfig').read())
            raise LinuxRTL8125Error("获取IPv4地址失败")
        for _ in range(10):
            return_value = subprocess.getoutput('ping www.baidu.com -c 10 -I {}'.format(ipv4_eth0))
            all_logger.info("{}".format(return_value))
            if '100% packet loss' in return_value or 'unknown' in return_value or 'failure' in return_value:
                all_logger.info("eth0 fail to ping www.baidu.com")
                all_logger.info("再次尝试")
                self.set_ethernet_down()
                time.sleep(3)
                self.set_ethernet_up()
                self.udhcpc_get_ip(self.rtl8125_ethernet_name)
            else:
                all_logger.info('PC ping test end')
                break
        else:
            raise LinuxRTL8125Error("尝试10次获取ip并ping失败")

    def mpdn_set_3_way_apn(self):
        """
        1. at+cgdcont=1,"IPV4V6","apn1" //set first apn
        2. at+cgdcont=2,"IPV4V6","apn2" //set second apn
        3. at+cgdcont=3,"IPV4V6","apn3" //set third apn
        """
        all_logger.info('start set 3 way APN')
        self.at_handler.send_at('at+cgdcont=1,"IPV4V6","apn1"', 0.6)
        self.at_handler.send_at('at+cgdcont=2,"IPV4V6","apn2"', 0.6)
        self.at_handler.send_at('at+cgdcont=3,"IPV4V6","apn3"', 0.6)
        return_value = self.at_handler.send_at('at+cgdcont?', 0.6)
        all_logger.info('APN set result:{}'.format(return_value))

    def mpdn_add_2_vlan_enable(self):
        """
        add 2 vlan
        """
        all_logger.info('start add 2 vlan')
        self.at_handler.send_at('at+qmap="vlan",2,"enable"', 5)
        self.at_handler.send_at('at+qmap="vlan",3,"enable"', 5)
        return_value = self.at_handler.send_at('at+qmap="vlan"', 5)
        all_logger.info('add 2 vlan result:{}'.format(return_value))

    def mpdn_query_vlan_activations(self):
        """
        1. at+qmap="vlan" //query the number of VLAN activations
        """
        number = 0
        all_logger.info('start query the number of VLAN activations')
        return_value = self.at_handler.send_at('at+qmap="vlan"', 1)
        all_logger.info('{}'.format(return_value))
        if 'QMAP: "vlan",0' in return_value:
            number = number + 1
        if 'QMAP: "vlan",2' in return_value:
            number = number + 1
        if 'QMAP: "vlan",3' in return_value:
            number = number + 1
        all_logger.info('the number of VLAN activations is {}'.format(number))

    def mpdn_query_rule(self):
        """
        At+qmap="mPDN_rule" //query the number of mPDN rule
        """
        number = 0
        all_logger.info('start query the number of mPDN rule')
        return_value = self.at_handler.send_at('At+qmap="mPDN_rule"', 1)
        all_logger.info('{}'.format(return_value))
        if '"mPDN_rule",0,1,0,1,1' in return_value:
            number = number + 1
        if '"mPDN_rule",1,2,2,1,1' in return_value:
            number = number + 1
        if '"mPDN_rule",2,3,3,1,1' in return_value:
            number = number + 1
        if '"mPDN_rule",3,4,4,1,1' in return_value:
            number = number + 1
        all_logger.info('the number of mPDN rule is {}'.format(number))

    def get_trl8125_mac_address(self):
        return_value = subprocess.getoutput('cat /sys/class/net/{}/address'.format(self.rtl8125_ethernet_name))
        mac_address = ''.join(return_value)
        if not mac_address:
            raise LinuxRTL8125Error('fail to get mac address.')
        all_logger.info('mac adress is {}'.format(mac_address))
        return mac_address

    def mpdn_set_3_rule(self, mac_address):
        """
        1. delete all rules
        2. add rule
        """
        time.sleep(3)
        all_logger.info('start add mpdn rule')
        time.sleep(3)
        self.at_handler.send_at('At+qmap="mPDN_rule",0', 10)
        time.sleep(5)
        self.at_handler.send_at('At+qmap="mPDN_rule",1', 10)
        time.sleep(5)
        self.at_handler.send_at('At+qmap="mPDN_rule",2', 10)
        time.sleep(5)
        return_value1 = self.at_handler.send_at('At+qmap="mPDN_rule",0,1,0,1,1,"{}"'.format(mac_address), 20)
        if 'ERROR' in return_value1:
            all_logger.info(return_value1)
            raise LinuxRTL8125Error("add rule return error!")
        time.sleep(5)
        return_value2 = self.at_handler.send_at('At+qmap="mPDN_rule",1,2,2,1,1,"8c:ec:4b:cd:62:ed"', 20)
        if 'ERROR' in return_value2:
            all_logger.info(return_value2)
            raise LinuxRTL8125Error("add second rule return error!")
        time.sleep(5)
        return_value3 = self.at_handler.send_at('At+qmap="mPDN_rule",2,3,3,1,1,"8c:ec:4b:cd:62:ee"', 20)
        if 'ERROR' in return_value3:
            all_logger.info(return_value3)
            raise LinuxRTL8125Error("add third rule return error!")
        time.sleep(5)

    def mpdn_check_status(self):
        """
        AT+QMAP="mPDN_status"
        +QMAP: "mPDN_status",0(rule),1,1(ippt_status),1(backhaul_status)
        +QMAP: "mPDN_status",1,0,0,0
        +QMAP: "mPDN_status",2,0,0,0
        +QMAP: "mPDN_status",3,0,0,0

        OK
        """
        all_logger.info('start check mPDN status')
        rerurn_value = self.at_handler.send_at('AT+QMAP="mPDN_status"', 5)
        time.sleep(5)
        all_logger.info("{}".format(rerurn_value))
        rule_number = ''.join(re.findall(r'\+QMAP: "mPDN_status",([0-3]),[1-4],1,1', rerurn_value))
        if rule_number == '':
            raise LinuxRTL8125Error('have no rule connert!!!')
        elif rule_number == '0':
            all_logger.info('these rules are connected:{}.'.format(rule_number))
            return rule_number
        else:
            all_logger.info('these rules are connected:{}.'.format(rule_number))
            return rule_number

    def mpdn_add_2_pc_vlan(self):
        """
        SET route
        other:need apt install vlan
        """
        return_value1 = subprocess.getoutput('modprobe 8021q')
        all_logger.info('加载vlan模块modprobe 8021q{}'.format(return_value1))
        return_value2 = subprocess.getoutput('sudo ifconfig {} down'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo ifconfig {} down\n{}'.format(self.rtl8125_ethernet_name, return_value2))
        return_value3 = subprocess.getoutput('sudo ifconfig {} hw ether 8c:ec:4b:cd:62:ec up'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo ifconfig {} hw ether 8c:ec:4b:cd:62:ec up\n{}'.format(self.rtl8125_ethernet_name, return_value3))
        return_value4 = subprocess.getoutput('sudo vconfig add {} 1'.format(self.rtl8125_ethernet_name))
        all_logger.info('vconfig add {} 1\n{}'.format(self.rtl8125_ethernet_name, return_value4))
        return_value5 = subprocess.getoutput('sudo vconfig add {} 2'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo vconfig add {} 2\n{}'.format(self.rtl8125_ethernet_name, return_value5))
        self.get_trl8125_mac_address()
        return_value6 = subprocess.getoutput('sudo ifconfig {}.1 hw ether 8c:ec:4b:cd:62:ed up'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo ifconfig {}.1 hw ether 8c:ec:4b:cd:62:ed up\n{}'.format(self.rtl8125_ethernet_name, return_value6))
        return_value7 = subprocess.getoutput('sudo ifconfig {}.2 hw ether 8c:ec:4b:cd:62:ee up'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo ifconfig {}.2 hw ether 8c:ec:4b:cd:62:ee up\n{}'.format(self.rtl8125_ethernet_name, return_value7))
        time.sleep(10)
        return_value8 = subprocess.getoutput('ifconfig')
        all_logger.info('ifconfig\n{}'.format(return_value8))

    def mpdn_pc_get_ip_connect(self):
        """
        add 2 vlan for PC
        """
        return_value1 = subprocess.getoutput('sudo udhcpc -i {}'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo udhcpc -i {}\n{}'.format(self.rtl8125_ethernet_name, return_value1))
        return_value2 = subprocess.getoutput('sudo udhcpc -i {}.1'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo udhcpc -i {}.1\n{}'.format(self.rtl8125_ethernet_name, return_value2))
        return_value3 = subprocess.getoutput('sudo udhcpc -i {}.2'.format(self.rtl8125_ethernet_name))
        all_logger.info('sudo udhcpc -i {}.2\n{}'.format(self.rtl8125_ethernet_name, return_value3))
        time.sleep(10)
        return_value11 = subprocess.getoutput('ifconfig')
        all_logger.info('ifconfig\n{}'.format(return_value11))

    def mpdn_route_set(self):
        """
        route set for mpdn
        """
        return_value0 = subprocess.getoutput('echo 1 > /proc/sys/net/ipv4/ip_forward')
        all_logger.info('echo 1 > /proc/sys/net/ipv4/ip_forward\n{}'.format(return_value0))
        return_value1 = subprocess.getoutput('echo 0 > /proc/sys/net/ipv4/conf/{}/rp_filter'.format(self.rtl8125_ethernet_name))
        all_logger.info('echo 0 > /proc/sys/net/ipv4/conf/{}/rp_filter\n{}'.format(self.rtl8125_ethernet_name, return_value1))
        return_value2 = subprocess.getoutput('echo 0 > /proc/sys/net/ipv4/conf/{}.1/rp_filter'.format(self.rtl8125_ethernet_name))
        all_logger.info('echo 0 > /proc/sys/net/ipv4/conf/{}.1/rp_filter\n{}'.format(self.rtl8125_ethernet_name, return_value2))
        return_value3 = subprocess.getoutput('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter')
        all_logger.info('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter\n{}'.format(return_value3))

    def mpdn_ping_check_3_way(self):
        """
        ping after 3 way mPDN get ip
        """
        all_logger.info('start {} ping'.format(self.rtl8125_ethernet_name))
        # rerurn_ipv4_eth0 = subprocess.getoutput('ifconfig')
        # ipv4_eth0 = ''.join(re.findall(r'eth0: .*\n.*inet (\d+.\d+.\d+.\d+)', rerurn_ipv4_eth0))
        all_logger.info("ifconfig {} | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        ipv4_eth0 = subprocess.getoutput("ifconfig {} | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        all_logger.info('{}'.format(ipv4_eth0))
        return_value = subprocess.getoutput('ping www.baidu.com -c 10 -I {}'.format(ipv4_eth0))
        all_logger.info("{}".format(return_value))
        if '100% packet loss' in return_value or 'unknown host' in return_value:
            raise LinuxRTL8125Error("eth0 fail to ping www.baidu.com")

        all_logger.info('start {}.1 ping'.format(self.rtl8125_ethernet_name))
        # rerurn_ipv4_eth01 = subprocess.getoutput('ifconfig')
        # ipv4_eth01 = ''.join(re.findall(r'eth0.1:.*\n.*inet (\d+.\d+.\d+.\d+)', rerurn_ipv4_eth01))
        all_logger.info("ifconfig {}.1 | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        ipv4_eth01 = subprocess.getoutput("ifconfig {}.1 | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        all_logger.info('{}'.format(ipv4_eth01))
        return_value = subprocess.getoutput('ping www.baidu.com -c 10 -I {}'.format(ipv4_eth01))
        all_logger.info("{}".format(return_value))
        if '100% packet loss' in return_value or 'unknown host' in return_value:
            raise LinuxRTL8125Error("{}.1 fail to ping www.baidu.com".format(self.rtl8125_ethernet_name))

        all_logger.info('start {}.2 ping'.format(self.rtl8125_ethernet_name))
        # rerurn_ipv4_eth02 = subprocess.getoutput('ifconfig')
        # ipv4_eth02 = ''.join(re.findall(r'eth0.2:.*\n.*inet (\d+.\d+.\d+.\d+)', rerurn_ipv4_eth02))
        all_logger.info("ifconfig {}.2 | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        ipv4_eth02 = subprocess.getoutput("ifconfig {}.2 | grep 'inet'| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(self.rtl8125_ethernet_name))
        all_logger.info('{}'.format(ipv4_eth02))
        return_value = subprocess.getoutput('ping www.baidu.com -c 10 -I {}'.format(ipv4_eth02))
        all_logger.info("{}".format(return_value))
        if '100% packet loss' in return_value or 'unknown host' in return_value:
            raise LinuxRTL8125Error("{}.2 fail to ping www.baidu.com".format(self.rtl8125_ethernet_name))

    def mpdn_del_rule(self):
        """
        detele mPDN rule
        """
        all_logger.info('start detele mPDN rule')
        self.at_handler.send_at('At+qmap="mPDN_rule",0', 10)
        self.at_handler.send_at('At+qmap="mPDN_rule",1', 10)
        self.at_handler.send_at('At+qmap="mPDN_rule",2', 10)

    def mpdn_dis_vlan(self):
        """
        disbale mPDN vlan
        """
        all_logger.info('start disbale mPDN vlan')
        self.at_handler.send_at('at+qmap="vlan",2,"disable"', 5)
        self.at_handler.send_at('at+qmap="vlan",3,"disable"', 5)

    def exit_rtl8125_mode(self):
        """
        1. 执行AT+QCFG="data_interface",0,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",0 //启用RC模式（重启生效）
        3. 执行AT+QMAPWAC=0 //开启移动AP自动拨号（重启生效）
        """
        all_logger.info('exit rtl8125 mode')
        all_logger.info('开始关闭pcie net')
        return_value = self.at_handler.send_at('AT+QCFG="data_interface",0,0', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("关闭pcie net异常")

        all_logger.info('开始关闭RC模式')
        return_value = self.at_handler.send_at('AT+QCFG="pcie/mode",0', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("关闭RC模式异常")

        time.sleep(5)
        all_logger.info('关闭移动AP自动拨号')
        return_value = self.at_handler.send_at('AT+QMAPWAC=0', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("关闭AP自动拨号异常")

    def enter_rtl8125_mode(self):
        """
        1. 执行AT+QCFG="data_interface",1,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",1 //启用RC模式（重启生效）
        3. 执行AT+QETH="eth_driver","r8125" //选择rtl8125驱动（重启生效）
        4. 执行AT+QMAPWAC=1 //开启移动AP自动拨号（重启生效）
        :return: True，切换成功，False，切换失败
        """
        all_logger.info('enter rtl8125 mode')
        all_logger.info('开始打开pcie net')
        return_value = self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("打开pcie net异常")

        all_logger.info('开始启用RC模式')
        return_value = self.at_handler.send_at('AT+QCFG="pcie/mode",1', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("启用RC模式异常")

        all_logger.info('选择rtl8125驱动')
        return_value = self.at_handler.send_at('AT+QETH="eth_driver","r8125"', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("选择rtl8125驱动异常")
        all_logger.info('开启移动AP自动拨号')
        return_value = self.at_handler.send_at('AT+QMAPWAC=1', 0.6)
        if 'OK' not in return_value:
            raise LinuxRTL8125Error("开启移动AP自动拨号异常")

    def get_ipv4_with_timeout(self):
        for i in range(30):
            all_logger.info('get IPv4')
            ipv4 = subprocess.getoutput(
                'ifconfig {} | grep "inet " | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rtl8125_ethernet_name))
            if ipv4:
                all_logger.info('IPv4: {}'.format(ipv4))
                return ipv4
            time.sleep(1)
        else:
            raise LinuxRTL8125Error("Fail to get IPv4")

    @staticmethod
    def cfun04_check_network():
        all_logger.info("进行PC端PING测试，ping www.baidu.com -c 4")
        ping_data = subprocess.getoutput('ping www.baidu.com -c 4')
        all_logger.info("{}".format(ping_data))
        if 'unknown host' not in ping_data and '100% packet loss' not in ping_data and 'failure' not in ping_data:
            all_logger.info("异常！cfun0后仍可连接网络，请检查PC网线连接是否正确！")
            return False
        all_logger.info("PC连接网络失败，符合预期")
        return True

    def ping_module_and_PC_each_other(self, flag=True):
        """
        1. 模块debug内ping PC的IP
        2. PC ping模块内部的IP
        """
        # 启动线程
        time.sleep(3)
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        try:
            all_logger.info('开始获取模块内部IP')
            data = debug_port.exec_command('ifconfig')
            return_data = ''.join(re.findall(r'bridge0.*\n.*', data))
            ip_value = ''.join(re.findall(r'addr:(\d+.\d+.\d+.\d+)', return_data))
            if 'bridge0' not in data or ip_value == '':
                all_logger.info('{}'.format(ip_value))
                raise LinuxRTL8125Error("获取模块内部IP失败")
            else:
                all_logger.info('已获取模块内部IP为: {}'.format(ip_value))

            all_logger.info('开始获取PC端IP')
            all_logger.info("获取IPv4地址")
            rerurn_ipv4_eth0 = subprocess.getoutput('ifconfig')
            ipv4 = ''.join(re.findall(r'eth0: .*\n.*inet (\d+.\d+.\d+.\d+)', rerurn_ipv4_eth0))
            all_logger.info('{}'.format(ipv4))
            if ipv4 != '':
                all_logger.info('{}'.format(ipv4))
            else:
                all_logger.info("获取IPv4地址失败")
                all_logger.info(os.popen('ifconfig').read())
                return False
            all_logger.info("已获取PC端IP地址为：{}".format(ipv4))
            if flag:
                all_logger.info("开始模块内部和PC互ping测试")
                all_logger.info("PC端IP地址：{}".format(ipv4))
                all_logger.info('模块内部IP地址: {}'.format(ip_value))
                all_logger.info("开始PC>>>ping>>>模块内部IP，ping -c 4 -I {} {}".format(ipv4, ip_value))
                ping_data = os.popen("ping -c 4 -I {} {}".format(ipv4, ip_value)).read()
                all_logger.info(ping_data)
                if '0% packet loss' not in ping_data and '25% packet loss' not in ping_data and '50% packet loss' not in ping_data:
                    all_logger.info('ping失败')
                    return False
                all_logger.info("PC端IP地址：{}".format(ipv4))
                all_logger.info('模块内部IP地址: {}'.format(ip_value))
                all_logger.info("模块内部IP>>>ping>>>PC，ping -c 4 -I {} {}".format(ip_value, ipv4))
                debug_port.exec_command("ping -c 4 -I {} {}".format(ip_value, ipv4))
                time.sleep(5)
                all_logger.info('ctrl c get msg')
                ping_data_module_final = debug_port.exec_command("\x03")
                all_logger.info(ping_data_module_final)
                if '100% packet loss' in ping_data_module_final:
                    all_logger.info('ping失败')
                    return False
                all_logger.info('模块内部和PC互ping测试结束')
                debug_port.close_debug()
                return True
        finally:
            debug_port.close_debug()

    @staticmethod
    def ping_get_connect_status(ipv6_address="2402:f000:1:881::8:205", flag=True, ipv6_flag=False):
        """
        1. 查询PC是否获得IP
        2. ping测试
        """
        ipv4 = ''
        ipv6 = ''
        interface_name = '以太网适配器'
        for i in range(30):
            all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
            connection_dic = {}
            ipconfig = os.popen("ipconfig").read()
            all_logger.debug(ipconfig)
            ipconfig = re.sub('\n.*?\n\n\n', '', ipconfig)  # 去除\nWindows IP 配置\n\n\n
            ipconfig_list = ipconfig.split('\n\n')
            for m in range(0, len(ipconfig_list), 2):  # 步进2，i为key，i+1为value
                connection_dic[ipconfig_list[m]] = ipconfig_list[m + 1]
            for k, v in connection_dic.items():
                if interface_name in k:
                    ipv6 = re.findall(r"\s{3}IPv6.*?:\s(.*?)\n", v)
                    ipv4 = re.findall(r"\s{3}IPv4.*?:\s(.*?)\n", v)
                    if ipv6:
                        ipv6 = ''.join(ipv6[0])
                    if ipv4:
                        ipv4 = ''.join(ipv4[0])
            if (ipv6_flag and ipv6) or (ipv6_flag is False and ipv4):
                time.sleep(1)
                break
            else:
                time.sleep(1)
        else:
            all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            return False
        if ipv6_flag:
            all_logger.info("获取IPV6地址成功：{}".format(ipv6))
            all_logger.info("进行PING检查，ping -S {} {}".format(ipv6, ipv6_address))
            if flag:
                ping_data = os.popen("ping -S {} {}".format(ipv6, ipv6_address)).read()
                all_logger.info(ping_data)
                if '(0% 丢失' not in ping_data and '(25% 丢失' not in ping_data and '(50% 丢失' not in ping_data:
                    return False
                return True
            else:
                subprocess.Popen("ping -S {} {}".format(interface_name, ipv6_address), shell=True)
                time.sleep(1)
        else:
            all_logger.info("获取IPV4地址成功：{}".format(ipv4))
            all_logger.info("进行PC端PING测试，ping -4 -S {} www.baidu.com".format(ipv4))
            if flag:
                ping_data = os.popen("ping -4 -S {} www.baidu.com".format(ipv4)).read()
                all_logger.info(ping_data)
                if '(0% 丢失' not in ping_data and '(25% 丢失' not in ping_data and '(50% 丢失' not in ping_data:
                    all_logger.info("PC端ping失败")
                    return False
                all_logger.info("进行PC端PING测试结束")
                return True
            else:
                subprocess.Popen("ping -4 -S {} -l 10240 www.baidu.com".format(interface_name), shell=True)
                time.sleep(1)

    def check_network_card(self):
        """
        Debug输入ifconfig命令检查brige0是否获得IP
        :return: True，检查成功，False，检查失败
        """
        # 启动线程
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()

        try:
            all_logger.info('check network card')
            time.sleep(20)
            data = debug_port.exec_command('ifconfig')
            all_logger.info('ifconfig data : {}'.format(data))
            return_data = ''.join(re.findall(r'bridge0.*\n.*', data))
            ip_value = ''.join(re.findall(r'addr:(\d+.\d+.\d+.\d+)', return_data))
            if 'bridge0' not in data or ip_value == '':
                raise LinuxRTL8125Error("network card bridge0 not find or don't get IP.")
            else:
                all_logger.info('already find network card bridge0 and IP: {}'.format(ip_value))
        finally:
            all_logger.info('check network card end')
            debug_port.close_debug()

    def check_rtl8125_pci(self):
        """
        Debug输入命令lspci检查RTL8125的PCI
        :return: True，检查成功，False，检查失败
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
            if '10ec:8125' not in data:
                raise LinuxRTL8125Error(
                    "RTL8125 not find in return value!!! please check EVB setting or other that can be affected.")
            else:
                all_logger.info('already find pci of RTL8125 "10ec:8125"')
        finally:
            all_logger.info('check pci end')
            debug_port.close_debug()


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
