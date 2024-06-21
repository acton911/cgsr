import re
import sys
import serial
import time
import requests
from threading import Thread
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxRIURCError
from utils.functions.driver_check import DriverChecker


class LinuxRiUrcManager:
    def __init__(self, at_port, dm_port, uart_port, modem_port, phone_number):
        self.at_port = at_port
        self.dm_port = dm_port
        self.uart_port = uart_port
        self.modem_port = modem_port
        self.phone_number = phone_number
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.driver_check.check_usb_driver()
        try:
            self.at_handle.readline_keyword('PB DONE', timout=50)  # 确保每条case执行前不会有其他开机URC上报
            time.sleep(3)
        except Exception:   # noqa
            pass
        self.at_handle.send_at('AT+CEREG=0;+CGREG=0;+CREG=0;+C5GREG=0;&W', 3)   # 确保case执行前，不会有多余的网络上报导致引脚跳变
        self.url = 'https://stcall.quectel.com:8054/api/task'
        self.rg_flag = True
        self.gpio = GPIO()

    def check_cfun_change_at_urc(self, is_delay=False):
        """
        检测切换CFUN时1AT口上报的URC
        :param is_delay: 是否开启延时, True:开启; False:未开启
        :return:
        """
        exc_type = None
        exc_value = None
        uart_urc_check = None
        try:
            self.driver_check.check_usb_driver()
            check_content = ['+CPIN: READY', '+QUSIM: 1', '+QIND: SMS DONE', '+QIND: PB DONE']
            uart_urc_check = PortCheck(self.uart_port, check_content, False, 'Uart')
            time.sleep(5)
            self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            self.at_handle.send_at('AT+QCFG="urc/delay",0')
            self.at_handle.send_at('AT+QURCCFG="URCPORT","ALL"', 10)
            if is_delay:
                for i in range(3):
                    if self.set_delay():
                        break
                else:
                    raise LinuxRIURCError('设置三次AT+QCFG="urc/delay",1延时上报URC指令不成功')
            self.at_handle.send_at('AT+CFUN=0', 10)
            time.sleep(1)
            modem_urc_check = PortCheck(self.modem_port, check_content, serial.Serial(self.modem_port).getRI(), 'Modem')
            modem_urc_check.setDaemon(True)
            self.at_handle.send_at('AT+CFUN=1', 10)
            at_ri_thread = PortCheck(self.at_port, check_content, serial.Serial(self.at_port).getRI(), 'AT')
            at_ri_thread.setDaemon(True)
            at_ri_thread.start()
            modem_urc_check.start()
            if self.rg_flag:
                uart_urc_check.setDaemon(True)
                uart_urc_check.start()
            start_time = time.time()
            while True:
                if at_ri_thread.finish_flag:
                    all_logger.info('CFUN01切换已检测到PB DONE')
                    time.sleep(10)  # 多等待一段时间再停止检测RI引脚跳变，观察引脚是否存在多跳变的情况
                    at_ri_thread.stop_flag = True
                    modem_urc_check.stop_flag = True
                    if self.rg_flag:
                        uart_urc_check.stop_flag = True
                    break
                if time.time() - start_time > 100:
                    all_logger.info('CFUN01切换后，100S内未检测到PB DONE')
                    raise LinuxRIURCError('CFUN01切换后，100S内未检测到PB DONE')
            at_ri_thread.join()    # 阻塞ri线程，检查引脚跳变是否正常
            modem_urc_check.join()    # 阻塞ri线程，检查引脚跳变是否正常
            if self.rg_flag:
                uart_urc_check.join()    # 阻塞ri线程，检查引脚跳变是否正常
            if at_ri_thread.error_msg:
                all_logger.info(at_ri_thread.error_msg)
                raise LinuxRIURCError(at_ri_thread.error_msg)
            elif modem_urc_check.error_msg:
                all_logger.info(modem_urc_check.error_msg)
                raise LinuxRIURCError(modem_urc_check.error_msg)
            if self.rg_flag:
                if uart_urc_check.error_msg:
                    all_logger.info(uart_urc_check.error_msg)
                    raise LinuxRIURCError(uart_urc_check.error_msg)
            # if at_ri_thread.cur_jump_times != 3:
            #     all_logger.info('AT口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(at_ri_thread.cur_jump_times))
            #     raise LinuxRIURCError('AT口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(at_ri_thread.cur_jump_times))
            # elif modem_urc_check.cur_jump_times != 3:
            #     all_logger.info('Modem口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(modem_urc_check.cur_jump_times))
            #     raise LinuxRIURCError('Modem口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(modem_urc_check.cur_jump_times))
            # else:
            #     all_logger.info('AT口和MODEM口RI引脚电平状态检测正常')
            # if self.rg_flag:
            #     if uart_urc_check.cur_jump_times != 3:
            #         all_logger.info('Uart口口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(uart_urc_check.cur_jump_times))
            #         raise LinuxRIURCError('Uart口口CFUN01切换期望RI引脚跳变三次实际跳变{}次'.format(uart_urc_check.cur_jump_times))
            #     else:
            #         all_logger.info('Uart口RI引脚电平状态检测正常')
            # if not is_delay:    # 未开启延时功能
            #     if at_ri_thread.ri_change_time - at_ri_thread.urc_report_time > 0.05:
            #         all_logger.info('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
            #         raise LinuxRIURCError('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms')
            #     elif at_ri_thread.ri_change_time - at_ri_thread.urc_report_time < 0:
            #         all_logger.info('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
            #         raise LinuxRIURCError('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变')
            #     else:
            #         all_logger.info('未开启延时,URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            # else:
            #     if at_ri_thread.urc_report_time - at_ri_thread.ri_change_time > 1:
            #         all_logger.info('开启延时上报，上报URC时间与RI引脚跳动时间超过1S,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            #         raise LinuxRIURCError('开启延时上报，上报URC时间与RI引脚跳动时间超过1S')
            #     elif at_ri_thread.urc_report_time - at_ri_thread.ri_change_time < 0:
            #         all_logger.info('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            #         raise LinuxRIURCError('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC')
            #     else:
            #         all_logger.info('开启延时后URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            uart_urc_check.stop_flag = True
            self.set_delay(False)
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

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

    def send_msg(self, content='123456'):
        """
        系统主发短信到模块端
        :param content:期望系统所发短信内容
        :return:
        """
        content = {"exec_type": 2,
                   "payload": {
                       "msg_content": content,
                       "phone_number": '+86' + self.phone_number,
                   },
                   "request_id": "10011"
                   }
        msg_request = requests.post(self.url, json=content)
        all_logger.info(msg_request.json())

    def check_msg_at_urc(self, is_delay=False):
        """
        检测来短信时上报信息及RI电平状态
        :param is_delay: 是否开启延时, True:开启; False:未开启
        :return:
        """
        # uart = None
        exc_type = None
        exc_value = None
        try:
            # uart = PortCheck(self.uart_port, ['CMTI:'], False, 'Uart')
            self.driver_check.check_usb_driver()
            time.sleep(5)
            self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            self.at_handle.send_at('AT+QCFG="urc/delay",0')
            if is_delay:
                for i in range(3):
                    if self.set_delay():
                        break
                else:
                    raise LinuxRIURCError('设置三次AT+QCFG="urc/delay",1延时上报URC指令不成功')
            self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 10)    # 指定存储空间
            self.at_handle.send_at('AT+CMGD=0,4', 10)   # 让系统发送短信前，首先删除所有短信，以免长期发送导致没有存储空间
            self.at_handle.send_at('AT+QURCCFG="URCPORT","USBAT"', 10)
            at_ri_thread = PortCheck(self.at_port, ['CMTI:'], serial.Serial(self.at_port).getRI(), 'AT')
            at_ri_thread.setDaemon(True)
            at_ri_thread.start()
            self.send_msg()    # 让平台发送短信到模块
            start_time = time.time()
            while True:
                if at_ri_thread.finish_flag:
                    time.sleep(10)  # 多等待一段时间再停止检测RI引脚跳变，观察引脚是否存在多跳变的情况
                    at_ri_thread.stop_flag = True
                    all_logger.info('模块端已接受到短信')
                    break
                if time.time() - start_time > 300:
                    all_logger.info('300S内模块未收到短信，请检查系统端呼短平台是否正常')
                    raise LinuxRIURCError('300S内模块未收到短信，请检查系统端呼短平台是否正常')
            at_ri_thread.join()    # 阻塞ri线程，检查引脚跳变是否正常
            if at_ri_thread.error_msg:
                all_logger.info(at_ri_thread.error_msg)
                raise LinuxRIURCError(at_ri_thread.error_msg)
            # if at_ri_thread.cur_jump_times != 1:
            #     all_logger.info('模块端接收到短信上报后期望RI引脚跳变一次，实际跳变{}次'.format(at_ri_thread.cur_jump_times))
            #     raise LinuxRIURCError('模块端接收到短信上报后期望RI引脚跳变一次，实际跳变{}次'.format(at_ri_thread.cur_jump_times))
            # if not is_delay:    # 未开启延时功能
            #     if at_ri_thread.ri_change_time - at_ri_thread.urc_report_time > 0.05 or at_ri_thread.ri_change_time - at_ri_thread.urc_report_time < 0:
            #         all_logger.info('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
            #         raise LinuxRIURCError('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms')
            #     elif at_ri_thread.ri_change_time - at_ri_thread.urc_report_time < 0:
            #         all_logger.info('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
            #         raise LinuxRIURCError('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变')
            #     else:
            #         all_logger.info('未开启延时,URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            # else:
            #     if at_ri_thread.urc_report_time - at_ri_thread.ri_change_time > 1 or at_ri_thread.urc_report_time - at_ri_thread.ri_change_time < 0:
            #         all_logger.info('开启延时上报，上报URC时间与RI引脚跳动时间超过1S,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            #         raise LinuxRIURCError('开启延时上报，上报URC时间与RI引脚跳动时间超过1S')
            #     elif at_ri_thread.urc_report_time - at_ri_thread.ri_change_time < 0:
            #         all_logger.info('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
            #         raise LinuxRIURCError('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC')
            #     else:
            #         all_logger.info('开启延时后URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            # uart.stop_flag = True
            self.set_delay(False)
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def check_ring_at_urc(self, is_delay=False):
        """
        检测来电时上报信息及RI电平状态
        :param is_delay: 是否开启延时, True:开启; False:未开启
        :return:
        """
        uart = None
        exc_type = None
        exc_value = None
        try:
            uart = PortCheck(self.uart_port, ['NO CARRIER'], False, 'Uart')
            self.driver_check.check_usb_driver()
            time.sleep(5)
            self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            self.at_handle.send_at('AT+QCFG="urc/delay",0')
            if is_delay:
                for i in range(3):
                    if self.set_delay():
                        break
                else:
                    raise LinuxRIURCError('设置三次AT+QCFG="urc/delay",1延时上报URC指令不成功')
            self.at_handle.send_at('AT+QURCCFG="URCPORT","USBAT"', 10)
            at_ri_thread = PortCheck(self.at_port, ['NO CARRIER'], serial.Serial(self.at_port).getRI(), 'AT')
            at_ri_thread.setDaemon(True)
            at_ri_thread.start()
            self.hang_up_after_system_dial(3)  # 让平台给模块打电话
            start_time = time.time()
            while True:
                if at_ri_thread.finish_flag:
                    time.sleep(10)  # 多等待一段时间再停止检测RI引脚跳变，观察引脚是否存在多跳变的情况
                    at_ri_thread.stop_flag = True
                    all_logger.info('模块端已接受到来电')
                    break
                if time.time() - start_time > 300:
                    all_logger.info('300S内模块未收到来电，请检查系统端呼短平台是否正常')
                    raise LinuxRIURCError('300S内模块未收到来电，请检查系统端呼短平台是否正常')
            at_ri_thread.join()    # 阻塞ri线程，检查引脚跳变是否正常
            if at_ri_thread.error_msg:
                all_logger.info(at_ri_thread.error_msg)
                raise LinuxRIURCError(at_ri_thread.error_msg)
        #     expect_jump_times = at_ri_thread.cur_value.count('RING')    # 来电时根据实际上报RING的次数决定期望跳变次数
        #     if at_ri_thread.cur_jump_times != expect_jump_times:
        #         all_logger.info('模块端接收到来电上报后期望RI引脚跳变{}次，实际跳变{}次'.format(at_ri_thread.cur_value.count('RING') + 1, at_ri_thread.cur_jump_times))
        #         raise LinuxRIURCError('模块端接收到来电上报后期望RI引脚跳变{}次，实际跳变{}次'.format(at_ri_thread.cur_value.count('RING') + 1, at_ri_thread.cur_jump_times))
        #     if not is_delay:    # 未开启延时功能
        #         if at_ri_thread.ri_change_time - at_ri_thread.urc_report_time > 0.05 or at_ri_thread.ri_change_time - at_ri_thread.urc_report_time < 0:
        #             all_logger.info('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
        #             raise LinuxRIURCError('未开启延时上报，RI引脚跳动时间与上报URC时间超过50ms')
        #         elif at_ri_thread.ri_change_time - at_ri_thread.urc_report_time < 0:
        #             all_logger.info('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变,RI引脚跳动时间戳为{},URC上报时间戳为{}'.format(at_ri_thread.ri_change_time, at_ri_thread.urc_report_time))
        #             raise LinuxRIURCError('未开启延时上报,RI引脚跳变在上报URC之前，期望在上报URC之后出现引脚跳变')
        #         else:
        #             all_logger.info('未开启延时,URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        #     else:
        #         if at_ri_thread.urc_report_time - at_ri_thread.ri_change_time > 1 or at_ri_thread.urc_report_time - at_ri_thread.ri_change_time < 0:
        #             all_logger.info('开启延时上报，上报URC时间与RI引脚跳动时间超过1S,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        #             raise LinuxRIURCError('开启延时上报，上报URC时间与RI引脚跳动时间超过1S')
        #         elif at_ri_thread.urc_report_time - at_ri_thread.ri_change_time < 0:
        #             all_logger.info('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC,URC上报时间戳为{},RI引脚跳动时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        #             raise LinuxRIURCError('开启延时上报,上报URC在RI引脚跳变之前，期望在RI引脚跳变之后上报URC')
        #         else:
        #             all_logger.info('开启延时后URC上报与RI引脚跳变时间间隔正常，URC上报时间戳为{}，RI跳变时间戳为{}'.format(at_ri_thread.urc_report_time, at_ri_thread.ri_change_time))
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            uart.stop_flag = True
            self.set_delay(False)
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def check_reset_broadcast(self):
        """
        检测重启时各端口URC上报及引脚跳变情况
        :return:
        """
        uart_urc_check = None
        exc_type = None
        exc_value = None
        try:
            uart_check_content = ['RDY', '+CFUN: 1', '+CPIN: READY', '+QUSIM: 1', '+QIND: SMS DONE', '+QIND: PB DONE']
            uart_urc_check = PortCheck(self.uart_port, uart_check_content, False, 'Uart', False)
            self.driver_check.check_usb_driver()
            time.sleep(5)
            self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            self.at_handle.send_at('AT+QCFG="urc/delay",0')
            at_modem_check_content = ['+CPIN: READY', '+QUSIM: 1', '+QIND: SMS DONE', '+QIND: PB DONE']
            self.at_handle.send_at('AT+QURCCFG="URCPORT","ALL"', 10)
            self.at_handle.send_at('AT+CFUN=1,1', 10)
            # 开始定义多个检测URC及RI引脚跳变线程，定义每个口的RI引脚跳变都按照接收到RDY计算，为四次RI引脚跳变
            if self.rg_flag:
                uart_urc_check.setDaemon(True)
                uart_urc_check.start()  # UART检测线程可以立刻启动
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            time.sleep(0.5)
            at_ri_thread = PortCheck(self.at_port, at_modem_check_content, serial.Serial(self.at_port).getRI(), 'AT')
            at_ri_thread.setDaemon(True)
            modem_urc_check = PortCheck(self.modem_port, at_modem_check_content, serial.Serial(self.modem_port).getRI(), 'Modem')
            modem_urc_check.setDaemon(True)
            thread_list = [at_ri_thread, modem_urc_check, uart_urc_check] if self.rg_flag else [at_ri_thread, modem_urc_check]
            at_ri_thread.start()
            modem_urc_check.start()
            start_time = time.time()
            while True:
                if at_ri_thread.finish_flag:
                    all_logger.info('模块重启后AT口已检测到PB DONE上报')
                    time.sleep(10)  # 等待一会后停止检测各个端口的RI引脚跳变情况
                    at_ri_thread.stop_flag = True
                    modem_urc_check.stop_flag = True
                    if self.rg_flag:
                        uart_urc_check.stop_flag = True
                    break
                if time.time() - start_time > 100:
                    all_logger.info('模块重启后100S内未检测到PB DONE上报')
                    raise LinuxRIURCError('模块重启后100S内未检测到PB DONE上报')
            for i in thread_list:
                i.join()    # 阻塞每个线程结束
            # 检查每个线程运行过程是否有异常抛出及RI引脚跳变是否正常
            # if 'RDY' in at_ri_thread.cur_value:
            #     if at_ri_thread.cur_jump_times != 4:
            #         all_logger.info('模块重启后AT口检测到RDY上报，但RI实际跳变{}次，期望跳变4次'.format(at_ri_thread.cur_jump_times))
            #         raise LinuxRIURCError('模块重启后AT口检测到RDY上报，但RI实际跳变{}次，期望跳变4次'.format(at_ri_thread.cur_jump_times))
            #     else:
            #         all_logger.info('模块重启后AT口RI引脚跳变正常')
            # else:
            #     if at_ri_thread.cur_jump_times != 3:
            #         all_logger.info('模块重启后AT口未检测到RDY上报，但RI实际跳变{}次，期望跳变3次'.format(at_ri_thread.cur_jump_times))
            #         raise LinuxRIURCError('模块重启后AT口未检测到RDY上报，但RI实际跳变{}次，期望跳变3次'.format(at_ri_thread.cur_jump_times))
            #     else:
            #         all_logger.info('模块重启后AT口RI引脚跳变正常')
            # if 'RDY' in modem_urc_check.cur_value:
            #     if modem_urc_check.cur_jump_times != 4:
            #         all_logger.info('模块重启后Modem口检测到RDY上报，但RI实际跳变{}次，期望跳变4次'.format(modem_urc_check.cur_jump_times))
            #         raise LinuxRIURCError('模块重启后Modem口检测到RDY上报，但RI实际跳变{}次，期望跳变4次'.format(modem_urc_check.cur_jump_times))
            #     else:
            #         all_logger.info('模块重启后Modem口RI引脚跳变正常')
            # else:
            #     if modem_urc_check.cur_jump_times != 3:
            #         all_logger.info('模块重启后Modem口未检测到RDY上报，但RI实际跳变{}次，期望跳变3次'.format(modem_urc_check.cur_jump_times))
            #         raise LinuxRIURCError('模块重启后Modem口未检测到RDY上报，但RI实际跳变{}次，期望跳变3次'.format(modem_urc_check.cur_jump_times))
            #     else:
            #         all_logger.info('模块重启后Modem口RI引脚跳变正常')
            if at_ri_thread.error_msg:
                all_logger.info(at_ri_thread.error_msg)
                raise LinuxRIURCError(at_ri_thread.error_msg)
            if modem_urc_check.error_msg:
                all_logger.info(modem_urc_check.error_msg)
                raise LinuxRIURCError(modem_urc_check.error_msg)
            if self.rg_flag:
                if uart_urc_check.error_msg:
                    all_logger.info(uart_urc_check.error_msg)
                    raise LinuxRIURCError(uart_urc_check.error_msg)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            uart_urc_check.stop_flag = True
            time.sleep(5)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def powerkey_broadcast(self):
        """
        检测Powerkey方式关机后广播RDY上报
        :return:
        """
        uart_urc_check = None
        exc_type = None
        exc_value = None
        try:
            uart_urc_check = PortCheck(self.uart_port, ['POWERED DOWN'], False, 'Uart')
            uart_urc_check.setDaemon(True)
            self.driver_check.check_usb_driver()
            time.sleep(5)
            self.rg_flag = True if 'RG' in self.at_handle.send_at('ATI') else False
            self.at_handle.send_at('AT+QCFG="urc/delay",0')
            self.at_handle.send_at('AT+QURCCFG="URCPORT","USBAT"', 10)
            at_ri_thread = PortCheck(self.at_port, ['NORMAL POWER DOWN', 'POWERED DOWN'], serial.Serial(self.at_port).getRI(), 'AT')
            at_ri_thread.setDaemon(True)
            at_ri_thread.start()
            modem_urc_check = PortCheck(self.modem_port, ['POWERED DOWN'], serial.Serial(self.modem_port).getRI(), 'Modem')
            modem_urc_check.setDaemon(True)
            modem_urc_check.start()
            if self.rg_flag:
                uart_urc_check.start()
                time.sleep(1)
                self.gpio.set_pwk_low_level()  # RG需要先拉低再拉高再拉低关机
                time.sleep(1)
                self.gpio.set_pwk_high_level()
                time.sleep(1)
                self.gpio.set_pwk_low_level()
            else:
                self.gpio.set_pwk_low_level()  # RM直接拉低即可关机
            while True:
                if at_ri_thread.finish_flag:
                    all_logger.info('Powerkey关机已检测到POWERED DOWN上报')
                    time.sleep(3)
                    at_ri_thread.stop_flag = True
                    modem_urc_check.stop_flag = True
                    if self.rg_flag:
                        uart_urc_check.set_rts_false()
                        uart_urc_check.stop_flag = True
                    break
            at_ri_thread.join()
            modem_urc_check.join()
            if self.rg_flag:
                uart_urc_check.join()
            # if at_ri_thread.cur_jump_times != 2:
            #     all_logger.info('Powerkey关机，AT口RI引脚跳变次数期望为2，实际为{}'.format(at_ri_thread.cur_jump_times))
            #     raise LinuxRIURCError('Powerkey关机，AT口RI引脚跳变次数期望为2，实际为{}'.format(at_ri_thread.cur_jump_times))
            # if modem_urc_check.cur_jump_times != 1:
            #     all_logger.info('Powerkey关机，Modem口RI引脚跳变次数期望为1，实际为{}'.format(modem_urc_check.cur_jump_times))
            #     raise LinuxRIURCError('Powerkey关机，Modem口RI引脚跳变次数期望为1，实际为{}'.format(modem_urc_check.cur_jump_times))
            # if self.rg_flag:
            #     if uart_urc_check.cur_jump_times != 1:
            #         all_logger.info('Powerkey关机，UART口RI引脚跳变次数期望为1，实际为{}'.format(uart_urc_check.cur_jump_times))
            #         raise LinuxRIURCError('Powerkey关机，UART口RI引脚跳变次数期望为1，实际为{}'.format(uart_urc_check.cur_jump_times))
            if at_ri_thread.error_msg:
                all_logger.info(at_ri_thread.error_msg)
                raise LinuxRIURCError(at_ri_thread.error_msg)
            if modem_urc_check.error_msg:
                all_logger.info(modem_urc_check.error_msg)
                raise LinuxRIURCError(modem_urc_check.error_msg)
            if self.rg_flag:
                if uart_urc_check.error_msg:
                    all_logger.info(uart_urc_check.error_msg)
                    raise LinuxRIURCError(uart_urc_check.error_msg)
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            self.gpio.set_vbat_low_level()
            self.gpio.set_pwk_high_level()
            uart_urc_check.stop_flag = True
            self.driver_check.check_usb_driver()
            time.sleep(10)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def delay_cfun_urc_check(self):
        """
        开启延时CFUN01切换上报时URC跳变
        :return:
        """
        self.check_cfun_change_at_urc(True)

    def delay_msg_urc_check(self):
        """
        开启延时来短信上报时URC跳变
        :return:
        """
        self.check_msg_at_urc(True)

    def delay_ring_urc_check(self):
        """
        开启延时来电上报时URC跳变
        :return:
        """
        self.check_ring_at_urc(True)

    def set_delay(self, delay=True):
        """
        设置延时上报
        :param delay: True:设置延时上报，False:关闭延时上报
        :return:
        """
        self.at_handle.send_at('AT+QCFG="urc/delay",{}'.format('1' if delay else '0'), 10)
        delay_vaule = self.at_handle.send_at('AT+QCFG="urc/delay"', 10)
        if ''.join(re.findall(r'\+QCFG: "urc/delay",(\d)', delay_vaule)) != '1':
            return False
        else:
            return True


class PortCheck(Thread):
    def __init__(self, port, check_content: list, origin_ri, port_name, is_ri=True):
        """
        检测端口的URC上报，并将开启的端口传递给RI检测的线程，并开启RI检测线程
        :param port: 需要检测的口
        :param check_content: 检测的内容
        :param origin_ri: 初始电平，RI检测线程需要
        :param port_name: 需要检测的端口名
        :param is_ri: 是否需要检测RI电平，RI检测线程需要
        """
        super().__init__()
        self.port = port
        self.port_name = port_name
        self.error_msg = ''
        self.urc_content = check_content
        self.at_handle = ATHandle(port)
        self.cur_value = ''
        self.origin_ri_line = origin_ri
        all_logger.info('{}口初始电平为{}'.format(port_name, 0 if origin_ri is False else 1))
        self.cur_jump_times = 0
        self.urc_report_time = time.time()
        self.ri_change_time = time.time()
        self.stop_flag = False
        self.is_ri = is_ri
        self.keyword = check_content[-1]
        self.finish_flag = False    # 如果检测到PB Done或者Powered Down就变为True，主线程就会停止检测
        self._port = serial.Serial()
        self._port.port = self.port
        self._port.baudrate = 115200
        self._port.timeout = 0
        self._port.open()
        self.ri_check = RICheck(self._port, origin_ri, port_name, is_ri)
        self.ri_check.setDaemon(True)

    def set_rts_true(self):
        time.sleep(1)
        self._port.setRTS(True)
        all_logger.info('rts: {}'.format(self._port.rts))

    def set_rts_false(self):
        time.sleep(1)
        self._port.setRTS(False)
        all_logger.info('rts: {}'.format(self._port.rts))

    def run(self):
        self.ri_check.start()       # 在这里启动RI检测线程，两线程并行，防止URC检测不及时或者RI引脚检测不及时
        self._port.flushInput()
        self._port.flushOutput()
        start_time = time.time()
        try:
            return_value_cache = ''
            while True:
                return_value = self.at_handle.readline(self._port)
                return_value_cache += return_value
                if self.keyword in return_value:
                    self.urc_report_time = time.time()
                    self.finish_flag = True
                if self.stop_flag:
                    all_logger.info('收到结束{}口RI及URC检测子线程信号'.format(self.port_name))
                    for i in range(10):
                        if self.ri_check.is_alive():
                            self.ri_check.stop_flag = True
                            time.sleep(2)
                        else:
                            self.ri_check.join()
                    all_logger.info('{}口RI进程结束完毕'.format(self.port_name))
                    break
                if time.time() - start_time > 300:
                    all_logger.info('300S内未检测到{}URC上报'.format(self.keyword))
                    self.finish_flag = True     # 超时未检测到URC上报后也应该发出结束信号
                    raise LinuxRIURCError('300S内未检测到{}URC上报'.format(self.keyword))
            self.cur_value = return_value_cache
            self.cur_jump_times = self.ri_check.cur_jump_times
            self.ri_change_time = self.ri_check.ri_change_time
            all_logger.info('{}口检测到上报URC为:\r\n{}'.format(self.port_name, self.cur_value.strip().replace('\r\n', '  ')))
            for i in self.urc_content:
                if i not in return_value_cache:
                    self.error_msg = '{}口未检测到{}上报'.format(self.port_name, i)
            else:
                all_logger.info('{}口URC检测正常'.format(self.port_name))
        except Exception as e:
            self.error_msg = str(e)
        finally:
            all_logger.info('结束{}口RI及URC检测子线程'.format(self.port_name))
            self.error_msg += self.ri_check.error_msg
            self._port.close()


class RICheck(Thread):
    def __init__(self, port, origin_ri, port_name, is_ri=True):
        """
        检测端口的RI电平状态
        :param port: 需要检测的口
        :param origin_ri:  端口初始RI电平状态
        :param port_name:  端口名
        :param is_ri:  是否检测RI引脚电平，默认检测
        """
        super().__init__()
        self.port = port
        self.port_name = port_name
        self.error_msg = ''
        self.origin_ri_line = origin_ri
        self.cur_jump_times = 0
        self.stop_flag = False
        self.is_ri = is_ri
        self.ri_change_time = time.time()

    def run(self):
        continued_time_list = []
        try:
            with self.port as _port:
                while True:
                    if _port.getRI() != self.origin_ri_line:
                        start_time = time.time()
                        self.ri_change_time = time.time()
                        while True:
                            if _port.getRI() == self.origin_ri_line:
                                continued_time = float(time.time() - start_time) * 1000
                                all_logger.info('{}口RI引脚跳变持续时间为{}ms'.format(self.port_name, format(continued_time, '.2f')))
                                continued_time_list.append(continued_time)
                                self.cur_jump_times += 1
                                break
                            if time.time() - start_time > 10000:
                                raise LinuxRIURCError('{}口引脚跳变一次后，10S内未跳变回默认状态'.format(self.port_name))
                    if self.stop_flag:
                        all_logger.info('收到结束{}口URC检测子线程信号'.format(self.port_name))
                        break
            for i in continued_time_list:
                if i > 500 and self.is_ri:
                    all_logger.info('{}口RI引脚跳变时间间隔超过500ms'.format(self.port_name))
                    raise LinuxRIURCError('{}口RI引脚跳变时间间隔超过500ms'.format(self.port_name))
                else:
                    all_logger.info('{}口RI引脚跳变时间间隔为{}ms'.format(self.port_name, i))
        except Exception:   # noqa
            self.error_msg = ''     # RI引脚跳变相关错误信息不再上报


if __name__ == '__main__':
    linux_ri = LinuxRiUrcManager('COM6', 'COM3', 'COM28', 'COM5', '18119613687')
    linux_ri.hang_up_after_system_dial(3)
