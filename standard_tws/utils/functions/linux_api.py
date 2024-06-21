from functools import partial
from ..logger.logging_handles import all_logger
from ..functions.decorators import watchdog
from ..exception.exceptions import LinuxAPIError
import subprocess
import time
import asyncio
import os
from threading import Thread
import signal
import re
from collections import deque
import psutil
from icmplib import multiping
from icmplib import ping
from requests_toolbelt.adapters import source
import requests

watchdog = partial(watchdog, logging_handle=all_logger, exception_type=LinuxAPIError)


class LinuxAPI:

    @staticmethod
    def get_port():
        """
        !仅支持一个电脑上一个设备。
        通过udevadm映射AT口为ttyUSBAT，DM口为ttyUSBDM。
        :return: AT口
        """
        subprocess.run("""echo 'SUBSYSTEMS=="usb",DRIVERS=="option",ATTRS{bInterfaceClass}=="ff",ATTRS{bInterfaceNumber}=="02",SYMLINK+="ttyUSBAT"' > /etc/udev/rules.d/99-usb-serial.rules""", shell=True)
        subprocess.run("""echo 'SUBSYSTEMS=="usb",DRIVERS=="option",ATTRS{bInterfaceClass}=="ff",ATTRS{bInterfaceNumber}=="03",SYMLINK+="ttyUSBDM"' >> /etc/udev/rules.d/99-usb-serial.rules""", shell=True)
        time.sleep(0.1)
        subprocess.run("udevadm control --reload", shell=True)
        subprocess.run("udevadm trigger", shell=True)
        for _ in range(10):
            time.sleep(1)
            s_at = subprocess.run("ls -l /dev | grep ttyUSBAT", capture_output=True, shell=True, text=True)
            s_dm = subprocess.run("ls -l /dev | grep ttyUSBDM", capture_output=True, shell=True, text=True)
            if s_at.stdout and s_dm.stdout:
                return '/dev/ttyUSBAT', '/dev/ttyUSBDM'
        else:
            raise LinuxAPIError("自动获取端口失败")

    @staticmethod
    def get_ip_address(network_card_name, ipv6_flag):
        """
        获取IP地址
        """
        for i in range(30):
            all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
            all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name, 'inet6' if ipv6_flag else 'inet'))
            ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
            if ip and 'error' not in ip:
                all_logger.info('IP: {}'.format(ip))
                return ip
            time.sleep(1)
        else:
            all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            all_logger.info(os.popen('ifconfig').read())
            return False

    @staticmethod
    @watchdog("进行PING连接测试")
    def ping_get_connect_status(ipv6_flag=False, network_card_name="wwan0", times=20, flag=True):
        ip = LinuxAPI.get_ip_address(network_card_name, ipv6_flag)
        all_logger.info(f"DNS: {subprocess.getoutput('cat /etc/resolv.conf')}")
        if not flag:
            ping('www.baidu.com', count=times, interval=1, source=ip)
            time.sleep(1)
        else:
            if not ipv6_flag:
                target_ip_list = ['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8']
                for i in range(4):
                    try:
                        ping_data = ping(target_ip_list[i], count=times, interval=1, source=ip)
                        all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                        if ping_data.is_alive:
                            all_logger.info('ping检查正常')
                            return True
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info(f'ping地址{target_ip_list[i]}失败')
                        continue
                else:
                    try:
                        all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                        ip = LinuxAPI.get_ip_address(network_card_name, ipv6_flag)
                        ping_datas = multiping(['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8'], count=times, interval=1, source=ip)
                        for ping_data in ping_datas:
                            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                            if ping_data.is_alive:
                                all_logger.info('重新获取IP后ping检查正常')
                                return True
                        else:
                            raise LinuxAPIError('重新获取IP后ping检查异常')
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info('ping检查异常，发送request请求检查网络是否正常')
                        s = requests.Session()
                        new_source = source.SourceAddressAdapter(ip)   # 指定网卡信息
                        s.mount('http://', new_source)
                        s.mount('https://', new_source)
                        s.trust_env = False   # 禁用系统的环境变量，在系统设置有代理的时候可用用此选项禁止请求使用代理
                        response = s.get(url='http://www.baidu.com')
                        response_1 = s.get(url='http://www.sina.com')
                        if response.status_code == 200 or response_1.status_code == 200:
                            all_logger.info('拨号后request请求正常')
                            return True
                        else:
                            all_logger.info('拨号后request请求失败')
                            raise LinuxAPIError('拨号后ping检查异常，request请求异常')
            elif ipv6_flag:
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times, interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return True
                else:
                    all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                    ip = LinuxAPI.get_ip_address(network_card_name, ipv6_flag)
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times, interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return True
                else:
                    all_logger.info('ping ipv6检查异常')
                    raise LinuxAPIError('ping ipv6检查异常')

    @staticmethod
    @watchdog("进行内网连接测试")
    def check_intranet(local_network_card_name, intranet_url='https://stgit.quectel.com'):

        def get_dns_status():
            # 判断DNS是否正常
            for i in range(30):
                resolv_conf = subprocess.getoutput('cat /etc/resolv.conf')  # 获取ubuntu dns
                all_logger.info(f"resolve.conf: {resolv_conf}")
                dns = re.findall(r"nameserver\s(.*)", resolv_conf)  # 匹配dns
                if dns:  # 如果获取到了DNS
                    all_logger.error(f"DNS: {dns}")
                    break
                time.sleep(1)  # 如果没有DNS，等待1s
            else:
                all_logger.error("DNS获取异常, 未获取到正确的DNS地址")
                return False

            for i in range(100):
                ping_data = multiping(dns, count=1, timeout=1)
                for data in ping_data:
                    if data.packets_received == 1:
                        return True
            else:
                all_logger.error("连续100次Ping DNS服务IP异常")

        all_logger.info('开始检查内网连接')
        for num in range(10):
            # requests获取stgit.quectel.com状态
            status_code = 0
            try:
                r = requests.get(intranet_url, timeout=1)  # 请求stgit.quectel.com，超时时间3S
                status_code = r.status_code
            except requests.exceptions.RequestException as e:
                all_logger.error(f"连接stgit.quectel.com异常：{e}")

            # 判断状态
            if status_code == 200:
                all_logger.info('the intranet connect successfully!')
                return True  # 正常退出
            else:
                all_logger.info("连接{}失败".format(intranet_url))
                # 查询当前DNS配置
                resolv = subprocess.getoutput('cat /etc/resolv.conf')
                all_logger.info('cat /etc/resolv.conf\r\n{}'.format(resolv))
                # 查询各个网络ip状态
                ifconfig = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig))
                # killall quectel-CM
                qcm = subprocess.getoutput('killall quectel-CM')
                all_logger.info('killall quectel-CM\r\n{}'.format(qcm))
                # 重新禁用启用本地网
                if_down = subprocess.getoutput('ifconfig {} down'.format(local_network_card_name))
                all_logger.info('ifconfig {} down\r\n{}'.format(local_network_card_name, if_down))
                all_logger.info("等待3S")
                time.sleep(3)
                if_up = subprocess.getoutput('ifconfig {} up'.format(local_network_card_name))
                all_logger.info('ifconfig {} up\r\n{}'.format(local_network_card_name, if_up))
                # 重新配置DNS、获取ip
                udhcpc_value = subprocess.getoutput('udhcpc -i {}'.format(local_network_card_name))
                all_logger.info('udhcpc -i {}\r\n{}'.format(local_network_card_name, udhcpc_value))
                # 等待判断DNS是否正常
                get_dns_status()
        else:
            raise LinuxAPIError('尝试10次连接内网失败，请检查设备连接和配置情况是否正确!')


class QuectelCMThread(Thread):

    """
    quectel-CM后台拨号，用于拨号后检查网络情况。
    """

    def __init__(self, cmd='quectel-CM', netcard_name='wwan0'):
        super().__init__()
        self.ctrl_c_flag = False
        self.terminate_flag = False
        self.cmd = cmd
        self.netcard_name = netcard_name

    def run(self):
        async def quectel_cm():
            input_cmd = self.cmd.split(' ')
            s = await asyncio.create_subprocess_exec(*input_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            while True:
                line = b''
                try:
                    line = await asyncio.wait_for(s.stdout.readline(), 0.1)
                except asyncio.TimeoutError:
                    pass
                finally:
                    if line:
                        all_logger.info("[quectel-CM] {}".format(line.decode('utf-8', 'ignore')))
                        if 'No route items found' in line.decode("UTF-8") or 'Network is unreachable' in line.decode("UTF-8"):
                            all_logger.error(f'{self.netcard_name} No route items found')
                            all_logger.info(f'reset {self.netcard_name} netcard')
                            time.sleep(2)
                            return_value5 = subprocess.getoutput(f'udhcpc -i {self.netcard_name}')
                            all_logger.info('udhcpc -i {}\r\n{}'.format(self.netcard_name, return_value5))
                    if self.ctrl_c_flag:  # safety terminate application with ctrl c when APP have teardown action
                        ctrl_c = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT
                        all_logger.info("[quectel-CM] {}".format(repr(line.decode('utf-8', 'ignore'))))
                        if s.returncode is None:
                            s.send_signal(ctrl_c)
                        self.ctrl_c_flag = False
                    if self.terminate_flag:
                        if s.returncode is None:
                            s.terminate()
                        await s.wait()
                        return True

        loop = asyncio.new_event_loop()  # in thread must creat new event loop.
        asyncio.set_event_loop(loop)
        tasks = [quectel_cm()]
        loop.run_until_complete(asyncio.wait(tasks))
        loop.close()

    def ctrl_c(self, flag=False):
        self.ctrl_c_flag = True
        if flag:
            return True
        time.sleep(3)

    def terminate(self):
        self.terminate_flag = True


class PINGThread(Thread):

    """
    PING线程，用于检查网络的同时进行其他业务例如打电话，发短信
    """

    def __init__(self, ipv6_flag=False, network_card_name="wwan0", times=10):
        super().__init__()
        self.ctrl_c_flag = False
        self.terminate_flag = False
        self.ipv6_flag = ipv6_flag
        self.network_card_name = network_card_name
        self.times = times
        self.ping_cache = ''

    def ctrl_c(self):
        self.ctrl_c_flag = True
        time.sleep(3)

    def terminate(self):
        self.terminate_flag = True

    @watchdog("获取PING结果")
    def get_result(self):
        ping_status = re.findall(r'(\d+)\s.*?(\d+)\s.*?,\s(\d+)', self.ping_cache)
        if ping_status:
            transmitted, received, packet_loss_percent = ping_status.pop()
            if packet_loss_percent != '0':
                all_logger.info("PING异常, 发送:{}, 接收:{}, 丢包率{}%".format(transmitted, received, packet_loss_percent))
                return False
            else:
                all_logger.info("PING检查正常")
                return True
        else:
            all_logger.info(subprocess.getoutput(f"ping 8.8.8.8 -c 4 -I {self.network_card_name}"))
            all_logger.info(subprocess.getoutput(f"ping 114.114.114.114 -c 4 -I {self.network_card_name}"))
            all_logger.info("PING异常: {}".format(self.ping_cache))
            return False

    @watchdog("获取无网络PING结果")
    def non_network_get_result(self):
        ping_status = re.findall(r'(\d+)\s.*?(\d+)\s.*?,\s(\d+)', self.ping_cache)
        if ping_status:
            transmitted, received, packet_loss_percent = ping_status.pop()
            if packet_loss_percent != '100':
                all_logger.info("PING异常, 发送:{}, 接收:{}, 丢包率{}%".format(transmitted, received, packet_loss_percent))
                return False
            else:
                all_logger.info("PING检查确认无网络")
                return True
        else:
            all_logger.info("PING检查确认无网络")
            return True

    def run(self):
        version_flag = True     # True:Ubuntu_18.04
        version = subprocess.run('ping', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if '-6' not in version.stdout:
            version_flag = False    # Flase:Ubuntu_16.04
        else:
            all_logger.info(version.stdout)
        start_timestamp = time.time()
        ping_command = "ping {} -I {} -c {} ipv6.tsinghua.edu.cn".format('-6' if version_flag else '', self.network_card_name, self.times) if self.ipv6_flag else \
                       "ping {} -I {} -c {} www.baidu.com".format('-4' if version_flag else '', self.network_card_name, self.times)
        all_logger.info(ping_command)

        async def ping():
            s = await asyncio.create_subprocess_shell(ping_command, stdout=asyncio.subprocess.PIPE,
                                                      stderr=asyncio.subprocess.STDOUT)
            while True:
                line = b''
                try:
                    line = await asyncio.wait_for(s.stdout.readline(), 0.1)
                except asyncio.TimeoutError:
                    pass
                finally:
                    if line:
                        self.ping_cache += line.decode('utf-8', 'ignore')
                        all_logger.info("[PING] {}".format(line.decode('utf-8', 'ignore')))
                    if self.ctrl_c_flag:  # safety terminate application with ctrl c when APP have teardown action
                        ctrl_c = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT
                        all_logger.info("[PING] {}".format(repr(line.decode('utf-8', 'ignore'))))
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
                        ctrl_c = signal.CTRL_C_EVENT if os.name == 'nt' else signal.SIGINT  # pylint: disable=E1101
                        if s.returncode is None:
                            s.send_signal(ctrl_c)
                        while time.time() - auto_terminate_time < 3:
                            try:
                                line = await asyncio.wait_for(s.stdout.readline(), 0.1)
                                if line:
                                    self.ping_cache += line.decode('utf-8', 'ignore')
                                    all_logger.info("[PING] {}".format(line.decode('utf-8', 'ignore')))
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


class FFMPEGThread(Thread):

    """
    用于检查网络直播观看是否正常
    """

    def __init__(self, network_card_name='wwan0', ban_network_card_name="eth0", network_standard=100, check_times=10, m3u8="http://117.169.120.140:8080/live/cctv-13/.m3u8"):
        super().__init__()
        self.dq = deque(maxlen=10)  # 存放最近10s的速度，如果平均值小于network_standard，则异常
        self.m3u8 = m3u8  # m3u8视频地址
        self.network_card_name = network_card_name  # 网卡名称，用于psutil指定网卡获取网卡数据量
        self.check_times = check_times  # 检查的总时间
        self.s = None  # ffmpeg的subprocess实例
        self.error_flag = False  # 标志位，如果异常则flag为True
        self.network_standard = network_standard  # 网络标准速度，KB/s
        self.ban_network_card_name = ban_network_card_name  # 运行ffmpeg之前需要禁止的网卡，防止ffmpeg使用非network_card_name的网络
        self.eth_connection_name = self.get_eth_connection_name(self.ban_network_card_name)
        all_logger.info("self.eth_connection_name: {}".format(self.eth_connection_name))

    def run(self):
        start_time = time.time()

        # 拼接视频路径
        video_path = os.path.join(os.getcwd(), 'test.mp4')
        if os.path.exists(video_path):
            os.remove(video_path)

        if self.ban_network_card_name:
            all_logger.info("nmcli con down id '{}'".format(self.eth_connection_name))
            p = subprocess.run("nmcli con down id '{}'".format(self.eth_connection_name), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
            all_logger.info(p.stdout)
        time.sleep(3)

        # 拼接ffmpeg下载m3u8在线视频命令行
        command = ['ffmpeg', '-i', self.m3u8, video_path]

        # 运行ffmpeg
        self.s = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        while True:
            data_before = 0
            data_after = 0

            # 获取1s的数据量
            network_card_status = psutil.net_io_counters(pernic=True).get(self.network_card_name)
            if network_card_status:
                data_before = network_card_status.bytes_recv
            time.sleep(1)
            network_card_status = psutil.net_io_counters(pernic=True).get(self.network_card_name)
            if network_card_status:
                data_after = network_card_status.bytes_recv

            # 计算速率
            kb_per_second = int((data_after - data_before) / 1024)
            all_logger.info("网卡:{}, ffmpeg当前速率{}KB/s".format(self.network_card_name, kb_per_second))

            # 将每秒的数据量放入deque
            self.dq.append(kb_per_second)

            # 计算当前的速率
            if len(self.dq) >= self.dq.maxlen / 2 and sum(self.dq) / len(self.dq) < self.network_standard:
                all_logger.info("网卡:{}, ffmpeg速率检查异常，{}".format(self.network_card_name, self.dq))
                self.error_flag = True
                if self.s.returncode is None:
                    self.s.kill()  # kill ffmpeg
                    self.s.wait()
                if self.ban_network_card_name:
                    all_logger.info("nmcli con up id '{}'".format(self.eth_connection_name))
                    p = subprocess.run("nmcli con up id '{}'".format(self.eth_connection_name), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                    all_logger.info(p.stdout)
                    time.sleep(20)
                break

            # 超过检查时间
            if (time.time() - start_time) > self.check_times:
                if self.s.returncode is None:
                    self.s.kill()  # kill ffmpeg
                    self.s.wait()
                if self.ban_network_card_name:
                    all_logger.info("nmcli con up id '{}'".format(self.eth_connection_name))
                    p = subprocess.run("nmcli con up id '{}'".format(self.eth_connection_name), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
                    all_logger.info(p.stdout)
                    time.sleep(20)
                break

    def get_eth_connection_name(self, network_card_name):
        all_logger.info("nmcli -t c | grep {} | cut -d : -f 1 | tr -s ' ' | head -c -1".format(network_card_name))
        eth_name = os.popen("nmcli -t c | grep {} | cut -d : -f 1 | tr -s ' ' | head -c -1".format(network_card_name)).read()
        all_logger.info(eth_name)
        all_logger.info(os.popen('nmcli -t d').read())
        return eth_name

    @watchdog("检查观看直播时网络情况")
    def get_result(self):
        if self.error_flag:
            all_logger.info("观看直播网络异常")
            return False
        else:
            all_logger.info("观看直播网络正常")
            return True


def disable_network_card(network_card_name):
    for i in range(3):
        all_logger.info('ifconfig {} down'.format(network_card_name))
        s = subprocess.getstatusoutput('ifconfig {} down'.format(network_card_name))
        all_logger.info(s)
        time.sleep(1)
        s = subprocess.getoutput('ifconfig')
        all_logger.info(s)
        if network_card_name not in s:
            break
        else:
            all_logger.info(s)


def enable_network_card(network_card_name):
    for i in range(3):
        all_logger.info('ifconfig {} up'.format(network_card_name))
        s = subprocess.getoutput('ifconfig {} up'.format(network_card_name))
        all_logger.info(s)
        time.sleep(1)
        s = subprocess.getoutput('ifconfig')
        if network_card_name in s:
            break
        else:
            all_logger.info(s)


def enable_network_card_and_check(network_card_name):
    all_logger.info('ifconfig {} up'.format(network_card_name))
    s = subprocess.getoutput('ifconfig {} up'.format(network_card_name))
    all_logger.info(s)

    LinuxAPI().check_intranet(network_card_name)
