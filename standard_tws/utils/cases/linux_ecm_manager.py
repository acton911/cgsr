from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import ECMError
from utils.functions.linux_api import LinuxAPI
import subprocess
import time
import re
import os
from utils.functions.gpio import GPIO
import requests
from utils.operate.reboot_pc import Reboot


class LinuxECMManager:
    def __init__(self, at_port, dm_port, network_card_name, local_network_card_name, phone_number, params_path):
        self.driver_check = DriverChecker(at_port, dm_port)
        self.at_port = at_port
        self.dm_port = dm_port
        self.phone_number = phone_number
        self.at_handle = ATHandle(at_port)
        self.network_card_name = network_card_name
        self.local_network_card_name = local_network_card_name
        self.gpio = GPIO()
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.operator = self.at_handle.get_operator()
        self.reboot = Reboot(at_port, dm_port, params_path)

    def check_qmapwac(self):
        """
        指令查询AQC拨号是否正常
        :return: None
        """
        qmapwac = self.at_handle.send_at("AT+QMAPWAC?")
        if '1' not in ''.join(re.findall(r'\+QMAPWAC: \d', qmapwac)):
            raise ECMError('AT+QMAPWAC?返回值不正常')

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是usb模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)

    def chang_net(self, network=''):
        """
        切换网络制式
        :param network: 需要切换的网络制式:AUTO, LTE等
        :return: None
        """
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",{}'.format(network))
        time.sleep(3)   # 等待一会再查询，否则可能切换不及时
        if network not in self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref"'):
            raise ECMError('网络制式切换失败')

    def send_sms_check_network(self):
        """
        拨号过程中发短信检查网络是否正常
        :return: None
        """
        self.send_msg()

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
        self.at_handle.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        all_logger.info('{}'.format(self.phone_number))
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        self.at_handle.readline_keyword('+CMTI', timout=300)
        time.sleep(5)

    def dial_check_network(self):
        """
        拨号后进行PING连接，检查网路是否正常
        :return: None
        """
        _operator_mapping = {
            'CMCC': "10086",
            '中国联通': "10010",
            '中国电信': "10000",
        }
        operator_number = _operator_mapping[self.operator]
        self.at_handle.send_at("ATD{};".format(operator_number))
        LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        self.at_handle.send_at("ATH")

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
        raise ECMError('卸载Gobinet驱动失败')

    def check_ecm_driver(self, is_disappear=False):    # 检测ecm驱动
        """
        检测ECM拨号驱动是否正常加载或消失
        :param is_disappear: True: 检测ECM拨号正常消失；False: 检测ECM拨号正常加载
        :return:
        """
        lsusb_value = os.popen('lsusb -t').read()
        all_logger.info("lsusb -t查询返回:\n")
        all_logger.info(lsusb_value)
        if 'cdc_ether' in lsusb_value and not is_disappear:
            ifconfig_val = os.popen('ifconfig').read()
            all_logger.info(ifconfig_val)
            if self.network_card_name in ifconfig_val:
                all_logger.info('ecm驱动检测成功')
                return True
            else:
                all_logger.info('未检测到ecm驱动')
                raise ECMError('未检测到ecm驱动')
        if is_disappear and 'cdc_ether' not in lsusb_value:
            all_logger.info('ecm驱动消失')
            return True

    def check_moudle_ip(self):
        """
        检测模块拨号状态及IP类型检测
        :return: True
        """
        cgdcont_val = self.at_handle.send_at('AT+CGDCONT?')
        if 'IPV4V6' not in ''.join(re.findall(r'\+CGDCONT: 1,.*', cgdcont_val)):
            all_logger.info(cgdcont_val)
            raise ECMError('模块拨号类型非IPV4V6')
        cgp_val = self.at_handle.send_at('AT+CGPADDR')
        ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', cgp_val)
        if not ip:
            all_logger.info(cgp_val)
            raise ECMError('模块拨号类型非IPV4V6')
        qnet_val = self.at_handle.send_at('AT+QNETDEVSTATUS?')
        if '4' not in qnet_val and '6' not in qnet_val:
            all_logger.info(qnet_val)
            raise ECMError('模块拨号类型非IPV4V6')
        all_logger.info('模块拨号IP类型确认正常')
        return True

    def dump_check(self):
        """
        检测模块是否Dump
        :return: None
        """
        for i in range(30):
            port_list = self.driver_check.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                time.sleep(1)
                continue
            elif self.at_port not in port_list and self.dm_port in port_list:
                raise ECMError('模块DUMP')

    def sim_lock(self):
        """
        SIM卡锁PIN，重启后检查是否锁PIN成功
        :return: True
        """
        self.at_handle.send_at('AT+CLCK="SC",1,"1234"', timeout=5)
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        time.sleep(3)
        return_val = self.at_handle.send_at('AT+CLCK="SC",2', timeout=5)
        if '+CLCK: 1' in return_val:
            return True
        else:
            raise ECMError('SIM卡锁pin失败')

    def check_dial_status(self, keyword='', keyword1=''):
        """
        确认拨号成功后的QNETDEVSTATUS值是否正常: +QNETDEVSTATUS: 0,1,4,1', '+QNETDEVSTATUS: 0,1,6,1
        :param keyword: 需要检测的关键词
        :param keyword1: 需要检测的关键词
        :return: None
        """
        ret_val = self.at_handle.send_at('AT+QNETDEVSTATUS?')
        if keyword not in ret_val and keyword1 not in ret_val:
            raise ECMError('拨号状态不正常')
        else:
            all_logger.info('拨号状态正常')

    def check_dial(self):
        """
        确认模块不能注网时的QNETDEVSTATUS值
        :return:None
        """
        self.at_handle.send_at('AT+QNETDEVSTATUS=1')
        qnet_val = self.at_handle.send_at('AT+QNETDEVSTATUS?')
        if qnet_val.count('0') > 1:
            all_logger.info(qnet_val)
            raise ECMError('当前拨号状态不正常')

    def disconnect_dial(self):
        """
        断开ECM拨号
        :return: True
        """
        nmc = subprocess.run('nmcli connection', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             shell=True)
        ls = re.findall(r'\n.*{}'.format(self.network_card_name), nmc.stdout)[0].replace('\n', '').split(' ')
        cmd = ls[0] + '\\ ' + ls[1] + '\\ ' + ls[2]
        delete = subprocess.run('nmcli connection delete {}'.format(cmd), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=True, text=True)
        if '已成功删除' in delete.stdout:
            all_logger.info('成功断开ECM拨号')
            return True
        else:
            raise ECMError('断开ECM拨号失败')

    def dial_reset_many(self):
        """
        CFUN01切换验证重复拨号断开拨号
        :return: None
        """
        time.sleep(10)
        self.at_handle.send_at('AT+QNETDEVSTATUS=1')
        LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        for i in range(5):
            all_logger.info('Send: AT+CFUN=0')
            self.at_handle.readline_keyword(at_flag=True, at_cmd='AT+CFUN=0', keyword1='+QNETDEVSTATUS: 1,0,6,1',
                                            keyword2='+QNETDEVSTATUS: 1,0,4,1')
            all_logger.info('拨号状态为0')
            self.at_handle.send_at('AT+CFUN=1', timeout=15)
            time.sleep(10)
            self.check_dial_status('+QNETDEVSTATUS: 1,1,6,1', '+QNETDEVSTATUS: 1,1,4,1')
            time.sleep(10)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)

    def connect_local_net(self, is_connect=True):
        """
        设置断开或者连接本地网
        :param is_connect: True:连接本地网并断开拨号，False: 断开本地网并连接拨号
        :return: True
        """
        if is_connect:
            os.popen('ifconfig {} up'.format(self.local_network_card_name)).read()
            for i in range(20):
                local_ip_re = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', os.popen('ifconfig {}'.format
                                                                                        (self.local_network_card_name)).read())
                if local_ip_re:
                    all_logger.info('本地网连接成功')
                    time.sleep(10)
                    return True
                time.sleep(3)
            else:
                raise ECMError('本地网连接失败')
        else:
            os.popen('ifconfig {} down'.format(self.local_network_card_name)).read()
            for i in range(20):
                local_ip_re = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', os.popen('ifconfig {}'.format
                                                                                        (self.local_network_card_name)).read())
                if not local_ip_re:
                    all_logger.info('本地网断开成功')
                    time.sleep(3)
                    return True
                time.sleep(3)
            else:
                raise ECMError('本地网断开失败')

    def connect_ecm_net(self, is_connect=True):
        """
        连接或断开ECM拨号
        :param is_connect:连接ECM拨号，False:断开ECM拨号
        :return: True
        """
        if is_connect:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} up'.format(self.network_card_name))
            all_logger.info('ifconfig {} up\r\n{}'.format(self.network_card_name, ifconfig_down_value))

        else:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.network_card_name))
            all_logger.info('ifconfig {} down\r\n{}'.format(self.network_card_name, ifconfig_down_value))

    def get_netcard_ip(self, is_success=True):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        ifconfig_value = os.popen('ifconfig usb0').read()
        try:
            re_ifconfig = re.findall(r'{}.*\n(.*)'.format(self.network_card_name), ifconfig_value)[0].strip()
            ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
        except IndexError:
            pass
        if is_success:
            if ip:
                all_logger.info('获取IP地址正常,IP地址为{}'.format(ip))
                return ip
            else:
                raise ECMError('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                raise ECMError('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))
