import datetime
import filecmp
import glob
import hashlib
import os
import random
import re
import shutil
import subprocess
import time
from collections import deque
from subprocess import PIPE
from threading import Thread
from zipfile import ZipFile
import paramiko
import requests
import serial
import sys
from utils.functions.jenkins import multi_thread_merge_version
from utils.exception.exceptions import LinuxPCIEDFOTAError
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger, at_logger
from utils.operate.at_handle import ATHandle
from utils.operate.uart_handle import UARTHandle
from utils.functions.gpio import GPIO
import serial.tools.list_ports


class LinuxPCIEDFOTAManager:
    def __init__(self, uart_port, revision, sub_edition, prev_upgrade_revision, svn, ChipPlatform,
                 prev_upgrade_sub_edition, prev_svn, at_port, dm_port, prev_firmware_path, firmware_path):
        self.at_port = at_port
        self.dm_port = dm_port
        self.dun_port = '/dev/mhi_DUN'
        self.bhi_port = '/dev/mhi_BHI'
        self.firmware_path = firmware_path
        self.revision = revision
        self.sub_edition = sub_edition
        self.prev_upgrade_revision = prev_upgrade_revision
        self.prev_upgrade_sub_edition = prev_upgrade_sub_edition
        self.prev_firmware_path = prev_firmware_path
        self.prev_svn = prev_svn
        self.svn = svn
        self.ChipPlatform = ChipPlatform
        self.uart_handler = UARTHandle(uart_port)
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        md5 = hashlib.md5()
        md5.update(f'{self.revision}{self.sub_edition}{self.prev_upgrade_revision}{self.prev_upgrade_sub_edition}'.encode('utf-8'))
        self.package_dir = md5.hexdigest()[:10]   # 创建一个文件夹，用于在ftp和http(s)服务器上创建，避免重复
        self.driver_check = DriverChecker(self.at_port, self.dm_port)
        self.gpio = GPIO()
        # self.Is_XiaoMi_version = True if '_XM' in self.revision else False

    def check_pcie_driver(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK']
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        all_logger.info('执行ls /dev/mhi*返回{}'.format(driver_value))
        for i in driver_list:
            if i in driver_value:
                continue
            elif '/dev/mhi_BHI' in driver_value and '/dev/mhi_DIAG' not in driver_value:
                all_logger.info('检测到有/dev/mhi_BHI口但是没有/dev/mhi_DIAG，尝试重启恢复')
                self.driver_check.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.read_poweron_urc()
                self.at_handler.check_network()
                continue
            else:
                raise LinuxPCIEDFOTAError('PCIE驱动检测失败，未检测到{}驱动'.format(i))
        else:
            all_logger.info('PCIE驱动检测正常')

    def send_at_pcie(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        with serial.Serial(self.dun_port, baudrate=115200, timeout=0) as _dun_port:
            for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
                at_start_timestamp = time.time()
                _dun_port.write('{}\r\n'.format(at_command).encode('utf-8'))
                at_logger.info('Send: {}'.format(at_command))
                return_value_cache = ''
                while True:
                    # AT端口值获取
                    time.sleep(0.001)  # 减小CPU开销
                    return_value = _dun_port.readline().decode('utf-8')
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
                                return_value = _dun_port.readline().decode('utf-8')
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
            raise LinuxPCIEDFOTAError('data_interface信息查询值不一致,查询信息为{}'.format(data_interface_value))

    @staticmethod
    def check_pcie_pci():
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        pci_value = subprocess.getoutput('lspci')
        all_logger.info('执行lspci返回:\r\n{}'.format(pci_value))
        if '0306' in pci_value or '0308' in pci_value:
            all_logger.info('PCI检测正常')
        else:
            raise LinuxPCIEDFOTAError('PCI检测失败')

    def reset_a_version(self):
        """
        恢复到A版本。
        :return: None
        """
        # 版本号
        for i in range(10):
            return_value = self.at_handler.send_at('ATI+CSUB', 0.6)
            revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
            sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
            if revision == self.prev_upgrade_revision and sub_edition == self.prev_upgrade_sub_edition:
                all_logger.info("检查当前是A版本成功")
                return True
            time.sleep(0.1)
        else:
            exc_type = None
            exc_value = None
            try:
                self.qfirehose_upgrade('prev', False, True, True)
                self.driver_check.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.read_poweron_urc()
                self.at_handler.check_network()
                self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.3)
                self.qfirehose_upgrade('prev', False, False, False)
                self.driver_check.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.read_poweron_urc()
                self.at_handler.check_network()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                time.sleep(5)
                if exc_type and exc_value:
                    raise exc_type(exc_value)
            time.sleep(20)  # 等到正常
            self.after_upgrade_check()

    def reset_b_version(self):
        """
        恢复到B版本。
        :return: None
        """
        for i in range(10):
            # 版本号
            return_value = self.at_handler.send_at('ATI+CSUB', 0.6)
            revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
            sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
            if revision == self.revision and sub_edition == self.sub_edition:
                all_logger.info("检查当前是B版本成功")
                return True
            time.sleep(0.1)
        else:
            exc_type = None
            exc_value = None
            try:
                self.qfirehose_upgrade('cur', False, True, True)
                self.driver_check.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.read_poweron_urc()
                self.at_handler.check_network()
                self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.3)
                self.qfirehose_upgrade('cur', False, False, False)
                self.driver_check.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.read_poweron_urc()
                self.at_handler.check_network()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                time.sleep(5)
                if exc_type and exc_value:
                    raise exc_type(exc_value)
            time.sleep(20)  # 等到正常
            self.after_upgrade_check()

    def init_with_version_a(self):
        """
        VBAT开机，检查当前是A版本。
        :return: None
        """
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.reset_a_version()
        self.at_handler.check_network()
        time.sleep(10)

    def init_with_version_b(self):
        """
        VBAT开机，检查当前是B版本。
        :return: None
        """
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.reset_b_version()
        self.at_handler.check_network()
        time.sleep(10)

    def init(self):
        """
        VBAT开机，检查当前是B版本。
        :return: None
        """
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.at_handler.check_network()
        time.sleep(10)

    def dfota_b_a_upgrade_check(self):
        """
        升级后进行的检查，包括:
        1. 版本号 ATI+CSUB
        3. 查号 AT+EGMR=0,7
        4. SVN号检查 AT+EGMR=0,9
        5. 找网确认
        6. MBN查询AT+QMBNCFG="LIST"
        7. 备份CEFS AT+QPRTPARA=1
        8. 备份后检查 AT+QPRTPARA=4，能查询成功还原次数(返回值第二个参数)
        :return: True，检查成功，False，检查失败
        """
        all_logger.info("进行升级后版本号、查号、MBN备份还原找网检查")
        time.sleep(10)
        # 版本号
        for _ in range(10):
            return_value = self.at_handler.send_at('ATI+CSUB', 0.6)
            revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
            sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
            if revision == self.prev_upgrade_revision and sub_edition == self.prev_upgrade_sub_edition:
                break
            time.sleep(1)
        else:
            raise LinuxPCIEDFOTAError('ATI查询的A版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxPCIEDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.prev_svn) not in return_value:
            raise LinuxPCIEDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常:\r\n{}".format(return_value))
                time.sleep(10)
        else:
            raise LinuxPCIEDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令后查询异常")

    def dfota_a_b_upgrade_check(self):
        """
        升级后进行的检查，包括:
        1. 版本号 ATI+CSUB
        3. 查号 AT+EGMR=0,7
        4. SVN号检查 AT+EGMR=0,9
        5. 找网确认
        6. MBN查询AT+QMBNCFG="LIST"
        7. 备份CEFS AT+QPRTPARA=1
        8. 备份后检查 AT+QPRTPARA=4，能查询成功还原次数(返回值第二个参数)
        :return: True，检查成功，False，检查失败
        """
        all_logger.info("进行升级后版本号、查号、MBN备份还原找网检查")
        time.sleep(10)
        # 版本号
        for _ in range(10):
            return_value = self.at_handler.send_at('ATI+CSUB', 0.6)
            revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
            sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
            if revision == self.revision and sub_edition == self.sub_edition:
                break
            time.sleep(1)
        else:
            raise LinuxPCIEDFOTAError('ATI查询的B版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxPCIEDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise LinuxPCIEDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常:\r\n{}".format(return_value))
                time.sleep(10)
        else:
            raise LinuxPCIEDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令后查询异常")

    def dfota_upgrade_online(self, dfota_type, a_b=True, dl_stop=False, upgrade_stop=False, start=False, end=False, dl_vbat=False, dl_cfun=False):
        fota_cmd = []
        if dfota_type.upper() == "FTP":
            fota_cmd.extend(['ftp://test:test@112.31.84.164:8309/5G/'])
        elif dfota_type.upper() == 'HTTP':
            fota_cmd.extend(['http://112.31.84.164:8300/5G/'])
        elif dfota_type.upper() == 'HTTPS':
            fota_cmd.extend(['https://112.31.84.164:8301/5G/'])
        fota_cmd.extend([self.package_dir, '/'])
        if a_b:
            fota_cmd.extend(['a-b.zip'])
        else:
            fota_cmd.extend(['b-a.zip'])
        fota_cmd = ''.join(fota_cmd)
        all_logger.info(fota_cmd)
        # step1
        if dl_cfun:  # 如果需要下载包过程断网
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.send_at('AT+CFUN=0', 15)
            time.sleep(5)
            self.at_handler.dfota_dl_package_701_702()
            self.at_handler.send_at("AT+CFUN=1", 15)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            time.sleep(10)
        if dl_vbat:
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            time.sleep(10)
        self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
        self.driver.check_usb_driver_dis()

        # step2
        if self.revision.startswith("RG") and self.ChipPlatform.startswith("SDX55"):
            if upgrade_stop:
                self.uart_handler.dfota_step_2(stop_download=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if start:
                self.uart_handler.dfota_step_2(start=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end:
                self.uart_handler.dfota_step_2()
                all_logger.info("在FOTA END 0处断电")
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end is False:
                at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
                self.uart_handler.dfota_step_2()
                if 'START' not in at_background_read.get_info():
                    all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                                     "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
            else:
                self.uart_handler.dfota_end_0()
        else:  # RM项目
            self.driver.check_usb_driver()
            if upgrade_stop:  # 随机断电
                self.at_handler.dfota_step_2(stop_download=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if start:  # 在上报+QIND: "FOTA","START"时候断电
                self.at_handler.dfota_step_2(start=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end:  # 在上报+QIND: "FOTA","END", 0处断电
                self.at_handler.dfota_step_2()
                all_logger.info("在FOTA END 0处断电")
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end is False:  # 正常升级
                self.at_handler.dfota_step_2()
            else:
                self.at_handler.dfota_end_0()

    def upload_package_to_sftp(self):
        a_b_path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip')
        b_a_path = os.path.join(os.getcwd(), 'firmware', 'b-a.zip')
        for i in range(10):
            try:
                with paramiko.SSHClient() as client:
                    all_logger.info('sftp logging success!')
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect("192.168.30.10", username="quectel", password="centos@123")
                    transport = client.get_transport()

                    try:
                        all_logger.info('sftp mkdir')
                        sftp = paramiko.SFTPClient.from_transport(transport)
                        sftp.mkdir('/html/5G/{}'.format(self.package_dir))
                    except Exception as e:
                        all_logger.info('sftp mkdir fial: {}'.format(e))

                    all_logger.info('sftp upload file')
                    sftp.put(a_b_path, "/html/5G/{}/a-b.zip".format(self.package_dir))
                    sftp.put(b_a_path, "/html/5G/{}/b-a.zip".format(self.package_dir))

                all_logger.info('server package dir:\r\n/html/5G/{}'.format(self.package_dir))
                # 创建cache_sftp文件夹
                all_logger.info('sftp mkdir')
                if not os.path.exists(os.path.join(os.getcwd(), 'firmware', 'cache_sftp')):
                    os.mkdir(os.path.join(os.getcwd(), 'firmware', 'cache_sftp'))

                # 下载下来进行版本包对比
                all_logger.info('sftp download and compare')
                package_check_flag = False
                for file in ['a-b.zip', 'b-a.zip']:
                    r = requests.get('http://112.31.84.164:8300/5G/{}/{}'.format(self.package_dir, file))
                    cache_path = os.path.join(os.getcwd(), 'firmware', 'cache_sftp', file)
                    with open(cache_path, 'wb') as fp:
                        fp.write(r.content)
                    if not filecmp.cmp(cache_path, os.path.join(os.getcwd(), 'firmware', file), shallow=False):
                        all_logger.error("文件对比不同")
                        package_check_flag = True
                if package_check_flag:
                    continue

                break  # 成功跳出
            except Exception as e:
                all_logger.error(e)
        else:
            raise LinuxPCIEDFOTAError("请使用xftp软件，使用sftp协议，端口22，连接192.168.25.74，用户名：quectel，密码centos@123，检查内网是否可以正常连接")
        
    def read_poweron_urc(self, timeout=60):
        start_time = time.time()
        urc_value = []
        count = 0
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            while time.time() - start_time < timeout:
                read_value = self.at_handler.readline(at_port)
                if read_value != '':
                    urc_value.append(read_value)
                continue
            for urc in urc_value:
                if urc == '+QIND: PB DONE\r\n':
                    count = count + 1
            all_logger.info('{}s检测URC上报内容为{},且pb done上报{}次'.format(timeout, urc_value, count))
            
    def after_upgrade_check(self, a_b=False):
        """
        升级后进行的检查，包括:
        1. 版本号 ATI+CSUB
        2. 写号 AT+EGMR=1,7,"864505040004635"
        3. 查号 AT+EGMR=0,7
        4. SVN号检查 AT+EGMR=0,9
        5. 找网确认
        6. MBN查询AT+QMBNCFG="LIST"
        7. 备份CEFS AT+QPRTPARA=1
        8. 备份后检查 AT+QPRTPARA=4，能查询成功还原次数(返回值第二个参数)
        :return: True，检查成功，False，检查失败
        """
        all_logger.info("进行升级后版本号、查号写号、MBN备份还原找网检查")
        # 版本号
        for _ in range(10):
            return_value = self.at_handler.send_at('ATI+CSUB', 0.6)
            revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
            sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
            if a_b is False:
                if revision == self.prev_upgrade_revision and sub_edition == self.prev_upgrade_sub_edition:
                    break
            else:
                if revision == self.revision and sub_edition == self.sub_edition:
                    break
            time.sleep(1)
        else:
            raise LinuxPCIEDFOTAError('ATI查询的版本号和当前设置版本号不一致')

        # 写号
        return_value = self.at_handler.send_at('AT+EGMR=1,7,"864505040004635"', 0.3)
        if 'OK' not in return_value:
            raise LinuxPCIEDFOTAError("写号异常")

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxPCIEDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.prev_svn) not in return_value:
            raise LinuxPCIEDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常:\r\n{}".format(return_value))
                time.sleep(10)
        else:
            raise LinuxPCIEDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=4执行异常")
        else:
            raise LinuxPCIEDFOTAError("执行备份指令后查询异常")

    @staticmethod
    def make_dfota_package():
        """
        查找当前路径 + firmware + prev/cur路径下面的所有targetfiles.zip，然后制作差分包。
        :return: None
        """
        all_logger.info("开始制作差分包")
        orig_target_file = ''
        cur_target_file = ''

        firmware_path = os.path.join(os.getcwd(), 'firmware')
        for path, _, files in os.walk(os.path.join(firmware_path, 'prev')):
            for file in files:
                if file == 'targetfiles.zip':
                    orig_target_file = os.path.join(path, file)
        if not orig_target_file:
            raise LinuxPCIEDFOTAError("获取前一个版本target file zip失败")

        for path, _, files in os.walk(os.path.join(firmware_path, 'cur')):
            for file in files:
                if file == 'targetfiles.zip':
                    cur_target_file = os.path.join(path, file)
        if not cur_target_file:
            raise LinuxPCIEDFOTAError("获取当前版本target file zip失败")

        multi_thread_merge_version(orig_target_file, cur_target_file)

        # 兼容小米定制版本
        # if self.Is_XiaoMi_version:
        #     multi_thread_merge_fota_full_images(orig_target_file, cur_target_file)
        # else:
        #     multi_thread_merge_version(orig_target_file, cur_target_file)

    def check_module_version(self, is_cur):
        """
        检查版本信息是否正确
        :param is_cur: 检查版本是否为当前版本 True:升级到当前版本后检查;False:升级到上个A版本检查
        :return:
        """
        self.at_handler.send_at('ATE', 3)
        csub_value = self.at_handler.send_at('ATI+CSUB', 10)
        at_revison = ''.join(re.findall(r'Revision: (.*)', csub_value))
        at_sub = ''.join(re.findall(r'SubEdition: (.*)', csub_value))
        at_version = at_revison + at_sub
        version_r = re.sub(r'[\r\n]', '', at_version)
        revision_c = self.revision + self.sub_edition
        prev_upgrade_revision_p = self.prev_upgrade_revision + self.prev_upgrade_sub_edition
        if is_cur:
            if revision_c != version_r:
                print('cur')
                raise LinuxPCIEDFOTAError('系统下发版本号与升级后查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(revision_c, at_version))
        else:
            if prev_upgrade_revision_p != version_r:
                print('pre')
                raise LinuxPCIEDFOTAError('系统下发版本号与升级后查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(prev_upgrade_revision_p, at_version))

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
        # 转译路径中的特殊符号、防止使用失败
        package_name = package_name.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ').replace('(', '\(').replace(')', '\)')
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
                                   stderr=subprocess.STDOUT, shell=True)
        all_logger.info('QFirehose -f {} {}'.format(package_name, '-e' if erase else ''))
        os.set_blocking(upgrade.stdout.fileno(), False)
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
                    raise LinuxPCIEDFOTAError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise LinuxPCIEDFOTAError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise LinuxPCIEDFOTAError('120S内升级失败')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/cur')
        os.popen('umount /mnt/prev')

    @staticmethod
    def unzip_firmware():
        """
        解压当前路径 + firmware + prev/cur路径下面的所有zip包
        :return: None
        """
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        for path, _, files in os.walk(firmware_path):
            for file in files:
                # 避免有一些除版本包之外的其他包，例如存在modem.zip，直接删除
                if file.endswith('.zip') and 'modem' in file.lower():
                    os.remove(os.path.join(path, file))
                    continue
                # 如果是其他文件，解压
                if file.endswith('.zip'):
                    with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                        all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                        to_unzip.extractall(path)
        all_logger.info('解压固件成功')

    def mount_package(self):
        """
        挂载版本包
        :return:
        """
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        prev_package_path = self.prev_firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'cur' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/cur')
        if 'prev' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/prev')
        os.popen('mount -t cifs {} /mnt/cur -o user="cris.hu@quectel.com",password="hxc111...."'.format(cur_package_path)).read()
        os.popen('mount -t cifs {} /mnt/prev -o user="cris.hu@quectel.com",password="hxc111...."'.format(prev_package_path)).read()
        if os.listdir('/mnt/cur') and os.listdir('/mnt/prev'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise LinuxPCIEDFOTAError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def ubuntu_copy_file():
        """
        Ubuntu下复制版本包
        :return:
        """
        os.mkdir(os.getcwd() + '/firmware')
        os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/cur')
        os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/prev')

        cur_file_list = os.listdir('/mnt/cur')
        all_logger.info('/mnt/cur目录下现有如下文件:{}'.format(cur_file_list))
        all_logger.info('开始复制当前版本版本包到本地')
        for i in cur_file_list:
            shutil.copy(os.path.join('/mnt/cur', i), os.path.join(os.getcwd(), 'firmware', 'cur'))

        prev_file_list = os.listdir('/mnt/prev')
        all_logger.info('/mnt/prev目录下现有如下文件:{}'.format(prev_file_list))
        all_logger.info('开始复制上一版本版本包到本地')
        for i in prev_file_list:
            shutil.copy(os.path.join('/mnt/prev', i), os.path.join(os.getcwd(), 'firmware', 'prev'))

        if os.path.join(os.getcwd(), 'firmware', 'cur') and os.path.join(os.getcwd(), 'firmware', 'prev'):
            all_logger.info('版本获取成功')
        else:
            raise LinuxPCIEDFOTAError('版本包获取失败')


class ATBackgroundThreadWithDriverCheck(Thread):

    """
    用于类似quectel-CM拨号后上报拨号状态URC的检测：
    首先创建ATBackgroundThread，然后进行quectel-CM拨号，最后检查ATBackgroundThread中读取到的AT。
    """

    def __init__(self, at_port, dm_port):
        super().__init__()
        self._at_port = at_port
        self._dm_port = dm_port
        self.dq = deque(maxlen=1000)
        self.flag = True
        self.daemon = True
        self.start()

    def run(self):
        self.check_usb_driver()
        for i in range(100):
            try:
                at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(0.1)
                continue
        else:
            raise LinuxPCIEDFOTAError("检测DFOTA升级时打开AT口异常")

        while self.flag:
            time.sleep(0.001)  # 减少资源占用
            return_value = self.readline(at_port)
            if return_value:
                self.dq.append(return_value)
        at_port.close()

    def get_info(self):
        self.flag = False
        return ''.join(self.dq)

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

    def check_usb_driver(self):
        """
        检测驱动是否出现
        :return: True:检测到驱动；False：没有检测到驱动
        """
        all_logger.info('检测驱动加载')
        check_usb_driver_start_timestamp = time.time()
        timeout = 300
        while True:
            port_list = self.get_port_list()
            check_usb_driver_total_time = time.time() - check_usb_driver_start_timestamp
            if check_usb_driver_total_time < timeout:  # timeout S内
                if self._at_port in port_list and self._dm_port in port_list:  # 正常情况
                    all_logger.info('USB驱动{}加载成功!'.format(self._at_port))
                    time.sleep(0.1)  # 延迟0.1秒避免端口打开异常
                    return True
                elif self._dm_port in port_list and self._at_port not in port_list:  # 发现仅有DM口并且没有AT口
                    time.sleep(3)  # 等待3S口还是只有AT口没有DM口判断为DUMP，RG502QEAAAR01A01M4G出现两个口相差1秒
                    port_list = self.get_port_list()
                    if self._dm_port in port_list and self._at_port not in port_list:
                        all_logger.error('模块DUMP')
                        self.check_usb_driver()
                else:
                    time.sleep(0.1)  # 降低检测频率，减少CPU占用
            else:  # timeout秒驱动未加载
                all_logger.error("模块开机{}秒内USB驱动{}加载失败".format(timeout, self._at_port))
                return False
