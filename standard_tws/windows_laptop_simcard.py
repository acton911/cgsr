import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_laptop_simcard_manager import WindowsLaptopSimcardManager
from utils.logger.logging_handles import all_logger


class WindowsLaptopSimcard(WindowsLaptopSimcardManager):

    @startup_teardown()
    def test_windows_laptop_simcard_00_000(self):
        self.check_cfun('1')

    @startup_teardown()
    def test_windows_laptop_simcard_13_001(self):
        """
        1.访问右下角Internet图标
        2.点亮飞行模式图标
        3.再次点击飞行模式图标
        """
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        time.sleep(5)
        self.check_cfun('4')
        self.click_disable_airplane_mode_and_check()
        self.windows_api.press_esc()
        self.check_cfun('1')

    @startup_teardown()
    def test_windows_laptop_simcard_13_002(self):
        """
        1.访问右下角Internet图标
        2.点击飞行模式图标
        3.查询网络状态
        4.AT指令切换CFUN为1，并查询网络状态
        5.访问右下角Internet图标
        6.再次点击飞行模式
        """
        try:
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            time.sleep(5)
            self.check_cfun('4')
            self.at_handler.cfun1()
            self.check_cfun('1')
        finally:
            self.click_disable_airplane_mode_and_check()
            self.windows_api.press_esc()

    @startup_teardown(teardown=['enable_mobile_network'])
    def test_windows_laptop_simcard_13_003(self):
        """
        1.MBIM拨号，在窗口可以ping网址
        2.访问右下角Internet图标
        3.点亮飞行模式图标
        4.检查ping状态
        5.再次点击飞行模式图标
        6.再次检查ping状态
        """
        try:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)
            self.page_main.click_network_icon()
            self.page_main.click_network_details()
            self.page_main.click_enable_auto_connect()
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.windows_api.press_esc()
            time.sleep(5)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.check_cfun('4')
            self.click_disable_airplane_mode_and_check()
            self.check_cfun('1')
            time.sleep(5)
            if self.is_win11:
                all_logger.info("当前为win11系统")
                self.page_main.click_network_details()
            self.check_mbim_connect(auto_connect=True)
            self.windows_api.ping_get_connect_status()
            self.windows_api.ping_get_connect_status(ipv6_address=self.ipv6_address, ipv6_flag=True)
            self.windows_api.press_esc()
        finally:
            time.sleep(5)
            self.disable_auto_connect_and_disconnect()
            time.sleep(5)

    @startup_teardown()
    def test_windows_laptop_simcard_13_004(self):
        """
        1.访问右下角Internet图标
        2.点亮飞行模式图标
        3.打开AT口发送CFUN1,1使模块关机重启
        4.查询此时CFUN值
        5.查看飞行模式图标
        6.再次点击飞行模式图标
        """
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        self.check_cfun('4')
        self.at_handler.cfun1_1()
        time.sleep(60)
        self.check_cfun('4')
        self.click_disable_airplane_mode_and_check()
        time.sleep(5)
        self.windows_api.press_esc()
        self.check_cfun('1')
        self.at_handler.check_network()

    @startup_teardown()
    def test_windows_laptop_simcard_13_005(self):
        """
        1.打开AT口，设置CFUN值为0
        2.访问右下角Internet图标
        3.点亮飞行模式图标
        4.再次点击飞行模式图标
        5.查询此时CFUN值
        """
        self.at_handler.cfun0()
        self.check_cfun('0')
        time.sleep(5)
        self.page_main.click_network_icon()
        self.click_enable_airplane_mode_and_check()
        self.click_disable_airplane_mode_and_check()
        time.sleep(5)
        self.windows_api.press_esc()
        self.check_cfun('1')


if __name__ == '__main__':
    param_dict = {
        'at_port': 'COM3',
        'dm_port': 'COM5',
        'mbim_driver_name': 'Quectel RM520NGLAP #12',
        'ipv6_address': "2400:3200::1",
        'phone_number': '18656504506'
    }
    w = WindowsLaptopSimcard(**param_dict)

    # w.test_windows_laptop_simcard_00_000()
    # w.test_windows_laptop_simcard_13_001()  # OK
    # w.test_windows_laptop_simcard_13_002()  # OK
    w.test_windows_laptop_simcard_13_003()  # OK
    w.test_windows_laptop_simcard_13_004()  # OK
    w.test_windows_laptop_simcard_13_005()  # OK
