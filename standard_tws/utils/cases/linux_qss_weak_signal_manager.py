import sys
import threading
import traceback
import pymysql
import requests
import serial
from icmplib import ping, multiping  # noqa
from requests_toolbelt.adapters import source
from utils.functions.gpio import GPIO
from utils.functions.linux_api import QuectelCMThread
from utils.operate.at_handle import ATHandle
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
import subprocess
import time
import os
import re
from tools.qss.qss_client import ConnectQSS, WriteSimcard
import pandas as pd  # noqa
from selenium import webdriver  # noqa
from selenium.webdriver.common.by import By  # noqa
from utils.exception.exceptions import QSSWeakSignalError


class LinuxQSSWeakSignalManager:
    def __init__(self, at_port, dm_port, debug_port, wwan_path, qmi_usb_network_card_name,
                 local_network_card_name, qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name,
                 name_sub_version, chrome_driver_path, default_sa_band, default_nsa_band, default_lte_band, default_wcdma_band):
        self.driver_check = DriverChecker(at_port, dm_port)
        self.at_port = at_port
        self.dm_port = dm_port
        self.debug_port = debug_port
        self.at_handle = ATHandle(at_port)
        self.wwan_path = wwan_path
        self.qss_ip = qss_ip
        self.local_ip = local_ip
        self.node_name = node_name
        self.mme_file_name = mme_file_name
        self.enb_file_name = enb_file_name
        self.ims_file_name = ims_file_name
        self.write_simcard = WriteSimcard(self.at_port)
        self.gpio = GPIO()
        self.local_network_card_name = local_network_card_name
        self.qmi_usb_network_card_name = qmi_usb_network_card_name
        self.name_sub_version = name_sub_version
        self.chrome_driver_path = chrome_driver_path
        # 组网Network(NSA),Band(B3+n41),PCI(123),LTE频点(1300),5G频点(504990),网络配置(移动5G-Auto),DLcapacity,ULcapacity,测试接口,测试系统,驱动版本,软件版本,测试次数,RSRP,SINR,RSRQ,"DL(Mbps)","UL(Mbps)",DL-AVG,UL-AVG,SIM-ICCID,SIM-IMSI,模块PN,模块IMEI,测试时间段
        self.speedtest_data_col = ['Dial',
                                   'test_times',
                                   'QRSRP_PRX',
                                   'QRSRP_DRX',
                                   'QRSRP_RX2',
                                   'QRSRP_RX3',
                                   'RSRP',
                                   'SINR',
                                   'RSRQ',
                                   'DL(Mbps)',
                                   'UL(Mbps)',
                                   'Ping(ms)',
                                   'Jitter(ms)',
                                   'Network',
                                   'Band',
                                   'PCI',
                                   'LTE_Frequency',
                                   '5G_Frequency',
                                   'Interface',
                                   'OS',
                                   'Driver_Version',
                                   'Version',
                                   'ICCID',
                                   'IMSI',
                                   'IMEI',
                                   'test_time']
        self.speedtest_records = []
        self.speedtest_records.append(self.speedtest_data_col)
        self.speedtest_data = {'Dial': '', 'test_times': '',
                               'QRSRP_PRX': '', 'QRSRP_DRX': '', 'QRSRP_RX2': '', 'QRSRP_RX3': '',
                               'RSRP': '', 'SINR': '', 'RSRQ': '',
                               'DL(Mbps)': '', 'UL(Mbps)': '', 'Ping(ms)': '', 'Jitter(ms)': '',
                               'Network': '', 'Band': '', 'PCI': '', 'LTE_Frequency': '', '5G_Frequency': '',
                               'Interface': '', 'OS': '', 'Driver_Version': '', 'Version': '',
                               'ICCID': '', 'IMSI': '', 'IMEI': '', 'test_time': ''}
        self.test_fail = []
        self.default_sa_band = default_sa_band
        self.default_nsa_band = default_nsa_band
        self.default_lte_band = default_lte_band
        self.default_wcdma_band = default_wcdma_band
        self.enb_file_name_now = ''

    def send_at_until_rusult(self, at_command, until_result, time_out=300, at_time_out=3):
        """
        at_command: AT命令
        until_result： 期望结果
        time_out： 超时时间
        at_time_out： 单条at超时时间
        一直发送AT，直到获得期望的结果或者超时报错
        """
        start_time = time.time()
        while time.time() - start_time < time_out:
            return_value = self.at_handle.send_at(at_command, at_time_out)
            all_logger.info(return_value)
            if until_result in return_value:
                break
            time.sleep(1)
        else:
            raise QSSWeakSignalError(f'异常! {time_out}s内查询{at_command} 结果中未获得期望字段 {until_result}')

    def test_linux_qss_dial_rate_qmi(self):
        # 拨号前初始化和设置
        self.qmi_start_init()
        # 拨号测速
        self.qmi_quectel_cm(self.qmi_usb_network_card_name, 'QMI', 'USB')

    def check_bands_exist(self, enb_file_name_now):
        """
        从配置文件名称中，分离出各种band，然后判断这些band当前版本是否支持，如果不支持则不测试
        """
        nsa_bands = ''
        sa_bands = ''
        if 'B' in enb_file_name_now.split('-')[-1].split('.')[0].upper():
            nsa_bands = re.findall(r'N(\d+)', enb_file_name_now.upper())
        else:
            sa_bands = re.findall(r'N(\d+)', enb_file_name_now.upper())

        lte_bands = re.findall(r'B(\d+)', enb_file_name_now.upper())
        if len(lte_bands) >= 1:
            for lte_band in lte_bands:
                if lte_band not in self.default_lte_band.split(':'):
                    all_logger.info(f"当前版本不支持此 LTE band {lte_band}")
                    return False
        if len(nsa_bands) >= 1:
            for nsa_band in nsa_bands:
                if nsa_band not in self.default_nsa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 NSA band {nsa_band}")
                    return False
        if len(sa_bands) >= 1:
            for sa_band in sa_bands:
                if sa_band not in self.default_sa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 SA band {sa_band}")
                    return False
        return True

    def check_weak_signal(self):
        # AT+QRSRP
        prx, drx, rx2, rx3 = self.get_qrsrp()
        # AT+QENG="servingcell"中的'RSRP','SINR','RSRQ',
        RSRP = '' if self.get_qeng_info('RSRP') is False else self.get_qeng_info('RSRP')['RSRP']
        SINR = '' if self.get_qeng_info('SINR') is False else self.get_qeng_info('SINR')['SINR']
        RSRQ = '' if self.get_qeng_info('RSRQ') is False else self.get_qeng_info('RSRQ')['RSRQ']
        all_logger.info("检查信号值:")
        all_logger.info("*************************************************")
        all_logger.info("AT+QRSRP:")
        all_logger.info(f'prx:{prx}')
        all_logger.info(f'drx:{drx}')
        all_logger.info(f'rx2:{rx2}')
        all_logger.info(f'rx3:{rx3}')
        all_logger.info('AT+QENG="servingcell":')
        all_logger.info(f'RSRP:{RSRP}')
        all_logger.info(f'SINR:{SINR}')
        all_logger.info(f'RSRQ:{RSRQ}')
        all_logger.info("*************************************************")
        for i in prx, drx, rx2, rx3, RSRP:
            if int(i) > -90:
                raise QSSWeakSignalError(f"信号值异常，当前信号值不在弱信号范围：{i}")

    def check_qss_network_bands(self, enb_file_name_now):
        # 检查注网是否正常
        all_logger.info(f"开始检查 {enb_file_name_now} 注网后band是否正常")
        return_qeng = self.at_handle.send_at('AT+qeng="servingcell"', 3)
        # CA
        if '-CA-' in enb_file_name_now.upper():
            return_qcainfo = self.at_handle.send_at('AT+QCAINFO', 3)
            all_logger.info(return_qcainfo)
            qss_file_sa_bands = re.findall(r'N(\d+)', enb_file_name_now.upper())
            qss_file_lte_bands = re.findall(r'B(\d+)', enb_file_name_now.upper())
            qcainfo_sa_bands = re.findall(r'NR5G\sBAND\s(\d+)', return_qcainfo)
            qcainfo_lte_bands = re.findall(r'LTE\sBAND\s(\d+)', return_qcainfo)
            if qss_file_sa_bands[0] != '':
                for band in qss_file_sa_bands[0]:
                    if band not in qcainfo_sa_bands:
                        all_logger.info(f"CA注网异常: {self.enb_file_name_now}")
                        return False
            if qss_file_lte_bands[0] != '':
                for band in qss_file_lte_bands[0]:
                    if band not in qcainfo_lte_bands:
                        all_logger.info(f"CA注网异常: {self.enb_file_name_now}")
                        return False
        # SA
        elif 'NR5G-SA' in return_qeng and '-SA-' in enb_file_name_now.upper():
            qeng_sa_band = ''.join(re.findall(r'\+QENG:\s"servingcell",".*",".*",".*",\s?.*,.*,.*,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*', return_qeng))
            qss_file_sa_band = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            if qeng_sa_band != qss_file_sa_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        # NSA
        elif 'NR5G-NSA' in return_qeng and '-NSA-' in enb_file_name_now.upper():
            self.at_handle.send_at('AT+CFUN=0', 10)
            self.at_handle.send_at('AT+CFUN=1', 10)
            self.at_handle.check_network()
            return_qeng = self.at_handle.send_at('AT+qeng="servingcell"', 3)
            if '-32768,-32768,-32768' in return_qeng:
                all_logger.info(f"注网NSA异常：{return_qeng}")
                return False
            qeng_sa_band = ''.join(re.findall(r'\+QENG:\s"NR5G-NSA",.*,.*,.*,.*,.*,.*,.*,(.*),.*,.*', return_qeng))
            qss_file_sa_band = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            if qeng_sa_band != qss_file_sa_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
            qeng_lte_band = ''.join(re.findall(r'\+QENG:\s"LTE",".*",.*,\d+,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*,.*,.*,.*,.*', return_qeng))
            qss_file_lte_band = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if qeng_lte_band != qss_file_lte_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        # LTE
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng and '-LTE-' in enb_file_name_now.upper():
            qeng_lte_band = ''.join(re.findall(r'\+QENG:\s"servingcell",".*",".*",".*",.*,\d+,.*,.*,.*,(.*),.*,.*,.*,.*,.*,.*,.*,.*,.*,.*', return_qeng))
            qss_file_lte_band = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if qeng_lte_band != qss_file_lte_band:
                all_logger.info(f"注网失败 : {return_qeng}")
                return False
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return False

        all_logger.info("注网正常")
        return True

    def check_network(self, timeout=300, times=2):
        """
        连续多次检查模块驻网。每次之间切换cfun
        :return: False: 模块没有注上网。cops_value:模块注册的网络类型，
        """
        all_logger.info("检查网络")
        check_network_start_time = time.time()
        times_now = 0
        while True:
            return_value = self.at_handle.send_at('AT+COPS?')
            cell_value = self.at_handle.send_at('AT+QENG="servingcell"')
            cops_value = "".join(re.findall(r'\+COPS: .*,.*,.*,(\d+)', return_value))
            if cops_value != '':
                all_logger.info("当前网络：{}".format(cops_value))
                all_logger.info("当前小区信息：{}".format(cell_value))
                time.sleep(1)
                return cops_value
            if time.time() - check_network_start_time > timeout:
                all_logger.error("{}内找网失败".format(timeout))
                all_logger.info("当前小区信息：{}".format(cell_value))
                check_network_start_time = time.time()
                self.at_handle.cfun0()
                time.sleep(3)
                self.at_handle.cfun1()
                time.sleep(10)
                times_now += 1
            if times_now == times:
                all_logger.error("连续{}次找网失败".format(times))
                all_logger.info("当前小区信息：{}".format(cell_value))
                all_logger.info(f'找网失败:{self.enb_file_name_now}')
                self.test_fail.append(f'找网失败:{self.enb_file_name_now}')
                return False
            time.sleep(1)

    def dump_check(self, time_out=300):
        start_time = time.time()
        while time.time() - start_time < time_out:
            port_list = self.at_handle.get_port_list()
            if self.dm_port in port_list and self.at_port not in port_list:  # 发现仅有DM口并且没有AT口
                time.sleep(3)  # 等待3S口还是只有AT口没有DM口判断为DUMP，RG502QEAAAR01A01M4G出现两个口相差1秒
                port_list = self.at_handle.get_port_list()
                if self.dm_port in port_list and self.at_port not in port_list:
                    all_logger.error('模块DUMP')
                    raise QSSWeakSignalError(f'模块出现DUMP!{port_list}')
        else:
            all_logger.info(f'{time_out}s内模块没有出现DUMP')

    def open_qss(self, need_check_network=True, ims_open=False):
        """
        need_check_network : 是否需要检查注网
        ims_open： 是否需要开启ims文件
        """
        # 将卡写成00101卡
        self.write_simcard_00101()

        all_logger.info(f'self.enb_file_name:{self.enb_file_name_now}')
        if ims_open:
            task = [self.mme_file_name, self.enb_file_name_now, self.ims_file_name]
        else:
            task = [self.mme_file_name, self.enb_file_name_now]
        qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QSSWeakSignalError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(15)
        self.at_handle.cfun0()
        time.sleep(5)
        self.at_handle.cfun1()
        time.sleep(5)
        # 是否需要检查开网后是否注网正常
        if need_check_network:
            check_network_result = self.check_network()
            if not check_network_result:
                raise QSSWeakSignalError('注网异常')
            # 检查注网后的bands是否对应
            check_bands_result = self.check_qss_network_bands(self.enb_file_name_now)
            if not check_bands_result:
                raise QSSWeakSignalError('检查注网后的bands异常')

        return start_time, qss_connection

    def write_simcard_00101(self):
        # 将卡写成00101卡
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('00101'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('00101', '8949024')

    def qss_call(self):
        self.at_handle.send_at('ATD666;', 3)
        time.sleep(5)
        return_call = self.at_handle.send_at('AT+CLCC', 3)
        if 'CLCC: 3,0,0,0,0,"666"' in return_call or 'CLCC: 2,0,2,0,0,"666"' in return_call:
            all_logger.info(f"通话正常:{return_call}")
            return True
        else:
            all_logger.info(f"通话异常:{return_call}")
            return False

    def get_weak_enb_file_name(self):
        """
        找到当前版本支持的弱信号配置文件
        """
        nsa_enb_file_name_now = ''
        sa_enb_file_name_now = ''
        for enb_file_name_now in self.enb_file_name:
            nsa_bands = ''
            sa_bands = ''
            all_logger.info(enb_file_name_now)
            if '-NSA-' in enb_file_name_now.upper() and 'WEAK' in enb_file_name_now.upper():
                nsa_bands = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            elif '-SA-' in enb_file_name_now.upper() and 'WEAK' in enb_file_name_now.upper():
                sa_bands = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            else:
                all_logger.info("此配置文件非弱信号配置文件")
            lte_bands = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if lte_bands:
                if lte_bands not in self.default_lte_band.split(':'):
                    all_logger.info(f"当前版本不支持此 LTE band {lte_bands}")
                    continue
            if nsa_bands and nsa_enb_file_name_now == '':
                if nsa_bands not in self.default_nsa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 NSA band {nsa_bands}")
                    continue
                nsa_enb_file_name_now = enb_file_name_now
            if sa_bands and sa_enb_file_name_now == '':
                if sa_bands not in self.default_sa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 SA band {sa_bands}")
                    continue
                sa_enb_file_name_now = enb_file_name_now
            if sa_enb_file_name_now != '' and nsa_enb_file_name_now != '':
                break
        else:
            all_logger.info("未找到当前版本支持的弱信号配置文件！")
            return False
        all_logger.info(f'NSA: {nsa_enb_file_name_now}, SA: {sa_enb_file_name_now}')
        return nsa_enb_file_name_now, sa_enb_file_name_now

    def get_enb_file_name(self):
        """
        找到当前版本支持的正常信号配置文件
        """
        nsa_enb_file_name_now = ''
        sa_enb_file_name_now = ''
        for enb_file_name_now in self.enb_file_name:
            nsa_bands = ''
            sa_bands = ''
            all_logger.info(enb_file_name_now.split('-')[-1].upper())
            if 'B' in enb_file_name_now.split('-')[-1].upper():
                nsa_bands = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            else:
                sa_bands = ''.join(re.findall(r'N(\d+)', enb_file_name_now.upper()))
            lte_bands = ''.join(re.findall(r'B(\d+)', enb_file_name_now.upper()))
            if lte_bands:
                if lte_bands not in self.default_lte_band.split(':'):
                    all_logger.info(f"当前版本不支持此 LTE band {lte_bands}")
                    continue
            if nsa_bands and nsa_enb_file_name_now == '':
                if nsa_bands not in self.default_nsa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 NSA band {nsa_bands}")
                    continue
                nsa_enb_file_name_now = enb_file_name_now
            if sa_bands and sa_enb_file_name_now == '':
                if sa_bands not in self.default_sa_band.split(':'):
                    all_logger.info(f"当前版本不支持此 SA band {sa_bands}")
                    continue
                sa_enb_file_name_now = enb_file_name_now
            if sa_enb_file_name_now != '' and nsa_enb_file_name_now != '':
                break
        else:
            all_logger.info("未找到当前版本支持的正常信号配置文件！")
            return False
        return nsa_enb_file_name_now, sa_enb_file_name_now

    def get_qss_connection(self, tesk_duration=300, task_status=0, task=None):
        param_dict = {
            'name_group': 'QSS_Weak_Signal',  # 发起任务的用例名称(可以从下发消息中获取)
            'node_name': self.node_name,  # 发起任务的设备名称(可以从下发消息中获取)
            'ip': self.local_ip,  # 发起任务的设备IP地址(可以从下发消息中获取)
            'qss_ip': self.qss_ip,  # 所用qss服务器的IP
            'tesk_duration': tesk_duration,  # 任务持续时间或者需要增加的时间
            'task_status': task_status,  # 任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
            'task': task,  # 任务内容(需要开启网络的mme\enb\ims等文件名称列表)
        }
        qss_json_now = ConnectQSS.create_qss_task_json(**param_dict)
        servet_test = ConnectQSS(self.qss_ip, self.local_ip, qss_json_now)
        return servet_test

    @staticmethod
    def end_task(qss_connection):
        end_result = qss_connection.end_task()
        if end_result:
            all_logger.info("结束QSS成功")
        else:
            all_logger.info("结束QSS失败")

    @staticmethod
    def delay_task(start_time, qss_connection, time_need):
        if time.time() - start_time < time_need:
            delay_result = qss_connection.delay_task(time_need)
            if delay_result:
                all_logger.info("延时qss成功")
            else:
                all_logger.info('延时qss异常')

    def get_network(self):
        return_qeng = self.at_handle.send_at('AT+QENG="servingcell"', 3)
        all_logger.info(return_qeng)
        if 'NR5G-SA' in return_qeng:
            network_mode = 'SA'
        elif 'NR5G-NSA' in return_qeng:
            network_mode = 'NSA'
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng:
            network_mode = 'LTE'
        elif 'WCDMA' in return_qeng:
            network_mode = 'WCDMA'
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return 'No Network'
        all_logger.info(f"当前注网模式为：{network_mode}")
        return network_mode

    def speedtest_dial(self, dial='QMI', network='NSA', interface='USB', test_times=3):
        all_logger.info(f'开始进行{dial}测速')
        self.get_speed_test_data_all(dial=dial, network=network, interface=interface)
        for i in range(int(test_times)):
            all_logger.info(f'开始第{i+1}次测速')
            self.get_speed_test_data_single(test_times=f'{i + 1}')
            self.speedtest_records.append(list(self.speedtest_data.values()))

    def speedtest_qss(self):
        """
        单次测速获取速率
        """
        dl_text = 0
        ul_text = 0
        ping_text = 0
        jit_text = 0
        try:
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')  # 这个配置很重要
            driver = webdriver.Chrome(chrome_options=chrome_options,
                                      executable_path=self.chrome_driver_path)  # 如果没有把chromedriver加入到PATH中，就需要指明路径

            driver.get("http://192.168.2.1")
            driver.maximize_window()
            time.sleep(10)

            # click start
            driver.find_element(By.ID, "startStopBtn").click()
            time.sleep(60)

            # get resutl
            ping_text = driver.find_element(By.ID, "pingText").text  # ping延迟
            jit_text = driver.find_element(By.ID, "jitText").text  # ping抖动
            dl_text = driver.find_element(By.ID, "dlText").text  # 下载速度
            ul_text = driver.find_element(By.ID, "ulText").text  # 上传速度
            all_logger.info("*************************************************")
            all_logger.info(f'Ping(ms):{ping_text}')
            all_logger.info(f'Jitter(ms):{jit_text}')
            all_logger.info(f'Download(Mbps):{dl_text}')
            all_logger.info(f'Upload(Mbps):{ul_text}')
            all_logger.info("*************************************************")
        except Exception as e:
            all_logger.info(e)
            all_logger.info(f'speed_test_fail:{self.enb_file_name_now}')
            self.test_fail.append(f'speed_test_fail:{self.enb_file_name_now}')
            return False
        finally:
            return dl_text, ul_text, ping_text, jit_text

    def get_cimi(self):
        rerurn_cimi = self.at_handle.send_at("AT+CIMI", 3)
        cimi_value = ''.join(re.findall(r'(\d.*)\r', rerurn_cimi))
        if cimi_value != '':
            all_logger.info(f"当前CIMI为 : {cimi_value}")
            return cimi_value
        else:
            all_logger.info("获取CIMI失败！")
            return False

    def speedtest_report(self, case_name):
        """
        生成测速报告
        """
        all_logger.info(self.speedtest_data)
        df = pd.DataFrame(data=self.speedtest_records)
        speedtest_report_path = os.path.join(os.getcwd(), '5G_Speed_test_report_' + case_name + '.csv')
        df.to_csv(speedtest_report_path, index=False)  # noqa
        all_logger.info(speedtest_report_path)

    def get_speed_test_data_single(self, test_times='1'):
        """
        测速报告中各种信息
        """
        # 'test_times',
        self.speedtest_data['test_times'] = test_times
        prx, drx, rx2, rx3 = self.get_qrsrp()
        # 'QRSRP_PRX',
        self.speedtest_data['QRSRP_PRX'] = prx
        # 'QRSRP_DRX',
        self.speedtest_data['QRSRP_DRX'] = drx
        # 'QRSRP_RX2',
        self.speedtest_data['QRSRP_RX2'] = rx2
        # 'QRSRP_RX3',
        self.speedtest_data['QRSRP_RX3'] = rx3
        # 'RSRP',
        self.speedtest_data['RSRP'] = '' if self.get_qeng_info('RSRP') is False else self.get_qeng_info('RSRP')['RSRP']
        # 'SINR',
        self.speedtest_data['SINR'] = '' if self.get_qeng_info('SINR') is False else self.get_qeng_info('SINR')['SINR']
        # 'RSRQ',
        self.speedtest_data['RSRQ'] = '' if self.get_qeng_info('RSRQ') is False else self.get_qeng_info('RSRQ')['RSRQ']
        # test_time
        all_logger.info('开始进行测速ing')
        self.speedtest_data['test_time'] = time.asctime(time.localtime(time.time()))
        dl_now, ul_now, ping_now, jetter_now = self.speedtest_qss()
        # 'DL(Mbps)',
        self.speedtest_data['DL(Mbps)'] = dl_now
        # 'UL(Mbps)',
        self.speedtest_data['UL(Mbps)'] = ul_now
        # 'Ping(ms)',
        self.speedtest_data['Ping(ms)'] = ping_now
        # 'Jitter(ms)',
        self.speedtest_data['Jitter(ms)'] = jetter_now

    def get_speed_test_data_all(self, dial='QMI', network='NSA', interface='USB', ):
        """
        测速报告中各种信息
        """
        # 'Dial',
        self.speedtest_data['Dial'] = dial
        # 'Network',
        self.speedtest_data['Network'] = network
        # 'Band',
        self.speedtest_data['Band'] = self.enb_file_name_now.split('.')[0]
        # 'PCI',
        """
        AT+QENG="servingcell"
        +QENG: "servingcell","NOCONN"
        +QENG: "LTE","FDD",460,01,5F1EA15,12,1650,3,5,5,DE10,-99,-12,-67,11,9,230,-
        +QENG:"NR5G-NSA",460,01,747,-71,33,-11,627264,78,12,1
        """
        self.speedtest_data['PCI'] = '' if self.get_qeng_info('PCID') is False else self.get_qeng_info('PCID')['PCID']
        if network == "NSA" or network == "LTE":
            # 'LTE_Frequency',
            self.speedtest_data['LTE_Frequency'] = '' if self.get_qeng_info('earfcn') is False else \
                self.get_qeng_info('earfcn')['earfcn']
        else:
            self.speedtest_data['LTE_Frequency'] = ''
        if network == "NSA" or network == "SA":
            # '5G_Frequency',
            self.speedtest_data['5G_Frequency'] = '' if self.get_qeng_info('ARFCN') is False else \
                self.get_qeng_info('ARFCN')['ARFCN']
        else:
            self.speedtest_data['5G_Frequency'] = ''
        # 'Interface',
        self.speedtest_data['Interface'] = interface
        # 'OS',
        self.speedtest_data['OS'] = 'LINUX'
        # 'Driver_Version',
        self.speedtest_data['Driver_Version'] = self.get_driver_version(dial)
        # 'Version',
        self.speedtest_data['Version'] = self.name_sub_version
        # 'ICCID',
        self.speedtest_data['ICCID'] = '\'' + self.get_ccid()
        # 'IMSI',
        self.speedtest_data['IMSI'] = '\'' + self.get_cimi()
        # 'IMEI',
        self.speedtest_data['IMEI'] = '\'' + self.get_imei()

    def get_qrsrp(self):
        qrsrp_value = self.at_handle.send_at("AT+QRSRP")
        all_logger.info(qrsrp_value)
        prx = ''
        drx = ''
        rx2 = ''
        rx3 = ''
        try:
            rx = re.findall(r'\+QRSRP:\s(.?\d+),(.?\d+),(.?\d+),(.?\d+),\w+', qrsrp_value)
            prx, drx, rx2, rx3 = rx[0][0], rx[0][1], rx[0][2], rx[0][3]
        except Exception as e:
            all_logger(e)
        finally:
            return prx, drx, rx2, rx3

    def get_imei(self):
        rerurn_imei = self.at_handle.send_at("AT+EGMR=0,7", 3)
        imei_value = ''.join(re.findall(r'EGMR:\s"(.*)"', rerurn_imei))
        if imei_value != '':
            all_logger.info(f"当前模块imei为 : {imei_value}")
            return imei_value
        else:
            all_logger.info("获取模块imei失败！")
            return False

    def get_ccid(self):
        rerurn_ccid = self.at_handle.send_at("AT+CCID", 3)
        ccid_value = ''.join(re.findall(r'CCID:\s(.*)\r', rerurn_ccid))
        if ccid_value != '':
            all_logger.info(f"当前CCID为 : {ccid_value}")
            return ccid_value
        else:
            all_logger.info("获取CCID失败！")
            return False

    @staticmethod
    def get_driver_version(dial):
        driver_version = ''
        if dial == 'QMI':
            modinfo_value = subprocess.getoutput('modinfo qmi_wwan_q')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\sversion:\s+(.*)', modinfo_value))
        elif dial == 'GobiNet':
            modinfo_value = subprocess.getoutput('modinfo GobiNet')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\sversion:\s+(.*)', modinfo_value))
        elif "PCIE" in dial:
            modinfo_value = subprocess.getoutput('dmesg | grep mhi')
            all_logger.info(modinfo_value)
            driver_version = ''.join(re.findall(r'\smhi_init\s(Quectel.*)', modinfo_value))

        return driver_version

    def bound_network(self, network_type):
        """
        固定指定网络
        :param network_type: 取值：SA/NSA/LTE/WCDMA
        """
        # 固定网络
        network_type = network_type.upper()  # 转换为大写

        all_logger.info("固定网络到{}".format(network_type))
        if network_type in ["LTE", "WCDMA"]:  # 固定LTE或者WCDMA
            self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref",{}'.format(network_type))
        elif network_type == 'SA':  # 固定SA网络
            self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref",NR5G')
        elif network_type == "NSA":  # 使用nr5g_disable_mode进行SA和NSA偏号设置
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO')
            at_data = self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",1')
        else:
            all_logger.info("不支持的网络类型设置")
            self.test_fail.append("不支持的网络类型设置")
            return False

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            all_logger.error('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')
            return False

    def get_qeng_info(self, *search_info):
        """
        获取qeng中的关键信息(所查询参数需要严格和照下面<>中的的同名)

        In SA mode:
        +QENG: "servingcell",<state>,"NR5G-SA",<duplex_mode>,<MCC>,<MNC>,<cellID>,<PCID>,<TAC>,<ARFCN>,<band>,<NR_DL_bandwidth>,<RSRP>,<RSRQ>,<SINR>,<scs>,<srxlev>

        In EN-DC mode:
        +QENG: "servingcell",<state>
        +QENG: "LTE",<is_tdd>,<lte_MCC>,<lte_MNC>,<cellID>,<lte_PCID>,<earfcn>,<freq_band_ind>,<UL_bandwidth>,<lte_DL_bandwidth>,<TAC>,<RSRP>,<lte_RSRQ>,<RSSI>,<SINR>,<CQI>,<tx_power>,<srxlev>
        +QENG: "NR5G-NSA",<MCC>,<MNC>,<PCID>,<RSRP>,<SINR>,<RSRQ>,<ARFCN>,<band>,<NR_DL_bandwidth>,<scs>

        +QENG: "servingcell","NOCONN"
        +QENG: "LTE","FDD",460,00,1A2D001,1,1300,3,5,5,1,-55,-6,-29,19,0,-,84
        +QENG: "NR5G-NSA",460,00,65535,-32768,-32768,-32768

        OK

        AT+QENG="servingcell"
        +QENG: "servingcell","NOCONN"
        +QENG: "LTE","FDD",460,01,5F1EA15,12,1650,3,5,5,DE10,-99,-12,-67,11,9,230,-
        +QENG:"NR5G-NSA",460,01,747,-71,33,-11,627264,78,12,1

        In LTE mode:
        +QENG: "servingcell",<state>,"LTE",<is_tdd>,<MCC>,<MNC>,<cellID>,<PCID>,<earfcn>,<freq_band_ind>,<UL_bandwidth>,<DL_bandwidth>,<TAC>,<RSRP>,<RSRQ>,<RSSI>,<SINR>,<CQI>,<tx_power>,<srxlev>

        In WCDMA mode:
        +QENG: "servingcell",<state>,"WCDMA",<MCC>,<MNC>,<LAC>,<cellID>,<uarfcn>,<PSC>,<RAC>,<RSCP>,<ecio>,<phych>,<SF>,<slot>,<speech_code>,<comMod>

        """
        qeng_info = {}
        search_result = {}
        qeng_values = []
        keys = ''
        all_logger.info(f'开始查询{search_info}')
        return_qeng = self.at_handle.send_at('AT+QENG="servingcell"', 3)
        all_logger.info(return_qeng)
        if 'SEARCH' in return_qeng:
            state = 'SEARCH'
            all_logger.info(f"{state} : UE正在搜索，但（还）找不到合适的 3G/4G/5G 小区")
            return False
        elif 'LIMSRV' in return_qeng:
            state = 'LIMSRV'
            all_logger.info(f"{state} : UE正在驻留小区，但尚未在网络上注册")
            return False
        elif 'NOCONN' in return_qeng:
            state = 'NOCONN'
            all_logger.info(f"{state} : UE驻留在小区并已在网络上注册，处于空闲模式")
        elif 'CONNECT' in return_qeng:
            state = 'CONNECT'
            all_logger.info(f"{state} : UE正在驻留小区并已在网络上注册，并且正在进行呼叫")
        else:
            all_logger.info("未知状态!")

        if 'NR5G-SA' in return_qeng:
            network_mode = 'SA'
        elif 'NR5G-NSA' in return_qeng:
            network_mode = 'NSA'
        elif 'LTE' in return_qeng and 'NR5G-NSA' not in return_qeng:
            network_mode = 'LTE'
        elif 'WCDMA' in return_qeng:
            network_mode = 'WCDMA'
        else:
            all_logger.info(f"注网失败 : {return_qeng}")
            return False
        all_logger.info(f"当前注网模式为：{network_mode}")

        if network_mode == 'SA':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*","(.*)",\s?(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',
                return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values[0]}')
                return False
            keys = ['state', 'duplex_mode', 'MCC', 'MNC', 'cellID', 'PCID', 'TAC', 'ARFCN', 'band', 'NR_DL_bandwidth',
                    'RSRP', 'RSRQ', 'SINR', 'scs', 'srxlev']

        elif network_mode == 'NSA':
            qeng_state = re.findall(r'\+QENG: "servingcell","(.*)"', return_qeng)
            if '-32768,-32768,-32768' in return_qeng:
                all_logger.info(f"注网NSA异常：{return_qeng}")
                return False
            qeng_values_lte = re.findall(
                r'\+QENG:\s"LTE","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',
                return_qeng)
            qeng_values_nr5g = re.findall(r'\+QENG:\s"NR5G-NSA",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',
                                          return_qeng)
            qeng_values_all = tuple(qeng_state) + qeng_values_lte[0] + qeng_values_nr5g[0]
            # all_logger.info(qeng_values_all)
            if len(qeng_values_all) != 28:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values_all}')
                return False
            key_state = ['state']
            keys_lte = ['is_tdd', 'lte_MCC', 'lte_MNC', 'cellID', 'lte_PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth',
                        'lte_DL_bandwidth', 'TAC', 'lte_RSRP', 'lte_RSRQ', 'RSSI', 'lte_SINR', 'CQI', 'tx_power',
                        'srxlev']
            keys_nr5g = ['MCC', 'MNC', 'PCID', 'RSRP', 'SINR', 'RSRQ', 'ARFCN', 'band', 'NR_DL_bandwidth', 'scs']
            keys = key_state + keys_lte + keys_nr5g
            # all_logger.info(keys)
            qeng_values.append(qeng_values_all)

        elif network_mode == 'LTE':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',
                return_qeng)
            if len(qeng_values[0]) != 18:
                all_logger.error(f'AT+QENG="servingcell"返回值异常！:{qeng_values[0]}')
                return False
            keys = ['state', 'is_tdd', 'MCC', 'MNC', 'cellID', 'PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth',
                    'DL_bandwidth', 'TAC', 'RSRP', 'RSRQ', 'RSSI', 'SINR', 'CQI', 'tx_power', 'srxlev']

        elif network_mode == 'WCDMA':
            qeng_values = re.findall(
                r'\+QENG:\s"servingcell","(.*)",".*",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)',
                return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            keys = ['state', 'MCC', 'MNC', 'LAC', 'cellID', 'uarfcn', 'PSC', 'RAC', 'RSCP', 'ecio', 'phych', 'SF',
                    'slot', 'speech_code', 'comMod']

        for i in range(len(qeng_values[0])):
            qeng_info[keys[i]] = qeng_values[0][i]
        # all_logger.info(qeng_info)

        for j in range(len(search_info)):
            if search_info[j] not in qeng_info.keys():
                all_logger.info(f"所查找的内容不存在:{search_info[j]}")
                return False
            else:
                search_result[search_info[j]] = qeng_info[search_info[j]]
        all_logger.info(search_result)
        return search_result

    @staticmethod
    def load_qmi_wwan_q_drive():
        """
        加载qmi驱动
        :return:
        """
        all_logger.info('开始卸载所有网卡驱动')
        network_types = ['qmi_wwan', 'qmi_wwan_q', 'cdc_ether', 'cdc_mbim', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

        time.sleep(5)
        all_logger.info('开始加载qmi_wwan_q网卡驱动')
        subprocess.run("modprobe -a qmi_wwan_q", shell=True)

    def check_wwan_driver(self, is_disappear=False):
        """
        检测wwan驱动是否加载成功
        :param is_disappear: False：检测WWAN驱动正常加载；True：检测WWAN驱动正常消失
        :return: True
        """
        check_cmd = subprocess.Popen('lsusb -t', stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, shell=True)
        check_time = time.time()
        all_logger.info("lsusb -t查询返回:\n")
        while True:
            time.sleep(0.001)
            check_cmd_val = check_cmd.stdout.readline().decode('utf-8', 'ignore')
            if check_cmd_val != '':
                all_logger.info(check_cmd_val)
            if 'qmi_wwan' in check_cmd_val and not is_disappear:
                all_logger.info('wwan驱动检测成功')
                check_cmd.terminate()
                return True
            if is_disappear and 'qmi_wwan' not in check_cmd_val:
                all_logger.info('wwan驱动消失')
                check_cmd.terminate()
                return True
            if time.time() - check_time > 2:
                all_logger.info('未检测到wwan驱动')
                check_cmd.terminate()
                all_logger.info('qmi_wwan_driver_check')
                self.test_fail.append('qmi_wwan_driver_check')
                return False

    def check_route(self):
        """
        检测模块拨号成功后路由配置
        """
        time.sleep(2)
        all_logger.info('***check route***')
        return_value = subprocess.getoutput('route -n')
        all_logger.info(f'{return_value}')
        if self.qmi_usb_network_card_name in return_value:
            all_logger.info('路由配置成功')

    def ping_get_connect_status(self, ipv6_flag=False, network_card_name="wwan0", times=20, flag=True):
        ip = self.get_ip_address(network_card_name, ipv6_flag)
        all_logger.info(f"DNS: {subprocess.getoutput('cat /etc/resolv.conf')}")
        if not flag:
            ping('www.baidu.com', count=times, interval=1, source=ip)
            time.sleep(1)
        else:
            if not ipv6_flag:
                target_ip_list = ['www.baidu.com', '192.168.2.1', '192.168.2.2', 'www.qq.com', 'www.sina.com',
                                  '8.8.8.8']
                for i in range(4):
                    try:
                        ping_data = ping(target_ip_list[i], count=times, interval=1, source=ip)
                        all_logger.info(
                            f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                        if ping_data.is_alive:
                            all_logger.info('ping检查正常')
                            return ping_data.packet_loss
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info(f'ping地址{target_ip_list[i]}失败')
                        continue
                else:
                    try:
                        all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                        ip = self.get_ip_address(network_card_name, ipv6_flag)
                        ping_datas = multiping(['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8'], count=times,
                                               interval=1, source=ip)
                        for ping_data in ping_datas:
                            all_logger.info(
                                f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                            if ping_data.is_alive:
                                all_logger.info('重新获取IP后ping检查正常')
                                return ping_data.packet_loss
                    except Exception as e:
                        all_logger.info(e)
                        all_logger.info('ping检查异常，发送request请求检查网络是否正常')
                        s = requests.Session()
                        new_source = source.SourceAddressAdapter(ip)  # 指定网卡信息
                        s.mount('http://', new_source)
                        s.mount('https://', new_source)
                        s.trust_env = False  # 禁用系统的环境变量，在系统设置有代理的时候可用用此选项禁止请求使用代理
                        response = s.get(url='http://www.baidu.com')
                        response_1 = s.get(url='http://www.sina.com')
                        if response.status_code == 200 or response_1.status_code == 200:
                            all_logger.info('拨号后request请求正常')
                            return 100
                        else:
                            all_logger.info('拨号后request请求失败')
                            return False
            elif ipv6_flag:
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times,
                                       interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(
                        f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return ping_data.packet_loss
                else:
                    all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                    ip = self.get_ip_address(network_card_name, ipv6_flag)
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times,
                                       interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(
                        f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return ping_data.packet_loss
                    else:
                        all_logger.info('ping ipv6检查异常')
                        return False

    @staticmethod
    def get_ip_address(network_card_name, ipv6_flag, false_mode=False):
        """
        获取IP地址
        """
        try_times = 1 if false_mode else 30  # 方便快速获取fail结果
        for i in range(try_times):
            all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
            all_logger.info(
                "ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name,
                                                                                            'inet6' if ipv6_flag else 'inet'))
            ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name,
                                                                                                      'inet6' if ipv6_flag else 'inet')).read()
            if ip and 'error' not in ip:
                all_logger.info('IP: {}'.format(ip))
                return ip
            if false_mode:  # 提高精准度
                time.sleep(0.001)
            else:
                time.sleep(1)
        else:
            all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            all_logger.info(os.popen('ifconfig').read())
            return False

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

    def qmi_start_init(self):  # Linux Mbim拨号前的初始化检查与设置
        time.sleep(60)  # 防止发AT口还未加载、发AT不生效等问题发生（AT配置已USB方式开机很慢）
        self.check_and_set_pcie_data_interface('usb')
        check_qmi = self.check_linux_qmi_and_driver_name()
        if not check_qmi:
            self.enter_qmi_mode()

    def check_and_set_to_usb(self):
        """
        设置回USB模式
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        elif '"data_interface",0,0' not in data_interface_value:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.vbat()
            self.at_handle.check_urc()
            time.sleep(5)

    def check_and_set_pcie_data_interface(self, mode):
        """
        检测模块data_interface信息
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info(f'{data_interface_value}')
        if mode == 'usb' and '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        elif mode == 'usb' and '"data_interface",0,0' not in data_interface_value:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.vbat()
            self.at_handle.check_urc()
            time.sleep(5)
        elif mode == 'pcie' and '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        elif mode == 'pcie' and '"data_interface",1' not in data_interface_value:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",1,0并重启模块'.
                            format(data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",1,0', 0.3)
            self.vbat()
            time.sleep(5)

    def vbat(self):
        # VBAT断电
        self.gpio.set_vbat_high_level()
        # 检测驱动消失
        self.driver_check.check_usb_driver_dis()
        # VBAT开机
        time.sleep(1)
        self.gpio.set_vbat_low_level_and_pwk()
        # 检测驱动加载
        self.driver_check.check_usb_driver()

    def enter_qmi_mode(self):
        self.set_linux_qmi_and_remove_driver()
        self.load_wwan_driver()
        self.vbat()
        self.at_handle.check_urc()
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_linux_qmi_and_driver_name()

    def set_linux_qmi_and_remove_driver(self):
        """
        设置MBIM拨号方式并且删除所有的网卡
        :return: None
        """
        time.sleep(5)  # 防止刚开机AT不生效
        all_logger.info("设置USBNET为0")
        self.at_handle.send_at('AT+QCFG="USBNET",0')

        network_types = ['qmi_wwan', 'qmi_wwan_q', 'GobiNet']
        for name in network_types:
            all_logger.info(f"删除{name}网卡")
            subprocess.run(f"modprobe -r {name}", shell=True)

    def load_wwan_driver(self):
        """
        编译WWAN驱动
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.wwan_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.wwan_path]), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'install', '--directory', self.wwan_path]), shell=True,
                           capture_output=True, text=True)
        all_logger.info(s.stdout)

    def check_linux_qmi_and_driver_name(self, test_mode="USB"):
        """
        检查是否是MBIM拨号方式，检查mbim驱动是否加载，检查WWAN驱动名称
        :return: None
        """
        if test_mode == 'USB':  # 兼容pcie
            all_logger.info("检查USBNET为0")
            for i in range(0, 5):
                time.sleep(5)
                usbnet = self.at_handle.send_at('AT+QCFG="USBNET"')
                if ',0' in usbnet:
                    all_logger.info('当前设置usbnet模式为0')
                    break
                else:
                    if i == 4:
                        all_logger.info(f'设置usbnet失败,当前查询返回为{usbnet}')
                        all_logger.info('usbnet_set')
                        self.test_fail.append('usbnet_set')
                        return False
                    all_logger.info(f'当前查询指令返回{usbnet},等待5秒后再次查询')
                    continue

            all_logger.info("检查qmi_wwan_q驱动加载")
            timeout = 30
            for _ in range(timeout):
                s = subprocess.run('lsusb -t', shell=True, capture_output=True, text=True)
                all_logger.info(s)
                if 'qmi_wwan_q' in s.stdout:
                    break
                time.sleep(1)
            else:
                all_logger.info(f"qmi驱动开机后{timeout}S未加载成功")
                all_logger.info('qmi_wwan_q_check')
                self.test_fail.append('qmi_wwan_q_check')
                return False
        all_logger.info("检查网卡名称")
        network_card_name_now = self.qmi_usb_network_card_name if test_mode == 'USB' else self.qmi_usb_network_card_name
        s = subprocess.run("ip a | grep -o {}".format(network_card_name_now), shell=True, capture_output=True,
                           text=True)
        all_logger.info(s)
        if network_card_name_now not in s.stdout:
            all_logger.info(f'qmi驱动名称异常->"{s.stdout}"')
            all_logger.info('qmi_driver_name')
            self.test_fail.append('qmi_driver_name')
            return False
        return True

    def qmi_quectel_cm(self, network_card_name, dial, test_mode):
        self.at_handle.cfun0()
        time.sleep(3)
        self.at_handle.cfun1()  # 避免长时间不做业务，NSA掉落到LTE使得数据不准确
        time.sleep(3)
        self.at_handle.check_network()
        network = self.get_network()
        qcm = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(
                'ifconfig {} down'.format(self.local_network_card_name))  # 禁用本地网卡
            all_logger.info('ifconfig {} down\r\n{}'.format(self.local_network_card_name, ifconfig_down_value))
            time.sleep(20)
            # set quectel-CM
            qcm = QuectelCMThread(cmd='quectel-CM')
            qcm.setDaemon(True)
            # 检查网络
            self.at_handle.check_network()
            # Linux quectel-CM拨号
            dial_connect_start_timestamp = time.time()
            qcm.start()
            # 检查mbim网卡是否获取到IP
            while time.time() - dial_connect_start_timestamp <= 120:
                connect_result = self.get_ip_address(network_card_name="{}".format(network_card_name), ipv6_flag=False)
                if connect_result:
                    all_logger.info("Qmi quectel-CM拨号成功！")
                    break
            else:
                ifconfig_value = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(ifconfig_value))
                all_logger.info("120s内Qmi quectel-CM拨号失败！")
                all_logger.info(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                self.test_fail.append(f'quectel-CM拨号失败:{self.enb_file_name_now}')
                return False
            time.sleep(30)  # 等待拨号稳定
            # 检查拨号
            all_logger.info('start check driver')
            # 检查mbim驱动和网卡
            if test_mode == "USB":
                self.check_linux_qmi_and_driver_name()
            else:
                self.check_linux_qmi_and_driver_name('pcie')
            # ping测试
            for j in range(10):
                result = self.ping_get_connect_status(network_card_name=network_card_name)
                if not result and str(result) != '0.0':
                    self.udhcpc_get_ip(self.qmi_usb_network_card_name)
                    # ping失败的话，失败次数+1
                    all_logger.info('ping失败，丢包率为：{}'.format(result))
                else:
                    # 记录丢包率
                    all_logger.info('丢包率为：{}'.format(result))
                    break
            else:
                all_logger.info("尝试10次重新获取IP并ping失败！")
                all_logger.info(f'ping失败:{self.enb_file_name_now}')
                self.test_fail.append(f'ping失败:{self.enb_file_name_now}')
                return False
            self.speedtest_dial(dial=dial, network=network, interface=test_mode)
            time.sleep(30)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            qcm.ctrl_c()
            qcm.terminate()
            # 恢复默认网卡
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.local_network_card_name} up')
            all_logger.info(f'ifconfig {self.local_network_card_name} up\r\n{ifconfig_up_value}')
            self.udhcpc_get_ip(self.local_network_card_name)
            self.check_intranet(self.local_network_card_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def check_intranet(self, local_network_card_name, intranet_address='stgit.quectel.com'):
        all_logger.info('开始检查内网连接')
        intranet_flag = True
        i = 0
        while i < 10:
            time.sleep(3)
            i = i + 1
            return_value = subprocess.getoutput('ping {} -c 10'.format(intranet_address))
            all_logger.info("{}".format(return_value))
            if '100% packet loss' in return_value or 'unknown' in return_value or 'unreachable' in return_value or 'failure' in return_value:
                all_logger.info("连接{}失败".format(intranet_address))
                # 查询当前DNS配置
                return_value_resolv = subprocess.getoutput('cat /etc/resolv.conf')
                all_logger.info('cat /etc/resolv.conf\r\n{}'.format(return_value_resolv))
                # 查询各个网络ip状态
                return_value1 = subprocess.getoutput('ifconfig')
                all_logger.info('ifconfig\r\n{}'.format(return_value1))
                # 开始尝试恢复内网
                all_logger.info('the intranet connect FAIL!')
                all_logger.info('Trying to connect...')
                # killall quectel-CM
                return_value2 = subprocess.getoutput('killall quectel-CM')
                all_logger.info('killall quectel-CM\r\n{}'.format(return_value2))
                # 重新禁用启用本地网
                return_value3 = subprocess.getoutput('ifconfig {} down'.format(local_network_card_name))
                all_logger.info('ifconfig {} down\r\n{}'.format(local_network_card_name, return_value3))
                return_value4 = subprocess.getoutput('ifconfig {} up'.format(local_network_card_name))
                all_logger.info('ifconfig {} up\r\n{}'.format(local_network_card_name, return_value4))
                time.sleep(3)
                # 重新配置DNS、获取ip
                return_value5 = subprocess.getoutput('udhcpc -i {}'.format(local_network_card_name))
                all_logger.info('udhcpc -i {}\r\n{}'.format(local_network_card_name, return_value5))
                intranet_flag = False
            else:
                all_logger.info('the intranet connect successfully!')
                intranet_flag = True
                break
        if not intranet_flag:
            all_logger.info('尝试10次连接内网失败，请检查设备连接和配置情况是否正确!')
            self.test_fail.append('尝试10次连接内网失败，请检查设备连接和配置情况是否正确!')
            return False

    def check_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",1' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询值不一致,查询信息为{}'.format(data_interface_value))
            all_logger.info("PCIE")
            self.test_fail.append("PCIE")
            return False

    def set_qsclk(self, mode=1):
        """
        :param mode:0: 设置开启不保存；1: 设置开启保存
        :return:
        """
        for i in range(3):
            self.at_handle.send_at('AT+QSCLK=1,{}'.format(1 if mode == 1 else 0))
            qsc_val = self.at_handle.send_at('AT+QSCLK?')
            if '+QSCLK: 1,{}'.format(1 if mode == 1 else 0) in qsc_val:
                return True
            time.sleep(1)
        else:
            raise QSSWeakSignalError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

    @staticmethod
    def linux_enter_low_power(level_value=True, wakeup=True):
        """
        Linux需要休眠首先dmesg查询USB节点，然后设置节点的autosuspend值为1，level值为auto，wakeup值为enabled
        :return: None
        """
        dmesg_data = os.popen('dmesg').read()
        dmesg_data_regex = re.findall(r'usb\s(\d+-\d+):.*Quectel.*', dmesg_data)
        if dmesg_data_regex:
            node_list = list(set(dmesg_data_regex))
            for node in node_list:
                node_path = os.path.join('/sys/bus/usb/devices/', node, 'power')
                autosuspend = 'cd {} && echo 1 > {}'.format(node_path, 'autosuspend')
                level = 'cd {} && echo {} > {}'.format(node_path, 'auto' if level_value else 'on', 'level')
                wakeup = 'cd {} && echo {} > {}'.format(node_path, 'enabled' if wakeup else 'disabled', 'wakeup')
                commands = [autosuspend, level, wakeup]
                for command in commands:
                    try:
                        all_logger.info(command)
                        s = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                        out, error = s.communicate()
                        all_logger.info([out, error])
                    except Exception as e:
                        all_logger.info(e)
        if level_value:
            all_logger.info('已更改autosuspend 、level、wakeup值为进入慢时钟')
        else:
            all_logger.info('已更改autosuspend 、level、wakeup值为退出慢时钟')

    def debug_check(self, is_low_power, times=12, is_at=False, sleep=True):
        """
        每隔5S循环检测debug口是否通指令，期望进入慢时钟后debug口输入无返回值，默认超时时间为60S
        :param is_low_power: 是否进入慢时钟,True:进入；False:未进入
        :param times: 检测次数
        :param is_at: 是否需要发送AT后再检测debug口情况
        :param sleep: 是否需要等待
        :return:
        """
        for i in range(times):
            if sleep:
                time.sleep(5)
            if is_at:
                self.at_handle.send_at('AT')
            with serial.Serial(self.debug_port, baudrate=115200, timeout=0) as _debug_port:
                _debug_port.flushOutput()
                _debug_port.write('\r\n'.encode('utf-8'))
                start_time = time.time()
                value = ''
                while True:
                    value += _debug_port.readline().decode('utf-8', 'ignore')
                    if time.time() - start_time > 1:
                        break
                if is_low_power:    # 期望模块已进入慢时钟检测Debug口
                    if value:   # 如果有返回值代表还未进入慢时钟，等待五秒后在检查
                        all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通,等待5S后再次检测')
                        all_logger.info(value)
                        continue
                    else:
                        all_logger.info('检测debug口无返回值，正常')
                        return True
                else:   # 期望模块未进入慢时钟检测Debug口
                    if value:
                        all_logger.info(value.replace('\r\n', ''.strip()))
                        all_logger.info('检测debug口有返回值，正常')
                        return True
                    else:       # 如果无返回值代表模块仍未退出慢时钟，等待5S后再检查
                        all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出,等待5S后再次检测')
                        continue
        else:
            if is_low_power:  # 期望模块已进入慢时钟检测Debug口
                all_logger.info(value.replace('\r\n', ''.strip()))
                all_logger.info('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
                raise QSSWeakSignalError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise QSSWeakSignalError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def close_lowpower(self):
        """
        发送指令退出慢时钟
        :return: True
        """
        for i in range(3):
            val = self.at_handle.send_at('AT+QSCLK=0,0')
            if 'OK' in val:
                return True
        else:
            raise QSSWeakSignalError('退出慢时钟失败')


class MySQL:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def fetchone(self, sql):
        # 进行查询,返回一条结果
        connection = pymysql.connect(host=self.host,
                                     user=self.user,
                                     password=self.password,
                                     database=self.database,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                return result

    def fetchall(self, sql):
        # 进行查询,返回所有结果
        connection = pymysql.connect(host=self.host,
                                     user=self.user,
                                     password=self.password,
                                     database=self.database,
                                     cursorclass=pymysql.cursors.DictCursor
                                     )
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                return result
