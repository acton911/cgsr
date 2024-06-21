import datetime
import re
import serial
import shutil
import glob
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import LinuxATUpgradeError
import time
import os
import subprocess
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from tools.auto_insmod_pcie.auto_insmod_pcie import Reboot_PCIE
from utils.functions.driver_check import DriverChecker
from utils.log.dump.dump_linux import QLogDUMP
import random
from subprocess import STDOUT, PIPE
from zipfile import ZipFile
import serial.tools.list_ports


class LinuxATManagerPowerManager:
    def __init__(self, usbat_port, usbdm_port, imei, svn, pcie_driver_path, cur_version, firmware_path):
        self.at_port = '/dev/mhi_DUN'
        self.dm_port = '/dev/mhi_BHI'
        self.usbat_port = usbat_port
        self.usbdm_port = usbdm_port
        self.cur_version = cur_version
        self.imei = imei
        self.svn = svn
        self.firmware_path = firmware_path
        self.at_handler = ATHandle(usbat_port)
        self.driver = DriverChecker(usbat_port, usbdm_port)
        self.qlog_dump = QLogDUMP()
        self.gpio = GPIO()
        self.PCIE = Reboot_PCIE(pcie_driver_path, '/dev/ttyUSBAT', '/dev/ttyUSBDM', r'/sys/bus/pci/devices/0000\:01\:00.0')

    def check_pcie_driver(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK', '/dev/mhi_QMI0']
        lspci_value = os.popen('lspci').read()
        if '0306' in lspci_value or '0308' in lspci_value:
            all_logger.info('PCI检测正常')
        else:
            raise LinuxATUpgradeError('PCI检测失败，未检测到相关信息')
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        all_logger.info('执行ls /dev/mhi*返回{}'.format(driver_value))
        for i in driver_list:
            if i in driver_value:
                continue
            elif '/dev/mhi_BHI' in driver_value and '/dev/mhi_DIAG' not in driver_value:
                all_logger.info('检测到有/dev/mhi_BHI口但是没有/dev/mhi_DIAG，尝试重启恢复')
                time.sleep(2)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.at_handler.check_urc()
                time.sleep(2)
                self.at_handler.check_network()
                continue
            else:
                raise LinuxATUpgradeError('PCIE驱动检测失败，未检测到{}驱动'.format(i))
        else:
            all_logger.info('PCIE驱动检测正常')

    def send_at_pcie(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _at_port:
            for _ in range(1, 5):  # 连续5次发送AT返回空，并且每次检测到口还在，则判定为AT不通
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

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若不是pcie模式，则设置AT+QCFG="data_interface",1,0并重启模块
        用以防止模块全擦造成恢复成usb模式
        :return: None
        """
        data_interface_value = self.at_handler.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",1,0并重启模块'.format(
                data_interface_value))
            self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(5)

    def cfun1_1(self):
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(5)

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
            raise LinuxATUpgradeError('data_interface信息查询值不一致,查询信息为{}'.format(data_interface_value))

    def check_module_version(self):
        """
        检查版本信息是否正确
        :return:
        """
        self.at_handler.send_at('ATE', 3)
        csub_value = self.at_handler.send_at('ATI+CSUB', 10)
        at_revison = ''.join(re.findall(r'Revision: (.*)', csub_value))
        at_sub = ''.join(re.findall(r'SubEdition: (.*)', csub_value))
        at_version = at_revison + at_sub
        version_r = re.sub(r'[\r\n]', '', at_version).replace('\n', '')
        if self.cur_version != version_r:
            raise LinuxATUpgradeError('系统下发版本号与查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(self.cur_version, at_version))

    def chceck_module_info(self):
        """
        检查模块IMEI号及SVN号
        :return:
        """
        imei_info = self.at_handler.send_at('AT+GSN', 10)
        imei = ''.join(re.findall(r'\d{15}', imei_info))
        if imei != self.imei:
            raise LinuxATUpgradeError('当前查询imei号与系统所填不一致，当前所查为{}，系统所填为{}'.format(imei, self.imei))
        svn_info = self.at_handler.send_at('AT+EGMR=0,9', 10)
        svn = ''.join(re.findall(r'\+EGMR: "(\d+)', svn_info))
        if svn != self.svn:
            raise LinuxATUpgradeError('当前所查最新版本SVN号与系统所填不一致，当前所查为{}, 系统所填为{}'.format(svn, self.svn))

    @staticmethod
    def qfirehose_upgrade(package, vbat, factory, erase):
        """
        Qfirehose普通升级及断电方法
        :param package: 升级包路径,cur or prev
        :param vbat: 是否断电升级
        :param factory: 是否工厂升级
        :param erase: 是否全擦
        :return:
        """
        # 首先确定版本包名称
        package_name = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware', package)):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', package, p)):
                if factory:
                    if p.lower().endswith('factory'):
                        package_name = os.path.join(os.getcwd(), 'firmware', package, p)
                else:
                    if not p.lower().endswith('factory'):
                        package_name = os.path.join(os.getcwd(), 'firmware', package, p)
        if not package_name:
            raise Exception("未找到{}升级包".format('工厂' if factory else '标准'))
        is_factory = True if 'factory' in package_name else False  # 是否是工厂包升级，是的话指令需要加-e
        val = os.popen('ps -ef | grep QFirehose').read()
        if 'QFirehose -f {}'.format(package_name) in val:
            try:
                kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                    all_logger.info('已关闭升级进程')
            except subprocess.TimeoutExpired:
                all_logger.info('关闭升级进程失败')
        start_time = time.time()
        random_off_time = round(random.uniform(1, 60))
        if vbat:
            all_logger.info('升级进行到{}S时断电'.format(random_off_time))
        upgrade = subprocess.Popen('QFirehose -f {} {}'.format(package_name, '-e' if is_factory else ''), stdout=PIPE,
                                   stderr=STDOUT, shell=True)
        all_logger.info('QFirehose -f {} {}'.format(package_name, '-e' if erase else ''))
        os.set_blocking(upgrade.stdout.fileno(), False)    # pylint: disable=E1101
        while True:
            time.sleep(0.001)
            upgrade_content = upgrade.stdout.readline().decode('utf-8')
            if upgrade_content != '':
                if vbat and time.time() - start_time > random_off_time:
                    all_logger.info('升级过程断电'.format())
                    return True
                if upgrade_content == '.':
                    continue
                all_logger.info(repr(upgrade_content).replace("'", ''))
                if 'Upgrade module successfully' in upgrade_content:
                    all_logger.info('升级成功')
                    upgrade.terminate()
                    upgrade.wait()
                    return True
                if 'fail to access {}'.format(package_name) in upgrade_content:
                    raise LinuxATUpgradeError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise LinuxATUpgradeError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 360:
                all_logger.info('360S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise LinuxATUpgradeError('360S内升级失败')

    def mount_package(self):
        """
        挂载版本包
        :return:
        """
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'cur' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/cur')
        os.popen('mount -t cifs {} /mnt/cur -o user="cris.hu@quectel.com",password="hxc111...."'.format
                 (cur_package_path)).read()
        if os.listdir('/mnt/cur'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise LinuxATUpgradeError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def ubuntu_copy_file():
        """
        Ubuntu下复制版本包
        :return:
        """
        os.mkdir(os.getcwd() + '/firmware')
        os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/cur')

        cur_file_list = os.listdir('/mnt/cur')
        all_logger.info('/mnt/cur目录下现有如下文件:{}'.format(cur_file_list))
        all_logger.info('开始复制当前版本版本包到本地')
        for i in cur_file_list:
            shutil.copy(os.path.join('/mnt/cur', i), os.path.join(os.getcwd(), 'firmware', 'cur'))
        if os.path.join(os.getcwd(), 'firmware', 'cur'):
            all_logger.info('版本获取成功')
        else:
            raise LinuxATUpgradeError('版本包获取失败')

    @staticmethod
    def unzip_firmware():
        """
        解压当前路径 + firmware + prev/cur路径下面的所有zip包
        :return: None
        """
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        for path, _, files in os.walk(firmware_path):
            for file in files:
                if file.endswith('.zip'):
                    with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                        all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                        to_unzip.extractall(path)
        all_logger.info('解压固件成功')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/cur')

    @staticmethod
    def is_upgrade_process_exist():
        """
        :return:
        """
        val = os.popen('ps -ef | grep QFirehose').read()
        all_logger.info(val)
        if 'QFirehose -f' in val:
            try:
                kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                    all_logger.info('已关闭升级进程')
            except subprocess.TimeoutExpired:
                all_logger.info('关闭升级进程失败')

    def get_port_list(self):
        """
        获取当前电脑设备管理器中所有的COM口的列表
        :return: COM口列表，例如['COM3', 'COM4']
        """
        if os.name == 'nt':
            try:
                all_logger.debug('get_port_list')
                port_name_list = []
                ports = serial.tools.list_ports.comports()
                for port, _, _ in sorted(ports):
                    port_name_list.append(port)
                all_logger.debug(port_name_list)
                return port_name_list
            except TypeError:  # Linux偶现
                return self.get_port_list()
        else:
            return glob.glob('/dev/ttyUSB*')

    def set_modem_value(self, modem, ap):
        """
        设置modemrstlevel和aprstlevel值并输入AT+QTEST="DUMP",1指令
        :param modem: modem设置值
        :param ap: ap设置值
        :return:
        """
        self.at_handler.send_at('AT+QCFG="ModemRstLevel",{}'.format(modem), timeout=10)
        self.at_handler.send_at('AT+QCFG="ApRstLevel",{}'.format(ap), timeout=10)
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _at_port:
            _at_port.write('AT+QTEST="DUMP",1\r\n'.encode('utf-8'))
            all_logger.info('发送AT+QTEST="DUMP",1指令')
        if modem == 0 and ap == 0:  # 模块只剩一个DM口
            for i in range(10):
                if self.usbdm_port in self.get_port_list() and self.usbat_port not in self.get_port_list():
                    all_logger.info('模块已进入dump')
                    return True
                all_logger.info(f'当前端口情况为{self.get_port_list()}')
                time.sleep(5)
            else:
                raise LinuxATUpgradeError('模块Dump后端口异常')

    def back_dump_value(self):
        """
        恢复dump指令到默认值11
        :return:
        """
        self.at_handler.send_at('AT+QCFG="ModemRstLevel",1', 10)
        self.at_handler.send_at('AT+QCFG="ApRstLevel",1', 10)

    @staticmethod
    def is_qdl():
        """
        判断Linux下Qfirehose断电升级后模块是否进入紧急下载模式,进入返回True，未进入返回False
        :return:
        """
        for i in range(3):
            lsusb = os.popen('lsusb').read()
            all_logger.info(lsusb)
            if '9008' in lsusb:
                all_logger.info('模块已进入紧急下载模式')
                return True
            elif '2c7c' in lsusb:
                all_logger.info('模块未进入紧急下载模式')
                time.sleep(10)
                return False
            time.sleep(3)
