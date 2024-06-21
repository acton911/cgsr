import os
import random
import re
import subprocess
import sys
import time
from collections import deque
from functools import partial
from threading import Thread
from ..logger.logging_handles import all_logger
from ..functions.decorators import watchdog
from utils.exception.exceptions import IPerfError
import traceback

"""
class IPerfError(ExitCode1):
"""

watchdog = partial(watchdog, logging_handle=all_logger, exception_type=IPerfError)


class IPerfServer(Thread):

    ansi_color_regex = r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]'  # based on https://stackoverflow.com/a/38662876

    def __init__(self, ip, user, passwd, ssh_port, linux):
        super().__init__()
        self.ip = ip
        self.user = user
        self.passwd = passwd
        self.ssh_port = ssh_port
        self.linux = linux
        self.client = None
        self.port = None
        self.iperf_success_flag = False
        self.shutdown_flag = False
        self.error_info = ''
        self.port_range = (29000, 29999)
        self.dq_stdout = deque(maxlen=10)
        self.start()
        self.wait_iperf_init()

        # if iperf server not success
        if self.error_info:
            raise IPerfError(self.error_info)
        if not self.iperf_success_flag:
            raise IPerfError("10S内未检测到Server listening on {}".format(self.port))

        all_logger.info("start iperf server success")

    def run(self):
        try:
            self.connect_to_server()
            self.get_port()
            self.open_iperf3_server()
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            all_logger.error(traceback.format_exc())
            all_logger.error(e)
            self.error_info = "\n\niPerf3 Exception：\nexc_type: {}\nexc_value: {}\nexc_traceback: {}\n".format(
                exc_type,
                exc_value,
                exc_traceback
            )

    def shutdown(self):
        self.client.close()

    def wait_iperf_init(self, timeout=10):
        target_time = time.perf_counter() + timeout
        while time.perf_counter() < target_time:
            if self.iperf_success_flag or self.error_info:  # if success or have error info
                break
            time.sleep(0.001)

    def connect_to_server(self):
        import paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(hostname=self.ip, username=self.user, password=self.passwd, port=self.ssh_port, timeout=8)

    def get_port(self):
        # get TCP and UDP port use random
        self.port = random.randint(*self.port_range)  # USE HIGH LEVEL PORT
        _, stdout, _ = self.client.exec_command('netstat -an | {} "{}"'.format('findstr' if os.name == 'nt' else 'grep', self.port))
        # port exists?
        while True:
            time.sleep(0.001)
            if stdout.channel.exit_status_ready():
                data = stdout.channel.recv(1024).decode("GBK", "ignore")
                all_logger.info(data)
                if not data:  # not exist
                    all_logger.info("current port: {}".format(self.port))
                    break
                else:  # if port already use, use random get another port
                    self.port = random.randint(*self.port_range)  # USE HIGH LEVEL PORT
                    _, stdout, _ = self.client.exec_command('netstat -an | {} "{}"'.format('findstr' if os.name == 'nt' else 'grep', self.port))

    def open_iperf3_server(self):
        # exec command open iperf server
        if not self.linux:
            stdin, stdout, stderr = self.client.exec_command('{} -s -p {} -1'.format('iperf3.9', self.port), get_pty=True)
        else:
            stdin, stdout, stderr = self.client.exec_command('{} -s -p {} -1'.format('iperf3', self.port), get_pty=True)

        # if iperf3 not exit or stdout or stderr has output
        while not stdout.channel.exit_status_ready() or stdout.channel.recv_ready() or stderr.channel.recv_stderr_ready():
            # decline CPU usage
            time.sleep(0.001)

            # stdout
            if stdout.channel.recv_ready():
                data = re.sub(self.ansi_color_regex, '', stdout.channel.recv(1024).decode('GBK', 'ignore'))
                all_logger.info('stdout: {}'.format(data))
                self.dq_stdout.append(data)
                if "listening on {}".format(self.port) in ''.join(self.dq_stdout):
                    self.iperf_success_flag = True

            # stderr
            if stderr.channel.recv_stderr_ready():
                data = re.sub(self.ansi_color_regex, '', stderr.channel.recv(1024).decode('GBK', 'ignore'))
                all_logger.info('stderr: {}'.format(data))


def iperf(ip="112.31.84.164", user='Q', passwd='st', port=19999, mode=3, times=100, bandwidth='10M', interval=None, bind=None, parallel=None, length=None, window=None, mtu=None, omit=None, linux=False):
    """
    iPerf3.9 wrapper.
    :param ip: iPerf3.9 server ip
    :param user: iPerf3.9 server ssh user
    :param passwd: iPerf3.9 server ssh passwd
    :param port: iPerf3.9 server ssh port
    :param mode:  1：TCP发送; 2：TCP接收; 3：TCP上下同传; 4: UDP发送; 5: UDP接收; 6: UDP上下同传
    :param times: 运行的时间，默认是10S
    :param bandwidth: 带宽，例如10M代表10Mbits/s
    :param interval: log每次返回的间隔，默认1S一次log
    :param bind: 是否绑定网卡，如果需要绑定，则输入对应网卡的IP
    :param parallel: 使用的线程数，默认为1
    :param length: The length of buffers to read or write. default 128 KB for TCP, dynamic or 1460 for UDP
    :param window: TCP/UDP window size
    :param mtu: The MTU(maximum segment size) - 40 bytes for the header. ethernet MSS is 1460 bytes (1500 byte MTU).
    :param omit: omit n, skip n seconds
    :param linux: 服务器为linux
    :return: None
    """
    # TODO: 优化iperf判断，优化iperf数据展示方式
    for i in range(10):
        try:
            iperf_server = IPerfServer(ip, user, passwd, port, linux)
            break
        except Exception as e:
            all_logger.error('iPerf服务开启异常：{}，正在重试'.format(e))
            time.sleep(1)
    else:
        raise IPerfError("连续十次iPerf服务器开启异常，请联系Flynn或Cris定位问题")

    transmit_mode_mapping = {
        1: [],  # TCP上传，本地Server，远端Client
        2: ['-R'],  # TCP下载，本地client，远端Server
        3: ['--bidir'],  # TCP上下同传
        4: ['-u'],  # UDP上传，本地Server，远端Client
        5: ['-u', '-R'],  # UDP下载，本地client，远端Server
        6: ['-u', '--bidir']  # UDP上传同传
    }
    iperf_cmd = ['iperf3',
                 '-c', ip,
                 '-p', str(iperf_server.port),
                 '-f', 'm',
                 '-t', str(times),
                 '--forceflush',
                 ]

    iperf_cmd.extend(transmit_mode_mapping[mode])

    iperf_cmd_tail = []
    if interval:
        iperf_cmd_tail.extend(['-i', str(interval)])
    if bandwidth:
        iperf_cmd_tail.extend(['-b', str(bandwidth)])
    if bind:  # 绑定本机的IP，使用某个IP进行数据传输
        iperf_cmd_tail.extend(['-B', str(bind)])
    if parallel:  # 并行线程数
        iperf_cmd_tail.extend(['-P', str(parallel)])
    if length:  # The length of buffers to read or write. default 128 KB for TCP, dynamic or 1460 for UDP
        iperf_cmd_tail.extend(['-l', str(length)])
    if window:  # window
        iperf_cmd_tail.extend(['-w', str(window)])
    if mtu:  # TCP: maximum segment sizeThe MTU - 40 bytes for the header. ethernet MSS is 1460 bytes (1500 byte MTU).
        iperf_cmd_tail.extend(['-M', str(mtu)])
    if omit:  # omit n, skip n seconds
        iperf_cmd_tail.extend(['-O', str(omit)])

    iperf_cmd.extend(iperf_cmd_tail)

    all_logger.info('[iperf3 cmd] {}'.format(' '.join(iperf_cmd)))

    s = subprocess.Popen(iperf_cmd,
                         shell=True if os.name == 'nt' else False,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         text=True,
                         errors='ignore'
                         )

    speed_abnormal_times = 0
    result_cache = ''
    network_error_flag = False

    while s.poll() is None:
        data = s.stdout.readline().replace('\n', '')
        all_logger.info('[iPerf3] {}'.format(data)) if data else None
        if '0.00 Mbits/sec' in data and 'sender' not in data and 'receiver' not in data:
            all_logger.error('[iPerf3] 出现断流: {}'.format(data))
            network_error_flag = True
        speed_abnormal_times += 1 if '0.00 Mbits/sec' in data and 'sender' not in data and 'receiver' not in data else 0
        result_cache += data if 'sender' in data or 'receiver' in data else ''
        if 'iperf3' in data:
            break

    iperf_server.shutdown()  # shutdown iperf3 service

    if s.returncode != 0:  # 如果异常，不进行参数统计
        raise IPerfError("IPERF测速出现异常，请检查log")

    if network_error_flag:
        raise IPerfError("iPerf测速出现断流，请检查log")


if __name__ == '__main__':
    iperf()
