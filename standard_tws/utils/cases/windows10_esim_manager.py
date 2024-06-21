import os
import re
import time
from threading import Thread
import serial
from utils.functions.images import pic_compare
from utils.functions.decorators import startup_teardown
from utils.functions.windows_api import WindowsAPI
from utils.pages.page_main import PageMain
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import WindowsEsimError
from utils.operate.at_handle import ATHandle
from pywinauto.keyboard import send_keys
from utils.functions.driver_check import DriverChecker
from utils.pages.page_mobile_broadband import PageMobileBroadband


class Windows10EsimManager:
    path_to_airplane_mode_pic = "utils/images/toolbar_airplane_mode"
    path_to_toolbar_network_pic = "utils/images/toolbar_network"
    path_to_sim_lock_pic = 'utils/images/sim_locked_signal'

    def __init__(self, at_port, dm_port, mbim_driver, profile_info):
        self.at_port = at_port
        self.dm_port = dm_port
        self.mbim_driver = mbim_driver
        self.profile_info = profile_info.split(',')
        self.activation_code_A = self.profile_info[0].strip()   # 三个激活码，期望A和B为同运营商，C为不用运营商
        self.activation_code_B = self.profile_info[2].strip()
        self.activation_code_C = self.profile_info[4].strip()
        self.iccid_A = self.profile_info[1].strip()
        self.iccid_B = self.profile_info[3].strip()
        self.iccid_C = self.profile_info[5].strip()
        self.page_main = PageMain()
        self.windows_api = WindowsAPI()
        self.at_handle = ATHandle(at_port)
        self.at_handle.switch_to_mbim(self.mbim_driver)
        self.windows_api.check_dial_init()
        self.driver_check = DriverChecker(at_port, dm_port)
        self.pageMobileBroadband = PageMobileBroadband()
        try:
            self.disable_auto_connect_and_disconnect()  # 确保取消自动拨号
        except Exception:   # noqa
            pass
        self.windows_change_slot()      # 保证测试时候为卡槽二

    @startup_teardown(startup=['pageMobileBroadband', 'open_mobile_broadband_page'])
    def windows_change_slot(self):
        """
        slot: 需要切换的卡槽。1：卡槽一；2：卡槽二
        Windows界面控制切换卡槽
        :return:
        """
        current_slot = self.pageMobileBroadband.check_slot()    # 首先确认当前卡槽
        if current_slot.exists(timeout=10):  # 如果当前是卡槽1，则直接切到卡槽二
            self.pageMobileBroadband.choose_simcard_2()
            time.sleep(3)   # 切换后等待一会再执行后续操作
        else:
            all_logger.info('当前已是卡槽二')

    def check_cpin(self, is_ready=True):
        """
        检测cpin状态
        :param is_ready: profile文件是否应用情况下检测
        :return:
        """
        cpin_value = self.at_handle.send_at('AT+CPIN?', 5)
        if is_ready:
            if '+CPIN: READY' not in cpin_value:
                all_logger.info('当前CPIN状态异常')
                raise WindowsEsimError('当前CPIN状态异常')
        else:
            if 'CME ERROR' not in cpin_value:
                all_logger.info('profile文件未激活状态，CPIN返回异常')

    def set_pn_lock(self):
        """
        设置PN锁
        :return:
        """
        self.at_handle.send_at('AT+CLCK="PN",1,"1234"', 5)
        value = self.at_handle.send_at('AT+CLCK="PN",2', 5)
        if '+CLCK: 1' not in value:
            all_logger.info('设置PN锁后AT+CLCK="PN",2查询设置失败')
            raise WindowsEsimError('设置PN锁后AT+CLCK="PN",2查询设置失败')

    def check_pn_lock(self):
        """
        检查pn锁是否生效
        :return:
        """
        cpin_value = self.at_handle.send_at('AT+CPIN?', 5)
        if '+CPIN: PH-NET PIN' not in cpin_value:
            all_logger.info('PN锁上锁生效后，切换不同运营商检查失败')
            raise WindowsEsimError('PN锁上锁生效后，切换不同运营商检查失败')

    def unlock_sc_lock(self, pwd):
        """
        解锁SC锁
        :param pwd: SC锁密码
        :return:
        """
        if '+CLCK: 1' in self.at_handle.send_at('AT+CLCK="SC",2', 5):
            self.at_handle.send_at('AT+CLCK="SC",0,"{}"'.format(pwd), 5)
            value = self.at_handle.send_at('AT+CLCK="SC",2', 5)
            if '+CLCK: 0' not in value:
                all_logger.info("SC锁解锁后检查异常")
                raise WindowsEsimError("SC锁解锁后检查异常")
        else:
            all_logger.info('SC锁已解锁，无需再解')
            return None

    def unlock_pn_lock(self):
        """
        解除PN锁
        :return:
        """
        if '+CLCK: 0' in self.at_handle.send_at('AT+CLCK="PN",2', 5):
            all_logger.info('PN锁已解锁，无需再解')
            return None
        self.at_handle.send_at('AT+CLCK="PN",0,"1234"', 5)
        value = self.at_handle.send_at('AT+CLCK="PN",2', 5)
        if '+CLCK: 0' not in value:
            all_logger.info("PN锁解锁后检查异常")
            raise WindowsEsimError("PN锁解锁后检查异常")

    def set_pf_lock(self):
        """
        设置PF锁
        :return:
        """
        self.at_handle.send_at('AT+CLCK="PF",1,"1234"', 5)
        value = self.at_handle.send_at('AT+CLCK="PF",2', 5)
        if '+CLCK: 1' not in value:
            all_logger.info('设置PN锁后AT+CLCK="PF",2查询设置失败')
            raise WindowsEsimError('设置PN锁后AT+CLCK="PF",2查询设置失败')

    def check_pf_lock(self):
        """
        检测PF锁是否生效
        :return:
        """
        cpin_value = self.at_handle.send_at('AT+CPIN?', 5)
        if '+CPIN: PH-FSIM PIN' not in cpin_value:
            all_logger.info('PF锁上锁生效后，切换不同profile文件检查失败')
            raise WindowsEsimError('PF锁上锁生效后，切换不同profile文件检查失败')

    def unlock_pf_lock(self):
        """
        PF锁解锁
        :return:
        """
        if '+CLCK: 0' in self.at_handle.send_at('AT+CLCK="PF",2', 5):
            all_logger.info('PF锁已解锁，无需再解')
            return None
        self.at_handle.send_at('AT+CLCK="PF",0,"1234"', 5)
        value = self.at_handle.send_at('AT+CLCK="PF",2', 5)
        if '+CLCK: 0' not in value:
            all_logger.info("PF锁解锁后检查异常")
            raise WindowsEsimError("PF锁解锁后检查异常")

    def check_eid(self):
        """
        检查EID号
        :return: 返回EID号
        """
        eid = self.at_handle.send_at('AT+QSIMCFG="EID"')
        try:
            eid_number = re.findall(r'\+QSIMCFG: "eid",(\d+)', eid)[0]
        except IndexError as e:
            all_logger.info(e)
            all_logger.info('AT指令未查询到eid号')
            raise WindowsEsimError('AT指令未查询到eid号')
        self.pageMobileBroadband.esim_page_down()
        check_element = [{'title': '设置', 'control_type': "Window"},
                         {'title': eid_number, 'class_name': 'TextBlock'}]
        if not self.pageMobileBroadband.find_element(check_element).exists():
            all_logger.info('AT查询EID号与界面显示不一致')
            self.pageMobileBroadband.esim_page_up()
            raise WindowsEsimError('AT查询EID号与界面显示不一致')
        else:
            self.pageMobileBroadband.find_element(check_element).print_control_identifiers()
            all_logger.info('AT指令EID号查询与界面显示一致')
            self.pageMobileBroadband.esim_page_up()

    def check_qccid(self, iccid, is_ready=True):
        """
        检查qccid号
        :param iccid: 预期的iccid号
        :param is_ready: profile文件是否应用情况下检测
        :return: 返回ICCID号
        """
        qccid_value = ''
        if is_ready:
            for i in range(10):
                qccid_value = self.at_handle.send_at('AT+QCCID', 5)
                if re.findall(r'ICCID: (\d+)', qccid_value):
                    break
                time.sleep(3)
            try:
                qccid_num = re.findall(r'ICCID: (\d+)', qccid_value)[0]
            except IndexError as e:
                all_logger.info(e)
                all_logger.info('未检测到qccid号')
                raise WindowsEsimError('未检测到qccid号')
            if qccid_num != iccid:
                raise WindowsEsimError('AT指令查询ICCID号与系统下发不符，系统下发为{}，AT指令查询为{}'.format(self.iccid_A, qccid_num))
            check_element = [{'title': '设置', 'control_type': "Window"},
                             {'title': qccid_num, 'class_name': 'TextBlock'}]
            if not self.pageMobileBroadband.find_element(check_element).exists():
                all_logger.info('AT查询QCCID号与界面显示不一致')
                raise WindowsEsimError('AT查询QCCID号与界面显示不一致')
            else:
                self.pageMobileBroadband.find_element(check_element).print_control_identifiers()
                all_logger.info('AT指令QCCID号查询与界面显示一致')
        else:
            qccid_value = self.at_handle.send_at('AT+QCCID', 5)
            if 'CME ERROR' not in qccid_value:
                all_logger.info('profile文件未激活状态，QCCID返回异常')

    def check_imsi(self, is_ready=True):
        """
        检查IMSI号是否正确
        :param is_ready: profile文件是否应用情况下检测
        :return:
        """
        imsi_number = ''
        for i in range(10):
            imsi_number = self.at_handle.send_at('AT+CIMI', 5)
            if re.findall(r'AT\+CIMI\s+(\d+)\s+OK\s+', imsi_number):
                break
            time.sleep(3)
        if is_ready:
            try:
                re_imsi = ''.join(re.findall(r'AT\+CIMI\s+(\d+)\s+OK\s+', imsi_number))
                all_logger.info('当前IMSI号为:{}'.format(re_imsi))
            except IndexError as e:
                all_logger.info(e)
                all_logger.info('未检测到IMSI号')
                raise WindowsEsimError('未检测到IMSI号')
        else:
            if 'CME ERROR' not in imsi_number:
                all_logger.info('profile文件未激活状态，CIMI返回异常')
                raise WindowsEsimError('profile文件未激活状态，CIMI返回异常')

    def check_profile_exist(self, is_activate=False):
        """
        检查是否存在profile文件，如果没有就先添加，做测试前准备工作
        :param is_activate: 是否需要激活
        :return:
        """
        if not self.pageMobileBroadband.element_esim_option.exists():
            raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
        self.pageMobileBroadband.click_manage_esim()
        if not self.pageMobileBroadband.check_profile_exist.exists():   # 先检测是否存在profile文件，如果没有先添加
            try:
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)  # 可能会一次添加失败，提示服务器问题，重新再添加一次
            except Exception:   # noqa
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)
        if is_activate:
            if self.pageMobileBroadband.check_profile_active_exist.exists():    # 如果已存在激活文件，无需激活
                all_logger.info('已存在激活Profile文件，无需激活')
                return
            self.pageMobileBroadband.click_esim_profile()
            self.pageMobileBroadband.use_esim_profile()

    def repeat_activate(self):
        """
        重复激活去激活profile文件
        :return:
        """
        self.pageMobileBroadband.click_esim_profile()
        self.pageMobileBroadband.stop_esim_profile()    # 首先去激活，保证初始状态
        checkurc1, checkurc2, checkurc3, checkurc4, checkurc5 = CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port)
        checkurc_list = [checkurc1, checkurc2, checkurc3, checkurc4, checkurc5]
        for i in checkurc_list:
            i.setDaemon(True)
            i.start()
            self.pageMobileBroadband.use_esim_profile()
            i.join()
            if i.error_msg:
                raise WindowsEsimError(i.error_msg)
            self.at_handle.check_network()
            self.pageMobileBroadband.stop_esim_profile()

    def cfun_reset(self):
        """
        进行cfun重启
        :return:
        """
        time.sleep(2)
        self.at_handle.send_at('AT+CFUN=1,1', 15)

    def reset_activate_profile(self):
        """
        激活Profile_A时重启模块
        :return:
        """
        active_reset = Thread(target=self.at_handle.cfun1_1)
        active_reset.start()
        self.pageMobileBroadband.use_esim_profile('Profile_A', False)
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        time.sleep(15)  # 等待一会再检查profile文件
        if not self.pageMobileBroadband.check_profilea_active_exist.exists():
            all_logger.info('重启前激活Profile_A文件，重启后未检测到')
            raise WindowsEsimError('重启前激活Profile_A文件，重启后未检测到')
        if self.pageMobileBroadband.check_profilec_active_exist.exists():
            all_logger.info('重启前激活Profile_A文件，重启后Profile_C文件仍处于激活状态')
            raise WindowsEsimError('重启前激活Profile_A文件，重启后Profile_C文件仍处于激活状态')

    def repeat_reset_profile(self):
        """
        激活及去激活profile前重启模块
        :return:
        """
        for i in range(5):
            active_reset = Thread(target=self.at_handle.cfun1_1)
            active_reset.start()
            self.pageMobileBroadband.use_esim_profile()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(10)  # 等待一会再检查profile文件
            self.pageMobileBroadband.click_esim_profile()
            self.pageMobileBroadband.use_esim_profile()
            self.at_handle.check_network()
            dis_active = Thread(target=self.at_handle.cfun1_1)
            dis_active.start()
            self.pageMobileBroadband.stop_esim_profile()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(10)  # 等待一会再检查profile文件
            self.pageMobileBroadband.click_esim_profile()
            self.pageMobileBroadband.use_esim_profile()
            time.sleep(5)
            self.at_handle.check_network()
            self.pageMobileBroadband.stop_esim_profile()

    def repeat_delete_profile(self):
        """
        重复删除添加profile
        :return:
        """
        checkurc1, checkurc2, checkurc3, checkurc4, checkurc5 = CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port), CheckUrc(self.at_port)
        checkurc_list = [checkurc1, checkurc2, checkurc3, checkurc4, checkurc5]
        for i in checkurc_list:
            i.setDaemon(True)
            self.pageMobileBroadband.delete_esim_profile()
            time.sleep(1)
            try:
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)  # 可能会一次添加失败，提示服务器问题，重新再添加一次
            except Exception:   # noqa
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)
            time.sleep(1)
            self.pageMobileBroadband.click_esim_profile()
            i.start()
            self.pageMobileBroadband.use_esim_profile()
            i.join()
            time.sleep(5)
            self.at_handle.check_network()

    def check_inistat(self):
        """
        发送AT+QINISTAT指令检查返回值
        :return:
        """
        inistat_value = self.at_handle.send_at('AT+QINISTAT', 10)
        if ''.join(re.findall(r'\+QINISTAT:.*(\d)', inistat_value)) != '7':
            raise WindowsEsimError('AT+QINISTAT指令返回值不为7，为{}'.format(''.join(re.findall(r'\+QINISTAT:.*(\d)', inistat_value))))

    def check_qinistat_value(self):
        """
        激活profile后上报URC同时发AT+QINISTAT指令查询进度
        :return:
        """
        check_urc = CheckUrc(self.at_port)
        check_urc.setDaemon(True)
        before_cpin_value = self.at_handle.send_at('AT+QINISTAT', 10)
        if ''.join(re.findall(r'\+QINISTAT:.*(\d)', before_cpin_value)) != '0':
            raise WindowsEsimError('上报CPIN Ready前查询AT+QINISTAT返回值不为0')
        check_urc.start()
        self.pageMobileBroadband.use_esim_profile()
        check_urc.join()
        after_pbdone_value = self.at_handle.send_at('AT+QINISTAT', 10)
        if ''.join(re.findall(r'\+QINISTAT:.*(\d)', after_pbdone_value)) != '7':
            raise WindowsEsimError('上报CPIN Ready前查询AT+QINISTAT返回值不为7')
        if ''.join(re.findall(r'\+QINISTAT:.*(\d)', check_urc.cpin_inistat_value)) != '1':
            raise WindowsEsimError('上报CPIN Ready前查询AT+QINISTAT返回值不为7')
        if ''.join(re.findall(r'\+QINISTAT:.*(\d)', check_urc.sms_inistat_value)) != '3':
            raise WindowsEsimError('上报CPIN Ready前查询AT+QINISTAT返回值不为7')

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        try:
            self.page_main.click_network_icon()
        except Exception:   # noqa
            self.page_main.click_network_icon()
        self.page_main.click_esim_network_details()
        disconnect_button = self.page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.page_main.click_esim_disable_auto_connect()
        self.windows_api.press_esc()

    def disable_auto_connect_find_connect_button(self):
        """
        windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            try:
                self.page_main.click_network_icon()
            except Exception:   # noqa
                self.page_main.click_network_icon()
            self.page_main.click_esim_network_details()
            status = self.page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
        else:
            raise WindowsEsimError("未发现连接按钮")

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
        internet_info = os.popen('ipconfig').read()
        all_logger.info(internet_info)
        mobile = re.findall(r'手机网络[\s\S]*', internet_info)
        if 'IPv4 地址' not in ''.join(mobile):
            all_logger.info('未检测到模块拨号后的IP地址')
        info = '未检测到断开连接按钮，' if not connect_info and not auto_connect else '' + '未检测到已经连接信息' if not already_connect_info else ""
        raise WindowsEsimError('未检测到模块拨号后的IP地址' + info)

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
            raise WindowsEsimError("模块进入飞行模式检查失败")
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
            raise WindowsEsimError("模块退出飞行模式检查失败")
        else:
            return True

    def add_profile(self, activate_code, iccid, profile_name):
        """
        添加profile文件
        :param activate_code: profile文件激活码
        :param iccid: iccid号
        :param profile_name: 需要激活的profile名称
        :return:
        """
        try:
            self.pageMobileBroadband.add_esim_profile(activate_code)    # 可能会一次添加失败，提示服务器问题，重新再添加一次
        except Exception: # noqa
            self.pageMobileBroadband.add_esim_profile(activate_code)
        self.pageMobileBroadband.click_esim_profile()
        self.pageMobileBroadband.use_esim_profile()
        self.check_qccid(iccid)
        self.pageMobileBroadband.edit_esim_profile(profile_name, False)

    def check_multiple_profile(self):
        """
        检测是否存在Profile_A，Profile_B,Profile_C文件
        :return:
        """
        if not self.pageMobileBroadband.check_profilea_exist.exists() \
                or not self.pageMobileBroadband.check_profileb_exist.exists() \
                or not self.pageMobileBroadband.check_profilec_exist.exists():
            self.pageMobileBroadband.delete_esim_profile()  # 如果不存在命名的profile文件，直接全部删除后重新添加
            all_logger.info('当前profile文件不符合预期，删除现有重新添加三个profile文件')
            self.add_profile(self.activation_code_A, self.iccid_A, 'Profile_A')
            self.add_profile(self.activation_code_B, self.iccid_B, 'Profile_B')
            self.add_profile(self.activation_code_C, self.iccid_C, 'Profile_C')

    def check_active_profile(self, profile):
        """
        检测当前profile列表中哪个文件处于激活状态
        :param profile: 需要检测的文件
        :return:
        """
        if profile == 'Profile_A':
            if not self.pageMobileBroadband.check_profilea_active_exist.exists():
                all_logger.info('当前profile文件列表中未检测到激活的Profile_A文件')
                raise WindowsEsimError('当前profile文件列表中未检测到激活的Profile_A文件')
        elif profile == 'Profile_C':
            if not self.pageMobileBroadband.check_profilec_active_exist.exists():
                all_logger.info('当前profile文件列表中未检测到激活的Profile_C文件')
                raise WindowsEsimError('当前profile文件列表中未检测到激活的Profile_C文件')

    def check_deactivate_profile(self, profile):
        """
        检测当前profile列表中哪个文件处于未激活状态
        :param profile: 需要检测的文件
        :return:
        """
        if profile == 'Profile_A':
            if self.pageMobileBroadband.check_profilea_active_exist.exists():
                all_logger.info('当前profile文件列表中检测到激活的Profile_A文件')
                raise WindowsEsimError('当前profile文件列表中检测到激活的Profile_A文件')
        elif profile == 'Profile_C':
            if self.pageMobileBroadband.check_profilec_active_exist.exists():
                all_logger.info('当前profile文件列表中检测到激活的Profile_C文件')
                raise WindowsEsimError('当前profile文件列表中检测到激活的Profile_C文件')

    def set_sim_pin(self):
        """
        高级选项界面设置SIM_PIN
        :return:
        """
        send_keys('1234')    # 一般1234密码正确，但也可能为0000或其他
        self.pageMobileBroadband.click_save_sim_pin()
        time.sleep(1)
        for i in range(10):     # 设置完后可能过会才显示是否设置正确
            if self.pageMobileBroadband.check_sim_pin_error.exists():   # 说明1234设置错误，重新输入一次0000
                send_keys('0000')
                self.pageMobileBroadband.click_save_sim_pin()
                time.sleep(1)
                for j in range(10):     # 同样为了防止点击确定后，不及时显示是否设置正确
                    if self.pageMobileBroadband.check_sim_pin_correct.exists():   # 说明0000设置正确
                        all_logger.info('设置SIM_PIN成功')
                        self.pageMobileBroadband.click_save_sim_pin()
                        return '0000'
                    time.sleep(1)
                else:
                    all_logger.info('使用1234及0000设置SIM_PIN均失败，防止锁PUK，不再设置')
                    raise WindowsEsimError('使用1234及0000设置SIM_PIN均失败，防止锁PUK，不再设置')
            elif self.pageMobileBroadband.check_sim_pin_correct.exists():   # 说明1234设置正确
                all_logger.info('设置SIM_PIN成功')
                self.pageMobileBroadband.click_save_sim_pin()
                return '1234'
            time.sleep(1)

    def cfun_1_1(self):
        """
        cfun11重启
        :return:
        """
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        self.windows_api.check_dial_init()   # 检测拨号驱动是否加载

    def unlock_pin_dial(self, pin_passwd):
        """
        解除SC锁后进行拨号
        :param pin_passwd: SC锁密码
        :return:
        """
        try:
            self.page_main.click_network_icon()
        except Exception:   # noqa
            self.page_main.click_network_icon()
        self.page_main.click_esim_network_details()
        self.page_main.click_unlock_sim_pin()
        send_keys(pin_passwd)
        self.page_main.click_sim_pin_ok_without_check()
        self.windows_api.press_esc()
        self.at_handle.check_network()

    def delete_sim_pin(self, pin_passwd):
        """
        删除SIM_PIN
        :param pin_passwd: SC锁密码
        :return:
        """
        self.pageMobileBroadband.click_delete_sim_pin()
        send_keys(pin_passwd)
        self.pageMobileBroadband.click_save_sim_pin()
        if self.pageMobileBroadband.check_delete_pin_success.exists():   # 说明1234设置正确
            all_logger.info('删除SIM_PIN成功')
            self.pageMobileBroadband.click_save_sim_pin()

    def lock_esim_prepare(self):
        """
        ESIM卡上锁相关case准备步骤
        :return:
        """
        try:
            self.disable_auto_connect_and_disconnect()      # 可能点击一次后不出现拨号界面，再点击一次
        except Exception:   # noqa
            self.disable_auto_connect_and_disconnect()
        self.check_profile_exist(True)
        self.pageMobileBroadband.use_esim_profile()
        self.pageMobileBroadband.esim_back()
        self.pageMobileBroadband.click_advanced_operation()     # 点击高级选项进入并划到下面
        if not self.pageMobileBroadband.check_sim_pin_delete.exists():      # 若未上锁，先上锁
            self.pageMobileBroadband.advance_page_down()
            self.pageMobileBroadband.click_set_sim_pin()    # 点击添加SC锁
            pin_passwd = self.set_sim_pin()     # 获取pin密码是1234还是0000
            return pin_passwd

    def check_sim_pin_locked(self):
        """
        检查SIM PIN是否是Locked状态
        :return: None
        """
        sim_pin_status = self.page_main.element_sim_pin_locked_text.exists()
        if not sim_pin_status:
            raise WindowsEsimError("未找到SIM PIN 已锁定Text")
        # pic_status = pic_compare(self.path_to_sim_lock_pic)
        # if not pic_status:
        #     raise WindowsEsimError('SIM 卡锁定图标对比失败')
        connect_info = repr(self.page_main.element_connect_info.wrapper_object())
        if '手机网络' not in connect_info:
            raise WindowsEsimError("未检测到手机网络描述")


class CheckUrc(Thread):
    """
    检测AT口URC上报
    """
    def __init__(self, at_port, is_inistat=False):
        super().__init__()
        self.at_port = at_port
        self.at_handle = ATHandle(at_port)
        self.check_urc = ['+CPIN: READY', '+QUSIM: 1', '+QIND: SMS DONE', '+QIND: PB DONE']
        self.error_msg = ''
        self.finish_flag = False
        self.cpin_inistat_value = ''
        self.sms_inistat_value = ''
        self.is_inistat = is_inistat

    def run(self):
        _at_port = serial.Serial(self.at_port, baudrate=115200, timeout=0)
        try:
            return_value_cache = ''
            start_time = time.time()
            while True:
                return_value = self.at_handle.readline(_at_port)
                if return_value != '':
                    return_value_cache += return_value
                if self.check_urc[-1] in return_value_cache:
                    all_logger.info('已检测到{}上报'.format(self.check_urc[-1]))
                    break
                if self.is_inistat:
                    if '+CPIN: READY' in return_value:
                        self.cpin_inistat_value = self.at_handle.send_at('AT+QINISTAT', 10)
                    elif '+QIND: SMS DONE' in return_value:
                        self.sms_inistat_value = self.at_handle.send_at('AT+QINISTAT', 10)
                if time.time() - start_time > 20:
                    all_logger.info('20S内未检测到{}上报'.format(self.check_urc[-1]))
                    raise WindowsEsimError('20S内未检测到{}上报'.format(self.check_urc[-1]))
            all_logger.info('AT口检测到上报URC为:\r\n{}'.format(return_value_cache.strip().replace('\r\n', '  ')))
            for i in self.check_urc:
                if i not in return_value_cache:
                    self.error_msg += 'AT口未检测到{}上报'.format(i)
                    raise WindowsEsimError(self.error_msg)
            else:
                all_logger.info('AT口URC检测正常'.format())
        except Exception as e:
            self.error_msg += str(e)
        finally:
            _at_port.close()
