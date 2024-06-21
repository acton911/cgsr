import threading

import requests
import serial
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.functions.linux_api import LinuxAPI, PINGThread
from utils.logger.logging_handles import all_logger, at_logger
from utils.exception.exceptions import MBIMError, ATError
import subprocess
import time
import os
from utils.functions.iperf import iperf
from utils.operate.reboot_pc import Reboot


class LinuxMBIMManager:
    def __init__(self, at_port, dm_port, imei, phone_number, extra_ethernet_name, params_path):
        self.linux_api = LinuxAPI()
        self._at_port = at_port
        self.at_handler = ATHandle(at_port)
        self.phone_number = phone_number
        self.driver = DriverChecker(at_port, dm_port)
        self.imei = imei
        self.extra_ethernet_name = extra_ethernet_name
        self.operator = self.at_handler.get_operator()
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.reboot = Reboot(at_port, dm_port, params_path)

    def enter_mbim_mode(self):
        self.set_linux_mbim_and_remove_driver()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()
        self.check_linux_mbim_and_driver_name()

    def reset_usbnet(self):
        """
        设置USBNET的值为0并重启
        :return: None
        """
        all_logger.info("设置USBNET为0")
        self.at_handler.send_at('AT+QCFG="USBNET",0', 0.3)
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()

    def hang_up_after_system_dial(self, wait_time):
        """
        系统拨号n秒后主动挂断
        :param wait_time: 系统拨号持续时长
        :return:
        """
        content = {"exec_type": 1,
                   "payload": {
                       "phone_number": self.phone_number,
                       "hang_up_after_dial": wait_time
                   },
                   "request_id": "10011"
                   }
        dial_request = requests.post(self.url, json=content)
        all_logger.info(dial_request.json())
        self.at_handler.readline_keyword('RING', timout=300)
        time.sleep(5)
        self.at_handler.readline_keyword('NO CARRIER', timout=300)
        time.sleep(5)

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        self.at_handler.send_at('AT+CPMS="ME","ME","ME"', 10)  # 指定存储空间
        self.at_handler.send_at('AT+CMGD=0,4', 10)  # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
        all_logger.info(f'{self.phone_number}')
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())
        self.at_handler.readline_keyword('+CMTI', timout=300)
        time.sleep(5)

    def set_linux_mbim_and_remove_driver(self):
        """
        设置MBIM拨号方式并且删除所有的网卡
        :return: None
        """
        time.sleep(5)  # 防止刚开机AT不生效
        all_logger.info("设置USBNET为2")
        self.at_handler.send_at('AT+QCFG="USBNET",2')

        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'GobiNet']
        for name in network_types:
            all_logger.info(f"删除{name}网卡")
            subprocess.run(f"modprobe -r {name}", shell=True)

    def udhcpc_get_ip(self, network_card_name):
        all_logger.info(f"udhcpc -i {network_card_name}")
        process = subprocess.Popen(f'udhcpc -i {network_card_name}',
                                   stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE,
                                   shell=True)
        t = threading.Timer(120, self.process_input)
        t.setDaemon(True)
        t.start()
        get_result = ''
        while process.poll() is None:
            value = process.stdout.readline().decode()
            if value:
                all_logger.info(value)
                get_result += value
        all_logger.info(get_result)

    @staticmethod
    def process_input():
        subprocess.Popen("killall udhcpc", shell=True)

    def check_linux_mbim_and_driver_name(self):
        """
        检查是否是MBIM拨号方式，检查mbim驱动是否加载，检查WWAN驱动名称
        :return: None
        """
        all_logger.info("检查USBNET为2")
        for i in range(0, 5):
            time.sleep(5)
            usbnet = self.at_handler.send_at('AT+QCFG="USBNET"')
            if ',2' in usbnet:
                all_logger.info('当前设置usbnet模式为2')
                break
            else:
                if i == 4:
                    raise MBIMError(f'设置usbnet失败,当前查询返回为{usbnet}')
                all_logger.info(f'当前查询指令返回{usbnet},等待5秒后再次查询')
                continue
        all_logger.info("检查cdc_mbim驱动加载")
        timeout = 30
        for _ in range(timeout):
            s = subprocess.run('lsusb -t', shell=True, capture_output=True, text=True)
            all_logger.info(s)
            if 'cdc_mbim' in s.stdout:
                break
            time.sleep(1)
        else:
            all_logger.info(f"MBIM驱动开机后{timeout}S未加载成功")
            raise MBIMError(f"MBIM驱动开机后{timeout}S未加载成功")

        all_logger.info("检查wwan0驱动名称")
        s = subprocess.run("ip a | grep -o wwan0", shell=True, capture_output=True, text=True)
        all_logger.info(s)
        if 'wwan0' not in s.stdout:
            all_logger.info(f'MBIM驱动名称异常->"{s.stdout}"')
            raise MBIMError(f'MBIM驱动名称异常->"{s.stdout}"')

    @staticmethod
    def check_linux_wwan0_network_card_disappear():
        """
        断开拨号后，检查WWAN0网卡消失
        :return: None
        """
        wwan0_status = os.popen('ifconfig wwan0').read()
        if 'not found' in wwan0_status:
            all_logger.info("quectel-CM异常，wwan0网卡未消失")
            raise MBIMError("quectel-CM异常，wwan0网卡未消失")

    def check_linux_mbim_before_connect(self):
        """
        进行MBIM拨号前，检查MBIM状态是否正常
        :return: None
        """
        all_logger.info("获取MBIM挂载的节点")
        mount_node = os.popen('ls /dev/cdc-wdm* | tr -s " "| cut -d / -f 3 | head -c -1').read()
        if not mount_node:
            all_logger.info("{}".format(os.popen('ls /dev/cdc-wdm*').read()))
            raise MBIMError("未找到MBIM挂载的节点，例如 /dev/cdc-wdm1")

        all_logger.info("检查MBIM是未连接状态")
        for i in range(30):
            uname_ubuntu = os.popen('cat /etc/issue').read()
            if '20.04' in uname_ubuntu or '18.04' in uname_ubuntu:
                all_logger.info(f'{uname_ubuntu}')
                break
            mbim_status = os.popen(f'nmcli | grep {mount_node}').read()
            if 'disconnected' in mbim_status or '已断开' in mbim_status or 'unavailable' in mbim_status:
                break
            time.sleep(1)
        else:
            all_logger.info("{}".format(os.popen('nmcli').read()))
            raise MBIMError("未检测到MBIM disconnected 信息")

        all_logger.info("获取网卡在mmcli -L列表位置")
        mmcli_number = os.popen('mmcli -L | cut -d / -f 6 | cut -d " " -f 1 | head -c -1').read()
        all_logger.info('mmcli -L | cut -d / -f 6 | cut -d " " -f 1 | head -c -1')
        all_logger.info(f'{mmcli_number}')
        if not mmcli_number:
            all_logger.info("{}".format(os.popen('mmcli -L').read()))
            raise MBIMError("mmcli -L命令未获取到网卡序列号")

        all_logger.info("获取imei")
        mmcli_imei = os.popen(f'mmcli -m {mmcli_number} | grep imei | tr -s " " | cut -d " " -f 5 | head -c -1').read()
        all_logger.info(f'mmcli -m {mmcli_number} | grep imei | tr -s " " | cut -d " " -f 5 | head -c -1')
        all_logger.info(f'{mmcli_imei}')
        if mmcli_imei != self.imei:
            all_logger.info("{}".format(os.popen(f'mmcli -m {mmcli_number}').read()))
            raise MBIMError("IMEI对比异常")

        all_logger.info("获取运行商")
        _operator_mapping = {
            'CMCC': "CMCC",
            '中国联通': "CHN-UNICOM",
            '中国电信': "中国电信",
        }

        for i in range(10):
            all_logger.info(f'mmcli -m {mmcli_number} | grep "operator name:" | tr -s " "| cut -d " " -f 5 | head -c -1')
            mmcli_operator = os.popen(f'mmcli -m {mmcli_number} | grep "operator name:" | tr -s " "| cut -d " " -f 5 | head -c -1').read()
            if mmcli_operator == _operator_mapping[self.operator]:
                break
            time.sleep(1)
        else:
            all_logger.info("{}".format(os.popen(f'mmcli -m {mmcli_number}').read()))
            raise MBIMError("运营商对比异常")

    def linux_mbim_connect(self):
        """
        进行MBIM拨号连接
        :return: None
        """
        _operator_mapping = {
            'CMCC': "CMNET",
            '中国联通': "3GNET",
            '中国电信': "CTNET",
        }
        apn = _operator_mapping[self.operator]
        os.popen(f'nmcli connection delete "{apn}"').read()
        os.popen(f'nmcli c add con-name "{apn}" type gsm ifname "*" apn "{apn}"').read()
        time.sleep(5)

    @staticmethod
    def check_linux_mbim_after_connect():
        """
        MBIM拨号成功后检查MBIM的状态是否异常
        :return: None
        """
        all_logger.info("检查信号")
        signal_status = os.popen('mmcli -m 6 | grep -oE "signal quality.*"').read()
        all_logger.info(signal_status)

        all_logger.info("获取MBIM挂载的节点")
        mount_node = os.popen('ls /dev/cdc-wdm* | tr -s " "| cut -d / -f 3 | head -c -1').read()
        if not mount_node:
            all_logger.info("{}".format(os.popen('ls /dev/cdc-wdm*').read()))
            raise MBIMError("未找到MBIM挂载的节点，例如 /dev/cdc-wdm1")

        all_logger.info("检查MBIM是已连接状态")
        mbim_status = os.popen(f'nmcli | grep {mount_node}').read()
        if 'connected' not in mbim_status or '已连接' in mbim_status:
            all_logger.info("{}".format(os.popen('nmcli').read()))
            raise MBIMError("未检测到MBIM connected 信息")

        all_logger.info("获取ip信息上传")
        ip_status = os.popen("ifconfig wwan0").read()
        all_logger.info(ip_status)

    def linux_mbim_disconnect(self):
        """
        断开MBIM拨号连接
        :return: None
        """
        all_logger.info("断开MBIM连接")
        _operator_mapping = {
            'CMCC': "CMNET",
            '中国联通': "3GNET",
            '中国电信': "CTNET",
        }
        apn = _operator_mapping[self.operator]
        os.popen(f'nmcli connection delete "{apn}"').read()
        time.sleep(1)

    def dial_check_network(self):
        """
        拨号后进行PING连接，检查网路是否正常
        :return: None
        """
        _operator_mapping = {
            'CMCC': "10086",
            '中国联通': "10010",
            '中国电信': "10000",
        }
        operator_number = _operator_mapping[self.operator]
        self.at_handler.send_at(f"ATD{operator_number};")
        self.check_linux_mbim_and_driver_name()
        self.linux_api.ping_get_connect_status()
        self.at_handler.send_at("ATH")

    def cfun_0_1_4(self):
        """
        CFUN 0 1 4切换检查MBIM的状态
        :return: None
        """
        all_logger.info("查询CFUN状态")
        cfun_status = self.at_handler.send_at("at+cfun?", 15)
        if ': 1' not in cfun_status:
            raise MBIMError("CFUN状态不为1")

        all_logger.info("检查拨号情况")
        self.check_linux_mbim_before_connect()
        self.linux_mbim_connect()
        self.check_linux_mbim_after_connect()
        time.sleep(30)
        self.linux_api.ping_get_connect_status()

        all_logger.info("切换CFUN0")
        self.at_handler.send_at("at+cfun=0", 15)
        ping = PINGThread(times=5)
        ping.start()
        ping.join()
        ping.non_network_get_result()

        all_logger.info("切换CFUN1")
        self.at_handler.send_at("at+cfun=1", 15)
        self.at_handler.check_network()
        self.linux_mbim_disconnect()

        all_logger.info("检查拨号情况")
        self.check_linux_mbim_before_connect()
        self.linux_mbim_connect()
        self.check_linux_mbim_after_connect()
        self.linux_api.ping_get_connect_status()

        all_logger.info("切换CFUN4")
        self.at_handler.send_at("at+cfun=4", 15)
        ping = PINGThread(times=5)
        ping.start()
        ping.join()
        ping.non_network_get_result()

        all_logger.info("切换CFUN1")
        self.at_handler.send_at("at+cfun=1", 15)
        self.at_handler.check_network()
        self.linux_mbim_disconnect()

        all_logger.info("检查拨号情况")
        self.check_linux_mbim_before_connect()
        self.linux_mbim_connect()
        self.check_linux_mbim_after_connect()
        self.linux_api.ping_get_connect_status()
        self.linux_mbim_disconnect()

    @staticmethod
    def live_streaming_test(times=100):
        """
        检查观看直播是否正常
        :param times: 测试时间
        :return: None
        """
        iperf(times=times)

    @staticmethod
    def mbim_non_network_check():
        """
        没有网络检查MBIM拨号装填
        :return: None
        """
        ping = PINGThread(times=5)
        ping.start()
        ping.join()
        ping.non_network_get_result()

    def hard_reset(self):
        """
        硬重置，CFUN1，1后检查MBIM驱动加载，检查网络，用于异常恢复
        :return: None
        """
        self.set_linux_mbim_and_remove_driver()
        self.at_handler.cfun1_1()
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.check_urc()
        self.check_linux_mbim_and_driver_name()
        self.at_handler.check_network()

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是pcie模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handler.send_at('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handler.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            self.check_urc()
            time.sleep(5)

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
                        all_logger.info(f"{at_port_data}")
                    if 'PB DONE' in at_port_data:
                        time.sleep(1)  #  等待1s，尝试避免Device or resource busy
                        return True

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
                        at_logger.info(f'{repr(buf)}')
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            at_logger.error(f'Fatal ERROR: {error}')
        finally:
            return buf
