import subprocess
import sys
import time
import traceback
from utils.cases.linux_qss_weak_signal_manager import LinuxQSSWeakSignalManager
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
from utils.functions.linux_api import QuectelCMThread
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import QSSWeakSignalError


class LinuxQSSWeakSignal(LinuxQSSWeakSignalManager):

    @startup_teardown()
    def test_linux_qss_weak_signal_01_000(self):
        """
        用于方法调试
        """
        # self.enb_file_name_now, _ = self.get_weak_enb_file_name()
        # print(self.enb_file_name_now)
        # print(_)
        iperf(ip=self.qss_ip, user='sdr', passwd='123123', port=22, bandwidth='30M', times=30, mode=1, linux=True)

    @startup_teardown()
    def test_linux_qss_weak_signal_01_001(self):
        """
        1.进行qmi拨号
        2.在弱信号环境下进行iperf TCP打流
        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss()
            self.delay_task(start_time, qss_connection, 100)
            self.check_weak_signal()  # 检查弱信号

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False
            # iperf打流测试
            iperf(ip="10.66.129.204", user='sdr', passwd='123123', port=22, bandwidth='30M', times=120, mode=1,
                  linux=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_002(self):
        """
        1.进行qmi拨号
        2.移动到无信号环境下或者屏蔽信号，观察拨号状态
        3.重新移动到有信号环境下或者解除屏蔽信号，观察拨号状态
        4.进行iperf打流
        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        qss_connection3 = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time1, qss_connection1 = self.open_qss()
            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # 正常信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False

            # 恢复默认网卡,防止断网断拨号后，与qss失去联系
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)

            # 断网
            try:
                self.enb_file_name_now = '00101-enb-no-signal.cfg'
                start_time2 = qss_connection2 = self.open_qss(False)
                self.delay_task(start_time2, qss_connection2, 100)
            except:  # noqa
                all_logger.info('已经断网')

            time.sleep(5)
            # 无信号后断网检查
            return_value_qeng = self.at_handle.send_at('at+qeng="servingcell"')
            all_logger.info(return_value_qeng)
            if 'NOCONN' not in return_value_qeng and 'CONNECT' not in return_value_qeng:
                all_logger.info("和预期一致，已经断开网络")
            else:
                all_logger.info("预期不一致，无信号模块网络没有断开")
                self.test_fail.append('预期不一致，无信号模块网络没有断开')

            # 恢复网络
            self.enb_file_name_now, _ = self.get_weak_enb_file_name()
            start_time3, qss_connection3 = self.open_qss()
            self.delay_task(start_time3, qss_connection3, 100)

            # 等待自动恢复拨号稳定
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            self.udhcpc_get_ip(self.qmi_usb_network_card_name)
            # 恢复信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'恢复信号后ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'恢复信号后ping失败:{self.enb_file_name_now}')
                return False
            # 打流测试
            iperf(ip="10.66.129.204", user='sdr', passwd='123123', port=22, bandwidth='30M', times=60, mode=1,
                  linux=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)
            self.end_task(qss_connection3)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_003(self):
        """
        1.使模块处于弱信号下，观察模块能否进入慢时钟
        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss()
            self.delay_task(start_time, qss_connection, 100)
            self.check_weak_signal()  # 检查弱信号
            # 测试慢时钟
            self.set_qsclk()
            rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            if rg_flag:
                self.gpio.set_dtr_high_level()  # 默认拉高DTR
            self.linux_enter_low_power()

            if not self.at_handle.check_network():
                raise QSSWeakSignalError('找网失败')
            # self.at_handle.cfun0()
            time.sleep(60)
            self.debug_check(True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.close_lowpower()
            self.linux_enter_low_power(False, False)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

    @startup_teardown()
    def test_linux_qss_weak_signal_01_004(self):
        """
        1.进行qmi拨号
        2.在弱信号环境下进行iperf TCP打流，记录当前平均速率S1
        3.在强信号环境下进行iperf TCP打流，记录当前平均速率S2
        4.对比S2和S1
        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time1, qss_connection1 = self.open_qss()
            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # 正常信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False
            # 测速
            speed1, _, _, _ = self.speedtest_qss()

            # 恢复默认网卡,防止断网断拨号后，与qss失去联系
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)

            # 正常信号
            self.enb_file_name_now = self.enb_file_name[0]
            # qss开网
            try:
                start_time2, qss_connection2 = self.open_qss()
                self.delay_task(start_time2, qss_connection2, 100)
            except:  # noqa
                all_logger.info('完成开网')

            # 等待自动恢复拨号稳定
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            self.udhcpc_get_ip(self.qmi_usb_network_card_name)

            # 恢复信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'恢复信号后ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'恢复信号后ping失败:{self.enb_file_name_now}')
                return False
            # 测速
            speed2, _, _, _ = self.speedtest_qss()
            all_logger.info(f'正常信号速率：{speed2}, 弱信号速率：{speed1}')
            if float(speed2) < float(speed1):
                raise QSSWeakSignalError("异常！强信号速率比弱信号高")
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)
            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_005(self):
        """
        1.进行qmi拨号
        2.在弱信号环境下进行iperf TCP打流
        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss()
            self.check_weak_signal()  # 检查弱信号
            self.delay_task(start_time, qss_connection, 100)

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False
            # iperf打流测试
            iperf(ip="10.66.129.204", user='sdr', passwd='123123', port=22, bandwidth='30M', times=120, mode=1,
                  linux=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_006(self):
        """
        SA网络下无信号到有信号，SA网络恢复，拨号恢复，iperf 测速
        """
        # 获取当前所需配置文件
        _, self.enb_file_name_now = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        qss_connection3 = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time1, qss_connection1 = self.open_qss()
            self.check_weak_signal()  # 检查弱信号
            self.delay_task(start_time1, qss_connection1, 100)

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # 正常信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False

            # 恢复默认网卡,防止断网断拨号后，与qss失去联系
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)

            # 断网
            try:
                self.enb_file_name_now = '00101-enb-no-signal.cfg'
                start_time2 = qss_connection2 = self.open_qss(False)
                self.delay_task(start_time2, qss_connection2, 100)
            except:  # noqa
                all_logger.info('已经断网')

            time.sleep(5)
            # 无信号后断网检查
            return_value_qeng = self.at_handle.send_at('at+qeng="servingcell"')
            all_logger.info(return_value_qeng)
            if 'NOCONN' not in return_value_qeng and 'CONNECT' not in return_value_qeng:
                all_logger.info("和预期一致，已经断开网络")
            else:
                all_logger.info("预期不一致，无信号模块网络没有断开")
                self.test_fail.append('预期不一致，无信号模块网络没有断开')

            # 恢复网络
            _, self.enb_file_name_now = self.get_weak_enb_file_name()
            start_time3, qss_connection3 = self.open_qss()
            self.delay_task(start_time3, qss_connection3, 100)

            # 等待自动恢复拨号稳定
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            self.udhcpc_get_ip(self.qmi_usb_network_card_name)
            # 恢复信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'恢复信号后ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'恢复信号后ping失败:{self.enb_file_name_now}')
                return False
            # 打流测试
            iperf(ip="10.66.129.204", user='sdr', passwd='123123', port=22, bandwidth='30M', times=60, mode=1,
                  linux=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)
            self.end_task(qss_connection3)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_007(self):
        """
        NSA网络下无信号到有信号，NSA网络恢复，拨号恢复，iperf 测速
        """
        # 获取当前所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        qss_connection3 = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time1, qss_connection1 = self.open_qss()
            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # 正常信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False

            # 恢复默认网卡,防止断网断拨号后，与qss失去联系
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)

            # 断网
            try:
                self.enb_file_name_now = '00101-enb-no-signal.cfg'
                start_time2 = qss_connection2 = self.open_qss(False)
                self.delay_task(start_time2, qss_connection2, 100)
            except:  # noqa
                all_logger.info('已经断网')

            time.sleep(5)
            # 无信号后断网检查
            return_value_qeng = self.at_handle.send_at('at+qeng="servingcell"')
            all_logger.info(return_value_qeng)
            if 'NOCONN' not in return_value_qeng and 'CONNECT' not in return_value_qeng:
                all_logger.info("和预期一致，已经断开网络")
            else:
                all_logger.info("预期不一致，无信号模块网络没有断开")
                self.test_fail.append('预期不一致，无信号模块网络没有断开')

            # 恢复网络
            self.enb_file_name_now, _ = self.get_weak_enb_file_name()
            start_time3, qss_connection3 = self.open_qss()
            self.delay_task(start_time3, qss_connection3, 100)

            # 等待自动恢复拨号稳定
            time.sleep(60)
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            self.udhcpc_get_ip(self.qmi_usb_network_card_name)
            # 恢复信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'恢复信号后ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'恢复信号后ping失败:{self.enb_file_name_now}')
                return False
            # 打流测试
            iperf(ip="10.66.129.204", user='sdr', passwd='123123', port=22, bandwidth='30M', times=60, mode=1,
                  linux=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)
            self.end_task(qss_connection3)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_008_(self):
        """
        1. 移除天线,放进屏蔽箱/屏蔽服5min
        2. 另一方给此模块发送短信
        3. 拿出屏蔽箱/屏蔽服后,接收信息正常
        4. 确认可收到一条数短信且查看QXDM log确认模块有回应短信的ACK于短信中心
        """
        pass  # 暂时无法实现

    @startup_teardown()
    def test_linux_qss_weak_signal_01_009(self):
        """
        1、查询网络状态
        2、激活APN
        3、查询获取IP地址
        4、使模块掉网
        5、再次查询激活状态
        6、查询IP地址

        1、AT+QNWPREFCFG= "mode_pref",NR5G
        AT+CGDCONT?
        AT+CREG?;+CGREG?;+CEREG?;+C5GREG?;+COPS?;+CSQ
        2、AT+CGACT=1,1
        3、AT+CGACT?
        AT+CGPADDR=1
        4、AT+CREG?;+CGREG?;+CEREG?;+C5GREG?;+COPS?;+CSQ
        5、AT+CGACT?
        6、AT+CGPADDR
        7、AT+QNWPREFCFG= "mode_pref",LTE:NR5G


        1、AT+QNWPREFCFG= "mode_pref",NR5G

              OK
             AT+CGDCONT?+CGDCONT: 1,"IPV4V6","","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0",0,0,0,0,,,,,,,,,"",,,,0
             +CGDCONT: 2,"IPV4V6","ims","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0",0,0,0,0,,,,,,,,,"",,,,0
             +CGDCONT: 3,"IPV4V6","sos","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0",0,0,0,1,,,,,,,,,"",,,,0

             OK
             AT+CREG?;+CGREG?;+CEREG?;+C5GREG?;+COPS?;+CSQ
             +CREG: 0,0

             +CGREG: 0,0

             +CEREG: 0,0

             +C5GREG: 0,1

             +COPS: 0,0,"CHINA MOBILE",11

             +CSQ: 5,99

             OK
        2、AT+CGACT=1,1

              OK
             AT+CGACT?
             +CGACT: 1,1
             +CGACT: 2,0
             +CGACT: 3,0

             OK
        3、AT+CGPADDR=1
          +CGPADDR: 1,"10.152.205.78","36.14.4.90.4.4.60.201.0.0.0.0.0.0.0.1"

             OK
        4、+CGREG: 2,0

        +CGREG: 2,0

        +CEREG: 2,0

        +COPS: 2

        +CSQ: 7,99

        OK
        5、AT+CGACT?
               +CGACT: 1,0
               +CGACT: 2,0
               +CGACT: 3,0

                OK
        6、AT+CGPADDR
               +CGPADDR: 1,""（X6X结果）
                +CGPADDR: 2,"0.0.0.0","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"
                +CGPADDR: 3,"0.0.0.0","0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0"

               OK
        7、AT+QNWPREFCFG= "mode_pref",LTE:NR5G

      OK
        """
        self.bound_network('SA')
        # 获取本次测试所需配置文件
        _, self.enb_file_name_now = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        exc_type = None
        exc_value = None
        try:
            start_time1, qss_connection1 = self.open_qss()

            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            retunrn_cgdcont = self.at_handle.send_at('AT+CGDCONT?')
            all_logger.info(retunrn_cgdcont)

            return_c5greg = self.at_handle.send_at('AT+CREG?;+CGREG?;+CEREG?;+C5GREG?;+COPS?;+CSQ')
            all_logger.info(return_c5greg)
            if '+C5GREG: 0,1' not in return_c5greg:
                raise QSSWeakSignalError("C5GREG返回值异常")

            # 激活APN
            self.at_handle.send_at('AT+CGACT=1,1', 10)
            return_cgact = self.at_handle.send_at('AT+CGACT?')
            all_logger.info(return_cgact)
            if '+CGACT: 1,1' not in return_cgact:
                raise QSSWeakSignalError(f"AT+CGACT?查询结果异常!")

            # 查询IP
            return_cgpaddr = self.at_handle.send_at('AT+CGPADDR=1', 3)
            all_logger.info(return_cgpaddr)
            if '+CGPADDR: 1,"192.168.' not in return_cgpaddr:
                raise QSSWeakSignalError('查询获取IP异常')

            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time2, qss_connection2 = self.open_qss(False)
            all_logger.info('等待网络稳定')
            time.sleep(10)
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(5)

            self.send_at_until_rusult('AT+CGACT?', '+CGACT: 1,0')
            self.send_at_until_rusult('AT+CGPADDR', '+CGPADDR: 1,"0.0.0.0')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto', 3)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_010(self):
        """
        Auto模式弱信号下,激活成功后掉网
        1、查询网络状态
        2、激活APN
        3、查询获取IP地址
        4、使模块掉网
        5、再次查询激活状态
        6、查询IP地址
        """
        # 获取本次测试所需配置文件
        _, self.enb_file_name_now = self.get_weak_enb_file_name()

        qss_connection1 = ''
        qss_connection2 = ''
        exc_type = None
        exc_value = None
        try:
            start_time1, qss_connection1 = self.open_qss()

            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            retunrn_cgdcont = self.at_handle.send_at('AT+CGDCONT?')
            all_logger.info(retunrn_cgdcont)

            return_c5greg = self.at_handle.send_at('AT+CREG?;+CGREG?;+CEREG?;+C5GREG?;+COPS?;+CSQ')
            all_logger.info(return_c5greg)
            if '+C5GREG: 0,1' not in return_c5greg:
                raise QSSWeakSignalError("C5GREG返回值异常")

            # 激活APN
            self.at_handle.send_at('AT+CGACT=1,1', 10)
            return_cgact = self.at_handle.send_at('AT+CGACT?')
            all_logger.info(return_cgact)
            if '+CGACT: 1,1' not in return_cgact:
                raise QSSWeakSignalError(f"AT+CGACT?查询结果异常!")

            # 查询IP
            return_cgpaddr = self.at_handle.send_at('AT+CGPADDR=1', 3)
            all_logger.info(return_cgpaddr)
            if '+CGPADDR: 1,"192.168.' not in return_cgpaddr:
                raise QSSWeakSignalError('查询获取IP异常')

            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time2, qss_connection2 = self.open_qss(False)
            all_logger.info('等待网络稳定')
            time.sleep(10)
            self.at_handle.cfun0()
            time.sleep(5)
            self.at_handle.cfun1()
            time.sleep(5)

            self.send_at_until_rusult('AT+CGACT?', '+CGACT: 1,0')
            self.send_at_until_rusult('AT+CGPADDR', '+CGPADDR: 1,"0.0.0.0')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_011(self):
        """
        1.模块放到屏蔽箱或者屏蔽房，查询当前信号值（不可以拔天线）
        2.查询当前网络运营商
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time, qss_connection = self.open_qss(False)
            self.delay_task(start_time, qss_connection, 250)
            all_logger.info('等待网络稳定')

            time.sleep(10)
            return_csq = self.at_handle.send_at('AT+csq', 3)
            all_logger.info(return_csq)

            return_value = self.at_handle.send_at('AT+COPS=?', 180)
            all_logger.info(return_value)

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_012(self):
        """
        没有信号环境下，屏蔽房（或屏蔽服）屏蔽5min正常（确认是否会Dump）
        1.查询当前注网
        2.放入屏蔽箱并查询信号以及网络状态
        3.拿出后观察能否正常快速注网
        4.拨号并浏览网页
        """
        # 设置DUMP模式
        self.at_handle.send_at('at+QCFG="modemrstlevel",0', 3)
        self.at_handle.send_at('at+QCFG="aprstlevel",0', 3)
        # 获取当前所需配置文件
        _, self.enb_file_name_now = self.get_weak_enb_file_name()
        qss_connection1 = ''
        qss_connection2 = ''
        qss_connection3 = ''
        qcm = None
        exc_type = None
        exc_value = None
        try:
            start_time1, qss_connection1 = self.open_qss()

            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            # 拨号
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(self.qmi_usb_network_card_name),
                                                     ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            self.check_linux_qmi_and_driver_name()
            # 正常信号ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False

            # 无信号
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time2, qss_connection2 = self.open_qss(False)

            # 无信号 ping测试
            result_ping_fail = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
            if not result_ping_fail:
                all_logger.info("和预期一致，ping失败")
            else:
                all_logger.info("和预期不一致，无信号时ping没有失败")
                self.test_fail.append('和预期不一致，无信号时ping没有失败')
            # 持续监测5min是否会出现dump
            self.dump_check()

            # 恢复信号
            _, self.enb_file_name_now = self.get_weak_enb_file_name()
            start_time3, qss_connection3 = self.open_qss()

            # 等待自动恢复拨号稳定
            time.sleep(60)
            # 恢复信号ping测试
            for k in range(10):
                result = self.ping_get_connect_status(network_card_name=self.qmi_usb_network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'恢复信号后ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'恢复信号后ping失败:{self.enb_file_name_now}')
                return False

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)
            self.end_task(qss_connection3)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_013_(self):
        """
        1、禁用SA
        2、设置CSQ为1
        3、查看当前CSQ配置参数值
        4、插拔天线==================暂时无法实现
        5、设置CSQ为0
        6、插拔天线
        7、启用SA
        """

    @startup_teardown()
    def test_linux_qss_weak_signal_01_014(self):
        """
        有卡无信号，默认配置的情况下，查询主小区以及临近小区
        1、拔掉天线，并AT+CSQ查询
        2、配置AUTO模式
        3、查询当前网络及网络信号值
        4、查询主小区
        5、查询临近小区（又称辅小区）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time, qss_connection = self.open_qss(False)
            self.delay_task(start_time, qss_connection, 250)

            return_csq = self.at_handle.send_at('AT+csq', 3)
            all_logger.info(return_csq)

            return_servingcell = self.at_handle.send_at('AT+QENG="SERVINGCELL"', 3)
            all_logger.info(return_servingcell)
            if 'SEARCH' not in return_servingcell and 'LIMSRV' not in return_servingcell:
                raise QSSWeakSignalError('无信号AT+QENG="SERVINGCELL"查询结果异常！')

            return_neighbourcell = self.at_handle.send_at('at+qeng="neighbourcell"', 3)
            all_logger.info(return_neighbourcell)
            if '+QENG' in return_neighbourcell or 'OK' not in return_neighbourcell:
                raise QSSWeakSignalError('无信号at+qeng="neighbourcell"查询结果异常！')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)
            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_015(self):
        """
        屏蔽环境，180S扫不到小区，AT+QSCAN返回OK
        1.执行AT+QSCAN=3
        2.180S返回仅OK（关注返回时间是否是180S）
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time, qss_connection = self.open_qss(False)
            self.delay_task(start_time, qss_connection, 220)

            return_qscan = self.at_handle.send_at('AT+qscan=3', 180)
            all_logger.info(return_qscan)
            if '+QSCAN' in return_qscan or 'OK' not in return_qscan:
                all_logger.info(return_qscan)
                raise QSSWeakSignalError('无信号AT+QSCAN=3查询结果异常！')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)
            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_016(self):
        """
        弱信号下拨打写入模块的有SIM卡（<type>=1）类型的紧急呼叫号码
        1.拔除模块天线后查询信号值是否降低到弱信号区间范围
        2.拨打已写入模块的有SIM卡（<type>=1）类型的紧急呼叫号码并观察网络是否发生回落
        3.CLCC查询当前通话状态并观察DSCI信息上报

        4.AT+QECCNUM=1,1,"133"
        5.AT+QECCNUM=0,1
        6.AT^DSCI=1
        7.ATD133;
        8.AT+CLCC


        4.OK
        5.+QECCNUM: 1,"911","112","000","133"

        OK
        6.OK
        7.OK
        按紧急呼叫号码流程执行,提示"匪警请拨110……."
        LTE网络不会回落
        8.^DSCI: 2,0,2,0,133,129

        ^DSCI: 2,0,7,0,133,129

        +CLCC: 1,1,0,1,0,"",128

        +CLCC: 2,0,3,0,0,"133",129（第三位参数值显示为3或者0都可以，这个根据当地网络状态，3表示转服务台，0表示人工台接听）

        OK


        4.添加号码成功，返回OK
        5.查询显示已添加的有SIM卡类型紧急呼叫号码
        6.成功开启DSCI自动上报
        7.按紧急呼叫号码流程执行，提示“匪警请拨110…….”
        LTE网络不会回落
        8.显示当前紧急通话号码，同时有DSCI相关信息上报

        """
        # 获取本次开网所需配置文件
        self.enb_file_name_now, _ = self.get_weak_enb_file_name()

        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss(ims_open=True)
            self.delay_task(start_time, qss_connection, 100)
            self.check_weak_signal()  # 检查弱信号

            # 添加紧急呼叫号码
            self.at_handle.send_at('AT+QECCNUM=1,1,"133"', 3)
            return_qeccnum = self.at_handle.send_at('AT+QECCNUM=0,1')
            all_logger.info(return_qeccnum)
            if '133' not in return_qeccnum:
                raise QSSWeakSignalError('紧急号码查询异常！')
            # 打开dsci上报
            self.at_handle.send_at('AT^DSCI=1', 3)
            return_atd = self.at_handle.send_at('ATD133;', 3)
            all_logger.info(return_atd)
            if 'NO CARRIER' in return_atd:
                raise QSSWeakSignalError('ATD返回NO CARRIER，请确认当前版本是否支持call')
            return_clcc = self.at_handle.send_at('AT+CLCC')
            all_logger.info(return_clcc)
            if '+CLCC: 2,0,3,0,0,"133",129' not in return_clcc and '+CLCC: 3,0,2,0,0,"133",129' not in return_clcc:
                raise QSSWeakSignalError('AT+CLCC查询紧急呼叫结果异常！')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('AT^DSCI=0', 3)
            self.at_handle.send_at('ATH', 3)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_017(self):
        """
        无信号时拨打写入模块的有SIM卡（<type>=1）类型的紧急呼叫号码
        1.模块当前处于无信号状态
        2.无法呼出，模块无异常(无信号状态下模块无法驻留小区，所以也无法进行紧急通话业务)
        """
        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # 掉网
            self.enb_file_name_now = '00101-enb-no-signal.cfg'
            start_time, qss_connection = self.open_qss(False)
            self.delay_task(start_time, qss_connection, 220)

            # 添加紧急呼叫号码
            self.at_handle.send_at('AT+QECCNUM=1,1,"133"', 3)
            return_qeccnum = self.at_handle.send_at('AT+QECCNUM=0,1')
            all_logger.info(return_qeccnum)
            if '133' not in return_qeccnum:
                raise QSSWeakSignalError('紧急号码查询异常！')

            return_atd = self.at_handle.send_at('ATD133;', 3)
            all_logger.info(return_atd)
            if 'NO CARRIER' not in return_atd and 'OK' not in return_atd:
                raise QSSWeakSignalError('异常！无信号QTD未返回NO CARRIER')

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('ATH', 3)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)
            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_018(self):
        """
        在弱信号下检查网络回落情况以及通话保持情况
        1.进行VOLTE通话
        2.对方接听
        3.模块弱信号下，查询信号值及RSRP,RSRQ值
        4.查询网络状态

        """
        # 获取本次开网所需配置文件
        _, self.enb_file_name_now = self.get_weak_enb_file_name()

        qss_connection = ''
        exc_type = None
        exc_value = None
        try:
            # qss开网
            start_time, qss_connection = self.open_qss(ims_open=True)
            self.delay_task(start_time, qss_connection, 100)
            self.check_weak_signal()  # 检查弱信号

            # 电话功能禁用验证
            self.delay_task(start_time, qss_connection, 60)
            call_result = self.qss_call()
            if not call_result:
                raise QSSWeakSignalError("弱信号下，通话异常！")
            self.at_handle.send_at('ATH', 3)

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('ATH', 3)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_weak_signal_01_019(self):
        """
        1.插上天线，查询信号值
        2.查询网络状态
        3.挂断电话
        4.查询网络动态

        1.信号值增加，直至峰值,CSQ范围在29~31,RSRP,RSRQ值增加
        2.插上天线后网络仍然保持在LTE，通话正常
        3.挂断电话，返回OK
        4.LTE网络状态无变化
        """
        # 获取当前所需配置文件
        self.enb_file_name_now,  _ = self.get_weak_enb_file_name()
        qss_connection1 = ''
        qss_connection2 = ''
        exc_type = None
        exc_value = None
        try:
            start_time1, qss_connection1 = self.open_qss(ims_open=True)

            self.delay_task(start_time1, qss_connection1, 100)
            self.check_weak_signal()  # 检查弱信号

            # 电话功能验证
            self.delay_task(start_time1, qss_connection1, 60)
            call_result1 = self.qss_call()
            if not call_result1:
                raise QSSWeakSignalError("弱信号下，通话异常！")
            self.at_handle.send_at('ATH', 3)

            # 恢复正常信号
            self.enb_file_name_now = self.enb_file_name[0]
            start_time2, qss_connection2 = self.open_qss()

            # 等待稳定
            time.sleep(60)
            # 电话功能验证
            self.delay_task(start_time2, qss_connection2, 60)
            call_result2 = self.qss_call()
            if not call_result2:
                raise QSSWeakSignalError("弱信号下，通话异常！")
            self.at_handle.send_at('ATH', 3)

        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handle.send_at('ATH', 3)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.end_task(qss_connection1)
            self.end_task(qss_connection2)

            if self.test_fail:  # 提示异常并且不影响别的band继续测试
                raise QSSWeakSignalError(f"weak signal 出现异常：{self.test_fail}")


if __name__ == "__main__":
    p_list = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB0',
        'wwan_path': '/home/ubuntu/Tools/Drivers/qmi_wwan_q',
        'qmi_usb_network_card_name': 'wwan0_1',
        'local_network_card_name': 'eth1',
        'qss_ip': '10.66.129.204',
        'local_ip': '66.66.66.66',
        'node_name': 'jeckson_test',
        "mme_file_name": "00101-mme-ims.cfg",
        "enb_file_name": [
            "00101-endc-gnb-nsa-b3n78.cfg",
            "tdd-gnb-sa-n78-weak.cfg",
            "tdd-gnb-sa-n41-weak.cfg",
            "gnb-nsa-b3n78-weak.cfg",
            "gnb-nsa-b3n41-weak.cfg",
        ],
        "ims_file_name": "00101-ims.cfg",
        'name_sub_version': 'RM502QAEAAR13A02M4G_01.001.01.001V03',
        'chrome_driver_path': '/home/ubuntu/Desktop/Function_qss/20221114/standard_tws-develop/test/chromedriver',
        'default_sa_band': '1:2:3:5:7:8:12:20:25:28:38:40:41:48:66:71:77:78:79',
        'default_nsa_band': '1:2:3:5:7:8:12:20:25:28:38:40:41:48:66:71:77:78:79',
        'default_lte_band': '1:2:3:4:5:7:8:12:13:14:18:19:20:25:26:28:29:30:32:34:38:39:40:41:42:43:46:48:66:71',
        'default_wcdma_band': '1:2:3:4:5:6:8:19',
    }
    qss_test = LinuxQSSWeakSignal(**p_list)
    # qss_test.test_linux_qss_weak_signal_01_000()
    # qss_test.test_linux_qss_weak_signal_01_001()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_002()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_003()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_004()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_005()  # 完成精简改造 iperf断流
    # qss_test.test_linux_qss_weak_signal_01_006()  # 完成精简改造  PASS(x6x) 拨号经常ping不通
    # qss_test.test_linux_qss_weak_signal_01_007()  # 完成精简改造  PASS(x6x) 拨号经常ping不通

    # qss_test.test_linux_qss_weak_signal_01_009()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_010()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_011()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_012()  # 完成精简改造  拨号后获取IP失败

    # qss_test.test_linux_qss_weak_signal_01_014()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_015()  # 完成精简改造  PASS(x6x)
    # qss_test.test_linux_qss_weak_signal_01_016()  # 完成精简改造  PASS(x6x) 133nocarrier?
    # qss_test.test_linux_qss_weak_signal_01_017()  # 完成精简改造  PASS(x6x) 20200?
    # qss_test.test_linux_qss_weak_signal_01_018()  # 完成精简改造 PASS(x6x)
    qss_test.test_linux_qss_weak_signal_01_019()  # 完成精简改造  PASS(x6x)SA有一定概率注网后再次掉网
