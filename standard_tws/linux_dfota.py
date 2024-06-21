import time
import sys
import traceback
import subprocess
from utils.functions.decorators import startup_teardown
from utils.cases.linux_dfota_manager import LinuxDFOTAManager, ATBackgroundThreadWithDriverCheck
from utils.logger.logging_handles import all_logger
from utils.functions.linux_api import LinuxAPI, QuectelCMThread
from utils.operate.at_handle import ATHandle
from utils.functions.iperf import iperf


class LinuxDFOTA(LinuxDFOTAManager):

    @startup_teardown()
    def test_linux_dfota_01_001(self):
        """
        制作正向升级和反向升级差分包
        """
        self.mount_package()
        self.ubuntu_copy_file()
        self.make_dfota_package()

    @startup_teardown()
    def test_linux_dfota_01_002(self):
        """
        检查差分包中不能有BOOTABLE_IMAGES文件夹
        """
        self.check_bootable_images()

    @startup_teardown(startup=['init'])
    def test_linux_dfota_01_003(self):
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

    @startup_teardown()
    def test_linux_dfota_02_001(self):
        """
        上传差分包到HTTP及HTTPS服务器
        """
        self.prepare_package()
        self.upload_package_to_sftp()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_002(self):
        """
        HTTPS DFOTA正向升级
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_004(self):
        """
        HTTPS DFOTA反向升级
        """

        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_005(self):
        """
        HTTPS DFOTA正向升级过程中随机断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_006(self):
        """
        HTTPS DFOTA反向升级过程中随机断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False, upgrade_stop=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_007(self):
        """
        HTTPS DFOTA正向升级，开始升级上报+QIND: "FOTA","START"时断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True, start=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_008(self):
        """
        HTTPS DFOTA反向升级，开始升级上报+QIND: "FOTA","START"时断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False, start=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_009(self):
        """
        HTTPS DFOTA正向升级，升级完成上报+QIND: "FOTA","END",0时断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True, end=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_010(self):
        """
        HTTPS DFOTA反向升级，升级完成上报+QIND: "FOTA","END",0时断电
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False, end=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_011(self):
        """
        HTTPS DFOTA下载差分包过程中断网（正向升级）
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True, dl_stop=True, dl_cfun=True, dl_cgatt=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_012(self):
        """
        HTTPS DFOTA下载差分包过程中断网（反向升级）
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_cfun=True, dl_cgatt=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_013(self):
        """
        HTTPS DFOTA下载差分包过程中断电（正向升级）
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=True, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_02_014(self):
        """
        HTTPS DFOTA下载差分包过程中断电（反向升级）
        """
        self.check_sftp_url()
        self.check_imei()
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_vbat=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_02_015(self):
        """
        HTTP DFOTA正反向升级
        """
        self.check_sftp_url()
        self.check_imei()
        all_logger.info("开始进行正常升级")
        self.dfota_upgrade_online('HTTP', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

        all_logger.info("开始进行反向升级")
        self.dfota_upgrade_online('HTTP', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown()
    def test_linux_dfota_03_001(self):
        """
        上传差分包到FTP服务器
        """
        self.prepare_package()
        self.upload_package_to_ftp()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_03_002(self):
        """
        Qflash工具升级当前测试标准版本，检查基本信息
        """

        self.qfirehose_upgrade('cur', False, False, False)
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_03_003(self):
        """
        FTP DFOTA反向升级功能正常
        """
        self.upload_package_to_ftp()
        self.check_imei()
        self.dfota_upgrade_online('FTP', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_03_004(self):
        """
        FTP DFOTA正向升级功能正常
        """
        self.upload_package_to_ftp()
        self.check_imei()
        self.dfota_upgrade_online('FTP', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init'])
    def test_linux_dfota_04_001(self):
        """
        QFIL全擦烧录A版本的工厂版本，Qflash工具烧录A版本的标准版本后，检查基本信息
        """
        self.qfirehose_upgrade('prev', False, True, True)
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()
        self.after_upgrade_check()

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_04_002(self):
        """
        ADB方式上传正向升级差分包到UFS中后升级正常，基本信息查询正常
        """
        self.check_imei()
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
        if self.revision.startswith("RG") and self.ChipPlatform == "SDX55":
            at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
            self.uart_handler.dfota_step_2()
            if 'START' not in at_background_read.get_info():
                all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                                 "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
        else:
            self.at_handler.dfota_step_2()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_04_003(self):
        """
        ADB方式上传反向升级差分包到UFS中后升级正常，基本信息查询正常
        """
        self.check_imei()
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b=False)
        # 兼容小米版本
        if self.Is_XiaoMi_version:
            self.at_handler.send_at('AT+QFOTADL="/usrdata/cache/ufs/b-a.zip"')
        else:
            self.at_handler.send_at('AT+QFOTADL="/cache/ufs/b-a.zip"')
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        if self.revision.startswith("RG") and self.ChipPlatform.startswith("SDX55"):
            at_background_read = ATBackgroundThreadWithDriverCheck(self.at_port, self.dm_port)
            self.at_handler.dfota_step_2()
            if 'START' not in at_background_read.get_info():
                all_logger.error("DFOTA MAIN UART检测到FOTA START上报，但是AT口未检测到START上报，"
                                 "出现原因是AT口驱动未加载出来或者未打开，FOTA START信息就已经上报，导致USB AT口无法捕获，应报BUG")
        else:
            self.at_handler.dfota_step_2()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()

    @startup_teardown(startup=['init'])
    def test_linux_dfota_05_001(self):
        """
        获取差分包MD5码校验
        """
        self.check_adb_devices_connect()
        self.push_package_and_check(a_b=False)
        self.push_package_and_check(a_b=True)

    @startup_teardown()
    def test_linux_dfota_07_001(self):
        """
        查询AT+QFOTAPID默认值，默认值下fota在线升级，期望正常
        """
        self.prepare_package(prev='cur', fota='b-a.zip')
        self.check_sftp_url()
        self.check_imei()
        all_logger.info("Qflash工具升级当前测试标准版本，检查基本信息")
        self.qfirehose_upgrade('cur', False, False, False)
        self.driver_check.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        all_logger.info("查询AT+QFOTAPID默认值")
        self.check_QFOTAPID('test_linux_dfota_07_001')
        mbn = self.get_mbn_list()
        all_logger.info("开始进行反向升级")
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        all_logger.info("开始进行正向升级")
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.compare_mbn_list(mbn)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_002(self):
        """
        AT+QFOTAPID参数设置以及功能测试
        """
        self.check_imei()
        self.check_sftp_url()
        all_logger.info("AT+QFOTAPID参数设置")
        self.check_QFOTAPID('test_linux_dfota_07_002')
        all_logger.info("开始进行反向升级")
        mbn = self.get_mbn_list()
        self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, dl_QFOTAPID=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        all_logger.info("开始进行正向升级")
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.compare_mbn_list(mbn)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_003(self):
        """
        添加APN，AT+QFOTAPID指定APN，FOTA在线升级，期望正常
        """
        self.check_imei()
        self.check_sftp_url()
        all_logger.info("添加APN，AT+QFOTAPID指定APN")
        self.check_QFOTAPID('test_linux_dfota_07_003')
        all_logger.info("开始进行反向升级")
        mbn = self.get_mbn_list()
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        all_logger.info("开始进行正向升级")
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.compare_mbn_list(mbn)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_004(self):
        """
        AT+QFOTAPID指定APN，重启，期望指定APN未变，FOTA在线升级，期望正常
        """
        self.check_imei()
        self.check_sftp_url()
        all_logger.info("AT+QFOTAPID指定APN，重启")
        self.check_QFOTAPID('test_linux_dfota_07_004')
        all_logger.info("开始进行反向升级")
        mbn = self.get_mbn_list()
        self.dfota_upgrade_online('HTTPS', a_b=False)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_b_a_upgrade_check()
        all_logger.info("开始进行正向升级")
        self.dfota_upgrade_online('HTTPS', a_b=True)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        self.dfota_a_b_upgrade_check()
        self.compare_mbn_list(mbn)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_005(self):
        """
        QFOTAPID默认值与网卡拨号同一路apn，进行在线升级，期望升级失败
        """
        self.check_imei()
        time.sleep(5)
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # 加载mbin驱动
            self.check_and_set_pcie_data_interface()
            self.enter_mbim_mode()
            # 检测注网
            self.at_handler.check_network()
            # 拨号
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.extra_ethernet_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.extra_ethernet_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread()
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            self.linux_api.ping_get_connect_status()
            time.sleep(2)
            self.check_sftp_url()
            all_logger.info("设置QFOTAPID与网卡拨号同一路apn")
            self.check_QFOTAPID('test_linux_dfota_07_005')
            all_logger.info("开始进行反向升级")
            self.dfota_upgrade_online('HTTPS', a_b=False, dl_stop=True, case_id=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()    # noqa
            qcm.terminate()    # noqa
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_006(self):
        """
        QFOTAPID默认值与网卡拨号不同路apn，进行在线升级期望升级成功
        """
        self.check_imei()
        time.sleep(5)
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # 加载mbin驱动
            self.check_and_set_pcie_data_interface()
            self.enter_mbim_mode()
            # 检测注网
            self.at_handler.check_network()
            # 拨号
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.extra_ethernet_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.extra_ethernet_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread()
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            self.linux_api.ping_get_connect_status()
            time.sleep(2)
            all_logger.info("设置 QFOTAPID默认值与网卡拨号不同路apn")
            self.check_sftp_url()
            self.check_QFOTAPID('test_linux_dfota_07_006')
            all_logger.info("开始进行反向升级")
            mbn = self.get_mbn_list()
            self.dfota_upgrade_online('HTTPS', a_b=False)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.dfota_b_a_upgrade_check()
            all_logger.info("开始进行正向升级")
            self.dfota_upgrade_online('HTTPS', a_b=True)
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.dfota_a_b_upgrade_check()
            self.compare_mbn_list(mbn)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()   # noqa
            qcm.terminate()    # noqa
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_07_007(self):
        """
        配置合法/不合法参数设置
        """
        all_logger.info("QFOTAPID配置合法/不合法参数设置")
        self.check_QFOTAPID('test_linux_dfota_07_007')

    @startup_teardown()
    def test_linux_dfota_09_001(self):
        """
        QFirehose全擦烧录A版本的工厂版本后，烧录A版本的标准版本，检查基本信息
        """
        exc_type = None
        exc_value = None
        try:
            self.prepare_package()
            self.qfirehose_upgrade('prev', False, True, True)
            self.driver_check.check_usb_driver()
            self.gpio.set_vbat_high_level()
            self.driver.check_usb_driver_dis()
            self.gpio.set_vbat_low_level_and_pwk()
            self.driver.check_usb_driver()
            self.read_poweron_urc()
            self.at_handler.check_network()
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

    @startup_teardown(startup=['init_with_version_a'])
    def test_linux_dfota_09_002(self):
        """
        HTTPS 正向升级：检查Multifota升级串口log
        """
        self.check_sftp_url()
        self.check_imei()
        data = self.dfota_upgrade_online('HTTPS', a_b=True, multifota=True)
        self.dfota_a_b_upgrade_check()
        self.at_handler.check_network()
        all_logger.info('打印debug口信息')
        all_logger.info(data)
        self.check_Multifota(data)

    @startup_teardown(startup=['init_with_version_b'])
    def test_linux_dfota_09_004(self):
        """
        HTTPS 反向升级：检查Multifota升级串口log
        """
        self.check_sftp_url()
        self.check_imei()
        data = self.dfota_upgrade_online('HTTPS', a_b=False, multifota=True)
        self.dfota_b_a_upgrade_check()
        self.at_handler.check_network()
        all_logger.info('打印debug口信息')
        all_logger.info(data)
        self.check_Multifota(data)


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
    w = LinuxDFOTA(**param_dict)
    w.test_linux_dfota_01_001()
    w.test_linux_dfota_01_002()
    w.test_linux_dfota_01_003()
    w.test_linux_dfota_02_001()
    w.test_linux_dfota_02_002()
