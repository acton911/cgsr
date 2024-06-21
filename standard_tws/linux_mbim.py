from utils.functions.decorators import startup_teardown
from utils.cases.linux_mbim_manager import LinuxMBIMManager
from utils.functions.iperf import iperf
from utils.functions.linux_api import QuectelCMThread
import time
import sys
from utils.logger.logging_handles import all_logger
import subprocess
import traceback


class LinuxMBIM(LinuxMBIMManager):
    @startup_teardown()
    def test_linux_mbim_1(self):
        """
        查询当前MBIM驱动加载成功
        """
        time.sleep(60)  # 防止发AT口还未加载、发AT不生效等问题发生
        try:
            self.check_and_set_pcie_data_interface()
            self.enter_mbim_mode()
        finally:
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_2(self):
        """
        SA网络下quectel-CM工具拨号测试
        """
        self.enter_mbim_mode()
        self.at_handler.bound_network("SA")
        self.at_handler.check_network()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_3(self):
        """
        NSA网络下quectel-CM工具拨号测试
        """
        self.enter_mbim_mode()
        self.at_handler.bound_network("NSA")

        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.extra_ethernet_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.extra_ethernet_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread('quectel-CM -4 -6')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            # 检查wwan0网卡消失
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.check_linux_wwan0_network_card_disappear()
            self.linux_api.check_intranet(self.extra_ethernet_name)
            self.at_handler.bound_network("SA")
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_4(self):
        """
        重复连接+数传+断开连接10次
        """
        all_logger.info('开始测试断重复连接+数传+断开连接10次')
        for i in range(10):
            all_logger.info('开始第{}次拨号'.format(i + 1))
            qcm = None
            exc_type = None
            exc_value = None
            try:
                self.enter_mbim_mode()
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
                all_logger.info('start')
                # 检查拨号
                self.check_linux_mbim_and_driver_name()
                self.linux_api.ping_get_connect_status()
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, _ = sys.exc_info()
            finally:
                all_logger.info('开始第{}次断开拨号'.format(i + 1))
                # 断开连接
                qcm.ctrl_c()
                qcm.terminate()
                ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
                all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
                self.udhcpc_get_ip(self.extra_ethernet_name)
                # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
                # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
                self.linux_api.check_intranet(self.extra_ethernet_name)
                # 检查wwan0网卡消失
                self.check_linux_wwan0_network_card_disappear()
                if exc_type and exc_value:
                    raise exc_type(exc_value)
                # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_5(self):
        """
        拨号后指定带宽30Miperf连接五分钟
        """
        self.enter_mbim_mode()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
            ipv4_get = subprocess.getoutput("ifconfig wwan0 | grep 'inet '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1")
            all_logger.info("ifconfig wwan0 | grep 'inet '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1\r\n{}".format(ipv4_get))
            iperf(bandwidth='30M', times=300)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_6(self):
        """
        重启后进行IPV4V6拨号
        """
        self.enter_mbim_mode()
        # 检查网络
        self.at_handler.check_network()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['hard_reset'])
    def test_linux_mbim_7(self):
        """
        验证CFUN切换后MBIM能否正常数传连接
        """
        # self.cfun_0_1_4()
        self.enter_mbim_mode()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()

            self.at_handler.send_at('AT+CFUN=0', 15)
            self.at_handler.send_at('AT+CFUN=1', 15)
            # 检查网络
            self.at_handler.check_network()
            time.sleep(30)  # 等待拨号稳定
            self.linux_api.ping_get_connect_status()

            self.at_handler.send_at('AT+CFUN=4', 15)
            # 检查网络
            self.at_handler.check_network()
            self.at_handler.send_at('AT+CFUN=1', 15)
            time.sleep(30)  # 等待拨号稳定
            self.linux_api.ping_get_connect_status()

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_8(self):
        """
        LTE网络下quectel-CM工具拨号测试
        """
        self.enter_mbim_mode()
        self.at_handler.bound_network("LTE")

        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            self.at_handler.bound_network("SA")
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_9(self):
        """
        LTE拨号后指定带宽10Miperf连接五分钟
        """
        self.enter_mbim_mode()
        self.at_handler.bound_network("LTE")

        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
            ipv4_get = subprocess.getoutput("ifconfig wwan0 | grep 'inet '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1")
            all_logger.info("ifconfig wwan0 | grep 'inet '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1\r\n{}".format(ipv4_get))
            iperf(bandwidth='10M', times=300)

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            self.at_handler.bound_network("SA")
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['linux_mbim_disconnect'])
    def test_linux_mbim_10(self):
        """
        来电后数传
        """
        self.enter_mbim_mode()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
            self.dial_check_network()

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()
        """
        self.check_linux_mbim_before_connect()
        self.linux_mbim_connect()
        self.check_linux_mbim_after_connect()
        self.linux_api.ping_get_connect_status()
        """
        # self.dial_check_network()

    @startup_teardown(teardown=['linux_mbim_disconnect'])
    def test_linux_mbim_11(self):
        """
        来短信后数传
        """
        """
        self.check_linux_mbim_before_connect()
        self.linux_mbim_connect()
        self.check_linux_mbim_after_connect()
        self.linux_api.ping_get_connect_status()
        self.send_sms_check_network()
        """
        self.enter_mbim_mode()
        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
            self.send_msg()
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_12(self):
        """
        拨号后禁用网卡
        """
        self.enter_mbim_mode()
        qcm = None
        exc_type = None
        exc_value = None
        try:
            return_value = subprocess.getoutput('ifconfig wwan0 down')
            all_logger.info('ifconfig wwan0 down\n{}'.format(return_value))
            time.sleep(5)
            return_value = subprocess.getoutput('ifconfig wwan0 up')
            all_logger.info('ifconfig wwan0 up\n{}'.format(return_value))
            time.sleep(5)
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_13(self):
        """
        解pin后拨号
        """
        self.enter_mbim_mode()
        self.at_handler.send_at('AT+CLCK="SC",1,"1234"')
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(20)
        self.at_handler.send_at('AT+CPIN=1234')
        time.sleep(20)
        self.at_handler.check_network()

        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()

        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"', 10)
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_mbim_14(self):
        """
        WCDMA网络下quectel-CM工具拨号测试
        """
        self.enter_mbim_mode()
        self.at_handler.bound_network("WCDMA")

        qcm = None
        exc_type = None
        exc_value = None
        try:
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
            self.check_linux_mbim_and_driver_name()
            self.linux_api.ping_get_connect_status()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # 检查wwan0网卡消失
            self.check_linux_wwan0_network_card_disappear()
            self.at_handler.bound_network("SA")
            if exc_type and exc_value:
                raise exc_type(exc_value)
            # self.reset_usbnet()

    @startup_teardown(startup=['hard_reset'],
                      teardown=['linux_mbim_disconnect'])
    def test_linux_mbim_15(self):
        """
        MBIM自动拨号连接正常
        """
        try:
            self.enter_mbim_mode()
            all_logger.info("apt install modemmanager -y")
            subprocess.getoutput('apt install modemmanager -y')
            time.sleep(20)
            all_logger.info("ModemManager start&")
            subprocess.run('ModemManager start&', shell=True)
            time.sleep(20)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.extra_ethernet_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.extra_ethernet_name, ifconfig_down_value))
            time.sleep(20)
            self.check_linux_mbim_before_connect()
            self.linux_mbim_connect()
            self.check_linux_mbim_after_connect()
            self.linux_api.ping_get_connect_status()
            self.linux_api.ping_get_connect_status(ipv6_flag=True)
        finally:
            # apt remove modemmanager -y
            # killall ModemManager start
            all_logger.info("apt remove modemmanager -y")
            subprocess.getoutput('apt remove modemmanager -y')
            time.sleep(20)
            all_logger.info("killall ModemManager start")
            subprocess.getoutput('killall ModemManager start')
            time.sleep(10)
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.extra_ethernet_name))  # 启用本地网卡
            all_logger.info('ifconfig {} up\r\n{}'.format(self.extra_ethernet_name, ifconfig_up_value))
            self.udhcpc_get_ip(self.extra_ethernet_name)
            # udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.extra_ethernet_name))  # get ip
            # all_logger.info('udhcpc -i {}\r\n{}'.format(self.extra_ethernet_name, udhcpc_value))
            self.linux_api.check_intranet(self.extra_ethernet_name)
            # self.reset_usbnet()

    def test_linux_mbim_16(self):
        """
        电脑重启
        @return:
        """
        if not self.reboot.get_restart_flag():
            self.test_linux_mbim_2()
            self.reboot.restart_computer()
        else:
            self.test_linux_mbim_2()


if __name__ == "__main__":
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'imei': '869710030002905',
        'phone_number': '18714813160',
        'extra_ethernet_name': 'eth0'
    }
    linux_mbim = LinuxMBIM(**param_dict)
    # linux_mbim.test_linux_mbim_1()
    linux_mbim.test_linux_mbim_2()
    # linux_mbim.test_linux_mbim_3()
    # linux_mbim.test_linux_mbim_4()
    # linux_mbim.test_linux_mbim_5()
    # linux_mbim.test_linux_mbim_6()
    # linux_mbim.test_linux_mbim_7()
    # linux_mbim.test_linux_mbim_8()
    # linux_mbim.test_linux_mbim_9()
    # linux_mbim.test_linux_mbim_10()
    # linux_mbim.test_linux_mbim_11()
    # linux_mbim.test_linux_mbim_12()
    # linux_mbim.test_linux_mbim_13()
    # linux_mbim.test_linux_mbim_14()
    # linux_mbim.test_linux_mbim_15()
