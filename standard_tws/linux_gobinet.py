from utils.functions.decorators import startup_teardown
from utils.cases.linux_gobinet_manager import LinuxGobiNetManager
from utils.functions.linux_api import QuectelCMThread
import time
import sys
from utils.logger.logging_handles import all_logger
from utils.functions.iperf import iperf
import subprocess
import traceback


class LinuxGobiNet(LinuxGobiNetManager):

    @startup_teardown()
    def test_linux_gobinet_1(self):
        # 设置gobinet拨号后重启
        time.sleep(60)
        self.check_and_set_pcie_data_interface()
        time.sleep(20)
        self.set_linux_gobinet()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.readline_keyword('PB DONE', timout=60)
        self.at_handler.bound_network("SA")
        self.at_handler.check_network()

    @startup_teardown()
    def test_linux_gobinet_2(self):
        # 卸载其他网卡驱动，编译GobiNet网卡驱动
        self.remove_all_network_card_driver()
        self.compile_gobinet_driver()

    @startup_teardown()
    def test_linux_gobinet_3(self):
        # Check Linux网卡驱动信息
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.readline_keyword('PB DONE', timout=60)
        self.load_gobinet_drive()
        all_logger.info('检查GobiNet驱动加载')
        self.check_gobinet_driver()

    def test_linux_gobinet_18(self):
        """
        拨号后禁用网卡
        """
        qcm = None
        exc_type = None
        exc_value = None
        try:
            return_value = subprocess.getoutput('ifconfig usb0 down')
            all_logger.info(f'ifconfig usb0 down\n{return_value}')
            time.sleep(5)
            return_value = subprocess.getoutput('ifconfig usb0 up')
            all_logger.info(f'ifconfig usb0 up\n{return_value}')
            time.sleep(5)
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')  #
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_6(self):
        """
        5G网络下quectel-CM工具拨号测试
        """
        # SA
        self.at_handler.bound_network("SA")
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')  #
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_5(self):
        """
        重复连接+数传+断开连接10次
        """
        all_logger.info('开始测试断重复连接+数传+断开连接5次')
        for i in range(5):
            all_logger.info(f'开始第{i + 1}次拨号')
            qcm = None
            exc_type = None
            exc_value = None
            try:
                ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
                all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
                time.sleep(20)
                # set quectel-CM
                qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
                qcm.setDaemon(True)
                # 检查网络
                self.at_handler.check_network()
                # Linux quectel-CM拨号
                qcm.start()
                time.sleep(30)  # 等待拨号稳定
                all_logger.info('start')
                self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            except Exception as e:
                all_logger.info(e)
                exc_type, exc_value, _ = sys.exc_info()
            finally:
                all_logger.info(f'开始第{i + 1}次断开拨号')
                # 断开连接
                qcm.ctrl_c()
                qcm.terminate()
                ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
                all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
                udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
                all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
                self.linux_api.check_intranet(self.extra_ethernet_name)
                if exc_type and exc_value:
                    raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_9(self):
        """
        拨号后cfun切换能自动连接
        """
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(10)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            self.at_handler.send_at('AT+CFUN=0', 15)
            self.at_handler.send_at('AT+CFUN=1', 15)
            time.sleep(30)  # 等待拨号稳定
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_16(self):
        """
        重启后进行IPV4V6拨号
        """
        q = None
        que = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            q.setDaemon(True)
            q.start()
            self.at_handler.cfun1_1()
            q.ctrl_c()
            q.terminate()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.readline_keyword('PB DONE', timout=60)
            self.load_gobinet_drive()
            all_logger.info('检查GobiNet驱动加载')
            self.check_gobinet_driver()
            que = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            que.setDaemon(True)
            que.start()
            time.sleep(25)
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            que.ctrl_c()
            que.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_19(self):
        """
        仅LTE网络下拨号后指定带宽10M iperf连接五分钟
        """
        self.at_handler.bound_network("LTE")
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            self.get_netcard_ip()
            iperf(bandwidth='10M', times=300)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_20(self):
        """
        5G网络下拨号后指定带宽30M iperf连接五分钟
        """
        self.at_handler.bound_network("SA")
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            self.get_netcard_ip()
            iperf(bandwidth='30M', times=300)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_4(self):
        """
        LTE网络下quectel-CM工具拨号测试
        """
        self.at_handler.bound_network("LTE")
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_17(self):
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            # 发送短信
            self.send_sms_check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_12(self):
        """
        锁SIM卡
        """
        self.at_handler.set_sim_pin()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.at_handler.readline_keyword('PB DONE', timout=60)
        self.load_gobinet_drive()
        all_logger.info('检查GobiNet驱动加载')
        self.check_gobinet_driver()
        qcm = None
        exc_type = None
        exc_value = None
        try:
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查网络
            self.gobinet_non_network_check()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            self.at_handler.send_at("AT+CPIN=1234")
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"')
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.at_handler.readline_keyword('PB DONE', timout=60)
            time.sleep(2)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_13(self):
        """
        模块解PIN后继续拨号测试
        """
        time.sleep(2)
        self.at_handler.bound_network('SA')
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_gobinet_7(self):
        """
        WCDMA网络下quectel-CM工具拨号测试
        """
        self.at_handler.bound_network("WCDMA")

        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            time.sleep(2)
            self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_linux_gobinet_8(self):
        """
        GobiNet拨号数传中来电测试
        :return:
        """
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            all_logger.info('第一次拨号引导主机获取DNS')
            q = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(10)
            q.ctrl_c()
            q.terminate()
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(netcard_name=self.gobinet_network_card_name)
            qcm.setDaemon(True)
            # 检查网络
            self.at_handler.check_network()
            # Linux quectel-CM拨号
            qcm.start()
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            self.linux_api.ping_get_connect_status(network_card_name=self.gobinet_network_card_name)
            # 打电话
            self.dial_check_network()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            # 断开连接
            qcm.ctrl_c()
            qcm.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def test_linux_gobinet_03_006(self):
        """
        电脑重启
        @return:
        """
        if not self.reboot.get_restart_flag():
            self.test_linux_gobinet_6()
            self.reboot.restart_computer()
        else:
            self.test_linux_gobinet_6()


if __name__ == "__main__":
    param_dict = {
        'at_port': '/dev/ttyUSB2',
        'dm_port': '/dev/ttyUSB0',
        'gobinet_driver_path': '/home/flynn/Downloads/Gobinet/GobiNet/',
        'gobinet_network_card_name': 'usb0'
    }
    linux_gobinet = LinuxGobiNet(**param_dict)
