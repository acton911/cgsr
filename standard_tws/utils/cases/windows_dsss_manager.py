import getpass
import os
import pickle
import re
import subprocess
import time
import requests
import serial
from threading import Thread
from utils.exception.exceptions import WindowsDSSSError
from utils.functions.gpio import GPIO
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.decorators import startup_teardown
from tapp_constructor import constructor
if os.name == "nt":
    from utils.pages.page_main import PageMain
    from utils.pages.page_mobile_broadband import PageMobileBroadband
    from utils.functions.windows_api import WindowsAPI
    from utils.pages.win11_page_mobile_broadband import Win11PageMobileBroadband
    from utils.pages.win11_page_main import Win11PageMain
    from utils.functions.fw import FW


class WindowsDSSSManager:
    def __init__(self, at_port, dm_port, card_info, mbim_driver_name, profile_info, params_path, firmware_path, ati, csub):
        self.at_port = at_port
        self.dm_port = dm_port
        self.deviceCardList = card_info
        self.profile_info = profile_info
        self.mbim_driver_name = mbim_driver_name
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.params_path = params_path
        self.gpio = GPIO()
        self.system_number = ''  # 系统上做主叫或被叫业务使用的号码
        self.firmware_path = firmware_path
        self.ati = ati
        self.csub = csub
        if os.name == 'nt':
            self.at_handle.switch_to_mbim(mbim_driver_name)
            self.page_main = PageMain()
            self.pageMobileBroadband = PageMobileBroadband()
            self.windows_api = WindowsAPI()
            self.win11_pageMobileBroadband = Win11PageMobileBroadband()
            self.win11_page_main = Win11PageMain()

    def check_slot(self):
        """
        确认当前SIM卡卡槽
        :return: True：卡槽一，False：卡槽二
        """
        slot_number = self.at_handle.send_at('AT+QUIMSLOT?', timeout=30)
        if '+QUIMSLOT: 1' in slot_number:
            return True
        elif '+QUIMSLOT: 2' in slot_number:
            return False
        else:
            raise WindowsDSSSError('确认当前SIM卡卡槽失败')

    def query_slot(self, slot):
        """
        检查当前卡槽是否正常
        :param slot:预期卡槽位置  1, 2
        :return:
        """
        if slot == 1:
            if not self.check_slot():
                raise WindowsDSSSError('当前卡槽位置不为一，期望处于卡槽一')
        else:
            if self.check_slot():
                raise WindowsDSSSError('当前卡槽位置不为二，期望处于卡槽二')

    def check_sim_info(self, slot):
        """
        检测SIM卡信息是否正常
        :param slot: 需要检查的卡槽
        :return:
        """
        sys_imsi_2 = ''
        sys_qccid_2 = ''
        iccid = self.at_handle.send_at('AT+QCCID', 3)
        re_iccid = ''.join(re.findall(r"\+QCCID: (\d+\S+)", iccid))
        cimi_data = self.at_handle.send_at('AT+CIMI', 3)
        re_imsi = ''.join(re.findall(r'AT\+CIMI\s+(\d+)\s+OK\s+', cimi_data))
        for i in self.deviceCardList:
            if i.get('evb_slot_number') == 2 and i.get('slot_number') == 1:
                sys_qccid_2 = i['sim_iccid']
                sys_imsi_2 = i['sim_imsi']
        sys_qccid_1 = self.deviceCardList[0]['sim_iccid']
        sys_imsi_1 = self.deviceCardList[0]['sim_imsi']
        if slot == 1:
            if sys_imsi_1 != re_imsi:
                raise WindowsDSSSError('卡一IMSI号与系统不一致，系统下发为{}，实际查询为{}'.format(sys_imsi_1, re_imsi))
            if sys_qccid_1 != re_iccid:
                raise WindowsDSSSError('卡一ICCID号与系统不一致，系统下发为{}，实际查询为{}'.format(sys_qccid_1, re_iccid))
        elif slot == 2:
            if sys_imsi_2 != re_imsi:
                raise WindowsDSSSError('卡二IMSI号与系统不一致，系统下发为{}，实际查询为{}'.format(sys_imsi_2, re_imsi))
            if sys_qccid_2 != re_iccid:
                raise WindowsDSSSError('卡二ICCID号与系统不一致，系统下发为{}，实际查询为{}'.format(sys_qccid_2, re_iccid))

    def change_simcard(self, slot):
        """
        AT+QUIMSLOT=指令切换卡槽
        :param slot: 1：使用卡槽一；2：使用卡槽二
        :return: None
        """
        self.at_handle.send_at('AT+QUIMSLOT={}'.format(slot), timeout=30)
        self.at_handle.readline_keyword(keyword1='READY', keyword2='PB DONE', timout=80)

    def check_mbn(self, mode):
        """
        换卡后检查激活MBN
        :param mode: 所检查的运营商
        """
        if 'CU' in mode:
            mode = 'CU'
        elif 'CMCC' in mode:
            mode = 'CMCC'
        elif 'CT' in mode:
            mode = 'CT'
        mbn_value = self.at_handle.send_at('AT+QMBNCFG="LIST"', 10)
        activate_mbn = ''.join(re.findall(r'\+QMBNCFG: "List",\d+,\d,1,.*', mbn_value))
        if mode in activate_mbn:
            all_logger.info('查询激活MBN正常')
        else:
            all_logger.info('查询激活MBN值为{}'.format(activate_mbn))
            raise WindowsDSSSError('查询激活MBN失败')

    def check_module_info(self, cfun):
        """
        查询模块基本信息，CFUN及CPIN值
        :param cfun: 查询预期CFUN值
        :return:
        """
        cfun_value = self.at_handle.send_at('AT+CFUN?', 3)
        cpin_value = self.at_handle.send_at('AT+CPIN?', 3)
        if cfun == 0:
            if 'CFUN: 0' not in cfun_value:
                raise WindowsDSSSError('设置CFUN为0后切换到另一卡槽查询不为0')
            if 'CME ERROR' not in cpin_value:
                raise WindowsDSSSError('CFUN值为0，CPIN查询期望返回CME ERROR')
        elif cfun == 1:
            if 'CFUN: 1' not in cfun_value:
                raise WindowsDSSSError('设置CFUN为1后切换到另一卡槽查询不为1')
            if 'CPIN: READY' not in cpin_value:
                raise WindowsDSSSError('CFUN值为1，CPIN查询期望返回CPIN: READY')
        elif cfun == 4:
            if 'CFUN: 4' not in cfun_value:
                raise WindowsDSSSError('设置CFUN为4后切换到另一卡槽查询不为4')
            if 'CPIN: READY' not in cpin_value:
                raise WindowsDSSSError('CFUN值为4，CPIN查询期望返回CPIN: READY')

    def hang_up_after_module_answer(self, slot):
        """
        被叫方接听n秒后，系统主动挂断
        :param slot: 当前是卡一接听还是卡二接听
        :return:
        """
        phone_number = ''
        if slot == 1:
            phone_number = self.deviceCardList[slot - 1]['phonenumber']
        else:
            for i in self.deviceCardList:
                if i.get('evb_slot_number') == 2 and i.get('slot_number') == 1:
                    phone_number = i['phonenumber']
        content = {"exec_type": 1,
                   "payload": {
                       "phone_number": phone_number,
                       "hang_up_after_answer": 5   # 接听后3S挂断
                   },
                   "request_id": "10011"
                   }
        dial_request = requests.post(self.url, json=content)
        all_logger.info(dial_request.json())
        self.system_number = dial_request.json()['data']['phone_number']
        self.check_dial_called(True)
        self.at_handle.send_at('ATH', 10)

    def check_dial_called(self, is_answered=False):
        """
        模块被叫，检测Ring是否正常上报，接通及不接通时呼叫状态是否正常
        :param is_answered:模块被叫检测到Ring上报后是否接通，True:模块主动接通，False:模块不接通
        :return:
        """
        self.at_handle.readline_keyword('RING', timout=80)
        dial_state = self.at_handle.send_at('AT+CLCC', 10)
        if ''.join(re.findall(r'\+CLCC: \d,\d,(\d).*{}.*'.format(self.system_number), dial_state)) != '4':
            raise WindowsDSSSError('当前拨号模块被叫状态异常')   # 异常
        else:
            all_logger.info('模块处于来电状态中，状态正常')
        if is_answered:
            self.at_handle.send_at('ATA', 10)   # 先接通来电
            time.sleep(1)
            dial_state = self.at_handle.send_at('AT+CLCC', 10)
            if ''.join(re.findall(r'\+CLCC: \d,\d,(\d).*{}.*'.format(self.system_number), dial_state)) != '0':
                raise WindowsDSSSError('当前拨号模块被叫状态异常')   # 异常
            else:
                all_logger.info('当前来电已接通，状态正常')

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
            raise WindowsDSSSError("未发现连接按钮")

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
        raise WindowsDSSSError(info)

    def mbim_dial(self):
        """
        flag:True:进行取消自动拨号；False:直接进行拨号连接
        MBIM拨号
        :return:
        """
        self.get_interface_name()
        time.sleep(10)  # 等待MBIM拨号稳定
        self.disable_auto_connect_and_disconnect()
        self.disable_auto_connect_find_connect_button()
        try:
            self.page_main.click_connect_button()
        except Exception as e:
            all_logger.info(e)
            self.page_main.click_connect_button()
        self.check_mbim_connect()
        time.sleep(1)

    def check_restart_slot(self, slot=1):
        """
        模块重启后检查SIM卡卡槽
        slot: 检查卡槽一 还是卡槽二
        :return:
        """
        if slot == 1:
            if self.check_slot():
                self.at_handle.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
                if self.check_slot():
                    return True
                else:
                    raise WindowsDSSSError('重启后SIM卡卡槽不为1')
        else:
            if not self.check_slot():
                self.at_handle.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
                if not self.check_slot():
                    return True
                else:
                    raise WindowsDSSSError('重启后SIM卡卡槽不为2')

    def check_restart_slot_win11(self, slot=1):
        """
        笔电中模块重启后检查SIM卡卡槽，因为重启后相关URC上报很快，可能会捕捉不到，重启后直接检查卡槽是否切换成功及CPIN状态
        slot: 检查卡槽一 还是卡槽二
        :return:
        """
        if slot == 1:
            if self.check_slot():
                self.at_handle.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                time.sleep(5)
                self.check_module_info(1)
                if self.check_slot():
                    return True
                else:
                    raise WindowsDSSSError('重启后SIM卡卡槽不为1')
        else:
            if not self.check_slot():
                self.at_handle.cfun1_1()
                self.driver_check.check_usb_driver_dis()
                self.driver_check.check_usb_driver()
                time.sleep(5)
                self.check_module_info(1)
                if not self.check_slot():
                    return True
                else:
                    raise WindowsDSSSError('重启后SIM卡卡槽不为2')

    @staticmethod
    def get_interface_name():
        """
        获取连接的名称
        :return: 当前连接名称
        """
        for i in range(10):
            mobile_broadband_info = os.popen('netsh mbn show interface').read()
            mobile_broadband_num = ''.join(re.findall(r'系统上有 (\d+) 个接口', mobile_broadband_info))  # 手机宽带数量
            if mobile_broadband_num and int(mobile_broadband_num) > 1:
                raise WindowsDSSSError("系统上移动宽带有{}个，多于一个".format(mobile_broadband_num))
            mobile_broadband_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', mobile_broadband_info))
            if mobile_broadband_name != '':
                return mobile_broadband_name
            time.sleep(5)

    def windows_change_slot(self, slot):
        """
        slot: 需要切换的卡槽。1：卡槽一；2：卡槽二
        Windows界面控制切换卡槽
        :return:
        """
        current_slot = self.pageMobileBroadband.check_slot()    # 首先确认当前卡槽
        if slot == 1:
            if current_slot.exists(timeout=10):     # 如果当前是卡槽1，则先切到卡槽二再切回卡槽一
                if not self.check_slot():
                    self.change_simcard(1)
                self.pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', timout=50)
                self.pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
            else:   # 如果当前是卡槽二，则直接切到卡槽一
                if self.check_slot():
                    self.change_simcard(2)
                self.pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
        else:
            if current_slot.exists(timeout=10):  # 如果当前是卡槽1，则直接切到卡槽二
                if not self.check_slot():  # 指令查询如果是卡槽二，则切换到卡槽一
                    self.change_simcard(1)
                self.pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
            else:  # 如果当前是卡槽二，则先切换切到卡槽一再切换到卡槽二
                if self.check_slot():  # 指令查询如果是卡一，则切换到卡二
                    self.change_simcard(2)
                self.pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', timout=50)
                self.pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)

    @startup_teardown(startup=['win11_pageMobileBroadband', 'open_mobile_broadband_page'])
    def win11_change_slot(self, slot):
        """
        slot: 需要切换的卡槽。1：卡槽一；2：卡槽二
        Windows界面控制切换卡槽
        :return:
        """
        self.win11_pageMobileBroadband.mobile_page_up()   # 电脑打开网络页面可能不显示卡槽信息，默认首先向上翻页
        current_slot = self.win11_pageMobileBroadband.check_slot()    # 首先确认当前卡槽
        if slot == 1:
            if current_slot.exists(timeout=10):     # 如果当前是卡槽1，则先切到卡槽二再切回卡槽一
                if not self.check_slot():
                    self.change_simcard(1)
                self.win11_pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', timout=50)
                self.win11_pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
            else:   # 如果当前是卡槽二，则直接切到卡槽一
                if self.check_slot():
                    self.change_simcard(2)
                self.win11_pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
        else:
            if current_slot.exists(timeout=10):  # 如果当前是卡槽1，则直接切到卡槽二
                if not self.check_slot():  # 指令查询如果是卡槽二，则切换到卡槽一
                    self.change_simcard(1)
                self.win11_pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)
            else:  # 如果当前是卡槽二，则先切换切到卡槽一再切换到卡槽二
                if self.check_slot():  # 指令查询如果是卡一，则切换到卡二
                    self.change_simcard(2)
                self.win11_pageMobileBroadband.choose_simcard_1()
                self.at_handle.readline_keyword('+CPIN: READY', timout=50)
                self.win11_pageMobileBroadband.choose_simcard_2()
                self.at_handle.readline_keyword('+CPIN: READY', 'PB DONE', timout=80)

    def win11_disable_auto_connect_and_disconnect(self):
        """
        笔电取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        try:
            self.win11_page_main.click_network_icon()
        except Exception:   # noqa
            self.win11_page_main.click_network_icon()
        self.win11_page_main.click_network_details()
        disconnect_button = self.win11_page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.win11_page_main.click_disable_auto_connect()
        self.windows_api.press_esc()

    def win11_disable_auto_connect_find_connect_button(self):
        """
        笔电windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            self.win11_page_main.click_network_icon()
            self.win11_page_main.click_network_details()
            status = self.win11_page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
        else:
            raise WindowsDSSSError("未发现连接按钮")

    def win11_check_mbim_connect(self, auto_connect=False):
        """
        笔电检查mbim是否是连接状态。
        :return: None
        """
        num = 0
        timeout = 30
        connect_info = None
        already_connect_info = None
        while num <= timeout:
            connect_info = self.win11_page_main.element_mbim_disconnect_button.exists()
            already_connect_info = self.win11_page_main.element_mbim_already_connect_text.exists()
            if auto_connect is False:
                if connect_info and already_connect_info:
                    return True
            else:
                if already_connect_info:
                    return True
            num += 1
            time.sleep(1)
        info = '未检测到断开连接按钮，' if not connect_info and not auto_connect else '' + '未检测到已经连接信息' if not already_connect_info else ""
        raise WindowsDSSSError(info)

    def dial(self):
        """
        模拟点击网络图标连接拨号
        :return:
        """
        self.win11_disable_auto_connect_and_disconnect()
        self.win11_disable_auto_connect_find_connect_button()
        self.win11_page_main.click_connect_button()
        self.win11_check_mbim_connect()

    def win11_mbim_dial(self):
        """
        笔电项目用拨号
        @return:
        """
        self.windows_api.check_dial_init()
        self.dial()
        self.windows_api.ping_get_connect_status()
        self.windows_api.press_esc()
        self.win11_page_main.click_network_icon()
        self.win11_page_main.click_network_details()
        self.win11_page_main.click_disconnect_button()

    def sim_det(self, is_open):
        """
        开启/关闭SIM卡热插拔功能
        :param is_open:是否开启热插拔功能 True:开启；False:关闭
        :return:
        """
        if is_open:
            self.at_handle.send_at('AT+QSIMDET=1,1', 10)
            self.at_handle.send_at('AT+QSIMSTAT=1', 10)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)
            if '1,1' in self.at_handle.send_at('AT+QSIMDET?', 10) and '+QSIMSTAT: 1' in self.at_handle.send_at('AT+QSIMSTAT?', 10):
                all_logger.info('成功开启热插拔功能')
            else:
                all_logger.info('开启热拔插功能失败')
                raise WindowsDSSSError('开启热拔插功能失败')
        else:
            self.at_handle.send_at('AT+QSIMDET=0,1', 10)
            self.at_handle.send_at('AT+QSIMSTAT=0', 10)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)
            if '0,1' in self.at_handle.send_at('AT+QSIMDET?', 10) and '+QSIMSTAT: 0' in self.at_handle.send_at('AT+QSIMSTAT?', 10):
                all_logger.info('成功关闭热插拔功能')
            else:
                all_logger.info('关闭热拔插功能失败')
                raise WindowsDSSSError('关闭热拔插功能失败')

    def check_sim_det_urc(self, is_ready, slot):
        """
        检测热插拔功能时上报的URC
        :param is_ready:掉卡或识别到卡URC True:正常识别SIM卡；False:掉卡
        :param slot:操作的卡槽
        :return:
        """
        check_content = ['+QSIMSTAT: 1,1', '+CPIN: READY', '+QUSIM: 1', '+QIND: SMS DONE', '+QIND: PB DONE'] \
            if is_ready else ['+QSIMSTAT: 1,0', '+CPIN: NOT READY']
        urc_check = URCCheck(self.at_port, check_content)
        urc_check.setDaemon(True)
        urc_check.start()
        time.sleep(1)
        if slot == 1:
            self.gpio.set_sim1_det_high_level() if is_ready else self.gpio.set_sim1_det_low_level()     # 拉低或拉高SIM_DET引脚检测掉卡URC上报
        elif slot == 2:
            self.gpio.set_sim2_det_high_level() if is_ready else self.gpio.set_sim2_det_low_level()     # 拉低或拉高SIM_DET引脚检测掉卡URC上报
        urc_check.join()
        if urc_check.error_msg:
            all_logger.info(f'开启热插拔后插拔卡URC异常{urc_check.error_msg}')
            raise WindowsDSSSError(f'开启热插拔后插拔卡URC异常{urc_check.error_msg}')
        else:
            all_logger.info('开启热插拔后插拔卡URC检测正常')

    def check_slot_2_note(self):
        """
        笔电项目专用，执行case前首先检查卡槽二是否激活ESIM，如未激活首先激活再执行case
        """
        from windows11_esim import WindowsEsim
        win11_esim = WindowsEsim(self.at_port, self.dm_port, self.mbim_driver_name, self.profile_info)
        win11_esim.windows_esim_4(False)

    def delete_esim_profile(self):
        """
        删除esim使用的profile文件
        """
        from windows11_esim import WindowsEsim
        win11_esim = WindowsEsim(self.at_port, self.dm_port, self.mbim_driver_name, self.profile_info)
        win11_esim.windows_esim_3()

    def change_switcher(self, slot):
        """
        使用切卡器切换卡槽
        :param slot:需要切换的卡槽
        """
        switcher_port = self.deviceCardList[0]['switcher']
        with serial.Serial(switcher_port, baudrate=115200, timeout=0) as _switch_port:
            _switch_port.setDTR(False)
            time.sleep(1)
            start_time = time.time()
            _switch_port.write(f"SIMSWITCH,{slot}\r\n".encode('utf-8'))
            while time.time() - start_time < 3:
                value = _switch_port.readline().decode('utf-8')
                if value:
                    all_logger.info(value)
                if 'OK' in value:
                    break
        self.at_handle.send_at('AT+CFUN=0', 15)
        time.sleep(1)
        self.at_handle.send_at('AT+CFUN=1', 15)

    def change_evb_slot_empty(self):
        """
        将EVB卡槽一上的切卡器切到空卡槽
        """
        self.change_switcher('8')   # 将切卡器切到卡槽8
        time.sleep(5)
        cpin_value = self.at_handle.send_at('AT+CPIN?', 3)
        if 'ERROR' in cpin_value:
            all_logger.info('切换空卡槽成功，识别不到SIM卡')
        elif '+CPIN: READY' in cpin_value:
            all_logger.info('切换空卡槽后，仍能识别到SIM')
            raise WindowsDSSSError('切换空卡槽后，仍能识别到SIM')

    def check_disable_physim_default_value(self):
        """
        检测禁用SIM卡默认值
        """
        value = self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM"', 5)
        if '+QSIMCFG: "disable_physim",0,0' in value:
            all_logger.info('禁用SIM卡默认值检查正常')
            return True
        else:
            all_logger.info('禁用SIM卡默认值检查异常')
            raise WindowsDSSSError('禁用SIM卡默认值检查异常')

    def get_test_times(self):
        """
        获取当前重启次数
        """
        try:
            with open(self.params_path, 'rb') as p:
                # original_setting
                original_setting = pickle.load(p).test_setting
                if not isinstance(original_setting, dict):
                    original_setting = eval(original_setting)
                all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
                # case_setting
                case_setting = pickle.load(p)
                all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
                # script_context
                script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
                all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
        except SyntaxError:
            raise Exception("\n系统参数解析异常：\n原始路径: \n {}".format(repr(self.params_path)))
        all_logger.info('-'*99)
        all_logger.info(case_setting)
        all_logger.info('-'*99)
        try:
            test_times = case_setting['restart_parameters'].get('testtimes', None)
            all_logger.info(f'当前测试重启次数为{test_times}')
            return test_times
        except Exception:   # noqa
            return None

    def restart_computer(self, test_times):
        # 第一步，解析下发参数，获取重启方法所需参数值
        try:
            with open(self.params_path, 'rb') as p:
                # original_setting
                original_setting = pickle.load(p).test_setting
                if not isinstance(original_setting, dict):
                    original_setting = eval(original_setting)
                all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
                # case_setting
                case_setting = pickle.load(p)
                all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
                # script_context
                script_context = eval(case_setting["script_context"])  # 脚本所有TWS系统传参
                all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
        except SyntaxError:
            raise Exception("\n系统参数解析异常：\n原始路径: \n {}".format(repr(self.params_path)))

        # 第二步，实例化TestOperation类，之后赋值restart方法需要的参数，方便之后调用
        con = constructor.TestOperation()
        # 赋值restart方法所需参数
        constructor.current_test_case = {"id_case": case_setting['id_case']}
        constructor.main_task_id = original_setting['task_id']

        # 第三步，进行重启
        # 重启前关闭QualcommPackageManager工具，该工具会阻止电脑重启
        all_logger.info(os.popen('taskkill /f /t /im QualcommPackageManager*').read())
        all_logger.info(os.popen('taskkill /f /t /im QuectelLogCollectTool*').read())
        all_logger.info('开始重启整机')
        con.restart(testtimes=test_times)    # 重启

    def get_q_mode_switch_path(self):
        """
        获取本机的QModeSwitch工具的路径，默认 C:\\Users\\q\\Desktop\\Tools 下
        """
        check_path = fr"C:\Users\{getpass.getuser()}\Desktop\Tools"
        ati = self.at_handle.send_at('ATI')
        ati_regex = ''.join(re.findall(r'Revision: (\w+)', ati))
        pattern = ati_regex[:5]  # QModeSwitch_RM520_xxxx.exe，所以取ATI前五位判断QModeSwitch是否正常
        for path, _, files in os.walk(check_path):
            for file in files:
                if file.endswith('.exe') and file.startswith("QModeSwitch") and pattern in file:
                    mode_switch_tool_path = os.path.join(path, file)
                    return mode_switch_tool_path
        raise WindowsDSSSError(f"在{check_path}中未找到适合{pattern}的QModeSwitch，请检查工具文件夹是否存在，版本是否正常")

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
            raise WindowsDSSSError(f"连续三次使用QModeSwitch工具关闭端口失败，期望AT口({self.at_port}), DM口({self.dm_port})\n"
                          f"当前端口列表：{port_list}")

    def close_all_ports(self):
        # 打开所有端口->判断AT口DM口是否存在
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.close_all_ports_and_check(q_mode_switch_path)

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
            raise WindowsDSSSError(f"连续三次使用QModeSwitch工具打开端口失败，期望AT口({self.at_port}), DM口({self.dm_port})\n"
                          f"当前端口列表：{port_list}")

    def open_all_ports(self):
        # 打开所有端口->判断AT口DM口是否存在
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.open_all_ports_and_check(q_mode_switch_path)

    @staticmethod
    def mbim_connect():
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
            all_logger.info("连接拨号失败！\r\n{}".format(data3))
            raise WindowsDSSSError("连接拨号失败！\r\n{}".format(data3))
        time.sleep(10)

    @staticmethod
    def check_mbim_connect_disconnect(connect=True):
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
            all_logger.info("异常！当前没有断开连接！\r\n{}".format(data3))
            raise WindowsDSSSError("异常！当前没有断开连接！\r\n{}".format(data3))
        elif connect and '断开连接' in data3:
            all_logger.info("异常！当前没有连接！\r\n{}".format(data3))
            raise WindowsDSSSError("异常！当前没有连接！\r\n{}".format(data3))

    def mbim_connect_and_check(self):
        """
        mbim连接，检查是否正常
        :return: None
        """
        time.sleep(10)
        all_logger.info('开始建立连接')
        self.mbim_connect()
        self.check_mbim_connect_disconnect()
        self.windows_api.ping_get_connect_status()
        time.sleep(5)

    def fw_upgrade(self):
        """
        笔电升级
        """
        fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path, factory=False,
                ati=self.ati, csub=self.csub)
        fw.upgrade()

    def check_windows_slot(self, is_exits):
        """
        检测是否存在SIM卡切换选项
        :param is_exits: 期望是否存在
        """
        self.win11_pageMobileBroadband.open_mobile_broadband_page()
        self.win11_pageMobileBroadband.mobile_page_up()   # 电脑打开网络页面可能不显示卡槽信息，默认首先向上翻页
        try:
            self.win11_pageMobileBroadband.check_change_slot_exist.print_control_identifiers()
            flag = True
        except Exception:   # noqa
            flag = False
        if flag:
            if is_exits:
                all_logger.info('当前存在切换SIM卡选项功能,符合预期')
            else:
                all_logger.info('当前存在切换SIM卡选项功能,不符合预期')
                raise WindowsDSSSError('当前存在切换SIM卡选项功能,不符合预期')
        else:
            if not is_exits:
                all_logger.info('当前不存在切换SIM卡选项功能,符合预期')
            else:
                all_logger.info('当前不存在切换SIM卡选项功能,不符合预期')
                raise WindowsDSSSError('当前不存在切换SIM卡选项功能,不符合预期')


class URCCheck(Thread):
    def __init__(self, at_port, check_content: list):
        """
        检测热插拔时的URC上报
        :param at_port:
        :param check_content:
        """
        super().__init__()
        self.at_handle = ATHandle(at_port)
        self.check_content = check_content
        self._at_port = serial.Serial()
        self._at_port.port = at_port
        self._at_port.baudrate = 115200
        self._at_port.timeout = 0
        self._at_port.open()
        self.error_msg = ''
        self.stop_word = check_content[-1]

    def run(self) -> None:
        try:
            start_time = time.time()
            return_value_cache = ''
            while True:
                return_value = self.at_handle.readline(self._at_port)
                return_value_cache += return_value
                if len(self.check_content) > 2 and self.stop_word in return_value:      # 掉卡检测可能先上报CPIN NOT READY也可能先上报SIMSTAT
                    all_logger.info(f'已检测到{self.stop_word}')
                    break
                elif len(self.check_content) == 2:
                    if self.check_content[0] in return_value_cache and self.check_content[1] in return_value_cache:
                        all_logger.info(f'已检测到{self.stop_word}')
                        break
                if time.time() - start_time > 60:
                    all_logger.info(f'60S内未检测到{self.stop_word}上报')
                    raise WindowsDSSSError(f'60S内未检测到{self.stop_word}上报')
            all_logger.info('AT口检测到上报URC为:\r\n{}'.format(return_value_cache.strip().replace('\r\n', '  ')))
            for i in self.check_content:
                if i not in return_value_cache:
                    self.error_msg += 'AT口未检测到{}上报  '.format(i)
                if self.error_msg != '':
                    raise WindowsDSSSError(self.error_msg)
            else:
                all_logger.info('AT口URC检测正常'.format())
        except Exception as e:
            self.error_msg += str(e)
        finally:
            self._at_port.close()
