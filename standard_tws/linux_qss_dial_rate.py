from utils.cases.linux_qss_dial_rate_manager import LinuxQSSDialRateManager
from utils.functions.decorators import startup_teardown
from utils.exception.exceptions import QSSDialRateError


class LinuxQSSDialRate(LinuxQSSDialRateManager):

    # qmi
    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_dial_rate_qmi(self):
        # 拨号前初始化和设置
        self.qmi_start_init()
        # 拨号测速
        self.qmi_quectel_cm(self.qmi_usb_network_card_name, 'QMI', 'USB')

    # at pcie qmi
    @startup_teardown()
    def test_linux_qss_dial_rate_at_pcie_qmi(self):
        # 拨号前初始化和设置
        self.at_pcie_qmi_start_init()
        # 拨号测速
        self.qmi_quectel_cm(self.pcie_network_card_name, 'PCIE_QMI', 'PCIE')

    # mbim
    @startup_teardown()
    def test_linux_qss_dial_rate_mbim(self):
        # 拨号前初始化和设置
        self.linux_mbim_start_init()
        # 拨号测速
        self.mbim_quectel_cm(self.mbim_usb_network_card_name, 'MBIM', 'USB')

    # at pcie mbim
    @startup_teardown()
    def test_linux_qss_dial_rate_at_pcie_mbim(self):
        # 拨号前初始化和设置
        self.linux_at_pcie_mbim_start_init()
        # 拨号测速
        self.mbim_quectel_cm(self.pcie_network_card_name, 'PCIE_MBIM', 'PCIE')

    # gobinet
    @startup_teardown()
    def test_linux_qss_dial_rate_gobinet(self):
        # 拨号前初始化和设置
        self.gobinet_start_init()
        # 拨号测速
        self.gobinet_quectel_cm(self.gobinet_usb_network_card_name, 'GobiNet', 'USB')

    # ecm
    @startup_teardown()
    def test_linux_qss_dial_rate_ecm(self):
        # 拨号前初始化和设置
        self.ecm_start_init()
        # 拨号测速
        self.ecm_quectel_cm(self.ecm_usb_network_card_name, 'ECM', 'USB')

    @startup_teardown()
    def test_linux_qss_test(self):
        try:
            self.get_speed_test_data_all(dial='QMI', network='NSA', interface='USB')
            self.get_speed_test_data_single(test_times='1')
            self.speedtest_records.append(list(self.speedtest_data.values()))
            self.get_speed_test_data_single(test_times='2')
            self.speedtest_records.append(list(self.speedtest_data.values()))
            self.get_speed_test_data_single(test_times='3')
        finally:
            self.speedtest_report()

    # ALL
    @startup_teardown(teardown=['check_and_set_to_usb'])
    def test_linux_qss_dial_rate(self):
        qss_connection = ''
        try:
            start_time, qss_connection = self.open_qss_cu()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_qmi()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_mbim()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_gobinet()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_ecm()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_at_pcie_qmi()
            self.delay_task(start_time, qss_connection, 300)
            self.test_linux_qss_dial_rate_at_pcie_mbim()
            if not self.test_pass_flag:
                raise QSSDialRateError(f"测速出现异常！{self.test_fail_dial}")
        finally:
            self.speedtest_report()
            self.end_task(qss_connection)


if __name__ == "__main__":
    # at_port, dm_port, wwan_path, gobinet_path, pcie_driver_path, qmi_usb_network_card_name, mbim_usb_network_card_name, gobinet_usb_network_card_name, ecm_usb_network_card_name, pcie_network_card_name,
    # local_network_card_name, qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'wwan_path': '/home/ubuntu/Tools/Drivers/qmi_wwan_q',
        'gobinet_path': '/home/ubuntu/tools/GobiNet',
        'pcie_driver_path': '/home/ubuntu/Tools/Drivers/pcie_mhi',
        'qmi_usb_network_card_name': 'wwan0_1',
        'mbim_usb_network_card_name': 'wwan0',
        'gobinet_usb_network_card_name': 'usb0',
        'ecm_usb_network_card_name': 'usb0',
        'pcie_network_card_name': 'rmnet_mhi0.1',
        'local_network_card_name': 'eth1',
        'qss_ip': '10.66.98.136',
        'local_ip': '66.66.66.66',
        'node_name': 'jeckson_test',
        # 'mme_file_name': ['00101-mme-ims.cfg','00101-mme-ims.cfg'],
        # 'enb_file_name': ['00101-gnb-sa-n78-DLmax.cfg','00101-endc-gnb-nsa-b3n78.cfg'],  # SA & NSA
        # 'ims_file_name': ['00101-ims.cfg','00101-ims.cfg'],
        # 'mme_file_name': '00101-mme-ims.cfg',
        # 'mme_file_name': '00101-mme-ims-esm-33.cfg',
        # 'mme_file_name': '00101-mme-ims-5Gmm.cfg',
        # 'enb_file_name': '00101-gnb-sa-n78-DLmax.cfg',
        # 'enb_file_name': '00101-endc-gnb-nsa-b3n78.cfg',
        # 'ims_file_name': '00101-ims.cfg',
        # 'mme_file_name': '46003-mme-ims.cfg',  # CT
        # 'enb_file_name': '46003-gnb-nsa-b3n78-DLmax.cfg',  # CT
        # 'ims_file_name': '46003-ims.cfg',  # CT
        'mme_file_name': '46000-mme-ims.cfg',
        'enb_file_name': '46000-gnb-nsa-B3N41.cfg',
        'ims_file_name': '46000-ims.cfg',
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
        'name_sub_version': 'RM502QAEAAR13A02M4G_01.001.01.001V03',
        'chrome_driver_path': '/home/ubuntu/Desktop/Function_qss/20221114/standard_tws-develop/test/chromedriver'
    }
    # 50501/896101、
    linux_qss = LinuxQSSDialRate(**param_dict)
    # linux_qss.test_linux_qss_dial_rate_qmi()  # OK
    # linux_qss.test_linux_qss_dial_rate_at_pcie_qmi()  # OK
    # linux_qss.test_linux_qss_dial_rate_mbim()  # FAIL
    # linux_qss.test_linux_qss_dial_rate_at_pcie_mbim()  # 优化驱动检查和默认值恢复
    # linux_qss.test_linux_qss_dial_rate_gobinet()  # OK
    # linux_qss.test_linux_qss_dial_rate_ecm()  # OK
    # linux_qss.test_linux_qss_test()
    linux_qss.test_linux_qss_dial_rate()
