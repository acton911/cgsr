import datetime
import re
import time
import serial
import subprocess
import os
from functools import partial
import serial.threaded
from collections import deque
from utils.logger.logging_handles import at_logger

if os.name == 'nt':
    from utils.functions.windows_api import WindowsAPI
    from utils.functions.setupapi import get_network_card_names
from utils.functions.decorators import watchdog
from utils.exception.exceptions import ATError
from threading import Thread
import random
import glob
import serial.tools.list_ports

watchdog = partial(watchdog, logging_handle=at_logger, exception_type=ATError)


class TestLines(serial.threaded.LineReader):
    def __init__(self):
        super(TestLines, self).__init__()
        self.received_lines = deque()

    def handle_line(self, data):
        self.received_lines.append(data)

    def readline(self):
        if self.received_lines:
            return self.received_lines.popleft()
        else:
            return ''


class ATHandle:
    def __init__(self, at_port):
        self._at_port = at_port
        # self._at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)

    def __enter__(self):
        try:
            self._at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
        except ValueError:
            pass
        finally:
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._at_port.close()

    @staticmethod
    def readline(port):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值：
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

    def get_port_list(self):
        """
        获取当前电脑设备管理器中所有的COM口的列表
        :return: COM口列表，例如['COM3', 'COM4']
        """
        if os.name == 'nt':
            try:
                at_logger.debug('get_port_list')
                port_name_list = []
                ports = serial.tools.list_ports.comports()
                for port, _, _ in sorted(ports):
                    port_name_list.append(port)
                at_logger.debug(port_name_list)
                return port_name_list
            except TypeError:  # Linux偶现
                return self.get_port_list()
        else:
            return glob.glob('/dev/ttyUSB*')

    def send_at(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        # 判断是否有异常重启
        self.check_if_at_port_exist()

        # 开始发送AT
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
                at_start_timestamp = time.time()
                __at_port.write('{}\r\n'.format(at_command).encode('utf-8'))
                at_logger.info('Send: {}'.format(at_command))
                return_value_cache = ''
                while True:
                    # AT端口值获取
                    time.sleep(0.001)  # 减小CPU开销
                    return_value = self.readline(__at_port)
                    if return_value != '':
                        return_value_cache += '{}'.format(return_value)
                        if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                            return return_value_cache
                        if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                            at_logger.error('{}指令返回ERROR'.format(at_command))
                            return return_value_cache
                    # 超时等判断
                    current_total_time = time.time() - at_start_timestamp
                    out_time = time.time()
                    if current_total_time > timeout:
                        if return_value_cache and at_command in return_value_cache:
                            at_logger.error('{}命令执行超时({}S)'.format(at_command, timeout))
                            while True:
                                time.sleep(0.001)  # 减小CPU开销
                                return_value = self.readline(__at_port)
                                if return_value != '':
                                    return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                                if time.time() - out_time > 3:
                                    return return_value_cache
                        elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                            at_logger.error('{}命令执行返回格式错误，未返回AT指令本身'.format(at_command))
                            return return_value_cache
                        else:
                            at_logger.error(
                                '{}命令执行{}S内无任何回显\n当前端口列表: {}'.format(at_command, timeout, self.get_port_list()))
                            time.sleep(0.5)
                            break
            else:
                at_logger.info("close at port")
                __at_port.close()
                at_logger.info("close at port success")
                at_logger.error('连续10次执行{}命令无任何回显，AT不通，保存现场，请在“5G-自动化用例改造群”反馈问题'.format(at_command))
                # DEBUG内容，保存AT不通现场。
                while True:
                    time.sleep(1)

    def check_if_at_port_exist(self):
        port_list = self.get_port_list()
        if self._at_port not in port_list:
            at_logger.error("ATHandle.send_at发送AT前端口不存在，可能存在异常重启现象")
        else:
            return True  # 正常情况跳出

        # 在1S内如果AT口正常，依然退出(避免AT口检测函数的异常)
        for i in range(10):
            time.sleep(0.1)
            port_list = self.get_port_list()
            if self._at_port in port_list:
                return True

        at_logger.error("等待180秒后再次检查")
        time.sleep(180)

        port_list = self.get_port_list()
        if self._at_port in port_list:
            at_logger.error("模块可能存在异常重启现象，保存现场，请在“5G-自动化用例改造群”反馈问题")
            # DEBUG内容，保存发送AT突然掉口的情况
            while True:
                time.sleep(1)

    def send_at_pcie(self, at_command, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            with serial.threaded.ReaderThread(__at_port, TestLines) as protocol:
                for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
                    at_start_timestamp = time.time()
                    protocol.write_line('{}\r\n'.format(at_command))
                    at_logger.info('Send: {}'.format(at_command))
                    return_value_cache = ''
                    while True:
                        # AT端口值获取
                        time.sleep(0.001)  # 减小CPU开销
                        return_value = protocol.readline()
                        if return_value != '':
                            return_value_cache += '{}\r\n'.format(return_value)
                            print(return_value_cache)
                            if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                                return return_value_cache
                            if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                                at_logger.error('{}指令返回ERROR'.format(at_command))
                                return return_value_cache
                        # 超时等判断
                        current_total_time = time.time() - at_start_timestamp
                        out_time = time.time()
                        if current_total_time > timeout:
                            if return_value_cache and at_command in return_value_cache:
                                at_logger.error('{}命令执行超时({}S)'.format(at_command, timeout))
                                while True:
                                    time.sleep(0.001)  # 减小CPU开销
                                    return_value = protocol.readline()
                                    if return_value != '':
                                        return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                                    if time.time() - out_time > 3:
                                        return return_value_cache
                            elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                                at_logger.error('{}命令执行返回格式错误，未返回AT指令本身'.format(at_command))
                                return return_value_cache
                            else:
                                at_logger.error(
                                    '{}命令执行{}S内无任何回显\n当前端口列表: {}'.format(at_command, timeout, self.get_port_list()))
                                time.sleep(0.5)
                                break
                else:
                    at_logger.error('连续10次执行{}命令无任何回显，AT不通'.format(at_command))

    def check_urc(self):
        """
        用于开机检测端口是否有任何内容上报，如果读取到任何内容，则停止。
        :return: True：有URC
        """
        at_logger.info("检测端口是否可以正常打开")
        cnt = 10
        while cnt != 0:
            cnt = cnt - 1
            try:
                with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
                    at_logger.info("AT口打开正常")
                    break
            except (serial.serialutil.SerialException, OSError) as e:
                at_logger.error(e)
                at_logger.info("打开AT口失败，尝试重新打开AT口")
                time.sleep(3)
        else:
            raise ATError("连续10次打开AT口失败")

        at_logger.info("检测URC上报")
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            check_urc_start_timestamp = time.time()
            while True:
                time.sleep(0.001)  # 减小CPU开销
                if time.time() - check_urc_start_timestamp > 60:  # 暂定60S没有URC上报则异常
                    raise ATError("60S内未检查到URC上报")
                else:  # 检查URC
                    at_port_data = self.readline(__at_port)
                    if at_port_data != '':
                        time.sleep(1)  #  等待1s，尝试避免Device or resource busy
                        return True

    def at_handle_test(self):
        """
        测试方式，不关注
        :return:None
        """
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            __at_port.write("AT\r\n".encode('utf-8'))
            time.sleep(0.1)
            print(__at_port.read(size=1024))

    def send_at_without_check(self, at_command):
        """
        only send. eg: AT+QFASTBOOT
        :return:None
        """
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            at_logger.info("{}\r\n".format(at_command).encode('utf-8'))
            __at_port.write("{}\r\n".format(at_command).encode('utf-8'))
            time.sleep(0.1)
            try:
                at_logger.info(__at_port.read(size=1024))
            except serial.serialutil.SerialException:
                at_logger.info("send_at_without_check read nothing after send {}.".format(at_command))

    def check_network(self):
        """
        检查模块驻网。
        :return: False: 模块没有注上网。cops_value:模块注册的网络类型，
        """
        at_logger.info("检查网络")
        check_network_start_time = time.time()
        timeout = 300
        while True:
            return_value = self.send_at('AT+COPS?')
            cell_value = self.send_at('AT+QENG="servingcell"')
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', return_value))
            if cops_value != '':
                at_logger.info("当前网络：{}".format(cops_value))
                at_logger.info("当前小区信息：{}".format(cell_value))
                time.sleep(1)
                return cops_value
            if time.time() - check_network_start_time > timeout:
                at_logger.error("{}内找网失败".format(timeout))
                at_logger.info("当前小区信息：{}".format(cell_value))
                return False
            time.sleep(1)

    @watchdog("发送AT获取模块数据并和剪切板比较")
    def get_and_compare_module_data(self):
        # TODO: 网络详情列表网络类型和数据类类型检查新增
        # 查询当前网卡
        self.send_at('AT+QCFG="USBNET"')
        # 获取version
        version_data = self.send_at("ATI")
        model = ''.join(re.findall(r'\s(.*?)\s+Revision', version_data))
        revision_data = ''.join(re.findall(r'Revision: (.*?)\s', version_data))
        # 获取imei
        imei_data = self.send_at("AT+EGMR=0,7")
        imei = ''.join(re.findall(r'\+EGMR: "(\d+)"', imei_data))
        # 获取imsi
        cimi_data = self.send_at("AT+CIMI")
        imsi = ''.join(re.findall(r'AT\+CIMI\s+(\d+)\s+OK\s+', cimi_data))
        # ICCID
        iccid_data = self.send_at("AT+QCCID")
        iccid = ''.join(re.findall(r"\+QCCID:\s(\d+\S+)", iccid_data))
        # 本机号码
        cnum_data = self.send_at("AT+CNUM")
        number = ''.join(re.findall(r'CNUM: ,"(.*?)"', cnum_data))
        # 参数拼接
        module_data = {
            "model": model,
            "version": revision_data,
            "imei": imei,
            "imsi": imsi,
            "iccid": iccid,
            "phone_number": number
        }
        at_logger.info(module_data)

        # 是否是CI构建的版本
        is_ci = ''.join(
            re.findall(r'\d{8}', revision_data))  # CI判断标准，有日期，例如：RG500QEAAAR11A06M4G_BETA22011002_01.001.01.001_V01

        clipboard_data = WindowsAPI().get_clipboard_data()
        for field, field_data in module_data.items():
            print(field, field_data)
            if field == 'version' and is_ci:  # 针对CI的修改，如果版本号名称很长有截断，只判断部分版本号
                if field_data.split('_')[0] in clipboard_data:
                    continue
            if field_data not in clipboard_data:
                at_logger.error("模块端获取的{}与PC端获取的信息{}不一致".format(field, clipboard_data))
                return False

        return True

    def get_operator(self) -> str:
        """
        因为TWS分发CASE会根据不同的运营商分发，在TWS Constant Configuration里面配置参数无效。
        所以根据AT+CIMI指令的返回的IMSI的前五位(PLMN)进行当前运营商的获取。
        :return: 当前运行商的名称，取值["CMCC"、"中国联通"、"中国电信"]
        """
        _operator_plmn_mapping = {  # PLMN和运营商名称的映射关系
            '46000': '移动',
            '46002': '移动',
            '46007': '移动',
            '46004': '移动',
            '46001': '联通',
            '46006': '联通',
            '46009': '联通',
            '46003': '电信',
            '46005': '电信',
            '46011': '电信',
            '00101': '白卡',
        }

        _operator_mapping = {
            "移动": "CMCC",
            "联通": "中国联通",
            "电信": "中国电信",
            "白卡": "白卡",
        }
        time.sleep(5)
        cimi_data = self.send_at('AT+CIMI')
        cimi = ''.join(re.findall(r"\d{14,16}", cimi_data))
        plmn = cimi[:5]  # 获取前五位PLMN的值
        if not plmn:
            raise ATError("AT+CIMI查询PLMN失败")
        return _operator_mapping[_operator_plmn_mapping[plmn]]

    def sin_pin_remove(self):
        """
        删除SIM的PIN码，用于指令删除SIM PIN或者异常后SIM PIN的清除工作
        :return:
        """
        clck_status = self.send_at('AT+CLCK="SC",2', timeout=5)
        if "+CLCK: 1" in clck_status:
            self.send_at('AT+CLCK="SC",0,"1234"', timeout=5)
            self.check_network()

    def bound_5G_network(self):  # noqa
        # 检查当前是否是5G网络
        network_info = self.check_servingcell()
        at_logger.info(f"检查当前是否是5G网络: {network_info}")
        if network_info:  # 如果返回了NSA或者SA并且不为''
            return True  # 是5G网络立刻结束

        # 尝试固定SA网络
        self.send_at('AT+QNWPREFCFG="mode_pref",NR5G')
        at_data = self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
        if 'ERROR' in at_data:
            raise ATError('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')

        # 查询固定SA是否正常
        start_timestamp = time.time()
        while time.time() - start_timestamp < 60:
            at_logger.info("正在检查是否注册SA网络")
            servingcell = self.check_servingcell()
            if servingcell == 'SA':
                at_logger.info("注册SA网络类型成功")
                return True  # 固定了SA网络则立刻返回
            time.sleep(3)
        else:
            at_logger.error("60秒内注册SA网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持")

        # 尝试固定NSA网络
        self.send_at('AT+QNWPREFCFG="mode_pref",AUTO')
        self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",1')

        # 查询固定NSA是否正常
        start_timestamp = time.time()
        while time.time() - start_timestamp < 60:
            at_logger.info("正在检查是否注册NSA网络")
            servingcell = self.check_servingcell()
            if servingcell == 'NSA':
                at_logger.info("注册NSA网络类型成功")
                return True  # 固定NSA网络正常
            time.sleep(3)
        else:
            raise ATError("注册SA and NSA网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持")  # 异常抛出

    def bound_network(self, network_type, timeout=180):
        """
        固定指定网络
        :param timeout：设置指定网络后检查的超时时间
        :param network_type: 取值：SA/NSA/LTE/WCDMA
        """
        # 固定网络
        network_type = network_type.upper()  # 转换为大写

        at_logger.info("固定网络到{}".format(network_type))
        if network_type in ["LTE", "WCDMA"]:  # 固定LTE或者WCDMA
            self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at('AT+QNWPREFCFG= "mode_pref",{}'.format(network_type))
        elif network_type == 'SA':  # 固定SA网络
            self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.send_at('AT+QNWPREFCFG= "mode_pref",NR5G')
        elif network_type == "NSA":  # 使用nr5g_disable_mode进行SA和NSA偏号设置
            self.send_at('AT+QNWPREFCFG="mode_pref",AUTO')
            at_data = self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",1')
        else:
            raise ATError("不支持的网络类型设置")

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            raise ATError('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')

        # 查询是否固定正常
        start_timestamp = time.time()
        while time.time() - start_timestamp < timeout:
            # 获取当前网络状态
            at_logger.info("正在检查是否注册{}网络".format(network_type))
            cops_value = self.check_network()  # 检查cops值，用作LTE和WCDMA固定的检查
            network_info = self.check_servingcell()  # 检查serving cell的值，用作SA和NSA的检查

            # 判断当前网络状态
            if network_type == "LTE" and cops_value == '7':
                at_logger.info("注册LTE网络类型成功，当前COPS: 7")
                return True
            elif network_type == "WCDMA" and cops_value == '2':
                at_logger.info("注册WCDMA网络类型成功，当前COPS: 2")
                return True
            elif network_type == network_info:  # 5G网络，包括SA和NSA
                at_logger.info("注册{}网络类型成功".format(network_type))
                return True
            time.sleep(3)
        else:
            raise ATError("{}秒内注册{}网络类型失败，请检查当前网络环境是否支持和SIM卡是否支持".format(timeout, network_type))

    def check_servingcell(self):
        """
        bound_network联合使用的函数。
        注册5G网络时候检测是SA还是NSA
        :return: '11' 注册 'SA', '13' 注册NSA
        """
        network = self.send_at('AT+QENG="SERVINGCELL"')
        if 'NOCONN' in network or 'CONNECT' in network:
            if 'NR5G-NSA' in network:
                return 'NSA'
            elif 'NR5G-SA' in network:
                return 'SA'
            else:
                return ''
        else:
            return ''

    def reset_network_to_default(self):
        """
        进行网络类型绑定之后设置回初始值
        :return:
        """
        mode_pref_data = self.send_at('AT+QNWPREFCFG= "mode_pref",AUTO')
        nr5g_disable_mode_data = self.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
        if "ERROR" in mode_pref_data:
            raise ATError('发送AT+QNWPREFCFG="mode_pref",AUTO 返回ERROR')
        if "ERROR" in nr5g_disable_mode_data:
            raise ATError('发送AT+QNWPREFCFG="nr5g_disable_mode",0 返回ERROR')

    def send_sms(self, opeartor):
        """
        给对应运营商发送短信
        :param opeartor: 运营商
        :return: None
        """
        _operator_mapping = {
            'CMCC': "10086",
            "中国联通": "10010",
            "中国电信": "10000"
        }
        at_logger.info("发送短信到{}".format(_operator_mapping[opeartor]))

        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            __at_port.write('AT+CMGF=1;+CMGS="{}"\r\n'.format(_operator_mapping[opeartor]).encode("utf-8"))
            time.sleep(0.3)
            __at_port.write('00{}'.format(chr(0x1a)).encode('utf-8'))

    def readline_keyword(self, keyword1='', keyword2='', timout=10, at_flag=False, at_cmd=''):
        # 先检测AT口是否可以正常打开
        for i in range(10):
            try:
                __at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
                __at_port.close()
                break
            except Exception:  # noqa
                time.sleep(1)
                continue
        else:
            raise ATError('连续十次打开AT口失败')
        at_logger.info('检查关键字:{} {}, 超时时间:{}'.format(keyword1, keyword2, timout))
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as __at_port:
            if at_flag:
                __at_port.write('{}\r\n'.format(at_cmd).encode('utf-8'))
            start_time = time.time()
            return_val_cache = ''
            while True:
                time.sleep(0.001)
                return_val = self.readline(__at_port)
                if return_val != '':
                    return_val_cache += return_val
                if time.time() - start_time > timout:
                    raise ATError('{}S内未检测到{},{}'.format(timout, keyword1, keyword2))
                if keyword1 in return_val_cache and keyword2 in return_val_cache:
                    at_logger.info('已检测到{},{}'.format(keyword1, keyword2))
                    return True

    def set_cgdcont(self, operator, ip_type="IPV4V6"):
        apn_mapping = {
            "CMCC": "CMNET",
            "中国电信": "CTNET",
            "中国联通": "3GNET",
            None: ""
        }

        # 添加APN
        error_apn = '123'
        apn = apn_mapping.get(operator, error_apn)
        self.send_at('at+cgdcont=1,"{}","{}"'.format(ip_type, apn))

    def set_qnetdevstatus(self, status=1):
        self.send_at("AT+QNETDEVSTATUS={}".format(status))

    def set_sim_pin(self):
        self.send_at('AT+CLCK="SC",1,"1234"')

    def switch_to_ndis(self, ndis_driver_name='Quectel Wireless Ethernet Adapter'):
        """
        切换NDIS拨号模式。
        :param ndis_driver_name: NDIS windows 网卡名称
        :return: True，切换成功
        """
        at_logger.info("检查是否是NDIS拨号模式")
        usbnet = self.send_at('AT+QCFG="USBNET"')
        network_cards = get_network_card_names()
        if ',0' in usbnet:
            for name in network_cards:
                if ndis_driver_name.replace('*', ' ').strip() in name:  # 替换通配符和空白字符
                    at_logger.info("当前已经是NDIS拨号模式")
                    return True
        # 不是NDIS:
        # 切换NDIS -> 装载驱动 -> CFUN1,1 -> 检测驱动
        at_logger.info("切换NDIS拨号")
        self.send_at('AT+QCFG="usbnet",0', 3)
        time.sleep(5)  # 增加两条AT的间隔时间，目前发现有可能会出现AT不通
        usbnet = self.send_at('AT+QCFG="usbnet"', 3)
        if ',0' not in usbnet:
            raise ATError("切换NDIS模式失败")
        at_logger.info("安装NDIS驱动")
        # 2. 装载驱动
        driver_path = ''
        for path, dirs, files in os.walk('C:\\Program Files (x86)'):
            for file in files:
                if 'qcwwan.inf' in file and 'windows10' in path:
                    driver_path = os.path.join(path, file)
        if driver_path == '':
            raise ATError("未检测到NDIS驱动安装，请重新安装模块驱动到默认路径")
        driver_path = driver_path.replace('&', '"&"')
        at_logger.info(driver_path)
        s = subprocess.run("powershell pnputil /add-driver '{}'".format(driver_path), shell=True, capture_output=True,
                           text=True)
        if s.returncode != 0:
            at_logger.info(s)
            raise ATError("添加NDIS驱动失败")
        # 3. CFUN1,1
        self.send_at('AT+CFUN=1,1', 3)
        # 4. check ndis_driver_name
        timeout = 100
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(1)
            drivers = get_network_card_names()
            for driver in drivers:
                if ndis_driver_name.replace('*', ' ').strip() in driver:
                    at_logger.info("切换NDIS拨号模式成功")
                    at_logger.info("等待30S")
                    time.sleep(30)
                    return True
        raise ATError("切换NDIS拨号模式失败")

    def switch_to_mbim(self, mbim_driver_name="RG500Q"):
        """
        切换MBIM拨号模式。
        :param mbim_driver_name: MBIM驱动的名称
        :return: True:切换成功
        """
        mbim_driver_names = mbim_driver_name.split(",")
        at_logger.info("检查是否是MBIM拨号模式")
        usbnet = self.send_at('AT+QCFG="USBNET"')
        network_cards = get_network_card_names()
        if ',2' in usbnet:
            for network_card in network_cards:
                for name in mbim_driver_names:
                    if name in network_card:
                        at_logger.info("当前已经是MBIM拨号模式")
                        return True

        # 不是MBIM
        # 卸载驱动->切换usbnet2->cfun1,1->检测驱动
        at_logger.info('卸载NDIS驱动')
        s = subprocess.run("powershell pnputil /enum-drivers", shell=True, capture_output=True, text=True)
        ndis_driver_name = ''.join(re.findall(r'(oem.*?inf)\n.*?qcwwan', s.stdout))
        if ndis_driver_name:
            at_logger.info('ndis_driver_name:{}'.format(ndis_driver_name))
            s = subprocess.run('powershell pnputil /delete-driver {} /force'.format(ndis_driver_name), shell=True,
                               capture_output=True, text=True)
            at_logger.info(s)

        at_logger.info("切换MBIM拨号")
        self.send_at('AT+QCFG="usbnet",2', 3)
        time.sleep(5)  # 增加两条AT的间隔时间，目前发现有可能会出现AT不通
        usbnet = self.send_at('AT+QCFG="usbnet"', 3)
        if ',2' not in usbnet:
            raise ATError("切换MBIM模式失败")

        # 3. CFUN1,1
        self.send_at('AT+CFUN=1,1', 3)

        # 4. check mbim_driver_name
        timeout = 150
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(1)
            drivers = get_network_card_names()
            at_logger.info('drivers: {}'.format(drivers))
            at_logger.info('mbim_driver_name：{}'.format(mbim_driver_name))
            at_logger.info(mbim_driver_name in ''.join(drivers))
            mbim_driver_names = mbim_driver_name.split(",")
            for driver in drivers:
                for mbim_driver in mbim_driver_names:
                    if mbim_driver.replace('*', ' ').strip() in driver:
                        at_logger.info("切换MBIM拨号模式成功")
                        at_logger.info("等待30S")
                        time.sleep(30)
                        return True
        raise ATError("切换MBIM拨号模式失败")

    @watchdog("获取版本号是否正确")
    def check_version(self, revision, sub_edition):
        return_value = self.send_at('ATI+CSUB', 20)
        revision_r = ''.join(re.findall(r'Revision: (.*)', return_value))
        sub_edition_r = ''.join(re.findall('SubEdition: (.*)', return_value))
        if revision not in revision_r or sub_edition not in sub_edition_r:
            raise ATError("模块版本号检查异常")

    @watchdog("检查USB口稳定性")
    def check_at_port_stability(self):
        # self.check_urc()
        time.sleep(3)
        self.send_at("ATE")
        start = time.time()
        try:
            with serial.Serial(self._at_port, baudrate=115200, timeout=0.8) as at_port:
                while time.time() - start < 60:
                    at_logger.info('AT\r\n'.encode('utf-8'))
                    at_port.write('AT\r\n'.encode('utf-8'))
                    time.sleep(0.5)
                    data = at_port.read(size=1024).decode('utf-8', 'ignore')
                    at_logger.info(repr(data))
        except Exception as e:
            raise ATError("AT口异常：{}".format(e))

    @watchdog("QTEST DUMP 测试")
    def check_qtest_dump(self):
        cache = ""
        with serial.Serial(self._at_port, baudrate=115200, timeout=0.8) as at_port:
            at_port.write('AT+QTEST="dump",1\r'.encode('utf-8'))
            start = time.time()
            while time.time() - start < 60:
                time.sleep(0.1)
                data = self.readline(at_port)
                if data:
                    cache += data
        at_logger.info(f"cache: {cache}\nrepr(cache): {repr(cache)}")
        if cache.replace('AT+QTEST="dump",1\r', "") == "":
            raise ATError('发送 AT+QTEST="dump",1 指令后未发现modem重启后的URC上报')
        cfun = self.send_at('AT+CFUN?', timeout=15)
        if 'CFUN: 1' not in cfun:
            raise ATError('发送AT+QTEST="dump",1后20S CFUN值异常')
        cpin = self.send_at('AT+CPIN?')
        if 'READY' not in cpin:
            raise ATError('发送AT+QTEST="dump",1后20S CPIN值异常')

    @watchdog("获取模块默认usbid")
    def check_usb_default_id(self):
        res = self.send_at('at+qcfg="usbid"')
        if '11388,2048' not in res:
            raise ATError('at+qcfg="usbid"查询默认USBID异常，查询结果为{}'.format(res))

    @watchdog("标准版本检查默认拨号模式NDIS")
    def check_default_dial_mode(self):
        res = self.send_at('at+qcfg="usbnet"')
        res = ''.join(re.findall(r'"usbnet",0', res))
        if not res:
            raise ATError("默认拨号模式检查异常{}".format(res))

    @watchdog("检查笔电默认拨号模式为MBIM")
    def check_default_dial_mode_mbim(self):
        res = self.send_at('at+qcfg="usbnet"')
        res = ''.join(re.findall(r'"usbnet",2', res))
        if not res:
            raise ATError("默认拨号模式检查异常{}".format(res))

    @watchdog("解除SIM PIN")
    def at_unlock_sim_pin(self, pin):
        res = self.send_at("at+cpin={}".format(pin), timeout=5)
        if 'OK' not in res:
            raise ATError("SIM PIN解除异常")

    @watchdog("开始进行DFOTA升级")
    def dfota_ftp_http_https_step_1(self, dfota_type, fota_cmd, stop_download=False):
        """
        仅处理at+qfotadl指令中关机前的部分：
        1. FTP，检测+QIND: "FOTA","FTPSTART" 到 +QIND: "FOTA","FTPEND",0
        2. HTTP，检测+QIND: "FOTA","HTTPSTART" 到 +QIND: "FOTA","HTTPEND",0
        2. HTTPS，检测+QIND: "FOTA","HTTPSTART" 到 +QIND: "FOTA","HTTPEND",0
        :return: None
        """
        check_fragment = 'FTP' if dfota_type.upper() == 'FTP' else "HTTP"
        at_logger.info('check_fragment: {}'.format(check_fragment))
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as at_port:
            at_port.write(f'AT+QFOTADL="{fota_cmd}"\r\n'.encode('utf-8'))
            at_logger.info('Send: {}'.format(f'AT+QFOTADL="{fota_cmd}"\r\n'))
            # 检查 FTPSTART / HTTPSTART
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                check_msg = '+QIND: "FOTA","{}START"'.format(check_fragment)
                if check_msg in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    break
                if time.time() - start_time > 60:
                    raise ATError("发送升级指令后60秒内未检测到{}".format(check_msg))
                if 'ERROR' in recv:
                    raise ATError("发送DFOTA升级指令返回ERROR")
            # 如果需要断电或者断网
            if stop_download:
                sleep_time = random.uniform(1, 2)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            # 检查 "FOTA","FTPEND",0 "FOTA","HTTPEND",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","{}END",(\d+)'.format(check_fragment), recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}".format(recv))
                        return True
                    else:
                        at_logger.error("DFOTA下载差分包异常：{}".format(recv))
                        return False
                if time.time() - start_time > 300:
                    raise ATError("DFOTA下载差分包超过300S异常")

    @watchdog("检测DFOTA差分包加载")
    def dfota_step_2(self, stop_download=False, start=False):
        """
        发送at+qfotadl指令关机并开机后的log检查：
        检测+QIND: "FOTA","START" 到 +QIND: "FOTA","END",0
        :return: None
        """

        for i in range(100):
            try:
                at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(1)
                continue
        else:
            raise ATError("检测DFOTA升级时打开AT口异常")

        start_urc_flag = False
        start_time = time.time()
        try:
            # 检查 FTPSTART / HTTPSTART，如果检测到UPDATING，则没有检测到，为了保证可以断电等操作，直接跳出
            while time.time() - start_time < 300:
                time.sleep(0.001)
                recv = self.readline(at_port)
                check_msg = '+QIND: "FOTA","START"'
                if check_msg in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    start_urc_flag = True
                    if start:
                        at_logger.info(f"在{check_msg}处断电")
                        return True
                    break
                if '+QIND: "FOTA","UPDATING"' in recv:
                    at_logger.error("未检测到{}".format(check_msg))
                    break
            else:
                at_logger.error('DFOTA 检测{} +QIND: "FOTA","START"失败')
                raise ATError('DFOTA升级过程异常：检测{} +QIND: "FOTA","START"失败')
            # 如果需要断电或者断网
            if stop_download:
                sleep_time = random.uniform(5, 10)
                at_logger.info("随机等待{} s".format(sleep_time))
                time.sleep(sleep_time)
                return True
            # 检查 "FOTA","END",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","END",(\d+)', recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                        return True
                    else:
                        at_logger.error("DFOTA升级异常异常：{}".format(recv))
                        return False
                if time.time() - start_time > 300:
                    raise ATError("DFOTA下载差分包超过300S异常")
        finally:
            if getattr(at_port, 'close', None):
                at_port.close()
            if start_urc_flag is False:
                raise ATError('未检测到DFOTA上报+QIND: "FOTA","START"')

    @watchdog('检查DFOTA ,"UPDATING",95+')
    def dfota_end_0(self):

        for i in range(100):
            try:
                at_port = serial.Serial(self._at_port, baudrate=115200, timeout=0)
                break
            except serial.serialutil.SerialException as e:
                at_logger.info(e)
                time.sleep(1)
                continue
        else:
            raise ATError("检测DFOTA升级时打开AT口异常")

        updating_urc_flag = False
        start_urc_flag = False
        try:
            # 检查 FTPSTART / HTTPSTART，如果检测到UPDATING，则没有检测到，为了保证可以断电等操作，直接跳出
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                check_msg = '+QIND: "FOTA","START"'
                if check_msg in recv:
                    at_logger.info("已检测到{}".format(check_msg))
                    start_urc_flag = True
                    break
                if '+QIND: "FOTA","UPDATING"' in recv:
                    at_logger.error("FOTA END 0断电检测到UPDATING URC")
                    updating_urc_flag = True
                    break
            # 检查 "FOTA","END",0
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","END",(\d+)', recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                        return True
                    else:
                        at_logger.error("DFOTA升级异常异常：{}".format(recv))
                        return False
                if '+QIND: "FOTA","UPDATING"' in recv:
                    at_logger.error("FOTA END 0断电检测到UPDATING URC")
                    updating_urc_flag = True
                if time.time() - start_time > 300:
                    raise ATError("DFOTA下载差分包超过300S异常")
        finally:
            if getattr(at_port, 'close', None):
                at_port.close()
            if start_urc_flag is False:
                raise ATError('未检测到DFOTA上报+QIND: "FOTA","START"')
            if updating_urc_flag:
                raise ATError("FOTA END 0断电检测到UPDATING URC")

    @watchdog("检测701异常")
    def dfota_dl_package_701_702(self):
        """
        dfota断网后需要捕获701异常
        :return:
        """
        start_time = time.time()
        with serial.Serial(self._at_port, baudrate=115200, timeout=0) as at_port:
            while True:
                time.sleep(0.001)
                recv = self.readline(at_port)
                if 'END",701' in recv or 'END",702' in recv:
                    at_logger.info("已经检测到701")
                    return True
                if time.time() - start_time > 180:
                    raise ATError("断网后DFOTA升级命令未返回701")

    @watchdog("发送AT+CFUN?")
    def cfun(self):
        """
        发送AT+CFUN?
        """
        cfun_status = self.send_at("AT+CFUN?", 15)
        if "OK" not in cfun_status:
            raise ATError("发送AT+CFUN?未返回OK")

    @watchdog("发送AT+CFUN=0")
    def cfun0(self):
        """
        发送AT+CFUN=0
        """
        cfun_status = self.send_at("AT+CFUN=0", 15)
        if "OK" not in cfun_status:
            raise ATError("发送AT+CFUN=0未返回OK")

    @watchdog("发送AT+CFUN=1")
    def cfun1(self):
        """
        发送AT+CFUN=1
        """
        cfun_status = self.send_at("AT+CFUN=1", 15)
        if "OK" not in cfun_status:
            raise ATError("发送AT+CFUN=1未返回OK")

    @watchdog("发送AT+CFUN=4")
    def cfun4(self):
        """
        发送AT+CFUN=4
        """
        cfun_status = self.send_at("AT+CFUN=4", 15)
        if "OK" not in cfun_status:
            raise ATError("发送AT+CFUN=4未返回OK")

    @watchdog("发送CFUN1/1重启")
    def cfun1_1(self):
        at_logger.info("发送AT+CFUN=1,1")
        cfun_status = self.send_at("AT+CFUN=1,1", 15)
        if "OK" not in cfun_status:
            return False

    @watchdog("设置DUMP模式不重启")
    def set_dump_0(self):
        at_logger.info("Set DUMP Mode")
        # 设置系统不重启
        self.send_at('AT+QCFG="ModemRstLevel",0', timeout=3)
        # 设置死机进DUMP
        self.send_at('AT+QCFG="ApRstLevel",0', timeout=3)

    @watchdog("获取mbn状态")
    def get_mbn_status(self):
        for i in range(20):
            self.send_at('at+cgdcont?', timeout=15)
            mbn_status = self.send_at('at+qmbncfg="list"', timeout=15)
            if 'OK' in mbn_status and ",0,1,1" in mbn_status:
                break
            time.sleep(3)
        else:
            at_logger.error('case执行前初始化查询MBN列表异常')


class ATBackgroundThread(Thread):
    """
    用于类似quectel-CM拨号后上报拨号状态URC的检测：
    首先创建ATBackgroundThread，然后进行quectel-CM拨号，最后检查ATBackgroundThread中读取到的AT。
    """

    def __init__(self, at_port, check_info='', timeout=0):
        super().__init__()
        self.at_port = at_port
        self.cache = ''
        self.check_info = check_info
        self.flag = True
        self.timeout = timeout

    @staticmethod
    def readline(port):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值：
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

    def run(self):
        start_timestamp = time.time()
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            while self.flag:
                time.sleep(0.001)  # 减少资源占用
                return_value = self.readline(at_port)
                if return_value:
                    self.cache += return_value
                if self.timeout and time.time() - start_timestamp > self.timeout:
                    break

    @watchdog("获取是否上报信息")
    def get_info(self):
        at_logger.info(self.cache)
        self.flag = False
        self.check_info = [self.check_info] if isinstance(self.check_info, str) else self.check_info
        for item in self.check_info:
            if item not in self.cache:
                at_logger.error("未检测到上报{}".format(item))
                return False
            else:
                at_logger.info("成功检测到上报{}".format(item))


if __name__ == '__main__':
    # with ATHandle(at_port="COM73") as at:
    #     print(at.send_at('AT+COPS?'))
    at_handler = ATHandle("COM7")
    at_handler.bound_network("NSA")
    # at_handler.bound_5G_network()
