import time
from utils.cases.linux_cloud_ota_manager import LinuxCloudOTAManager


class LinuxCloudOTA(LinuxCloudOTAManager):
    def linux_cloud_ota_1(self):
        """
        查询AT+QFOTACFG指令默认值
        :return:
        """
        self.query_default_fota_value()

    def linux_cloud_ota_2(self):
        """
        制作差分包并上传，添加版本
        :return:
        """
        if self.check_merge_version():
            self.check_version(True)
            return True
        try:
            self.mount_package()
            self.ubuntu_copy_file()
            self.unzip_firmware()
            self.make_dfota_package()
            self.check_version(True)
        finally:
            self.umount_package()

    def linux_cloud_ota_3(self):
        """
        创建计划，设置升级策略、导入黑白名单，激活计划并审核计划
        :return:
        """
        self.create_upgrade_plan(True)

    def linux_cloud_ota_4(self):
        """
        升级前模块信息查询
        :return:
        """
        self.check_info_before_upgrade()

    def linux_cloud_ota_5(self):
        """
        添加PK,以及HTTP的URL
        :return:
        """
        self.prepare_before_upgrade()

    def linux_cloud_ota_6(self):
        """
        执行升级指令，升级方式为立即升级，进行HTTP正向升级
        :return:
        """
        self.ota_upgrade()
        self.check_module_info(self.version_flag, self.imei)

    def linux_cloud_ota_7(self):
        """
        上传反向升级差分包创建计划，设置黑、白名单，并激活计划
        :return:
        """
        self.check_version(False)
        self.create_upgrade_plan(False)

    def linux_cloud_ota_8(self):
        """
        查询产品PK,URL，获取计划，升级协议为HTTPS，进行反向升级
        :return:
        """
        self.prepare_before_upgrade()
        self.ota_upgrade()
        self.check_module_info(self.version_flag, self.imei)

    def linux_cloud_ota_9(self):
        """
        设置产品A白名单，设置PK为未添加升级计划的空产品B，升级协议为HTTPS
        :return:
        """
        plan_id = ''
        try:
            self.white_list(self.version_flag)
            product_info = self.add_empty_product()
            self.set_empty_product(product_info)
            self.ota_upgrade()
            self.check_module_info(self.version_flag, self.imei)
        finally:
            self.prepare_before_upgrade()
            self.delete_white_list(plan_id)
            time.sleep(3)

    def linux_cloud_ota_10(self):
        """
        设置产品A白名单，设置PK为错误密钥，升级协议为HTTPS
        :return:
        """
        plan_id = ''
        try:
            plan_id = self.white_list(self.version_flag)
            self.set_error_product()
            self.ota_error_upgrade()
        finally:
            self.prepare_before_upgrade()
            self.delete_white_list(plan_id)
            time.sleep(3)

    def linux_cloud_ota_11(self):
        """
        不设置白名单，升级方式为手动升级，升级协议为HTTPS
        :return:
        """
        try:
            self.set_error_imei()
            self.prepare_before_upgrade()
            self.ota_upgrade()
            self.check_module_info(self.version_flag, '123456781234567')
        finally:
            self.at_handle.send_at(f'AT+EGMR=1,7,"{self.imei}"')

    def linux_cloud_ota_12(self):
        """
        延迟升级功能测试
        :return:
        """
        self.delay_upgrade()
        self.check_module_info(self.version_flag, self.imei)

    def linux_cloud_ota_13(self):
        """
        低电量状态无法升级
        :return:
        """
        self.low_power_upgrade()

    def linux_cloud_ota_14(self):
        """
        设置为黑名单的IMEI号无法升级
        :return:
        """
        self.black_list(self.version_flag)

    def linux_cloud_ota_15(self):
        """
        执行升级指令后，下载完成未开始升级时断电
        :return:
        """
        self.vbat_before_download()

    def linux_cloud_ota_16(self):
        """
        升级过程中断电
        :return:
        """
        self.vbat_in_upgrade()

    def linux_cloud_ota_17(self):
        """
        下载差分包过程断网
        :return:
        """
        self.disconnect_network_upgrade()

    def linux_cloud_ota_18(self):
        """
        下载差分包过程断电3次，上报升级失败
        :return:
        """
        self.vbat_in_download_upgrade()


if __name__ == '__main__':
    pramas_dict = {'at_port': '/dev/ttyUSBAT', 'dm_port': '/dev/ttyUSBDM',
                   'prev_firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\OpenLinux-Yct\RG502QEU_VA\Temp\RG502QEUAAR12A02M4G_YctOpen_BL_BETA_20211116A_02.001.02.001',
                   'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\OpenLinux-Yct\RG502QEU_VA\Release\RG502QEUAAR12A02M4G_YctOpen_BL_01.001V06.01.001V06',
                   'module_model': 'RG501QEU',
                   "prev_ati": "RG502QEUAAR12A02M4G_YctOpen_BL_BETA_20211116A", "ati": "RG502QEUAAR12A02M4G_Yctopen_BL",
                   "prev_sub": "V01", "sub": "V06", "imei": "869710030002905"
                   }
    linux_coud_ota = LinuxCloudOTA(**pramas_dict)
    linux_coud_ota.check_merge_version()
