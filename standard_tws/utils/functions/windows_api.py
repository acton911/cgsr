import os
import re
import time
import keyboard
import subprocess
import mouse
import requests
from requests_toolbelt.adapters import source
from icmplib import multiping
from icmplib import ping
import win32clipboard
from functools import partial
from ..logger.logging_handles import all_logger
from ..functions.decorators import watchdog
from ..exception.exceptions import WindowsAPIError
import asyncio
from threading import Thread
import signal


watchdog = partial(watchdog, logging_handle=all_logger, exception_type=WindowsAPIError)


class WindowsAPI:

    @staticmethod
    def wheel(offset=-1):
        """
        鼠标滚动操作：首先点击参数传入的界面，然后使用mouse库的wheel进行滚动。
        :param offset: 需要滚动的偏移量，windows下，负值为向下，具体根据需求确定偏移。
        :return: None
        """
        mouse.wheel(offset)

    @staticmethod
    def get_clipboard_data(retries=10, delay=0.1):
        """
        获取剪切板的数据。
        :param retries: 异常重试次数。
        :param delay: 每次异常重试的间隔。
        :return: 剪切板的数据。
        """
        while True:
            try:
                win32clipboard.OpenClipboard()
                break
            except Exception as e:
                all_logger.info(e)
                retries = retries - 1
                time.sleep(delay)
        try:
            data = win32clipboard.GetClipboardData()
        finally:
            win32clipboard.CloseClipboard()
        return data

    @staticmethod
    @watchdog("检查拨号功能加载")
    def check_dial_init():
        """
        等待模块开机后PC端拨号功能加载成功
        :return: True:检测到， False：未检测到
        """
        timeout = 300  # 等待PC端拨号可以使用的最大时间
        stat_timestamp = time.time()
        while True:
            interface_status = os.popen('netsh mbn show interface').read()
            all_logger.info(repr(interface_status))

            # 如果超时
            if time.time() - stat_timestamp > timeout:
                all_logger.error("开机成功后{}秒内PC拨号功能未加载成功，请确定原因".format(timeout))
                return False

            if '没有' in interface_status:  # 如果没有检测到
                time.sleep(3)
            else:  # 如果检测到了
                all_logger.info("PC拨号功能加载成功")
                if time.time() - stat_timestamp >= 15:
                    all_logger.error("拨号功能加载时长超过15S")
                    return time.time() - stat_timestamp  # 返回时间用于判断
                else:
                    end_timestamp = time.time()
                    all_logger.info('wait 15 seconds')
                    time.sleep(15)  # 等待稳定
                    return end_timestamp - stat_timestamp  # 返回时间用于判断

    @staticmethod
    @watchdog("检查拨号功能消失")
    def check_dial_disappear():
        """
        等待模块开机后PC端拨号功能消失
        :return: True:检测到， False：未检测到
        """
        timeout = 100  # 等待PC端拨号可以使用的最大时间
        stat_timestamp = time.time()
        while True:
            interface_status = os.popen('netsh mbn show interface').read()
            if '没有' in interface_status:
                return True
            elif time.time() - stat_timestamp > timeout:
                all_logger.error("{}秒内PC拨号未消失，请确定原因".format(timeout))
                return False
            else:
                time.sleep(1)

    @staticmethod
    @watchdog("按ESC")
    def press_esc():
        keyboard.send('esc')
        time.sleep(1)

    @staticmethod
    def get_ip_address(ipv6_flag):
        """
        获取IP地址
        """
        all_logger.info("获取拨号连接名称")
        interface_data = os.popen("netsh mbn show interface").read()
        interface_name = ''.join(re.findall(r"\s+名称\s+:\s(.*)", interface_data))
        ipv4 = ''
        ipv6 = ''
        for i in range(30):
            all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
            connection_dic = {}
            ipconfig = os.popen("ipconfig").read()
            all_logger.debug(ipconfig)
            ipconfig = re.sub('\n.*?\n\n\n', '', ipconfig)  # 去除\nWindows IP 配置\n\n\n
            ipconfig_list = ipconfig.split('\n\n')
            for m in range(0, len(ipconfig_list), 2):  # 步进2，i为key，i+1为value
                connection_dic[ipconfig_list[m]] = ipconfig_list[m + 1]
            for k, v in connection_dic.items():
                if interface_name in k:
                    ipv6 = re.findall(r"\s{3}IPv6.*?:\s(.*?)\n", v)
                    ipv4 = re.findall(r"\s{3}IPv4.*?:\s(.*?)\n", v)
                    if ipv6 and ipv6_flag:
                        ipv6 = ''.join(ipv6[0])
                        return ipv6
                    if ipv4 and not ipv6_flag:
                        ipv4 = ''.join(ipv4[0])
                        return ipv4
            if (ipv6_flag and ipv6) or (ipv6_flag is False and ipv4):
                time.sleep(1)
                break
            else:
                time.sleep(1)
        else:
            all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            all_logger.error(subprocess.getoutput("ipconfig"))
            all_logger.error(subprocess.getoutput("ipconfig -all"))
            all_logger.error(subprocess.getoutput(f"ping -4 -S {ipv4} baidu.com"))
            all_logger.error(subprocess.getoutput(f"ping -4 -S {ipv4} 8.8.8.8"))
            all_logger.error(subprocess.getoutput(f"ping -4 -S {ipv4} 114.114.114.114"))
            return False

    @staticmethod
    @watchdog("进行PING连接测试")
    def ping_get_connect_status(ipv6_address="2402:f000:1:881::8:205", flag=True, ipv6_flag=False):
        if ipv6_flag:
            all_logger.info("进行IPV6 PING检查")
            ipv6 = WindowsAPI.get_ip_address(ipv6_flag)
            all_logger.info(f'IPV6地址为:{ipv6}')
            if flag:
                ping_datas = multiping([ipv6_address, '2400:3200::1', '2400:da00::6666'], count=10, interval=1, source=ipv6, family=6)
                for ping_data in ping_datas:
                    all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping ipv6检查正常')
                        return ipv6
                else:
                    all_logger.info('ping ipv6检查异常,尝试重新获取IP后进行测试')
                    ipv6 = WindowsAPI.get_ip_address(ipv6_flag)
                    all_logger.info(f'IPV6地址为:{ipv6}')
                    ping_datas = multiping([ipv6_address, '2400:3200::1', '2400:da00::6666'], count=10, interval=1, source=ipv6, family=6)
                    for ping_data in ping_datas:
                        all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                        if ping_data.is_alive:
                            all_logger.info('ping ipv6检查正常')
                            return ipv6
                    else:
                        all_logger.info('ping ipv6检查异常')
                        raise WindowsAPIError('ping ipv6检查异常')
            else:
                ping('2402:f000:1:881::8:205', count=10, interval=1, source=ipv6, family=6)
                time.sleep(1)
        else:
            all_logger.info("进行IPV4 PING检查")
            ipv4 = WindowsAPI.get_ip_address(ipv6_flag)
            all_logger.info(f'IPV4地址为:{ipv4}')
            target_ip_list = ['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8']
            if flag:
                for i in range(4):
                    try:
                        ping_data = ping(target_ip_list[i], count=10, interval=1, source=ipv4)
                        all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                        if ping_data.is_alive:
                            all_logger.info('ping ipv4检查正常')
                            return ipv4
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info(f'ping地址{target_ip_list[i]}失败')
                        continue
                else:
                    try:
                        all_logger.info('ping ipv4检查异常,尝试重新获取IP后进行测试')
                        ipv4 = WindowsAPI.get_ip_address(ipv6_flag)
                        all_logger.info(f'IPV4地址为:{ipv4}')
                        ping_datas = multiping(['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8'], count=10, interval=1, source=ipv4)
                        for ping_data in ping_datas:
                            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                            if ping_data.is_alive:
                                all_logger.info('ping ipv4检查正常')
                                return ipv4
                        else:
                            raise WindowsAPIError('重新获取IP后ping ipv4检查异常')
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info('ping检查异常，发送request请求检查网络是否正常')
                        s = requests.Session()
                        new_source = source.SourceAddressAdapter(ipv4)   # 指定网卡信息
                        s.mount('http://', new_source)
                        s.mount('https://', new_source)
                        s.trust_env = False   # 禁用系统的环境变量，在系统设置有代理的时候可用用此选项禁止请求使用代理
                        response = s.get(url='http://www.baidu.com')
                        response_1 = s.get(url='http://www.sina.com')
                        if response.status_code == 200 or response_1.status_code == 200:
                            all_logger.info('拨号后request请求正常')
                            return ipv4
                        else:
                            all_logger.info('拨号后request请求失败')
                            raise WindowsAPIError('拨号后ping检查异常，request请求失败')
            else:
                ping('www.baidu.com', count=10, interval=1)
                time.sleep(1)

    @staticmethod
    def enable_disable_com_port(flag, port, silicon=False):
        """
        禁用或者启用端口，防止端口占用。
        :param port: 需要禁用的串口号
        :param flag: True:禁用驱动，False：启用驱动。
        :param silicon: 有的UART线是Silicon生产的，名称不一样，所以要增加兼容
        :return: None
        """
        all_logger.info('{}驱动{}'.format("禁用" if flag else "启用", port))
        cmd = 'powershell "Get-PnpDevice -FriendlyName "USB*Port*{}*" -status "OK" | disable-pnpdevice -Confirm:$True"'.format(port) if flag else\
            'powershell "Get-PnpDevice -FriendlyName "USB*Port*{}*" -status "Error" | enable-pnpdevice -Confirm:$Ture"'.format(port)
        if silicon:
            cmd = 'powershell "Get-PnpDevice -FriendlyName "*UART*Bridge*{}*" -status "OK" | disable-pnpdevice -Confirm:$True"'.format(port) if flag else\
                'powershell "Get-PnpDevice -FriendlyName "*UART*Bridge*{}*" -status "Error" | enable-pnpdevice -Confirm:$Ture"'.format(port)
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

        time.sleep(1)

    @staticmethod
    def remove_ndis_driver():
        """
        在Windows切换USBNET 1的时候，卸载NDIS驱动（不卸载会导致monitor与TWS系统交互异常）
        :return: None
        """
        all_logger.info('检查NDIS驱动')
        s = subprocess.run("powershell pnputil /enum-drivers", shell=True, capture_output=True, text=True)
        ndis_driver_name = ''.join(re.findall(r'(oem.*?inf)\n.*?qcwwan', s.stdout))
        if ndis_driver_name:
            all_logger.info('卸载NDIS驱动')
            all_logger.info('ndis_driver_name:{}'.format(ndis_driver_name))
            s = subprocess.run('powershell pnputil /delete-driver {} /force'.format(ndis_driver_name), shell=True, capture_output=True, text=True)
            all_logger.info(s)


class PINGThread(Thread):

    """
    PING线程，用于检查网络的同时进行其他业务例如打电话，发短信
    """

    def __init__(self, ipv6_flag=False, times=10, flag=False):
        """
        :param ipv6_flag: 是否PingIPV6地址
        :param times: ping时长
        :param flag: 是否指定IP地址进行ping操作
        """
        super().__init__()
        self.ctrl_c_flag = False
        self.terminate_flag = False
        self.ipv6_flag = ipv6_flag
        self.times = times
        self.flag = flag
        self.ping_cache = ''

    def ctrl_c(self):
        self.ctrl_c_flag = True
        time.sleep(3)

    def terminate(self):
        self.terminate_flag = True

    def run(self):
        ping_command = ''
        start_timestamp = time.time()
        if self.flag:
            for i in range(10):
                ipconfig_value = os.popen('ipconfig').read().replace('\n', '')
                mobile_info = ''.join(re.findall(r'手机网络.*子网掩码', ipconfig_value)).replace('   ', '\n').strip()
                ip_add = ''.join(re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', mobile_info))
                if not ip_add:
                    time.sleep(2)
                    continue
                all_logger.info(ipconfig_value)
                ping_command = "ping -S {} -n {} www.baidu.com".format(ip_add, self.times)
                break
        else:
            ping_command = "ping -n {} www.baidu.com".format(self.times)
        ping_command = ping_command.split(' ')
        all_logger.info(ping_command)

        async def ping():
            all_logger.info('进行ping业务')
            s = await asyncio.create_subprocess_exec(*ping_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            while True:
                line = b''
                try:
                    line = await asyncio.wait_for(s.stdout.readline(), 0.1)
                except asyncio.TimeoutError:
                    pass
                finally:
                    if line:
                        self.ping_cache += line.decode('gbk', 'ignore')
                        all_logger.info("[PING] {}".format(line.decode('gbk', 'ignore').strip()))
                    if self.ctrl_c_flag:  # safety terminate application with ctrl c when APP have teardown action
                        ctrl_c = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT
                        all_logger.info("[PING] {}".format(repr(line.decode('gbk', 'ignore').strip())))
                        if s.returncode is None:
                            s.send_signal(ctrl_c)
                        self.ctrl_c_flag = False
                    if self.terminate_flag:
                        if s.returncode is None:
                            s.terminate()
                        await s.wait()
                        return True
                    if time.time() - start_timestamp > self.times:
                        auto_terminate_time = time.time()
                        while time.time() - auto_terminate_time < 3:
                            try:
                                line = await asyncio.wait_for(s.stdout.readline(), 0.1)
                                if line:
                                    self.ping_cache += line.decode('gbk', 'ignore')
                                    all_logger.info("[PING] {}".format(line.decode('gbk', 'ignore')).strip())
                            except asyncio.TimeoutError:
                                pass
                        if s.returncode is None:
                            s.terminate()
                        await s.wait()
                        return True

        loop = asyncio.new_event_loop()  # in thread must creat new event loop.
        asyncio.set_event_loop(loop)
        tasks = [ping()]
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()
