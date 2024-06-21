import subprocess
import serial.tools.list_ports
import shutil
import serial
import time
import os
import random
import re
from utils.operate.at_handle import ATHandle
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import PretestError
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI
from utils.functions.gpio import GPIO
from collections import defaultdict
from subprocess import PIPE
from zipfile import ZipFile


class LinuxPretestManager:
    def __init__(self, firmware_path, revision, sub_edition, usb_id, name_real_version, at_port=None, dm_port=None, modem_port=None, debug_port=None):
        self.at_port = at_port
        self.dm_port = dm_port
        self.modem_port = modem_port
        self.debug_port = debug_port
        self.firmware_path = firmware_path
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.linux_api = LinuxAPI()
        self.modem_port = modem_port
        self.revision = revision
        self.sub_edition = sub_edition
        self.usb_id = usb_id
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

    @staticmethod
    def ubuntu_copy_file():
        """
        Ubuntu下复制版本包
        :return:
        """
        os.mkdir(os.getcwd() + '/firmware')
        os.path.join(os.getcwd(), 'firmware')
    
        cur_file_list = os.listdir('/mnt/cur')
        all_logger.info('/mnt/cur目录下现有如下文件:{}'.format(cur_file_list))
        all_logger.info('开始复制当前版本版本包到本地')
        for i in cur_file_list:
            shutil.copy(os.path.join('/mnt/cur', i), os.path.join(os.getcwd(), 'firmware'))
    
        if os.path.join(os.getcwd(), 'firmware'):
            all_logger.info('版本获取成功')
        else:
            raise PretestError('版本包获取失败')

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

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/cur')

    def mount_package(self):
        """
        挂载版本包
        :return:
        """
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'cur' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/cur')
        os.popen('mount -t cifs {} /mnt/cur -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            cur_package_path)).read()
        if os.listdir('/mnt/cur'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise PretestError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

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

    def check_modemrstlevel_aprstlevel_default_value(self):
        """
        检查modemrstlevel默认值。
        :return: None
        """
        self.at_handler.send_at('at+qcfg="modemrstlevel",1')
        self.at_handler.send_at('at+qcfg="aprstlevel",1')
        self.cfun1_1()
        modemrstlevel = self.at_handler.send_at('at+qcfg="modemrstlevel"')
        aprstlevel = self.at_handler.send_at('at+qcfg="aprstlevel"')
        cfun = self.at_handler.send_at('at+cfun?')
        cpin = self.at_handler.send_at('at+cpin?')
        if '"ModemRstLevel",1' not in modemrstlevel:
            raise Exception(f"ModemRstLevel默认值异常: {modemrstlevel}")
        if '"ApRstLevel",1' not in aprstlevel:
            raise Exception(f"ApRstLevel默认值异常: {aprstlevel}")
        if ' READY' not in cpin:
            raise Exception(f"ApRstLevel默认值异常: {cpin}")
        if 'CFUN: 1' not in cfun:
            raise Exception(f"ApRstLevel默认值异常: {cfun}")

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
        
    def get_auto_sel(self):
        """
        获取MBN的默认激活状态是否正常
        :return:
        """
        res = self.at_handler.send_at('AT+QMBNCFG="Autosel"')
        if '"AutoSel",1' not in res:
            raise Exception(f"MBN默认激活状态查询异常{res}")

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

    @staticmethod
    def qfirehose_upgrade(vbat, factory, erase):
        """
        Qfirehose普通升级及断电方法
        :param vbat: 是否断电升级
        :param factory: 是否工厂升级
        :param erase: 是否全擦
        :return:
        """
        # 首先确定版本包名称
        package_name = ''
        for p in os.listdir(os.path.join(os.getcwd(), 'firmware')):
            if os.path.isdir(os.path.join(os.getcwd(), 'firmware', p)):
                if factory:
                    if p.lower().endswith('factory'):
                        package_name = os.path.join(os.getcwd(), 'firmware', p)
                else:
                    if not p.lower().endswith('factory'):
                        package_name = os.path.join(os.getcwd(), 'firmware', p)
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
                    raise PretestError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise PretestError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise PretestError('120S内升级失败')

    def cfun1_1(self):
        """
        检测cfun11重启功能
        :return:
        """
        self.at_handler.send_at('AT+CFUN=1,1', 10)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        time.sleep(10)

    def check_wcdma(self):
        """
        检测版本是否支持wcdma
        """
        re_value = self.at_handler.send_at('AT+QNWPREFCFG= "mode_pref"', 0.3)
        if 'AUTO' in re_value:
            all_logger.error('版本支持wcdma')
        else:
            all_logger.error('版本不支持wcdma')
            raise PretestError('版本不支持wcdma')
        