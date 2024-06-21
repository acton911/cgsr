from utils.functions.decorators import startup_teardown
from utils.cases.linux_cclk_manager import LinuxCCLKManager
from utils.functions.gpio import GPIO
import time
from utils.logger.logging_handles import all_logger
import os

class LinuxCCLK(LinuxCCLKManager):

    @startup_teardown()
    def test_linux_cclk_01_001(self):
        # 执行升级工厂包
        if os.name == "nt":
            self.qfil_with_power_on()
        else:
            self.qfirehose_without_power_on()
        # 检测USB驱动
        self.driver.check_usb_driver()
        time.sleep(2)  # 避免出现开机检测不到CPIN: READY情况
        # 10s内检测+CPIN READY,保证模块AT可以执行且有返回
        self.at_handler.readline_keyword('+CPIN: READY',timout=30)
        # 查看时钟 +CCLK: "80/01/06,13:02:52"
        self.check_init_cclk()
        # QLTS查询 +QLTS: ""
        self.check_init_qlts()
        # 模块驻网检测
        self.at_handler.check_network()
        # 查看驻网后时钟
        self.check_net_cclk()


    def test_linux_cclk_02_001(self):
        # 执行升级工厂包
        if os.name == "nt":
            self.qfil_with_power_on()
        else:
            self.qfirehose_without_power_on()
        # 检测USB驱动
        self.driver.check_usb_driver()
        time.sleep(2)  # 避免出现开机检测不到CPIN: READY情况
        # 检测+CPIN READY,保证模块AT可以执行且有返回
        self.at_handler.readline_keyword('+CPIN: READY',timout=30)
        try:
            # 模块未找到网之前,执行AT+QSIMDET=1,0
            self.set_sim_det()  # 设置为开启低电平检测
            # 控制GPIO,VBAT重启
            gpio = GPIO()
            gpio.set_vbat_high_level()
            time.sleep(3)
            gpio.set_vbat_low_level_and_pwk()
            time.sleep(2)
            gpio.set_sim1_det_high_level()  # 设置SIM卡的电平引脚为高电平
            # 检测USB驱动
            self.driver.check_usb_driver()
            time.sleep(2)
            # 检测+CPIN NOT READY,保证模块AT可以执行且有返回
            self.at_handler.readline_keyword('+CPIN: NOT READY',timout=30)
            # 查看时钟 +CCLK: "80/01/06,13:02:52"
            self.check_init_cclk()
            # QLTS查询 +QLTS: ""
            self.check_init_qlts()
        finally:
            all_logger.info('环境恢复,高电平检测')
            # 恢复高电平检测
            self.set_sim_det_rec()
            # 控制GPIO,VBAT重启
            gpio = GPIO()
            gpio.set_vbat_high_level()
            time.sleep(3)
            gpio.set_vbat_low_level_and_pwk()
            time.sleep(2)
            # 检测USB驱动
            self.driver.check_usb_driver()
            time.sleep(2)
            # 检测+QIND: PB DONE
            self.at_handler.readline_keyword('PB DONE',timout=60)


if __name__ == '__main__':
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM'
    }
    w = LinuxCCLK(**param_dict)
    w.test_linux_cclk_01_001()
    w.test_linux_cclk_02_001()
