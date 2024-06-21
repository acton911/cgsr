import random
import re
from functools import partial
import serial
from utils.exception.exceptions import UARTError
from utils.logger.logging_handles import all_logger, at_logger
import time
from utils.functions.decorators import watchdog


watchdog = partial(watchdog, logging_handle=all_logger, exception_type=UARTError)


class UARTHandle:
    def __init__(self, uart_port):
        super().__init__()
        self.uart_port = uart_port
        self.run()
        self.PORT_CACHE = ''

    def run(self):
        try:
            self.uart_port = serial.Serial(self.uart_port, baudrate=115200, timeout=0)
        except serial.serialutil.SerialException:
            raise UARTError('UART端口:{}被占用或端口设置错误，请检查端口是否填写正确并重新运行'.format(self.uart_port))
        self.uart_port.setDTR(False)
        self.uart_port.setRTS(False)

    def set_dtr_true(self):
        time.sleep(1)
        self.uart_port.setDTR(True)
        all_logger.info('dtr: {}'.format(self.uart_port.dtr))

    def set_dtr_false(self):
        time.sleep(1)
        self.uart_port.setDTR(False)
        all_logger.info('dtr: {}'.format(self.uart_port.dtr))

    def set_rts_true(self):
        time.sleep(1)
        self.uart_port.setRTS(True)
        all_logger.info('rts: {}'.format(self.uart_port.rts))

    def set_rts_false(self):
        time.sleep(1)
        self.uart_port.setRTS(False)
        all_logger.info('rts: {}'.format(self.uart_port.rts))

    def readline(self, port):
        """
        拼接此类不在一行的log。
        [2020-09-01 10:20:23.593831] '         Starting Create Volatile Files a'
        [2020-09-01 10:20:23.607004] 'nd Directories...\r\n'
        :param port: 需要读取的端口
        :return: '':此次readline方法读取的不是以\n结尾；all_return_value：此次读取log以\n结尾
        """
        return_value = port.readline().decode('utf-8', 'ignore')
        if return_value != '':  # 如果不为空，和PORT_CACHE拼接
            self.PORT_CACHE += return_value
        if return_value.endswith('\n') is False:  # 不以\n结尾，直接返回空串
            return ''
        else:  # 以\n结尾，赋值PORT_CACHE给all_return_value，然后清空PORT_CACHE后返回读取到的所有值
            all_return_value = self.PORT_CACHE
            all_return_value = re.sub(r'\x1b\[.*?m', '', all_return_value)  # 替换ANSI COLOR
            self.PORT_CACHE = ''
            all_logger.info(repr(all_return_value))
            return all_return_value

    @watchdog("检测DFOTA差分包加载")
    def dfota_step_2(self, stop_download=False, start=False):
        """
        发送at+qfotadl指令关机并开机后的log检查：
        检测+QIND: "FOTA","START" 到 +QIND: "FOTA","END",0
        :return: None
        """

        start_urc_flag = False
        start_time = time.time()
        try:
            # 检查 FTPSTART / HTTPSTART，如果检测到UPDATING，则没有检测到，为了保证可以断电等操作，直接跳出
            while time.time() - start_time < 300:
                time.sleep(0.001)
                recv = self.readline(self.uart_port)
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
                raise UARTError('DFOTA升级过程异常：检测{} +QIND: "FOTA","START"失败')
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
                recv = self.readline(self.uart_port)
                recv_regex = ''.join(re.findall(r'\+QIND:\s"FOTA","END",(\d+)', recv))
                if recv_regex:
                    if recv_regex == '0':
                        at_logger.info("已经检测到{}，升级成功".format(repr(recv)))
                        return True
                    else:
                        at_logger.error("DFOTA升级异常异常：{}".format(recv))
                        return False
                if time.time() - start_time > 300:
                    raise UARTError("DFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise UARTError('未检测到DFOTA上报+QIND: "FOTA","START"')

    @watchdog("检查DFOTA END 0")
    def dfota_end_0(self):
        updating_urc_flag = False
        start_urc_flag = False
        try:
            # 检查 FTPSTART / HTTPSTART，如果检测到UPDATING，则没有检测到，为了保证可以断电等操作，直接跳出
            while True:
                time.sleep(0.001)
                recv = self.readline(self.uart_port)
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
                recv = self.readline(self.uart_port)
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
                    raise UARTError("DFOTA下载差分包超过300S异常")
        finally:
            if start_urc_flag is False:
                raise UARTError('未检测到DFOTA上报+QIND: "FOTA","START"')
            if updating_urc_flag:
                raise UARTError("FOTA END 0断电检测到UPDATING URC")
