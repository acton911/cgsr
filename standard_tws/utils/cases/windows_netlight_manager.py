import subprocess
import os
import time
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import WindowsNetLightError
from utils.operate.at_handle import ATHandle
from utils.functions.gpio import GPIO
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI


class WindowsNetLightManager:
    def __init__(self, at_port, dm_port, wwan_path, network_card_name, extra_ethernet_name):
        self.at_port = at_port
        self.dm_port = dm_port
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.all_logger = all_logger
        self.linux_api = LinuxAPI()
        self.wwan_path = wwan_path
        self.extra_ethernet_name = extra_ethernet_name
        self.network_card_name = network_card_name
        self.gpio = GPIO()

    def module_typerg(self):
        time.sleep(10)
        type_value = self.at_handle.send_at('ATI')
        if 'RM' in type_value:
            all_logger.info('当前测试项目为RM项目,不执行此case')
            return True

    def module_typerm(self):
        time.sleep(10)
        type_value = self.at_handle.send_at('ATI')
        if 'RG' in type_value:
            all_logger.info('当前测试项目为RG项目,不执行此case')
            return True

    def open_hot_plug(self):
        """
        开启SIM卡热插拔
        """
        self.at_handle.send_at('at+qsimdet=1,1')
        self.at_handle.send_at('at+qsimstat=1')
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        time.sleep(20)
        all_logger.info('模块热插拔功能开启成功')

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是usb模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.readline_keyword('PB DONE', timout=60)
            time.sleep(5)

    @staticmethod
    def modprobe_driver():
        """
        卸载GobiNet驱动
        :return: True
        """
        for i in range(3):
            all_logger.info('modprobe -r GobiNet卸载Gobinet驱动')
            all_logger.info(os.popen('modprobe -r GobiNet').read())
            all_logger.info('modprobe -r qmi_wwan卸载qmi_wwan驱动')
            all_logger.info(os.popen('modprobe -r qmi_wwan').read())
            check_modprobe = os.popen('lsusb -t').read()
            all_logger.info('卸载驱动后查看驱动情况:\n')
            all_logger.info(check_modprobe)
            if 'GobiNet' not in check_modprobe:
                all_logger.info('驱动卸载成功')
                return True
        raise WindowsNetLightError('卸载Gobinet驱动失败')

    def load_wwan_driver(self):
        """
        编译WWAN驱动
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.wwan_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.wwan_path]), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'install', '--directory', self.wwan_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

    @staticmethod
    def load_qmi_wwan_q_drive():
        """
        加载qmi驱动
        :return:
        """
        all_logger.info('开始卸载所有网卡驱动')
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

        time.sleep(5)
        all_logger.info('开始加载qmi_wwan_q网卡驱动')
        subprocess.run("modprobe -a qmi_wwan_q", shell=True)

    @staticmethod
    def check_wwan_driver(is_disappear=False):
        """
        检测wwan驱动是否加载成功
        :param is_disappear: False：检测WWAN驱动正常加载；True：检测WWAN驱动正常消失
        :return: True
        """
        check_cmd = subprocess.Popen('lsusb -t', stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, shell=True)
        check_time = time.time()
        all_logger.info("lsusb -t查询返回:\n")
        while True:
            time.sleep(0.001)
            check_cmd_val = check_cmd.stdout.readline().decode('utf-8', 'ignore')
            if check_cmd_val != '':
                all_logger.info(check_cmd_val)
            if 'qmi_wwan' in check_cmd_val and not is_disappear:
                all_logger.info('wwan驱动检测成功')
                check_cmd.terminate()
                return True
            if is_disappear and 'qmi_wwan' not in check_cmd_val:
                all_logger.info('wwan驱动消失')
                check_cmd.terminate()
                return True
            if time.time() - check_time > 2:
                all_logger.info('未检测到wwan驱动')
                check_cmd.terminate()
                raise WindowsNetLightError

    def check_statuslight_alwaysbright(self, times=10):
        """
        持续检测10次net_status灯常亮状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            if 1 == level_status:
                all_logger.info('第{}次检测为高电平,灯为常亮状态'.format(i))

            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常亮状态'.format(i, level_status))

    def check_statuslight_alwaysdown(self, times=10):
        """
        持续检测10次net_status灯长灭状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            if 0 == level_status:
                all_logger.info('第{}次检测为低电平,灯为常灭状态'.format(i))

            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常灭状态'.format(i, level_status))

    def check_modelight_alwaysbright(self, times=10):
        """
        持续检测10次net_mode灯常亮状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_net_mode_gpio_level()
            level_status = status_list['level']
            if 1 == level_status:
                all_logger.info('第{}次检测为高电平,灯为常亮状态'.format(i))

            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常亮状态'.format(i, level_status))

    def check_modelight_alwaysdown(self, times=10):
        """
        持续检测10次net_mode灯常亮状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_net_mode_gpio_level()
            level_status = status_list['level']
            if 0 == level_status:
                all_logger.info('第{}次检测为低电平,灯为常灭状态'.format(i))

            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常灭状态'.format(i, level_status))

    def check_statuslight_longdownshortbright(self, times=60):
        """
        持续检测10次net_status灯长灭短亮状态
        :param times: 检测次数
        :return:
        """
        level_list = []
        level1_list = []
        level0_list = []
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            level_list.append(level_status)
        for i in level_list:
            if i == 1:
                level1_list.append(i)
                continue
            level0_list.append(i)
        if 1 in level_list and 0 in level_list:
            all_logger.info('net_status灯状态为长灭短亮,状态正常')
        else:
            all_logger.info('当前检测灯亮状态为{}'.format(level1_list))
            all_logger.info('当前检测灯灭状态为{}'.format(level0_list))
            raise WindowsNetLightError('当前net_status灯状态不对')

    def check_statuslight_longbrightshortdown(self, times=60):
        """
        持续检测10次net_status灯长亮短灭状态
        :param times: 检测次数
        :return:
        """
        level_list = []
        level1_list = []
        level0_list = []
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            level_list.append(level_status)
        for i in level_list:
            if i == 1:
                level1_list.append(i)
                continue
            level0_list.append(i)
        if 1 in level_list and 0 in level_list:
            all_logger.info('net_status灯状态为长亮短灭,状态正常')
        else:
            all_logger.info('当前检测灯亮状态为{}'.format(level1_list))
            all_logger.info('当前检测灯灭状态为{}'.format(level0_list))
            raise WindowsNetLightError('当前net_status灯状态不对')

    def check_statuslight_blink(self, times=20):
        """
        持续检测10次net_status灯闪烁状态
        :param times: 检测次数
        :return:
        """
        level_list = []
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            level_list.append(level_status)
        if 1 in level_list and 0 in level_list:
            all_logger.info('net_status灯状态为不停闪烁,状态正常')
        else:
            all_logger.info('当前高低电平状态为{}'.format(level_list))
            raise WindowsNetLightError('当前net_status灯状态不对')

    def check_wwanled_alwaysdown(self, times=10):
        """
        持续检测10次wwan_led灯常灭状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_wwan_led_gpio_level()
            level_status = status_list['level']
            if 0 == level_status:
                all_logger.info('第{}次检测为低电平,灯为常灭状态'.format(i))
            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常灭状态'.format(i, level_status))

    def check_wwanled_alwaysbright(self, times=10):
        """
        持续检测10次wwan_led灯常亮状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_wwan_led_gpio_level()
            level_status = status_list['level']
            if 1 == level_status:
                all_logger.info('第{}次检测为高电平,灯为常亮状态'.format(i))
            else:
                raise WindowsNetLightError('当前第{}次检测值为{},灯不为常亮状态'.format(i, level_status))
