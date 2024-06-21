import random
import shutil
import time
from collections import defaultdict
import serial.tools.list_ports
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.exception.exceptions import LinuxABSystemError
from utils.functions.jenkins import multi_thread_merge_SDX6X_AB_gentools, query_key
from utils.operate.uart_handle import UARTHandle
import subprocess
from utils.logger.logging_handles import all_logger, at_logger
from subprocess import STDOUT, PIPE
from zipfile import ZipFile
import filecmp
import os
from ftplib import FTP
import requests
import paramiko
import re
import hashlib
from getpass import getuser
from utils.functions.gpio import GPIO
import sys


class LinuxABSystemManager:

    def __init__(self, oc_num, uart_port, revision, sub_edition, prev_upgrade_revision, svn, prev_upgrade_sub_edition,
                 prev_svn, at_port, dm_port, prev_firmware_path, firmware_path, name_sub_version, prev_name_sub_version,
                 unmatch_firmware_path, unmatch_name_sub_version):
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
        self.uart_handler = UARTHandle(uart_port)
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
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

    @staticmethod
    def query_modem_cpu_status(query_mode=True, times=10, cpu_max=99, cpu_min=0):
        """
        查询模块cpu占用情况
        times: 查询的采集次数
        query_mode: True(查询并返回查询值); False(未达到期望值报错)
        cpu_max: 期望最大值
        cpu_min: 期望最小值
        """
        # 按3s一次进行times次采集CPU数据
        status_return = subprocess.getoutput("adb shell top -d 3 -n {}".format(times + 1))
        # all_logger.info("status_return:\r\n{}".format(status_return))
        cpu_status = re.findall(
            r'CPU:\s+\d+.\d+%\s+usr\s+\d+.\d+%\s+sys\s+\d+.\d+%\s+nic\s+\d+.\d+%\s+idle\s+\d+.\d+%\s+io\s+\d+.\d+%\s+irq\s+\d+.\d+%\s+sirq',
            status_return)
        cpu_free = re.findall(
            r'CPU:\s+\d+.\d+%\s+usr\s+\d+.\d+%\s+sys\s+\d+.\d+%\s+nic\s+(\d+.\d+)%\s+idle\s+\d+.\d+%\s+io\s+\d+.\d+%\s+irq\s+\d+.\d+%\s+sirq',
            status_return)
        all_logger.info("\r\n" + "#" * 90 + "\r\n")
        for i in cpu_status:
            all_logger.info("\r\n" "{}\r\n".format(i))
        # all_logger.info("\r\n" + "#"*90 + "\r\ncpu_status:\r\n{}\r\n".format(cpu_status) + "#"*90)
        all_logger.info("\r\n" + "#" * 90 + "\r\ncpu_free:\r\n{}\r\n".format(cpu_free) + "#" * 90)
        # 去掉第一个波动较大值
        cpu_free.pop(0)
        # 求平均值
        cpu_free_sum = 0
        for i in cpu_free:
            cpu_free_sum = cpu_free_sum + float(i)
        cpu_free_avg = cpu_free_sum / len(cpu_free)
        all_logger.info("\r\ncpu_free_avg:{}".format(str(cpu_free_avg)))
        all_logger.info("\r\n" + "#" * 90 + "\r\n")
        if query_mode:
            return cpu_free_avg
        else:
            if cpu_free_avg > cpu_max:
                raise LinuxABSystemError("CPU占用率异常,平均空闲率为: {},高于期望值{}".format(str(cpu_free_avg), str(cpu_max)))
            if cpu_free_avg < cpu_min:
                raise LinuxABSystemError("CPU占用率异常,平均空闲率为: {},低于期望值{}".format(str(cpu_free_avg), str(cpu_min)))

    def eblock(self, block, nums=12):
        """
        擦除指定分区
        """
        all_logger.info("开始擦除{}分区".format(block))
        for i in range(nums):
            self.at_handler.send_at('AT+QNAND="EBlock","{}",{}'.format(block, i + 1), 3)
            all_logger.info('AT+QNAND="EBlock","{}",{}'.format(block, i + 1))
            time.sleep(1)
        all_logger.info("擦除{}分区结束".format(block))

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
            raise LinuxABSystemError('ATI查询的B版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxABSystemError("写号后查号异常")

        # 有BUG临时调试
        """
        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise LinuxABSystemError("SVN查询异常\r\n{}".format(return_value))
        """

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
            raise LinuxABSystemError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxABSystemError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxABSystemError("执行备份指令后查询异常")

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
            raise LinuxABSystemError('ATI查询的A版本号和当前设置版本号不一致')

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxABSystemError("写号后查号异常")

        # 有BUG临时调试
        """
        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise LinuxABSystemError("SVN查询异常")
        """

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
            raise LinuxABSystemError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxABSystemError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=1指令执行异常")
        else:
            raise LinuxABSystemError("执行备份指令后查询异常")

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
            raise LinuxABSystemError("FTP上传差分包失败")

    def make_dfota_package(self, factory):
        """
        查找当前路径 + firmware + prev/cur路径下面的所有targetfiles.zip，然后制作差分包。
        :return: None
        """
        all_logger.info("开始制作差分包")
        orig_target_file = ''
        cur_target_file = ''
        old_zip_path = os.getcwd() + r'/firmware/prev'
        new_zip_path = os.getcwd() + r'/firmware/cur'
        if factory:
            if os.path.exists(os.path.join(old_zip_path, self.prev_name_sub_version + '_factory.zip')):
                orig_target_file = os.path.join(old_zip_path, self.prev_name_sub_version + '_factory.zip')
                all_logger.info("前一个版本工厂包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取前一个版本工厂包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')
                all_logger.info("当前版本工厂包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise LinuxABSystemError("获取当前版本工厂包名称失败")

        else:
            if os.path.exists(os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')):
                orig_target_file = os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')
                all_logger.info("前一个版本标准包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取前一个版本标准包名称失败")

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
            raise LinuxABSystemError("请使用xftp软件，使用sftp协议，端口22，连接192.168.25.74，用户名：quectel，密码centos@123，检查内网是否可以正常连接")

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
                    raise LinuxABSystemError("复制文件对比异常")
        all_logger.info('下载固件成功')

    @staticmethod
    def get_package_name(package, factory):
        """
        获取版本包的完整名称
        :param package: 升级包路径,cur or prev
        :param factory: 是否工厂升级
        :return: 版本包的完整名称
        """
        # 首先确定版本包名称
        package_name = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware', package)):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', package, p)):
                if factory:
                    if p.lower().endswith('factory.zip') and p.lower().startswith(''):
                        package_name = os.path.join(os.getcwd(), 'firmware', package, p)
                        all_logger.info("package_name:{}".format(package_name))
                        return package_name
                else:
                    if not p.lower().endswith('factory.zip'):
                        package_name = os.path.join(os.getcwd(), 'firmware', package, p)
                        all_logger.info("package_name:{}".format(package_name))
                        return package_name
        if not package_name:
            raise Exception("未找到{}升级包".format('工厂' if factory else '标准'))

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
    def qfil(dl_port: str, erase=True, factory=True, external_path=''):
        """
        进行QFile升级
        :param dl_port: 紧急下载口
        :param erase: 是否进行全擦
        :param factory: 进行工厂版本还是标准版本
        :param external_path: 一般DFOTA中: 升级A版本，则填写cur，如果升级B版本，填写prev
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
        if factory:
            check_files = ['prog_firehose_lite.elf', "rawprogram_nand_p4K_b256K_factory.xml", 'patch_p4K_b256K.xml']
        else:
            check_files = ['prog_firehose_lite.elf', "rawprogram_nand_p4K_b256K_update.xml", 'patch_p4K_b256K.xml']
        for file in check_files:
            if file not in os.listdir(firehose_path):
                raise Exception("升级包firehose目录内未发现{}".format(file))

        # simplify set search_path in subprocess and fh_loader.exe command
        all_logger.info("copy QSaharaServer and fh_loader to firehose dir")
        if not os.path.exists(os.path.join(firehose_path, 'QSaharaServer.exe')):
            shutil.copy(os.path.join(qfil_path, 'QSaharaServer.exe'), firehose_path)
        if not os.path.exists(os.path.join(firehose_path, 'fh_loader.exe')):
            shutil.copy(os.path.join(qfil_path, 'fh_loader.exe'), firehose_path)

        all_logger.info("load firehose programmer")
        load_programmer = fr'QSaharaServer.exe -s 13:prog_firehose_lite.mbn -p \\.\{dl_port}'
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

        all_logger.info("download package")
        rawprogram_file = 'rawprogram_nand_p4K_b256K_factory.xml' if factory else 'rawprogram_nand_p4K_b256K_update.xml'
        all_in_one = fr'fh_loader.exe --port=\\.\{dl_port} --sendxml={rawprogram_file},patch_p4K_b256K.xml --search_path={firehose_path} {fh_cmd} --reset'
        upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=firehose_path,
            timeout=180,
            error_message='升级失败'
        )

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
        return_value = ''
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
            all_logger.info("{}".format(return_value))
            raise LinuxABSystemError('ATI查询的版本号和当前设置版本号不一致')

        # 写号
        return_value = self.at_handler.send_at('AT+EGMR=1,7,"864505040004635"', 0.3)
        if 'OK' not in return_value:
            raise LinuxABSystemError("写号异常")

        # 查号
        return_value = self.at_handler.send_at('AT+EGMR=0,7', 0.3)
        if 'OK' not in return_value or '864505040004635' not in return_value:
            raise LinuxABSystemError("写号后查号异常")

        # 有BUG临时调试
        """
        # SVN号
        return_value = self.at_handler.send_at('AT+EGMR=0,9', 0.3)
        if str(self.svn) not in return_value:
            raise LinuxABSystemError("SVN查询异常\r\n{}\r\n{}".format(self.svn, return_value))
        """

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
            raise LinuxABSystemError("升级后MBN列表查询异常")

        # 备份指令
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1执行异常")
        else:
            raise LinuxABSystemError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handler.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=4执行异常")
        else:
            raise LinuxABSystemError("执行备份指令后查询异常")

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
            time.sleep(1)
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

    def init_with_version_a(self):
        """
        VBAT开机，检查当前是A版本。
        :return: None
        """
        self.gpio.set_vbat_high_level()
        self.driver.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver.check_usb_driver()
        self.check_urc()
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
        self.check_urc()
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
        self.check_urc()
        self.at_handler.check_network()
        time.sleep(10)

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
            ')', '\)')
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
                    raise LinuxABSystemError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise LinuxABSystemError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise LinuxABSystemError('120S内升级失败')

    def unlock_adb(self):
        usbcfg_value = self.at_handler.send_at('AT+QCFG="USBCFG"', 3)
        if ',1,1,1,1,1,1' in usbcfg_value:
            all_logger.info("模块ADB已开启")
        else:
            PID = ''
            PID = re.findall(r'0x(\w+),0x(\w+)', usbcfg_value)
            if PID:
                all_logger.info("PID: {}".format(PID))
            if not PID:
                raise LinuxABSystemError("获取PID失败")
            if not self.Is_OCPU_version:
                qadbkey = self.at_handler.send_at('AT+QADBKEY?')
                qadbkey = ''.join(re.findall(r'\+QADBKEY:\s(\S+)', qadbkey))
                adb_key = query_key(qadbkey, qtype='adb')
                if not qadbkey:
                    raise LinuxABSystemError("获取QADBKEY失败")

                self.at_handler.send_at('AT+QADBKEY="{}"'.format(adb_key), 3)

                self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(PID[0][0], PID[0][1]), 3)
            else:
                all_logger.info('当前为OCPU版本，直接开启！')
                self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(PID[0][0], PID[0][1]), 3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.check_urc()
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
            # subprocess.run('adb kill-server')
            adb_value = repr(os.popen('adb devices').read())
            all_logger.info(adb_value)
            devices_online = ''.join(re.findall(r'\\n(.*)\\tdevice', adb_value))
            devices_offline = ''.join(re.findall(r'\\n(.*)\\toffline', adb_value))
            if devices_online != '' or devices_offline != '':  # 如果检测到设备
                all_logger.info('已检测到adb设备')  # 写入log
                return True
            elif time.time() - adb_check_start_time > 100:  # 如果超时
                raise LinuxABSystemError("adb超时未加载")
            else:  # 既没有检测到设备，也没有超时，等1S
                time.sleep(1)

    def at_package_and_check(self, a_b=True):
        # 删除所有文件、避免AT上传报错
        self.at_handler.send_at('AT+QFDEL="*"', 3)
        path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip' if a_b else "b-a.zip")
        all_logger.info("path:{}".format(path))
        file_name = 'a-b.zip' if a_b else "b-a.zip"
        all_logger.info("file_name:{}".format(file_name))
        file_size = os.path.getsize(path)
        all_logger.info("file_size:{}".format(file_size))
        package_md5 = hashlib.md5()
        with open(path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))
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

        for i in range(10):
            """
            at_port.write('AT+QFUPL="EFS:{}",{},300,1\r\n'.format(file_name, file_size).encode("utf-8"))
            all_logger.info('AT+QFUPL="EFS:{}",{},300,1\r\n'.format(file_name, file_size).encode("utf-8"))
            """
            self.qfupl(at_port, file_name, path)
            md5 = subprocess.getoutput('adb shell md5sum /cache/ufs/{}'.format('a-b.zip' if a_b else "b-a.zip"))
            all_logger.info(md5)
            at_logger.info('adb get md5:{}'.format(md5))
            if package_md5 in md5:
                all_logger.info("MD5对比正常")
                time.sleep(5)
                return 'a-b.zip' if a_b else "b-a.zip"
            time.sleep(1)
        else:
            raise LinuxABSystemError("ADB PUSH升级包失败")

    def qfupl(self, at_port_opened, package_name, package_path):
        # 开始写文件命令
        file_size = os.path.getsize(package_path)
        all_logger.info(['文件大小 {} bit'.format(file_size)])

        upl_command = 'AT+QFUPL="{}",{}'.format(package_name, file_size)
        all_logger.info('Send {}'.format(upl_command))
        at_port_opened.write('{}\r\n'.format(upl_command).encode('utf-8'))

        # 判断是否正常且无 CME ERROR
        cache = ''
        start = time.time()
        timeout = 3
        while True:
            time.sleep(0.001)
            data = self.readline(at_port_opened)
            if data:
                cache += data
                if "ERROR" not in cache and 'CONNECT' in data:
                    break
            if time.time() - start > 3:
                raise LinuxABSystemError('{}命令超时:{}S'.format(upl_command, timeout))
            if 'ERROR' in cache:
                raise LinuxABSystemError('{}返回异常:{}'.format(upl_command, data))

        # 写入文件
        with open(package_path, 'rb+') as f:
            write_size = 0
            cache = ''
            percent = 0
            while True:
                # 写入AT口
                chunk = f.read(1024 * 4)
                write_size += at_port_opened.write(chunk)
                # 计算百分比
                write_percent = write_size / file_size * 100 // 10
                if percent != write_percent:
                    all_logger.info('已发送 {} %'.format(round(write_percent * 10, 0)))
                    percent = write_percent
                # 读AT口
                data = self.readline(at_port_opened)
                if data:
                    cache += data
                    if 'ERROR' in data:
                        raise LinuxABSystemError(['文件上传过程中出现异常:{}'.format(data)])
                    if 'OK' in data:
                        break
            if write_size != file_size:
                raise LinuxABSystemError('文件上传大小:{} 与实际不一致:{}'.format(write_size, file_size))

    @staticmethod
    def push_package_and_check(a_b=True):
        path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip' if a_b else "b-a.zip")
        package_md5 = hashlib.md5()
        with open(path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))

        for i in range(10):
            # subprocess.run('adb kill-server')
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
                return 'a-b.zip' if a_b else "b-a.zip"
            time.sleep(1)
        else:
            raise LinuxABSystemError("ADB PUSH升级包失败")

    def push_modify_file(self, mode, a_b=True):
        """
        mode:修改方式
            add:增加
            del:删除
            part:下载到一半的残包
        """
        # 获取残包文件
        if mode == 'part':
            file_name = 'a-b.zip' if a_b else 'b-a.zip'
            self.ab_update_online("HTTP", '_', a_b=a_b, get_part_file=True)
        else:
            # 复制差分包
            os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/modify')
            file_list = os.listdir(os.path.join(os.getcwd(), 'firmware'))
            all_logger.info('/firmware目录下现有如下文件:{}'.format(file_list))
            all_logger.info('开始复制文件到单独目录modify下')
            file_name = 'a-b.zip' if a_b else 'b-a.zip'
            for i in file_list:
                if i == file_name:
                    all_logger.info(i)
                    shutil.copy(os.path.join(os.getcwd(), 'firmware', i),
                                os.path.join(os.getcwd(), 'firmware', 'modify'))
            if os.path.exists(os.path.join(os.getcwd(), 'firmware', 'modify', file_name)):
                all_logger.info('复制文件成功')
            else:
                raise LinuxABSystemError('复制文件失败')

            # 解压差分包
            file_path = os.path.join(os.getcwd(), 'firmware', 'modify')
            for path, _, files in os.walk(file_path):
                for file in files:
                    if file.endswith('.zip'):
                        with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                            all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                            to_unzip.extractall(path)
            all_logger.info('解压固件成功')

            # 删除差分包原文件
            subprocess.getoutput('rm -rf {}/{}'.format(file_path, file_name))
            if not os.path.exists(os.path.join(os.getcwd(), 'firmware', 'modify', file_name)):
                all_logger.info('删除差分包原文件成功')
            else:
                return_value = subprocess.getoutput('ls {}'.format(file_path))
                raise LinuxABSystemError('删除差分包原文件失败:\r\n{}'.format(return_value))

            # 新增一个文件
            if mode == 'add':
                f_size = 10
                file_context = '1234567890' * 102 + '1234'  # 1024
                path = os.path.join(os.getcwd(), 'firmware', 'modify', str(f_size) + 'k.txt')
                with open(path, 'w') as f:
                    f.write(file_context * f_size)
                all_logger.info('新增一个文件成功')

            # 随机删除一个文件
            if mode == 'del':
                return_files = os.listdir(file_path)
                all_logger.info(return_files)
                raneom_num = random.randint(0, len(return_files))
                all_logger.info("随机删除{}文件".format(return_files[raneom_num]))
                all_logger.info('rm -rf {}/{}'.format(file_path, return_files[raneom_num]))
                subprocess.getoutput('rm -rf {}/{}'.format(file_path, return_files[raneom_num]))
                if not os.path.exists(os.path.join(os.getcwd(), 'firmware', 'modify', return_files[raneom_num])):
                    all_logger.info('随机删除文件成功')
                else:
                    return_value = subprocess.getoutput('ls {}'.format(file_path))
                    raise LinuxABSystemError('随机删除文件失败:\r\n{}'.format(return_value))

            # 再次压缩成修改后的固件包
            for path, _, files in os.walk(file_path):
                for file in files:
                    if not file.endswith('.zip'):
                        all_logger.info(file)
                        with ZipFile(os.path.join(file_path, file_name), 'a') as to_zip:
                            all_logger.info('zip {} to {}'.format(os.path.join(file_path, file),
                                                                  os.path.join(file_path, file_name)))
                            to_zip.write(os.path.join(file_path, file), file)
            all_logger.info('压缩固件成功')

        # 检查文件
        all_logger.info(file_name)
        if os.path.exists(os.path.join(os.getcwd(), 'firmware', 'modify', file_name)):
            all_logger.info('修改固件包准备成功')
        else:
            raise LinuxABSystemError(
                '修改固件包准备失败:\r\n{}'.format(os.listdir(os.path.join(os.getcwd(), 'firmware', 'modify'))))
        up_load_path = os.path.join(os.getcwd(), 'firmware', 'modify', file_name)

        # ADB上传到模块中
        # 先删除UFS下其他残留文件
        subprocess.getoutput('adb shell rm -rf /cache/ufs/*')

        package_md5 = hashlib.md5()
        with open(up_load_path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))

        for i in range(10):
            # subprocess.run('adb kill-server')
            adb_push = subprocess.getstatusoutput('adb push "{}" /cache/ufs'.format(up_load_path))
            all_logger.info(adb_push)
            if adb_push[0] != 0:
                continue
            md5 = subprocess.getoutput('adb shell md5sum /cache/ufs/{}'.format('a-b.zip' if a_b else "b-a.zip"))
            all_logger.info(md5)
            at_logger.info('adb get md5:{}'.format(md5))
            if package_md5 in md5:
                all_logger.info("MD5对比正常")
                time.sleep(5)
                return 'a-b.zip' if a_b else "b-a.zip"
            time.sleep(1)
        else:
            raise LinuxABSystemError("ADB PUSH升级包失败")

    @staticmethod
    def reboot_package_check(a_b=True):
        path = os.path.join(os.getcwd(), 'firmware', 'a-b.zip' if a_b else "b-a.zip")
        package_md5 = hashlib.md5()
        with open(path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))

        for i in range(10):
            # subprocess.run('adb kill-server')
            md5 = subprocess.getoutput('adb shell md5sum /cache/ufs/{}'.format('a-b.zip' if a_b else "b-a.zip"))
            all_logger.info(md5)
            at_logger.info('adb get md5:{}'.format(md5))
            if package_md5 in md5:
                all_logger.info("MD5对比正常")
                time.sleep(5)
                return True
            time.sleep(1)
        else:
            raise LinuxABSystemError("重启后检查USF版本包失败:".format(subprocess.getoutput('adb shell ls /cache/ufs')))

    @staticmethod
    def push_others(f_size=10):
        """
        上传指定大小的文件至UFS
        f_size : 大小，单位为kb
        """
        file_context = '1234567890' * 102 + '1234'  # 1024
        path = os.path.join(os.getcwd(), 'firmware', str(f_size) + 'k.txt')
        with open(path, 'w') as f:
            f.write(file_context * f_size)

        for i in range(10):
            time.sleep(1)
            # subprocess.run('adb kill-server')
            adb_push = subprocess.getstatusoutput('adb push "{}" /cache/ufs'.format(path))
            all_logger.info(adb_push)
            if adb_push[0] != 0:
                continue
            all_logger.info(
                "{}上传成功: ls /cache/ufs\r\n{}".format(path, subprocess.getoutput("adb shell ls -l /cache/ufs")))
            return str(f_size) + 'k.txt'
        else:
            raise LinuxABSystemError("adb push上传{}至UFS失败".format(path))

    def set_package_name(self, a_b=True):
        """
        AT+QABFOTA="package"  设置升级包名称
        """
        package_name = 'a-b.zip' if a_b else "b-a.zip"
        all_logger.info("设置版本包名称")
        self.at_handler.send_at('AT+QABFOTA="package","{}"'.format(package_name), 3)
        return_value = self.at_handler.send_at('AT+QABFOTA="package"', 3)
        all_logger.info("{}".format(return_value))
        if package_name not in return_value:
            raise LinuxABSystemError("设置版本包名称异常!")
        else:
            all_logger.info("设置版本包名称成功")

    def check_activeslot(self):
        """
        AT+QABFOTA="activeslot"  查询当前运行系统
        """
        all_logger.info("查询当前运行系统")
        return_value = self.at_handler.send_at('AT+QABFOTA="activeslot"', 3)
        key_system = ''.join(re.findall(r'\+QABFOTA: "activeslot",(\d)', return_value))
        all_logger.info("key_system:{}".format(key_system))
        if key_system == '0' or key_system == '1':
            all_logger.info("查询当前运行系统为{}!".format(self.start_sequence[key_system]))
            return key_system
        else:
            raise LinuxABSystemError("查询当前运行系统异常!{}".format(return_value))

    def query_state(self, state_module):
        """
        AT+QABFOTA="state"  查询升级状态
        """
        # all_logger.info("查询当前升级状态")
        return_value = self.at_handler.send_at('AT+QABFOTA="state"', 3)
        key_state = ''.join(re.findall(r'\+QABFOTA: "state",\w+ \((\d)\)', return_value))
        # all_logger.info("key_state:{}".format(key_state))
        if key_state in self.state_code.keys():
            # all_logger.info("查询当前升级状态为[{}],期望查询值为[{}]".format(self.state_code[key_state], self.state_code[state_module]))
            pass
        else:
            raise LinuxABSystemError("查询升级状态异常!{}".format(return_value))
        if state_module != key_state:
            raise LinuxABSystemError("state查询异常!查询值为{},于预期不符!预期为{}".format(key_state, state_module))
        else:
            all_logger.info("state查询正常, state: {}".format(key_state))

    def send_update(self):
        """
        AT+QABFOTA="update"  触发AB系统升级
        """
        all_logger.info("触发AB系统升级")
        self.at_handler.send_at('AT+QABFOTA="UPDATE"', 0.3)

    def ab_update_online(self, dfota_type, ufs_file, a_b=True, dl_stop=False, upgrade_stop=False, start=False,
                         end=False, dl_vbat=False, dl_cfun=False, check_dl_stop_file=False, get_part_file=False):
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
            fota_cmd.extend(['a-b.zip'])
        else:
            fota_cmd.extend(['b-a.zip'])
        fota_cmd = ''.join(fota_cmd)
        all_logger.info(fota_cmd)
        # step1

        if dl_cfun:  # 如果需要下载包过程断网
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.at_handler.send_at('AT+CFUN=0', 15)
            time.sleep(2)
            self.dfota_dl_package_701_702()
            time.sleep(2)
            self.at_handler.send_at("AT+CFUN=1", 15)
            time.sleep(5)
            if check_dl_stop_file:
                all_logger.info("下载包过程断网后UFS文件是否包含残缺文件")
                return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
                all_logger.info("{}".format(return_value_files))
                # 残缺文件名
                # filename_part = 'a-b' if a-b else 'b-a'
                filename_part = 'ipth_package.bin.dd'  # 有bug临时调试用
                if filename_part not in return_value_files:
                    raise LinuxABSystemError("下载包过程断网后UFS文件异常!\r\n{}\r\n{}".format(ufs_file, return_value_files))
                self.reboot_module()
                self.check_urc()
                time.sleep(3)
                all_logger.info("再次重启后检查文件是否缺失")
                return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
                all_logger.info("{}".format(return_value_files))
                for i in ufs_file:
                    if i not in return_value_files:
                        raise LinuxABSystemError(
                            "再次重启后UFS文件异常!用户文件丢失!\r\n{}\r\n{}".format(ufs_file, return_value_files))
                if filename_part in return_value_files:
                    raise LinuxABSystemError("再次重启后UFS文件异常!残缺文件仍然存在\r\n{}\r\n{}".format(ufs_file, return_value_files))
                return True
            time.sleep(2)
            self.at_handler.check_network()
            time.sleep(10)
        if get_part_file:  # 获取残包
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, True)
            time_start = time.time()
            value_return = ''
            while time.time() - time_start < 180:
                time.sleep(0.001)
                value_return = subprocess.getoutput("adb shell cat /run/abfota_wget.log")
                # 下载到一半时pull出来
                if '50%' in value_return:
                    all_logger.info(value_return)
                    filename_part = 'a-b.zip' if a_b else 'b-a.zip'
                    os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/modify')
                    file_path = os.path.join(os.getcwd(), 'firmware', 'modify')
                    subprocess.getoutput(
                        "adb pull /cache/ufs/ipth_package.bin.dd {}".format(os.path.join(file_path, filename_part)))
                    break
            else:
                value_return_cache = subprocess.getoutput("adb shell ls /cache/ufs/")
                raise LinuxABSystemError("180s内获取残缺包失败:\r\n{}\r\n{}".format(value_return, value_return_cache))
            self.at_handler.send_at("AT+CFUN=1", 15)
            time.sleep(5)
            return True
        if dl_vbat:
            self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, dl_stop)
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.check_urc()
            self.at_handler.check_network()
            time.sleep(10)
        self.dfota_ftp_http_https_step_1(dfota_type, fota_cmd, stop_download=False)

        if a_b:
            self.set_package_name(a_b=True)
            self.send_update()
        else:
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
        if upgrade_stop:  # 随机断电
            self.dfota_step_2()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
        if start:  # 在上报+QIND: "FOTA","START"时候断电
            self.dfota_step_2()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
        if end:  # 在上报+QIND: "ABFOTA","update", 100处断电
            self.dfota_step_2()
            all_logger.info("在ABFOTA update 100处断电")
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
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
        while time.time() - start_time < 900:
            time.sleep(1)
            try:
                self.query_state(state_module="0")
                break
            except Exception:
                pass
        # 升级重启后等待15min查询升级状态
        self.query_state(state_module="0")
        all_logger.info("升级完成!")

    def check_state_all_time(self, state_module):
        """
        一直查询，直到状态为期望值
        """
        all_logger.info("持续查询state直到出现期望值为[{}] ing...".format(self.state_code[state_module]))
        start_time = time.time()
        while time.time() - start_time < 900:
            time.sleep(1)
            try:
                self.query_state(state_module=state_module)
                break
            except Exception:
                self.driver.check_usb_driver()  # 检测是否发生dump了
                pass
        else:
            raise LinuxABSystemError("900s内未查询到{}状态".format(state_module))

    def check_backup(self, a_version=True):
        """
        查询是否出现同步状态、若没有、全擦升级并结束测试
        """
        start_time = time.time()
        while time.time() - start_time < 900:
            time.sleep(1)
            try:
                self.query_state(state_module='2')
                break
            except Exception:
                self.driver.check_usb_driver()  # 检测是否发生dump了
                pass
        else:
            raise LinuxABSystemError("900s内未查询到同步状态!")

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

    def ab_update_local(self, ufs_file, a_b=True, upgrade_stop=False, delete_package=False,
                        delete_package_and_reboot=False, send_again=False, backup_reboot=False):
        system_before = self.check_activeslot()
        all_logger.info("system_before:{}".format(system_before))
        if a_b:
            self.set_package_name(a_b=True)
        else:
            self.set_package_name(a_b=False)
        time.sleep(5)
        self.send_update()

        # step2
        if upgrade_stop:  # 随机断电
            self.dfota_step_2(upgrade_stop=True)
            self.reboot_module()
            self.check_urc()
            time.sleep(3)
            all_logger.info("随机断电重启后UFS文件是否缺失")
            return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
            all_logger.info("{}".format(return_value_files))
            for i in ufs_file:
                if i not in return_value_files:
                    raise LinuxABSystemError("随机断电重启后UFS文件异常!\r\n{}\r\n{}".format(ufs_file, return_value_files))
        if delete_package:  # 升级过程中删除升级包
            self.dfota_step_2(delete_package=True, a_b=a_b)
            self.driver.check_usb_driver()
            self.check_state_all_time(state_module='5')
            self.check_state_all_time(state_module='0')
            self.push_package_and_check(a_b)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=a_b)
            return True
        if delete_package_and_reboot:  # 升级过程中删除升级包并重启模块
            self.dfota_step_2(delete_package=True, a_b=a_b)
            self.reboot_module()
            self.check_state_all_time(state_module='5')
            self.check_state_all_time(state_module='0')
            time.sleep(5)
            system_before = self.check_activeslot()
            self.eblock(block='b_system' if system_before == '1' else 'system')
            self.reboot_module()
            self.check_urc()
            time.sleep(5)
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after != system_before:
                all_logger.info("重启后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError(
                    "重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            return True
        """
        if send_again:  # 升级过程中再次发送升级命令
            self.dfota_step_2(send_again=True)

            try:
                self.dfota_step_2(send_again=True)
            except Exception as e:
                msg = traceback.format_exc()
                all_logger.info("升级失败信息msg: {}".format(msg))
            if 'error' in msg:
                all_logger.info("指令返回error,和预期一致!")
            else:
                all_logger.info("异常!未出现预期指令返回error现象!")
        """
        # 正常升级
        if send_again:
            self.dfota_step_2(send_again=True)
        elif upgrade_stop:
            self.dfota_step_2(continu_update=True)
        else:
            self.dfota_step_2()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()
        time.sleep(5)
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
        if backup_reboot:
            all_logger.info("开始同步过程中断电")
            self.reboot_module()
            self.check_urc()
            time.sleep(3)
            all_logger.info("备份过程中断电重启后UFS文件是否缺失")
            return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
            all_logger.info("{}".format(return_value_files))
            for i in ufs_file:
                if i not in return_value_files:
                    raise LinuxABSystemError("随机断电重启后UFS文件异常!\r\n{}\r\n{}".format(ufs_file, return_value_files))
            self.query_state(state_module="2")
        start_time = time.time()
        while time.time() - start_time < 600:
            time.sleep(1)
            try:
                self.query_state(state_module="0")
                break
            except Exception:
                pass
        # 升级重启后等待10min查询升级状态
        self.query_state(state_module="0")
        return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
        all_logger.info("{}".format(return_value_files))
        all_logger.info("升级完成!")

    def ab_update(self, ufs_file, a_b=True, query_mode=True):
        """
        AT+QABFOTA="UPDATE"  触发AB系统升级
        ufs_file:不包含fota包
        ufs_file2:包含fota包
        """
        # 升级前查询CPU情况
        all_logger.info("升级前查询CPU情况")
        self.query_modem_cpu_status(query_mode=query_mode, cpu_min=95, times=3)
        all_logger.info("开始触发AB系统升级")
        system_before = self.check_activeslot()
        all_logger.info("system_before:{}".format(system_before))
        self.send_update()
        time_update_use = self.dfota_step_2(query_mode=query_mode)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()
        time.sleep(3)
        all_logger.info("检查升级后升级状态是否正确")
        self.query_state(state_module="2")
        # 升级后查询CPU状态
        all_logger.info("升级后查询CPU状态")
        self.query_modem_cpu_status(query_mode=query_mode, cpu_min=70, cpu_max=90, times=3)
        # 等待文件
        time.sleep(60)
        all_logger.info("检查升级后UFS文件是否缺失")
        return_value_files = self.at_handler.send_at('AT+QFLST="*"', 3)
        all_logger.info("{}".format(return_value_files))
        for i in ufs_file:
            if i not in return_value_files:
                raise LinuxABSystemError("检查升级后UFS文件异常!\r\n{}\r\n{}".format(ufs_file, return_value_files))
        # 检查是否存在tmpupdate文件
        if "tmpupdate" not in return_value_files:
            all_logger.info("检查升级后UFS文件异常!不存在tmpupdate文件\r\n{}".format(return_value_files))
        all_logger.info("升级后运行系统查询")
        system_after = self.check_activeslot()
        if system_after != system_before:
            all_logger.info("升级后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
        else:
            raise LinuxABSystemError(
                "升级后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
        # 升级后信息查询
        if a_b:
            self.dfota_a_b_upgrade_check()
        else:
            self.dfota_b_a_upgrade_check()
        # 升级重启后查询升级状态
        self.query_state(state_module="2")
        start_time = time.time()
        time_backup_use = ''
        all_logger.info("持续查询当前升级状态ling")
        while time.time() - start_time < 600:
            time.sleep(1)
            try:
                self.query_state(state_module="0")
                time_backup_use = time.time() - start_time + 63  # 加上之前的sleep时间
                break
            except Exception:
                pass
        all_logger.info("time_backup_use:{}".format(str(time_backup_use)))
        # 备份完成查询升级状态
        self.query_state(state_module="0")
        # 备份完成检查文件
        file_name = 'a-b.zip' if a_b else "b-a.zip"
        ufs_file.remove(file_name)
        return_value_files2 = self.at_handler.send_at('AT+QFLST="*"', 3)
        for i in ufs_file:
            if i not in return_value_files2:
                raise LinuxABSystemError("检查升级后UFS文件异常!\r\n{}\r\n{}".format(ufs_file, return_value_files2))
        all_logger.info("升级完成!")
        time.sleep(5)
        # 备份完成查询CPU状态
        all_logger.info("备份完成查询CPU状态")
        self.query_modem_cpu_status(query_mode=query_mode, cpu_min=95, times=3)
        return time_backup_use, time_update_use

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

    def check_ab_update_urc(self):
        """
        AT+QABFOTA="UPDATE"  触发AB系统升级后检测URC上报
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
                    if '+QABFOTA: "update",100' in at_port_data:
                        time.sleep(1)  #  等待1s，尝试避免Device or resource busy
                        return True

    @staticmethod
    def readline(port):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值:
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
                # +QIND: "ABFOTA","HTTP START"
                check_msg = '+QIND: "ABFOTA","{}START"'.format(check_fragment)
                if check_msg in recv:
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
            # 检查 "ABFOTA","FTPEND",0 "ABFOTA","HTTPEND",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                if recv != '':
                    at_logger.info("{}".format(recv))
                recv_regex = ''.join(re.findall(r'\+QIND:\s"ABFOTA","{}END",(\d+)'.format(check_fragment), recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}".format(recv))
                        return True
                    else:
                        raise LinuxABSystemError("ABFOTA下载差分包异常: {}".format(recv))
                if time.time() - start_time > 300:
                    raise LinuxABSystemError("ABFOTA下载差分包超过300S异常")

    # @watchdog("检测701异常")
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

    def dfota_step_2(self, upgrade_stop=False, delete_package=False, query_mode=True, continu_update=False,
                     send_again=False, a_b=True):
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
        time_update_use = ''
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
            at_port.write(f'AT+QABFOTA="state"\r\n'.encode('utf-8'))
            at_logger.info('Send: {}'.format(f'AT+QABFOTA="state"'))
            # self.query_state(state_module="1")
            # 检查 "ABFOTA","update",100

            # 如果升级过程中再次发送升级命令
            if send_again:
                all_logger.info("再次发送升级命令")
                time.sleep(2)
                at_port.write(f'AT+QABFOTA="UPDATE"\r\n'.encode('utf-8'))
                all_logger.info('Send: {}'.format(f'AT+QABFOTA="UPDATE"'))
            start_time = time.time()
            time_delete = 0
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
                if delete_flag:
                    time_delete = time_delete + 1
                    if time_delete > 3000:
                        all_logger.info("异常!删除升级包3s内未检测到升级状态异常URC上报")
                        return True
                        # raise LinuxABSystemError("异常!删除升级包3s内未检测到升级状态异常URC上报")
                    else:
                        pass
                if '+QABFOTA: "UPDATE"' in recv:
                    recv_regex = ''.join(re.findall(r'\++QABFOTA:\s"UPDATE",(\d+)', recv))
                    if recv_regex:
                        if recv_regex == '100':
                            at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                            time_update_use = time.time() - start_time
                            all_logger.info("time_update_use:{}".format(str(time_update_use)))
                            return time_update_use
                        elif recv_regex == '55':
                            # 升级中查询CPU状态
                            all_logger.info("升级中查询CPU状态")
                            self.query_modem_cpu_status(query_mode=query_mode, cpu_max=1, cpu_min=0, times=3)
                        elif recv_regex == '44':
                            # 如果需要升级过程中删除升级包
                            if delete_package:
                                if a_b:
                                    at_port.write(f'AT+QFDEL="UFS:a-b.zip"\r\n'.encode('utf-8'))
                                    at_logger.info('Send: {}'.format(f'AT+QFDEL="UFS:a-b.zip"'))
                                else:
                                    at_port.write(f'AT+QFDEL="UFS:b-a.zip"\r\n'.encode('utf-8'))
                                    at_logger.info('Send: {}'.format(f'AT+QFDEL="UFS:b-a.zip"'))
                                delete_flag = True
                            else:
                                pass
                        else:
                            pass
                    if time.time() - start_time > 300:
                        raise LinuxABSystemError("ABFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise LinuxABSystemError('未检测到ABFOTA上报+QIND: "ABFOTA","UPDATE",11')

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
            raise LinuxABSystemError('版本包获取失败')

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
        os.popen('mount -t cifs {} /mnt/cur -o user="jeckson.yin@quectel.com",password="Admin@1234567"'.format(
            cur_package_path)).read()
        os.popen('mount -t cifs {} /mnt/prev -o user="jeckson.yin@quectel.com",password="Admin@1234567"'.format(
            prev_package_path)).read()
        if os.listdir('/mnt/cur') and os.listdir('/mnt/prev'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise LinuxABSystemError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    def unmatch_mount_package(self):
        """
        挂载版本包
        :return:
        """
        unmatch_firmware_path = self.unmatch_firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'unmatch' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/unmatch')
        os.popen('mount -t cifs {} /mnt/unmatch -o user="jeckson.yin@quectel.com",password="Admin@1234567"'.format(
            unmatch_firmware_path)).read()
        if os.listdir('/mnt/unmatch'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise LinuxABSystemError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def unmatch_ubuntu_copy_file():
        """
        Ubuntu下复制版本包
        :return:
        """
        os.mkdir(os.path.join(os.getcwd(), 'firmware') + '/unmatch')

        unmatch_file_list = os.listdir('/mnt/unmatch')
        all_logger.info('/mnt/unmatch目录下现有如下文件:{}'.format(unmatch_file_list))
        all_logger.info('开始复制unmatch版本版本包到本地')
        for i in unmatch_file_list:
            shutil.copy(os.path.join('/mnt/unmatch', i), os.path.join(os.getcwd(), 'firmware', 'unmatch'))

        if os.path.join(os.getcwd(), 'firmware', 'unmatch'):
            all_logger.info('unmatch版本获取成功')
        else:
            raise LinuxABSystemError('unmatch版本包获取失败')

    @staticmethod
    def unmatch_unzip_firmware():
        """
        解压当前路径 + firmware + unmatch路径下面的所有zip包
        :return: None
        """
        firmware_path = os.path.join(os.getcwd(), 'firmware', 'unmatch')
        for path, _, files in os.walk(firmware_path):
            for file in files:
                if file.endswith('.zip'):
                    all_logger.info(file)
                    with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                        all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                        to_unzip.extractall(path)
        all_logger.info('解压固件成功')

    def unmatch_make_dfota_package(self, factory):
        """
        查找当前路径 + firmware + unmatch/cur路径下面zip，然后制作差分包。
        :return: None
        """
        all_logger.info("开始制作差分包")
        orig_target_file = ''
        cur_target_file = ''
        old_zip_path = os.getcwd() + r'/firmware/unmatch'
        new_zip_path = os.getcwd() + r'/firmware/cur'
        if factory:
            if os.path.exists(os.path.join(old_zip_path, self.unmatch_name_sub_version + '_factory.zip')):
                orig_target_file = os.path.join(old_zip_path, self.unmatch_name_sub_version + '_factory.zip')
                all_logger.info("unmatch版本工厂包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取unmatch版本工厂包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')
                all_logger.info("当前版本工厂包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise LinuxABSystemError("获取当前版本工厂包名称失败")

        else:
            if os.path.exists(os.path.join(old_zip_path, self.unmatch_name_sub_version + '.zip')):
                orig_target_file = os.path.join(old_zip_path, self.unmatch_name_sub_version + '.zip')
                all_logger.info("unmatch版本标准包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise LinuxABSystemError("获取unmatch版本标准包名称失败")

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
        elif '4' in oc_num_key:
            oc_key = '4'
            all_logger.info("当前flash为 4+4")
        else:
            all_logger.info(self.oc_num)
            raise LinuxABSystemError('请检查resouce参数dev_oc_num是否填写正确')
        all_logger.info("oc_key: {}".format(oc_key))

        multi_thread_merge_SDX6X_AB_gentools(orig_target_file, cur_target_file, self.unmatch_name_sub_version,
                                             self.name_sub_version, module_id, oc_key, unmatch_version=True)

    @staticmethod
    def unmatch_push_package_and_check(a_b=True):
        path = os.path.join(os.getcwd(), 'firmware', 'unmatch', 'a-b.zip' if a_b else "b-a.zip")
        package_md5 = hashlib.md5()
        with open(path, 'rb') as f:
            package_md5.update(f.read())
        package_md5 = package_md5.hexdigest()
        all_logger.info("package_md5: {}".format(package_md5))

        for i in range(10):
            # subprocess.run('adb kill-server')
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
                return 'a-b.zip' if a_b else "b-a.zip"
            time.sleep(1)
        else:
            raise LinuxABSystemError("ADB PUSH升级包失败")
