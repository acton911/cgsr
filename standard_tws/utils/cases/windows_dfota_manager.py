import glob
import random
import shutil
import time
from collections import defaultdict
import serial.tools.list_ports
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI
from utils.exception.exceptions import WindowsDFOTAError, LinuxATUpgradeError
from utils.functions.jenkins import multi_thread_merge_version, multi_thread_merge_fota_full_images
from utils.operate.uart_handle import UARTHandle
import subprocess
from utils.logger.logging_handles import all_logger, at_logger
from subprocess import STDOUT, PIPE
from zipfile import ZipFile
from collections import deque
import filecmp
import os
from ftplib import FTP
import requests
import paramiko
import re
from threading import Thread
from utils.functions.getpassword import getpass
import hashlib
from getpass import getuser
from utils.functions.gpio import GPIO
from utils.functions.decorators import watchdog
from functools import partial


class WindowsDFOTAManager:

    def __init__(self, uart_port, revision, sub_edition, prev_upgrade_revision, svn, prev_upgrade_sub_edition, prev_svn, at_port, dm_port, modem_port, prev_firmware_path, firmware_path):
        self.at_port = at_port
        self.dm_port = dm_port
        self.modem_port = modem_port
        self.firmware_path = firmware_path
        self.revision = revision
        self.sub_edition = sub_edition
        self.prev_upgrade_revision = prev_upgrade_revision
        self.prev_upgrade_sub_edition = prev_upgrade_sub_edition
        self.prev_firmware_path = prev_firmware_path
        self.prev_svn = prev_svn
        self.check_prev_data()
        self.svn = svn
        self.uart_port = uart_port
        self.uart_handler = UARTHandle(uart_port)
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.windows_api = WindowsAPI()
        md5 = hashlib.md5()
        md5.update(f'{self.revision}{self.sub_edition}{self.prev_upgrade_revision}{self.prev_upgrade_sub_edition}'.encode('utf-8'))
        self.package_dir = md5.hexdigest()[:10]   # 创建一个文件夹，用于在ftp和http(s)服务器上创建，避免重复
        self.tws_cache_dir = self.get_tws_cache_dir()
        self.gpio = GPIO()
        self.Is_XiaoMi_version = True if '_XM' in self.revision else False

    def check_prev_data(self):
        if not self.prev_upgrade_revision or not self.prev_upgrade_sub_edition or not self.prev_firmware_path or not self.prev_svn:
            raise WindowsDFOTAError("未检查到数据库填写的prev_upgrade_revision/prev_upgrade_sub_edition/prev_firmware_path"
                                    "/prev_svn相关参数或者CI传参异常，请检查数据库中name_sub_version是否存在，是否有空格，是否有重复名称")

    def get_tws_cache_dir(self):
        if os.name == 'nt':
            return os.path.join("C:\\Users", getuser(), 'TWS_TEST_DATA')
        else:
            raise NotImplementedError("暂未实现")

    def copy_firmware(self):
        """
        复制路径的所有文件，用于复制共享的升级包到本地。
        复制的路径为脚本运行路径 + firmware文件夹，a-b升级过程中，a版本放在prev，升级后的b版本(当前版本)放在cur文件版
        return: None
        """
        for path, firmware_path in zip(['prev', 'cur'], [self.prev_firmware_path, self.firmware_path]):
            # 查找缓存是否存在
            all_logger.info(f"path: {path}\nfirmware_path: {firmware_path}")
            cache_path = os.path.join(self.tws_cache_dir, 'PackageCache', os.path.basename(firmware_path))
            if os.path.exists(cache_path):
                firmware_path = cache_path
            current_path = os.path.join(os.getcwd(), 'firmware', path)
            all_logger.info(f'robocopy "{firmware_path}" "{current_path}" /MIR')
            s = subprocess.Popen(f'robocopy "{firmware_path}" "{current_path}" /MIR', shell=True,
                                 stdout=PIPE, stderr=STDOUT, text=True)
            while s.poll() is None:
                outs = s.stdout.readline()
                if '.zip' in outs:
                    all_logger.info(repr(outs))
                if ''.join(re.findall(r'\d+\.0%', outs)):
                    all_logger.info(re.sub(r"\.0| |\\n|'", '', repr(outs)))
            # 如果缓存不存在版本包，则复制到缓存
            if not os.path.exists(cache_path):
                s = subprocess.run(f'robocopy "{current_path}" "{cache_path}" /MIR', shell=True,
                                   stdout=PIPE, stderr=STDOUT, text=True)
                all_logger.info(s)
            for file in os.listdir(current_path):
                if not filecmp.cmp(os.path.join(current_path, file), os.path.join(firmware_path, file)):
                    raise WindowsDFOTAError("复制文件对比异常")
        all_logger.info('下载固件成功')

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

    def make_dfota_package(self):
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
            raise WindowsDFOTAError("获取前一个版本target file zip失败")

        for path, _, files in os.walk(os.path.join(firmware_path, 'cur')):
            for file in files:
                if file == 'targetfiles.zip':
                    cur_target_file = os.path.join(path, file)
        if not cur_target_file:
            raise WindowsDFOTAError("获取当前版本target file zip失败")

        # 兼容小米定制版本
        if self.Is_XiaoMi_version:
            multi_thread_merge_fota_full_images(orig_target_file, cur_target_file)
        else:
            multi_thread_merge_version(orig_target_file, cur_target_file)

    @staticmethod
    def check_bootable_images():
        """
        检查制作完成的差分包中，不好含BOOTABLE_IMAGES文件夹。
        首先解压到当前脚本运行路径 + firmware + cache文件夹，然后用os.walk()方法查找是否含有BOOTABLE IMAGES文件夹
        :return:
        """
        all_logger.info("开始检查差分包是否包含BOOTABLE_IMAGES文件夹")
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        dfota_packages = ['a-b.zip', 'b-a.zip']

        for file in os.listdir(firmware_path):
            if file in dfota_packages:
                with ZipFile(os.path.join(firmware_path, file), 'r') as to_unzip:
                    all_logger.info('exact {} to {}'.format(os.path.join(firmware_path, file), os.path.join(firmware_path, 'cache', file)))
                    to_unzip.extractall(os.path.join(firmware_path, 'cache', file))

        check_msg = 'BOOTABLE_IMAGES'
        for path, dirs, files in os.walk(os.path.join(os.getcwd(), 'firmware', 'cache')):
            if check_msg in dirs or check_msg in files:
                raise WindowsDFOTAError("发现{}".format(check_msg))
        all_logger.info("检查完成")

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
            if check_message in outs:
                all_logger.error(f"cmd: {cmd} timeout，but returned success!")
                return True
            else:
                raise Exception(error_message)

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

    def qfil(self, dl_port: str, erase=True, factory=True, external_path=''):
        """
        进行QFile升级
        :param dl_port: 紧急下载口
        :param erase: 是否进行全擦
        :param factory: 进行工厂版本还是标准版本
        :param external_path: 一般DFOTA中：升级A版本，则填写cur，如果升级B版本，填写prev
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

        all_logger.info("get {} firehose path".format('factory' if factory else 'standard'))
        factory_package_path = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware', external_path)):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', external_path, p)):
                if factory:
                    if p.lower().endswith('factory'):
                        factory_package_path = os.path.join(os.getcwd(), 'firmware', external_path, p)
                else:
                    if not p.lower().endswith('factory'):
                        factory_package_path = os.path.join(os.getcwd(), 'firmware', external_path, p)
        if not factory_package_path:
            raise Exception("未找到{}升级包".format('工厂' if factory else '标准'))

        firehose_path = os.path.join(factory_package_path, 'update', 'firehose')

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

        if erase:
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
        rawprogram_file = 'rawprogram_nand_p4K_b256K_factory.xml' if factory else 'rawprogram_nand_p4K_b256K_update.xml'
        all_in_one = fr'fh_loader.exe --port=\\.\{dl_port} --sendxml={rawprogram_file},patch_p4K_b256K.xml --search_path={firehose_path} {fh_cmd} --reset'
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
                s.write(bytes.fromhex('4b650100540f7e'))
            start = time.time()
            while not dl_port and time.time() - start < 30:
                time.sleep(1)
                all_logger.info('{}S'.format(int(time.time() - start)))
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

    def qfil_upgrade_and_check(self, erase=True, factory=True, external_path=''):
        """
        进行QFIL升级并检查
        :param erase: 是否进行全擦升级，QFLASH默认非全擦升级
        :param factory: 因为复制版本包的时候会复制所有的版本包，所以需要进行factory和非factory选择判断
        :param external_path: 额外的路径，如果同时有A B两个版本，如果A版本，路径为/firmware/cur/xxx，如果B版本，则路径为/firmware/prev/xxx
        :return: True
        """
        # 获取模块的SER, 和对应所有SER的端口，用于后续升级后端口检查
        ports = {'at_port': self.at_port, 'dm_port': self.dm_port}
        port_list = self.get_ser_ports_mapping(ports)

        # 切换紧急下载
        dl_port = self.switch_edl_mode()

        # 升级
        self.qfil(dl_port, erase, factory=factory, external_path=external_path)

        # 获取升级后的端口
        all_logger.info("对比升级前后端口")
        start = time.time()
        while time.time() - start < 180:
            port_list_after_download = self.driver.get_port_list()
            all_logger.info('port_list_after_download{}'.format(port_list_after_download))
            if len(list(set(port_list) & set(port_list_after_download))) == len(port_list):
                return True
            time.sleep(1)
        else:
            port_list_after_download = self.driver.get_port_list()
            raise Exception("升级前后端口列表不同，升级前{}，升级后{}".format(port_list, port_list_after_download))

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
            raise WindowsDFOTAError('ATI查询的版本号和当前设置版本号不一致')

        # 写号
        return_value = self.at_handler.send_at('AT+EGMR=1,7,"864505040004635"', 0.3)
        if 'OK' not in return_value:
            raise WindowsDFOTAError("写号异常")

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise WindowsDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.prev_svn) not in return_value:
            raise WindowsDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=4执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令后查询异常")

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
            raise WindowsDFOTAError("请使用xftp软件，使用sftp协议，端口22，连接192.168.25.74，用户名：quectel，密码centos@123，检查内网是否可以正常连接")

    def upload_package_to_ftp(self):
        a_b_path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip')
        b_a_path = os.path.join(os.getcwd(), 'firmware', 'b-a.zip')

        for i in range(10):
            try:
                with FTP() as ftp:
                    all_logger.info('login ftp server')
                    # ftp.login(user='test', passwd='test')
                    ftp.connect('112.31.84.164', 8309)
                    ftp.login(user='test', passwd='test')
                    try:
                        all_logger.info('ftp mkdir')
                        ftp.mkd('./5G/{}'.format(self.package_dir))
                    except Exception as e:
                        all_logger.error(e)
                    all_logger.info('ftp chdir')
                    ftp.cwd('./5G/{}'.format(self.package_dir))
                    all_logger.info('upload a-b.zip')
                    with open(a_b_path, 'rb') as fp:
                        ftp.storbinary('STOR {}'.format(os.path.basename(a_b_path)), fp)
                    all_logger.info('upload b-a.zip')
                    with open(b_a_path, 'rb') as fp:
                        ftp.storbinary('STOR {}'.format(os.path.basename(b_a_path)), fp)

                    all_logger.info("ftp服务器文件夹路径为(filezilla等工具登录112.31.84.164:8309可查看fota包是否正常): \r\n/5G/{}".format(self.package_dir))

                    # mkdir cache_ftp directory
                    if not os.path.exists(os.path.join(os.getcwd(), 'firmware', 'cache_ftp')):
                        os.mkdir(os.path.join(os.getcwd(), 'firmware', 'cache_ftp'))

                    # RETR and check
                    all_logger.info('check package')
                    package_check_flag = False
                    for file in ['a-b.zip', 'b-a.zip']:
                        cache_path = os.path.join(os.getcwd(), 'firmware', 'cache_ftp', file)
                        with open(cache_path, 'wb') as fp:
                            ftp.retrbinary('RETR {}'.format(file), fp.write)
                        if not filecmp.cmp(cache_path, os.path.join(os.getcwd(), 'firmware', file), shallow=False):
                            all_logger.error("文件对比不同")
                            package_check_flag = True
                    if package_check_flag:
                        continue

                break  # 正常跳出
            except Exception as e:
                all_logger.error(e)
        else:
            raise WindowsDFOTAError("FTP上传差分包失败")

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

    watchdog = partial(watchdog, logging_handle=at_logger, exception_type=WindowsDFOTAError)

    @watchdog("开始进行DFOTA升级")
    def dfota_ftp_http_https_step_1(self, dfota_type, fota_cmd, stop_download=False):
        """
        仅处理at+qfotadl指令中关机前的部分：
        1. FTP，检测+QIND: "FOTA","FTPSTART" 到 +QIND: "FOTA","FTPEND",0
        2. HTTP，检测+QIND: "FOTA","HTTPSTART" 到 +QIND: "FOTA","HTTPEND",0
        2. HTTPS，检测+QIND: "FOTA","HTTPSTART" 到 +QIND: "FOTA","HTTPEND",0
        :return: None
        """
        check_fragment = 'FTP' if dfota_type.upper() == 'FTP' else "HTTP"
        at_logger.info('check_fragment: {}'.format(check_fragment))
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            at_port.write(f'AT+QFOTADL="{fota_cmd}"\r\n'.encode('utf-8'))
            at_logger.info('Send: {}'.format(f'AT+QFOTADL="{fota_cmd}"\r\n'))
            # 检查 FTPSTART / HTTPSTART
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.at_handler.readline(at_port)
                check_msg = '+QIND: "FOTA","{}START"'.format(check_fragment)
                if check_msg in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    self.check_modem_port_connectivity()
                    break
                if time.time() - start_time > 60:
                    raise WindowsDFOTAError("发送升级指令后60秒内未检测到{}".format(check_msg))
                if 'ERROR' in recv:
                    raise WindowsDFOTAError("发送DFOTA升级指令返回ERROR")

            # 如果需要断电或者断网
            if stop_download:
                sleep_time = random.uniform(1, 2)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            # 检查 "FOTA","FTPEND",0 "FOTA","HTTPEND",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.at_handler.readline(at_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","{}END",(\d+)'.format(check_fragment), recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}".format(recv))
                        return True
                    else:
                        at_logger.error("DFOTA下载差分包异常：{}".format(recv))
                        return False
                if time.time() - start_time > 300:
                    raise WindowsDFOTAError("DFOTA下载差分包超过300S异常")

    @watchdog("检测DFOTA差分包加载")
    def dfota_step_2(self, stop_download=False, start=False):
        """
        发送at+qfotadl指令关机并开机后的log检查：
        检测+QIND: "FOTA","START" 到 +QIND: "FOTA","END",0
        :return: None
        """

        start_urc_flag = False
        start_time = time.time()
        try:
            # 检查 FTPSTART / HTTPSTART，如果检测到UPDATING，则没有检测到，为了保证可以断电等操作，直接跳出
            while time.time() - start_time < 300:
                time.sleep(0.001)
                recv = self.at_handler.readline(self.uart_port)
                check_msg = '+QIND: "FOTA","START"'
                if check_msg in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    self.check_modem_port_connectivity()
                    start_urc_flag = True
                    if start:
                        at_logger.info(f"在{check_msg}处断电")
                        return True
                    break
                if '+QIND: "FOTA","UPDATING"' in recv:
                    at_logger.error("未检测到{}".format(check_msg))
                    break
            else:
                at_logger.error('DFOTA 检测{} +QIND: "FOTA","START"失败')
                raise WindowsDFOTAError('DFOTA升级过程异常：检测{} +QIND: "FOTA","START"失败')
            # 如果需要断电或者断网
            if stop_download:
                sleep_time = random.uniform(5, 10)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            # 检查 "FOTA","END",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.at_handler.readline(self.uart_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","END",(\d+)', recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                        return True
                    else:
                        at_logger.error("DFOTA升级异常异常：{}".format(recv))
                        return False
                if time.time() - start_time > 300:
                    raise WindowsDFOTAError("DFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise WindowsDFOTAError('未检测到DFOTA上报+QIND: "FOTA","START"')

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
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.send_at('AT+CFUN=0', 15)
            time.sleep(5)
            self.at_handler.send_at("AT+CFUN=1", 15)
            self.at_handler.dfota_dl_package_701_702()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(10)
        if dl_vbat:
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
            time.sleep(10)
        self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
        self.driver.check_usb_driver_dis()

        # step2
        if self.revision.startswith("RG"):  # RG项目
            if upgrade_stop:  # 随机断电
                self.uart_handler.dfota_step_2(stop_download=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if start:  # 在上报+QIND: "FOTA","START"时候断电
                self.uart_handler.dfota_step_2(start=True)
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end:  # 在上报+QIND: "FOTA","END", 0处断电
                self.uart_handler.dfota_step_2()
                all_logger.info("在FOTA END 0处断电")
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
            if end is False:  # 正常升级
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
            self.qfil_upgrade_and_check(erase=True, factory=True, external_path='prev')  # 全擦，工厂包，升级到前一个版本
            # time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
            # self.qfil_upgrade_and_check(erase=False, factory=False, external_path='prev')  # 不擦，标准包，升级前一个版本的标准包
            time.sleep(20)  # 等到正常
            self.after_upgrade_check()

    def reset_b_version(self):
        """
        恢复到A版本。
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
            self.qfil_upgrade_and_check(erase=True, factory=True, external_path='cur')  # 全擦，工厂包，升级到前一个版本
            time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
            # self.qfil_upgrade_and_check(erase=False, factory=False, external_path='cur')  # 不擦，标准包，升级前一个版本的标准包
            # time.sleep(20)  # 等到正常
            self.after_upgrade_check(a_b=True)

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
            raise WindowsDFOTAError('ATI查询的B版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise WindowsDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise WindowsDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令后查询异常")

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
            raise WindowsDFOTAError('ATI查询的A版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise WindowsDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.prev_svn) not in return_value:
            raise WindowsDFOTAError("SVN查询异常")

        # 找网
        self.at_handler.check_network()

        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsDFOTAError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise WindowsDFOTAError("执行备份指令后查询异常")

    def init_with_version_a(self):
        """
        VBAT开机，检查当前是A版本。
        :return: None
        """
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.reset_a_version()
        self.at_handler.check_network()
        self.set_usbnet_1()
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
        self.at_handler.check_urc()
        self.reset_b_version()
        self.at_handler.check_network()
        self.set_usbnet_1()
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
        self.at_handler.check_urc()
        self.at_handler.check_network()
        self.set_usbnet_1()
        time.sleep(10)

    def set_usbnet_1(self):
        self.windows_api.remove_ndis_driver()
        return_value = self.at_handler.send_at('AT+QCFG="USBNET",1', timeout=3)
        if 'OK' not in return_value:
            raise WindowsDFOTAError("设置网卡USBNET默认为1失败")

    def get_mbn_list(self):
        # 查询MBN
        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                return return_value
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsDFOTAError("MBN列表查询异常")

    def compare_mbn_list(self, mbn):
        all_logger.info("开始对比MBN列表")
        check_dict = dict()
        check_mbn = re.findall(r'\+QMBNCFG:\s"\S+",\d+,\d+,\d+,"(\S+?)",(\S+)', mbn)
        for mbn in check_mbn:
            mbn, seq = mbn
            check_dict[mbn] = seq

        for i in range(10):
            return_value = self.at_handler.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsDFOTAError("MBN列表查询异常")

        cur_dict = dict()
        cur_mbn = re.findall(r'\+QMBNCFG:\s"\S+",\d+,\d+,\d+,"(\S+?)",(\S+)', return_value)
        for mbn in cur_mbn:
            mbn, seq = mbn
            cur_dict[mbn] = seq

        if len(cur_dict.items() - check_dict.items()) != 0 or len(check_dict.items() - cur_dict.items()) != 0:
            raise WindowsDFOTAError("升级前后MBN列表检查不一致，请确认是否版本有修改点")
        all_logger.info("MBN列表对比成功")

    def unlock_adb(self):
        PID = ''
        for num, _, info in serial.tools.list_ports.comports():
            if num == self.at_port.upper():
                PID = ''.join(re.findall(r'PID=(\S+:\S+)', info))
                if PID:
                    PID = PID.split(":")
        if not PID:
            raise WindowsDFOTAError("获取PID失败")

        qadbkey = self.at_handler.send_at('AT+QADBKEY?')
        qadbkey = ''.join(re.findall(r'\+QADBKEY:\s(\S+)', qadbkey))
        if not qadbkey:
            raise WindowsDFOTAError("获取QADBKEY失败")

        self.at_handler.send_at('AT+QADBKEY="{}"'.format(getpass(qadbkey, 'adb')), 3)

        self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(PID[0], PID[1]), 3)

        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        time.sleep(10)

    @staticmethod
    def check_adb_devices_connect():
        """
        检查adb devices是否有设备连接
        :return: True:adb devices已经发现设备
        """
        adb_check_start_time = time.time()
        while True:
            # 发送adb devices
            subprocess.run('adb kill-server')
            adb_value = repr(os.popen('adb devices').read())
            all_logger.info(adb_value)
            devices_online = ''.join(re.findall(r'\\n(.*)\\tdevice', adb_value))
            devices_offline = ''.join(re.findall(r'\\n(.*)\\toffline', adb_value))
            if devices_online != '' or devices_offline != '':  # 如果检测到设备
                all_logger.info('已检测到adb设备')  # 写入log
                return True
            elif time.time() - adb_check_start_time > 100:  # 如果超时
                raise WindowsDFOTAError("adb超时未加载")
            else:  # 既没有检测到设备，也没有超时，等1S
                time.sleep(1)

    @staticmethod
    def push_package_and_check(a_b=True):
        path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip' if a_b else "b-a.zip")
        package_md5 = hashlib.md5()
        with open(path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))

        for i in range(10):
            subprocess.run('adb kill-server')
            adb_push = subprocess.getstatusoutput('adb push "{}" /cache/ufs'.format(path))
            all_logger.info(adb_push)
            if adb_push[0] != 0:
                continue
            md5 = subprocess.getoutput('adb shell md5sum /cache/ufs/{}'.format('a-b.zip' if a_b else "b-a.zip"))
            all_logger.info(md5)
            at_logger.info('adb get md5:{}'.format(md5))
            if package_md5 in md5:
                all_logger.info("MD5对比正常")
                time.sleep(5)
                return True
            time.sleep(1)
        else:
            raise WindowsDFOTAError("ADB PUSH升级包失败")
        
    @staticmethod
    def check_usb():
        """
        检查当前是紧急下载模式还是USB模式
        :return:True：USB模式；False：紧急下载模式
        """
        for i in range(10):
            usb_val = os.popen('lsusb').read()
            if '2c7c' in usb_val:
                all_logger.info('当前为USB模式')
                time.sleep(10)
                return True
            elif '9008' in usb_val:
                all_logger.info('当前为紧急下载模式')
                return False
            time.sleep(2)

    def qfirehose_upgrade(self, package, factory):
        """
        Qfirehose普通升级及断电方法
        :param package: 升级包路径,cur or prev
        :param factory: 是否工厂升级
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
        is_factory = True if 'factory' in package_name else False    # 是否是工厂包升级，是的话指令需要加-e
        val = os.popen('ps -ef | grep QFirehose').read()
        if 'QFirehose -f {}'.format(package_name) in val:
            try:
                kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                    all_logger.info('已关闭升级进程')
            except subprocess.TimeoutExpired:
                all_logger.info('关闭升级进程失败')
        start_time = time.time()
        upgrade = subprocess.Popen('QFirehose -f {} {}'.format(package_name, '-e' if is_factory else ''), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        all_logger.info('QFirehose -f {} {}'.format(package_name, '-e' if factory else ''))
        os.set_blocking(upgrade.stdout.fileno(), False)
        while True:
            time.sleep(0.001)
            upgrade_content = upgrade.stdout.readline().decode('utf-8')
            if upgrade_content != '':
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
                    self.gpio.set_vbat_high_level()
                    time.sleep(3)
                    self.gpio.set_vbat_low_level_and_pwk()
                    if self.check_usb():    # 如果重启后USB口可以正常加载，重新升级一次
                        all_logger.error('升级失败')
                        raise LinuxATUpgradeError('升级失败')
                    else:
                        all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                        raise LinuxATUpgradeError('升级失败，且重启后模块已处于紧急下载模式')
            if time.time() - start_time > 120:
                all_logger.error('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                self.gpio.set_vbat_high_level()
                time.sleep(3)
                self.gpio.set_vbat_low_level_and_pwk()
                if self.driver.get_port_list():    # 如果重启后USB口可以正常加载，重新升级一次
                    all_logger.error('升级失败')
                    raise LinuxATUpgradeError('升级失败')
                else:
                    all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                    raise LinuxATUpgradeError('升级失败，且重启后模块已处于紧急下载模式')

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
            raise WindowsDFOTAError("检测DFOTA升级时打开AT口异常")

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


if __name__ == '__main__':
    a = ATBackgroundThreadWithDriverCheck(at_port="COM14", dm_port="COM13")
    time.sleep(40)
    print(a.get_info())
    time.sleep(19)
