import sys
from utils.functions.decorators import startup_teardown
from utils.cases.linux_pcie_dfota_manager import LinuxPCIEDFOTAManager
import time
from utils.logger.logging_handles import all_logger
import traceback


class LinuxPCIEDFOTA(LinuxPCIEDFOTAManager):

    @startup_teardown()
    def test_linux_pcie_dfota_01_001(self):
        """
        制作正向升级和反向升级差分包
        """
        exc_type = None
        exc_value = None
        try:
            self.mount_package()
            self.ubuntu_copy_file()
            self.unzip_firmware()
            self.make_dfota_package()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.umount_package()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(startup=['init'])
    def test_linux_pcie_dfota_01_002(self):
        """
        QFirehose全擦烧录A版本的工厂版本后，烧录A版本的标准版本，检查基本信息
        """
        exc_type = None
        exc_value = None
        try:
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
            self.at_handler.send_at('AT+QCFG="data_interface",1,0', 0.3)
            self.qfirehose_upgrade('prev', False, False, False)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)
        time.sleep(20)  # 等到正常
        self.after_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown()
    def test_linux_pcie_dfota_01_003(self):
        """
        上传差分包到HTTP及HTTPS服务器
        """
        self.upload_package_to_sftp()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_pcie_dfota_01_004(self):
        """
        HTTPS DFOTA正向升级
        """
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_pcie_dfota_01_005(self):
        """
        HTTPS DFOTA反向升级
        """
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_pcie_dfota_01_006(self):
        """
        HTTPS DFOTA正向升级过程中随机断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_pcie_dfota_01_007(self):
        """
        HTTPS DFOTA反向升级过程中随机断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_pcie_dfota_01_008(self):
        """
        HTTPS DFOTA下载差分包过程中断电（正向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_pcie_dfota_01_009(self):
        """
        HTTPS DFOTA下载差分包过程中断电（反向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        self.check_pcie_pci()
        self.check_pcie_driver()
        self.check_pcie_data_interface()


if __name__ == '__main__':
    param_dict = {
        'uart_port': '/dev/ttyUSB0',
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'revision': 'RG500QEAAAR11A06M4G',
        'sub_edition': 'V01',
        'svn': "58",  # 当前版本SVN号
        'prev_upgrade_revision': 'RG500QEAAAR11A02M4G',
        'prev_upgrade_sub_edition': 'V05',
        'prev_svn': '52',  # 上个版本的SVN号
        'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G '
                         r'Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A06M4G_01.001V01.01.001V01',
        'prev_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G '
                              r'Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A02M4G_01.001V05.01.001V05 '
    }
    w = LinuxPCIEDFOTA(**param_dict)
    w.test_linux_pcie_dfota_01_001()
    w.test_linux_pcie_dfota_01_002()
    w.test_linux_pcie_dfota_01_003()
    w.test_linux_pcie_dfota_01_004()
    w.test_linux_pcie_dfota_01_005()
    w.test_linux_pcie_dfota_01_006()
    w.test_linux_pcie_dfota_01_007()
    w.test_linux_pcie_dfota_01_008()
    w.test_linux_pcie_dfota_01_009()
