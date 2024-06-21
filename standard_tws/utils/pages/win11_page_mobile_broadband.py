from functools import partial
from ..logger.logging_handles import all_logger
from ..functions.decorators import watchdog
from ..operate.base import BaseOperate
from ..exception.exceptions import NormalError
from pywinauto.keyboard import send_keys
import win32gui
import time
import os
import win32api

# ***************win11已兼容*******************
# Button：移动运营商设置
oprate_setting = [{'title': '设置', 'control_type': "Window"},
                  {'title': "移动运营商设置", 'auto_id': "AdvancedOptionsButton"}]

sim_slot = [{'title': '设置', 'control_type': "Window"},
            {'title': '将此 SIM 卡用于手机网络数据', 'class_name': "TextBlock"}]

# ***************win11已兼容*******************
# TextBlock 运营商设置 使用 SIM 卡的 PIN 码
sim_pin_button_win11 = [{'title': '设置', 'control_type': "Window"},
                         {'title': "使用 SIM 卡的 PIN 码", "control_type": "Group"}]

# TextBlock：手机网络页面文本
mobile_net_data = [{'title': '设置', 'control_type': "Window"},
                   {'title': "连接设置", 'class_name': "TextBlock"}]

# TextBlock：手机网络页面文本
more_mobile_net_data = [{'title': '设置', 'control_type': "Window"},
                        {'title': "更多手机网络设置", 'class_name': "TextBlock"}]

# TextBlock 高级选项的展示框
advanced_option_inner = [{'title': '设置', 'control_type': "Window"},
                         {"class_name": "TextBlock", "auto_id": "pageTitle"}]

# Button：复制SIM卡属性
button_copy_attributes = [{'title': '设置', 'control_type': "Window"},
                          {'class_name': 'Button',
                           'auto_id': 'SystemSettings_Connections_MobileBroadband_AdapterProperty_CopyButton'}]

# ***************win11已兼容*******************
# 属性
attributes = [{'title': '设置', 'control_type': "Window"},
              {'title': '属性',
               'class_name': 'NamedContainerAutomationPeer'}]

# Button：使用SIM卡的PIN码
sim_pin_button = [{'title': '设置', 'control_type': "Window"},
                  {'class_name': "Button", 'auto_id': "SystemSettings_Connections_MobileBroadband_EnableSimPin1_Button"}]

# ***************win11已兼容*******************
# 连接按钮：设置SIM PIN时候的密码
sim_pin_connect_button = [{'title': '设置', 'control_type': "Window"},
                          {'title': "连接", "auto_id": "MbbConnectButton"}]

# ***************win11已兼容*******************
# PasswordBox：设置SIM PIN时候的密码
sim_pin_button_check_main = [{'title': '设置', 'control_type': "Window"},
                             {'class_name': "PasswordBox", "auto_id": "MobileBroadbandPinPasswordBox"}]

# ***************win11已兼容*******************
# PasswordBox：设置SIM PIN时候的密码
sim_pin_button_check = [{'title': '设置', 'control_type': "Window"},
                        {'class_name': "PasswordBox",
                         "auto_id": "SystemSettings_Connections_MobileBroadband_EnableSimPin1_EnterPINPasswordBox"}]

# Button：输入SIM卡PIN码后下一步的按钮
sim_pin_ok_button = [{"title": "设置", "control_type": "Window"},
                     {'class_name': "Button", 'auto_id': "NextButton"}]

# Button：设置SIM PIN完成的确认
sim_pin_save_button = [{'title': '设置', 'control_type': "Window"},
                       {'class_name': "Button", 'title': "确定"}]

# Button：取消设置SIM PIN
sim_pin_cancel_save_button = [{'title': '设置', 'control_type': "Window"},
                              {'class_name': "Button", 'title': "取消"}]

# Button：删除SIM PIN
delete_sim_pin_button = [{'title': '设置', 'control_type': "Window"},
                         {'class_name': 'Button',
                          "auto_id": "SystemSettings_Connections_MobileBroadband_DisableSimPin1_Button"}]

# PasswordBox：删除SIM PIN的输入框
delete_sim_pin_box = [{'title': '设置', 'control_type': "Window"},
                      {'class_name': 'PasswordBox',
                       "auto_id": "SystemSettings_Connections_MobileBroadband_DisableSimPin1_EnterPINPasswordBox"}]

# Button：确认删除SIM PIN
delete_sim_pin_confirm_button = [{'title': '设置', 'control_type': "Window"},
                                 {'class_name': 'Button', 'title': "确定"}]

# Button：取消删除SIM PIN
delete_sim_pin_cancel_button = [{'title': '设置', 'control_type': "Window"},
                                {'class_name': 'Button', 'title': "确定"}]

# Button：添加APN
add_apn_button = [{'title': '设置', 'control_type': "Window"},
                  {"auto_id": "AddAPNButton", "class_name": "Button"}]

# GroupBox：APN设置GroupBox
add_apn_group_box = [{'title': '设置', 'control_type': "Window"},
                     {"auto_id": "pageContent", "control_type": "Group"}]

# Edit：配置文件名称
profile_name_edit = [{'title': '设置', 'control_type': "Window"},
                     {"auto_id": "NetworkConnectionAPNProfileTextBox", "control_type": "Edit"}]

# Edit：接入点名称
access_point_name_edit = [{'title': '设置', 'control_type': "Window"},
                          {"auto_id": "NetworkConnectionAPNTextBox", "control_type": "Edit"}]

# Edit：APN用户名
access_point_username_edit = [{'title': '设置', 'control_type': "Window"},
                              {"auto_id": "NetworkConnectionUserNameTextBox", "control_type": "Edit"}]

# Edit：APN password
access_point_password_edit = [{'title': '设置', 'control_type': "Window"},
                              {"auto_id": "ApnPasswordBox", "control_type": "Edit"}]

# ComboBox：登录信息类型(无、PAP、CHAP、MS-CHAP v2)
access_point_auth_type_box = [{'title': '设置', 'control_type': "Window"},
                              {"auto_id": "NetworkConnectionAuthenticationTypeDropdown", "control_type": "ComboBox"}]

# ComboBox：APN 的IP类型(默认、IPv4、IPv6、IPv4v6)
access_point_ip_type_box = [{'title': '设置', 'control_type': "Window"},
                            {"auto_id": "NetworkConnectionIPTypeDropdown", "control_type": "ComboBox"}]

# CheckBox：应用此配置文件
activate_apn_profile_checkbox = [{'title': '设置', 'control_type': "Window"},
                                 {'auto_id': "SystemSettings_Connections_MobileBroadband_APNEditor_CheckBox",
                                  'control_type': "CheckBox"}]

# Button：保存APN
apn_save_button = [{'title': '设置', 'control_type': "Window"},
                   {"auto_id": "APNSaveButton", "class_name": "Button"}]

# 结束APN配置Button
apn_finish_button = [{'title': '设置', 'control_type': "Window"},
                     {"title": "确定", "class_name": "Button"}]

# Group：Internet 接入点
internet_access_point = [{'title': '设置', 'control_type': "Window"},
                         {'title': "Internet 接入点", 'control_type': "Group"}]

# setting window
setting_window_element = [{'title': '设置', 'control_type': "Window"}]

# 手机网络页面翻页参数
page_down_param = {'title': '设置', 'control_type': "Window"}

# Close button
close_button = [{'title': '设置', 'control_type': "Window"},
                {"auto_id": "Close", "control_type": "Button"}]

# SIM卡1
sim_info_1 = [{'title': '设置', 'control_type': "Window"},
              {'title': "SIM 卡 1", 'class_name': "TextBlock"}]

# SIM卡2
sim_info_2 = [{'title': '设置', 'control_type': "Window"},
              {'title': "SIM 卡 2", 'class_name': "TextBlock"}]

# Button：管理 eSIM 卡配置文件
manage_esim = [{'title': '设置', 'control_type': "Window"},
               {'title': "eSIM 配置文件", 'class_name': "TextBlock"}]

# 登录要求文本
esim_manage_text = [{'title': '设置', 'control_type': "Window"},
                    {'title': "登录要求", 'class_name': 'TextBlock'}]

# 删除profile文件
delete_profile = [{'title': '设置', 'control_type': "Window"},
                  {'title': "删除", 'class_name': 'Button'}]

query_delete = [{'title': '设置', 'control_type': "Window"},
                {'title': "是", 'class_name': 'Button'}]

# profile文件
current_profile = [{'title': '设置', 'control_type': "Window"},
                   {'auto_id': 'SystemSettings_Connections_MobileBroadband_ESim_ProfileList_ListView',
                    'control_type': 'List'}, {'control_type': 'Group'}]

# 打印出ESIM配置页面的所有信息,测试用
test_print = [{'title': '设置', 'control_type': "Window"}]

# 添加profile文件按钮
add_profile_button = [{'title': '设置', 'control_type': "Window"},
                      {'auto_id': 'PermanentNavigationView', 'control_type': 'Custom'},
                      {'auto_id': 'pageContent', 'control_type': 'Group'},
                      {'auto_id': 'ItemsControlScrollViewer', 'control_type': 'Pane'},
                      {'title': '添加用户配置',
                       'auto_id': 'SystemSettings_Connections_MobileBroadband_ESim_AddProfile_Button',
                       'control_type': 'Button'}]

# 让我输入移动运营商提供的激活代码按钮
acivate_button = [{'title': '设置', 'control_type': "Window"},
                  {'title': '让我输入移动运营商提供的激活代码', 'class_name': 'RadioButton'}]

# 下一页按钮
next_page_button = [{'title': '设置', 'control_type': "Window"},
                    {'title': '下一页', 'class_name': 'Button'}]

# profile激活代码输入框
profile_activate_text = [{'title': '设置', 'control_type': "Window"},
                         {'class_name': 'TextBox'}]

# 下载配置文件按钮
download_profile_button = [{'title': '设置', 'control_type': "Window"},
                           {'title': '是', 'class_name': 'Button'}]

# 配置文件就绪文本
profile_ready_to_use = [{'title': '设置', 'control_type': "Window"},
                        {'title': '新配置文件已准备就绪', 'class_name': 'TextBlock'}]

# 关闭按钮
profile_close_button = [{'title': '设置', 'control_type': "Window"},
                        {'title': '关闭', 'class_name': 'Button'}]

# 使用按钮
use_profile_button = [{'title': '设置', 'control_type': "Window"},
                      {'title': '使用', 'class_name': 'Button'}]

# 编辑名称按钮
edit_name_button = [{'title': '设置', 'control_type': "Window"},
                    {'title': '编辑名称', 'class_name': 'Button'}]

# 配置文件名称文本框
deploy_name_text = [{'title': '设置', 'control_type': "Window"},
                    {'class_name': 'TextBox'}]

# 保存按钮
save_button = [{'title': '设置', 'control_type': "Window"},
               {'title': '保存', 'auto_id': 'CESimProfileEntrySettingHandler_Button', 'class_name': 'Button'}]

# 停止使用按钮
stop_use_profile_button = [{'title': '设置', 'control_type': "Window"},
                           {'title': '停止使用', 'class_name': 'Button'}]

# ICCID文本
iccid_text = [{'title': '设置', 'control_type': "Window"},
              {'title': 'ICCID', 'class_name': 'TextBlock'}]

# esim激活profile后显示活动
active_list = [{'title': '设置', 'control_type': "Window"},
               {'auto_id': 'SystemSettings_Connections_MobileBroadband_ESim_ProfileList_ListView',
                'control_type': 'List'}, {'control_type': 'Group'},
               {'title': '显示所有设置', 'auto_id': 'EntityItemButton'},
               {'title': '活动', 'control_type': 'Text'}]

# Profile_A 活动
profile_a_activate = [{'title': '设置', 'control_type': "Window"},
                      {'title': 'Profile_A', 'control_type': 'Group'},
                      {"title": "活动", "control_type": "Text"}]

# Profile_B 活动
profile_b_activate = [{'title': '设置', 'control_type': "Window"},
                      {'title': 'Profile_B', 'control_type': 'Group'},
                      {"title": "活动", "control_type": "Text"}]


# Profile_C 活动
profile_c_activate = [{'title': '设置', 'control_type': "Window"},
                      {'title': 'Profile_C', 'control_type': 'Group'},
                      {"title": "活动", "control_type": "Text"}]

# Profile_A文件
profile_a = [{'title': '设置', 'control_type': "Window"},
             {'title_re': 'Profile_A.*', 'control_type': 'Group'}]

# Profile_B文件
profile_b = [{'title': '设置', 'control_type': "Window"},
             {'title_re': 'Profile_B.*', 'control_type': 'Group'}]

# Profile_C文件
profile_c = [{'title': '设置', 'control_type': "Window"},
             {'title_re': 'Profile_C.*', 'control_type': 'Group'}]

# 返回按钮
back_button = [{'title': '设置', 'control_type': "Window"},
               {'title': '返回', 'auto_id': 'NavigationViewBackButton', "control_type": "Button"}]

# 移动运营商设置文本
operator_set_text = [{'title': '设置', 'control_type': "Window"},
                     {'title': '移动运营商设置', 'auto_id': 'AdvancedOptionsButton', "control_type": "Group"}]

# 使用 SIM 卡的 PIN 码按钮
use_sim_pin_button = [{'title': '设置', 'control_type': "Window"},
                      {'title': '使用 SIM 卡的 PIN 码', 'class_name': 'Button'}]

# PIN码输入错误文本框
pin_error_box = [{'title': '设置', 'control_type': "Window"},
                 {'title_re': 'SIM 卡的 PIN 码 不正确.*', 'class_name': 'TextBlock'}]

# PIN码输入正确文本框
pin_correct_box = [{'title': '设置', 'control_type': "Window"},
                   {'title': '已接受该 SIM 卡的 PIN 码。', 'class_name': 'TextBlock'}]

# PIN码删除失败
pin_delete_fail = [{'title': '设置', 'control_type': "Window"},
                   {'title_re': 'SIM 卡的 PIN 码 不正确.*', 'class_name': 'TextBlock'}]

# PIN码删除成功
pin_delete_success = [{'title': '设置', 'control_type': "Window"},
                      {'title_re': '该 SIM 卡的 PIN 码已删除。', 'class_name': 'TextBlock'}]

# 写卡
# Button：Read Card
read_card_option = [
    {'title': 'SIM Personalize tools(Copyright: GreenCard Co.,Ltd Ver 3.1.0)', 'control_type': "Window"},
    {'title': "Read Card", 'class_name': "TButton"}]

# Button：Write Card
write_card_option = [
    {'title': 'SIM Personalize tools(Copyright: GreenCard Co.,Ltd Ver 3.1.0)', 'control_type': "Window"},
    {'title': "Write Card", 'class_name': "TButton"}]

# Button：Write Card
same_with_gsm_option = [
    {'title': 'SIM Personalize tools(Copyright: GreenCard Co.,Ltd Ver 3.1.0)', 'control_type': "Window"},
    {'title': "Same with GSM", 'class_name': "TButton"}]

# Button：读卡后点击OK按钮
ok_option = [{'title': 'Information', 'control_type': "Window"}, {'title': "OK", 'class_name': "TButton"}]

# SIM PIN密码1234
sim_pin = "1234"

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class Win11PageMobileBroadband(BaseOperate):

    def __init__(self):
        super().__init__()

    # ***************win11已兼容*******************
    """
    页面的打开和关闭
    """
    @watchdog("打开手机网络界面")
    def open_mobile_broadband_page(self):
        for i in range(3):
            try:
                os.popen("start ms-settings:network-cellular").read()
                all_logger.info("wait 5 seconds")
                time.sleep(5)
                setting_window = self.uia_app.window(title='设置', control_type="Window")
                setting_window.set_focus()
                hwnd = win32gui.FindWindow(None, '设置')
                win32gui.MoveWindow(hwnd, 400, 1, 800, 880, True)  # 实验室分辨率1400*900，此分辨率是最佳分辨率
                time.sleep(5)  # 如果立刻下一步操作windows可能会出现奇怪的界面
                if not self.element_oprate_setting.exists():
                    all_logger.error("打开手机网络页面异常")
                    self.click(close_button, close_button, check_disappear=True)
                    continue
                return True
            except Exception as e:
                all_logger.error(f"打开手机网络界面异常：{e}")
                continue
        else:
            all_logger.error("打开手机网络页面异常")

    @watchdog("关闭手机网络界面")
    def close_mobile_broadband_page(self):
        time.sleep(1)  # 如果立刻关闭可能有异常
        self.click(close_button, close_button, check_disappear=True)
        # os.popen("taskkill /f /t /im  SystemSettings.exe").read()

    """
    翻页
    """
    @watchdog("翻页")
    def this_page_down(self):
        self.page_down(**page_down_param)

    """
    点击并输入
    """
    @watchdog("设置框输入SIM PIN")
    def input_sim_pin(self):
        self.click_input_sth(sim_pin_button_check, sim_pin)

    # ***************win11已兼容*******************
    @watchdog("解锁框输入SIM PIN")
    def input_unclock_sim_pin(self):
        self.click_input_sth(sim_pin_button_check_main, sim_pin)

    # ***************win11已兼容*******************
    @watchdog("确认SIM PIN")
    def click_sim_pin_ok_without_check(self):
        self.click_without_check(sim_pin_ok_button)

    @watchdog("删除框输入SIM PIN")
    def input_delete_sim_pin(self):
        self.click_input_sth(delete_sim_pin_box, sim_pin)

    """
    点击不检查
    """
    @watchdog("点击属性复制按钮")
    def click_copy_attributes_button(self):
        self.click_without_check(button_copy_attributes)

    # ***************win11已兼容*******************
    @watchdog("点击click_sim_pin_connect_button")
    def click_sim_pin_connect_button(self):
        self.click_without_check(sim_pin_connect_button)

    # """
    # 点击后检查
    # """
    # @watchdog("点击高级选项")
    # def click_advanced_operation(self):
    #     self.click(advanced_option, advanced_option_inner)

    # ***************win11已兼容*******************
    @watchdog("移动运营商设置")
    def click_oprate_setting(self):
        self.click(oprate_setting, attributes)

    @watchdog("点击使用SIM卡的PIN码")
    def click_set_sim_pin(self):
        self.click(sim_pin_button, sim_pin_button_check)

    @watchdog("点击确认按钮")
    def click_save_sim_pin(self):
        self.click_without_check(sim_pin_save_button)

    @watchdog("点击删除SIM PIN")
    def click_delete_sim_pin(self):
        self.click(delete_sim_pin_button, delete_sim_pin_box)

    @watchdog("点击确认删除SIM PIN")
    def click_confirm_delete_sim_pin(self):
        self.click_without_check(delete_sim_pin_confirm_button)

    @watchdog("点击添加APN按钮")
    def click_add_apn_button(self):
        self.click(add_apn_button, add_apn_group_box)

    @watchdog("点击保存APN")
    def click_save_apn_button(self):
        self.click(apn_save_button, apn_finish_button)

    @watchdog("选择使用卡1")
    def choose_simcard_1(self):
        self.click(sim_info_2, sim_info_1)
        self.click(sim_info_1, sim_info_1)

    @watchdog("选择使用卡2")
    def choose_simcard_2(self):
        self.click(sim_info_1, sim_info_2)
        self.click(sim_info_2, sim_info_2)

    @watchdog("检查当前卡槽")
    def check_slot(self):
        """
        检查当前是否是卡槽一，不是的话则为卡槽二
        :return:
        """
        return self.find_element(sim_info_1)

    # ***************win11已兼容*******************
    @property
    @watchdog("移动运营商设置")
    def element_oprate_setting(self):
        return self.find_element(oprate_setting)

    @property
    @watchdog("获取APN配置文件输入框")
    def element_profile_name_edit(self):
        return self.find_element(profile_name_edit)

    @property
    @watchdog("获取APN名称输入框")
    def element_access_point_name_edit(self):
        return self.find_element(access_point_name_edit)

    @property
    @watchdog("获取APN用户名输入框")
    def element_access_point_username_edit(self):
        return self.find_element(access_point_username_edit)

    @property
    @watchdog("获取APN密码输入框")
    def element_access_point_password_edit(self):
        return self.find_element(access_point_password_edit)

    @property
    @watchdog("获取APN认证类型ComboBox")
    def element_access_point_auth_type_combo_box(self):
        return self.find_element(access_point_auth_type_box)

    @property
    @watchdog("获取APN IP类型ComboBox")
    def element_access_point_ip_type_combo_box(self):
        return self.find_element(access_point_ip_type_box)

    @property
    @watchdog("获取应用此配置文件CheckBox")
    def element_activate_apn_profile_checkbox(self):
        return self.find_element(activate_apn_profile_checkbox)

    @property
    @watchdog("获取设置界面")
    def element_setting_page(self):
        return self.find_element(setting_window_element)

    @property
    @watchdog("获取APN Group")
    def element_internet_access_point_group(self):
        return self.find_element(internet_access_point)

    @property
    @watchdog("获取高级选项按钮")
    def element_advanced_option(self):
        return self.find_element(mobile_net_data)

    @property
    @watchdog("获取管理esim按钮")
    def element_esim_option(self):
        return self.find_element(manage_esim)

    @property
    @watchdog("查看当前是否存在切换SIM卡选项")
    def check_change_slot_exist(self):
        return self.find_element(sim_slot)

    @property
    @watchdog("查看当前是否存在profile文件")
    def check_profile_exist(self):
        return self.find_element(current_profile)

    @property
    @watchdog("查看当前是否存在profileA文件")
    def check_profilea_exist(self):
        return self.find_element(profile_a)

    @property
    @watchdog("查看当前是否存在profileB文件")
    def check_profileb_exist(self):
        return self.find_element(profile_b)

    @property
    @watchdog("查看当前是否存在profileC文件")
    def check_profilec_exist(self):
        return self.find_element(profile_c)

    @property
    @watchdog("查看当前是否存在profile 活动文件")
    def check_profile_active_exist(self):
        return self.find_element(active_list)

    @property
    @watchdog("查看当前是否存在profileA 活动文件")
    def check_profilea_active_exist(self):
        return self.find_element(profile_a_activate)

    @property
    @watchdog("查看当前是否存在profileC 活动文件")
    def check_profilec_active_exist(self):
        return self.find_element(profile_c_activate)

    @watchdog("点击管理esim卡配置文件查看profile列表")
    def click_manage_esim(self):
        self.find_element(manage_esim).print_control_identifiers()
        self.click_without_check(manage_esim)
        if self.find_element(current_profile).exists():
            all_logger.info('检测到profile文件')
            return True
        else:
            all_logger.info('未发现profile文件')

    @watchdog("点击profile文件")
    def click_esim_profile(self):
        self.click_without_check(current_profile)

    @watchdog("点击Profile_A文件")
    def click_esim_profile_a(self):
        self.click_without_check(profile_a)

    @watchdog("点击Profile_B文件")
    def click_esim_profile_b(self):
        self.click_without_check(profile_b)

    @watchdog("点击Profile_C文件")
    def click_esim_profile_c(self):
        self.click_without_check(profile_c)

    @watchdog("删除esim卡profile配置文件")
    def delete_esim_profile(self):
        while True:
            if self.find_element(current_profile).exists():
                all_logger.info('存在有profile文件，进行删除')
                all_logger.info('点击profile文件')
                self.click(current_profile, delete_profile)
                all_logger.info('点击删除按钮')
                self.click_without_check(delete_profile)
                all_logger.info('点击确认删除')
                try:
                    self.click(query_delete, delete_profile, True, 60)
                    all_logger.info('删除成功')
                except Exception:   # noqa
                    all_logger.info('删除失败，重新删除')
                time.sleep(3)
            else:
                all_logger.info('未发现profile文件,无需删除')
                return True

    @watchdog("添加esim卡profile配置文件")
    def add_esim_profile(self, activation_code):
        self.click(add_profile_button, acivate_button, timeout=30)
        self.click_without_check(acivate_button)
        self.click(next_page_button, profile_activate_text, timeout=30)
        self.click_without_check(profile_activate_text)
        if not win32api.GetKeyState(20):    # 先检测当前是大写还是小写，小写的话先切换到大写，防止输入变为中文输入
            send_keys('{CAPSLOCK}')
        send_keys('{}'.format(activation_code))
        try:
            self.click(next_page_button, download_profile_button, timeout=90)
            self.click(download_profile_button, profile_ready_to_use, timeout=90)
            time.sleep(1)
        except Exception:    # noqa
            send_keys('{ESC}')
            time.sleep(1)
            all_logger.info('profile激活失败')
            raise Exception('profile激活失败')
        send_keys('{ESC}')

    @watchdog("使用esim卡profile配置文件，激活profile")
    def use_esim_profile(self, profile_name=None, is_check=True):
        profile_dict = {'Profile_A': 'click_esim_profile_a', 'Profile_B': 'click_esim_profile_b', 'Profile_C': 'click_esim_profile_c'}
        check_active_dict = {'Profile_A': profile_a_activate, 'Profile_B': profile_b_activate, 'Profile_C': profile_c_activate}
        if profile_name:    # 存在多个文件，激活指定profile文件
            exec('self.{}()'.format(profile_dict[profile_name]))
            if self.find_element(use_profile_button).exists():  # 界面上存在使用按钮，需要点击使用激活
                self.click(use_profile_button, query_delete, timeout=30)
                if is_check:    # 某些case无需确认是否激活成功
                    try:
                        self.click(query_delete, check_active_dict[profile_name], timeout=300)
                    except Exception:   # noqa,可能存在点击激活后未正常激活，重复再试一次
                        self.click(use_profile_button, query_delete, timeout=30)
                        self.click(query_delete, check_active_dict[profile_name], timeout=300)
                    all_logger.info('profile文件激活成功')
                    time.sleep(3)  # 刚激活完等待一会再做关于ESIM卡的业务
                    send_keys('{ESC}')
                    return None
                else:
                    self.click_without_check(query_delete)  # 若无需确认，点击后直接返回即可
                    send_keys('{ESC}')
                    return None
            else:
                all_logger.info('当前配置文件已激活，无需激活')
        self.click_esim_profile()
        if self.find_element(use_profile_button).exists():  # 界面上存在使用按钮，需要点击使用激活
            self.click(use_profile_button, query_delete, timeout=30)
            self.click(query_delete, active_list, timeout=300)
            all_logger.info('profile文件激活成功')
            time.sleep(3)   # 刚激活完等待一会再做关于ESIM卡的业务
            send_keys('{ESC}')
        else:
            send_keys('{TAB}')
            send_keys('{ESC}')
            all_logger.info('当前配置文件已激活，无需激活')

    @watchdog("停止使用esim卡profile配置文件，去激活profile")
    def stop_esim_profile(self, profile_name=None):
        profile_dict = {'Profile_A': 'click_esim_profile_a', 'Profile_B': 'click_esim_profile_b', 'Profile_C': 'click_esim_profile_c'}
        if profile_name:    # 存在多个文件，去激活指定文件
            exec('self.{}()'.format(profile_dict[profile_name]))
            if self.find_element(stop_use_profile_button).exists():  # 界面上存在停止使用按钮，需要点击停止使用去激活
                self.click(stop_use_profile_button, query_delete, timeout=30)
                self.click(query_delete, active_list, True, timeout=30)
                all_logger.info('profile文件去激活成功')
                time.sleep(3)  # 刚去激活完等待一会
                send_keys('{ESC}')
            else:
                all_logger.info('当前配置文件已处于去激活状态')
        self.click_esim_profile()
        if self.find_element(stop_use_profile_button).exists():  # 界面上存在停止使用按钮，需要点击停止使用去激活
            self.click(stop_use_profile_button, query_delete, timeout=30)
            self.click(query_delete, active_list, True, timeout=30)
            all_logger.info('profile文件去激活成功')
            time.sleep(3)  # 刚去激活完等待一会
            send_keys('{ESC}')
        else:
            send_keys('{TAB}')
            send_keys('{ESC}')
            all_logger.info('当前配置文件已处于去激活状态')

    @watchdog("编辑profile文件名称")
    def edit_esim_profile(self, name, is_activate=True):
        """
        :param name: 需要配置的名称
        :param is_activate: 修改过名称后激活还是去激活。True：激活；False：去激活
        :return:
        """
        # 确认profile文件名称修改后是否正确
        profile_name_text = [{'title': '设置', 'control_type': "Window"},
                             {'auto_id': 'SystemSettings_Connections_MobileBroadband_ESim_ProfileList_ListView',
                              'control_type': 'List'}, {'control_type': 'Group'},
                             {'title': '显示所有设置', 'auto_id': 'EntityItemButton'},
                             {'title_re': f'{name}.*', 'control_type': 'Text'}]
        self.click(current_profile, edit_name_button, timeout=30)
        self.click(edit_name_button, deploy_name_text, timeout=30)
        self.click_without_check(deploy_name_text)
        send_keys('^a^x')
        if not win32api.GetKeyState(20):    # 先检测当前是大写还是小写，小写的话先切换到大写，防止输入变为中文输入
            send_keys('{CAPSLOCK}')
        send_keys(name)
        send_keys('{TAB}')
        time.sleep(1)
        send_keys('{ENTER}')    # 该按钮有时鼠标点击不生效，采用键盘方式点击
        if not self.find_element(profile_name_text).exists():
            all_logger.info('编辑profile名称后未检查到新名称，编辑未生效')
            raise NormalError('编辑profile名称后未检查到新名称，编辑未生效')
        self.find_element(profile_name_text).print_control_identifiers()
        if is_activate:
            self.use_esim_profile()
        else:
            self.stop_esim_profile()

    @watchdog("手机网络页面向下翻页")
    def mobile_page_down(self):
        try:
            self.click_without_check(mobile_net_data)
        except Exception:   # noqa
            self.click_without_check(more_mobile_net_data)
        send_keys('{PGDN}')

    @watchdog("手机网络页面向上翻页")
    def mobile_page_up(self):
        try:
            self.click_without_check(mobile_net_data)
        except Exception:   # noqa
            self.click_without_check(more_mobile_net_data)
        send_keys('{PGUP}')

    @watchdog("Esim卡配置页面向下翻页")
    def esim_page_down(self):
        self.click_without_check(esim_manage_text)
        send_keys('{PGDN}')

    @watchdog("Esim卡配置页面向上翻页")
    def esim_page_up(self):
        self.click_without_check(esim_manage_text)
        send_keys('{PGUP}')

    @watchdog("Esim卡配置页面返回到上一页")
    def esim_back(self):
        self.click(back_button, mobile_net_data)

    @watchdog("高级选项页向下翻页")
    def advance_page_down(self):
        self.find_element(operator_set_text).print_control_identifiers()
        self.click_without_check(operator_set_text)
        send_keys('{PGDN}')

    '''
    可能存在sim_pin值为0000的情况
    '''
    @watchdog("设置框输入SIM PIN")
    def input_sim_pin_0(self):
        self.click_input_sth(sim_pin_button_check, '0000')

    @property
    @watchdog("查看SIM_PIN密码是否设置错误")
    def check_sim_pin_error(self):
        return self.find_element(pin_error_box)

    @property
    @watchdog("查看SIM_PIN密码是否设置正确")
    def check_sim_pin_correct(self):
        return self.find_element(pin_correct_box)

    @property
    @watchdog("查看是否存在删除PIN码")
    def check_sim_pin_delete(self):
        return self.find_element(delete_sim_pin_button)

    @property
    @watchdog("查看SIM_PIN密码是否删除成功")
    def check_delete_pin_success(self):
        return self.find_element(pin_delete_success)

    @property
    @watchdog("查看SIM_PIN密码是否设置失败")
    def check_delete_pin_fail(self):
        return self.find_element(pin_delete_fail)

    """
    写卡工具页面的打开和关闭
    """
    @watchdog("打开读写卡工具界面")
    def open_sim_wirte_page(self):
        for i in range(3):
            import pywinauto
            global app
            app = pywinauto.Application(backend="uia").start('D:\\Tools\\GRSIMWrite 3.10\\GRSIMWrite.exe', timeout=10)
            setting_window = self.uia_app.window(title='SIM Personalize tools(Copyright: GreenCard Co.,Ltd Ver 3.1.0)',
                                                 control_type="Window")
            setting_window.set_focus()
            hwnd = win32gui.FindWindow(None, 'SIM Personalize tools(Copyright: GreenCard Co.,Ltd Ver 3.1.0)')
            win32gui.MoveWindow(hwnd, 400, 100, 1200, 700, True)  # 实验室分辨率1400*900，此分辨率是最佳分辨率
            time.sleep(1)  # 如果立刻下一步操作windows可能会出现奇怪的界面
            if not self.element_advanced_option.exists():
                all_logger.error("打开读写卡工具界面正常")
                self.click(close_button, close_button, check_disappear=True)
                continue
            return True
        else:
            raise Exception("打开读写卡工具界面异常")

    """
    点击Read Card不检查
    """
    @watchdog("点击Read Card按钮")
    def click_read_card_button(self):
        self.click_without_check(read_card_option)

    # ***************win11已兼容*******************
    @watchdog("点击Read Card按钮")
    def click_read_card_button(self):
        self.click_without_check(sim_pin_button_check)

    """
    点击Wriet Card不检查
    """
    @watchdog("点击Write Card按钮")
    def click_write_card_button(self):
        self.click_without_check(write_card_option)

    """
    点击Same with GSM不检查
    """
    @watchdog("点击Same with GSM按钮")
    def click_same_with_gsm_button(self):
        self.click_without_check(same_with_gsm_option)

    """
    点击弹框OK按钮不检查
    """
    @watchdog("点击OK按钮")
    def click_ok_button(self):
        self.click_without_check(ok_option)

    """
    写入ICCID
    """
    @watchdog("写入ICCID")
    def input_iccid(self, icc_id):
        iccid = app.window()
        iccid['Edit46'].set_text(icc_id)
        time.sleep(1)

    """
    写入IMSI
    """
    @watchdog("写入IMSI")
    def input_imsi(self, im_si):
        im_si_app = app.window()
        im_si_app['Edit33'].set_text(im_si)
        time.sleep(1)
