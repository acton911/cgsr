import sys
import time
from utils.cases.linux_at_qmi_manager import LinuxATQMIManager
from utils.functions.linux_api import QuectelCMThread, LinuxAPI
from utils.logger.logging_handles import all_logger
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
import subprocess
import traceback


class LinuxAtQMI(LinuxATQMIManager):
    def test_linux_at_qmi_1(self):
        """
        AT配置PCIE模式模块在Linux PC下开机,PCI设备加载成功
        """
        time.sleep(60)
        self.check_and_set_pcie_data_interface()
        time.sleep(60)  # 避免和后台运行的驱动加载程序冲突
        self.PCIE.switch_pcie_mode(pcie_mbim_mode=False)
        time.sleep(5)
        self.check_pcie_pci()
        self.check_pcie_driver()

    def test_linux_at_qmi_2(self):
        """
        查询模块找网状态及拨号工具编译
        """
        all_logger.info('等待网络稳定')
        time.sleep(60)
        self.check_network_pcie()
        self.check_netcard()
        self.make_dial_tool()

    def test_linux_at_qmi_3(self):
        """
        quectel-CM工具拨号
        """
        self.bound_network("SA")
        self.at_handler.check_network()
        self.dial()

    def test_linux_at_qmi_4(self):
        """
        quectel-CM工具拨号及频繁断开
        """
        for i in range(5):
            all_logger.info(f'第{i}次拨号后断开')
            self.get_ip_address()
            self.dial()
            time.sleep(20)  # wait dial complete

    @startup_teardown()
    def test_linux_at_qmi_5(self):
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
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                iperf(bandwidth='30M', times=300)
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
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_at_qmi_6(self):
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
            q = QuectelCMThread(netcard_name=self.network_card_name)
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
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.check_intranet()

    @startup_teardown()
    def test_linux_at_qmi_7(self):
        """
        固定LTE网络制式，注册LTE网络，quectel-CM工具MBIM拨号功能正常
        """
        self.bound_network("LTE")
        time.sleep(20)
        self.at_handler.check_network()
        self.dial()
        self.bound_network("SA")
        self.at_handler.check_network()

    @startup_teardown()
    def test_linux_at_qmi_8(self):
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
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            if is_success:
                LinuxAPI().ping_get_connect_status(network_card_name=self.network_card_name, times=times)
                iperf(bandwidth="10M", times=300)
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
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('LTE iperf test end')
            self.check_intranet()

    @startup_teardown()
    def test_linux_at_qmi_9(self):
        """
        quectel-CM工具拨号ATD
        """
        self.bound_network('SA')
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
            q = QuectelCMThread(netcard_name=self.network_card_name)
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
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('ATD dial test end')
            self.send_at_pcie('at+qurccfg="urcport","usbat"', 10)
            self.check_intranet()

    @startup_teardown()
    def test_linux_at_qmi_10(self):
        """
        quectel-CM工具拨号SMS
        """
        self.bound_network("LTE")
        time.sleep(20)
        self.at_handler.check_network()
        all_logger.info('start SMS dial test')
        self.send_at_pcie('at+qurccfg="urcport","usbmodem"', 10)
        times = 10
        is_success = True
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(netcard_name=self.network_card_name)
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
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('SMS dial test end')
            self.send_at_pcie('at+qurccfg="urcport","usbat"', 10)
            self.check_intranet()

    @startup_teardown()
    def test_linux_at_qmi_11(self):
        """
        禁用当前拨号网卡
        """
        return_value = subprocess.getoutput(f'ifconfig {self.network_card_name} down')
        all_logger.info(f'ifconfig {self.network_card_name} down\n{return_value}')
        time.sleep(5)
        all_logger.info('禁用网卡后进行Qucetel-CM拨号')
        self.dial()
        time.sleep(20)
        self.at_handler.check_network()
        return_value = subprocess.getoutput(f'ifconfig {self.network_card_name} up')
        all_logger.info(f'ifconfig {self.network_card_name} up\n{return_value}')
        time.sleep(20)
        all_logger.info('启用网卡后进行Qucetel-CM拨号')
        self.dial()

    @startup_teardown()
    def test_linux_at_qmi_12(self):
        """
        quectel-CM工具拨号WCDMA
        """
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(30)
        self.at_handler.check_network()
        self.bound_network("WCDMA")
        self.at_handler.check_network()
        self.dial()
        self.bound_network("NSA")
        self.at_handler.check_network()

    @startup_teardown()
    def test_linux_at_qmi_13(self):
        """
        SIM PIN状态下QMI能否正常数传连接
        """
        self.at_handler.send_at('AT+CLCK="SC",1,"1234"')
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(20)
        q = None
        exc_value = None
        exc_type = None
        try:
            self.local_net_down()
            time.sleep(20)  # 避免后续拨号号后ping失败
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            q.start()
            time.sleep(30)
            self.get_ip_address(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handler.send_at('AT+CPIN=1234')
            time.sleep(10)
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"', 10)
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            self.check_intranet()
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_at_qmi_14(self):
        """
        EVB断电后QMI能否正常数传连接
        """
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(10)
        self.at_handler.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0', 10)
        self.at_handler.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 10)
        self.at_handler.check_network()
        self.dial()

    def test_linux_pcie_qmi_15(self):
        """
        验证整机重启后QMI能否正常数传连接
        @return:
        """
        if not self.reboot.get_restart_flag():  # 代表此时还未进行重启主机
            self.reboot.restart_computer()
        else:
            self.test_linux_at_qmi_1()
            self.at_handler.check_network()
            self.dial()

    def test_linux_pcie_qmi_16(self):
        """
        查询PCIE PCIE接口
        """
        self.test_linux_at_qmi_1()
        self.check_pcie_port()


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

    pcie_qmi = LinuxAtQMI(**params_dict)
    # pcie_qmi.test_linux_at_qmi_1()
    # pcie_qmi.test_linux_at_qmi_2()
    # pcie_qmi.test_linux_at_qmi_3()
    # pcie_qmi.test_linux_at_qmi_4()
    # pcie_qmi.test_linux_at_qmi_5()
    # pcie_qmi.test_linux_at_qmi_6()
    # pcie_qmi.test_linux_at_qmi_7()
    # pcie_qmi.test_linux_at_qmi_8()
    # pcie_qmi.test_linux_at_qmi_9()
    # pcie_qmi.test_linux_at_qmi_10()
    # pcie_qmi.test_linux_at_qmi_11()
    # pcie_qmi.test_linux_at_qmi_12()
    pcie_qmi.test_linux_pcie_qmi_15()
    # pcie_qmi.test_linux_pcie_qmi_16()
