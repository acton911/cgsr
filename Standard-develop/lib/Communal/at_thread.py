# -*- encoding=utf-8 -*-
import random
from threading import Thread, Event
import datetime
import serial
import time
import os
import re
import serial.tools.list_ports
import logging
import json
import hashlib
import subprocess
from subprocess import PIPE, STDOUT
from functions import pause
import glob
import numpy as np
# TODO:增加URC内容顺序的check
# TODO:增加URC格式的check


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
        self.cefs_restore_times = 0
        self.dfota_powerfailure_time = 0
        self.multi_vbat_time = 4

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
        #cpin_not_ready = re.findall(r'CPIN: NOT READY', content)
        cpin_not_inserted = re.findall(r'CPIN: NOT INSERTED', content)
        # if cpin_not_ready:
        #     self.log_queue.put(['df', runtimes, 'cpin_not_ready', 1])  # net_fail_times
        #     self.log_queue.put(['all', '[{}] runtimes:{} CPIN: NOT READY'.format(datetime.datetime.now(), runtimes)])
        #     self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} CPIN: NOT READY'.format(datetime.datetime.now(), runtimes)])
        #     raise URCError
        if cpin_not_inserted:
            self.log_queue.put(['df', runtimes, 'cpin_not_inserted', 1])  # net_fail_times
            self.log_queue.put(['all', '[{}] runtimes:{} CPIN: NOT INSERTED'.format(datetime.datetime.now(), runtimes)])
            self.log_queue.put(['df', runtimes, 'error', '[{}] runtimes:{} CPIN: NOT INSERTED'.format(datetime.datetime.now(), runtimes)])
            raise URCError

    def dial_mode_check(self, dial_mode, runtimes):
        """
        查询AT+QCFG="USBNET"当前的模式。
        :param dial_mode: 拨号方式 NDIS/MBIM
        :param runtimes: 运行次数
        :return: False, 对比不一致； True, 对比一致
        """
        dial_mode = dial_mode.upper()  # 转换为大写，防止主脚本写错
        usbnet_mode = ''
        for i in range(10):     # 防止过快发送该指令导致获取值失败
            return_value = self.send_at('AT+QCFG="USBNET"', runtimes)
            usbnet_mode = ''.join(re.findall(r'\"usbnet\",(\d+)', return_value, re.IGNORECASE))
            if usbnet_mode != '':
                break
            else:
                time.sleep(2)
        if dial_mode == 'NDIS' and usbnet_mode != '0':
            self.log_queue.put(['all', '[{}] runtimes:{} NDIS拨号方式，AT+QCFG="USBNET"返回值应该是0，当前为{}，请检查'.format(datetime.datetime.now(), runtimes, usbnet_mode)])
            return False
        elif dial_mode == 'MBIM' and usbnet_mode != '2':
            self.log_queue.put(['all', '[{}] runtimes:{} MBIM拨号方式，AT+QCFG="USBNET"返回值应该是2，当前为{}，请检查'.format(datetime.datetime.now(), runtimes, usbnet_mode)])
            return False
        elif dial_mode == 'ECM' and usbnet_mode != '1':
            self.log_queue.put(['all', '[{}] runtimes:{} ECM拨号方式，AT+QCFG="USBNET"返回值应该是1，当前为{}，请检查'.format(datetime.datetime.now(), runtimes, usbnet_mode)])
            return False
        elif dial_mode == 'WWAN' and usbnet_mode != '0':
            self.log_queue.put(['all', '[{}] runtimes:{} WWAN拨号方式，AT+QCFG="USBNET"返回值应该是0，当前为{}，请检查'.format(datetime.datetime.now(), runtimes, usbnet_mode)])
            return False
        elif dial_mode == 'GOBINET' and usbnet_mode != '0':
            self.log_queue.put(['all', '[{}] runtimes:{} GOBINET拨号方式，AT+QCFG="USBNET"返回值应该是0，当前为{}，请检查'.format(datetime.datetime.now(), runtimes, usbnet_mode)])
            return False
        return True

    def check_power_down_urc(self, timeout, runtimes):
        """
        用于关机POWERED DOWN URC检测。
        检测指定的URC，例如按压POWERKEY关机时候，模块会上报POWERED DOWN。
        :param timeout: 检测的超时时间
        :param runtimes: 当前脚本的运行次数
        :return: True：有指定的URC；False：未检测到。
        """
        # TODO：方法需要修改
        at_start_timestamp = time.time()
        port_check_interval = time.time()
        pwrkey_urc_list = []
        while True:
            time.sleep(0.001)  # 减小CPU开销
            # AT端口值获取
            if (time.time() - at_start_timestamp) > timeout:  # 判断是否超时
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到NORMAL POWER DOWN和POWERED DOWN上报，模块未掉口，关机失败'.format(datetime.datetime.now(), runtimes, timeout)])
                return False
            elif time.time() - port_check_interval > 1:  # 每隔1S检查一次驱动情况
                port_list = self.get_port_list()
                if self.at_port not in port_list and self.dm_port not in port_list:
                    self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到NORMAL POWER DOWN和POWERED DOWN上报，模块已掉口'.format(datetime.datetime.now(), runtimes, round(time.time() - at_start_timestamp))])
                    return True
                port_check_interval = time.time()
            else:
                return_value = self.readline(self.at_port_opened)
                if return_value != '':
                    pwrkey_urc_list.append(return_value)
                    self.urc_checker(return_value, runtimes)
                    urc_all_value = ''.join(pwrkey_urc_list)
                    if 'NORMAL POWER DOWN' in urc_all_value and 'POWERED DOWN' in urc_all_value:
                        return True

    def check_specified_urc(self, info, timeout, runtimes):
        """
        ！！！过期的函数，仅用于参考。
        检测指定的URC，例如按压POWERKEY关机时候，模块会上报POWERED DOWN。为了防止URC丢失，需要注意端口打开的时间点。
        :param info: 需要检测的内容，例如POWERED DOWN
        :param timeout: 检测的超时时间
        :param runtimes: 当前脚本的运行次数
        :return: True：有指定的URC；False：未检测到。
        """
        at_start_timestamp = time.time()
        port_check_interval = time.time()
        while True:
            time.sleep(0.001)  # 减小CPU开销
            # AT端口值获取
            if (time.time() - at_start_timestamp) > timeout:  # 判断是否超时
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未收到{}上报'.format(datetime.datetime.now(), runtimes, timeout, info)])
                return False
            elif time.time() - port_check_interval > 1:  # 每隔1S检查一次驱动情况
                port_check_status = self.check_port(runtimes)
                if port_check_status is False:
                    return False
                port_check_interval = time.time()
            else:
                return_value = self.readline(self.at_port_opened)
                if return_value != '':
                    self.urc_checker(return_value, runtimes)
                    if info in return_value:
                        return True

    def prepare_at(self, version, imei, cpin_flag, runtimes):
        """
        脚本运行前模块需要执行的AT指令。
        :param version: 当前模块的版本
        :param imei: 当前模块的IMEI号
        :param cpin_flag: cpin
        :param runtimes: 当前脚本的运行次数
        :return: None
        """
        # TODO:重新check此处AT指令的超时时间
        self.send_at('ATE1', runtimes, 3)
        # 版本号
        return_value = self.send_at('ATI+CSUB', runtimes, 0.6)
        revision = ''.join(re.findall(r'Revision: (.*)', return_value))
        sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
        version_r = revision + sub_edition
        version_r = re.sub(r'[\r\n]', '', version_r)
        if version not in version_r:
            self.log_queue.put(['all', "ATI查询的版本号和当前设置版本号不一致,请确认下当前设置的版本号是否正确"])
            pause()
        # IMEI
        return_value = self.send_at('AT+EGMR=0,7', runtimes, 0.3)
        if imei not in return_value:
            self.log_queue.put(['all', "AT+EGMR=0,7查询的IMEI号和当前设置的IMEI号不一致,请确认下当前设置的IMEI号是否正确"])
            pause()
        # CPIN  如果要锁PIN找网时间设置为True，如果要开机到找网的时间设置为False
        return_value = self.send_at('AT+CPIN?', runtimes, 5)
        if cpin_flag:  # 如果计算锁PIN找网时间
            if 'CPIN: READY' in return_value:
                self.send_at('AT+CLCK="SC",1,"1234"', runtimes, 5)
        else:  # 如果计算开机找网时间
            if 'SIM PIN' in return_value:
                self.send_at('AT+CLCK="SC",0,"1234"', runtimes, 5)
        # 5G特殊指令
        self.send_at('AT+QNWPREFCFG="gw_band"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="lte_band"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="nsa_nr5g_band"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="nr5g_band"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="ue_usage_setting"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="roam_pref",255', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="roam_pref"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="srv_domain",2', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG="srv_domain"', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG= "mode_pref",AUTO', runtimes, 0.3)
        self.send_at('AT+QNWPREFCFG= "mode_pref"', runtimes, 0.3)
        # 其他
        self.send_at('AT+CIMI', runtimes, 0.3)
        self.send_at('AT+CREG=2;+CGREG=2;+CEREG=2;&W', runtimes, 0.9)
        self.send_at('AT+QPRTPARA=?', runtimes, 10)
        return_val = self.send_at('AT+QPRTPARA=4', runtimes, 10)
        restore = ''.join(re.findall(r'\+QPRTPARA:\s(\d|\d\d),.*', return_val))
        if int(restore) != 0:
            self.log_queue.put(['at_log', '[{}]模块已进行备份'.format(datetime.datetime.now())])
            self.log_queue.put(['df', runtimes, 'qprtpara_restore_times', restore])
            return True
        else:
            self.send_at('AT+QPRTPARA=1', runtimes, 10)
        self.send_at('AT&W', runtimes, 0.3)

    def check_restore(self, runtimes):
        """
        执行指令AT+QPRTPARA=4查询还原次数
        """
        self.log_queue.put(['at_log', '[{}]模块还原次数查询'.format(datetime.datetime.now())])
        time.sleep(2)
        self.send_at('AT+QPRTPARA=4', runtimes, 10)

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

    def sms_init(self, pdu_or_text, cscs, runtimes):
        """
        初始化cmgf、cscs、csmp参数
        删除sim卡所有短信。
        :param pdu_or_text:
        :param cscs:
        :param runtimes:
        :return:
        """
        # 设置cmgf cscs csmp cmee
        self.send_at('AT+CMGF={}'.format(pdu_or_text), runtimes, 0.3)
        self.send_at('AT+CSCS="{}"'.format(cscs), runtimes, 0.3)
        self.send_at('AT+CSMP=17,71,0,0', runtimes, 10)
        self.send_at('AT+CMEE=1', runtimes, 0.3)
        self.send_at('AT&W', runtimes, 0.3)
        # 删除所有短信
        self.send_at('AT+CMGD=0,4', runtimes, 10)
        # 查询短信列表是否为空
        return_cmgf = self.send_at('AT+CMGF?', runtimes, 0.3)
        return_cmgf_re = ''.join(re.findall(r'CMGF:\s(\d+)', return_cmgf))
        if return_cmgf_re == '1':
            for i in range(1, 11):
                time.sleep(1)  # 等1S短信删除动作
                return_cmgl = self.send_at('AT+CMGL="ALL"', runtimes, 0.3)
                if '+CMGL:' not in return_cmgl and 'OK' in return_cmgl:
                    return True
                else:
                    self.send_at('AT+CMGD=0,4', runtimes, 3)
                    self.log_queue.put(['all', "[{}] runtimes:{} 初始化第{}次删除所有短信失败".format(datetime.datetime.now(), runtimes, i)])
                    time.sleep(1)
            else:
                self.log_queue.put(['all', "[{}] runtimes:{} 初始化连续10次删除所有短信失败！".format(datetime.datetime.now(), runtimes)])
                pause()

    def ufs_compare_init(self, runtimes):
        """
        文件相关指令初始化
        :param runtimes:
        :return:
        """
        self.send_at('AT+QFUPL=?', runtimes, 0.3)
        self.send_at('AT+QFOPEN=?', runtimes, 0.3)
        self.send_at('AT+QFDWL=?', runtimes, 0.3)
        self.send_at('AT+QFLST="*"', runtimes, 0.3)
        self.send_at('AT+QFDEL="*"', runtimes, 0.3)  # 防止UFS空间不足，初始化删除全部文件

    def sms_send_receive(self, msg_content, phone_number, cms_error_list, runtimes):
        """
        模块自发自收
        :param msg_content: 消息内容
        :param phone_number:  电话号码
        :param cms_error_list:  可能的错误列表
        :param runtimes: 运行次数
        :return:  True:正常 False:异常
        """
        # 写短信
        for i in range(1, 11):
            time.sleep(10)
            cmgw_index = self.sms_cmgw(msg_content, cms_error_list, runtimes)
            if cmgw_index is False:
                return False
            elif 'ERROR' in cmgw_index:
                self.log_queue.put(['all', '[{}] 第{}次执行AT+CMGW指令返回ERROR'.format(datetime.datetime.now(), i)])
                continue
            else:
                break
        else:
            self.log_queue.put(['all', '[{}] 连续10次执行AT+CMGW指令返回ERROR'.format(datetime.datetime.now())])
            return False
        #  发短信后收短信
        cmss_index = self.sms_cmss(cmgw_index, phone_number, cms_error_list, runtimes)
        if cmss_index is False:
            return False
        elif cmss_index or cmss_index == '0':
            # 读短信 # TODO:之后版本增加短信内容检测
            sms_cmgr_value = self.send_at('AT+CMGR={}'.format(cmss_index), runtimes, 60)
            return_va_cmgr = ''.join(re.findall(r'\+CMGR:\s(.*)', sms_cmgr_value))
            if str(phone_number) in return_va_cmgr:
                self.log_queue.put(['at_log', '[{}] 短信读取成功'.format(datetime.datetime.now())])
            else:
                self.log_queue.put(['all', '[{}] runtime: {} 短信读取失败'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'cmgr_error_times', 1])
                return False
            # 删短信
            cmgd_status = self.send_at('AT+CMGD={},4'.format(cmss_index), runtimes, 10)
            if cmgd_status is False:
                self.log_queue.put(['all', '[{}] runtime: {}短信删除失败'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'cmgd_error_times', 1])
                return False
            else:
                self.log_queue.put(['at_log', '[{}] 短信删除成功'.format(datetime.datetime.now())])

    def sms_cmss(self, cmgw_index, phone_number, cms_error_list, runtimes):
        """
        发送短信
        :param cmgw_index: index
        :param phone_number: 电话号码
        :param cms_error_list: 错误李彪
        :param runtimes: 当前脚本运行次数
        :return: True:正常；False：异常
        """
        # 发送
        cmss_start_time = time.time()
        cmss_return_value = self.send_at('AT+CMSS={},"{}"'.format(cmgw_index, phone_number), runtimes, 120)
        cms_error = [i for i in cms_error_list if 'CMS ERROR: ' + i in cmss_return_value]  # 为了避免号码中有CMS ERROR代码，需要拼接完整
        if cms_error:
            self.log_queue.put(['all', '[{}] runtimes：{} 短信发送失败,上报错误码：+CMS ERROR: {}'.format(datetime.datetime.now(), runtimes, cms_error)])
            self.log_queue.put(['df', runtimes, 'cmss_error_times', 1])
        elif '+CMSS:' in cmss_return_value:
            cmss_send_time = time.time() - cmss_start_time
            self.log_queue.put(['at_log', '[{}] 短信发送成功'.format(datetime.datetime.now())])
            self.log_queue.put(['df', runtimes, 'cmss_send_time', cmss_send_time])
        else:
            self.log_queue.put(['at_log', '[{}] 短信发送失败'.format(datetime.datetime.now())])
            self.log_queue.put(['df', runtimes, 'cmss_error_times', 1])
            return False

        # 接收短信
        return_value_cache = ''
        timeout = 60  # 接收短信超时时间
        recv_message_start_time = time.time()
        while True:
            time.sleep(0.001)
            cmss_port_value = self.readline(self.at_port_opened)
            if cmss_port_value != '':
                return_value_cache += cmss_port_value
                cmss_index = ''.join(re.findall(r'CMTI:\s\"\w+\",(\d+)', cmss_port_value))
                if cmss_index:
                    self.log_queue.put(['at_log', '[{}] 短信接收成功'.format(datetime.datetime.now())])
                    return cmss_index
            if time.time() - recv_message_start_time > timeout:
                self.log_queue.put(['at_log', '[{}]发送短信成功后超过{}s仍未收到短信上报'.format(datetime.datetime.now(), timeout)])
                self.log_queue.put(['df', runtimes, 'cmss_receive_error_times', 1])
                return False

    def sms_cmgw(self, msg_content, cms_error_list, runtimes):
        """
        写短信
        :param msg_content: 短信内容
        :param cms_error_list: 短信错误列表
        :param runtimes: 当前脚本运行次数
        :return: True:正常；Flase：异常
        """
        self.at_port_opened.write('AT+CMGW\r\n'.encode('utf-8'))
        self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), 'AT+CMGW\\r\\n')])
        return_value_cache = ''
        cmgw_start_time = time.time()
        timeout = 60
        flag = False
        while True:
            time.sleep(0.001)
            return_cmgw_value = self.readline(self.at_port_opened)
            if return_cmgw_value != '':
                return_value_cache += return_cmgw_value
                if '>' in return_value_cache:  # 如果出现 > 符号，写入短信后将flag置为True开始接收成功信息
                    if flag is False:
                        self.at_port_opened.write('{}{}'.format(msg_content, chr(0x1a)).encode('utf-8'))
                        self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format(msg_content))])
                        return_value_cache += return_cmgw_value
                        flag = True
                        time.sleep(2)
                if re.findall(r'ERROR\s+', return_cmgw_value) and 'AT+CMGW' in return_value_cache:  # 如果返回ERROR
                    self.log_queue.put(['df', runtimes, 'cmgw_error_times', 1])
                    return return_value_cache
                if flag:
                    cmgw_index = ''.join(re.findall(r'CMGW:\s(\d+)', return_value_cache))
                    if cmgw_index and 'OK' in return_value_cache:
                        self.log_queue.put(['at_log', '[{}] 短信写入成功'.format(datetime.datetime.now())])
                        return cmgw_index
                    if time.time() - cmgw_start_time > timeout:
                        self.log_queue.put(['all', '[{}] runtimes： {}短信写入失败,超时{}s无+CMGW: index上报'.format(datetime.datetime.now(), runtimes, timeout)])
                        self.log_queue.put(['df', runtimes, 'cmgw_error_times', 1])
                        return False
                    # 判断CMS ERROR
                    cms_error = [i for i in cms_error_list if 'CMS ERROR: ' + i in return_value_cache]  # 为了避免号码中有CMS ERROR代码，需要拼接完整
                    if cms_error:
                        self.log_queue.put(['all', '[{}] runtimes： {}短信写入失败,上报错误码：+CMS ERROR: {}'.format(datetime.datetime.now(), runtimes, cms_error)])
                        self.log_queue.put(['df', runtimes, 'cmgw_error_times', 1])
                        return False

    def check_qtemp(self, runtimes):
        """
        温度查询,写入log
        :return:
        """
        for i in range(0, 5):
            time.sleep(3)
            return_qtemp_value = self.send_at('AT+QTEMP', runtimes, 10)
            if return_qtemp_value != '':
                qtemp_key = re.findall(r'QTEMP:\"(.*?)\",\"\d+\"', return_qtemp_value)
                qtemp_value = re.findall(r'QTEMP.*\"(\d+)\"', return_qtemp_value)
                if qtemp_key and qtemp_value:
                    qtemp_dict = dict(zip(qtemp_key, qtemp_value))
                    qtemp_dict_to_str = json.dumps(qtemp_dict)
                    self.log_queue.put(['df', runtimes, 'qtemp_list', qtemp_dict_to_str])
                    return True
                else:
                    continue

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

    def check_module_info(self, imei, runtimes):
        """
        查询和对比模块IMEI、CFUN、CPIN号
        :param imei: 模块的IMEI号
        :param runtimes: 当前脚本的运行次数
        :return: None
        """
        # TODO:重新check此处AT指令的超时时间
        # IMEI
        time.sleep(10)
        imei_value = self.send_at('AT+EGMR=0,7', runtimes, timeout=3)
        imei_re = ''.join(re.findall(r'EGMR: "(\d{15})"', imei_value))
        if imei_re != imei and 'OK' in imei_value:
            self.log_queue.put(['all', '[{}] runtimes:{} 模块IMEI号发生改变'.format(datetime.datetime.now(), runtimes)])
            pause()

        self.send_at('AT+EGMR=0,5', runtimes, timeout=3)
        # CFUN  刚开机可能需要等待几秒CFUN才会变成1
        return_value_re = ''
        for _ in range(20):  # 等待10S
            cfun_value = self.send_at('AT+CFUN?', runtimes, timeout=3)
            return_value_re = ''.join(re.findall(r'CFUN:\s(\d+)', cfun_value))
            if '1' in return_value_re and 'OK' in cfun_value:
                break
            time.sleep(0.5)
        else:
            self.log_queue.put(['df', runtimes, 'cfun_fail_times', 1])
            self.log_queue.put(['all', "[{}] runtimes:{} CFUN值错误，当前CFUN={}".format(datetime.datetime.now(), runtimes, return_value_re)])
            return False
        # CPIN
        for _ in range(20):  # 等待10S
            cpin_value = self.send_at('AT+CPIN?', runtimes, timeout=3)
            cpin_value_re = ''.join(re.findall(r"\+(.*ERROR.*)", cpin_value))
            if cpin_value_re != '':
                time.sleep(0.5)
                continue
            if 'READY' in cpin_value and "OK" in cpin_value:
                break
        else:
            cpin_value = self.send_at('AT+CPIN?', runtimes, timeout=3)
            cpin_value_re = ''.join(re.findall(r"\+(.*ERROR.*)", cpin_value))
            self.log_queue.put(['all', "[{}] runtimes:{} CPIN值异常 {}".format(datetime.datetime.now(), runtimes, cpin_value_re)])
            return False
        return True

    def check_network(self, cpin_flag, runtimes):
        """
        使用AT+COPS?检查当前网络，如果Act有值，则认为注上网。
        :param cpin_flag: False：找网时间从开机到找网；True：找网时间从解PIN到注网。
        :param runtimes: 当前的脚本的运行次数
        :return: None
        """
        creg_value = ''
        cgreg_value = ''
        cereg_value = ''
        net_timeout = 360
        # 找网成功标志
        cops_flag = False
        # others
        network_result = {}  # 每次找网的log，用于写入network_log
        network_result_head = True  # 通过runtimes=1和此参数为True的时候给第一行写上log
        time.sleep(10)
        if cpin_flag:
            self.send_at('AT+CPIN=1234', runtimes, 0.3)
        # 如果需要计算锁PIN找网时间则需要解PIN
        check_network_start_timestamp = time.time()  # 所有找网操作之前的时间戳，用于计算找网时间
        self.log_queue.put(['network_log', '{}runtimes:{}{}'.format('=' * 30, runtimes, '=' * 90)]) if runtimes != 1 else ''  # 每次写入network log

        while True:
            # 获取AT+CSQ的值
            csq_result = self.send_at('AT+CSQ', runtimes)
            csq_value = "".join(re.findall(r'\+CSQ: (\d+),\d+', csq_result))

            # 进行AT+COPS?找网
            cops_result = self.send_at('AT+COPS?', runtimes, timeout=3)  # 找网设置为3S
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', cops_result))
            if cops_value != '':
                self.log_queue.put(['df', runtimes, 'cops_value', cops_value])  # net_fail_times
                self.log_queue.put(['df', runtimes, 'net_register_timestamp', time.time()])  # net_register_timestamp
                cops_flag = True

            # 找网当前时间判断，超时写超时，不超时等0.1S后再找
            check_network_time = round(time.time() - check_network_start_timestamp, 2)
            if check_network_time >= net_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} 找网超时'.format(datetime.datetime.now(), runtimes)])
            else:
                time.sleep(0.5)  # 每次找网的时间间隔，时间太短log会很多

            # NETWORK LOG写入：每次while循环将各个结果写入network_log
            if cops_flag or check_network_time >= net_timeout:  # 如果找网失败或者cops找到网了，需要查一下creg，cereg，cgreg
                cereg_result = self.send_at('AT+CEREG?', runtimes)
                cereg_value = ''.join(re.findall(r'\+CEREG:\s\S+', cereg_result))
                creg_result = self.send_at('AT+CREG?', runtimes)
                creg_value = ''.join(re.findall(r'\+CREG:\s\S+', creg_result))
                cgreg_result = self.send_at('AT+CGREG?', runtimes)
                cgreg_value = ''.join(re.findall(r'\+CGREG:\s\S+', cgreg_result))
            network_result[format("LocalTime", "^28")] = format('[{}]'.format(datetime.datetime.now()), "^28")
            network_result[format("runtimes", "^8")] = format(runtimes, "^8")
            network_result[format("csq_value", "^9")] = format(csq_value, "^9")
            network_result[format("cops_value", "^10")] = format(cops_value, "^10")
            network_result[format("check_network_time", "^18")] = format(check_network_time, "^18")
            network_result[format("creg_value", "^35")] = format(creg_value, "^35")
            network_result[format("cgreg_value", "^35")] = format(cgreg_value, "^35")
            network_result[format("cereg_value", "^35")] = format(cereg_value, "^35")
            if network_result_head and runtimes == 1:  # 只有第一次会写入network_log表头
                network_result_head = False
                self.log_queue.put(['network_log', '\t'.join(network_result.keys())])
                self.log_queue.put(['network_log', '{}runtimes:{}{}'.format('=' * 30, runtimes, '=' * 90)])
            self.log_queue.put(['network_log', '\t'.join(network_result.values())])  # 每次写入network log

            # 只有成功或者失败的时候才会退出
            if cops_flag or check_network_time >= net_timeout:  # 如果找到网或者找网总时间大于360S
                self.log_queue.put(['df', runtimes, 'check_network_time', check_network_time]) if cops_flag else ''  # check_network_time
                self.log_queue.put(['df', runtimes, 'net_fail_times', 0 if cops_flag else 1])  # net_fail_times
                self.send_at('AT+COPS?', runtimes, timeout=180)
                self.send_at('AT+QENG="servingcell"', runtimes, timeout=3)
                self.send_at('AT+QENDC', runtimes, timeout=0.3)
                self.send_at('AT+QSIMWRFREQ', runtimes, timeout=0.3)
                self.qftest_record(runtimes)
                break  # 退出找网

    def check_dssa_network(self, cpin_flag, runtimes):
        """
        新增dssa找网操作，找网超时则暂停脚本
        使用AT+COPS?检查当前网络，如果Act有值，则认为注上网。
        :param cpin_flag: False：找网时间从开机到找网；True：找网时间从解PIN到注网。
        :param runtimes: 当前的脚本的运行次数
        :return: None
        """
        creg_value = ''
        cgreg_value = ''
        cereg_value = ''
        net_timeout = 360
        # 找网成功标志
        cops_flag = False
        # others
        network_result = {}  # 每次找网的log，用于写入network_log
        network_result_head = True  # 通过runtimes=1和此参数为True的时候给第一行写上log
        time.sleep(10)
        if cpin_flag:
            self.send_at('AT+CPIN=1234', runtimes, 0.3)
        # 如果需要计算锁PIN找网时间则需要解PIN
        check_network_start_timestamp = time.time()  # 所有找网操作之前的时间戳，用于计算找网时间
        self.log_queue.put(['network_log', '{}runtimes:{}{}'.format('=' * 30, runtimes,
                                                                    '=' * 90)]) if runtimes != 1 else ''  # 每次写入network log

        while True:
            # 获取AT+CSQ的值
            csq_result = self.send_at('AT+CSQ', runtimes)
            csq_value = "".join(re.findall(r'\+CSQ: (\d+),\d+', csq_result))

            # 进行AT+COPS?找网
            cops_result = self.send_at('AT+COPS?', runtimes, timeout=3)  # 找网设置为3S
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', cops_result))
            if cops_value != '':
                self.log_queue.put(['df', runtimes, 'cops_value', cops_value])  # net_fail_times
                self.log_queue.put(['df', runtimes, 'net_register_timestamp', time.time()])  # net_register_timestamp
                cops_flag = True

            # 找网当前时间判断，超时写超时，不超时等0.1S后再找
            check_network_time = round(time.time() - check_network_start_timestamp, 2)
            if check_network_time >= net_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} 找网超时'.format(datetime.datetime.now(), runtimes)])
                pause()
            else:
                time.sleep(2)  # 每次找网的时间间隔，时间太短log会很多

            # NETWORK LOG写入：每次while循环将各个结果写入network_log
            if cops_flag or check_network_time >= net_timeout:  # 如果找网失败或者cops找到网了，需要查一下creg，cereg，cgreg
                cereg_result = self.send_at('AT+CEREG?', runtimes)
                cereg_value = ''.join(re.findall(r'\+CEREG:\s\S+', cereg_result))
                creg_result = self.send_at('AT+CREG?', runtimes)
                creg_value = ''.join(re.findall(r'\+CREG:\s\S+', creg_result))
                cgreg_result = self.send_at('AT+CGREG?', runtimes)
                cgreg_value = ''.join(re.findall(r'\+CGREG:\s\S+', cgreg_result))
            network_result[format("LocalTime", "^28")] = format('[{}]'.format(datetime.datetime.now()), "^28")
            network_result[format("runtimes", "^8")] = format(runtimes, "^8")
            network_result[format("csq_value", "^9")] = format(csq_value, "^9")
            network_result[format("cops_value", "^10")] = format(cops_value, "^10")
            network_result[format("check_network_time", "^18")] = format(check_network_time, "^18")
            network_result[format("creg_value", "^35")] = format(creg_value, "^35")
            network_result[format("cgreg_value", "^35")] = format(cgreg_value, "^35")
            network_result[format("cereg_value", "^35")] = format(cereg_value, "^35")
            if network_result_head and runtimes == 1:  # 只有第一次会写入network_log表头
                network_result_head = False
                self.log_queue.put(['network_log', '\t'.join(network_result.keys())])
                self.log_queue.put(['network_log', '{}runtimes:{}{}'.format('=' * 30, runtimes, '=' * 90)])
            self.log_queue.put(['network_log', '\t'.join(network_result.values())])  # 每次写入network log

            # 只有成功或者失败的时候才会退出
            if cops_flag or check_network_time >= net_timeout:  # 如果找到网或者找网总时间大于360S
                self.log_queue.put(['df', runtimes, 'check_network_time',
                                    check_network_time]) if cops_flag else ''  # check_network_time
                self.log_queue.put(['df', runtimes, 'net_fail_times', 0 if cops_flag else 1])  # net_fail_times
                self.send_at('AT+COPS?', runtimes, timeout=180)
                self.send_at('AT+QENG="servingcell"', runtimes, timeout=3)
                self.send_at('AT+QENDC', runtimes, timeout=0.3)
                break  # 退出找网

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
                    if re.findall(r'ERROR\s+', return_value) or re.findall(r'Error', return_value) and at_command in return_value_cache:
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
                        if re.findall(r'ERROR\s+', return_value) or re.findall(r'Error', return_value) and at_command in return_value_cache:
                            self.log_queue.put(['all', '[{}] runtimes:{} {}指令返回ERROR'.format(datetime.datetime.now(), runtimes, at_command)]) if 'COPS' not in at_command else ''  # *屏蔽锁pin AT+COPS错误
                            return return_value_cache
                        if time.time() - break_time > 5:
                            break

                    # 跳出While重新发送AT
                    break
        else:
            self.log_queue.put(['all', '[{}] runtimes:{} 连续10次执行{}指令异常'.format(datetime.datetime.now(), runtimes, at_command)])
            pause()

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

    def check_file_size(self, package_path, runtimes):
        """
        检查所有UFS分区文件大小。
        :param package_path: 升级包的路径，用于检查升级包的大小
        :param runtimes: 当前脚本的运行的次数
        :return: True:检查到正确的版本包；False：没有检查到版本包或版本包大小异常
        """
        file_size = os.path.getsize(package_path)
        for i in range(30):
            return_value = self.send_at('AT+QFLST', runtimes, 3)
            return_value = ''.join(re.findall(r'UFS:.*?,(\d+)', return_value))
            if str(file_size) in return_value:  # 如果返回正确的文件大小
                self.log_queue.put(['at_log', '[{}] 版本包大小检查一致'.format(datetime.datetime.now())])
                return True
            elif '+QFLST' in return_value.upper() and str(file_size) not in return_value:  # 返回了文件大小，但是不匹配
                self.log_queue.put(['all', '[{}] runtimes:{} 版本包大小检查不一致'.format(datetime.datetime.now(), runtimes)])
                return False
            else:
                time.sleep(1)
                continue
        else:
            self.log_queue.put(['at_log', '[{}] AT+QFLST未检查到版本包'.format(datetime.datetime.now())])
            return False

    def check_fota_file(self, package_path, runtimes):
        """
        check 指定路径下差分包是否存在
        :param package_path: 差分包路径
        :param runtimes: 当前脚本运行次数
        :return: None
        """
        if not os.path.exists(package_path):
            self.log_queue.put(['all', '[{}]runtimes: {}查询{}路径文件报错,请确认文件是否存在'.format(datetime.datetime.now(), runtimes, package_path)])
            pause()

    def dfota_version_check(self, version, mode, runtimes):
        """
        查询和对比模块版本号
        :param version: 版本号
        :param mode: 模式，是正向还是反向升级
        :param runtimes: 当前脚本运行次数
        :return: None
        """
        return_value = self.send_at('ATI+CSUB', runtimes, 20)
        revision = ''.join(re.findall(r'Revision: (.*)', return_value))
        sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
        version_r = revision + sub_edition
        version_r = re.sub(r'[\r|\n]', '', version_r)
        if version != version_r:
            self.log_queue.put(['df', runtimes, 'fota_a_b_version_fail_times' if mode == 'forward' else 'fota_b_a_version_fail_times', 1])
            self.log_queue.put(['all', '[{}] runtimes:{} 模块版本号检查异常'.format(datetime.datetime.now(), runtimes)])

    def check_dfota_status(self, version, package_error_list, upgrade_error_list, mode, multi_vbat, vbat, is_x6x, runtimes):
        """
        用于DFOTA上报的URC检测
        :param version: 当前升级之后的版本
        :param package_error_list: 文档定义的升级过程中出现升级包错误
        :param upgrade_error_list: 文档定义的升级过程中的非升级包错误
        :param runtimes: 当前脚本的运行次数
        :param mode: 模式，是正向还是反向升级
        :param multi_vbat:mutil fota升级过程中断电
        :param vbat: 是否进行升级过程中断电
        :param is_x6x: 是否为x6x项目
        :return: True：有指定的URC；False：未检测到。
        """
        version = version[1] if mode == 'forward' else version[0]  # 传入的version为列表[version, after_upgrade_version]
        dfota_start_timestamp = time.time()
        driver_check_interval = time.time()
        dfota_timeout = 1000
        vbat_point = self.dfota_powerfailure_time  # 从0S开始计时
        multi_vbat_point = self.multi_vbat_time
        if mode == 'backward' and vbat:
            self.dfota_powerfailure_time += 1
        if mode == 'backward' and multi_vbat:
            self.multi_vbat_time += 0.2
        if self.dfota_powerfailure_time > 80:  # 实测升级时间不超过80S
            self.dfota_powerfailure_time = 0
        if self.multi_vbat_time > 10:
            self.multi_vbat_time = 4
        # 先检测上报START之后再进行断电测试,检测50S
        check_time = time.time()
        while time.time() - check_time < 16:
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if '+QIND: "FOTA","START"' in return_value:
                if vbat_point == 0 and vbat:
                    self.log_queue.put(['df', runtimes, 'fota_a_b_start_timestamp' if mode == 'forward' else 'fota_b_a_start_timestamp', time.time()])
                    self.log_queue.put(['at_log', '[{}] 在升级到FOTA START时断电'.format(datetime.datetime.now())])  # 写入log
                    self.log_queue.put(['at_log', '[{}] 等待3S'.format(datetime.datetime.now())])  # JIRA STSDX55-2067
                    time.sleep(3)
                    return True
                else:
                    break
        else:
            self.log_queue.put(['at_log', '[{}] 未检测到"FOTA","START"'.format(datetime.datetime.now())])  # 写入log
        start_time = time.time() + 1
        while True:
            # AT端口值获取
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                self.urc_checker(return_value, runtimes)
                upgrade_error = [i for i in upgrade_error_list if i in return_value]  # 循环获取log中有无upgrade_error_list中的问题
                package_error = [i for i in package_error_list if i in return_value]  # 循环获取log中有无package_error_list中的问题
                if package_error:
                    self.log_queue.put(['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级过程升级包错误，错误代码{}'.format(datetime.datetime.now(), runtimes, package_error)])
                    print('升级过程中上报错误码{},请联系研发查看/cache/recovery/last_log文件定位问题'.format(package_error))
                    pause()
                    return False
                elif upgrade_error:
                    self.log_queue.put(['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级过程中异常，错误代码{}'.format(datetime.datetime.now(), runtimes, upgrade_error)])
                    print('升级过程中上报错误码{},请联系研发查看/cache/recovery/last_log文件定位问题'.format(upgrade_error))
                    pause()
                    return False
                elif '"FOTA","END",0' in return_value:
                    if vbat:
                        self.log_queue.put(['at_log', '[{}] 升级上报END 0 等待1S后断电'.format(datetime.datetime.now())])  # 写入log
                        time.sleep(1)
                        return True
                    if multi_vbat:
                        self.log_queue.put(['at_log', '[{}]升级上报END 0 等待{}S后断电'.format(datetime.datetime.now(), multi_vbat_point) ]) # 写入LOG
                        time.sleep(multi_vbat_point)
                        return  True
                    self.log_queue.put(['df', runtimes, 'fota_a_b_end_timestamp' if mode == 'forward' else 'fota_b_a_end_timestamp', time.time()])
                    self.log_queue.put(['at_log', '[{}] DFOTA升级成功'.format(datetime.datetime.now())])  # 写入log
                    return True
                elif vbat and vbat_point != 0:  # 不在"FOTA","START"断电时候的情况
                    if time.time() - start_time > vbat_point:
                        self.log_queue.put(['df', runtimes, 'fota_a_b_start_timestamp' if mode == 'forward' else 'fota_b_a_start_timestamp', time.time()])
                        self.log_queue.put(['at_log', '[{}] 在升级到{}秒时断电'.format(datetime.datetime.now(), vbat_point)])  # 写入log
                        if is_x6x is False:  # X55项目随机断电
                            if vbat_point <= 3:
                                time.sleep(3)
                            return True
                        else:  # x6x项目随机断电
                            if vbat_point <= 3:
                                time.sleep(3)
                            return True
            elif (time.time() - dfota_start_timestamp) > dfota_timeout:
                return_value = self.send_at('ATI+CSUB', runtimes, 20)
                revision = ''.join(re.findall(r'Revision: (.*)', return_value))
                sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
                version_r = revision + sub_edition
                version_r = re.sub(r'[\r|\n]', '', version_r)
                if version == version_r:
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级指令发送成功，重启后未上报升级log，但是版本已经升级成功'.format(datetime.datetime.now(), runtimes)])
                    pause()
                self.log_queue.put(['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内DFOTA未升级成功'.format(datetime.datetime.now(), runtimes, dfota_timeout)])
                return False
            elif time.time() - driver_check_interval > 1:
                driver_check_interval = time.time()
                if os.name == "nt":
                    self.check_port(runtimes)
                else:
                    self.check_port(runtimes)
            if time.time() - start_time > vbat_point and vbat and vbat_point != 0:
                self.log_queue.put(
                    ['df', runtimes, 'fota_a_b_start_timestamp' if mode == 'forward' else 'fota_b_a_start_timestamp',
                     time.time()])
                self.log_queue.put(['at_log', '[{}] 在升级到{}秒时断电'.format(datetime.datetime.now(), vbat_point)])  # 写入log
                if is_x6x is False:  # X55项目随机断电
                    if vbat_point <= 3:
                        time.sleep(3)
                    return True
                else:  # x6x项目随机断电
                    if vbat_point <= 3:
                        time.sleep(3)
                    return True

    def fota_urc_check(self, at_port, dm_port, runtimes):
        check_time = time.time()
        while True:
            time.sleep(0.01)
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                if '"FOTA","END",505' in return_value:
                    self.log_queue.put(['all', '[{}] runtimes:{} 差分包检查错误，错误代码:505'.format(datetime.datetime.now(), runtimes)])
                    pause()
            if time.time() - check_time > 1:
                check_time = time.time()
                port_list = self.get_port_list()
                if at_port not in port_list and dm_port not in port_list:
                    return True

    def fota_online_urc_check(self, online_error_list, at_port, dm_port, runtimes):
        """
        DFOTA在线升级指令升级返回OK后，再次返回例如"HTTPEND",0
        此函数就是为了检测版本包下载完成的标志
        :param online_error_list: 下载包过程中可能出现的错误 目前： [601， 701]
        :param at_port: AT口，用作检查端口
        :param dm_port: DM口，用作检查端口
        :param runtimes: 脚本运行次数
        :return: True:下载成功；False：下载失败
        """
        download_start_timestamp = time.time()
        download_timeout = 300
        while True:
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                self.urc_checker(return_value, runtimes)
                download_error_list = [i for i in online_error_list if i in return_value]
                if download_error_list:
                    self.log_queue.put(['all', '[{}] runtimes:{} 下载升级包错误，错误代码{}'.format(datetime.datetime.now(), runtimes, download_error_list)])
                    return False
                elif 'END",0' in return_value:
                    while True:
                        time.sleep(0.01)
                        return_value = self.readline(self.at_port_opened)
                        port_list = self.get_port_list()
                        # TODO:修改此处
                        if at_port and dm_port not in port_list:
                            self.log_queue.put(['at_log', '[{}] 升级包下载成功'.format(datetime.datetime.now())])  # 写入log
                            return True
                        if '"FOTA","END",505' in return_value:
                            self.log_queue.put(['all', '[{}] runtimes:{} 差分包检查错误，错误代码:505'.format(datetime.datetime.now(), runtimes)])
                            pause()
            elif time.time() - download_start_timestamp > download_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未检查到DFOTA升级包下载完成的URC'.format(datetime.datetime.now(), runtimes, download_timeout)])
                return False

    def data_interface(self, mode, debug, runtimes):
        """
        data_interface指令相关操作
        :param mode: 0：设置0,0；1：设置1,1；2，检查0，0；3，检查1，1
        :param debug: 设置脚本遇到异常是停止还是继续运行False：继续运行；True：停止脚本
        :param runtimes: 当前runtimes
        :return:
        """
        time.sleep(5)  # 上报URC后等待5S才会发AT
        if mode == 0 or mode == 1:
            command_string = '0,0' if mode == 0 else '1,0'
            self.send_at('at+qcfg="data_interface",{}'.format(command_string), runtimes)
            for i in range(10):
                time.sleep(1)
                data_interface = self.send_at('at+qcfg="data_interface"', runtimes)
                if ',{}'.format(command_string) in data_interface:
                    return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} atfwd异常，at+qcfg="data_interface"设置为{}后，查询仅返回OK'.format(datetime.datetime.now(), runtimes, command_string)])
                self.log_queue.put(['df', runtimes, 'data_interface_value_error_times', 1])
                if debug:
                    pause()
        elif mode == 2 or mode == 3:
            command_string = '0,0' if mode == 2 else '1,0'
            for i in range(10):
                time.sleep(1)
                data_interface = self.send_at('at+qcfg="data_interface"', runtimes)
                if ',{}'.format(command_string) in data_interface:
                    return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} atfwd异常，at+qcfg="data_interface"查询预期{}失败，仅返回OK'.format(datetime.datetime.now(), runtimes, command_string)])
                self.log_queue.put(['df', runtimes, 'data_interface_value_error_times', 1])
                if debug:
                    pause()

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

    def switch_slot(self, imei, is_vbat, runtimes):
        """
        查询当前在哪个卡槽，然后切换卡槽。
        :param imei: 模块当前IMEI
        :param is_vbat: 是否上报ready前进行断电
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
                if is_vbat:
                    self.log_queue.put(['at_log', '[{}] 上报ready前进行断电'.format(datetime.datetime.now())])
                    return True
                self.check_cpin(runtimes)  # 检查CPIN: READY
                self.check_module_info(imei, runtimes)
                return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} 卡槽1切换卡槽2失败！'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'switch_error_times', 1])
                return False
        else:
            return_value_slot = self.send_at('AT+QUIMSLOT=1', runtimes, timeout=3)
            if return_value_slot:
                self.log_queue.put(['df', runtimes, 'switch_time', time.time() - start_time])
                if is_vbat:
                    self.log_queue.put(['at_log', '[{}] 上报ready前进行断电'.format(datetime.datetime.now())])
                    return True
                self.check_cpin(runtimes)  # 检查CPIN: READY
                self.check_module_info(imei, runtimes)
                return True
            else:
                self.log_queue.put(['all', '[{}] runtimes:{} 卡槽2切换卡槽1失败！'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'switch_error_times', 1])
                return False

    def cfun_change(self, runtimes):
        value = random.choice(['0', '1', '4'])
        self.send_at('AT+CFUN?', runtimes, timeout=15)
        for i in range(1, 6):
            self.send_at('AT+CFUN={}'.format(value), runtimes, timeout=15)
            cfun_value = self.send_at('AT+CFUN?', runtimes, timeout=15)
            cfun_value_re = re.findall(r'CFUN:\s(\d+)', cfun_value)
            if value in cfun_value_re:
                break
            else:
                self.log_queue.put(['all', '[{}] runtimes:{}第{}次切换CFUN为{}失败！'.format(datetime.datetime.now(), runtimes, i, value)])
                self.log_queue.put(['df', runtimes, 'cfun_fail_times', i])
        else:
            self.log_queue.put(['all', '[{}] 切换CFUN为{}连续五次失败！'.format(datetime.datetime.now(), value)])
            pause()
        if value == '1':
            time.sleep(3)   # 切换成功后等待3S再找网
            self.check_network(False, runtimes)
        elif value == '0':
            return True
        elif value == '4':
            time.sleep(0.1)
            self.send_at('AT+QCCID', runtimes, timeout=0.3)
            self.send_at('AT+CPMS?', runtimes, timeout=0.3)

    def qfirehose_version_check(self, version, runtimes):
        """
        查询和对比模块版本号
        :param version: 当前模块的版本号
        :param runtimes: 当前脚本的运行次数
        :return: None
        """
        return_value = self.send_at('ATI+CSUB', runtimes, 20)
        revision = ''.join(re.findall(r'Revision: (.*)', return_value))
        sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
        version_r = revision + sub_edition
        version_r = re.sub(r'[\r|\n]', '', version_r)
        if version != version_r:
            self.log_queue.put(['df', runtimes, 'qfirehose_version_fail_times', 1])
            self.log_queue.put(['all', '[{}] runtimes:{} 模块版本号检查失败,当前版本为{}'.format(datetime.datetime.now(), runtimes, version_r)])
            self.log_queue.put(['at_log', '[{}] 升级后版本不一致，升级失败，重新开始升级'.format(datetime.datetime.now())])
            return False

    def upl_package_at(self, package_name, package_path, up_vbat, runtimes):
        """
        AT方式上传文件至UFS分区
        :param package_name: 文件名称
        :param package_path: 本地文件存放路径
        :param package_path: 上传文件超时时间
        :param up_vbat: 上传过程中是否断电
        :param runtimes:
        :return:
        """
        file_size = os.path.getsize(package_path)
        upl_timeout = (round(file_size / (1024 ** 2), 3) * 2 + 20) * 60
        self.at_port_opened.write('AT+QFUPL="{}",{}\r\n'.format(package_name, file_size).encode('utf-8'))
        self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format('AT+QFUPL="{}",{}'.format(package_name, file_size)))])
        md = hashlib.md5()
        return_value_cache = ''
        encryption = ''
        up_flag = False
        up_file_start_time = time.time()
        urc_timeout = 60  # 上传成功后 urc上报超时时间
        upl_end_time = 0.0
        while True:
            time.sleep(0.001)
            return_upl_value = self.readline(self.at_port_opened)
            if return_upl_value != '':
                return_value_cache += '[{}] {}'.format(datetime.datetime.now(), return_upl_value)
                if re.search('CONNECT', str(return_value_cache)) and up_flag is False:
                    self.log_queue.put(['at_log', '[{}]文件正在上传中,请耐心等待...'.format(datetime.datetime.now())])
                    if up_vbat:
                        return False
                    up_size = 0
                    ne_size = file_size
                    with open(package_path, 'rb+') as f:
                        for i in range(ne_size // 1024 + 2):
                            self.logger.info('文件上传过程中...')
                            if ne_size <= 1024:
                                data_str = f.read(ne_size)
                                up_size += ne_size
                            else:
                                data_str = f.read(1024)
                                up_size += 1024
                                ne_size = ne_size - 1024
                            self.at_port_opened.write(data_str)
                            md.update(data_str)  # 加密传输文件(byte)
                            if up_size == file_size:
                                up_flag = True
                                encryption = md.hexdigest()
                                upl_end_time = time.time()
                                break
                            if time.time() - up_file_start_time > upl_timeout:
                                self.log_queue.put(['all', '[{}]runtimes: {}上传文件超时{}S'.format(datetime.datetime.now(), runtimes, upl_timeout)])
                                self.send_at('AT+QFDEL="{}"'.format(package_name), runtimes, 3)
                                self.log_queue.put(['df', runtimes, 'upl_fail_times', 1])
                                return False
                    self.log_queue.put(['at_log', '[{}]文件上传完成, 文件的MD5值:{}'.format(datetime.datetime.now(), encryption)])
                if re.search('ERROR', return_upl_value):
                    result = re.search(r'\+CME ERROR: (\d+)', return_upl_value)
                    code = int(result.group(1))
                    self.log_queue.put(['all', '[{}]runtimes:{}AT+QFUPL命令报错码：{}'.format(datetime.datetime.now(), runtimes, code)])
                    self.log_queue.put(['df', runtimes, 'upl_fail_times', 1])
                    return False
                if time.time() - up_file_start_time > 60 and 'CONNECT' not in return_value_cache:
                    # 未收到connect返回 可能dump
                    self.log_queue.put(['at_log', '[{}]runtimes:{}超时60S未收到CONNECT'.format(datetime.datetime.now(), runtimes)])
                    self.check_port(runtimes)
                    time.sleep(5)
                    return False
                if up_flag:
                    if re.search(r'\+QFUPL: ', return_value_cache) and 'OK' in return_value_cache:
                        return_size_list = re.findall(r'\+QFUPL: (\d+)', return_value_cache)
                        return_size_tostr = ''.join(return_size_list)
                        if int(return_size_tostr) == file_size:
                            self.log_queue.put(['at_log', '[{}]文件上传成功'.format(datetime.datetime.now())])
                            self.log_queue.put(['df', runtimes, 'upl_file_time', time.time() - up_file_start_time])
                            return True
                    if time.time() - upl_end_time > urc_timeout:
                        self.log_queue.put(['all', '[{}]超时{}s无+QFUPL：上报'.format(datetime.datetime.now(), urc_timeout)])
                        return False

    def dwl_package_at(self, file_size, package_name, dwl_timeout, runtimes):
        """
        AT方式下载文件
        :param file_size: 文件大小
        :param package_name: 文件名
        :param dwl_timeout: 下载文件超时时间
        :param runtimes:
        :return:
        """
        dwl_start_time = time.time()
        return_dwl_value = self.send_at('AT+QFDWL="{}"'.format(package_name), runtimes, dwl_timeout)
        if return_dwl_value != '':
            if re.search(r'\+QFDWL: (\d+),(.*)', return_dwl_value):
                dwl_result = re.search(r'\+QFDWL: (\d+),(.*)', return_dwl_value)
                if int(dwl_result.group(1)) == file_size:
                    self.log_queue.put(['at_log', '[{}]文件下载成功'.format(datetime.datetime.now())])
                    self.log_queue.put(['df', runtimes, 'dwl_file_time', time.time() - dwl_start_time])
                    return True
            elif re.search(r'\+CME ERROR: (\d+)', return_dwl_value):
                result = re.search(r'\+CME ERROR: (\d+)', return_dwl_value)
                code = int(result.group(1))
                if code == 405:
                    self.log_queue.put(['all', '[{}]runtimes:{}AT命令报错码：{}文件未发现'.format(datetime.datetime.now(), runtimes, code)])
                    self.log_queue.put(['df', runtimes, 'dwl_fail_times', 1])
                    return False
                elif code == 426:
                    self.log_queue.put(['all', '[{}]runtimes:{}AT命令报错码：{}文件已打开'.format(datetime.datetime.now(), runtimes, code)])
                    self.log_queue.put(['df', runtimes, 'dwl_fail_times', 1])
                    return False
                else:
                    self.log_queue.put(['all', '[{}]runtimes:{}AT命令报错码：{}'.format(datetime.datetime.now(), runtimes, code)])
                    self.log_queue.put(['df', runtimes, 'dwl_fail_times', 1])
                    return False

    def qfopen_package_at(self, package_name, qfopen_mode, runtimes):
        """
        打开文件
        :param package_name:
        :param qfopen_mode:
        0:不存在，新建  存在则不覆盖读写模式打开文件（默认打开方式）
        1:不存在，新建 存在则擦除文件（文件名保留，内容被擦除）
        2:不存在，报错  存在则只读形式打开文件
        :param runtimes:
        :return:
        """
        qfopen_return_value = self.send_at('AT+QFOPEN="{}",{}'.format(package_name, qfopen_mode), runtimes)
        if qfopen_return_value != '':
            if re.search(r'\+QFOPEN: (\d+)', qfopen_return_value):
                qfopen_result = re.search(r'\+QFOPEN: (\d+)', qfopen_return_value)
                if int(qfopen_result.group(1)):
                    self.log_queue.put(['at_log', '[{}]文件打开成功'.format(datetime.datetime.now())])
                    qfopen_index = int(qfopen_result.group(1))
                    self.send_at('AT+QFOPEN?', runtimes)
                    self.send_at('AT+QFCLOSE={}'.format(qfopen_index), runtimes)
                    return True
            elif re.search('ERROR', qfopen_return_value):
                result = re.search(r'\+CME ERROR: (\d+)', qfopen_return_value)
                code = int(result.group(1))
                error_dict = {406: '无效文件名', 410: '文件打开失败', 421: '超时', 426: '文件已打开'}
                if code in error_dict.keys():
                    self.log_queue.put(['all', '[{}]runtimes:{}AT命令报错码：{}{}'.format(datetime.datetime.now(), runtimes, code, error_dict[code])])
                else:
                    self.log_queue.put(['all', '[{}]runtimes:{}AT命令报错码：{}'.format(datetime.datetime.now(), runtimes, code)])
                self.log_queue.put(['df', runtimes, 'open_fail_times', 1])
                return False

    def qfdel_package_at(self, runtimes):
        """
        删除文件
        :param runtimes:
        :return:
        """
        qfdel_timeout = 60
        while True:
            time.sleep(0.001)
            del_return_value = self.send_at('AT+QFDEL="*"', runtimes)
            qfdel_start_time = time.time()
            if re.search('ERROR', del_return_value):
                continue
            if time.time() - qfdel_start_time > qfdel_timeout:
                self.log_queue.put(['all', '[{}]runtimes:{}超时{}S删除文件失败'.format(datetime.datetime.now(), runtimes, qfdel_timeout)])
                self.log_queue.put(['df', runtimes, 'del_fail_times', 1])
                return False
            if 'OK' in del_return_value:
                return True

    def ufs_updw_file(self, package_name, package_path, qfopen_mode, up_vbat, runtimes):
        """
        :param package_name:
        :param package_path:
        :param qfopen_mode:
        :param up_vbat:
        :param runtimes:
        :return:
        """
        # dwl_file_timeout = (round(file_size / (1024 ** 2), 3) / 2) * 60
        # 上传文件
        self.log_queue.put(['at_log', '[{}]文件上传前查询QFLST'.format(datetime.datetime.now())])
        file_value = self.send_at('AT+QFLST="*"', runtimes)
        if package_name in file_value:
            self.log_queue.put(['at_log', '[{}]文件上传前查询到待上传文件已存在,进行删除后再上传'.format(datetime.datetime.now())])
            self.qfdel_package_at(runtimes)
        time.sleep(2)
        upl_return_value = self.upl_package_at(package_name, package_path, up_vbat, runtimes)
        if upl_return_value:
            self.log_queue.put(['at_log', '[{}]文件上传成功后查询QFLST'.format(datetime.datetime.now())])
            self.send_at('AT+QFLST="*"', runtimes)
            # TODO 下载文件（现有问题 sw建议上此功能后再加）
            dwl_timeout = 60
            file_size = os.path.getsize(package_path)
            self.dwl_package_at(file_size, package_name, dwl_timeout, runtimes)
            # 打开文件
            open_return_value = self.qfopen_package_at(package_name, qfopen_mode, runtimes)
            if open_return_value:
                # 删除文件
                del_status = self.qfdel_package_at(runtimes)
                if del_status:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return True

    def check_atd(self, number, ATS_time, runtimes):
        # 查询APN等信息
        self.send_at('AT+QCFG="ims"', runtimes, timeout=1)
        self.send_at('AT+CGPADDR', runtimes, timeout=1)
        self.send_at('AT+CGDCONT?', runtimes, timeout=1)
        # 进行拨号
        return_val = self.send_at('ATD{};'.format(number), runtimes, timeout=5)
        if 'OK' not in return_val:
            self.log_queue.put(['df', runtimes, 'ATD_Fail_times', 1])
            return False
        # CLCC判断拨号是否成功
        time.sleep(ATS_time + 5)    # 等待自动接听后再查询
        timeout = 30
        for i in range(timeout):
            return_value = self.send_at('AT+CLCC;', runtimes, timeout=1)
            return_value_re = re.findall(r'CLCC:\s\d+,\d+,(\d+),\d+,\d+,\"(\d+)\".*', return_value)  # +CLCC: 3,0,0,0,0,"10000",129\r\n
            if return_value_re:
                for (status, phone_number) in return_value_re:
                    if '0' in status and number in phone_number:
                        self.send_at('ATH;', runtimes, timeout=1)
                        time.sleep(0.5)
                        return True
            time.sleep(1)
        else:
            self.log_queue.put(['all', '[{}] runtimes:{} 拨号成功后连续{}S, AT+CLCC?未检测到stat为0'.format(datetime.datetime.now(), runtimes, timeout)])
            return False

    def cefs_random(self, runtimes, mode):
        """
        使用AT指令随机擦除Cefs分区Block
        """
        cefs_restore = self.send_at('AT+QPRTPARA=4', runtimes, timeout=3)
        cefs_restore_befor = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', cefs_restore))
        self.cefs_restore_times = int(cefs_restore_befor)
        if mode == "cefs":
            for i in range(20):
                self.send_at('AT+QNAND="EBLOCK","0:EFS2",{}'.format(random.randrange(1, 89)), runtimes, timeout=3)
        if mode == "usrdata":
            self.at_port_opened.write('AT+QFASTBOOT\r\n'.encode('utf-8'))
            self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), 'AT+QFASTBOOT\\r\\n')])
            time.sleep(3)
            self.log_queue.put(['at_log', "[{}] 执行fastboot erase usrdata".format(datetime.datetime.now())])
            fast_boot = subprocess.Popen('fastboot erase usrdata', stdout=PIPE, stderr=STDOUT, shell=True)
            start_time = time.time()
            while True:
                time.sleep(0.001)
                fast_boot_content = fast_boot.stdout.readline().decode("UTF-8")
                if fast_boot_content != '':
                    self.log_queue.put(['at_log', "[{} Recv]{} ".format(datetime.datetime.now(), fast_boot_content)])
                if time.time() - start_time > 2:
                    fast_boot.terminate()
                    fast_boot.wait()
                    break
            self.log_queue.put(['at_log', "[{}] 执行fastboot reboot".format(datetime.datetime.now())])
            fast_boot_reboot = subprocess.Popen('fastboot reboot', stdout=PIPE, stderr=STDOUT, shell=True)
            time_stamp = time.time()
            while True:
                time.sleep(0.001)
                fast_boot_reboot_content = fast_boot_reboot.stdout.readline().decode("UTF-8")
                if fast_boot_reboot_content != '':
                    self.log_queue.put(['at_log', "[{} Recv]{} ".format(datetime.datetime.now(), fast_boot_reboot_content)])
                if time.time() - time_stamp > 2:
                    fast_boot_reboot.terminate()
                    fast_boot_reboot.wait()
                    break

    def check_pb_done(self, check_time=50):
        """
        检测PB DONE上报
        :param check_time: 检测时间
        :return:
        """
        start_time = time.time()
        while time.time() - start_time < check_time:
            read_value = self.readline(self.at_port_opened)
            if 'PB DONE' in read_value:
                self.log_queue.put(['at_log', "[{}] 已检测到PB DONE上报".format(datetime.datetime.now())])
                return True
        else:
            self.log_queue.put(['at_log', "[{}] {}S内未检测到PB DONE上报，不再检测".format(datetime.datetime.now(), check_time)])

    def cefs_restore(self, mode, runtimes):
        cefs_restore = self.send_at('AT+QPRTPARA=4', runtimes, timeout=3)
        cefs_restore_re = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', cefs_restore))
        if mode == 'cefs':
            if int(cefs_restore_re) != self.cefs_restore_times:
                self.log_queue.put(['at_log', "[{}] AT+QPRTPARA=4查询发现还原动作！".format(datetime.datetime.now())])
                self.log_queue.put(['at_log', "[{}] 还原前参数为{},还原后参数为{}".format(datetime.datetime.now(), self.cefs_restore_times, cefs_restore_re)])
                self.log_queue.put(['df', runtimes, 'cefs_restore_times', 1])
                self.cefs_restore_times = int(cefs_restore_re)
            else:
                self.log_queue.put(['at_log', "[{}] AT+QPRTPARA=4查询未发现还原动作！".format(datetime.datetime.now())])
                self.log_queue.put(['df', runtimes, 'restore_times', 0])
        if mode == 'usrdata':
            if int(cefs_restore_re) != self.cefs_restore_times:
                self.log_queue.put(['at_log', "[{}] AT+QPRTPARA=4查询发现还原动作！".format(datetime.datetime.now())])
                self.log_queue.put(['at_log', "[{}] 还原前参数为{},还原后参数为{}".format(datetime.datetime.now(), self.cefs_restore_times, cefs_restore_re)])
                self.log_queue.put(['df', runtimes, 'usrdata_restore_times', 1])
                self.cefs_restore_times = int(cefs_restore_re)
            else:
                self.log_queue.put(['at_log', "[{}] AT+QPRTPARA=4查询未发现还原动作！".format(datetime.datetime.now())])
                self.log_queue.put(['df', runtimes, 'restore_times', 0])

    def qcfg_usbcfg(self, mode, runtimes):
        """

        :param mode: True:开启adb False:关闭ADB
        :param runtimes:
        :return:
        """

        time_start = time.time()
        if mode:
            while True:
                time.sleep(1)
                return_value = self.send_at('at+qcfg="usbcfg"', runtimes)
                if return_value != '':
                    adb_value = re.search(r'0x2C7C,0x0800,(\d,){5}(\d+)', str(return_value)).group(2)
                    if adb_value and adb_value == '1':
                        return True
                    elif adb_value == '0':
                        return_value = self.send_at('at+qcfg="usbcfg",0x2C7C,0x0800,1,1,1,1,1,1', runtimes, 10)
                        if 'OK' in return_value:
                            continue
                    elif time.time() - time_start > 60:
                        self.log_queue.put(['all', '[{}] runtimes:{}60s内开启ADB失败，请确认ATFWD有无异常'.format(datetime.datetime.now(), runtimes)])
                        pause()
        else:
            return_value = self.send_at('at+qcfg="usbcfg",0x2C7C,0x0800,1,1,1,1,1,0', runtimes, 10)
            if 'OK' in return_value:
                return True
            else:
                self.log_queue.put(['all', '[{}]runtimes:{}ADB关闭失败'.format(datetime.datetime.now(), runtimes)])
                pause()

    def act_deact_init(self, contextID, context_type, apn, runtimes):
        """
        激活去激活初始化
        :param contextID:
        :param context_type:
        :param apn:
        :param runtimes:
        :return:
        """
        self.send_at('AT+QICSGP={},{},"{}"'.format(contextID, context_type, apn), runtimes)
        self.check_network(False, runtimes)
        self.send_at('AT+QIACT?', runtimes, 150)
        self.send_at('AT&W', runtimes, 0.3)

    def qprtpara_restore(self, restore_times, runtimes):
        """
        还原次数统计
        :param restore_times:
        :param runtimes:
        :return:
        """
        qprtpara_return = self.send_at('AT+QPRTPARA=4', runtimes, timeout=3)
        if qprtpara_return != '':
            restore = ''.join(re.findall(r'\+QPRTPARA:\s\d+,(\d+),.*', qprtpara_return))
            if int(restore) != restore_times:
                self.log_queue.put(['all', '[{}]前{}次发生还原{}次'.format(datetime.datetime.now(), runtimes, restore)])
                self.log_queue.put(['df', runtimes, 'qprtpara_restore_times', restore])
                return True

    def activate_pdp(self, contextID, runtimes):
        """
        激活PDP
        :param contextID:
        :param runtimes:
        :return:
        """
        act_time_start = time.time()
        # 激活
        while True:
            time.sleep(0.001)
            qiact_return_value = self.send_at('AT+QIACT={}'.format(contextID), runtimes, 150)
            if qiact_return_value != '':
                if 'OK' in qiact_return_value:
                    break
                if 'ERROR' in qiact_return_value:
                    # 存在已被激活可能 去激活
                    self.send_at('AT+QIDEACT={}'.format(contextID), runtimes, 150)
                    continue
                if time.time() - act_time_start > 60:
                    self.log_queue.put(['all', '[{}]:runtimes:{}PDP激活失败'.format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'activate_fail_times', 1])
                    return False
            else:
                return False
        # PDP Address check
        self.send_at('AT+QIACT?', runtimes, 150)
        addr_value = self.send_at('AT+CGPADDR={}'.format(contextID), runtimes, 150)
        if addr_value != '':
            if re.search(r'\"(\d?.*)\"', addr_value).group(0):
                activate_time = time.time() - act_time_start
                self.log_queue.put(['df', runtimes, 'activate_time', activate_time])
                return True
            else:
                self.log_queue.put(['all', '[{}]runtimes:{}PDP地址获取失败'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'activate_fail_times', 1])
                return False
        else:
            return False

    def deactivate_pdp(self, contextID, runtimes):
        """
        去激活PDP
        :param contextID:
        :param runtimes:
        :return:
        """
        deact_start_time = time.time()
        while True:
            time.sleep(0.001)
            deact_return_value = self.send_at('AT+QIDEACT={}'.format(contextID), runtimes, 150)
            if deact_return_value != '':
                if 'OK' in deact_return_value:
                    deactivate_time = time.time() - deact_start_time
                    self.log_queue.put(['df', runtimes, 'deactivate_time', deactivate_time])
                    return True
                elif time.time() - deact_start_time > 60:
                    self.log_queue.put(['all', '[{}]runtimes:{}PDP去激活失败'.format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'deactivate_fail_times', 1])
                    return False
                else:
                    continue
            else:
                return False

    def client_connect(self, connection_type, server_ip, server_port, access_mode, runtimes):
        '''
        连接TCP
        :param connection_type: TCP或UDP连接方式
        :param server_ip: tcp服务器地址
        :param server_port: tcp端口
        :param access_mode: buffer模式：0，push模式：1
        :param runtimes: 运行次数
        :return: 连接成功返回True，连续失败三次Deact模块
        '''
        for i in range(4):
            if i == 3:
                self.log_queue.put(['all', '[{}]runtimes:{}连续三次建立TCP连接失败,DEACT模块'.format(datetime.datetime.now(), runtimes)])
                return_deact = self.client_deactive(connection_type, server_ip, server_port, access_mode, runtimes)
                if return_deact is False:
                    return False
            return_val = self.send_at('AT+QIOPEN=1,0,"{}","{}",{},0,{}'.format(connection_type, server_ip, server_port, access_mode), runtimes, 150)
            if 'ERROR' in return_val:
                self.at_port_opened.write('AT+QIGETERROR\r\n'.encode('utf-8'))
                start_time = time.time()
                return_err_cache = ''
                while True:
                    time.sleep(0.001)
                    return_err = self.readline(self.at_port_opened)
                    if return_err != '':
                        return_err_cache += return_err
                    if time.time() - start_time > 0.3:
                        break
                retu_re = re.findall(r'QIGETERROR:\s+(?P<QIGETERROR>.*)', return_err_cache)
                self.log_queue.put(['all', '[{}]runtimes:{}建立TCP连接失败，错误描述为{},重新连接'.format(datetime.datetime.now(), runtimes, retu_re)])
                self.close_tcp(runtimes)
                continue
            time.sleep(10)
            return_state_istate = re.findall("[0-9]+", self.send_at('AT+QISTATE?', runtimes))
            return_state_re = return_state_istate[-18]
            if '2' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接已经创建成功'.format(datetime.datetime.now())])
                return True
            elif '0' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接尚未建立'.format(datetime.datetime.now())])
                self.close_tcp(runtimes)
                continue
            elif '1' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端正在连接'.format(datetime.datetime.now())])
                self.close_tcp(runtimes)
                continue
            elif '3' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接正在关闭'.format(datetime.datetime.now())])
                self.close_tcp(runtimes)
                continue
            elif '4' == return_state_re:
                self.log_queue.put(['at_log', '[{}]远程服务器正在关闭客户端连接'.format(datetime.datetime.now())])
                self.close_tcp(runtimes)
                continue

    def client_deactive(self, connection_type, server_ip, server_port, access_mode, runtimes):
        '''
        Deacti模块
        :param connection_type: TCP或UDP连接方式
        :param server_ip: tcp服务器地址
        :param server_port: tcp端口
        :param access_mode: buffer模式：0，push模式：1
        :param runtimes: 运行次数
        :return: 连接成功返回True，失败返回False重启模块
        '''
        for i in range(4):
            if i == 3:
                self.log_queue.put(['all', '[{}]runtimes:{}连续三次DEACT模块后建立TCP连接失败'.format(datetime.datetime.now(), runtimes)])
                return False
            self.send_at('AT+QIDEACT=1', runtimes, 40)
            return_val = self.send_at_two_steps_check('AT+QIOPEN=1,0,"{}","{}",{},0,{}'.format(connection_type, server_ip, server_port, access_mode), runtimes, 150, 'QIOPEN', 150)
            if 'ERROR' in return_val:
                self.at_port_opened.write('AT+QIGETERROR\r\n'.encode('utf-8'))
                start_time = time.time()
                return_err_cache = ''
                while True:
                    time.sleep(0.001)
                    return_err = self.readline(self.at_port_opened)
                    if return_err != '':
                        return_err_cache += return_err
                    if time.time() - start_time > 0.3:
                        break
                retu_re = re.findall(r'QIGETERROR:\s+(?P<QIGETERROR>.*)', return_err_cache)
                self.log_queue.put(['all', '[{}]runtimes:{}建立TCP连接失败，错误描述为{},重新连接'.format(datetime.datetime.now(), runtimes, retu_re)])
                self.close_tcp(runtimes)
                continue
            return_state_istate = re.findall("[0-9]+", self.send_at('AT+QISTATE?', runtimes))
            return_state_re = return_state_istate[-18]
            if '2' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接已经创建成功'.format(datetime.datetime.now())])
                return True
            elif '0' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接尚未建立'.format(datetime.datetime.now())])
                continue
            elif '1' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端正在连接'.format(datetime.datetime.now())])
                continue
            elif '3' == return_state_re:
                self.log_queue.put(['at_log', '[{}]客户端连接正在关闭'.format(datetime.datetime.now())])
                continue
            elif '4' == return_state_re:
                self.log_queue.put(['at_log', '[{}]远程服务器正在关闭客户端连接'.format(datetime.datetime.now())])
                continue

    def client_send_recv_compare(self, connection_mode, access_mode, runtimes):
        """
        发送数据，非透传buffer连接发送完数据后需要执行QIRD进行数据确认，push连接发送成功后会直接返回发送内容
        :param connection_mode:  长连短连，确认是否需要执行QICLOSE关闭tcp连接
        :param access_mode:  0：非透传buffer连接，每次发送完需要确认；1：非透传push连接，每次发送完会直吐发送成功内容
        :param runtimes:    运行次数
        :return:    确认发送成功返回TRUE
        """
        input_val = '0123456789' * 145 + '01234567'
        self.log_queue.put(['at_log', '[{}]发送数据'.format(datetime.datetime.now())])
        self.at_port_opened.write('AT+QISEND=0,1460\r\n'.encode('utf-8'))
        st_time = time.time()
        while True:
            time.sleep(0.001)
            self.readline(self.at_port_opened)
            if time.time() - st_time > 2:
                break
        time.sleep(1)   # 指令文档建议输完QISEND指令后等待500ms再发送内容，此处等待一秒
        if access_mode == 0:    # buffer模式，不会直接返回数据本身
            self.log_queue.put(['df', runtimes, 'buffer_send_start_timestamp', time.time()])
            self.send_at('{}'.format(input_val), runtimes)  # 直接发送内容，会返回send ok
            time.sleep(3)
            for i in range(4):
                return_qird_fir = self.send_at('AT+QIRD=0,1460', runtimes)
                return_qird_sec = self.send_at('AT+QIRD=0,1460', runtimes)
                return_qird = return_qird_fir + return_qird_sec
                if '+QIRD: 1360' in return_qird and '+QIRD: 100' in return_qird:
                    self.log_queue.put(['at_log', '[{}]数据确认发送成功'.format(datetime.datetime.now())])
                    self.log_queue.put(['df', runtimes, 'buffer_send_end_timestamp', time.time()])
                    self.log_queue.put(['df', runtimes, 'buffer_send_success_times', 1])
                    if connection_mode == 1:   # 如果是短连,先断开TCP连接
                        self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
                        self.close_tcp(runtimes)
                        time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                        return True
                    else:
                        time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return True
                elif input_val in return_qird:
                    self.log_queue.put(['at_log', '[{}]数据确认发送成功'.format(datetime.datetime.now())])
                    self.log_queue.put(['df', runtimes, 'buffer_send_end_timestamp', time.time()])
                    self.log_queue.put(['df', runtimes, 'buffer_send_success_times', 1])
                    if connection_mode == 1:   # 如果是短连,先断开TCP连接
                        self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
                        self.close_tcp(runtimes)
                        time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return True
                elif i == 3:
                    self.log_queue.put(['all', '[{}] runtimes:{} buffer模式未读取到发送数据'.format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'buffer_send_end_timestamp', time.time()])
                    self.log_queue.put(['df', runtimes, 'buffer_send_fail_times', 1])
                    if connection_mode == 1:  # 如果是短连,先断开TCP连接
                        self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
                        self.close_tcp(runtimes)
                        time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                        return False
                    else:
                        time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return False
                time.sleep(0.1)     # 防止数据接收不及时
        elif access_mode == 1:  # push模式，发送数据后会直接返回数据本身
            self.log_queue.put(['df', runtimes, 'push_send_start_timestamp', time.time()])
            self.at_port_opened.write('{}\r\n'.format(input_val).encode('utf-8'))
            start_time = time.time()
            return_push_cache = ''
            count = 0
            while True:
                time.sleep(0.001)
                return_push = self.readline(self.at_port_opened)
                if return_push != '':
                    return_push_cache += return_push
                if time.time() - start_time > 3:    # 等待返回结果
                    break
            reval = re.findall(r'\+QIURC: "recv",0,(\d+)', return_push_cache)
            for i in range(len(reval)):
                count += int(reval[i])
            if count == 1460:
                self.log_queue.put(['at_log', '[{}]数据确认发送成功'.format(datetime.datetime.now())])
                self.log_queue.put(['df', runtimes, 'push_send_end_timestamp', time.time()])
                self.log_queue.put(['df', runtimes, 'push_send_success_times', 1])
                if connection_mode == 1:  # 如果是短连,先断开TCP连接
                    self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
                    self.close_tcp(runtimes)
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return True
                else:
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                return True
            else:
                self.log_queue.put(['all', '[{}] runtimes{} push模式数据发送失败'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'push_send_end_timestamp', time.time()])
                self.log_queue.put(['df', runtimes, 'push_send_fail_times', 1])
                self.log_queue.put(['at_log', '[{}],返回内容为{}'.format(datetime.datetime.now(), return_push_cache)])
                if connection_mode == 1:  # 如果是短连,先断开TCP连接
                    self.close_tcp(runtimes)
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return False
                else:
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                    return False

    def close_tcp(self, runtimes):
        for i in range(3):
            return_close = self.send_at('AT+QICLOSE=0', runtimes, 11)
            if 'OK' in return_close:
                self.log_queue.put(['at_log', '[{}]断开TCP连接成功'.format(datetime.datetime.now())])
                return True

    def client_connect_trans(self, connection_type, server_ip, server_port, access_mode, runtimes):    # 透传模式连接TCP
        for i in range(7):
            if i > 2:      # 连续三次建立连接失败则deact模块
                if i == 6:
                    self.log_queue.put(['all', '[{}]runtimes:{}连续三次DEACT模块后建立TCP连接失败'.format(datetime.datetime.now(), runtimes)])
                    return False
                if i == 3:
                    self.log_queue.put(['all', '[{}]runtimes:{}连续三次建立TCP连接失败，DEACT模块'.format(datetime.datetime.now(), runtimes)])
                self.send_at('AT+QIDEACT=1', runtimes, 40)
            self.at_port_opened.write('AT+QIOPEN=1,0,"{}","{}",{},0,{}\r\n'.format(connection_type, server_ip, server_port, access_mode).encode('utf-8'))
            start_tran_time = time.time()
            while True:
                time.sleep(0.001)
                return_val = self.readline(self.at_port_opened)
                if 'CONNECT' in return_val:
                    self.log_queue.put(['at_log', '[{}]TCP透传连接建立成功'.format(datetime.datetime.now())])
                    return True
                if time.time() - start_tran_time > 150:
                    self.log_queue.put(['all', '[{}]  runtimes:{}150S内建立TCP连接失败'.format(datetime.datetime.now(), runtimes)])
                    self.close_tcp(runtimes)
                    break

    def client_connect_trans_init(self, connection_type, server_ip, server_port, access_mode, runtimes):    # 透传模式连接TCP
        for i in range(7):
            if i > 2:      # 连续三次建立连接失败则deact模块
                if i == 6:
                    self.log_queue.put(['all', '[{}]runtimes:{}连续三次DEACT模块后建立TCP连接失败'.format(datetime.datetime.now(), runtimes)])
                    return False
                if i == 3:
                    self.log_queue.put(['all', '[{}]runtimes:{}连续三次建立TCP连接失败，DEACT模块'.format(datetime.datetime.now(), runtimes)])
                self.send_at('AT+QIDEACT=1', runtimes, 40)
            self.at_port_opened.write('AT+QIOPEN=1,0,"{}","{}",{},0,{}\r\n'.format(connection_type, server_ip, server_port, access_mode).encode('utf-8'))
            start_tran_time = time.time()
            while True:
                time.sleep(0.001)
                return_val = self.readline(self.at_port_opened)
                if 'CONNECT' in return_val:
                    self.log_queue.put(['at_log', '[{}]TCP透传连接建立成功'.format(datetime.datetime.now())])
                    self.at_port_opened.write('+++'.encode('utf-8'))
                    while True:
                        time.sleep(0.001)
                        ret = self.readline(self.at_port_opened)
                        if 'OK' in ret:
                            break
                        else:
                            self.at_port_opened.write('+++'.encode('utf-8'))
                            time.sleep(1)
                    return True
                if time.time() - start_tran_time > 10:
                    self.log_queue.put(['all', '[{}]  runtimes:{}150S内建立TCP连接失败'.format(datetime.datetime.now(), runtimes)])
                    self.close_tcp(runtimes)
                    break

    def client_send_recv_compare_tran(self, connect_mode, runtimes):
        if runtimes > 1 and connect_mode == 0:       # 透传模式每次需要执行ATO指令重新建立TCP连接
            self.at_port_opened.write('ATO\r\n'.encode('utf-8'))
        time.sleep(3)   # 重新连接后等待一会再发数据
        input_val = '0123456789' * 145 + '01234567'
        self.log_queue.put(['df', runtimes, 'tran_send_start_timestamp', time.time()])
        self.at_port_opened.write('{}\r\n'.format(input_val).encode('utf-8'))
        start_time = time.time()
        while True:
            time.sleep(0.001)
            return_value = self.readline(self.at_port_opened, 5)
            if input_val in return_value:
                self.log_queue.put(['at_log', '[{}]TCP透传模式发送数据成功，退出连接'.format(datetime.datetime.now())])
                self.log_queue.put(['df', runtimes, 'tran_send_end_timestamp', time.time()])
                self.log_queue.put(['df', runtimes, 'tran_send_success_times', 1])
                self.at_port_opened.write('+++'.encode('utf-8'))
                st = time.time()
                while True:
                    time.sleep(0.001)
                    ret = self.readline(self.at_port_opened)
                    if 'OK' in ret:
                        break
                    elif time.time() - st > 10:     # +++发的过多会导致uart口不通AT
                        self.at_port_opened.write('+++'.encode('utf-8'))
                        time.sleep(1)
                if connect_mode == 1:       # 1:短连，每次发送完数据后需断开连接
                    self.close_tcp(runtimes)
                    time.sleep(60)  # 参考LTE确认发送成功后等待一段时间（60秒）
                else:
                    time.sleep(60)
                return True
            if time.time() - start_time > 10:
                self.log_queue.put(['all', '[{}]TCP透传模式发送数据失败，退出连接'.format(datetime.datetime.now())])
                self.log_queue.put(['df', runtimes, 'tran_send_end_timestamp', time.time()])
                self.log_queue.put(['df', runtimes, 'tran_send_fail_times', 1])
                self.at_port_opened.write('+++'.encode('utf-8'))
                self.at_port_opened.write('+++'.encode('utf-8'))
                st = time.time()
                while True:
                    time.sleep(0.001)
                    ret = self.readline(self.at_port_opened)
                    if 'OK' in ret:
                        break
                    elif time.time() - st > 10:     # +++发的过多会导致uart口不通AT
                        self.at_port_opened.write('+++'.encode('utf-8'))
                        time.sleep(1)
                if connect_mode == 1:
                    self.close_tcp(runtimes)
                    time.sleep(60)  # 参考LTE确认发送失败后等待一段时间（60秒）
                    return False
                time.sleep(60)
                return False

    def recvdata_compare(self, access_mode, recv_data, connection_mode, wait_time, runtimes):
        '''
        buffer模式下模块接收到数据与定义的数据做对比
        :param access_mode: 0:buffer模式， 1:push模式
        :param recv_data: 定义的模块接收到的数据
        :param connection_mode: 长连短连，0：长连，1：短连
        :param wait_time: 服务器发送消息的间隔时间
        :param runtimes:
        :return:
        '''
        if access_mode == 0:    # buffer模式下数据对比
            for i in range(4):
                return_qird = self.send_at('AT+QIRD=0', runtimes)
                if recv_data in return_qird:
                    self.log_queue.put(['at_log', '[{}]数据确认接收成功'.format(datetime.datetime.now())])
                    self.log_queue.put(['df', runtimes, 'send_success_times', 1])
                    return True
                time.sleep(wait_time)
            else:
                self.log_queue.put(['all', '[{}] runtimes:{}模块接收数据与实际下发不匹配,请检查Qserver是否在正常发送数据'.format(datetime.datetime.now(), runtimes)])
                self.log_queue.put(['df', runtimes, 'send_fail_times', 1])
                return False
        elif access_mode == 1:  # push模式下数据对比
            start_time = time.time()
            while True:
                time.sleep(0.001)
                recv = self.readline(self.at_port_opened)
                if recv_data in recv:
                    self.log_queue.put(['at_log', '[{}]数据确认接收成功'.format(datetime.datetime.now())])
                    self.log_queue.put(['df', runtimes, 'send_success_times', 1])
                    if connection_mode == 1:  # 如果是短连,先断开TCP连接
                        self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
                        self.close_tcp(runtimes)
                        return True
                    return True
                if time.time() - start_time > wait_time + 5:
                    self.log_queue.put(['all', '[{}] runtimes:{}模块接收数据与实际下发不匹配,请检查Qserver是否在正常发送数据'.format(datetime.datetime.now(), runtimes)])
                    self.log_queue.put(['df', runtimes, 'send_fail_times', 1])
                    return False

    def many_client_connect(self, connection_type, server_ip, server_port, access_mode, runtimes):
        '''
        连接TCP
        :param connection_type: TCP或UDP连接方式
        :param server_ip: tcp服务器地址
        :param server_port: tcp端口
        :param access_mode: buffer模式：0，push模式：1
        :param runtimes: 运行次数
        :return: 连接成功返回True，连续失败三次Deact模块
        '''
        for j in range(1, 7):
            for i in range(6):
                if i >= 3:
                    self.log_queue.put(['all', '[{}]runtimes:{}连续三次建立TCP连接失败,DEACT模块'.format(datetime.datetime.now(), runtimes)])
                    self.send_at('AT+QIDEACT=1', runtimes, 40)
                return_val = self.send_at('AT+QIOPEN=1,{},"{}","{}",{},0,{}'.format(j, connection_type, server_ip, server_port, access_mode), runtimes, 150)
                if 'ERROR' in return_val:
                    self.at_port_opened.write('AT+QIGETERROR\r\n'.encode('utf-8'))
                    start_time = time.time()
                    return_err_cache = ''
                    while True:
                        time.sleep(0.001)
                        return_err = self.readline(self.at_port_opened)
                        if return_err != '':
                            return_err_cache += return_err
                        if time.time() - start_time > 0.3:
                            break
                    retu_re = re.findall(r'QIGETERROR:\s+(?P<QIGETERROR>.*)', return_err_cache)
                    self.log_queue.put(['all', '[{}]runtimes:{}建立TCP连接失败，错误描述为{},重新连接'.format(datetime.datetime.now(), runtimes, retu_re)])
                    self.close_tcp(runtimes)
                    continue
                time.sleep(10)
                return_state_istate = re.findall("[0-9]+", self.send_at('AT+QISTATE?', runtimes))
                return_state_re = return_state_istate[-18]
                if '2' == return_state_re:
                    self.log_queue.put(['at_log', '[{}]客户端连接已经创建成功'.format(datetime.datetime.now())])
                    break
                elif '0' == return_state_re:
                    self.log_queue.put(['at_log', '[{}]客户端连接尚未建立'.format(datetime.datetime.now())])
                    self.close_tcp(runtimes)
                    continue
                elif '1' == return_state_re:
                    self.log_queue.put(['at_log', '[{}]客户端正在连接'.format(datetime.datetime.now())])
                    self.close_tcp(runtimes)
                    continue
                elif '3' == return_state_re:
                    self.log_queue.put(['at_log', '[{}]客户端连接正在关闭'.format(datetime.datetime.now())])
                    self.close_tcp(runtimes)
                    continue
                elif '4' == return_state_re:
                    self.log_queue.put(['at_log', '[{}]远程服务器正在关闭客户端连接'.format(datetime.datetime.now())])
                    self.close_tcp(runtimes)
                    continue

    def many_client_send_recv_compare(self, connection_mode, runtimes):
        '''
        多路连续收发下确认收发消息是否正常
        :param connection_mode: 0：长连，1：短连
        :param runtimes:
        :return:
        '''
        input_val = '0123456789' * 49 + '01234567'
        for i in range(1, 7):
            self.log_queue.put(['at_log', '[{}]发送数据'.format(datetime.datetime.now())])
            self.at_port_opened.write('AT+QISEND={},500\r\n'.format(i).encode('utf-8'))
            st_time = time.time()
            while True:
                time.sleep(0.001)
                self.readline(self.at_port_opened)
                if time.time() - st_time > 2:
                    break
            self.send_at('{}'.format(input_val), runtimes)  # 直接发送内容，会返回send ok
        for j in range(1, 7):
            return_val = self.send_at('AT+QIRD={}'.format(j), runtimes)
            if input_val in return_val:
                self.log_queue.put(['at_log', '[{}]第{}路数据确认接收成功'.format(datetime.datetime.now(), j)])
                self.log_queue.put(['df', runtimes, 'many_send_success_times', 1])
            else:
                self.log_queue.put(['all', '[{}] runtimes:{}第{}路接收数据与发送不一致'.format(datetime.datetime.now(), runtimes, j)])
                self.log_queue.put(['at_log', '[{}] 实际接收数据为{}'.format(datetime.datetime.now(), return_val)])
                self.log_queue.put(['df', runtimes, 'many_send_fail_times', 1])
        if connection_mode == 1:  # 如果是短连,先断开TCP连接
            self.log_queue.put(['at_log', '[{}]断开TCP连接'.format(datetime.datetime.now())])
            self.close_tcp(runtimes)

    def aqc_init(self, runtimes):
        self.send_at('AT+QMAPWAC=1', runtimes)
        self.send_at('AT+QCFG="pcie/mode",1', runtimes)

    def efs_check(self, qftest_filesize, qftest_file_num, qftest_test_cnt, qftest_write_interval, runtimes):
        efs_test_cmd = f'AT+QFTEST="EFSStressWrite",' \
                       f'1,' \
                       f'{qftest_filesize},' \
                       f'{qftest_file_num},' \
                       f'{qftest_test_cnt},' \
                       f'{qftest_write_interval}'
        efs_status = self.send_at(efs_test_cmd, runtimes, timeout=5)
        if 'Ok:0x0,1' not in efs_status:  # Ok:0x0,1,0,0,10
            self.log_queue.put(['all', '[{}] runtimes:{}指令{}执行异常，返回结果：{}'.format(datetime.datetime.now(), runtimes, efs_test_cmd, efs_status)])
            return False

        cnt = 0
        cur_cnt = 0
        while True:  # 进行： Ok:0x0,1,3,0,10，# 结束： Ok:0x0,0,10,0,0
            time.sleep(30)  # 每隔30S

            # AT+QFTEST="EFS/StressWrite",2
            efs_status = self.send_at('AT+QFTEST="EFSStressWrite",2', runtimes, timeout=5)
            efs_status_regex = re.search(r'Ok:.*?,(\d+),(\d+),(\d+),\d+', efs_status)
            if 'ERROR' in efs_status:
                break
            if efs_status_regex:
                status, cnt_read, cur_cnt_read = efs_status_regex.groups()
                if status == '0':
                    if cnt_read == str(qftest_test_cnt):
                        cnt = qftest_test_cnt
                        cur_cnt = 0
                    break  # 检查结束
                cnt = cnt_read
                cur_cnt = cur_cnt_read

            # AT+QFTEST="EFS/BlockEC"
            block_status = self.send_at('AT+QFTEST="EFSBlockEC"', runtimes, timeout=5)
            if 'ERROR' in block_status:
                break

        write_size = int(cnt) * int(qftest_filesize) * int(qftest_file_num) + int(cur_cnt) * int(qftest_filesize)
        write_size = write_size / 1024 / 1024 / 1024
        self.log_queue.put(['df', runtimes, 'write_size', write_size])

        qprtpara_status = self.send_at('AT+QPRTPARA=4', runtimes, timeout=5)
        qprtpara_status_regex = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', qprtpara_status))
        if qprtpara_status_regex:
            self.log_queue.put(['df', runtimes, 'restore_times', int(qprtpara_status_regex)])

    def block_test(self, qftest_partition, qftest_block_id, qftest_erase_write_times, qftest_data, qftest_timer, runtimes):
        flash_test_command = f'AT+QFTEST=' \
                             f'"FlashStrTest",' \
                             f'"{qftest_partition}",' \
                             f'1,' \
                             f'{qftest_block_id},' \
                             f'{qftest_erase_write_times},' \
                             f'{qftest_data},' \
                             f'{qftest_timer}'
        flash_status = self.send_at(flash_test_command, runtimes, timeout=5)
        if 'Ok:0x0,1' not in flash_status:  # Ok:0x0,1,79,0,300000
            self.log_queue.put(['all', '[{}] runtimes:{}指令{}执行异常，返回结果：{}'.format(datetime.datetime.now(), runtimes, flash_test_command, flash_status)])
            return False

        cnt = 0
        cnt_last = 0
        while True:

            time.sleep(30)  # 每隔30S

            flash_status = self.send_at(f'AT+QFTEST="FlashStrTest","{qftest_partition}",2', runtimes, timeout=15)
            flash_status_regex = re.search(r'.*:.*,(\d+),\d+,(\d+),\d+', flash_status)
            if 'ERROR' in flash_status.upper():
                break

            if flash_status_regex:
                status, cnt_cur = flash_status_regex.groups()
                if status == '0':  # 已经停止了测试
                    self.logger.info('cnt_cur:{}\nqftest_erase_write_times:{}\ncnt_last:{}\n'.format(cnt_cur, qftest_erase_write_times, cnt_last))
                    if cnt_cur == str(qftest_erase_write_times):  # 测试次数和设置相同: Ok:0x0,0,79,2000,0
                        cnt = qftest_erase_write_times
                    else:  # 次数不等
                        cnt = cnt_last
                    break
                cnt_last = cnt_cur  # 记录最新的值

        if getattr(self, 'block_erase_times', None) is None:  # 没有发现block_erase_times变量
            setattr(self, 'block_erase_times', 0)
        self.block_erase_times += int(cnt)  # noqa
        self.log_queue.put(['df', runtimes, 'block_erase_times', self.block_erase_times])  # noqa

        qprtpara_status = self.send_at('AT+QPRTPARA=4', runtimes, timeout=5)
        qprtpara_status_regex = ''.join(re.findall(r'\+QPRTPARA:\s\d*,(\d*)', qprtpara_status))
        if qprtpara_status_regex:
            self.log_queue.put(['df', runtimes, 'restore_times', int(qprtpara_status_regex)])

    def check_calibration(self, is_calibration, runtimes):
        '''
        发送AT+QRFCALIBRATE指令检测校准是否正常
        :param is_calibration: 1: 模块已校准；0:模块未校准
        :return:
        '''
        return_value = self.send_at('AT+QRFCALIBRATE', runtimes)
        re_info = ''.join(re.findall(r'\+QRFCALIBRATE:(\d)', return_value))
        if int(re_info) == is_calibration:
            self.log_queue.put(['at_log', '[{}]检测校准状态正常'.format(datetime.datetime.now())])
        else:
            self.log_queue.put(['all', '[{}]检测校准状态异常，AT+QRFCALIBRATE指令返回值为:{}'.format(datetime.datetime.now(), re_info)])

    def qfupl(self, package_name, package_path, runtimes):
        # 开始写文件命令
        file_size = os.path.getsize(package_path)
        self.log_queue.put(['at_log', '[{}] {} 文件大小 {} bit'.format(datetime.datetime.now(), package_path, file_size)])

        upl_command = 'AT+QFUPL="{}",{}'.format(package_name, file_size)
        self.log_queue.put(['at_log', '[{} Send] {}'.format(datetime.datetime.now(), '{}\\r\\n'.format(upl_command))])
        self.at_port_opened.write('{}\r\n'.format(upl_command).encode('utf-8'))

        # 判断是否正常且无 CME ERROR
        cache = ''
        start = time.time()
        timeout = 3
        while True:
            time.sleep(0.001)
            data = self.readline(self.at_port_opened)
            if data:
                cache += data
                if "ERROR" not in cache and 'CONNECT' in data:
                    break
            if time.time() - start > 3:
                self.log_queue.put(['all', '[{}] runtimes:{} {}命令超时:{}S'.format(datetime.datetime.now(), runtimes, upl_command, timeout)])
                return False
            if 'ERROR' in cache:
                self.log_queue.put(['all', '[{}] runtimes:{} {}返回异常:{}'.format(datetime.datetime.now(), runtimes, upl_command, data)])
                return False

        # 写入文件
        with open(package_path, 'rb+') as f:
            write_size = 0
            cache = ''
            percent = 0
            while True:
                # 写入AT口
                chunk = f.read(1024 * 4)
                write_size += self.at_port_opened.write(chunk)
                # 计算百分比
                write_percent = write_size / file_size * 100 // 10
                if percent != write_percent:
                    self.log_queue.put(['at_log', '[{}] 已发送 {} %'.format(datetime.datetime.now(), round(write_percent * 10, 0))])
                    percent = write_percent
                # 读AT口
                data = self.readline(self.at_port_opened)
                if data:
                    cache += data
                    if 'ERROR' in data:
                        self.log_queue.put(['all', '[{}] runtimes:{} 文件上传过程中出现异常:{}'.format(datetime.datetime.now(), runtimes, data)])
                        return False
                    if 'OK' in data:
                        break
            if write_size != file_size:
                self.log_queue.put(['all', '[{}] runtimes:{} 文件上传大小:{} 与实际不一致:{}'.format(datetime.datetime.now(), runtimes, write_size, file_size)])

    def cfun_0_1(self, runtimes):
        self.send_at('AT+CFUN=0', runtimes, 15)

        cfun = self.send_at('AT+CFUN?', runtimes, timeout=15)
        cfun_re = re.findall(r'CFUN:\s(\d+)', cfun)
        if '0' not in cfun_re:
            self.log_queue.put(['all', '[{}] runtimes:{} CFUN0切换失败'.format(datetime.datetime.now(), runtimes)])
            return False

        time.sleep(5)

        self.send_at('AT+CFUN=1', runtimes, 15)

        cfun = self.send_at('AT+CFUN?', runtimes, timeout=15)
        cfun_re = re.findall(r'CFUN:\s(\d+)', cfun)
        if '1' not in cfun_re:
            self.log_queue.put(['all', '[{}] runtimes:{} CFUN1切换失败'.format(datetime.datetime.now(), runtimes)])
            return False
        time.sleep(10)

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

    def config_fotacfg(self, http_or_https, server_address, config_username, config_password, runtimes):
        self.log_queue.put(['at_log', '配置服务器地址'])
        self.send_at('AT+QFOTACFG="server","{}"'.format(server_address), runtimes, 10)
        self.log_queue.put(['at_log', '配置识别码'])
        self.send_at('AT+QFOTACFG="pk","{}","{}"'.format(config_username, config_password), runtimes, 10)
        self.log_queue.put(['at_log', '配置在线升级方式http or https'])
        self.send_at('AT+QFOTACFG="tls",{}'.format(http_or_https), runtimes, 10)
        self.log_queue.put(['at_log', '开始配置时延'])
        self.send_at('AT+QFOTACFG="delay",1', runtimes, 10)
        time.sleep(2)
        cfg_value = self.send_at('AT+QFOTACFG?', runtimes, 10)
        if server_address in cfg_value and config_password in cfg_value:
            self.log_queue.put(['at_log', '配置成功'])
            return True
        else:
            self.log_queue.put(['at_log', '配置失败,当前配置为{}'.format(cfg_value)])
            return False

    def fota_online_download_urc_check(self, online_error_list, runtimes):
        """
        DFOTA在线升级指令升级返回OK后，再次返回例如"HTTPEND",0
        此函数就是为了检测版本包下载完成的标志
        :param online_error_list: 下载包过程中可能出现的错误
        :param runtimes: 脚本运行次数
        :return: True:下载成功；False：下载失败
        """
        download_start_timestamp = time.time()
        download_timeout = 300
        while True:
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                self.urc_checker(return_value, runtimes)
                download_error_list = [i for i in online_error_list if i in return_value]
                if download_error_list:
                    self.log_queue.put(['all',
                                        '[{}] runtimes:{} 下载升级包错误，错误代码{}'.format(datetime.datetime.now(), runtimes, download_error_list)])
                    return False
                elif '"fota",5' in return_value:
                    self.log_queue.put(['at_log', '[{}] 升级包下载失败'.format(datetime.datetime.now())])  # 写入log
                    return False
                elif '"fota",6' in return_value:
                    time.sleep(10)
                    self.log_queue.put(['at_log', '[{}] 升级包下载成功,开始升级'.format(datetime.datetime.now())])  # 写入log
                    return True
            elif time.time() - download_start_timestamp > download_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未检查到DFOTA升级包下载完成的URC'.format(datetime.datetime.now(), runtimes, download_timeout)])
                return False

    def check_otafota_status(self, version, mode, runtimes):
        """
        用于DFOTA上报的URC检测
        :param version: 当前升级之后的版本
        :param package_error_list: 文档定义的升级过程中出现升级包错误
        :param upgrade_error_list: 文档定义的升级过程中的非升级包错误
        :param runtimes: 当前脚本的运行次数
        :param mode: 模式，是正向还是反向升级
        :param vbat: 是否进行升级过程中断电
        :return: True：有指定的URC；False：未检测到。
        """
        self.log_queue.put(['at_log', '开始检测升级'])
        version = version[1] if mode == 'forward' else version[0]  # 传入的version为列表[version, after_upgrade_version]
        dfota_start_timestamp = time.time()
        dfota_timeout = 1000
        while True:
            # AT端口值获取
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                if '"FOTA","END",0' in return_value:
                    self.log_queue.put(
                        ['df', runtimes, 'fota_a_b_end_timestamp' if mode == 'forward' else 'fota_b_a_end_timestamp', time.time()])
                    self.log_queue.put(['at_log', '[{}] DFOTA升级成功'.format(datetime.datetime.now())])  # 写入log
                    return True

            elif (time.time() - dfota_start_timestamp) > dfota_timeout:
                return_value = self.send_at('ATI+CSUB', runtimes, 20)
                revision = ''.join(re.findall(r'Revision: (.*)', return_value))
                sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
                version_r = revision + sub_edition
                version_r = re.sub(r'[\r|\n]', '', version_r)
                if version == version_r:
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级指令发送成功，重启后未上报升级log，但是版本已经升级成功'.format(datetime.datetime.now(), runtimes)])
                    pause()
                self.log_queue.put(
                    ['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                self.log_queue.put(
                    ['all', '[{}] runtimes:{} {}S内DFOTA未升级成功'.format(datetime.datetime.now(), runtimes, dfota_timeout)])
                return False

    def check_success_urc(self, mode, runtimes):
        """
        用于检测升级成功状态7
        """
        check_start_timestamp = time.time()
        check_timeout = 60
        while True:
            # AT端口值获取
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                if '"fota",7' in return_value:
                    self.log_queue.put(
                        ['df', runtimes, 'fota_a_b_end_timestamp' if mode == 'forward' else 'fota_b_a_end_timestamp', time.time()])
                    self.log_queue.put(['at_log', '[{}] 检测到上报状态7,DFOTA升级成功'.format(datetime.datetime.now())])  # 写入log
                    return True
            elif time.time() - check_start_timestamp > check_timeout:
                self.log_queue.put(['all', '[{}] runtimes:{} {}S内未检查到DFOTA升级成功的URC'.format(datetime.datetime.now(), runtimes, check_timeout)])
                return True

    def qftest_value_record(self, mode, runtimes):
        self.send_at('ATE1', runtimes, 3)
        qftest_orig = self.send_at('AT+QFTEST="FSPartitionEC"', runtimes, 3)
        if "OK" not in qftest_orig or "ERROR" in qftest_orig:
            self.log_queue.put(['at_log', '[{}] 查询flash指令返回失败,当前返回为{}'.format(datetime.datetime.now(), qftest_orig)])
            return  # 异常不记录
        if mode == 'forward':
            self.log_queue.put(['flash_log', '[{}] 当前为第{}次:A-B升级{}'.format(datetime.datetime.now(), runtimes, qftest_orig)])
        if mode == 'backward':
            self.log_queue.put(
                ['flash_log', '[{}] 当前为第{}次:B-A升级{}'.format(datetime.datetime.now(), runtimes, qftest_orig)])

    def check_fotastate(self, runtimes):
        """
        升级前查询state状态为SUCCEED
        """
        for i in range(10):
            time.sleep(1)
            state_value = self.send_at('AT+QABFOTA="state"', runtimes, 15)
            if 'SUCCEED' in state_value or 'FAILED' in state_value:
                self.log_queue.put(['at_log', '[{}] 升级前状态查询正常，为{}'.format(datetime.datetime.now(), state_value)])
                return True

        self.log_queue.put(['at_log', '[{}] 升级前状态查询不正常，不为SUCCEED或FAILED'.format(datetime.datetime.now())])
        return False

    def set_package_name(self, packagename, runtimes):
        """
        升级包命名
        """
        pack_value = self.send_at('at+qabfota="package","{}"'.format(packagename), runtimes, 15)
        if 'OK' in pack_value:
            return True
        else:
            return False

    def check_upgradestate(self, runtimes):
        """
        升级指令发送成功后查询模块状态
        """
        while True:
            state_value = self.send_at('AT+QABFOTA="state"', runtimes, 15)
            if 'UPDATE' in state_value:
                self.log_queue.put(['at_log', '正在升级中'])
                return True

            else:
                self.log_queue.put(['at_log', '升级中状态查询不正常，不为UPDATE'])
                pause()
                return False

    def check_adbfota_status(self, version, package_error_list, upgrade_error_list, mode, vbat, runtimes):
        """
        用于DFOTA上报的URC检测
        :param version: 当前升级之后的版本
        :param package_error_list: 文档定义的升级过程中出现升级包错误
        :param upgrade_error_list: 文档定义的升级过程中的非升级包错误
        :param runtimes: 当前脚本的运行次数
        :param mode: 模式，是正向还是反向升级
        :param vbat: 是否进行升级过程中断电
        :return: True：有指定的URC；False：未检测到。
        """
        self.log_queue.put(['at_log', '开始检测升级'])
        version = version[1] if mode == 'forward' else version[0]  # 传入的version为列表[version, after_upgrade_version]
        dfota_start_timestamp = time.time()
        dfota_timeout = 300
        vbat_point_start = time.time()
        if self.dfota_powerfailure_time > 120:  # 实测升级时间不超过80S
            self.dfota_powerfailure_time = 2
        start_time = time.time() + 2
        while True:
            # AT端口值获取
            time.sleep(0.01)  # 每2秒检测一次memory
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                self.urc_checker(return_value, runtimes)
                upgrade_error = [i for i in upgrade_error_list if
                                 i in return_value]  # 循环获取log中有无upgrade_error_list中的问题
                package_error = [i for i in package_error_list if
                                 i in return_value]  # 循环获取log中有无package_error_list中的问题
                if package_error:
                    self.log_queue.put(
                        ['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级过程升级包错误，错误代码{}'.format(datetime.datetime.now(),
                                                                                          runtimes, package_error)])
                    return False
                elif upgrade_error:
                    self.log_queue.put(
                        ['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                    self.log_queue.put(['all',
                                        '[{}] runtimes:{} 升级过程中异常，错误代码{}'.format(datetime.datetime.now(), runtimes,
                                                                                 upgrade_error)])
                    return False

                elif '"UPDATE",100' in return_value:
                    self.log_queue.put(['df', runtimes,
                                        'fota_a_b_end_timestamp' if mode == 'forward' else 'fota_b_a_end_timestamp',
                                        time.time()])
                    self.log_queue.put(['at_log', '[{}] DFOTA升级成功'.format(datetime.datetime.now())])  # 写入log
                    return True

                elif vbat and '"UPDATE",22' in return_value:
                    vbat_point_end = time.time()
                    vbat_point = vbat_point_end - vbat_point_start
                    self.log_queue.put(['df', runtimes,
                                        'fota_a_b_start_timestamp' if mode == 'forward' else 'fota_b_a_start_timestamp',
                                        time.time()])
                    self.log_queue.put(
                        ['at_log', '[{}] 在升级到{}秒时断电'.format(datetime.datetime.now(), vbat_point)])  # 写入log
                    return True

                elif '"UPDATE",22' in return_value or '"UPDATE",66' in return_value or '"UPDATE",88' in return_value:
                    self.check_memory(mode)

            elif (time.time() - dfota_start_timestamp) > dfota_timeout:
                return_value = self.send_at('ATI+CSUB', runtimes, 20)
                revision = ''.join(re.findall(r'Revision: (.*)', return_value))
                sub_edition = ''.join(re.findall('SubEdition: (.*)', return_value))
                version_r = revision + sub_edition
                version_r = re.sub(r'[\r|\n]', '', version_r)
                if version == version_r:
                    self.log_queue.put(['all', '[{}] runtimes:{} 升级指令发送成功，重启后未上报升级log，但是版本已经升级成功'.format(
                        datetime.datetime.now(), runtimes)])
                    pause()
                self.log_queue.put(
                    ['df', runtimes, 'fota_a_b_fail_times' if mode == 'forward' else 'fota_b_a_fail_times', 1])
                self.log_queue.put(['all',
                                    '[{}] runtimes:{} {}S内DFOTA未升级成功'.format(datetime.datetime.now(), runtimes,
                                                                             dfota_timeout)])
                return False

    def check_twosystem_synchronization(self, backup_vbat, mode, runtimes):
        """
        :param backup_vbat: 是否进行同步过程中断电
        """
        self.log_queue.put(['df', runtimes, 'fota_ab_start_timestamp', time.time()])
        vbat_point = random.randint(1, 60)

        while True:
            time.sleep(30)
            state_value = self.send_at('AT+QABFOTA="state"', runtimes, 15)
            if 'BACKUP' not in state_value:
                self.log_queue.put(['at_log', '[{}] AB系统同步成功'.format(datetime.datetime.now())])
                self.log_queue.put(['at_log', '[{}] 当前查询状态为 {}'.format(datetime.datetime.now(), state_value)])
                self.log_queue.put(
                    ['df', runtimes, 'fota_ab_end_timestamp', time.time()])
                return True
            else:
                self.log_queue.put(['at_log', '[{}] 当前状态为 {},两个系统同步中'.format(datetime.datetime.now(), state_value)])
                self.check_memory(mode, is_upgrade=False)

            if backup_vbat:
                self.log_queue.put(['at_log', '[{}] 在同步到{}秒时断电'.format(datetime.datetime.now(), vbat_point)])
                time.sleep(vbat_point)
                return True

    def check_memory(self, mode, is_upgrade=True):
        """
        检查memory使用情况
        """
        if is_upgrade:
            self.log_queue.put(['memory_log', '[{}]:======升级过程中查询memory====='.format(datetime.datetime.now())])
        else:
            self.log_queue.put(['memory_log', '[{}]:======同步过程中查询memory====='.format(datetime.datetime.now())])

        s = subprocess.Popen("powershell adb shell", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.PIPE)
        check_time = 10
        s.stdin.write(b'df -ahT\r\n')
        s.stdin.write(b'exit\r\n')
        s.stdin.close()
        st = time.time()
        out_cache = ''

        while True:
            out = s.stdout.readline()
            if out != '' and b'insmod' not in out:
                out = out.decode('utf-8')
                out_cache += out

            if '/cache' in out:
                s.terminate()
                s.wait()
                break

            if time.time() - st > check_time:
                s.terminate()
                s.wait()
                break

        content = re.findall(r'Filesystem.*Mounted on|tmpfs.*run|/dev/ubi2_0.*cache', out_cache)
        arr = np.array(content)

        if mode == 'forward':
            self.log_queue.put(['memory_log', '[{}]:A-B升级{}'.format(datetime.datetime.now(), arr)])
            return True

        if mode == 'backward':
            self.log_queue.put(['memory_log', '[{}]:B-A升级{}'.format(datetime.datetime.now(), arr)])
            return True

    def check_twosystem_vbatbackup(self, mode, runtimes):
        """
        统计同步断电时的同步时间
        """
        while True:
            time.sleep(20)
            state_value = self.send_at('AT+QABFOTA="state"', runtimes, 15)
            if 'BACKUP' not in state_value:
                self.log_queue.put(['at_log', 'AB系统同步成功'])
                self.log_queue.put(['at_log', '当前查询状态为 {}'.format(state_value)])
                self.log_queue.put(
                    ['df', runtimes, 'fota_ab_end_timestamp', time.time()])
                return True
            else:
                self.log_queue.put(['at_log', '当前状态为 {},两个系统同步中'.format(state_value)])
                self.check_memory(mode, is_upgrade=False)

    def absystem_upgrade_log(self, runtimes):
        """
        因随机断电存在不上报升级进度log，需发送AT指令后才上报,故用于测试增加
        """
        self.send_at('ATI', runtimes, 15)

    def download_ab_package(self, package_path, online_error_list, download_vbat, package_name, runtimes):
        """
        从ftp/http下载升级包
        DFOTA在线升级指令升级返回OK后，再次返回例如"HTTPEND",0
        param package_path：在线差分包路径
        param download_Vbat: 是否进行下载过程中断电
        """
        time.sleep(5)
        self.log_queue.put(['at_log', '[{}] 开始进行差分包下载'.format(datetime.datetime.now())])
        vbat_point = random.randint(1, 5)
        self.send_at('AT+QABFOTA="download","{}"'.format(package_path), runtimes, 10)
        download_start_timestamp = time.time()
        download_timeout = 300
        while True:
            time.sleep(0.001)  # 减小CPU开销
            return_value = self.readline(self.at_port_opened)
            if return_value != '':
                self.urc_checker(return_value, runtimes)
                download_error_list = [i for i in online_error_list if i in return_value]
                if download_error_list:
                    self.log_queue.put(['all',
                                        '[{}] runtimes:{} 下载升级包错误，错误代码{}'.format(datetime.datetime.now(), runtimes,
                                                                                 download_error_list)])
                    return False
                elif 'END",0' in return_value:
                    self.log_queue.put(['at_log', '[{}] 升级包下载成功'.format(datetime.datetime.now())])
                    return True

                elif download_vbat and '+QIND: "ABFOTA"' in return_value:
                    self.log_queue.put(['at_log', '[{}] 在下载差分包到{}秒时断电'.format(datetime.datetime.now(), vbat_point)])
                    time.sleep(vbat_point)
                    return True

            elif time.time() - download_start_timestamp > download_timeout:
                for i in range(1, 5):
                    time.sleep(2)
                    flst_value = self.send_at('AT+QFLST="*"', runtimes, 10)
                    if package_name in flst_value:
                        self.log_queue.put(['at_log', '[{}] 差分包已下载完成,但未检测到下载完成URC'.format(datetime.datetime.now())])
                        break
                    else:
                        self.log_queue.put(['at_log', '[{}] 未检测到差分包下载完成,2秒后继续检测'.format(datetime.datetime.now())])

                self.log_queue.put(
                    ['all', '[{}] runtimes:{} {}S内未检查到DFOTA升级包下载完成的URC'.format(datetime.datetime.now(),
                                                                               runtimes, download_timeout)])
                return False

    def download_vbat_ufscheck(self, package_name, runtimes):
        """
        下载过程中断电重启后检查ufs中是否有残留文件
        """
        while True:
            flst_value = self.send_at('AT+QFLST="*"', runtimes, 10)
            if package_name not in flst_value:
                self.log_queue.put(['at_log', '[{}] 下载差分包过程中断电重启后查询ufs无残留差分包'.format(datetime.datetime.now())])
                return True
            else:
                self.log_queue.put(
                    ['at_log', '[{}] 下载差分包过程中断电重启后查询ufs存在残留差分包,功能失败脚本暂停'.format(datetime.datetime.now())])
                pause()

    def check_download_ufs(self, package_name, runtimes):
        """
        下载差分包成功后检查ufs
        """
        time.sleep(10)
        self.log_queue.put(['at_log', '[{}] 下载完差分包后因存在转化名称时间,所以等待10秒后查询'.format(datetime.datetime.now())])
        while True:
            flst_value = self.send_at('AT+QFLST="*"', runtimes, 10)
            if package_name in flst_value:
                self.log_queue.put(['at_log', '[{}] ufs中差分包名称正确'.format(datetime.datetime.now())])
                return True
            else:
                self.log_queue.put(['at_log', '[{}] ufs中差分包名称错误,功能失败脚本暂停'.format(datetime.datetime.now())])
                pause()

    def check_ufs_package(self, runtimes):
        """
        检测整个升级同步过程中的ufs分区变化
        """
        flst_value = self.send_at('AT+QFLST="*"', runtimes, 10)
        self.log_queue.put(['memory_log', '[{}]:查询UFS分区值为:{}'.format(datetime.datetime.now(), flst_value)])


    def break_ab_boot(self, mode, Partition_Type, a, b, runtimes):
        """
        擦除AB分区boot分区
        """
        erasepartitions = random.randint(a,b)

        self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)

        if mode == 'forward':
            self.send_at('AT+QNAND="EBlock","{}",{}'.format(Partition_Type,erasepartitions), runtimes, 10)
            return True

        if mode == 'backward':
            self.send_at('AT+QNAND="EBlock","b_{}",{}'.format(Partition_Type, erasepartitions), runtimes, 10)
            return True

    def check_abboot(self, mode, runtimes):
        """
        检查重启后的分区
        """
        time.sleep(15)
        recv_value = self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)
        if mode == 'forward':
            if '"activeslot",1' in recv_value:
                self.log_queue.put(['at_log', '[{}] 重启后分区为B分区'.format(datetime.datetime.now())])

            else:
                self.log_queue.put(['at_log', '[{}] 重启后分区不为B分区,为{}'.format(datetime.datetime.now(), recv_value)])
                self.log_queue.put(['df', runtimes, 'abboot_fail_times', 1])
                return False

        if mode == 'backward':
            if '"activeslot",0' in recv_value:
                self.log_queue.put(['at_log', '[{}] 重启后分区为A分区'.format(datetime.datetime.now())])

            else:
                self.log_queue.put(['at_log', '[{}] 重启后分区不为A分区,为{}'.format(datetime.datetime.now(), recv_value)])
                self.log_queue.put(['df', runtimes, 'abboot_fail_times', 1])
                return False

    def check_addoot_state(self, runtimes):
        time.sleep(6)
        for i in range(20):
            time.sleep(6)
            state_value = self.send_at('AT+QABFOTA="state"', runtimes, 15)
            if 'SUCCEED' in state_value:
                self.log_queue.put(['at_log', '当前AB状态为SUCCEED'])
                return True

    def orderA_break_ab_boot(self, i, Partition_Type, runtimes):
        """
        顺序擦除A分区
        """
        time.sleep(4)
        self.log_queue.put(['at_log', '[{}]开始擦除{}分区第{}个分区'.format(datetime.datetime.now(), Partition_Type, i)])
        self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)
        self.send_at('AT+QNAND="EBlock","{}",{}'.format(Partition_Type, i), runtimes, 10)
        return True

    def orderA_check_abboot(self, i, Partition_Type, runtimes):
        """
        检查重启后的分区
        """
        time.sleep(15)
        recv_value = self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)
        if '"activeslot",1' in recv_value:
            self.log_queue.put(['at_log', '[{}] 重启后分区为B分区'.format(datetime.datetime.now())])

        else:
            self.log_queue.put(['at_log', '[{}] 重启后分区不为B分区,为{},重新擦除'.format(datetime.datetime.now(), recv_value)])
            self.log_queue.put(['ab_bootfail_log', '[{}]:擦除{}分区第{}个分区后重启查询分区没变'.format(datetime.datetime.now(), Partition_Type, i)])
            self.log_queue.put(['df', runtimes, 'abboot_fail_times', 1])
            return False

    def orderB_break_ab_boot(self, i, Partition_Type, runtimes):
        """
        顺序擦除B分区
        """
        time.sleep(4)
        self.log_queue.put(['at_log', '[{}]开始擦除b_{}分区第{}个分区'.format(datetime.datetime.now(), Partition_Type, i)])
        self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)
        self.send_at('AT+QNAND="EBlock","b_{}",{}'.format(Partition_Type, i), runtimes, 10)
        return True

    def orderB_check_abboot(self, i, Partition_Type, runtimes):
        """
        检查重启后的分区
        """
        time.sleep(15)
        recv_value = self.send_at('AT+QABFOTA="ACTIVESLOT"', runtimes, 10)
        if '"activeslot",0' in recv_value:
            self.log_queue.put(['at_log', '[{}] 重启后分区为A分区'.format(datetime.datetime.now())])

        else:
            self.log_queue.put(['at_log', '[{}] 重启后分区不为A分区,为{},重新擦除'.format(datetime.datetime.now(), recv_value)])
            self.log_queue.put(['ab_bootfail_log', '[{}]:擦除b_{}分区第{}个分区后重启查询分区没变'.format(datetime.datetime.now(), Partition_Type, i)])
            self.log_queue.put(['df', runtimes, 'abboot_fail_times', 1])
            return False

    def switch_dialmode(self, is_route, runtimes):  # rgmii新增
        """
        切换路由模式和桥模式
        is_route : True 切换为路由模式, False : 切换为桥模式
        """
        self.send_at('at+qmap="mpdn_rule",0 ', runtimes, timeout=20)
        if is_route:
            self.log_queue.put(['at_log', '[{}] 切换拨号模式为路由模式'.format(datetime.datetime.now())])
            self.send_at('at+qmap="mpdn_rule",0,1,0,0,1', runtimes, timeout=8)
        else:
            self.log_queue.put(['at_log', '[{}] 切换拨号模式为桥模式'.format(datetime.datetime.now())])
            self.send_at('AT+QMAP="mPDN_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', runtimes, timeout=8)

    def set_ipptmode(self, runtimes):
        self.log_queue.put(['at_log', '[{}] 配置IPPT模式'.format(datetime.datetime.now())])
        self.send_at('AT+QMAP="mPDN_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', runtimes, timeout=8)

    def set_rulenowait(self, runtimes):
        self.log_queue.put(['at_log', '[{}] 配置mpdn_rule为0'.format(datetime.datetime.now())])
        self.send_nowait_at('at+QMAP="mPDN_rule",0', runtimes)

    def set_rulewait(self, runtimes):
        self.log_queue.put(['at_log', '[{}] 配置mpdn_rule为0'.format(datetime.datetime.now())])
        self.send_at('at+QMAP="mPDN_rule",0', runtimes, timeout=20)

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

    def check_policy_band(self, runtimes):
        """
        检查policy_band 返回,若返回只有0,则指令异常,暂停脚本
        """
        band_list = []
        self.log_queue.put(
            ['at_log', '[{}] 开始查询policy_band指令'.format(datetime.datetime.now())])
        policy_band_value = self.send_at('at+qnwprefcfg="policy_band"', runtimes)
        gw_bandvalue = ''.join(re.findall(r'QNWPREFCFG: "gw_band",(\d+)', policy_band_value))
        band_list.append(gw_bandvalue)

        lte_bandvalue = ''.join(re.findall(r'QNWPREFCFG: "lte_band",(\d+)', policy_band_value))
        band_list.append(lte_bandvalue)

        nsa_bandvalue = ''.join(re.findall(r'QNWPREFCFG: "nsa_nr5g_band",(\d+)', policy_band_value))
        band_list.append(nsa_bandvalue)

        nr5g_bandvaule = ''.join(re.findall(r'QNWPREFCFG: "nr5g_band",(\d+)', policy_band_value))
        band_list.append(nr5g_bandvaule)

        if band_list.count('0') == 4:
            self.log_queue.put(
                    ['at_log', '[{}] 查询policy_band指令返回异常'.format(datetime.datetime.now())])
            self.log_queue.put(
                ['at_log', '[{}]查询policy_band指令返回: {}'.format(datetime.datetime.now(), policy_band_value)])
            pause()

        time.sleep(2)
        self.log_queue.put(
            ['at_log', '[{}] 开始检查QNVFR相关指令是否正确返回'.format(datetime.datetime.now())])

        self.send_at('AT+QNVFR="/policyman/net_scan_time"', runtimes)
        self.send_at('AT+QNVFR="/policyman/auto_learn_time"', runtimes)
        self.send_at('AT+QNVFR="/policyman/device_config.xml"', runtimes)
        self.send_at('AT+QNVFR="/policyman/global_defines.xml"', runtimes)
        self.send_at('AT+QNVFR="/policyman/pre.xml"', runtimes)
        self.send_at('AT+QNVFR="/policyman/lte_feature_restrictions.xml"', runtimes)
        self.send_at('AT+QNVFR="/policyman/generic_band_restrictions.xml"', runtimes)

    def switch_qftmmode(self, runtimes):
        time.sleep(10)
        self.send_at('AT+QFTMMODE=1', runtimes, timeout=15)
        time.sleep(10)
        mode_value = self.send_at('AT+QFTMMODE?', runtimes, timeout=15)
        if '1' not in mode_value:
            self.log_queue.put(['all', '[{}] QFTMMODE值错误！'.format(datetime.datetime.now())])
            pause()
        time.sleep(10)
        self.check_port(runtimes)
        self.send_at('AT+QFTMMODE=0', runtimes, timeout=15)
        time.sleep(10)
        mode_value = self.send_at('AT+QFTMMODE?', runtimes, timeout=15)
        if '0' not in mode_value:
            self.log_queue.put(['all', '[{}] QFTMMODE值错误！'.format(datetime.datetime.now())])
            pause()
        time.sleep(10)
        self.check_port(runtimes)
        self.send_at('AT+CFUN=1,1', runtimes, timeout=15)
        time.sleep(2)

    def check_efsec(self, runtimes, is_vbat):
        """
        查询EFSBlockEC
        """
        if is_vbat is True:
            self.log_queue.put(['at_log', '[{}] 随机断电之前查询EFSBlockEC'.format(datetime.datetime.now())])
            efs_value = self.send_at('AT+QFTEST="EFSBlockEC"', runtimes, timeout=6)
            self.log_queue.put(
                ['efsec_log', '[{}] 随机断电之前查询EFSBlockEC返回: {}'.format(datetime.datetime.now(), efs_value)])
        else:
            self.log_queue.put(['at_log', '[{}] 模块开机后查询EFSBlockEC'.format(datetime.datetime.now())])
            efs_value = self.send_at('AT+QFTEST="EFSBlockEC"', runtimes, timeout=6)
            self.log_queue.put(
                ['efsec_log', '[{}] 模块开机后查询EFSBlockEC返回: {}'.format(datetime.datetime.now(), efs_value)])

    def set_restore(self, runtimes):
        """
        设置模块还原
        """
        self.log_queue.put(['at_log', '[{}]设置模块还原'.format(datetime.datetime.now())])
        time.sleep(2)
        self.send_at('AT+QPRTPARA=3', runtimes, 10)

    def check_cefsblock(self, block_restore_count, runtimes):
        """
        查询并验证坏块个数及id
        :return:
        """
        time.sleep(2)
        self.log_queue.put(['at_log', '[{}]查询模块当前还原次数'.format(datetime.datetime.now())])
        count_value = self.send_at('AT+QCEFSCFG="restore_count"', runtimes, timeout=3)
        self.log_queue.put(['cefsblock_log', '[{}]当前查询模块还原次数为:{}'.format(datetime.datetime.now(), count_value)])
        time.sleep(2)
        self.log_queue.put(['at_log', '[{}]记录模块连续还原次数'.format(datetime.datetime.now())])
        con_value = self.send_at('AT+QCEFSCFG="block_consecutive_restore_count"', runtimes, timeout=3)
        self.log_queue.put(['cefsblock_log', '[{}]当前查询模块连续还原次数为:{}'.format(datetime.datetime.now(), con_value)])
        time.sleep(2)
        # 查询指令AT+QPRTPARA=4
        self.log_queue.put(['at_log', '[{}]查询模块备份信息'.format(datetime.datetime.now())])
        para_value = self.send_at('AT+QPRTPARA=4', runtimes, timeout=3)
        self.log_queue.put(['cefsblock_log', '[{}]查询模块备份信息返回:{}'.format(datetime.datetime.now(), para_value)])
        bad_num = int(''.join(re.findall(r'\+QPRTPARA: .*,(\d+)', para_value)))
        self.log_queue.put(['cefsblock_log', '[{}]模块备份信息查询到坏块个数为:{}'.format(datetime.datetime.now(), bad_num)])
        time.sleep(2)
        # 查询指令AT+QCEFSCFG="get_bad_blocks_id"
        bad_value_intlist = []
        self.log_queue.put(['at_log', '[{}]执行指令AT+QCEFSCFG="get_bad_blocks_id"查询坏块id'.format(datetime.datetime.now())])
        bad_values = self.send_at('AT+QCEFSCFG="get_bad_blocks_id"', runtimes, timeout=3)
        self.log_queue.put(['cefsblock_log', '[{}]执行指令AT+QCEFSCFG="get_bad_blocks_id"返回:{}'.format(datetime.datetime.now(), bad_values)])
        bad_value = ''.join(re.findall(r'"get_bad_blocks_id",(.*)\r\n', bad_values))  # 得到字符串类型
        if len(bad_value) == 0:
            if bad_num == 0:
                self.log_queue.put(['at_log', '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询无坏块,查询返回结果一致'.format(datetime.datetime.now())])
                self.log_queue.put(
                    ['cefsblock_log', '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询无坏块,查询返回结果一致'.format(datetime.datetime.now())])
            else:
                self.log_queue.put(['at_log',
                                    '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回结果不一致'.format(datetime.datetime.now())])
                self.log_queue.put(['cefsblock_log',
                                    '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回结果不一致'.format(datetime.datetime.now())])
                self.log_queue.put(['at_log',
                                    '[{}]指令AT+QCEFSCFG="get_bad_blocks_id"查询返回{}'.format(datetime.datetime.now(), bad_values)])
                self.log_queue.put(['at_log',
                                    '[{}]指令AT+QPRTPARA=4查询返回{}'.format(datetime.datetime.now(), para_value)])
                pause()
        else:
            bad_values = re.split(',', bad_value)  # 去除字符串中,并转换成列表
            for i in bad_values:
                bad_value_intlist.append(int(i))  # 将字符串为元素的列表转换成int类型元素
            self.log_queue.put(['cefsblock_log', '[{}]指令"get_bad_blocks_id"查询返回坏块个数为:{}'.format(datetime.datetime.now(), len(bad_value_intlist))])
            if bad_num == len(bad_value_intlist):
                self.log_queue.put(['at_log', '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回坏块数量一致'.format(datetime.datetime.now())])
                self.log_queue.put(
                    ['cefsblock_log', '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回坏块数量一致'.format(datetime.datetime.now())])
            else:
                self.log_queue.put(['at_log',
                                    '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回坏块数量不一致'.format(datetime.datetime.now())])
                self.log_queue.put(['cefsblock_log',
                                    '[{}]指令"get_bad_blocks_id"与AT+QPRTPARA=4查询返回坏块数量不一致'.format(datetime.datetime.now())])
                self.log_queue.put(['at_log',
                                    '[{}]指令AT+QCEFSCFG="get_bad_blocks_id"查询返回{}'.format(datetime.datetime.now(), bad_values)])
                self.log_queue.put(['at_log',
                                    '[{}]指令AT+QPRTPARA=4查询返回{}'.format(datetime.datetime.now(), para_value)])
                pause()
        time.sleep(2)
        # 查询指令AT+QCEFSCFG="block_restore_count"
        block_count_intlist = []
        block_count_countlist = []
        element_list = []
        self.log_queue.put(['at_log', '[{}]执行指令AT+QCEFSCFG="block_restore_count"查询坏块统计'.format(datetime.datetime.now())])
        block_count = self.send_at('AT+QCEFSCFG="block_restore_count"', runtimes, timeout=3)
        self.log_queue.put(['cefsblock_log', '[{}]执行指令"block_restore_count"返回:{}'.format(datetime.datetime.now(), block_count)])
        bad_count = re.findall(r'(\d+),', block_count)
        for i in bad_count:  # 处理匹配出的列表
            block_count_intlist.append(int(i))
        for i, element in enumerate(block_count_intlist):  # 查找出block值大于设定值的元素并取出其下标放入列表block_count_countlist中
            if element >= block_restore_count:
                element_list.append(element)
                block_count_countlist.append(i)
        self.log_queue.put(['cefsblock_log', '[{}]指令"block_restore_count"查询到坏点值为为:{}'.format(datetime.datetime.now(), element_list)])
        self.log_queue.put(['cefsblock_log', '[{}]指令"block_restore_count"查询到坏点id为:{}'.format(datetime.datetime.now(), block_count_countlist)])
        self.log_queue.put(['at_log', '[{}]指令"block_restore_count"查询到坏点值为为:{}'.format(datetime.datetime.now(), element_list)])
        self.log_queue.put(['at_log', '[{}]指令"block_restore_count"查询到坏点id为:{}'.format(datetime.datetime.now(), block_count_countlist)])
        if bad_value_intlist == block_count_countlist:
            self.log_queue.put(['at_log', '[{}]指令"get_bad_blocks_id"查询到的坏点id在"block_restore_count"中对应的位置一致'.format(datetime.datetime.now())])
            self.log_queue.put(['cefsblock_log', '[{}]指令"get_bad_blocks_id"查询到的坏点id在"block_restore_count"中对应的位置一致'.format(
                datetime.datetime.now())])
        else:
            self.log_queue.put(['at_log', '[{}]指令"get_bad_blocks_id"查询到的坏点id在"block_restore_count"中对应的位置不一致'.format(
                datetime.datetime.now())])
            self.log_queue.put(['cefsblock_log', '[{}]指令"get_bad_blocks_id"查询到的坏点id在"block_restore_count"中对应的位置不一致'.format(
                datetime.datetime.now())])
            pause()

    def set_blocklimit(self, block_restore_count, total_restore_count, runtimes):
        self.log_queue.put(['at_log', '[{}] 查询cefs总还原次数上限'.format(datetime.datetime.now())])
        self.send_at('AT+QCEFSCFG="restore_count_limit"', runtimes, timeout=3)
        self.log_queue.put(['at_log', '[{}] 设置cefs总还原次数上限为{}'.format(datetime.datetime.now(), total_restore_count)])
        self.send_at('AT+QCEFSCFG="restore_count_limit",{}'.format(total_restore_count), runtimes, timeout=3)
        self.log_queue.put(['at_log', '[{}] 查询cefs分区各block累计触发还原次数上限'.format(datetime.datetime.now())])
        self.send_at('AT+QCEFSCFG="block_restore_count_limit"', runtimes, timeout=3)
        self.log_queue.put(['at_log', '[{}] 设置cefs分区各block累计触发还原次数上限为{}'.format(datetime.datetime.now(), block_restore_count)])
        self.send_at('AT+QCEFSCFG="block_restore_count_limit",{}'.format(block_restore_count), runtimes, timeout=3)
        time.sleep(2)

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

    def check_mbn_lost(self, mbn_list, runtimes):
        time.sleep(6)
        mbn_status = ''
        self.log_queue.put(['at_log', '[{}] 升级成功后再次重启模块后检查mbn'.format(datetime.datetime.now())])
        self.log_queue.put(['at_log', '[{}] 当前系统填写mbn列表为:{}'.format(datetime.datetime.now(), mbn_list)])
        for i in range(20):
            mbn_status = self.send_at('at+qmbncfg="list"', runtimes, timeout=15)
            if 'OK' in mbn_status and ",1,1" in mbn_status:
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
