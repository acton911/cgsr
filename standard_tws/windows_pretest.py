import re
import sys
import time
from utils.functions.decorators import startup_teardown
from utils.cases.windows_pretest_manager import WindowsPretestManager
from utils.functions.debug_exec import DebugPort
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import PretestError
import traceback
from utils.functions.middleware import Middleware
from utils.log import log
import os


class WindowsPretest(WindowsPretestManager):

    @startup_teardown()
    def test_windows_pretest_01_001(self):
        """
        检查cefs只在工厂版本配置，标准版本不会包含
        """
        self.copy_firmware()
        self.unzip_firmware()
        self.check_cefs_bin()

    @startup_teardown()
    def test_windows_pretest_01_002(self):
        """
        擦除所有分区后
        QFIL工具Firehose方式升级工厂版本并确认cefs.mbn下载成功
        """
        self.pretest_upgrade_erase()

    @startup_teardown()
    def test_windows_pretest_01_003(self):
        exc_type = None
        exc_value = None
        try:
            self.switch_laptop_urc()
            time.sleep(2)
            self.at_handler.check_qtest_dump()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
            self.force_restart()
        finally:
            if exc_type and exc_value:
                all_logger.error(f"exc_type:{exc_type} \n exc_value:{exc_value}")
                raise exc_type(exc_value)

    @startup_teardown()
    def test_windows_pretest_01_004(self):
        """
        擦除所有分区后
        FW工具Firehose方式升级工厂版本并确认cefs.mbn下载成功
        """
        self.pretest_upgrade_erase()

    @startup_teardown()
    def test_windows_pretest_01_005(self):
        """
        开机后USB刷新次数和加载时间确认
        """
        exc_type = None
        exc_value = None
        debug_port = DebugPort(self.debug_port)
        debug_port.setDaemon(True)
        debug_port.start()
        try:
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.check_urc()
            self.at_handler.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            if exc_type and exc_value:
                all_logger.error(f"exc_type:{exc_type} \n exc_value:{exc_value}")
                debug_port.close_debug()
                raise exc_type(exc_value)
            all_logger.info("wait 30 seconds wait USB_STATE")
            time.sleep(30)  # 等待USB_STATE变化
            usb_state = debug_port.exec_command("dmesg | grep USB_STATE")
            debug_port.close_debug()
            if len(re.findall(r"CONFIGURED", usb_state)) > 1:
                raise PretestError("第二次重启模块dmesg | grep USB_STATE出现多次CONFIGURED")

    @startup_teardown()
    def test_windows_pretest_01_006(self):
        """
        确认版本号及USB口不正常通信不会跳口
        """
        self.at_handler.check_version(self.revision, self.sub_edition)
        self.check_modem_port_connectivity()

    @startup_teardown()
    def test_windows_pretest_01_007(self):
        """
        确认MBN自动激活默认开启
        """
        self.get_auto_sel()

    @startup_teardown()
    def test_windows_pretest_01_008(self):
        """
        确认版本默认网卡类型正确(必须擦除rawdata分区后确认默认值)
        """
        self.at_handler.check_default_dial_mode()

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_windows_pretest_01_009(self):
        """
        确认版本默认网卡类型正确(必须擦除rawdata分区后确认默认值)
        """
        self.at_handler.check_default_dial_mode_mbim()

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_windows_pretest_01_010(self):
        self.at_handler.set_cgdcont(None)
        self.at_handler.send_at("AT+CFUN=0", 15)
        all_logger.info('wait 5 seconds')
        time.sleep(5)
        self.at_handler.send_at("AT+CFUN=1", 15)
        self.at_handler.check_network()
        self.at_handler.set_cgdcont('123')
        self.at_handler.send_at("AT+CFUN=0", 15)
        all_logger.info('wait 5 seconds')
        time.sleep(5)
        self.at_handler.send_at("AT+CFUN=1", 15)
        self.at_handler.check_network()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_pretest_02_005(self):
        """
        Cat X检查
        """
        log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_windows_pretest_02_005')
        all_logger.info(f"log_save_path: {log_save_path}")
        self.at_handler.cfun0()
        with Middleware(log_save_path=log_save_path) as m:
            # 业务逻辑
            self.at_handler.cfun1()
            self.at_handler.check_network()

            all_logger.info("wait 60 seconds")
            time.sleep(60)

            # 停止抓Log
            log.stop_catch_log_and_save(m.log_save_path)
            log_n, log_p = m.find_log_file()
            qdb_n, qdb_p = m.find_qdb_file()

            # 发送本地Log文件
            message_types = {"LOG_PACKET": ["0xB821"]}
            interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                       "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
            data = log.load_log_from_remote(log_p, qdb_p, message_types, interested_return_filed)
            all_logger.info(data)

            # TODO: 优化此处UE能力判断
            ue_CategoryDL = "ue-CategoryDL-r12"
            ue_CategoryUL = "ue-CategoryUL-r12"
            dl_256QAM_r12 = "dl-256QAM-r12 supported"
            if ue_CategoryDL in repr(data) and ue_CategoryUL in repr(data) and dl_256QAM_r12 in repr(data):
                all_logger.info("UE 能力检查正常")
            else:
                raise PretestError("UE 能力检查异常")

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_windows_pretest_02_008(self):
        """
        确认任意某张卡任意APN均可注网
        """
        self.at_handler.bound_network("NSA")

    @startup_teardown()
    def test_windows_pretest_7(self):
        """
        Windows下Manufacturer/Product检查
        """
        self.get_usb_view_info()

    @startup_teardown()
    def test_windows_pretest_8(self):
        """
        Windows下VID/PID/REV/MI检查
        """
        self.check_pid_vid_rev_mi()
        self.at_handler.check_usb_default_id()


if __name__ == '__main__':
    param_dict = {
        'at_port': 'COM10',
        'dm_port': 'COM7',
        'modem_port': 'COM6',
        'debug_port': 'COM4',
        'vid_pid_rev': r'USB\VID_2C7C&PID_0800&REV_0414&MI_02',  # 填写
        'revision': 'RG500QEAAAR11A06M4G',  # 下发version_name参数解析
        'sub_edition': 'V01',  # 下发version_name参数解析
        'fw_download_path': r"C:\FW_Download_And_Format_V5.1.1",  # 填写
        'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55'
                         r'\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A06M4G_01.001V01.01.001V01',
    }
    w = WindowsPretest(**param_dict)
    # w.test_windows_pretest_01_001()
    # w.test_windows_pretest_01_002()
    # w.test_windows_pretest_01_003()
    # w.test_windows_pretest_01_004()
    # w.test_windows_pretest_01_005()
    # w.test_windows_pretest_01_006()
    # w.test_windows_pretest_01_007()
    # w.test_windows_pretest_01_008()
    # w.test_windows_pretest_02_008()
