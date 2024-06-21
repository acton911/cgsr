import threading
from utils.functions.windows_api import WindowsAPI
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import WindowsLowPowerError
from utils.pages.page_main import PageMain
import winreg
import subprocess
import time
from utils.pages.page_devices_manager import PageDevicesManager
import os
from utils.pages.page_mbim_sar import PageMbimSar
from pywinauto import mouse
import re
from pywinauto.keyboard import send_keys
import pyperclip
from utils.functions.fw import FW
## from tools.micropython.quts import QUTS


class WindowsLapTopMbimSarManager:
    def __init__(self, at_port, dm_port, mbim_pcie_driver_name, QuectelMbimSarTool_path, WinRT_LTETEST_path, nv_path, firmware_path):
        self.at_port = at_port
        self.nv_path = nv_path
        self.firmware_path = firmware_path
        self.mbim_pcie_driver_name = mbim_pcie_driver_name
        self.QuectelMbimSarTool_path = QuectelMbimSarTool_path
        self.dm_port = dm_port
        self.WinRT_LTETEST_path = WinRT_LTETEST_path
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.all_logger = all_logger
        self.page_main = PageMain()
        self.windows_api = WindowsAPI()
        self.page_devices_manager = PageDevicesManager()
        self.page_mbim_sar_manager = PageMbimSar()
        ## self.QUTS = QUTS()
        # self.application = Application()
        self.ati = self.get_ati()
        self.csub = self.get_csub()

    def enter_S3_S4_sleep(self, c=1, d=30, p=30, s=4):
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
            raise WindowsLowPowerError("PC进入{}模式失败！".format(s))
        time.sleep(3)

    def enter_modern_standby(self, c=1, d=30, p=30):
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
            raise WindowsLowPowerError("PC进入modern standby失败！")
        time.sleep(3)

    def get_pwrtest_path(self):
        """
        获取本机的pwrtest工具的路径，默认 C:\Program Files (x86)\Windows Kits\10\Tools\x64 下
        """
        check_path = r"C:\Program Files (x86)\Windows Kits\10\Tools\x64"
        for path, _, files in os.walk(check_path):  # pwrtest.exe
            for file in files:
                if file.endswith('.exe') and file.startswith("pwrtest"):
                    pwrtest_path = os.path.join(path, file)
                    return pwrtest_path
        raise WindowsLowPowerError(f"在{check_path}中未找到pwrtest.exe，请检查工具文件夹是否存在")

    def fw_erase(self):
        """
        fw全擦工厂
        :param param:
        :return:
        """
        fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                factory=True, ati=self.ati, csub=self.csub)
        fw.upgrade()

    def fw_normal(self):
        """
        fw升级标准
        :param param:
        :return:
        """
        fw = FW(at_port=self.at_port, dm_port=self.dm_port, firmware_path=self.firmware_path,
                factory=False, ati=self.ati, csub=self.csub)
        fw.upgrade()

    def get_csub(self):
        # SubEdition:\s(.*)
        vsub_value = self.at_handle.send_at('AT+CSUB')
        # SubEdition: (.*)\r
        # SubEdition:\s(.*)
        csub_regex = ''.join(re.findall(r'SubEdition: (.*)\r', vsub_value))
        if csub_regex:
            return csub_regex
        else:
            return False

    def init_nv(self):
        all_logger.info("点击GetSarDiagEnable按钮")
        self.page_mbim_sar_manager.element_GetSarDiagEnable_butoon.click()
        time.sleep(0.5)
        return_value4 = self.get_QuectelMbimSarTool_out()
        if "GetSarEnable SUCCESS" not in return_value4:
            raise WindowsLowPowerError(
                "初始化失败，点击GetSarDiagEnable后未返回GetSarEnable SUCCESS：\r\n{}".format(return_value4))

        all_logger.info("点击SetSarDiagEnable按钮")
        self.page_mbim_sar_manager.element_SetSarDiagEnable_butoon.click()
        time.sleep(0.5)
        return_value5 = self.get_QuectelMbimSarTool_out()
        if "SetSarEnable SUCCESS" not in return_value5:
            raise WindowsLowPowerError(
                "初始化失败，点击SetSarDiagEnable后未返回SetSarDiagEnable SUCCESS：\r\n{}".format(return_value5))

        all_logger.info("点击GetSarDiagEnable按钮")
        self.page_mbim_sar_manager.element_GetSarDiagEnable_butoon.click()
        time.sleep(0.5)
        return_value6 = self.get_QuectelMbimSarTool_out()
        if "GetSarEnable SUCCESS. (Enable)" not in return_value6:
            raise WindowsLowPowerError(
                "初始化失败，点击GetSarDiagEnable后未返回GetSarEnable SUCCESS. (Enable)：\r\n{}".format(return_value6))

    def init_mbim_sar(self):
        all_logger.info("点击Init按钮")
        self.page_mbim_sar_manager.element_Init_butoon.click()
        time.sleep(0.5)
        return_value1 = self.get_QuectelMbimSarTool_out()
        if "Init SUCCESS" not in return_value1:
            raise WindowsLowPowerError("初始化失败，点击Init后未返回Init SUCCESS：\r\n{}".format(return_value1))

        all_logger.info("点击OpenDeviceSerives按钮")
        self.page_mbim_sar_manager.element_OpenDeviceSerives_butoon.click()
        time.sleep(0.5)
        return_value2 = self.get_QuectelMbimSarTool_out()
        if "OpenDeviceServices SUCCESS" not in return_value2:
            raise WindowsLowPowerError(
                "初始化失败，点击OpenDeviceSerives后未返回OpenDeviceServices SUCCESS：\r\n{}".format(return_value2))

        all_logger.info("点击GetIsMbimReady按钮")
        self.page_mbim_sar_manager.element_GetIsMbimReady_butoon.click()
        time.sleep(0.5)
        return_value3 = self.get_QuectelMbimSarTool_out()
        if "GetIsMbimReady SUCCESS. (Ready)" not in return_value3:
            raise WindowsLowPowerError(
                "初始化失败，点击GetIsMbimReady后未返回GetIsMbimReady SUCCESS. (Ready)：\r\n{}".format(return_value3))

    def click_reboot(self):
        all_logger.info("点击SetDeviceReboot按钮")
        self.page_mbim_sar_manager.element_SetDeviceReboot_butoon.click()
        time.sleep(0.5)
        return_value8 = self.get_QuectelMbimSarTool_out()
        if "SetDeviceRoot SUCCESS" not in return_value8:
            raise WindowsLowPowerError(
                "初始化失败，点击SetDeviceReboot后未返回SetSmartSarValue NV_CONFIG1 SUCCESS：\r\n{}".format(return_value8))
        start_time = time.time()
        return_value_reboot = ''
        while time.time() - start_time < 60:
            time.sleep(1)
            return_value_reboot = self.get_QuectelMbimSarTool_out()
            if "MBIM device on" in return_value_reboot:
                all_logger.info("device已重启成功：{}".format(return_value_reboot))
                break
            else:
                continue
        else:
            raise WindowsLowPowerError("60s内device重启失败：{}".format(return_value_reboot))

    def check_mbim_network_card(self):
        """
        检查pcie mbim网卡是否正常加载
        :return: None
        """
        # "Quectel' 'UDE' 'Client"
        # 'Quectel RM520NGLAP'
        str_mbim = self.mbim_pcie_driver_name.replace(" ", "' '")
        cmd = 'powershell "Get-PnpDevice -FriendlyName "{}" -status "OK"'.format(str_mbim)
        all_logger.info(cmd)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

        proc.stdin.write(b"A\n")
        proc.stdin.flush()
        proc.stdin.close()

        while proc.returncode is None:
            proc.poll()
        check_result = proc.stdout.read().decode('GBK', "ignore")
        all_logger.info(check_result)
        if '找不到' in check_result:
            raise WindowsLowPowerError("找不到pcie_mbim网卡：{}， 或者网卡状态异常".format(self.mbim_pcie_driver_name))
        else:
            all_logger.info("pcie_mbim网卡加载正常")

    def check_mbn(self):
        # 查询MBN
        for i in range(10):
            return_value = self.at_handle.send_at('AT+QMBNCFG="LIST"', 30)
            if 'OK' in return_value and '+QMBNCFG:' in return_value:
                break
            else:
                all_logger.error("查询MBN列表异常")
                time.sleep(10)
        else:
            raise WindowsLowPowerError("升级后MBN列表查询异常")

    def check_efs_backup(self):
        # 备份指令
        for _ in range(10):
            return_value = self.at_handle.send_at('AT+QPRTPARA=1', 30)
            if 'OK' in return_value:
                break
            else:
                all_logger.error("AT+QPRTPARA=1执行异常")
        else:
            raise WindowsLowPowerError("执行备份指令异常")

        # 备份后查询
        for _ in range(10):
            return_value = self.at_handle.send_at('AT+QPRTPARA=4', 30)
            restore_times = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', return_value))
            if 'OK' in return_value and restore_times != '':
                break
            else:
                all_logger.error("AT+QPRTPARA=4执行异常")
        else:
            raise WindowsLowPowerError("执行备份指令后查询异常")

    def check_dump_mode_value(self):
        """
        检查默认值
        AT+QCFG="ModemRstLevel"
        AT+QCFG="ApRstLevel"
        """
        self.at_handle.send_at('AT+QCFG="ModemRstLevel",1', 0.3)
        self.at_handle.send_at('AT+QCFG="ApRstLevel",1', 0.3)
        modem_value = self.at_handle.send_at('AT+QCFG="ModemRstLevel"', 0.3)
        modem_value_key = re.findall(r'\+QCFG: "ModemRstLevel",(\d)', modem_value)[0]
        all_logger.info(modem_value_key)
        if modem_value_key == '1':
            all_logger.info('AT+QCFG="ModemRstLevel默认值正常：\r\n{}'.format(modem_value))
        else:
            raise WindowsLowPowerError('AT+QCFG="ModemRstLevel默认值异常！\r\n{}'.format(modem_value))
        ap_value = self.at_handle.send_at('AT+QCFG="ApRstLevel"', 0.3)
        ap_value_key = re.findall(r'\+QCFG: "ApRstLevel",(\d)', ap_value)[0]
        if ap_value_key == '1':
            all_logger.info('AT+QCFG="ModemRstLevel默认值正常：\r\n{}'.format(ap_value))
        else:
            raise WindowsLowPowerError('AT+QCFG="ModemRstLevel默认值异常！\r\n{}'.format(ap_value))

    def get_QuectelMbimSarTool_out(self):
        log_info = self.page_mbim_sar_manager.element_mbim_sar_outlog.get_value()
        all_logger.info("QuectelMbimSarTool当前log内容为:\r\n****************************************\r\n{}\r\n****************************************".format(log_info))
        return log_info

    def get_value_by_crtl_c(self):
        # 全选（ctrl+A）
        send_keys("^a")
        # 复制(ctrl+C)
        send_keys("^c")
        text = pyperclip.paste()
        all_logger.info("获取剪切板内容：\r\n" + text)
        return text

    def get_ati(self):
        ati = self.at_handle.send_at('ATI')
        ati_regex = ''.join(re.findall(r'Revision: (\w+)', ati))
        if ati_regex:
            return ati_regex
        else:
            return False

    def get_gmi(self):
        gmi = self.at_handle.send_at('AT+GMI')
        gmi_regex = ''.join(re.findall(r'GMI\W+(\w+)', gmi))
        if gmi_regex:
            return gmi_regex
        else:
            return False

    def get_operator(self):
        plmn_mapping = {  # PLMN和运营商名称的映射关系
            '46000': 'CHINA MOBILE',
            '46002': 'CHINA MOBILE',
            '46004': 'CHINA MOBILE',
            '46007': 'CHINA MOBILE',
            '46008': 'CHINA MOBILE',
            '46001': 'CHN-UNICOM',
            '46006': 'CHN-UNICOM',
            '46009': 'CHN-UNICOM',
            '46003': 'CHN-CT',
            '46005': 'CHN-CT',
            '46011': 'CHN-CT',
        }
        cimi = self.at_handle.send_at('AT+CIMI')
        cimi_regex = ''.join(re.findall(r'\d+', cimi))
        if cimi_regex:
            all_logger.info(f"{cimi_regex[:5]},{plmn_mapping[cimi_regex[:5]]}")
            return cimi_regex[:5], plmn_mapping[cimi_regex[:5]]
        else:
            return False

    def mbim_connect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

        profile_name = ''.join(re.findall(r'---\s+(.*)', data2))

        for i in range(10):
            time.sleep(5)
            os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
            all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
            time.sleep(5)

            data3 = os.popen('netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name)).read()
            all_logger.info('netsh mbn connect interface="{}" connmode=name name="{}"'.format(interface_name, profile_name))
            time.sleep(5)
            if '失败' not in data3:
                break
        else:
            raise WindowsLowPowerError("连接拨号失败！\r\n{}".format(data3))
        time.sleep(10)

    def mbim_disconnect(self):
        """
        通过接口指令连接MBIM拨号
        """
        global data3
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        time.sleep(5)
        os.popen('netsh mbn disconnect interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn disconnect interface="{}"'.format(interface_name))
        time.sleep(10)

    def check_mbim_connect_disconnect(self, connect=True):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        data1 = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r'\s+名称\s+:\s(.*)', data1))

        data2 = os.popen('netsh mbn show profiles interface="{}"'.format(interface_name)).read()
        all_logger.info('netsh mbn show profiles interface="{}"'.format(interface_name))

        profile_name = ''.join(re.findall(r'---\s+(.*)', data2))

        # netsh mbn show profilestate interface="手机网络" name="EFAE6521-9049-451C-84A0-72CDE3D6372D"
        data3 = os.popen('netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name)).read()
        all_logger.info('netsh mbn show profilestate interface="{}" name="{}"'.format(interface_name, profile_name))
        if not connect and '已连接' in data3:
            raise WindowsLowPowerError("异常！当前没有断开连接！\r\n{}".format(data3))
        elif connect and '断开连接' in data3:
            raise WindowsLowPowerError("异常！当前没有连接！\r\n{}".format(data3))

    def mbim_connect_and_check(self):
        """
        mbim连接，检查是否正常
        :return: None
        """
        self.mbim_connect()
        self.check_mbim_connect_disconnect()
        self.windows_api.ping_get_connect_status()
        time.sleep(5)

    def mbim_disconnect_and_check(self):
        """
        mbim断开连接，检查是否正常
        :return: None
        """
        self.mbim_disconnect()
        self.check_mbim_connect_disconnect(False)
        time.sleep(5)

    def process_input(self, target_process):
        print(666)
        target_process.stdin.write(b'q\r\n')
        target_process.stdin.close()
        print(999)

    def open_WinRT_LTETEST_startmon(self, Istransmitting=False):
        all_logger.info('打开QuectelMbimSarTool工具')
        os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
        fw_path = ''
        for path, _, files in os.walk(self.WinRT_LTETEST_path):
            for file in files:
                if file.startswith("WinRT_LTETEST") and file.upper().endswith(".EXE"):
                    # print(file)
                    fw_path = os.path.join(path, file)
        if not fw_path:
            raise Exception("WinRT_LTETEST工具路径异常")
        self.WinRT_LTETEST_path = os.path.dirname(fw_path)  # 为了防止填写的路径有问题，获取.exe文件的路径
        fw_path = fw_path + ' ' + "StartMon"
        # self.mbim_connect_and_check()
        all_logger.info(f'开始执行：{fw_path}')
        get_result = ''
        process = subprocess.Popen(fw_path,
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
        t = threading.Timer(60, self.process_input, args=(process,))
        t.setDaemon(True)
        t.start()
        while process.poll() is None:
            value = process.stdout.readline().decode()
            if value:
                print(value)
                get_result += value
        print(get_result)
        if not Istransmitting and 'is not transmitting' in get_result:
             all_logger.info("WinRT_LTETEST工具已经检测到数据不流通:\r\n{}".format(get_result))
        elif Istransmitting and 'is transmitting' in get_result:
            all_logger.info("WinRT_LTETEST工具已经检测到数据流通:\r\n{}".format(get_result))
        else:
            raise WindowsLowPowerError("数据流通检测异常:\r\n{}".format(get_result))

    def open_WinRT_LTETEST(self, check_mode=''):
        """
        使用WinRT_LTETEST工具
        """
        all_logger.info('打开WinRT_LTETEST工具')
        os.popen('taskkill /f /t /im "WinRT_LTETEST*"').read()
        fw_path = ''
        for path, _, files in os.walk(self.WinRT_LTETEST_path):
            for file in files:
                if file.startswith("WinRT_LTETEST") and file.upper().endswith(".EXE"):
                    # print(file)
                    fw_path = os.path.join(path, file)
        if not fw_path:
            raise Exception("WinRT_LTETEST工具路径异常")
        self.WinRT_LTETEST_path = os.path.dirname(fw_path)  # 为了防止填写的路径有问题，获取.exe文件的路径
        fw_path = fw_path + ' ' + check_mode
        all_logger.info(f'开始执行：{fw_path}')
        return_value = os.popen(fw_path).read()
        all_logger.info("WinRT_LTETEST返回值：\r\n******************************\r\n{}******************************".format(return_value))
        return return_value

    def close_QuectelMbimSarTool(self):
        """
        关闭FW QuectelMbimSarTool工具
        :return: None
        """
        all_logger.info('关闭QuectelMbimSarTool工具')
        os.popen('taskkill /f /t /im "QuectelMbimSarTool*"').read()

    def write_mbim_sar_tool_config(self, nv_path="", nv_config1_name="rtsar_config.config", nv_config2_name="", nv_4g_name="", nv_5g_name=""):
        """
        直接在config文件中填写路径，打开后不用再去选择
        :return: None
        """
        if not nv_config1_name and not nv_config2_name and not nv_4g_name and not nv_5g_name:
            raise WindowsLowPowerError("请填写需要添加的nv名称！")
        all_logger.info("开始配置mbim_sar工具nv文件路径")
        mbim_sar_config_path = os.path.join(self.QuectelMbimSarTool_path, "config.ini")
        all_logger.info(mbim_sar_config_path)
        nv_config1_path = ''
        nv_config2_path = ''
        nv_4g_path = ''
        nv_5g_path = ''
        for path, _, files in os.walk(nv_path):
            for file in files:
                if file == nv_config1_name:
                    nv_config1_path = os.path.join(path, file)
                elif file == nv_config2_name:
                    nv_config2_path = os.path.join(path, file)
                elif file == nv_4g_name:
                    nv_4g_path = os.path.join(path, file)
                elif file == nv_5g_name:
                    nv_5g_path = os.path.join(path, file)

        if nv_config1_name and nv_config1_path:
            all_logger.info(f"nv文件已找到:\r\nnv_config1_path:{nv_config1_path}")
        elif nv_config1_name and not nv_config1_path:
            raise WindowsLowPowerError(f"未找到nv文件,请检查nv文件路径是否正确:\r\nnv_path:{nv_path}\r\nnv_config1_path:{nv_config1_path}")

        if nv_config2_name and nv_config2_path:
            all_logger.info(f"nv文件已找到:\r\nnv_config1_path:{nv_config2_path}")
        elif nv_config2_name and not nv_config2_path:
            raise WindowsLowPowerError(
                f"未找到nv文件,请检查nv文件路径是否正确:\r\nnv_path:{nv_path}\r\nnv_config1_path:{nv_config2_path}")

        if nv_4g_name and nv_4g_path:
            all_logger.info(f"nv文件已找到:\r\nnv_config1_path:{nv_4g_path}")
        elif nv_4g_name and not nv_4g_path:
            raise WindowsLowPowerError(f"未找到nv文件,请检查nv文件路径是否正确:\r\nnv_path:{nv_path}\r\nnv_config1_path:{nv_4g_path}")

        if nv_5g_name and nv_5g_path:
            all_logger.info(f"nv文件已找到:\r\nnv_config1_path:{nv_5g_path}")
        elif nv_5g_name and not nv_5g_path:
            raise WindowsLowPowerError(f"未找到nv文件,请检查nv文件路径是否正确:\r\nnv_path:{nv_path}\r\nnv_config1_path:{nv_5g_path}")

        with open(mbim_sar_config_path, "w", encoding="utf-8") as f:
            """
            nv路径写入配置文件，若没有配置文件则新建配置文件，有则覆盖原内容。
            写入如下格式内容：
            [FILE]
            NV_CONFIG1=D:\Auto\Tools\SDX62_SAR\RM520NGL_SAR_RFNV\00029619
            NV_CONFIG2=D:\Auto\Tools\SDX62_SAR\RM520NGL_SAR_RFNV\00029619
            NV_4G=D:\Auto\Tools\SDX62_SAR\RM520NGL_SAR_RFNV\00029619
            NV_5G=D:\Auto\Tools\SDX62_SAR\RM520NGL_SAR_RFNV\00029619
            """
            f.write('[FILE]\r\nNV_CONFIG1={}\r\nNV_CONFIG2={}\r\nNV_4G={}\r\nNV_5G={}\r\n'.format(nv_config1_path, nv_config2_path, nv_4g_path, nv_5g_path))
        all_logger.info("已将nv文件路径写入mbim_sar配置文件")

    def open_QuectelMbimSarTool(self, nv_path="", nv_config1_name="", nv_config2_name="", nv_4g_name="", nv_5g_name="",):
        """
        rtsar_config.config\00029619\00030007
        打开FW QuectelMbimSarTool工具
        :return: None
        """
        self.write_mbim_sar_tool_config(nv_path=nv_path, nv_config1_name=nv_config1_name, nv_config2_name=nv_config2_name, nv_4g_name=nv_4g_name, nv_5g_name=nv_5g_name)
        all_logger.info('打开QuectelMbimSarTool工具')
        os.popen('taskkill /f /t /im "QuectelMbimSarTool*"').read()
        mbim_sar_path = ''
        # print(self.QuectelMbimSarTool_path)
        for path, _, files in os.walk(self.QuectelMbimSarTool_path):
            for file in files:
                # print(file)
                if file.startswith("QuectelMbimSarTool") and file.upper().endswith(".EXE"):
                    mbim_sar_path = os.path.join(path, file)
        if not mbim_sar_path:
            raise Exception("QuectelMbimSarTool工具路径异常")
        self.QuectelMbimSarTool_path = os.path.dirname(mbim_sar_path)  # 为了防止填写的路径有问题，获取.exe文件的路径
        subprocess.Popen(mbim_sar_path, shell=True, cwd=self.QuectelMbimSarTool_path)
        all_logger.info("wait 5 seconds")
        time.sleep(5)

    def list_nv(self):
        """
        使用QRCT读取NV
        """
        mouse.click(coords=(150, 110))
        time.sleep(1)
        mouse.click(coords=(115, 305))
        time.sleep(1)
        mouse.click(coords=(160, 140))
        time.sleep(1)
        mouse.click(coords=(160, 160))
        time.sleep(1)
        mouse.click(coords=(10, 580))
        time.sleep(1)
        mouse.click(coords=(70, 618))
        time.sleep(1)
        mouse.click(coords=(190, 635))
        time.sleep(1)
        mouse.click(coords=(315, 655))
        time.sleep(1)
        mouse.click(coords=(5, 625))
        time.sleep(600)

    def read_nv_29619(self):
        """
        使用QRCT读取NV
        """
        mouse.click(coords=(25, 675))
        time.sleep(1)
        mouse.double_click(coords=(115, 715))
        time.sleep(1)

    def read_nv_30007(self):
        """
        使用QRCT读取NV
        """
        mouse.double_click(coords=(115, 888))
        time.sleep(1)

    def chose_md_port(self):
        """
        为QRCT选择DM口
        """
        # self.QUTS._create_nv_service()
        time.sleep(5)
        mouse.click(coords=(115, 40))
        time.sleep(1)
        mouse.click(coords=(115, 60))
        time.sleep(1)
        mouse.click(coords=(360, 40))
        time.sleep(1)
        mouse.click(coords=(360, 110))
        time.sleep(1)
        mouse.click(coords=(560, 40))
        time.sleep(3)
        mouse.click(coords=(560, 60))
        time.sleep(1)
        mouse.click(coords=(730, 40))
        time.sleep(3)

    def open_QRCT(self):
        """
        打开QRCT工具
        # "C:\Program Files (x86)\Qualcomm\QDART\QRCT4\QRCT.exe"
        :return: None
        """
        QRCT_path = r"C:\Program Files (x86)\Qualcomm\QDART\QRCT4"
        all_logger.info('打开QRCT工具')
        os.popen('taskkill /f /t /im "QRCT*"').read()
        qrct_path = ''
        # print(QRCT_path)
        for path, _, files in os.walk(QRCT_path):
            for file in files:
                # print(file)
                if file.startswith("QRCT") and file.upper().endswith(".EXE"):
                    qrct_path = os.path.join(path, file)
        if not qrct_path:
            raise Exception("QRCT工具路径异常")
        QRCT_path = os.path.dirname(qrct_path)  # 为了防止填写的路径有问题，获取.exe文件的路径
        # app = self.application.start(r"C:\Program Files (x86)\Qualcomm\QDART\QRCT4\QRCT.exe -a -n -y --arguments")
        time.sleep(5)
        # dlg = app['Qualcomm Radio Control Tool']
        # dlg.maximize()
        # subprocess.Popen(qrct_path, shell=True, cwd=QRCT_path)
        all_logger.info("wait 10 seconds")
        time.sleep(10)

    def check_mbim_connect(self, auto_connect=False):
        """
        检查mbim是否是连接状态。
        :return: None
        """
        num = 0
        timeout = 30
        connect_info = None
        already_connect_info = None
        while num <= timeout:
            connect_info = self.page_main.element_mbim_disconnect_button.exists()
            already_connect_info = self.page_main.element_mbim_already_connect_text.exists()
            if auto_connect is False:
                if connect_info and already_connect_info:
                    return True
            else:
                if already_connect_info:
                    return True
            num += 1
            time.sleep(1)
        info = '未检测到断开连接按钮，' if not connect_info and not auto_connect else '' + '未检测到已经连接信息' if not already_connect_info else ""
        raise WindowsLowPowerError(info)

    def disable_auto_connect_find_connect_button(self):
        """
        windows BUG：如果取消自动连接，模块开机后立刻点击状态栏网络图标，有可能没有连接按钮出现
        :return:
        """
        for _ in range(30):
            self.page_main.click_network_icon()
            time.sleep(1)
            self.page_main.click_network_details()
            status = self.page_main.element_mbim_connect_button.exists()
            if status:
                return True
            self.windows_api.press_esc()
        else:
            raise WindowsLowPowerError("未发现连接按钮")

    def dial(self):
        """
        模拟点击网络图标连接拨号
        :return:
        """
        self.disable_auto_connect_and_disconnect()
        self.disable_auto_connect_find_connect_button()
        self.page_main.click_connect_button()
        self.check_mbim_connect()

    def enable_disable_pcie_ports(self, flag, pcie_ports):
        for i in pcie_ports:
            if flag:
                all_logger.info("开始禁用{}".format(i))
                self.enable_disable_device(True, i)
            else:
                all_logger.info("开始启用{}".format(i))
                self.enable_disable_device(False, i)

    def disable_auto_connect_and_disconnect(self):
        """
        取消自动连接，并且点击断开连接，用于条件重置
        :return: None
        """
        self.page_main.click_network_icon()
        self.page_main.click_network_details()
        disconnect_button = self.page_main.element_mbim_disconnect_button
        if disconnect_button.exists():
            disconnect_button.click()
        self.page_main.click_disable_auto_connect()
        self.windows_api.press_esc()

    def set_qsclk(self, mode=1):
        """
        :param mode:0: 设置开启不保存；1: 设置开启保存
        :return:
        """
        for i in range(3):
            self.at_handle.send_at('AT+QSCLK=1,{}'.format(1 if mode == 1 else 0))
            qsc_val = self.at_handle.send_at('AT+QSCLK?')
            if '+QSCLK: 1,{}'.format(1 if mode == 1 else 0) in qsc_val:
                return True
            time.sleep(1)
        else:
            raise WindowsLowPowerError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

    def close_lowpower(self):
        """
        指令退出慢时钟
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=0,0')
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('退出慢时钟失败')

    def open_lowpower(self):
        """
        指令开启慢时钟
        :return:
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=1')
            if 'OK' in val:
                return True
        else:
            raise WindowsLowPowerError('开启慢时钟失败')

    def disable_low_power_registry(self):
        """
        修改注册表，使模块退出慢时钟
        :return:
        """
        reg_root = winreg.HKEY_LOCAL_MACHINE
        reg_path = r'SYSTEM\CurrentControlSet\Services\qcusbser'
        key = winreg.OpenKey(reg_root, reg_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            key_value = winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled")
            winreg.QueryValueEx(key, "QCDriverSelectiveSuspendIdleTime")
            if 0 in key_value:
                self.cfun_reset()
                all_logger.info('已去激活注册表')
                return True
        except FileNotFoundError:  # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 0)
        time.sleep(1)
        if 0 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('去激活注册表失败')
            raise WindowsLowPowerError('去激活注册表失败')
        else:
            self.cfun_reset()
            all_logger.info('已去激活注册表')

    def check_qsclk(self, mode=1, is_save=True):
        """
        默认查询+QSCLK: 1,1返回值
        :param mode: 0:查询AT+AT+QSCLK=?返回值；1: 查询AT+QSCLK?返回值
        :param is_save: Ture:设置AT+QSCLK=1,1后查询；False:设置AT+QSCLK=1,0后查询
        :return:
        """
        if mode == 0:
            for i in range(3):
                qsclk_val = self.at_handle.send_at('AT+QSCLK=?')
                if '+QSCLK: (0,1),(0,1)' in qsclk_val:
                    return True
                time.sleep(1)
            else:
                raise WindowsLowPowerError('AT+QSCLK=?返回值格式不正确')
        elif mode == 1:
            for i in range(3):
                qsclk_val = self.at_handle.send_at('AT+QSCLK?')
                if is_save:
                    if '+QSCLK: 1,1' in qsclk_val:
                        return True
                else:
                    if '+QSCLK: 0,0' in qsclk_val:
                        return True
                time.sleep(1)
            else:
                raise WindowsLowPowerError('AT+QSCLK?返回值格式不正确')

    def cfun_reset(self):
        """
        CFUN11重启模块
        :return:
        """
        self.at_handle.send_at('AT+CFUN=1,1', 10)
        self.driver_check.check_usb_driver()
        all_logger.info('打开设备管理器')
        self.page_devices_manager.open_devices_manager()
        all_logger.info('刷新设备管理器')
        self.page_devices_manager.element_scan_devices_icon().click()
        time.sleep(60)
        # self.at_handle.readline_keyword('PB DONE', timout=80)

    @staticmethod
    def enable_low_power_registry():
        """
        修改注册表值，使模块进入慢时钟
        :return:
        """
        reg_root = winreg.HKEY_LOCAL_MACHINE
        reg_path = r'SYSTEM\CurrentControlSet\Services\qcusbser'
        key = winreg.OpenKey(reg_root, reg_path, 0, winreg.KEY_ALL_ACCESS)
        try:
            key_value = winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled")
            winreg.QueryValueEx(key, "QCDriverSelectiveSuspendIdleTime")
            if 1 in key_value:
                all_logger.info('已激活注册表')
                return True
        except FileNotFoundError:   # 如果不存在这个值的话直接设置添加
            winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "QCDriverSelectiveSuspendIdleTime", 0, winreg.REG_DWORD, 2147483651)
        winreg.SetValueEx(key, "QCDriverPowerManagementEnabled", 0, winreg.REG_DWORD, 1)
        time.sleep(1)
        if 1 not in winreg.QueryValueEx(key, "QCDriverPowerManagementEnabled"):
            all_logger.info('激活注册表失败')
            raise WindowsLowPowerError('激活注册表失败')
        else:
            all_logger.info('已激活注册表')

    @staticmethod
    def enable_disable_device(flag, device_name):
        """
        禁用或者启用驱动。
        :param device_name: 设备管理器中设备或驱动名称
        :param flag: True:禁用驱动，False：启用驱动。
        :return: None
        """
        all_logger.info('{}驱动{}'.format("禁用" if flag else "启用", device_name))
        cmd = 'powershell "Get-PnpDevice -FriendlyName "{}" -status "OK" | disable-pnpdevice -Confirm:$True"'.format(
            device_name) if flag else \
            'powershell "Get-PnpDevice -FriendlyName "{}" -status "Error" | enable-pnpdevice -Confirm:$Ture"'.format(
                device_name)
        all_logger.info(cmd)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True
        )

        proc.stdin.write(b"A\n")
        proc.stdin.flush()
        proc.stdin.close()

        while proc.returncode is None:
            proc.poll()

        all_logger.info(proc.stdout.read().decode('GBK', "ignore"))

        time.sleep(3)


    @staticmethod
    def readline(port):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值:
        如果有值，读取直到\n；
        如果有值，超过1S，直接返回；
        如果没有值，返回 ''
        :param port: 已经打开的端口
        :return: buf:端口读取到的值；没有值返回 ''
        """
        buf = ''
        try:
            if port.in_waiting > 0:
                start_time = time.time()
                while True:
                    buf += port.read(1).decode('utf-8', 'replace')
                    if buf.endswith('\n'):
                        at_logger.debug("{} {}".format("RECV", repr(buf).replace("'", '')))
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > 1:
                        at_logger.info('{}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            at_logger.error('Fatal ERROR: {}'.format(error))
        finally:
            return buf
