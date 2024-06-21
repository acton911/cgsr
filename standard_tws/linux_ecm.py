from utils.cases.linux_ecm_manager import LinuxECMManager
import time
from utils.functions.linux_api import LinuxAPI
from utils.logger.logging_handles import all_logger
from utils.functions.iperf import iperf
import traceback
import subprocess


class LinuxEcm(LinuxECMManager):
    def test_linux_ecm_1(self):
        """
        配置USBNET参数
        :return:
        """
        time.sleep(20)
        self.check_and_set_pcie_data_interface()
        time.sleep(30)
        self.at_handle.send_at('AT+QCFG="USBNET",1')
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=60)
        time.sleep(5)  # 停一会再发指令，否则会返回ERROR
        self.check_qmapwac()
        self.chang_net('AUTO')
        self.at_handle.check_network()

    def test_linux_ecm_2(self):
        """
        卸载qmi_wwan/GbiNet驱动
        :return:
        """
        self.modprobe_driver()

    def test_linux_ecm_3(self):
        """
        检查Linux网卡驱动信息
        :return:
        """
        self.check_ecm_driver()

    def test_linux_ecm_5(self):
        """
        5G网络下，ECM拨号测试
        :return:
        """
        try:
            self.chang_net('AUTO')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(3)
            self.at_handle.check_network()
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_moudle_ip()
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_7(self):
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.chang_net('AUTO')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(10)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            time.sleep(20)
            self.get_netcard_ip()
            iperf(bandwidth='30M', times=300)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_10(self):
        try:
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.connect_ecm_net(is_connect=False)
            time.sleep(4)
            self.connect_ecm_net(is_connect=True)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_11(self):
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.chang_net('LTE')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(10)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            time.sleep(20)
            self.get_netcard_ip()
            iperf(bandwidth='10M', times=300)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_13(self):
        """
        重复拨号-断开-拨号连接（5次即可）测试
        :return:
        """
        # exc_type = None
        # exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.dial_reset_many()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)
        #     exc_type, exc_value, exc_tb = sys.exc_info()
        # finally:
        #      self.connect_local_net()
        #      self.connect_ecm_net(False)
        #      if exc_type and exc_value:
        #          raise exc_type(exc_value)
        print('hh')

    def test_linux_ecm_12(self):
        """
        ECM拨号数传中重启拨号测试
        :return:
        """
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.at_handle.send_at('AT+CFUN=1')
            time.sleep(10)
            self.at_handle.send_at('AT+QNETDEVSTATUS=1')
            self.at_handle.check_network()
            time.sleep(4)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_dial_status('+QNETDEVSTATUS: 1,1,4,1', '+QNETDEVSTATUS: 1,1,6,1')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.check_ecm_driver(True)
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            self.check_ecm_driver()
            self.at_handle.check_network()
            time.sleep(4)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_8(self):
        """
        Simcard锁PIN情况下ECM拨号，模块解PIN后继续拨号测试
        :return:
        """
        try:
            self.chang_net('AUTO')
            self.sim_lock()
            time.sleep(4)
            self.dump_check()
            self.check_dial()
            time.sleep(6)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.at_handle.send_at('AT+QNETDEVSTATUS=1')
            self.at_handle.send_at('AT+CLCK="SC",0,"1234"')
            time.sleep(30)
            self.at_handle.check_network()
            time.sleep(4)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_9(self):
        """
        重启后进行IPV4V6拨号
        :return:
        """
        try:
            operator = self.at_handle.get_operator()
            self.at_handle.set_cgdcont(operator, ip_type="IPV4V6")
            self.at_handle.set_qnetdevstatus(1)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(10)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_dial_status('+QNETDEVSTATUS: 0,1,4,1', '+QNETDEVSTATUS: 0,1,6,1')
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_14(self):
        """
        拨号后cfun切换能自动连接
        :return:
        """
        try:
            self.at_handle.check_network()
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(10)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.at_handle.send_at('AT+CFUN=0', 10)
            self.at_handle.send_at('AT+CFUN=1', 10)
            time.sleep(5)
            self.at_handle.check_network()
            self.at_handle.send_at('AT+QNETDEVSTATUS=1')
            self.at_handle.readline_keyword('+QNETDEVSTATUS: 1,1,4,1', '+QNETDEVSTATUS: 1,1,6,1', at_flag=True, at_cmd='AT+QNETDEVSTATUS?')
            self.check_ecm_driver()
            time.sleep(4)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_4(self):
        """
        LTE网络下，ECM拨号测试
        :return:
        """
        try:
            self.chang_net('LTE')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(3)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.at_handle.check_network()
            self.check_ecm_driver()
            time.sleep(15)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_moudle_ip()
        finally:
            self.chang_net('AUTO')
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_6(self):
        """
        WCDMA网络下，ECM拨号测试
        :return:
        """
        try:
            self.chang_net('WCDMA')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(3)
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.at_handle.check_network()
            time.sleep(10)
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.check_moudle_ip()
        finally:
            self.chang_net('AUTO')
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_15(self):
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.chang_net('AUTO')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(10)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.send_sms_check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_16(self):
        try:
            ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(self.local_network_card_name))  # 断开本地网
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            self.chang_net('AUTO')
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(10)
            self.at_handle.check_network()
            LinuxAPI.ping_get_connect_status(network_card_name=self.network_card_name)
            self.dial_check_network()
        finally:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)

    def test_linux_ecm_17(self):
        """
        电脑重启
        @return:
        """
        if not self.reboot.get_restart_flag():
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)
            self.test_linux_ecm_5()
            self.at_handle.cfun0()
            self.reboot.restart_computer()
        else:
            ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.local_network_card_name))  # 启用本地网
            all_logger.info('ifconfig {} up\r\n{}'.format(self.local_network_card_name, ifconfig_up_value))
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            LinuxAPI.check_intranet(self.local_network_card_name)
            time.sleep(30)
            self.at_handle.cfun1()
            self.test_linux_ecm_5()


if __name__ == '__main__':
    param_dict = {"at_port": '/dev/ttyUSB2',
                  "dm_port": '/dev/ttyUSB0',
                  "network_card_name": 'usb0',
                  "local_network_card_name": 'eth0'}
    ecm = LinuxEcm(**param_dict)
