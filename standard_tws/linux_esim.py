import sys
import traceback

from utils.cases.linux_esim_manager import LinuxESIMManager
from utils.logger.logging_handles import all_logger


class LinuxESIM(LinuxESIMManager):
    def linux_esim_1(self):
        """
        Linux系统下添加profile
        """
        self.delete_profile()   # case执行前先删除现有profile文件
        self.add_profile(self.activation_code_A)

    def linux_esim_2(self):
        """
        指令查询
        """
        self.check_order()

    def linux_esim_3(self):
        """
        LPA功能开关,默认值放到ALL-ATC中check，此处关闭LPA功能后直接检测AT指令返回值
        """
        self.close_lpa()
        self.close_lpa_order_check()
        self.open_lpa()
        self.cfun_reset()
        self.check_lpa(True)
        self.close_lpa()
        self.cfun_reset()
        self.check_lpa(False)
        self.check_illegal_order()

    def linux_esim_4(self):
        """
        查询profile文件信息（"profile的数量）
        """
        self.linux_esim_1()     # 首先确定当前只存在一个profile文件，然后再确定数量是否正确
        self.check_profile_num()
        self.check_profile_detail()
        self.check_profile_detail(False)

    def linux_esim_5(self):
        """
        激活/去激活配置文件
        """
        self.linux_esim_1()
        self.check_profile_activate('1', False)
        self.add_profile(self.activation_code_B)
        self.activate_profile('2')     # case初始确保存在两个profile文件,一个已激活状态
        self.activate_profile('1')     # 激活之前未激活的Profile
        self.check_profile_activate('2', False)     # 之前已激活的检查是否去激活
        self.repeat_activate('1', True)
        self.disable_profile('1')
        self.repeat_activate('1', False)

    def linux_esim_6(self):
        """
        更新配置文件的nickname
        """
        self.linux_esim_1()
        self.nickname_profile(nickname='Quectel')
        self.nickname_profile(nickname='Quectel"123', is_correct=False)
        self.nickname_profile(nickname='Quectel"', is_correct=False)
        self.nickname_profile(nickname='Quec"tel', is_correct=False)
        self.nickname_profile(nickname='q' * 63)
        self.nickname_profile(nickname='q' * 64, is_correct=False)

    def linux_esim_7(self):
        """
        配置SM-DP服务器地址
        """
        exc_type = None
        exc_value = None
        try:
            self.linux_esim_1()
            self.check_server_address()
            self.set_server_address("esim.wo.com.cn")
            self.set_server_address("")
            self.set_server_address('aa"a', False)
            self.set_server_address('"aaa', False)
            self.set_server_address('aaa"', False)
            # self.set_server_address("w"*254)
            # self.set_server_address("w"*255, False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.set_server_address("esim.wo.com.cn")
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_esim_8(self):
        """
        删除配置文件
        """
        self.linux_esim_1()
        self.add_profile(self.activation_code_B)
        self.delete_single_profile()

    def linux_esim_9(self):
        """
        关闭LPA
        """
        self.close_lpa()

    def linux_esim_10(self):
        """
        CFUN切换到4，正常识别ESIM卡
        """
        exc_type = None
        exc_value = None
        try:
            self.linux_esim_1()
            self.activate_profile('1')
            self.set_cfun(4)
            self.check_module_info()
            self.check_no_net()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.set_cfun(1)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_esim_11(self):
        """
        CFUN切换到0，无法识别ESIM卡
        """
        exc_type = None
        exc_value = None
        try:
            self.linux_esim_1()
            self.activate_profile('1')
            self.set_cfun(0)
            self.check_module_info(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.set_cfun(1)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def linux_esim_12(self):
        """
        CFUN切换到1，正常识别ESIM卡
        """
        self.linux_esim_1()
        self.activate_profile('1')
        self.set_cfun(1)
        self.check_module_info()
        self.at_handle.check_network()

    def linux_esim_13(self):
        """
        重复多次切换CFUN，ESIM卡状态正常
        """
        exc_type = None
        exc_value = None
        try:
            self.linux_esim_1()
            self.activate_profile('1')
            self.change_cfun()
            self.check_module_info()
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.set_cfun(1)
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    esim = LinuxESIM('/dev/ttyUSBAT', '/dev/ttyUSBDM', '/home/cris/Driver/qmi_wwan_q',
                     '1$trl.prod.ondemandconnectivity.com$X6OONS2BNAV4QCYL, 8988247000111720869,'
                     '1$trl.prod.ondemandconnectivity.com$ALDYCKQQ95GZKC1M, 8988247000111701224,'
                     '1$trl.prod.ondemandconnectivity.com$ALDYCKQQ95GZKC1M, 8988247000111701224')
    # esim.linux_esim_1()
    # esim.linux_esim_2()
    # esim.linux_esim_3()
    # esim.linux_esim_4()
    # esim.linux_esim_5()
    # esim.linux_esim_6()
    # esim.linux_esim_7()
    # esim.linux_esim_8()
    # esim.linux_esim_9()
    esim.linux_esim_10()
    esim.linux_esim_11()
    esim.linux_esim_12()
    esim.linux_esim_13()
