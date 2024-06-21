import datetime
import os
import re
import time
import glob
import serial
import shutil
import random
import subprocess
import numpy as np
from zipfile import ZipFile
from threading import Thread
import serial.tools.list_ports
from subprocess import STDOUT, PIPE
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.exception.exceptions import UpgradeOnOffError
from utils.logger.logging_handles import all_logger, at_logger
from utils.functions import jenkins
from utils.log.dump.dump_linux import QLogDUMP


class UpgradeOnOff:
    def __init__(self, at_port, dm_port, modem_port, imei, svn, firmware_path, prev_firmware_path, uart_port,
                 port_info, prev_version, usb_id, prev_svn, cur_version, package_name, prev_package_name):
        self.at_port = at_port
        self.dm_port = dm_port
        self.modem_port = modem_port
        self.imei = imei
        self.svn = svn
        self.uart_port = uart_port
        self.firmware_path = firmware_path
        self.prev_firmware_path = prev_firmware_path
        self.port_info = port_info.replace('/', '\\')
        self.prev_version = prev_version
        self.usb_id = usb_id
        self.prev_svn = prev_svn
        self.cur_version = cur_version
        self.cur_package_name = package_name    # 当前测试版本包名
        self.prev_package_name = prev_package_name    # 上一测试版本包名
        self.at_handler = ATHandle(self.at_port)
        self.driver_check = DriverChecker(self.at_port, self.dm_port)
        self.qlog_dump = QLogDUMP()
        time.sleep(1)
        self.adb_key = ''
        self.gpio = GPIO()

    def set_dial_mode(self):
        """设置usbnet值为1，防止Windows下模块拨号导致case执行fail"""
        # if os.name == "nt":
        #     WindowsAPI().remove_ndis_driver()
        self.at_handler.send_at('AT+QCFG="USBNET",1')

    @staticmethod
    def check_dial_init():
        """
        等待模块开机后PC端拨号功能加载成功
        :return: True:检测到， False：未检测到
        """
        timeout = 100  # 等待PC端拨号可以使用的最大时间
        stat_timestamp = time.time()
        while True:
            interface_status = os.popen('netsh mbn show interface').read()
            if '没有' in interface_status:
                time.sleep(1)
            elif time.time() - stat_timestamp > timeout:
                all_logger.error("开机成功后{}秒内PC拨号功能未加载成功，请确定原因".format(timeout))
                return False
            else:
                all_logger.info("PC拨号功能加载成功")
                if time.time() - stat_timestamp >= 15:
                    all_logger.error("拨号功能加载时长超过15S")
                    return time.time() - stat_timestamp  # 返回时间用于判断
                else:
                    all_logger.info('wait 15 seconds')
                    time.sleep(15)  # 等待稳定
                    return True

    def set_adb(self):
        """
        设置开启adb
        :return:
        """
        re_value = ''
        for i in range(3):
            value = self.at_handler.send_at('AT+QCFG="USBCFG"', 10)
            re_value = ''.join(re.findall(r'usbcfg",0x2C7C,0x080\d,(.*)', value))
            if re_value:
                break
            else:
                time.sleep(5)
        if re_value[10] == '0':     # 说明此时还未开启adb
            if self.adb_key:
                self.at_handler.send_at('AT+QADBKEY="{}"'.format(self.adb_key), 10)
                usbcfg_value = self.at_handler.send_at('AT+QCFG="USBCFG"', 3)
                pid = re.findall(r'0x(\w+),0x(\w+)', usbcfg_value)
                if pid:
                    all_logger.info("PID: {}".format(pid))
                if not pid:
                    raise UpgradeOnOffError("获取PID失败")
                if 'ERROR' in self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(pid[0][0], pid[0][1]), timeout=10):
                    all_logger.info('开启adb失败')
                    raise UpgradeOnOffError('开启adb失败')
                self.at_handler.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                self.at_handler.check_urc()
                time.sleep(3)
                self.check_adb()
            else:
                adb_id = self.check_adbkey()
                adb_key = jenkins.query_key(adb_id)
                all_logger.info('获取到的adb密钥为{}'.format(adb_key))
                self.adb_key = adb_key
                self.at_handler.send_at('AT+QADBKEY="{}"'.format(adb_key), 10)
                usbcfg_value = self.at_handler.send_at('AT+QCFG="USBCFG"', 3)
                pid = re.findall(r'0x(\w+),0x(\w+)', usbcfg_value)
                if pid:
                    all_logger.info("PID: {}".format(pid))
                if not pid:
                    raise UpgradeOnOffError("获取PID失败")
                if 'ERROR' in self.at_handler.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(pid[0][0], pid[0][1]), timeout=10):
                    all_logger.info('开启adb失败')
                    raise UpgradeOnOffError('开启adb失败')
                self.at_handler.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                self.at_handler.check_urc()
                time.sleep(3)
                self.check_adb()
        elif re_value[10] == '1':
            all_logger.info('当前已开启adb')

    def check_adb(self):
        """
        检测ADB功能是否开启
        :return:
        """
        re_value = ''
        for i in range(3):
            value = self.at_handler.send_at('AT+QCFG="USBCFG"', 10)
            re_value = ''.join(re.findall(r'usbcfg",0x2C7C,0x080\d,(.*)', value))
            if re_value:
                break
            else:
                time.sleep(5)
        if re_value[10] == '1':
            all_logger.info('当前已开启adb')
            return
        else:
            all_logger.info('开启adb失败')
            raise UpgradeOnOffError('开启adb失败')

    def check_adbkey(self):
        """
        获取adbkey，查询密钥开启adb
        :return:
        """
        key_value = self.at_handler.send_at('AT+QADBKEY?', 10)
        re_value = ''.join(re.findall(r'\+QADBKEY: (\d+)', key_value)).strip()
        return int(re_value)

    def compare_file(self):
        """
        用于对比标准包与工厂包差异
        :return:
        """
        path = os.path.join(os.getcwd(), 'firmware', 'cur')
        standard_list = []  # 标准版本文件夹列表
        factory_list = []   # 工厂版本文件夹列表
        factory_file_list = []   # 工厂版本文件列表
        standard_file_list = []     # 标准版本文件列表
        different_list = ['dbg', 'upgrade']     # 正常文件夹差异
        different_list1 = ['efuse', 'fuse']   # X6X RM项目工厂包多了个efuse文件夹
        different_file_list = ['factory.xqcn', 'rawprogram_nand_p4K_b256K_factory.xml', 'cefs.mbn']     # 正常文件差异
        different_file_list1 = ['rawprogram_nand_p4K_b256K_efuse.xml']  # X6X RM项目工厂包多了rawprogram_nand_p4K_b256K_efuse.xml文件
        partition_factory_path = ''     # 工厂包下partition_nand_xml文件路径
        partition_standard_path = ''    # 标准包下partition_nand_xml文件路径
        rawprogram_factory_path = ''    # 工厂包下rawprogram_nand_p4K_b256K.xml路径
        rawprogram_standard_path = ''   # 标准包下rawprogram_nand_p4K_b256K.xml路径
        for root, dirs, files in os.walk(path):
            # root 表示当前正在访问的文件夹路径，dirs 表示该文件夹下的子目录名list，files 表示该文件夹下的文件list
            # 遍历所有的文件夹
            for d in dirs:
                if 'factory' in os.path.join(root, d) and self.cur_package_name in os.path.join(root, d):  # 工厂包下文件
                    factory_list.append(d)
                    if self.cur_version[:5] in ["RM520", "RM530"]:  # X6X RM项目工厂包多了个efuse文件夹
                        for i in os.listdir(os.path.join(root, d)):
                            if '.' not in i or 'efuse' in d:
                                continue
                            if i == 'partition_nand.xml':
                                partition_factory_path = os.path.join(os.path.join(root, d), i)
                            if i == 'rawprogram_nand_p4K_b256K_factory.xml':
                                rawprogram_factory_path = os.path.join(os.path.join(root, d), i)
                            factory_file_list.append(i)
                    else:
                        for i in os.listdir(os.path.join(root, d)):
                            if '.' not in i:
                                continue
                            if i == 'partition_nand.xml':
                                partition_factory_path = os.path.join(os.path.join(root, d), i)
                            if i == 'rawprogram_nand_p4K_b256K_factory.xml':
                                rawprogram_factory_path = os.path.join(os.path.join(root, d), i)
                            factory_file_list.append(i)
                elif 'factory' not in os.path.join(root, d) and self.cur_package_name in os.path.join(root, d):  # 标准包下文件
                    standard_list.append(d)
                    for i in os.listdir(os.path.join(root, d)):
                        if '.' not in i or 'dbg' in d or 'upgrade' in d:    # 去除文件夹及多出的文件夹比较
                            continue
                        if i == 'partition_nand.xml':
                            partition_standard_path = os.path.join(os.path.join(root, d), i)
                        if i == 'rawprogram_nand_p4K_b256K_update.xml':
                            rawprogram_standard_path = os.path.join(os.path.join(root, d), i)
                        standard_file_list.append(i)
        factory_list = factory_list[1:]     # 切片去除主文件夹名
        standard_list = standard_list[1:]   # 切片去除主文件夹名

        # 比较文件夹区别
        all_logger.info('工厂包文件夹下包含{}子文件夹，标准包文件夹下包含{}子文件夹'.format(factory_list, standard_list))
        if self.cur_version[:5] in ["RM520", "RM530"]:  # X6X RM项目工厂包多了个efuse文件夹
            for i in standard_list[1:]:
                if i not in factory_list and i not in different_list:
                    raise UpgradeOnOffError('标准包比工厂包多出文件夹{},请确认是否正常'.format(i))
            for i in factory_list[1:]:
                if i not in standard_list and i not in different_list1:
                    raise UpgradeOnOffError('工厂包比标准包包多出文件夹{},请确认是否正常'.format(i))
            else:
                all_logger.info('文件夹差异正常')
        else:
            for i in standard_list[1:]:
                if i not in factory_list and i not in different_list:
                    raise UpgradeOnOffError('标准包比工厂包多出文件夹{},请确认是否正常'.format(i))
            else:
                all_logger.info('文件夹差异正常')

        # 比较文件区别
        actual_different_file_list = set(factory_file_list).difference(set(standard_file_list))     # 工厂包比标准包多出的文件
        all_logger.info('实际检查工厂包比标准包多出{}'.format(actual_different_file_list))
        if self.cur_version[:5] in ["RM520", "RM530"]:  # X6X RM项目工厂包多了rawprogram_nand_p4K_b256K_efuse.xml文件
            for i in actual_different_file_list:
                if i not in different_file_list and i not in different_file_list1:
                    raise UpgradeOnOffError('工厂包比标准包多出{}文件,请确认是否正常'.format(i))
            else:
                all_logger.info('文件差异正常')
        else:
            for i in actual_different_file_list:
                if i not in different_file_list:
                    raise UpgradeOnOffError('工厂包比标准包多出{}文件,请确认是否正常'.format(i))
            else:
                all_logger.info('文件差异正常')

        # 比较文件内容区别
        partition_factory = self.readfile(partition_factory_path)
        partition_standard = self.readfile(partition_standard_path)
        set_partition = set(partition_factory).difference(set(partition_standard))
        if len(set_partition) != 1:
            raise UpgradeOnOffError('partition_nand.xml文件工厂包比标准包多出数量不为一行，请确认是否正常')
        partition_different = ''.join(set_partition).replace('\t', '')
        if 'cefs.mbn' not in partition_different:
            raise UpgradeOnOffError('对比partition_nand_xml文件工厂包下比标准包下多出{}内容，请确认是否正常'.format(partition_different))
        rawprogram_factory = self.readfile(rawprogram_factory_path)
        rawprogram_standard = self.readfile(rawprogram_standard_path)
        set_rawprogram_factroy = set(rawprogram_factory).difference(set(rawprogram_standard))   # 工厂包比标准包的差异
        set_rawprogram_standard = set(rawprogram_standard).difference(set(rawprogram_factory))  # 标准包比工厂包的差异
        if len(set(rawprogram_factory)) - len(set(rawprogram_standard)) != 2:
            raise UpgradeOnOffError('rawprogram_nand_p4K_b256K_update.xml文件工厂包比标准包多出数量不为两行，工厂包比标准包多出内容为{}'
                                    '标准包比工厂包不同内容为{}请确认是否正常'.format(set_rawprogram_factroy, set_rawprogram_standard))
        factory_more_standard = ''
        for i in set_rawprogram_factroy:    # 将差异的地方用字符串存储
            factory_more_standard += ''.join(list(i)).strip()
        if 'cefs.mbn' not in factory_more_standard or 'erase' not in factory_more_standard:
            raise UpgradeOnOffError('rawprogram_nand_p4K_b256K_update.xml文件差异异常，请检查,差异内容为{},{}'.format(factory_more_standard, factory_more_standard))

    @staticmethod
    def readfile(file):
        fd = None
        try:
            fd = open(file, "r")
            text = fd.read().splitlines()  # 读取之后进行行分割
            return text
        except Exception as e:
            raise UpgradeOnOffError('读取文件{}异常:{}'.format(file, e))
        finally:
            fd.close()

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

    def switch_edl_mode(self, flag):
        """
        切换EDL mode
        :return: None
        """
        # 转到下载口
        dl_port = ''
        for i in range(3):
            all_logger.info("switch to dl port")
            if flag:    # 断电升级，如果已经进入紧急下载模式，此时只有QDL口，直接返回QDL口即可
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

    def modem_send(self, is_cur):
        """
        使用modem口发ATI+CSUB查询版本信息
        :param: is_cur:是否查询当前版本信息True:查询是否是当前版本；False:查询是否是上一归档版本
        :return:
        """
        with serial.Serial(self.modem_port, baudrate=115200, timeout=0) as _modem_port:
            _modem_port.write('{}\r\n'.format('ATI+CSUB').encode('utf-8'))
            at_logger.info('Send: {}'.format('ATI+CSUB'))
            return_value_cache = ''
            start_time = time.time()
            while True:
                time.sleep(0.001)
                return_value = _modem_port.readline().decode()
                if return_value != '':
                    all_logger.info(return_value.strip())
                    return_value_cache += return_value
                if 'OK' in return_value:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                    break
                if time.time() - start_time > 10:
                    all_logger.info('Modem口执行"ATI+CSUB"指令超时')
        rev = re.findall(r'Revision: (.*)', return_value_cache)[0].strip()
        sub = re.findall(r'SubEdition: (.*)', return_value_cache)[0].strip()
        release_name = rev + sub
        release_name = re.sub(r'[\r\n]', '', release_name).replace('\n', '')
        if is_cur:
            sys_release_name = self.cur_version
        else:
            sys_release_name = self.prev_version
        if release_name == sys_release_name:
            all_logger.info('版本信息检查正常')
        else:
            raise UpgradeOnOffError('查询版本信息与系统上信息不一致,查询信息为{},系统信息为{}'.format(release_name, sys_release_name))

    def chceck_module_info(self, is_cur=True):
        """
        检查模块IMEI号及SVN号
        :param is_cur:是否检查当前版本的svn号,True:检查当前版本，False:检查上一版本
        :return:
        """
        imei_info = self.at_handler.send_at('AT+GSN', 10)
        imei = ''.join(re.findall(r'\d{15}', imei_info))
        if imei != self.imei:
            raise UpgradeOnOffError('当前查询imei号与系统所填不一致，当前所查为{}，系统所填为{}'.format(imei, self.imei))
        svn_info = self.at_handler.send_at('AT+EGMR=0,9', 10)
        svn = ''.join(re.findall(r'\+EGMR: "(\d+)', svn_info))
        if is_cur:
            if svn != self.svn:
                raise UpgradeOnOffError('当前所查最新版本SVN号与系统所填不一致，当前所查为{}, 系统所填为{}'.format(svn, self.svn))
        else:
            if svn != self.prev_svn:
                raise UpgradeOnOffError('当前所查上一版本SVN号与系统所填不一致，当前所查为{}, 系统所填为{}'.format(svn, self.svn))

    def check_module_id(self):
        """
        检查端口PID等信息
        :return:
        """
        lsusb = os.popen('lsusb').read()
        all_logger.info(lsusb)
        usb_num = self.usb_id.split(',')
        pid = format(int(usb_num[0]), 'x').zfill(4)
        all_logger.info('pid为{}'.format(pid))
        vid = format(int(usb_num[1]), 'x').zfill(4)
        all_logger.info('vid为{}'.format(vid))
        if pid in lsusb and vid in lsusb:
            all_logger.info('查询硬件ID信息为：{},{}'.format(pid, vid))
            time.sleep(10)
        else:
            raise Exception('查询AT口Pid：{},{}等信息与配置不一致'.format(pid, vid))

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
        
    @staticmethod
    def adb_check_cpu(check_value: float, check_time=60):
        """
        进入adb输入top查询CPU Loading正常，确认不会某个进程CPU占用率过高
        :param: check_value,检测CPU Loading值是否低于期望值
        :param: check_time,检测时长
        :return:
        """
        all_logger.info('等待一段时间后进行cpu占用率检测')
        time.sleep(32)
        s = subprocess.Popen("adb shell", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        s.stdin.write(b'top\r\n')
        s.stdin.close()
        st = time.time()
        out_cache = ''
        while True:
            out = s.stdout.readline()
            if out != b'' and b'insmod' not in out:
                out = f'"{datetime.datetime.now()}":{out.decode("utf-8")}'
                out_cache += out
            if time.time() - st > check_time:
                s.terminate()
                s.wait()
                break

        content = re.findall(r'\d{1,2}:\d{1,2}:\d{1,2}.\d{1,4}|root.*|system.*|radio.*|gps.*', out_cache)
        [all_logger.info(line.strip()) for line in content]
        cpu_content = re.findall(r'root.*|system.*|radio.*|gps.*', out_cache)
        arr = np.array(cpu_content)
        all_logger.info('检查CPU Loading情况:\n{}'.format(arr))
        line = [x[29:34] for x in arr]
        all_logger.info(line)
        for i in line:
            try:
                if float(i) > check_value:
                    raise Exception('查询CPU Loading出现某个进程CPU占用率过高,占用率为:{}，请确认'.format(i))
            except ValueError:
                continue
        else:
            all_logger.info('adb检查cpu占有率正常')

    def check_default_modem(self):
        """
        检查modemrstlevel和aprstlevel默认值,发送AT+QTEST="DUMP",1指令
        :return:
        """
        modem = self.at_handler.send_at('AT+QCFG="ModemRstLevel"', timeout=10)
        ap = self.at_handler.send_at('AT+QCFG="ApRstLevel"', timeout=10)
        re_modem = ''.join(re.findall(r'"ModemRstLevel",(\d)', modem))
        re_ap = ''.join(re.findall(r'"ApRstLevel",(\d)', ap))
        if int(re_modem) != 1 or int(re_ap) != 1:
            raise UpgradeOnOffError('modemrstlevel和aprstlevel默认值异常，当前查询值分别为{},{}'.format(re_modem, re_ap))
        self.at_handler.readline_keyword(keyword1='RDY', keyword2='PB DONE', at_flag=True, at_cmd='AT+QTEST="DUMP",1', timout=50)

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

    def back_dump_value(self):
        """
        恢复dump指令到默认值11
        :return:
        """
        self.at_handler.send_at('AT+QCFG="ModemRstLevel",1', 10)
        self.at_handler.send_at('AT+QCFG="ApRstLevel",1', 10)

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
        if modem == 1 and ap == 1:  # 模块仅Modem重启，USB口不会消失，USB口有RDY上报，此后模块正常注网
            self.at_handler.check_urc()
            time.sleep(5)
            self.at_handler.send_at('AT+CFUN?', 10)
            self.at_handler.check_network()
        if modem == 0 and ap == 1:  # 模块只是会重启
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handler.check_urc()
            time.sleep(5)
            self.at_handler.send_at('AT+CFUN?', 10)
            self.at_handler.check_network()
        if modem == 0 and ap == 0:  # 模块只剩一个DM口
            for i in range(10):
                if self.dm_port in self.get_port_list() and self.at_port not in self.get_port_list():
                    all_logger.info('模块已进入dump')
                    return True
                all_logger.info(f'当前端口情况为{self.get_port_list()}')
                time.sleep(5)
            else:
                raise UpgradeOnOffError('模块Dump后端口异常')

    def check_dump_log(self):
        """
        检查是否已存在dumplog，若已存在需先删除
        :return:
        """
        # 首先看下qpst文件夹下有无dumplog，有的话删除
        path = r'C:\ProgramData\Qualcomm\QPST\Sahara'
        if os.path.exists(path):
            pass
        else:
            os.mkdir(r'C:\ProgramData\Qualcomm\QPST\Sahara')
        for f in os.listdir(path):
            if 'Port_{}'.format(self.dm_port) in f:
                dump_path = os.path.join(path, 'Port_{}'.format(self.dm_port))
                shutil.rmtree(dump_path)
                all_logger.info('已删除之前存在dumplog')

    # def qpst(self):
    #     r"""
    #     打开qpst抓dumplog，打开指令start /d "C:\Program Files (x86)\Qualcomm\QPST\bin" QPSTConfig.exe
    #     :return:
    #     """
    #     exc_type = None
    #     exc_value = None
    #     q = None
    #     try:
    #         q = Qpst()
    #         q.click_add_port()
    #         q.input_port(self.dm_port)
    #         time.sleep(10)  # 等一会再去检查是否有dumplog
    #         path = r'C:\ProgramData\Qualcomm\QPST\Sahara'
    #         for i in range(10):
    #             for f in os.listdir(path):
    #                 if 'Port_{}'.format(self.dm_port) not in f:
    #                     time.sleep(5)
    #                     continue
    #                 else:
    #                     all_logger.info('已获取到dump_log存在')
    #                     return True
    #         else:
    #             raise UpgradeOnOffError('模块进入dump后未获取dumplog')
    #     except Exception as e:
    #         all_logger.info(e)
    #         exc_type, exc_value, exc_tb = sys.exc_info()
    #     finally:
    #         q.close_qpst()
    #         if exc_type and exc_value:
    #             raise exc_type(exc_value)

    @staticmethod
    def compare_sbl_file():
        """
        比较SBL1文件大小
        :return:
        """
        path = os.path.join(os.getcwd(), 'firmware')
        cur_sbl1_path = ''      # 当前版本的sbl1文件路径
        pre_sbl1_path = ''      # 上一个A版本的sbl1文件路径
        for root, dirs, file in os.walk(path):
            for d in dirs:
                if 'cur' in os.path.join(root, d):
                    for i in os.listdir(os.path.join(root, d)):
                        if 'sbl1.mbn' in i and 'factory' not in os.path.join(root, d):
                            cur_sbl1_path = os.path.join(os.path.join(root, d), i)
                            all_logger.info('当前版本的sbl1文件路径为{}'.format(cur_sbl1_path))
                if 'pre' in os.path.join(root, d):
                    for i in os.listdir(os.path.join(root, d)):
                        if 'sbl1.mbn' in i and 'factory' not in os.path.join(root, d):
                            pre_sbl1_path = os.path.join(os.path.join(root, d), i)
                            all_logger.info('上个A版本的sbl1文件路径为{}'.format(pre_sbl1_path))
        cur_sbl_size = os.path.getsize(cur_sbl1_path)
        pre_sbl_size = os.path.getsize(pre_sbl1_path)
        if cur_sbl_size != pre_sbl_size:
            raise UpgradeOnOffError('当前版本的sbl1文件与上一个A版本的sbl1文件大小不一致，请确认')
        else:
            all_logger.info('当前版本的sbl1文件与上一个A版本的sbl1文件大小确认一致')

    def qpowd(self, mode):
        """
        检测Qpowd关机功能
        :param mode:0: AT+QPOWD=0关机; 1:AT+QPOWD=1关机; 2: AT+QPOWD关机
        :return:
        """
        if mode == 0:   # 紧急开关机，上报Power Down很快
            all_logger.info('Send: AT+QPOWD=0')
            self.at_handler.readline_keyword('POWERED DOWN', at_flag=True, at_cmd='AT+QPOWD=0', timout=30)
        elif mode == 1:
            self.at_handler.send_at('AT+QPOWD=1', 10)
            self.at_handler.readline_keyword('POWERED DOWN', timout=30)
        elif mode == 2:
            self.at_handler.send_at('AT+QPOWD', 10)
            self.at_handler.readline_keyword('POWERED DOWN', timout=30)
        self.driver_check.check_usb_driver_dis()
        self.gpio.set_pwk_high_level()
        self.driver_check.check_usb_driver()
        self.at_handler.check_urc()
        time.sleep(10)
        self.adb_check_cpu(40.0)

    def cfun1_1(self):
        """
        检测cfun11重启功能
        :return:
        """
        self.at_handler.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handler.check_urc()
        time.sleep(10)
        self.adb_check_cpu(40.0)

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
        random_off_time = round(random.uniform(1, 60))
        if vbat:
            all_logger.info('升级进行到{}S时断电'.format(random_off_time))
        upgrade = subprocess.Popen('QFirehose -f {} {}'.format(package_name, '-e' if is_factory else ''), stdout=PIPE, stderr=STDOUT, shell=True)
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
                    raise UpgradeOnOffError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise UpgradeOnOffError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise UpgradeOnOffError('120S内升级失败')

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
                imei_status = self.at_handler.send_at("AT+EGMR=0,7", timeout=1)
                if imei in imei_status:
                    all_logger.info("当前IMEI查询与Resource设置值一致")
                    return True

                # 不一致写入
                all_logger.info(f"写入IMEI1: {imei}")
                self.at_handler.send_at(f'AT+EGMR=1,7,"{imei}"', timeout=1)

                # 写入后查询
                imei_status = self.at_handler.send_at("AT+EGMR=0,7", timeout=1)
                if imei not in imei_status:
                    all_logger.error(f"写入IMEI1后，查询的返回值异常：{imei_status}，期望：{imei}")
            else:
                all_logger.error("\nTWS Resource界面可能未配置IMEI1，请检查" * 3)

        # 目前支持升级factory版本后写入重新写入IMEI
        imei = getattr(self, 'imei', '')

        if imei:  # IMEI不为None，说明是传参进来的，直接使用传参的值:
            write_imei_and_check(self.imei)
        elif os.path.exists('auto_python_params'):  # 说明是Case调用，Case调用会在脚本目录生成auto_python_params文件，将其中的值取出
            with open('auto_python_params', 'rb') as p:
                # original_setting
                args = pickle.load(p).test_setting  # noqa
                if not isinstance(args, dict):
                    args = eval(args)
                imei = args.get('res')[0].get("imei_number", '')
                write_imei_and_check(imei)
        else:
            all_logger.info("未查找到auto_python_params，也未传参IMEI和SN，不进行IMEI的恢复")

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
        version_r = re.sub(r'[\r\n]', '', at_version).replace('\n', '')
        if is_cur:
            if self.cur_version != version_r:
                raise UpgradeOnOffError('系统下发版本号与升级后查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(self.cur_version, at_version))
        else:
            if self.prev_version != version_r:
                raise UpgradeOnOffError('系统下发版本号与升级后查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(self.prev_version, at_version))

    def check_usb_id(self):
        """
        检查USBID是否正确，AT+QCFG=”USBID“返回值
        :return:
        """
        at_value = self.at_handler.send_at('AT+QCFG="USBID"', 10)
        re_usb_info = ''.join(re.findall(r'usbid",(.*)', at_value))
        usb_value = self.usb_id.split(',')
        for i in usb_value:
            if i not in re_usb_info:
                raise UpgradeOnOffError('系统所填USBID信息与AT查询不一致，系统填写{}，AT查询结果{}'.format(self.usb_id, re_usb_info))

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
            raise UpgradeOnOffError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

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
            all_logger.info(f'cur路径下存在{os.listdir(os.path.join(os.getcwd(), "firmware", "cur"))}',
                            f'prev路径下存在{os.listdir(os.path.join(os.getcwd(), "firmware", "prev"))}')
        else:
            raise UpgradeOnOffError('版本包获取失败')

    @staticmethod
    def scan_virus():
        """
        扫描版本包中是否存在病毒
        :return:
        """
        scan_result = os.popen('clamscan -r {} -i'.format(os.path.join(os.getcwd(), 'firmware'))).read()
        all_logger.info('版本包病毒扫描结果为:{}'.format(scan_result))
        if int(''.join(re.findall(r'Infected files: (\d+)', scan_result))) > 0:
            raise UpgradeOnOffError('版本包中扫描存在病毒，请确认')
        else:
            all_logger.info('版本包病毒扫描正常')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/cur')
        os.popen('umount /mnt/prev')

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

    @staticmethod
    def is_qdl():
        """
        判断Linux下Qfirehose断电升级后模块是否进入紧急下载模式,进入返回True，未进入返回False
        :return:
        """
        for i in range(10):
            lsusb = os.popen('lsusb').read()
            all_logger.info(lsusb)
            if '9008' in lsusb:
                all_logger.info('模块已进入紧急下载模式')
                return True
            elif '2c7c' in lsusb:
                all_logger.info('模块未进入紧急下载模式')
                time.sleep(10)
                return False
            time.sleep(5)

    def reset(self):
        """
        控制reset引脚重启模块
        :return:
        """
        self.gpio.set_reset_high_level()
        self.driver_check.check_usb_driver_dis()
        self.gpio.set_reset_low_level()
        self.driver_check.check_usb_driver()
        self.at_handler.check_urc()
        self.adb_check_cpu(40.0)

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

    def linux_reset_module(self):
        """
        如果case升级失败会导致模块处于紧急下载模式，每次case执行前检查
        :return:
        """
        if self.is_qdl():   # 如果当前处于紧急下载模式，首先重启模块，之后再检查是否仍处于紧急下载模式
            self.gpio.set_vbat_high_level()
            time.sleep(3)
            self.gpio.set_vbat_low_level_and_pwk()
            if self.is_qdl():
                all_logger.info('模块升级失败，且重启后进入紧急下载模式，重新升级恢复')
                self.qfirehose_upgrade('cur', False, False, False)
            else:
                all_logger.info('重启后恢复正常')


class Powerkey(Thread):
    """
    检测AT口Powerkey关机后的URC上报
    """
    def __init__(self, at_port, modem_port, urc_list: list):
        super().__init__()
        self.at_port = at_port
        self.modem_port = modem_port
        self.at_handle = ATHandle(at_port)
        self.power_off_urc = urc_list
        self._at_port = serial.Serial()
        self._at_port.port = self.at_port
        self._at_port.baudrate = 115200
        self._at_port.timeout = 0
        self._at_port.open()
        self.error_msg = ''
        self.finish_flag = False
        self.stop_flag = False
        self.modem_powerkey = Modem_Powerkey(self.modem_port, urc_list)
        self.modem_powerkey.setDaemon(True)
        self.modem_powerkey.start()

    def run(self):
        start_time = time.time()
        try:
            return_value_cache = ''
            while True:
                return_value = self.at_handle.readline(self._at_port)
                return_value_cache += return_value
                if 'POWERED DOWN' in return_value:
                    time.sleep(1)
                    self.modem_powerkey.stop_flag = True
                    self.modem_powerkey.join()
                    break
                if time.time() - start_time > 60:
                    all_logger.info('60S内未检测到POWERED DOWNURC上报')
                    raise UpgradeOnOffError('60S内未检测到POWERED DOWNURC上报')
            all_logger.info('AT口检测到上报URC为:\r\n{}'.format(return_value_cache.strip().replace('\r\n', '  ')))
            for i in self.power_off_urc:
                if i not in return_value_cache:
                    self.error_msg += 'AT口未检测到{}上报  '.format(i)
                    if self.error_msg != '':
                        raise UpgradeOnOffError(self.error_msg)
            else:
                all_logger.info('AT口URC检测正常'.format())
        except Exception as e:
            self.error_msg += str(e)
        finally:
            self.error_msg += self.modem_powerkey.error_msg
            self._at_port.close()


class Modem_Powerkey(Thread):
    """
    检测Modem口Powerkey关机后的URC上报
    """
    def __init__(self, modem_port, power_off_urc):
        super().__init__()
        self.modem_port = modem_port
        self.at_handle = ATHandle(modem_port)
        self.power_off_urc = power_off_urc
        self._modem_port = serial.Serial()
        self._modem_port.port = self.modem_port
        self._modem_port.baudrate = 115200
        self._modem_port.timeout = 0
        self._modem_port.open()
        self.error_msg = ''
        self.stop_flag = False

    def run(self):
        start_time = time.time()
        try:
            return_value_cache = ''
            while True:
                return_value = self.at_handle.readline(self._modem_port)
                return_value_cache += return_value
                if self.stop_flag:
                    break
                if time.time() - start_time > 60:
                    all_logger.info('60S内未检测到POWERED DOWN URC上报')
                    raise UpgradeOnOffError('60S内未检测到POWERED DOWN URC上报')
            all_logger.info('Modem口检测到上报URC为:\r\n{}'.format(return_value_cache.strip().replace('\r\n', '  ')))
            for i in self.power_off_urc:
                if i not in return_value_cache:
                    self.error_msg += 'Modem口未检测到{}上报  '.format(i)
                if self.error_msg != '':
                    raise UpgradeOnOffError(self.error_msg)
            else:
                all_logger.info('Modem口URC检测正常'.format())
        except Exception as e:
            self.error_msg += str(e)
        finally:
            self._modem_port.close()
