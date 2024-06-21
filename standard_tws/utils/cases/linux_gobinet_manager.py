import subprocess
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI, PINGThread
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxGobiNetError
import requests
import time
import os
import re
from utils.operate.reboot_pc import Reboot


class LinuxGobiNetManager:
    def __init__(self, at_port, dm_port, gobinet_driver_path, gobinet_network_card_name, extra_ethernet_name,
                 phone_number, params_path):
        self.linux_api = LinuxAPI()
        self.at_port = at_port
        self.phone_number = phone_number
        self.at_handler = ATHandle(self.at_port)
        self.gobinet_driver_path = gobinet_driver_path
        self.gobinet_network_card_name = gobinet_network_card_name
        self.extra_ethernet_name = extra_ethernet_name
        self.driver = DriverChecker(at_port, dm_port)
        self.operator = self.at_handler.get_operator()
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.reboot = Reboot(at_port, dm_port, params_path)

    def set_linux_gobinet(self):
        """
        设置模块拨号方式为GobiNet
        :return: None
        """
        all_logger.info("设置USBNET为0")
        self.at_handler.send_at('AT+QCFG="USBNET",0')

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是usb模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handler.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handler.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
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
        self.at_handler.send_at("ATD{};".format(operator_number))
        self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        self.at_handler.send_at("ATH")

    @staticmethod
    def remove_all_network_card_driver():
        """
        删除所有除了GobiNet之外的网卡
        :return: None
        """
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

    @staticmethod
    def load_gobinet_drive():
        """
        加载GobiNet驱动
        :return:
        """
        all_logger.info('开始卸载所有网卡驱动')
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

        time.sleep(5)
        all_logger.info('开始加载GobiNet网卡驱动')
        subprocess.run("modprobe -a GobiNet", shell=True)

    def compile_gobinet_driver(self):
        """
        根据传入的GobiNet驱动路径进行编译
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.gobinet_driver_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.gobinet_driver_path]), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.gobinet_driver_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.gobinet_driver_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.gobinet_driver_path]))
        s = subprocess.run(' '.join(['make', 'install', '--directory', self.gobinet_driver_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

    def check_gobinet_driver(self):
        """
        检查GobiNet网卡名称是否正确
        :return: None
        """
        # 检查lsusb -t 是否包含GobiNet字符串
        all_logger.info("lsusb -t")
        s = subprocess.run('lsusb -t', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        all_logger.info(s.stdout)
        if 'GobiNet' not in s.stdout:
            all_logger.info("lsusb -t未检查到GobiNet驱动")
            raise LinuxGobiNetError("lsusb -t未检查到GobiNet驱动")

        # 检查ifconfig是否有网卡
        all_logger.info("ifconfig {}".format(self.gobinet_network_card_name))
        s = subprocess.run("ifconfig {}".format(self.gobinet_network_card_name), shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
        all_logger.info(s.stdout)
        if 'not found' in s.stdout:
            all_logger.info("ifconfig {}未检查到GobiNet 网卡".format(self.gobinet_network_card_name))
            raise LinuxGobiNetError("ifconfig {}未检查到GobiNet 网卡".format(self.gobinet_network_card_name))

    def gobinet_non_network_check(self):
        """
        GobiNet拨号方式没有网络检查
        :return:
        """
        ping = PINGThread(times=5, network_card_name=self.gobinet_network_card_name)
        ping.start()
        ping.join()
        ping.non_network_get_result()

    def send_sms_check_network(self):
        """
        进行PING的时候发送短信检查网络是否正常
        :return: None
        """
        self.send_msg()

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handler.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
        self.at_handler.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
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
        self.at_handler.readline_keyword('+CMTI', timout=300)
        time.sleep(5)

    def get_netcard_ip(self, is_success=True):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        ifconfig_value = os.popen('ifconfig usb0').read()
        try:
            re_ifconfig = re.findall(r'{}.*\n(.*)'.format(self.gobinet_network_card_name), ifconfig_value)[0].strip()
            ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
        except IndexError:
            pass
        if is_success:
            if ip:
                all_logger.info('获取IP地址正常,IP地址为{}'.format(ip))
                return ip
            else:
                all_logger.info('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
                raise LinuxGobiNetError('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                all_logger.info('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))
                raise LinuxGobiNetError('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))
