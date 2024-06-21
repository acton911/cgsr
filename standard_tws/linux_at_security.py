import sys
import time
import traceback
from utils.functions.decorators import startup_teardown
from utils.cases.linux_atsecurity_manager import LinuxATSecurityManager
from utils.logger.logging_handles import all_logger


class LinuxATSecurity(LinuxATSecurityManager):

    @startup_teardown()
    def ATSecurityTest_02_001(self):
        """
        制作正向升级和反向升级差分包
        """
        self.mount_package()
        self.ubuntu_copy_file()
        self.unzip_firmware()
        self.make_dfota_package()
        # 上传差分包到HTTP及HTTPS服务器
        self.upload_package_to_sftp()
        # HTTPS DFOTA反向升级
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        # HTTPS DFOTA正向升级
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['reset_b_version'])
    def ATSecurityTest_02_002(self):
        """
        在线HTTP方式反向升级（http://220.180.239.212:8300/5G/2b496b6f77）
        """
        try:
            self.mount_package()
            self.ubuntu_copy_file()
            self.unzip_firmware()
            self.make_abdfota_package(factory=False)
            self.upload_package_to_sftp()
            all_logger.info("开始在线HTTP方式反向升级")
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("HTTP", a_b=False)
            self.dfota_b_a_upgrade_check()
            all_logger.info("在线HTTP方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def ATSecurityTest_02_003(self):
        """
        在线HTTP方式正向升级（http://220.180.239.212:8300/5G/2b496b6f77）
        """
        try:
            all_logger.info("开始在线HTTP方式正向升级")
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("HTTP", a_b=True)
            self.dfota_a_b_upgrade_check()
            all_logger.info("在线HTTP方式正向升级结束")
        finally:
            self.reset_after(a_version=False)


if __name__ == '__main__':
    param_dict = {
        'uart_port': 'COM5',
        'at_port': 'COM11',
        'dm_port': 'COM14',
        'revision': 'RG500QEAAAR11A06M4G',
        'sub_edition': 'V01',
        'svn': "58",  # 当前版本SVN号
        'prev_upgrade_revision': 'RG500QEAAAR11A02M4G',
        'prev_upgrade_sub_edition': 'V05',
        'prev_svn': '52',  # 上个版本的SVN号
        'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A06M4G_01.001V01.01.001V01',
        'prev_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A02M4G_01.001V05.01.001V05'
    }
    w = LinuxATSecurity(**param_dict)
    w.ATSecurityTest_02_001()
