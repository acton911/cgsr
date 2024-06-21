# -*- encoding=utf-8 -*-
from threading import Thread, Event
import datetime
import serial
import time
import os
import re
import serial.tools.list_ports
import logging
from functions import pause
import glob


class URCError(Exception):
    pass


class ATThread(Thread):
    def __init__(self, at_port, dm_port, at_queue, main_queue, log_queue):
        super().__init__()
        self.at_port = at_port.upper() if os.name == 'nt' else at_port  # win平台转换为大写便于后续判断
        self.dm_port = dm_port.upper() if os.name == 'nt' else dm_port  # win平台转换为大写便于后续判断
        self.at_queue = at_queue
        self.main_queue = main_queue
        self.log_queue = log_queue
        self.at_port_opened = type(serial)  # 初始化AT口
        self.at_port_opened_flag = False  # AT口打开时为True，串口读取URC；AT口关闭的时候为False，不再读取URC
        self._methods_list = [x for x, y in self.__class__.__dict__.items()]
        self.logger = logging.getLogger(__name__)

    def run(self):
        while True:
            time.sleep(0.001)  # 减小CPU开销
            (func, *param), evt = ['0', '0'] if self.at_queue.empty() else self.at_queue.get()  # 如果at_queue有内容读，无内容[0,0]
            runtimes = param[-1] if len(param) != 0 else 0
            self.logger.info('{}->{}->{}'.format(func, param, evt)) if func != '0' else ''
            try:
                if func == 'open':  # 每次检测到端口后打开端口，进行各种AT操作前打开需要确保端口是打开状态
                    # 调用方式：'AT', 'open', runtimes
                    open_port_status = self.open()  # 打开端口
                    if open_port_status:
                        self.main_queue.put(True)
                        evt.set()
                    else:
                        self.log_queue.put(['all', '[{}] runtimes:{} 连续10次打开端口失败'.format(datetime.datetime.now(), runtimes)])
                        self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} 连续10次打开端口失败'.format(datetime.datetime.now(), runtimes)])
                        self.log_queue.put(['write_result_log', runtimes])
                        self.main_queue.put(False)
                        evt.set()
                elif func == 'close':  # 重启模块/不再进行AT口操作/新的Runtimes必须关闭口，并在下个Runtimes打开
                    # 调用方式：'AT', 'close', runtimes
                    self.close()  # 关闭端口
                    self.main_queue.put(True)
                    evt.set()
                elif func in self._methods_list:
                    at_status = getattr(self.__class__, '{}'.format(func))(self, *param)
                    if at_status is not False:
                        self.main_queue.put(True)
                    else:
                        self.close()
                        self.at_port_opened_flag = False
                        self.main_queue.put(False)
                    evt.set()
                elif func.upper().startswith('AT'):  # 主脚本调用单独发AT，分为只返回OK和返回OK继续返回值类型(AT+QPOWD)
                    at_status = self.at(func, param)
                    if at_status:
                        self.main_queue.put(True)
                    else:
                        self.close()
                        self.at_port_opened_flag = False
                        self.main_queue.put(False)
                    evt.set()
                elif self.at_port_opened_flag:  # 没有检测到任何方法，并且端口是打开的状态，不停的读取URC，此方法要放最后
                    return_value = self.readline(self.at_port_opened)
                    if return_value != '':
                        self.urc_checker(return_value, '')
            except serial.serialutil.SerialException as e:
                # 记录当前端口状态
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), e)])
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), self.at_port_opened)])
                self.logger.info(self.at_port_opened)
                self.logger.info(e)
                # 获取当前端口情况
                port_list = self.get_port_list()
                self.log_queue.put(['at_log', '[{}] 端口异常, 当前COM口情况: {}'.format(datetime.datetime.now(), port_list)])
                self.log_queue.put(['all', '[{}] runtimes:{} 端口异常，当前端口情况：{}'.format(datetime.datetime.now(), runtimes, port_list)])
                self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} 端口异常，当前端口情况：{}'.format(datetime.datetime.now(), runtimes, port_list)])
                # 关闭端口并把flag置为False，停止读取URC
                self.close()
                self.at_port_opened_flag = False
                # 如果evt的类型为Event
                if isinstance(evt, Event):
                    self.log_queue.put(['write_result_log', runtimes])
                    self.main_queue.put(False)
                    evt.set()
            except URCError:
                # 如果evt的类型为Event，说明当前线程在执行主线程的任务
                if isinstance(evt, Event):
                    # 关闭端口并把flag置为False，停止读取URC
                    self.close()
                    self.at_port_opened_flag = False
                    self.log_queue.put(['write_result_log', runtimes])
                    self.main_queue.put(False)
                    evt.set()

    def open(self):
        """
        打开AT口，如果打开失败，重新打开，打开后at_port_opened_flag设置为True，开始读URC
        :return: None
        """
        for _ in range(10):
            self.logger.info(self.at_port_opened)
            # 打开之前判断是否有close属性，有则close
            if getattr(self.at_port_opened, 'close', None):
                self.close()
            # 端口打开失败->等待2S
            try:
                self.at_port_opened = serial.Serial(self.at_port, baudrate=115200, timeout=0)
                self.at_port_opened_flag = True
                self.logger.info(self.at_port_opened)
                return True
            except (serial.serialutil.SerialException, OSError) as e:  # Linux 偶现开口OSError
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), e)])
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), self.at_port_opened)])
                self.logger.info(self.at_port_opened)
                self.logger.info(e)
                time.sleep(2)
            except Exception as e:
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), e)])
                self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), self.at_port_opened)])
                self.logger.info(self.at_port_opened)
                self.logger.info(e)
                time.sleep(2)
        self.log_queue.put(['all', '[{}] 连续10次打开AT口失败'.format(datetime.datetime.now())])
        pause()

    def close(self):
        """
        关闭AT口，并将at_port_opened设置为False，停止读取urc
        :return: None
        """
        self.logger.info(self.at_port_opened)
        self.at_port_opened_flag = False
        self.at_port_opened.close()
        self.logger.info(self.at_port_opened)

    def get_port_list(self):
        """
        获取当前电脑设备管理器中所有的COM口的列表
        :return: COM口列表，例如['COM3', 'COM4']
        """
        if os.name == 'nt':
            self.logger.info('serial_tools_port_list')
            port_name_list = []
            ports = serial.tools.list_ports.comports()
            for port, _, _ in sorted(ports):
                port_name_list.append(port)
            self.logger.info('serial_tools_port_list:{}'.format(port_name_list))
            return port_name_list
        else:
            self.logger.info("glob.glob('/dev/ttyUSB*')")
            ports = glob.glob('/dev/ttyUSB*')
            self.logger.info(ports)
            return ports

    def check_atfwdok(self, runtimes):
        check_atfwdok_start_timestamp = time.time()
        atfwdok_timeout = 10
        self.log_queue.put(
            ['at_log', '[{}] 开机后开始检查atfwd程序是否成功加载'.format(datetime.datetime.now())])
        while True:
            atfwd_value = self.send_at('AT+qatlist=2', runtimes, timeout=3)
            if 'AT+QCFG' in atfwd_value and 'OK' in atfwd_value:
                self.log_queue.put(
                    ['at_log', '[{}] 已检查到atfwd程序成功加载'.format(datetime.datetime.now())])
                break
            # 检查atfwd当前时间判断，超时写超时，不超时等1S后再找
            check_atfwdok_time = round(time.time() - check_atfwdok_start_timestamp, 2)
            if check_atfwdok_time >= atfwdok_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} 检查atfwd超时'.format(datetime.datetime.now(), runtimes)])
                break
            else:
                time.sleep(1)

    def at(self, func, param):
        """
        需要传入参数参考 [at_command, timeout, repeat_times, result, result_timeout, mode, runtime]
        例如：
            发送AT+QPOWD=0:
                ('AT', 'AT+QPOWD=1', 0.3, 1, 'POWERED DOWN', 60, 1, self.runtimes)
                意思是代表发送AT+QPOWD=1命令，等待OK超时为0.3S，仅发送一次，60S内等待POWERED DOWN上报，使用send_at_two_steps_check，当前runtimes
            发送AT+CFUN?:
                ('AT', 'AT+CFUN?', 6, 1, self.runtimes)
                意思是发送AT+CFUN?，等待超时时间6秒，默认发送1次，当前runtimes次数
        参数参考：
            at_command:AT指令,例如AT+CFUN?;
            timeout:文档中AT指令的超时时间,例如0.3;
            repeat_times:如果不是OK或者指定值时发送AT的次数,一般为1,如果到达指定次数没有返回OK，返回False;
            result:send_at_two_steps_check方法需要用到,检测AT+QPOWD=0这种会二次返回AT的指令;
            result_timeout:返回OK后继续检测，直到URC上报的时间;
            mode:空("")或0代表使用send_at函数,1代表使用send_at_two_steps_check函数。
            runtimes:当前的runtimes,例如100
        :param func: 参数解析的func，以AT开头
        :param param: 参数解析的后的param
        :return:True：指定次数内返回OK；False：指定次数内没有返回OK。
        """
        mode = ''
        result = ''
        result_timeout = ''
        at_command = func  # AT指令即为func
        if len(param) == 6:
            timeout, repeat_times, result, result_timeout, mode, runtimes = param
        else:
            timeout, repeat_times, runtimes = param
        for times in range(1, repeat_times + 1):  # +1是为了从1开始，range(1,4)返回123
            if mode == 0 or mode == '':
                at_return_value = self.send_at(at_command, runtimes, timeout)
            else:
                at_return_value = self.send_at_two_steps_check(at_command, runtimes, timeout, result, result_timeout)
            if 'OK' in at_return_value:
                return True
            elif times == repeat_times:
                self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} {}返回值错误'.format(datetime.datetime.now(), runtimes, at_command)])
                return False

    def send_at_two_steps_check(self, at_command, runtimes, timeout, result, result_timeout):
        """
        发送AT指令。（用于返回OK后还会继续返回信息的AT指令，例如AT+QPOWD=0，在返回OK后，会再次有POWERED DOWN上报）
        :param at_command: AT指令
        :param runtimes: 脚本的运行次数
        :param timeout: AT指令的超时时间，参考AT文档
        :param result: AT指令返回OK后，再次返回的内容
        :param result_timeout: 返回AT后的urc的上报的超时时间
        :return: AT指令返回值
        """
        for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
            at_start_timestamp = time.time()
            self.at_port_opened.write('{}\r\n'.format(at_command).encode('utf-8'))
            self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format(at_command))])
            self.logger.info('Send: {}'.format(at_command))
            return_value_cache = ''
            at_returned_ok_flag = False
            at_returned_ok_timestamp = time.time()
            urc_check_interval = time.time()
            while True:
                # AT端口值获取
                time.sleep(0.001)  # 减小CPU开销
                return_value = self.readline(self.at_port_opened)
                if return_value != '':
                    return_value_cache += '[{} Recv] {}'.format(datetime.datetime.now(), repr(return_value).replace("'", ''))
                    self.urc_checker(return_value, runtimes)
                    if 'OK' in return_value and at_command in return_value_cache and not at_returned_ok_flag:
                        at_returned_ok_timestamp = time.time()
                        urc_check_interval = time.time()
                        at_returned_ok_flag = True
                    if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}指令返回ERROR'.format(datetime.datetime.now(), runtimes, at_command)])
                        return return_value_cache
                if at_returned_ok_flag:  # 如果返回OK了
                    if result in return_value_cache:
                        return return_value_cache
                    elif time.time() - at_returned_ok_timestamp > result_timeout:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到{}上报，模块未掉口，关机失败'.format(datetime.datetime.now(), runtimes, result_timeout, result)])
                        pause()
                    elif time.time() - urc_check_interval > 1:  # 每隔1S检查一次驱动情况
                        urc_check_interval = time.time()
                        port_list = self.get_port_list()
                        if self.at_port not in port_list and self.dm_port not in port_list:
                            self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到{}上报，模块已掉口'.format(datetime.datetime.now(), runtimes, round(time.time() - at_start_timestamp), result)])
                            return return_value_cache
                elif (time.time() - at_start_timestamp) > timeout:  # 如果超时
                    out_time = time.time()
                    if return_value_cache and at_command in return_value_cache:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行超时({}S)'.format(datetime.datetime.now(), runtimes, at_command, timeout)])
                        while True:
                            time.sleep(0.001)  # 减小CPU开销
                            return_value = self.readline(self.at_port_opened)
                            if return_value != '':
                                return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                            if time.time() - out_time > 3:
                                return return_value_cache
                    elif return_value_cache and at_command not in return_value_cache and 'OK' in return_value_cache:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行返回格式错误，未返回AT指令本身'.format(datetime.datetime.now(), runtimes, at_command)])
                        return return_value_cache
                    else:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行{}S内无任何回显'.format(datetime.datetime.now(), runtimes, at_command, timeout)])
                        self.check_port(runtimes)
                        time.sleep(0.5)
                        break
        else:
            self.log_queue.put(['all', '[{}] runtimes:{} 连续10次执行{}命令无任何回显，AT不通'.format(datetime.datetime.now(), runtimes, at_command)])
            pause()

    def readline(self, port, timeout=1):
        """
        重写readline方法，首先用in_waiting方法获取IO buffer中是否有值：
        如果有值，读取直到\n；
        如果有值，超过1S，直接返回；
        如果没有值，返回 ''
        :param port: 已经打开的端口
        :param timeout: 端口检测超时时间
        :return: buf:端口读取到的值；没有值返回 ''
        """
        buf = ''
        try:
            if port.in_waiting > 0:
                start_time = time.time()
                while True:
                    buf += port.read(1).decode('utf-8', 'replace')
                    if buf.endswith('\n'):
                        self.logger.info(repr(buf))
                        self.log_queue.put(['at_log', '[{} Recv] {}'.format(datetime.datetime.now(), repr(buf).replace("'", ''))])
                        break  # 如果以\n结尾，停止读取
                    elif time.time() - start_time > timeout:
                        self.logger.info('异常 {}'.format(repr(buf)))
                        break  # 如果时间>1S(超时异常情况)，停止读取
        except OSError as error:
            self.logger.info('Fatal ERROR: {}'.format(error))
        finally:
            # TODO:此处可以添加异常URC检测和POWERED URC检测。
            return buf

    def urc_checker(self, content, runtimes):
        """
        URC持续上报和AT指令发送过程中异常URC检测
        :param content: 消息内容
        :param runtimes: 当前脚本运行次数
        :return: None
        """
        cpin_not_ready = re.findall(r'CPIN: NOT READY', content)
        cpin_not_inserted = re.findall(r'CPIN: NOT INSERTED', content)
        if cpin_not_ready:
            self.log_queue.put(['df', runtimes, 'cpin_not_ready', 1])  # net_fail_times
            self.log_queue.put(['all', '[{}] runtimes:{} CPIN: NOT READY'.format(datetime.datetime.now(), runtimes)])
            self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} CPIN: NOT READY'.format(datetime.datetime.now(), runtimes)])
            raise URCError
        elif cpin_not_inserted:
            self.log_queue.put(['df', runtimes, 'cpin_not_inserted', 1])  # net_fail_times
            self.log_queue.put(['all', '[{}] runtimes:{} CPIN: NOT INSERTED'.format(datetime.datetime.now(), runtimes)])
            self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} CPIN: NOT INSERTED'.format(datetime.datetime.now(), runtimes)])
            raise URCError

    @staticmethod
    def at_format_check(at_command, return_value):
        """
        用于AT指令格式的检查。
        :param at_command: AT指令
        :param return_value: AT指令的返回值
        :return: None
        """
        # 可能存在部分指令不符合以下格式，通过at_command区分
        # TODO:重新检查AT指令返回值格式
        return_value = ''.join(re.findall(r"\[.*?]\s'AT[\s\S]*", return_value))  # 此处替换为了防止发送AT前有URC上报
        at_check_cache = return_value.split('\r\n')
        if 'OK' in return_value:
            for item in at_check_cache:
                num_r, num_n = len(re.findall(r'\r', item)), len(re.findall(r'\n', item))
                if at_command.upper() in item and (num_r != 1 or num_n != 0):  # AT command在返回值，并且\r为1，\n为0
                    print('[{}] {}指令格式错误'.format(datetime.datetime.now(), at_command))
                elif at_command.upper() not in item and (num_r != 0 or num_n != 0):  # AT command不在返回值，并且\r为0，\n为0
                    print('[{}] {}指令格式错误'.format(datetime.datetime.now(), at_command))

    def send_at(self, at_command, runtimes, timeout=0.3):
        """
        发送AT指令。（用于返回OK的AT指令）
        :param at_command: AT指令内容
        :param runtimes: 当前脚本的运行次数
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
            at_start_timestamp = time.time()
            self.at_port_opened.write('{}\r\n'.format(at_command).encode('utf-8'))
            self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format(at_command))])
            self.logger.info('Send: {}'.format(at_command))
            return_value_cache = ''
            while True:
                # AT端口值获取
                time.sleep(0.001)  # 减小CPU开销
                return_value = self.readline(self.at_port_opened)
                if return_value != '':
                    self.urc_checker(return_value, runtimes)
                    return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                    if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                        self.at_format_check(at_command, return_value_cache)
                        return return_value_cache
                    if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}指令返回ERROR'.format(datetime.datetime.now(), runtimes, at_command)]) if 'COPS' not in at_command else ''  # *屏蔽锁pin AT+COPS错误
                        return return_value_cache
                # 超时等判断
                current_total_time = time.time() - at_start_timestamp
                if current_total_time > timeout:  # 超时
                    if return_value_cache:  # 如果AT指令缓存区有值
                        if at_command in return_value_cache:
                            self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行超时({}S)'.format(datetime.datetime.now(), runtimes, at_command, timeout)])
                        elif at_command not in return_value_cache and 'OK' in return_value_cache:
                            # 特殊情况，可能是modem重启
                            self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行返回格式错误，未返回AT指令本身'.format(datetime.datetime.now(), runtimes, at_command)])
                    else:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行{}S内无任何回显'.format(datetime.datetime.now(), runtimes, at_command, timeout)])

                    # 检查端口信息，如果
                    self.check_port(runtimes)

                    # 额外检查5S，读取log
                    break_time = time.time()
                    while True:
                        time.sleep(0.001)  # 减小CPU开销
                        return_value = self.readline(self.at_port_opened)
                        if return_value != '':
                            return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                        if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                            self.at_format_check(at_command, return_value_cache)
                            return return_value_cache
                        if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                            self.log_queue.put(['all', '[{}] runtimes:{} {}指令返回ERROR'.format(datetime.datetime.now(), runtimes, at_command)]) if 'COPS' not in at_command else ''  # *屏蔽锁pin AT+COPS错误
                            return return_value_cache
                        if time.time() - break_time > 5:
                            break

                    # 跳出While重新发送AT
                    break
        else:
            self.log_queue.put(['all', '[{}] runtimes:{} 连续10次执行{}指令异常'.format(datetime.datetime.now(), runtimes, at_command)])
            pause()

    def send_nowait_at(self, at_command, runtimes, timeout=0.3):
        """
        用于新增RGMII/RTL8125需求,在执行完指令后不要返回,直接进行后续操作
        :param at_command: AT指令内容
        :param runtimes: 当前脚本的运行次数
        :param timeout: AT指令的超时时间，参考AT文档
        :return: AT指令返回值
        """
        for _ in range(1, 11):  # 连续10次发送AT返回空，并且每次检测到口还在，则判定为AT不通
            at_start_timestamp = time.time()
            self.at_port_opened.write('{}\r\n'.format(at_command).encode('utf-8'))
            self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format(at_command))])
            self.logger.info('Send: {}'.format(at_command))
            return_value_cache = ''
            while True:
                # AT端口值获取
                time.sleep(0.001)  # 减小CPU开销
                return_value = self.readline(self.at_port_opened)
                if return_value != '':
                    self.urc_checker(return_value, runtimes)
                    return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_value)
                    if 'OK' in return_value and at_command in return_value_cache:  # 避免发AT无返回值后，再次发AT获取到返回值的情况
                        self.at_format_check(at_command, return_value_cache)
                        return return_value_cache
                    if re.findall(r'ERROR\s+', return_value) and at_command in return_value_cache:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}指令返回ERROR'.format(datetime.datetime.now(), runtimes, at_command)]) if 'COPS' not in at_command else ''  # *屏蔽锁pin AT+COPS错误
                        return return_value_cache
                # 超时等判断
                current_total_time = time.time() - at_start_timestamp
                if current_total_time > timeout:  # 超时
                    if return_value_cache:  # 如果AT指令缓存区有值
                        if at_command in return_value_cache:
                            self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行超时({}S)'.format(datetime.datetime.now(), runtimes, at_command, timeout)])
                            return True
                        elif at_command not in return_value_cache and 'OK' in return_value_cache:
                            # 特殊情况，可能是modem重启
                            self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行返回格式错误，未返回AT指令本身'.format(datetime.datetime.now(), runtimes, at_command)])
                    else:
                        self.log_queue.put(['all', '[{}] runtimes:{} {}命令执行{}S内无任何回显'.format(datetime.datetime.now(), runtimes, at_command, timeout)])

                    # 跳出While重新发送AT
                    break
        else:
            self.log_queue.put(['all', '[{}] runtimes:{} 连续10次执行{}指令异常'.format(datetime.datetime.now(), runtimes, at_command)])
            pause()

    def qftest_record(self, runtimes):
        time.sleep(4)
        qftest_orig = self.send_at('AT+QFTEST="FSPartitionEC"', runtimes, 3)
        if "OK" not in qftest_orig or "ERROR" in qftest_orig:
            return  # 异常不记录
        qftest_regex = re.findall(r'QFTEST:\s".*?",(\d+)\s:\s(\d+)', qftest_orig)
        # 新增resul中flash分区擦除次数
        qftest_str = str(dict(qftest_regex))
        self.log_queue.put(['df', runtimes, 'qftest_record', qftest_str])  # 此处为了开关机不统计异常开机时间
        if 'QFTEST:"FSPartitionEC"' in qftest_orig or 'QFTEST: "FSPartitionEC"' in qftest_orig:
            cefs_value = "".join(re.findall(r'"FSPartitionEC",1,(\d+)', qftest_orig))
            usrdata_value = "".join(re.findall(r'"FSPartitionEC",2,(\d+)', qftest_orig))
            if cefs_value and usrdata_value:
                cefs_value = int(cefs_value)
                usrdata_value = int(usrdata_value)
                self.log_queue.put(['df', runtimes, 'cefs_erase_times', cefs_value])  # 此处统计查询出来的cefs值
                self.log_queue.put(['df', runtimes, 'usrdata_erase_times', usrdata_value])  # 此处统计查询出来的usrdata值
            else:
                self.log_queue.put(
                    ['all', '{} runtimes:{} 查询flash返回异常,请手动验证确认'.format(datetime.datetime.now(), runtimes)])
                return True
        else:
            cefs_value = "".join(re.findall(r'QFTEST: "PartitionCtlEC",1 : (\d+)', qftest_orig))
            usrdata_value = "".join(re.findall(r'QFTEST: "PartitionCtlEC",2 : (\d+)', qftest_orig))
            if cefs_value and usrdata_value:
                cefs_value = int(cefs_value)
                usrdata_value = int(usrdata_value)
                self.log_queue.put(['df', runtimes, 'cefs_erase_times', cefs_value])  # 此处统计查询出来的cefs值
                self.log_queue.put(['df', runtimes, 'usrdata_erase_times', usrdata_value])  # 此处统计查询出来的usrdata值
            else:
                self.log_queue.put(
                    ['all', '{} runtimes:{} 查询flash返回异常,请手动验证确认'.format(datetime.datetime.now(), runtimes)])
                return True

    def check_restore(self, runtimes):
        """
        执行指令AT+QPRTPARA=4查询还原次数
        """
        self.log_queue.put(['at_log', '[{}]模块还原次数查询'.format(datetime.datetime.now())])
        time.sleep(2)
        self.send_at('AT+QPRTPARA=4', runtimes, 10)

    def memory_leak_monitoring(self, runtimes):
        self.log_queue.put(['at_log', '开始进行内存空间查询'])
        dail_value = self.send_at('AT+QDMEM?', runtimes, 15)
        if dail_value and 'ERROR' not in dail_value:
            large_item_total = int(''.join(re.findall(r'large_item",(\d+)', dail_value)))
            large_item_free = int(''.join(re.findall(r'large_item",\d+,\d+,(\d+)', dail_value)))
            large_item_measurement_standard = large_item_total // 3
            if large_item_free < large_item_measurement_standard:
                self.log_queue.put(['at_log', 'large_item存在内存泄露'])
                pause()
            else:
                self.log_queue.put(['at_log', 'large_item内存正常'])

            smsall_item_total = int(''.join(re.findall(r'smsall_item",(\d+)', dail_value)))
            smsall_item_free = int(''.join(re.findall(r'smsall_item",\d+,\d+,(\d+)', dail_value)))
            smsall_item_measurement_standard = smsall_item_total // 3
            if smsall_item_free < smsall_item_measurement_standard:
                self.log_queue.put(['at_log', 'smsall_item存在内存泄露'])
                pause()
            else:
                self.log_queue.put(['at_log', 'smsall_item内存正常'])

            dup_item_total = int(''.join(re.findall(r'dup_item",(\d+)', dail_value)))
            dup_item_free = int(''.join(re.findall(r'dup_item",\d+,\d+,(\d+)', dail_value)))
            dup_item_measurement_standard = dup_item_total // 3
            if dup_item_free < dup_item_measurement_standard:
                self.log_queue.put(['at_log', 'dup_item存在内存泄露'])
                pause()
            else:
                self.log_queue.put(['at_log', 'dup_item内存正常'])

        else:
            self.log_queue.put(['at_log', 'AT+QDMEM?指令查询异常'])

    def check_port(self, runtimes):
        """
        发送AT不通等情况需要检测当前的端口情况，可能出现DUMP和模块异常关机两种情况。
        1. 模块DUMP，现象：仅有DM口，AT口不存在
        电脑设置DUMP重启->模块DUMP->检测模块重启->检测到AT口出现->检测URC->检测到URC后等待10S(最好等待)->脚本继续进行
        电脑没有设置DUMP重启->模块DUMP->检测模块重启->卡死在等待重启界面->现场保留状态
        2. 模块异常关机，现象：发送指令或者检测过程中DM口和AT口都消失了
        模块重启->检测AT口出现->检测URC->检测到URC后等待10S(最好等待)
        :param runtimes:当前脚本的运行次数。
        :return:None
        """
        port_list = self.get_port_list()
        if self.at_port in port_list and self.dm_port in port_list:  # AT √ DM √
            return True
        else:  # 异常
            self.log_queue.put(['all', '[{}] runtimes:{} 端口异常：当前端口: {}，检查模块恢复'.format(datetime.datetime.now(), runtimes, port_list)])
            for n in range(5):
                time.sleep(1)  # 如果出现异常情况，等待1S重新获取端口情况，避免没有同时消失造成的异常关机和DUMP的误判
                port_list = self.get_port_list()
                if self.at_port in port_list and self.dm_port in port_list:  # AT √ DM √
                    return True
            else:
                if self.at_port not in port_list and self.dm_port in port_list:  # AT × DM √
                    self.log_queue.put(['all', '[{}] runtimes:{} 模块DUMP'.format(datetime.datetime.now(), runtimes)])
                elif self.at_port not in port_list and self.dm_port not in port_list:  # AT × DM ×
                    self.log_queue.put(['all', '[{}] runtimes:{} 模块异常关机'.format(datetime.datetime.now(), runtimes)])
                elif self.at_port in port_list and self.dm_port not in port_list:  # AT √ DM ×
                    self.log_queue.put(['all', '[{}] runtimes:{} 仅AT口加载，DM口未加载'.format(datetime.datetime.now(), runtimes)])
                self.close()
                self.check_at_dm_port(runtimes)
                self.open()
                self.check_urc(runtimes)
                self.log_queue.put(['df', runtimes, 'error', 1])  # 此处为了开关机不统计异常开机时间
                return False

    def check_urc(self, runtimes):
        """
        用于开机检测端口是否有任何内容上报，如果读取到任何内容，则停止。
        :param runtimes: 当前脚本的运行次数
        :return: True：有URC；False：未检测到
        """
        port_check_interval = time.time()
        check_urc_start_timestamp = time.time()
        while True:
            time.sleep(0.001)  # 减小CPU开销
            check_urc_total_time = time.time() - check_urc_start_timestamp
            if check_urc_total_time > 60:  # 暂定60S没有URC上报则异常
                return_value = self.send_at('AT', runtimes)
                self.urc_checker(return_value, runtimes)
                if 'OK' in return_value:
                    self.log_queue.put(['all', "[{}] runtimes:{} 检测到驱动后60S内无开机URC上报".format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'rn_timestamp', time.time()]) if runtimes != 0 else 1
                    return True
                else:
                    self.log_queue.put(['all', "[{}] runtimes:{} 检测到驱动后60S内无开机URC上报且发送AT无返回值".format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} 无URC上报'.format(datetime.datetime.now(), runtimes)])
                    return False
            elif time.time() - port_check_interval > 3:  # 每隔3S检查一次驱动情况
                port_check_interval = time.time()
                port_check_status = self.check_port(runtimes)
                if port_check_status is False:
                    check_urc_start_timestamp = time.time()
            else:  # 检查URC
                at_port_data = self.readline(self.at_port_opened)
                if at_port_data != '':
                    self.log_queue.put(['df', runtimes, 'rn_timestamp', time.time()]) if runtimes != 0 else 1
                    self.urc_checker(at_port_data, runtimes)
                    return True

    def check_at_dm_port(self, runtimes):
        """
        检测当前电脑的端口列表，仅当AT口和DM口都出现才会break，否则一直检测。
        :return: None
        """
        self.log_queue.put(['at_log', '[{}] {}'.format(datetime.datetime.now(), '开始检测USB驱动重新加载')])
        dump_timestamp = time.time()
        power_on_timestamp = time.time()
        while True:
            time.sleep(0.5)  # 每隔0.5S检查一次
            # 检测at口和dm口是否在端口列表
            port_list = self.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                time.sleep(1)  # 端口出现后等待1s打开口
                break
            # 每隔3S判断是否DUMP
            if time.time() - dump_timestamp > 3:
                if self.at_port not in port_list and self.dm_port in port_list:
                    self.log_queue.put(['all', '[{}] runtimes:{} 模块DUMP'.format(datetime.datetime.now(), runtimes)])
                dump_timestamp = time.time()
            # 每隔300S检测是否正常开机，没有则上报未正常开机
            if time.time() - power_on_timestamp > 300:
                power_on_timestamp = time.time()
                self.log_queue.put(['all', '[{}] runtimes:{} 模块300S内未正常开机'.format(datetime.datetime.now(), runtimes)])
            # TODO：此处可以增加自动打开QPST抓DUMP。
            # # DUMP 300S强制重启
            # if time.time()-start_timestamp > 300 and self.dm_port in port_list and self.at_port not in port_list:
            #     start_timestamp = time.time()
            #     self.log_queue.put(['at_log', '[{}] 300S内模块未从DUMP模式恢复，强制重启'.format(datetime.datetime.now())])
            #     with serial.Serial(self.dm_port, 115200, timeout=0.8) as dm_port:
            #         dm_port.write(bytes.fromhex('0700000008000000'))

    def check_cpin(self, runtimes):
        """
        用于单双卡切换后 CPIN READY是否正常上报。
        :param runtimes: 当前脚本运行次数。
        :return: True，接收到CPIN: READY上报；False：timeout时间内没有收到CPIN READY上报。
        """
        timeout = 20
        start_timestamp = time.time()
        while True:
            time.sleep(0.001)
            port_data = self.readline(self.at_port_opened)
            if port_data != "":
                if 'CPIN: READY' in port_data:
                    return True
            if time.time() - start_timestamp > timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到CPIN: READY上报'.format(datetime.datetime.now(), runtimes, timeout)])
                return False

    def dsss_init(self, runtimes):
        """
        初始化设置切到SIM卡1。
        :param runtimes: 脚本运行次数
        :return: None
        """
        self.send_at('AT+QUIMSLOT=?', runtimes, 0.3)
        for i in range(1, 11):
            self.send_at('AT+QUIMSLOT=1', runtimes, 0.3)
            time.sleep(2)  # 切卡会有cpin等urc上报，立即查询可能存在AT不通
            simslot_return_value = self.send_at('AT+QUIMSLOT?', runtimes, 0.3)
            simslot_index = ''.join(re.findall(r'QUIMSLOT:\s(\d+)', simslot_return_value))
            if '1' in simslot_index and 'OK' in simslot_return_value:
                return True
        else:
            self.log_queue.put(['all', "[{}] runtimes:{} 连续10次执行at+quimslot=1切换卡槽".format(datetime.datetime.now(), runtimes)])
            pause()

    # 私有方法
    def switch_slot(self, runtimes):
        """
        查询当前在哪个卡槽，然后切换卡槽。
        :param runtimes: 当前脚本的运行次数
        :return: True: 正常切换；False：切换过程中发现异常。
        """
        start_time = time.time()
        slot_value = self.send_at('AT+QUIMSLOT?', runtimes, timeout=3)
        return_value_re = ''.join(re.findall(r'QUIMSLOT:\s(\d+)', slot_value))
        if '1' == return_value_re and 'OK' in slot_value:
            return_value_slot = self.send_at('AT+QUIMSLOT=2', runtimes, timeout=3)
            if return_value_slot:
                self.log_queue.put(['df', runtimes, 'switch_time', time.time() - start_time])
                self.check_cpin(runtimes)  # 检查CPIN: READY
                self.select_mbn1(runtimes)
                return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} 卡槽1切换卡槽2失败！'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'switch_error_times', 1])
                return False
        else:
            return_value_slot = self.send_at('AT+QUIMSLOT=1', runtimes, timeout=3)
            if return_value_slot:
                self.log_queue.put(['df', runtimes, 'switch_time', time.time() - start_time])
                self.check_cpin(runtimes)  # 检查CPIN: READY
                self.select_mbn2(runtimes)
                return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} 卡槽2切换卡槽1失败！'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'switch_error_times', 1])
                return False

    def select_mbn1(self, runtimes):
        time.sleep(1)
        self.send_nowait_at('at+qmbncfg="select","CDMAless-Verizon"', runtimes, timeout=1)

    def select_mbn2(self, runtimes):
        time.sleep(1)
        self.send_nowait_at('at+qmbncfg="select","ROW_Generic_3GPP_PTCRB_GCF"', runtimes, timeout=1)

    def check_mbn_lost(self, runtimes):
        time.sleep(6)
        mbn_status = ''
        mbn_list = ['Volte_OpenMkt-Commercial-CMCC', 'ROW_Generic_3GPP_PTCRB_GCF', 'FirstNet', 'Rogers_Canada',
                    'Bell_Canada', 'Telus_Canada', 'Commercial-Sprint', 'Commercial-TMO', 'VoLTE-ATT',
                    'CDMAless-Verizon', 'Telia_Sweden', 'TIM_Italy_Commercial', 'France-Commercial-Orange',
                    'Commercial-DT-VOLTE', 'Germany-VoLTE-Vodafone', 'UK-VoLTE-Vodafone', 'Commercial-EE',
                    'Optus_Australia_Commercial', 'Telstra_Australia_Commercial', 'Commercial-LGU', 'Commercial-KT',
                    'Commercial-SKT', 'Commercial-Reliance', 'Commercial-SBM','Commercial-KDDI', 'Commercial-DCM',
                    'VoLTE-CU', 'VoLTE_OPNMKT_CT', 'ROW_Commercial']
        self.log_queue.put(['at_log', '[{}] SIM卡切换后检查mbn'.format(datetime.datetime.now())])
        for i in range(20):
            mbn_status = self.send_at('at+qmbncfg="list"', runtimes, timeout=15)
            if 'OK' in mbn_status:
                self.log_queue.put(['at_log', '[{}] mbn查询指令返回:{}'.format(datetime.datetime.now(), mbn_status)])
                self.log_queue.put(['at_log', '[{}] 开始检查mbn'.format(datetime.datetime.now())])
                break
            time.sleep(3)
        else:
            self.log_queue.put(['at_log', '[{}] 查询mbn指令返回异常:{}'.format(datetime.datetime.now(), mbn_status)])
            pause()

        self.log_queue.put(['at_log', '[{}] 开始检查mbn是否缺失'.format(datetime.datetime.now())])
        for i in mbn_list:
            if i in mbn_status:
                self.log_queue.put(['at_log', '[{}] 当前Mbn_{}检查正常'.format(datetime.datetime.now(), i)])
            else:
                self.log_queue.put(['at_log', '[{}] 当前Mbn_{}检查缺失'.format(datetime.datetime.now(), i)])
                self.log_queue.put(['at_log', '[{}] 指令查询返回 {}'.format(datetime.datetime.now(), mbn_list)])
                pause()
        self.log_queue.put(['at_log', '[{}] mbn检查正常没有缺失'.format(datetime.datetime.now())])
        self.log_queue.put(['at_log', '[{}] 开始检查mbn是重复'.format(datetime.datetime.now())])
        value = re.findall(r'QMBNCFG: "List",\d+,\d,\d,"(.*)"', mbn_status)
        for j in mbn_list:
            mbn_num = value.count(j)
            if mbn_num > 1:
                self.log_queue.put(['at_log', '[{}] 当前Mbn_{}重复'.format(datetime.datetime.now(), j)])
                pause()
            self.log_queue.put(['at_log', '[{}] 当前检查mbn_{}没有重复'.format(datetime.datetime.now(), j)])
        self.log_queue.put(['at_log', '[{}] mbn检查正常,没有重复'.format(datetime.datetime.now())])