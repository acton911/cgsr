import serial

from utils.functions.qfil import QFIL
from utils.functions.qfirehose import QFirehose
from utils.functions.fw import FW
from utils.functions.case import need_upgrade, upload_step_log, is_laptop
from utils.functions.gpio import GPIO
from utils.exception.exceptions import FatalError
from utils.logger.logging_handles import all_logger
from utils.functions.driver_check import DriverChecker
from utils.operate.at_handle import ATHandle
import subprocess
import time
import os
import re
import getpass
import shutil
import sys


class StartupManager:
    def __init__(self, **kwargs):
        # 参数处理
        self.version_upgrade = 1  # factory版本包，会被__update_args方法更新为系统下发的参数
        self.need_upgrade = True   # 默认需要升级，会被__update_args方法更新为TWS系统下发的参数
        self.factory = False  # 升级工厂还是标准，会被__update_args方法更新为TWS系统下发的参数
        self.__update_args(kwargs)  # 更新传参
        self.__handle_args()  # 打印和初始化一些参数
        self.__update_laptop_args()  # !!!判断是否是笔电，如果是笔电，更新一些参数
        self.is_audio = True if 'AUDIO' in self.args.device_number.upper() else False  # noqa 判断是否是audio设备，如果设备名称包含audio则判定为audio设备
        # 实例化
        self.__check_gpio_config()
        self.gpio = GPIO()
        self.driver_handle = DriverChecker(self.at_port, self.dm_port)
        self.at_handle = ATHandle(self.at_port)
        if self.is_laptop:  # 笔电设备，使用FW
            self.fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                         factory=self.factory, ati=self.ati, csub=self.csub, imei=self.imei, sn=self.sn)  # noqa 此处增加IMEI和SN参考restore_imei_sn_and_ect函数注释，正常Python调用不需要，会自动查找
        elif os.name == "nt":  # 普通Windows设备，使用QFil
            self.qfil = QFIL(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                             factory=self.factory, ati=self.ati, csub=self.csub, imei=self.imei, sn=self.sn) # noqa 此处增加IMEI和SN参考restore_imei_sn_and_ect函数注释，正常Python调用不需要，会自动查找
        else:  # Ubuntu使用QFirehose
            self.qfirehose = QFirehose(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                                       factory=self.factory, ati=self.ati, csub=self.csub,
                                       package_name=self.name_sub_version, imei=self.imei, sn=self.sn) # noqa 此处增加IMEI和SN参考restore_imei_sn_and_ect函数注释，正常Python调用不需要，会自动查找

    def __getattr__(self, item):
        return self.__dict__.get(item)

    def __update_args(self, kwargs):
        for k, v in kwargs.items():
            all_logger.info(f"{k}: {v}")
            if v == '':
                raise FatalError(f"\n系统参数 '{k}'\nrepr(k): {repr(k)}，值异常，请检查log ")
            setattr(self, k, v)

    def __update_laptop_args(self):
        laptop = is_laptop(self.args.name_real_version)  # 判断是否是笔电版本
        if laptop is True:  # 是笔电版本
            self.is_laptop = True
            # self.factory = False
            all_logger.info(f"\n当前版本{self.ati}判断为笔电版本，factory：{self.factory}" * 3)
        else:
            self.is_laptop = False

    def __handle_args(self):
        """
        初始化和打印必须参数。
        :return:
        """
        all_logger.info(f"\nversion_type: {self.version_type}\ntype(version_type): {type(self.version_type)}"
                        f"\nversion_upgrade: {self.version_upgrade}\ntype(version_upgrade): {type(self.version_upgrade)}")
        self.factory = False if self.version_type == 2 else True  # 只有系统指定标准包才升级标准包，否则都使用工厂包
        self.need_upgrade = need_upgrade(self.at_port, self.ati, self.csub, self.qgmr)  # 根据版本判断是否需要升级

    @staticmethod
    def __check_gpio_config():
        """
        个人测试机如果没有运行过micropython没有这个文件会导致异常，所以检测是否有文件，没有则复制。
        :return: None
        """
        all_logger.info(f"cwd: {os.getcwd()}")
        all_logger.info(f"sys.argv[0]: {sys.argv[0]}")
        gpio_config_path = os.path.join(os.path.dirname(sys.argv[0]), 'tools', 'micropython', 'gpio_config.ini')
        all_logger.info(f"gpio_config_path: {gpio_config_path}, {os.path.exists(gpio_config_path)}")
        try:
            if os.name == 'nt':
                config_path = os.path.join("C:\\Users", getpass.getuser(), 'gpio_config.ini')
            else:
                config_path = os.path.join('/root', 'gpio_config.ini')
            if not os.path.exists(config_path):
                shutil.copy(gpio_config_path, config_path)
        except Exception as e:
            all_logger.error(e)

    def emergency_download_mode_check(self):
        """
        检查当前是否是紧急下载模式，如果是紧急下载模式，进行恢复操作
        :return: None
        """
        if os.name == 'nt':
            self.windows_emergency_download_mode_check()
        else:
            self.linux_emergency_download_mode_check()

    def windows_emergency_download_mode_check(self):
        """
        Windows的紧急下载模式恢复流程，注意根据恢复状态决定下一步升级是否要升级。
        :return: None
        """
        it_is_edl = self.qfil.get_download_port()
        if it_is_edl:
            all_logger.info("当前是紧急下载模式，尝试重启恢复")
            self.gpio.set_vbat_high_level()
            time.sleep(1)
            self.gpio.set_vbat_low_level_and_pwk()

            all_logger.info("等待10S")
            time.sleep(10)

            # 重启后判断是否是紧急下载模式
            it_is_edl = self.qfil.get_download_port()
            if it_is_edl:
                all_logger.info("重启后还是紧急下载模式，尝试升级")
                self.qfil.qfil_edl()
                self.need_upgrade = False
                self.version_upgrade = 0
            else:
                port_list = [self.at_port, self.dm_port]
                self.qfil.check_port_load(port_list)
                all_logger.info("等待30S")
                time.sleep(30)
                self.need_upgrade = True  # 紧急模式重启能正常开机的，默认需要重新升级

    def linux_emergency_download_mode_check(self):
        """
        Linux的紧急下载模式恢复流程，注意根据恢复状态决定下一步升级是否要升级。
        :return: None
        """
        is_edl = self.qfirehose.linux_edl_check()
        if is_edl:
            all_logger.info("当前是紧急下载模式，尝试重启恢复")
            self.gpio.set_vbat_high_level()
            time.sleep(1)
            self.gpio.set_vbat_low_level_and_pwk()

            all_logger.info("等待10S")
            time.sleep(10)

            # 重启后判断是否是紧急下载模式
            is_edl = self.qfirehose.linux_edl_check()
            if is_edl:
                all_logger.info("重启后还是紧急下载模式，尝试升级")
                self.qfirehose.linux_upgrade()
                self.need_upgrade = False
                self.version_upgrade = 0
            else:
                port_list = [self.at_port, self.dm_port]
                self.qfirehose.check_usb_loaded(port_list)
                all_logger.info("等待30S")
                time.sleep(30)
                self.need_upgrade = True  # 紧急模式重启能正常开机的，默认需要重新升级

    def upgrade(self):
        """
        判断是否要进行升级操作，如果要升级，则升级。
        :return: None
        """
        if self.need_upgrade or self.version_upgrade:  # 系统下发需要升级(version_upgrade=1)或版本不匹配，则进行升级
            upload_step_log(self.args.task_id, "开始进行升级")
            if self.version_type == 0:  # 系统Resource设备Version参数没有勾选或者为None
                upload_step_log(self.args.task_id, "系统Resource设备Version参数没有勾选或者为None, 先升级工厂包，后升级标准包")
                # 先升级工厂，不需要修改factory参数
                start_timestamp1 = time.time()
                if self.is_laptop:
                    self.fw.upgrade()
                elif os.name == 'nt':
                    self.qfil.qfil()
                else:
                    self.qfirehose.linux_upgrade()
                upload_step_log(self.args.task_id, f"升级工厂包结束，耗时{round(time.time() - start_timestamp1, 2)}s，即将升级标准")
                # 再升级标准，修改factory参数
                if self.is_laptop:
                    self.fw.factory_to_standard()
                    self.fw.upgrade()
                elif os.name == 'nt':
                    self.qfil.factory_to_standard()
                    self.qfil.qfil()
                else:
                    self.qfirehose.factory_to_standard()
                    self.qfirehose.linux_upgrade()
                upload_step_log(self.args.task_id, f"升级标准包结束，升级工厂和标准包共耗时{round(time.time() - start_timestamp1, 2)}s")
            elif self.version_type == 1:  # 系统Resource设备Version参数设置为Factory
                upload_step_log(self.args.task_id, "系统Resource设备Version参数设置为Factory, 仅升级工厂包")
                start_timestamp = time.time()
                if self.is_laptop:
                    self.fw.upgrade()
                elif os.name == 'nt':
                    self.qfil.qfil()
                else:
                    self.qfirehose.linux_upgrade()
                upload_step_log(self.args.task_id, f"升级工厂包结束，耗时{round(time.time() - start_timestamp, 2)}s")
            else:  # 系统Resource设备Version参数设置为Standard
                upload_step_log(self.args.task_id, "系统Resource设备Version参数设置为Standard, 仅升级标准包")
                start_timestamp = time.time()
                if self.is_laptop:
                    self.fw.upgrade()
                elif os.name == 'nt':
                    self.qfil.qfil()
                else:
                    self.qfirehose.linux_upgrade()
                upload_step_log(self.args.task_id, f"升级标准包结束，耗时{round(time.time() - start_timestamp, 2)}s")
        else:
            upload_step_log(self.args.task_id, "当前版本无需升级")

    def power_on_check(self):
        """
        检测当前是否是开机状态，如果不是开机状态，尝试恢复。
        :return: None
        """
        all_logger.info("检测模块是否正常开机")
        port_list = self.driver_handle.get_port_list()
        if self.at_port not in port_list or self.dm_port not in port_list:
            all_logger.error("模块未正常开机，尝试VBAT重启")
            self.gpio.set_vbat_high_level()
            self.driver_handle.check_usb_driver_dis()
            time.sleep(1)
            self.gpio.set_vbat_low_level_and_pwk()
            driver_status = self.driver_handle.check_usb_driver()
            if driver_status is False:
                raise FatalError(f"模块尝试重启异常, 可能是：\n1. AT口或DM口未加载，当前端口列表：{self.driver_handle.get_port_list()}\n"
                                 f"2. 可能是TWS系统端口列表填写错误或端口发生变化")
        all_logger.info("模块已正常开机")

    def ndis_driver_resume(self):
        """
        如果是Windows并且USBNET为0，且驱动不对，尝试自己安装后重启。
        :return: None
        """
        # 非Windows，退出
        if os.name != "nt":
            return True

        # 非USBNET0，退出
        usbnet = self.at_handle.send_at('AT+QCFG="USBNET"', timeout=3)
        if ',0' not in usbnet:
            return True

        # 网卡名获取检测
        from utils.functions.setupapi import get_network_card_names
        network_card_names = ''.join(get_network_card_names())
        if 'QUECTEL WIRELESS' not in network_card_names.upper():
            # 查找驱动
            driver_path = ''
            for path, dirs, files in os.walk('C:\\Program Files (x86)'):
                for file in files:
                    if 'qcwwan.inf' in file and 'windows10' in path:
                        driver_path = os.path.join(path, file)
            if driver_path == '':
                all_logger.info("未检测到NDIS驱动安装，请重新安装模块驱动到默认路径")
                return False
            driver_path = driver_path.replace('&', '"&"')
            # 装载
            all_logger.info(f"powershell pnputil /add-driver '{driver_path}'")
            return_code, output = subprocess.getstatusoutput(f"powershell pnputil /add-driver '{driver_path}'")
            if return_code == 0:
                all_logger.info("NDIS驱动装载成功")
            else:
                all_logger.error(f"NDIS驱动加载失败：{output}")
                return False

            # 装载驱动成功后需要重启
            all_logger.info("wait 10 seconds")
            time.sleep(10)
            self.at_handle.send_at("AT+CFUN=1,1", timeout=3)
            self.driver_handle.check_usb_driver_dis()
            self.driver_handle.check_usb_driver()
            all_logger.info("wait 30 seconds")
            time.sleep(30)

    def sim_switch(self, port):
        """
        使用切卡器进行切卡操作
        :param port:
        :return:
        """
        all_logger.info(f'打开切卡器端口{port}进行SIMSWITCH操作')
        with serial.Serial(port, baudrate=115200, timeout=0) as _switch_port:
            _switch_port.setDTR(False)
            time.sleep(1)
            start_time = time.time()
            _switch_port.write("SIMSWITCH,1\r\n".encode('utf-8'))
            while time.time() - start_time < 3:
                value = _switch_port.readline().decode('utf-8', 'ignore')
                if value:
                    all_logger.info(value)
                if 'OK' in value:
                    break
        self.at_handle.send_at('AT+CFUN=0', 15)
        time.sleep(1)
        self.at_handle.send_at('AT+CFUN=1', 15)

    def restore_sim_switch(self):
        """
        恢复切卡器至卡槽一
        """
        switch_info = self.args.switcher
        all_logger.info(switch_info)
        if switch_info:     # 如果没有安装切卡器，就不做切卡器相关操作
            all_logger.info('恢复切卡器至卡槽一')
            if os.name == 'nt':
                switch_1_port = ''.join(re.findall(r'COM\d+', switch_info[0]))
            else:
                switch_1_port = '/dev/ttyUSBSWITCHER'
            self.sim_switch(switch_1_port)
        time.sleep(10)

    def check_clck(self):
        all_logger.info("检查SIM卡锁状态")
        clck_status = self.at_handle.send_at('AT+CLCK="SC",2', timeout=5)
        if "CLCK: 0" in clck_status:
            all_logger.info("查询无SIM PIN锁")
            return True
        if "CLCK: 1" in clck_status:
            all_logger.error("查询有SIM PIN锁，尝试解锁")
            self.at_handle.send_at('AT+CLCK="SC",0,"1234"', timeout=5)
            self.check_clck()

    def check_cfun(self):
        all_logger.info("检查CFUN状态")
        cfun_status = self.at_handle.send_at("AT+CFUN?", timeout=15)
        all_logger.info(f"cfun_status: {cfun_status}")
        cfun_status_regex = ''.join(re.findall(r"CFUN:\s(\d+)", cfun_status))
        if "OK" in cfun_status and "1" not in cfun_status_regex:  # 异常

            # 尝试CFUN切换
            all_logger.error(f"CFUN值异常，当前CFUN值：{cfun_status_regex}，尝试恢复CFUN为1")
            self.reset_cfun()  # CFUN0、1切换尝试

            # 再次查询CFUN值
            cfun_status = self.at_handle.send_at("AT+CFUN?", timeout=3)
            all_logger.info(f"cfun_status: {cfun_status}")
            cfun_status_regex = ''.join(re.findall(r"CFUN:\s(\d+)", cfun_status))
            if "OK" in cfun_status and "1" not in cfun_status_regex:  # 还是异常
                raise FatalError(f"发送AT+CFUN?返回值异常，未检测到CFUN: 1，返回值为：{cfun_status}")
            else:
                return True

    def reset_cfun(self):
        all_logger.info("尝试恢复CFUN状态")
        self.at_handle.send_at("AT+CFUN=0", timeout=15)
        all_logger.info("等待5S")
        time.sleep(5)
        self.at_handle.send_at("AT+CFUN=1", timeout=15)
        all_logger.info("等待10S")
        time.sleep(10)

    def check_network(self):
        network_status = self.at_handle.check_network()
        if network_status is False:
            raise FatalError("初始化模块网络状态异常")

    def get_version(self):
        self.at_handle.send_at("ATI+CSUB", timeout=3)

    def get_mbn_status(self):
        for i in range(20):
            self.at_handle.send_at('at+cgdcont?', timeout=15)
            mbn_status = self.at_handle.send_at('at+qmbncfg="list"', timeout=15)
            if 'OK' in mbn_status and ",0,1,1" in mbn_status:
                break
            time.sleep(3)
        else:
            all_logger.error('case执行前初始化查询MBN列表异常')

    @staticmethod
    def _get_config_path():
        if os.name == 'nt':
            config_path = os.path.join("C:\\Users", getpass.getuser(), 'debug_mode')
        else:
            config_path = os.path.join('/root', 'debug_mode')
        return config_path

    def get_debug_flag(self):
        """
        设置是否是DEBUG模式，如果是DEBUG模式，则跳过升级
        :return:
        """
        debug_path = os.path.exists(self._get_config_path())
        if debug_path:
            all_logger.error("*" * 100)
            all_logger.error("* 当前为DEBUG模式，将不会进行升级等相关操作")
            all_logger.error("*" * 100)
            return True
        else:
            return False

    def switch_rtl8125(self):
        """
        如果当前case是rtl8125则拉高开关4，否则拉低（需要提前统一焊接和初始化所有开关位置）
        :return: None
        """
        if os.name == 'posix':
            all_logger.info(f"name_group: {self.args.name_group}")
            if 'RTL8125' in self.args.name_group or 'Eth' in self.args.name_group:
                all_logger.info("当前测试需要使用RTL8125，开始相关设置")
                self.gpio.set_rtl_8125_high_level()
            else:
                all_logger.info("当前测试不需要使含RTL8125")
                self.gpio.set_rtl_8125_low_level()
        else:
            all_logger.info('非Linux系统暂不考虑该引脚')

    def set_modem_port(self):
        """
        笔电项目设置上报口为modem
        @return:
        """
        all_logger.info('当前为笔电项目，设置上报口为Modem')
        self.at_handle.send_at('AT+QURCCFG="URCPORT","USBMODEM"', 3)

    def disable_low_power_registry(self):
        """
        修改注册表，使模块退出慢时钟
        :return:
        """
        import winreg
        reg_root = winreg.HKEY_LOCAL_MACHINE
        reg_path = r'SYSTEM\CurrentControlSet\Services\qcusbser'
        key = winreg.OpenKey(reg_root, reg_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            key_value = winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled")
            winreg.QueryValueEx(key, "QCDriverSelectiveSuspendIdleTime")
            if 0 in key_value:
                all_logger.info('已去激活注册表')
                return True
        except FileNotFoundError:   # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
        time.sleep(1)
        self.at_handle.send_at("AT+CFUN=1,1", timeout=3)
        self.driver_handle.check_usb_driver_dis()
        self.driver_handle.check_usb_driver()
        all_logger.info("wait 30 seconds")
        time.sleep(30)

    @staticmethod
    def linux_quit_low_power(level_value=False, wakeup=False):
        """
        Linux下设置退出慢时钟
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
                        sub = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                        out, error = sub.communicate()
                        all_logger.info([out, error])
                    except Exception as e:
                        all_logger.info(e)
        if level_value:
            all_logger.info('已更改autosuspend 、level、wakeup值为进入慢时钟')
        else:
            all_logger.info('已更改autosuspend 、level、wakeup值为退出慢时钟')

    def set_dump_mode(self):
        all_logger.info("Set DUMP Mode")
        # 设置系统不重启
        self.at_handle.send_at('AT+QCFG="ModemRstLevel",0', timeout=3)
        # 设置死机进DUMP
        self.at_handle.send_at('AT+QCFG="ApRstLevel",0', timeout=3)

    @staticmethod
    def umount_directory():
        """
        解除文件挂载
        @return:
        """
        dir_list = ['/mnt/firmware', '/mnt/cur', '/mnt/prev']
        for i in dir_list:
            all_logger.info(os.popen(f'umount {i}').read())

    def enable_sim_1(self):
        """
        笔电惠普定制默认关闭SIM1，要求把SIM1打开后重启
        :return:
        """
        # 设置系统不重启
        self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,0', timeout=3)
        # CFUN1,1重启
        self.at_handle.cfun1_1()
        self.driver_handle.check_usb_driver_dis()
        self.driver_handle.check_usb_driver()
        self.at_handle.check_urc()
        # 等待10s
        all_logger.info("wait 10 seconds.")
        time.sleep(10)

    def auto_insmode_pcie(self):
        """
        针对Ubuntu系统下的PCIE设备，初始化过程中检查是否正常加载PCIE驱动
        """
        lspci_value = os.popen('lspci').read()
        if 'Qualcomm Device 030' in lspci_value:    # x55:0306  x6x:0308
            all_logger.error('lspci查询检测到PCIE设备')
            return
        all_logger.info('未检测到PCIE设备，编译pcie驱动后进行安装')
        self.at_handle.send_at('AT+QCFG="DATA_INTERFACE",1,0', 15)
        pcie_path = ''
        for path, dirs, files in os.walk('/home/ubuntu'):
            for d in dirs:
                if d == 'pcie_mhi':
                    pcie_path = os.path.join(path, d)
                    all_logger.info(f'pcie_mhi目录为{pcie_path}')
                    break
            if pcie_path:
                break
        os.popen(f'make clean --directory {pcie_path}').read()
        time.sleep(1)
        os.popen(f'make --directory {pcie_path}').read()
        time.sleep(1)
        pcie_mhi_path = os.path.join(pcie_path, 'pcie_mhi.ko')
        time.sleep(1)
        os.popen(f'insmod {pcie_mhi_path}').read()
        self.at_handle.send_at('AT+CFUN=1,1', 15)
        self.driver_handle.check_usb_driver_dis()
        self.driver_handle.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=50)
        pcie_driver = os.popen('ls /dev/mhi*').read()
        if '/dev/mhi_DUN' not in pcie_driver and '/dev/mhi_BHI' not in pcie_driver:
            all_logger.error('未检测到PCIE驱动')
        else:
            all_logger.info('已检测到PCIE驱动')

    def resume_sim_det(self):
        """
        MH8100EUAC默认是低电平SIM卡检测，要恢复低电平检测
        引脚逻辑：
        1、AT+QSIMDET=0,0时，不受EVB引脚电平影响，无论EVB的SIM卡引脚为高/低电平，都能识别
        2、AT+QSIMDET=1,0时，EVB的SIM卡引脚必须为低电平，SIM卡才能识别
        3、AT+QSIMDET=1,1时，EVB的SIM卡引脚必须为高电平，SIM卡才能识别
        :return: None
        """
        # 先查询ATI和AT+QSIMDET?
        ati = self.at_handle.send_at('ATI', 3)
        sim_det = self.at_handle.send_at('AT+QSIMDET?', 3)

        # 如果是MH8001EUAC，并且QSIMDET是1,1
        if "MH8001EUAC" in ati and "+QSIMDET: 1,1" in sim_det:
            # 恢复为默认QSIMDET: 1,0
            self.at_handle.send_at('AT+QSIMDET=1,0', 3)

            # 恢复引脚默认电平
            self.gpio.set_sim1_det_low_level()
            self.gpio.set_sim2_det_low_level()

            # 重启后生效：CFUN1,1->检测驱动消失->检测USB驱动->检测URC->检测网络
            self.at_handle.send_at('AT+CFUN=1,1', 3)
            self.driver_handle.check_usb_driver_dis()
            self.driver_handle.check_usb_driver()
            self.at_handle.check_urc()
            self.at_handle.check_network()

            # 等待30S
            all_logger.info("wait 30 seconds")
            time.sleep(30)

    def set_cfun_nv(self):
        """RM520NGLAAR01A06M4G_12.001.12.001_V01
        默认CFUN是0，设置CFUN1后重启依然为0，使用NV强制设置CFUN值，设置后重启保存。
        AT+QNVFW="/nv/item_files/Thin_UI/enable_thin_ui_cfg",01
        :return: None
        """
        qgmr = self.at_handle.send_at('AT+QGMR?', 3)
        # 如果是MH8001EUAC，并且QSIMDET是1,1
        if "RM520NGLAA" in qgmr and '12.201.12.201' in qgmr:
            # 使用NV设置CFUN值为1
            self.at_handle.send_at('AT+QNVFW="/nv/item_files/Thin_UI/enable_thin_ui_cfg",01', 3)

            # 重启后生效：CFUN1,1->检测驱动消失->检测USB驱动->检测URC->检测网络
            self.at_handle.send_at('AT+CFUN=1,1', 3)
            self.driver_handle.check_usb_driver_dis()
            self.driver_handle.check_usb_driver()
            self.at_handle.check_urc()
            self.at_handle.check_network()

            # 等待30S
            all_logger.info("wait 30 seconds")
            time.sleep(30)


if __name__ == '__main__':
    test_dict = {"at_port": "COM10"}
    s = StartupManager(**test_dict)
    s.ndis_driver_resume()
