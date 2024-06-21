from utils.cases.linux_lowpower_manager import LinuxLowPowerManager
from utils.exception.exceptions import LinuxLowPowerError
from utils.logger.logging_handles import all_logger
import sys
import time
import traceback


class LinuxLowPower(LinuxLowPowerManager):
    def linux_low_power_1(self):
        """
        QSCLK查询支持的参数范围
        """
        exc_type = None
        exc_value = None
        try:
            self.check_qsclk(0)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def linux_low_power_2(self):
        """
        QSCLK设置开启不保存
        """
        exc_type = None
        exc_value = None
        try:
            self.set_qsclk(0)   # 设置开启不保存
            self.debug_check(True)  # 期望进入慢时钟，debug不通
            self.linux_enter_low_power(False)   # 先将levle值设置为on，退出慢时钟，否则后续cfun11可能无法重启
            self.at_handle.cfun1_1()    # 重启模块后期望未开启慢时钟
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            self.at_handle.check_network()
            time.sleep(5)
            self.check_qsclk(is_save=False)
            self.linux_enter_low_power()    # 重启完成后再开启慢时钟
            self.debug_check(False)  # 期望未进入慢时钟，debug正常输出
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def linux_low_power_3(self):
        """
        QSCLK设置开启且保存，重启模块后，模块能再次进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.debug_check(True)  # 期望进入慢时钟，debug不通
            self.linux_enter_low_power(False)   # 先将level值设置为on，退出慢时钟，否则后续cfun11可能无法重启
            self.at_handle.cfun1_1()    # 重启模块后期望开启慢时钟
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            self.at_handle.check_network()
            self.check_qsclk()
            self.linux_enter_low_power()    # 重启完成后再开启慢时钟
            self.debug_check(True)  # 期望进入慢时钟，debug不通
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def linux_low_power_4(self):
        """
        USB3.0下，CFUN为1进入USB慢时钟功能正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.at_handle.check_network()
            if self.rg_flag:    # RM的模块不受DTR引脚影响
                self.gpio.set_dtr_high_level()    # 拉高DTR
            self.debug_check(True)
            if self.rg_flag:   # RM版本DTR电平状态对于慢时钟无影响
                self.gpio.set_dtr_low_level()
                time.sleep(5)  # 等待一段时间退出慢时钟
                self.debug_check(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if self.rg_flag:
                self.gpio.set_dtr_high_level()  # 拉高DTR
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_5(self, mode=0):
        """
        CFUN为0进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_cfun(mode)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_6(self):
        """
        CFUN为4进入慢时钟
        :return:
        """
        self.linux_low_power_5(4)

    def linux_low_power_7(self):
        """
        CFUN为1进入慢时钟
        :return:
        """
        self.linux_low_power_5(1)

    def linux_low_power_8(self):
        """
        模块进入睡眠后,MBIM/QMI_WWAN数据连接唤醒
        """
        exc_type = None
        exc_value = None
        try:
            self.mbim_dial()
            self.dial()
            time.sleep(10)
            self.debug_check(True, 20)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_9(self):
        """
        模块进入睡眠后，来电阶段性唤醒，不接听直到超时挂断
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.hang_up_after_system_dial(20)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_10(self):
        """
        模块进入睡眠后，来短信唤醒
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.send_msg()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_11(self):
        """
        USB口发送AT命令唤醒模块
        """
        exc_type = None
        exc_value = None
        try:
            for i in range(3):
                self.debug_check(is_low_power=False, is_at=True)
            time.sleep(5)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_12(self):
        """
        打开GNSS会话后(AT+QGPS=1),输出NMEA语句，模块不能进入慢时钟
        """
        exc_type = None
        exc_value = None
        try:
            self.set_gnss()
            self.listen_nema()
            self.debug_check(False)
            self.close_gnss()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_gnss()
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_13(self):
        """
        数传过程中不能进入慢时钟
        """
        exc_type = None
        exc_value = None
        try:
            self.mbim_dial()
            self.dial()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_15(self):
        """
        移动NSA模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('LTE:NR5G')
            self.set_nr5g_mode(1)
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('移动固定NSA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_nr5g_mode(0)
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_16(self):
        """
        移动固定5G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('NR5G')
            self.set_nr5g_mode(0)
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('移动固定SA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_17(self):
        """
        移动5G固定4G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('LTE')
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('移动固定LTE找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_18(self):
        """
        联通NSA模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('LTE:NR5G')
            self.set_nr5g_mode(1)
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('联通固定NSA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_nr5g_mode(0)
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_19(self):
        """
        联通固定5G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('NR5G')
            self.set_nr5g_mode(0)
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('联通固定SA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_20(self):
        """
        联通5G固定4G模式下可正常进入慢时钟
        :return:
        """
        time.sleep(60)
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('LTE')
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('联通固定LTE找网失败')
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_21(self):
        """
        联通5G固定3G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('WCDMA')
            if not self.at_handle.check_network():
                raise LinuxLowPowerError('联通固定3G找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_22(self):
        """
        开启SIM卡热插拔后，换卡能重新进入慢时钟
        """
        exc_type = None
        exc_value = None
        try:
            self.sim_det(True)  # 首先开启热拔插功能
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.check_simcard(False)
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handle.readline_keyword('PB DONE', timout=60)
            self.linux_enter_low_power()
            self.check_simcard(True)
            self.at_handle.check_network()
            self.debug_check(True, times=20)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            self.sim_det(False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_23(self):
        """
        设置QSCLK为0模块不能进入睡眠
        """
        exc_type = None
        exc_value = None
        try:
            self.close_lowpower()
            self.debug_check(False)
            self.open_lowpower()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_24(self):
        """
        关autosuspend模块不能进入慢时钟
        """
        exc_type = None
        exc_value = None
        try:
            self.debug_check(True)
            self.linux_enter_low_power(False)
            time.sleep(1)
            self.debug_check(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_low_power_25(self):
        """
        同时关闭USB Auto Suspend和USB Remote Wakeup功能，模块无法进入慢时钟（标准项目测试）
        """
        exc_type = None
        exc_value = None
        try:
            self.debug_check(True)
            self.linux_enter_low_power(False, False)
            time.sleep(1)
            self.debug_check(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.set_netmode('AUTO')
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    params_dict = {
        "at_port": '/dev/ttyUSBAT',
        "dm_port": '/dev/ttyUSBDM',
        "uart_port": '/dev/ttyUSB4',
        "nema_port": '/dev/ttyUSB1',
        "debug_port": '/dev/ttyUSB4',
        "phone_number": 13275863160,
    }

    test = LinuxLowPower(**params_dict)
    test.linux_low_power_1()
    test.linux_low_power_2()
    test.linux_low_power_3()
    test.linux_low_power_4()
    test.linux_low_power_5()
    test.linux_low_power_6()
    test.linux_low_power_7()
    test.linux_low_power_8()
    test.linux_low_power_9()
    test.linux_low_power_10()
    test.linux_low_power_11()
    test.linux_low_power_12()
    test.linux_low_power_13()
    test.linux_low_power_15()
    test.linux_low_power_16()
    test.linux_low_power_17()
    test.linux_low_power_18()
    test.linux_low_power_19()
    test.linux_low_power_20()
    test.linux_low_power_21()
    test.linux_low_power_22()
    test.linux_low_power_23()
    test.linux_low_power_24()
