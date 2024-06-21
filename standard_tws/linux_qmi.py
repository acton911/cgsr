import sys
from utils.cases.linux_qmi_manager import LinuxQMIManager
import time
from utils.functions.linux_api import LinuxAPI, QuectelCMThread
from utils.logger.logging_handles import all_logger
import subprocess
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
import traceback


class LinuxQmi(LinuxQMIManager):

    @startup_teardown()
    def test_linux_qmi_1(self):
        """
        配置USBNET参数
        :return:
        """
        time.sleep(30)  # 等待升级完成后AT口正常使用
        self.check_and_set_pcie_data_interface()
        time.sleep(20)
        self.at_handle.send_at('AT+QCFG="USBNET"', timeout=3)
        self.at_handle.send_at('AT+QCFG="USBNET",0', timeout=3)
        self.at_handle.check_network()

    @startup_teardown()
    def test_linux_qmi_2(self):
        """
        加载qmi_wwan驱动
        :return:
        """
        self.modprobe_driver()
        self.load_wwan_driver()
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=60)
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()

    @startup_teardown()
    def test_linux_qmi_3(self):
        """
        Check Linux网卡驱动信息
        :return:
        """
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()

    @startup_teardown()
    def test_linux_qmi_4(self):
        """
        WCDMA网络下，quectel-CM工具拨号测试
        :return:
        """
        self.at_handle.bound_network('WCDMA')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_5(self):
        """
        仅LTE网络下，quectel-CM工具拨号测试
        :return:
        """
        self.at_handle.bound_network('LTE')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_6(self):
        """
        SA-5G网络下，quectel-CM工具拨号测试
        :return:
        """
        self.enter_qmi_mode()
        all_logger.info('等待网络稳定')
        time.sleep(20)
        self.at_handle.bound_network('SA')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_7(self):
        """
        NSA-5G网络下，quectel-CM工具拨号测试
        :return:
        """
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",auto')
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_15(self):
        """
        重启后进行IPV4V6拨号
        :return:
        """
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            self.at_handle.cfun1_1()
            self.check_wwan_driver(True)
            q.ctrl_c()
            q.terminate()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            self.load_qmi_wwan_q_drive()
            all_logger.info('检查qmi_wwan_q驱动加载')
            self.check_wwan_driver()
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name, ipv6_flag=True)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_16(self):
        """
        拨号后cfun切换能自动连接
        :return:
        """
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(25)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.at_handle.send_at('AT+CFUN=0', 15)
            self.at_handle.send_at('AT+CFUN=1', 15)
            time.sleep(30)  # 等待拨号稳定
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.at_handle.send_at('AT+CFUN=4', 15)
            self.at_handle.send_at('AT+CFUN=1', 15)
            time.sleep(60)  # 等待拨号稳定
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_17(self):
        """
        拨号后禁用网卡
        """
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO')
        q = None
        exc_type = None
        exc_value = None
        try:
            return_value = subprocess.getoutput(f'ifconfig {self.network_card_name} down')
            all_logger.info(f'ifconfig wwan0 down\n{return_value}')
            time.sleep(5)
            return_value = subprocess.getoutput(f'ifconfig {self.network_card_name} up')
            all_logger.info(f'ifconfig wwan0 up\n{return_value}')
            time.sleep(5)
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            q.start()
            time.sleep(60)  # 等待拨号稳定
            # 检查拨号
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_18(self):
        """
        5G网络下拨号后指定带宽30M iperf连接五分钟
        :return:
        """
        self.at_handle.bound_network('SA')
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            q.start()
            time.sleep(60)  # 等待拨号稳定
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            # 检查拨号
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.get_netcard_ip()
            iperf(bandwidth='30M', times=300)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_19(self):
        """
        仅LTE网络下拨号后指定带宽10M iperf连接五分钟
        :return:
        """
        self.at_handle.bound_network("LTE")
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            q.start()
            time.sleep(60)  # 等待拨号稳定
            # 检查拨号
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.get_netcard_ip()
            iperf(bandwidth='10M', times=300)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_13(self):
        """
        Simcard锁PIN情况下使用quectel-CM工具拨号测试 模块解PIN后继续拨号测试
        :return:
        """
        self.sim_lock()
        q = None
        exc_type = None
        exc_value = None
        try:
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(25)
            self.get_ip_address(False)
            self.dump_check()
            self.at_handle.send_at('AT+CLCK="SC",0,"1234"', timeout=5)
            time.sleep(25)
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_14(self):
        """
        重复拨号-断开-拨号连接（5次即可）测试
        :return:
        """
        all_logger.info('开始测试断重复连接+数传+断开连接5次')
        for i in range(5):
            all_logger.info(f'开始第{i + 1}次拨号')
            q = None
            exc_type = None
            exc_value = None
            try:
                ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
                all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
                time.sleep(20)
                # set quectel-CM
                q = QuectelCMThread(netcard_name=self.network_card_name)
                q.setDaemon(True)
                # 检查网络
                self.at_handle.check_network()
                # Linux quectel-CM拨号
                q.start()
                time.sleep(60)  # 等待拨号稳定
                self.check_route()
                time.sleep(2)
                all_logger.info('start')
                LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, _ = sys.exc_info()
            finally:
                all_logger.info(f'开始第{i + 1}次断开拨号')
                # 断开连接
                q.ctrl_c()
                q.terminate()
                ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
                all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
                udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
                all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
                self.linux_api.check_intranet(self.extra_ethernet_name)
                if exc_type and exc_value:
                    raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_qmi_8(self):
        """
        拨号后ping过程中来电和来短信
        :return:
        """
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        time.sleep(5)
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.dial_check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            time.sleep(2)
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_linux_qmi_9(self):
        """
        电脑重启
        @return:
        """
        if not self.reboot.get_restart_flag():
            self.test_linux_qmi_7()
            self.reboot.restart_computer()
        else:
            self.test_linux_qmi_7()
