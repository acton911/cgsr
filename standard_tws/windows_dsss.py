import os
from utils.cases.windows_dsss_manager import WindowsDSSSManager
from utils.exception.exceptions import WindowsDSSSError
from utils.functions.decorators import startup_teardown
from utils.logger.logging_handles import all_logger
import sys
import traceback


class WindowsDSSS(WindowsDSSSManager):
    def windows_dsss_1(self):
        """
        指令切换到SIM卡1，验证SIM卡1功能
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if not self.check_slot():   # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.check_sim_info(1)
            self.check_module_info(1)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_2(self):
        """
        指令切换到SIM卡2，验证SIM卡2功能
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            if self.check_slot():    # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            self.check_sim_info(2)
            self.check_module_info(1)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_3(self):
        """
        指令设置SIM卡2,断电保存，开机验证SIM卡2功能
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            if self.check_slot():  # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            self.check_restart_slot(2)
            self.at_handle.check_network()
            self.check_sim_info(2)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_4(self):
        """
        指令进行SIM1/SIM2切换5次
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if self.check_slot():  # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            for i in range(5):
                self.change_simcard(1)
                self.change_simcard(2)
            self.at_handle.check_network()
            self.check_sim_info(2)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    @startup_teardown(startup=['pageMobileBroadband', 'open_mobile_broadband_page'],
                      teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_dsss_5(self):
        """
        WIN10界面切换到SIM卡1
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:   # 笔电部分界面操作
                self.check_slot_2_note()
                self.win11_change_slot(1)
                self.at_handle.check_network()
                self.win11_mbim_dial()
                self.query_slot(1)
                self.check_sim_info(1)
            else:
                self.windows_change_slot(1)
                self.at_handle.check_network()
                self.mbim_dial()
                self.check_mbim_connect()
                self.query_slot(1)
                self.check_sim_info(1)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    @startup_teardown(startup=['pageMobileBroadband', 'open_mobile_broadband_page'],
                      teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_dsss_6(self):
        """
        WIN10界面切换到SIM卡2
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:   # 笔电部分界面操作
                self.check_slot_2_note()
                self.win11_change_slot(2)
                self.at_handle.check_network()
                self.query_slot(2)
                self.check_sim_info(2)
            else:
                self.windows_change_slot(2)
                self.at_handle.check_network()
                self.mbim_dial()
                self.check_mbim_connect()
                self.query_slot(2)
                self.check_sim_info(2)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_7(self):
        """
        设置CFUN0/1,在SIM卡切换后依然生效
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.at_handle.send_at('AT+CFUN=0', 15)
            self.at_handle.send_at('AT+QUIMSLOT=2', 10)
            self.check_module_info(0)
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.at_handle.check_network()
            self.change_simcard(1)
            self.check_module_info(1)
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 15)
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_8(self):
        """
        设置CFUN4,在SIM卡切换后依然生效
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if self.check_slot():  # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            self.at_handle.send_at('AT+CFUN=4', 15)
            self.change_simcard(1)
            self.check_module_info(4)
            self.at_handle.send_at('AT+CFUN=1', 15)
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+CFUN=1', 15)
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_9(self):
        """
        SIM1热插拔功能的验证
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.sim_det(True)  # 首先开启热拔插功能
            self.check_sim_det_urc(False, 1)   # 先检测掉卡是否正常
            self.check_sim_det_urc(True, 1)   # 再检测上卡是否正常
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.sim_det(False)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_10(self):
        """
        SIM2热插拔功能的验证
        :return:
        """
        exc_type = None
        exc_value = None
        if os.name == 'nt' and sys.getwindowsversion().build > 20000:
            self.check_slot_2_note()
        try:
            if self.check_slot():  # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            self.sim_det(True)  # 首先开启热拔插功能
            self.check_sim_det_urc(False, 2)   # 先检测掉卡是否正常
            self.check_sim_det_urc(True, 2)   # 再检测上卡是否正常
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if os.name == 'nt' and sys.getwindowsversion().build > 20000:
                self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.sim_det(False)
            if exc_value and exc_type:
                raise exc_type(exc_value)

    def windows_dsss_11(self):
        """
        只有SIM卡槽2插卡，验证SIM卡2功能是否正常
        """
        try:
            self.check_slot_2_note()
            if not self.check_slot():
                self.change_simcard(1)
            self.change_evb_slot_empty()
            self.change_simcard(2)
            self.check_sim_info(2)
            self.at_handle.check_network()      # 笔电卡槽二为ESIM，拨号后无法连接网络，只验证注网
        finally:
            self.change_switcher(1)
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            self.delete_esim_profile()

    def windows_dsss_12(self):
        """
        禁用SIM卡2 功能,确认禁用功能是否正常
        """
        restart_times = self.get_test_times()
        try:
            if not restart_times:   # 如果还未进行过重启
                all_logger.info('设置禁用卡槽二并重启主机')
                self.check_disable_physim_default_value()
                self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,1', 3)    # 开启禁用卡二指令
                self.restart_computer(1)
            if restart_times == 1:
                all_logger.info('已设置禁用卡槽二并重启主机')
                self.check_windows_slot(False)
                self.close_all_ports()
                self.win11_mbim_dial()
                self.fw_upgrade()
                self.check_windows_slot(False)
                self.open_all_ports()
                self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,0', 3)  # 开启启用卡二指令
                self.restart_computer(2)
            if restart_times == 2:      # 此时已经重新启用SIM2功能，可以通过界面切换
                all_logger.info('通过界面切换SIM卡2')
                self.check_slot_2_note()
                self.check_sim_info(2)
                self.at_handle.check_network()  # 笔电卡槽二为ESIM，拨号后无法连接网络，只验证注网
                self.delete_esim_profile()
                self.win11_change_slot(1)
                self.check_sim_info(1)
                self.at_handle.check_network()
                self.win11_mbim_dial()
            if restart_times == 3:      # 代表此时经历过异常处理，并且重启主机，需要再次抛出异常:
                all_logger.info('当前case执行异常，检查log确认')
                raise WindowsDSSSError('当前case执行异常，检查log确认')
        finally:
            self.open_all_ports()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if restart_times != 3:  # 如果一直手机页面有问题，可能会循环执行重启主机
                try:
                    self.check_windows_slot(True)
                except Exception:   # noqa
                    self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,0', 3)  # 开启启用卡二指令
                    self.restart_computer(3)

    def windows_dsss_13(self):
        """
        禁用SIM卡1 功能,确认禁用功能是否正常
        """
        restart_times = self.get_test_times()
        try:
            if not restart_times:   # 如果还未进行过重启
                self.check_slot_2_note()
                all_logger.info('设置禁用卡槽一并重启主机')
                self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",1,0', 3)    # 开启禁用卡二指令
                self.restart_computer(1)
            if restart_times == 1:
                all_logger.info('已设置禁用卡槽一并重启主机')
                self.check_windows_slot(False)
                self.close_all_ports()
                self.fw_upgrade()
                self.check_windows_slot(False)
                self.open_all_ports()
                self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,0', 3)  # 开启启用卡一指令
                self.restart_computer(2)
            if restart_times == 2:
                all_logger.info('已完成第二次重启，重新启用SIM卡一功能')
                self.at_handle.check_network()
                self.win11_mbim_dial()
            if restart_times == 3:  # 代表此时经历过异常处理，并且重启主机，需要再次抛出异常:
                all_logger.info('当前case执行异常，检查log确认')
                raise WindowsDSSSError('当前case执行异常，检查log确认')
        finally:
            self.open_all_ports()
            self.win11_change_slot(2)
            self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)
            if restart_times != 3:  # 如果一直手机页面有问题，可能会循环执行重启主机
                try:
                    self.check_windows_slot(True)
                except Exception:   # noqa
                    self.at_handle.send_at('AT+QSIMCFG="DISABLE_PHYSIM",0,0', 3)  # 开启启用卡一指令
                    self.restart_computer(3)

    def windows11_dsss_1(self):
        """
        [笔电项目]指令切换到SIM卡2，验证SIM卡2功能
        """
        self.check_slot_2_note()    # 首先确保卡槽二正常激活ESIM
        self.at_handle.send_at('AT+QURCCFG="URCPORT","USBMODEM"', 10)
        try:
            self.windows_dsss_2()
        finally:
            self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)

    def windows11_dsss_2(self):
        """
        [笔电项目]指令设置SIM卡2,断电保存，开机验证SIM卡2功能
        """
        self.at_handle.send_at('AT+QURCCFG="URCPORT","USBMODEM"', 10)
        try:
            self.check_slot_2_note()
            if self.check_slot():  # 如果当前是卡槽一，再执行切换卡槽方法
                self.change_simcard(2)
            self.check_restart_slot_win11(2)
            self.at_handle.check_network()
            self.check_sim_info(2)
        finally:
            self.delete_esim_profile()
            if not self.check_slot():  # 如果当前是卡槽二，再执行切换卡槽方法
                self.change_simcard(1)


if __name__ == '__main__':
    param_dict = {'at_port': 'COM8', 'dm_port': 'COM6', "mbim_driver_name": "",
                  "card_info": [{'sim_imsi': '460015867255358', 'sim_operator': 'CU', 'sim_iccid_crsm': '98681081380010087427', 'phonenumber_PDU': '3172853661F0',
                                'sca_number_PDU': '0891683108200105F0', 'phonenumber': '13275863160', 'evb_slot_number': 1, 'switcher': 'COM14',
                                'phonenumber_HEX': '3133323735383633313630', 'sim_iccid': '89860118830001804772',
                                'phonenumber_UCS2': '00310033003200370035003800360033003100360030', 'sca_number': '+8613800210500',
                                'sim_puk': '31169468', 'operator_servicenumber': '10010', 'slot_number': 1},
                               {'sim_imsi': '460015125315669', 'sim_operator': 'CU-noVOLTE', 'sim_iccid_crsm': '98683081415521915475',
                                'phonenumber_PDU': '9151153491F5', 'sca_number_PDU': '0891683110305005F0', 'phonenumber': '19155143195',
                                'evb_slot_number': 1, 'switcher': 'COM14', 'imsi_cdma': '460110934878888',
                                'phonenumber_HEX': '3139313535313433313935', 'sim_iccid': '89860118803447167625',
                                'phonenumber_UCS2': '00310039003100350035003100340033003100390035', 'sca_number': '+8613010305500',
                                'sim_puk': '1234', 'operator_servicenumber': '10000', 'slot_number': 2},
                               {'sim_imsi': '460115471751387', 'sim_operator': 'CT', 'sim_iccid_crsm': '98680052210363091333',
                                'phonenumber_PDU': '5151865726F4', 'sca_number_PDU': '0891683108501505F0', 'phonenumber': '15156875624',
                                'evb_slot_number': 1, 'switcher': 'COM14', 'phonenumber_HEX': '3135313536383735363234',
                                'sim_iccid': '89860320045512519678', 'phonenumber_UCS2': '00310035003100350036003800370035003600320034',
                                'sca_number': '+8613800551500', 'sim_puk': '52711791', 'operator_servicenumber': '10086', 'slot_number': 3},
                               {'sim_imsi': '460015125315669', 'sim_operator': 'CU',
                                'sim_iccid_crsm': '98680052210363091333',
                                'phonenumber_PDU': '5151865726F4', 'sca_number_PDU': '0891683108501505F0',
                                'phonenumber': '15156875624',
                                'evb_slot_number': 1, 'switcher': 'COM14', 'phonenumber_HEX': '3135313536383735363234',
                                'sim_iccid': '89860118803447167625',
                                'phonenumber_UCS2': '00310035003100350036003800370035003600320034',
                                'sca_number': '+8613800551500', 'sim_puk': '52711791',
                                'operator_servicenumber': '10086',
                                'slot_number': 4}],
                  "profile_info": '1$trl.prod.ondemandconnectivity.com$O0JZWPYPVBTB2BI6,8988247000112154019,1$trl.prod.ondemandconnectivity.com$QBLPITRU56PEUQQB,8988247000111652385,1$trl.prod.ondemandconnectivity.com$JTVCF3QG4G8QTPYI,8988247000111735644'}
    dsss = WindowsDSSS(**param_dict)
    # dsss.windows_dsss_1()
    # dsss.windows_dsss_2()
    # dsss.windows_dsss_3()
    # dsss.windows_dsss_4()
    # dsss.windows_dsss_5()
    # dsss.windows_dsss_7()
    # dsss.windows_dsss_8()
    # dsss.windows_dsss_9()
    # dsss.windows_dsss_10()
    # dsss.windows_dsss_11()
    # dsss.windows_dsss_12()
    # dsss.windows_dsss_13()
    # dsss.windows_dsss_14()
    # dsss.windows_dsss_15()
    # dsss.windows_dsss_16()
    # dsss.windows_dsss_17()
    dsss.windows11_dsss_1()
