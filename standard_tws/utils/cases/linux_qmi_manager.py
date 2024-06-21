from utils.operate.at_handle import ATHandle
from utils.operate.reboot_pc import Reboot
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import QMIError
from utils.functions.linux_api import LinuxAPI
import subprocess
import time
import os
import re


class LinuxQMIManager:
    def __init__(self, at_port, dm_port, wwan_path, network_card_name, extra_ethernet_name, params_path):
        self.linux_api = LinuxAPI()
        self.driver_check = DriverChecker(at_port, dm_port)
        self.at_port = at_port
        self.dm_port = dm_port
        self.at_handle = ATHandle(at_port)
        self.wwan_path = wwan_path
        self.extra_ethernet_name = extra_ethernet_name
        self.network_card_name = network_card_name
        self.operator = self.at_handle.get_operator()
        self.reboot = Reboot(at_port, dm_port, params_path)

    def enter_qmi_mode(self):
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        time.sleep(2)
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",NR5G')
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()

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
        self.linux_api.ping_get_connect_status()
        self.at_handle.send_at("ATH")

    @staticmethod
    def modprobe_driver():
        """
        卸载GobiNet驱动
        :return: True
        """
        all_logger.info('开始卸载GobiNet,qmi_wwan网卡驱动')
        network_types = ['qmi_wwan', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

    def load_wwan_driver(self):
        """
        编译WWAN驱动
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.wwan_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.wwan_path]), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'install', '--directory', self.wwan_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

    @staticmethod
    def load_qmi_wwan_q_drive():
        """
        加载qmi驱动
        :return:
        """
        all_logger.info('开始卸载所有网卡驱动')
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

        time.sleep(5)
        all_logger.info('开始加载qmi_wwan_q网卡驱动')
        subprocess.run("modprobe -a qmi_wwan_q", shell=True)

    @staticmethod
    def check_wwan_driver(is_disappear=False):
        """
        检测wwan驱动是否加载成功
        :param is_disappear: False：检测WWAN驱动正常加载；True：检测WWAN驱动正常消失
        :return: True
        """
        check_cmd = subprocess.Popen('lsusb -t', stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, shell=True)
        check_time = time.time()
        all_logger.info("lsusb -t查询返回:\n")
        while True:
            time.sleep(0.001)
            check_cmd_val = check_cmd.stdout.readline().decode('utf-8', 'ignore')
            if check_cmd_val != '':
                all_logger.info(check_cmd_val)
            if 'qmi_wwan' in check_cmd_val and not is_disappear:
                all_logger.info('wwan驱动检测成功')
                check_cmd.terminate()
                return True
            if is_disappear and 'qmi_wwan' not in check_cmd_val:
                all_logger.info('wwan驱动消失')
                check_cmd.terminate()
                return True
            if time.time() - check_time > 2:
                all_logger.info('未检测到wwan驱动')
                check_cmd.terminate()
                raise QMIError

    def get_ip_address(self, is_success=True, ipv6_flag=False):
        """
        判断是否获取到IPV4地址,目前只应用了is_sucess=False状态下的检测
        :param is_success: True: 拨号正常状态下检测IP地址是否正常获取; False: 断开拨号后检测IP地址是否正常消失
        :param ipv6_flag: True: 检测IPV6地址；False: 检测IPV4地址
        :return: True
        """
        if is_success:
            for i in range(30):
                all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
                all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                                (self.network_card_name, 'inet6' if ipv6_flag else 'inet'))
                ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                              (self.network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
                if ip and 'error' not in ip:
                    all_logger.info(ip)
                    return ip.replace('地址:', '')
                time.sleep(1)
            else:
                all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            return False
        else:
            for i in range(3):
                all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
                all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                                (self.network_card_name, 'inet6' if ipv6_flag else 'inet'))
                ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                              (self.network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
                if ip and 'error' not in ip:
                    all_logger.info(ip)
                    raise QMIError("断开拨号后仍能检测到IP")
                time.sleep(1)
            else:
                all_logger.info("断开拨号后正常获取IPv6地址失败" if ipv6_flag else "断开拨号后正常获取IPv4地址失败")
            return True

    def dump_check(self):
        """
        检测模块是否发生DUMP
        :return: None
        """
        for i in range(10):
            port_list = self.driver_check.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                time.sleep(1)
                continue
            elif self.at_port not in port_list and self.dm_port in port_list:
                raise QMIError('模块DUMP')

    def sim_lock(self):
        """
        SIM卡锁PIN
        :return: True
        """
        self.at_handle.send_at('AT+CLCK="SC",1,"1234"', timeout=5)
        self.at_handle.send_at('AT+CFUN=0', timeout=15)
        time.sleep(3)
        self.at_handle.send_at('AT+CFUN=1', timeout=15)
        return_val = self.at_handle.send_at('AT+CLCK="SC",2', timeout=5)
        if '+CLCK: 1' in return_val:
            return True
        else:
            raise QMIError('SIM卡锁Pin失败')

    def get_netcard_ip(self, is_success=True):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        ifconfig_value = os.popen('ifconfig {}'.format(self.network_card_name)).read()
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
                raise QMIError('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                raise QMIError('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))

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

    def check_route(self):
        """
        检测模块拨号成功后路由配置
        """
        time.sleep(2)
        all_logger.info('***check route***')
        return_value = subprocess.getoutput('route -n')
        all_logger.info(f'{return_value}')
        if self.network_card_name in return_value:
            all_logger.info('路由配置成功')
