import os
import re
import subprocess
import sys
import time
import serial
import requests
from utils.functions.gpio import GPIO
from utils.functions.linux_api import LinuxAPI
from utils.exception.exceptions import LinuxLowPowerError
from utils.functions.linux_api import QuectelCMThread, PINGThread
from utils.logger.logging_handles import all_logger, at_logger
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker


class LinuxLowPowerManager:
    def __init__(self, at_port, dm_port, uart_port, nema_port, debug_port, phone_number, mbim_driver_name, pc_ethernet_name):
        self.at_port = at_port
        self.dm_port = dm_port
        self.uart_port = uart_port
        self.nema_port = nema_port
        self.phone_number = phone_number    # 获取手机号
        self.debug_port = debug_port
        self.mbim_driver_name = mbim_driver_name
        self.pc_ethernet_name = pc_ethernet_name
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.all_logger = all_logger
        self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.linux_api = LinuxAPI()
        self.driver_check.check_usb_driver()
        self.prepare_at()
        self.gpio = GPIO()
        self.gpio.set_sim1_det_high_level()     # 默认将SIM_DET引脚设置为IN,确保引脚输出电平不会过高并且SIM卡正常识别
        self.linux_enter_low_power()
        self.set_qsclk()  # 每个case执行前设置开启保存
        if self.rg_flag:
            self.gpio.set_dtr_high_level()  # 默认拉高DTR

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
                raise LinuxLowPowerError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise LinuxLowPowerError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def prepare_at(self):
        """
        检测是否可以正常发AT
        :return:
        """
        for i in range(10):
            value = self.at_handle.send_at('AT')
            if value != '':
                time.sleep(5)
                return
            time.sleep(5)

    def check_cfun(self, value):
        """
        检查AT+CFUN返回值是否正确
        :param value: 需要核实的cfun值
        :return: None
        """
        cfun_value = self.at_handle.send_at('AT+CFUN?')
        if str(value) in cfun_value:
            all_logger.info('当前CFUN值正常')
        else:
            raise LinuxLowPowerError('CFUN值异常')

    def change_cfun(self, value):
        """
        切换CFUN值
        :param value:  需要改变的CFUN值
        :return: None
        """
        self.at_handle.send_at('AT+CFUN={}'.format(value))
        time.sleep(1)
        self.check_cfun(value)
        time.sleep(5)

    def set_gnss(self):
        """
        设置开启GPS功能
        :return: True
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QGPS=1')
            if 'OK' in val:
                return True
        else:
            raise LinuxLowPowerError('AT+QGPS=1设置失败')

    def close_gnss(self):
        """
        设置关闭GNSS功能
        :return: True
        """
        gps_val = self.at_handle.send_at('AT+QGPS?')
        if 'QGPS: 1' in gps_val:
            for i in range(3):
                val = self.at_handle.send_at('AT+QGPSEND')
                if 'OK' in val:
                    return True
            else:
                raise LinuxLowPowerError('关闭GPS失败')
        else:
            return True

    def listen_nema(self):
        """
        打开NEMA口读取log
        :return: True
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

    def check_qsclk(self, mode=1, is_save=True):
        """
        默认查询+QSCLK: 1,1返回值
        :param mode: 0:查询AT+AT+QSCLK=?返回值；1: 查询AT+QSCLK?返回值
        :param is_save: Ture:设置AT+QSCLK=1,1后查询；False:设置AT+QSCLK=1,0后查询
        :return: True
        """
        if mode == 0:
            for i in range(3):
                qsclk_val = self.at_handle.send_at('AT+QSCLK=?')
                if '+QSCLK: (0,1),(0,1)' in qsclk_val:
                    return True
                time.sleep(1)
            else:
                raise LinuxLowPowerError('AT+QSCLK=?返回值格式不正确')
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
                raise LinuxLowPowerError('AT+QSCLK?返回值格式不正确')

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
            raise LinuxLowPowerError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

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

    def set_linux_mbim_and_remove_driver(self):
        """
        设置模块拨号模式为MBIM模式，并且卸载其他拨号驱动
        :return: None
        """
        all_logger.info("设置USBNET为2")
        self.at_handle.send_at('AT+QCFG="USBNET",2')

        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

    def check_linux_mbim_and_driver_name(self):
        """
        检测当前是否设置为MBIM拨号模式，MBIM驱动是否加载正常
        :return: True
        """
        time.sleep(5)
        all_logger.info("检查USBNET为2")
        usbnet = self.at_handle.send_at('AT+QCFG="USBNET"')
        if ',2' not in usbnet:
            raise LinuxLowPowerError("切换USBNET,2失败")

        all_logger.info("检查cdc_mbim驱动加载")
        timeout = 30
        for _ in range(timeout):
            s = subprocess.run('lsusb -t', shell=True, capture_output=True, text=True)
            all_logger.info(s)
            if 'cdc_mbim' in s.stdout:
                break
            time.sleep(1)
        else:
            raise LinuxLowPowerError("MBIM驱动开机后{}S未加载成功".format(timeout))

        all_logger.info("检查mbim驱动名称")
        s = subprocess.run("ip a | grep -o {}".format(self.mbim_driver_name), shell=True, capture_output=True, text=True)
        all_logger.info(s)
        if '{}'.format(self.mbim_driver_name) not in s.stdout:
            raise LinuxLowPowerError('MBIM驱动名称异常->"{}"'.format(s.stdout))
        all_logger.info(os.popen('ifconfig').read())

    def mbim_dial(self):
        """
        进行MBIM驱动编译，重启模块检查驱动是否正常
        :return: None
        """
        exc_type = None
        exc_value = None
        self.set_linux_mbim_and_remove_driver()
        try:
            self.linux_enter_low_power(False)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.linux_enter_low_power()
            if exc_type and exc_value:
                raise exc_type(exc_value)
        self.check_linux_mbim_and_driver_name()

    def dial(self):
        """
        进行拨号及Ping操作,之后检测耗流，最后断开拨号并检测网卡是否消失
        :return: None
        """
        qcm = None
        ping = None
        exc_type = None
        exc_value = None
        try:
            # set quectel-CM
            qcm = QuectelCMThread()
            qcm.setDaemon(True)
            ping = PINGThread(times=60)
            ping.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(20)  # 等待拨号稳定
            # 检查拨号
            self.check_linux_mbim_and_driver_name()
            ping.start()
            self.debug_check(False)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            ping.ctrl_c()
            ping.terminate()
            qcm.ctrl_c()
            qcm.terminate()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.pc_ethernet_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.pc_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.pc_ethernet_name)
            self.set_usbnet()
            time.sleep(10)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def set_usbnet(self):
        """
        切换usbnet值，使其不为2，mbim拨号
        :return:
        """
        self.at_handle.send_at('AT+QCFG="usbnet",0', 10)
        self.linux_enter_low_power(False)
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        self.linux_enter_low_power()

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
            raise LinuxLowPowerError('退出慢时钟失败')

    def open_lowpower(self):
        """
        发送指令进入慢时钟
        :return: True
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=1')
            if 'OK' in val:
                return True
        else:
            raise LinuxLowPowerError('开启慢时钟失败')

    def set_cfun(self, mode):
        """
        设置CFUN值
        :param mode: 需要设置的CFUN值: 0, 1, 4
        :return: True
        """
        val = ''
        for i in range(3):
            if mode == 0:
                val = self.at_handle.send_at('AT+CFUN=0')
            elif mode == 1:
                val = self.at_handle.send_at('AT+CFUN=1')
            elif mode == 4:
                val = self.at_handle.send_at('AT+CFUN=4')
            if 'OK' in val:
                return True
        else:
            raise LinuxLowPowerError('切换CFUN={}失败'.format(mode))

    def check_sleep(self):
        """
        使PC进入睡眠，并检测PC睡眠期间模块耗流是否正常，唤醒PC后检测模块拨号功能是否正常
        :return:
        """
        os.popen('rtcwake -m mem -s 60')
        self.debug_check(True, 10)
        time.sleep(60)
        self.dial()

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
            raise LinuxLowPowerError('AT+QNWPREFCFG="MODE_PREF",{}设置失败'.format(mode))

    def set_nr5g_mode(self, mode):
        """
        :param mode: 1:设置关闭nr5g; 0:设置打开nr5g
        :return:
        """
        mode = str(mode)
        self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",{}'.format(mode))
        mode_value = self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode"')
        if mode not in mode_value:
            raise LinuxLowPowerError('设置{}5G模式失败'.format('开启' if mode == 0 else '关闭'))

    def hang_up_after_system_dial(self, wait_time):
        """
        系统拨号n秒后主动挂断
        :param wait_time: 系统拨号持续时长
        :return:
        """
        content = {"exec_type": 1,
                   "payload": {
                       "phone_number": self.phone_number,
                       "hang_up_after_dial": wait_time},
                   "request_id": "10011"}
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
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",LTE', 10)    # 固定网络制式为LTE
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
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 10)  # 恢复网络制式为AUTO

    def sim_det(self, is_open):
        """
        开启/关闭SIM卡热插拔功能
        :param is_open:是否开启热插拔功能 True:开启；False:关闭
        :return:
        """
        if is_open:
            self.at_handle.send_at('AT+QSIMDET=1,1', 10)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)
            if '1,1' in self.at_handle.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功开启热插拔功能')
            else:
                all_logger.info('开启热拔插功能失败')
                raise LinuxLowPowerError('开启热拔插功能失败')
        else:
            self.at_handle.send_at('AT+QSIMDET=0,1', 10)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)
            if '0,1' in self.at_handle.send_at('AT+QSIMDET?', 10):
                all_logger.info('成功关闭热插拔功能')
            else:
                all_logger.info('关闭热拔插功能失败')
                raise LinuxLowPowerError('关闭热拔插功能失败')

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
        else:
            for i in range(3):
                cpin_value = self.at_handle.send_at('AT+CPIN?', 10)
                if 'READY' not in cpin_value:
                    all_logger.info('当前SIM卡状态检测正常，无法识别到SIM卡')
                    return
                time.sleep(1)
            else:
                all_logger.info('当前SIM卡状态检测异常，可以检测到SIM卡')
