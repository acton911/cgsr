import os
import re
import getpass
import numpy as np
from utils.functions.windows_api import WindowsAPI
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import WindowsLowPowerError
from utils.pages.win11_page_main import Win11PageMain
import serial
import winreg
import subprocess
import time
import requests
from utils.pages.page_devices_manager import PageDevicesManager
from utils.functions.images import pic_compare


class WindowsLapTopLowPowerManager:
    # SIM LOCK 图片路径
    path_to_sim_lock_pic = 'utils/images/sim_locked_signal'
    path_to_airplane_mode_pic = "utils/images/toolbar_airplane_mode"
    path_to_toolbar_network_pic = "utils/images/toolbar_network"
    mess_apn = 'asd123@!#'

    def __init__(self, at_port, dm_port, nema_port, debug_port, phone_number, mbim_pcie_driver_name, power_port):
        self.at_port = at_port
        self.dm_port = dm_port
        self.power_port = power_port
        self.nema_port = nema_port
        self.phone_number = phone_number    # 获取卡槽一的手机号
        self.debug_port = debug_port
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.all_logger = all_logger
        self.page_main = Win11PageMain()
        self.windows_api = WindowsAPI()
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.page_devices_manager = PageDevicesManager()
        self.at_handle.send_at('AT+QURCCFG="urcport","usbmodem"', 3)  # 设置上报口
        # self.set_qsclk()  # 每个case执行前设置开启保存
        self.at_handle.switch_to_mbim(mbim_pcie_driver_name)
        self.enable_low_power_registry()  # 默认每条case前激活注册表
        # self.windows_api.check_dial_init()
        # try:
        #     self.disable_auto_connect_and_disconnect()      # 确保每次case执行前拨号不自动连接
        # except Exception:   # noqa
        #     pass
        self.mbim_disconnect_and_check()
        """
        self.cfun_reset()
        """
        # PCIE慢时钟需要禁用的口  Quectel UDE Device
        self.pcie_ports = ["Quectel' 'UDE' 'Device", "Quectel' 'UDE' 'Client", "Quectel' 'UDE' 'AT' 'Port*", "Quectel' 'UDE' 'DM' 'Port*", "Quectel' 'UDE' 'EFS' 'Port*", "Quectel' 'UDE' 'NMEA' 'Port*"]
        # self.pcie_ports = ["Quectel' 'UDE' 'Device", "Quectel' 'UDE' 'Client"]
        self.ati = self.get_ati()

    def enter_S3_S4_sleep(self, c=1, d=30, p=30, s=4):
        """
        使电脑进入S3睡眠(台式机)，或者S4休眠一段时间
        pwrtest /sleep [/c:n] [/d:n] [/p:n] [/h:{y|n}] [/s:{1|3|4|all|rnd|hibernate|standby|dozes4}] [/unattend] [dt:n] [/e:n] [/?]
        /c：n
        指定要运行的默认) (1 的周期数。
        /d：n
        指定默认) (90 的延迟时间（以秒为单位）。
        /p：n
        以秒为单位指定睡眠时间 (60) 。 如果休眠时不支持唤醒计时器，系统将重新启动并在写入休眠文件) 后立即恢复。
        /s：{1|3|4|所有|rnd|休眠|备用|dozes4}
        1
        指定目标状态始终为 S1。
        3
        指定目标状态始终是 S3。
        4
        指定目标状态始终为 S4。
        all
        指定按顺序对所有支持的电源状态进行循环。
        rnd
        指定随机遍历所有支持的电源状态。
        r
        指定目标状态始终处于休眠状态 (S4) 。
        转入
        指定目标状态为) (S1 或 S3 可用的任何备用状态。
        dozes4
        指定从新式备用 (S0 低功耗空闲) doze 到 S4。
        （剩余其他参数暂不关注）
        """
        pwrtest_path = self.get_pwrtest_path().replace(" ", "' '").replace("(", "`(").replace(")", "`)")
        cmd = 'powershell "{} /sleep /c:{} /d:{} /p:{} /s:{}"'.format(pwrtest_path, c, d, p, s)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )
        return_value = proc.stdout.read().decode('GBK', "ignore")
        all_logger.info(return_value)
        if 'Complete' not in return_value:
            raise WindowsLowPowerError("PC进入{}模式失败！".format(s))
        time.sleep(3)

    def enter_modern_standby(self, c=1, d=30, p=30):
        """
        使支持S0i3的笔电进入S0i3睡眠
        pwrtest /cs [/c:n] [/d:n] [/p:n][/?]
        /c：n   指定默认运行周期 (1) 周期数。
        /d：n   指定连接待机 (之间的) 延迟时间（以秒 (60 秒为默认) 。
        /p：n   指定连接的待机退出时间 (秒;默认为 60 秒) 。
        """
        pwrtest_path = self.get_pwrtest_path().replace(" ", "' '").replace("(", "`(").replace(")", "`)")
        cmd = 'powershell "{} /cs /c:{} /d:{} /p:{}"'.format(pwrtest_path, c, d, p)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )
        return_value = proc.stdout.read().decode('GBK', "ignore")
        all_logger.info(return_value)
        if 'Connected Standby' not in return_value:
            raise WindowsLowPowerError("PC进入modern standby失败！")
        time.sleep(3)

    def get_pwrtest_path(self):
        """
        获取本机的pwrtest工具的路径，默认 C:\Program Files (x86)\Windows Kits\10\Tools\x64 下
        """
        check_path = r"C:\Program Files (x86)\Windows Kits\10\Tools\x64"
        for path, _, files in os.walk(check_path):  # pwrtest.exe
            for file in files:
                if file.endswith('.exe') and file.startswith("pwrtest"):
                    pwrtest_path = os.path.join(path, file)
                    return pwrtest_path
        raise WindowsLowPowerError(f"在{check_path}中未找到pwrtest.exe，请检查工具文件夹是否存在")

    def click_enable_airplane_mode_and_check(self):
        """
        点击飞行模式后检查是否是飞行模式。
        :return: None
        """
        flag = False

        all_logger.info("点击飞行模式按钮")
        self.page_main.element_airplane_mode_button.click_input()  # 点击飞行模式图标
        time.sleep(3)  # 等待mobile_network_button状态切换

        if self.page_main.element_airplane_mode_button.get_toggle_state() != 1:
            all_logger.error("进入飞行模式后飞行模式按钮的状态异常")
            flag = True
        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("进入飞行模式后手机网络按钮的状态异常")
            flag = True

        all_logger.info("检查网络是否是已关闭")
        already_closed_text = self.page_main.element_mobile_network_already_closed_text
        if not already_closed_text.exists():
            all_logger.error("进入飞行模式后网络状态异常")
            flag = True

        all_logger.info("检查状态栏网络图标是否是飞行模式按钮")
        pic_status = pic_compare(self.path_to_airplane_mode_pic)
        if not pic_status:
            all_logger.error("检查飞行模式图标失败")
            flag = False

        if flag:
            raise WindowsLowPowerError("模块进入飞行模式检查失败")
        else:
            return True

    def click_disable_airplane_mode_and_check(self):
        """
        点击退出飞行模式后检查是否已经退出飞行模式。
        :return: None
        """
        flag = False

        # 判断飞行模式按钮的初始状态为按下
        if self.page_main.element_airplane_mode_button.get_toggle_state() == 0:
            all_logger.error("飞行模式按钮初始状态异常")
            flag = True

        all_logger.info("点击飞行模式按钮")
        self.page_main.element_airplane_mode_button.click_input()  # 点击飞行模式图标
        time.sleep(3)  # 等待mobile_network_button状态切换

        if self.page_main.element_airplane_mode_button.get_toggle_state() != 0:
            all_logger.error("退出飞行模式后飞行模式按钮的状态异常")
            flag = True
        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("退出飞行模式后手机网络按钮的状态异常")
            flag = True

        pic_status = pic_compare(self.path_to_toolbar_network_pic)
        if not pic_status:
            all_logger.error("检查状态栏网络图标失败")
            flag = False

        if flag:
            raise WindowsLowPowerError("模块退出飞行模式检查失败")
        else:
            return True

    def disable_airplane_mode(self):
        """
        禁止飞行模式，用于case前置条件。
        :return: None
        """
        self.page_main.click_network_icon()
        if self.page_main.element_airplane_mode_button.get_toggle_state() != 0:
            self.page_main.element_airplane_mode_button.click()
            time.sleep(5)
        self.windows_api.press_esc()

    def mbim_connect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

        profile_name = ''.join(re.findall(r'---\s+(.*)', data2))

        for i in range(10):
            time.sleep(5)
            os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
            all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
            time.sleep(5)

            data3 = os.popen('netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name)).read()
            all_logger.info('netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name))
            time.sleep(5)
            if '失败' not in data3:
                break
        else:
            raise WindowsLowPowerError("连接拨号失败！\r\n{}".format(data3))
        time.sleep(10)

    def mbim_disconnect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        time.sleep(5)
        os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
        time.sleep(10)

    def check_mbim_connect_disconnect(self, connect=True):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

        profile_name = ''.join(re.findall(r'---\s+(.*)', data2))

        # netsh mbn show profilestate interface="手机网络" name="EFAE6521-9049-451C-84A0-72CDE3D6372D"
        data3 = os.popen('netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name)).read()
        all_logger.info('netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name))
        if not connect and '已连接' in data3:
            raise WindowsLowPowerError("异常！当前没有断开连接！\r\n{}".format(data3))
        elif connect and '断开连接' in data3:
            raise WindowsLowPowerError("异常！当前没有连接！\r\n{}".format(data3))

    def mbim_connect_and_check(self):
        """
        mbim连接，检查是否正常
        :return: None
        """
        self.mbim_connect()
        self.check_mbim_connect_disconnect()
        self.windows_api.ping_get_connect_status()
        time.sleep(5)

    def mbim_disconnect_and_check(self):
        """
        mbim断开连接，检查是否正常
        :return: None
        """
        self.mbim_disconnect()
        self.check_mbim_connect_disconnect(False)
        time.sleep(5)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        # self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)    # 指定存储空间
        # self.at_handle.send_at('AT+CMGD=0,4', 10)   # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        # self.at_handle.readline_keyword('+CMTI', timout=300)
        # self.debug_check(False, sleep=False)
        # self.debug_check(True)

    def check_mbim_connect(self, auto_connect=False):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        num = 0
        timeout = 30
        connect_info = None
        already_connect_info = None
        while num <= timeout:
            connect_info = self.page_main.element_mbim_disconnect_button.exists()
            already_connect_info = self.page_main.element_mbim_already_connect_text.exists()
            if auto_connect is False:
                if connect_info and already_connect_info:
                    return True
            else:
                if already_connect_info:
                    return True
            num += 1
            time.sleep(1)
        info = '未检测到断开连接按钮，' if not connect_info and not auto_connect else '' + '未检测到已经连接信息' if not already_connect_info else ""
        raise WindowsLowPowerError(info)

    def disable_auto_connect_find_connect_button(self):
        """
        windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            self.page_main.click_network_icon()
            time.sleep(1)
            self.page_main.click_network_details()
            status = self.page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
        else:
            raise WindowsLowPowerError("未发现连接按钮")

    def dial(self):
        """
        模拟点击网络图标连接拨号
        :return:
        """
        self.disable_auto_connect_and_disconnect()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()

    def enable_disable_pcie_ports(self, flag, pcie_ports):
        for i in pcie_ports:
            if flag:
                all_logger.info("开始禁用{}".format(i))
                self.enable_disable_device(True, i)
            else:
                all_logger.info("开始启用{}".format(i))
                self.enable_disable_device(False, i)

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        disconnect_button = self.page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.page_main.click_disable_auto_connect()
        self.windows_api.press_esc()

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
            raise WindowsLowPowerError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

    def close_lowpower(self):
        """
        指令退出慢时钟
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=0,0')
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('退出慢时钟失败')

    def open_lowpower(self):
        """
        指令开启慢时钟
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=1')
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('开启慢时钟失败')

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
                if is_low_power:    # 期望模块已进入慢时钟检测Debug口
                    if value:   # 如果有返回值代表还未进入慢时钟，等待五秒后在检查
                        all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通,等待5S后再次检测')
                        continue
                    else:
                        all_logger.info('检测debug口无返回值，正常')
                        return True
                else:   # 期望模块未进入慢时钟检测Debug口
                    if value:
                        all_logger.info(value.replace('\r\n', ''.strip()))
                        all_logger.info('检测debug口有返回值，正常')
                        return True
                    else:       # 如果无返回值代表模块仍未退出慢时钟，等待5S后再检查
                        all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出,等待5S后再次检测')
                        continue
        else:
            if is_low_power:  # 期望模块已进入慢时钟检测Debug口
                all_logger.info(value.replace('\r\n', ''.strip()))
                all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
                raise WindowsLowPowerError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise WindowsLowPowerError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def close_devices_page(self):
        """
        关闭设备管理器
        :return: None
        """
        all_logger.info('关闭设备管理器')
        os.popen('taskkill /f /t /im "mmc.exe*"').read()

    def disable_low_power_registry(self):
        """
        修改注册表，使模块退出慢时钟
        :return:
        """
        reg_root = winreg.HKEY_LOCAL_MACHINE
        reg_path = r'SYSTEM\CurrentControlSet\Services\qcusbser'
        key = winreg.OpenKey(reg_root, reg_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            key_value = winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled")
            winreg.QueryValueEx(key, "QCDriverSelectiveSuspendIdleTime")
            if 0 in key_value:
                # self.cfun_reset()
                all_logger.info('已去激活注册表')
                return True
        except FileNotFoundError:  # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
        time.sleep(1)
        if 0 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('去激活注册表失败')
            raise WindowsLowPowerError('去激活注册表失败')
        else:
            # self.cfun_reset()
            all_logger.info('已去激活注册表')

    def check_qsclk(self, mode=1, is_save=True):
        """
        默认查询+QSCLK: 1,1返回值
        :param mode: 0:查询AT+AT+QSCLK=?返回值；1: 查询AT+QSCLK?返回值
        :param is_save: Ture:设置AT+QSCLK=1,1后查询；False:设置AT+QSCLK=1,0后查询
        :return:
        """
        if mode == 0:
            for i in range(3):
                qsclk_val = self.at_handle.send_at('AT+QSCLK=?')
                if '+QSCLK: (0,1),(0,1)' in qsclk_val:
                    return True
                time.sleep(1)
            else:
                raise WindowsLowPowerError('AT+QSCLK=?返回值格式不正确')
        elif mode == 1:
            for i in range(3):
                qsclk_val = self.at_handle.send_at('AT+QSCLK?')
                if is_save:
                    if '+QSCLK: 1,1' in qsclk_val:
                        return True
                else:
                    if '+QSCLK: 0,0' in qsclk_val:
                        return True
                time.sleep(1)
            else:
                raise WindowsLowPowerError('AT+QSCLK?返回值格式不正确')

    def cfun_reset(self):
        """
        CFUN11重启模块
        :return:
        """
        self.at_handle.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver()
        all_logger.info('打开设备管理器')
        self.page_devices_manager.open_devices_manager()
        all_logger.info('刷新设备管理器')
        self.page_devices_manager.element_scan_devices_icon().click()
        time.sleep(90)
        # self.at_handle.readline_keyword('PB DONE', timout=80)

    @staticmethod
    def enable_low_power_registry():
        """
        修改注册表值，使模块进入慢时钟
        :return:
        """
        reg_root = winreg.HKEY_LOCAL_MACHINE
        reg_path = r'SYSTEM\CurrentControlSet\Services\qcusbser'
        key = winreg.OpenKey(reg_root, reg_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            key_value = winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled")
            winreg.QueryValueEx(key, "QCDriverSelectiveSuspendIdleTime")
            if 1 in key_value:
                all_logger.info('已激活注册表')
                return True
        except FileNotFoundError:   # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
        time.sleep(1)
        if 1 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('激活注册表失败')
            raise WindowsLowPowerError('激活注册表失败')
        else:
            all_logger.info('已激活注册表')

    @staticmethod
    def enable_disable_device(flag, device_name):
        """
        禁用或者启用驱动。
        :param device_name: 设备管理器中设备或驱动名称
        :param flag: True:禁用驱动，False：启用驱动。
        :return: None
        """
        all_logger.info('{}驱动{}'.format("禁用" if flag else "启用", device_name))
        cmd = 'powershell "Get-PnpDevice -FriendlyName "{}" -status "OK" | disable-pnpdevice -Confirm:$True"'.format(
            device_name) if flag else \
            'powershell "Get-PnpDevice -FriendlyName "{}" -status "Error" | enable-pnpdevice -Confirm:$Ture"'.format(
                device_name)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

        proc.stdin.write(b"A\n")
        proc.stdin.flush()
        proc.stdin.close()

        while proc.returncode is None:
            proc.poll()

        all_logger.info(proc.stdout.read().decode('GBK', "ignore"))

        time.sleep(3)

    def open_all_ports(self):
        # 打开所有端口->判断AT口DM口是否存在
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.open_all_ports_and_check(q_mode_switch_path)

    def close_all_ports(self):
        # 打开所有端口->判断AT口DM口是否存在
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.close_all_ports_and_check(q_mode_switch_path)

    def get_ati(self):
        ati = self.at_handle.send_at('ATI')
        ati_regex = ''.join(re.findall(r'Revision: (\w+)', ati))
        if ati_regex:
            return ati_regex
        else:
            return False

    def get_q_mode_switch_path(self):
        """
        获取本机的QModeSwitch工具的路径，默认 C:\\Users\\q\\Desktop\\Tools 下
        """
        check_path = fr"C:\Users\{getpass.getuser()}\Desktop\Tools"
        pattern = self.ati[:5]  # QModeSwitch_RM520_xxxx.exe，所以取ATI前五位判断QModeSwitch是否正常
        for path, _, files in os.walk(check_path):
            for file in files:
                if file.endswith('.exe') and file.startswith("QModeSwitch") and pattern in file:
                    mode_switch_tool_path = os.path.join(path, file)
                    return mode_switch_tool_path
        raise WindowsLowPowerError(f"在{check_path}中未找到适合{pattern}的QModeSwitch，请检查工具文件夹是否存在，版本是否正常")

    def open_all_ports_and_check(self, mode_switch_path):
        """
        切换模块为all port模式
        :param mode_switch_path: QModeSwitch工具的路径
        :return: None
        """
        port_list = list()
        for _ in range(3):
            cmd = f"{mode_switch_path} -p 0"
            output = subprocess.getoutput(cmd)
            all_logger.info(f"cmd: {cmd}\noutput:{output}")

            all_logger.info("wait 3 seconds")

            port_list = self.driver_check.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                all_logger.info("QModeSwitch打开所有端口成功")
                return True

            time.sleep(3)
        else:
            raise WindowsLowPowerError(f"连续三次使用QModeSwitch工具打开端口失败，期望AT口({self.at_port}), DM口({self.dm_port})\n"
                          f"当前端口列表：{port_list}")

    def close_all_ports_and_check(self, mode_switch_path):
        """
        切换模块为GPS+MBIM模式
        :param mode_switch_path: QModeSwitch工具的路径
        :return: None
        """
        port_list = list()
        for _ in range(3):
            cmd = f"{mode_switch_path} -p 1"
            output = subprocess.getoutput(cmd)
            all_logger.info(f"cmd: {cmd}\noutput:{output}")

            all_logger.info("wait 3 seconds")

            port_list = self.driver_check.get_port_list()
            if self.at_port not in port_list and self.dm_port not in port_list:
                all_logger.info("QModeSwitch关闭所有端口成功")
                return True

            time.sleep(3)
        else:
            raise WindowsLowPowerError(f"连续三次使用QModeSwitch工具关闭端口失败，期望AT口({self.at_port}), DM口({self.dm_port})\n"
                          f"当前端口列表：{port_list}")

    def get_current_volt(self, max_electric=10, max_rate=0.1, check_time=60, mode=0, check_frequency=1):
        """
        max_electric # 设置进入休眠后的平均耗流标准，实测不得超过该标准，单位为毫安
        max_rate # 在采样数据中出现的高于设定标准的峰值频率
        check_time  # 检测休眠耗流时长，单位为秒,若需要检测连续24H耗流，则此处可以填写86400
        check_frequency  # 检测频率，单位为秒
        mode # 0为睡眠检测，1为唤醒检测
        wait_sleep_time = 120  # 设置静置等待进入睡眠时间，单位为秒
        """
        for i in range(100):
            try:
                p_port = serial.Serial(self.power_port, baudrate=9600, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(0.5)
                continue
        else:
            raise WindowsLowPowerError("检测打开程控电源Power port口异常")
        get_volt_start_timestamp = time.time()
        volt_list = []
        while True:
            time.sleep(0.001)
            p_port.write('meas:curr?\r\n'.encode('UTF-8'))
            # at_logger.info('Send: {}'.format(f'meas:curr?'))
            return_value = self.readline(p_port)
            if time.time() - get_volt_start_timestamp > check_time:  # 到达检测时间
                upset_list = [volt for volt in volt_list if volt > max_electric]  # 电流大于设定值时加入此列表
                curr_avg = np.round(np.mean(volt_list), 2)  # 计算电流平均值
                real_rate = round(len(upset_list) / len(volt_list), 2)  # 大于设定值的比率
                all_logger.info('耗流平均值实测为{}mA'.format(curr_avg))
                all_logger.info('耗流值偏高频率为{}%'.format(real_rate * 100))
                if mode == 0:
                    if real_rate > max_rate:
                        raise WindowsLowPowerError('休眠耗流值偏高频率为{}%， 休眠耗流值偏高频率异常'.format(real_rate * 100))
                    else:
                        all_logger.info('休眠耗流值偏高频率为{}%\n, 耗流值偏高频率正常'.format(real_rate * 100))
                    if curr_avg > max_electric:
                        raise WindowsLowPowerError('休眠耗流平均值实测为{}mA， 休眠耗流平均值异常'.format(curr_avg))
                    else:
                        all_logger.info('休眠耗流平均值实测为{}mA，休眠耗流平均值正常'.format(curr_avg))

                elif mode == 1:
                    if real_rate > max_rate:
                        raise WindowsLowPowerError('唤醒耗流值偏高实测为{}%， 唤醒耗流值偏高频率异常'.format(real_rate * 100))
                    else:
                        all_logger.info('唤醒耗流值偏高频率为{}%, 唤醒耗流值偏高频率正常'.format(real_rate * 100))
                    if curr_avg > max_electric:
                        raise WindowsLowPowerError('唤醒耗流平均值实测为{}mA， 唤醒耗流平均值异常'.format(curr_avg))
                    else:
                        all_logger.info('唤醒耗流平均值实测为{}mA，唤醒耗流平均值正常'.format(curr_avg))
                break
            if return_value != '':
                current_voltage = float(return_value) * 1000
                all_logger.info('[power] {} mA'.format(round(current_voltage, 4)))
                volt_list.append(current_voltage)
            time.sleep(check_frequency)

    def set_volt(self, volt):
        self.power_port.write('Volt {}\r\n'.format(volt).encode('utf-8'))
        all_logger.info(["程控电源电压设置为{}V".format(volt)])

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
