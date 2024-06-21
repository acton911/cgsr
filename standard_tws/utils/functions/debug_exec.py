import re
import time
from utils.logger.logging_handles import all_logger
import serial
from threading import Thread
from utils.functions.getpassword import getpass
from collections import deque
import traceback
import subprocess
import os


class DebugPort(Thread):

    def __init__(self, debug_port):
        super().__init__()
        self.openssl_test()
        if os.name == 'nt':
            try:
                # 尝试打开串口
                self.debug_port = serial.Serial(debug_port, baudrate=115200, timeout=0.8)
            except serial.serialutil.SerialException as e:
                # 打印异常
                all_logger.error(traceback.format_exc())
                all_logger.error(e)
                # 禁用启用串口
                from utils.functions.windows_api import WindowsAPI
                win_api = WindowsAPI()
                win_api.enable_disable_com_port(True, debug_port)
                win_api.enable_disable_com_port(False, debug_port)
                win_api.enable_disable_com_port(True, debug_port, silicon=True)
                win_api.enable_disable_com_port(False, debug_port, silicon=True)
                del win_api
                # 打开串口
                self.debug_port = serial.Serial(debug_port, baudrate=115200, timeout=0.8)
        else:
            self.debug_port = serial.Serial(debug_port, baudrate=115200, timeout=0.8)
        self.debug_port.write('\r\n'.encode('utf-8'))
        self.debug_open_flag = True
        self.debug_read_flag = True
        self.dq = deque(maxlen=100)

    @staticmethod
    def openssl_test():
        """
        check if openssl exists, if not exist, raise FileNotFoundError.
        :return: None
        """
        subprocess.run(["openssl", "help"])

    def readline(self, port):
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
                        all_logger.info("DEBUG {} {}".format("RECV", repr(buf).replace("'", '')))
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > 1:
                        all_logger.info('{}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            all_logger.error('Fatal ERROR: {}'.format(error))
        finally:
            if buf:
                self.dq.append(buf)
            return buf

    def run(self):
        """
        自动登录debug port
        :return:
        """
        qid = ''
        while True:
            time.sleep(0.001)
            if self.debug_read_flag:
                res = self.readline(self.debug_port)
                if 'login:' in res:
                    self.debug_port.write('root\r\n'.encode('utf-8'))
                if 'quectel-ID' in res:
                    qid = ''.join(re.findall(r'quectel-ID : (\d+)', res))
                if 'Password:' in res:
                    passwd = getpass(qid)
                    self.debug_port.write('{}\r\n'.format(passwd).encode('utf-8'))
                if not self.debug_open_flag:
                    break

    def exec_command(self, cmd, timeout=1):
        """
        在debug口执行命令
        :param cmd: 需要执行的命令
        :param timeout: 检查命令的超时时间
        :return: None
        """
        self.debug_read_flag = False
        self.debug_port.write('{}\r\n'.format(cmd).encode('utf-8'))
        cache = ''
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.001)
            res = self.readline(self.debug_port)
            if res:
                cache += res
        self.debug_read_flag = True
        return cache

    def close_debug(self):
        """
        关闭DEBUG口，结束线程
        :return: None
        """
        all_logger.info('close_debug')
        # 取消读
        self.debug_read_flag = False
        time.sleep(0.1)
        # 关闭口并退出线程
        all_logger.info(self.debug_port)
        self.debug_port.close()
        all_logger.info(self.debug_port)
        all_logger.info("debug port is closed")
        self.debug_open_flag = False

    def ctrl_c(self):
        self.debug_port.write("\x03".encode())

    def get_latest_data(self, depth=10):
        return ''.join(list(self.dq)[-depth:])
