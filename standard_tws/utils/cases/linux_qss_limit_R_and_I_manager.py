import glob
import hashlib
import shutil
import threading
from collections import deque
import random
from zipfile import ZipFile
import serial
from utils.functions.gpio import GPIO
from utils.functions.jenkins import multi_thread_merge_version, multi_thread_merge_fota_full_images, query_key
from utils.functions.jenkins import multi_thread_merge_SDX6X_AB_gentools
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger, at_logger
import subprocess
import time
import os
import re
from tools.qss.qss_client import ConnectQSS, WriteSimcard
from utils.exception.exceptions import QSSLimitRAndIError
from utils.operate.uart_handle import UARTHandle
import serial.tools.list_ports
from subprocess import PIPE


class LinuxQSSLimitRAndIManager:
    def __init__(self, uart_port, at_port, dm_port, debug_port,
                 qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name,
                 name_sub_version, ChipPlatform, prev_firmware_path, prev_name_sub_version, firmware_path, oc_num):
        self.driver_check = DriverChecker(at_port, dm_port)
        self.oc_num = oc_num
        self.uart_port = uart_port
        self.at_port = at_port
        self.dm_port = dm_port
        self.debug_port = debug_port
        self.at_handle = ATHandle(at_port)
        self.prev_firmware_path = prev_firmware_path
        self.firmware_path = firmware_path
        self.prev_name_sub_version = prev_name_sub_version
        self.ChipPlatform = ChipPlatform
        self.qss_ip = qss_ip
        self.local_ip = local_ip
        self.node_name = node_name
        self.mme_file_name = mme_file_name
        self.enb_file_name = enb_file_name
        self.ims_file_name = ims_file_name
        self.write_simcard = WriteSimcard(self.at_port)
        self.gpio = GPIO()
        self.name_sub_version = name_sub_version
        self.Is_OCPU_version = True if 'OCPU' in self.name_sub_version else False
        self.Is_XiaoMi_version = True if '_XM' in self.name_sub_version else False
        self.Is_ab_fota_version = True if 'M8G_' in self.name_sub_version else False
        self.uart_handler = UARTHandle(uart_port)
        self.cur_standard_path = ''
        self.prev_standard_path = ''
        self.cur_factory_path = ''
        self.prev_factory_path = ''
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

    def prepare_package(self):
        if not os.path.exists(os.path.join(os.getcwd(), 'firmware')):
            self.mount_package()
            self.ubuntu_copy_file()
            self.make_fota_package()
        else:
            all_logger.info('已有版本包，直接使用')

    def make_fota_package(self):
        if self.Is_ab_fota_version:
            self.make_ab_fota_package()
        else:
            self.make_dfota_package()

    def make_ab_fota_package(self, factory=False):
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
                raise QSSLimitRAndIError("获取前一个版本工厂包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '_factory.zip')
                all_logger.info("当前版本工厂包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise QSSLimitRAndIError("获取当前版本工厂包名称失败")

        else:
            if os.path.exists(os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')):
                orig_target_file = os.path.join(old_zip_path, self.prev_name_sub_version + '.zip')
                all_logger.info("前一个版本标准包名称orig_target_file为:\r\n{}".format(orig_target_file))
            if not orig_target_file:
                all_logger.info(os.listdir(old_zip_path))
                raise QSSLimitRAndIError("获取前一个版本标准包名称失败")

            if os.path.exists(os.path.join(new_zip_path, self.name_sub_version + '.zip')):
                cur_target_file = os.path.join(new_zip_path, self.name_sub_version + '.zip')
                all_logger.info("当前版本标准包名称cur_target_file为:\r\n{}".format(cur_target_file))
            if not cur_target_file:
                all_logger.info(os.listdir(new_zip_path))
                raise QSSLimitRAndIError("获取当前版本标准包名称失败")

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
            raise QSSLimitRAndIError('请检查resouce参数dev_oc_num是否填写正确')
        all_logger.info("oc_key: {}".format(oc_key))

        multi_thread_merge_SDX6X_AB_gentools(orig_target_file, cur_target_file, self.prev_name_sub_version,
                                             self.name_sub_version, module_id, oc_key)

    def check_roback(self, prev=False):
        """
        查看当前版本是否合入防回滚
        :param prev: 升级包路径,cur or prev
        :return:
        """
        if prev:
            return_value = self.at_handle.send_at('AT+QCFG="rollback"', 0.6)
            if '+QCFG: "rollback",1' in return_value or 'ERROR' in return_value:
                all_logger.info('烧录非禁R&I版本正常')
            else:
                all_logger.info('烧录非禁R&I版本异常，当前指令返回信息为{}'.format(return_value))
                raise QSSLimitRAndIError('烧录非禁R&I版本异常')
        else:
            return_value = self.at_handle.send_at('AT+QCFG="rollback"', 0.6)
            if '+QCFG: "rollback",0' in return_value:
                all_logger.info('烧录禁R&I版本正常')
            else:
                all_logger.info('烧录禁R&I版本异常，当前指令返回信息为{}'.format(return_value))
                raise QSSLimitRAndIError('烧录非禁R&I版本异常')

    def set_roaming(self):
        """
        设置默认关闭漫游后注网
        :return:
        """
        return_value = self.at_handle.send_at('AT+QNWCFG="data_roaming",1', 0.6)
        if 'OK' in return_value:
            all_logger.info('漫游指令设置成功')
        else:
            all_logger.info('漫游指令设置异常，当前指令返回信息为{}'.format(return_value))
            raise QSSLimitRAndIError('漫游指令设置异常')
        return_value = self.at_handle.send_at('AT+QNWCFG="data_roaming"', 0.6)
        if '+QNWCFG: "data_roaming",1' in return_value:
            all_logger.info('漫游指令设置成功')
        else:
            all_logger.info('漫游指令设置异常，当前指令返回信息为{}'.format(return_value))
            raise QSSLimitRAndIError('漫游指令设置异常')

    def get_module_id(self):
        gmm_value = self.at_handle.send_at("AT+GMM")
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

    def send_after_urc(self, at_command, urc, timeout=120):
        """
        在某个URC出现后立刻发送指定指令
        """
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as __at_port:
            at_start_timestamp = time.time()
            return_value_cache = ''
            while time.time() - at_start_timestamp < timeout:
                # AT端口值获取
                time.sleep(0.001)  # 减小CPU开销
                return_value = self.readline(__at_port)
                if return_value != '':
                    return_value_cache += '{}'.format(return_value)
                    if urc in return_value:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                        __at_port.write('{}\r\n'.format(at_command).encode('utf-8'))
                        at_logger.info(f'already find {urc} , start send: {at_command}')
                        return return_value_cache
                    else:
                        continue
            else:
                raise QSSLimitRAndIError(f'{timeout} s内未出现URC: {urc}')

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
                                                                                                         '\(').replace(  # noqa
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
                    raise QSSLimitRAndIError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.info('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    raise QSSLimitRAndIError('升级失败')
            if vbat and time.time() - start_time > random_off_time:
                all_logger.info('升级过程随机断电')
                return True
            if time.time() - start_time > 120:
                all_logger.info('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                raise QSSLimitRAndIError('120S内升级失败')

    def abd_fota(self, a_b=True):
        if self.Is_ab_fota_version:
            self.abd_ab_fota(a_b)
        else:
            self.abd_dfota(a_b)

    def abd_ab_fota(self, a_b=True):
        try:
            self.unlock_adb()
            self.check_adb_devices_connect()
            self.push_package_and_check(a_b)
            self.set_package_name(a_b)
            self.query_state(state_module="0")
            self.ab_update(a_b)
            all_logger.info("ADB本地方ab-fota升级结束")
        finally:
            self.reset_after()

    def ab_update(self, a_b=True):
        """
        AT+QABFOTA="UPDATE"  触发AB系统升级
        ufs_file:不包含fota包
        ufs_file2:包含fota包
        """
        # 升级前查询CPU情况
        all_logger.info("开始触发AB系统升级")
        system_before = self.check_activeslot()
        all_logger.info("system_before:{}".format(system_before))
        self.send_update()
        time_update_use = self.dfota_step_2(a_b=a_b)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()
        time.sleep(3)
        all_logger.info("检查升级后升级状态是否正确")
        self.query_state(state_module="2")
        system_after = self.check_activeslot()
        if system_after != system_before:
            all_logger.info("升级后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
        else:
            raise QSSLimitRAndIError(
                "升级后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
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
            except Exception:  # noqa
                pass
        all_logger.info("time_backup_use:{}".format(str(time_backup_use)))
        # 备份完成查询升级状态
        self.query_state(state_module="0")
        time.sleep(5)
        return time_backup_use, time_update_use

    def dfota_step_2(self, upgrade_stop=False, delete_package=False, continu_update=False, send_again=False, a_b=True):
        """
        发送AT+QABFOTA="download"指令后的log检查:
        检测+QIND: "ABFOTA","UPDATE",11 到 +QIND: "ABFOTA","UPDATE",100
        :return: None
        """
        for i in range(100):
            try:
                at_port = serial.Serial(self.at_port, baudrate=115200, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(0.5)
                continue
        else:
            raise QSSLimitRAndIError("检测ABFOTA升级时打开AT口异常")
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
                            raise QSSLimitRAndIError("触发AB系统升级异常!查询当前升级状态为[{}]!".format(self.exit_code[key_update]))
                        else:
                            raise QSSLimitRAndIError("未知异常!\r\n{}".format(recv))
                else:
                    at_logger.error('ABFOTA 检测{} +QIND: "ABFOTA","UPDATE",11失败')
                    raise QSSLimitRAndIError('ABFOTA升级过程异常: 检测{} +QIND: "ABFOTA","UPDATE",11失败')
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
                        raise QSSLimitRAndIError("发送指令异常,返回ERROR!{}".format(recv))
                if '+QABFOTA: "state"' in recv:
                    key_state = ''.join(re.findall(r'\+QABFOTA: "state",\w+ \((\d)\)', recv))
                    all_logger.info("key_state:{}".format(key_state))
                    if key_state in self.state_code.keys():
                        all_logger.info("查询当前升级状态为[{}]!".format(self.state_code[key_state]))
                    else:
                        if delete_flag:
                            all_logger.info("查询升级状态异常!{}".format(recv))
                        else:
                            raise QSSLimitRAndIError("查询升级状态异常!{}".format(recv))
                    if key_state != '1':
                        if delete_flag:
                            all_logger.info("删除升级包后,已经查询升级状态异常[{}]!".format(self.state_code[key_state]))
                            return True
                        raise QSSLimitRAndIError("查询升级状态异常[{}]!".format(self.state_code[key_state]))
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
                        raise QSSLimitRAndIError("ABFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise QSSLimitRAndIError('未检测到ABFOTA上报+QIND: "ABFOTA","UPDATE",11')

    def send_update(self):
        """
        AT+QABFOTA="update"  触发AB系统升级
        """
        all_logger.info("触发AB系统升级")
        self.at_handle.send_at('AT+QABFOTA="UPDATE"', 0.3)

    def check_activeslot(self):
        """
        AT+QABFOTA="activeslot"  查询当前运行系统
        """
        all_logger.info("查询当前运行系统")
        return_value = self.at_handle.send_at('AT+QABFOTA="activeslot"', 3)
        key_system = ''.join(re.findall(r'\+QABFOTA: "activeslot",(\d)', return_value))
        all_logger.info("key_system:{}".format(key_system))
        if key_system == '0' or key_system == '1':
            all_logger.info("查询当前运行系统为{}!".format(self.start_sequence[key_system]))
            return key_system
        else:
            raise QSSLimitRAndIError("查询当前运行系统异常!{}".format(return_value))

    def reset_after(self):
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
            except Exception:  # noqa
                pass
        else:
            all_logger.info("异常!600s内未检测到初始状态!开始升级!")
            # 升级到上个支持俄罗斯的版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

    def set_package_name(self, a_b):
        """
        AT+QABFOTA="package"  设置升级包名称
        """
        package_name = 'a-b.zip' if a_b else "b-a.zip"
        all_logger.info("设置版本包名称")
        self.at_handle.send_at('AT+QABFOTA="package","{}"'.format(package_name), 3)
        return_value = self.at_handle.send_at('AT+QABFOTA="package"', 3)
        all_logger.info("{}".format(return_value))
        if package_name not in return_value:
            raise QSSLimitRAndIError("设置版本包名称异常!")
        else:
            all_logger.info("设置版本包名称成功")

    def query_state(self, state_module):
        """
        AT+QABFOTA="state"  查询升级状态
        """
        # all_logger.info("查询当前升级状态")
        return_value = self.at_handle.send_at('AT+QABFOTA="state"', 3)
        key_state = ''.join(re.findall(r'\+QABFOTA: "state",\w+ \((\d)\)', return_value))
        # all_logger.info("key_state:{}".format(key_state))
        if key_state in self.state_code.keys():
            # all_logger.info("查询当前升级状态为[{}],期望查询值为[{}]".format(self.state_code[key_state], self.state_code[
            # state_module]))
            pass
        else:
            raise QSSLimitRAndIError("查询升级状态异常!{}".format(return_value))
        if state_module != key_state:
            raise QSSLimitRAndIError("state查询异常!查询值为{},于预期不符!预期为{}".format(key_state, state_module))
        else:
            all_logger.info("state查询正常, state: {}".format(key_state))

    def abd_dfota(self, a_b):
        fota_file = 'a-b.zip' if a_b else 'b-a.zip'
        self.unlock_adb()
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b)
        # 兼容小米版本
        if self.Is_XiaoMi_version:
            self.at_handle.send_at(f'AT+QFOTADL="/usrdata/cache/ufs/{fota_file}"')
        else:
            self.at_handle.send_at(f'AT+QFOTADL="/cache/ufs/{fota_file}"')
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        if self.name_sub_version.startswith("RG") and self.ChipPlatform == "SDX55":
            at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
            self.uart_handler.dfota_step_2()
            if 'START' not in at_background_read.get_info():
                all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                                 "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
        else:
            self.at_handle.dfota_step_2()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()

    def reset_version(self):
        # 升级到当前禁R&I的工厂版本
        self.qfirehose_upgrade('cur', False, True, True)
        self.driver_check.check_usb_driver()
        self.gpio.set_vbat_high_level()
        self.driver_check.check_usb_driver_dis()
        self.gpio.set_vbat_low_level_and_pwk()
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()

    @staticmethod
    def push_package_and_check(a_b):
        fota_file = 'a-b.zip' if a_b else 'b-a.zip'
        path = os.path.join(os.getcwd(), 'firmware', fota_file)
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
            md5 = subprocess.getoutput('adb shell md5sum /cache/ufs/{}'.format(fota_file))
            all_logger.info(md5)
            all_logger.info('adb get md5:{}'.format(md5))
            if package_md5 in md5:
                all_logger.info("MD5对比正常")
                time.sleep(5)
                return True
            time.sleep(1)
        else:
            raise QSSLimitRAndIError("ADB PUSH升级包失败")

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
                raise QSSLimitRAndIError("adb超时未加载")
            else:  # 既没有检测到设备，也没有超时，等1S
                time.sleep(1)

    def unlock_adb(self):
        usbcfg_value = self.at_handle.send_at('AT+QCFG="USBCFG"', 3)
        if ',1,1,1,1,1,1' in usbcfg_value:
            all_logger.info("模块ADB已开启")
        else:
            PID = re.findall(r'0x(\w+),0x(\w+)', usbcfg_value)  # noqa
            if PID:
                all_logger.info("PID: {}".format(PID))
            if not PID:
                raise QSSLimitRAndIError("获取PID失败")
            if not self.Is_OCPU_version:
                qadbkey = self.at_handle.send_at('AT+QADBKEY?')
                qadbkey = ''.join(re.findall(r'\+QADBKEY:\s(\S+)', qadbkey))
                adb_key = query_key(qadbkey, qtype='adb')
                if not qadbkey:
                    raise QSSLimitRAndIError("获取QADBKEY失败")

                self.at_handle.send_at('AT+QADBKEY="{}"'.format(adb_key), 3)

                self.at_handle.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(PID[0][0], PID[0][1]), 3)
            else:
                all_logger.info('当前为OCPU版本，直接开启！')
                self.at_handle.send_at('AT+QCFG="USBCFG",0x{},0x{},1,1,1,1,1,1'.format(PID[0][0], PID[0][1]), 3)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(10)

    def read_poweron_urc(self, timeout=60):
        start_time = time.time()
        urc_value = []
        count = 0
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            while time.time() - start_time < timeout:
                read_value = self.at_handle.readline(at_port)
                if read_value != '':
                    urc_value.append(read_value)
                continue
            for urc in urc_value:
                if urc == '+QIND: PB DONE\r\n':
                    count = count + 1
            all_logger.info('{}s检测URC上报内容为{},且pb done上报{}次'.format(timeout, urc_value, count))

    # @staticmethod
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
            raise QSSLimitRAndIError("获取前一个版本target file zip失败")
        # 在firmware/cur文件夹下查找当前版本targetfiles.zip文件，若存在则复制到firmware/fota/prev路径下，并以其标准包命名
        for path, _, files in os.walk(os.path.join(firmware_path, 'cur')):
            for file in files:
                if file == 'targetfiles.zip':
                    cur_target_file = os.path.join(path, file)
                    shutil.copy(os.path.join(cur_target_file),
                                os.path.join(firmware_path_fota, 'cur', name_sub_version_zip))
                    cur_target_file = os.path.join(firmware_path_fota, 'cur', name_sub_version_zip)  # noqa
        if not cur_target_file:
            raise QSSLimitRAndIError("获取当前版本target file zip失败")

        # 兼容小米定制版本
        if self.Is_XiaoMi_version:
            multi_thread_merge_fota_full_images(orig_target_file, cur_target_file)
        else:
            multi_thread_merge_version(orig_target_file, cur_target_file)
        # 差分包制作完成后，删除firmware/fota文件夹
        shutil.rmtree(firmware_path_fota, ignore_errors=True)

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        for i in range(10):
            time.sleep(3)
            os.popen('umount /mnt/prev').read()
            os.popen('umount /mnt/cur').read()
            if not os.listdir('/mnt/prev') and not os.listdir('/mnt/cur'):
                all_logger.info('共享卸载成功')
                break

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
            raise QSSLimitRAndIError('解压版本包失败')
        all_logger.info('解压固件成功')
        # os.popen(f'rm -rf /{firmware_path}/cur/*.zip').read()    # 最后删除压缩文件
        # os.popen(f'rm -rf /{firmware_path}/prev/*.zip').read()    # 最后删除压缩文件
        return True

    def ubuntu_copy_file(self):
        """
        Ubuntu下复制版本包到PackPath目录下
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
        if search_result_cur and search_result_cur_factory and not self.Is_ab_fota_version:
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
                raise QSSLimitRAndIError('当前版本包获取失败')
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
            if self.name_sub_version + '.zip' in os.listdir(os.path.join(os.getcwd(), 'firmware',
                                                                         'cur')) and self.name_sub_version + '_factory.zip' in os.listdir(  # noqa
                os.path.join(os.getcwd(), 'firmware', 'cur')):
                all_logger.info('当前版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'cur')))
                raise QSSLimitRAndIError('当前版本包获取失败')

        search_result_prev = self.search_package('prev')  # 先从本地寻找版本包
        search_result_prev_factory = self.search_package('prev_factory')  # 先从本地寻找版本包
        if search_result_prev and search_result_prev_factory and not self.Is_ab_fota_version:
            all_logger.info(
                f"cp {self.prev_standard_path} to {os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version)}")  # noqa
            shutil.copytree(self.prev_standard_path,
                            os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version))
            all_logger.info(
                f"cp {self.prev_factory_path} to {os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version + '_factory')}")  # noqa
            shutil.copytree(self.prev_factory_path,
                            os.path.join(os.getcwd(), 'firmware', 'prev', self.prev_name_sub_version + '_factory'))

            if self.prev_name_sub_version in os.listdir(os.path.join(os.getcwd(), 'firmware',
                                                                     'prev')) and self.prev_name_sub_version + '_factory' in os.listdir(  # noqa
                os.path.join(os.getcwd(), 'firmware', 'prev')):
                all_logger.info('上一版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'prev')))
                raise QSSLimitRAndIError('上一版本包获取失败')
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
            if self.prev_name_sub_version + '.zip' in os.listdir(os.path.join(os.getcwd(), 'firmware',
                                                                              'prev')) and self.prev_name_sub_version + '_factory.zip' in os.listdir(  # noqa
                os.path.join(os.getcwd(), 'firmware', 'prev')):
                all_logger.info('上一版本包获取成功')
            else:
                all_logger.info(os.listdir(os.path.join(os.getcwd(), 'firmware', 'prev')))
                raise QSSLimitRAndIError('上一版本包获取失败')
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
                    self.prev_standard_path = os.path.join(path, prev_package_name)
                    all_logger.info(self.prev_standard_path)
                if cur_package_name + '_factory' in dirs:
                    self.cur_factory_path = os.path.join(path, cur_package_name + '_factory')
                    all_logger.info(self.cur_factory_path)
                if prev_package_name + '_factory' in dirs:
                    self.prev_factory_path = os.path.join(path, prev_package_name + '_factory')
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
            raise QSSLimitRAndIError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    def send_at_until_rusult(self, at_command, until_result, time_out=300, at_time_out=3):
        """
        at_command: AT命令
        until_result： 期望结果
        time_out： 超时时间
        at_time_out： 单条at超时时间
        一直发送AT，直到获得期望的结果或者超时报错
        """
        start_time = time.time()
        while time.time() - start_time < time_out:
            return_value = self.at_handle.send_at(at_command, at_time_out)
            all_logger.info(return_value)
            if until_result in return_value:
                break
            time.sleep(1)
        else:
            raise QSSLimitRAndIError(f'异常! {time_out}s内查询{at_command} 结果中未获得期望字段 {until_result}')

    def check_weak_signal(self):
        # AT+QRSRP
        prx, drx, rx2, rx3 = self.get_qrsrp()
        # AT+QENG="servingcell"中的'RSRP','SINR','RSRQ',  # noqa
        RSRP = '' if self.get_qeng_info('RSRP') is False else self.get_qeng_info('RSRP')['RSRP']  # noqa
        SINR = '' if self.get_qeng_info('SINR') is False else self.get_qeng_info('SINR')['SINR']  # noqa
        RSRQ = '' if self.get_qeng_info('RSRQ') is False else self.get_qeng_info('RSRQ')['RSRQ']   # noqa
        all_logger.info("检查信号值:")
        all_logger.info("*************************************************")
        all_logger.info("AT+QRSRP:")
        all_logger.info(f'prx:{prx}')
        all_logger.info(f'drx:{drx}')
        all_logger.info(f'rx2:{rx2}')
        all_logger.info(f'rx3:{rx3}')
        all_logger.info('AT+QENG="servingcell":')
        all_logger.info(f'RSRP:{RSRP}')
        all_logger.info(f'SINR:{SINR}')
        all_logger.info(f'RSRQ:{RSRQ}')
        all_logger.info("*************************************************")
        for i in prx, drx, rx2, rx3, RSRP:
            if int(i) > -90:
                raise QSSLimitRAndIError(f"信号值异常，当前信号值不在弱信号范围：{i}")

    def check_qss_network_bands(self, enb_file_name_now):
        # 检查注网是否正常
        all_logger.info(f"开始检查 {enb_file_name_now} 注网后band是否正常")
        return_qeng = self.at_handle.send_at('AT+qeng="servingcell"', 3)
        # CA
        if '-CA-' in enb_file_name_now.upper():
            return_qcainfo = self.at_handle.send_at('AT+QCAINFO', 3)
            all_logger.info(return_qcainfo)
            qss_file_sa_bands = re.findall(r'N(\d+)', enb_file_name_now.upper())
            qss_file_lte_bands = re.findall(r'B(\d+)', enb_file_name_now.upper())
            qcainfo_sa_bands = re.findall(r'NR5G\sBAND\s(\d+)', return_qcainfo)
            qcainfo_lte_bands = re.findall(r'LTE\sBAND\s(\d+)', return_qcainfo)
            if qss_file_sa_bands[0] != '':
                for band in qss_file_sa_bands[0]:
                    if band not in qcainfo_sa_bands:
                        all_logger.info(f"CA注网异常: {self.enb_file_name}")
                        return False
            if qss_file_lte_bands[0] != '':
                for band in qss_file_lte_bands[0]:
                    if band not in qcainfo_lte_bands:
                        all_logger.info(f"CA注网异常: {self.enb_file_name}")
                        return False
        # SA
        elif 'NR5G-SA' in return_qeng and '-SA-' in enb_file_name_now.upper():
            qeng_sa_band = ''.join(
                re.findall(r'\+QENG:\s"servingcell",".*",".*",".*",\s?.*,.*,.*,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*',
                           return_qeng))
            qss_file_sa_band = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            if qeng_sa_band != qss_file_sa_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        # NSA
        elif 'NR5G-NSA' in return_qeng and '-NSA-' in enb_file_name_now.upper():
            self.at_handle.send_at('AT+CFUN=0', 10)
            self.at_handle.send_at('AT+CFUN=1', 10)
            self.at_handle.check_network()
            return_qeng = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            if '-32768,-32768,-32768' in return_qeng:
                all_logger.info(f"注网NSA异常：{return_qeng}")
                return False
            qeng_sa_band = ''.join(re.findall(r'\+QENG:\s"NR5G-NSA",.*,.*,.*,.*,.*,.*,.*,(.*),.*,.*', return_qeng))
            qss_file_sa_band = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            if qeng_sa_band != qss_file_sa_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
            qeng_lte_band = ''.join(
                re.findall(r'\+QENG:\s"LTE",".*",.*,\d+,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*,.*,.*,.*,.*', return_qeng))
            qss_file_lte_band = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if qeng_lte_band != qss_file_lte_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        # LTE
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng and '-LTE-' in enb_file_name_now.upper():
            qeng_lte_band = ''.join(
                re.findall(r'\+QENG:\s"servingcell",".*",".*",".*",.*,\d+,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*,.*,.*,.*,.*',
                           return_qeng))
            qss_file_lte_band = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if qeng_lte_band != qss_file_lte_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return False

        all_logger.info("注网正常")
        return True

    def check_network(self, timeout=300, times=2):
        """
        连续多次检查模块驻网。每次之间切换cfun
        :return: False: 模块没有注上网。cops_value:模块注册的网络类型，
        """
        all_logger.info("检查网络")
        check_network_start_time = time.time()
        times_now = 0
        while True:
            return_value = self.at_handle.send_at('AT+COPS?')
            cell_value = self.at_handle.send_at('AT+QENG="servingcell"')
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', return_value))
            if cops_value != '':
                all_logger.info("当前网络：{}".format(cops_value))
                all_logger.info("当前小区信息：{}".format(cell_value))
                time.sleep(1)
                return cops_value
            if time.time() - check_network_start_time > timeout:
                all_logger.error("{}内找网失败".format(timeout))
                all_logger.info("当前小区信息：{}".format(cell_value))
                check_network_start_time = time.time()
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(10)
                times_now += 1
            if times_now == times:
                all_logger.error("连续{}次找网失败".format(times))
                all_logger.info("当前小区信息：{}".format(cell_value))
                all_logger.info(f'找网失败:{self.enb_file_name}')
                raise QSSLimitRAndIError("连续{}次找网失败".format(times))
            time.sleep(1)

    def dump_check(self, time_out=300):
        start_time = time.time()
        while time.time() - start_time < time_out:
            port_list = self.at_handle.get_port_list()
            if self.dm_port in port_list and self.at_port not in port_list:  # 发现仅有DM口并且没有AT口
                time.sleep(3)  # 等待3S口还是只有AT口没有DM口判断为DUMP，RG502QEAAAR01A01M4G出现两个口相差1秒
                port_list = self.at_handle.get_port_list()
                if self.dm_port in port_list and self.at_port not in port_list:
                    all_logger.error('模块DUMP')
                    raise QSSLimitRAndIError(f'模块出现DUMP!{port_list}')
        else:
            all_logger.info(f'{time_out}s内模块没有出现DUMP')

    def limit_r_and_i_check(self, timeout=180):
        """
        检查限R&I是否生效
        """
        all_logger.info("限R&I版本检查网络")
        check_network_start_time = time.time()
        while True:
            return_value = self.at_handle.send_at('AT+COPS?')
            cell_value = self.at_handle.send_at('AT+QENG="servingcell"')
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', return_value))
            if cops_value != '':
                all_logger.info("当前网络：{}".format(cops_value))
                all_logger.info("当前小区信息：{}".format(cell_value))
                raise QSSLimitRAndIError(f"异常!禁R&I版本查询COPS有值")
            if time.time() - check_network_start_time > timeout:
                all_logger.error("和预期一致，限R&I版本 {} 内找网失败".format(timeout))
                all_logger.info("当前小区信息：{}".format(cell_value))
                return_qscan = self.at_handle.send_at("AT+QSCAN=3", 180)
                all_logger.info(return_qscan)
                return True
            time.sleep(1)

    def open_qss(self, imsi, ccid='8949024', need_check_network=True, ims_open=False, tesk_duration=300):
        """
        imsi, ccid : 写卡使用到的imsi和ccid开头
        need_check_network : 是否需要检查注网
        ims_open： 是否需要开启ims文件
        """
        # 将卡写成00101卡
        self.write_simcard_r_or_i(imsi, ccid)

        all_logger.info(f'self.enb_file_name:{self.enb_file_name}')
        if ims_open:
            task = [self.mme_file_name, self.enb_file_name, self.ims_file_name]
        else:
            task = [self.mme_file_name, self.enb_file_name]
        qss_connection = self.get_qss_connection(tesk_duration, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QSSLimitRAndIError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(20)

        # 是否需要检查开网后是否注网正常
        if need_check_network:
            check_network_result = self.check_network()
            if not check_network_result:
                raise QSSLimitRAndIError('注网异常')
            # 检查注网后的bands是否对应
            check_bands_result = self.check_qss_network_bands(self.enb_file_name)
            if not check_bands_result:
                raise QSSLimitRAndIError('检查注网后的bands异常')

        return start_time, qss_connection

    def write_simcard_r_or_i(self, imsi, ccid):
        """
        将卡写成指定运营商的卡
        """
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith(imsi):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard(imsi, ccid)

    def write_simcard(self):
        # 将卡写成00101卡
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('00101'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('00101', '8949024')

    def qss_call(self):
        self.at_handle.send_at('ATD666;', 3)
        time.sleep(3)
        return_call = self.at_handle.send_at('AT+CLCC', 3)
        if 'CLCC: 3,0,0,0,0,"666"' in return_call:
            all_logger.info(f"通话正常:{return_call}")
            return True
        else:
            all_logger.info(f"通话异常:{return_call}")
            return False

    def get_qss_connection(self, tesk_duration=300, task_status=0, task=None):
        param_dict = {
            'name_group': 'QSS_Weak_Signal',  # 发起任务的用例名称(可以从下发消息中获取)
            'node_name': self.node_name,  # 发起任务的设备名称(可以从下发消息中获取)
            'ip': self.local_ip,  # 发起任务的设备IP地址(可以从下发消息中获取)
            'qss_ip': self.qss_ip,  # 所用qss服务器的IP
            'tesk_duration': tesk_duration,  # 任务持续时间或者需要增加的时间
            'task_status': task_status,  # 任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
            'task': task,  # 任务内容(需要开启网络的mme\enb\ims等文件名称列表)
        }
        qss_json_now = ConnectQSS.create_qss_task_json(**param_dict)
        servet_test = ConnectQSS(self.qss_ip, self.local_ip, qss_json_now)
        return servet_test

    @staticmethod
    def end_task(qss_connection):
        end_result = qss_connection.end_task()
        if end_result:
            all_logger.info("结束QSS成功")
        else:
            all_logger.info("结束QSS失败")

    @staticmethod
    def delay_task(start_time, qss_connection, time_need):
        if time.time() - start_time < time_need:
            delay_result = qss_connection.delay_task(time_need)
            if delay_result:
                all_logger.info("延时qss成功")
            else:
                all_logger.info('延时qss异常')

    def get_network(self):
        return_qeng = self.at_handle.send_at('AT+QENG="servingcell"', 3)
        all_logger.info(return_qeng)
        if 'NR5G-SA' in return_qeng:
            network_mode = 'SA'
        elif 'NR5G-NSA' in return_qeng:
            network_mode = 'NSA'
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng:
            network_mode = 'LTE'
        elif 'WCDMA' in return_qeng:
            network_mode = 'WCDMA'
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return 'No Network'
        all_logger.info(f"当前注网模式为：{network_mode}")
        return network_mode

    def get_cimi(self):
        rerurn_cimi = self.at_handle.send_at("AT+CIMI", 3)
        cimi_value = ''.join(re.findall(r'(\d.*)\r', rerurn_cimi))
        if cimi_value != '':
            all_logger.info(f"当前CIMI为 : {cimi_value}")
            return cimi_value
        else:
            all_logger.info("获取CIMI失败！")
            return False

    def get_qrsrp(self):
        qrsrp_value = self.at_handle.send_at("AT+QRSRP")
        all_logger.info(qrsrp_value)
        prx = ''
        drx = ''
        rx2 = ''
        rx3 = ''
        try:
            rx = re.findall(r'\+QRSRP:\s(.?\d+),(.?\d+),(.?\d+),(.?\d+),\w+', qrsrp_value)
            prx, drx, rx2, rx3 = rx[0][0], rx[0][1], rx[0][2], rx[0][3]
        except Exception as e:
            all_logger(e)
        finally:
            return prx, drx, rx2, rx3

    def get_imei(self):
        rerurn_imei = self.at_handle.send_at("AT+EGMR=0,7", 3)
        imei_value = ''.join(re.findall(r'EGMR:\s"(.*)"', rerurn_imei))
        if imei_value != '':
            all_logger.info(f"当前模块imei为 : {imei_value}")
            return imei_value
        else:
            all_logger.info("获取模块imei失败！")
            return False

    def get_ccid(self):
        rerurn_ccid = self.at_handle.send_at("AT+CCID", 3)
        ccid_value = ''.join(re.findall(r'CCID:\s(.*)\r', rerurn_ccid))
        if ccid_value != '':
            all_logger.info(f"当前CCID为 : {ccid_value}")
            return ccid_value
        else:
            all_logger.info("获取CCID失败！")
            return False

    @staticmethod
    def get_driver_version(dial):
        driver_version = ''
        if dial == 'QMI':
            modinfo_value = subprocess.getoutput('modinfo qmi_wwan_q')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\sversion:\s+(.*)', modinfo_value))
        elif dial == 'GobiNet':
            modinfo_value = subprocess.getoutput('modinfo GobiNet')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\sversion:\s+(.*)', modinfo_value))
        elif "PCIE" in dial:
            modinfo_value = subprocess.getoutput('dmesg | grep mhi')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\smhi_init\s(Quectel.*)', modinfo_value))

        return driver_version

    def bound_network(self, network_type):
        """
        固定指定网络
        :param network_type: 取值：SA/NSA/LTE/WCDMA
        """
        # 固定网络
        network_type = network_type.upper()  # 转换为大写

        all_logger.info("固定网络到{}".format(network_type))
        if network_type in ["LTE", "WCDMA"]:  # 固定LTE或者WCDMA
            self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref",{}'.format(network_type))
        elif network_type == 'SA':  # 固定SA网络
            self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref",NR5G')
        elif network_type == "NSA":  # 使用nr5g_disable_mode进行SA和NSA偏号设置
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",1')
        else:
            all_logger.info("不支持的网络类型设置")
            raise QSSLimitRAndIError("不支持的网络类型设置")

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            all_logger.error('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')
            return False

    def get_qeng_info(self, *search_info):
        """
        获取qeng中的关键信息(所查询参数需要严格和照下面<>中的的同名)

        In SA mode:
        +QENG: "servingcell",<state>,"NR5G-SA",<duplex_mode>,<MCC>,<MNC>,<cellID>,<PCID>,<TAC>,<ARFCN>,<band>,<NR_DL_bandwidth>,<RSRP>,<RSRQ>,<SINR>,<scs>,<srxlev>  # noqa

        In EN-DC mode:
        +QENG: "servingcell",<state>
        +QENG: "LTE",<is_tdd>,<lte_MCC>,<lte_MNC>,<cellID>,<lte_PCID>,<earfcn>,<freq_band_ind>,<UL_bandwidth>,<lte_DL_bandwidth>,<TAC>,<RSRP>,<lte_RSRQ>,<RSSI>,<SINR>,<CQI>,<tx_power>,<srxlev>  # noqa
        +QENG: "NR5G-NSA",<MCC>,<MNC>,<PCID>,<RSRP>,<SINR>,<RSRQ>,<ARFCN>,<band>,<NR_DL_bandwidth>,<scs>

        +QENG: "servingcell","NOCONN"
        +QENG: "LTE","FDD",460,00,1A2D001,1,1300,3,5,5,1,-55,-6,-29,19,0,-,84
        +QENG: "NR5G-NSA",460,00,65535,-32768,-32768,-32768

        OK

        AT+QENG="servingcell"
        +QENG: "servingcell","NOCONN"
        +QENG: "LTE","FDD",460,01,5F1EA15,12,1650,3,5,5,DE10,-99,-12,-67,11,9,230,-
        +QENG:"NR5G-NSA",460,01,747,-71,33,-11,627264,78,12,1

        In LTE mode:
        +QENG: "servingcell",<state>,"LTE",<is_tdd>,<MCC>,<MNC>,<cellID>,<PCID>,<earfcn>,<freq_band_ind>,<UL_bandwidth>,<DL_bandwidth>,<TAC>,<RSRP>,<RSRQ>,<RSSI>,<SINR>,<CQI>,<tx_power>,<srxlev>  # noqa

        In WCDMA mode:
        +QENG: "servingcell",<state>,"WCDMA",<MCC>,<MNC>,<LAC>,<cellID>,<uarfcn>,<PSC>,<RAC>,<RSCP>,<ecio>,<phych>,<SF>,<slot>,<speech_code>,<comMod>

        """
        qeng_info = {}
        search_result = {}
        qeng_values = []
        keys = ''
        all_logger.info(f'开始查询{search_info}')
        return_qeng = self.at_handle.send_at('AT+QENG="servingcell"', 3)
        all_logger.info(return_qeng)
        if 'SEARCH' in return_qeng:
            state = 'SEARCH'
            all_logger.info(f"{state} : UE正在搜索，但（还）找不到合适的 3G/4G/5G 小区")
            return False
        elif 'LIMSRV' in return_qeng:
            state = 'LIMSRV'
            all_logger.info(f"{state} : UE正在驻留小区，但尚未在网络上注册")
            return False
        elif 'NOCONN' in return_qeng:
            state = 'NOCONN'
            all_logger.info(f"{state} : UE驻留在小区并已在网络上注册，处于空闲模式")
        elif 'CONNECT' in return_qeng:
            state = 'CONNECT'
            all_logger.info(f"{state} : UE正在驻留小区并已在网络上注册，并且正在进行呼叫")
        else:
            all_logger.info("未知状态!")

        if 'NR5G-SA' in return_qeng:
            network_mode = 'SA'
        elif 'NR5G-NSA' in return_qeng:
            network_mode = 'NSA'
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng:
            network_mode = 'LTE'
        elif 'WCDMA' in return_qeng:
            network_mode = 'WCDMA'
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return False
        all_logger.info(f"当前注网模式为：{network_mode}")

        if network_mode == 'SA':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*","(.*)",\s?(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',  # noqa
                return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values[0]}')
                return False
            keys = ['state', 'duplex_mode', 'MCC', 'MNC', 'cellID', 'PCID', 'TAC', 'ARFCN', 'band', 'NR_DL_bandwidth',
                    'RSRP', 'RSRQ', 'SINR', 'scs', 'srxlev']

        elif network_mode == 'NSA':
            qeng_state = re.findall(r'\+QENG: "servingcell","(.*)"', return_qeng)
            if '-32768,-32768,-32768' in return_qeng:
                all_logger.info(f"注网NSA异常：{return_qeng}")
                return False
            qeng_values_lte = re.findall(
                r'\+QENG:\s"LTE","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',  # noqa
                return_qeng)
            qeng_values_nr5g = re.findall(r'\+QENG:\s"NR5G-NSA",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',  # noqa
                                          return_qeng)
            qeng_values_all = tuple(qeng_state) + qeng_values_lte[0] + qeng_values_nr5g[0]
            # all_logger.info(qeng_values_all)
            if len(qeng_values_all) != 28:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values_all}')
                return False
            key_state = ['state']
            keys_lte = ['is_tdd', 'lte_MCC', 'lte_MNC', 'cellID', 'lte_PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth',
                        'lte_DL_bandwidth', 'TAC', 'lte_RSRP', 'lte_RSRQ', 'RSSI', 'lte_SINR', 'CQI', 'tx_power',
                        'srxlev']
            keys_nr5g = ['MCC', 'MNC', 'PCID', 'RSRP', 'SINR', 'RSRQ', 'ARFCN', 'band', 'NR_DL_bandwidth', 'scs']
            keys = key_state + keys_lte + keys_nr5g
            # all_logger.info(keys)
            qeng_values.append(qeng_values_all)

        elif network_mode == 'LTE':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',  # noqa
                return_qeng)
            if len(qeng_values[0]) != 18:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values[0]}')
                return False
            keys = ['state', 'is_tdd', 'MCC', 'MNC', 'cellID', 'PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth',
                    'DL_bandwidth', 'TAC', 'RSRP', 'RSRQ', 'RSSI', 'SINR', 'CQI', 'tx_power', 'srxlev']

        elif network_mode == 'WCDMA':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',  # noqa
                return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            keys = ['state', 'MCC', 'MNC', 'LAC', 'cellID', 'uarfcn', 'PSC', 'RAC', 'RSCP', 'ecio', 'phych', 'SF',
                    'slot', 'speech_code', 'comMod']

        for i in range(len(qeng_values[0])):
            qeng_info[keys[i]] = qeng_values[0][i]
        # all_logger.info(qeng_info)

        for j in range(len(search_info)):
            if search_info[j] not in qeng_info.keys():
                all_logger.info(f"所查找的内容不存在:{search_info[j]}")
                return False
            else:
                search_result[search_info[j]] = qeng_info[search_info[j]]
        all_logger.info(search_result)
        return search_result

    @staticmethod
    def load_qmi_wwan_q_drive():
        """
        加载qmi驱动
        :return:
        """
        all_logger.info('开始卸载所有网卡驱动')
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

        time.sleep(5)
        all_logger.info('开始加载qmi_wwan_q网卡驱动')
        subprocess.run("modprobe -a qmi_wwan_q", shell=True)

    def udhcpc_get_ip(self, network_card_name):
        all_logger.info(f"udhcpc -i {network_card_name}")
        process = subprocess.Popen(f'udhcpc -i {network_card_name}',
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   shell=True)
        t = threading.Timer(120, self.process_input)
        t.setDaemon(True)
        t.start()
        get_result = ''
        while process.poll() is None:
            value = process.stdout.readline().decode()
            if value:
                all_logger.info(value)
                get_result += value
        all_logger.info(get_result)

    @staticmethod
    def process_input():
        subprocess.Popen("killall udhcpc", shell=True)

    def vbat(self):
        # VBAT断电
        self.gpio.set_vbat_high_level()
        # 检测驱动消失
        self.driver_check.check_usb_driver_dis()
        # VBAT开机
        time.sleep(1)
        self.gpio.set_vbat_low_level_and_pwk()
        # 检测驱动加载
        self.driver_check.check_usb_driver()

    def set_qsclk(self, mode=1):
        """
        :param mode:0: 设置开启不保存；1: 设置开启保存
        :return:
        """
        for i in range(3):
            self.at_handle.send_at('AT+QSCLK=1,{}'.format(1 if mode == 1 else 0))
            qsc_val = self.at_handle.send_at('AT+QSCLK?')
            if '+QSCLK: 1,{}'.format(1 if mode == 1 else 0) in qsc_val:
                return True
            time.sleep(1)
        else:
            raise QSSLimitRAndIError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

    @staticmethod
    def linux_enter_low_power(level_value=True, wakeup=True):
        """
        Linux需要休眠首先dmesg查询USB节点，然后设置节点的autosuspend值为1，level值为auto，wakeup值为enabled
        :return: None
        """
        dmesg_data = os.popen('dmesg').read()
        dmesg_data_regex = re.findall(r'usb\s(\d+-\d+):.*Quectel.*', dmesg_data)
        if dmesg_data_regex:
            node_list = list(set(dmesg_data_regex))
            for node in node_list:
                node_path = os.path.join('/sys/bus/usb/devices/', node, 'power')
                autosuspend = 'cd {} && echo 1 > {}'.format(node_path, 'autosuspend')
                level = 'cd {} && echo {} > {}'.format(node_path, 'auto' if level_value else 'on', 'level')
                wakeup = 'cd {} && echo {} > {}'.format(node_path, 'enabled' if wakeup else 'disabled', 'wakeup')
                commands = [autosuspend, level, wakeup]
                for command in commands:
                    try:
                        all_logger.info(command)
                        s = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                        out, error = s.communicate()
                        all_logger.info([out, error])
                    except Exception as e:
                        all_logger.info(e)
        if level_value:
            all_logger.info('已更改autosuspend 、level、wakeup值为进入慢时钟')
        else:
            all_logger.info('已更改autosuspend 、level、wakeup值为退出慢时钟')

    def debug_check(self, is_low_power, times=12, is_at=False, sleep=True):
        """
        每隔5S循环检测debug口是否通指令，期望进入慢时钟后debug口输入无返回值，默认超时时间为60S
        :param is_low_power: 是否进入慢时钟,True:进入；False:未进入
        :param times: 检测次数
        :param is_at: 是否需要发送AT后再检测debug口情况
        :param sleep: 是否需要等待
        :return:
        """
        for i in range(times):
            if sleep:
                time.sleep(5)
            if is_at:
                self.at_handle.send_at('AT')
            with serial.Serial(self.debug_port, baudrate=115200, timeout=0) as _debug_port:
                _debug_port.flushOutput()
                _debug_port.write('\r\n'.encode('utf-8'))
                start_time = time.time()
                value = ''
                while True:
                    value += _debug_port.readline().decode('utf-8', 'ignore')
                    if time.time() - start_time > 1:
                        break
                if is_low_power:  # 期望模块已进入慢时钟检测Debug口
                    if value:  # 如果有返回值代表还未进入慢时钟，等待五秒后在检查
                        all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通,等待5S后再次检测')
                        all_logger.info(value)
                        continue
                    else:
                        all_logger.info('检测debug口无返回值，正常')
                        return True
                else:  # 期望模块未进入慢时钟检测Debug口
                    if value:
                        all_logger.info(value.replace('\r\n', ''.strip()))
                        all_logger.info('检测debug口有返回值，正常')
                        return True
                    else:  # 如果无返回值代表模块仍未退出慢时钟，等待5S后再检查
                        all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出,等待5S后再次检测')
                        continue
        else:
            if is_low_power:  # 期望模块已进入慢时钟检测Debug口
                all_logger.info(value.replace('\r\n', ''.strip()))
                all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
                raise QSSLimitRAndIError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise QSSLimitRAndIError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def close_lowpower(self):
        """
        发送指令退出慢时钟
        :return: True
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=0,0')
            if 'OK' in val:
                return True
        else:
            raise QSSLimitRAndIError('退出慢时钟失败')


class ATBackgroundThreadWithDriverCheck(threading.Thread):
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
                all_logger.info(e)
                time.sleep(0.1)
                continue
        else:
            raise QSSLimitRAndIError("检测DFOTA升级时打开AT口异常")

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
                        all_logger.debug("{} {}".format("RECV", repr(buf).replace("'", '')))
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > 1:
                        all_logger.info('{}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            all_logger.error('Fatal ERROR: {}'.format(error))
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
