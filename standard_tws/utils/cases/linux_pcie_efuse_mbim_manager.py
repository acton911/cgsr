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
from utils.operate.reboot_pc import Reboot


class LinuxPcieEfuseMBIMManager:
    def __init__(self, quectel_cm_path, sim_info, version_name, network_card_name, local_network_card_name, pcie_driver_path, phone_number, params_path):
        self.at_port = '/dev/mhi_DUN'
        self.dm_port = '/dev/mhi_BHI'
        self.quectel_cm_path = quectel_cm_path
        self.sim_info = sim_info
        self.version_name = version_name
        self.local_network_card_name = local_network_card_name
        self.network_card_name = network_card_name
        self.pcie_driver_path = pcie_driver_path
        self.phone_number = phone_number
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.PCIE = Reboot_PCIE(pcie_driver_path, '/dev/ttyUSBAT', '/dev/ttyUSBDM', '/sys/bus/pci/devices/0000\:01\:00.0')  # noqa
        self.reboot = Reboot(self.at_port, self.dm_port, params_path)

    def check_intranet(self, intranet_ip='192.168.11.252'):
        all_logger.info('start check intranet')
        intranet_flag = True
        i = 0
        while i < 10:
            time.sleep(3)
            i = i + 1
            return_value = subprocess.getoutput('ping {} -c 10'.format(intranet_ip))
            all_logger.info("{}".format(return_value))
            if '100% packet loss' in return_value or 'unknown' in return_value or 'unreachable' in return_value or 'failure' in return_value:
                all_logger.info("fail to ping {}".format(intranet_ip))
                return_value1 = subprocess.getoutput('ifconfig')  # get ip
                all_logger.info('ifconfig\r\n{}'.format(return_value1))
                all_logger.info('the intranet connect FAIL!')
                all_logger.info('Trying to connect...')
                # killall quectel-CM
                return_value2 = subprocess.getoutput('killall quectel-CM')
                all_logger.info('killall quectel-CM\r\n{}'.format(return_value2))
                return_value3 = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))
                all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, return_value3))
                time.sleep(3)
                return_value4 = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
                all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, return_value4))
                intranet_flag = False
            else:
                all_logger.info('the intranet connect successfully!')
                intranet_flag = True
                break
        if not intranet_flag:
            all_logger.info('The intranet connect FAIL, please check the intranet!')
            raise LinuxPcieMBIMError('The intranet connect FAIL, please check the intranet!')

    @staticmethod
    def check_pcie_driver():
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK', '/dev/mhi_MBIM']
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        all_logger.info('执行ls /dev/mhi*返回{}'.format(driver_value))
        for i in driver_list:
            if i in driver_value:
                continue
            else:
                all_logger.info('PCIE驱动检测失败，未检测到{}驱动'.format(i))
                raise LinuxPcieMBIMError('PCIE驱动检测失败，未检测到{}驱动'.format(i))
        else:
            all_logger.info('PCIE驱动检测正常')

    def insmod_pcie_mbim(self):
        """
        insmod pcie_mhi.ko mhi_mbim_enabled=1
        """
        return_value = subprocess.getoutput('ls {}'.format(self.pcie_driver_path))
        all_logger.info('ls {}'.format(self.pcie_driver_path))
        all_logger.info('\r\n{}'.format(return_value))
        if 'Makefile' not in return_value:
            all_logger.info('error pcie driver path, please check again!')
            raise LinuxPcieMBIMError('error pcie driver path, please check again!')
        if 'pcie_mhi.ko' not in return_value:
            # make clean
            all_logger.info(' '.join(['make', 'clean', '--directory', self.pcie_driver_path]))
            s = subprocess.run(' '.join(['make', 'clean', '--directory', self.pcie_driver_path]), shell=True,
                               capture_output=True, text=True)
            all_logger.info(s.stdout)

            # make install
            all_logger.info(' '.join(['make', 'install', '--directory', self.pcie_driver_path]))
            s = subprocess.run(' '.join(['make', '--directory', self.pcie_driver_path]), shell=True, capture_output=True,
                               text=True)
            all_logger.info(s.stdout)

            # make install
            all_logger.info(' '.join(['make', 'install', '--directory', self.pcie_driver_path]))
            s = subprocess.run(' '.join(['make', '--directory', self.pcie_driver_path]), shell=True,
                               capture_output=True,
                               text=True)
            all_logger.info(s.stdout)
        # insmod pcie_mhi.ko
        all_logger.info(' '.join(['insmod', '--directory', 'pcie_mhi.ko', self.pcie_driver_path]))
        pci_value = subprocess.getoutput('insmod {}/pcie_mhi.ko mhi_mbim_enabled=1'.format(self.pcie_driver_path))
        all_logger.info('insmod {}/pcie_mhi.ko mhi_mbim_enabled=1\r\n{}'.format(self.pcie_driver_path, pci_value))

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
        self.readline_keyword('+CMTI', timout=100)
        time.sleep(5)

    def readline_keyword(self, keyword1='', keyword2='', timout=10, at_flag=False, at_cmd=''):
        at_logger.info('检查关键字:{} {}, 超时时间:{}'.format(keyword1, keyword2, timout))
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as __at_port:
            if at_flag:
                __at_port.write('{}\r\n'.format(at_cmd).encode('utf-8'))
            start_time = time.time()
            return_val_cache = ''
            while True:
                time.sleep(0.001)
                return_val = __at_port.readline().decode("utf-8", "ignore")
                if return_val != '':
                    return_val_cache += return_val
                if time.time() - start_time > timout:
                    raise LinuxPcieMBIMError('{}S内未检测到{},{}'.format(timout, keyword1, keyword2))
                if keyword1 in return_val_cache and keyword2 in return_val_cache:
                    at_logger.info('{}'.format(return_val_cache))
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
                        at_logger.info('{}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            at_logger.error('Fatal ERROR: {}'.format(error))
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

        at_logger.info("固定网络到{}".format(network_type))
        if network_type in ["LTE", "WCDMA"]:  # 固定LTE或者WCDMA
            self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at_pcie('AT+QNWPREFCFG= "mode_pref",{}'.format(network_type))
        elif network_type == 'SA':  # 固定SA网络
            self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at_pcie('AT+QNWPREFCFG= "mode_pref",NR5G')
        elif network_type == "NSA":  # 使用nr5g_disable_mode进行SA和NSA偏号设置
            self.send_at_pcie('AT+QNWPREFCFG="mode_pref",AUTO')
            at_data = self.send_at_pcie('AT+QNWPREFCFG="nr5g_disable_mode",1')
        else:
            all_logger.info("不支持的网络类型设置")
            raise LinuxPcieMBIMError("不支持的网络类型设置")

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            all_logger.info('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')
            raise LinuxPcieMBIMError('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')

        # 查询是否固定正常
        start_timestamp = time.time()
        while time.time() - start_timestamp < timeout:
            # 获取当前网络状态
            at_logger.info("正在检查是否注册{}网络".format(network_type))
            cops_value = self.check_network_pcie()  # 检查cops值，用作LTE和WCDMA固定的检查
            network_info = self.check_servingcell()

            # 判断当前网络状态
            if network_type == "LTE" and cops_value == '7':
                at_logger.info("注册LTE网络类型成功，当前COPS: 7")
                return True
            elif network_type == "WCDMA" and cops_value == '2':
                at_logger.info("注册WCDMA网络类型成功，当前COPS: 2")
                return True
            elif network_type == network_info:  # 5G网络
                at_logger.info("注册{}网络类型成功".format(network_type))
                return True
            time.sleep(3)
        else:
            all_logger.info("{}秒内注册{}网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持".format(timeout, network_type))
            raise LinuxPcieMBIMError("{}秒内注册{}网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持".format(timeout, network_type))

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

    @staticmethod
    def check_pcie_pci():
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        pcie_pci = '0306'
        pci_value = subprocess.getoutput('lspci')
        all_logger.info('执行lspci返回:\r\n{}'.format(pci_value))
        if pcie_pci not in pci_value:
            all_logger.info('PCI检测失败，未检测到{}'.format(pcie_pci))
            raise LinuxPcieMBIMError('PCI检测失败，未检测到{}'.format(pcie_pci))
        else:
            all_logger.info('PCI检测正常')

    def check_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常
        :return: None
        """
        data_interface_value = self.send_at_pcie('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询值不一致,查询信息为{}'.format(data_interface_value))
            raise LinuxPcieMBIMError('data_interface信息查询值不一致,查询信息为{}'.format(data_interface_value))

    def check_module_info(self):
        """
        检测模块基本信息是否正常
        :return: None
        """
        qccid_value = self.send_at_pcie('AT+QCCID')
        all_logger.info("AT+QCCID\r\n{}".format(qccid_value))
        re_qccid = re.findall(r'\+QCCID: (\d+\S+)', qccid_value)[0]
        sys_qccid = self.sim_info
        if re_qccid == sys_qccid or re_qccid in sys_qccid:
            all_logger.info('QCCID信息正常')
        else:
            all_logger.info('QCCID信息查询值与系统不一致,查询信息为{},系统信息为{}'.format(re_qccid, sys_qccid))
            raise LinuxPcieMBIMError('QCCID信息查询值与系统不一致,查询信息为{},系统信息为{}'.format(re_qccid, sys_qccid))
        self.send_at_pcie('AT+CVERSION')
        release_info = self.send_at_pcie('ATI+CSUB')
        rev = re.findall(r'Revision: (.*)', release_info)[0].strip()
        sub = re.findall(r'SubEdition: (.*)', release_info)[0].strip()
        release_name = rev + sub
        sys_release_name = re.findall(r'(.*)_', self.version_name)[0] + self.version_name[-3:]
        if release_name == sys_release_name:
            all_logger.info('版本信息检查正常')
        else:
            all_logger.info('查询版本信息与系统上信息不一致,查询信息为{},系统信息为{}'.format(release_name, sys_release_name))
            raise LinuxPcieMBIMError('查询版本信息与系统上信息不一致,查询信息为{},系统信息为{}'.format(release_name, sys_release_name))

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
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_MBIM')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
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
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

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
            re_ifconfig = re.findall(r'{}.*\n(.*)'.format(self.network_card_name), ifconfig_value)[0].strip()
            ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
        except IndexError:
            pass
        if is_success:
            if ip:
                all_logger.info('获取IP地址正常,IP地址为{}'.format(ip))
            else:
                all_logger.info('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
                raise LinuxPcieMBIMError('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                all_logger.info('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))
                raise LinuxPcieMBIMError('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))

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
            all_logger.info('CFUN值异常')
            raise LinuxPcieMBIMError('CFUN值异常')

    def change_cfun(self, value):
        """
        改变CFUN值并检查是否改变成功
        value: 需要改变的CFUN值
        :return None
        """
        self.send_at_pcie('AT+CFUN={}'.format(value))
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
                _at_port.write('{}\r\n'.format(at_command).encode('utf-8'))
                at_logger.info('Send: {}'.format(at_command))
                return_value_cache = ''
                while True:
                    # AT端口值获取
                    time.sleep(0.001)  # 减小CPU开销
                    return_value = _at_port.readline().decode('utf-8')
                    if return_value != '':
                        return_value_cache += '{}'.format(return_value)
                        if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                            return return_value_cache
                        if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                            at_logger.error('{}指令返回ERROR'.format(at_command))
                            return return_value_cache
                    # 超时等判断
                    current_total_time = time.time() - at_start_timestamp
                    out_time = time.time()
                    if current_total_time > timeout:
                        if return_value_cache and at_command in return_value_cache:
                            at_logger.error('{}命令执行超时({}S)'.format(at_command, timeout))
                            while True:
                                time.sleep(0.001)  # 减小CPU开销
                                return_value = _at_port.readline().decode('utf-8')
                                if return_value != '':
                                    return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                                if time.time() - out_time > 3:
                                    return return_value_cache
                        elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                            at_logger.error('{}命令执行返回格式错误，未返回AT指令本身'.format(at_command))
                            return return_value_cache
                        else:
                            at_logger.error('{}命令执行{}S内无任何回显'.format(at_command, timeout))
                            time.sleep(0.5)
                            break
            else:
                at_logger.error('连续10次执行{}命令无任何回显，AT不通'.format(at_command))

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
                at_logger.info("当前网络：{}".format(cops_value))
                time.sleep(1)
                return cops_value
            if time.time() - check_network_start_time > timeout:
                at_logger.error("{}内找网失败".format(timeout))
                return False
            time.sleep(1)

    def local_net_up(self):
        """
        开启本地网
        :return: None
        """
        return_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))
        all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, return_value))
        for i in range(10):
            try:
                ifconfig_value = subprocess.getoutput('ifconfig')
                re_value = re.findall('{}.*\n(.*)'.format(self.local_network_card_name), ifconfig_value)[0].strip()
                ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_value)[0]
            except IndexError:
                time.sleep(3)
                continue
            if ip:
                all_logger.info('开启本地网成功')
                time.sleep(5)
                return True
        else:
            all_logger.info('开启本地网失败')
            raise LinuxPcieMBIMError('开启本地网失败')

    def local_net_down(self):
        """
        关闭本地网
        :return: None
        """
        return_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))
        all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, return_value))
        for i in range(10):
            ifconfig_value = subprocess.getoutput('ifconfig')
            if self.local_network_card_name not in ifconfig_value:
                all_logger.info('关闭本地网成功')
                return True
            else:
                time.sleep(3)
                continue
        else:
            all_logger.info('关闭本地网失败')
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
