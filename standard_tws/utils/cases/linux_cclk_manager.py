import re
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import CCLKError
from utils.functions.gpio import GPIO
from utils.functions.qfirehose import QFirehose
from utils.functions.qfil import QFIL
from utils.functions.qfil import QFILError


class LinuxCCLKManager:

    def __init__(self, at_port, dm_port, firmware_path, factory, package_name, ati, csub):
        self.at_port = at_port
        self.dm_port = dm_port
        self.firmware_path = firmware_path
        self.factory = factory
        self.ati = ati
        self.csub = csub
        self.driver = DriverChecker(at_port, dm_port)
        self.at_handler = ATHandle(at_port)
        self.factory_flag = factory  # 是否进行全擦工厂升级
        self.package_name = package_name
        self.gpio = GPIO()
        self.erase = True if factory else False


    # linux自定义升级
    def qfirehose_without_power_on(self):
        qfirehose = QFirehose(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                                       factory=self.factory, ati=self.ati, csub=self.csub,
                                       package_name=self.package_name)
        qfirehose.check_package()  # 首先检查版本包是否已存在
        try:
            qfirehose.qfirehose_upgrade()  # 如果升级失败，再来一次
        except Exception as e:
            if '紧急下载模式' in str(e):  # 如果模块处于紧急下载模式，则先拉低powerkey
                all_logger.info('RM模块处于紧急下载模式，拉低powerkey后升级')
                self.gpio.set_pwk_low_level()
            qfirehose.qfirehose_upgrade()
            self.gpio.set_pwk_high_level()


    # windows自定义升级
    def qfil_with_power_on(self):
        qfil = QFIL(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                         factory=self.factory, ati=self.ati, csub=self.csub)
        try:
            # before_upgrade_ports = qfil.ports()  # 获取端口列表
            for i in range(3):
                try:
                    if qfil.copy_and_unzip_firmware():  # 下载解压固件
                        break
                except Exception as e:
                    all_logger.info(e)
            else:
                raise QFILError('三次下载解压固件失败')
            qfil.copy_qsaharaserver_and_fhloader()  # 复制QSaharaServer.exe和fh_loader.exe到版本包路径，便于后续处理
            qfil.switch_edl_mode()  # 切换紧急下载模式

            qfil.load_programmer()  # QSaharaServer.exe load programmer
            if self.erase:  # erase all flash
                qfil.erase_with_xml()
                qfil.erase_all()

            qfil.load_package()  # 升级
            qfil.load_patch()
            qfil.set_start_partition()
            qfil.reset_module()  # 重启
        except Exception as e:
            if '紧急下载模式' in str(e):  # 如果模块处于紧急下载模式，则先拉低powerkey
                all_logger.info('RM模块处于紧急下载模式，拉低powerkey后升级')
                self.gpio.set_pwk_low_level()
            # before_upgrade_ports = qfil.ports()  # 获取端口列表
            for i in range(3):
                try:
                    if qfil.copy_and_unzip_firmware():  # 下载解压固件
                        break
                except Exception as e:
                    all_logger.info(e)
            else:
                raise QFILError('三次下载解压固件失败')
            qfil.copy_qsaharaserver_and_fhloader()  # 复制QSaharaServer.exe和fh_loader.exe到版本包路径，便于后续处理
            qfil.switch_edl_mode()  # 切换紧急下载模式

            qfil.load_programmer()  # QSaharaServer.exe load programmer
            if self.erase:  # erase all flash
                qfil.erase_with_xml()
                qfil.erase_all()

            qfil.load_package()  # 升级
            qfil.load_patch()
            qfil.set_start_partition()
            qfil.reset_module()  # 重启
            self.gpio.set_pwk_high_level()


    def check_init_cclk(self):
        cclk_result = self.at_handler.send_at('AT+CCLK?')
        all_logger.info('cclk初始值-->{}'.format(cclk_result))
        if '80/01' in cclk_result:
            return True
        else:
            raise CCLKError("CCLK查询初始值异常")

    def check_net_cclk(self):
        cclk_result = self.at_handler.send_at('AT+CCLK?')
        all_logger.info('cclk驻网后查询值-->{}'.format(cclk_result))
        if '80/01' not in cclk_result:
            return True
        else:
            raise CCLKError("CCLK查询值异常")

    def check_init_qlts(self):
        qlts_result = self.at_handler.send_at('AT+QLTS')
        all_logger.info('qlts初始值-->{}'.format(qlts_result))
        qlts_result_re = ''.join(re.findall(r'\+QLTS: (.*)', qlts_result))
        print(f'qlts_result_re--->{qlts_result_re}')
        if '""' in qlts_result_re:
            return True
        else:
            raise CCLKError("QLTS查询值异常")

    def set_sim_det(self):
        self.at_handler.send_at('AT+QSIMDET=1,0')

    def set_sim_det_rec(self):
        self.at_handler.send_at('AT+QSIMDET=1,1')
