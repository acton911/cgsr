import os
import re
import subprocess
import time
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker


class Reboot_PCIE:
    def __init__(self, pcie_driver_path, at_port, dm_port, pci_path):
        self.pcie_driver_path = pcie_driver_path
        self._at_port = at_port
        self._dm_port = dm_port
        self.at_handler = ATHandle(at_port)
        self.driver = DriverChecker(at_port, dm_port)
        self.port_list = DriverChecker(at_port, dm_port)
        self.pci_path = pci_path

    def check_pcie_driver_alltime(self, device_id='0306', pcie_mbim_mode=False):
        """
        被动检测模块重启并自动加载驱动
        一直检测usb驱动，一旦USB消失则运行驱动安装程序
        用于PCIE测试机重启(包括升级)后自动安装驱动
        """
        global full_pci_devices_path
        print('lspci -v')
        value_lspci_v = subprocess.getoutput('lspci -v')
        # 匹配由16进制组成的PCIE插槽位置路径，例：00:1f.1
        pci_devices_path1 = ''.join(re.findall(r'([0-9a-fA-F]+):[0-9a-fA-F]+.[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path2 = ''.join(re.findall(r'[0-9a-fA-F]+:([0-9a-fA-F]+).[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path3 = ''.join(re.findall(r'[0-9a-fA-F]+:[0-9a-fA-F]+.([0-9a-fA-F]+).*?{}'.format(device_id), value_lspci_v))
        # 拼接成linux下可执行的路径名
        if pci_devices_path1 and pci_devices_path2 and pci_devices_path3:
            full_pci_devices_path = '/sys/bus/pci/devices/0000\:{}\:{}.{}'.format(pci_devices_path1, pci_devices_path2, pci_devices_path3)
            print("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))
        else:
            full_pci_devices_path = self.pci_path
            # full_pci_devices_path = '/sys/bus/pci/devices/0000\:01\:00.0'
            print("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))
        while True:
            time.sleep(0.01)
            # 删除ubuntu20.04自带驱动，避免和pcie驱动冲突
            print('rmmod mhi-pci-generic')
            subprocess.getoutput("rmmod mhi-pci-generic")  # ubuntu20.04需要卸载此驱动，否则冲突
            time.sleep(3)
            self.check_usb_driver_dis_alltime()
            print('rmmod mhi-pci-generic')
            subprocess.getoutput("rmmod mhi-pci-generic")  # ubuntu20.04需要卸载此驱动，否则冲突
            time.sleep(3)
            # 卸载当前pcie驱动 （按STSDX55-4169要求，去除此操作）
            # print('rmmod pcie_mhi.ko')
            # subprocess.getoutput('rmmod pcie_mhi.ko')
            # time.sleep(3)
            while True:
                port_list = self.port_list.get_port_list()
                if self._at_port not in port_list and self._dm_port not in port_list:
                    # 先移除驱动
                    print('echo 1 > {}/remove'.format(full_pci_devices_path))
                    subprocess.getoutput('echo 1 > {}/remove'.format(full_pci_devices_path))
                    time.sleep(2)
                    # 重新加载驱动
                    print('echo 1 > /sys/bus/pci/rescan')
                    subprocess.getoutput('echo 1 > /sys/bus/pci/rescan')
                    time.sleep(2)
                else:
                    print("已检测到模块开机")
                    break
            # 检查重启后pci识别是否正常
            self.driver.check_usb_driver()
            time.sleep(3)
            print('lspci')
            lspci_value = subprocess.getoutput('lspci')
            if device_id not in lspci_value:
                print("重启后模块PCIE识别失败,未检测到device id：{}".format(device_id))
            # 加载pcie驱动
            time.sleep(3)
            """
            # 按STSDX55-4169要求，去除此操作
            if pcie_mbim_mode:
                print('insmod pcie_mhi.ko {}/mhi_mbim_enabled=1'.format(self.pcie_driver_path))
                subprocess.getoutput("insmod {}/pcie_mhi.ko mhi_mbim_enabled=1".format(self.pcie_driver_path))
            else:
                print('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))
                subprocess.getoutput('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))
            time.sleep(3)
            """
            self.driver.check_usb_driver()
            if pcie_mbim_mode:
                self.check_pcie_driver_mbim()
            else:
                self.check_pcie_driver()

    def switch_pcie_mode(self, device_id='0306', pcie_mbim_mode=False):
        """
        主动切换pcie驱动，不重启模块
        """
        global full_pci_devices_path
        print('lspci -v')
        value_lspci_v = subprocess.getoutput('lspci -v')
        # 匹配由16进制组成的PCIE插槽位置路径，例：00:1f.1
        pci_devices_path1 = ''.join(re.findall(r'([0-9a-fA-F]+):[0-9a-fA-F]+.[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path2 = ''.join(re.findall(r'[0-9a-fA-F]+:([0-9a-fA-F]+).[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path3 = ''.join(re.findall(r'[0-9a-fA-F]+:[0-9a-fA-F]+.([0-9a-fA-F]+).*?{}'.format(device_id), value_lspci_v))
        # 拼接成linux下可执行的路径名
        if pci_devices_path1 and pci_devices_path2 and pci_devices_path3:
            full_pci_devices_path = '/sys/bus/pci/devices/0000\:{}\:{}.{}'.format(pci_devices_path1, pci_devices_path2, pci_devices_path3)
            print("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))
        else:
            full_pci_devices_path = self.pci_path
            # full_pci_devices_path = '/sys/bus/pci/devices/0000\:01\:00.0'
            print("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))

        # 需要切换到的模式
        if pcie_mbim_mode:
            # 切换到MBIM
            # 卸载当前pcie驱动
            print('rmmod pcie_mhi.ko')
            subprocess.getoutput('rmmod pcie_mhi.ko')
            time.sleep(3)
            # 先移除驱动
            print('echo 1 > {}/remove'.format(full_pci_devices_path))
            subprocess.getoutput('echo 1 > {}/remove'.format(full_pci_devices_path))
            time.sleep(2)
            # 重新加载驱动
            print('echo 1 > /sys/bus/pci/rescan')
            subprocess.getoutput('echo 1 > /sys/bus/pci/rescan')
            time.sleep(2)
            # ubuntu20.04需要卸载此驱动，否则冲突
            print('rmmod mhi-pci-generic')
            subprocess.getoutput("rmmod mhi-pci-generic")
            time.sleep(3)
            # 安装MBIM驱动
            print('insmod pcie_mhi.ko {}/mhi_mbim_enabled=1'.format(self.pcie_driver_path))
            subprocess.getoutput("insmod {}/pcie_mhi.ko mhi_mbim_enabled=1".format(self.pcie_driver_path))
        else:
            # 切换到QMI
            # 卸载当前pcie驱动
            print('rmmod pcie_mhi.ko')
            subprocess.getoutput('rmmod pcie_mhi.ko')
            time.sleep(3)
            # 先移除驱动
            print('echo 1 > {}/remove'.format(full_pci_devices_path))
            subprocess.getoutput('echo 1 > {}/remove'.format(full_pci_devices_path))
            time.sleep(2)
            # 重新加载驱动
            print('echo 1 > /sys/bus/pci/rescan')
            subprocess.getoutput('echo 1 > /sys/bus/pci/rescan')
            time.sleep(2)
            # ubuntu20.04需要卸载此驱动，否则冲突
            print('rmmod mhi-pci-generic')
            subprocess.getoutput("rmmod mhi-pci-generic")
            time.sleep(3)
            # 安装QMI驱动
            print('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))
            subprocess.getoutput('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))
        time.sleep(3)
        # 检查pci识别是否正常
        print('lspci')
        lspci_value = subprocess.getoutput('lspci')
        if device_id not in lspci_value:
            print("模块PCIE识别失败,未检测到device id：{}".format(device_id))
        time.sleep(5)
        if pcie_mbim_mode:
            self.check_pcie_driver_mbim()
        else:
            self.check_pcie_driver()

    def check_usb_driver_dis_alltime(self):
        """
        检测某个COM口是否消失
        :return: None
        """
        print('自动检测重启并安装PCIE驱动ing...')
        while True:
            port_list = self.port_list.get_port_list()
            if self._at_port not in port_list and self._dm_port not in port_list:
                print('USB驱动{}掉口成功!'.format(self._at_port))
                break
            else:
                time.sleep(0.1)

    def check_pcie_driver(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK', '/dev/mhi_QMI0']
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        print('执行ls /dev/mhi*返回{}'.format(driver_value))
        for i in driver_list:
            if i in driver_value:
                continue
            else:
                print('PCIE驱动检测失败，未检测到{}驱动'.format(i))
        else:
            print('PCIE驱动检测正常')

    def check_pcie_driver_mbim(self):
        """
        查询PCIE驱动是否加载正常
        :return: None
        """
        driver_list = ['/dev/mhi_BHI', '/dev/mhi_DIAG', '/dev/mhi_DUN', '/dev/mhi_LOOPBACK', '/dev/mhi_MBIM']
        driver_value = os.popen('ls /dev/mhi*').read().replace('\n', '  ')
        print('执行ls /dev/mhi*返回{}'.format(driver_value))
        for i in driver_list:
            if i in driver_value:
                continue
            else:
                print('PCIE驱动检测失败，未检测到{}驱动'.format(i))
        else:
            print('PCIE驱动检测正常')

    def reboot_to_pcie(self, device_id='0306', pcie_mbim_mode=False):
        """
        主动单次重启并重新安装驱动
        """
        # 查询PCIE模块所在插槽信息
        print('lspci -v')
        value_lspci_v = subprocess.getoutput('lspci -v')

        # 匹配由16进制组成的PCIE插槽位置路径，例：00:1f.1
        pci_devices_path1 = ''.join(re.findall(r'([0-9a-fA-F]+):[0-9a-fA-F]+.[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path2 = ''.join(re.findall(r'[0-9a-fA-F]+:([0-9a-fA-F]+).[0-9a-fA-F]+.*?{}'.format(device_id), value_lspci_v))
        pci_devices_path3 = ''.join(re.findall(r'[0-9a-fA-F]+:[0-9a-fA-F]+.([0-9a-fA-F]+).*?{}'.format(device_id), value_lspci_v))

        # 拼接成linux下可执行的路径名
        if pci_devices_path1 and pci_devices_path2 and pci_devices_path3:
            full_pci_devices_path = '/sys/bus/pci/devices/0000\:{}\:{}.{}'.format(pci_devices_path1, pci_devices_path2, pci_devices_path3)
            print("当前模块PCIE插槽位置路径为：{}".format(full_pci_devices_path))
        else:
            print("获取当前PCIE模块插槽位置路径失败，请确认模块状态和device id是否正确")

        # 卸载当前pcie驱动
        print('rmmod pcie_mhi.ko')
        subprocess.getoutput('rmmod pcie_mhi.ko')
        time.sleep(3)

        # 重启模块
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()

        # 先移除驱动
        print('echo 1 > {}/remove'.format(full_pci_devices_path))
        subprocess.getoutput('echo 1 > {}/remove'.format(full_pci_devices_path))

        time.sleep(3)

        # 重新加载驱动
        print('echo 1 > /sys/bus/pci/rescan')
        subprocess.getoutput('echo 1 > /sys/bus/pci/rescan')

        self.driver.check_usb_driver()
        time.sleep(3)

        # 检查重启后pci识别是否正常
        print('lspci')
        lspci_value = subprocess.getoutput('lspci')
        if device_id not in lspci_value:
            print("重启后模块PCIE识别失败,未检测到device id：{}".format(device_id))

        # 加载pcie驱动
        time.sleep(3)
        print('rmmod mhi-pci-generic')
        subprocess.getoutput("rmmod mhi-pci-generic")  # ubuntu20.04需要卸载此驱动，否则冲突

        time.sleep(3)

        if pcie_mbim_mode:
            print('insmod pcie_mhi.ko {}/mhi_mbim_enabled=1'.format(self.pcie_driver_path))
            subprocess.getoutput("insmod {}/pcie_mhi.ko mhi_mbim_enabled=1".format(self.pcie_driver_path))
        else:
            print('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))
            subprocess.getoutput('insmod {}/pcie_mhi.ko'.format(self.pcie_driver_path))

        time.sleep(3)
        self.driver.check_usb_driver()
        self.at_handler.check_network()
        if pcie_mbim_mode:
            self.check_pcie_driver_mbim()
        else:
            self.check_pcie_driver()


if __name__ == '__main__':
    # 01:00.0
    """
    pci_path_all = input("请输入PCI插槽位置(lspci -v查询所得,例如01:00.0),不输入默认为01:00.0:")
    if pci_path_all:
        pci_devices_path1 = ''.join(re.findall(r'([0-9a-fA-F]+):[0-9a-fA-F]+.[0-9a-fA-F]+.*?', pci_path_all))
        pci_devices_path2 = ''.join(re.findall(r'[0-9a-fA-F]+:([0-9a-fA-F]+).[0-9a-fA-F]+.*?', pci_path_all))
        pci_devices_path3 = ''.join(re.findall(r'[0-9a-fA-F]+:[0-9a-fA-F]+.([0-9a-fA-F]+).*?', pci_path_all))
        pci_path = '/sys/bus/pci/devices/0000\:{}\:{}.{}'.format(pci_devices_path1, pci_devices_path2, pci_devices_path3)
    else:
        pci_path = '/sys/bus/pci/devices/0000\:01\:00.0'
    pcie_driver_path = input("请输入PCIE驱动路径,不输入默认为/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi:")
    if pcie_driver_path:
        pass
    else:
        pcie_driver_path = '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi'
    at_port = input("请输入USB AT口名称,不输入默认为/dev/ttyUSBAT:")
    if at_port:
        pass
    else:
        at_port = '/dev/ttyUSBAT'
    dm_port = input("请输入USB DM口名称,不输入默认为/dev/ttyUSBDM:")
    if dm_port:
        pass
    else:
        dm_port = '/dev/ttyUSBDM'
    params = {
        'pcie_driver_path': pcie_driver_path,
        'at_port': at_port,
        'dm_port': dm_port,
        'pci_path': pci_path,
    }
    s = Reboot_PCIE(**params)
    input_value = input("请输入安装驱动类型QMI或者MBIM(注意大写),不输入默认为QMI:")
    if input_value == 'MBIM':
        s.check_pcie_driver_alltime(pcie_mbim_mode=True)
    elif input_value == 'QMI':
        s.check_pcie_driver_alltime()
    elif input_value == '':
        s.check_pcie_driver_alltime()
    else:
        print("Error Input!!!")
    """
    params = {
        'pcie_driver_path': '/home/ubuntu/Tools_Ubuntu_SDX55/Drivers/pcie_mhi',
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'pci_path': '/sys/bus/pci/devices/0000\:01\:00.0',
    }
    s = Reboot_PCIE(**params)
    s.check_pcie_driver_alltime()
