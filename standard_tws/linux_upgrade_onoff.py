import re
import sys
import time
from utils.functions.decorators import startup_teardown
from utils.cases.linux_upgrade_onoff_manager import UpgradeOnOff
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import UpgradeOnOffError
from utils.cases.linux_upgrade_onoff_manager import Powerkey
import traceback


class LinuxUpgradeOnOff(UpgradeOnOff):
    def test_upgrade_1(self):
        """
        使用卡巴斯基工具分别对标准版本包和工厂版本包进行扫描确认无病毒,使用其他杀毒工具测试也可以
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.mount_package()
            self.ubuntu_copy_file()
            self.unzip_firmware()
            self.scan_virus()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.umount_package()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_2(self):
        """
        对比工厂包和标准包的文件的差异性
        :return:
        """
        self.compare_file()

    @startup_teardown(teardown=['linux_reset_module'])
    def test_upgrade_4(self):
        """
        Linux系统firehose方式升级功能正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.restore_imei_sn_and_ect()
            self.qfirehose_upgrade('prev', False, True, False)
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(False)
            self.check_module_id()
            self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)
            self.check_usb_id()
            self.check_module_version(True)
            self.check_module_id()
            self.at_handler.check_network()
            self.chceck_module_info()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['linux_reset_module'])
    def test_upgrade_5(self):
        """
        Linux系统firehose方式全擦升级
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(False)
            self.check_module_id()
            self.qfirehose_upgrade('cur', False, True, True)
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(True)
            self.check_module_id()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_6(self):
        """
        确认PowerKey开机及关机功能及URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(30)
            power_off_urc = ['NORMAL POWER DOWN', 'POWERED DOWN', '+CREG: 0', '+CEREG: 0', '+CGREG: 0']
            self.at_handler.send_at('AT+CREG=2;+CGREG=2;+CEREG=2;&W')
            net_value = self.at_handler.send_at('AT+CREG?;+CGREG?;+CEREG?')
            creg_val = ''.join(re.findall(r'\+CREG: .*,(\d)', net_value))
            cereg_val = ''.join(re.findall(r'\+CEREG: .*,(\d)', net_value))
            cgreg_val = ''.join(re.findall(r'\+CGREG: .*,(\d)', net_value))
            power_off_urc.remove('+CREG: 0') if creg_val == '0' else None
            power_off_urc.remove('+CEREG: 0') if cereg_val == '0' else None
            power_off_urc.remove('+CGREG: 0') if cgreg_val == '0' else None
            all_logger.info(f'检测关机URC列表为{power_off_urc}')
            self.at_handler.send_at('AT+QURCCFG="urcport","all"', timeout=3)
            if 'RG' in self.at_handler.send_at('ATI'):
                try:
                    powerkey_thread = Powerkey(self.at_port, self.modem_port, power_off_urc)   # Normal Power Down等URC上报很快，开启线程捕捉
                    powerkey_thread.setDaemon(True)
                    powerkey_thread.start()
                    self.gpio.set_pwk_low_level()     # RG需要先拉低再拉高再拉低关机
                    time.sleep(1)
                    self.gpio.set_pwk_high_level()
                    time.sleep(1)
                    self.gpio.set_pwk_low_level()
                    powerkey_thread.join()  # 阻塞检测powerkey关机URC上报线程
                    if powerkey_thread.error_msg != '':
                        all_logger.info('Powerkey检测URC出现异常:{}'.format(powerkey_thread.error_msg))
                        raise UpgradeOnOffError('Powerkey检测URC出现异常:{}'.format(powerkey_thread.error_msg))
                except UpgradeOnOffError as e:
                    raise Exception(e)
                self.driver_check.check_usb_driver_dis()
                self.gpio.set_pwk_high_level()
                self.driver_check.check_usb_driver()
                time.sleep(3)
                self.read_poweron_urc()
                time.sleep(10)
                self.adb_check_cpu(40.0)
            else:
                try:
                    if self.cur_version[:5] in ["RM520", "RM530"]:   # X6X RM项目 无'NORMAL POWER DOWN', 'POWERED DOWN'上报
                        self.gpio.set_pwk_low_level()   # 直接拉低
                    else:
                        powerkey_thread = Powerkey(self.at_port, self.modem_port, power_off_urc)  # Normal Power Down等URC上报很快，开启线程捕捉
                        powerkey_thread.setDaemon(True)
                        powerkey_thread.start()
                        time.sleep(1)
                        self.gpio.set_pwk_low_level()  # RM直接拉低即可关机
                        powerkey_thread.join()
                        if powerkey_thread.error_msg != '':
                            all_logger.info('Powerkey检测URC出现异常:{}'.format(powerkey_thread.error_msg))
                            raise UpgradeOnOffError('Powerkey检测URC出现异常:{}'.format(powerkey_thread.error_msg))
                except UpgradeOnOffError as e:
                    raise Exception(e)
                self.driver_check.check_usb_driver_dis()
                self.gpio.set_pwk_high_level()
                self.driver_check.check_usb_driver()
                time.sleep(3)
                self.read_poweron_urc()
                time.sleep(10)
                self.adb_check_cpu(40.0)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.gpio.set_pwk_high_level()
            self.driver_check.check_usb_driver()
            time.sleep(15)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_7(self):
        """
        qpowd正常关机功能及URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(15)
            self.qpowd(2)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.driver_check.check_usb_driver()
            time.sleep(15)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_8(self):
        """
        qpowd=1正常关机功能及URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(15)
            self.qpowd(1)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.driver_check.check_usb_driver()
            time.sleep(15)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_9(self):
        """
        qpowd=0紧急关机功能及URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(15)
            self.qpowd(0)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.driver_check.check_usb_driver()
            time.sleep(15)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_10(self):
        """
        CFUN1,1重启,URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(15)
            self.cfun1_1()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_13(self):
        """
        升级查询CPU Loading正常，不会某个进程CPU占用率过高
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            self.adb_check_cpu(40.0)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['linux_reset_module'])
    def test_upgrade_14(self):
        """
        Linux系统firehose方式升级过程中随机断电，重新升级正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('prev', False, True, False)
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(False)
            self.check_module_id()
            self.qfirehose_upgrade('cur', True, False, False)
            self.gpio.set_vbat_high_level()
            self.is_upgrade_process_exist()
            time.sleep(3)
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            time.sleep(6)
            if self.is_qdl():  # 模块已转紧急下载模式
                if self.cur_version[:5] in ["RM520", "RM530"]:     # X6X RM项目断电升级，进入紧急下载模式后，直接升级
                    self.qfirehose_upgrade('cur', False, False, False)
                else:
                    self.gpio.set_pwk_low_level()
                    self.qfirehose_upgrade('cur', False, False, False)
                    self.gpio.set_pwk_high_level()
            else:
                self.qfirehose_upgrade('cur', False, False, False)
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)
            self.check_usb_id()
            self.check_module_version(True)
            self.at_handler.check_network()
            self.chceck_module_info()
            self.check_module_id()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            self.driver_check.check_usb_driver()
            time.sleep(10)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['linux_reset_module'])
    def test_upgrade_15(self):
        """
        Linux系统firehose方式升级功能正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('prev', False, True, False)
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(False)
            self.check_module_id()
            self.qfirehose_upgrade('cur', False, True, False)
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(True)
            self.check_module_id()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['linux_reset_module'])
    def test_upgrade_16(self):
        """
        Linux系统firehose方式升级过程中随机断电，重新升级正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('prev', False, True, False)
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_module_version(False)
            self.check_module_id()
            self.qfirehose_upgrade('cur', True, True, False)
            self.gpio.set_vbat_high_level()
            self.is_upgrade_process_exist()
            time.sleep(3)
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            time.sleep(6)
            if self.is_qdl():  # 模块已转紧急下载模式
                if self.cur_version[:5] in ["RM520", "RM530"]:   # X6X RM项目断电升级，进入紧急下载模式后，直接升级
                    self.qfirehose_upgrade('cur', False, True, False)
                else:
                    self.gpio.set_pwk_low_level()
                    self.qfirehose_upgrade('cur', False, True, False)
                    self.gpio.set_pwk_high_level()
            else:
                self.qfirehose_upgrade('cur', False, True, False)
            self.driver_check.check_usb_driver()
            self.read_poweron_urc()
            time.sleep(5)
            self.restore_imei_sn_and_ect()
            self.check_usb_id()
            self.check_module_version(True)
            self.at_handler.check_network()
            self.chceck_module_info()
            self.check_module_id()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            self.driver_check.check_usb_driver()
            time.sleep(10)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_17(self):
        """
        默认值状态modem重启功能确认
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.check_default_modem()
            self.set_modem_value(1, 1)
            self.set_adb()
            self.adb_check_cpu(40.0)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_18(self):
        """
        ModemRstLevel为0 & Aprstlevel为1时模块整机重启
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_modem_value(0, 1)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.back_dump_value()
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_19(self):
        """
        ModemRstLevel为0 & Aprstlevel为0时模块进Dump
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.check_dump_log()
            self.set_modem_value(0, 0)
            # self.qpst()     # 因为每个case执行结束会断电，所以这里直接抓dumplog
            if not self.qlog_dump.catch_dump():
                all_logger.info('使用Qlog抓取dumplog失败，重启模块恢复')
                self.gpio.set_vbat_high_level()
                time.sleep(3)
                self.gpio.set_vbat_low_level()
                self.gpio.set_pwk_high_level()
                self.driver_check.check_usb_driver()
                raise UpgradeOnOffError('使用Qlog抓取dumplog失败')
            self.gpio.set_pwk_high_level()
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.read_poweron_urc()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            self.back_dump_value()
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_upgrade_21(self):
        """
        SBL1文件大小对比
        :return:
        """
        self.compare_sbl_file()

    def test_upgrade_22(self):
        """
        reset重启功能及URC上报正常
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.set_adb()
            time.sleep(15)
            self.reset()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.gpio.set_reset_low_level()
            self.driver_check.check_usb_driver()
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)


if __name__ == '__main__':
    # at_port, dm_port, modem_port, imei, svn, firmware_path, version_name, prev_firmware_path, uart_port, port_info, prev_version, usb_id):
    fir_path = r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A05M4G_01.001V01.01.001V01'
    prev_path = r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A04M4G_01.001V01.01.001V01'
    params_dict = {
        "at_port": 'COM23',
        "dm_port": 'COM22',
        "modem_port": 'COM5',
        "imei": '869710030002905',
        "svn": '56',
        "firmware_path": fir_path,
        "prev_firmware_path": prev_path,
        "uart_port": 'COM28',
        "port_info": r'USB\VID_2C7C&PID_0800&REV_0414&MI_02',
        "prev_version": "",
        'usb_id': '',
        'prev_svn': '',
        'cur_version': ''
    }
    test = LinuxUpgradeOnOff(**params_dict)
    test.test_upgrade_19()
