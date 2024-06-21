import os
import re
import shutil
import subprocess
import time
from sys import path
path.append(os.path.join('..', '..'))
from zipfile import ZipFile
from utils.functions.gpio import GPIO
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle
from utils.exception.exceptions import NormalError
from utils.functions.driver_check import DriverChecker


class Linux_Custom_Upgrade:
    def __init__(self, factory, at_port, dm_port, expect_version, firmware_path, package_name):
        """
        进行Linux系统下升级
        :param factory:是否进行全擦升级True:全擦工厂，False:不全擦标准
        """
        self.factory_flag = factory             # 是否进行全擦工厂升级
        self.gpio = GPIO()
        self.package_name = package_name        # 升级版本的包名
        self.at_handle = ATHandle(at_port)
        self.firmware_path = firmware_path      # 升级版本的共享路径
        self.expect_version = expect_version    # 升级后的版本号对比
        self.driver_check = DriverChecker(at_port, dm_port)
        self.version_flag = True if 'RG' in self.at_handle.send_at('ati') else False    # 标记当前版本是RG还是RM

    def linux_upgrade(self):
        """
        linux下升级
        :return:
        """
        self.check_package()    # 首先检查版本包是否已存在
        try:
            self.qfirehose_upgrade()     # 如果升级失败，再来一次
            self.driver_check.check_usb_driver()
            self.check_urc()
            self.check_module_version()
        except Exception as e:
            if '紧急下载模式' in str(e) and not self.version_flag:       # 如果RM模块处于紧急下载模式，则先拉低powerkey
                all_logger.info('RM模块处于紧急下载模式，拉低powerkey后升级')
                self.gpio.set_pwk_low_level()
            else:
                all_logger.info('RG模块处于紧急下载模式，直接进行升级')
            self.qfirehose_upgrade()
            self.driver_check.check_usb_driver()
            self.check_urc()
            self.check_module_version()

    def qfirehose_upgrade(self,):
        """
        Qfirehose升级
        :return:
        """
        # 确定版本包名称
        package_name = ''
        for p in os.listdir('/root/TWS_TEST_DATA/PackPath'):
            if os.path.isdir(os.path.join('/root/TWS_TEST_DATA/PackPath', p)):
                if self.factory_flag:
                    if p.lower().endswith('factory') and self.package_name in p:
                        package_name = os.path.join('/root/TWS_TEST_DATA/PackPath', p)
                else:
                    if not p.lower().endswith('factory') and self.package_name in p:
                        package_name = os.path.join('/root/TWS_TEST_DATA/PackPath', p)
        if not package_name:
            raise Exception("未找到{}升级包".format('工厂' if self.factory_flag else '标准'))
        is_factory = True if 'factory' in package_name else False    # 是否是工厂包升级，是的话指令需要加-e
        val = os.popen('ps -ef | grep QFirehose').read()
        if 'QFirehose -f {}'.format(package_name) in val:
            try:
                kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                    all_logger.info('已关闭升级进程')
            except subprocess.TimeoutExpired:
                all_logger.info('关闭升级进程失败')
        start_time = time.time()
        upgrade = subprocess.Popen('QFirehose -f {} {}'.format(package_name, '-e' if is_factory else ''), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        all_logger.info('QFirehose -f {} {}'.format(package_name, '-e' if self.factory_flag else ''))
        os.set_blocking(upgrade.stdout.fileno(), False)
        while True:
            time.sleep(0.001)
            upgrade_content = upgrade.stdout.readline().decode('utf-8')
            if upgrade_content != '':
                if upgrade_content == '.':
                    continue
                all_logger.info(repr(upgrade_content).replace("'", ''))
                if 'Upgrade module successfully' in upgrade_content:
                    all_logger.info('升级成功')
                    upgrade.terminate()
                    upgrade.wait()
                    return True
                if 'fail to access {}'.format(package_name) in upgrade_content:
                    raise NormalError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.error('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    self.vbat()
                    if self.check_usb():    # 如果重启后USB口可以正常加载，重新升级一次
                        all_logger.error('升级失败')
                        raise NormalError('升级失败')
                    else:
                        all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                        raise NormalError('升级失败，且重启后模块已处于紧急下载模式')
            if time.time() - start_time > 120:
                all_logger.error('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                self.vbat()
                if self.check_usb():    # 如果重启后USB口可以正常加载，重新升级一次
                    all_logger.error('升级失败')
                    raise NormalError('升级失败')
                else:
                    all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                    raise NormalError('升级失败，且重启后模块已处于紧急下载模式')

    def check_module_version(self):
        """
        检查版本信息是否正确
        :return:
        """
        self.at_handle.send_at('ATE', 3)
        csub_value = self.at_handle.send_at('ATI+CSUB', 10)
        at_revison = ''.join(re.findall(r'Revision: (.*)', csub_value))
        at_sub = ''.join(re.findall(r'SubEdition: (.*)', csub_value))
        at_version = at_revison + at_sub
        version_r = re.sub(r'[\r\n]', '', at_version)
        if self.expect_version != version_r:
            raise NormalError('系统下发版本号与升级后查询版本号不一致，系统下发为{}，AT指令查询为{}'.format(self.expect_version, at_version))

    def mount_package(self):
        """
        挂载版本包
        :return:
        """
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'firmware' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/firmware')
        all_logger.info(os.popen('mount -t cifs {} /mnt/firmware -o user="cris.hu@quectel.com",password="hxc111...."'.format(
            cur_package_path)).read())
        if os.listdir('/mnt/firmware'):
            all_logger.info('版本包挂载成功')
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise NormalError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        os.popen('umount /mnt/firmware')

    def ubuntu_copy_file(self):
        """
        Ubuntu下复制版本包到PackPath目录下
        :return:
        """
        if not os.path.exists(r'/root/TWS_TEST_DATA/PackPath'):
            os.mkdir(r'/root/TWS_TEST_DATA/PackPath')

        cur_file_list = os.listdir('/mnt/firmware')
        all_logger.info('PackPath目录下现有如下文件:{}'.format(cur_file_list))
        all_logger.info('开始复制当前版本版本包到本地')
        for i in cur_file_list:
            if self.factory_flag:
                if 'factory' in i:
                    shutil.copy(os.path.join('/mnt/firmware', i), '/root/TWS_TEST_DATA/PackPath')
            else:
                if 'factory' not in i:
                    shutil.copy(os.path.join('/mnt/firmware', i), '/root/TWS_TEST_DATA/PackPath')

        if self.package_name + '.zip' in os.listdir('/root/TWS_TEST_DATA/PackPath'):
            all_logger.info('版本获取成功')
            self.unzip_firmware()   # 获取成功后进行解压
        else:
            raise NormalError('版本包获取失败')

    def unzip_firmware(self):
        """
        解压/root/TWS_TEST_DATA/PackPath路径下的版本包
        :return: None
        """
        firmware_path = '/root/TWS_TEST_DATA/PackPath'
        for path, _, files in os.walk(firmware_path):
            for file in files:
                if file.endswith('.zip') and self.package_name in file:
                    with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                        all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                        to_unzip.extractall(path)
                        os.popen(f'rm -rf /root/TWS_TEST_DATA/PackPath/{self.package_name}.zip').read()    # 最后删除压缩文件
        all_logger.info('解压固件成功')

    def check_package(self):
        """
        检测是否已存在升级文件
        :return:
        """
        if not os.path.exists(r'/root/TWS_TEST_DATA/PackPath'):     # 如果不存在PackPath目录，创建该目录并复制版本包
            os.mkdir(r'/root/TWS_TEST_DATA/PackPath')
            try:
                self.mount_package()
                self.ubuntu_copy_file()
            finally:
                self.umount_package()
        else:       # 遍历目录，如果不存在版本包则从共享取版本包
            cur_file_list = os.listdir(r'/root/TWS_TEST_DATA/PackPath')
            if self.package_name not in cur_file_list:
                try:
                    self.mount_package()
                    self.ubuntu_copy_file()
                finally:
                    self.umount_package()
            else:
                all_logger.info('已存在升级版本包，可直接升级')

    @staticmethod
    def check_usb():
        """
        检查当前是紧急下载模式还是USB模式
        :return:True：USB模式；False：紧急下载模式
        """
        for i in range(10):
            usb_val = os.popen('lsusb -t').read()
            if '2c7c' in usb_val:
                all_logger.info('当前为USB模式')
                time.sleep(10)
                return True
            elif '9008' in usb_val:
                all_logger.info('当前为紧急下载模式')
                return False
            time.sleep(2)

    def vbat(self):
        """
        vbat方式重启模块
        :return:
        """
        self.gpio.set_vbat_high_level()
        time.sleep(3)
        self.gpio.set_vbat_low_level_and_pwk()

    def check_urc(self):
        """
        检测开机URC直到PB Done
        """
        time.sleep(3)   # 等待一会再打开端口检测
        self.at_handle.readline_keyword('PB DONE', timout=60)


if __name__ == '__main__':
    params = {'factory': False, 'at_port': '/dev/ttyUSBAT', 'dm_port': '/dev/ttyUSBDM',
              'expect_version': 'RG500QEAAAR11A05M4GV01',
              'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A05M4G_01.001V01.01.001V01',
              'package_name': 'RG500QEAAAR11A05M4G_01.001V01.01.001V01'}
    up = Linux_Custom_Upgrade(**params)
    up.linux_upgrade()
