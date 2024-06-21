import re
import subprocess
import time
import winreg
import requests
import serial
from utils.functions.driver_check import DriverChecker
from utils.functions.windows_api import WindowsAPI, PINGThread
from utils.pages.page_main import PageMain
from utils.pages.page_notification import PageNotification
from utils.operate.at_handle import ATHandle
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import WindowsSMSError


class WindowsSMSManager:
    def __init__(self, at_port, dm_port, debug_port, phone_number, mbim_driver_name, sim_operator):
        self.at_port = at_port
        self.dm_port = dm_port
        self.debug_port = debug_port
        self.phone_number = phone_number
        self.mbim_driver_name = mbim_driver_name
        self.sim_operator = sim_operator
        self.page_main = PageMain()
        self.driver_check = DriverChecker(at_port, dm_port)
        self.windows_api = WindowsAPI()
        self.at_handle = ATHandle(at_port)
        self.page_notification = PageNotification()
        self.at_handle.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        time.sleep(5)

    def check_sms_format(self):
        """
        1.查看短信格式
        2.查看短信编码格式
        3.查询短信接收格式
        :return:
        """
        value_1 = self.at_handle.send_at('AT+CMGF?', 10)
        value_2 = self.at_handle.send_at('AT+CSCS?', 10)
        value_3 = self.at_handle.send_at('AT+CNMI?', 10)
        if '+CMGF: 0' not in value_1:
            all_logger.info('AT+CMGF?查询默认值不为0')
            self.at_handle.send_at('AT+CMGF=0', 10)
            raise WindowsSMSError('AT+CMGF?查询默认值不为0')
        if '+CSCS: "GSM"' not in value_2:
            all_logger.info('AT+CSCS?查询默认值不为GSM')
            self.at_handle.send_at('AT+CSCS="GSM"', 10)
            raise WindowsSMSError('AT+CSCS?查询默认值不为GSM')
        if '+CNMI: 2,1,0,0,0' not in value_3:
            all_logger.info('AT+CNMI?查询返回值不为2,1,0,0,0')
            self.at_handle.send_at('AT+CNMI=2,1,0,0,0', 10)
            raise WindowsSMSError('AT+CNMI?查询返回值不为2,1,0,0,0')

    def check_sim_status(self):
        """
        1. 查询SIM卡状态
        2. 查询网络状态
        3. 确认当前SIM卡的短信中心号码
        :return:
        """
        sms_center_phone = []
        if 'CMCC' in self.sim_operator:
            sms_center_phone = ['+8613800210500', '+8613800551500']
        elif 'CU' in self.sim_operator:
            sms_center_phone = ['+8613010314500', '+8613010305500']
        value_1 = self.at_handle.send_at('AT+CPIN?', 10)
        value_2 = self.at_handle.send_at('AT+CSCA?', 10)
        if '+CPIN: READY' not in value_1:
            all_logger.info('SIM卡状态检测异常')
            raise WindowsSMSError('SIM卡状态检测异常')
        for i in sms_center_phone:
            if i in value_2:
                all_logger.info('短信中心号码检查正常')
                break
        else:
            all_logger.info('短信中心号码检查异常')
            raise WindowsSMSError('短信中心号码检查异常')
        self.at_handle.check_network()

    def send_pdu_msg(self, value, content, string_value):
        """
        发送短信
        :param value: at+cmgs指令后跟的值
        :param content: 短信内容，根据实际发送的编码格式决定
        :param string_value: 短信内容(实际显示的内容)
        :return:
        """
        self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS={value}')
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
            _port.write(content.encode('utf-8'))
            _port.write(chr(0x1A).encode())
        self.at_handle.readline_keyword('+CMGS', '+CMT', timout=60)
        all_logger.info('模块已接收到短信')
        if self.page_notification.check_msg_push(self.phone_number, string_value) is False:
            all_logger.info('短信内容或发件人号码核实不正确')
            raise WindowsSMSError('短信内容或发件人号码核实不正确')
        else:
            all_logger.info('短信内容及发件人号码核实正常')

    def invert_phone_number(self):
        """
        手机号每两位互相颠倒顺序，最后一位用F补全用于拼接短信内容
        :return:
        """
        phone_number = self.phone_number + 'F'
        num_list = ['0' for x in range(0, 12)]
        j = 1
        for i in phone_number:
            if j % 2 == 0:
                num_list[j-2] = i
            else:
                num_list[j] = i
            j += 1
        return ''.join(num_list)

    def click_disable_mobile_network_and_check(self):
        """
        点击禁用手机网络图标然后检查。
        :return: None
        """
        flag = False

        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("手机网络按钮初始状态异常")
            flag = True

        all_logger.info("点击按钮关闭手机网络")
        self.page_main.element_mobile_network_button.click_input()
        time.sleep(3)

        if not self.page_main.element_mobile_network_already_closed_text.exists():
            all_logger.error("关闭手机网络后状态异常")
            flag = True

        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("点击禁用手机网络后手机网络图标检查异常")
            flag = True

        if flag:
            return WindowsSMSError("点击禁用手机网络图标后状态检查失败")
        else:
            return True

    def click_enable_mobile_network_and_check(self):
        """
        点击启用手机网络图标然后检查。
        :return: None
        """
        flag = False

        if self.page_main.element_mobile_network_button.get_toggle_state() != 0:
            all_logger.error("手机网络按钮初始状态异常")
            flag = True

        # mbim_logger.error("点击按钮开启手机网络")
        self.page_main.element_mobile_network_button.click_input()
        time.sleep(3)

        if self.page_main.element_mobile_network_button.get_toggle_state() != 1:
            all_logger.error("开启手机网络后按钮状态异常")
            flag = True

        if flag:
            return WindowsSMSError("点击启用手机网络图标后状态检查失败")
        else:
            return True

    def check_msg_number(self, num):
        """
        检查短信数量是否正常
        :param num: 预期收到短信数量
        :return:
        """
        value = self.at_handle.send_at('AT+CPMS?', 10)
        if f'+CPMS: "ME",{num}' in value:
            all_logger.info('短信数量核对正常')
        else:
            all_logger.info(f'期望接收到{num}条短信，实际查询数量不符')
            raise WindowsSMSError(f'期望接收到{num}条短信，实际查询数量不符')

    def send_no_class_msg(self, value, content, string_value):
        """
        1.发送no class (00)的短消息
        2.MBIM端确认有消息推送
        3.关机手机网络
        4.开启手机网络
        5.重复步骤1~4两次
        :param value: at+cmgs指令后跟的值
        :param content: 短信内容，根据实际发送的编码格式决定
        :param string_value: 短信内容(实际显示的内容)
        :return:
        """
        for i in range(4):
            self.send_pdu_msg(value, content, string_value)
            self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            try:
                self.click_enable_mobile_network_and_check()
            except:     # noqa
                self.click_enable_mobile_network_and_check()
            time.sleep(5)

    def send_no_class_long_msg(self, value, content, string_value):
        """
        1.发送no class (00)的长短信
        2.MBIM端确认有消息推送
        3.关机手机网络
        4.开启手机网络
        5.重复步骤1~4两次
        :param value: at+cmgs指令后跟的值
        :param content: 短信内容，根据实际发送的编码格式决定
        :param string_value: 短信内容(实际显示的内容)
        :return:
        """
        for i in range(4):
            self.send_pdu_msg(value, content, string_value)
            self.page_main.click_network_icon()
            self.click_disable_mobile_network_and_check()
            try:
                self.click_enable_mobile_network_and_check()
            except:     # noqa
                self.click_enable_mobile_network_and_check()
            time.sleep(5)

    def write_msg_full(self):
        """
        写短信将存储空间占满
        :return:
        """
        save_size = self.at_handle.send_at('AT+CPMS?', 10)
        msg_total = int(re.findall(r'\+CPMS: "ME",\d+,(\d+)', save_size)[0])
        cur_msg = int(re.findall(r'\+CPMS: "ME",(\d+)', save_size)[0])
        self.at_handle.send_at('AT+CMGF=1', 10)
        all_logger.info('写短信占满存储空间')
        for i in range(msg_total - cur_msg):
            try:
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW')
                with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                    _port.write('test'.encode('utf-8'))
                    _port.write(chr(0x1A).encode())
                self.at_handle.readline_keyword('+CMGW', 'OK')
            except Exception:   # noqa
                pass
            time.sleep(0.3)
        self.at_handle.send_at('AT+CMGF=0', 10)
        current_size = self.at_handle.send_at('AT+CPMS?', 10)
        current_num = int(re.findall(r'\+CPMS: "ME",(\d+)', current_size)[0])
        if current_num != msg_total:
            all_logger.info('短信未写满，继续写满短信')
            self.write_msg_full()
        else:
            all_logger.info('短信已写满')

    def send_multiple_msg(self, times, value, content, string_value):
        """
        循环发送多次短信
        :param times: 发送短信的次数
        :param value: at+cmgs指令后跟的值
        :param content: 短信内容，根据实际发送的编码格式决定
        :param string_value: 短信内容(实际显示的内容)
        :return:
        """
        for i in range(times):
            self.send_pdu_msg(value, content, string_value)

    def send_pdu_msg_without_check(self):
        """
        只发送短信，不检查来短信上报
        :return:
        """
        self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGS=19')
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
            _port.write(f'0011FF0D9168{self.invert_phone_number()}0000A804F4F29C0E'.encode('utf-8'))
            _port.write(chr(0x1A).encode())
        self.at_handle.readline_keyword('+CMGS', 'OK', timout=30)

    def send_pdu_msg_with_check(self):
        """
        发送短信，并检查两次短信上报
        :return:
        """
        self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGS=19')
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
            _port.write(f'0011FF0D9168{self.invert_phone_number()}0000A804F4F29C0E'.encode('utf-8'))
            _port.write(chr(0x1A).encode())
        self.at_handle.readline_keyword('+CMTI: "ME",0', '+CMTI: "ME",1', timout=90)
        all_logger.info('模块已接收到短信')
        if self.page_notification.check_msg_push(self.phone_number, 'test') is False:
            all_logger.info('短信内容或发件人号码核实不正确')
            raise WindowsSMSError('短信内容或发件人号码核实不正确')
        else:
            all_logger.info('短信内容及发件人号码核实正常')

    def send_full_msg(self):
        """
        短信满的情况下继续发送短信
        当短信满了之后在接收一条信息不会上报，会删除已读短信，当我们再接收一条信息会收到两条信息
        :return:
        """
        # 首先发送一条短信，不检查短信上报
        self.send_pdu_msg_without_check()

        # 再发送一条检查两条短信上报
        self.send_pdu_msg_with_check()

    def send_gsm_msg(self, class_type):
        """
        发送GSM格式短信
        :param class_type:短信类型。如 no class，class 0等
        :return:
        """
        class_dict = {'no_class': '17,71,0,0', 'class_0': '17,0,0,240', 'class_1': '17,167,0,241',
                      'class_2': '17,168,0,242', 'class_3': '17,197,0,243'}
        origin_val = ''
        try:
            value = self.at_handle.send_at('AT+CSMP?', 10)
            origin_val = re.findall(r'\+CSMP: (.*)', value)[0]      # 保存初始值，每次设置完后需要恢复
            self.at_handle.send_at('AT+CMGF=1', 10)
            self.at_handle.send_at(f'AT+CSMP={class_dict[class_type]}', 10)
            content = 'GSM msg test #%#*(()97970 #DGFHffh#1https://www.sina.com.cn/19/06/04,03:01:38+32+86'
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{self.phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', '+CMT', timout=30)
            all_logger.info('模块已接收到短信')
            if self.page_notification.check_msg_push(self.phone_number, content) is False:
                all_logger.info('短信内容或发件人号码核实不正确')
                raise WindowsSMSError('短信内容或发件人号码核实不正确')
            else:
                all_logger.info('短信内容及发件人号码核实正常')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)
            self.at_handle.send_at(f'AT+CSMP={origin_val}', 10)

    def send_hex_msg(self):
        """
        发送十六进制短信，不检查短信推送内容，短信中心转发会存在乱码
        :return:
        """
        try:
            self.at_handle.send_at('AT+CMGF=1', 10)
            content = '5e605f207e402324252628292a5b5d7c5c000102030405060708090d0a0b0c0d0a0e0f10111213141516171819'
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{self.phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(bytes.fromhex(content))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', '+CMT', timout=30)
            all_logger.info('模块已接收到短信')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)

    def send_ucs2_msg(self):
        """
        发送UCS2短信
        :return:
        """
        content = '00550043005300320020006E006F00200063006C006100730073002D00500044005553D190016D4B8BD5007E0023004000250026003A00680065006C006C006F005E002A00280029'
        receive_content = 'UCS2 no class-PDU发送测试~#@%&:hello^*()'
        origin_val = ''
        try:
            self.at_handle.send_at('AT+CMGF=1', 10)
            self.at_handle.send_at('AT+CSCS="UCS2"', 10)
            value = self.at_handle.send_at('AT+CSMP?', 10)
            origin_val = re.findall(r'\+CSMP: (.*)', value)[0]      # 保存初始值，每次设置完后需要恢复
            self.at_handle.send_at('AT+CSMP=17,20,0,8', 10)
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.send_at(content, 10)
            self.at_handle.readline_keyword('OK', '+CMTI', at_flag=True, at_cmd=f'AT+CMSS=0,"{self.format_usc2_phone_number()}"')
            all_logger.info('模块已接收到短信')
            if self.page_notification.check_msg_push(self.phone_number, receive_content) is False:
                all_logger.info('短信内容或发件人号码核实不正确')
                raise WindowsSMSError('短信内容或发件人号码核实不正确')
            else:
                all_logger.info('短信内容及发件人号码核实正常')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)
            self.at_handle.send_at(f'AT+CSMP={origin_val}', 10)

    def format_usc2_phone_number(self):
        """
        将手机号格式化为UCS2格式
        :return:
        """
        ucs_list = []
        for i in self.phone_number:
            ucs_list.append('003')
            ucs_list.append(i)
        return ''.join(ucs_list)

    def send_ira_msg(self):
        """
        发送IRA格式短信
        :return:
        """
        content = '123456789ABCDEFGabcdefg'
        origin_val = ''
        try:
            self.at_handle.send_at('AT+CMGF=1', 10)
            self.at_handle.send_at('AT+CSCS="IRA"', 10)
            value = self.at_handle.send_at('AT+CSMP?', 10)
            origin_val = re.findall(r'\+CSMP: (.*)', value)[0]      # 保存初始值，每次设置完后需要恢复
            self.at_handle.send_at('AT+CSMP=17,196,0,0', 10)
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{self.phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(content.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', '+CMT', timout=30)
            all_logger.info('模块已接收到短信')
            if self.page_notification.check_msg_push(self.phone_number, content) is False:
                all_logger.info('短信内容或发件人号码核实不正确')
                raise WindowsSMSError('短信内容或发件人号码核实不正确')
            else:
                all_logger.info('短信内容及发件人号码核实正常')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)
            self.at_handle.send_at(f'AT+CSMP={origin_val}', 10)

    def send_wcdma_msg(self):
        """
        切换到卡二联通卡固定wcdma后发送短信
        :return:
        """
        try:
            self.at_handle.bound_network('WCDMA')
            self.send_gsm_msg('no_class')
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 10)

    def change_slot(self, slot):
        """
        切换卡槽
        :param slot:需要切换的卡槽 1或2
        :return:
        """
        cur_slot = self.at_handle.send_at('AT+QUIMSLOT?', 10)
        if f'+QUIMSLOT: {slot}' in cur_slot:
            all_logger.info(f'当前卡槽已是卡槽{slot},无需切换')
            self.check_cpin()
            self.at_handle.check_network()
            return True
        else:
            self.at_handle.send_at(f'AT+QUIMSLOT={slot}', 10)
            self.at_handle.readline_keyword('PB DONE', timout=90)
            self.at_handle.check_network()
            all_logger.info(f'已切换到卡槽{slot}')

    def check_cpin(self):
        """
        检查当前SIM卡状态是否正常
        :return:
        """
        cpin_val = self.at_handle.send_at('AT+CPIN?', 10)
        if '+CPIN: READY' in cpin_val:
            all_logger.info('当前SIM卡检测正常')
            return True
        else:
            all_logger.info('当前SIM卡检测异常')
            raise WindowsSMSError('当前SIM卡检测异常')

    def send_msg_with_ping(self):
        """
        做ping业务的时候正常收发短信
        :return:
        """
        self.at_handle.switch_to_mbim(self.mbim_driver_name)
        self.at_handle.check_network()
        self.windows_api.check_dial_init()
        ping = PINGThread(times=30, flag=True)
        ping.setDaemon(True)
        self.dial()
        ping.start()
        try:
            self.page_main.click_network_icon()
        except Exception:   # noqa
            self.page_main.click_network_icon()
        self.send_gsm_msg('no_class')
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        self.page_main.click_disconnect_button()
        ping.terminate()

    def dial(self):
        """
        模拟点击网络图标连接拨号
        :return:
        """
        self.disable_auto_connect_and_disconnect()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()

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
            raise WindowsSMSError("未发现连接按钮")

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
        raise WindowsSMSError(info)

    @staticmethod
    def disable_adapter():
        """
        禁用模块拨号网卡驱动
        :return:
        """
        subprocess.run('powershell Disable-NetAdapter -Name "手机网络" -Confirm:$false', shell=True, capture_output=True, text=True)
        value = subprocess.run('powershell Get-NetAdapter -Name "手机网络"', shell=True, capture_output=True, text=True)
        all_logger.info(value.stdout)
        if 'Disabled' in value.stdout:
            all_logger.info('手机网络已禁用')
            return True
        else:
            all_logger.info('禁用手机网络失败')
            raise WindowsSMSError('禁用手机网络失败')

    @staticmethod
    def enable_adapter():
        """
        启用模块拨号网卡驱动
        :return:
        """
        subprocess.run('powershell Enable-NetAdapter -Name "手机网络" -Confirm:$false', shell=True, capture_output=True, text=True)
        value = subprocess.run('powershell Get-NetAdapter -Name "手机网络"', shell=True, capture_output=True, text=True)
        all_logger.info(value.stdout)
        if 'Disconnected' in value.stdout or 'UP' in value.stdout:
            all_logger.info('手机网络已启用')
            return True
        else:
            all_logger.info('启用手机网络失败')
            raise WindowsSMSError('启用手机网络失败')

    def send_msg_no_push(self):
        """
        发送短信后检测通知中心未收到推送
        :return:
        """
        try:
            self.send_gsm_msg('no_class')
            return False
        except Exception:   # noqa
            all_logger.info('正常未检测到系统收到推送消息')
            return True

    def send_msg_with_disable_adapter(self):
        """
        禁用网卡情况下收发短信
        :return:
        """
        content = 'GSM msg test #%#*(()97970 #DGFHffh#1https://www.sina.com.cn/19/06/04,03:01:38+32+86'
        try:
            self.disable_adapter()
            if not self.send_msg_no_push():
                raise WindowsSMSError('禁用网卡驱动后仍检测到推送消息')
            self.enable_adapter()
            time.sleep(2)
            if self.page_notification.check_msg_push(self.phone_number, content) is False:
                all_logger.info('启用网卡后短信内容或发件人号码核实不正确')
                raise WindowsSMSError('启用网卡后短信内容或发件人号码核实不正确')
            else:
                all_logger.info('启用网卡后短信内容及发件人号码核实正常')
        finally:
            self.enable_adapter()

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
            raise WindowsSMSError('退出慢时钟失败')

    def cfun_reset(self):
        """
        CFUN11重启模块
        :return:
        """
        self.at_handle.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=80)

    def enable_low_power_registry(self):
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
                self.cfun_reset()
                all_logger.info('已激活注册表')
                return True
        except FileNotFoundError:   # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
        time.sleep(1)
        if 1 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('激活注册表失败')
            raise WindowsSMSError('激活注册表失败')
        else:
            self.cfun_reset()
            all_logger.info('已激活注册表')

    def disable_low_power_registry(self):
        """
        修改注册表，使模块退出慢时钟
        :return:
        """
        self.close_lowpower()
        self.at_handle.send_at('AT+QGPS=1', 10)
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
            raise WindowsSMSError('去激活注册表失败')
        else:
            self.cfun_reset()
            all_logger.info('已去激活注册表')

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
                raise WindowsSMSError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise WindowsSMSError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def open_lowpower(self):
        """
        指令开启慢时钟
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=1,1')
            if 'OK' in val:
                return True
        else:
            raise WindowsSMSError('开启慢时钟失败')

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
                raise WindowsSMSError('关闭GPS失败')
        else:
            return True

    def send_msg_with_low_power(self):
        """
        进入慢时钟后收发短信
        :return:
        """
        try:
            self.open_lowpower()
            self.enable_low_power_registry()
            self.close_gnss()
            time.sleep(10)
            self.debug_check(True, times=20)
            self.send_gsm_msg('no_class')
        finally:
            self.close_lowpower()
            self.disable_low_power_registry()
            self.close_gnss()

    def get_sim_2_number(self):
        """
        系统上不配置SIM卡二号码，需要自己获取
        :return:
        """
        iccid_num = self.at_handle.send_at('AT+QCCID', 10)
        iccid = ''.join(re.findall(r'\+QCCID: (\d+\S+)', iccid_num))[:-1]  # 最后一位号码舍弃
        headers = {"Authorization": "bearerb96ee906-7dda-4df4-b7bc-008ee3b2d7ca"}
        url = f'https://sim.quectel.com:8213/api/globalSims?keyword={iccid}'
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            all_logger.info(f'请求获取手机号错误，接口返回:{r.json()}')
            raise WindowsSMSError(f'请求获取手机号错误，接口返回:{r.json()}')
        return r.json()['data'][0]['number']

    def send_gsm_msg_num(self, class_type, phone_number):
        """
        发送GSM格式短信,需要传入手机号，用于使用卡二发送短信
        :param class_type:短信类型。如 no class，class 0等
        :param phone_number:手机号码
        :return:
        """
        class_dict = {'no_class': '17,71,0,0', 'class_0': '17,0,0,240', 'class_1': '17,167,0,241',
                      'class_2': '17,168,0,242', 'class_3': '17,197,0,243'}
        origin_val = ''
        try:
            value = self.at_handle.send_at('AT+CSMP?', 10)
            origin_val = re.findall(r'\+CSMP: (.*)', value)[0]      # 保存初始值，每次设置完后需要恢复
            self.at_handle.send_at('AT+CMGF=1', 10)
            self.at_handle.send_at(f'AT+CSMP={class_dict[class_type]}', 10)
            content = 'GSM msg test #%#*(()97970 #DGFHffh#1https://www.sina.com.cn/19/06/04,03:01:38+32+86'
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', '+CMT', timout=30)
            all_logger.info('模块已接收到短信')
            if self.page_notification.check_msg_push(phone_number, content) is False:
                all_logger.info('短信内容或发件人号码核实不正确')
                raise WindowsSMSError('短信内容或发件人号码核实不正确')
            else:
                all_logger.info('短信内容及发件人号码核实正常')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)
            self.at_handle.send_at(f'AT+CSMP={origin_val}', 10)

    def sim_2_send_msg(self):
        """
        使用卡二自发自收信息
        :return:
        """
        number = self.get_sim_2_number()    # 首先获取SIM卡二手机号
        self.at_handle.check_network()
        self.windows_api.check_dial_init()
        self.send_gsm_msg_num('no_class', number)
