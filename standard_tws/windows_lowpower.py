import sys
import time
from utils.functions.windows_api import PINGThread
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import WindowsLowPowerError
from utils.cases.windows_lowpower_manager import WindowsLowPowerManager
import traceback


class WindowsLowPower(WindowsLowPowerManager):
    def windows_low_power_1(self):
        """
        QSCLK查询支持的参数范围
        :return:
        """
        self.check_qsclk(0)

    def windows_low_power_2(self):
        """
        QSCLK设置开启不保存，重启模块后，模块不会进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_qsclk(0)   # 设置开启不保存
            self.debug_check(True)  # 期望进入慢时钟，debug不通
            self.disable_autosuspend()
            self.cfun_reset()
            self.at_handle.check_network()
            time.sleep(5)
            self.check_qsclk(is_save=False)
            self.enable_autosuspend()
            self.debug_check(False)  # 期望未进入慢时钟，debug正常输出
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.enable_autosuspend()
            self.close_lowpower()
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_low_power_3(self):
        """
        QSCLK设置开启且保存，重启模块后，模块能再次进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.debug_check(True)  # 期望进入慢时钟，debug不通
            self.disable_autosuspend()
            self.cfun_reset()
            self.at_handle.check_network()
            self.check_qsclk()
            self.enable_autosuspend()
            self.debug_check(True)  # 期望进入慢时钟，debug不通
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.enable_autosuspend()
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_low_power_4(self):
        """
        USB3.0下，CFUN为1进入USB慢时钟功能正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.at_handle.check_network()
            if self.rg_flag:
                self.gpio.set_dtr_high_level()    # 拉高DTR
            self.at_handle.check_network()
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
            self.disable_low_power_registry()
            self.close_lowpower()
            if self.rg_flag:
                self.gpio.set_dtr_high_level()  # 拉高DTR
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_5(self, mode=0):
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
            self.disable_low_power_registry()
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_6(self):
        """
        CFUN为4进入慢时钟
        :return:
        """
        self.windows_low_power_5(4)

    def windows_low_power_7(self):
        """
        CFUN为1进入慢时钟
        :return:
        """
        self.windows_low_power_5(1)

    def windows_low_power_8(self):
        """
        模块进入睡眠后，MBIM/NDIS数据连接唤醒
        :return:
        """
        ping = None
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.windows_api.check_dial_init()
            ping = PINGThread(times=150, flag=True)
            ping.setDaemon(True)
            self.dial()
            ping.start()
            time.sleep(60)
            self.debug_check(False)
            self.page_main.click_disconnect_button()
            ping.terminate()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            self.page_main.click_disconnect_button()
            ping.terminate()
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_9(self):
        """
        模块进入睡眠后，来电阶段性唤醒，不接听直到超时挂断
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.hang_up_after_system_dial(20)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_10(self):
        """
        模块进入睡眠后，来短信唤醒
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.send_msg()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_11(self):
        """
        模块进入睡眠后，拉低DTR唤醒
        :return:
        """
        exc_type = None
        exc_value = None
        if self.rg_flag:
            try:
                self.gpio.set_dtr_low_level()
                self.debug_check(False)
                self.gpio.set_dtr_high_level()
                time.sleep(5)
                self.debug_check(True)
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                self.disable_low_power_registry()
                self.gpio.set_dtr_high_level()
                self.close_lowpower()
                if exc_type and exc_value:
                    raise exc_type(exc_value)
        else:
            all_logger.info('RM项目不受引脚高低电平控制，无需测试')

    def windows_low_power_12(self):
        """
        USB口发送AT命令唤醒模块
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_qsclk()
            for i in range(3):
                self.debug_check(False, is_at=True)
            time.sleep(10)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_13(self):
        """
        打开GNSS会话后(AT+QGPS=1)，输出NMEA语句，模块不能进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_gnss()
            self.listen_nema()
            time.sleep(60)
            self.debug_check(False)
            self.close_gnss()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.close_gnss()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_14(self):
        """
        数据传输中不能进入慢时钟
        :return:
        """
        ping = None
        exc_type = None
        exc_value = None
        try:
            self.at_handle.check_network()
            self.windows_api.check_dial_init()
            self.dial()
            ping = PINGThread(times=200, flag=True)
            ping.setDaemon(True)
            ping.start()
            time.sleep(60)
            self.debug_check(False)
            self.page_main.click_disconnect_button()
            ping.terminate()
            self.debug_check(True)
        except Exception as e:
            self.page_main.click_disconnect_button()
            ping.terminate()
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_15(self):
        """
        关autosuspend模块不能进入慢时钟(RM项目测试)
        :return:
        """
        exc_type = None
        exc_value = None
        if not self.rg_flag:
            try:
                self.disable_autosuspend()
                self.debug_check(False)
                self.enable_autosuspend()
                self.debug_check(True)
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                self.disable_low_power_registry()
                self.close_lowpower()
                self.enable_autosuspend()
                if exc_type and exc_value:
                    raise exc_type(exc_value)
        else:
            all_logger.info('非RM项目，无需测试')

    def windows_low_power_16(self):
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
                raise WindowsLowPowerError('移动NSA模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_nr5g_mode(0)
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_17(self):
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
                raise WindowsLowPowerError('移动固定SA模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_18(self):
        """
        移动5G固定4G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('LTE')
            if not self.at_handle.check_network():
                raise WindowsLowPowerError('移动固定4G模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_19(self):
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
                raise WindowsLowPowerError('联通NSA模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_nr5g_mode(0)
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_20(self):
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
                raise WindowsLowPowerError('联通固定SA模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_21(self):
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
                raise WindowsLowPowerError('联通固定4G模式下找网失败')
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_22(self):
        """
        联通5G固定3G模式下可正常进入慢时钟
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_netmode('WCDMA')
            if not self.at_handle.check_network():
                raise WindowsLowPowerError('联通固定3G模式下找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.set_netmode('AUTO')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_23(self):
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
            self.check_simcard(True)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            self.sim_det(False)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def windows_low_power_24(self):
        """
        设置QSCLK为0模块不能进入睡眠
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.close_lowpower()
            time.sleep(60)
            self.debug_check(False)
            self.open_lowpower()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.disable_low_power_registry()
            self.close_lowpower()
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    params_dict = {
        "at_port": 'COM6',
        "dm_port": 'COM3',
        "uart_port": 'COM8',
        "nema_port": 'COM4',
        "switch_port": 'COM8',
        "sim_info": [{'sim_operator': 'CMCC', 'slot_number': 1}, {'sim_operator': 'CU-VOLTE', 'slot_number': 2}],
        "debug_port": 'COM28',
        "phone_number": 18714813160,
    }

    test = WindowsLowPower(**params_dict)
    test.windows_low_power_1()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_2()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_3()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_4()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_5()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_6()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_7()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_8()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_9()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_10()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_11()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_12()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_13()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_14()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_15()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_16()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_17()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_18()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_19()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_20()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_21()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_22()
    test = WindowsLowPower(**params_dict)
    test.windows_low_power_23()
