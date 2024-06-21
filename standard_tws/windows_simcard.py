import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_simcard_manager import WindowsSIMCARDManager
from utils.logger.logging_handles import all_logger
from utils.functions.windows_api import PINGThread


class WindowsSIMCARD(WindowsSIMCARDManager):

    @startup_teardown(teardown=['disable_airplane_mode'])
    def windows_simcard_13_001(self):
        """
        笔电点亮电脑飞行模式图标，进入飞行模式；关闭飞行模式图标，退出飞行模式
        1.访问右下角Internet图标
        2.点亮飞行模式图标
        3.再次点击飞行模式图标
        """
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        self.click_disable_airplane_mode_and_check()
        self.windows_api.press_esc()
        self.at_handler.check_network()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def windows_simcard_13_002(self):
        """
        笔电在飞行模式下切换CFUN=1成功，模块注网成功
        1.访问右下角Internet图标
        2.点击飞行模式图标
        3.查询网络状态
        4.AT指令切换CFUN为1，并查询网络状态
        5.访问右下角Internet图标
        6.再次点击飞行模式
        """
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        self.windows_api.press_esc()
        time.sleep(10)
        self.check_cfun('4')
        self.reset_cfun1()
        self.at_handler.check_network()
        self.page_main.click_network_icon()
        self.click_disable_airplane_mode_and_check()
        self.at_handler.check_network()

    @startup_teardown(teardown=['disable_airplane_mode'])
    def windows_simcard_13_003(self):
        """
        笔电MBIM拨号过程中能进入飞行模式然后退出飞行模式，MBIM拨号可恢复
        1.MBIM拨号，在窗口可以ping网址
        2.访问右下角Internet图标
        3.点亮飞行模式图标
        4.检查ping状态
        5.再次点击飞行模式图标
        6.再次检查ping状态
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.windows_api.ping_get_connect_status()
            self.windows_api.press_esc()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            # self.windows_api.ping_get_connect_status()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.press_esc()

        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['windows_api', 'press_esc'])
    def windows_simcard_13_004(self):
        """
        笔电点亮电脑飞行模式图标进入飞行模式，重启模块后，任然处于飞行模式，查询CFUN为4
        1.访问右下角Internet图标
        2.点亮飞行模式图标
        3.打开AT口发送CFUN1,1使模块关机重启
        4.查询此时CFUN值
        5.查看飞行模式图标
        6.再次点击飞行模式图标
        """
        try:
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            self.windows_api.press_esc()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.windows_api.press_esc()
            self.check_cfun('4')
            # self.at_handler = ATHandle(at_port)
            self.at_handler.cfun1_1()
            time.sleep(30)
            self.check_cfun('4')
            self.page_main.click_network_icon()
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()
            self.at_handler.check_network()
            self.windows_api.ping_get_connect_status()
        finally:
            self.disable_auto_connect_and_disconnect()

    @startup_teardown(startup=['disable_auto_connect_and_disconnect'],
                      teardown=['windows_api', 'press_esc'])
    def windows_simcard_13_005(self):
        """
        笔电在CFUN为0时点击飞行模式图标进入飞行模式后，再点击飞行模式图标，退出飞行模式，检查此时CFUN值应为1
        1.打开AT口，设置CFUN值为0
        2.访问右下角Internet图标
        3.点亮飞行模式图标
        4.再次点击飞行模式图标
        5.查询此时CFUN值
        """
        self.at_handler.cfun0()
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        self.click_disable_airplane_mode_and_check()
        self.windows_api.press_esc()
        self.check_cfun('1')
