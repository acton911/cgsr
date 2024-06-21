from utils.cases.linux_qss_band_traversal_manager import LinuxQSSBandTraversalManager
from utils.functions.decorators import startup_teardown
from utils.exception.exceptions import QSSBandTraversalError


class LinuxQSSBandTraversal(LinuxQSSBandTraversalManager):

    @startup_teardown(teardown=['reset_network_to_default'])
    def test_linux_qss_band_traversal_01_000(self):
        pass

    @startup_teardown()
    def test_linux_qss_band_traversal_01_001(self):
        """
        插入00101白卡遍历band，验证驻网和速率
        1. 连接数据库，查询模组支持的LTE band，逐个开启QSS的单LTE配置，验证注网
        """
        # 将卡写成00101卡
        self.write_simcard_with_plmn_ccid('00101', '8949024')
        self.bands_traverse('00101', self.default_lte_band, False, 'test_linux_qss_band_traversal_ROW', mode='lte')  # 遍历LTE

        self.pass_rate('ROW', list(set(self.default_lte_band.split(':'))-set(self.support_lte_band)))  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_002(self):
        """
        插入00101白卡遍历band，验证驻网和速率
        1. 连接数据库，查询模组支持的SA band，逐个开启QSS的单SA配置，验证注网和速率
        """
        # 将卡写成00101卡
        self.write_simcard_with_plmn_ccid('00101', '8949024')
        self.bands_traverse('00101', self.default_sa_band, False, 'test_linux_qss_band_traversal_ROW', mode='sa')  # 遍历SA,测速

        self.pass_rate('ROW', list(set(self.default_sa_band.split(':'))-set(self.support_sa_band)))  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_003(self):
        """
        插入白卡，激活VZW mbn, 遍历band，验证驻网和速率
       """
        # 将卡写成VZW
        self.write_simcard_with_plmn_ccid('311480', '891480')
        self.update_suport_bands()
        self.bands_traverse('311480', self.vzw_band, False, 'test_linux_qss_band_traversal_VZW')  # 遍历lte,测速

        self.pass_rate('VZW', self.vzw_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_004(self):
        """
        插入白卡，激活Telstra mbn, 遍历band，验证驻网和速率
        """
        # 将卡写成Telstra
        self.write_simcard_with_plmn_ccid('50501', '896101')
        self.update_suport_bands()
        self.bands_traverse('50501', self.telstra_band, False, 'test_linux_qss_band_traversal_Telstra')  # 遍历lte,测速

        self.pass_rate('Telstra', self.telstra_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_005(self):
        """
        插入白卡，激活TMO mbn, 遍历band，验证驻网和速率
        """
        # 将卡写成TMO
        self.write_simcard_with_plmn_ccid('310260', '8901260')
        self.update_suport_bands()
        self.bands_traverse('310260', self.tmo_band, False, 'test_linux_qss_band_traversal_TMO')  # 遍历lte,测速

        self.pass_rate('TMO', self.tmo_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_006(self):
        """
        插入白卡，激活ATT mbn, 遍历band，验证驻网和速率
        """
        # 将卡写成ATT
        self.write_simcard_with_plmn_ccid('310410', '8901410')
        self.update_suport_bands()
        self.bands_traverse('310410', self.att_band, False, 'test_linux_qss_band_traversal_ATT')  # 遍历lte,测速

        self.pass_rate('ATT', self.att_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_007(self):
        """
        国内运营商CMCC
        """
        # 将卡写成CMCC
        self.write_simcard_with_plmn_ccid('46000', '898600')
        self.update_suport_bands()
        self.bands_traverse('46000', self.cmcc_band, False, 'test_linux_qss_band_traversal_CMCC')  # 遍历cmcc,测速

        self.pass_rate('CMCC', self.cmcc_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_008(self):
        """
        国内运营商CU
        """
        # 将卡写成CU
        self.write_simcard_with_plmn_ccid('46001', '898601')
        self.update_suport_bands()
        self.bands_traverse('46001', self.cu_band, False, 'test_linux_qss_band_traversal_CU')  # 遍历c,测速

        self.pass_rate('CU', self.cu_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")

    @startup_teardown()
    def test_linux_qss_band_traversal_01_009(self):
        """
        国内运营商CT
        """
        # 将卡写成CT
        self.write_simcard_with_plmn_ccid('46011', '898603')
        self.update_suport_bands()
        self.bands_traverse('46011', self.ct_band, False, 'test_linux_qss_band_traversal_CT')  # 遍历ct,测速

        self.pass_rate('CT', self.ct_band)  # 计算成功率
        if self.test_fail:  # 提示异常并且不影响别的band继续测试
            raise QSSBandTraversalError(f"band遍历出现异常：{self.test_fail}")


if __name__ == "__main__":
    p_list = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'wwan_path': '/home/ubuntu/Tools/Drivers/qmi_wwan_q',
        'qmi_usb_network_card_name': 'wwan0_1',
        'local_network_card_name': 'eth1',
        'qss_ip': '10.66.98.136',
        'local_ip': '66.66.66.66',
        'node_name': 'jeckson_test',
        # ROW
        'mme_file_name': '00101-mme-ims.cfg',
        'enb_file_name': [
            '00101-fdd-enb-b1.cfg',
            '00101-fdd-enb-b12.cfg',
            '00101-fdd-enb-b13.cfg',
            '00101-fdd-enb-b14.cfg',
            '00101-fdd-enb-b17.cfg',
            '00101-fdd-enb-b18.cfg',
            '00101-fdd-enb-b19.cfg',
            '00101-fdd-enb-b2.cfg',
            '00101-fdd-enb-b20.cfg',
            '00101-fdd-enb-b25.cfg',
            '00101-fdd-enb-b26.cfg',
            '00101-fdd-enb-b28.cfg',
            '00101-fdd-enb-b3.cfg',
            '00101-fdd-enb-b30.cfg',
            '00101-fdd-enb-b4.cfg',
            '00101-fdd-enb-b5.cfg',
            '00101-fdd-enb-b66.cfg',
            '00101-fdd-enb-b7.cfg',
            '00101-fdd-enb-b71.cfg',
            '00101-fdd-enb-b8.cfg',
            '00101-fdd-gnb-sa-n1.cfg',
            '00101-fdd-gnb-sa-n12.cfg',
            '00101-fdd-gnb-sa-n13.cfg',
            '00101-fdd-gnb-sa-n14.cfg',
            '00101-fdd-gnb-sa-n18.cfg',
            '00101-fdd-gnb-sa-n2.cfg',
            '00101-fdd-gnb-sa-n20.cfg',
            '00101-fdd-gnb-sa-n25.cfg',
            '00101-fdd-gnb-sa-n26.cfg',
            '00101-fdd-gnb-sa-n28.cfg',
            '00101-fdd-gnb-sa-n3.cfg',
            '00101-fdd-gnb-sa-n30.cfg',
            '00101-fdd-gnb-sa-n5.cfg',
            '00101-fdd-gnb-sa-n66.cfg',
            '00101-fdd-gnb-sa-n7.cfg',
            '00101-fdd-gnb-sa-n70.cfg',
            '00101-fdd-gnb-sa-n71.cfg',
            '00101-fdd-gnb-sa-n8.cfg',
            '00101-tdd-enb-b34.cfg',
            '00101-tdd-enb-b38.cfg',
            '00101-tdd-enb-b39.cfg',
            '00101-tdd-enb-b40.cfg',
            '00101-tdd-enb-b41.cfg',
            '00101-tdd-enb-b42.cfg',
            '00101-tdd-enb-b43.cfg',
            '00101-tdd-enb-b46.cfg',
            '00101-tdd-enb-b48.cfg',
            '00101-tdd-gnb-sa-n38.cfg',
            '00101-tdd-gnb-sa-n40.cfg',
            '00101-tdd-gnb-sa-n41.cfg',
            '00101-tdd-gnb-sa-n48.cfg',
            '00101-tdd-gnb-sa-n77.cfg',
            '00101-tdd-gnb-sa-n78.cfg',
            '00101-tdd-gnb-sa-n79.cfg'
        ],
        'ims_file_name': '00101-ims.cfg',
        'name_sub_version': 'RM502QAEAAR13A02M4G_01.001.01.001V03',
        'chrome_driver_path': '/home/ubuntu/Desktop/Function_qss/20221114/standard_tws-develop/test/chromedriver',
        'default_sa_band': '1:2:3:5:7:8:12:20:25:28:38:40:41:48:66:71:77:78:79',
        'default_nsa_band': '1:2:3:5:7:8:12:20:25:28:38:40:41:48:66:71:77:78:79',
        'default_lte_band': '1:2:3:4:5:7:8:12:13:14:18:19:20:25:26:28:29:30:32:34:38:39:40:41:42:43:46:48:66:71',
        'default_wcdma_band': '1:2:3:4:5:6:8:19',
    }
    qss_test = LinuxQSSBandTraversal(**p_list)
    qss_test.test_linux_qss_band_traversal_01_001()
    # qss_test.test_linux_qss_band_traversal_01_002()
    # qss_test.test_linux_qss_band_traversal_01_003()
    # qss_test.test_linux_qss_band_traversal_01_004()
    # qss_test.test_linux_qss_band_traversal_01_005()
