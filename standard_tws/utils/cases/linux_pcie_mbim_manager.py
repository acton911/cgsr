import datetime
import re
import subprocess
import sys
import requests
import serial
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import LinuxPcieMBIMError
from utils.functions.linux_api import LinuxAPI, QuectelCMThread
import time
import os
from tools.auto_insmod_pcie.auto_insmod_pcie import Reboot_PCIE
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.operate.reboot_pc import Reboot


class LinuxPcieMBIMManager:
    def __init__(self, quectel_cm_path, sim_info, version_name, network_card_name, local_network_card_name,
                 pcie_driver_path, phone_number, usbat_port, usbdm_port, params_path):
        self.at_port = '/dev/mhi_DUN'
        self.dm_port = '/dev/mhi_BHI'
        self.linux_api = LinuxAPI()
        self.quectel_cm_path = quectel_cm_path
        self.sim_info = sim_info
        self.version_name = version_name
        self.local_network_card_name = local_network_card_name
        self.network_card_name = network_card_name
        self.pcie_driver_path = pcie_driver_path
        self.phone_number = phone_number
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.PCIE = Reboot_PCIE(pcie_driver_path, usbat_port, usbdm_port, r'/sys/bus/pci/devices/0000\:01\:00.0')
        self.at_handler = ATHandle(usbat_port)
        self.driver = DriverChecker(usbat_port, usbdm_port)
        self.reboot = Reboot(self.at_port, self.dm_port, params_path)

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若不是pcie模式，则设置AT+QCFG="data_interface",1,0并重启模块
        用以防止模块全擦造成恢复成usb模式
        :return: None
        """
        data_interface_value = self.at_handler.send_at('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",1,0并重启模块'.
                            format(data_interface_value))
            self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(5)

    def check_intranet(self, intranet_ip='192.168.11.252'):
        all_logger.info('start check intranet')
        intranet_flag = True
        i = 0
        while i < 10:
            time.sleep(3)
            i = i + 1
            return_value = subprocess.getoutput(f'ping {intranet_ip} -c 10')
            all_logger.info(f"{return_value}")
            if '100% packet loss' in return_value or 'unknown' in return_value or 'unreachable' in return_value or \
                    'failure' in return_value:
                all_logger.info(f"fail to ping {intranet_ip}")
                return_value1 = subprocess.getoutput('ifconfig')  # get ip
                all_logger.info(f'ifconfig\r\n{return_value1}')
                all_logger.info('the intranet connect FAIL!')
                all_logger.info('Trying to connect...')
                # killall quectel-CM
                return_value2 = subprocess.getoutput('killall quectel-CM')
                all_logger.info(f'killall quectel-CM\r\n{return_value2}')
                return_value3 = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
                all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{return_value3}')
                time.sleep(3)
                return_value4 = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
                all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{return_value4}')
                intranet_flag = False
            else:
                all_logger.info('the intranet connect successfully!')
                intranet_flag = True
                break
        if not intranet_flag:
            raise LinuxPcieMBIMError('The intranet connect FAIL, please check the intranet!')

    def check_pcie_driver(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK', '/dev/mhi_MBIM']
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        all_logger.info(f'执行ls /dev/mhi*返回{driver_value}')
        for i in driver_list:
            if i in driver_value:
                continue
            elif '/dev/mhi_BHI' in driver_value and '/dev/mhi_DIAG' not in driver_value:
                all_logger.info('检测到有/dev/mhi_BHI口但是没有/dev/mhi_DIAG，尝试重启恢复')
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(5)
                continue
            else:
                raise LinuxPcieMBIMError(f'PCIE驱动检测失败，未检测到{i}驱动')
        else:
            all_logger.info('PCIE驱动检测正常')

    def insmod_pcie_mbim(self):
        """
        insmod pcie_mhi.ko mhi_mbim_enabled=1
        """
        return_value = subprocess.getoutput(f'ls {self.pcie_driver_path}')
        all_logger.info(f'ls {self.pcie_driver_path}')
        all_logger.info(f'\r\n{return_value}')
        if 'Makefile' not in return_value:
            raise LinuxPcieMBIMError('error pcie driver path, please check again!')

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.pcie_driver_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.pcie_driver_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make
        all_logger.info(' '.join(['make', '--directory', self.pcie_driver_path]))
        s = subprocess.run(' '.join(['make', '--directory', self.pcie_driver_path]), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s.stdout)

        # rmmod pcie_mhi.ko
        all_logger.info(' '.join(['rmmod', '--directory', 'pcie_mhi.ko', self.pcie_driver_path]))
        pci_value = subprocess.getoutput(f'rmmod {self.pcie_driver_path}/pcie_mhi.ko')
        all_logger.info(f'rmmod {self.pcie_driver_path}/pcie_mhi.ko\r\n{pci_value}')

        # insmod pcie_mhi.ko mhi_mbim_enabled=1
        all_logger.info(' '.join(['insmod', '--directory', 'pcie_mhi.ko', self.pcie_driver_path]))
        pci_value = subprocess.getoutput(f'insmod {self.pcie_driver_path}/pcie_mhi.ko mhi_mbim_enabled=1')
        all_logger.info(f'insmod {self.pcie_driver_path}/pcie_mhi.ko mhi_mbim_enabled=1\r\n{pci_value}')

        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(5)

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
        time.sleep(10)
        self.readline_keyword('RING', timout=300)
        time.sleep(10)
        self.readline_keyword('NO CARRIER', timout=300)
        time.sleep(5)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.send_at_pcie('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
        self.send_at_pcie('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        all_logger.info(f'{self.phone_number}')
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        self.readline_keyword('+CMTI', timout=100)
        time.sleep(5)

    def readline_keyword(self, keyword1='', keyword2='', timout=10, at_flag=False, at_cmd=''):
        at_logger.info(f'检查关键字:{keyword1} {keyword2}, 超时时间:{timout}')
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as __at_port:
            if at_flag:
                __at_port.write(f'{at_cmd}\r\n'.encode())
            start_time = time.time()
            return_val_cache = ''
            while True:
                time.sleep(0.001)
                return_val = __at_port.readline().decode("utf-8", "ignore")
                if return_val != '':
                    return_val_cache += return_val
                if time.time() - start_time > timout:
                    raise LinuxPcieMBIMError(f'{timout}S内未检测到{keyword1},{keyword2}')
                if keyword1 in return_val_cache and keyword2 in return_val_cache:
                    at_logger.info(f'{return_val_cache}')
                    return True

    @staticmethod
    def readline(port):
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
                        at_logger.debug("{} {}".format("RECV", repr(buf).replace("'", '')))
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > 1:
                        at_logger.info(f'{repr(buf)}')
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            at_logger.error(f'Fatal ERROR: {error}')
        finally:
            return buf

    def bound_network(self, network_type, timeout=180):
        """
        固定指定网络
        :param timeout：设置指定网络后检查的超时时间
        :param network_type: 取值：SA/NSA/LTE/WCDMA
        """
        # 固定网络
        network_type = network_type.upper()  # 转换为大写

        at_logger.info(f"固定网络到{network_type}")
        if network_type in ["LTE", "WCDMA"]:  # 固定LTE或者WCDMA
            self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at_pcie(f'AT+QNWPREFCFG= "mode_pref",{network_type}')
        elif network_type == 'SA':  # 固定SA网络
            self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at_pcie('AT+QNWPREFCFG= "mode_pref",NR5G')
        elif network_type == "NSA":  # 使用nr5g_disable_mode进行SA和NSA偏号设置
            self.send_at_pcie('AT+QNWPREFCFG="mode_pref",AUTO')
            at_data = self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",1')
        else:
            raise LinuxPcieMBIMError("不支持的网络类型设置")

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            raise LinuxPcieMBIMError('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')

        # 查询是否固定正常
        start_timestamp = time.time()
        while time.time() - start_timestamp < timeout:
            # 获取当前网络状态
            at_logger.info(f"正在检查是否注册{network_type}网络")
            cops_value = self.check_network_pcie()  # 检查cops值，用作LTE和WCDMA固定的检查
            network_info = self.check_servingcell()

            # 判断当前网络状态
            if network_type == "LTE" and cops_value == '7':
                at_logger.info(f"注册{network_type}网络类型成功，当前COPS: 7")
                return True
            elif network_type == "WCDMA" and cops_value == '2':
                at_logger.info(f"注册{network_type}网络类型成功，当前COPS: 2")
                return True
            elif network_type == network_info:  # 5G网络
                at_logger.info(f"注册{network_type}网络类型成功")
                return True
            time.sleep(3)
        else:
            raise LinuxPcieMBIMError(f"{timeout}秒内注册{network_type}网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持")

    def check_servingcell(self):
        """
        bound_network联合使用的函数。
        注册5G网络时候检测是SA还是NSA
        :return: '11' 注册 'SA', '13' 注册NSA
        """
        network = self.send_at_pcie('AT+QENG="SERVINGCELL"')
        if 'NR5G-NSA' in network:
            return 'NSA'
        elif 'NR5G-SA' in network:
            return 'SA'
        else:
            return ''

    def check_pcie_pci(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        pcie_pci_x55 = '0306'
        pcie_pci_x6x = '0308'
        pci_value = subprocess.getoutput('lspci')
        all_logger.info(f'执行lspci返回:\r\n{pci_value}')
        if pcie_pci_x55 in pci_value or pcie_pci_x6x in pci_value:
            all_logger.info('PCI检测正常')
        else:
            raise LinuxPcieMBIMError('PCI检测失败，未检测到相关信息')

    def check_pcie_port(self, device_id='030'):
        """
        查询PCIE接口速率
        """
        self.check_pcie_pci()
        # 检测节点路径
        global full_pci_devices_path
        all_logger.info('lspci -v')
        value_lspci_v = subprocess.getoutput('lspci -v')
        # 匹配由16进制组成的PCIE插槽位置路径，例：00:1f.1
        pci_devices_path1 = ''.join(
            re.findall(r'([0-9a-fA-F]+):[0-9a-fA-F]+.[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path2 = ''.join(
            re.findall(r'[0-9a-fA-F]+:([0-9a-fA-F]+).[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path3 = ''.join(
            re.findall(r'[0-9a-fA-F]+:[0-9a-fA-F]+.([0-9a-fA-F]+).*?{}'.format(device_id), value_lspci_v))
        # 拼接成linux下可执行的路径名
        if pci_devices_path1 and pci_devices_path2 and pci_devices_path3:
            full_pci_devices_path = '/sys/bus/pci/devices/0000\:{}\:{}.{}'.format(pci_devices_path1, pci_devices_path2, pci_devices_path3)
            all_logger.info("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))
        pci_port_value = subprocess.getoutput('cat {}/current_link_speed'.format(full_pci_devices_path))
        all_logger.info(pci_port_value)
        if '5.0 GT/s PCIe' in pci_port_value:
            all_logger.info('PCIe速率接口查询成功')
        else:
            self.check_pcie_pci()
            pci_port_value = subprocess.getoutput('cat {}/current_link_speed'.format(full_pci_devices_path))
            all_logger.info(pci_port_value)
            if '5.0 GT/s PCIe' in pci_port_value:
                all_logger.info('PCIe速率接口查询成功')
            else:
                raise LinuxPcieMBIMError('PCI接口速率，查询失败')

    def check_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常
        :return: None
        """
        data_interface_value = self.send_at_pcie('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            raise LinuxPcieMBIMError(f'data_interface信息查询值不一致,查询信息为{data_interface_value}')

    def check_module_info(self):
        """
        检测模块基本信息是否正常
        :return: None
        """
        qccid_value = self.send_at_pcie('AT+QCCID')
        all_logger.info(f"AT+QCCID\r\n{qccid_value}")
        re_qccid = re.findall(r'\+QCCID: (\d+\S+)', qccid_value)[0]
        sys_qccid = self.sim_info
        if re_qccid in sys_qccid:
            all_logger.info('QCCID信息正常')
        else:
            raise LinuxPcieMBIMError(f'QCCID信息查询值与系统不一致,查询信息为{re_qccid},系统信息为{sys_qccid}')
        self.send_at_pcie('AT+CVERSION')
        release_info = self.send_at_pcie('ATI+CSUB')
        rev = re.findall(r'Revision: (.*)', release_info)[0].strip()
        sub = re.findall(r'SubEdition: (.*)', release_info)[0].strip()
        release_name = rev + sub
        sys_release_name = re.findall(r'(.*)_', self.version_name)[0] + self.version_name[-3:]
        if release_name == sys_release_name:
            all_logger.info('版本信息检查正常')
        else:
            raise LinuxPcieMBIMError(f'查询版本信息与系统上信息不一致,查询信息为{release_name},系统信息为{sys_release_name}')

    def make_dial_tool(self):
        """
        编译拨号工具
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.quectel_cm_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.quectel_cm_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.quectel_cm_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.quectel_cm_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.quectel_cm_path]))
        s = subprocess.run(' '.join(['make', '--directory', self.quectel_cm_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

    def dial(self, times=10, is_success=True):
        """
        拨号后进行Ping业务
        times: ping的时长
        is_success: 是否成功拨号后再ping
        :return: None
        """
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(10)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            time.sleep(10)
            all_logger.info('恢复网络制式为AUTO')
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def check_sleep(self):
        """
        验证PC睡眠唤醒后是否可以正常拨号
        :return: None
        """
        os.popen('rtcwake -m mem -s 300').read()
        time.sleep(10)
        self.dial()

    def get_ip_address(self, is_success=False):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        ifconfig_value = os.popen('ifconfig -a').read()
        try:
            re_ifconfig = re.findall(fr'{self.network_card_name}.*\n(.*)', ifconfig_value)[0].strip()
            ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
        except IndexError:
            pass
        if is_success:
            if ip:
                all_logger.info(f'获取IP地址正常,IP地址为{ip}')
            else:
                raise LinuxPcieMBIMError(f'获取IP地址异常,未获取到IP地址,ifconfig -a返回{ifconfig_value}')
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                raise LinuxPcieMBIMError(f'异常,当前未进行拨号,但获取到IP地址{ip}')

    def check_cfun(self, value):
        """
        检查当前CFUN状态是否正常
        value: 需要核实的cfun值
        :return: None
        """
        cfun_value = self.send_at_pcie('AT+CFUN?')
        if str(value) in cfun_value:
            all_logger.info('当前CFUN值正常')
        else:
            raise LinuxPcieMBIMError('CFUN值异常')

    def change_cfun(self, value):
        """
        改变CFUN值并检查是否改变成功
        value: 需要改变的CFUN值
        :return None
        """
        self.send_at_pcie(f'AT+CFUN={value}')
        time.sleep(1)
        self.check_cfun(value)
        time.sleep(5)

    def send_at_pcie(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _at_port:
            for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
                at_start_timestamp = time.time()
                _at_port.write(f'{at_command}\r\n'.encode())
                at_logger.info(f'Send: {at_command}')
                return_value_cache = ''
                while True:
                    # AT端口值获取
                    time.sleep(0.001)  # 减小CPU开销
                    return_value = _at_port.readline().decode('utf-8')
                    if return_value != '':
                        return_value_cache += f'{return_value}'
                        if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                            return return_value_cache
                        if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                            at_logger.error(f'{at_command}指令返回ERROR')
                            return return_value_cache
                    # 超时等判断
                    current_total_time = time.time() - at_start_timestamp
                    out_time = time.time()
                    if current_total_time > timeout:
                        if return_value_cache and at_command in return_value_cache:
                            at_logger.error(f'{at_command}命令执行超时({timeout}S)')
                            while True:
                                time.sleep(0.001)  # 减小CPU开销
                                return_value = _at_port.readline().decode('utf-8')
                                if return_value != '':
                                    return_value_cache += f'[{datetime.datetime.now()}] {return_value}'
                                if time.time() - out_time > 3:
                                    return return_value_cache
                        elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                            at_logger.error(f'{at_command}命令执行返回格式错误，未返回AT指令本身')
                            return return_value_cache
                        else:
                            at_logger.error(f'{at_command}命令执行{timeout}S内无任何回显')
                            time.sleep(0.5)
                            break
            else:
                at_logger.error(f'连续10次执行{at_command}命令无任何回显，AT不通')

    def check_network_pcie(self):
        """
        检查模块驻网。
        :return: False: 模块没有注上网。cops_value:模块注册的网络类型，
        """
        at_logger.info("检查网络")
        check_network_start_time = time.time()
        timeout = 300
        while True:
            return_value = self.send_at_pcie('AT+COPS?')
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', return_value))
            if cops_value != '':
                at_logger.info(f"当前网络：{cops_value}")
                time.sleep(1)
                return cops_value
            if time.time() - check_network_start_time > timeout:
                at_logger.error(f"{timeout}内找网失败")
                return False
            time.sleep(1)

    def local_net_up(self):
        """
        开启本地网
        :return: None
        """
        return_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
        all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{return_value}')
        # os.popen('ifconfig {} up'.format(self.local_network_card_name))

    def local_net_down(self):
        """
        关闭本地网
        :return: None
        """
        return_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} down')
        # os.popen('ifconfig {} down'.format(self.local_network_card_name))
        all_logger.info(f'ifconfig {self.local_network_card_name} down\r\n{return_value}')
        for i in range(10):
            ifconfig_value = subprocess.getoutput('ifconfig')
            if self.local_network_card_name not in ifconfig_value:
                all_logger.info('关闭本地网成功')
                return True
            else:
                time.sleep(3)
                continue
        else:
            raise LinuxPcieMBIMError('关闭本地网失败')

    def check_platform(self):
        """
        检查是RM模块还是RG模块，RM返回False，RG返回True
        :return: True: RM模块；False: RG模块
        """
        paltform = self.send_at_pcie('ATI')
        if 'RM' in paltform:
            return False
        else:
            return True
