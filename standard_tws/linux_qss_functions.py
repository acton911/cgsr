import os
import re
import sys
from utils.cases.linux_qss_functions_manager import LinuxQSSFunctionsManager
import time

from utils.functions.iperf import iperf
from utils.functions.linux_api import QuectelCMThread, enable_network_card_and_check
from utils.functions.middleware import Middleware
from utils.log import log
from utils.logger.logging_handles import all_logger
import subprocess
from utils.functions.decorators import startup_teardown
import traceback
from utils.exception.exceptions import QMIError


class LinuxQSSFunctions(LinuxQSSFunctionsManager):

    def test_linux_qss_cfuntions_01_000(self):
        # self.at_handle.cfun0()
        # time.sleep(1)
        # self.at_handle.cfun1()
        # time.sleep(5)
        # rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
        # all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
        # all_logger.info(f"nr band : {rerutn_bands['band']}")
        # time.sleep(10)
        self.check_modelight_alwaysbright()
        self.check_statuslight_longbrightshortdown()

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_001(self):
        """
        1.查询当前项目Catx
        2.查询ue-categoryDL&ue-categoryUL
        3. 抓取找网QXDM log
        4. Ctrl+A全选--右键Refilter Item---OTA--全选后点击
        5. 找UE上报能力：
          dl支持256QAM---cat13
          UL不支持64QAM----cat3
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_qss_cfuntions_01_001')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handle.cfun0()
                time.sleep(5)
                self.at_handle.cfun1()
                time.sleep(3)

                # 注网及检查注网B3n78
                self.at_handle.check_network()
                rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
                all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
                all_logger.info(f"nr band : {rerutn_bands['band']}")
                if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                    raise QMIError("注网异常(B3n78)!")

                self.delay_task(start_time, qss_connection, 100)

                all_logger.info("wait 15 seconds, catch log end")
                time.sleep(15)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                # message_types = {"LOG_PACKET": ["0xB821"]}
                message_types = {"LOG_PACKET": ["0xB0C0"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE",
                                           "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info("************************data*****************************")
                all_logger.info(repr(data))
                all_logger.info("************************data*****************************")

                # ue-CategoryDL.*?\s\d+\d+
                # ue_dl = ''.join(re.findall(r'ue-CategoryDL.*(\d\d),', repr(data)))
                # ue_ul = ''.join(re.findall(r'ue-CategoryUL.*(\d\d),', repr(data)))
                ue_dl = ''.join(re.findall(r'ue-CategoryDL.*?\s\d+\d+,', repr(data)))
                ue_ul = ''.join(re.findall(r'ue-CategoryUL.*?\s\d+\d+,', repr(data)))
                all_logger.info(ue_dl)
                all_logger.info(ue_ul)
                ue_dl_key = ''.join(re.findall(r'ue-CategoryDL.*?\s(\d+\d+),', repr(data)))
                ue_ul_key = ''.join(re.findall(r'ue-CategoryUL.*?\s(\d+\d+),', repr(data)))

                if self.cat_dl not in ue_dl_key:
                    raise QMIError(f"CAT DL 值异常,未找到期望值CAT{self.cat_dl} 请确认: {ue_dl}")
                else:
                    all_logger.info("ue-CategoryDL常常")
                if self.cat_ul not in ue_ul_key:
                    raise QMIError(f"CAT UL 值异常,未找到期望值CAT{self.cat_ul} 请确认: {ue_dl}")
                else:
                    all_logger.info("ue-CategoryUL常常")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_002(self):
        """
        Verizon认证项目,激活Verizon的MBN后确认禁用电话功能,保留短信功能
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成Version卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('311480'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('311480', '891480')
            # QSS开网
            task = [self.mme_file_name, self.enb_file_name, self.ims_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=100, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B66N77
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '66' != rerutn_bands['freq_band_ind'] or '77' != rerutn_bands['band']:
                raise QMIError("注网异常(B66N77)!")
            time.sleep(5)

            # 电话功能禁用验证
            self.delay_task(start_time, qss_connection, 60)
            call_result = self.qss_call()
            if call_result:
                raise QMIError("异常，仍然可以正常通话！")
            else:
                all_logger.info("和预期一致，无法通话")

            # 短信功能正常验证
            self.delay_task(start_time, qss_connection, 60)
            self.qss_send_sms()
        finally:
            self.at_handle.send_at("ATH")
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_003(self):
        """
        1、AUTO网络模式下，关闭SA网络
        2、执行AT+QENG="servingcell"确认有5G NR信息
        3、AT+QENDC返回值：+QENDC: 1,1,1,1（前三个参数返回不准确，仅关注最后一个参数返回为1即可）
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 100)

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_004(self):
        """
        1、AUTO网络模式下，关闭SA网络
        2、执行AT+QENG="servingcell"确认有5G NR信息
        3、AT+QENDC返回值：+QENDC: 1,1,1,1（前三个参数返回不准确，仅关注最后一个参数返回为1即可）
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cmcc()
            self.delay_task(start_time, qss_connection, 60)

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_005(self):
        """
        1、AUTO网络模式下，关闭SA网络
        2、执行AT+QENG="servingcell"确认有5G NR信息
        3、AT+QENDC返回值：+QENDC: 1,1,1,1（前三个参数返回不准确，仅关注最后一个参数返回为1即可）
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 60)

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_006(self):
        """
        1、AUTO网络模式下，关闭SA网络
        2、执行AT+QENG="servingcell"确认有5G NR信息
        3、AT+QENDC返回值：+QENDC: 1,1,1,1（前三个参数返回不准确，仅关注最后一个参数返回为1即可）
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_ct()
            self.delay_task(start_time, qss_connection, 60)

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_007(self):
        """
        NSA-5G网络下，quectel-CM工具拨号测试
        """
        self.bound_network('NSA')
        qss_connection = ''
        q = None
        exc_type = None
        exc_value = None
        try:
            start_time, qss_connection = self.open_qss_cu()
            # 模块进入qmi模式
            self.delay_task(start_time, qss_connection, 300)
            self.enter_qmi_mode()
            self.delay_task(start_time, qss_connection, 300)
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread()
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            self.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.extra_ethernet_name)
            self.linux_api.check_intranet(self.extra_ethernet_name)
            self.end_task(qss_connection)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_008(self):
        """
        RG系列测试
        插入SIM卡
        联通卡固定网NSA only找网方式下找网拨号，确认网络灯的状态
        """
        if self.module_typerg():
            return True
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto')

        self.bound_network('NSA')
        # 将卡写成联通卡
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('46001'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('46001', '898601')

        # 模块进入qmi模式
        self.enter_qmi_mode()

        # QSS开网
        task = [self.mme_file_name, self.enb_file_name]
        qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QMIError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(20)

        # 注网及检查注网b3n78
        self.at_handle.cfun0()
        time.sleep(5)
        self.at_handle.cfun1()
        time.sleep(3)
        self.at_handle.check_network()
        rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
        all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
        all_logger.info(f"nr band : {rerutn_bands['band']}")
        if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
            raise QMIError("注网异常(b3n78)!")
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            if time.time() - start_time < 260:
                delay_result = qss_connection.delay_task(260)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread()
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_modelight_alwaysbright()
            self.check_statuslight_blink()
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.check_modelight_alwaysbright()
            self.check_statuslight_longbrightshortdown()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(10)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.extra_ethernet_name)
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_009(self):
        """
        移动NSA模式下可正常进入慢时钟
        :return:
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            self.bound_network('NSA')

            # 将卡写成移动卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46000'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46000', '898600')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '41' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n41)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            self.set_qsclk()
            rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            if rg_flag:
                self.gpio.set_dtr_high_level()  # 默认拉高DTR
            self.linux_enter_low_power()

            if not self.at_handle.check_network():
                raise QMIError('移动固定NSA找网失败')
            self.at_handle.cfun0()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_010(self):
        """
        联通NSA模式下可正常进入慢时钟
        :return:
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            self.bound_network('NSA')

            # 将卡写成联通卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46001'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46001', '898601')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 200:
                delay_result = qss_connection.delay_task(200)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            self.set_qsclk()
            rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            if rg_flag:
                self.gpio.set_dtr_high_level()  # 默认拉高DTR
            self.linux_enter_low_power()

            if not self.at_handle.check_network():
                raise QMIError('移动固定NSA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_011(self):
        """
        电信NSA模式下可正常进入慢时钟
        :return:
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            self.bound_network('NSA')

            # 将卡写成电信卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46003'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46003', '898602')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 200:
                delay_result = qss_connection.delay_task(200)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            self.set_qsclk()
            rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            if rg_flag:
                self.gpio.set_dtr_high_level()  # 默认拉高DTR
            self.linux_enter_low_power()

            if not self.at_handle.check_network():
                raise QMIError('移动固定NSA找网失败')
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_019(self):
        """
        1、禁用SA模式
        2、cfun0/1切换cops/QNWINFO查询网络状态
        3、查询EN-DC连接状态
        4、使用QENG查询主小区信息
        5、启用SA

        1、查询当前网络制式为AUTO
        2、注NSA网成功
        3、ENDC为0,0,0,1
        4、注LTE和5G网，且均显示为NOCONN状态
        5、返回
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成电信卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46003'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46003', '898603')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 60:
                delay_result = qss_connection.delay_task(60)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_012(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band

        备注：合肥电信支持N78"
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band"', 3)
        nsa_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"nsa_nr5g_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band",78', 3)
        qss_connection = ''
        try:
            # 将卡写成电信卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46003'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46003', '898603')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="nsa_nr5g_band",{nsa_bands}', 3)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_013(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band

        备注：合肥电信支持N78"
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="lte_band"', 3)
        lte_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"lte_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="lte_band",3', 3)
        qss_connection = ''
        try:
            # 将卡写成电信卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46003'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46003', '898603')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="lte_band",{lte_bands}', 3)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_014(self):
        """
        1、禁用SA模式
        2、cfun0/1切换cops/QNWINFO查询网络状态
        3、查询EN-DC连接状态
        4、使用QENG查询主小区信息
        5、启用SA

        1、查询当前网络制式为AUTO
        2、注NSA网成功
        3、ENDC为0,0,0,1
        4、注LTE和5G网，且均显示为NOCONN状态
        5、返回
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成联通卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46001'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46001', '898601')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_015(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band

        备注：合肥电信支持N78"
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band"', 3)
        nsa_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"nsa_nr5g_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band",78', 3)
        qss_connection = ''
        try:
            # 将卡写成联通卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46001'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46001', '898601')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="nsa_nr5g_band",{nsa_bands}', 3)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_016(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band

        备注：合肥电信支持N78"
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="lte_band"', 3)
        lte_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"lte_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="lte_band",3', 3)
        qss_connection = ''
        try:
            # 将卡写成联通卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46001'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46001', '898601')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            if time.time() - start_time < 100:
                delay_result = qss_connection.delay_task(100)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="lte_band",{lte_bands}', 3)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_017(self):
        """
        1、禁用SA模式
        2、cfun0/1切换cops/QNWINFO查询网络状态
        3、查询EN-DC连接状态
        4、使用QENG查询主小区信息
        5、启用SA

        1、查询当前网络制式为AUTO
        2、注NSA网成功
        3、ENDC为0,0,0,1
        4、注LTE和5G网，且均显示为NOCONN状态
        5、返回
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成移动卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46000'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46000', '898600')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '41' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n41)!")
            time.sleep(5)

            if time.time() - start_time < 30:
                delay_result = qss_connection.delay_task(30)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_018(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band

        备注：合肥电信支持N78"
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band"', 3)
        nsa_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"nsa_nr5g_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="nsa_nr5g_band",41', 3)
        qss_connection = ''
        try:
            # 将卡写成移动卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46000'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46000', '898600')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '41' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n41)!")
            time.sleep(5)

            if time.time() - start_time < 30:
                delay_result = qss_connection.delay_task(30)
                if delay_result:
                    all_logger.info("延时qss成功")
                else:
                    raise QMIError('延时qss异常')

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="nsa_nr5g_band",{nsa_bands}', 3)
            end_result = qss_connection.end_task()
            if end_result:
                all_logger.info("结束QSS成功")
            else:
                all_logger.info("结束QSS失败")

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_019(self):
        """
        1、固定所在地支持的NSA BAND
        2、查询设置
        3、查询网络状态
        4、恢复默认NSA band
        """
        self.bound_network('NSA')
        return_bands = self.at_handle.send_at('AT+QNWPREFCFG="lte_band"', 3)
        lte_bands = ''.join(re.findall(r'\+QNWPREFCFG:\s"lte_band",(.*)', return_bands))
        self.at_handle.send_at('AT+QNWPREFCFG="lte_band",3', 3)
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cmcc()
            self.delay_task(start_time, qss_connection, 30)

            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")
        finally:
            self.at_handle.send_at(f'AT+QNWPREFCFG="lte_band",{lte_bands}', 3)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_020(self):
        """
        1.查询当前网络状态
        2.通过QRSRP指令查询LTE和5G-NR模式信号接收功率的信号值，与QXDM的0XB97F log对比
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_qss_cfuntions_01_028')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handle.cfun0()
                time.sleep(5)
                self.at_handle.cfun1()
                time.sleep(3)

                # 注网及检查注网B3n78
                self.at_handle.check_network()
                rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
                all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
                all_logger.info(f"nr band : {rerutn_bands['band']}")
                if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                    raise QMIError("注网异常(B3n78)!")
                self.delay_task(start_time, qss_connection, 100)

                return_rsrp = self.at_handle.send_at("AT+QRSRP", 3)
                all_logger.info(return_rsrp)
                lte_rsrp = re.findall(r'\+QRSRP:\s(.*),(.*),.*,.*,LTE', return_rsrp)
                nr5g_rsrp = re.findall(r'\+QRSRP:\s(.*),(.*),.*,.*,NR5G', return_rsrp)
                all_logger.info(lte_rsrp)
                all_logger.info(nr5g_rsrp)

                all_logger.info("wait 5 seconds, catch log end")
                time.sleep(5)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"QTRACE": ["MMODE/STRM/High/CM"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE",
                                           "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info("************************data*****************************")
                all_logger.info(data)
                all_logger.info("************************data*****************************")

                nr5g_rsrp_qxdm = re.findall(r'NR5G-NSA.*rsrp\s(.\d+),\ssinr\s.\d+\srsrq\s.\d+', repr(data))
                lte_rsrp_qxdm = re.findall(r'Format\s=\sLTE\srssi\s\d+,\srsrq\s.\d+,\srsrp\s(.\d+),\ssinr\s\d+', repr(data))

                lte_lte_rsrp_max = int(lte_rsrp[0][0]) + 5
                lte_lte_rsrp_min = int(lte_rsrp[0][0]) - 5
                nr5g_lte_rsrp_max = int(nr5g_rsrp[0][0]) + 5
                nr5g_lte_rsrp_min = int(nr5g_rsrp[0][0]) - 5
                if -145 <= lte_lte_rsrp_min <= int(lte_rsrp_qxdm[0]) <= lte_lte_rsrp_max <= -35:
                    all_logger.info("lte RSRP和QXDM log对比正常")
                else:
                    all_logger.info(lte_lte_rsrp_min)
                    all_logger.info(lte_rsrp_qxdm[0])
                    all_logger.info(lte_lte_rsrp_max)
                    raise QMIError("lte RSRP和QXDM log对比异常")
                if -145 <= nr5g_lte_rsrp_min <= int(nr5g_rsrp_qxdm[0]) <= nr5g_lte_rsrp_max <= -35:
                    all_logger.info("nr5g RSRP和QXDM log对比正常")
                else:
                    all_logger.info(nr5g_lte_rsrp_min)
                    all_logger.info(int(nr5g_rsrp_qxdm[0]))
                    all_logger.info(nr5g_lte_rsrp_max)
                    raise QMIError("nr5g RSRP和QXDM log对比异常")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_021(self):
        """
        Auto模式，NSA网络环境下，插联通卡CALL时qeng查询servingcell(data only版本无需测试)

        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成联通卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('46001'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('46001', '898601')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name, self.ims_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(b3n78)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            self.qss_call()
            return_atdcheck = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            if 'CONNECT' not in return_atdcheck:
                raise QMIError(f"注网异常：{return_atdcheck}")
        finally:
            self.at_handle.send_at("ATH")
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_022(self):
        """
        Auto模式，NSA网络环境下，插联通卡CALL时qeng查询servingcell(data only版本无需测试)

        """
        qss_connection1 = ''
        qss_connection2 = ''
        try:
            # 掉卡
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            # QSS开网 lte (六个以上PLMN的特殊文件)
            task = [self.mme_file_name[0], self.enb_file_name[0]]
            qss_connection1 = self.get_qss_connection(tesk_duration=120, task=task)
            start_result = qss_connection1.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(60)
            return_scan1 = self.at_handle.send_at("AT+QSCAN=1", 180)
            all_logger.info(return_scan1)
            return_scan2 = self.at_handle.send_at("AT+QSCAN=2", 180)
            all_logger.info(return_scan2)
            return_scan3 = self.at_handle.send_at("AT+QSCAN=3", 180)
            all_logger.info(return_scan3)
            if "LTE" in return_scan1 and "LTE" in return_scan3 and "NR5G" not in return_scan2:
                all_logger.info("LTE下QSCAN正常")
            else:
                raise QMIError("LTE下QSCAN异常!")
            self.end_task(qss_connection1)

            # QSS开网 SA (六个以上PLMN的特殊文件)
            task = [self.mme_file_name[1], self.enb_file_name[1]]
            qss_connection2 = self.get_qss_connection(tesk_duration=120, task=task)
            start_result = qss_connection2.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(60)
            return_scan1 = self.at_handle.send_at("AT+QSCAN=1", 180)
            all_logger.info(return_scan1)
            return_scan2 = self.at_handle.send_at("AT+QSCAN=2", 180)
            all_logger.info(return_scan2)
            return_scan3 = self.at_handle.send_at("AT+QSCAN=3", 180)
            all_logger.info(return_scan3)
            if "LTE" not in return_scan1 and "LTE" not in return_scan3 and "NR5G" in return_scan2 and "NR5G" in return_scan3:
                all_logger.info("LTE下QSCAN正常")
            else:
                raise QMIError("LTE下QSCAN异常!")
        finally:
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(5)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_025(self):
        """
        1.开启控制平面延迟
        2.禁用SA
        3.查询当前网络环境
        4.CFUN0/1切换
        5.不断查询AT+QNWCFG="ctrl_plane_dly"，查询末位值不为0
        6.启用SA,关闭控制面时延
        """
        self.bound_network('NSA')
        self.at_handle.send_at('AT+QNWCFG="ctrl_plane_dly",1', 3)
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 100)
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(180)
            return_value = self.at_handle.send_at('AT+QNWCFG="ctrl_plane_dly"', 3)
            all_logger.info(return_value)
            result = re.findall(r'\+QNWCFG: "ctrl_plane_dly",1,"(.*)",(.*)', return_value)
            # \+QNWCFG: "ctrl_plane_dly",1,"(.*)",(.*)
            if 'LTE' != result[0][0] or '0' == result[0][1]:
                raise QMIError(f"LTE控制面延迟异常!{return_value}")

        finally:
            self.at_handle.send_at('AT+QNWCFG="ctrl_plane_dly",0', 3)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_026(self):
        """
        1.执行指令关闭模组注SA网络
        2.查询注网
        3.开启指令功能
        4.查询NSA网络下的用户层数据路径与最近的0xB840日志内容对比即可
        5.恢复默认值
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_qss_cfuntions_01_034')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                self.at_handle.cfun0()
                time.sleep(5)
                self.at_handle.cfun1()
                time.sleep(3)

                # 注网及检查注网B3n78
                self.at_handle.check_network()
                rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
                all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
                all_logger.info(f"nr band : {rerutn_bands['band']}")
                if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                    raise QMIError("注网异常(B3n78)!")
                self.delay_task(start_time, qss_connection, 100)

                self.at_handle.send_at('AT+QNWCFG="data_path",0', 3)
                return_value = self.at_handle.send_at('AT+QNWCFG="data_path"', 3)
                all_logger.info(return_value)
                data_path = ''.join(re.findall(r'\+QNWCFG: "data_path",1,"(.*)"', return_value))

                all_logger.info("wait 5 seconds, catch log end")
                time.sleep(5)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"LOG_PACKET": ["0xB840"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE",
                                           "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info("************************data*****************************")
                all_logger.info(data)
                all_logger.info("************************data*****************************")
                data_path_qxdm = ''.join(re.findall(r'RLC\sPath\s=\s+(\S+)', repr(data)))
                all_logger.info(data_path_qxdm)
                if data_path != data_path_qxdm:
                    raise QMIError("NSA网络下的用户层数据路异常")
        finally:
            self.at_handle.send_at('AT+QNWCFG="data_path",0', 3)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_027(self):
        """
        1.模块注网失败
        2.自动上报URC
        3.使用指令查询错误码(QSS配置的是33)
        4.使用AT+QNETRC?指令查询错误码
        """
        qss_connection = ''
        try:
            # 将卡写成00101卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('00101'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('00101', '8949024')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(3)
            rerutn_bands = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            all_logger.info(rerutn_bands)
            if 'NOCONN' not in rerutn_bands and 'CONNECT' not in rerutn_bands:
                all_logger.info("和预期一致，注网失败！")
            else:
                all_logger.info("和预期不一致，没有注网失败！")

            self.delay_task(start_time, qss_connection, 100)

            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)
            return_value1 = self.at_handle.send_at('AT+QESMINFO?', 3)
            all_logger.info(return_value1)
            return_value2 = self.at_handle.send_at('AT+QNETRC?', 3)
            all_logger.info(return_value2)
            if '+QESMINFO: 33' not in return_value1 or '+QNETRC: "esm_cause",33' not in return_value2:  # QSS配置的是33
                raise QMIError("ESIM错误码异常!")

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_028(self):
        """
        1.模块注网失败
        2.自动上报URC
        3.使用指令查询错误码
        4.使用AT+QNETRC?指令查询错误码
        """
        qss_connection = ''
        try:
            # 将卡写成00101卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('00101'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('00101', '8949024')

            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=360, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            rerutn_bands = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            all_logger.info(rerutn_bands)
            if 'NOCONN' not in rerutn_bands and 'CONNECT' not in rerutn_bands:
                all_logger.info("和预期一致，注网失败！")
            else:
                all_logger.info("和预期不一致，没有注网失败！")

            self.delay_task(start_time, qss_connection, 100)

            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)
            return_value1 = self.at_handle.send_at('AT+QEMMINFO?', 3)
            all_logger.info(return_value1)
            return_value2 = self.at_handle.send_at('AT+QNETRC?', 3)
            all_logger.info(return_value2)
            if '+QEMMINFO: 7,' not in return_value1 or '+QNETRC: "emm_cause",7' not in return_value2:  # QSS配置的是7
                raise QMIError("ESIM错误码异常!")

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_029(self):
        """
        1.仪表配置5GMM的错误码环境
        AT+QNETRC?
        2.配置URC上报
        3.cfun0/1切换5gmm错误码自动上报
        """
        qss_connection = ''
        try:
            # 将卡写成00101卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('00101'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('00101', '8949024')

            # QSS开网(带错误码的、注不上网的)
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            rerutn_bands = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            all_logger.info(rerutn_bands)
            if 'NOCONN' not in rerutn_bands and 'CONNECT' not in rerutn_bands:
                all_logger.info("和预期一致，注网失败！")
            else:
                all_logger.info("和预期不一致，没有注网失败！")

            self.delay_task(start_time, qss_connection, 100)

            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)
            return_value2 = self.at_handle.send_at('AT+QNETRC?', 3)
            all_logger.info(return_value2)
            if '+QNETRC: "5gmm_cause",3' not in return_value2:  # QSS配置的是3
                raise QMIError("ESIM错误码异常!")

            self.at_handle.send_at('AT+QNETRC=7', 3)
            return_value1 = self.at_handle.send_at('AT+QNETRC')
            all_logger.info(return_value1)
            if '+QNETRC: 7' not in return_value1:  # QSS配置的是33
                raise QMIError("AT+QNETRC返回值异常")

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_030(self):
        """
        1.仪表开启00101的SA网络
        2.模块插其他保卡（不是00101的白卡即可）
        3.模块可以注网漫游
        4. 关闭漫游功能后CFUN0/1切换
        5. 模块注网失败
        6.打开漫游
        7.仪表开启00101的NSA网络
        8.CFUN0/1切换可以注网
        9.关闭漫游
        10CFUN0/1切换注网失
        """
        qss_connection = ''
        qss_connection2 = ''
        try:
            # 将卡写成50501卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('50501'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('50501', '896101')
            # QSS开网 00101 SA
            task = [self.mme_file_name, self.enb_file_name[0]]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 3)  # 开启漫游功能
            # 注网及检查注网N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('band')
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '78' != rerutn_bands['band']:
                raise QMIError("注网异常(N78)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 100)
            self.at_handle.send_at('AT+QNWCFG="data_roaming",1', 3)  # 关闭漫游功能
            # 无法注网
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(10)
            rerutn_bands = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            all_logger.info(rerutn_bands)
            if 'NOCONN' in rerutn_bands or 'CONNECT' in rerutn_bands:
                raise QMIError("异常,关闭漫游后仍可以注网！")
            time.sleep(5)

            # QSS开网 00101 NSA
            task2 = [self.mme_file_name, self.enb_file_name[1]]
            print("66666666666666666666666666666666666666666666666666666666666666666")
            qss_connection2 = self.get_qss_connection(tesk_duration=330, task=task2)
            start_time2 = time.time()
            start_result = qss_connection2.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 3)  # 开启漫游功能
            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(B3N78)!")
            time.sleep(5)

            self.delay_task(start_time2, qss_connection2, 100)
            self.at_handle.send_at('AT+QNWCFG="data_roaming",1', 3)  # 关闭漫游功能
            # 无法注网
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(10)
            rerutn_bands = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            all_logger.info(rerutn_bands)
            if 'NOCONN' in rerutn_bands or 'CONNECT' in rerutn_bands:
                raise QMIError("异常,关闭漫游后仍可以注网！")
            time.sleep(5)

        finally:
            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 3)  # 开启漫游功能
            self.end_task(qss_connection)
            self.end_task(qss_connection2)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_031(self):
        """
        模块支持的，实网下没有的ENDC组合注网
        1、查询当前网络制式
        2、cops/QNWINFO/CSQ查询网络状态
        4、查询EN-DC连接状态
        5、QENG查询临近小区信息
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成version卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('311480'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('311480', '891480')
            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B66N77
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '66' != rerutn_bands['freq_band_ind'] or '77' != rerutn_bands['band']:
                raise QMIError("注网异常(B66N77)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            # 检查ENDC
            return_endc = self.at_handle.send_at('AT+QENDC', 3)
            all_logger.info(return_endc)
            endc_last = ''.join(re.findall(r'\+QENDC:\s\d,\d,\d,(\d)', return_endc))
            if endc_last != '1':
                raise QMIError(f"ENDC值异常 : {return_endc}")

            return_neighbourcell = self.at_handle.send_at('AT+QENG="neighbourcell"', 3)
            all_logger.info(return_neighbourcell)
            if "ERROR" in return_neighbourcell:
                raise QMIError(f"return_neighbourcell值异常 : {return_neighbourcell}")

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_032(self):
        """

        1.仪表开启2CA网络B13B66n2
        2.检查网络，查询参数
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成Version卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('311480'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('311480', '891480')
            # QSS开网 2CA  B13B66n2
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B13B66N2
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            # rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            rerutn_bands = self.get_qeng_info('freq_band_ind')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            # all_logger.info(f"nr band : {rerutn_bands['band']}")
            # if '66' != rerutn_bands['freq_band_ind'] or '2' != rerutn_bands['band']:
            if '13' != rerutn_bands['freq_band_ind']:
                raise QMIError("注网异常(B13B66N2)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            # LTE\sBAND\s(\d+)
            return_qcainfo = self.at_handle.send_at('AT+QCAINFO', 3)
            all_logger.info(return_qcainfo)
            bands = re.findall(r'LTE\sBAND\s(\d+)', return_qcainfo)
            if '66' not in bands or '13' not in bands:
                raise QMIError("qcainfo检查异常！")
        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_033(self):
        """
        1.仪表开启3CA网络B13B2B66n66
        2.检查网络，查询参数
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成Version卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('311480'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('311480', '891480')
            # QSS开网 3CA  B13B2B66n66
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=180, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B13B2B66n66
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            # rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            rerutn_bands = self.get_qeng_info('freq_band_ind')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            # all_logger.info(f"nr band : {rerutn_bands['band']}")
            # if '66' != rerutn_bands['freq_band_ind'] or '66' != rerutn_bands['band']:
            if '13' != rerutn_bands['freq_band_ind']:
                raise QMIError("注网异常(B13B2B66n66)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            # LTE\sBAND\s(\d+)
            return_qcainfo = self.at_handle.send_at('AT+QCAINFO', 3)
            all_logger.info(return_qcainfo)
            bands = re.findall(r'LTE\sBAND\s(\d+)', return_qcainfo)
            if '66' not in bands or '2' not in bands or '13' not in bands:
                raise QMIError("qcainfo检查异常！")
        finally:
            self.end_task(qss_connection)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_034(self):
        """
        仅有SA网络环境，查询AT+QSCAN
        1.QSS开启SA网络
        2.模块不插卡，查询AT+QSCAN 搜索附近的LTE小区和NR5G小区
        """
        qss_connection = ''
        try:
            # 掉卡
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            # QSS开网 SA
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(60)
            return_scan1 = self.at_handle.send_at("AT+QSCAN=1", 180)
            all_logger.info(return_scan1)
            return_scan2 = self.at_handle.send_at("AT+QSCAN=2", 180)
            all_logger.info(return_scan2)
            return_scan3 = self.at_handle.send_at("AT+QSCAN=3", 180)
            all_logger.info(return_scan3)
            if "LTE" not in return_scan1 and "LTE" not in return_scan3 and "NR5G" in return_scan2 and "NR5G" in return_scan3:
                all_logger.info("仅SA环境下QSCAN正常")
            else:
                raise QMIError("仅SA环境下QSCAN异常!")
        finally:
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(5)
            self.end_task(qss_connection)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_035(self):
        """
        1.QSS开启NSA网络
        2.模块不插卡，查询AT+QSCAN 搜索附近的LTE小区和NR5G小区
        """
        qss_connection = ''
        try:
            # 掉卡
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            # QSS开网 NSA
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=330, task=task)
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(60)
            return_scan1 = self.at_handle.send_at("AT+QSCAN=1", 180)
            all_logger.info(return_scan1)
            return_scan2 = self.at_handle.send_at("AT+QSCAN=2", 180)
            all_logger.info(return_scan2)
            return_scan3 = self.at_handle.send_at("AT+QSCAN=3", 180)
            all_logger.info(return_scan3)
            if "LTE" in return_scan1 and "LTE" in return_scan3 and "NR5G" not in return_scan2 and "NR5G" not in return_scan3:
                all_logger.info("NSA环境下QSCAN正常")
            else:
                raise QMIError("NSA环境下QSCAN异常!")
        finally:
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(5)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_038(self):
        """
        使用白卡注网后查询号码
        1.使用00101的白卡注网
        2.AT+QNWCFG="msisdn"指令查询当前号码
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成00101卡
            imsi_n = ''
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('00101'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                imsi_n, _ = self.write_simcard.write_white_simcard('00101', '8949024')
            # QSS开网
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(B3N78)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            return_cfact = self.at_handle.send_at('AT+CGACT?', 3)
            all_logger.info(return_cfact)
            return_cgdcont = self.at_handle.send_at('AT+CGDCONT?', 3)
            all_logger.info(return_cgdcont)

            return_msisdn = self.at_handle.send_at('AT+QNWCFG="msisdn"', 3)
            all_logger.info(return_msisdn)
            number = ''.join(re.findall(r'\+QNWCFG:\s"msisdn",0,"(.*)"', return_msisdn))
            if imsi_n != number:
                raise QMIError('AT+QNWCFG="msisdn"查询号码异常')

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_cfuntions_01_039(self):
        """
        1.使用00101的白卡注网
        2.AT+QNWCFG="msisdn"指令查询当前号码
        """
        self.bound_network('NSA')
        qss_connection = ''
        try:
            # 将卡写成00101卡
            return_imsi = self.write_simcard.get_cimi()
            if return_imsi.startswith('50501'):
                all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
            else:
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(60)  # 先等待一会，否则直接写卡可能失败
                self.write_simcard.write_white_simcard('50501', '896101')
            # QSS开网  非00101的B3N78网络
            task = [self.mme_file_name, self.enb_file_name]
            qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
            start_time = time.time()
            start_result = qss_connection.start_task()
            if not start_result:
                raise QMIError('开启qss异常')
            all_logger.info('等待网络稳定')
            time.sleep(20)

            self.at_handle.send_at('AT+QNWCFG="data_roaming",0', 3)  # 开启漫游功能

            # 注网及检查注网B3N78
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(3)
            self.at_handle.check_network()
            rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
            all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
            all_logger.info(f"nr band : {rerutn_bands['band']}")
            if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
                raise QMIError("注网异常(B3N78)!")
            time.sleep(5)

            self.delay_task(start_time, qss_connection, 60)
            return_cfact = self.at_handle.send_at('AT+CGACT?', 3)
            all_logger.info(return_cfact)
            return_cgdcont = self.at_handle.send_at('AT+CGDCONT?', 3)
            all_logger.info(return_cgdcont)
            self.at_handle.send_at('AT+CREG?;+CEREG?;+CGREG?', 3)

            return_msisdn = self.at_handle.send_at('AT+QNWCFG="msisdn"', 3)
            all_logger.info(return_msisdn)
            number = ''.join(re.findall(r'\+QNWCFG:\s"msisdn",0,"(.*)"', return_msisdn))
            if return_imsi != number:
                raise QMIError('AT+QNWCFG="msisdn"查询号码异常')

        finally:
            self.end_task(qss_connection)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_qss_cfuntions_01_041(self):
        self.bound_network('NSA')
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 120)

            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_qss_cfuntions_01_049')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                self.delay_task(start_time, qss_connection, 300)
                self.at_handle.check_network()
                self.set_apn(2, 'apn2')
                return_apn = self.at_handle.send_at("AT+CGDCONT?", 3)
                all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

                return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
                self.open_vlan('2')
                return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
                return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
                if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                    raise QMIError("mpdn rule检查异常！{return_default_value}")
                self.send_mpdn_rule('0,1,0,0,1')
                self.send_mpdn_rule('1,2,2,0,1')

                self.check_mPDN_rule('0', '1')
                self.check_mPDN_rule('2', '2')

                self.check_MPDN_status('0', '1')
                self.check_MPDN_status('2', '2')

                self.two_way_dial_set(now_mode)

                self.mpdn_route_set(now_mode, 2)

                self.delay_task(start_time, qss_connection, 300)
                now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
                ifconfig_get_result = subprocess.getoutput('ifconfig')
                all_logger.info(f'ifconfig :{ifconfig_get_result}')
                if f'{now_network_card_name}.2' not in ifconfig_get_result:
                    raise QMIError("网卡状态异常：{ifconfig_all_result}")

                self.ping_get_connect_status(network_card_name=now_network_card_name)
                self.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')

                return_qgpapn = self.at_handle.send_at("AT+QGPAPN", 6)
                all_logger.info(return_qgpapn)
                apn_1_name = ''.join(re.findall(r'\+QGPAPN:\s1,"(.*)"', return_qgpapn))
                apn_2_name = ''.join(re.findall(r'\+QGPAPN:\s2,"(.*)"', return_qgpapn))
                all_logger.info(apn_1_name)
                all_logger.info(apn_2_name)
                if apn_1_name == '' or apn_2_name == '':
                    raise QMIError(f"获取apn名称异常：{return_qgpapn}")

                return_qgpapn_1 = self.at_handle.send_at("AT+QGPAPN=1", 6)
                all_logger.info(return_qgpapn_1)
                ip_apn1 = ''.join(re.findall(r'\+QGPAPN:\s1,".*","(.*)"', return_qgpapn_1))
                ip_apn2 = ''.join(re.findall(r'\+QGPAPN:\s2,".*","(.*)"', return_qgpapn_1))
                all_logger.info(ip_apn1)
                all_logger.info(ip_apn2)
                if ip_apn1 == '' or ip_apn2 == '':
                    raise QMIError(f"AT+QGPAPN=1获取IP异常：{return_qgpapn_1}")
                return_debug_value = self.get_value_debug('ifconfig -a')
                if ip_apn1 not in return_debug_value or ip_apn2 not in return_debug_value:
                    raise QMIError(f"异常，AT+QGPAPN=1获取的IP: {ip_apn1}、{ip_apn2}在debug中未查询到： {return_debug_value}")
                else:
                    all_logger.info(f"已经在debug信息中找到 {ip_apn1}、{ip_apn2}")

                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
                self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
                time.sleep(60)  # disable vlan后模块可能会重启
                self.driver_check.check_usb_driver()
                time.sleep(3)  # 立即发AT可能会误判为AT不通
                self.exit_eth_mode(now_mode)

                self.delay_task(start_time, qss_connection, 300)
                enable_network_card_and_check(self.pc_ethernet_name)  # 恢复网络，传送解析log
                ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.pc_ethernet_name))  # 启用本地网卡
                all_logger.info('ifconfig {} up\r\n{}'.format(self.pc_ethernet_name, ifconfig_up_value))
                self.udhcpc_get_ip_eth(network_name=self.pc_ethernet_name)

                all_logger.info("wait 30 seconds, catch log end")
                time.sleep(30)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"LOG_PACKET": ["0xB800", "0xB0E3"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info(data)

                apn_1_name_len = len(apn_1_name)
                for k in range(apn_1_name_len):
                    if f'({apn_1_name[k]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise QMIError(f'异常！ ({apn_1_name[k]}) 不在 {repr(data)} 之中')

                apn_2_name_len = len(apn_2_name)
                for j in range(apn_2_name_len):
                    if f'({apn_2_name[j]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise QMIError(f'异常！ ({apn_2_name[j]}) 不在 {repr(data)} 之中')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver_check.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)
            self.end_task(qss_connection)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_042(self):
        """
        1.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        2.查询PC端本地连接IPv4地址（ifconfig）
        3.使用AT+QDMZ设置IPv4 dmz地址
        4.使用AT+QDMZ已设置的IPv4 dmz地址
        5.QSS服务器端ping设置的IPv4 dmz地址
        6.禁用QMAP拨号规则0
        """
        seq = 1
        now_mode = ''
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 120)

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            self.delay_task(start_time, qss_connection, 120)

            retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
            all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
            ipv4_adress = self.get_network_card_ipv4(now_mode)
            if ipv4_adress:
                self.send_at_error_try_again(f'AT+QDMZ=1,4,{ipv4_adress}')
            else:
                raise QMIError(f"ipv4获取异常: {ipv4_adress}")
            return_check = self.send_at_error_try_again('AT+QDMZ', 3)
            if ipv4_adress not in return_check:
                raise QMIError(f"异常！AT+QDMZ=1,4,{ipv4_adress}设置ipv6后，AT+QDMZ查询失败：{return_check}")

            self.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            self.end_task(qss_connection)

    @startup_teardown()
    def test_linux_qss_cfuntions_01_043(self):
        """
        1.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.查询当前mPDN拨号状态
        2.查询PC端本地连接IPv4地址（ifconfig）
        3.查询当前默认QMAP拨号的DMZ配置
        4.使用AT+QDMZ设置IPv4 dmz地址
        5.使用AT+QDMZ已设置的IPv4 dmz地址
        6.QSS服务器端ping设置的IPv4 dmz地址
        7.禁用QMAP拨号规则0
        """
        now_mode = ''
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 120)

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            self.common_connect_check(now_mode)
            self.delay_task(start_time, qss_connection, 120)

            retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
            all_logger.info(f'AT+QMAP="wwan": {retunr_value}')

            return_dmz_default = self.send_at_error_try_again('AT+QMAP="DMZ"', 3)
            status_dmz = re.findall(r'\+QMAP:\s"DMZ",(\d)', return_dmz_default)
            if '1' in status_dmz:
                all_logger.info(return_dmz_default)
                raise QMIError('AT+QMAP="DMZ"默认值异常')

            ipv4_adress = self.get_network_card_ipv4(now_mode)
            if ipv4_adress:
                self.send_at_error_try_again(f'AT+QMAP="DMZ",1,4,{ipv4_adress}')
            else:
                raise QMIError(f"ipv4获取异常: {ipv4_adress}")

            mdz_set_resutl = self.at_handle.send_at('AT+QMAP="DMZ"', 3)
            if ipv4_adress not in mdz_set_resutl:
                raise QMIError('AT+QMAP="DMZ"设置ip后查询异常！')

            return_check = self.send_at_error_try_again('AT+QDMZ', 3)
            if ipv4_adress not in return_check:
                raise QMIError(f"异常！AT+QDMZ=1,4,{ipv4_adress}设置ipv6后，AT+QDMZ查询失败：{return_check}")

            self.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
        finally:
            self.eth_network_card_down(now_mode)
            self.at_handle.send_at('AT+QMAP="DMZ",0', 3)  # 恢复默认值
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_qss_cfuntions_01_044(self):
        """
        1.模块注册NSA网络
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.指定带宽30M通过Iperf灌包速率测试5min
        4.禁用规则0
        """
        self.bound_network('NSA')
        now_mode = ''
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 120)

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            self.common_connect_check(now_mode)

            self.delay_task(start_time, qss_connection, 330)
            all_logger.info("开始30M灌包速率测试5min")
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            self.end_task(qss_connection)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_qss_cfuntions_01_045(self):
        """
        1.模块注册NSA网络
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.指定带宽30M通过Iperf灌包速率测试5min
        4.禁用规则0
        """
        self.bound_network('NSA')
        now_mode = ''
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 120)

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)

            self.delay_task(start_time, qss_connection, 330)
            all_logger.info("开始30M灌包速率测试5min")
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            self.end_task(qss_connection)


if __name__ == "__main__":
    # at_port, dm_port, wwan_path, network_card_name, extra_ethernet_name, params_path, qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name, cat_dl, cat_ul
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB0',
        'wwan_path': '/home/ubuntu/Tools/Drivers/qmi_wwan_q',
        'network_card_name': 'wwan0_1',
        'extra_ethernet_name': 'eth1',
        'params_path': '11',
        'qss_ip': '10.66.98.136',
        'local_ip': '11.11.11.11',
        'node_name': 'jeckson_test',
        # 'mme_file_name': ['00101-mme-ims.cfg','00101-mme-ims.cfg'],
        # 'enb_file_name': ['00101-gnb-sa-n78-DLmax.cfg','00101-endc-gnb-nsa-b3n78.cfg'],  # SA & NSA
        # 'ims_file_name': ['00101-ims.cfg','00101-ims.cfg'],
        # 'mme_file_name': '00101-mme-ims.cfg',
        # 'mme_file_name': '00101-mme-ims-esm-33.cfg',
        'mme_file_name': '00101-mme-ims-5Gmm.cfg',
        'enb_file_name': '00101-gnb-sa-n78-DLmax.cfg',
        # 'enb_file_name': '00101-endc-gnb-nsa-b3n78.cfg',
        'ims_file_name': '00101-ims.cfg',
        # 'mme_file_name': '46003-mme-ims.cfg',  # CT
        # 'enb_file_name': '46003-gnb-nsa-b3n78-DLmax.cfg',  # CT
        # 'ims_file_name': '46003-ims.cfg',  # CT
        # 'mme_file_name': '46000-mme-ims.cfg',
        # 'enb_file_name': '46000-gnb-nsa-B3N41.cfg',
        # 'ims_file_name': '46000-ims.cfg',
        # 'mme_file_name': '46001-mme-ims.cfg',
        # 'enb_file_name': '46001-gnb-nsa-b3n78-DLmax.cfg',
        # 'ims_file_name': '46001-ims.cfg',
        # 'mme_file_name': '311480-mme-ims.cfg',
        # 'enb_file_name': '311480-gnb-nsa-b66n77.cfg',
        # 'enb_file_name': '311480-b13b66+n2.cfg',
        # 'ims_file_name': '311480-ims.cfg',
        # 'mme_file_name': ['00101-mme-ims.cfg','50501-mme-ims.cfg'],
        # 'enb_file_name': ['00101-enb-plmns.cfg','50501-gnb-sa-six-plmn.cfg'],
        # 'ims_file_name': '00101-ims.cfg',
        'cat_dl': '20',
        'cat_ul': '18',
        'rgmii_ethernet_name': 'eth2',
        'rtl8125_ethernet_name': 'eth0',
        'eth_test_mode': '3',
        'pc_ethernet_name': 'eth1',
    }
    # 50501/896101、
    linux_qss = LinuxQSSFunctions(**param_dict)
    # linux_qss.test_linux_qss_cfuntions_01_000()
    # linux_qss.test_linux_qss_cfuntions_01_008()  #  cu OK可以获取到cat信息，到很难获取到最大cat值(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_009()  # Verizon OK(311480-gnb-nsa-b66n77.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_010()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_011()  # CMCC OK(46000-gnb-nsa-B3N41.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_012()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_013()  # CT OK(46003-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_014()  # cu  OK(46001-gnb-nsa-b3n78-DLmax.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_015()  # CU 灯 RG

    # linux_qss.test_linux_qss_cfuntions_01_016()  # CMCC OK cfun1进入慢时钟失败,cfun0 pass(46000-gnb-nsa-B3N41.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_017()  # cu OK cfun1进入慢时钟失败,cfun0 pass(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_018()  # CT OK cfun1进入慢时钟失败,cfun0 pass(46003-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_019()  # CT OK(46003-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_020()  # CT OK(46003-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_021()  # CT OK(46003-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_022()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_023()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_024()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_025()  # CMCC OK(46000-gnb-nsa-B3N41.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_026()  # CMCC OK(46000-gnb-nsa-B3N41.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_027()  # CMCC OK(46000-gnb-nsa-B3N41.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_028()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_029()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_030()  # lte (六个以上PLMN的特殊文件) OK(['00101-enb-plmns.cfg','50501-gnb-sa-six-plmn.cfg'])

    # linux_qss.test_linux_qss_cfuntions_01_033()  # cu OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_034()  # cu LOG zhua bu dao neirong (46001-gnb-nsa-b3n78-DLmax.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_035()  # QSS配置的错误码是33 (00101-mme-ims-esm-33.cfg, 00101-endc-gnb-nsa-b3n78.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_036()  # 错误码(00101-mme-ims-emm-7.cfg, 00101-endc-gnb-nsa-b3n78.cfg)
    linux_qss.test_linux_qss_cfuntions_01_037()  # 错误码(00101-mme-ims-5Gmm.cfg, 00101-gnb-sa-n78-DLmax.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_038()  # 00101_SA & NSA OK(['00101-gnb-sa-n78-DLmax.cfg','00101-endc-gnb-nsa-b3n78.cfg'])
    # linux_qss.test_linux_qss_cfuntions_01_039()  # Verizon OK(311480-gnb-nsa-b66n77.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_040()  # Verizon 2CA  B13B66n2   mei ge xiang mu bu yi yang ,shanchu
    # linux_qss.test_linux_qss_cfuntions_01_041()  # Verizon 3CA  B13B2B66n66  mei ge xiang mu bu yi yang ,shanchu

    # linux_qss.test_linux_qss_cfuntions_01_042()  # SA simdet OK(00101-gnb-sa-n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_043()  # NSA simdet OK(00101-endc-gnb-nsa-b3n78.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_046()  # 00101_NSA_b3n78 OK not support AT+QNWCFG="msisdn"(00101-endc-gnb-nsa-b3n78.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_047()  # 50501 OK not support AT+QNWCFG="msisdn"(00101-endc-gnb-nsa-b3n78.cfg)

    # linux_qss.test_linux_qss_cfuntions_01_049()  # cu phy second dial FAIL (46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_050()  # cu phy OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_051()  # cu phy OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_052()  # cu phy OK(46001-gnb-nsa-b3n78-DLmax.cfg)
    # linux_qss.test_linux_qss_cfuntions_01_053()  # cu phy OK(46001-gnb-nsa-b3n78-DLmax.cfg)
