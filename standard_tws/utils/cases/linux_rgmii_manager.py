import os
import subprocess
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxRGMIIError
from utils.functions.linux_api import LinuxAPI
import re
import time
import requests


class LinuxRGMIIManager:
    def __init__(self, at_port, dm_port, debug_port, rgmii_ethernet_name, pc_ethernet_name, phone_number):
        self.linux_api = LinuxAPI()
        self.at_port = at_port
        self.at_handler = ATHandle(self.at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.rgmii_ethernet_name = rgmii_ethernet_name
        self.pc_ethernet_name = pc_ethernet_name
        self.debug_port = debug_port
        self.default_apns = None
        self.linux_api = LinuxAPI()
        self.phone_number = phone_number
        self.url = 'https://stcall.quectel.com:8054/api/task'

    def set_usbnet_0(self):
        """
        Set AT+QCFG="USBNET",0 , eliminate interface from other dialing.
        :return: None
        """
        usbnet = self.at_handler.send_at('AT+QCFG="USBNET"')
        if ',0' in usbnet:
            all_logger.info('AT+QCFG="USBNET" is 0')
        else:
            all_logger.info("set USBNET 0")
            self.at_handler.send_at('AT+QCFG="USBNET",0')
            self.at_handler.send_at("AT+CFUN=1,1", 3)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()

    def qeth_attr_check(self):
        qeth_standard = ['+QETH: "rgmii",("enable","disable"),(0,1),(-1,0,1),(1-8)',
                         '+QETH: "ipptmac",<host_mac_addr>',
                         '+QETH: "mac_address",<rgmii_mac_addr>',
                         '+QETH: "speed",("0M","10M","100M","1000M")',
                         '+QETH: "an",("on","off")',
                         '+QETH: "mac_mode",(0,1)',
                         '+QETH: "eth_driver",<eth_driver>,(0,1)',
                         '+QETH: "eth_at",("enable","disable")']
        all_logger.info('\nqeth_standard: \n{}'.format('\n'.join(qeth_standard)))

        qeth = self.at_handler.send_at("AT+QETH=?")
        qeth_regex = re.findall(r"(\+QETH:\s.*?)\s", qeth)
        all_logger.info('\nqeth_regex: \n{}'.format('\n'.join(qeth_regex)))

        a_b_diff = set(qeth_standard).difference(set(qeth_regex))
        b_a_diff = set(qeth_regex).difference(set(qeth_standard))
        if a_b_diff or b_a_diff:
            raise LinuxRGMIIError("AT+QETH=? Checked Error! Diff: {}, Plese Check".format(a_b_diff if a_b_diff else b_a_diff))

        return True

    def qeth_check_default(self):
        self.at_handler.send_at('AT+QETH="RGMII","disable",1')  # set voltage 0

        standard = ['+QETH: "RGMII","DISABLE",1,-1',
                    '+QETH: "RGMII",0,1',
                    '+QETH: "RGMII",0,2',
                    '+QETH: "RGMII",0,3',
                    '+QETH: "RGMII",0,4']

        qeth_rgmii = self.at_handler.send_at('AT+QETH="RGMII"')
        if 'OK' not in qeth_rgmii or 'ERROR' in qeth_rgmii:
            raise LinuxRGMIIError("AT+QETH=? return Error!")

        for s in standard:
            if s not in standard:
                raise LinuxRGMIIError("AT+QETH=? return Error!")

        all_logger.info("AT+QETH=? default check success!")

        return True

    def rgmii(self, status, voltage, mode='', profile_id='', parallel=(0, 0), check=True):
        """
                RGMII         status       voltage  mode   profile_id
        +QETH: "rgmii",("enable","disable"),(0,1),(-1,0,1),(1-8)
        status : ENABLE, DISABLE
        mode : 0 : COMMON-RGMII ; 1 : IPPassthrough
        voltage : default: 1: 2.5V ; 0, 1.8V
        """
        # set
        rgmii_at = f'AT+QETH="RGMII","{status}",{voltage}'
        if mode != '':
            rgmii_at += ',{}'.format(mode)
        if profile_id:
            rgmii_at += ',{}'.format(profile_id)
        rgmii_dial_result = self.at_handler.send_at(rgmii_at, timeout=30)  # TODO：此处超时时间需要检查

        # check
        if check:
            rgmii_check_result = self.at_handler.send_at('AT+QETH="RGMII"', 15)
            line_0 = '+QETH: "RGMII","{}",{},{}'.format(status.upper(), voltage, '-1' if status.upper() == 'DISABLE' else mode)
            line_1 = '+QETH: "RGMII",{},{}'.format(0 if mode == '' or status.upper() == 'DISABLE' else 1, 1 if not profile_id else profile_id)
            line_2 = '+QETH: "RGMII",{},{}'.format(2 if parallel[0] else 0, parallel[1] if parallel[1] else 2)
            line_3 = '+QETH: "RGMII",0,3'
            line_4 = '+QETH: "RGMII",0,4'
            all_check_info_list = [line_0, line_1, line_2, line_3, line_4]
            all_logger.info("all_check_info_list: {}".format(all_check_info_list))
            for info in all_check_info_list:
                if info not in rgmii_check_result:
                    all_logger.error('AT+QETH="RGMII" not found {}.'.format(info))
                    raise LinuxRGMIIError('AT+QETH="RGMII" not found {}.'.format(info))

        self.restart_rgmii_network_card()  # TODO: 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
        if status == "enable":
            # 连接网卡、防止网卡不自动连接
            s_udhcpc = subprocess.getoutput(f'udhcpc -i {self.rgmii_ethernet_name}')
            all_logger.info(f"udhcpc -i {self.rgmii_ethernet_name} : {s_udhcpc}")

        return rgmii_dial_result

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

    def ipptmac_check_default(self):
        ipptmac = self.at_handler.send_at('AT+QETH="ipptmac"', 3)
        all_logger.info('ippt_mac: {}'.format(ipptmac))
        ipptmac_regex = re.findall(r'\S{2}:\S{2}:\S{2}:\S{2}:\S{2}:\S{2}', ipptmac)
        all_logger.info('ipptmac_regex: {}'.format(ipptmac_regex))
        if not ipptmac_regex or "OK" not in ipptmac:
            raise LinuxRGMIIError("AT+QETH='ipptmac' return Error!")

    def ipptmac_set_check(self):
        all_logger.info('ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name))
        pc_ethernet_orig_mac = subprocess.getoutput('ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name))
        self.at_handler.send_at(f'AT+QETH="ipptmac",{pc_ethernet_orig_mac}', 3)
        qeth_ipptmac = self.at_handler.send_at('AT+QETH="ipptmac"', 3)
        if pc_ethernet_orig_mac not in qeth_ipptmac:
            raise LinuxRGMIIError("MAC code check failed after write MAC code.")

        self.at_handler.send_at("AT+CFUN=1,1")
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.at_handler.check_network()
        qeth_ipptmac = self.at_handler.send_at('AT+QETH="ipptmac"', 3)
        if pc_ethernet_orig_mac not in qeth_ipptmac:
            raise LinuxRGMIIError("MAC code check failed after write and restart.")

    def at_get_mac_address(self):
        mac_address = self.at_handler.send_at('AT+QETH="MAC_ADDRESS"', 3)
        mac_address_regex = ''.join(re.findall(r'\+QETH:\s"mac_address",(\S{2}:\S{2}:\S{2}:\S{2}:\S{2}:\S{2})', mac_address))
        all_logger.info("mac_address_regex: {}".format(mac_address_regex))
        if not mac_address_regex:
            raise LinuxRGMIIError('AT+QETH="MAC_ADDRESS" fail to get mac address.')
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
            raise LinuxRGMIIError("Switch Fastboot mode failed.")

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

    def speedtest(self, network_card):
        for i in range(3):
            cache = ''
            s = subprocess.Popen('speedtest --accept-license -I {}'.format(network_card), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            all_logger.info('开始测速：speedtest --accept-license -I {}'.format(network_card))
            while s.poll() is None:
                data = s.stdout.readline().decode('utf-8', 'replace')
                if data:
                    all_logger.info('[SPEEDTEST] {}'.format(data))
                    cache += data
                    download_speed = ''.join(re.findall(r'ownload:\s+(\d+\.\d+) Mbps', cache))
                    if download_speed:
                        try:
                            out, err = s.communicate(timeout=0.1)
                        except subprocess.TimeoutExpired:
                            pass
                        s.terminate()
                        s.wait()
                        all_logger.info('Speedtest test download speed is {} Mbps'.format(int(float(download_speed))))
                        return int(float(download_speed))
        else:
            raise LinuxRGMIIError("Fail to get max download speed via speedtest")

    def qeth_an_check_default(self):
        an = self.at_handler.send_at('AT+QETH="AN"', 3)
        all_logger.info(an)
        if '+QETH: "an","on"' not in an:
            raise LinuxRGMIIError('AT+QETH="AN" default check failed.')

    def qeth_speed_check_default(self):
        speed = self.at_handler.send_at('AT+QETH="SPEED"', 3)
        if '+QETH: "speed","0M"' not in speed:
            raise LinuxRGMIIError('AT+QETH="SPEED" default check failed.')

    def qeth_dm_check_default(self):
        dm = self.at_handler.send_at('AT+QETH="DM"', 3)
        if '+QETH: "dm","full"' not in dm:
            raise LinuxRGMIIError('AT+QETH="DM" default check failed.')

    def ethtool_get_speed(self):
        all_logger.info('ethtool {} | grep Speed'.format(self.rgmii_ethernet_name))
        out = subprocess.getoutput('ethtool {} | grep Speed'.format(self.rgmii_ethernet_name))
        all_logger.info(out)
        speed = ''.join(re.findall(r'\d+', out))
        if not speed:
            raise LinuxRGMIIError("fail to get {} speed".format(self.rgmii_ethernet_name))
        return int(speed)

    def ethtool_set_speed(self, speed):
        s = subprocess.getoutput('ethtool -s {} speed {} duplex full'.format(self.rgmii_ethernet_name, speed))
        all_logger.info(s)

    def ethtool_set_speed_autonegoff(self, speed):
        s = subprocess.getoutput('ethtool -s {} speed {} duplex full  autoneg off '.format(self.rgmii_ethernet_name, speed))
        all_logger.info(s)

    def ethtool_set_speed_autonegon(self, speed):
        s = subprocess.getoutput('ethtool -s {} speed {} duplex full  autoneg on '.format(self.rgmii_ethernet_name, speed))
        all_logger.info(s)

    def common_connect(self):
        self.rgmii(status="enable", voltage=1, mode=0)  # Common
        self.common_connect_check()

    def common_connect_check(self):
        # get ipv4
        ipv4 = self.get_network_card_ipv4(www=False)
        self.get_network_card_ipv6()

        # wait 10 seconds
        all_logger.info("wait 10 seconds")
        time.sleep(10)

        # check ipv4
        if ipv4.startswith('192.168') is False:
            raise LinuxRGMIIError("Common RGMII IPv4 not start with 192.168.")

        # check connect ipv4
        self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name)

        # check connect ipv6
        self.linux_api.ping_get_connect_status(ipv6_flag=True, network_card_name=self.rgmii_ethernet_name)

    def ip_pass_through_connect_check(self):
        # get ipv4
        ipv4 = self.get_network_card_ipv4(www=True)
        self.get_network_card_ipv6()

        # wait 10 seconds
        all_logger.info("wait 10 seconds")
        time.sleep(10)

        # check ipv4
        if ipv4.startswith('192.168') is True:
            raise LinuxRGMIIError("IP Passthrough RGMII IPv4 start with 192.168.")

        # check connect ipv4
        self.linux_api.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name)

        # check connect ipv6
        self.linux_api.ping_get_connect_status(ipv6_flag=True, network_card_name=self.rgmii_ethernet_name)

    def eth_set_get_speed(self, speed):
        return_value = self.at_handler.send_at('AT+QETH="SPEED","{}M"'.format(speed), 3)
        if "OK" not in return_value:
            raise LinuxRGMIIError('AT+QETH="SPEED","{}M" fail to set speed.'.format(speed))

        return_value = self.at_handler.send_at('at+qeth="SPEED"')
        return_value_regex = ''.join(re.findall(r'"(\d+)M', return_value))
        if str(speed) not in return_value_regex:
            raise LinuxRGMIIError('at+qeth="SPEED" check failed after set speed to {} Mbps'.format(speed))

    def eth_set_get_speed_1000(self):
        self.eth_set_get_speed(1000)

    def dmz_default_check(self):
        data = self.at_handler.send_at('AT+QDMZ=?', 3)
        if "<IP_address>\r\n\r\nOK\r\n" not in data:
            raise LinuxRGMIIError('AT+QDMZ=? default check failed.')

        data = self.at_handler.send_at('AT+QDMZ', 3)
        if '+QDMZ: 0,4\r\n+QDMZ: 0,6\r\n\r\nOK' not in data:
            raise LinuxRGMIIError('AT+QDMZ default check failed.')

    def print_ip(self):
        s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name))
        all_logger.info(s)

    def get_network_card_ipv4(self, www=False):
        out = None
        for i in range(30):
            out = subprocess.getoutput('ifconfig {} | grep "inet " | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name))
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
            s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name))
            all_logger.info(s)
            if www:
                raise LinuxRGMIIError("IP Passthrough RGMII 拨号模式，未获取到公网IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))
            else:
                raise LinuxRGMIIError("Common RGMII 拨号模式，未获取到192.168.开头的IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))

    def get_network_card_ipv6(self):
        for i in range(30):
            out = subprocess.getoutput('ifconfig {} | grep "inet6 24" | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name))
            if out and out.startswith('24'):
                all_logger.info(f"IPv6 address is: {repr(out)}")
                return out
            else:
                time.sleep(1)
                continue
        else:
            s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name))
            all_logger.info(s)
            raise LinuxRGMIIError('Fail to get ipv6 address')

    def eth_speed_reset(self):
        self.ethtool_set_speed(1000)
        self.at_handler.send_at('AT+QETH="AN","ON"')

    def get_ipv4_with_timeout(self):
        for i in range(30):
            all_logger.info('get IPv4')
            ipv4 = subprocess.getoutput('ifconfig {} | grep "inet " | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name))
            all_logger.info(f'get_ipv4_status: {ipv4}')
            if ipv4:
                all_logger.info('IPv4: {}'.format(ipv4))
                return ipv4
            time.sleep(1)
        else:
            raise LinuxRGMIIError("Fail to get IPv4")

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

    def restart_rgmii_network_card(self):
        # TODO: 20.04.3系统RGMII拨号后需要重启网卡，需要进一步验证，可能要删除
        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} down')
        all_logger.info(f"ifconfig {self.rgmii_ethernet_name} down: {s}")

        all_logger.info('wait 0.5 seconds')
        time.sleep(0.5)

        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} up')
        all_logger.info(f"ifconfig {self.rgmii_ethernet_name} up: {s}")

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
                    raise LinuxRGMIIError('未检测到ecm驱动')
            if is_disappear and 'cdc_ether' not in check_cmd_val:
                all_logger.info('ecm驱动消失')
                check_cmd.terminate()
                return True
            if time.time() - check_time > 2:
                all_logger.info('未检测到ecm驱动')
                check_cmd.terminate()
                raise LinuxRGMIIError('检测驱动超时')

    @staticmethod
    def modprobe_driver():
        """
        卸载WWAN和GobiNet驱动
        :return: True
        """
        for i in range(3):
            all_logger.info('modprobe -r GobiNet卸载Gobinet驱动')
            all_logger.info(os.popen('modprobe -r GobiNet').read())
            all_logger.info('modprobe -r qmi_wwan卸载qmi_wwan驱动')
            all_logger.info(os.popen('modprobe -r qmi_wwan').read())
            check_modprobe = os.popen('lsusb -t').read()
            all_logger.info('卸载驱动后查看驱动情况:\n')
            all_logger.info(check_modprobe)
            if 'GobiNet' not in check_modprobe and 'qmi_wwan' not in check_modprobe:
                all_logger.info('驱动卸载成功')
                return True
        raise LinuxRGMIIError('卸载Gobinet驱动失败')

    def reset_usbnet_0(self):
        self.at_handler.send_at('AT+QCFG="USBNET",0', timeout=3)
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        all_logger.info('wait 10 seconds')
        time.sleep(10)
