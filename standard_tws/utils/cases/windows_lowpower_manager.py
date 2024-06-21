from utils.functions.windows_api import WindowsAPI
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import WindowsLowPowerError, ATError
from utils.pages.page_main import PageMain
from utils.functions.gpio import GPIO
import serial
import winreg
import subprocess
import time
import re
import os
import requests


class WindowsLowPowerManager:
    def __init__(self, at_port, dm_port, uart_port, nema_port, debug_port, phone_number, mbim_driver_name, func):
        self.at_port = at_port
        self.dm_port = dm_port
        self.uart_port = uart_port
        self.nema_port = nema_port
        self.phone_number = phone_number    # 获取卡槽一的手机号
        self.debug_port = debug_port
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.all_logger = all_logger
        self.page_main = PageMain()
        self.windows_api = WindowsAPI()
        self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.set_qsclk()  # 每个case执行前设置开启保存
        self.at_handle.switch_to_mbim(mbim_driver_name)
        self.windows_api.check_dial_init()
        try:
            self.disable_auto_connect_and_disconnect()      # 确保每次case执行前拨号不自动连接
        except Exception:   # noqa
            pass
        self.gpio = GPIO()
        self.gpio.set_sim1_det_high_level()     # 默认将SIM_DET引脚设置为IN,确保引脚输出电平不会过高并且SIM卡正常识别
        if func != 'windows_low_power_1':
            self.enable_low_power_registry()    # 默认每条case前激活注册表
            self.cfun_reset()
        if self.rg_flag:
            self.gpio.set_dtr_high_level()  # RG的模块默认拉高DTR

    def cfun_reset(self):
        """
        CFUN11重启模块
        :return:
        """
        self.at_handle.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        try:    # 开启慢时钟功能后可能会检测不到URC，此处检测URC失败不做异常处理
            self.at_handle.readline_keyword('PB DONE', timout=60)
        except ATError:
            pass

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        try:
            self.page_main.click_network_icon()
        except Exception:   # noqa
            self.page_main.click_network_icon()
        self.page_main.click_network_details()
        disconnect_button = self.page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.page_main.click_disable_auto_connect()
        self.windows_api.press_esc()

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
            for j in range(10):     # 检测Debug口是否可以正常打开
                try:
                    port = serial.Serial(self.debug_port, baudrate=115200, timeout=0)
                    port.close()
                    time.sleep(1)
                    break
                except Exception:   # noqa
                    time.sleep(1)
                    continue
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

    def disable_auto_connect_find_connect_button(self):
        """
        windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            status = self.page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
        else:
            raise WindowsLowPowerError("未发现连接按钮")

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

    def dial(self):
        """
        模拟点击网络图标连接拨号
        :return:
        """
        self.disable_auto_connect_and_disconnect()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()

    def set_gnss(self):
        """
        开启GPS功能
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QGPS=1')
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('AT+QGPS=1设置失败')

    def close_gnss(self):
        """
        关闭GPS功能
        :return:
        """
        gps_val = self.at_handle.send_at('AT+QGPS?')
        if 'QGPS: 1' in gps_val:
            for i in range(3):
                val = self.at_handle.send_at('AT+QGPSEND')
                if 'OK' in val:
                    return True
            else:
                raise WindowsLowPowerError('关闭GPS失败')
        else:
            return True

    def listen_nema(self):
        """
        打开NEMA口读取log
        :return:
        """
        start_time = time.time()
        with serial.Serial(self.nema_port, baudrate=115200, timeout=0) as _nema_port:
            while True:
                time.sleep(0.001)
                return_val = self.at_handle.readline(_nema_port)
                if return_val != '':
                    at_logger.info(return_val)
                if time.time() - start_time > 3:
                    _nema_port.close()
                    return True

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

    @ staticmethod
    def get_interface_name():
        """
        获取连接的名称
        :return: 当前连接名称
        """
        for i in range(10):
            mobile_broadband_info = os.popen('netsh mbn show interface').read()
            mobile_broadband_num = ''.join(re.findall(r'系统上有 (\d+) 个接口', mobile_broadband_info))  # 手机宽带数量
            if mobile_broadband_num and int(mobile_broadband_num) > 1:
                raise WindowsLowPowerError("系统上移动宽带有{}个，多于一个".format(mobile_broadband_num))
            mobile_broadband_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', mobile_broadband_info))
            if mobile_broadband_name != '':
                return mobile_broadband_name
            time.sleep(5)

    def disable_autosuspend(self):
        """
        关闭autosuspend功能
        :return:
        """
        interface_name = self.get_interface_name()
        args1 = ["powershell", 'Set-NetAdapterAdvancedProperty -Name "{}" -DisplayName "Selective Suspend" -DisplayValue "Disabled"'.format(interface_name)]
        args2 = ["powershell", 'Get-NetAdapterAdvancedProperty -Name "{}"'.format(interface_name)]
        all_logger.info(args1)
        all_logger.info(args2)
        clo = subprocess.Popen(args1, stdout=subprocess.PIPE)
        time.sleep(1)
        p = subprocess.Popen(args2, stdout=subprocess.PIPE)
        result = p.stdout.read().decode('GBK')
        if 'Disabled' in result:
            all_logger.info('成功关闭autosuspend功能')
            clo.terminate()
            clo.wait()
            p.terminate()
            p.wait()
        else:
            clo.terminate()
            clo.wait()
            p.terminate()
            p.wait()
            all_logger.info(result)
            all_logger.info('关闭autosuspend功能失败')

    def enable_autosuspend(self):
        """
        开启autosuspend功能
        :return:
        """
        interface_name = self.get_interface_name()
        args1 = ["powershell", 'Set-NetAdapterAdvancedProperty -Name "{}" -DisplayName "Selective Suspend" -DisplayValue "Enabled"'.format(interface_name)]
        args2 = ["powershell", 'Get-NetAdapterAdvancedProperty -Name "{}"'.format(interface_name)]
        clo = subprocess.Popen(args1, stdout=subprocess.PIPE)
        time.sleep(1)
        p = subprocess.Popen(args2, stdout=subprocess.PIPE)
        result = p.stdout.read().decode('GBK')
        if 'Enabled' in result:
            all_logger.info('成功开启autosuspend功能')
            clo.terminate()
            clo.wait()
            p.terminate()
            p.wait()
        else:
            clo.terminate()
            clo.wait()
            p.terminate()
            p.wait()
            all_logger.info(result)
            all_logger.info('开启autosuspend功能失败')

    def set_cfun(self, mode):
        """
        设置CFUN值
        :param mode: 需要设置的CFUN值
        :return:
        """
        val = ''
        for i in range(3):
            if mode == 0:
                val = self.at_handle.send_at('AT+CFUN=0', 15)
            elif mode == 1:
                val = self.at_handle.send_at('AT+CFUN=1', 15)
            elif mode == 4:
                val = self.at_handle.send_at('AT+CFUN=4', 15)
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('切换CFUN={}失败'.format(mode))

    def set_netmode(self, mode):
        """
        设置网络制式
        :param mode:AUTO,NR5G,LTE等
        :return:
        """
        for i in range(3):
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",{}'.format(mode))
            time.sleep(5)
            val = self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF"')
            if mode in val:
                return True
        else:
            raise WindowsLowPowerError('AT+QNWPREFCFG="MODE_PREF",{}设置失败'.format(mode))

    def set_nr5g_mode(self, mode):
        """
        :param mode: 1:设置关闭nr5g; 0:设置打开nr5g
        :return:
        """
        mode = str(mode)
        self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",{}'.format(mode))
        mode_value = self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode"')
        if mode not in mode_value:
            raise WindowsLowPowerError('设置{}5G模式失败'.format('开启' if mode == 0 else '关闭'))

    def cfun_change(self):
        """
        进行CFUN01切换，之后发送AT+CPIN?指令检测SIM卡是否检测正常
        :return:
        """
        zero_flag, one_flag = False, False
        for i in range(5):
            cfun_zero_val = self.at_handle.send_at('AT+CFUN=0', 15)
            if 'OK' in cfun_zero_val:
                zero_flag = True
            cfun_one_val = self.at_handle.send_at('AT+CFUN=1', 15)
            if 'OK' in cfun_one_val:
                one_flag = True
            if zero_flag and one_flag:
                time.sleep(5)
                sim_card = self.at_handle.send_at('AT+CPIN?')
                if 'READY' in sim_card:
                    return True
                else:
                    continue
        else:
            raise WindowsLowPowerError('连续五次CFUN01切换失败')

    def check_operater(self, mode, times=10):
        """
        切卡后检查运营商是否正确,通过AT+COPS指令进行判断
        :param mode:  运营商:CMCC, CU, CT
        :param times: 检测次数
        :return:
        """
        operater_dic = {'CMCC': 'CHINA MOBILE', 'CU': 'CHN-UNICOM', 'CT': 'CHN-CT'}
        for i in range(times):
            cops_val = self.at_handle.send_at('AT+COPS?')
            if operater_dic[mode] in cops_val:
                return True
            time.sleep(2)
        else:
            self.at_handle.send_at('AT+CIMI')

    def hang_up_after_system_dial(self, wait_time):
        """
        系统拨号n秒后主动挂断
        :param wait_time: 系统拨号持续时长
        :return:
        """
        content = {"exec_type": 1,
                   "payload": {
                       "phone_number": self.phone_number,
                       "hang_up_after_dial": wait_time
                   },
                   "request_id": "10011"
                   }
        dial_request = requests.post(self.url, json=content)
        all_logger.info(dial_request.json())
        self.at_handle.readline_keyword('RING', timout=300)
        self.debug_check(False, 10)
        self.at_handle.readline_keyword('NO CARRIER', timout=300)
        self.debug_check(True)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)    # 指定存储空间
        self.at_handle.send_at('AT+CMGD=0,4', 10)   # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        self.at_handle.readline_keyword('+CMTI', timout=300)
        self.debug_check(False, sleep=False)
        self.debug_check(True)

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
                self.cfun_reset()
                all_logger.info('已去激活注册表')
                return True
        except FileNotFoundError:   # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
        time.sleep(1)
        if 0 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('去激活注册表失败')
            raise WindowsLowPowerError('去激活注册表失败')
        else:
            self.close_lowpower()
            self.cfun_reset()
            all_logger.info('已去激活注册表')

    def sim_det(self, is_open):
        """
        开启/关闭SIM卡热插拔功能
        :param is_open:是否开启热插拔功能 True:开启；False:关闭
        :return:
        """
        if is_open:
            self.at_handle.send_at('AT+QSIMDET=1,1', 10)
            self.cfun_reset()
            if '1,1' in self.at_handle.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功开启热插拔功能')
            else:
                all_logger.info('开启热拔插功能失败')
                raise WindowsLowPowerError('开启热拔插功能失败')
        else:
            self.at_handle.send_at('AT+QSIMDET=0,1', 10)
            self.cfun_reset()
            if '0,1' in self.at_handle.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功关闭热插拔功能')
            else:
                all_logger.info('关闭热拔插功能失败')
                raise WindowsLowPowerError('关闭热拔插功能失败')

    def check_simcard(self, is_ready):
        """
        检测当前SIM卡状态
        :param is_ready:期望当前卡状态是否正常。True:期望正常检测到卡；False:期望检测不到卡
        :return:
        """
        if is_ready:
            for i in range(3):
                cpin_value = self.at_handle.send_at('AT+CPIN?', 10)
                if 'READY' in cpin_value:
                    all_logger.info('当前SIM卡状态检测正常，可以检测到SIM卡')
                    return
                time.sleep(1)
            else:
                all_logger.info('当前SIM卡状态检测异常，无法识别到SIM卡')
                raise WindowsLowPowerError('当前SIM卡状态检测异常，无法识别到SIM卡')
        else:
            for i in range(3):
                cpin_value = self.at_handle.send_at('AT+CPIN?', 10)
                if 'READY' not in cpin_value:
                    all_logger.info('当前SIM卡状态检测正常，无法识别到SIM卡')
                    return
                time.sleep(1)
            else:
                all_logger.info('当前SIM卡状态检测异常，可以检测到SIM卡')
                raise WindowsLowPowerError('当前SIM卡状态检测异常，可以检测到SIM卡')
