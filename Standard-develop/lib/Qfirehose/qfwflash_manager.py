# -*- encoding=utf-8 -*-
import datetime
import os
import subprocess
from threading import Event
import logging
import time


class Qfwflash:
    def __init__(self, main_queue, route_queue, uart_queue, log_queue, uart_port, evb, version, imei, is_calibration,
                 VBAT, is_5g_m2_evb, runtimes):
        self.main_queue = main_queue
        self.route_queue = route_queue
        self.uart_queue = uart_queue
        self.uart_port = uart_port
        self.evb = evb
        self.imei = imei
        self.version = version
        self.is_calibration = is_calibration
        self.runtimes = runtimes
        self.VBAT = VBAT
        self.is_5g_m2_evb = is_5g_m2_evb
        self.log_queue = log_queue
        self.logger = logging.getLogger(__name__)

    def route_queue_put(self, *args, queue=None):
        """
        往某个queue队列put内容，默认为None时向route_queue发送内容，并且接收main_queue队列如果有内容，就接收。
        :param args: 需要往queue中发送的内容
        :param queue: 指定queue发送，默认route_queue
        :return: main_queue内容
        """
        self.logger.info('{}->{}'.format(queue, args))
        if queue is None:
            evt = Event()
            self.route_queue.put([*args, evt])
            evt.wait()
        else:
            evt = Event()
            queue.put([*args, evt])
            evt.wait()
        _main_queue_data = self.main_queue.get(timeout=0.1)
        return _main_queue_data

    def vbat(self, packagename=''):
        """
        M.2 EVB：拉高DTR断电->检测驱动消失->拉低DTR上电；
        5G-EVB_V2.1：拉高RTS->拉高DTR断电->检测驱动消失->拉低DTR上电。
        5G-M.2-EVB: 拉低DTR断电 -> 检测驱动消失 -> 拉高DTR上电：
        :return: None
        """
        if self.is_5g_m2_evb:
            self.log_queue.put(['at_log', "[{}] 拉动DTR控制VBAT断电上电\n".format(datetime.datetime.now())])
            # 断电
            self.route_queue_put('Uart', 'set_dtr_true')
            self.log_queue.put(['at_log', "[{}] Set DTR True".format(datetime.datetime.now())])
            # 检测驱动消失
            self.route_queue_put('Process', 'check_usb_driver_dis', True, self.runtimes)
            time.sleep(3)
            if packagename:
                val = os.popen('ps -ef | grep QFirehose').read()
                if 'QFirehose -f {}'.format(packagename) in val:
                    self.log_queue.put(['at_log', '[{}] 关闭升级进程前升级进程情况\n:{}'.format(datetime.datetime.now(), val)])
                    try:
                        kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                        if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                            self.log_queue.put(['at_log', '[{}] 上电前已关闭升级进程'.format(datetime.datetime.now())])
                            time.sleep(1)
                            val_after = os.popen('ps -ef | grep QFirehose').read()
                            self.log_queue.put(
                                ['at_log', '[{}] 关闭升级进程后升级进程情况\n:{}'.format(datetime.datetime.now(), val_after)])
                    except subprocess.TimeoutExpired:
                        self.log_queue.put(['all', '[{}] 关闭升级进程失败'.format(datetime.datetime.now())])
            # 上电
            self.route_queue_put('Uart', 'set_dtr_false')
            self.log_queue.put(['at_log', "[{}] Set DTR False".format(datetime.datetime.now())])
        else:
            self.log_queue.put(['at_log', "[{}] 拉动DTR控制VBAT断电上电\n".format(datetime.datetime.now())])
            # 断电
            self.route_queue_put('Uart', 'set_dtr_false')
            self.log_queue.put(['at_log', "[{}] Set DTR False".format(datetime.datetime.now())])
            # 检测驱动消失
            self.route_queue_put('Process', 'check_usb_driver_dis', True, self.runtimes)
            # 等待3S上电
            time.sleep(3)
            if packagename:
                val = os.popen('ps -ef | grep QFirehose').read()
                if 'QFirehose -f {}'.format(packagename) in val:
                    self.log_queue.put(['at_log', '[{}] 关闭升级进程前升级进程情况\n:{}'.format(datetime.datetime.now(), val)])
                    try:
                        kill_qf = subprocess.run('killall QFirehose', shell=True, timeout=10)
                        if kill_qf.returncode == 0 or kill_qf.returncode == 1:
                            self.log_queue.put(['at_log', '[{}] 上电前已关闭升级进程'.format(datetime.datetime.now())])
                            time.sleep(1)
                            val_after = os.popen('ps -ef | grep QFirehose').read()
                            self.log_queue.put(['at_log', '[{}] 关闭升级进程后升级进程情况\n:{}'.format(datetime.datetime.now(), val_after)])
                    except subprocess.TimeoutExpired:
                        self.log_queue.put(['all', '[{}] 关闭升级进程失败'.format(datetime.datetime.now())])
            # 上电
            self.route_queue_put('Uart', 'set_dtr_true')
            self.log_queue.put(['at_log', "[{}] Set DTR True".format(datetime.datetime.now())])
            self.route_queue_put('Uart', 'set_rts_false')
            self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])

    def qfwflash_init(self):
        # 1. 断电后上电
        self.vbat()
        # 2. 初始化检测USB驱动
        main_queue_data = self.route_queue_put('Process', 'check_usb_driver', True, self.runtimes)
        if main_queue_data is False:
            print('初始化检测驱动加载失败，退出脚本')
            exit()
        # 3. 打开AT口
        main_queue_data = self.route_queue_put('AT', 'open', self.runtimes)
        if main_queue_data is False:
            print('初始化打开AT口异常，退出脚本')
            exit()
        # 4. 检测开机URC
        main_queue_data = self.route_queue_put('AT', 'check_urc', self.runtimes)
        if main_queue_data is False:
            print('初始化未检测到URC上报，退出脚本')
            exit()
        # 5. 普通AT初始化
        main_queue_data = self.route_queue_put('AT', 'prepare_at', self.version, self.imei, False, self.runtimes)
        if main_queue_data is False:
            print('AT初始化异常，退出脚本')
            exit()
        # 6. AT+QPRTPARA?
        main_queue_data = self.route_queue_put('AT', 'AT+QPRTPARA?', 6, 1, self.runtimes)
        if main_queue_data is False:
            print('初始化，备份指令执行异常，退出脚本')
            exit()
        # 7. 检测校准指令是否正常
        self.route_queue_put('AT', 'check_calibration', self.is_calibration, self.runtimes)
        # 7. 关闭AT口
        main_queue_data = self.route_queue_put('AT', 'close', self.runtimes)
        if main_queue_data is False:
            print('初始化关闭端口出现异常，退出脚本')
            exit()

    def qfwflash_normal_exception_init(self):
        # 关口防止端口变化
        None if self.runtimes == 0 else self.route_queue_put('AT', 'close', self.runtimes)
        # 1. 断电后上电
        self.vbat()
        # 3. 初始化检测USB驱动
        main_queue_data = self.route_queue_put('Process', 'check_usb_driver', True, self.runtimes)
        if main_queue_data is False:
            return False
        # 4. 打开AT口
        main_queue_data = self.route_queue_put('AT', 'open', self.runtimes)
        if main_queue_data is False:
            return False
        # 5. 检测URC
        main_queue_data = self.route_queue_put('AT', 'check_urc', self.runtimes)
        if main_queue_data is False:
            return False
        # 6. 关闭AT口
        main_queue_data = self.route_queue_put('AT', 'close', self.runtimes)
        if main_queue_data is False:
            return False

    def qfwflash_upgrade_vbat(self, packagename, mode, dm_port, runtimes):
        if self.is_5g_m2_evb:
            self.route_queue_put('Uart', 'set_rts_false')
            self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
            self.vbat(packagename)
            time.sleep(10)
            self.route_queue_put('Process', 'rts_check', runtimes)    # 首先lsusb查询模块当前是否处于紧急下载模式
            main_queue_data = self.route_queue_put('Process', 'get_rts_state', runtimes)
            if main_queue_data:    # 代表需要拉低rts
                self.route_queue_put('Uart', 'set_rts_true')
                self.log_queue.put(['at_log', "[{}] Set RTS True".format(datetime.datetime.now())])
            main_queue_data = self.route_queue_put('Process', 'qfwflash_upgrade', packagename, False, mode, dm_port,
                                                   runtimes)
            if main_queue_data is False:
                self.log_queue.put(['at_log', "[{}] 拉高RTS".format(datetime.datetime.now())])
                self.route_queue_put('Uart', 'set_rts_false')
                self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
                return False
            else:
                self.log_queue.put(['at_log', "[{}] 升级成功，拉高RTS".format(datetime.datetime.now())])
                self.route_queue_put('Uart', 'set_rts_false')
                self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
                return True
        else:
            # 断电升级执行
            self.route_queue_put('Uart', 'set_rts_false')
            self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
            self.vbat(packagename)
            time.sleep(10)
            self.route_queue_put('Process', 'rts_check', runtimes)    # 首先lsusb查询模块当前是否处于紧急下载模式
            main_queue_data = self.route_queue_put('Process', 'get_rts_state', runtimes)
            if main_queue_data:    # 代表需要拉低rts
                self.route_queue_put('Uart', 'set_rts_true')
                self.log_queue.put(['at_log', "[{}] Set RTS True".format(datetime.datetime.now())])
            main_queue_data = self.route_queue_put('Process', 'qfwflash_upgrade', packagename, False, mode, dm_port,
                                                   runtimes)
            if main_queue_data is False:
                self.log_queue.put(['at_log', "[{}] 拉高RTS".format(datetime.datetime.now())])
                self.route_queue_put('Uart', 'set_rts_false')
                self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
                return False
            else:
                self.log_queue.put(['at_log', "[{}] 升级成功，拉高RTS".format(datetime.datetime.now())])
                self.route_queue_put('Uart', 'set_rts_false')
                self.log_queue.put(['at_log', "[{}] Set RTS False".format(datetime.datetime.now())])
                return True

    def upgrade_fail_init(self, runtimes):
        """
        QFirehose升级失败后使用该方法初始化,因为存在升级失败后模块进入紧急下载模式的情况,端口不会正常加载
        """
        self.vbat()
        time.sleep(10)
        if self.is_5g_m2_evb:
            self.route_queue_put('Process', 'rts_check', runtimes)  # lsusb查询模块当前是否处于紧急下载模式
        else:
            self.route_queue_put('Process', 'rts_check', runtimes)  # lsusb查询模块当前是否处于紧急下载模式
            main_queue_data = self.route_queue_put('Process', 'get_rts_state', runtimes)
            if main_queue_data:  # 代表需要拉低rts
                self.route_queue_put('Uart', 'set_rts_true')
                self.log_queue.put(['at_log', "[{}] Set RTS True".format(datetime.datetime.now())])
