import random
import re
import sys
import time

from utils.functions.middleware import Middleware
from utils.logger.logging_handles import all_logger
from utils.cases.windows_laptop_mbim_sar_manager import WindowsLapTopMbimSarManager
import traceback
from utils.functions.decorators import startup_teardown
from utils.exception.exceptions import WindowsLowPowerError
import os
from utils.log import log


class WindowsLapTopMbimSar(WindowsLapTopMbimSarManager):
    @startup_teardown()
    def windows_laptop_mbim_sar_01_000(self):
        """
        笔电未插卡情况下，模块可以进入D3_COLD，刷新设备管理器唤醒正常（没有引脚无法实现掉卡）
        :return:
        """
        """
        self.open_QRCT()
        self.chose_md_port()
        self.list_nv()
        self.read_nv_29619()
        self.read_nv_30007()
        """

        # self.open_WinRT_LTETEST('StartMon')

        self.open_QuectelMbimSarTool()
        self.page_mbim_sar_manager.element_Init_butoon.click()
        self.get_QuectelMbimSarTool_out()
        self.close_QuectelMbimSarTool()

        # self.check_qsclk(0)
        # all_logger.info('打开设备管理器')
        # self.page_devices_manager.open_devices_manager()
        # all_logger.info('关闭设备管理器')
        # self.page_devices_manager.element_devices_close_button().click()
        # time.sleep(1)
        # all_logger.info("点击扫描检测硬件改动")
        # for i in range(10):
        #     self.page_devices_manager.element_scan_devices_icon().click()

        # self.page_main.click_network_icon()
        # self.page_main.element_airplane_mode_button.click_input()

        # self.enable_disable_device(True, "CMIOT USB AT Port*")
        # self.enable_disable_pcie_ports(False, self.pcie_ports)

    @startup_teardown()
    def windows_laptop_mbim_sar_01_001(self):
        """
        烧录工厂版本，备份QCN
        """
        exc_type = None
        exc_value = None
        try:
            # 备份QCN
            # self.QUTS.read_nv("/nv/item_files/modem/mmode/lte_bandpref")
            # self.QUTS.backup_qcn(back_name='qcn_mbim_sar_before_upgrade_')

            all_logger.info("start backup qcn")
            backup_path = os.path.join(os.getcwd(), "QCN_BACKUP", 'windows_laptop_mbim_sar_01_001')
            backup_name = 'qcn_mbim_sar_before_upgrade'
            qcn_file_path = os.path.join(backup_path, backup_name + '.xqcn')
            all_logger.info(qcn_file_path)
            log.backup_qcn(qcn_file_path)
            if os.path.exists(qcn_file_path):
                if os.path.getsize(qcn_file_path) == 0:
                    raise WindowsLowPowerError('backup qcn fail! file size is 0')
                all_logger.info('backup qcn sueecss')
            else:
                raise WindowsLowPowerError('backup qcn fail!')

            # 烧录工厂版本
            self.fw_erase()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_01_002(self):
        """
        1.查询ModemRstLevel默认值
        2.查询Aprstlevel默认值
        3.进行CEFS备份
        4.查询CEFS备份还原次数
        5.查询MBN列表
        (
        1.AT+QCFG="ModemRstLevel"
        2.AT+QCFG="ApRstLevel"
        3.AT+QPRTPARA=1
        4.AT+QPRTPARA=4
        5.AT+QMBNCFG="List"
        )
        """
        exc_type = None
        exc_value = None
        try:
            self.check_dump_mode_value()
            self.check_efs_backup()
            self.check_mbn()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_01_003(self):
        """
        1.开启QRCT查询NV#29619、NV#30007
        注：NV29619 查询默认WCDMA 和LTE Sar值，X55查询Type 482，X6X查询Type 513
        NV#30007 查询默认NR Sar值，Type ID为513
        2.开启QRCT查询NV，查询此时CFUN值
        3.关闭QRCT工具，CFUN0/1切换，确认注网正常
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QRCT()
            self.chose_md_port()
            self.list_nv()
            self.read_nv_29619()
            self.read_nv_30007()
            return_cfun = self.at_handle.send_at("AT+CFUN?", 0.3)
            if '+CFUN: 5' in return_cfun:
                all_logger.info("和预期一致，读取NV时，cfun为5：\r\n{}".format(return_cfun))
            else:
                raise Exception("和预期不一致，读取NV时，cfun不为5：\r\n{}".format(return_cfun))
            self.at_handle.send_at("AT+CFUN=0", 10)
            self.at_handle.send_at("AT+CFUN=1", 10)
            time.sleep(3)
            self.at_handle.check_network()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_001(self):
        """
        1.打开设备管理器->网络适配器
        2.打开Quectel MBIM Sar Tool，Local File Select加载本地Sar NV文件
        """
        exc_type = None
        exc_value = None
        try:
            self.check_mbim_network_card()
            # rtsar_config.config\00029619\00030007
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_002(self):
        """
        1. 启动Quectel MBIM SAR Tool工具，点击“Init”，枚举设备管理器中MBIM设备并建立连接。
        2. 点击“OpenDeviceSevices”，打开MBIM设备服务。
        3.点击“GetIsMbimReady”，确认MBIM设备是否处于正常连接状态。
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_003(self):
        """
        1.查询当前模块是否处于Smart SAR Mode
        点击”GetIsInSmartSarMode”
        2.，查询当前本地SmartSAR NV 的MD5校验值
        点击”GetLocalFileMD5”
        3.若模块当前处于Smart SAR，显示当前生效的FCC和ROW NV的MD5校验值
        点击”GetSmartSarNvMD5”
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()

            all_logger.info("点击GetIsInSmartSarMode按钮")
            self.page_mbim_sar_manager.element_GetIsInSmartSarMode_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "GetIsInSmartSarMode" not in return_value4:
                raise WindowsLowPowerError("初始化失败，点击GetIsInSmartSarMode后未返回GetIsInSmartSarMode：\r\n{}".format(return_value4))

            all_logger.info("点击GetLocalFileMD5按钮")
            self.page_mbim_sar_manager.element_GetLocalFileMD5_butoon.click()
            time.sleep(0.5)
            return_value5 = self.get_QuectelMbimSarTool_out()
            if "GetFileMd5 SUCCESS" not in return_value5:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetLocalFileMD5后未返回GetFileMd5 SUCCESS：\r\n{}".format(return_value5))
            File_Md5_value = ''.join(re.findall(r"MD5=( \w+)", return_value5))
            all_logger.info('File_Md5_value: {}'.format(File_Md5_value))

            all_logger.info("点击GetSmartSarNvMD5按钮")
            self.page_mbim_sar_manager.element_GetSmartSarNvMD5_butoon.click()
            time.sleep(0.5)
            return_value6 = self.get_QuectelMbimSarTool_out()
            if "GetSarMd5Value SUCCESS" not in return_value6:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSmartSarNvMD5后未返回GetSarMd5Value SUCCESS：\r\n{}".format(return_value6))
            Sar_Md5_Value = ''.join(re.findall(r"GetSarMd5Value SUCCESS\(md5=(\w+)", return_value6))
            if Sar_Md5_Value != '00000000000000000000000000000000':
                raise WindowsLowPowerError("默认Sar_Md5_Value异常：查询结果不是00000000000000000000000000000000：\r\n{}".format(Sar_Md5_Value))
            all_logger.info('Sar_Md5_Value: {}'.format(Sar_Md5_Value))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_004(self):
        """
        1.获取当前是否可以进行Smart SAR NV文件的读写操作
        X55点击”GetSmartSarDiagEnable”
        X62点击”GetSarDiagEnable”
        2.设置可进行读写操作
        X55选择Enable, 点击”SetSmartSarDiagEnable”
        X62选择Enable, 点击”SetSarDiagEnable”
        3.获取当前是否可以进行Smart SAR NV文件的读写操作
        X55点击”GetSmartSarDiagEnable”
        X62点击”GetSarDiagEnable”
        4.点击SetSmartSarValue,导入EFS文件
        5.点击SetDeviceReboot
        6. 重复步骤1-2，点击”GetSmartSarValue”,导出Smart EFS文件
        7.使用Beyound Compare与源文件进行对比，验证是否存在差异
        8.检查模块驻网是否正常
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

            self.click_reboot()
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_005(self):
        """
        1.选择本地导出Smart Sar文件路径点击”GetLocalFileMD5”，查询当前导出的文件SmartSAR NV 的MD5校验值。
        2.对比导出后和导入前文件的MD5校验值一致
        3.点击SetSmartSarValue，导出后的文件再导入模组
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击GetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_GetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "SUCCESS" not in return_value7:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSmartSarValue后未返回SUCCESS：\r\n{}".format(return_value7))
            GetSmartSarValue_file_name = ''.join(re.findall(r".*\\(.*_\d+-\d+-\d+_\d+_\d+_\d+)", return_value7))
            if GetSmartSarValue_file_name == '':
                raise WindowsLowPowerError(
                    "获取导出GetSmartSarValue_file_name异常：\r\n{}".format(GetSmartSarValue_file_name))
            else:
                all_logger.info('GetSmartSarValue_file_name: {}'.format(GetSmartSarValue_file_name))

            # GetSmartSarValue_file_path = os.path.join(self.QuectelMbimSarTool_path, "export_nv", GetSmartSarValue_file_name)
            # all_logger.info('GetSmartSarValue_file_path: {}'.format(GetSmartSarValue_file_path))

            self.open_QuectelMbimSarTool(nv_path=self.QuectelMbimSarTool_path, nv_config1_name=GetSmartSarValue_file_name)
            self.init_mbim_sar()

            all_logger.info("点击GetIsInSmartSarMode按钮")
            self.page_mbim_sar_manager.element_GetIsInSmartSarMode_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "GetIsInSmartSarMode" not in return_value8:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetIsInSmartSarMode后未返回GetIsInSmartSarMode：\r\n{}".format(return_value8))

            all_logger.info("点击GetLocalFileMD5按钮")
            self.page_mbim_sar_manager.element_GetLocalFileMD5_butoon.click()
            time.sleep(0.5)
            return_value9 = self.get_QuectelMbimSarTool_out()
            if "GetFileMd5 SUCCESS" not in return_value9:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetLocalFileMD5后未返回GetFileMd5 SUCCESS：\r\n{}".format(return_value9))
            File_Md5_value = ''.join(re.findall(r"MD5= (\w+)", return_value9))
            all_logger.info('File_Md5_value: {}'.format(File_Md5_value))

            all_logger.info("点击GetSmartSarNvMD5按钮")
            self.page_mbim_sar_manager.element_GetSmartSarNvMD5_butoon.click()
            time.sleep(0.5)
            return_value10 = self.get_QuectelMbimSarTool_out()
            if "GetSarMd5Value SUCCESS" not in return_value10:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSmartSarNvMD5后未返回GetSarMd5Value SUCCESS：\r\n{}".format(return_value10))
            Sar_Md5_Value = ''.join(re.findall(r"GetSarMd5Value SUCCESS\(md5=(\w+)", return_value10))
            all_logger.info('Sar_Md5_Value: {}'.format(Sar_Md5_Value))

            if File_Md5_value == Sar_Md5_Value:
                all_logger.info("导出的md5值一致：\r\nGetLocalFileMD5:{}\r\nGetSmartSarNvMD5:{}".format(File_Md5_value, Sar_Md5_Value))
            else:
                raise WindowsLowPowerError("导出的md5值不一致：\r\nGetLocalFileMD5:{}\r\nGetSmartSarNvMD5:{}".format(File_Md5_value, Sar_Md5_Value))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_006(self):
        """
        1.使用QuectelMbimSarTool工具导入Smart TX文件，导入成功后查询模块串口和MBIM是否正常
        2.笔电进行睡眠
        3.睡眠唤醒后查询模块串口和MBIM是否正常
        4.再次导入Smart TX文件
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))
            self.close_QuectelMbimSarTool()

            self.enter_modern_standby()
            time.sleep(60)  # 等待windows恢复正常

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_007(self):
        """
        1.使用QuectelMbimSarTool工具导入Smart TX文件，导入成功后查询模块串口和MBIM是否正常
        2.笔电进行休眠
        3.休眠唤醒后查询模块串口和MBIM是否正常
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))
            self.close_QuectelMbimSarTool()

            self.enter_S3_S4_sleep()
            time.sleep(360)  # 等待windows恢复正常

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_010(self):
        """
        1.导入相同Smart TX文件，期望提示：导入文件相同
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

            all_logger.info("再次点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8:
                all_logger.info("已检测到相同文件提示：\r\n{}".format(return_value8))
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_011(self):
        """
        操作：
        1.导入内容错误的EFS file文件，重启模块
        2.AT+QENG="SERVINGCELL"查询驻网是否正常
        3.导入正常的EFS file文件，重启模块
        4.AT+QENG="SERVINGCELL"查询驻网是否正常
        期望：
        1.期望导入文件错误时模块开机正常
        2.驻网成功
        3.导入正常
        4.驻网正常
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config-Error1.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))
            self.cfun_reset()
            all_logger.info('关闭设备管理器')
            self.page_devices_manager.element_devices_close_button().click()
            self.at_handle.check_network()

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

            self.cfun_reset()
            all_logger.info('关闭设备管理器')
            self.page_devices_manager.element_devices_close_button().click()
            self.at_handle.check_network()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_02_012(self):
        """
        1.导入Smart TX文件
        2.查询当前模块MD5信息，验证导入是否成功
        3.重复操作1~2步5次
        4.导入成功后SetDeviceReboot，重启模组
        """
        for i in range(1, 6):
            all_logger.info("开始导入第{}个文件".format(i))
            exc_type = None
            exc_value = None
            try:
                self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config-Error{}.config".format(i))
                self.init_mbim_sar()
                self.init_nv()

                all_logger.info("点击SetSmartSarValue按钮")
                self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
                time.sleep(0.5)
                return_value7 = self.get_QuectelMbimSarTool_out()
                if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                    pass
                else:
                    raise WindowsLowPowerError(
                        "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))

            except Exception as e:
                all_logger.error(traceback.format_exc())
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                self.close_QuectelMbimSarTool()
                if exc_type and exc_value:
                    raise exc_type(exc_value)
        self.cfun_reset()
        all_logger.info('关闭设备管理器')
        self.page_devices_manager.element_devices_close_button().click()
        self.at_handle.check_network()

    @startup_teardown()
    def windows_laptop_mbim_sar_02_013(self):
        """
        1.使用MbimSmartSarTestTool工具打开SmartSar Diag导入EFS 文件后关闭Diag
        2.打开QXDM使用DM口抓取log
        3.QXDM断开DM口连接
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value7 or "SUCCESS" in return_value7:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value7))
            self.close_QuectelMbimSarTool()

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'windows_laptop_mbim_sar_02_013')
            all_logger.info(f"log_save_path: {log_save_path}")
            self.at_handle.cfun0()
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handle.cfun1()
                self.at_handle.check_network()

                all_logger.info("wait 10 seconds")
                time.sleep(10)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_002(self):
        """
        1.Local File Select，选择本地文件路径，加载本地的传统Sar 4G&5G NV文件
        2.点击”GetLocalFileMD5”，查询当前本地传统SAR NV 的MD5校验值
        3.点击”GetSarNvMD5”,显示当前默认的4G_NV&5G_NV的MD5校验值
        """
        exc_type = None
        exc_value = None
        try:
            print(time.asctime(time.localtime(time.time())))
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619", nv_5g_name="00030007")
            self.init_mbim_sar()

            all_logger.info("点击GetLocalFileMD5按钮")
            self.page_mbim_sar_manager.element_GetLocalFileMD5_Tradition_butoon.click()
            time.sleep(0.5)
            return_value5 = self.get_QuectelMbimSarTool_out()
            if "GetFileMd5 SUCCESS" not in return_value5:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetLocalFileMD5后未返回GetFileMd5 SUCCESS：\r\n{}".format(return_value5))
            # File_Md5_value = ''.join(re.findall(r"MD5=( \w+)", return_value5))
            # all_logger.info('File_Md5_value: {}'.format(File_Md5_value))

            self.page_mbim_sar_manager.element_mbim_sar_outlog.select()
            get_value_by_crtl_c = self.get_value_by_crtl_c()
            File_Md5_4g_value, File_Md5_5g_value = re.findall(r"MD5= (\w+)", get_value_by_crtl_c)
            if not File_Md5_4g_value or not File_Md5_5g_value:
                raise WindowsLowPowerError("获取MD5值失败！\r\n{}".format(get_value_by_crtl_c))
            all_logger.info('\r\nFile_Md5_4g_value:{}\r\nFile_Md5_5g_value:{} '.format(File_Md5_4g_value, File_Md5_5g_value))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_003(self):
        """
        1.点击”GetSarDiagEnable”，获取当前是否可以进行传统SAR EFS文件的读写操作
        2.选择Enable, 点击”SetSarDiagEnable”,设置可进行读写操作。
        3.点击”GetSarDiagEnable”，获取当前是否可以进行传统SAR EFS文件的读写操作
        4. 点击”GetSarValue”,导出默认传统 SAR EFS文件
        5.点击SetSarValue,写入EFS文件
        6.点击SetDeviceReboot，模组重启
        7. 重复步骤 1，2后，点击”GetSmartSarValue”,导出NV文件
        8.使用Beyound Compare与源文件进行对比，验证是否存在差异
        9.检查模块驻网是否正常
        (确认模块加载口以及网卡是否正常
        查询CFUN值以及Modem是否存在重启或者dump
        查询还原次数是否增加)
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619", nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击GetSarValue按钮")
            self.page_mbim_sar_manager.element_GetSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "SUCCESS" not in return_value7:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSmartSarValue后未返回SUCCESS：\r\n{}".format(return_value7))
            self.page_mbim_sar_manager.element_mbim_sar_outlog.select()
            return_sar_files_name = self.get_value_by_crtl_c()
            GetSarValue_4g_file_name, GetSarValue_5g_file_name = re.findall(r".*\\(.*_\d+-\d+-\d+_\d+_\d+_\d+)", return_sar_files_name)
            if not GetSarValue_4g_file_name or not GetSarValue_5g_file_name:
                raise WindowsLowPowerError(
                    "获取导出GetSarValue_file_name异常：\r\n{}".format(return_sar_files_name))
            else:
                all_logger.info('\r\nGetSarValue_4g_file_name: {}\r\nGetSarValue_5g_file_name: {}'.format(GetSarValue_4g_file_name, GetSarValue_5g_file_name))

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))

            self.click_reboot()
            self.at_handle.check_network()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_004(self):
        """
        1.选择导出文件路径点击”GetLocalFileMD5”，查询当前导出的文件传统SAR NV 的MD5校验值
        2.对比导出后和导入前文件的MD5校验值一致
        3.点击SetDeviceReboot，模组重启
        4.选择Enable可进行读写操作。然后点击SetSarValue，将导出的传统Sar文件再次导入
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619", nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击GetLocalFileMD5按钮")
            self.page_mbim_sar_manager.element_GetLocalFileMD5_Tradition_butoon.click()
            time.sleep(0.5)
            return_value5 = self.get_QuectelMbimSarTool_out()
            if "GetFileMd5 SUCCESS" not in return_value5:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetLocalFileMD5后未返回GetFileMd5 SUCCESS：\r\n{}".format(return_value5))
            # File_Md5_value = ''.join(re.findall(r"MD5=( \w+)", return_value5))
            # all_logger.info('File_Md5_value: {}'.format(File_Md5_value))

            self.page_mbim_sar_manager.element_mbim_sar_outlog.select()
            get_Local_value_by_crtl_c = self.get_value_by_crtl_c()
            Local_File_Md5_4g_value, Local_File_Md5_5g_value = re.findall(r"MD5= (\w+)", get_Local_value_by_crtl_c)
            if not Local_File_Md5_4g_value or not Local_File_Md5_5g_value:
                raise WindowsLowPowerError("获取MD5值失败！\r\n{}".format(get_Local_value_by_crtl_c))
            all_logger.info(
                '\r\nLocal_File_Md5_4g_value:{}\r\nLocal_File_Md5_5g_value:{} '.format(Local_File_Md5_4g_value,
                                                                                       Local_File_Md5_5g_value))

            all_logger.info("点击GetSarValue按钮")
            self.page_mbim_sar_manager.element_GetSarValue_butoon.click()
            time.sleep(0.5)
            return_value7 = self.get_QuectelMbimSarTool_out()
            if "SUCCESS" not in return_value7:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSmartSarValue后未返回SUCCESS：\r\n{}".format(return_value7))
            self.page_mbim_sar_manager.element_mbim_sar_outlog.select()
            return_sar_files_name = self.get_value_by_crtl_c()
            GetSarValue_4g_file_name, GetSarValue_5g_file_name = re.findall(r".*\\(.*_\d+-\d+-\d+_\d+_\d+_\d+)",
                                                                            return_sar_files_name)
            if not GetSarValue_4g_file_name or not GetSarValue_5g_file_name:
                raise WindowsLowPowerError(
                    "获取导出GetSarValue_file_name异常：\r\n{}".format(return_sar_files_name))
            else:
                all_logger.info(
                    '\r\nGetSarValue_4g_file_name: {}\r\nGetSarValue_5g_file_name: {}'.format(GetSarValue_4g_file_name,
                                                                                              GetSarValue_5g_file_name))

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))

            self.click_reboot()
            self.at_handle.check_network()

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619", nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击GetSarNvMD5按钮")
            self.page_mbim_sar_manager.element_GetSarNvMD5_butoon.click()
            time.sleep(0.5)
            self.page_mbim_sar_manager.element_GetSarNvMD5_butoon.click()   # 工具BUG第一次必报错，所以点两次
            time.sleep(0.5)
            return_value5 = self.get_QuectelMbimSarTool_out()
            if "GetSarMd5Value SUCCESS" not in return_value5:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSarNvMD5后未返回GetSarMd5Value SUCCESS：\r\n{}".format(return_value5))

            self.page_mbim_sar_manager.element_mbim_sar_outlog.select()
            get_SarNv_value_by_crtl_c = self.get_value_by_crtl_c()
            SarNv_File_Md5_4g_value = ""
            SarNv_File_Md5_5g_value = ""
            names_nv = re.findall(r"md5=(\w+)", get_SarNv_value_by_crtl_c)
            if len(names_nv) == 2:
                SarNv_File_Md5_4g_value, SarNv_File_Md5_5g_value = names_nv
            elif len(names_nv) == 3:
                _, SarNv_File_Md5_4g_value, SarNv_File_Md5_5g_value = names_nv
            elif len(names_nv) == 4:
                _, _, SarNv_File_Md5_4g_value, SarNv_File_Md5_5g_value = names_nv

            if not SarNv_File_Md5_4g_value or not SarNv_File_Md5_5g_value:
                raise WindowsLowPowerError("获取MD5值失败！\r\n{}".format(get_SarNv_value_by_crtl_c))
            all_logger.info(
                '\r\nSarNv_File_Md5_4g_value:{}\r\nSarNv_File_Md5_5g_value:{} '.format(SarNv_File_Md5_4g_value,
                                                                                       SarNv_File_Md5_5g_value))

            if SarNv_File_Md5_4g_value == Local_File_Md5_4g_value and SarNv_File_Md5_5g_value == Local_File_Md5_5g_value:
                pass
            else:
                raise WindowsLowPowerError("MD5值不一致：\r\nLocal:{};{}\r\nsar:{};{}".format(Local_File_Md5_4g_value, Local_File_Md5_5g_value, SarNv_File_Md5_4g_value, SarNv_File_Md5_5g_value))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_007(self):
        """
        1.使用QuectelMbimSarTool工具导入MD5值不同的NV文件，导入成功后重启模组，查询模块串口和MBIM是否正常
        2.笔电进行睡眠
        3.睡眠唤醒后查询模块串口和MBIM是否正常
        """
        exc_type = None
        exc_value = None
        try:
            self.check_efs_backup()
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))
            self.close_QuectelMbimSarTool()

            self.enter_modern_standby()
            time.sleep(60)  # 等待windows恢复正常

            self.at_handle.check_network()
            self.check_mbim_network_card()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_008(self):
        """
        1.使用QuectelMbimSarTool工具导入MD5值不同的NV文件，导入成功后查询模块串口和MBIM是否正常
        2.笔电进行休眠
        3.休眠唤醒后查询模块串口和MBIM是否正常
        """
        exc_type = None
        exc_value = None
        try:
            self.check_efs_backup()
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))
            self.close_QuectelMbimSarTool()

            self.enter_S3_S4_sleep()
            time.sleep(360)  # 等待windows恢复正常

            self.at_handle.check_network()
            self.check_mbim_network_card()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_011(self):
        """
        1.导入EFS file文件，重启模块
        2.通过FWU工具进行版本升级
        3.升级后模块版本信息查询正常
        4.驻网正常
        """
        exc_type = None
        exc_value = None
        try:
            self.check_efs_backup()

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))
            self.close_QuectelMbimSarTool()
            self.fw_normal()
            self.at_handle.check_network()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_013(self):
        """
        1.导入EFS file文件，重启模块
        2.查询WCDMA、LTE Sar和5G值
        3.重复操作1~2步5次
        """
        for i in range(1, 6):
            all_logger.info("开始导入第{}个文件".format(i))
            exc_type = None
            exc_value = None
            try:
                self.open_QuectelMbimSarTool(nv_path=self.nv_path,  nv_4g_name="00029619-ERROR{}".format(i), nv_5g_name="00030007-ERROR{}".format(i))
                self.init_mbim_sar()
                self.init_nv()

                all_logger.info("点击SetSarValue按钮")
                self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
                time.sleep(0.5)
                return_value8 = self.get_QuectelMbimSarTool_out()
                if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                    pass
                else:
                    raise WindowsLowPowerError(
                        "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))

            except Exception as e:
                all_logger.error(traceback.format_exc())
                all_logger.info(e)
                exc_type, exc_value, exc_tb = sys.exc_info()
            finally:
                self.close_QuectelMbimSarTool()
                if exc_type and exc_value:
                    raise exc_type(exc_value)
        self.cfun_reset()
        time.sleep(60)
        all_logger.info('关闭设备管理器')
        self.page_devices_manager.element_devices_close_button().click()
        self.at_handle.check_network()

    @startup_teardown()
    def windows_laptop_mbim_sar_03_014(self):
        """
        1.进行CEFS备份，查询备份还原次数
        2.导入内容错误的EFS file文件后重启模块(网络需设置为对应异常NV的制式：29619对应WCDMA和LTE，30007对应NR)
        3.查询WCDMA和LTE Sar值
        4.AT+QENG="SERVINGCELL"查询驻网是否正常
        """
        exc_type = None
        exc_value = None
        try:
            self.check_efs_backup()

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619-ERROR1",
                                         nv_5g_name="00030007-ERROR1")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))

            self.cfun_reset()
            time.sleep(60)
            all_logger.info('关闭设备管理器')
            self.page_devices_manager.element_devices_close_button().click()
            self.at_handle.check_network()

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_03_015(self):
        """
        1.使用QuectelMbimSarTool工具打开传统Sar Diag导入EFS 文件后关闭Diag
        2.打开QXDM使用DM口抓取log
        3.QXDM断开DM口连接
        """
        exc_type = None
        exc_value = None
        try:
            self.check_efs_backup()

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()
            self.init_nv()

            all_logger.info("点击SetSarValue按钮")
            self.page_mbim_sar_manager.element_SetSarValue_butoon.click()
            time.sleep(0.5)
            return_value8 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value8 or "SUCCESS" in return_value8:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value8))
            self.close_QuectelMbimSarTool()

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'windows_laptop_mbim_sar_02_015')
            all_logger.info(f"log_save_path: {log_save_path}")
            self.at_handle.cfun0()
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handle.cfun1()
                self.at_handle.check_network()

                all_logger.info("wait 10 seconds")
                time.sleep(10)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_04_001(self):
        """
        1.使用QuectelMbimSarTool工具设置SetSarIndex为1
        2.点击GetSarIndex，查询Index值
        3.使用QRCT工具查询WCDMA和LTE Sar和5G Sar值
        (Index重启不保存，范围为0-8，建议随意取值测试)
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()

            self.page_mbim_sar_manager.element_SetSarIndex_number_butoon.select('1')

            all_logger.info("点击SetSarIndex按钮")
            self.page_mbim_sar_manager.element_SetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "SetSarIndex SUCCESS" in return_value4:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSarIndex后未返回SetSarIndex SUCCESS：\r\n{}".format(return_value4))
            sar_index = ''.join(re.findall(r"SetSarIndex SUCCESS\(level = (\d+)", return_value4))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的sar index不是1")

            all_logger.info("点击GetSarIndex按钮")
            self.page_mbim_sar_manager.element_GetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value3 = self.get_QuectelMbimSarTool_out()
            if "GetSarIndex SUCCESS" in return_value3:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSarIndex后未返回GetSarIndex SUCCESS：\r\n{}".format(return_value3))
            sar_index = ''.join(re.findall(r"GetSarIndex SUCCESS\(index = (\d+)", return_value3))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的sar index不是1")
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_04_002(self):
        """
        1.使用QuectelMbimSarTool工具设置SetSarIndex为2
        2.重启模块
        3.使用QRCT查询WCDMA和LTE Sar和5G Sar值
        (Index重启不保存，范围为0-8，建议随意取值测试)
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()

            self.page_mbim_sar_manager.element_SetSarIndex_number_butoon.select('1')

            all_logger.info("点击SetSarIndex按钮")
            self.page_mbim_sar_manager.element_SetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "SetSarIndex SUCCESS" in return_value4:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSarIndex后未返回SetSarIndex SUCCESS：\r\n{}".format(return_value4))
            sar_index = ''.join(re.findall(r"SetSarIndex SUCCESS\(level = (\d+)", return_value4))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的sar index不是1")

            all_logger.info("点击GetSarIndex按钮")
            self.page_mbim_sar_manager.element_GetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value3 = self.get_QuectelMbimSarTool_out()
            if "GetSarIndex SUCCESS" in return_value3:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSarIndex后未返回GetSarIndex SUCCESS：\r\n{}".format(return_value3))
            sar_index = ''.join(re.findall(r"GetSarIndex SUCCESS\(index = (\d+)", return_value3))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的sar index不是1")

            self.cfun_reset()
            time.sleep(60)
            all_logger.info('关闭设备管理器')
            self.page_devices_manager.element_devices_close_button().click()
            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_04_003(self):
        """
        1.使用QuectelMbimSarTool工具设置SetSarIndex为8
        2.查询注网是否正常
        (Index重启不保存，范围为0-8，建议随意取值测试)
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()

            self.page_mbim_sar_manager.element_SetSarIndex_number_butoon.select('8')

            all_logger.info("点击SetSarIndex按钮")
            self.page_mbim_sar_manager.element_SetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "SetSarIndex SUCCESS" in return_value4:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSarIndex后未返回SetSarIndex SUCCESS：\r\n{}".format(return_value4))
            sar_index = ''.join(re.findall(r"SetSarIndex SUCCESS\(level = (\d+)", return_value4))
            if sar_index != '8':
                raise WindowsLowPowerError("异常！返回的sar index不是8")

            all_logger.info("点击GetSarIndex按钮")
            self.page_mbim_sar_manager.element_GetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value3 = self.get_QuectelMbimSarTool_out()
            if "GetSarIndex SUCCESS" in return_value3:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSarIndex后未返回GetSarIndex SUCCESS：\r\n{}".format(return_value3))
            sar_index = ''.join(re.findall(r"GetSarIndex SUCCESS\(index = (\d+)", return_value3))
            if sar_index != '8':
                raise WindowsLowPowerError("异常！返回的sar index不是8")

            self.at_handle.check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_04_004(self):
        """
        1.开启Smart TX导入功能
        2.导入Smart TX文件
        3.点击GetIsInSarMode查询当前Smart Sar模式是否开启
        """
        exc_type = None
        exc_value = None
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path,  nv_config1_name="rtsar_config.config")
            self.init_mbim_sar()

            all_logger.info("点击SetSarDiagEnable按钮")
            self.page_mbim_sar_manager.element_SetSarDiagEnable_butoon.click()
            time.sleep(0.5)
            return_value1 = self.get_QuectelMbimSarTool_out()
            if "SetSarEnable SUCCESS" not in return_value1:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSarDiagEnable后未返回SetSarDiagEnable SUCCESS：\r\n{}".format(return_value1))

            all_logger.info("点击SetSmartSarValue按钮")
            self.page_mbim_sar_manager.element_SetSmartSarValue_butoon.click()
            time.sleep(0.5)
            return_value2 = self.get_QuectelMbimSarTool_out()
            if "is the same as that of the file in the module" in return_value2 or "SUCCESS" in return_value2:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSmartSarValue后未返回SetSmartSarValue SUCCESS：\r\n{}".format(return_value2))

            all_logger.info("点击GetIsInSmartSarMode按钮")
            self.page_mbim_sar_manager.element_GetIsInSmartSarMode_butoon.click()
            time.sleep(0.5)
            return_value3 = self.get_QuectelMbimSarTool_out()
            if "Enable" not in return_value3:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetIsInSmartSarMode后未返回Enable：\r\n{}".format(return_value3))
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_05_001(self):
        """
        1.运行Command Prompt(cmd)
        2.进入winltetest.exe路径下中执行WinRT_LTETEST.exe GetMcc
        """
        exc_type = None
        exc_value = None
        try:
            # 查询当前SIM卡运营商信息、模块信息
            query_operator_id, query_operator_name = self.get_operator()
            query_gmi = self.get_gmi()
            query_ati = self.get_ati()
            return_value = self.open_WinRT_LTETEST("GetMcc")
            network_provider_id = ''.join(re.findall(r"network provider id is (\d+)", return_value))
            if not network_provider_id or query_operator_id != network_provider_id:
                raise WindowsLowPowerError("返回network provider id异常！\r\n{}、{}".format(return_value, query_operator_id))
            network_provider_name = ''.join(re.findall(r"network provider name is (.*)", return_value))
            if not network_provider_name or query_operator_name != network_provider_name:
                raise WindowsLowPowerError("返回network provider name异常!\r\n{}、{}".format(return_value, query_operator_name))
            modem_manufacture_name = ''.join(re.findall(r"Modem manufacture name is (.*)", return_value))
            if not modem_manufacture_name or query_gmi != modem_manufacture_name:
                raise WindowsLowPowerError("返回Modem manufacture name异常!\r\n{}、{}".format(return_value, query_gmi))
            modem_model = ''.join(re.findall(r"Modem model is (.*)", return_value))
            if not modem_model or self.mbim_pcie_driver_name != modem_model:
                raise WindowsLowPowerError("返回Modem model异常!\r\n{}、{}".format(return_value, self.mbim_pcie_driver_name))
            modem_firmware = ''.join(re.findall(r"Modem firmware is (.*)", return_value))
            if not modem_firmware or query_ati != modem_firmware:
                raise WindowsLowPowerError("返回Modem firmware异常!\r\n{}、{}".format(return_value, query_ati))
            all_logger.info("{}、{}、{}、{}、{}".format(network_provider_id, network_provider_name, modem_manufacture_name, modem_model, modem_firmware))

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_05_002(self):
        """
        1.执行WinRT_LTETEST.exe GetSar
        2.执行WinRT_LTETEST.exe EnableSar
        3.执行WinRT_LTETEST.exe DisableSar
        """
        exc_type = None
        exc_value = None
        try:
            # 查询当前SIM卡运营商信息、模块信息
            self.open_WinRT_LTETEST("EnableSar")
            return_value1 = self.open_WinRT_LTETEST("GetSar")
            if 'Backoff is Enabled' not in return_value1:
                raise WindowsLowPowerError("开启Sar异常！{}".format(return_value1))
            return_value2 = self.open_WinRT_LTETEST("EnableSar")
            if 'Sar enable success' not in return_value2:
                raise WindowsLowPowerError("开启Sar异常！{}".format(return_value2))
            return_value3 = self.open_WinRT_LTETEST("DisableSar")
            if 'Sar Disable success' not in return_value3:
                raise WindowsLowPowerError("开启Sar异常！{}".format(return_value3))
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_05_003(self):
        """
        1.执行WinRT_LTETEST.exe GetSar,查询Index默认值
        2.执行WinRT_LTETEST.exe SetIndex 1
        3.使用QuectelMbimSarTool工具点击GetSarIndex，查询Index
        4.使用QuectelMbimSarTool 设置SetSarIndex 8
        5.执行WinRT_LTETEST.exe GetSar,查询Index值
        6.执行WinRT_LTETEST.exe SetIndex 9
        7.重启模组，查询Index
        (重启不保存，Index范围为0-8，建议随意取值测试)
        """
        exc_type = None
        exc_value = None
        try:

            # 临时调试
            # self.open_WinRT_LTETEST("SetIndex 0")
            return_value1 = self.open_WinRT_LTETEST("GetSar")
            if 'BackoffIndex 0' not in return_value1:
                raise WindowsLowPowerError("异常！默认index不是0\r\n{}".format(return_value1))
            return_value2 = self.open_WinRT_LTETEST("SetIndex 1")
            if 'success' not in return_value2:
                raise WindowsLowPowerError("设置index异常！\r\n{}".format(return_value2))

            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()

            all_logger.info("点击GetSarIndex按钮")
            self.page_mbim_sar_manager.element_GetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value3 = self.get_QuectelMbimSarTool_out()
            if "GetSarIndex SUCCESS" in return_value3:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetSarIndex后未返回GetSarIndex SUCCESS：\r\n{}".format(return_value3))
            sar_index = ''.join(re.findall(r"GetSarIndex SUCCESS\(index = (\d+)", return_value3))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的sar index不是1")

            self.page_mbim_sar_manager.element_SetSarIndex_number_butoon.select('8')

            all_logger.info("点击SetSarIndex按钮")
            self.page_mbim_sar_manager.element_SetSarIndex_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "SetSarIndex SUCCESS" in return_value4:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetSarIndex后未返回SetSarIndex SUCCESS：\r\n{}".format(return_value4))
            sar_index = ''.join(re.findall(r"SetSarIndex SUCCESS\(level = (\d+)", return_value4))
            if sar_index != '8':
                raise WindowsLowPowerError("异常！返回的sar index不是8")

            return_value5 = self.open_WinRT_LTETEST("GetSar")
            if 'BackoffIndex 8' not in return_value5:
                raise WindowsLowPowerError("异常！默认index不是8\r\n{}".format(return_value5))

            # Antenna backoff index only valid from 0 to 8
            return_value6 = self.open_WinRT_LTETEST("SetIndex 9")
            if 'Antenna backoff index only valid from 0 to 8' not in return_value6:
                raise WindowsLowPowerError("异常！设置index 9未返回正确提示\r\n{}".format(return_value6))

            self.cfun_reset()
            time.sleep(60)
            all_logger.info('关闭设备管理器')
            self.page_devices_manager.element_devices_close_button().click()
            self.at_handle.check_network()

            return_value7 = self.open_WinRT_LTETEST("GetSar")
            if 'BackoffIndex 0' not in return_value7:
                raise WindowsLowPowerError("异常！默认index不是0\r\n{}".format(return_value7))
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_QuectelMbimSarTool()
            os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def windows_laptop_mbim_sar_05_004(self):
        """
        1.使用QuectelMbimSarTool 点击GetDprLevel 查询默认值
        2.设置SetDprLevel 2 重启模块
        3.查询GetDprLevel
        4. 设置SetDprLevel 8 重启模块
        5.查询GetDprLevel
        (重启保存，Level参数范围1-8，建议随意取值测试)
        """
        try:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()

            all_logger.info("点击GetDprLevel按钮")
            self.page_mbim_sar_manager.element_GetDprLevel_butoon.click()
            time.sleep(0.5)
            return_value1 = self.get_QuectelMbimSarTool_out()
            if "GetSarDprLevel SUCCESS" in return_value1:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击GetDprLevel后未返回GetSarDprLevel SUCCESS：\r\n{}".format(return_value1))
            Level_index = ''.join(re.findall(r"GetSarDprLevel SUCCESS. DPR Level = (\d+)", return_value1))
            if Level_index != '1':
                raise WindowsLowPowerError("异常！返回的Level index不是1")

            for i in range(1, 3):
                all_logger.info("开始第{}次随机SetDprLevel测试".format(i))

                self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                             nv_5g_name="00030007")
                self.init_mbim_sar()

                range_num = str(int(random.random()*7+1))
                all_logger.info("本次随机数为{}".format(range_num))

                self.page_mbim_sar_manager.element_SetDprLevel_number_butoon.select(range_num)

                all_logger.info("点击SetDprLevel按钮")
                self.page_mbim_sar_manager.element_SetDprLevel_butoon.click()
                time.sleep(0.5)
                return_value2 = self.get_QuectelMbimSarTool_out()
                if "SetSarDprLevel SUCCESS" in return_value2:
                    pass
                else:
                    raise WindowsLowPowerError(
                        "初始化失败，点击SetDprLevel后未返回SetSarDprLevel SUCCESS：\r\n{}".format(return_value2))
                sar_index = ''.join(re.findall(r"SetSarDprLevel SUCCESS\.Level = (\d+)", return_value2))
                if sar_index != range_num:
                    raise WindowsLowPowerError("异常！返回的SetSarDprLevel不是{}".format(range_num))

                self.cfun_reset()
                time.sleep(60)
                all_logger.info('关闭设备管理器')
                self.page_devices_manager.element_devices_close_button().click()
                self.at_handle.check_network()

                all_logger.info("点击GetDprLevel按钮")
                self.page_mbim_sar_manager.element_GetDprLevel_butoon.click()
                time.sleep(0.5)
                return_value3 = self.get_QuectelMbimSarTool_out()
                if "GetSarDprLevel SUCCESS" in return_value3:
                    pass
                else:
                    raise WindowsLowPowerError(
                        "初始化失败，点击GetDprLevel后未返回GetSarDprLevel SUCCESS：\r\n{}".format(return_value3))
                sar_index = ''.join(re.findall(r"GetSarDprLevel SUCCESS. DPR Level = (\d+)", return_value3))
                if sar_index != range_num:
                    raise WindowsLowPowerError("异常！返回的GetSarDprLevel 不是{}".format(range_num))
        finally:
            self.open_QuectelMbimSarTool(nv_path=self.nv_path, nv_4g_name="00029619",
                                         nv_5g_name="00030007")
            self.init_mbim_sar()
            self.page_mbim_sar_manager.element_SetDprLevel_number_butoon.select('1')

            all_logger.info("点击SetDprLevel按钮")
            self.page_mbim_sar_manager.element_SetDprLevel_butoon.click()
            time.sleep(0.5)
            return_value4 = self.get_QuectelMbimSarTool_out()
            if "SetSarDprLevel SUCCESS" in return_value4:
                pass
            else:
                raise WindowsLowPowerError(
                    "初始化失败，点击SetDprLevel后未返回SetSarDprLevel SUCCESS：\r\n{}".format(return_value4))
            sar_index = ''.join(re.findall(r"SetSarDprLevel SUCCESS\.Level = (\d+)", return_value4))
            if sar_index != '1':
                raise WindowsLowPowerError("异常！返回的SetSarDprLevel不是1:\r\nreturn_value:{}\r\nsar_index:{}".format(return_value4, sar_index))
            self.close_QuectelMbimSarTool()
            os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()

    @startup_teardown()
    def windows_laptop_mbim_sar_05_005(self):
        """
        1.执行WinRT_LTETEST.exe StartMon，监测数据传输
        2.存在数传时，期望返回Transmission state change monitoring startedwwan is transmitting
        不存在数传时，期望返回Transmission state change monitoring startedwwan is not transmitting
        """
        try:
            self.mbim_disconnect_and_check()
            self.open_WinRT_LTETEST_startmon()

            self.mbim_connect_and_check()
            self.open_WinRT_LTETEST_startmon(True)
        finally:
            self.close_QuectelMbimSarTool()
            os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
            self.mbim_disconnect_and_check()
        """
        E:\Auto\Tools\MBIM_SAR\MSFT-SAR-Tool>WinRT_LTETEST.exe StartMon
        Hello, http://aka.ms/cppwinrt!
        Tool version : Feb  6 2020
        Transmission state change monitoring started
        wwan is transmitting
        wwan is transmitting
        wwan is transmitting
        wwan is not transmitting
        wwan is transmitting
        wwan is not transmitting
        wwan is transmitting
        wwan is transmitting
        wwan is not transmitting
        wwan is transmitting
        wwan is not transmitting

        """


if __name__ == '__main__':
    params_dict = {
        "at_port": 'COM3',
        "dm_port": 'COM5',
        "mbim_pcie_driver_name": 'Quectel RM520NGLAP #12',
        "QuectelMbimSarTool_path": r"E:\Auto\Tools\MBIM_SAR\SDX62\QuectelMbimSarTool_X62_V1.0.0.6",
        "WinRT_LTETEST_path": r"E:\Auto\Tools\MBIM_SAR\MSFT-SAR-Tool",
        "nv_path": r"E:\Auto\Tools\SDX62_SAR",
        "firmware_path": r"\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX6X\RM520NGLAP\Release\RM520NGLAPR01A04M4G_01.001.01.001_V01",
    }
    # 18110921823
    # 13225513715
    test = WindowsLapTopMbimSar(**params_dict)
    test.windows_laptop_mbim_sar_01_001()  # QXDM 待优化 OK
    # test.windows_laptop_mbim_sar_01_002()
    # test.windows_laptop_mbim_sar_02_001()  #
    # test.windows_laptop_mbim_sar_02_002()
    # test.windows_laptop_mbim_sar_02_003()
    # test.windows_laptop_mbim_sar_02_004()
    # test.windows_laptop_mbim_sar_02_005()
    # test.windows_laptop_mbim_sar_02_006()  # 待实现 OK
    # test.windows_laptop_mbim_sar_02_007()  # 待实现 OK
    # test.windows_laptop_mbim_sar_02_010()
    # test.windows_laptop_mbim_sar_02_011()
    # test.windows_laptop_mbim_sar_02_012()
    # test.windows_laptop_mbim_sar_02_013()  # QXDM 待优化 OK
    # test.windows_laptop_mbim_sar_03_002()
    # test.windows_laptop_mbim_sar_03_003()
    # test.windows_laptop_mbim_sar_03_004()
    # test.windows_laptop_mbim_sar_03_007()  # 待实现 OK
    # test.windows_laptop_mbim_sar_03_008()  # 待实现 OK
    # test.windows_laptop_mbim_sar_03_011()  # 升级
    # test.windows_laptop_mbim_sar_03_013()
    # test.windows_laptop_mbim_sar_03_014()
    # test.windows_laptop_mbim_sar_03_015()  # QXDM 待优化 OK
    # test.windows_laptop_mbim_sar_04_001()
    # test.windows_laptop_mbim_sar_04_002()
    # test.windows_laptop_mbim_sar_04_003()
    # test.windows_laptop_mbim_sar_04_004()
    # test.windows_laptop_mbim_sar_05_001()
    # test.windows_laptop_mbim_sar_05_002()
    # test.windows_laptop_mbim_sar_05_003()
    # test.windows_laptop_mbim_sar_05_004()
    # test.windows_laptop_mbim_sar_05_005()
