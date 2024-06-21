import time
from utils.exception.exceptions import LinuxABSystemError
from utils.functions.decorators import startup_teardown
from utils.cases.linux_ab_system_manager import LinuxABSystemManager
from utils.logger.logging_handles import all_logger
import subprocess
import traceback
import os
import re


class LinuxABSystem(LinuxABSystemManager):
    @startup_teardown()
    def test_linux_ab_system_01_001(self):
        """
        1、制作正向升级和反向升级差分包
        2、上传到HTTP及HTTPS服务器
        3、上传差分包到FTP服务器
        """
        self.mount_package()
        self.ubuntu_copy_file()
        self.unzip_firmware()
        self.make_dfota_package(factory=False)
        self.upload_package_to_sftp()
        self.upload_package_to_ftp()

        # self.get_module_id()
        # self.unlock_adb()
        # self.qfirehose_to_version(a_version=False)

        # self.push_modify_file('part', a_b=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_01_002(self):
        """
        差分包存放UFS目录下,重启后不会丢失
        """
        try:
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            self.push_package_and_check(a_b=False)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.check_urc()
            self.check_adb_devices_connect()
            self.reboot_package_check(a_b=False)
        finally:
            self.reset_after(a_version=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_01_003(self):
        """
        本地方式升级（ADB方式上传差分包）
        """
        try:
            all_logger.info("开始ADB本地方式反向升级")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=False)
            all_logger.info("ADB本地方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_01_004(self):
        """
        在线HTTP方式正向升级（http://220.180.239.212:8300/5G/2b496b6f77）
        """
        try:
            all_logger.info("开始在线HTTP方式正向升级")
            self.after_upgrade_check(a_b=False)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("HTTP", ufs_file='_', a_b=True)
            all_logger.info("在线HTTP方式正向升级结束")
        finally:
            self.reset_after(a_version=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_01_005(self):
        """
        在线HTTP方式反向升级（http://220.180.239.212:8300/5G/2b496b6f77）
        """
        try:
            all_logger.info("开始在线HTTP方式反向升级")
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("HTTP", ufs_file='_', a_b=False)
            all_logger.info("在线HTTP方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_01_006(self):
        """
        在线FTP方式正向升级
        """
        try:
            all_logger.info("开始在线FTP方式正向升级")
            self.after_upgrade_check(a_b=False)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("FTP", ufs_file='_', a_b=True)
            all_logger.info("在线FTP方式正向升级结束")
        finally:
            self.reset_after(a_version=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_01_007(self):
        """
        在线FTP方式反向升级
        """
        try:
            all_logger.info("开始在线FTP方式反向升级")
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            self.ab_update_online("FTP", ufs_file='_', a_b=False)
            all_logger.info("在线FTP方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_01_008(self):
        """
        本地方式正向升级（AT指令上传差分包）
        """
        try:
            all_logger.info("开始AT指令上传差分包方式正向升级")
            ufs_file = []
            self.after_upgrade_check(a_b=False)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.at_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=True)
            all_logger.info("AT指令上传差分包方式正向升级结束")
        finally:
            self.reset_after(a_version=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_01_009(self):
        """
        本地方式反向升级（AT指令上传差分包）
        """
        try:
            all_logger.info("开始AT指令上传差分包方式反向升级")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.at_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=False)
            all_logger.info("AT指令上传差分包方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_02_001(self):
        """
        确认升级以及同步过程中的CPU占用率,升级过程中CPU是完全占用的状态
        """
        try:
            all_logger.info("开始ADB指令上传差分包方式正向升级")
            # time.sleep(30)
            ufs_file = []
            self.after_upgrade_check(a_b=False)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=True, query_mode=False)
            all_logger.info("ADB指令上传差分包方式正向升级结束")
        finally:
            self.reset_after(a_version=False)

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_03_001(self):
        """
        升级以及同步过程耗费时间值
        """
        try:
            all_logger.info("开始ADB指令上传差分包方式反向升级")
            # time.sleep(30)
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            time_backup_use, time_update_use = self.ab_update(ufs_file=ufs_file, a_b=False)
            all_logger.info("time_backup_use::{}\r\ntime_update_use: {}".format(str(time_backup_use), str(time_update_use)))
            if time_backup_use < 600:
                all_logger.info("BACKUP时间正常: {}".format(str(time_backup_use)))
            else:
                raise LinuxABSystemError("BACKUP时间异: {}".format(str(time_backup_use)))
            if time_update_use < 90:
                all_logger.info("UPDATE时间正常: {}".format(str(time_update_use)))
            else:
                raise LinuxABSystemError("UPDATE时间异常: {}".format(str(time_update_use)))
            all_logger.info("ADB指令上传差分包方式反向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_001(self):
        """
        擦除A分区的system分区,重启后启动分区确认是否变化
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_system' if system_before == '1' else 'system')
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after != system_before:
                all_logger.info("重启后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_002(self):
        """
        擦除A分区的modem分区,重启后启动分区确认是否变化
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_modem' if system_before == '1' else 'modem')
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after != system_before:
                all_logger.info("重启后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_003(self):
        """
        擦除A分区的boot分区,重启后启动分区确认是否变化
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_boot' if system_before == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after != system_before:
                all_logger.info("重启后运行系统已改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_004(self):
        """
        A分区启动后,擦除B分区,重启后模块依旧从A分区启动,此时A分区不会还原B分区
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_boot' if system_before == '0' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            system_after = self.check_activeslot()
            if system_after == system_before:
                all_logger.info("重启后运行系统未改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            all_logger.info("等待300s后再继续擦除!")
            time.sleep(300)
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.eblock(block='b_boot' if system_before == '0' else 'boot', nums=1)
            self.reboot_module()
            self.driver.check_usb_driver_dis()
            if not self.driver.check_usb_driver():
                all_logger.info("口加载失败模块无法正常启动,和预期一致!")
                self.qfirehose_to_version(a_version=True)
            else:
                raise LinuxABSystemError("异常!未出现预期口加载失败现象!")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_005(self):
        """
        A分区启动后,擦除B分区的boot分区,之后通过指令切换到B分区,模块重启,首先尝试从B分区启动,由于B分区损坏启动失败,之后从A分区启动,A分区启动成功后会还原B分区
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_boot' if system_before == '0' else 'boot', nums=1)
            # fotainfo --set-activepart 1
            subprocess.getoutput("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            all_logger.info("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after == system_before:
                all_logger.info("重启后运行系统未改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_006(self):
        """
        A分区启动后,擦除B分区的system分区,之后通过指令切换到B分区,模块重启,首先尝试从B分区启动,由于B分区损坏启动失败,之后从A分区启动,A分区启动成功后会还原B分区
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_system' if system_before == '0' else 'system')
            # fotainfo --set-activepart 1
            subprocess.getoutput("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            all_logger.info("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after == system_before:
                all_logger.info("重启后运行系统未改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_007(self):
        """
        A分区启动后,擦除B分区的modem分区,之后通过指令切换到B分区,模块重启,首先尝试从B分区启动,由于B分区损坏启动失败,之后从A分区启动,A分区启动成功后会还原B分区
        """
        try:
            # self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_modem' if system_before == '0' else 'modem')
            # fotainfo --set-activepart 1
            subprocess.getoutput("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            all_logger.info("adb shell fotainfo --set-activepart {}".format('1' if system_before == '0' else '0'))
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            system_after = self.check_activeslot()
            if system_after == system_before:
                all_logger.info("重启后运行系统未改变\r\nsystem_before:{}\r\nsystem_after:{}".format(system_before, system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(system_before, system_after))
            self.check_state_all_time(state_module='0')
            self.eblock(block='b_boot' if system_after == '1' else 'boot', nums=1)
            self.reboot_module()
            self.check_urc()
            self.check_backup()
            if self.check_activeslot() != system_after:
                all_logger.info("重启后运行系统正常\r\nsystem_before:{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            else:
                raise LinuxABSystemError("重启后运行系统异常!system_before:\r\n{}\r\nsystem_after:{}".format(self.check_activeslot(), system_after))
            self.check_state_all_time(state_module='0')
        except Exception as e:
            all_logger.info(e)
            self.qfirehose_to_version(a_version=True)
            raise LinuxABSystemError(e)
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_008(self):
        """
        8+8激活分区损坏,能继续升级成功
        """
        try:
            # 根据OC来决定是否执行
            all_logger.info("当前oc_num为: {}".format(self.oc_num))
            # RG502NEUDA-M28-SGASA
            oc_num_key = ''.join(re.findall(r'-\w+-', self.oc_num))
            all_logger.info("oc_num_key: {}".format(oc_num_key))
            if '8' in oc_num_key:
                all_logger.info("当前flash为 8+8,开始测试")
                ufs_file = []
                self.after_upgrade_check(a_b=True)
                self.unlock_adb()
                self.check_state_all_time(state_module='0')
                system_before = self.check_activeslot()
                self.eblock(block='b_boot' if system_before == '1' else 'boot', nums=1)
                file_name = self.at_package_and_check(a_b=False)
                ufs_file.append(file_name)
                file1_name = self.push_others(f_size=10)
                ufs_file.append(file1_name)
                file2_name = self.push_others(f_size=1024)
                ufs_file.append(file2_name)
                self.set_package_name(a_b=False)
                self.query_state(state_module="0")
                self.ab_update(ufs_file=ufs_file, a_b=False)

            else:
                all_logger.info("当前flash 为4+4,此case测试8+8,故测试结束")
                pass
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_04_009(self):
        """
        4+4激活分区损坏,不重启继续升级不能继续升级成功
        """
        try:
            # 根据OC来决定是否执行
            all_logger.info("当前oc_num为: {}".format(self.oc_num))
            # RG502NEUDA-M28-SGASA
            oc_num_key = ''.join(re.findall(r'-\w+-', self.oc_num))
            all_logger.info("oc_num_key: {}".format(oc_num_key))
            if '8' in oc_num_key:
                all_logger.info("当前flash为 8+8,此case测试4+4,故测试结束")
                pass
            else:
                all_logger.info("当前flash为 4+4,开始测试")
                self.after_upgrade_check(a_b=True)
                self.unlock_adb()
                self.check_state_all_time(state_module='0')
                system_before = self.check_activeslot()
                self.eblock(block='b_boot' if system_before == '1' else 'boot', nums=1)
                self.check_adb_devices_connect()
                self.push_package_and_check(a_b=False)
                self.set_package_name(a_b=False)
                self.send_update()
                msg = ''
                # noinspection PyBroadException
                try:
                    self.dfota_step_2()
                except Exception:
                    msg = traceback.format_exc()
                    all_logger.info("升级失败信息msg: {}".format(msg))
                if '查询升级状态异常' in msg:
                    all_logger.info("升级失败,和预期一致!")
                else:
                    raise LinuxABSystemError("异常!未出现预期升级失败现象!")
        finally:
            # 重启一次，以免影响后续case
            self.reboot_module()
            self.check_urc()
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_04_010(self):
        """
        非激活分区损坏,不重启继续升级成功
        """
        try:
            all_logger.info("开始ADB本地方式正向升级")
            ufs_file = []
            self.after_upgrade_check(a_b=False)
            self.check_state_all_time(state_module='0')
            system_before = self.check_activeslot()
            self.eblock(block='b_boot' if system_before == '0' else 'boot', nums=1)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            self.query_state(state_module="0")
            self.ab_update(ufs_file=ufs_file, a_b=True)
            all_logger.info("ADB本地方式正向升级结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_05_001(self):
        """
        升级过程中断电,上电后UFS下差分包未丢失,模块能够继续升级,不需要再次手动触发升级指令
        """
        try:
            all_logger.info("开始ADB本地方式反向升级断电")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=False, upgrade_stop=True)
            all_logger.info("ADB本地方式反向升级断电结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_05_002(self):
        """
        升级过程中删除升级包,升级失败,且重新添加升级包重新进行升级,升级成功
        """
        try:
            all_logger.info("开始ADB本地方式反向升级过程中删除差分包")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=False, delete_package=True)
            all_logger.info("ADB本地方式反向升级过程中删除差分包结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_05_003(self):
        """
        差分包删除之后,非激活分区(B)升级到一半损坏,此时手动触发重启,从A分区启动,之后A分区还原B分区,B分区还原成功后需要手动验证还原成功
        """
        try:
            all_logger.info("开始ADB本地方式反向升级过程中删除差分包")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=False, delete_package_and_reboot=True)
            all_logger.info("ADB本地方式反向升级过程中删除差分包结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_05_004(self):
        """
        升级过程中再次执行升级指令
        """
        try:
            all_logger.info("开始ADB本地方式反向升级过程中再次执行升级指令")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=False, send_again=True)
            all_logger.info("ADB本地方式反向升级过程中再次执行升级指令结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_06_001(self):
        """
        同步过程中断电,上电后UFS下差分包未丢失,模块能够继续同步,同步完成后UFS下文件自动删除
        """
        try:
            all_logger.info("开始ADB本地方式反向升级同步过程中断电")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            file_name = self.push_package_and_check(a_b=False)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=False)
            self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=False, backup_reboot=True)
            all_logger.info("ADB本地方式反向升级同步过程中断电结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_07_001(self):
        """
        在线HTTP方式反向升级下载过程中断网,下载失败,找网成功后能够重新通过AT命令能够触发再次下载,且下载升级成功
        """
        try:
            all_logger.info("开始在线HTTP方式反向升级下载过程中断网")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.ab_update_online("HTTP", ufs_file=ufs_file, a_b=False, dl_cfun=True, dl_stop=True)
            all_logger.info("在线HTTP方式反向升级下载过程中断网结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_07_002(self):
        """
        在线FTP方式反向升级下载过程中断网,下载失败,找网成功后能够重新通过AT命令能够触发再次下载,且下载升级成功
        """
        try:
            all_logger.info("开始在线FTP方式反向升级下载过程中断网")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.ab_update_online("FTP", ufs_file=ufs_file, a_b=False, dl_cfun=True, dl_stop=True)
            all_logger.info("在线FTP方式反向升级下载过程中断网结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_07_003(self):
        """
        HTTP或FTP在线下载过程中断网,保证UFS中存在残缺包和任意一个文件,重启后残缺包需要删除,用户文件不能发生变化
        """
        try:
            all_logger.info("开始在线FTP方式反向升级下载过程中断网用户文件不能发生变化")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            time.sleep(60)  # 等待网络稳定
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.ab_update_online("FTP", ufs_file=ufs_file, a_b=False, dl_cfun=True, dl_stop=True, check_dl_stop_file=True)
            all_logger.info("在线FTP方式反向升级下载过程中断网用户文件不能发生变化结束")
        finally:
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_08_001(self):
        """
        改差分包文件内容再次压缩后上传
        """
        try:
            all_logger.info("开始ADB本地方式改差分包文件内容再次压缩后上传")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()
            self.push_modify_file('del', a_b=False)
            all_logger.info("等待180s")
            time.sleep(180)
            self.set_package_name(a_b=False)
            self.send_update()
            msg = ''
            # noinspection PyBroadException
            try:
                self.dfota_step_2()
            except Exception:
                msg = traceback.format_exc()
                all_logger.info("升级失败信息msg: {}".format(msg))
            if '异常' in msg:
                all_logger.info("升级失败,和预期一致!")
            else:
                raise LinuxABSystemError("异常!未出现预期升级失败现象!")

            # to do continu
            file_name = self.push_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            # self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=True)
            all_logger.info("ADB本地方式反向升级改差分包文件内容再次压缩后上传结束")
        finally:
            # 删除测试固件包
            subprocess.getoutput('rm -rf {}'.format(os.path.join(os.getcwd(), 'firmware', 'modify')))
            self.reset_after()

    @startup_teardown(startup=['reset_b_version'])
    def test_linux_ab_system_08_002(self):
        """
        上传残缺包
        """
        try:
            all_logger.info("开始上传残缺包测试")
            ufs_file = []
            self.after_upgrade_check(a_b=True)
            self.unlock_adb()
            self.check_adb_devices_connect()

            self.push_modify_file('part', a_b=False)

            self.set_package_name(a_b=False)
            self.send_update()
            msg = ''
            # noinspection PyBroadException
            try:
                self.dfota_step_2()
            except Exception:
                msg = traceback.format_exc()
                all_logger.info("升级失败信息msg: {}".format(msg))
            if '异常' in msg:
                all_logger.info("升级失败,和预期一致!")
            else:
                raise LinuxABSystemError("异常!未出现预期升级失败现象!")

            # to do continu
            file_name = self.push_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            # self.query_state(state_module="0")
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update(ufs_file=ufs_file, a_b=True)
            all_logger.info("上传残缺包测试结束")
        finally:
            # 删除测试固件包
            subprocess.getoutput('rm -rf {}'.format(os.path.join(os.getcwd(), 'firmware', 'modify')))
            self.reset_after()

    @startup_teardown(startup=['reset_a_version'])
    def test_linux_ab_system_08_003(self):
        """
        上传不匹配包
        """
        try:
            # 开始制作其他版本和当前版本的测试包
            all_logger.info("开始制作不匹配包")
            self.unmatch_mount_package()
            self.unmatch_ubuntu_copy_file()
            self.unmatch_unzip_firmware()
            self.unmatch_make_dfota_package(factory=False)
            all_logger.info("开始上传不匹配包测试")
            ufs_file = []
            self.after_upgrade_check(a_b=False)
            self.unlock_adb()
            self.check_adb_devices_connect()
            self.unmatch_push_package_and_check(a_b=True)

            self.set_package_name(a_b=True)
            self.send_update()
            msg = ''
            # noinspection PyBroadException
            try:
                self.dfota_step_2()
            except Exception:
                msg = traceback.format_exc()
                all_logger.info("升级失败信息msg: {}".format(msg))
            if '异常' in msg:
                all_logger.info("升级失败,和预期一致!")
            else:
                raise LinuxABSystemError("异常!未出现预期升级失败现象!")

            # to do continu
            self.check_state_all_time(state_module='0')
            file_name = self.push_package_and_check(a_b=True)
            ufs_file.append(file_name)
            file1_name = self.push_others(f_size=10)
            ufs_file.append(file1_name)
            file2_name = self.push_others(f_size=1024)
            ufs_file.append(file2_name)
            self.set_package_name(a_b=True)
            self.check_state_all_time(state_module='0')
            # self.ab_update(ufs_file=ufs_file, a_b=False)
            self.ab_update_local(ufs_file=ufs_file, a_b=True)
            all_logger.info("上传不匹配包测试结束")
        finally:
            self.reset_after()

# adb shell rm -rf /cache/ufs/*.zip


if __name__ == '__main__':
    param_dict = {
        'uart_port': '/dev/ttyUSBUART',
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'revision': 'SG520TMDAR01A01M4G_BETA_20220107A',
        'sub_edition': 'V01',
        'svn': '33',  # 当前版本SVN号
        'prev_upgrade_revision': 'SG520TMDAR01A01M4G',
        'prev_upgrade_sub_edition': 'V01',
        'prev_svn': '34',  # 上个版本的SVN号
        'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX6X\SG520TMDA\Temp\SG520TMDA_VA\SG520TMDAR01A01M4G_BETA_20220107A_01.001.01.001',
        'prev_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX6X\SG520TMDA\Release\SG520TMDA_VA\SG520TMDAR01A01M4G_01.001V01.01.001V01',
        'name_sub_version': 'SG520TMDAR01A01M4G_BETA_20220107A_01.001.01.001',
        'prev_name_sub_version': 'SG520TMDAR01A01M4G_01.001V01.01.001V01',
        'oc_num': "RG502NEUAA-M20-SGASA",
        'unmatch_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX6X\SG520TMDA\Release\SG520TMDA_VA\SG520TMDAR01A01M4G_01.001V03.01.001V03',
        'unmatch_name_sub_version': 'SG520TMDAR01A01M4G_01.001V03.01.001V03'
    }

    # flash 8+8
    # 'oc_num': "RG502NEUDA-M28-SGASA"

    # flash 4+4
    # 'oc_num': "RG502NEUAA-M20-SGASA"
    w = LinuxABSystem(**param_dict)

    # 已知问题：
    """
    在线下载fota包后名称改变(变成了update.zip)
    升级后SVN改变
    新版本升级失败必现(不能全擦正方向升级)
    擦除modem分区后at不通无法恢复
    GMM返回值错误(STSDX6X-168)
    下载中断后UFS文件异常
    概率性同步过程中CPU空闲率不达标
    概率性擦除system后重启不同步
    删除包后立刻自动重启,无任何urc上报
    刚烧完版本在线升级下载失败
    """
    # w.test_linux_ab_system_01_001()
    # w.test_linux_ab_system_01_002()
    # w.test_linux_ab_system_01_003()
    # w.test_linux_ab_system_01_004()
    # w.test_linux_ab_system_01_005()
    # w.test_linux_ab_system_01_006()
    # w.test_linux_ab_system_01_007()
    # w.test_linux_ab_system_01_008()
    # w.test_linux_ab_system_01_009()
    # w.test_linux_ab_system_02_001()  # 概率性同步过程中CPU空闲率不达标
    # w.test_linux_ab_system_03_001()
    # w.test_linux_ab_system_04_001()  # 概率性擦除system后重启不同步
    # w.test_linux_ab_system_04_002()  # 擦除modem后重启at不通
    # w.test_linux_ab_system_04_003()
    # w.test_linux_ab_system_04_004()
    # w.test_linux_ab_system_04_005()
    # w.test_linux_ab_system_04_006()  # 擦除后重启不同步
    # w.test_linux_ab_system_04_007()  # 擦除后重启不同步
    w.test_linux_ab_system_04_008()  # 待试跑正确性
    w.test_linux_ab_system_04_009()
    # w.test_linux_ab_system_04_010()
    # w.test_linux_ab_system_05_001()
    # w.test_linux_ab_system_05_002()  # 删除包后立刻自动重启，无任何urc上报（自动重启后手动查状态应该是NEEDSYNC (5)，重启前也应该要自动上报下这个urc）
    # w.test_linux_ab_system_05_003()  # 删除包后立刻自动重启，无任何urc上报（自动重启后手动查状态应该是NEEDSYNC (5)，重启前也应该要自动上报下这个urc）
    # w.test_linux_ab_system_05_004()
    # w.test_linux_ab_system_06_001()
    # w.test_linux_ab_system_07_001()
    # w.test_linux_ab_system_07_002()
    # w.test_linux_ab_system_07_003()  # 有BUG待完善：中断后UFS文件异常
    # w.test_linux_ab_system_08_001()  # 添加文件后可以升级成功，待确认
    # w.test_linux_ab_system_08_002()
    # w.test_linux_ab_system_08_003()
