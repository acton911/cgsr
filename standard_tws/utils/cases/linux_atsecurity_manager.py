import random
import shutil
import time
import glob
from collections import deque
import serial.tools.list_ports
from utils.functions.linux_api import LinuxAPI
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.exception.exceptions import LinuxABSystemError
from utils.functions.jenkins_at_security import multi_thread_merge_SDX6X_AB_gentools
from utils.functions.jenkins_at_security import multi_thread_merge_version, multi_thread_merge_fota_full_images
from utils.operate.uart_handle import UARTHandle
from utils.exception.exceptions import LinuxDFOTAError
import subprocess
from utils.logger.logging_handles import all_logger, at_logger
from threading import Thread
from subprocess import PIPE
from zipfile import ZipFile
import filecmp
import os
import requests
import paramiko
import re
import hashlib
from getpass import getuser
from utils.functions.gpio import GPIO
import sys


class LinuxATSecurityManager:

    def __init__(self, oc_num, uart_port, revision, sub_edition, prev_upgrade_revision, svn, ChipPlatform, prev_upgrade_sub_edition,
                 prev_svn, at_port, usb_id, dm_port, prev_firmware_path, firmware_path, name_sub_version, prev_name_sub_version,
                 unmatch_firmware_path, unmatch_name_sub_version, imei_number):
        self.at_port = at_port
        self._at_port = at_port
        self.dm_port = dm_port
        self.oc_num = oc_num
        self.unmatch_firmware_path = unmatch_firmware_path
        self.unmatch_name_sub_version = unmatch_name_sub_version
        self.name_sub_version = name_sub_version
        self.prev_name_sub_version = prev_name_sub_version
        self.firmware_path = firmware_path
        self.revision = revision
        self.sub_edition = sub_edition
        self.prev_upgrade_revision = prev_upgrade_revision
        self.prev_upgrade_sub_edition = prev_upgrade_sub_edition
        self.prev_firmware_path = prev_firmware_path
        self.prev_svn = prev_svn
        self.svn = svn
        self.imei_number = imei_number
        self.usb_id = usb_id
        self.ChipPlatform = ChipPlatform
        self.uart_handler = UARTHandle(uart_port)
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.linux_api = LinuxAPI()
        self.Is_XiaoMi_version = True if '_XM' in self.revision else False
        md5 = hashlib.md5()
        md5.update(
            f'sdx6x{self.revision}{self.sub_edition}{self.prev_upgrade_revision}{self.prev_upgrade_sub_edition}'.encode(
                'utf-8'))
        self.package_dir = md5.hexdigest()[:10]  # 创建一个文件夹，用于在ftp和http(s)服务器上创建，避免重复
        self.gpio = GPIO()
        # self.ab_system = ['NON-HLOS.ubi', 'sdxprairie-boot.img', 'sdxprairie-sysfs.ubi']
        # AB系统升级过程中出现异常导致升级程序退出，模块将上报
        self.exit_code = {
            "1": "升级脚本参数错误",
            "2": "SD卡不存在",
            "3": "升级包不存在",
            "4": "升级包解压异常",
            "5": "分区擦写异常",
            "6": "xml文件解析异常",
            "7": "文件差分操作异常",
            "8": "空间不足",
            "9": "文件检测异常",
            "10": "文件合成操作异常",
            "11": "分区检测异常",
            "12": "制作UBI文件系统分区卷异常",
            "13": "升级包异常，缺失config.xml文件",
            "14": "固件版本检测异常",
            "15": "升级包异常，镜像文件不存在"
        }
        # AT+QABFOTA="state"  查询升级状态返回码
        self.state_code = {
            "0": "SUCCEED : AB系统升级成功",
            "1": "UPDATE : AB系统正在升级",
            "2": "BACKUP : AB系统升级成功，需同步未激活系统",
            "3": "FAILED : AB系统升级失败",
            "4": "WRITEDONE : （暂不支持）",
            "5": "NEEDSYNC : AB系统升级失败，需还原损坏系统",
            "6": "UNKNOW TYPE : AB系统升级出现未知错误"
        }
        # AT+QABFOTA="activeslot"  查询当前运行系统
        self.start_sequence = {
            "0": "A系统",
            "1": "B系统",
        }
        # 是否是OCPU版本
        self.Is_OCPU_version = True if 'OCPU' in name_sub_version else False

    def check_prev_data(self):
        if not self.prev_upgrade_revision or not self.prev_upgrade_sub_edition or not self.prev_firmware_path or not self.prev_svn:
            raise LinuxDFOTAError("未检查到数据库填写的prev_upgrade_revision/prev_upgrade_sub_edition/prev_firmware_path"
                                  "/prev_svn相关参数或者CI传参异常，请检查数据库中name_sub_version是否存在，是否有空格，是否有重复名称")

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
        all_logger.info('mount -t cifs {} /mnt/cur -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            cur_package_path))
        os.popen('mount -t cifs {} /mnt/cur -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            cur_package_path)).read()
        all_logger.info('mount -t cifs {} /mnt/prev -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            prev_package_path))
        os.popen('mount -t cifs {} /mnt/prev -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            prev_package_path)).read()
        if os.listdir('/mnt/cur') and os.listdir('/mnt/prev'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise LinuxDFOTAError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def ubuntu_copy_file():
        """
        Ubuntu下复制版本包
        :return:
        """
        if not os.path.exists(os.path.join(os.getcwd(), '/firmware')):
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
                raise LinuxDFOTAError('版本包获取失败')
        else:
            all_logger.info('本地已存在版本包路径，无需再下载版本包')

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
            raise LinuxDFOTAError("获取前一个版本target file zip失败")

        for path, _, files in os.walk(os.path.join(firmware_path, 'cur')):
            for file in files:
                if file == 'targetfiles.zip':
                    cur_target_file = os.path.join(path, file)
        if not cur_target_file:
            raise LinuxDFOTAError("获取当前版本target file zip失败")

        # 兼容小米定制版本
        if self.Is_XiaoMi_version:
            multi_thread_merge_fota_full_images(orig_target_file, cur_target_file)
        else:
            multi_thread_merge_version(orig_target_file, cur_target_file)

    def make_abdfota_package(self, factory):
        """
        查找当前路径 + firmware + prev/cur路径下面的所有targetfiles.zip，然后制作差分包。
        判断OC，确认进行ABFOTA
        :return: None
        """
        all_logger.info("开始制作差分包")
        orig_target_file = ''
        cur_target_file = ''
        old_zip_path = os.getcwd() + r'/firmware/prev'
        all_logger.info("目标版本包路径old_zip_path为:\r\n{}".format(old_zip_path))
        new_zip_path = os.getcwd() + r'/firmware/cur'
        all_logger.info("当前版本包路径new_zip_path为:\r\n{}".format(new_zip_path))
        if factory:
            if os.path.exists(os.path.join(old_zip_path, self.prev_name_sub_version + '_factory.zip')):
                orig_target_file = os.path.join(old_zip_path, self.prev_name_sub_version + '_factory.zip')
                all_logger.info("目标版本工厂包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取目标版本工厂包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')
                all_logger.info("当前版本工厂包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise LinuxABSystemError("获取当前版本工厂包名称失败")

        else:
            if os.path.exists(os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')):
                orig_target_file = os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')
                all_logger.info("目标版本标准包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取目标版本标准包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '.zip')
                all_logger.info("当前版本标准包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise LinuxABSystemError("获取当前版本标准包名称失败")

        module_id = self.get_module_id()
        all_logger.info("module_id为:{}".format(module_id))

        # 根据OC来决定制作的差分包方式
        all_logger.info("当前oc_num为: {}".format(self.oc_num))
        # RG502NEUDA-M28-SGASA
        oc_num_key = ''.join(re.findall(r'-\w+-', self.oc_num))
        all_logger.info("oc_num_key: {}".format(oc_num_key))
        if '8' in oc_num_key:
            oc_key = '8'
            all_logger.info("当前flash为 8+8")
        else:
            oc_key = '4'
            all_logger.info("当前flash为 4+4")
        all_logger.info("oc_key: {}".format(oc_key))

        multi_thread_merge_SDX6X_AB_gentools(orig_target_file, cur_target_file, self.prev_name_sub_version,
                                             self.name_sub_version, module_id, oc_key)

    def get_module_id(self):
        gmm_value = self.at_handler.send_at("AT+GMM")
        all_logger.info("\r\n{}".format(gmm_value))
        key_value = ''.join(re.findall(r'\w+(-)\w+', gmm_value))
        if key_value == '-':
            module_id = ''.join(re.findall(r'\w+-\w+', gmm_value))  # 带 '-'，例如RG500Q-EA
        else:
            module_gmm = ''.join(re.findall(r'\W+(\w+)\W+OK', gmm_value))  # 不带 '-'，例如SG520TM
            list_i = list(module_gmm)  # str -> list
            list_i.insert(-2, '-')  # 补上 '-'
            module_id = ''.join(list_i)  # list -> str
        # module_id = 'SG520-TM'  # 有BUG临时调试
        all_logger.info("module_id为:{}".format(module_id))
        return module_id

    def upload_package_to_sftp(self):
        a_b_path = os.path.join(os.getcwd(), 'firmware', 'a-b&;|.zip')
        b_a_path = os.path.join(os.getcwd(), 'firmware', 'b-a&;|.zip')
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
                    sftp.put(a_b_path, "/html/5G/{}/a-b&;|.zip".format(self.package_dir))
                    sftp.put(b_a_path, "/html/5G/{}/b-a&;|.zip".format(self.package_dir))

                all_logger.info('server package dir:\r\n/html/5G/{}'.format(self.package_dir))
                # 创建cache_sftp文件夹
                all_logger.info('sftp mkdir')
                if not os.path.exists(os.path.join(os.getcwd(), 'firmware', 'cache_sftp')):
                    os.mkdir(os.path.join(os.getcwd(), 'firmware', 'cache_sftp'))

                # 下载下来进行版本包对比
                all_logger.info('sftp download and compare')
                package_check_flag = False
                for file in ['a-b&;|.zip', 'b-a&;|.zip']:
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

    def dfota_upgrade_online(self, dfota_type, a_b=True, dl_stop=False, upgrade_stop=False, start=False, end=False,
                             dl_vbat=False, dl_cfun=False, dl_cgatt=False):
        fota_cmd = []
        if dfota_type.upper() == "FTP":
            fota_cmd.extend(['ftp://test:test@112.31.84.164:8309/5G/'])
        elif dfota_type.upper() == 'HTTP':
            fota_cmd.extend(['http://112.31.84.164:8300/5G/'])
        elif dfota_type.upper() == 'HTTPS':
            fota_cmd.extend(['https://112.31.84.164:8301/5G/'])
        fota_cmd.extend([self.package_dir, '/'])
        if a_b:
            fota_cmd.extend(['a-b&;|.zip'])
        else:
            fota_cmd.extend(['b-a&;|.zip'])
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

    def check_activeslot(self):
        """
        AT+QABFOTA="activeslot"  查询当前运行系统
        """
        all_logger.info("查询当前运行系统")
        all_logger.info(self.__dict__)
        return_value = self.at_handler.send_at('AT+QABFOTA="activeslot"', 3)
        key_system = ''.join(re.findall(r'\+QABFOTA: "activeslot",(\d)', return_value))
        all_logger.info("key_system:{}".format(key_system))
        if key_system == '0' or key_system == '1':
            all_logger.info("查询当前运行系统为{}!".format(self.start_sequence[key_system]))
            return key_system
        else:
            raise LinuxABSystemError("查询当前运行系统异常!{}".format(return_value))

    def ab_update_online(self, dfota_type, a_b=True, end=False):
        fota_cmd = []
        system_before = self.check_activeslot()
        all_logger.info("system_before:{}".format(system_before))
        if dfota_type.upper() == "FTP":
            fota_cmd.extend(['ftp://test:test@112.31.84.164:8309/5G/'])
        elif dfota_type.upper() == 'HTTP':
            fota_cmd.extend(['http://112.31.84.164:8300/5G/'])
        elif dfota_type.upper() == 'HTTPS':
            fota_cmd.extend(['https://112.31.84.164:8301/5G/'])
        fota_cmd.extend([self.package_dir, '/'])
        if a_b:
            fota_cmd.extend(['a-b&;|.zip'])
        else:
            fota_cmd.extend(['b-a&;|.zip'])
        fota_cmd = ''.join(fota_cmd)
        all_logger.info(fota_cmd)
        # step1

        if a_b:
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
            self.set_package_name(a_b=True)
            self.send_update()
        else:
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)
            self.set_package_name(a_b=False)
            self.send_update()
        """
        all_logger.info("设置版本包名称")
        self.at_handler.send_at('AT+QABFOTA="package","update.zip"', 3)   #  有BUG临时调试
        return_value = self.at_handler.send_at('AT+QABFOTA="package"', 3)
        all_logger.info("{}".format(return_value))
        if "update.zip" not in return_value:
            raise LinuxABSystemError("设置版本包名称异常!")
        else:
            all_logger.info("设置版本包名称成功")
        self.send_update()
        """

        # step2

        if end is False:  # 正常升级
            self.dfota_step_2()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()
        all_logger.info("升级后运行系统查询")
        system_after = self.check_activeslot()
        if system_after != system_before:
            all_logger.info("升级后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
        else:
            raise LinuxABSystemError(
                "升级后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
        # 升级后信息查询
        all_logger.info("检查升级后升级状态是否正确")
        self.query_state(state_module="2")
        # 升级后信息查询
        if a_b:
            self.dfota_a_b_upgrade_check()
        else:
            self.dfota_b_a_upgrade_check()
        # 升级重启后查询升级状态
        self.query_state(state_module="2")
        start_time = time.time()
        while time.time() - start_time < 600:
            time.sleep(5)
            try:
                self.query_state(state_module="0")
                break
            except Exception:
                pass

        # 升级重启后等待10min查询升级状态
        self.query_state(state_module="0")
        all_logger.info("升级完成!")

    def check_urc(self):
        """
        用于开机检测端口是否有任何内容上报,如果读取到任何内容,则停止。
        :return: True:有URC
        """
        at_logger.info("检测端口是否可以正常打开")
        cnt = 10
        while cnt != 0:
            cnt = cnt - 1
            try:
                with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
                    at_logger.info("AT口打开正常")
                    break
            except (serial.serialutil.SerialException, OSError) as e:
                at_logger.error(e)
                at_logger.info("打开AT口失败，尝试重新打开AT口")
                time.sleep(3)
        else:
            raise LinuxABSystemError("连续10次打开AT口失败")

        at_logger.info("检测URC上报")
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            check_urc_start_timestamp = time.time()
            while True:
                time.sleep(0.001)  # 减小CPU开销
                if time.time() - check_urc_start_timestamp > 60:  # 暂定60S没有URC上报则异常
                    raise LinuxABSystemError("60S内未检查到URC上报")
                else:  # 检查URC
                    at_port_data = self.readline(__at_port)
                    if at_port_data != '':
                        all_logger.info("{}".format(at_port_data))
                    if 'PB DONE' in at_port_data:
                        time.sleep(1)  #  等待1s，尝试避免Device or resource busy
                        return True

    def query_state(self, state_module):
        """
        AT+QABFOTA="state"  查询升级状态
        """
        # all_logger.info("查询当前升级状态")
        return_value = self.at_handler.send_at('AT+QABFOTA="state"', 3)
        key_state = ''.join(re.findall(r'\+QABFOTA: "state",\w+ \((\d)\)', return_value))
        # all_logger.info("key_state:{}".format(key_state))
        if "FAILED" in return_value:
            raise LinuxABSystemError("查询升级失败!{}".format(return_value))
        elif key_state in self.state_code.keys():
            all_logger.info("查询当前升级状态为[{}]".format(self.state_code[key_state]))
            pass
        else:
            raise LinuxABSystemError("查询升级状态异常!{}".format(return_value))

        if state_module != key_state:
            raise LinuxABSystemError("state查询异常!查询值为{},于预期不符!预期为{}".format(key_state, state_module))
        else:
            all_logger.info("state查询正常, state: {}".format(key_state))

    def dfota_step_2(self, upgrade_stop=False, continu_update=False, send_again=False):
        """
        发送AT+QABFOTA="download"指令后的log检查:
        检测+QIND: "ABFOTA","UPDATE",11 到 +QIND: "ABFOTA","UPDATE",100
        :return: None
        """
        for i in range(100):
            try:
                at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(0.5)
                continue
        else:
            raise LinuxABSystemError("检测ABFOTA升级时打开AT口异常")
        start_urc_flag = False
        delete_flag = False
        start_time = time.time()
        try:
            if not continu_update:
                # 检查 FTPSTART / HTTPSTART，如果检测到"ABFOTA","update"，则没有检测到，为了保证可以断电等操作，直接跳出
                while time.time() - start_time < 300:
                    time.sleep(0.001)
                    recv = self.readline(at_port)
                    if recv != '':
                        all_logger.info("{}".format(recv))
                    error_msg = '+QABFOTA: "UPDATE",-'
                    check_msg = '+QABFOTA: "UPDATE",11'
                    if check_msg in recv:
                        at_logger.info("已检测到{}".format(check_msg))
                        start_urc_flag = True
                        break
                    elif error_msg in recv:
                        key_update = ''.join(re.findall(r'\+QABFOTA: "UPDATE",-(\d)', recv))
                        if key_update in self.exit_code.keys():
                            raise LinuxABSystemError("触发AB系统升级异常!查询当前升级状态为[{}]!".format(self.exit_code[key_update]))
                        else:
                            raise LinuxABSystemError("未知异常!\r\n{}".format(recv))
                else:
                    at_logger.error('ABFOTA 检测{} +QIND: "ABFOTA","UPDATE",11失败')
                    raise LinuxABSystemError('ABFOTA升级过程异常: 检测{} +QIND: "ABFOTA","UPDATE",11失败')
            else:
                start_urc_flag = True
            # 如果需要断电或者断网
            if upgrade_stop:
                sleep_time = random.uniform(10, 50)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            all_logger.info("检查升级中升级状态是否正确")
            time.sleep(3)
            at_port.write('AT+QABFOTA="state"\r\n'.encode('utf-8'))
            at_logger.info('Send: {}'.format('AT+QABFOTA="state"'))
            # self.query_state(state_module="1")
            # 检查 "ABFOTA","update",100

            # 如果升级过程中再次发送升级命令
            if send_again:
                all_logger.info("再次发送升级命令")
                time.sleep(2)
                at_port.write('AT+QABFOTA="UPDATE"\r\n'.encode('utf-8'))
                all_logger.info('Send: {}'.format('AT+QABFOTA="UPDATE"'))
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                if recv != '':
                    all_logger.info("{}".format(recv))
                if 'ERROR' in recv:
                    if send_again:
                        all_logger.info("已检测到ERROR信息,符合预期")
                    else:
                        raise LinuxABSystemError("发送指令异常,返回ERROR!{}".format(recv))
                if '+QABFOTA: "state"' in recv:
                    key_state = ''.join(re.findall(r'\+QABFOTA: "state",\w+ \((\d)\)', recv))
                    all_logger.info("key_state:{}".format(key_state))
                    if key_state in self.state_code.keys():
                        all_logger.info("查询当前升级状态为[{}]!".format(self.state_code[key_state]))
                    else:
                        if delete_flag:
                            all_logger.info("查询升级状态异常!{}".format(recv))
                        else:
                            raise LinuxABSystemError("查询升级状态异常!{}".format(recv))
                    if key_state != '1':
                        if delete_flag:
                            all_logger.info("删除升级包后,已经查询升级状态异常[{}]!".format(self.state_code[key_state]))
                            return True
                        raise LinuxABSystemError("查询升级状态异常[{}]!".format(self.state_code[key_state]))
                    else:
                        all_logger.info("state查询正常, state: {}".format(key_state))
                if '+QABFOTA: "UPDATE"' in recv:
                    recv_regex = ''.join(re.findall(r'\++QABFOTA:\s"UPDATE",(\d+)', recv))
                    if recv_regex:
                        if recv_regex == '100':
                            at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                            time_update_use = time.time() - start_time
                            all_logger.info("time_update_use:{}".format(str(time_update_use)))
                            return time_update_use
                    if time.time() - start_time > 300:
                        raise LinuxABSystemError("ABFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise LinuxABSystemError('ABFOTA升级失败')

    def dfota_dl_package_701_702(self):
        """
        dfota断网后需要捕获701异常
        :return:
        """
        start_time = time.time()
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as at_port:
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                if 'END",701' in recv or 'END",702' in recv or 'END",601' in recv or 'END",602' in recv:
                    all_logger.info("已经检测到下载失败信息:\r\n{}".format(recv))
                    return True
                if time.time() - start_time > 180:
                    raise LinuxABSystemError("断网后ABFOTA升级命令未返回下载失败信息:\r\n{}".format(recv))

    def set_package_name(self, a_b=True):
        """
        AT+QABFOTA="package"  设置升级包名称
        """
        package_name = 'a-b&;|.zip' if a_b else "b-a&;|.zip"
        all_logger.info("设置版本包名称")
        self.at_handler.send_at('AT+QABFOTA="package","{}"'.format(package_name), 3)
        return_value = self.at_handler.send_at('AT+QABFOTA="package"', 3)
        all_logger.info("{}".format(return_value))
        if package_name not in return_value:
            raise LinuxABSystemError("设置版本包名称异常!")
        else:
            all_logger.info("设置版本包名称成功")

    def send_update(self):
        """
        AT+QABFOTA="update"  触发AB系统升级
        """
        all_logger.info("触发AB系统升级")
        self.at_handler.send_at('AT+QABFOTA="UPDATE"', 0.3)

    def get_tws_cache_dir(self):
        if os.name == 'nt':
            return os.path.join("C:\\Users", getuser(), 'TWS_TEST_DATA')
        else:
            raise NotImplementedError("暂未实现")

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
            all_logger.info("检查当前是A版本失败，开始升级!")
            exc_type = None
            exc_value = None
            try:
                self.qfirehose_upgrade('prev', False, True, True)
                self.driver.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.check_urc()
                self.at_handler.check_network()
                self.qfirehose_upgrade('prev', False, False, False)
                self.driver.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.check_urc()
                self.at_handler.check_network()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                time.sleep(5)
                if exc_type and exc_value:
                    raise exc_type(exc_value)
            time.sleep(20)  # 等到正常
            # self.after_upgrade_check()

    def reboot_module(self):
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()

    def reset_after(self, a_version=True):
        """
        用例测试完成检查state是否正常，异常则全擦升级来恢复正常
        """
        time.sleep(5)
        all_logger.info("当前测试结束，开始结束检查流程")
        start_time = time.time()
        while time.time() - start_time < 599:
            time.sleep(5)
            try:
                self.query_state(state_module='0')
                break
            except Exception:
                pass
        else:
            all_logger.info("异常!600s内未检测到初始状态!开始升级!")
            self.qfirehose_to_version(a_version)
        """
        if a_version:
            self.reset_a_version()
        else:
            self.reset_b_version()
        """

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
            all_logger.info("检查当前是B版本失败，开始升级!")
            exc_type = None
            exc_value = None
            try:
                self.qfirehose_upgrade('cur', False, True, True)
                self.driver.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.check_urc()
                self.at_handler.check_network()
                self.qfirehose_upgrade('cur', False, False, False)
                self.driver.check_usb_driver()
                self.gpio.set_vbat_high_level()
                self.driver.check_usb_driver_dis()
                self.gpio.set_vbat_low_level_and_pwk()
                self.driver.check_usb_driver()
                self.check_urc()
                self.at_handler.check_network()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                time.sleep(5)
                if exc_type and exc_value:
                    raise exc_type(exc_value)
            time.sleep(20)  # 等到正常
            # self.after_upgrade_check()

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
        package_name = package_name.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)')
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

    def qfirehose_to_version(self, a_version):
        all_logger.info("开始全擦升级恢复初始状态!")
        self.reboot_module()
        exc_type = None
        exc_value = None
        try:
            if a_version:
                self.qfirehose_upgrade('prev', False, True, True)
            else:
                self.qfirehose_upgrade('cur', False, True, True)
            self.driver.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.check_urc()
            self.at_handler.check_network()
            if a_version:
                self.qfirehose_upgrade('prev', False, False, False)
            else:
                self.qfirehose_upgrade('cur', False, False, False)
            self.driver.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.check_urc()
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)
        time.sleep(20)  # 等到正常

    def dfota_ftp_http_https_step_1(self, dfota_type, fota_cmd, stop_download=False):
        """
        仅处理at+qfotadl指令中关机前的部分:
        1. FTP，检测+QIND: "ABFOTA","FTPSTART" 到 +QIND: "ABFOTA","FTPEND",0
        2. HTTP，检测+QIND: "ABFOTA","HTTPSTART" 到 +QIND: "ABFOTA","HTTPEND",0
        3. HTTPS，检测+QIND: "ABFOTA","HTTP START" 到 +QIND: "ABFOTA","HTTP END",0
        :return: None
        """
        check_fragment = 'FTP' if dfota_type.upper() == 'FTP' else "HTTP"
        at_logger.info('check_fragment: {}'.format(check_fragment))
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as at_port:
            at_port.write(f'AT+QABFOTA="download","{fota_cmd}"\r\n'.encode('utf-8'))
            at_logger.info('Send: {}'.format(f'AT+QABFOTA="download","{fota_cmd}"\r\n'))
            # 检查 FTPSTART / HTTPSTART
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                # +QIND: "ABFOTA","HTTPSTART"
                check_msg = '+QIND: "ABFOTA","{}START"'.format(check_fragment)
                #if check_msg in recv:
                if 'START' in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    break
                if time.time() - start_time > 60:
                    raise LinuxABSystemError("发送升级指令后60秒内未检测到{}".format(check_msg))
                if 'ERROR' in recv:
                    raise LinuxABSystemError("发送ABFOTA升级指令返回ERROR")
            # 如果需要断电或者断网
            if stop_download:
                sleep_time = random.uniform(1, 2)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            # 检查 "FTPEND",0  "HTTPEND",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                if recv != '':
                    at_logger.info("{}".format(recv))
                recv_regex = ''.join(re.findall(r'\+QIND:\s"ABFOTA","{}.*END",(\d+)'.format(check_fragment), recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}".format(recv))
                        self.at_handler.send_at('AT+QFLST="*"', 3)
                        return True
                    else:
                        raise LinuxABSystemError("ABFOTA下载差分包异常: {}".format(recv))
                if time.time() - start_time > 300:
                    raise LinuxABSystemError("ABFOTA下载差分包超过300S异常")

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
