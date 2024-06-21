import json
import os
import re
import shutil
import subprocess
import time
from zipfile import ZipFile
from utils.functions.gpio import GPIO
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
import pickle


class QFirehoseError(Exception):
    """QFirehose异常"""


class QFirehose:
    def __init__(self, *, at_port, dm_port, firmware_path, factory, package_name, ati, csub, **kwargs):
        """
        进行Linux系统下升级
        :param factory:是否进行全擦升级True:全擦工厂，False:不全擦标准
        """
        self.factory_flag = factory             # 是否进行全擦工厂升级
        self.gpio = GPIO()
        self.orig_package_name = package_name
        self.package_name = package_name + '_factory' if factory else package_name      # 升级版本的包名
        self.at_handle = ATHandle(at_port)
        self.firmware_path = firmware_path      # 升级版本的共享路径
        self.ati = ati  # ati版本号
        self.csub = csub  # at+csub版本号
        self.driver_check = DriverChecker(at_port, dm_port)
        # 处理传入的其他参数，例如IMEI和SN，在StartupManager类中可以找到
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        return self.__dict__.get(item, '')

    def factory_to_standard(self):
        """
        如果只实例化了一个QFirehose对象，如果想先升级工厂，再升级标准，不用多次实例化QFirehose。
        需要调用此函数修改内部一些参数，参照startup_manager.py的upgrade函数。
        :return: None
        """
        self.factory_flag = False
        self.package_name = self.orig_package_name

    @staticmethod
    def linux_edl_check():
        """
        Linux下检测模块是否进入紧急下载模式
        :return:True：紧急下载模式；False：USB模式
        """
        for i in range(10):
            usb_val = os.popen('lsusb').read()
            if '2c7c' in usb_val:
                all_logger.info('当前为USB模式')
                return False
            elif '9008' in usb_val:
                all_logger.info('当前为紧急下载模式')
                return True
            time.sleep(2)

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
            if '紧急下载模式' in str(e):       # 如果模块处于紧急下载模式，则先拉低powerkey
                all_logger.info('RM模块处于紧急下载模式，拉低powerkey后升级')
                self.gpio.set_pwk_low_level()
            self.qfirehose_upgrade()
            self.gpio.set_pwk_high_level()
            self.driver_check.check_usb_driver()
            self.check_urc()
            self.check_module_version()

    def qfirehose_upgrade(self):
        """
        Qfirehose升级
        :return:
        """
        # 确定版本包名称
        package_name = ''
        for root, dirs, files in os.walk('/root/TWS_TEST_DATA/PackPath'):
            if os.path.isdir(os.path.join('/root/TWS_TEST_DATA/PackPath', root)):
                if self.factory_flag:
                    if root.lower().endswith('factory') and self.package_name in root:
                        package_name = os.path.join('/root/TWS_TEST_DATA/PackPath', root)
                else:
                    if root.endswith(self.package_name):
                        package_name = os.path.join('/root/TWS_TEST_DATA/PackPath', root)
        if not package_name:
            raise QFirehoseError("未找到{}升级包".format('工厂' if self.factory_flag else '标准'))
        is_factory = ' -e' if 'factory' in package_name else ''   # 是否是工厂包升级，是的话指令需要加-e
        is_RG525FNAEB = ' -d emmc -n ' if 'RG525FNAEB' in package_name else ''  # noqa # RG525FNAEB定制
        val = os.popen('ps -ef | grep QFirehose').read()
        if 'QFirehose -f {}'.format(package_name) in val:
            try:
                kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                    all_logger.info('已关闭升级进程')
            except subprocess.TimeoutExpired:
                all_logger.info('关闭升级进程失败')
        start_time = time.time()
        upgrade = subprocess.Popen('QFirehose -f {}{}{}'.format(package_name, is_RG525FNAEB, is_factory), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        all_logger.info('QFirehose -f {}{}{}'.format(package_name, is_RG525FNAEB, is_factory))
        os.set_blocking(upgrade.stdout.fileno(), False)  # pylint: disable=E1101
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
                    raise QFirehoseError('请检查版本包路径是否填写正确')
                if 'Upgrade module failed' in upgrade_content:
                    all_logger.error('升级失败')
                    upgrade.terminate()
                    upgrade.wait()
                    self.vbat()
                    if self.check_usb():    # 如果重启后USB口可以正常加载，重新升级一次
                        all_logger.error('升级失败')
                        raise QFirehoseError('升级失败')
                    else:
                        all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                        raise QFirehoseError('升级失败，且重启后模块已处于紧急下载模式')
            if time.time() - start_time > 120:
                all_logger.error('120S内升级失败')
                upgrade.terminate()
                upgrade.wait()
                self.vbat()
                if self.check_usb():    # 如果重启后USB口可以正常加载，重新升级一次
                    all_logger.error('升级失败')
                    raise QFirehoseError('升级失败')
                else:
                    all_logger.error('升级失败，且重启后模块已处于紧急下载模式')
                    raise QFirehoseError('升级失败，且重启后模块已处于紧急下载模式')

    def check_module_version(self):
        """
        检查版本信息是否正确
        :return:
        """
        self.at_handle.send_at('ATE', 3)
        for i in range(10):
            try:
                # 版本号
                return_value = self.at_handle.send_at('ATI+CSUB', 0.6)
                revision = ''.join(re.findall(r'Revision: (.*)\r', return_value))
                sub_edition = ''.join(re.findall(r'SubEdition: (.*)\r', return_value))
                if revision == self.ati and sub_edition == self.csub.replace('-', ''):
                    all_logger.info(f"版本号：ATI: {self.ati}, CSUB: {self.csub.replace('-', '')} 检查成功")
                    break
            except Exception as e:
                all_logger.error(e)
            time.sleep(1)
        else:
            raise QFirehoseError("升级后版本号检查异常")

        # 如果是升级的factory版本，恢复SN等相关信息
        if self.factory_flag:
            self.restore_imei_sn_and_ect()

    def mount_package(self):
        """
        挂载版本包
        :return:
        """
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'firmware' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/firmware')
        for i in range(3):
            all_logger.info('mount -t cifs {} /mnt/firmware -o user="cris.hu@quectel.com",password="hxc111...."'.format(cur_package_path))
            all_logger.info(os.popen('mount -t cifs {} /mnt/firmware -o user="cris.hu@quectel.com",password="hxc111...."'.format(cur_package_path)).read())
            if os.listdir('/mnt/firmware'):
                all_logger.info('版本包挂载成功')
                break
            time.sleep(5)
        else:
            all_logger.info('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')
            raise QFirehoseError('版本包挂载失败,请检查版本包路径是否正确，或路径下是否存在版本包')

    @staticmethod
    def umount_package():
        """
        卸载已挂载的内容
        :return:
        """
        for i in range(10):
            time.sleep(3)
            os.popen('umount /mnt/firmware').read()
            if not os.listdir('/mnt/firmware'):
                all_logger.info('共享卸载成功')
                break

    def ubuntu_copy_file(self):
        """
        Ubuntu下复制版本包到PackPath目录下
        :return:
        """
        if not os.path.exists(r'/root/TWS_TEST_DATA/PackPath'):
            os.mkdir(r'/root/TWS_TEST_DATA/PackPath')

        cur_file_list = os.listdir('/mnt/firmware')
        all_logger.info('/mnt/firmware目录下现有如下文件:{}'.format(cur_file_list))
        all_logger.info(f'开始复制当前版本版本包:{self.package_name}到本地')
        for i in cur_file_list:
            if self.package_name + '.zip' in i:
                shutil.copy(os.path.join('/mnt/firmware', i), '/root/TWS_TEST_DATA/PackPath')

        if self.package_name + '.zip' in os.listdir('/root/TWS_TEST_DATA/PackPath'):
            all_logger.info('版本获取成功')
            self.unzip_firmware()   # 获取成功后进行解压
            return True
        else:
            raise QFirehoseError('版本包获取失败')

    def unzip_firmware(self):
        """
        解压/root/TWS_TEST_DATA/PackPath路径下的版本包
        :return: None
        """
        firmware_path = '/root/TWS_TEST_DATA/PackPath'
        try:
            for path, _, files in os.walk(firmware_path):
                for file in files:
                    if file.endswith('.zip') and self.package_name in file:
                        with ZipFile(os.path.join(path, file), 'r') as to_unzip:
                            all_logger.info('exact {} to {}'.format(os.path.join(path, file), path))
                            to_unzip.extractall(path)
        except Exception as e:
            all_logger.info(e)
            all_logger.info('版本包解压失败,卸载共享后重新挂载获取')
            self.umount_package()
            self.mount_package()
            raise QFirehoseError('解压版本包失败')
        all_logger.info('解压固件成功')
        os.popen(f'rm -rf /root/TWS_TEST_DATA/PackPath/{self.package_name}.zip').read()    # 最后删除压缩文件
        return True

    def check_package(self):
        """
        检测是否已存在升级文件
        :return:
        """
        if not os.path.exists(r'/root/TWS_TEST_DATA/PackPath'):     # 如果不存在PackPath目录，创建该目录并复制版本包
            os.mkdir(r'/root/TWS_TEST_DATA/PackPath')
            try:
                self.mount_package()
                self.get_package()
            finally:
                self.umount_package()
        else:       # 遍历目录，如果不存在版本包则从共享取版本包
            cur_file_list = os.listdir(r'/root/TWS_TEST_DATA/PackPath')
            if self.package_name not in cur_file_list:
                try:
                    self.mount_package()
                    self.get_package()
                finally:
                    self.umount_package()
            else:
                if 'devops' in self.firmware_path:       # 可能存在CI版本升V的情况，增加判断检查是否需要重新下载版本包
                    if not self.check_ci_package():      # 对比共享版本之前及当前版本包大小判断是否存在升V情况
                        try:
                            self.get_package()
                        finally:
                            self.umount_package()
                all_logger.info('已存在升级版本包，可直接升级')

    def get_package(self):
        """
        复制版本包到本地
        @return:
        """
        for i in range(3):
            try:
                if self.ubuntu_copy_file():
                    break
            except Exception as e:
                all_logger.info(e)
        else:
            raise QFirehoseError('三次获取版本包失败')

    def check_ci_package(self):
        """
        检查CI版本是否升V，根据版本包大小进行比较，将第一次下载的版本包存入json文件中，后续通过该文件查找比对大小，如果大小不一致则重新下载
        @return:  如果需要重新下载版本包:False；如果不需要:True
        """
        all_logger.info('当前为CI版本，需要检查版本是否存在升级情况，如果存在需要重新获取版本包')
        # 首先读取json文件获取记录的版本包大小
        json_path = os.path.join('/root/TWS_TEST_DATA/PackPath', 'package_info.json')
        content = {}
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                content = json.load(f)

        # 挂载远程，获取最新的版本包大小
        cur_package_path = self.firmware_path.replace('\\\\', '//').replace('\\', '/').replace(' ', '\\ ')
        if 'firmware' not in os.listdir('/mnt'):
            os.mkdir('/mnt' + '/firmware')
        all_logger.info('mount -t cifs {} /mnt/firmware -o user="cris.hu@quectel.com",password="hxc111...."'.format(cur_package_path))
        all_logger.info(os.popen('mount -t cifs {} /mnt/firmware -o user="cris.hu@quectel.com",password="hxc111...."'.format(cur_package_path)).read())

        remote_factory_package_name = os.path.join('/mnt/firmware', self.orig_package_name + '_factory.zip')
        remote_standard_package_name = os.path.join('/mnt/firmware', self.orig_package_name + '.zip')

        remote_factory_size = os.path.getsize(remote_factory_package_name)
        remote_standard_size = os.path.getsize(remote_standard_package_name)
        all_logger.info(f'挂载后工厂包大小为{remote_factory_size}')
        all_logger.info(f'挂在后标准包大小为{remote_standard_size}')

        factory_info = {self.orig_package_name + '_factory.zip': remote_factory_size}
        standard_info = {self.orig_package_name + '.zip': remote_standard_size}

        # 对比文件中记载包大小及当下包大小
        try:
            if content[f"{self.orig_package_name}_factory.zip"] != remote_factory_size:
                all_logger.info('工厂包大小不一致')
                all_logger.info(f'当前共享中版本包大小为{remote_factory_size}，记录之前版本包大小为{content[f"{self.orig_package_name}_factory.zip"]}')
                all_logger.info('版本可能升V，需要重新下载版本包')
                content.update(factory_info)
                content.update(standard_info)
                with open(json_path, 'w') as f_new:
                    json.dump(content, f_new)
                return False
            else:
                all_logger.info('工厂包大小一致')
        except Exception:   # noqa
            all_logger.info('当前版本包第一次下载，不存在升V情况')
            content.update(factory_info)
            content.update(standard_info)
            with open(json_path, 'w') as f_new:
                json.dump(content, f_new)
            return True

        try:
            if content[f"{self.orig_package_name}.zip"] != remote_standard_size:
                all_logger.info('标准包大小不一致')
                all_logger.info(f'当前共享中版本包大小为{remote_standard_size}，记录之前版本包大小为{content[f"{self.orig_package_name}.zip"]}')
                all_logger.info('版本可能升V，需要重新下载版本包')
                content.update(factory_info)
                content.update(standard_info)
                with open(json_path, 'w') as f_new:
                    json.dump(content, f_new)
                return False
            else:
                all_logger.info('标准包大小一致')
                return True
        except Exception:   # noqa
            all_logger.info('当前版本包第一次下载，不存在升V情况')
            content.update(factory_info)
            content.update(standard_info)
            with open(json_path, 'w') as f_new:
                json.dump(content, f_new)
            return True

    @staticmethod
    def check_usb():
        """
        检查当前是紧急下载模式还是USB模式
        :return:True：USB模式；False：紧急下载模式
        """
        for i in range(10):
            usb_val = os.popen('lsusb').read()
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

    def check_usb_loaded(self, ports):
        """
        检测USB驱动正常加载
        :return:
        """
        if self.driver_check.check_usb_driver():
            return True
        else:
            all_logger.error(f"模块未正常开机或模块开机后端口列表变化：\n期望端口列表包含：{ports}\n当前端口列表：{self.driver_check.get_port_list()}")

    def check_cpin(self):
        """
        检查模块CPIN状态
        @return:
        """
        cpin_value = self.at_handle.send_at('AT+CPIN?', 3)
        if 'READY' in cpin_value:
            return True
        else:
            raise QFirehoseError('升级完成后未检测到PB Done，且CPIN值检查异常')

    def check_urc(self):
        """
        检测开机URC直到PB Done
        """
        time.sleep(3)   # 等待一会再打开端口检测
        try:
            self.at_handle.readline_keyword('PB DONE', timout=60)
        except Exception:   # noqa
            self.check_cpin()

    def restore_imei_sn_and_ect(self):
        """
        当我们升级工厂版本后，会将Resource(https://tws.quectel.com:8152/Cluster/Device)节点中的IMEI Number写入IMEI1，SN写入。
        其中分为两种情况：
        1. 如果是在utils.cases.startup_manager的StartupManager中调用升级动作，无法获取IMEI和SN，需要通过device_id进行反查
            https://ticket.quectel.com/browse/ST5G-70
        2. 如果是在其他Case中调用，因为Common APP中写入了auto_python_params文件，所以直接从文件中读取，避免了传参的麻烦
        :return: None
        """

        def write_imei_and_check(imei):
            """
            写入IMEI并且查询。
            :param imei: IMEI号
            :return: None
            """
            if imei:  # 如果IMEI不为空
                # 判断是否一致，一致不写入
                imei_status = self.at_handle.send_at("AT+EGMR=0,7", timeout=1)
                if imei in imei_status:
                    all_logger.info("当前IMEI查询与Resource设置值一致")
                    return True

                # 不一致写入
                all_logger.info(f"写入IMEI1: {imei}")
                self.at_handle.send_at(f'AT+EGMR=1,7,"{imei}"', timeout=1)

                # 写入后查询
                imei_status = self.at_handle.send_at("AT+EGMR=0,7", timeout=1)
                if imei not in imei_status:
                    all_logger.error(f"写入IMEI1后，查询的返回值异常：{imei_status}，期望：{imei}")
            else:
                all_logger.error("\nTWS Resource界面可能未配置IMEI1，请检查" * 3)

        def write_sn_and_check(sn):
            """
            写入SN号并且查询
            :param sn: SN号
            :return: None
            """
            if sn:  # 如果SN不为空
                # 判断是否一致，一致不写入
                sn_status = self.at_handle.send_at("AT+EGMR=0,5", timeout=1)
                if sn in sn_status:
                    all_logger.info("当前IMEI查询与Resource设置值一致")
                    return True

                # 不一致写入
                all_logger.info(f"写入SN: {sn}")
                self.at_handle.send_at(f'AT+EGMR=1,5,"{sn}"', timeout=1)

                # 写入后查询
                sn_status = self.at_handle.send_at("AT+EGMR=0,5", timeout=1)
                if sn not in sn_status:
                    all_logger.error(f"写入sn后，查询的返回值异常：{sn_status}，期望：{sn}")
            else:
                all_logger.error("\nTWS Resource界面可能未配置SN，请检查" * 3)

        # 目前支持升级factory版本后写入重新写入IMEI和SN
        imei = getattr(self, 'imei', '')
        sn = getattr(self, 'sn', '')

        if sn or imei:  # SN或者IMEI不为None，说明是传参进来的，直接使用传参的值:
            write_imei_and_check(self.imei)
            write_sn_and_check(self.sn)
        elif os.path.exists('auto_python_params'):  # 说明是Case调用，Case调用会在脚本目录生成auto_python_params文件，将其中的值取出
            with open('auto_python_params', 'rb') as p:
                # original_setting
                args = pickle.load(p).test_setting  # noqa
                if not isinstance(args, dict):
                    args = eval(args)
                imei = args.get('res')[0].get("imei_number", '')
                sn = args.get('res')[0].get("sn", '')
                write_imei_and_check(imei)
                write_sn_and_check(sn)
        else:
            all_logger.info("未查找到auto_python_params，也未传参IMEI和SN，不进行IMEI和SN号的恢复")


if __name__ == '__main__':
    params = {'factory': False, 'at_port': '/dev/ttyUSBAT', 'dm_port': '/dev/ttyUSBDM',
              'expect_version': 'RG500QEAAAR11A05M4GV01',
              'firmware_path': r'\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX55\RG500QEA\Release\RG500QEA_H_R11\RG500QEAAAR11A05M4G_01.001V01.01.001V01',
              'package_name': 'RG500QEAAAR11A05M4G_01.001V01.01.001V01'}
