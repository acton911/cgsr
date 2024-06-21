import sys
import time
from utils.cases.linux_pcie_qmi_manager import LinuxPcieQMIManager
from utils.functions.linux_api import QuectelCMThread, LinuxAPI
from utils.logger.logging_handles import all_logger
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
import subprocess
import traceback


class LinuxPcieQMI(LinuxPcieQMIManager):
    def test_linux_pcie_qmi_1(self):
        """
        fuse模块开机,PCI设备加载成功
        """
        self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
        self.insmod_pcie_qmi()
        time.sleep(10)
        self.check_pcie_driver()

    def test_linux_pcie_qmi_2(self):
        """
        查询模块找网状态及拨号工具编译
        """
        self.check_network_pcie()
        self.check_netcard()
        self.make_dial_tool()

    def test_linux_pcie_qmi_3(self):
        """
        quectel-CM工具拨号
        """
        self.bound_network("SA")
        self.dial()

    # def test_linux_pcie_qmi_4(self):
    #     """
    #     禁本地网，拨号成功后ping百度访问网页
    #     """
    #     self.dial()
    #
    # def test_linux_pcie_qmi_5(self):
    #     """
    #     quectel-CM -4拨IPV4
    #     """
    #     self.dial(cmd='quectel-CM -4')
    #
    # def test_linux_pcie_qmi_6(self):
    #     """
    #     quectel-CM -6拨IPV6
    #     """
    #     self.dial(cmd='quectel-CM -6', ipv6_flag=True)

    # def test_linux_pcie_qmi_7(self):
    #     """
    #     quectel-CM -4 -6拨IPV6+IPV6
    #     """
    #     self.dial(cmd='quectel-CM -4 -6')

    def test_linux_pcie_qmi_4(self):
        """
        quectel-CM工具拨号及频繁断开
        """
        for i in range(1, 11):
            all_logger.info('第{}次拨号后断开'.format(i))
            self.get_ip_address()
            self.dial()
            time.sleep(20)  # wait dial complete

    @startup_teardown()
    def test_linux_pcie_qmi_5(self):
        """
        quectel-CM工具iperf
        """
        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_QMI0')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                iperf(bandwidth='30M', times=300)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.info(e)
            all_logger.error(traceback.format_exc())
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_pcie_qmi_6(self):
        """
        验证CFUN切换后qmi能否正常数传连接
        """
        times = 10
        is_success = True
        q = None
        exc_type = None
        exc_value = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_MBIM')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                self.send_at_pcie('AT+cfun=0', 10)
                self.send_at_pcie('AT+cfun=1', 10)
                time.sleep(30)
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                self.send_at_pcie('AT+cfun=4', 10)
                self.send_at_pcie('AT+cfun=1', 10)
                time.sleep(30)
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_pcie_qmi_7(self):
        """
        quectel-CM工具拨号
        """
        self.bound_network("LTE")
        time.sleep(20)
        self.dial()
        self.bound_network("SA")

    @startup_teardown()
    def test_linux_pcie_qmi_8(self):
        """
        quectel-CM工具拨号LTE iperf测试
        """
        self.bound_network("LTE")
        all_logger.info('start LTE iperf test')
        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_QMI0')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                iperf(bandwidth="10M", times=300)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.info(e)
            all_logger.error(traceback.format_exc())
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_pcie_qmi_9(self):
        """
        禁用当前拨号网卡
        """
        return_value = subprocess.getoutput('ifconfig {} down'.format(self.network_card_name))
        all_logger.info('ifconfig {} down\n{}'.format(self.network_card_name, return_value))
        time.sleep(5)
        return_value = subprocess.getoutput('ifconfig {} up'.format(self.network_card_name))
        all_logger.info('ifconfig {} up\n{}'.format(self.network_card_name, return_value))
        time.sleep(20)
        self.dial()

    @startup_teardown()
    def test_linux_pcie_qmi_10(self):
        """
        quectel-CM工具拨号WCDMA
        """
        self.bound_network("WCDMA")
        self.dial()
        self.bound_network("SA")

    @startup_teardown()
    def test_linux_pcie_qmi_11(self):
        """
        quectel-CM工具拨号ATD
        """
        all_logger.info('start ATD dial test')
        self.send_at_pcie('at+qurccfg="urcport","usbmodem"', 10)
        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_QMI0')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                self.hang_up_after_system_dial(wait_time=20)
                time.sleep(30)
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.info(e)
            all_logger.error(traceback.format_exc())
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
        all_logger.info('ATD dial test end')
        self.check_intranet()

    @startup_teardown()
    def test_linux_pcie_qmi_12(self):
        """
        quectel-CM工具拨号SMS
        """
        all_logger.info('start SMS dial test')
        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_QMI0')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                self.send_msg()
                time.sleep(30)
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.info(e)
            all_logger.error(traceback.format_exc())
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()
        all_logger.info('SMS dial test end')
        self.send_at_pcie('at+qurccfg="urcport","usbat"', 10)

    @startup_teardown()
    def test_linux_pcie_qmi_13(self):
        """
        解pin后拨号
        """
        self.send_at_pcie('AT+CLCK="SC",1,"1234"', 3)
        self.send_at_pcie('AT+CFUN=1,1', 3)
        time.sleep(120)
        self.send_at_pcie('AT+CPIN=1234', 3)
        time.sleep(30)

        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(cmd='quectel-CM -i /dev/mhi_MBIM')
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.send_at_pcie('AT+CLCK="SC",0,"1234"', 10)
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(self.local_network_card_name))  # get ip
            all_logger.info('udhcpc -i {}\r\n{}'.format(self.local_network_card_name, udhcpc_value))
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_pcie_qmi_14(self):
        """
        EVB断电后QMI能否正常数传连接
        :return:
        """
        self.bound_network("SA")
        self.dial()
        self.send_at_pcie('AT+CFUN=1,1', timeout=0.3)

    def test_linux_pcie_qmi_15(self):
        """
        验证整机重启后QMI能否正常数传连接
        @return:
        """
        if not self.reboot.get_restart_flag():  # 代表此时还未进行重启主机
            self.reboot.restart_computer()
        else:
            self.test_linux_pcie_qmi_1()
            self.check_network_pcie()
            self.dial()


if __name__ == '__main__':
    params_dict = {

        "quectel_cm_path": '/home/ubuntu/quectel-CM',
        "sim_info": '898602',
        "version_name": 'RG502QEAAAR11A05M4G_01.001V02.01.001V02',
        "network_card_name": 'rmnet_mhi0.1',
        "local_network_card_name": 'eth0',
        "pcie_driver_path": '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi',
        "phone_number": "18656503485"
    }

    pcie_qmi = LinuxPcieQMI(**params_dict)
