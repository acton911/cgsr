from ..operate.base import BaseOperate
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial
import sys
import time


# ToolBar：状态栏网络图标
toolbar_network_icon = [{"class_name": "Shell_TrayWnd"},
                        {'class_name': 'ToolbarWindow32', 'control_type': "ToolBar"},
                        {'auto_id': "{7820AE74-23E3-4229-82C1-E41CB67D5B9C}"}]

# Pane：点击网络图标后弹窗
toolbar_network_pane = [{"title": "网络连接", "control_type": "Window"},
                        {"auto_id": "MainScrollViewer", "control_type": "Pane"}]

# ListItem：点击网络图标后展示的元素
mobile_broadband_item_id = "SystemSettings_MobileBroadband_Connections_ListView" if \
    sys.getwindowsversion().build < 19041 else "MbbInterfaceList"
mobile_broadband_item = [{"title": "网络连接", "control_type": "Window"},
                         {"auto_id": mobile_broadband_item_id, 'control_type': "List"},
                         {'control_type': "ListItem"}]

# CheckBox：自动连接
mobile_broadband_item_check = [{"title": "网络连接", "control_type": "Window"},
                               {'class_name': 'CheckBox', 'auto_id': "autoConnectCheckBox"}]

# EsimCheckBox：自动连接(ESIM拨号时auto_id为paidCellAutoConnectCheckBox)
esim_mobile_broadband_item_check = [{"title": "网络连接", "control_type": "Window"},
                                    {'class_name': 'CheckBox', 'auto_id': "paidCellAutoConnectCheckBox"}]

# Button：解锁sim卡按钮
sim_pin_unlock_button_title = "解锁 SIM 卡" if \
    sys.getwindowsversion().build < 19041 else "连接"
sim_pin_unlock_button = [{"title": "网络连接", "control_type": "Window"},
                         {'title': sim_pin_unlock_button_title, "control_type": "Button"}]

# PasswordBox：SIM PIN的输入Box
sim_pin_input_box = [{"title": "网络连接", "control_type": "Window"},
                     {'class_name': "PasswordBox", 'auto_id': "MobileBroadbandPinPasswordBox"}]

# Button：输入SIM卡PIN码后下一步的按钮
sim_pin_ok_button = [{"title": "网络连接", "control_type": "Window"},
                     {'class_name': "Button", 'auto_id': "NextButton"}]

# Button：输入sim pin时候的取消按钮
sim_pin_cancel_button = [{"title": "网络连接", "control_type": "Window"},
                         {'class_name': "Button", "title": "取消"}]

# Button：MBIM连接按钮
mbim_connect_button = [{"title": "网络连接", "control_type": "Window"},
                       {'class_name': "Button", "title": "连接"}]

# Button：MBIM断开连接按钮
mbim_disconnect_button = [{"title": "网络连接", "control_type": "Window"},
                          {'class_name': "Button", "title": "断开连接"}]

# Text：MBIM已连接字样
mbim_already_connect = [{"title": "网络连接", "control_type": "Window"},
                        {'title': "已连接",
                         'auto_id': "SystemSettings_Connections_MediaItem_MobileBroadband_DescriptionTextBlock"}]

# Text：MBIM已断开连接字样
mbim_already_disconnect = [{"title": "网络连接", "control_type": "Window"},
                           {'title': "已断开连接",
                           'auto_id': "SystemSettings_Connections_MediaItem_MobileBroadband_DescriptionTextBlock"}]

# Text：SIM PIN 已锁定
sim_pin_locked = [{"title": "网络连接", "control_type": "Window"},
                  {'title': "已锁定",
                   'auto_id': "SystemSettings_Connections_MediaItem_MobileBroadband_DescriptionTextBlock",
                   'control_type': "Text"}]

# Text：获取连接字符串
connect_status = [{"title": "网络连接", "control_type": "Window"},
                  {"control_type": 'ListItem'}]

# Button：飞行模式按钮
airplane_mode_button = [{"title": "网络连接", "control_type": "Window"},
                        {'title': "飞行模式", 'auto_id': "Microsoft.QuickAction.AirplaneMode", "control_type": "Button"}]

# Button：手机网络按钮
mobile_network_button = [{"title": "网络连接", "control_type": "Window"},
                         {'title': "手机网络", 'auto_id': "Microsoft.QuickAction.Cellular", "control_type": "Button"}]

# Text：手机网络图标的已关闭文字
mobile_network_already_closed_text = [{"title": "网络连接", "control_type": "Window"},
                                      {'title': "已关闭", "control_type": "Text",
                                       "auto_id": "SystemSettings_Connections_"
                                                  "MediaItem_MobileBroadband_DescriptionTextBlock"}]

# SIM卡的PIN码1234
sim_pin = "1234"

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageMain(BaseOperate):
    def __init__(self):
        super().__init__()

    """
    点击并输入
    """
    @watchdog("输入SIM卡密码")
    def input_sim_pin(self):
        self.click_input_sth(sim_pin_input_box, sim_pin)

    """
    点击后检查
    """
    @watchdog("点击network icon")
    def click_network_icon(self):
        all_logger.info("wait 10 seconds")
        time.sleep(10)
        for i in range(10):
            try:
                self.click(toolbar_network_icon, toolbar_network_pane)
                return True
            except Exception as e:
                all_logger.error(e)
        else:
            raise NormalError("连续10次点击network icon异常")

    @watchdog("点击网络详情")
    def click_network_details(self):
        self.click(mobile_broadband_item, mobile_broadband_item_check)

    @watchdog("点击ESIM网络详情")
    def click_esim_network_details(self):
        self.click(mobile_broadband_item, esim_mobile_broadband_item_check)

    @watchdog("点击解锁SIM PIN")
    def click_unlock_sim_pin(self):
        self.click(sim_pin_unlock_button, sim_pin_input_box)

    @watchdog("确认SIM PIN")
    def click_sim_pin_ok(self):
        self.click(sim_pin_ok_button, sim_pin_cancel_button, check_disappear=True)

    @watchdog("确认SIM PIN")
    def click_sim_pin_ok_without_check(self):
        self.click_without_check(sim_pin_ok_button)

    @watchdog("点击连接按钮")
    def click_connect_button(self):
        self.click(mbim_connect_button, mbim_connect_button, check_disappear=True)

    @watchdog("点击断开连接按钮")
    def click_disconnect_button(self):
        self.click(mbim_disconnect_button, mbim_disconnect_button, check_disappear=True)

    """
    取消勾选CheckBox
    """
    @watchdog("取消自动拨号")
    def click_disable_auto_connect(self):
        self.click_disable_checkbox(mobile_broadband_item_check)

    """
    取消勾选EsimCheckBox
    """
    @watchdog("取消ESIM自动拨号")
    def click_esim_disable_auto_connect(self):
        self.click_disable_checkbox(esim_mobile_broadband_item_check)

    """
    勾选CheckBox
    """
    @watchdog("允许自动拨号")
    def click_enable_auto_connect(self):
        self.click_enable_checkbox(mobile_broadband_item_check)

    """
    勾选CheckBox
    """
    @watchdog("允许ESIM自动拨号")
    def click_esim_enable_auto_connect(self):
        self.click_enable_checkbox(esim_mobile_broadband_item_check)

    """
    获取元素实例
    """

    @property
    @watchdog("获取断开连接按钮")
    def element_mbim_disconnect_button(self):
        return self.find_element(mbim_disconnect_button)

    @property
    @watchdog("获取已连接Text")
    def element_mbim_already_connect_text(self):
        return self.find_element(mbim_already_connect)

    @property
    @watchdog("获取连接按钮")
    def element_mbim_connect_button(self):
        return self.find_element(mbim_connect_button)

    @property
    @watchdog("获取已断开连接Text")
    def element_mbim_already_disconnect_text(self):
        return self.find_element(mbim_already_disconnect)

    @property
    @watchdog("获取SIM PIN 已锁定Text")
    def element_sim_pin_locked_text(self):
        return self.find_element(sim_pin_locked)

    @property
    @watchdog("获取连接信息")
    def element_connect_info(self):
        return self.find_element(connect_status)

    @property
    @watchdog("获取飞行模式按钮")
    def element_airplane_mode_button(self):
        return self.find_element(airplane_mode_button)

    @property
    @watchdog("获取手机网络按钮")
    def element_mobile_network_button(self):
        return self.find_element(mobile_network_button)

    @property
    @watchdog("获取手机网络已关闭Text")
    def element_mobile_network_already_closed_text(self):
        return self.find_element(mobile_network_already_closed_text)

    @property
    @watchdog("获取网络详情按钮")
    def element_network_details(self):
        return self.find_element(mobile_broadband_item)
