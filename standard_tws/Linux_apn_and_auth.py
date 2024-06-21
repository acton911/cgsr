import sys
from utils.cases.linux_apn_and_auth_manager import linuxAPNandAuthFunctionsManager
import time

from utils.functions.linux_api import LinuxAPI, QuectelCMThread
from utils.functions.linux_api import QuectelCMThread, enable_network_card_and_check
from utils.logger.logging_handles import all_logger
import subprocess
from utils.functions.decorators import startup_teardown
import traceback
from utils.exception.exceptions import QMIError, ATError


class linuxAPNandAuthFunctions(linuxAPNandAuthFunctionsManager):

    def test_linux_apn_and_auth_01_001(self):
        """
        APN 为默认值时，QMI拨号上网正常
        """
        # 设置USBNET为0
        time.sleep(30)  # 等待升级完成后AT口正常使用
        self.check_and_set_pcie_data_interface()
        time.sleep(20)
        self.at_handle.send_at('AT+QCFG="USBNET"', timeout=3)
        self.at_handle.send_at('AT+QCFG="USBNET",0', timeout=3)
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=60)

        # 加载qmi_wwan_q驱动
        self.modprobe_driver()
        self.load_wwan_driver()
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.readline_keyword('PB DONE', timout=60)
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()

        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        self.at_handle.send_at('AT+CGDCONT?', timeout=0.3)

        # 进行QMI拨号,并ping IPV4 IPV6网址
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
            self.check_cgact()
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

    def test_linux_apn_and_auth_01_002(self):
        """
        APN长度为48位字符时，QMI拨号上网正常
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('123456789012345678901234567890123456789012345678')
        # QMI拨号
        self.dial()

    def test_linux_apn_and_auth_01_003(self):
        """
        APN长度为57位字符时，QMI拨号上网正常
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('123456789012345678901234567890123456789012345678901234567')
        # QMI拨号
        self.dial()

    def test_linux_apn_and_auth_01_004(self):
        """
        APN长度为62位字符时，QMI拨号失败或CGACT激活失败
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('12345678901234567890123456789012345678901234567890123456789012')
        # 激活第一路APN
        cgact_value_return = self.at_handle.send_at('AT+CGACT=1,1', timeout=150)
        if 'ERROR' in cgact_value_return:
            all_logger.info('激活第一路APN失败符合预期')
        else:
            raise ATError('激活第一路APN异常')

    def test_linux_apn_and_auth_01_005(self):
        """
        APN长度为63位字符时，设置失败
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont_fail('123456789012345678901234567890123456789012345678901234567890123')

    def test_linux_apn_and_auth_01_006(self):
        """
        APN Name中间包含连接符"-"时，QMI拨号上网正常
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 配置第一路APN
        self.set_cgdcont('123-123456')
        # 进行QMI拨号，并ping百度正常
        self.dial()

    def test_linux_apn_and_auth_01_007(self):
        """
        APN Name中间包含点"."时，QMI拨号上网正常
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 配置第一路APN
        self.set_cgdcont('abc.def')
        # 进行QMI拨号，并ping百度正常
        self.dial()

    def test_linux_apn_and_auth_01_008(self, ip_type="IPV4V6"):
        """
        APN name开头和结束必须为字母或者数字，不能以 “-”或者“.”结束
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        apn_list = ['-', '-123', '123-', '.', '.456', '123.']
        for apn in apn_list:
            cgdcont_value_return = self.at_handle.send_at('at+cgdcont=1,"{}","{}"'.format(ip_type, apn))
            if 'ERROR' in cgdcont_value_return:
                all_logger.info('配置APN返回结果符合预期')
            else:
                raise ATError('配置APN返回结果不符合预期')

    def test_linux_apn_and_auth_01_009(self):
        """
        APN为数字+英文(大小写)时，QMI拨号上网正常
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 配置第一路APN
        self.set_cgdcont('123ABCdefGHIJKLMNUVWxyz456')
        # 进行QMI拨号
        self.dial()

    def test_linux_apn_and_auth_01_010(self):
        """
        APN为数字+英文+特殊字符时，设置失败
        """
        # 注SA网络
        self.at_handle.bound_network('SA')
        self.at_handle.check_network()
        # 配置第一路APN
        self.set_cgdcont_fail('123abc*^&%<>123def')

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_apn_and_auth_02_001(self):
        """
        NSA网络下，APN为默认值时，QMI拨号上网正常
        """
        self.at_handle.bound_network('NSA')
        self.open_qss_white()
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_02_002(self):
        """
        APN长度为57位字符时，QMI拨号上网正常
        """
        self.at_handle.bound_network('NSA')
        self.open_qss_white()
        self.set_cgdcont('123456789012345678901234567890123456789012345678901234567')
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_02_003(self):
        """
        APN长度为62位字符时，QMI拨号上网正常
        """
        self.at_handle.bound_network('NSA')
        self.open_qss_white()
        self.set_cgdcont('12345678901234567890123456789012345678901234567890123456789012')
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_02_004(self):
        """
        APN为数字+英文(大小写)+支持的字符（-.）时，QMI拨号上网正常
        """
        self.at_handle.bound_network('NSA')
        self.open_qss_white()
        self.set_cgdcont('123-ABC.defGHIJKLM-NUVW.xyz456')
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_03_001(self):
        """
        APN为默认值时，QMI拨号上网正常
        """
        # 注LTE网络
        self.at_handle.bound_network('LTE')
        self.at_handle.check_network()
        self.at_handle.send_at('AT+CGDCONT?', 0.3)
        self.dial()

    def test_linux_apn_and_auth_03_002(self):
        """
        APN长度为57位字符时，QMI拨号上网正常
        """
        # 注LTE网络
        self.at_handle.bound_network('LTE')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('123456789012345678901234567890123456789012345678901234567')
        # 进行QMI拨号
        self.dial()

    def test_linux_apn_and_auth_03_003(self):
        """
        APN长度为62位字符时，QMI拨号上网正常
        """
        # 注LTE网络
        self.at_handle.bound_network('LTE')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('12345678901234567890123456789012345678901234567890123456789012')
        # 进行QMI拨号
        self.dial()

    def test_linux_apn_and_auth_03_004(self):
        """
        APN为数字+英文(大小写)+支持的字符(-.)时，QMI拨号上网正常
        """
        # 注LTE网络
        self.at_handle.bound_network('LTE')
        self.at_handle.check_network()
        # 设置APN
        self.set_cgdcont('123ABCdefGHIJKLM-NUVW.xyz456')
        # 进行QMI拨号
        self.dial()

    def test_linux_apn_and_auth_04_001(self):
        """
        PAP鉴权，APN的登录用户名、密码为空时，QMI拨号上网正常
        """
        # 固定SA网络
        self.at_handle.bound_network('SA')
        self.open_qss_white()
        self.set_qicsgp("", "", "", 0)
        self.dial(False)
        self.set_qicsgp("", "", "", 1)
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_04_002(self):
        """
        PAP鉴权，APN的登录用户名、密码长度为1字节时，QMI拨号上网正常
        """
        # 固定SA网络
        self.at_handle.bound_network('SA')
        self.open_qss_white()
        self.set_qicsgp("", "", "", 0)
        self.dial()
        self.set_qicsgp("1", "1", "1", 1)
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_04_003(self):
        """
        PAP鉴权，APN的登录用户名、密码长度为10字节时，QMI拨号上网正常
        """
        # 固定SA网络
        self.at_handle.bound_network('SA')
        self.open_qss_white()
        self.set_qicsgp("", "", "", 0)
        self.dial()
        self.set_qicsgp("", "1234567890", "1234567890", 1)
        self.dial()
        self.end_task(self.open_qss_white())

    def test_linux_apn_and_auth_04_004(self):
        """
        PAP鉴权，APN的登录用户名、密码长度为60字节时，QMI拨号上网正常
        """
        # 固定SA网络
        self.at_handle.bound_network('SA')
        self.open_qss_white()
        self.set_qicsgp("", "", "", 0)
        self.dial()
        self.set_qicsgp("123456789012345678901234567890123456789012345678901234567890", "123456789012345678901234567890123456789012345678901234567890", "123456789012345678901234567890123456789012345678901234567890", 1)
        self.dial()
        self.end_task(self.open_qss_white())


if __name__ == "__main__":
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
        'rgmii_ethernet_name': 'eth2',
        'rtl8125_ethernet_name': 'eth0',
        'eth_test_mode': '3',
        'pc_ethernet_name': 'eth1',
    }
    apn_and_auth = linuxAPNandAuthFunctions(**param_dict)
    apn_and_auth.test_linux_apn_and_auth_01_001()





























