import re
import sys
import time
import traceback
from utils.cases.linux_qss_limit_R_and_I_manager import LinuxQSSLimitRAndIManager
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import QSSLimitRAndIError


class LinuxQSSLimitRAndI(LinuxQSSLimitRAndIManager):

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_000(self):
        """
        用于方法调试
        """
        # self.enb_file_name_now, _ = self.get_weak_enb_file_name()
        # print(self.enb_file_name_now)
        # print(_)
        iperf(ip=self.qss_ip, user='sdr', passwd='123123', port=22, bandwidth='30M', times=30, mode=1, linux=True)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_001(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25001    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级当前版本工厂版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.umount_package()
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_002(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_003(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_004(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_005(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_006(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_007(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_008(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_009(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_010(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_011(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_012(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_013(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_014(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 32    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_015(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 93    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_016(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25001	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_017(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_018(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_019(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_020(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_021(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_022(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_023(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_024(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_025(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_026(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_027(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_028(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_029(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43232	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_030(self):
        """
        "烧录禁俄版本工厂版本，插入俄罗斯卡找Russia&Iran网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43293	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_046(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25001	LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到上个支持俄罗斯的版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # 升级当前禁R&I版本标准版本
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_047(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_048(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_049(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_050(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_051(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_052(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_053(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_054(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_055(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_056(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_057(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_058(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_059(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 32    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_060(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 93    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_061(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25001	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_062(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_063(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_064(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_065(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_066(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_067(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_068(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_069(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_070(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_071(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_072(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_073(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_074(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43232	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_075(self):
        """
        "从上个支持俄罗斯网络的版本，QFLASH升级标准版本到禁俄版本，插入俄罗斯卡找Russia网
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43293	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_091(self):
        """
        Russia SIM PLMN:25001
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        1.QSS配置plmn为25001的网络环境
        2.模组插plmn为25001的sim卡开机找网
        3.AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络和AT+QNWLOCK="common/4g"锁频点，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到上个支持俄罗斯的版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # 从上个支持俄罗斯的版本adb fota到当前禁R版本
            self.abd_fota()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_092(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_093(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_094(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_095(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_096(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_097(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_098(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_099(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_100(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_101(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_102(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_103(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_104(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 32    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_105(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 93    LTE网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_106(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25001	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_107(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25002	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25002', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_108(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25020	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25020', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_109(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25027	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25027', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_110(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25028	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25028', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_111(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25035	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25035', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_112(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25062	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25062', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_113(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Russia SIM PLMN:25099	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25099', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_114(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 35(IranCell)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_115(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 70 (TCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43270', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_116(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 11(IR-MCI)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43211', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_117(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 19 (MTCE)	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43219', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_118(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:432 14	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43214', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_119(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43232	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43232', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_01_120(self):
        """
        从上个支持俄罗斯网络的版本，FOTA升级到禁俄版本（B-factory->B-Update），插入俄罗斯卡找Russia网(若项目要求使能seboot，则使能seboot之后测试)
        (若项目要求使能seboot，则使能seboot之后测试)"
        Iran SIM PLMN:43293	5G网络
        （评审暂定只在第一条进行升级，后续直接开网写卡注网）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43293', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_001(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插ROW_Commercial的sim卡开机找网    00101/8949024
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到当前禁R&I的工厂版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('00101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_002(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插ROW_Generic_3GPP_PTCRB_GCF的sim卡开机找网    00101/8949024
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('00101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_003(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插Dito_Commercial的sim卡开机找网    51566/896366
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('51566', '896366', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_004(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Telia_Sweden 的sim卡开机找网    	24001/894601
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('24001', '894601', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_005(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 TIM_Italy_Commercial 的sim卡开机找网    	22201/893901
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('22201', '893901', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_006(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 France-Commercial-Orange 的sim卡开机找网    	20801,20802/893301
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('20801', '893301', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_007(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-DT-VOLTE 的sim卡开机找网    	26201/894901,894902,894903,8988228
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('26201', '894901', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_008(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Germany-VoLTE-Vodafone 的sim卡开机找网    	26202/894920
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('26202', '894920', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_009(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 UK-VoLTE-Vodafone 的sim卡开机找网    	23415,23591/8988239,894410
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('23415', '8988239', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_010(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 UK-VoLTE-Vodafone 的sim卡开机找网    	23430,23431,23432,23433,23434,23501,23502/894412,894430,894429
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('23430', '894412', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_011(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Optus_Australia_Commercial 的sim卡开机找网    	50502/896102
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50502', '896102', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_012(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Telstra_Australia_Commercial 的sim卡开机找网    	50501/896101
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_013(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-LGU 的sim卡开机找网    	45006/898206
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45006', '898206', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_014(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 "Commercial-KT 的sim卡开机找网    	45008/898230
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45008', '898230', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_015(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-SKT 的sim卡开机找网    	45005/898205
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45005', '898205', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_016(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-Reliance 的sim卡开机找网    	405840 405854 405855 405856 405857 405858 405859 405860 405861 405862 405863 405864 405865 405866 405867 405868 405869 405870 405871 405872 405873 405874/8991840 8991854 8991855 8991856 8991857 8991858 8991859 8991860 8991861 8991862 8991863 8991864 8991865 8991866 8991867 8991868 8991869 8991870 8991871 8991872 8991873 8991874
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('405840', '8991840', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_017(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-SBM 的sim卡开机找网    	44020/8981200
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44020', '8981200', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_018(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-KDDI 的sim卡开机找网    	44051/898130
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44051', '898130', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_019(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-DCM 的sim卡开机找网    		44010/8981100
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44010', '8981100', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_020(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 VoLTE-CU 的sim卡开机找网    		46001,46006,46009/898601,898606,898609
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46001', '898601', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_021(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 VoLTE_OPNMKT_CT 的sim卡开机找网    		46003 46005 46011 46012 45502 45507 46059 99904/898603 898611 8985302 8985307
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46003', '898603', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_02_022(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Volte_OpenMkt-Commercial-CMCC 的sim卡开机找网    		46000 46002 46004 46007 46008 46013/898600 898602 898604 898607 898608 898613
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46000', '898600', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_001(self):
        """
        1.QSS配置ROW_Commercial的网络环境
        2.模组插ROW_Commercial的sim卡开机找网    00101/8949024
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到当前禁R&I的工厂版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('00101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_002(self):
        """
        1.QSS配置ROW_Generic_3GPP_PTCRB_GCF的网络环境
        2.模组插ROW_Generic_3GPP_PTCRB_GCF的sim卡开机找网    00101/8949024
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('00101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_003(self):
        """
        1.QSS配置Dito_Commercial的网络环境
        2.模组插Dito_Commercial的sim卡开机找网    51566/896366
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('51566', '896366', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_004(self):
        """
        1.QSS配置Telia_Sweden的网络环境
        2.模组插 Telia_Sweden 的sim卡开机找网    	24001/894601
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('24001', '894601', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_005(self):
        """
        1.QSS配置 TIM_Italy_Commercial 的网络环境
        2.模组插 TIM_Italy_Commercial 的sim卡开机找网    	22201/893901
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('22201', '893901', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_006(self):
        """
        1.QSS配置 France-Commercial-Orange 的网络环境
        2.模组插 France-Commercial-Orange 的sim卡开机找网    	20801,20802/893301
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('20801', '893301', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_007(self):
        """
        1.QSS配置 Commercial-DT-VOLTE 的网络环境
        2.模组插 Commercial-DT-VOLTE 的sim卡开机找网    	26201/894901,894902,894903,8988228
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('26201', '894901', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_008(self):
        """
        1.QSS配置 Germany-VoLTE-Vodafone 的网络环境
        2.模组插 Germany-VoLTE-Vodafone 的sim卡开机找网    	26202/894920
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('26202', '894920', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_009(self):
        """
        1.QSS配置 UK-VoLTE-Vodafone 的网络环境
        2.模组插 UK-VoLTE-Vodafone 的sim卡开机找网    	23415,23591/8988239,894410
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('23415', '8988239', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_010(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 UK-VoLTE-Vodafone 的sim卡开机找网    	23430,23431,23432,23433,23434,23501,23502/894412,894430,894429
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('23430', '894412', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_011(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Optus_Australia_Commercial 的sim卡开机找网    	50502/896102
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50502', '896102', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_012(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Telstra_Australia_Commercial 的sim卡开机找网    	50501/896101
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_013(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-LGU 的sim卡开机找网    	45006/898206
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45006', '898206', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_014(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 "Commercial-KT 的sim卡开机找网    	45008/898230
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45008', '898230', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_015(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-SKT 的sim卡开机找网    	45005/898205
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('45005', '898205', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_016(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-Reliance 的sim卡开机找网    	405840 405854 405855 405856 405857 405858 405859 405860 405861 405862 405863 405864 405865 405866 405867 405868 405869 405870 405871 405872 405873 405874/8991840 8991854 8991855 8991856 8991857 8991858 8991859 8991860 8991861 8991862 8991863 8991864 8991865 8991866 8991867 8991868 8991869 8991870 8991871 8991872 8991873 8991874
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('405840', '8991840', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_017(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-SBM 的sim卡开机找网    	44020/8981200
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44020', '8981200', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_018(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-KDDI 的sim卡开机找网    	44051/898130
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44051', '898130', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_019(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Commercial-DCM 的sim卡开机找网    		44010/8981100
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('44010', '8981100', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_020(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 VoLTE-CU 的sim卡开机找网    		46001,46006,46009/898601,898606,898609
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46001', '898601', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_021(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 VoLTE_OPNMKT_CT 的sim卡开机找网    		46003 46005 46011 46012 45502 45507 46059 99904/898603 898611 8985302 8985307
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46003', '898603', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_03_022(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插 Volte_OpenMkt-Commercial-CMCC 的sim卡开机找网    		46000 46002 46004 46007 46008 46013/898600 898602 898604 898607 898608 898613
        3.AT+QNWPREFCFG="nr5g_band"锁band，AT+QNWPREFCFG="mode_pref",nr5g锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('46000', '898600', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 找网
            self.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_001(self):
        """
        Russia SIM PLMN:25001
        1.QSS开启Russia网络
        2.插入Russia卡烧录基准版本的工厂版本找网
        3.Qfirehose升级到目标版本找网
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到上个版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 升级到当前禁R&I的标准版本
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_002(self):
        """
        Russia SIM PLMN:25001
        1.QSS开启Russia网络
        2.插入Telstra卡烧录基准版本的工厂版本找网  '50501', '896101'
        3.QFlash升级到目标版本找网(包括锁cops和锁频点等)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_003(self):
        """
        Iran SIM PLMN:
        1.QSS开启Iran网络
        2.插入Iran卡烧录基准版本的工厂版本找网  43235
        3..QFlash升级到目标版本找网(包括锁cops和锁频点等)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_004(self):
        """
        1.QSS开启Iran网络
        2.插入Telstra卡烧录基准版本的工厂版本找网
        3.QFlash升级到目标版本找网(包括锁cops和锁频点等)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_005(self):
        """
        Russia SIM PLMN:25001
        1.QSS开启Russia网络
        2.插入Russia卡烧录基准版本的工厂版本找网
        3.DFOTA升级到目标版本找网
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到上个版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 从上个支持俄罗斯的版本adb fota到当前禁R版本
            self.abd_fota()

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_006(self):
        """
        Russia SIM PLMN:25001
        1.QSS开启Russia网络
        2.插入Telstra卡烧录基准版本的工厂版本找网  '50501', '896101'
        3.DFOTA升级到目标版本找网
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_007(self):
        """
        Iran SIM PLMN:
        1.QSS开启Iran网络
        2.插入Iran卡烧录基准版本的工厂版本找网  43235
        3.DFOTA升级到目标版本找网
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_04_008(self):
        """
        1.QSS开启Iran网络
        2.插入Telstra卡烧录基准版本的工厂版本找网
        3.DFOTA升级到目标版本找网
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('50501', '896101', need_check_network=True)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_05_001(self):
        """
        1.烧录非禁Russia&Iran的目标版本的工厂版本找网并进行备份AT+QPRTPARA=1
        2、查询当前版本是否合入防回滚at+qcfg="rollback"
        3.升级到禁Russia&Iran的标准版本找网
        4、查询当前版本是否合入防回滚at+qcfg="rollback"
        5.升级回到非禁Russia&Iran的目标版本的标准版本
        6.升级到禁Russia&Iran的标准版本找网
        7.AT+QPRTPARA=3手动还原找网

        1.驻网正常，Russia&Iran网络和其他运营商网络都正常
        2、返回error或者1（1：未开启软件防回滚功能，返回error表示不支持软件防回滚功能）
        3.无法注册Russia&Iran网络，其他运营商网络都正常
        4、返回0（开启软件防回滚功能）
        5.驻网正常，Russia&Iran网络和其他运营商网络都正常
        6.无法注册Russia&Iran网络，其他运营商网络都正常
        7.还原成功，模组无法注册Russia&Iran网络，其他运营商网络都正常
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False,  tesk_duration=1000)
            # self.delay_task(start_time, qss_connection, 200)

            # 1、升级回到上个版本的工厂版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 找网
            self.at_handle.send_at('AT+QPRTPARA=1', 15)  # 备份
            self.check_roback(True)
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",nr5g', 0.6)
            self.check_network()

            # 2、升级到当前禁R&I的标准版本
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 检查注网
            self.set_roaming()
            self.limit_r_and_i_check()
            self.check_roback(True)
            # 3、升级回到上个版本的标准版本
            self.qfirehose_upgrade('prev', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 找网
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",nr5g', 0.6)
            self.check_network()
            # 4、升级到当前禁R&I的标准版本
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 检查注网
            self.set_roaming()
            self.limit_r_and_i_check()
            # 5、还原检查注网
            self.at_handle.send_at('AT+QPRTPARA=3', 15)  # 还原
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 0.6)
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",auto', 0.6)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['reset_version'])
    def test_linux_qss_limit_r_and_i_05_002(self):
        """
        场景2：B(Factory) – A(update) [期望CFUN5 模组无法工作]  – B(update)[期望不能注册俄罗斯，而其他运营商可以正常工作]  -- A(update)[期望CFUN5模组无法工作] – 手动触发还原[期望CFUN5 模组无法工作] (备注：场景russia和iran的lte，5g网络各挑一个验证即可))
        1.烧录禁Russia&Iran的目标版本的工厂版本找网并进行备份AT+QPRTPARA=1
        2.升级到非禁Russia&Iran的标准版本找网,执行备注指令AT+QPRTPARA=4；然后在一分钟内连续三次执行at+qtest="dump",1指令，模块重启后查询CFUN值以及还原次数
        3.升级回到禁Russia&Iran的目标版本的标准版本AT+QPRTPARA=4查询、然后在一分钟内连续三次执行at+qtest="dump",1指令，模块重启后查询CFUN值以及还原次数
        4.升级到非禁Russia&Iran的标准版本找网

        1.无法注册Russia&Iran网络，可以注册其他运营商网络(锁运营商，锁频点)
        2.无法注册Russia&Iran网络和其他运营商网络，查询AT+CFUN?返回CFUN:5锁运营商，锁频点)，模块重启后查询cfun为5，且还原次数不会增加
        3.会上报一次RDY(自动还原过程)，AT+QPRTPARA=4查询会看到还原次数加1，无法注册Russia&Iran网络，可以注册其他运营商网络(锁运营商，锁频点)模块重启后查询cfun为1，且还原次数会增加
        4.无法注册Russia&Iran网络和其他运营商网络，查询AT+CFUN?返回CFUN:5或CFUN:7(锁运营商，锁频点)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False,  tesk_duration=1000)
            # self.delay_task(start_time, qss_connection, 200)

            # 1、升级到当前禁R&I的工厂版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 备份
            self.at_handle.send_at('AT+QPRTPARA=1', 15)  # 备份
            # 查询还原次数
            return_number1 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number1)
            number1 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number1))

            # 2、升级回到上个版本的标准版本
            self.qfirehose_upgrade('prev', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询还原次数
            return_number2 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number2)
            number2 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number2))
            if number1 != number2:
                raise QSSLimitRAndIError(f'查询还原次数发生变化，前：{number1}，后：{number2}')
            # 连续三次执行at+qtest="dump",1指令
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            # 模块重启
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询CFUN
            return_cfun1 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun1)
            if '5' not in return_cfun1:
                raise QSSLimitRAndIError('没有出现预期的cfun5!')
            self.limit_r_and_i_check()

            # 3、升级到当前禁R&I的标准版本
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询还原次数
            return_number3 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number3)
            number3 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number3))
            if int(number3) != int(number2) + 1:
                raise QSSLimitRAndIError(f'查询还原次数异常，前：{number2}，后：{number3}')
            else:
                all_logger.info('还原次数已经+1')
            # 连续三次执行at+qtest="dump",1指令
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            # 模块重启
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询CFUN
            return_cfun2 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun2)
            if '1' not in return_cfun2:
                raise QSSLimitRAndIError('cfun值异常!')
            self.set_roaming()
            self.limit_r_and_i_check()

            # 4、升级回到上个版本的标准版本
            self.qfirehose_upgrade('prev', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询CFUN
            return_cfun3 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun3)
            if '5' not in return_cfun3:
                raise QSSLimitRAndIError('没有出现预期的cfun5!')
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 0.6)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_05_003(self):
        """
        场景1：A(Factory) ) – 手动备份– B(update)-A(update) -- B(update) – 手动触发还原 (备注：场景russia和iran的lte，5g网络各挑一个验证即可))
        1.烧录非禁Russia&Iran的目标版本的工厂版本找网并进行备份AT+QPRTPARA=1
        2.fota升级到禁Russia&Iran的标准版本找网
        3.fota升级回到非禁Russia&Iran的目标版本的标准版本
        4.fota升级到禁Russia&Iran的标准版本找网
        5.AT+QPRTPARA=3手动还原找网

        1.驻网正常，Russia&Iran网络和其他运营商网络都正常
        2.无法注册Russia&Iran网络和其他运营商网络，其他运营商网络都正常
        3.驻网正常，Russia&Iran网络和其他运营商网络都正常
        4.无法注册Russia&Iran网络和其他运营商网络，其他运营商网络都正常
        5.还原成功，模组无法注册Russia&Iran网络和其他运营商网络，其他运营商网络都正常
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False,  tesk_duration=1000)
            # self.delay_task(start_time, qss_connection, 200)

            # 1、升级回到上个版本的工厂版本
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 找网
            self.at_handle.send_at('AT+QPRTPARA=1', 15)  # 备份
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",nr5g', 0.6)
            self.check_network()

            # 2、fota升级到当前禁R&I版本
            self.abd_fota()
            # 检查注网
            self.set_roaming()
            self.limit_r_and_i_check()

            # 3、fota升级回到上个版本版本
            self.abd_fota(False)
            # 找网
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",nr5g', 0.6)
            self.check_network()

            # 4、fota升级到当前禁R&I版本
            self.abd_fota()
            # 检查注网
            self.set_roaming()
            self.limit_r_and_i_check()

            # 5、还原检查注网
            self.at_handle.send_at('AT+QPRTPARA=3', 15)  # 还原
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 0.6)
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",auto', 0.6)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['reset_version'])
    def test_linux_qss_limit_r_and_i_05_004(self):
        """
        场景4：B(Factory) – A(update) [期望CFUN5 模组无法工作]  – B(update)[期望不能注册俄罗斯，而其他运营商可以正常工作]  -- A(update)[期望CFUN5模组无法工作] – 手动触发还原[期望CFUN5 模组无法工作] (备注：场景russia和iran的lte，5g网络各挑一个验证即可))
        1.烧录禁Russia&Iran的目标版本的工厂版本找网并进行备份AT+QPRTPARA=1
        2.升级到非禁Russia&Iran的标准版本找网,执行备注指令AT+QPRTPARA=4；然后在一分钟内连续三次执行at+qtest="dump",1指令，模块重启后查询CFUN值以及还原次数
        3.升级回到禁Russia&Iran的目标版本的标准版本AT+QPRTPARA=4，然后在一分钟内连续三次执行at+qtest="dump",1指令，模块重启后查询CFUN值以及还原次数查询然后在一分钟内连续三次执行at+qtest="dump",1指令，模块重启后查询CFUN值以及还原次数
        4.升级到非禁Russia&Iran的标准版本找网

        1.无法注册Russia&Iran网络，可以注册其他运营商网络(锁运营商，锁频点)
        2.无法注册Russia&Iran网络和其他运营商网络，查询AT+CFUN?返回CFUN:5锁运营商，锁频点)，模块重启后查询cfun为5，且还原次数不会增加
        3.会上报一次RDY(自动还原过程)，AT+QPRTPARA=4查询会看到还原次数加1，无法注册Russia&Iran网络，可以注册其他运营商网络(锁运营商，锁频点)，模块重启后查询cfun为1，且还原次数会增加
        4.无法注册Russia&Iran网络和其他运营商网络，查询AT+CFUN?返回CFUN:5(锁运营商，锁频点)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False,  tesk_duration=1000)
            # self.delay_task(start_time, qss_connection, 200)

            # 1、升级回到当前禁R&I版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 备份
            self.at_handle.send_at('AT+QPRTPARA=1', 15)  # 备份
            # 查询还原次数
            return_number1 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number1)
            number1 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number1))

            # 2、fota升级回到上个版本
            self.abd_fota(False)
            # 查询还原次数
            return_number2 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number2)
            number2 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number2))
            if number1 != number2:
                raise QSSLimitRAndIError(f'查询还原次数发生变化，前：{number1}，后：{number2}')
            # 连续三次执行at+qtest="dump",1指令
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            # 模块重启
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询CFUN
            return_cfun1 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun1)
            if '5' not in return_cfun1 and '7' not in return_cfun1:
                raise QSSLimitRAndIError('没有出现预期的cfun5或者cfun7!')
            self.limit_r_and_i_check()

            # 3、fota升级到当前禁R&I版本
            self.abd_fota()
            # 查询还原次数
            return_number3 = self.at_handle.send_at('AT+QPRTPARA=4', 15)
            all_logger.info(return_number3)
            number3 = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+)', return_number3))
            if int(number3) != int(number2) + 1:
                raise QSSLimitRAndIError(f'查询还原次数异常，前：{number2}，后：{number3}')
            else:
                all_logger.info('还原次数已经+1')
            # 连续三次执行at+qtest="dump",1指令
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            time.sleep(1)
            self.at_handle.send_at('at+qtest="dump",1', 19)
            # 重启模块
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            # 查询CFUN
            return_cfun2 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun2)
            if '1' not in return_cfun2:
                raise QSSLimitRAndIError('cfun值异常!')
            self.set_roaming()
            self.limit_r_and_i_check()

            # 4、升级回到上个版本的标准版本
            self.abd_fota(False)
            # 查询CFUN
            return_cfun3 = self.at_handle.send_at('AT+CFUN?', 15)
            all_logger.info(return_cfun3)
            if '5' not in return_cfun3 and '7' not in return_cfun3:
                raise QSSLimitRAndIError('没有出现预期的cfun5或者cfun7!')
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 0.6)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_06_001(self):
        """
        Russia SIM PLMN:25001
        1.QSS配置plmn为25001的网络环境
        2.模组插plmn为25001的sim卡开机找网
        3.重启模组
        4、在cpin:ready前后执行以下指令
        at+cops=0
        at+cops=1,2,"25001"
        等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 制作正向升级和反向升级差分包
            self.prepare_package()

            # 升级到当前禁R&I的工厂版本
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver_check.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()

            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 重启
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            # 指定urc出现后立刻发送AT
            self.send_after_urc('AT+CFUN=0', 'RDY')
            self.send_after_urc('AT+CFUN=1', '+CPIN: READY')
            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_06_002(self):
        """
        1.QSS配置plmn为43235的网络环境
        2.模组插plmn为43235的sim卡开机找网
        3.重启模组
        4、在cpin:ready前后执行以下指令
        at+cops=0
        at+cops=1,2,"
        等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 重启
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            # 指定urc出现后立刻发送AT
            self.send_after_urc('AT+CFUN=0', 'RDY')
            self.send_after_urc('AT+CFUN=1', '+CPIN: READY')
            # 检查注网
            self.limit_r_and_i_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_06_003(self):
        """
        1.QSS配置plmn为25001的网络环境
        2.模组插plmn为25001的sim卡开机找网
        3.AT+QNWPREFCFG="NR5G_BAND"，锁band
        AT+QNWPREFCFG="mode_pref",NR5G锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        4、切换至卡槽二
        5、AT+QNWPREFCFG="NR5G_BAND"，锁band
        AT+QNWPREFCFG="mode_pref",NR5G锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('25001', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()

            # 切换到sim2
            self.at_handle.send_at('AT+quimslot=2', 3)
            # 检查注网
            self.write_simcard_r_or_i('25001', '8949024')
            self.at_handle.cfun0()
            self.at_handle.cfun1()
            self.limit_r_and_i_check()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+quimslot=1', 3)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_limit_r_and_i_06_004(self):
        """
        1.QSS配置plmn为43235的网络环境
        2.模组插plmn为43235的sim卡开机找网
        3.AT+QNWPREFCFG="NR5G_BAND"，锁band
        AT+QNWPREFCFG="mode_pref",NR5G锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        4、切换至卡槽二
        5、AT+QNWPREFCFG="NR5G_BAND"，锁band
        AT+QNWPREFCFG="mode_pref",NR5G锁制式，AT+QNWLOCK="common/5g"锁频点，AT+COPS=1,2,"25001"&AT+COPS=4,2,"25001"锁运营商网络，等待5-10分钟（非禁Russia&Iran版本的找网时间的三倍左右）查看找网结果
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss('43235', need_check_network=False)
            # self.delay_task(start_time, qss_connection, 200)

            # 检查注网
            self.limit_r_and_i_check()

            # 切换到sim2
            self.at_handle.send_at('AT+quimslot=2', 3)
            # 检查注网
            self.write_simcard_r_or_i('43235', '8949024')
            self.at_handle.cfun0()
            self.at_handle.cfun1()
            self.limit_r_and_i_check()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+quimslot=1', 3)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == "__main__":
    # uart_port, at_port, dm_port, debug_port,
    # qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name,
    # ati, csub, name_sub_version, revision, sub_edition, prev_upgrade_revision, svn, ChipPlatform,
    # prev_upgrade_sub_edition, prev_svn, prev_firmware_path, firmware_path
    p_list = {
        'uart_port': '/dev/ttyUSB0',
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB1',
        'qss_ip': '10.66.129.204',
        'local_ip': '66.66.66.66',
        'node_name': 'jeckson_test',
        "mme_file_name": "25001-mme-ims.cfg",
        "enb_file_name": "25001-fdd-enb-lte-b3.cfg",
        "ims_file_name": "25001-ims.cfg",
        'name_sub_version': 'RG501QEUAAR12A07M4G_04.200.04.200_V01',
        'revision': 'RG501QEUAAR12A06M4G',  # ati
        'sub_edition': 'V01',
        'prev_upgrade_revision': 'RG501QEUAAR12A06M4G',  # pre_ati
        'svn': '99',
        'ChipPlatform': 'SDX55',
        'prev_upgrade_sub_edition': 'V03',  # pre_csub
        'prev_svn': '99',
        'prev_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG501QEU\Release\RG501QEU_VD_R12\RG501QEUAAR12A06M4G_04.001.04.001_V03',
        'firmware_path': r'\\192.168.11.252\quectel2\Project\Module Project Files\5G Project\SDX55\RG501QEU\Release\RG501QEU_VD_R12\RG501QEUAAR12A07M4G_04.200.04.200_V01',
        'prev_name_sub_version': 'RG501QEUAAR12A06M4G_04.001.04.001_V03',
    }
    qss_test = LinuxQSSLimitRAndI(**p_list)
    # qss_test.test_linux_qss_limit_r_and_i_01_000()
    qss_test.test_linux_qss_limit_r_and_i_01_001()  #
    qss_test.test_linux_qss_limit_r_and_i_01_002()  #
    qss_test.test_linux_qss_limit_r_and_i_01_003()
    qss_test.test_linux_qss_limit_r_and_i_01_004()
    qss_test.test_linux_qss_limit_r_and_i_01_005()
    qss_test.test_linux_qss_limit_r_and_i_01_006()
    qss_test.test_linux_qss_limit_r_and_i_01_007()
    qss_test.test_linux_qss_limit_r_and_i_01_008()
    qss_test.test_linux_qss_limit_r_and_i_01_009()
    qss_test.test_linux_qss_limit_r_and_i_01_010()
    qss_test.test_linux_qss_limit_r_and_i_01_011()
    qss_test.test_linux_qss_limit_r_and_i_01_012()
    qss_test.test_linux_qss_limit_r_and_i_01_013()
    qss_test.test_linux_qss_limit_r_and_i_01_014()
    qss_test.test_linux_qss_limit_r_and_i_01_015()

    qss_test.test_linux_qss_limit_r_and_i_01_016()
    qss_test.test_linux_qss_limit_r_and_i_01_017()
    qss_test.test_linux_qss_limit_r_and_i_01_018()
    qss_test.test_linux_qss_limit_r_and_i_01_019()
    qss_test.test_linux_qss_limit_r_and_i_01_020()
    qss_test.test_linux_qss_limit_r_and_i_01_021()
    qss_test.test_linux_qss_limit_r_and_i_01_022()
    qss_test.test_linux_qss_limit_r_and_i_01_023()
    qss_test.test_linux_qss_limit_r_and_i_01_024()
    qss_test.test_linux_qss_limit_r_and_i_01_025()
    qss_test.test_linux_qss_limit_r_and_i_01_026()
    qss_test.test_linux_qss_limit_r_and_i_01_027()
    qss_test.test_linux_qss_limit_r_and_i_01_028()
    qss_test.test_linux_qss_limit_r_and_i_01_029()
    qss_test.test_linux_qss_limit_r_and_i_01_030()

    qss_test.test_linux_qss_limit_r_and_i_01_046()  #
    qss_test.test_linux_qss_limit_r_and_i_01_047()  #
    qss_test.test_linux_qss_limit_r_and_i_01_048()
    qss_test.test_linux_qss_limit_r_and_i_01_049()
    qss_test.test_linux_qss_limit_r_and_i_01_050()
    qss_test.test_linux_qss_limit_r_and_i_01_051()
    qss_test.test_linux_qss_limit_r_and_i_01_052()
    qss_test.test_linux_qss_limit_r_and_i_01_053()
    qss_test.test_linux_qss_limit_r_and_i_01_054()
    qss_test.test_linux_qss_limit_r_and_i_01_055()
    qss_test.test_linux_qss_limit_r_and_i_01_056()
    qss_test.test_linux_qss_limit_r_and_i_01_057()
    qss_test.test_linux_qss_limit_r_and_i_01_058()
    qss_test.test_linux_qss_limit_r_and_i_01_059()
    qss_test.test_linux_qss_limit_r_and_i_01_060()

    qss_test.test_linux_qss_limit_r_and_i_01_061()
    qss_test.test_linux_qss_limit_r_and_i_01_062()
    qss_test.test_linux_qss_limit_r_and_i_01_063()
    qss_test.test_linux_qss_limit_r_and_i_01_064()
    qss_test.test_linux_qss_limit_r_and_i_01_065()
    qss_test.test_linux_qss_limit_r_and_i_01_066()
    qss_test.test_linux_qss_limit_r_and_i_01_067()
    qss_test.test_linux_qss_limit_r_and_i_01_068()
    qss_test.test_linux_qss_limit_r_and_i_01_069()
    qss_test.test_linux_qss_limit_r_and_i_01_070()
    qss_test.test_linux_qss_limit_r_and_i_01_071()
    qss_test.test_linux_qss_limit_r_and_i_01_072()
    qss_test.test_linux_qss_limit_r_and_i_01_073()
    qss_test.test_linux_qss_limit_r_and_i_01_074()
    qss_test.test_linux_qss_limit_r_and_i_01_075()

    qss_test.test_linux_qss_limit_r_and_i_01_091()  #
    qss_test.test_linux_qss_limit_r_and_i_01_092()  #
    qss_test.test_linux_qss_limit_r_and_i_01_093()
    qss_test.test_linux_qss_limit_r_and_i_01_094()
    qss_test.test_linux_qss_limit_r_and_i_01_095()
    qss_test.test_linux_qss_limit_r_and_i_01_096()
    qss_test.test_linux_qss_limit_r_and_i_01_097()
    qss_test.test_linux_qss_limit_r_and_i_01_098()
    qss_test.test_linux_qss_limit_r_and_i_01_099()
    qss_test.test_linux_qss_limit_r_and_i_01_100()
    qss_test.test_linux_qss_limit_r_and_i_01_101()
    qss_test.test_linux_qss_limit_r_and_i_01_102()
    qss_test.test_linux_qss_limit_r_and_i_01_103()
    qss_test.test_linux_qss_limit_r_and_i_01_104()
    qss_test.test_linux_qss_limit_r_and_i_01_105()

    qss_test.test_linux_qss_limit_r_and_i_01_106()
    qss_test.test_linux_qss_limit_r_and_i_01_107()
    qss_test.test_linux_qss_limit_r_and_i_01_108()
    qss_test.test_linux_qss_limit_r_and_i_01_109()
    qss_test.test_linux_qss_limit_r_and_i_01_110()
    qss_test.test_linux_qss_limit_r_and_i_01_111()
    qss_test.test_linux_qss_limit_r_and_i_01_112()
    qss_test.test_linux_qss_limit_r_and_i_01_113()
    qss_test.test_linux_qss_limit_r_and_i_01_114()
    qss_test.test_linux_qss_limit_r_and_i_01_115()
    qss_test.test_linux_qss_limit_r_and_i_01_116()
    qss_test.test_linux_qss_limit_r_and_i_01_117()
    qss_test.test_linux_qss_limit_r_and_i_01_118()
    qss_test.test_linux_qss_limit_r_and_i_01_119()
    qss_test.test_linux_qss_limit_r_and_i_01_120()

    qss_test.test_linux_qss_limit_r_and_i_02_001()  #
    qss_test.test_linux_qss_limit_r_and_i_02_002()  #
    qss_test.test_linux_qss_limit_r_and_i_02_003()
    qss_test.test_linux_qss_limit_r_and_i_02_004()
    qss_test.test_linux_qss_limit_r_and_i_02_005()
    qss_test.test_linux_qss_limit_r_and_i_02_006()
    qss_test.test_linux_qss_limit_r_and_i_02_007()
    qss_test.test_linux_qss_limit_r_and_i_02_008()
    qss_test.test_linux_qss_limit_r_and_i_02_009()
    qss_test.test_linux_qss_limit_r_and_i_02_010()
    qss_test.test_linux_qss_limit_r_and_i_02_011()
    qss_test.test_linux_qss_limit_r_and_i_02_012()
    qss_test.test_linux_qss_limit_r_and_i_02_013()
    qss_test.test_linux_qss_limit_r_and_i_02_014()
    qss_test.test_linux_qss_limit_r_and_i_02_015()
    qss_test.test_linux_qss_limit_r_and_i_02_016()
    qss_test.test_linux_qss_limit_r_and_i_02_017()
    qss_test.test_linux_qss_limit_r_and_i_02_018()
    qss_test.test_linux_qss_limit_r_and_i_02_019()
    qss_test.test_linux_qss_limit_r_and_i_02_020()
    qss_test.test_linux_qss_limit_r_and_i_02_021()
    qss_test.test_linux_qss_limit_r_and_i_02_022()

    qss_test.test_linux_qss_limit_r_and_i_03_001()  #
    qss_test.test_linux_qss_limit_r_and_i_03_002()  #
    qss_test.test_linux_qss_limit_r_and_i_03_003()
    qss_test.test_linux_qss_limit_r_and_i_03_004()
    qss_test.test_linux_qss_limit_r_and_i_03_005()
    qss_test.test_linux_qss_limit_r_and_i_03_006()
    qss_test.test_linux_qss_limit_r_and_i_03_007()
    qss_test.test_linux_qss_limit_r_and_i_03_008()
    qss_test.test_linux_qss_limit_r_and_i_03_009()
    qss_test.test_linux_qss_limit_r_and_i_03_010()
    qss_test.test_linux_qss_limit_r_and_i_03_011()
    qss_test.test_linux_qss_limit_r_and_i_03_012()
    qss_test.test_linux_qss_limit_r_and_i_03_013()
    qss_test.test_linux_qss_limit_r_and_i_03_014()
    qss_test.test_linux_qss_limit_r_and_i_03_015()
    qss_test.test_linux_qss_limit_r_and_i_03_016()
    qss_test.test_linux_qss_limit_r_and_i_03_017()
    qss_test.test_linux_qss_limit_r_and_i_03_018()
    qss_test.test_linux_qss_limit_r_and_i_03_019()
    qss_test.test_linux_qss_limit_r_and_i_03_020()
    qss_test.test_linux_qss_limit_r_and_i_03_021()
    qss_test.test_linux_qss_limit_r_and_i_03_022()

    qss_test.test_linux_qss_limit_r_and_i_04_001()  #
    qss_test.test_linux_qss_limit_r_and_i_04_002()  #
    qss_test.test_linux_qss_limit_r_and_i_04_003()
    qss_test.test_linux_qss_limit_r_and_i_04_004()
    qss_test.test_linux_qss_limit_r_and_i_04_005()
    qss_test.test_linux_qss_limit_r_and_i_04_006()
    qss_test.test_linux_qss_limit_r_and_i_04_007()
    qss_test.test_linux_qss_limit_r_and_i_04_008()

    qss_test.test_linux_qss_limit_r_and_i_05_001()  #
    qss_test.test_linux_qss_limit_r_and_i_05_002()  #
    qss_test.test_linux_qss_limit_r_and_i_05_003()  #
    qss_test.test_linux_qss_limit_r_and_i_05_004()  #

    qss_test.test_linux_qss_limit_r_and_i_06_001()  #
    qss_test.test_linux_qss_limit_r_and_i_06_002()  #
    qss_test.test_linux_qss_limit_r_and_i_06_003()
    qss_test.test_linux_qss_limit_r_and_i_06_004()
