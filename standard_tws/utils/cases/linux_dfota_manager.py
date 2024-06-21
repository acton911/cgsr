import serial
import random
import glob
import shutil
import time
import subprocess
import serial.tools.list_ports
import requests
import paramiko
import re
import filecmp
import os
import hashlib
import threading
# import zipfile
# import urllib3
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI
from utils.exception.exceptions import LinuxDFOTAError, FatalError
from utils.functions.jenkins import multi_thread_merge_version, multi_thread_merge_fota_full_images
from utils.operate.uart_handle import UARTHandle
from utils.logger.logging_handles import all_logger, at_logger
from subprocess import PIPE
from zipfile import ZipFile
from collections import deque
from ftplib import FTP
from threading import Thread
from utils.functions.getpassword import getpass
from utils.functions.gpio import GPIO
from urllib import request


class LinuxDFOTAManager:

    def __init__(self, uart_port, revision, sub_edition, prev_upgrade_revision, svn, ChipPlatform, imei_number, usb_id,
                 prev_upgrade_sub_edition, prev_svn, at_port, dm_port, prev_firmware_path, firmware_path,
                 extra_ethernet_name, debug_port, name_sub_version):
        self.at_port = at_port
        self.dm_port = dm_port
        self.firmware_path = firmware_path
        self.revision = revision
        self.sub_edition = sub_edition
        self.prev_upgrade_revision = prev_upgrade_revision
        self.prev_upgrade_sub_edition = prev_upgrade_sub_edition
        self.prev_firmware_path = prev_firmware_path
        self.prev_svn = prev_svn
        self.check_prev_data()
        self.svn = svn
        self.ChipPlatform = ChipPlatform
        self.imei_number = imei_number
        self.usb_id = usb_id
        self.uart_handler = UARTHandle(uart_port)
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.linux_api = LinuxAPI()
        self.extra_ethernet_name = extra_ethernet_name
        self.debug_port = debug_port
        self.name_sub_version = name_sub_version
        md5 = hashlib.md5()
        md5.update(
            f'{self.revision}{self.sub_edition}{self.prev_upgrade_revision}{self.prev_upgrade_sub_edition}'.encode(
                'utf-8'))
        self.package_dir = md5.hexdigest()[:10]  # 创建一个文件夹，用于在ftp和http(s)服务器上创建，避免重复
        self.driver_check = DriverChecker(self.at_port, self.dm_port)
        self.gpio = GPIO()
        self.Is_XiaoMi_version = True if '_XM' in self.revision else False
        self.prev_name_sub_version = self.prev_firmware_path.split('\\')[-1]
        self.cur_standard_path = ''
        self.prev_standard_path = ''
        self.cur_factory_path = ''
        self.prev_factory_path = ''

    def check_prev_data(self):
        if not self.prev_upgrade_revision or not self.prev_upgrade_sub_edition or not self.prev_firmware_path or not self.prev_svn:
            raise LinuxDFOTAError("未检查到数据库填写的prev_upgrade_revision/prev_upgrade_sub_edition/prev_firmware_path"
                                  "/prev_svn相关参数或者CI传参异常，请检查数据库中name_sub_version是否存在，是否有空格，是否有重复名称")

    def ubuntu_copy_file(self):
        """
        Ubuntu下复制版本包到firmware目录下
        :return:
        """
        if 'firmware' not in os.listdir(os.getcwd()):
            os.mkdir(os.getcwd() + '/firmware')
        if 'cur' not in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/cur')
        if 'prev' not in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/prev')
        search_result_cur = self.search_package('cur')  # 先从本地寻找版本包
        search_result_cur_factory = self.search_package('cur_factory')
        if search_result_cur and search_result_cur_factory:
            all_logger.info(
                f"cp {self.cur_standard_path} to {os.path.join(os.getcwd(), 'firmware', 'cur', self.name_sub_version)}")
            shutil.copytree(self.cur_standard_path, os.path.join(os.getcwd(), 'firmware', 'cur', self.name_sub_version))
            all_logger.info(
                f"cp {self.cur_factory_path} to {os.path.join(os.getcwd(), 'firmware', 'cur', self.name_sub_version + '_factory')}")  # noqa
            shutil.copytree(self.cur_factory_path,
                            os.path.join(os.getcwd(), 'firmware', 'cur', self.name_sub_version + '_factory'))

            if self.name_sub_version in os.listdir(
                    os.path.join(os.getcwd(), 'firmware', 'cur')) and self.name_sub_version + '_factory' in os.listdir(
                os.path.join(os.getcwd(), 'firmware', 'cur')):  # noqa
                all_logger.info('当前版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'cur')))
                raise FatalError('当前版本包获取失败')
        else:
            cur_file_list = os.listdir('/mnt/cur')
            all_logger.info('/mnt/cur目录下现有如下文件:{}'.format(cur_file_list))
            all_logger.info('开始复制当前版本版本包到本地')
            for i in cur_file_list:
                if self.name_sub_version + '.zip' in i:
                    all_logger.info(i)
                    shutil.copy(os.path.join('/mnt/cur', i), os.path.join(os.getcwd(), 'firmware', 'cur'))
                if self.name_sub_version + '_factory.zip' in i:
                    all_logger.info(i)
                    shutil.copy(os.path.join('/mnt/cur', i), os.path.join(os.getcwd(), 'firmware', 'cur'))
            if self.name_sub_version + '.zip' in os.listdir(os.path.join(os.getcwd(
            ), 'firmware', 'cur')) and self.name_sub_version + '_factory.zip' in os.listdir(
                os.path.join(os.getcwd(), 'firmware', 'cur')):
                all_logger.info('当前版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'cur')))
                raise FatalError('当前版本包获取失败')

        search_result_prev = self.search_package('prev')  # 先从本地寻找版本包
        search_result_prev_factory = self.search_package('prev_factory')  # 先从本地寻找版本包
        if search_result_prev and search_result_prev_factory:
            all_logger.info(
                f"cp {self.prev_standard_path} to {os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version)}")  # noqa
            shutil.copytree(self.prev_standard_path,
                            os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version))
            all_logger.info(
                f"cp {self.prev_factory_path} to {os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version + '_factory')}")  # noqa
            shutil.copytree(self.prev_factory_path,
                            os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version + '_factory'))

            if self.prev_name_sub_version in os.listdir(os.path.join(os.getcwd(

            ), 'firmware', 'prev')) and self.prev_name_sub_version + '_factory' in os.listdir(
                os.path.join(os.getcwd(), 'firmware', 'prev')):# noqa
                all_logger.info('上一版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'prev')))
                raise FatalError('上一版本包获取失败')
        else:
            prev_file_list = os.listdir('/mnt/prev')
            all_logger.info('/mnt/prev目录下现有如下文件:{}'.format(prev_file_list))
            all_logger.info('开始复制上一版本版本包到本地')
            for i in prev_file_list:
                if self.prev_name_sub_version + '.zip' in i:
                    all_logger.info(i)
                    shutil.copy(os.path.join('/mnt/prev', i), os.path.join(os.getcwd(), 'firmware', 'prev'))
                if self.prev_name_sub_version + '_factory.zip' in i:
                    all_logger.info(i)
                    shutil.copy(os.path.join('/mnt/prev', i), os.path.join(os.getcwd(), 'firmware', 'prev'))
            if self.prev_name_sub_version + '.zip' in os.listdir(os.path.join(os.getcwd(

            ), 'firmware', 'prev')) and self.prev_name_sub_version + '_factory.zip' in os.listdir(
                os.path.join(os.getcwd(), 'firmware', 'prev')):# noqa
                all_logger.info('上一版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'prev')))
                raise FatalError('上一版本包获取失败')
        self.unzip_firmware()

    def search_package(self, package_name):
        """
        搜索已测试case中是否已存在版本包，如果存在，直接使用，省去复制版本包时间
        :param package_name: 需要搜索的版本包，cur：当前版本的标准包; prev：当前版本及上一版本的标准包；all：标准及工厂
        :return:
        """
        all_logger.info(f'在其他路径中搜索是否已存在有{package_name}版本包')
        cur_package_name = self.name_sub_version  # 当前版本的标准包名
        prev_package_name = self.prev_name_sub_version  # 上一版本的标准包名
        case_path = '/root/TWS_TEST_DATA'
        for i in os.listdir(case_path):
            for path, dirs, files in os.walk(os.path.join(case_path, i)):
                if cur_package_name in dirs:
                    self.cur_standard_path = os.path.join(path, cur_package_name)
                    all_logger.info(self.cur_standard_path)
                if prev_package_name in dirs:
                    self.prev_standard_path = os.path.join(path, prev_package_name)  # noqa
                    all_logger.info(self.prev_standard_path)
                if cur_package_name + '_factory' in dirs:
                    self.cur_factory_path = os.path.join(path, cur_package_name + '_factory')  # noqa
                    all_logger.info(self.cur_factory_path)
                if prev_package_name + '_factory' in dirs:
                    self.prev_factory_path = os.path.join(path, prev_package_name + '_factory')  # noqa
                    all_logger.info(self.prev_factory_path)

                if package_name == 'cur' and self.cur_standard_path:  # 如果已经找到当前版本的标准包，直接返回
                    all_logger.info(f'当前版本的标准包路径为{self.cur_standard_path}')
                    return True
                elif package_name == 'prev' and self.prev_standard_path:
                    all_logger.info(f'上一版本的标准包路径为{self.prev_standard_path}')
                    return True
                elif package_name == 'cur_factory' and self.cur_factory_path:  # 如果已经找到当前版本的标准包，直接返回
                    all_logger.info(f'当前版本的工厂包路径为{self.cur_factory_path}')
                    return True
                elif package_name == 'prev_factory' and self.prev_factory_path:
                    all_logger.info(f'上一版本的工厂包路径为{self.prev_factory_path}')
                    return True
        else:
            all_logger.info('在其他路径下未找到版本包，从共享获取')

    def unzip_firmware(self):
        """
        解压/root/TWS_TEST_DATA/PackPath路径下的版本包
        :return: None
        """

        firmware_path = os.path.join(os.getcwd(), 'firmware')
        try:
            for path, _, files in os.walk(firmware_path):
                for file in files:
                    if file.endswith('.zip') and self.name_sub_version in file:
                        with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                            all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                            to_unzip.extractall(path)
                            if not os.path.exists(os.path.join('/root/TWS_TEST_DATA/PackPath', file.split('.zip')[0])):
                                shutil.copytree(os.path.join(path, file.split('.zip')[0]),
                                                os.path.join('/root/TWS_TEST_DATA/PackPath',
                                                             file.split('.zip')[0]))  # 共享给/root/TWS_TEST_DATA/PackPath
                    if file.endswith('.zip') and self.prev_name_sub_version in file:
                        with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                            all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                            to_unzip.extractall(path)
                            if not os.path.exists(os.path.join('/root/TWS_TEST_DATA/PackPath', file.split('.zip')[0])):
                                shutil.copytree(os.path.join(path, file.split('.zip')[0]),
                                                os.path.join('/root/TWS_TEST_DATA/PackPath',
                                                             file.split('.zip')[0]))  # 共享给/root/TWS_TEST_DATA/PackPath
        except Exception as e:
            all_logger.info(e)
            raise FatalError('解压版本包失败')
        all_logger.info('解压固件成功')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/cur')
        os.popen('umount /mnt/prev')

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
        for i in range(3):
            os.popen('mount -t cifs {} /mnt/cur -o user="jeckson.yin@quectel.com",password="Admin@1234567"'.format(
                cur_package_path)).read()
            os.popen('mount -t cifs {} /mnt/prev -o user="jeckson.yin@quectel.com",password="Admin@1234567"'.format(
                prev_package_path)).read()
            if os.listdir('/mnt/cur') and os.listdir('/mnt/prev'):
                all_logger.info('版本包挂载成功')
                break
            time.sleep(5)
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise FatalError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    def make_dfota_package(self):
        """
        查找当前路径 + firmware + prev/cur路径下面的所有targetfiles.zip，复制到fota+prev/cur路径下并重命名为标准包名，然后制作差分包。
        :return: None
        """
        all_logger.info("开始制作差分包")
        orig_target_file = ''
        cur_target_file = ''
        name_sub_version_zip = self.name_sub_version + '.zip'
        prev_name_sub_version_zip = self.prev_name_sub_version + '.zip'
        firmware_path = os.path.join(os.getcwd(), 'firmware')
        firmware_path_fota = os.path.join(os.getcwd(), 'firmware', 'fota')
        # 确认是否存在firmware/fota文件夹，若没有，则创建
        if not os.path.exists(firmware_path_fota):
            os.mkdir(firmware_path_fota)
        # 确认是否存在firmware/fota/prev、cur文件夹，若没有，则创建
        for file in ['/prev', '/cur']:
            if not os.path.exists(os.path.join(firmware_path_fota + file)):
                os.mkdir(os.path.join(firmware_path_fota + file))
        # 在firmware/prev文件夹下查找上个版本Atargetfiles.zip文件，若存在则复制到firmware/fota/prev路径下，并以其标准包命名
        for path, _, files in os.walk(os.path.join(firmware_path, 'prev')):
            for file in files:
                if file == 'targetfiles.zip':
                    orig_target_file = os.path.join(path, file)
                    shutil.copy(os.path.join(orig_target_file),
                                os.path.join(firmware_path_fota, 'prev', prev_name_sub_version_zip))
                    orig_target_file = os.path.join(firmware_path_fota, 'prev', prev_name_sub_version_zip)
        if not orig_target_file:
            raise FatalError("获取前一个版本target file zip失败")
        # 在firmware/cur文件夹下查找当前版本targetfiles.zip文件，若存在则复制到firmware/fota/prev路径下，并以其标准包命名
        for path, _, files in os.walk(os.path.join(firmware_path, 'cur')):
            for file in files:
                if file == 'targetfiles.zip':
                    cur_target_file = os.path.join(path, file)
                    shutil.copy(os.path.join(cur_target_file),
                                os.path.join(firmware_path_fota, 'cur', name_sub_version_zip))
                    cur_target_file = os.path.join(firmware_path_fota, 'cur', name_sub_version_zip)  # noqa
        if not cur_target_file:
            raise FatalError("获取当前版本target file zip失败")

        # 兼容小米定制版本
        if self.Is_XiaoMi_version:
            multi_thread_merge_fota_full_images(orig_target_file, cur_target_file)
        else:
            multi_thread_merge_version(orig_target_file, cur_target_file)
        # 差分包制作完成后，删除firmware/fota文件夹
        shutil.rmtree(firmware_path_fota, ignore_errors=True)

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
                    all_logger.info('exact {} to {}'.format(os.path.join(firmware_path, file),
                                                            os.path.join(firmware_path, 'cache', file)))
                    to_unzip.extractall(os.path.join(firmware_path, 'cache', file))

        check_msg = 'BOOTABLE_IMAGES'
        for path, dirs, files in os.walk(os.path.join(os.getcwd(), 'firmware', 'cache')):
            if check_msg in dirs or check_msg in files:
                raise LinuxDFOTAError("发现{}".format(check_msg))
        all_logger.info("检查完成")

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
        package_name = package_name.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ').replace('(',
                                                                                                         '\(').replace(
            ')', '\)')  # noqa
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
        os.set_blocking(upgrade.stdout.fileno(), False)  # pylint: disable=E1101
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
                    raise LinuxDFOTAError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise LinuxDFOTAError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise LinuxDFOTAError('120S内升级失败')

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

    def check_imei(self):
        """
        升级前进行AT+EGMR=0,7查询
        """
        all_logger.info("升级前进行IMEI号查询确认")
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        # 升级查询IMEI若为默认，则写入系统填写的IMEI号
        if '869710030002905' in return_value:
            return_value1 = self.at_handler.send_at(f'AT+EGMR=1,7,"{self.imei_number}"', 0.3)
            if 'OK' not in return_value1:
                raise LinuxDFOTAError("写号异常")
            # 查号
            return_value2 = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
            if str(self.imei_number) not in return_value2:
                raise LinuxDFOTAError("写号后查号异常")
        else:
            return_value2 = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
            if str(self.imei_number) not in return_value2:
                raise LinuxDFOTAError("查号异常，与TWS填写不一致，请检查")

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
            return_value = self.at_handler.send_at('ATI;+CSUB', 0.6)
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
            raise LinuxDFOTAError('ATI查询的版本号和当前设置版本号不一致')

        # 写号
        return_value = self.at_handler.send_at(f'AT+EGMR=1,7,"{self.imei_number}"', 0.3)
        if 'OK' not in return_value:
            raise LinuxDFOTAError("写号异常")

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if str(self.imei_number) not in return_value:
            raise LinuxDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if a_b is False:
            if str(self.prev_svn) not in return_value:
                raise LinuxDFOTAError("SVN查询异常")
        else:
            if str(self.svn) not in return_value:
                raise LinuxDFOTAError("SVN查询异常")

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
            raise LinuxDFOTAError("升级后MBN列表查询异常")

        time.sleep(3)
        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=4执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令后查询异常")

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
            raise LinuxDFOTAError("请使用xftp软件，使用sftp协议，端口22，连接192.168.25.74，用户名：quectel，密码centos@123，检查内网是否可以正常连接")

    def check_sftp_url(self):
        """
        检查sftp-url地址是否有效，如无则上传差分包到服务器
        :return: None
        """
        try:
            for file in ['a-b.zip', 'b-a.zip']:
                url = 'http://112.31.84.164:8300/5G/{}/{}'.format(self.package_dir, file)
                # 判断下载地址是否有效
                request.urlopen(url)
                all_logger.info('路径为:{}'.format(url))
            all_logger.info('stfp服务器中存在该版本差分包，无需重复上传')
        except Exception as e:
            all_logger.info(e, 'stfp服务器中不存在该版本差分包，上传差分包')
            self.upload_package_to_sftp()

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

                    all_logger.info("ftp服务器文件夹路径为(filezilla等工具登录112.31.84.164:8309可查看fota包是否正常): \r\n/5G/{}".format(
                        self.package_dir))

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
            raise LinuxDFOTAError("FTP上传差分包失败")

    def dfota_upgrade_online(self, dfota_type, a_b=True, dl_stop=False, upgrade_stop=False, start=False, end=False,
                             dl_vbat=False, dl_cfun=False, dl_cgatt=False, dl_QFOTAPID=False, case_id=False,
                             multifota=False):
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
        if dl_cgatt:  # 如果需要下载包过程断网
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.send_at('AT+CGATT=0', 15)
            time.sleep(5)
            self.at_handler.dfota_dl_package_701_702()
            self.at_handler.send_at("AT+CGATT=1", 15)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            time.sleep(10)
        if dl_cfun:  # 如果需要下载包过程断网
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.send_at('AT+CFUN=0', 15)
            time.sleep(5)
            self.at_handler.dfota_dl_package_701_702()  # 此处将断网上报URC检测调整至CFUN=1之前
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
        if dl_QFOTAPID:  # 如果设置为第5路sos
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.dfota_dl_package_701_702()
            time.sleep(3)
            self.at_handler.send_at('AT+QCFG="USBNET",2', 15)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            self.at_handler.send_at("AT+QFOTAPID=7", 0.6)
            time.sleep(3)
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 7' in return_value:
                all_logger.info('指定APN 7 成功')
            else:
                all_logger.info('指定APN 7异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('指定APN 7异常')
            time.sleep(10)
        if case_id:  # 如果为QFOTAPID默认值与网卡拨号同一路apn，进行在线升级，期望升级失败
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.dfota_dl_package_701_702()
            time.sleep(10)
            return True
        if multifota:  # 如果需要debug log
            time.sleep(10)
            self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            all_logger.info('驱动重新加载后打开debug口读取信息')
            data = self.debug_check()
            time.sleep(3)
            self.driver.check_usb_driver()
            time.sleep(3)
            return data
        self.at_handler.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
        self.driver.check_usb_driver_dis()

        # step2
        if self.revision.startswith("RG") and self.ChipPlatform.startswith("SDX55"):  # RG项目
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

    def debug_check(self, timeout=360):
        """
        下载差分包完成，驱动重新加载后，打开debug口进行log检测
        :param timeout: debug口检测时间
        :return:
        """
        with serial.Serial(self.debug_port, baudrate=115200, timeout=0) as _debug_port:
            start_time = time.time()
            value = ''
            while time.time() - start_time < timeout:
                time.sleep(0.001)
                res = _debug_port.readline().decode('utf-8', 'ignore')
                if res:
                    # all_logger.info('查询有没有dubug_log')
                    all_logger.info(res)
                    value += res
                if 'quec_multi_fota_sync_sbl entry' in value or 'clear multi fota mask flag' in value:
                    break
        return value

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
            self.qfirehose_upgrade(package='prev', vbat=False, factory=False, erase=False)  # 不擦，标准包，升级到前一个版本的标准包
            # time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
            # self.qfil_upgrade_and_check(erase=False, factory=False, external_path='prev')  # 不擦，标准包，升级前一个版本的标准包
            # time.sleep(20)  # 等到正常
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            self.after_upgrade_check()

    def prepare_package(self, prev='prev', fota='a-b.zip'):
        if not os.path.exists(os.path.join(os.getcwd(), 'firmware', prev)):
            self.mount_package()
            self.ubuntu_copy_file()
            self.make_dfota_package()
        elif not os.path.exists(os.path.join(os.getcwd(), 'firmware', fota)):
            self.make_dfota_package()
        else:
            all_logger.info('已有版本包，直接使用')

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
            self.qfirehose_upgrade(package='cur', vbat=False, factory=False, erase=False)  # 不擦，标准包，升级到前一个版本的标准包
            # time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
            # self.qfil_upgrade_and_check(erase=False, factory=False, external_path='cur')  # 不擦，标准包，升级前一个版本的标准包
            # time.sleep(20)  # 等到正常
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
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
            raise LinuxDFOTAError('ATI查询的B版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if str(self.imei_number) not in return_value:
            raise LinuxDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise LinuxDFOTAError("SVN查询异常")

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
            raise LinuxDFOTAError("升级后MBN列表查询异常")
        time.sleep(3)
        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令后查询异常")

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
            raise LinuxDFOTAError('ATI查询的A版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if str(self.imei_number) not in return_value:
            raise LinuxDFOTAError("写号后查号异常")

        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.prev_svn) not in return_value:
            raise LinuxDFOTAError("SVN查询异常")

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
            raise LinuxDFOTAError("升级后MBN列表查询异常")
        time.sleep(3)
        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxDFOTAError("执行备份指令后查询异常")

    def init_with_version_a(self):
        """
        VBAT开机，检查当前是A版本。
        :return: None
        """
        # 检查当前路径是否存在版本包和差分包
        self.prepare_package()
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.reset_a_version()
        self.unlock_adb()
        self.at_handler.check_network()

    def init_with_version_b(self):
        """
        VBAT开机，检查当前是B版本。
        :return: None
        """
        # 检查当前路径是否存在版本包和差分包
        self.prepare_package(prev='cur', fota='b-a.zip')
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.reset_b_version()
        self.unlock_adb()
        self.at_handler.check_network()

    def init(self):
        """
        VBAT开机，检查当前是B版本。
        :return: None
        """
        self.prepare_package()
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.unlock_adb()
        self.at_handler.check_network()

    def set_usbnet_1(self):
        return_value = self.at_handler.send_at('AT+QCFG="USBNET",1', timeout=3)
        if 'OK' not in return_value:
            raise LinuxDFOTAError("设置网卡USBNET默认为1失败")

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
            raise LinuxDFOTAError("MBN列表查询异常")

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
            raise LinuxDFOTAError("MBN列表查询异常")

        cur_dict = dict()
        cur_mbn = re.findall(r'\+QMBNCFG:\s"\S+",\d+,\d+,\d+,"(\S+?)",(\S+)', return_value)
        for mbn in cur_mbn:
            mbn, seq = mbn
            cur_dict[mbn] = seq

        if len(cur_dict.items() - check_dict.items()) != 0 or len(check_dict.items() - cur_dict.items()) != 0:
            raise LinuxDFOTAError("升级前后MBN列表检查不一致，请确认是否版本有修改点")
        all_logger.info("MBN列表对比成功")

    def unlock_adb(self):
        lsusb = os.popen('lsusb').read()
        all_logger.info(lsusb)
        usb_num = self.usb_id.split(',')
        pid = format(int(usb_num[0]), 'x').zfill(4)
        all_logger.info('pid为{}'.format(pid))
        vid = format(int(usb_num[1]), 'x').zfill(4)
        vlue = self.at_handler.send_at('AT+QCFG="USBCFG"', 3)
        if ',1,1,1,1,1,1,0' in vlue:
            all_logger.info('adb已开启')
        else:
            qadbkey = self.at_handler.send_at('AT+QADBKEY?')
            qadbkey = ''.join(re.findall(r'\+QADBKEY:\s(\S+)', qadbkey))
            if not qadbkey:
                raise LinuxDFOTAError("获取QADBKEY失败")

            self.at_handler.send_at('AT+QADBKEY="{}"'.format(getpass(qadbkey, 'adb')), 3)

            self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1,0'.format(pid, vid), 3)

            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
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
            subprocess.getoutput('adb kill-server')
            adb_value = repr(subprocess.getoutput('adb devices'))
            all_logger.info(adb_value)
            devices_online = ''.join(re.findall(r'\\n(.*)\\tdevice', adb_value))
            devices_offline = ''.join(re.findall(r'\\n(.*)\\toffline', adb_value))
            if devices_online != '' or devices_offline != '':  # 如果检测到设备
                all_logger.info('已检测到adb设备')  # 写入log
                return True
            elif time.time() - adb_check_start_time > 100:  # 如果超时
                raise LinuxDFOTAError("adb超时未加载")
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
            subprocess.getoutput('adb kill-server')
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
            raise LinuxDFOTAError("ADB PUSH升级包失败")

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

    def check_QFOTAPID(self, case_id):
        if case_id == 'test_linux_dfota_07_001':
            return_value = self.at_handler.send_at('AT+QFOTAPID=?', 0.3)
            if '+QFOTAPID: (1-8)' in return_value:
                all_logger.info('AT+QFOTAPID=?返回参数范围正确')
            else:
                all_logger.info('AT+QFOTAPID=?返回参数范围异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('AT+QFOTAPID=?返回参数范围异常')
            self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            time.sleep(3)

        elif case_id == 'test_linux_dfota_07_002':
            self.at_handler.check_network()
            self.at_handler.send_at('AT+CGDCONT?', 5)
            self.at_handler.send_at('AT+QFOTAPID=5', 0.6)
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.6)
            if '+QFOTAPID: 5' in return_value:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID为 5 成功')
            else:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID为 5 异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('配置DFOTA升级数据拨号的Profile ID为 5 异常')
            time.sleep(3)

        elif case_id == 'test_linux_dfota_07_003':
            self.at_handler.check_network()
            all_logger.info('指令添加APN')
            return_value = self.at_handler.send_at('AT+CGDCONT=7,"IPV4V6","666"', 3)
            if 'OK' in return_value:
                all_logger.info('添加APN 7成功')
            else:
                all_logger.info('添加APN 7异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('添加APN 7异常')
            self.at_handler.send_at('AT+CGDCONT?', 5)
            all_logger.info('AT+QFOTAPID配置DFOTA升级数据拨号的Profile ID为 7')
            self.at_handler.send_at('AT+QFOTAPID=7', 3)
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 7' in return_value:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID为 7 成功')
            else:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID为 7 异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('配置DFOTA升级数据拨号的Profile ID 异常')
            time.sleep(3)

        elif case_id == 'test_linux_dfota_07_004':
            self.at_handler.check_network()
            all_logger.info('AT+QFOTAPID指定APN')
            self.at_handler.send_at('AT+QFOTAPID=7', 0.6)
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 7' in return_value:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID为 7 成功')
            else:
                all_logger.info('配置DFOTA升级数据拨号的Profile ID异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('配置DFOTA升级数据拨号的Profile ID 异常')
            all_logger.info('cfun1,1')
            self.at_handler.send_at('AT+CFUN=1,1', 15)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            all_logger.info('AT+QFOTAPID?查询返回值')
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 7' in return_value:
                all_logger.info('重启后查询返回Profile ID仍为 7')
            else:
                all_logger.info('重启后查询返回Profile ID不为 7，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('重启后查询返回异常')
            all_logger.info('AT+CGDCONT=7删除第四路apn')
            self.at_handler.send_at('AT+CGDCONT=7', 0.6)
            time.sleep(3)
        elif case_id == 'test_linux_dfota_07_005':
            self.at_handler.check_network()
            all_logger.info('切换回第一路')
            self.at_handler.send_at('AT+QFOTAPID=1', 0.3)
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 1' in return_value:
                all_logger.info('切换回Profile ID 1')
            else:
                all_logger.info('切换回Profile ID 1异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('切换回Profile ID 1异常')
            time.sleep(3)

        elif case_id == 'test_linux_dfota_07_006':
            all_logger.info('配置DFOTA升级数据拨号的Profile ID为 7 ')
            self.at_handler.send_at('AT+QFOTAPID=4', 0.6)
            all_logger.info('AT+QFOTAPID?查询返回值')
            return_value = self.at_handler.send_at('AT+QFOTAPID?', 0.3)
            if '+QFOTAPID: 4' in return_value:
                all_logger.info('查询返回Profile ID为4')
            else:
                all_logger.info('查询Profile ID返回不为4，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('AT+QFOTAPID?查询返回Profile ID不为4异常')
            time.sleep(3)

        elif case_id == 'test_linux_dfota_07_007':
            all_logger.info('设置AT+QFOTAPID=0')
            return_value = self.at_handler.send_at('AT+QFOTAPID=0', 0.6)
            if 'ERROR' in return_value:
                all_logger.info('返回ERROR，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=0，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=0，返回异常')

            all_logger.info('设置AT+QFOTAPID=1')
            return_value = self.at_handler.send_at('AT+QFOTAPID=1', 0.3)
            if 'OK' in return_value:
                all_logger.info('返回OK，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=1，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=1，返回异常')

            all_logger.info('设置AT+QFOTAPID=8')
            return_value = self.at_handler.send_at('AT+QFOTAPID=8', 0.3)
            if 'OK' in return_value:
                all_logger.info('返回OK，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=8，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=8，返回异常')

            all_logger.info('设置AT+QFOTAPID=9')
            return_value = self.at_handler.send_at('AT+QFOTAPID=9', 0.3)
            if 'ERROR' in return_value:
                all_logger.info('返回ERROR，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=9，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=9，返回异常')

            all_logger.info('设置AT+QFOTAPID=+')
            return_value = self.at_handler.send_at('AT+QFOTAPID=+', 0.3)
            if 'ERROR' in return_value:
                all_logger.info('返回ERROR，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=+，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=+，返回异常')

            all_logger.info('设置AT+QFOTAPID=a')
            return_value = self.at_handler.send_at('AT+QFOTAPID=a', 0.3)
            if 'ERROR' in return_value:
                all_logger.info('返回ERROR，正确')
            else:
                all_logger.info('设置AT+QFOTAPID=a，返回异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxDFOTAError('设置AT+QFOTAPID=a，返回异常')
            time.sleep(3)
        else:
            all_logger.info("case_id传送错误")

    def check_Multifota(self, debug_data):  # noqa
        if 'layout' in debug_data and 'multi fota' in debug_data:
            if 'handle err' not in debug_data:
                all_logger.info('debug log中无err，PASS')
            else:
                all_logger.info('debug log中检测存在err，请手动check')
                raise LinuxDFOTAError('debug log中检测存在err，请手动check')
        else:
            all_logger.info('debug log中未检测到"layout"和"multi fota"关键词,请手动check')
            raise LinuxDFOTAError('debug log中未检测到"layout"和"multi fota"关键词,请手动check')

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是pcie模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handler.send_at('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handler.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)

    def enter_mbim_mode(self):
        self.set_linux_mbim_and_remove_driver()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.check_linux_mbim_and_driver_name()

    def check_linux_mbim_and_driver_name(self):
        """
        检查是否是MBIM拨号方式，检查mbim驱动是否加载，检查WWAN驱动名称
        :return: None
        """
        all_logger.info("检查USBNET为2")
        for i in range(0, 5):
            time.sleep(5)
            usbnet = self.at_handler.send_at('AT+QCFG="USBNET"')
            if ',2' in usbnet:
                all_logger.info('当前设置usbnet模式为2')
                break
            else:
                if i == 4:
                    raise LinuxDFOTAError(f'设置usbnet失败,当前查询返回为{usbnet}')
                all_logger.info(f'当前查询指令返回{usbnet},等待5秒后再次查询')
                continue
        all_logger.info("检查cdc_mbim驱动加载")
        timeout = 30
        for _ in range(timeout):
            s = subprocess.run('lsusb -t', shell=True, capture_output=True, text=True)
            all_logger.info(s)
            if 'cdc_mbim' in s.stdout:  # noqa
                break
            time.sleep(1)
        else:
            all_logger.info(f"MBIM驱动开机后{timeout}S未加载成功")
            raise LinuxDFOTAError(f"MBIM驱动开机后{timeout}S未加载成功")

        all_logger.info("检查wwan0驱动名称")
        s = subprocess.run("ip a | grep -o wwan0", shell=True, capture_output=True, text=True)
        all_logger.info(s)
        if 'wwan0' not in s.stdout:
            all_logger.info(f'MBIM驱动名称异常->"{s.stdout}"')
            raise LinuxDFOTAError(f'MBIM驱动名称异常->"{s.stdout}"')

    def set_linux_mbim_and_remove_driver(self):
        """
        设置MBIM拨号方式并且删除所有的网卡
        :return: None
        """
        time.sleep(5)  # 防止刚开机AT不生效
        all_logger.info("设置USBNET为2")
        self.at_handler.send_at('AT+QCFG="USBNET",2')

        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'GobiNet']
        for name in network_types:
            all_logger.info(f"删除{name}网卡")
            subprocess.run(f"modprobe -r {name}", shell=True)

    @staticmethod
    def process_input():
        subprocess.Popen("killall udhcpc", shell=True)

    @staticmethod
    def check_linux_wwan0_network_card_disappear():
        """
        断开拨号后，检查WWAN0网卡消失
        :return: None
        """
        wwan0_status = os.popen('ifconfig wwan0').read()
        if 'not found' in wwan0_status:
            all_logger.info("quectel-CM异常，wwan0网卡未消失")
            raise LinuxDFOTAError("quectel-CM异常，wwan0网卡未消失")

    def udhcpc_get_ip(self, network_card_name):  # noqa
        all_logger.info(f"udhcpc -i {network_card_name}")
        process = subprocess.Popen(f'udhcpc -i {network_card_name}',
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   shell=True)
        t = threading.Timer(120, self.process_input)  # pylint: disable=E1101
        t.setDaemon(True)
        t.start()
        get_result = ''
        while process.poll() is None:
            value = process.stdout.readline().decode()
            if value:
                all_logger.info(value)
                get_result += value
        all_logger.info(get_result)


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
            raise LinuxDFOTAError("检测DFOTA升级时打开AT口异常")

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
