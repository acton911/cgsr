import sys
from utils.logger.logging_handles import all_logger
from utils.functions.decorators import startup_teardown
from utils.exception.exceptions import WindowsEsimError
from utils.cases.windows11_esim_manager import Windows11EsimManager


class WindowsEsim(Windows11EsimManager):
    def windows_esim_1(self):
        """
        设置当前网卡类型为MBIM
        :return:
        """
        self.at_handle.switch_to_mbim(self.mbim_driver)

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_2(self):
        """
        查看ESIM卡识别正常
        :return:
        """
        self.pageMobileBroadband.mobile_page_down()
        if not self.pageMobileBroadband.element_esim_option.exists():
            raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
        self.pageMobileBroadband.click_manage_esim()

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_3(self):
        """
        删除当前的Profile
        :return:
        """
        self.pageMobileBroadband.open_mobile_broadband_page()
        self.pageMobileBroadband.mobile_page_down()
        if not self.pageMobileBroadband.element_esim_option.exists():
            raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
        self.pageMobileBroadband.click_manage_esim()
        self.pageMobileBroadband.delete_esim_profile()    # 如果检测到存在profile文件再删除

    def windows_esim_4(self, flag=True):
        """
        添加Profile文件并激活，查询基本信息
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.pageMobileBroadband.delete_esim_profile()    # 如果检测到存在profile文件，先删除再添加
            try:
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)  # 可能会一次添加失败，提示服务器问题，重新再添加一次
            except Exception:   # noqa
                all_logger.info('profile激活失败，重新激活一次')
                self.pageMobileBroadband.add_esim_profile(self.activation_code_A)
            self.pageMobileBroadband.use_esim_profile()
            self.check_cpin()
            self.check_qccid(self.iccid_A)
            self.at_handle.check_network()
            self.check_eid()
        finally:
            if flag:
                self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_5(self):
        """
        更新当前Profile的名称后重新激活
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.edit_esim_profile('A')
            self.pageMobileBroadband.edit_esim_profile('B', False)
            self.pageMobileBroadband.edit_esim_profile('1234')
            self.pageMobileBroadband.edit_esim_profile('1234ABCDE', False)
            self.pageMobileBroadband.edit_esim_profile('1234ABCDE' * 3)
            self.at_handle.check_network()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_6(self):
        """
        同一个Profile重复激活去激活正常
        :return:
        """
        try:
            self.check_profile_exist()
            self.repeat_activate()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_7(self):
        """
        激活Profile过程中重启模块确认重启后Profile激活正常,该用例经评审后已被删除，只做保留
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.stop_esim_profile()
            self.repeat_reset_profile()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_8(self):
        """
        确认同一个Profile重复删除再添加正常
        :return:
        """
        try:
            self.check_profile_exist()
            self.repeat_delete_profile()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_9(self):
        """
        激活当前的Profile，查询URC上报及AT+QINISTAT查询模块初始化的进度正常
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.stop_esim_profile()
            self.check_qinistat_value()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_10(self):
        """
        查询当前ESIM的IMSI和CCID号以及EID号
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.use_esim_profile()
            self.check_cpin()
            self.check_imsi()
            self.check_qccid(self.iccid_A)
            self.at_handle.check_network()
            self.check_eid()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_11(self):
        """
        数传功能确认
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.use_esim_profile()
            self.at_handle.check_network()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_12(self):
        """
        去激活当前的Profile并验证模块信息
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.stop_esim_profile()
            self.check_inistat()
            self.check_cpin(False)
            self.check_qccid(self.iccid_A, False)
            self.check_imsi(False)
            self.check_eid()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_13(self):
        """
        激活当前的Profile
        :return:
        """
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.use_esim_profile()
            self.at_handle.check_network()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_14(self):
        """
        MBIM连接界面飞行模式图标功能测试
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.use_esim_profile()
            self.at_handle.check_network()
            self.disable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            self.at_handle.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            try:
                self.windows_api.press_esc()
                self.page_main.click_network_icon()
                self.exit_airplane_mode_confirm()  # 确保退出飞行模式
                self.windows_api.press_esc()
            except Exception:   # noqa
                pass
            finally:
                self.windows_esim_3()  # 如果检测到存在profile文件再删除
                if exc_type and exc_value:
                    raise exc_type(exc_value)

    def windows_esim_15(self):
        """
        MBIM自动连接状态下启用再禁用飞行模式
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.check_profile_exist()
            self.pageMobileBroadband.use_esim_profile()
            self.at_handle.check_network()
            self.enable_auto_connect_and_disconnect()
            self.page_main.click_network_icon()
            self.click_enable_airplane_mode_and_check()
            self.click_disable_airplane_mode_and_check()
            self.page_main.click_esim_network_details()
            self.check_mbim_connect()
            self.windows_api.press_esc()
            self.at_handle.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            try:
                self.disable_auto_connect_and_disconnect()  # 确保取消自动连接
                self.page_main.click_network_icon()
                self.exit_airplane_mode_confirm()  # 确保退出飞行模式
                self.windows_api.press_esc()
            except Exception:    # noqa
                pass
            finally:
                self.windows_esim_3()  # 如果检测到存在profile文件再删除
                if exc_type and exc_value:
                    raise exc_type(exc_value)

    def windows_esim_16(self):
        """
        新增两个Profile，保持至少两个不相同运营商的Profile,记为Profile_B和Profile_C
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.pageMobileBroadband.delete_esim_profile()    # 如果检测到存在profile文件再删除
            self.add_profile(self.activation_code_A, self.iccid_A, 'Profile_A')
            self.add_profile(self.activation_code_B, self.iccid_B, 'Profile_B')
            self.add_profile(self.activation_code_C, self.iccid_C, 'Profile_C')
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_17(self):
        """
        去激活Profile_B， 激活新增的的Profile_C正常
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_B')
            self.pageMobileBroadband.stop_esim_profile('Profile_B')
            self.pageMobileBroadband.use_esim_profile('Profile_C')
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_18(self):
        """
        查询ESIM的IMSI和CCID号以及EID号
        :return:
        """
        try:
            profile_dict = {'Profile_A': 'click_esim_profile_a', 'Profile_B': 'click_esim_profile_b',
                            'Profile_C': 'click_esim_profile_c'}
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.check_cpin()
            self.check_imsi()
            self.check_qccid(self.iccid_C, profile_name=profile_dict['Profile_C'])
            self.check_eid()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_19(self):
        """
        确认Profile_C注网正常以及数传功能正常
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.at_handle.check_network()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_20(self):
        """
        去激活当前激活的Profile_C，激活Profile_A，确认功能正常
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.pageMobileBroadband.stop_esim_profile('Profile_C')
            self.pageMobileBroadband.use_esim_profile('Profile_A')
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_21(self):
        """
        查询ESIM的IMSI和CCID号以及EID号
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.check_cpin()
            self.check_imsi()
            self.check_qccid(self.iccid_A, profile_name='click_esim_profile_a')
            self.check_eid()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_22(self):
        """
        确认Profile_A注网正常以及数传功能正常
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.at_handle.check_network()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_23(self):
        """
        Profile_A激活状态下, 激活Profile_C，确认Profile_C激活正常，Profile_A被去激活,查询ESIM的IMSI和CCID号以及EID号
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.check_deactivate_profile('Profile_A')
            self.check_active_profile('Profile_C')
            self.check_cpin()
            self.check_imsi()
            self.check_qccid(self.iccid_C, profile_name='click_esim_profile_c')
            self.at_handle.check_network()
            self.check_eid()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_24(self):
        """
        Profile_C激活状态下, 激活Profile_A的时候重启模块，确认重启后Profile_A正常激活，Profile_C被去激活
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.reset_activate_profile()
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    def windows_esim_25(self):
        """
        Profile_A激活状态下, 激活Profile_C，确认Profile_A被去激活，Profile_C能正常激活
        :return:
        """
        try:
            self.pageMobileBroadband.mobile_page_down()
            if not self.pageMobileBroadband.element_esim_option.exists():
                raise WindowsEsimError('打开手机网络后未发现管理当前esim卡配置文件按钮')
            self.pageMobileBroadband.click_manage_esim()
            self.check_multiple_profile()
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.check_deactivate_profile('Profile_A')
            self.check_active_profile('Profile_C')
        finally:
            self.windows_esim_3()  # 如果检测到存在profile文件再删除

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_26(self):
        """
        MBIM界面添加SIM PIN功能验证
        :return:
        """
        self.check_profile_exist(True)
        self.pageMobileBroadband.esim_back()
        self.pageMobileBroadband.mobile_page_down()
        self.pageMobileBroadband.advance_page_down()
        self.pageMobileBroadband.click_set_sim_pin()    # 点击添加SC锁
        exc_type = None
        exc_value = None
        pin_passwd = None
        try:
            pin_passwd = self.set_sim_pin()     # 获取pin密码是1234还是0000
            self.cfun_1_1()
            self.unlock_pin_dial(pin_passwd)    # 解锁并验证注网
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.unlock_sc_lock(pin_passwd)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_27(self):
        """
        SIM PIN状态下MBIM图标信号显示及信号值显示
        :return:
        """
        self.check_profile_exist(True)
        self.pageMobileBroadband.use_esim_profile()
        self.pageMobileBroadband.esim_back()
        self.pageMobileBroadband.mobile_page_down()
        self.pageMobileBroadband.advance_page_down()
        self.pageMobileBroadband.click_set_sim_pin()    # 点击添加SC锁
        exc_type = None
        exc_value = None
        pin_passwd = None
        try:
            pin_passwd = self.set_sim_pin()     # 获取pin密码是1234还是0000
            self.cfun_1_1()
            try:
                self.page_main.click_network_icon()
            except Exception:   # noqa
                self.page_main.click_network_icon()
            self.page_main.click_esim_network_details()
            # TODO: 图标比对有问题
            self.check_sim_pin_locked()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.unlock_sc_lock(pin_passwd)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_28(self):
        """
        MBIM界面删除SIM PIN功能验证
        :return:
        """
        self.check_profile_exist(True)
        self.pageMobileBroadband.use_esim_profile()
        self.pageMobileBroadband.esim_back()
        self.pageMobileBroadband.mobile_page_down()
        self.pageMobileBroadband.advance_page_down()
        self.pageMobileBroadband.click_set_sim_pin()    # 点击添加SC锁
        exc_type = None
        exc_value = None
        pin_passwd = None
        try:
            pin_passwd = self.set_sim_pin()     # 获取pin密码是1234还是0000
            self.cfun_1_1()
            self.pageMobileBroadband.esim_back()
            self.pageMobileBroadband.mobile_page_down()
            self.pageMobileBroadband.advance_page_down()
            self.delete_sim_pin(pin_passwd)
            self.cfun_1_1()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.unlock_sc_lock(pin_passwd)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_29(self):
        """
        设置PN锁，并查询设置结果是否正确
        :return:
        """
        self.pageMobileBroadband.mobile_page_down()
        self.pageMobileBroadband.click_manage_esim()
        self.check_multiple_profile()
        self.pageMobileBroadband.use_esim_profile('Profile_A')
        exc_type = None
        exc_value = None
        try:
            self.set_pn_lock()
            # 设置PN锁后重启验证是否正常
            self.cfun_1_1()
            self.check_cpin()
            # 设置PN锁后去激活激活当前profile是否正常
            self.pageMobileBroadband.stop_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.check_cpin()
            # 设置PN锁后去激活激活与当前profile同运营商是否正常
            self.pageMobileBroadband.stop_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_B')
            self.check_cpin()
            # 设置PN锁后去激活激活与当前profile不同运营商是否正常
            self.pageMobileBroadband.stop_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_C')
            self.check_pn_lock()
            self.unlock_pn_lock()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.unlock_pn_lock()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['pageMobileBroadband', 'close_mobile_broadband_page'])
    def windows_esim_30(self):
        """
        设置PF锁相关case
        :return:
        """
        self.pageMobileBroadband.mobile_page_down()
        self.pageMobileBroadband.click_manage_esim()
        self.check_multiple_profile()
        self.pageMobileBroadband.use_esim_profile('Profile_A')
        exc_type = None
        exc_value = None
        try:
            self.set_pf_lock()
            # 设置PF锁后重启验证是否正常
            self.cfun_1_1()
            self.check_cpin()
            # 设置PF锁后去激活激活当前profile是否正常
            self.pageMobileBroadband.stop_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_A')
            self.check_cpin()
            # 设置PF锁后去激活，激活其他profile是否正常
            self.pageMobileBroadband.stop_esim_profile('Profile_A')
            self.pageMobileBroadband.use_esim_profile('Profile_B')
            self.check_pf_lock()
            self.unlock_pf_lock()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.unlock_pf_lock()
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    esim = WindowsEsim('COM8', 'COM5', 'RM520NGLAP',
                       profile_info='1$trl.prod.ondemandconnectivity.com$O0JZWPYPVBTB2BI6,8988247000112154019,'
                                    '1$consumer.rsp.world$4AJCQCD1D92OVVFS,8988247000112275590'
                                    '1$consumer.rsp.world$RX5CNFHHVENBJONP,8988247000112275566,'
                       )
    # esim.windows_esim_1()
    # esim.windows_esim_2()
    # esim.windows_esim_3()
    # esim.windows_esim_4()
    # esim.windows_esim_5()
    # esim.windows_esim_6()
    # esim.windows_esim_8()
    # esim.windows_esim_9()
    # esim.windows_esim_10()
    # esim.windows_esim_11()
    # esim.windows_esim_12()
    # esim.windows_esim_13()
    # esim.windows_esim_14()
    # esim.windows_esim_15()
    esim.windows_esim_16()
    # esim.windows_esim_17()
    # esim.windows_esim_18()
    # esim.windows_esim_19()
    # esim.windows_esim_20()
    # esim.windows_esim_21()
    # esim.windows_esim_22()
    # esim.windows_esim_23()
    # esim.windows_esim_24()
    # esim.windows_esim_25()
