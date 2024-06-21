import sys
import time
import os
from utils.cases.windows_laptop_upgradepoweronoff_manager import LaptopUpgradeOnOff
from utils.logger.logging_handles import all_logger
from utils.functions.fw import FW
from utils.functions.middleware import Middleware
from utils.log import log


class WindowsLaptopUpgradeOnOff(LaptopUpgradeOnOff):
    def test_laptopupgradeonoff_01_001(self):
        """
        PCIE Only模式使用AT指令查询模块为efuse状态
        """
        time.sleep(60)
        self.at_handler.send_at('AT')
        self.check_efuse_status()

    def test_laptopupgradeonoff_01_002(self):
        """
        升级到上个A工厂版本
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.prev_firmware_path,
                    factory=True, ati=self.prev_ati, csub=self.prev_csub)
            fw.upgrade()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_01_003(self):
        """
        升级到上个A标准版本
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.prev_firmware_path,
                    factory=False, ati=self.prev_ati, csub=self.prev_csub)
            fw.upgrade()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_01_004(self):
        """
        升级到当前标准版本
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                    factory=False, ati=self.ati, csub=self.csub)
            fw.upgrade()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_01_005(self):
        """
        升级到当前版本工厂版本
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                    factory=True, ati=self.ati, csub=self.csub)
            fw.upgrade()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_01_006(self):
        """
        升级到当前版本标准版本
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                    factory=False, ati=self.ati, csub=self.csub)
            fw.upgrade()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_01_007(self):
        """
        验证ADB功能可正常开启
        """
        exc_type = None
        exc_value = None
        try:
            time.sleep(10)
            self.check_hwid_value()
            self.at_handler.send_at('AT+QPCIE="ADB",1')
            #  self.cfun1_1()
            self.at_handler.check_network()
            self.check_adb_devices_connect()
            self.adb_check_hwid()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            self.at_handler.send_at('AT+QPCIE="ADB",0')
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_02_001(self):
        """
        验证AT+CFUN=1,1指令重启模块，确认驱动加载及功能正常
        """
        exc_type = None
        exc_value = None
        try:
            self.cfun1_1()
            self.at_handler.send_at('AT')
            self.check_efuse_status()
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_02_003(self):
        """
        验证ADB功能可正常开启
        """
        exc_type = None
        exc_value = None
        try:
            time.sleep(10)
            self.at_handler.send_at('AT+QPCIE="ADB",1')
            self.cfun1_1()
            self.at_handler.send_at('AT')
            self.at_handler.check_network()
            self.check_adb_devices_connect()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_02_004(self):
        """
        验证ADB功能可正常关闭
        """
        exc_type = None
        exc_value = None
        try:
            time.sleep(10)
            self.at_handler.send_at('AT+QPCIE="ADB",0')
            self.cfun1_1()
            self.at_handler.send_at('AT')
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_03_001(self):
        """
        升级过程中笔电睡眠
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                    factory=True, ati=self.ati, csub=self.csub)
            fw.upgrade_sleep()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_03_002(self):
        """
        升级过程中笔电休眠
        """
        exc_type = None
        exc_value = None
        try:
            fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                    factory=True, ati=self.ati, csub=self.csub)
            fw.upgrade_dormancy()
            time.sleep(10)
            self.at_handler.check_network()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_03_006(self):
        """
        使用QXDM在DM口抓取QXDM log
        """
        exc_type = None
        exc_value = None
        try:
            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_laptopupgradeonoff_03_006')
            all_logger.info(f"log_save_path: {log_save_path}")
            self.at_handler.cfun0()
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handler.cfun1()
                self.at_handler.check_network()
                all_logger.info("wait 10 seconds")
                time.sleep(10)
                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_laptopupgradeonoff_03_007(self):
        """
        ModemRstLevel为0 & Aprstlevel为0时模块进Dump
        :return:
        """
        exc_type = None
        exc_value = None
        try:
            self.check_dump_log()
            self.set_modem_value(0, 0)
            self.qpst()
            self.driver_check.check_usb_driver()
            time.sleep(3)
            self.at_handler.check_urc()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            self.back_dump_value()
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)
