from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import PretestError
from utils.functions.gpio import GPIO
import subprocess
from subprocess import STDOUT, PIPE
from collections import defaultdict
from zipfile import ZipFile
import serial.tools.list_ports
import filecmp
import shutil
import serial
import time
import os
import sys
import re
import traceback
from utils.pages.page_fw_download import PageFWDownload
from utils.pages.page_usb_view import PageUSBView
from utils.functions.setupapi import get_ports_hardware_id
from utils.functions.case import is_laptop
from utils.functions.fw import FW
from utils.functions.debug_exec import DebugPort


class WindowsPretestManager:
    def __init__(self, firmware_path, revision, sub_edition, fw_download_path, name_real_version, at_port=None, dm_port=None, modem_port=None, debug_port=None, vid_pid_rev='VID_2C7C/PID_0800/REV_0414'):
        self.at_port = at_port
        self.dm_port = dm_port
        self.modem_port = modem_port
        self.debug_port = debug_port
        self.firmware_path = firmware_path
        self.page_fw_download = PageFWDownload()
        self.page_usb_view = PageUSBView()
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.windows_api = WindowsAPI()
        self.modem_port = modem_port
        self.vid_pid_rev = vid_pid_rev
        self.revision = revision
        self.sub_edition = sub_edition
        self.fw_download_path = fw_download_path
        self.product = 'RG500'  # 暂时不用的参数
        self.default_apns = None
        self.gpio = GPIO()
        self.name_real_version = name_real_version

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

    def copy_firmware(self):
        """
        复制路径的所有文件，用于复制共享的升级包到本地。
        :return: None
        """
        current_path = os.path.join(os.getcwd(), 'firmware')
        all_logger.info(f'robocopy "{self.firmware_path}" "{current_path}" /MIR')
        s = subprocess.Popen(f'robocopy "{self.firmware_path}" "{current_path}" /MIR', shell=True,
                             stdout=PIPE, stderr=STDOUT, text=True)
        while s.poll() is None:
            time.sleep(0.001)
            outs = s.stdout.readline()
            if '.zip' in outs:
                all_logger.info(repr(outs))
            if ''.join(re.findall(r'\d+\.0%', outs)):
                all_logger.info(re.sub(r"\.0| |\\n|'", '', repr(outs)))
        for file in os.listdir(current_path):
            if not filecmp.cmp(os.path.join(current_path, file), os.path.join(self.firmware_path, file)):
                raise PretestError("复制文件对比异常")

    @staticmethod
    def unzip_firmware():
        """
        解压固件
        :return: None
        """
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        for file in os.listdir(firmware_path):
            if file.endswith('.zip') and len(file.strip(".zip")) > 10:  # zip结尾，并且不是factory.zip结尾，并且名字大于10位，例如RG500QEAAA是10位，大于10位
                with ZipFile(os.path.join(firmware_path, file), 'r') as to_unzip:
                    all_logger.info(f'exact {os.path.join(firmware_path, file)} to {firmware_path}')
                    to_unzip.extractall(firmware_path)

    @staticmethod
    def check_cefs_bin():
        """
        检查partition_nand.xml和rawprogram_nand_p4K_b256K_update.xml文件是否正常
        :return:
        """
        # 获取工厂包和标准包路径
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        factory_firmware = ''.join(d for d in os.listdir(firmware_path)
                                   if os.path.isdir(os.path.join(firmware_path, d)) and d.lower().endswith('factory'))
        if not factory_firmware:
            raise PretestError("未发现factory包")

        standard_firmware = re.sub(r'_factory', '', factory_firmware, re.IGNORECASE)
        if not standard_firmware:
            raise PretestError("未发现标准包")

        factory_firmware_path = os.path.join(firmware_path, factory_firmware)
        standard_firmware_path = os.path.join(firmware_path, standard_firmware)

        # 查看update/partition_nand.xml 标准包不能有cefs.mbn，工厂包有
        # 查看rawprogram_nand_p4K_b256K_update.xml 标准包不能含有cefs.mbn，工厂包有
        # 标准包整个包内不能含有cefs.mbn
        for path, dirs, files in os.walk(standard_firmware_path):
            for file in files:
                if file == 'cefs.mbn':
                    raise PretestError("标准包中发现含有cefs.mbn文件")
                if file == 'partition_nand.xml':
                    with open(os.path.join(path, file)) as f:
                        if 'cefs.mbn' in f.read():
                            raise PretestError("标准包中partition_nand.xml文件发现含有cefs.mbn配置")
                if file == 'rawprogram_nand_p4K_b256K_update.xml':
                    with open(os.path.join(path, file)) as f:
                        if 'cefs.mbn' in f.read():
                            raise PretestError("标准包中rawprogram_nand_p4K_b256K_update.xml文件发现含有cefs.mbn配置")

        mbn_flag = False
        for path, dirs, files in os.walk(factory_firmware_path):
            for file in files:
                if file == 'cefs.mbn':
                    mbn_flag = True
                if file == 'partition_nand.xml':
                    with open(os.path.join(path, file)) as f:
                        if 'cefs.mbn' not in f.read():
                            raise PretestError("工厂包中partition_nand.xml文件未发现cefs.mbn配置")
                if file == 'rawprogram_nand_p4K_b256K_factory.xml':
                    with open(os.path.join(path, file)) as f:
                        if 'cefs.mbn' not in f.read():
                            raise PretestError("工厂包中rawprogram_nand_p4K_b256K_factory.xml文件未发现cefs.mbn配置")
        if mbn_flag is False:
            raise PretestError("工厂包未包含cefs.mbn文件")

    @staticmethod
    def upgrade_subprocess_wrapper(*, cmd, cwd, timeout, check_message='All Finished Successfully', error_message):
        s = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=PIPE, stderr=STDOUT, text=True)
        try:
            outs, err = s.communicate(timeout=timeout)
            all_logger.info(outs)
            if check_message not in outs:
                all_logger.error(outs)
                raise RuntimeError(error_message)
        except subprocess.TimeoutExpired:
            s.terminate()
            outs, err = s.communicate()
            all_logger.error(outs)
            raise TimeoutError(error_message)

    @staticmethod
    def get_firmware_firehose_path(local_firmware_path):
        """
        获取升级包中update/firehose路径的位置。
        :return: None
        """
        for path, dirs, files in os.walk(local_firmware_path):
            for file in files:
                if file.startswith('prog_firehose_'):
                    mbn_name = file
                    all_logger.info(f"版本包firehose文件夹的mbn名称为: {mbn_name}")
                    return mbn_name

    def qfil(self, dl_port: str):
        """
        进行QFile升级
        :param dl_port: 紧急下载口
        :return: None
        """

        fh_cmd = ' --noprompt --showpercentagecomplete --zlpawarehost=1 --memoryname=nand'

        def upgrade_subprocess_wrapper(*, cmd, cwd, timeout, check_message='All Finished Successfully', error_message):
            """
            升级的依赖函数
            :param cmd: 命令
            :param cwd: 当前工作路径
            :param timeout: 超时时间
            :param check_message: 检查的信息
            :param error_message: 需要返回的异常信息
            :return:
            """
            s = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=PIPE, stderr=STDOUT, text=True)
            try:
                outs, err = s.communicate(timeout=timeout)
                all_logger.info(outs)
                if check_message not in outs:
                    all_logger.error(outs)
                    raise Exception(error_message)
            except subprocess.TimeoutExpired:
                s.terminate()
                outs, err = s.communicate()  #
                all_logger.error(outs)
                raise Exception(error_message)

        all_logger.info('get qfil path')
        qfil_possible_path = [r'C:\Program Files (x86)\Qualcomm', r'C:\Program Files\Qualcomm']
        qfil_path = ''
        for p in qfil_possible_path:
            for path, _, files in os.walk(p):
                if 'fh_loader.exe' in files and 'QSaharaServer.exe' in files:
                    qfil_path = path
        if not qfil_path:
            raise Exception("请确认QFIL工具是否安装和QFIL工具是否是默认安装路径，{}路径中未找到相关文件".format('和'.join(qfil_possible_path)))

        all_logger.info("get factory firehose path")
        factory_package_path = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', p)):
                if p.lower().endswith('factory'):
                    factory_package_path = os.path.join(os.getcwd(), 'firmware', p)
        if not factory_package_path:
            raise Exception("未找到factory升级包")

        firehose_path = os.path.join(factory_package_path, 'update', 'firehose')
        for file in ['prog_firehose_sdx55.mbn', "rawprogram_nand_p4K_b256K_factory.xml", 'patch_p4K_b256K.xml']:
            if file not in os.listdir(firehose_path):
                print(f"升级包firehose目录内未发现{file}")

        # simplify set search_path in subprocess and fh_loader.exe command
        all_logger.info("copy QSaharaServer and fh_loader to firehose dir")
        if not os.path.exists(os.path.join(firehose_path, 'QSaharaServer.exe')):
            shutil.copy(os.path.join(qfil_path, 'QSaharaServer.exe'), firehose_path)
        if not os.path.exists(os.path.join(firehose_path, 'fh_loader.exe')):
            shutil.copy(os.path.join(qfil_path, 'fh_loader.exe'), firehose_path)

        all_logger.info("load firehose programmer")
        load_programmer = fr'QSaharaServer.exe -s 13:{self.get_firmware_firehose_path(firehose_path)} -p \\.\{dl_port}'
        upgrade_subprocess_wrapper(
            cmd=load_programmer,
            cwd=firehose_path,
            timeout=10,
            check_message='Sahara protocol completed',
            error_message='QSaharaServer指令失败'
        )

        all_logger.info('wait 5 seconds')
        time.sleep(5)

        all_logger.info("erase with xml")
        # 1. create xml
        with open(os.path.join(firehose_path, 'erase.xml'), 'w') as f:
            f.write('<?xml version="1.0"?>\n<data>\n  <erase physical_partition_number="0" start_sector="0" />\n</data>')
        erase_xml = fr'fh_loader.exe --port=\\.\{dl_port} --sendxml=erase.xml --search_path={firehose_path} {fh_cmd}'
        upgrade_subprocess_wrapper(
            cmd=erase_xml,
            cwd=firehose_path,
            timeout=30,
            error_message='XML方式flash全擦失败'
        )

        all_logger.info("erase with partition")
        erase_0 = fr'fh_loader.exe --port=\\.\{dl_port} --erase=0 {fh_cmd}'
        upgrade_subprocess_wrapper(
            cmd=erase_0,
            cwd=firehose_path,
            timeout=30,
            error_message='指定分区方式flash全擦失败'
        )

        all_logger.info("download package")
        all_in_one = fr'fh_loader.exe --port=\\.\{dl_port} --sendxml=rawprogram_nand_p4K_b256K_factory.xml,patch_p4K_b256K.xml --search_path={firehose_path} {fh_cmd} --reset'
        upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=firehose_path,
            timeout=180,
            error_message='升级失败'
        )

    def switch_edl_mode(self):
        """
        切换EDL mode
        :return: None
        """
        # 转到下载口
        dl_port = ''
        for i in range(3):
            all_logger.info("switch to dl port")
            with serial.Serial(self.dm_port, baudrate=115200, timeout=0.8) as s:
                all_logger.info("send edl command")
                s.write(bytes.fromhex('4b650100540f7e'))
                all_logger.info("send edl command success")
            start = time.time()
            while not dl_port and time.time() - start < 30:
                time.sleep(1)
                all_logger.info(f'{int(time.time() - start)}S')
                dl_port = ''.join(num for num, name, _ in serial.tools.list_ports.comports() if '9008' in name)
            if dl_port:
                all_logger.info('wait 10 seconds')
                time.sleep(10)
                return dl_port
        else:
            raise Exception("切换紧急下载口失败")

    @staticmethod
    def get_ser_ports_mapping(ports):
        """
        获取AT、DM、NEMA、Modem口映射
        :param ports: 当前的端口列表
        :return: 端口列表映射
        """
        port_dict = defaultdict(list)
        ser_id = ''
        for num, name, info in serial.tools.list_ports.comports():
            port = ''.join(re.findall(r'(AT|DM|NMEA|Modem)', name))
            ser = ''.join(re.findall(r'SER=(\S+) ', info))
            if port and ser:
                port_dict[ser].append(num)
                if num in list(ports.values()):
                    ser_id = ser
        if not ser_id:
            raise Exception("获取端口SER属性失败")
        all_logger.info(port_dict)
        all_logger.info(ser_id)
        return port_dict[ser_id]

    def qfil_upgrade_and_check(self):
        """
        进行QFIL升级并检查
        :return: True
        """
        # 获取模块的SER, 和对应所有SER的端口，用于后续升级后端口检查
        ports = {'at_port': self.at_port, 'dm_port': self.dm_port}
        port_list = self.get_ser_ports_mapping(ports)
        all_logger.info(f'current port list: {port_list}')

        # 切换紧急下载
        dl_port = self.switch_edl_mode()

        # 升级
        self.qfil(dl_port)

        # 获取升级后的端口
        all_logger.info("对比升级前后端口")
        start = time.time()
        while time.time() - start < 180:
            port_list_after_download = self.driver.get_port_list()
            all_logger.info(f'port_list_after_download{port_list_after_download}')
            if len(list(set(port_list) & set(port_list_after_download))) == len(port_list):
                return True
            time.sleep(1)
        else:
            port_list_after_download = self.driver.get_port_list()
            raise Exception(f"升级前后端口列表不同，升级前{port_list}，升级后{port_list_after_download}")

    def check_modem_port_connectivity(self):
        """
        检查MODEM口是否可以正常通信
        :return: True:检查正常，False：检查异常
        """
        all_logger.info("检查Modem口是否正常")
        all_logger.info(f"modem_port: {self.modem_port}")
        with serial.Serial(self.modem_port, baudrate='115200', timeout=0.8) as modem_port:
            all_logger.info(f"modem_port.dtr: {modem_port.dtr}")
            all_logger.info(f"modem_port.rts: {modem_port.rts}")
            for i in range(3):
                all_logger.info(b'AT\r\n')
                modem_port.write(b'AT\r\n')
                time.sleep(0.1)
                data = modem_port.read(size=1024).decode('utf-8', 'ignore')
                all_logger.info(repr(data))
                if 'OK' in data and 'AT' in data:
                    return True
            else:
                raise Exception("Modem口检查异常")

    def check_modemrstlevel_aprstlevel_default_value(self):
        """
        检查modemrstlevel默认值。
        :return: None
        """
        modemrstlevel = self.at_handler.send_at('at+qcfg="modemrstlevel"')
        aprstlevel = self.at_handler.send_at('at+qcfg="aprstlevel"')
        if '"ModemRstLevel",1' not in modemrstlevel:
            raise Exception(f"ModemRstLevel默认值异常: {modemrstlevel}")
        if '"ApRstLevel",1' not in aprstlevel:
            raise Exception(f"ApRstLevel默认值异常: {aprstlevel}")

    def erase_all_partitions(self, dl_port):
        """
        擦除所有的分区
        :param dl_port: emergency download port num
        :return: None
        """

        fh_cmd = ' --noprompt --showpercentagecomplete --zlpawarehost=1 --memoryname=nand'

        def upgrade_subprocess_wrapper(*, cmd, cwd, timeout, check_message='All Finished Successfully',
                                       error_message):
            s = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=PIPE, stderr=STDOUT, text=True)
            try:
                outs, err = s.communicate(timeout=timeout)
                all_logger.info(outs)
                if check_message not in outs:
                    all_logger.error(outs)
                    raise Exception(error_message)
            except subprocess.TimeoutExpired:
                s.terminate()
                outs, err = s.communicate()  #
                all_logger.error(outs)
                if check_message in outs:
                    all_logger.error(f"cmd: {cmd} timeout，but returned success!")
                    return True
                else:
                    raise TimeoutError(error_message)

        all_logger.info('get qfil path')
        qfil_possible_path = [r'C:\Program Files (x86)\Qualcomm', r'C:\Program Files\Qualcomm']
        qfil_path = ''
        for p in qfil_possible_path:
            for path, _, files in os.walk(p):
                if 'fh_loader.exe' in files and 'QSaharaServer.exe' in files:
                    qfil_path = path
        if not qfil_path:
            raise Exception("请确认QFIL工具是否安装和QFIL工具是否是默认安装路径，{}路径中未找到相关文件".format('和'.join(qfil_possible_path)))

        all_logger.info("get factory firehose path")
        factory_package_path = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', p)):
                if p.lower().endswith('factory'):
                    factory_package_path = os.path.join(os.getcwd(), 'firmware', p)
        if not factory_package_path:
            raise Exception("未找到factory升级包")

        firehose_path = os.path.join(factory_package_path, 'update', 'firehose')
        for file in ['prog_firehose_sdx55.mbn', "rawprogram_nand_p4K_b256K_factory.xml", 'patch_p4K_b256K.xml']:
            if file not in os.listdir(firehose_path):
                print(f"升级包firehose目录内未发现{file}")

        # simplify set search_path in subprocess and fh_loader.exe command
        all_logger.info("copy QSaharaServer and fh_loader to firehose dir")
        if not os.path.exists(os.path.join(firehose_path, 'QSaharaServer.exe')):
            shutil.copy(os.path.join(qfil_path, 'QSaharaServer.exe'), firehose_path)
        if not os.path.exists(os.path.join(firehose_path, 'fh_loader.exe')):
            shutil.copy(os.path.join(qfil_path, 'fh_loader.exe'), firehose_path)

        all_logger.info("load firehose programmer")
        load_programmer = fr'QSaharaServer.exe -s 13:{self.get_firmware_firehose_path(firehose_path)} -p \\.\{dl_port}'
        upgrade_subprocess_wrapper(
            cmd=load_programmer,
            cwd=firehose_path,
            timeout=10,
            check_message='Sahara protocol completed',
            error_message='QSaharaServer指令失败'
        )

        all_logger.info('wait 5 seconds')
        time.sleep(5)

        all_logger.info("erase with xml")
        # 1. create xml
        with open(os.path.join(firehose_path, 'erase.xml'), 'w') as f:
            f.write(
                '<?xml version="1.0"?>\n<data>\n  <erase physical_partition_number="0" start_sector="0" />\n</data>')
        erase_xml = fr'fh_loader.exe --port=\\.\{dl_port} --sendxml=erase.xml --search_path={firehose_path} {fh_cmd}'
        upgrade_subprocess_wrapper(
            cmd=erase_xml,
            cwd=firehose_path,
            timeout=30,
            error_message='XML方式flash全擦失败'
        )

        all_logger.info("erase with partition")
        erase_0 = fr'fh_loader.exe --port=\\.\{dl_port} --erase=0 {fh_cmd}'
        upgrade_subprocess_wrapper(
            cmd=erase_0,
            cwd=firehose_path,
            timeout=30,
            error_message='指定分区方式flash全擦失败'
        )

        all_logger.info("reset")
        erase_0 = fr'fh_loader.exe --port=\\.\{dl_port} --reset {fh_cmd}'
        upgrade_subprocess_wrapper(
            cmd=erase_0,
            cwd=firehose_path,
            timeout=30,
            error_message='擦除所有分区后重置失败'
        )

        all_logger.info('wait 30 seconds')
        time.sleep(30)

    def fw_download(self, dl_port):
        """
        调用FW download工具
        :param dl_port: emergency download port
        :return: None
        """
        self.page_fw_download.element_login_ok_button.click()
        self.page_fw_download.element_settings_button.click()
        self.page_fw_download.element_passwd_edit.set_text("quectel")
        self.page_fw_download.element_passwd_ok_button.click()
        self.page_fw_download.element_operation_mode_combobox.select("Manual DL")
        reset_status = self.page_fw_download.element_reset_after_down_button.get_toggle_state()
        if reset_status == 0:
            self.page_fw_download.element_reset_after_down_button.click()
        dl_port = dl_port.replace("COM", '').replace('com', '')
        self.page_fw_download.element_first_download_edit.set_text(dl_port)
        self.page_fw_download.element_settings_ok_button.click()
        self.page_fw_download.element_load_fw_files.click()
        self.page_fw_download.element_passwd_edit.set_text("quectel")
        self.page_fw_download.element_passwd_ok_button.click()

        all_logger.info("get factory firehose path")
        factory_package_path = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', p)):
                if p.lower().endswith('factory'):
                    factory_package_path = os.path.join(os.getcwd(), 'firmware', p)
        if not factory_package_path:
            raise Exception("未找到factory升级包")

        firehose_path = os.path.join(factory_package_path, 'update', 'firehose')
        mbn_name = self.get_firmware_firehose_path(firehose_path)
        mbn_path = os.path.join(firehose_path, mbn_name)
        if not os.path.exists(mbn_path):
            raise Exception("未找到MBN文件")

        self.page_fw_download.element_mbn_path_edit.set_text(mbn_path)
        self.page_fw_download.element_mbn_ok_button.click()
        self.page_fw_download.element_first_download_button.click()

    def open_fw_download(self):
        """
        打开FW download工具
        :return: None
        """
        os.popen('taskkill /f /t /im "FW_Download*"').read()
        fw_path = ''
        for path, _, files in os.walk(self.fw_download_path):
            for file in files:
                if file.upper().startswith("FW_DOWNLOAD") and file.upper().endswith(".EXE"):
                    fw_path = os.path.join(path, file)
        if not fw_path:
            raise Exception("FW_Download工具路径异常")
        self.fw_download_path = os.path.dirname(fw_path)  # 为了防止填写的路径有问题，获取.exe文件的路径
        subprocess.Popen(fw_path, shell=True, cwd=self.fw_download_path)
        for i in range(5):
            all_logger.info("wait 5 seconds")
            time.sleep(5)
            if self.page_fw_download.element_login_ok_button.exists():
                all_logger.info("已成功查找到FW登录按钮")
                return True
            else:
                continue
        else:
            raise PretestError("打开FW工具未检查到登录按钮")

    def fw_download_and_check(self):
        """
        FW download升级后检查升级后是否正常。
        :return: None
        """
        # 获取模块的SER, 和对应所有SER的端口，用于后续升级后端口检查
        ports = {'at_port': self.at_port, 'dm_port': self.dm_port}
        port_list = self.get_ser_ports_mapping(ports)

        # 切换紧急下载
        dl_port = self.switch_edl_mode()

        # 擦除所有分区
        self.erase_all_partitions(dl_port)

        self.open_fw_download()

        # 升级
        self.fw_download(dl_port)

        # 获取升级后的端口
        all_logger.info("对比升级前后端口")
        start = time.time()
        while time.time() - start < 300:
            port_list_after_download = self.driver.get_port_list()
            all_logger.info(f'port_list_after_download{port_list_after_download}')
            if len(list(set(port_list) & set(port_list_after_download))) == len(port_list):
                os.popen('taskkill /f /t /im FW_Download*').read()
                return True
            time.sleep(1)
        else:
            port_list_after_download = self.driver.get_port_list()
            os.popen('taskkill /f /t /im FW_Download*').read()
            raise Exception(f"升级前后端口列表不同，升级前{port_list}，升级后{port_list_after_download}")

    def get_auto_sel(self):
        """
        获取MBN的默认激活状态是否正常
        :return:
        """
        res = self.at_handler.send_at('AT+QMBNCFG="Autosel"')
        if '"AutoSel",1' not in res:
            raise Exception(f"MBN默认激活状态查询异常{res}")

    def get_usb_view_info(self):
        """
        检查模块的iManufacturer和iProduct值
        :return: None
        """
        # kill usb_view
        subprocess.call('taskkill /f /t /im "usbview*"', shell=True)

        # 打开usbview.exe
        usbview_path = ''
        for path, _, files in os.walk(os.getcwd()):
            for file in files:
                if file == 'usbview.exe':
                    usbview_path = os.path.join(path, file)
        else:
            if not usbview_path:
                raise Exception("未找到usbview.exe文件")
        subprocess.Popen(usbview_path, shell=True)

        self.page_usb_view.element_usb_view_main_page.set_focus()
        hub_info = self.page_usb_view.element_hub_list.descendants()
        ports = re.findall(r"(\[Port\d+]\s+:\s+Highspeed USB.*?Device|\[Port\d+]\s+:\s+Quectel USB.*?Device)", str(hub_info))
        all_logger.info(ports)
        for port in ports:
            self.page_usb_view.element_hub_usb(port).click_input()
            port_info = self.page_usb_view.element_port_info_edit.get_value()
            all_logger.info(port_info)
            manufacturer = ''.join(re.findall(r'iManufacturer.*?\r\n.*"(.*?)"', port_info))
            product = ''.join(re.findall(r'iProduct.*?\r\n.*"(.*?)"', port_info))
            if 'Quectel' == manufacturer and self.product == product:
                return True
        else:
            raise Exception("usbview未获取到正确的iManufacturer和iProduct")

    def check_pid_vid_rev_mi(self):
        """
        检查模块的PID，VID，REV，MI
        :return: None
        """
        vid = ''.join(re.findall(r'(VID_\S+?)&', self.vid_pid_rev))
        pid = ''.join(re.findall(r'(PID_\S+?)&', self.vid_pid_rev))
        rev = ''.join(re.findall(r'(REV_\S+?)&', self.vid_pid_rev))
        pid_vid_rev = vid, pid, rev
        _vid = re.sub(r'VID_', '', pid_vid_rev[0], re.IGNORECASE)
        _pid = re.sub(r'PID_', '', pid_vid_rev[1], re.IGNORECASE)
        _rev = re.sub(r'REV_', '', pid_vid_rev[2], re.IGNORECASE)
        print(_vid, _pid, _rev)
        # 获取模块的SER, 和对应所有SER的端口，用于后续升级后端口检查
        port_list = self.get_ser_ports_mapping({'at_port': self.at_port, 'dm_port': self.dm_port})
        for port in get_ports_hardware_id():
            if port.num in port_list:
                info = re.findall(r"VID_(?P<VID>.*?)&PID_(?P<PID>.*?)&REV_(?P<REV>.*?)&MI_(?P<MI>\d+)", port.hwid)
                if not info:
                    all_logger.info(list(get_ports_hardware_id()))
                    raise Exception("获取端口详细信息失败")
                [(vid, pid, rev, mi)] = info
                if vid != _vid or pid != _pid or rev != _rev:
                    raise Exception("端口PID VID REV异常")
                if mi == '00' and port.desc != 'Quectel USB DM Port':
                    raise Exception(f"Quectel USB DM口的MI值应该是00，查询为{mi}")
                if mi == '01' and port.desc != 'Quectel USB NMEA Port':
                    raise Exception(f"Quectel USB NMEA口的MI值应该是01，查询为{mi}")
                if mi == '02' and port.desc != 'Quectel USB AT Port':
                    raise Exception(f"Quectel USB AT口的MI值应该是02，查询为{mi}")
                if mi == '03' and port.desc != 'Quectel USB Modem':
                    print(port.desc)
                    raise Exception(f"Quectel USB MODEM口的MI值应该是03，查询为{mi}")

    def force_restart(self):
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        time.sleep(1)
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.at_handler.check_network()
        all_logger.info('wait 30 seconds')
        time.sleep(30)

    def get_mbn_status(self):
        for i in range(20):
            self.at_handler.send_at('at+cgdcont?', timeout=15)
            mbn_status = self.at_handler.send_at('at+qmbncfg="list"', timeout=15)
            if 'OK' in mbn_status and ",0,1,1" in mbn_status:
                break
            time.sleep(3)
        else:
            all_logger.error('case执行前初始化查询MBN列表异常')

    def pretest_upgrade_erase(self):
        laptop = is_laptop(self.name_real_version)
        if laptop:
            exc_type = None
            exc_value = None
            try:
                fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                        factory=True, ati=self.revision, csub=self.sub_edition)
                fw.upgrade()
                time.sleep(10)
                self.at_handler.check_network()
                self.check_pid_vid_rev_mi()
                self.at_handler.check_at_port_stability()
                self.check_modem_port_connectivity()
                self.check_modemrstlevel_aprstlevel_default_value()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                time.sleep(5)
                if exc_type and exc_value:
                    raise exc_type(exc_value)

        elif os.name == "nt":
            exc_type = None
            exc_value = None
            debug_port = DebugPort(self.debug_port)
            debug_port.setDaemon(True)
            debug_port.start()
            try:
                self.qfil_upgrade_and_check()
                self.check_pid_vid_rev_mi()
                self.at_handler.check_at_port_stability()
                self.at_handler.check_version(self.revision, self.sub_edition)
                self.check_modem_port_connectivity()
                self.check_modemrstlevel_aprstlevel_default_value()
                # self.at_handler.check_qtest_dump()
            except Exception as e:
                all_logger.error(traceback.format_exc())
                all_logger.info(e)
                exc_type, exc_value, _ = sys.exc_info()
            finally:
                if exc_type and exc_value:
                    all_logger.error(f"exc_type:{exc_type} \n exc_value:{exc_value}")
                    debug_port.close_debug()
                    raise exc_type(exc_value)
                all_logger.info("wait 30 seconds wait USB_STATE")
                time.sleep(30)  # 等待USB_STATE变化
                usb_state = debug_port.exec_command("dmesg | grep USB_STATE")
                debug_port.close_debug()
                if len(re.findall(r"CONFIGURED", usb_state)) > 1:
                    raise PretestError("升级后模块第一次开机dmesg | grep USB_STATE出现多次CONFIGURED")

    def switch_laptop_urc(self):
        """
        适配笔电项目URC上报口
        """
        laptop = is_laptop(self.name_real_version)
        if laptop:
            all_logger.info('笔电项目修改urc上报口为modem')
            self.at_handler.send_at('at+qurccfg="urcport","usbmodem"')
        else:
            all_logger.info('当前为非笔电项目,上报口为AT口')
