import glob
import re
import os
import time
from collections import defaultdict
import serial.tools.list_ports
import shutil
import getpass
import subprocess
import zipfile
from subprocess import PIPE, STDOUT
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle
from utils.functions.gpio import GPIO
import concurrent.futures
from utils.exception.exceptions import FatalError
from utils.log import log
from utils.functions.driver_check import DriverChecker
import pickle


class QFILError(Exception):
    """QFIL工具升级异常"""


class QFIL:

    QFIL_EXTRA_PARAMS = ' --noprompt --showpercentagecomplete --zlpawarehost=1 --memoryname=nand'

    def __init__(self, *, at_port, dm_port, firmware_path, factory, ati, csub, **kwargs):
        self.erase = True if factory else False
        self.factory = factory
        self.at_port = at_port
        self.dm_port = dm_port
        self.ati = ati
        self.csub = csub
        self.firmware_path = firmware_path
        self.qfil_path = self.get_qfil_path()  # QFIL安装的路径
        self.local_firmware_path = ''  # 下载的升级包路径
        self.local_firmware_firehose_path = ''  # 下载的升级包的firehose路径
        self.mbn_name = ''  # 下载的升级包中的mbn的名称，用于项目兼容
        self.dl_port = ''  # 紧急下载口编号
        self.at_handle = ATHandle(self.at_port)
        self.driver_check = DriverChecker(self.at_port, self.dm_port)
        self.gpio = GPIO()
        # 处理传入的其他参数，例如IMEI和SN，在StartupManager类中可以找到
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        return self.__dict__.get(item, '')

    def factory_to_standard(self):
        """
        如果只实例化了一个QFIL对象，如果想先升级工厂，再升级标准，不用多次实例化QFIL。
        需要调用此函数修改内部一些参数，参照startup_manager.py的upgrade函数。
        :return: None
        """
        self.factory = False
        self.erase = False

    @staticmethod
    def get_qfil_path():
        """
        获取QFIL的path，用于之后复制QSaharaServer.exe和fh_loader.exe.
        :return: None
        """
        all_logger.info("获取本机QFIL安装路径")
        qfil_possible_path = [r'C:\Program Files (x86)\Qualcomm', r'C:\Program Files\Qualcomm']
        qfil_path = ''
        for p in qfil_possible_path:
            for path, _, files in os.walk(p):
                if 'fh_loader.exe' in files and 'QSaharaServer.exe' in files:
                    qfil_path = path
        if qfil_path:
            all_logger.info(f"本机QFIL的安装路径为: {qfil_path}")
            return qfil_path
        else:
            raise QFILError("请确认QFIL工具是否安装和QFIL工具是否是默认安装路径，{}路径中未找到相关文件".format('和'.join(qfil_possible_path)))

    def ports(self):
        """
        根据模块的AT口，DM口反查NEMA和MODEM口。
        :return: 当前模块的端口列表，如果异常，返回QFILError
        """
        all_logger.info("获取Windows端所有端口的对应状态")
        cur_ports = defaultdict(list)
        for num, _, info in serial.tools.list_ports.comports():
            ser = ''.join(re.findall(r'SER=(\S+)', info))
            cur_ports[ser].append(num)
        all_logger.info(f"当前端口列表状态：{cur_ports}")

        all_logger.info("获取当前模块的所有COM口")
        for _, p in cur_ports.items():
            if self.at_port in p and self.dm_port in p:
                all_logger.info(f"当前模块的所有COM口为：{p}")
                return p
        else:
            raise QFILError(f"获取模块对应所有COM口失败，AT口：{self.at_port}，DM口：{self.dm_port}，不同时在 {cur_ports} 中")

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

    @staticmethod
    def get_download_port():
        """
        获取紧急下载口
        :return: 紧急下载口，或者空
        """
        for port in serial.tools.list_ports.comports():
            if port.pid == 36872:  # 36872的16进制是9008
                return port.name
        return ''

    def switch_edl_mode(self):
        """
        切换EDL mode
        :return: None
        """
        # 转到下载口
        dl_port = ''
        for i in range(3):
            all_logger.info("切换紧急下载口")
            try:
                with serial.Serial(self.dm_port, baudrate=115200, timeout=0.8, write_timeout=10) as s:  # 此处加入write_timeout
                    all_logger.debug("写入切换紧急下载口命令")
                    s.write(bytes.fromhex('4b650100540f7e'))
            except Exception as e:
                all_logger.error(f"切换紧急口写入超时：{e}")
            start = time.time()
            while not dl_port and time.time() - start < 30:
                time.sleep(1)
                all_logger.info(f'{int(time.time() - start)}S')
                dl_port = self.get_download_port()
            if dl_port:
                all_logger.info('wait 10 seconds')
                time.sleep(10)
                self.dl_port = dl_port
                break
        else:
            raise QFILError("切换紧急下载口失败")

    @staticmethod
    def safe_listdir(directory, timeout):
        pool = concurrent.futures.ThreadPoolExecutor()

        for i in range(3):
            future = pool.submit(os.listdir, directory)
            try:
                return future.result(timeout)
            except concurrent.futures.TimeoutError:
                time.sleep(10)
                continue
        else:
            raise FatalError(f"连续三次获取{directory}目录内容失败")

    def copy_and_unzip_firmware(self):
        """
        复制解压版本包。
        :return: None
        """
        all_logger.info("复制解压版本包")
        # 获取工厂包和标准包
        remote_files = self.safe_listdir(self.firmware_path, 3)  # 为了防止os.listdir()阻塞，使用concurrent
        all_logger.info(f"远程路径总文件列表：{remote_files}")
        factory_firmware = ''.join([i for i in remote_files if i.endswith('factory.zip')])
        standard_firmware = ''.join([i for i in remote_files if i.endswith('.zip') and not i.endswith('factory.zip') and len(i.strip(".zip")) > 10])  # zip结尾，并且不是factory.zip结尾，并且名字大于10位，例如RG500QEAAA是10位，大于10位
        all_logger.info(f"工厂包：{factory_firmware}")
        all_logger.info(f"标准包：{standard_firmware}")

        # 判断本地版本包是否存在
        local_path = os.path.join('C:\\', 'Users', getpass.getuser(), 'TWS_TEST_DATA', 'PackPath') if os.name == 'nt' else \
            os.path.join('/root', 'TWS_TEST_DATA', "PackPath")
        local_zip_firmware_path = os.path.join(local_path, factory_firmware if self.factory else standard_firmware)
        self.local_firmware_path = local_zip_firmware_path.strip(".zip")
        all_logger.info(f"版本包已存在: {local_zip_firmware_path}" if os.path.exists(local_zip_firmware_path) else "版本包不存在")
        all_logger.info(f"版本包已解压: {self.local_firmware_path}" if os.path.exists(self.local_firmware_path) else "版本包未解压")

        # 检查共享文件夹，查看是否是CI版本(devops)，如果是，检查路径下存在几个版本文件夹，可能存在beta版本升V导致升级后版本校验失败的问题，需要重新下载版本包
        force_download_flag = False
        if 'devops' in self.firmware_path:
            remote_dir_len = len(os.listdir(os.path.abspath(os.path.dirname(self.firmware_path))))
            if remote_dir_len > 1:      # 如果CI版本包路径下文件数量大于1，代表beta版本升V，需要重新下载版本包
                all_logger.info('当前beta版本可能升V，重新下载版本包')
                force_download_flag = True

        if not os.path.exists(local_zip_firmware_path) or force_download_flag:  # 下载版本包
            all_logger.info("开始下载工厂包" if self.factory else "开始下载标准包")
            remote_path = os.path.join(self.firmware_path, factory_firmware if self.factory else standard_firmware)
            if os.path.exists(local_path) is False:
                os.mkdir(local_path)
            all_logger.info(fr"shutil.copy({remote_path}, {local_path})")
            shutil.copy(remote_path, local_path)

        try:
            if not os.path.exists(self.local_firmware_path) or force_download_flag:  # 解压版本包
                all_logger.info("开始解压工厂包" if self.factory else "开始解压标准包")
                with zipfile.ZipFile(local_zip_firmware_path, 'r') as to_unzip:
                    to_unzip.extractall(self.local_firmware_path)
        except Exception as e:
            all_logger.info(e)
            os.popen(f'del /F /S /Q "{local_zip_firmware_path}"').read()     # 如果解压失败首先删除压缩包
            all_logger.info('版本包解压失败')
            raise QFILError('版本包解压失败')
        all_logger.info('解压固件成功')
        return True

    def get_firmware_firehose_path(self):
        """
        获取升级包中update/firehose路径的位置。
        :return: None
        """
        for path, dirs, files in os.walk(self.local_firmware_path):
            for file in files:
                if file.startswith('prog_firehose_'):
                    self.local_firmware_firehose_path = path
                    self.mbn_name = file
                    all_logger.info(f"版本包firehose文件夹的路径为: {self.local_firmware_firehose_path}")
                    all_logger.info(f"版本包firehose文件夹的mbn名称为: {self.mbn_name}")
                    break
        if not self.local_firmware_firehose_path:
            raise QFILError("下载的升级包中为发现firehose文件夹，请检查当前升级的版本包和项目升级方式")

    def copy_qsaharaserver_and_fhloader(self):  # noqa
        """
        复制QFIL安装目录的QSaharaServer.exe和fh_loader.exe到版本包的update，firehose目录
        :return:
        """
        self.get_firmware_firehose_path()
        qsaharaserver_path = os.path.join(self.qfil_path, 'QSaharaServer.exe')  # noqa
        fh_loader_path = os.path.join(self.qfil_path, 'fh_loader.exe')
        all_logger.info("复制QSaharaServer.exe和fh_loader.exe到firehose文件夹")
        if not os.path.exists(os.path.join(self.local_firmware_firehose_path, "QSaharaServer.exe")):
            shutil.copy(qsaharaserver_path, self.local_firmware_firehose_path)
        if not os.path.exists(os.path.join(self.local_firmware_firehose_path, "fh_loader.exe")):
            shutil.copy(fh_loader_path, self.local_firmware_firehose_path)

    @staticmethod
    def upgrade_subprocess_wrapper(*, cmd, cwd, timeout, check_message='All Finished Successfully', error_message):
        """
        升级的依赖函数
        :param cmd: 命令
        :param cwd: 当前工作路径
        :param timeout: 超时时间
        :param check_message: 检查的信息
        :param error_message: 需要返回的异常信息
        :return: None
        """
        s = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=PIPE, stderr=STDOUT, text=True)
        try:
            outs, err = s.communicate(timeout=timeout)
            all_logger.info(outs)
            if check_message not in outs:
                all_logger.error(outs)
                raise QFILError(error_message)
        except subprocess.TimeoutExpired:
            s.terminate()
            outs, err = s.communicate()
            all_logger.error(outs)
            raise QFILError(error_message)

    def load_programmer(self):
        """
        升级的第一步。
        :return:
        """
        all_logger.info("加载QSaharaServer")
        load_programmer = fr'QSaharaServer.exe -s 13:{self.mbn_name} -p \\.\{self.dl_port}'
        all_logger.info(load_programmer)
        self.upgrade_subprocess_wrapper(
            cmd=load_programmer,
            cwd=self.local_firmware_firehose_path,
            timeout=30,
            check_message='Sahara protocol completed',
            error_message='QSaharaServer指令返回值异常，请检查Log'
        )
        all_logger.info('等待5S')
        time.sleep(5)

    def erase_with_xml(self):
        """
        使用生成的XML文件进行全擦，貌似没用？
        :return: None
        """
        all_logger.info("使用XML文件方式进行全擦")
        with open(os.path.join(self.local_firmware_firehose_path, 'erase.xml'), 'w') as f:
            f.write('<?xml version="1.0"?>\n<data>\n  <erase physical_partition_number="0" start_sector="0" />\n</data>')
        erase_xml = fr'fh_loader.exe --port=\\.\{self.dl_port} --sendxml=erase.xml --search_path={self.local_firmware_firehose_path} {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(erase_xml)
        self.upgrade_subprocess_wrapper(
            cmd=erase_xml,
            cwd=self.local_firmware_firehose_path,
            timeout=30,
            error_message='XML方式flash全擦失败，请检查Log'
        )

    def erase_all(self):
        """
        从地址0全擦
        :return: None
        """
        all_logger.info("Flash全擦")
        erase_0 = fr'fh_loader.exe --port=\\.\{self.dl_port} --erase=0 {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(erase_0)
        self.upgrade_subprocess_wrapper(
            cmd=erase_0,
            cwd=self.local_firmware_firehose_path,
            timeout=30,
            error_message='Flash全擦异常，请检查Log'
        )

    def load_package(self):
        """
        下载版本包到模块。
        :return:
        """
        all_logger.info("下载版本包到模块")
        rawprogram_file = 'rawprogram_nand_p4K_b256K_factory.xml' if self.factory else 'rawprogram_nand_p4K_b256K_update.xml'
        all_in_one = fr'fh_loader.exe --port=\\.\{self.dl_port} --sendxml={rawprogram_file} --search_path={self.local_firmware_firehose_path} {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(all_in_one)
        self.upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=self.local_firmware_firehose_path,
            timeout=180,
            error_message='下载版本包到模块异常，请检查Log'
        )

    def load_patch(self):
        """
        下载Patch到模块。
        :return: None
        """
        all_logger.info("下载patch到模块")
        all_in_one = fr'fh_loader.exe --port=\\.\{self.dl_port} --sendxml=patch_p4K_b256K.xml --search_path={self.local_firmware_firehose_path} {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(all_in_one)
        self.upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=self.local_firmware_firehose_path,
            timeout=180,
            error_message='下载patch到模块异常，请检查Log'
        )

    def set_start_partition(self):
        """
        升级完成后，需要设置启动分区为0。
        :return: None
        """
        all_logger.info("设置启动分区为0")
        all_in_one = fr'fh_loader.exe --port=\\.\{self.dl_port} --setactivepartition=0 {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(all_in_one)
        self.upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=self.local_firmware_firehose_path,
            timeout=180,
            error_message='设置启动分区为0异常，请检查Log'
        )

    def reset_module(self):
        """
        升级完成后，使用Reset重启模块
        :return: None
        """
        all_logger.info("重启模块")
        all_in_one = fr'fh_loader.exe --port=\\.\{self.dl_port} --reset {self.QFIL_EXTRA_PARAMS}'
        all_logger.info(all_in_one)
        self.upgrade_subprocess_wrapper(
            cmd=all_in_one,
            cwd=self.local_firmware_firehose_path,
            timeout=180,
            error_message='重启模块异常，请检查Log'
        )

    def check_port_load(self, ports):
        """
        检查模块是否正常开机
        :param ports: 升级前的端口列表
        :return: None
        """
        start = time.time()
        while time.time() - start < 180:
            port_list = self.get_port_list()
            if set(ports).issubset(set(port_list)):
                all_logger.info("模块已正常开机")
                break
            time.sleep(1)
        else:
            all_logger.error(f"模块未正常开机或模块开机后端口列表变化：\n期望端口列表包含：{ports}\n当前端口列表：{self.get_port_list()}")

    def qfil(self):
        before_upgrade_ports = self.ports()  # 获取端口列表
        for i in range(3):
            try:
                if self.copy_and_unzip_firmware():  # 下载解压固件
                    break
            except Exception as e:
                all_logger.info(e)
        else:
            raise QFILError('三次下载解压固件失败')
        self.copy_qsaharaserver_and_fhloader()  # 复制QSaharaServer.exe和fh_loader.exe到版本包路径，便于后续处理
        self.switch_edl_mode()  # 切换紧急下载模式

        self.load_programmer()  # QSaharaServer.exe load programmer
        if self.erase:  # erase all flash
            self.erase_with_xml()
            self.erase_all()

        self.load_package()  # 升级
        self.load_patch()
        self.set_start_partition()
        self.reset_module()  # 重启

        self.check_port_load(before_upgrade_ports)  # 检查升级前的口是否都在升级后的端口列表中

        # kill 删除升级程序
        self.kill_and_del_upgrade_tools()

        all_logger.info("检测PB DONE上报")
        try:
            self.at_handle.readline_keyword('PB DONE', timout=60)   # 升级完成后检测PB DONE上报
        except Exception:   # noqa
            pass

        self.check_module_version()  # 检查当前版本

        # 如果工厂版本，进行QCN的恢复
        if self.factory and getattr(self, 'sn', '') != '':  # 如果是正常的测试会使用check_module_version->restore_imei_sn_and_ect设置SN的值，如果SN有值，则进行QCN恢复
            restore_status = log.restore_qcn(self.sn)
            if restore_status is True:  # 如果需要进行QCN备份
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()

                all_logger.info("检测PB DONE上报")
                try:
                    self.at_handle.readline_keyword('PB DONE', timout=60)   # 升级完成后检测PB DONE上报
                except Exception:   # noqa
                    pass

    def qfil_edl(self):
        self.factory = True
        self.erase = True
        self.gpio.set_pwk_low_level()  # RM模块紧急下载模式，尝试重启后还是紧急下载模式，需要pwk电平置低，否则升级失败

        for i in range(3):
            try:
                if self.copy_and_unzip_firmware():  # 下载解压固件
                    break
            except Exception as e:
                all_logger.info(e)
        else:
            raise QFILError('三次下载解压固件失败')
        self.copy_qsaharaserver_and_fhloader()  # 复制QSaharaServer.exe和fh_loader.exe到版本包路径，便于后续处理
        self.dl_port = self.get_download_port()

        self.load_programmer()  # QSaharaServer.exe load programmer
        if self.erase:  # erase all flash
            self.erase_with_xml()
            self.erase_all()

        self.load_package()  # 升级
        self.load_patch()
        self.set_start_partition()
        self.reset_module()  # 重启

        # 控制VBAT重启，因为上面pwk设置了低电平
        self.gpio.set_vbat_high_level()
        self.gpio.set_vbat_low_level_and_pwk()

        # kill 删除升级程序
        self.kill_and_del_upgrade_tools()

        port_list = [self.at_port, self.dm_port]
        self.check_port_load(port_list)

        all_logger.info("等待30S")
        time.sleep(30)

        self.check_module_version()  # 检查当前版本

    def check_module_version(self):
        """
        检查版本信息是否正确
        :return:
        """
        all_logger.info("检查升级后的版本信息")
        self.at_handle.send_at('ATE', 3)
        for i in range(10):
            try:
                # 版本号
                return_value = self.at_handle.send_at('ATI+CSUB', 0.6)
                revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
                sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
                if revision == self.ati and sub_edition == self.csub.replace('-', ''):
                    all_logger.info(f"版本号：ATI: {self.ati}, CSUB: {self.csub.replace('-', '')} 检查成功")
                    break
            except Exception as e:
                all_logger.error(e)
            time.sleep(1)
        else:
            raise QFILError("升级后版本号检查异常")

        # 如果是升级的factory版本，恢复SN等相关信息
        if self.factory:
            self.restore_imei_sn_and_ect()

    def kill_and_del_upgrade_tools(self):
        s = subprocess.getoutput('taskkill /f /t /im fh_loader.exe')
        all_logger.info(f'taskkill /f /t /im fh_loader.exe : {s}')
        s = subprocess.getoutput('taskkill /f /t /im QSaharaServer.exe')
        all_logger.info(f'taskkill /f /t /im QSaharaServer.exe : {s}')
        s = subprocess.getoutput(f"del /f {os.path.join(self.local_firmware_firehose_path, 'fh_loader.exe')}")
        all_logger.info(f"del /f {os.path.join(self.local_firmware_firehose_path, 'fh_loader.exe')} : {repr(s)}")
        s = subprocess.getoutput(f"del /f {os.path.join(self.local_firmware_firehose_path, 'QSaharaServer.exe')}")
        all_logger.info(f"del /f {os.path.join(self.local_firmware_firehose_path, 'QSaharaServer.exe')} : {repr(s)}")
        s = subprocess.getoutput(f"del /f {os.path.join(self.local_firmware_firehose_path, 'erase.xml')}")
        all_logger.info(f"del /f {os.path.join(self.local_firmware_firehose_path, 'erase.xml')} : {repr(s)}")

    @staticmethod
    def pause(info="保留现场，问题定位完成后请直接关闭脚本"):
        """
        暂停当前脚本
        :return: None
        """
        print(info, end='')
        while True:
            import sys
            line = sys.stdin.readline()
            line = line.rstrip()  # 去掉sys.stdin.readline最后的\n
            if line.upper() == 'E':
                exit()
            elif line.upper() == 'C':
                break
            else:
                print("如有需要输入C后按ENTER继续(大部分脚本不支持): ", end='')

    def check_cgdcont(self):
        mbn_status = self.at_handle.send_at('at+qmbncfg="List"', timeout=15)
        operator = self.at_handle.get_operator()
        if operator == "CMCC":
            mbn = ''.join(re.findall('.*CMCC', mbn_status))
            if '1,1' not in mbn:
                self.pause()
        elif operator == "中国联通":
            mbn = ''.join(re.findall('.*CU', mbn_status))
            if '1,1' not in mbn:
                self.pause()
        else:
            mbn = ''.join(re.findall('.*CT', mbn_status))
            if '1,1' not in mbn:
                self.pause()

    def restore_imei_sn_and_ect(self):
        """
        当我们升级工厂版本后，会将Resource(https://tws.quectel.com:8152/Cluster/Device)节点中的IMEI Number写入IMEI1，SN写入。
        其中分为两种情况：
        1. 如果是在utils.cases.startup_manager的StartupManager中调用升级动作，无法获取IMEI和SN，需要通过device_id进行反查
            https://ticket.quectel.com/browse/ST5G-70
        2. 如果是在其他Case中调用，因为Common APP中写入了auto_python_params文件，所以直接从文件中读取，避免了传参的麻烦
        :return: None
        """
        def write_imei_and_check(imei):
            """
            写入IMEI并且查询。
            :param imei: IMEI号
            :return: None
            """
            if imei:  # 如果IMEI不为空
                # 判断是否一致，一致不写入
                imei_status = self.at_handle.send_at("AT+EGMR=0,7", timeout=1)
                if imei in imei_status:
                    all_logger.info("当前IMEI查询与Resource设置值一致")
                    return True

                # 不一致写入
                all_logger.info(f"写入IMEI1: {imei}")
                self.at_handle.send_at(f'AT+EGMR=1,7,"{imei}"', timeout=1)

                # 写入后查询
                imei_status = self.at_handle.send_at("AT+EGMR=0,7", timeout=1)
                if imei not in imei_status:
                    all_logger.error(f"写入IMEI1后，查询的返回值异常：{imei_status}，期望：{imei}")
            else:
                all_logger.error("\nTWS Resource界面可能未配置IMEI1，请检查" * 3)

        def write_sn_and_check(sn):
            """
            写入SN号并且查询
            :param sn: SN号
            :return: None
            """
            if sn:  # 如果SN不为空
                # 判断是否一致，一致不写入
                sn_status = self.at_handle.send_at("AT+EGMR=0,5", timeout=1)
                if sn in sn_status:
                    all_logger.info("当前IMEI查询与Resource设置值一致")
                    return True

                # 不一致写入
                all_logger.info(f"写入SN: {sn}")
                self.at_handle.send_at(f'AT+EGMR=1,5,"{sn}"', timeout=1)

                # 写入后查询
                sn_status = self.at_handle.send_at("AT+EGMR=0,5", timeout=1)
                if sn not in sn_status:
                    all_logger.error(f"写入sn后，查询的返回值异常：{sn_status}，期望：{sn}")
            else:
                all_logger.error("\nTWS Resource界面可能未配置SN，请检查" * 3)

        # 目前支持升级factory版本后写入重新写入IMEI和SN
        imei = getattr(self, 'imei', '')
        sn = getattr(self, 'sn', '')

        if sn or imei:  # SN或者IMEI不为None，说明是传参进来的，直接使用传参的值:
            write_imei_and_check(self.imei)
            write_sn_and_check(self.sn)
        elif os.path.exists('auto_python_params'):  # 说明是Case调用，Case调用会在脚本目录生成auto_python_params文件，将其中的值取出
            with open('auto_python_params', 'rb') as p:
                # original_setting
                args = pickle.load(p).test_setting  # noqa
                if not isinstance(args, dict):
                    args = eval(args)
                imei = args.get('res')[0].get("imei_number", '')
                sn = args.get('res')[0].get("sn", '')
                write_imei_and_check(imei)
                write_sn_and_check(sn)
        else:
            all_logger.info("未查找到auto_python_params，也未传参IMEI和SN，不进行IMEI和SN号的恢复")


if __name__ == '__main__':
    at_port = "COM10"  # AT口
    dm_port = "COM7"  # DM口
    factory = True  # 是否工厂
    ati = "RG500QEAAAR11A06M4G"  # ATI
    csub = "V01"  # AT+CSUB
    firmware_path = r"\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A06M4G_01.001V01.01.001V01"

    num = 0

    while True:
        num += 1
        print(f"{'=' * 50} runtimes: {num} {'=' * 50}")
        qfil = QFIL(at_port=at_port, dm_port=dm_port, factory=True, ati=ati, csub=csub, firmware_path=firmware_path)
        qfil.qfil()

        all_logger.info("wait 60 seconds")
        time.sleep(60)

        qfil.check_cgdcont()

        all_logger.info("wait 30 seconds")
        time.sleep(30)
