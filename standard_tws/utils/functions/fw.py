# -*- encoding=utf-8 -*-
import re
import os
import time
import shutil
import getpass
import subprocess
import zipfile
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
import concurrent.futures
from utils.exception.exceptions import FatalError
import pickle

# 笔电专用升级


class FWError(Exception):
    """QFIL工具升级异常"""


class FW:

    def __init__(self, *, at_port, dm_port, firmware_path, factory, ati, csub, **kwargs):
        self.factory = factory
        self.at_port = at_port
        self.dm_port = dm_port
        self.ati = ati
        self.csub = csub
        self.firmware_path = firmware_path
        self.at_handle = ATHandle(self.at_port)
        self.driver_handle = DriverChecker(at_port, dm_port)
        self.local_firmware_path = ''  # 下载的升级包路径
        # 处理传入的其他参数，例如IMEI和SN，在StartupManager类中可以找到
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        return self.__dict__.get(item, '')

    def factory_to_standard(self):
        """
        如果只实例化了一个FW对象，如果想先升级工厂，再升级标准，不用多次实例化FW。
        需要调用此函数修改内部一些参数，参照startup_manager.py的upgrade函数。
        :return: None
        """
        self.factory = False

    def upgrade(self):
        """
        1. 检测当前环境是否安装驱动
            C:\\Windows\\Firmware\\Quectel\\RM520NGLAP\\Application\\FWUpgrade
        2. 禁用QServiceRM520NGLAP
        3. 下载版本包
        4. 升级
        5. 检测网卡驱动
        6. 检测MBIM拨号
        7. 使用QModeSwitch_RM520_V1.0.1.exe -p 0打开所有口
        8. 检测AT口，DM口
        9. 查询当前版本号
        """
        # 检测驱动是否安装并获取FW工具->禁用QServiceRM520XXX->下载解压版本包->获取版本包的firehose路径
        fw_path = self.get_fw_path()
        self.disable_wu_service()
        self.copy_and_unzip_firmware()
        firehose_path = self.get_firehose_path()

        # 升级
        self.fw_upgrade(fw_path, firehose_path)

        # 检测网卡驱动加载(重新开机)—>检测MBIM功能加载正常
        self.check_network_card()
        self.check_mbim_loaded()

        # 打开所有端口->判断AT口DM口是否存在->检查版本号->结束
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.open_all_ports_and_check(q_mode_switch_path)
        self.check_module_version()

    def open_all_ports_and_check(self, mode_switch_path):
        """
        切换模块为all port模式
        :param mode_switch_path: QModeSwitch工具的路径
        :return: None
        """
        port_list = list()
        for _ in range(3):
            cmd = f"{mode_switch_path} -p 0"
            output = subprocess.getoutput(cmd)
            all_logger.info(f"cmd: {cmd}\noutput:{output}")

            all_logger.info("wait 3 seconds")

            port_list = self.driver_handle.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                all_logger.info("QModeSwitch打开所有端口成功")
                all_logger.info("wait 5 seconds")
                time.sleep(5)
                return True

            time.sleep(3)
        else:
            raise FWError(f"连续三次使用QModeSwitch工具打开端口失败，期望AT口({self.at_port}), DM口({self.dm_port})\n"
                          f"当前端口列表：{port_list}")

    def get_q_mode_switch_path(self):
        """
        获取本机的QModeSwitch工具的路径，默认 C:\\Users\\q\\Desktop\\Tools 下
        """
        check_path = fr"C:\Users\{getpass.getuser()}\Desktop\Tools"
        pattern = self.ati[:5]  # QModeSwitch_RM520_xxxx.exe，所以取ATI前五位判断QModeSwitch是否正常
        for path, _, files in os.walk(check_path):
            for file in files:
                if file.endswith('.exe') and file.startswith("QModeSwitch") and pattern in file:
                    mode_switch_tool_path = os.path.join(path, file)
                    return mode_switch_tool_path
        raise FWError(f"在{check_path}中未找到适合{pattern}的QModeSwitch，请检查工具文件夹是否存在，版本是否正常")

    @staticmethod
    def check_mbim_loaded():
        """
        检查MBIM功能是否正常
        """
        for _ in range(100):
            mbn_status = subprocess.getoutput("netsh mbn show interface")
            all_logger.info(mbn_status)
            regex_status = ''.join(re.findall(r'\s\d\s', mbn_status))  # 为了兼容中英文，仅匹配 ”系统上有 1 个接口“中的 ” 1 “
            if regex_status:
                all_logger.info("MBIM功能加载成功")
                return True
            time.sleep(3)
        else:
            raise FWError("MBIM功能100S内未正常加载")

    def check_network_card(self):
        """
        根据版本号，生成网卡，检查对应网卡是否加载
        """
        from utils.functions.setupapi import get_network_card_names

        network_cards = list()
        for _ in range(300):
            network_cards = get_network_card_names()
            network_cards = ''.join(network_cards).upper()  # 转换为大写好判断
            network_card_name_part = self.ati[:5]  # 网卡名为 "Quectel WWAN RM520N-GL"，取ATI前五位判断，即：判断RM520N是否在驱动列表
            if 'QUECTEL' in network_cards and network_card_name_part in network_cards:
                all_logger.info("网卡驱动已成功加载")
                return True
            time.sleep(1)
        else:
            raise FWError(f"300S内网卡未正常加载，网卡列表：{network_cards}")

    @staticmethod
    def fw_upgrade(fw_path, firehose_path):
        """
        使用驱动内部自带的FW工具进行升级
        :param fw_path: FW.exe工具的路径
        :param firehose_path: 版本包的firehose目录层级的路径
        :return: None
        """
        upgrade_cmd = f"{fw_path} -f {firehose_path} -v 1".split(" ")
        all_logger.info(f"upgrade cmd: {upgrade_cmd}")
        with subprocess.Popen(
            upgrade_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,

        ) as process:
            try:
                out, _ = process.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                all_logger.info("FW工具升级超过600S，升级超时")
                process.kill()
                out, _ = process.communicate()

            out = out.decode('utf-8', 'ignore')
            all_logger.info(f"out: {out}")

            if "Upgrade module successfully" in out:
                return True
            else:
                raise FWError("FW工具升级异常，请检查Log的升级日志")

    def get_firehose_path(self):
        """
        获取版本包的firehose的文件夹的路径
        """
        for path, dirs, _ in os.walk(self.local_firmware_path):
            for d in dirs:
                if d == 'firehose' and 'efuse' not in path:  # 不使用efuse路径下的firehose
                    firehose_path = os.path.join(path, d)
                    return firehose_path
        raise FWError(f"{self.local_firmware_path}路径下未找到firehose文件夹")

    @staticmethod
    def safe_listdir(directory, timeout):
        pool = concurrent.futures.ThreadPoolExecutor()

        for i in range(3):
            future = pool.submit(os.listdir, directory)
            try:
                return future.result(timeout)
            except concurrent.futures.TimeoutError:
                time.sleep(10)
                continue
        else:
            raise FatalError(f"连续三次获取{directory}目录内容失败")

    def copy_and_unzip_firmware(self):
        """
        复制解压版本包。
        :return: None
        """
        all_logger.info("复制解压版本包")
        # 获取工厂包和标准包
        remote_files = self.safe_listdir(self.firmware_path, 3)  # 为了防止os.listdir()阻塞，使用concurrent
        all_logger.info(f"远程路径总文件列表：{remote_files}")
        factory_firmware = ''.join([i for i in remote_files if i.endswith('factory.zip')])
        standard_firmware = ''.join([i for i in remote_files if i.endswith('.zip') and not i.endswith('factory.zip') and len(i.strip(".zip")) > 10])  # zip结尾，并且不是factory.zip结尾，并且名字大于10位，例如RG500QEAAA是10位，大于10位
        all_logger.info(f"工厂包：{factory_firmware}")
        all_logger.info(f"标准包：{standard_firmware}")

        # 判断本地版本包是否存在
        local_path = os.path.join('C:\\', 'Users', getpass.getuser(), 'TWS_TEST_DATA', 'PackPath') if os.name == 'nt' else \
            os.path.join('/root', 'TWS_TEST_DATA', "PackPath")
        local_zip_firmware_path = os.path.join(local_path, factory_firmware if self.factory else standard_firmware)
        self.local_firmware_path = local_zip_firmware_path.strip(".zip")
        all_logger.info(f"版本包已存在: {local_zip_firmware_path}" if os.path.exists(local_zip_firmware_path) else "版本包不存在")
        all_logger.info(f"版本包已解压: {self.local_firmware_path}" if os.path.exists(self.local_firmware_path) else "版本包未解压")

        if not os.path.exists(local_zip_firmware_path):  # 下载版本包
            all_logger.info("开始下载工厂包" if self.factory else "开始下载标准包")
            remote_path = os.path.join(self.firmware_path, factory_firmware if self.factory else standard_firmware)
            if os.path.exists(local_path) is False:
                os.mkdir(local_path)
            all_logger.info(fr"shutil.copy({remote_path}, {local_path})")
            shutil.copy(remote_path, local_path)

        try:
            if not os.path.exists(self.local_firmware_path):  # 解压版本包
                all_logger.info("开始解压工厂包" if self.factory else "开始解压标准包")
                with zipfile.ZipFile(local_zip_firmware_path, 'r') as to_unzip:
                    to_unzip.extractall(self.local_firmware_path)
        except Exception as e:
            all_logger.info(e)
            os.popen('del /F /S /Q "{}"'.format(local_zip_firmware_path)).read()     # noqa # 如果解压失败首先删除压缩包
            all_logger.info('版本包解压失败')
            raise FWError('版本包解压失败')
        all_logger.info('解压固件成功')
        return True

    def disable_wu_service(self):
        """
        禁用QServiceRM520XXX
        """
        service_name = f"QService{self.ati[:8]}"  # 取前8个字符，驱动安装路径为C:\Windows\Firmware\Quectel\RM520NGL
        cmd = f"net stop {service_name}"
        output = subprocess.getoutput(cmd)
        all_logger.info(f"{cmd} output: {output}")
        if "没有启动" not in output and "已成功停止" not in output and 'is not started' in output:
            raise FWError(f"停止QService服务异常: {output}")

    def get_fw_path(self):
        # 根据版本号获取路径
        driver_path = self.ati[:8]  # 取前8个字符 Qservice 名称为QserviceRM520NGL
        firmware_path = r"C:\Windows\Firmware\Quectel"
        try:
            firmware_path_list = os.listdir(firmware_path)
        except FileNotFoundError:
            raise FWError(f"驱动路径{firmware_path}不存在，请确认是否安装笔电驱动，笔电驱动是否默认保存在此文件夹")

        if driver_path not in firmware_path_list:
            raise FWError(f"当前ATI: {self.ati}的前十位{driver_path}名称的文件夹不存在驱动路径{firmware_path}，请确认最新驱动创建文件夹规则")

        driver_full_path = os.path.join(firmware_path, driver_path)
        for path, _, files in os.walk(driver_full_path):
            for file in files:
                if file.endswith('.exe') and file.startswith('FWUpgrade'):
                    fw_path = os.path.join(path, file)
                    return fw_path
        raise FWError(f"{driver_full_path} 路径未找到FWUpgrade开头的exe升级工具")

    def check_module_version(self):
        """
        检查版本信息是否正确
        :return:
        """
        all_logger.info("检查升级后的版本信息")
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
            raise FWError("升级后版本号检查异常")

        # 仅查询CFUN
        self.at_handle.send_at('AT+CFUN?', 15)

        # 如果是升级的factory版本，恢复SN等相关信息
        if self.factory:
            self.restore_imei_sn_and_ect()

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
                # 判断是否一致，一致跳出
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

    def upgrade_sleep(self):
        """
        1. 检测当前环境是否安装驱动
            C:\\Windows\\Firmware\\Quectel\\RM520NGLAP\\Application\\FWUpgrade
        2. 禁用QServiceRM520NGLAP
        3. 下载版本包
        4. 升级
        5. 检测网卡驱动
        6. 检测MBIM拨号
        7. 使用QModeSwitch_RM520_V1.0.1.exe -p 0打开所有口
        8. 检测AT口，DM口
        9. 查询当前版本号
        """
        # 检测驱动是否安装并获取FW工具->禁用QServiceRM520XXX->下载解压版本包->获取版本包的firehose路径
        fw_path = self.get_fw_path()
        self.disable_wu_service()
        self.copy_and_unzip_firmware()
        firehose_path = self.get_firehose_path()

        # 升级
        self.fw_sleepupgrade(fw_path, firehose_path)

        # 检测网卡驱动加载(重新开机)—>检测MBIM功能加载正常
        self.check_network_card()
        self.check_mbim_loaded()

        # 打开所有端口->判断AT口DM口是否存在->检查版本号->结束
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.open_all_ports_and_check(q_mode_switch_path)
        self.check_module_version()

    def fw_sleepupgrade(self, fw_path, firehose_path):
        """
        使用驱动内部自带的FW工具进行升级
        :param fw_path: FW.exe工具的路径
        :param firehose_path: 版本包的firehose目录层级的路径
        :return: None
        """
        upgrade_cmd = f"{fw_path} -f {firehose_path} -v 1".split(" ")
        all_logger.info(f"upgrade cmd: {upgrade_cmd}")
        with subprocess.Popen(
            upgrade_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,

        ) as process:
            try:
                self.enter_sleep()
                out, _ = process.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                all_logger.info("FW工具升级超过600S，升级超时")
                process.kill()
                out, _ = process.communicate()

            out = out.decode('utf-8', 'ignore')
            all_logger.info(f"out: {out}")

            if "Upgrade module successfully" in out:
                return True
            else:
                raise FWError("FW工具升级异常，请检查Log的升级日志")

    def enter_sleep(self, c=1, d=30, p=30):
        """
        使支持S0i3的笔电进入S0i3睡眠
        pwrtest /cs [/c:n] [/d:n] [/p:n][/?]
        /c：n   指定默认运行周期 (1) 周期数。
        /d：n   指定连接待机 (之间的) 延迟时间（以秒 (60 秒为默认) 。
        /p：n   指定连接的待机退出时间 (秒;默认为 60 秒) 。
        """
        pwrtest_path = self.get_pwrtest_path().replace(" ", "' '").replace("(", "`(").replace(")", "`)")
        cmd = 'powershell "{} /cs /c:{} /d:{} /p:{}"'.format(pwrtest_path, c, d, p)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )
        return_value = proc.stdout.read().decode('GBK', "ignore")
        all_logger.info(return_value)
        if 'Connected Standby' not in return_value:
            raise FWError("PC进入modern standby失败！")
        time.sleep(3)

    def upgrade_dormancy(self):
        """
        1. 检测当前环境是否安装驱动
            C:\\Windows\\Firmware\\Quectel\\RM520NGLAP\\Application\\FWUpgrade
        2. 禁用QServiceRM520NGLAP
        3. 下载版本包
        4. 升级
        5. 检测网卡驱动
        6. 检测MBIM拨号
        7. 使用QModeSwitch_RM520_V1.0.1.exe -p 0打开所有口
        8. 检测AT口，DM口
        9. 查询当前版本号
        """
        # 检测驱动是否安装并获取FW工具->禁用QServiceRM520XXX->下载解压版本包->获取版本包的firehose路径
        fw_path = self.get_fw_path()
        self.disable_wu_service()
        self.copy_and_unzip_firmware()
        firehose_path = self.get_firehose_path()

        # 升级
        self.fw_dormancyupgrade(fw_path, firehose_path)

        # 检测网卡驱动加载(重新开机)—>检测MBIM功能加载正常
        self.check_network_card()
        self.check_mbim_loaded()

        # 打开所有端口->判断AT口DM口是否存在->检查版本号->结束
        q_mode_switch_path = self.get_q_mode_switch_path()
        self.open_all_ports_and_check(q_mode_switch_path)
        self.check_module_version()

    def fw_dormancyupgrade(self, fw_path, firehose_path):
        """
        使用驱动内部自带的FW工具进行升级
        :param fw_path: FW.exe工具的路径
        :param firehose_path: 版本包的firehose目录层级的路径
        :return: None
        """
        upgrade_cmd = f"{fw_path} -f {firehose_path} -v 1".split(" ")
        all_logger.info(f"upgrade cmd: {upgrade_cmd}")
        with subprocess.Popen(
            upgrade_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,

        ) as process:
            try:
                self.enter_dormancy()
                out, _ = process.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                all_logger.info("FW工具升级超过600S，升级超时")
                process.kill()
                out, _ = process.communicate()

            out = out.decode('utf-8', 'ignore')
            all_logger.info(f"out: {out}")

            if "Upgrade module successfully" in out:
                return True
            else:
                raise FWError("FW工具升级异常，请检查Log的升级日志")

    def enter_dormancy(self, c=1, d=30, p=30, s=4):
        """
        使电脑进入S3睡眠(台式机)，或者S4休眠一段时间
        pwrtest /sleep [/c:n] [/d:n] [/p:n] [/h:{y|n}] [/s:{1|3|4|all|rnd|hibernate|standby|dozes4}] [/unattend] [dt:n] [/e:n] [/?]
        /c：n
        指定要运行的默认) (1 的周期数。
        /d：n
        指定默认) (90 的延迟时间（以秒为单位）。
        /p：n
        以秒为单位指定睡眠时间 (60) 。 如果休眠时不支持唤醒计时器，系统将重新启动并在写入休眠文件) 后立即恢复。
        /s：{1|3|4|所有|rnd|休眠|备用|dozes4}
        1
        指定目标状态始终为 S1。
        3
        指定目标状态始终是 S3。
        4
        指定目标状态始终为 S4。
        all
        指定按顺序对所有支持的电源状态进行循环。
        rnd
        指定随机遍历所有支持的电源状态。
        r
        指定目标状态始终处于休眠状态 (S4) 。
        转入
        指定目标状态为) (S1 或 S3 可用的任何备用状态。
        dozes4
        指定从新式备用 (S0 低功耗空闲) doze 到 S4。
        （剩余其他参数暂不关注）
        """
        pwrtest_path = self.get_pwrtest_path().replace(" ", "' '").replace("(", "`(").replace(")", "`)")
        cmd = 'powershell "{} /sleep /c:{} /d:{} /p:{} /s:{}"'.format(pwrtest_path, c, d, p, s)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )
        return_value = proc.stdout.read().decode('GBK', "ignore")
        all_logger.info(return_value)
        if 'Complete' not in return_value:
            raise FWError("PC进入{}模式失败！".format(s))
        time.sleep(3)


if __name__ == '__main__':
    params = {
        "at_port": "COM6",
        "dm_port": "COM5",
        "firmware_path": r"\\192.168.11.252\quectel\Project\Module Project Files\5G Project\SDX6X\RM520NGLAP\Release\RM520NGLAPR01A04M4G_01.001.01.001_V01",  # noqa
        "factory": False,
        "ati": "RM520NGLAPR01A04M4G",
        "csub": "V01"
    }

    fw = FW(**params)
    fw.upgrade()
