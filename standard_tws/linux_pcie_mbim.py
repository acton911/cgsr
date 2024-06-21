import sys
import time
from utils.cases.linux_pcie_mbim_manager import LinuxPcieMBIMManager
from utils.functions.linux_api import QuectelCMThread, LinuxAPI
from utils.functions.decorators import startup_teardown
from utils.functions.iperf import iperf
from utils.logger.logging_handles import all_logger
import subprocess
import traceback


class LinuxPcieMBIM(LinuxPcieMBIMManager):
    @startup_teardown()
    def test_linux_pcie_mbim_1(self):
        """
        查询当前PCI
        查询当前PCIE驱动加载成功
        """
        time.sleep(60)  # 防止发AT口还未加载、发AT不生效等问题发生
        self.driver.check_usb_driver()
        self.at_handler.send_at("ATE1", 3)
        self.check_and_set_pcie_data_interface()
        time.sleep(60)  # 避免和后台运行的驱动加载程序冲突
        # self.PCIE.switch_pcie_mode(pcie_mbim_mode=True)
        self.check_pcie_pci()
        self.insmod_pcie_mbim()
        time.sleep(10)
        self.check_pcie_driver()
        self.check_pcie_data_interface()
        self.linux_api.check_intranet(self.local_network_card_name)

    @startup_teardown()
    def test_linux_pcie_mbim_2(self):
        """
        查询模块找网状态
        """
        self.bound_network('SA')
        self.check_network_pcie()
        # self.check_module_info()
        self.linux_api.check_intranet(self.local_network_card_name)

    @startup_teardown()
    def test_linux_pcie_mbim_3(self):
        """
        quectel-CM工具编译
        """
        self.make_dial_tool()
        self.linux_api.check_intranet(self.local_network_card_name)

    @startup_teardown()
    def test_linux_pcie_mbim_4(self):
        """
        quectel-CM工具拨号测试SA
        """
        self.bound_network("SA")
        self.dial()

    @startup_teardown()
    def test_linux_pcie_mbim_5(self):
        """
        quectel-CM工具拨号及频繁断开
        """
        for i in range(10):
            all_logger.info(f'start dial test times {i+1}')
            self.get_ip_address()
            self.dial()
            time.sleep(20)  # wait dial complete

    @startup_teardown()
    def test_linux_pcie_mbim_6(self):
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
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_pcie_mbim_7(self):
        """
        quectel-CM工具拨号cfun=0\1\4
        """
        all_logger.info('start cfun0/1/4 test')
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
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('cfun0/1/4 test end')

    @startup_teardown()
    def test_linux_pcie_mbim_8(self):
        """
        quectel-CM工具拨号LTE
        """
        self.bound_network("LTE")
        time.sleep(20)
        self.dial()
        self.bound_network("SA")

    @startup_teardown()
    def test_linux_pcie_mbim_9(self):
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
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('LTE iperf test end')

    @startup_teardown()
    def test_linux_pcie_mbim_10(self):
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
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            self.send_at_pcie('at+qurccfg="urcport","usbat"', 10)
            all_logger.info('ATD dial test end')

    @startup_teardown()
    def test_linux_pcie_mbim_11(self):
        """
        quectel-CM工具拨号SMS
        """
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
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)
            all_logger.info('SMS dial test end')
            self.send_at_pcie('at+qurccfg="urcport","usbat"', 10)

    @startup_teardown()
    def test_linux_pcie_mbim_12(self):
        """
        quectel-CM工具拨号forbiden networkcard
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
    def test_linux_pcie_mbim_03_007(self):
        """
        解pin后拨号
        """
        self.at_handler.send_at('AT+CLCK="SC",1,"1234"')
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        time.sleep(20)
        self.at_handler.send_at('AT+CPIN=1234')
        time.sleep(20)
        self.at_handler.check_network()

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
            else:
                self.get_ip_address(False)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            self.at_handler.send_at('AT+CLCK="SC",0,"1234"', 10)
            q.ctrl_c()
            q.terminate()
            self.local_net_up()
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.local_network_card_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.local_network_card_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_pcie_mbim_13(self):
        """
        quectel-CM工具拨号WCDMA
        """
        try:
            self.bound_network("WCDMA")
            self.dial()
        finally:
            self.bound_network("SA")

    def test_linux_pcie_mbim_14(self):
        """
        电脑重启
        """
        if not self.reboot.get_restart_flag():
            self.dial()
            self.reboot.restart_computer()
        else:
            self.test_linux_pcie_mbim_1()
            self.check_network_pcie()
            self.dial()

    @startup_teardown()
    def test_linux_pcie_mbim_15(self):
        """
        查询PCIE接口速率
        """
        self.check_pcie_port()


if __name__ == '__main__':
    params_dict = {
        "quectel_cm_path": '/home/ubuntu/quectel-CM',
        "sim_info": '89860320845510939715',
        "version_name": 'RG502QEAAAR11A05M4G_01.001V02.01.001V02',
        "network_card_name": 'rmnet_mhi0.1',
        "local_network_card_name": 'eth0',
        "pcie_driver_path": '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi',
        "phone_number": "18110921823",
        "usbat_port": "/dev/ttyUSBAT",
        "usbdm_port": "/dev/ttyUSBDM",
    }

    pcie_mbim = LinuxPcieMBIM(**params_dict)
    # pcie_mbim.test_linux_pcie_mbim_1()
    # pcie_mbim.test_linux_pcie_mbim_2()
    # pcie_mbim.test_linux_pcie_mbim_3()
    # pcie_mbim.test_linux_pcie_mbim_4()
    # pcie_mbim.test_linux_pcie_mbim_5()
    # pcie_mbim.test_linux_pcie_mbim_6()
    # pcie_mbim.test_linux_pcie_mbim_7()
    # pcie_mbim.test_linux_pcie_mbim_8()
    # pcie_mbim.test_linux_pcie_mbim_9()
    # pcie_mbim.test_linux_pcie_mbim_10()
    # pcie_mbim.test_linux_pcie_mbim_11()
    # pcie_mbim.test_linux_pcie_mbim_12()
    # pcie_mbim.test_linux_pcie_mbim_13()
