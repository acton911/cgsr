from utils.functions.decorators import startup_teardown
from utils.cases.windows_dfota_manager import WindowsDFOTAManager, ATBackgroundThreadWithDriverCheck
import time
from utils.logger.logging_handles import all_logger


class WindowsDFOTA(WindowsDFOTAManager):

    @startup_teardown()
    def test_windows_dfota_01_001(self):
        """
        制作正向升级和反向升级差分包
        """
        self.copy_firmware()
        self.unzip_firmware()
        self.make_dfota_package()

    @startup_teardown()
    def test_windows_dfota_01_002(self):
        """
        检查差分包中不能有BOOTABLE_IMAGES文件夹
        """
        self.check_bootable_images()

    @startup_teardown(startup=['init'])
    def test_windows_dfota_01_003(self):
        """
        QFIL全擦烧录A版本的工厂版本，Qflash工具烧录A版本的标准版本后，检查基本信息
        """
        self.qfil_upgrade_and_check(erase=True, factory=True, external_path='prev')  # 全擦，工厂包，升级到前一个版本
        time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
        self.qfil_upgrade_and_check(erase=False, factory=False, external_path='prev')  # 不擦，标准包，升级前一个版本的标准包
        time.sleep(20)  # 等到正常
        self.after_upgrade_check()
        
    @startup_teardown(startup=['init'])
    def test_windows_dfota_01_003_01(self):
        """
        QFIL全擦烧录A版本的工厂版本，Qflash工具烧录A版本的标准版本后，检查基本信息
        """
        self.qfirehose_upgrade('prev', True)  # 全擦，工厂包，升级到前一个版本
        time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
        self.qfirehose_upgrade('prev', False)  # 不擦，标准包，升级前一个版本的标准包
        time.sleep(20)  # 等到正常
        self.after_upgrade_check()
        
    @startup_teardown()
    def test_windows_dfota_02_001(self):
        """
        上传差分包到HTTP及HTTPS服务器
        """
        self.upload_package_to_sftp()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_002(self):
        """
        HTTPS DFOTA正向升级
        """
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_004(self):
        """
        HTTPS DFOTA反向升级
        """
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_005(self):
        """
        HTTPS DFOTA正向升级过程中随机断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_006(self):
        """
        HTTPS DFOTA反向升级过程中随机断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_007(self):
        """
        HTTPS DFOTA正向升级，开始升级上报+QIND: "FOTA","START"时断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, start=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_008(self):
        """
        HTTPS DFOTA反向升级，开始升级上报+QIND: "FOTA","START"时断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, start=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_009(self):
        """
        HTTPS DFOTA正向升级，升级完成上报+QIND: "FOTA","END",0时断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, end=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_010(self):
        """
        HTTPS DFOTA反向升级，升级完成上报+QIND: "FOTA","END",0时断电
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, end=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_011(self):
        """
        HTTPS DFOTA下载差分包过程中断网（正向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, dl_stop=True, dl_cfun=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_012(self):
        """
        HTTPS DFOTA下载差分包过程中断网（反向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_cfun=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_013(self):
        """
        HTTPS DFOTA下载差分包过程中断电（正向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=True, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_02_014(self):
        """
        HTTPS DFOTA下载差分包过程中断电（反向升级）
        """
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_02_015(self):
        """
        HTTP DFOTA正反向升级
        """
        all_logger.info("开始进行正常升级")
        self.dfota_upgrade_online('HTTP', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()
        all_logger.info("开始进行反向升级")
        self.dfota_upgrade_online('HTTP', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown()
    def test_windows_dfota_03_001(self):
        """
        上传差分包到FTP服务器
        """
        self.upload_package_to_ftp()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_03_002(self):
        """
        Qflash工具升级当前测试标准版本，检查基本信息
        """
        mbn = self.get_mbn_list()
        self.qfil_upgrade_and_check(erase=False, factory=False, external_path='cur')  # 不擦，标准包，升级当前版本的标准包
        time.sleep(20)  # 等到正常
        self.dfota_a_b_upgrade_check()
        self.compare_mbn_list(mbn)

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_03_003(self):
        """
        FTP DFOTA反向升级功能正常
        """
        self.dfota_upgrade_online('FTP', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_03_004(self):
        """
        FTP DFOTA正向升级功能正常
        """
        self.dfota_upgrade_online('FTP', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init'])
    def test_windows_dfota_04_001(self):
        """
        QFIL全擦烧录A版本的工厂版本，Qflash工具烧录A版本的标准版本后，检查基本信息
        """
        self.qfil_upgrade_and_check(erase=True, factory=True, external_path='prev')  # 全擦，工厂包，升级到前一个版本
        time.sleep(20)  # 升级工厂版本后等待20S，不然可能会转换DL口失败
        self.qfil_upgrade_and_check(erase=False, factory=False, external_path='prev')  # 不擦，标准包，升级前一个版本的标准包
        time.sleep(20)  # 等到正常
        self.after_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_windows_dfota_04_002(self):
        """
        ADB方式上传正向升级差分包到UFS中后升级正常，基本信息查询正常
        """
        self.unlock_adb()
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b=True)
        # 兼容小米版本
        if self.Is_XiaoMi_version:
            self.at_handler.send_at('AT+QFOTADL="/usrdata/cache/ufs/a-b.zip"')
        else:
            self.at_handler.send_at('AT+QFOTADL="/cache/ufs/a-b.zip"')
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
        self.dfota_step_2()
        if 'START' not in at_background_read.get_info():
            all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                             "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_windows_dfota_04_003(self):
        """
        ADB方式上传反向升级差分包到UFS中后升级正常，基本信息查询正常
        """
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b=False)
        # 兼容小米版本
        if self.Is_XiaoMi_version:
            self.at_handler.send_at('AT+QFOTADL="/usrdata/cache/ufs/b-a.zip"')
        else:
            self.at_handler.send_at('AT+QFOTADL="/cache/ufs/b-a.zip"')
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
        self.dfota_step_2()
        if 'START' not in at_background_read.get_info():
            all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                             "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.check_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init'])
    def test_windows_dfota_05_001(self):
        """
        获取差分包MD5码校验
        """
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b=False)
        self.push_package_and_check(a_b=True)


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
    w = WindowsDFOTA(**param_dict)
    w.test_windows_dfota_01_001()
    w.test_windows_dfota_01_002()
    w.test_windows_dfota_01_003()
    w.test_windows_dfota_02_001()
    w.test_windows_dfota_02_002()
