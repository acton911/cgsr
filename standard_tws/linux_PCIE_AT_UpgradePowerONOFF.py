import sys
import time
from utils.cases.linux_pcie_at_upgradepoweronoff_manager import LinuxATManagerPowerManager
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxATUpgradeError


class LinuxATManagerPower(LinuxATManagerPowerManager):
    def test_pcie_upgradepoweronoff_1(self):
        """
        data_interface配置1,0为PCIE模式是否正常
        """
        time.sleep(60)
        self.check_and_set_pcie_data_interface()
        time.sleep(60)  # 避免和后台运行的驱动加载程序冲突
        self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
        time.sleep(5)
        self.check_pcie_driver()
        time.sleep(10)
        self.check_pcie_data_interface()

    def test_pcie_upgradepoweronoff_2(self):
        """
        使用QFirehose工具全擦升级工厂版本
        """
        exc_type = None
        exc_value = None
        try:
            self.mount_package()
            self.ubuntu_copy_file()
            self.unzip_firmware()
            time.sleep(10)
            self.check_module_version()
            self.at_handler.check_network()
            self.qfirehose_upgrade('cur', False, True, True)
            time.sleep(20)
            self.driver.check_usb_driver()
            time.sleep(60)
            self.check_and_set_pcie_data_interface()
            time.sleep(60)
            self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
            time.sleep(5)
            self.check_pcie_driver()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.umount_package()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_pcie_upgradepoweronoff_3(self):
        """
        QFirehose工具升级过程中EVB断电
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('cur', True, True, True)
            self.gpio.set_vbat_high_level()
            self.is_upgrade_process_exist()
            time.sleep(3)
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            time.sleep(10)
            if self.is_qdl():   # 模块已转紧急下载模式
                self.gpio.set_pwk_low_level()
                self.qfirehose_upgrade('cur', False, True, True)
                self.gpio.set_pwk_high_level()
            else:
                self.qfirehose_upgrade('cur', False, True, True)
            time.sleep(20)
            self.driver.check_usb_driver()
            time.sleep(60)
            self.check_and_set_pcie_data_interface()
            time.sleep(60)
            self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
            time.sleep(5)
            self.check_pcie_driver()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_pcie_upgradepoweronoff_4(self):
        """
        ModemRstLevel为0 & Aprstlevel为0时模块进Dump，使用QLog工具抓dump log
        """
        exc_type = None
        exc_value = None
        try:
            self.set_modem_value(0, 0)
            if not self.qlog_dump.catch_dump():
                all_logger.info('使用Qlog抓取dumplog失败，重启模块恢复')
                self.gpio.set_vbat_high_level()
                time.sleep(3)
                self.gpio.set_vbat_low_level()
                self.gpio.set_pwk_high_level()
                self.driver.check_usb_driver()
                raise LinuxATUpgradeError('使用Qlog抓取dumplog失败')
            self.gpio.set_pwk_high_level()
            self.driver.check_usb_driver()
            time.sleep(20)
            self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            self.back_dump_value()
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)
