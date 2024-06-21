import random
import threading
from collections import deque
from threading import Thread

import requests
import serial
from icmplib import ping, multiping # noqa
from requests_toolbelt.adapters import source

from utils.functions.getpassword import getpass
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from utils.operate.reboot_pc import Reboot
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import QMIError
from utils.functions.linux_api import LinuxAPI
import subprocess
import time
import os
import re
from tools.qss.qss_client import ConnectQSS, WriteSimcard


class LinuxQSSFunctionsManager:
    def __init__(self, at_port, dm_port, debug_port, wwan_path, network_card_name, extra_ethernet_name, params_path, qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name, cat_dl, cat_ul, rgmii_ethernet_name, rtl8125_ethernet_name, eth_test_mode, pc_ethernet_name):
        self.linux_api = LinuxAPI()
        self.driver_check = DriverChecker(at_port, dm_port)
        self.at_port = at_port
        self.dm_port = dm_port
        self.at_handle = ATHandle(at_port)
        self.wwan_path = wwan_path
        self.extra_ethernet_name = extra_ethernet_name
        self.network_card_name = network_card_name
        self.reboot = Reboot(at_port, dm_port, params_path)
        self.qss_ip = qss_ip
        self.local_ip = local_ip
        self.node_name = node_name
        self.mme_file_name = mme_file_name
        self.enb_file_name = enb_file_name
        self.ims_file_name = ims_file_name
        self.write_simcard = WriteSimcard(self.at_port)
        self.cat_dl = cat_dl
        self.cat_ul = cat_ul
        self.gpio = GPIO()
        self.debug_port = debug_port
        self.eth_test_mode = eth_test_mode
        self.rgmii_ethernet_name = rgmii_ethernet_name
        self.rtl8125_ethernet_name = rtl8125_ethernet_name
        self.pc_ethernet_name = pc_ethernet_name
        self.return_qgmr = self.at_handle.send_at('AT+QGMR', 0.6)
        self.eth_test_mode_list = {'2': 'RGMII8035|8211', '3': 'RTL8125', '4': 'RTL8168', '5': 'QCA8081'}
        self.default_apns = None

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

    def open_qss_ct(self):
        # 将卡写成电信卡
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('46003'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('46003', '898603')

        # QSS开网
        task = [self.mme_file_name, self.enb_file_name]
        qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QMIError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(20)

        # 注网及检查注网B3N78
        self.at_handle.cfun0()
        time.sleep(5)
        self.at_handle.cfun1()
        time.sleep(3)
        self.at_handle.check_network()
        rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
        all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
        all_logger.info(f"nr band : {rerutn_bands['band']}")
        if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
            raise QMIError("注网异常(B3n78)!")
        time.sleep(5)
        return start_time, qss_connection

    def open_qss_cmcc(self):
        # 将卡写成移动
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('46000'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('46000', '898600')

        # QSS开网
        task = [self.mme_file_name, self.enb_file_name]
        qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QMIError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(20)

        # 注网及检查注网移动B3n41
        self.at_handle.cfun0()
        time.sleep(5)
        self.at_handle.cfun1()
        time.sleep(3)
        self.at_handle.check_network()
        rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
        all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
        all_logger.info(f"nr band : {rerutn_bands['band']}")
        if '3' != rerutn_bands['freq_band_ind'] or '41' != rerutn_bands['band']:
            raise QMIError("注网异常(B3n41)!")
        time.sleep(5)
        return start_time, qss_connection

    def open_qss_cu(self):
        # 将卡写成联通卡
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('46001'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('46001', '898601')

        # QSS开网
        task = [self.mme_file_name, self.enb_file_name]
        qss_connection = self.get_qss_connection(tesk_duration=120, task=task)
        start_time = time.time()
        start_result = qss_connection.start_task()
        if not start_result:
            raise QMIError('开启qss异常')
        all_logger.info('等待网络稳定')
        time.sleep(20)

        # 注网及检查注网B3N78
        self.at_handle.cfun0()
        time.sleep(5)
        self.at_handle.cfun1()
        time.sleep(3)
        self.at_handle.check_network()
        rerutn_bands = self.get_qeng_info('freq_band_ind', 'band')
        all_logger.info(f"lte band : {rerutn_bands['freq_band_ind']}")
        all_logger.info(f"nr band : {rerutn_bands['band']}")
        if '3' != rerutn_bands['freq_band_ind'] or '78' != rerutn_bands['band']:
            raise QMIError("注网异常(B3n78)!")
        time.sleep(5)
        return start_time, qss_connection

    def get_qeng_info(self, *search_info):
        """
        获取qeng中的关键信息(所查询参数需要严格和照下面<>中的的同名)

        In SA mode:
        +QENG: "servingcell",<state>,"NR5G-SA",<duplex_mode>,<MCC>,<MNC>,<cellID>,<PCID>,<TAC>,<ARFCN>,<band>,<NR_DL_bandwidth>,<RSRP>,<RSRQ>,<SINR>,<scs>,<srxlev>

        In EN-DC mode:
        +QENG: "servingcell",<state>
        +QENG: "LTE",<is_tdd>,<lte_MCC>,<lte_MNC>,<cellID>,<lte_PCID>,<earfcn>,<freq_band_ind>,<UL_bandwidth>,<lte_DL_bandwidth>,<TAC>,<RSRP>,<lte_RSRQ>,<RSSI>,<SINR>,<CQI>,<tx_power>,<srxlev>
        +QENG: "NR5G-NSA",<MCC>,<MNC>,<PCID>,<RSRP>,<SINR>,<RSRQ>,<ARFCN>,<band>,<NR_DL_bandwidth>,<scs>

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
            return state
        elif 'LIMSRV' in return_qeng:
            state = 'LIMSRV'
            all_logger.info(f"{state} : UE正在驻留小区，但尚未在网络上注册")
            return state
        elif 'NOCONN' in return_qeng:
            state = 'NOCONN'
            all_logger.info(f"{state} : UE驻留在小区并已在网络上注册，处于空闲模式")
        elif 'CONNECT' in return_qeng:
            state = 'LIMSRV'
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
            qeng_values = re.findall(r'\+QENG:\s"servingcell","(.*)",".*","(.*)",\s(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            keys = ['state', 'duplex_mode', 'MCC', 'MNC', 'cellID', 'PCID', 'TAC', 'ARFCN', 'band', 'NR_DL_bandwidth', 'RSRP', 'RSRQ', 'SINR', 'scs', 'srxlev']

        elif network_mode == 'NSA':
            qeng_state = re.findall(r'\+QENG: "servingcell","(.*)"', return_qeng)
            qeng_values_lte = re.findall(r'\+QENG:\s"LTE","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', return_qeng)
            qeng_values_nr5g = re.findall(r'\+QENG:\s"NR5G-NSA",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', return_qeng)
            qeng_values_all = tuple(qeng_state) + qeng_values_lte[0] + qeng_values_nr5g[0]
            # all_logger.info(qeng_values_all)
            if len(qeng_values_all) != 28:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            key_state = ['state']
            keys_lte = ['is_tdd', 'lte_MCC', 'lte_MNC', 'cellID', 'lte_PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth', 'lte_DL_bandwidth', 'TAC', 'RSRP', 'lte_RSRQ', 'RSSI', 'SINR', 'CQI', 'tx_power', 'srxlev']
            keys_nr5g = ['MCC', 'MNC', 'PCID', 'RSRP', 'SINR', 'RSRQ', 'ARFCN', 'band', 'NR_DL_bandwidth', 'scs']
            keys = key_state + keys_lte + keys_nr5g
            # all_logger.info(keys)
            qeng_values.append(qeng_values_all)

        elif network_mode == 'LTE':
            qeng_values = re.findall(r'\+QENG:\s"servingcell","(.*)",".*","(.*)",(.*),(\d+),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', return_qeng)
            if len(qeng_values[0]) != 18:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            keys = ['state', 'is_tdd', 'MCC', 'MNC', 'cellID', 'PCID', 'earfcn', 'freq_band_ind', 'UL_bandwidth', 'DL_bandwidth', 'TAC', 'RSRP', 'RSRQ', 'RSSI', 'SINR', 'CQI', 'tx_power', 'srxlev']

        elif network_mode == 'WCDMA':
            qeng_values = re.findall(r'\+QENG:\s"servingcell","(.*)",".*",(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*),(.*)', return_qeng)
            if len(qeng_values[0]) != 15:
                all_logger.error('AT+QENG="servingcell"返回值异常！')
                return False
            keys = ['state', 'MCC', 'MNC', 'LAC', 'cellID', 'uarfcn', 'PSC', 'RAC', 'RSCP', 'ecio', 'phych', 'SF', 'slot', 'speech_code', 'comMod']

        for i in range(len(qeng_values[0])):
            qeng_info[keys[i]] = qeng_values[0][i]
        # all_logger.info(qeng_info)

        for j in range(len(search_info)):
            if search_info[j] not in qeng_info.keys():
                all_logger.info(f"所查找的内容不存在:{search_info[j]}")
            else:
                search_result[search_info[j]] = qeng_info[search_info[j]]
        all_logger.info(search_result)
        return search_result

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
            raise QMIError('AT+QSCLK=1,{}设置不成功'.format(1 if mode == 1 else 0))

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
            raise QMIError('退出慢时钟失败')

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
                raise QMIError('检测debug口有返回值，期望模块已进入慢时钟，debug口不通')
            else:
                all_logger.info('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')
                raise QMIError('检测debug口无返回值，期望模块未进入慢时钟，debug口正常输出')

    def check_statuslight_longbrightshortdown(self, times=60):
        """
        持续检测10次net_status灯长亮短灭状态
        :param times: 检测次数
        :return:
        """
        level_list = []
        level1_list = []
        level0_list = []
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            level_list.append(level_status)
        for i in level_list:
            if i == 1:
                level1_list.append(i)
                continue
            level0_list.append(i)
        if 1 in level_list and 0 in level_list:
            all_logger.info('net_status灯状态为长亮短灭,状态正常')
        else:
            all_logger.info('当前检测灯亮状态为{}'.format(level1_list))
            all_logger.info('当前检测灯灭状态为{}'.format(level0_list))
            raise QMIError('当前net_status灯状态不对')

    def check_statuslight_blink(self, times=20):
        """
        持续检测10次net_status灯闪烁状态
        :param times: 检测次数
        :return:
        """
        level_list = []
        for i in range(times):
            status_list = self.gpio.get_net_status_gpio_level()
            level_status = status_list['level']
            level_list.append(level_status)
        if 1 in level_list and 0 in level_list:
            all_logger.info('net_status灯状态为不停闪烁,状态正常')
        else:
            all_logger.info('当前高低电平状态为{}'.format(level_list))
            raise QMIError('当前net_status灯状态不对')

    def check_modelight_alwaysbright(self, times=10):
        """
        持续检测10次net_mode灯常亮状态
        :param times: 检测次数
        :return:
        """
        for i in range(times):
            status_list = self.gpio.get_net_mode_gpio_level()
            level_status = status_list['level']
            if 1 == level_status:
                all_logger.info('第{}次检测为高电平,灯为常亮状态'.format(i))

            else:
                raise QMIError('当前第{}次检测值为{},灯不为常亮状态'.format(i, level_status))

    def module_typerg(self):
        time.sleep(10)
        type_value = self.at_handle.send_at('ATI')
        if 'RM' in type_value:
            all_logger.info('当前测试项目为RM项目,不执行此case')
            return True

    def reset_network_to_default(self):
        """
        进行网络类型绑定之后设置回初始值
        :return:
        """
        mode_pref_data = self.at_handle.send_at('AT+QNWPREFCFG= "mode_pref",AUTO')
        nr5g_disable_mode_data = self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')
        if "ERROR" in mode_pref_data:
            raise QMIError('发送AT+QNWPREFCFG="mode_pref",AUTO 返回ERROR')
        if "ERROR" in nr5g_disable_mode_data:
            raise QMIError('发送AT+QNWPREFCFG="nr5g_disable_mode",0 返回ERROR')

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
            raise QMIError("不支持的网络类型设置")

        # 判断AT+QNWPREFCFG="nr5g_disable_mode"指令是否支持
        if 'ERROR' in at_data:
            raise QMIError('AT+QNWPREFCFG="nr5g_disable_mode"指令可能不支持')

    def qss_call(self):
        self.at_handle.send_at('ATD666;', 3)
        time.sleep(3)
        return_call = self.at_handle.send_at('AT+CLCC', 3)
        if 'CLCC: 3,0,0,0,0,"666"' in return_call:
            all_logger.info(f"通话正常:{return_call}")
            return True
        else:
            all_logger.info(f"通话异常:{return_call}")
            return False

    def qss_send_sms(self):
        return_cimi_value = self.at_handle.send_at("AT+CIMI", 3)
        cimi_value = ''.join(re.findall(r'(\d.*).', return_cimi_value))
        self.send_gsm_msg('no_class', cimi_value)

    def send_gsm_msg(self, class_type, phone_number):
        """
        发送GSM格式短信
        :param class_type:短信类型。如 no class，class 0等
        :param phone_number:发送对象手机号
        :return:
        """
        # 已修改UI及短信
        class_dict = {'no_class': '17,71,0,0', 'class_0': '17,0,0,240', 'class_1': '17,167,0,241',
                      'class_2': '17,168,0,242', 'class_3': '17,197,0,243'}
        origin_val = ''
        try:
            value = self.at_handle.send_at('AT+CSMP?', 10)
            origin_val = re.findall(r'\+CSMP: (.*)', value)[0]      # 保存初始值，每次设置完后需要恢复
            self.at_handle.send_at('AT+CMGF=1', 10)
            self.at_handle.send_at(f'AT+CSMP={class_dict[class_type]}', 10)
            content = 'GSM msg test #%#*(()97970 #DGFHffh#1https://www.sina.com.cn/19/06/04,03:01:38+32+86'
            all_logger.info(f'发送短信指令AT+CMGS="{phone_number}"')
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                all_logger.info(f'写入短信:{content}')
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            get_msg_urc = CheckSmsUrc(self.at_port)
            get_msg_urc.setDaemon(True)
            get_msg_urc.start()
            get_msg_urc.join()
            if not get_msg_urc.flag:
                raise QMIError('未检测到来短信上报+CMGS, +CMT等URC')
        finally:
            self.at_handle.send_at('AT+CMGF=0', 10)
            self.at_handle.send_at(f'AT+CSMP={origin_val}', 10)

    def get_qss_connection(self, tesk_duration=300, task_status=0, task=None):
        param_dict = {
            'name_group': 'Functions_QSS',  # 发起任务的用例名称(可以从下发消息中获取)
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

    def enter_qmi_mode(self):
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        time.sleep(2)
        self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",NR5G')
        self.load_qmi_wwan_q_drive()
        all_logger.info('检查qmi_wwan_q驱动加载')
        self.check_wwan_driver()

    @staticmethod
    def modprobe_driver():
        """
        卸载GobiNet驱动
        :return: True
        """
        all_logger.info('开始卸载GobiNet,qmi_wwan网卡驱动')
        network_types = ['qmi_wwan', 'GobiNet']
        for name in network_types:
            all_logger.info("删除{}网卡".format(name))
            subprocess.run("modprobe -r {}".format(name), shell=True)

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

    @staticmethod
    def check_wwan_driver(is_disappear=False):
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
                raise QMIError

    @staticmethod
    def get_ip_address_new(network_card_name, ipv6_flag, false_mode=False):
        """
        获取IP地址
        """
        try_times = 1 if false_mode else 30  # 方便快速获取fail结果
        for i in range(try_times):
            all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
            all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name, 'inet6' if ipv6_flag else 'inet'))
            ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format(network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
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

    def get_ip_address(self, is_success=True, ipv6_flag=False):
        """
        判断是否获取到IPV4地址,目前只应用了is_sucess=False状态下的检测
        :param is_success: True: 拨号正常状态下检测IP地址是否正常获取; False: 断开拨号后检测IP地址是否正常消失
        :param ipv6_flag: True: 检测IPV6地址；False: 检测IPV4地址
        :return: True
        """
        if is_success:
            for i in range(30):
                all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
                all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                                (self.network_card_name, 'inet6' if ipv6_flag else 'inet'))
                ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                              (self.network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
                if ip and 'error' not in ip:
                    all_logger.info(ip)
                    return ip.replace('地址:', '')
                time.sleep(1)
            else:
                all_logger.info("获取IPv6地址失败" if ipv6_flag else "获取IPv4地址失败")
            return False
        else:
            for i in range(3):
                all_logger.info("获取IPv6地址" if ipv6_flag else "获取IPv4地址")
                all_logger.info("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                                (self.network_card_name, 'inet6' if ipv6_flag else 'inet'))
                ip = os.popen("ifconfig {} | grep '{} '| tr -s ' ' | cut -d ' ' -f 3 | head -c -1".format
                              (self.network_card_name, 'inet6' if ipv6_flag else 'inet')).read()
                if ip and 'error' not in ip:
                    all_logger.info(ip)
                    raise QMIError("断开拨号后仍能检测到IP")
                time.sleep(1)
            else:
                all_logger.info("断开拨号后正常获取IPv6地址失败" if ipv6_flag else "断开拨号后正常获取IPv4地址失败")
            return True

    def dump_check(self):
        """
        检测模块是否发生DUMP
        :return: None
        """
        for i in range(10):
            port_list = self.driver_check.get_port_list()
            if self.at_port in port_list and self.dm_port in port_list:
                time.sleep(1)
                continue
            elif self.at_port not in port_list and self.dm_port in port_list:
                raise QMIError('模块DUMP')

    def sim_lock(self):
        """
        SIM卡锁PIN
        :return: True
        """
        self.at_handle.send_at('AT+CLCK="SC",1,"1234"', timeout=5)
        self.at_handle.send_at('AT+CFUN=0', timeout=15)
        time.sleep(3)
        self.at_handle.send_at('AT+CFUN=1', timeout=15)
        return_val = self.at_handle.send_at('AT+CLCK="SC",2', timeout=5)
        if '+CLCK: 1' in return_val:
            return True
        else:
            raise QMIError('SIM卡锁Pin失败')

    def get_netcard_ip(self, is_success=True):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        ifconfig_value = os.popen('ifconfig {}'.format(self.network_card_name)).read()
        try:
            re_ifconfig = re.findall(r'{}.*\n(.*)'.format(self.network_card_name), ifconfig_value)[0].strip()
            ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
        except IndexError:
            pass
        if is_success:
            if ip:
                all_logger.info('获取IP地址正常,IP地址为{}'.format(ip))
                return ip
            else:
                raise QMIError('获取IP地址异常,未获取到IP地址,ifconfig -a返回{}'.format(ifconfig_value))
        else:
            if not ip:
                all_logger.info('IP地址正常,当前未获取到IP地址')
            else:
                raise QMIError('异常,当前未进行拨号,但获取到IP地址{}'.format(ip))

    def check_and_set_pcie_data_interface(self):
        """
        检测模块data_interface信息是否正常,若是usb模式，则设置AT+QCFG="data_interface",0,0并重启模块
        :return: None
        """
        data_interface_value = self.at_handle.send_at('AT+QCFG="data_interface"')
        all_logger.info('{}'.format(data_interface_value))
        if '"data_interface",0,0' in data_interface_value:
            all_logger.info('data_interface信息正常')
        else:
            all_logger.info('data_interface信息查询异常,查询信息为：\r\n{}\r\n开始设置AT+QCFG="data_interface",0,0并重启模块'.format(
                data_interface_value))
            self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.3)
            self.at_handle.cfun1_1()
            self.driver_check.check_usb_driver_dis()
            self.driver_check.check_usb_driver()
            self.at_handle.check_urc()
            time.sleep(5)

    def check_route(self):
        """
        检测模块拨号成功后路由配置
        """
        time.sleep(2)
        all_logger.info('***check route***')
        return_value = subprocess.getoutput('route -n')
        all_logger.info(f'{return_value}')
        if self.network_card_name in return_value:
            all_logger.info('路由配置成功')

    def ping_get_connect_status(self, ipv6_flag=False, network_card_name="wwan0", times=20, flag=True):
        ip = self.get_ip_address_new(network_card_name, ipv6_flag)
        all_logger.info(f"DNS: {subprocess.getoutput('cat /etc/resolv.conf')}")
        if not flag:
            ping('www.baidu.com', count=times, interval=1, source=ip)
            time.sleep(1)
        else:
            if not ipv6_flag:
                target_ip_list = ['192.168.2.1', '192.168.2.2', 'www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8']
                for i in range(4):
                    try:
                        ping_data = ping(target_ip_list[i], count=times, interval=1, source=ip)
                        all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
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
                        ip = self.get_ip_address_new(network_card_name, ipv6_flag)
                        ping_datas = multiping(['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8'], count=times, interval=1, source=ip)
                        for ping_data in ping_datas:
                            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                            if ping_data.is_alive:
                                all_logger.info('重新获取IP后ping检查正常')
                                return ping_data.packet_loss
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
                            return 100
                        else:
                            all_logger.info('拨号后request请求失败')
                            return False
            elif ipv6_flag:
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times, interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return ping_data.packet_loss
                else:
                    all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                    ip = self.get_ip_address_new(network_card_name, ipv6_flag)
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times, interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return ping_data.packet_loss
                    else:
                        all_logger.info('ping ipv6检查异常')
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

    def enter_eth_mode(self, eth_test_mode='0'):
        """
        eth_test_mode:根据具体测试机配备的PHY硬件类型来决定(resource中需要配置)
        0  随机RGMII8035、8211和RTL8125
        1  随机RGMII8035、8211和RTL8168
        2  随机RGMII8035、8211
        3  RTL8125
        4  RTL8168
        """
        eth_test_mode_list1 = {'2': 'RGMII', '3': 'RTL8125'}
        eth_test_mode_list2 = {'2': 'RGMII', '4': 'RTL8168'}
        if eth_test_mode == '0':  # 随机模式
            eth_test_mode = random.choice(list(eth_test_mode_list1.keys()))
            all_logger.info(f"当前为随机测试模式，本条case随机到的测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        if eth_test_mode == '1':  # 随机模式
            eth_test_mode = random.choice(list(eth_test_mode_list2.keys()))
            all_logger.info(f"当前为随机测试模式，本条case随机到的测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        time.sleep(10)
        all_logger.info(f"本条case测试模式为{self.eth_test_mode_list[eth_test_mode]}")
        try:
            if eth_test_mode == '2':
                self.rgmii(status="enable", voltage=1)
                self.enter_eth_check('2')
            elif eth_test_mode == '3':
                self.enter_rtl_mode('8125')
                self.check_rtl_pci('8125')
                self.enter_eth_check('3')
            elif eth_test_mode == '4':
                self.enter_rtl_mode('8168')
                self.check_rtl_pci('8168')
                self.enter_eth_check('4')
            elif eth_test_mode == '5':
                self.enter_qca_mode()
                self.check_rtl_pci('8081')
                self.enter_eth_check('5')
            else:
                raise QMIError("未知测试模式，请确认eth_test_mode参数值是否正确")
        finally:
            return eth_test_mode

    def enter_qca_mode(self):
        return_value = self.at_handle.send_at('AT+QCFG="pcie/mode",3', 0.6)
        if 'OK' not in return_value:
            raise QMIError("QCA8081开启异常")

    def check_rtl_pci(self, mode):
        """
        Debug输入命令lspci检查RTL8125的PCI
        """
        # 启动线程
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()

        try:
            all_logger.info('wait 20 secs.')
            time.sleep(20)

            all_logger.info('check pci')
            data = debug_port.exec_command('lspci')
            all_logger.info('lspci data : {}'.format(data))
            if mode == '8125' and f'10ec:{mode}' not in data:
                raise QMIError(
                    f"RTL{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            elif mode == '8168' and f'10ec:{mode}' not in data:  # todo 待根据实际log完善
                raise QMIError(
                    f"RTL{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            elif mode == '8081' and f'10ec:{mode}' not in data:  # todo 待根据实际log完善
                raise QMIError(
                    f"{mode} not find in return value!!! please check EVB setting or other that can be affected.")
            else:
                all_logger.info(f'already find pci of PHY\r\n{data}"')
        finally:
            all_logger.info('check pci end')
            debug_port.close_debug()

    def udhcpc_get_ip_eth(self, eth_test_mode='2', network_name=''):
        # self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name
        now_network_name = (self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name) if network_name == '' else network_name
        all_logger.info(f"udhcpc -i {now_network_name}")
        process = subprocess.Popen(f'udhcpc -i {now_network_name}',
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

    def rgmii(self, status, voltage, mode='', profile_id='', parallel=(0, 0), check=True):
        """
                RGMII         status       voltage  mode   profile_id
        +QETH: "rgmii",("enable","disable"),(0,1),(-1,0,1),(1-8)
        status : ENABLE, DISABLE
        mode : 0 : COMMON-RGMII ; 1 : IPPassthrough
        voltage : default: 1: 2.5V ; 0, 1.8V
        """
        s_0 = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} up')
        all_logger.info(f"ifconfig {self.rgmii_ethernet_name} up: {s_0}")

        all_logger.info('wait 1 seconds')
        time.sleep(1)
        # set
        rgmii_at = f'AT+QETH="RGMII","{status}",{voltage}'
        if mode != '':
            rgmii_at += ',{}'.format(mode)
        if profile_id:
            rgmii_at += ',{}'.format(profile_id)
        rgmii_dial_result = self.at_handle.send_at(rgmii_at, timeout=30)

        # check
        if check:
            rgmii_check_result = self.at_handle.send_at('AT+QETH="RGMII"', 15)
            line_0 = '+QETH: "RGMII","{}",{},{}'.format(status.upper(), voltage,
                                                        '-1' if status.upper() == 'DISABLE' else mode)
            line_1 = '+QETH: "RGMII",{},{}'.format(0 if mode == '' or status.upper() == 'DISABLE' else 1, 1 if not profile_id else profile_id)
            line_2 = '+QETH: "RGMII",{},{}'.format(2 if parallel[0] else 0, parallel[1] if parallel[1] else 2)
            line_3 = '+QETH: "RGMII",0,3'
            line_4 = '+QETH: "RGMII",0,4'
            all_check_info_list = [line_0, line_1, line_2, line_3, line_4]
            all_logger.info("all_check_info_list: {}".format(all_check_info_list))
            for info in all_check_info_list:
                if info not in rgmii_check_result:
                    all_logger.error('AT+QETH="RGMII" not found {}.'.format(info))
                    raise QMIError('AT+QETH="RGMII" not found {}.'.format(info))

        self.restart_eth_network_card()
        time.sleep(3)
        if status == "enable":
            # 连接网卡、防止网卡不自动连接
            self.udhcpc_get_ip_eth()
        if status == "disable":
            # 关闭网卡
            s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name} down')
            all_logger.info(f"ifconfig {self.rgmii_ethernet_name} down: {s}")
        time.sleep(3)
        return rgmii_dial_result

    def enter_eth_check(self, eth_test_mode):
        """
        PHY模块灯被点亮，PC端本地连接状态为已连接无网络；可以ping通内网IP
        192.168.225.1
        """
        # wait 10 seconds
        all_logger.info("开始ping内网IP")
        time.sleep(10)

        ip = LinuxAPI.get_ip_address(self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name, ipv6_flag=False)
        try:
            ping_data = ping('192.168.225.1', count=20, interval=1, source=ip)
            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
            if ping_data.is_alive:
                all_logger.info('ping检查正常')
                return True
        except Exception as e:
            all_logger.info(e)
            all_logger.info('ping地址192.168.225.1失败')

    def enter_rtl_mode(self, mode='8125'):
        """
        1. 执行AT+QCFG="data_interface",1,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",1 //启用RC模式（重启生效）
        3. 执行AT+QETH="eth_driver","r8125" //选择rtl8125驱动（重启生效）
        AT+QETH="eth_driver"
        +QETH: "eth_driver","r8125",0
        +QETH: "eth_driver","r8168",0

        OK
        """
        all_logger.info(f'enter rtl{mode} mode')
        all_logger.info('开始打开pcie net')
        return_value = self.at_handle.send_at('AT+QCFG="data_interface",1,0', 0.6)
        if 'OK' not in return_value:
            raise QMIError("打开pcie net异常")

        all_logger.info('开始启用RC模式')
        return_value = self.at_handle.send_at('AT+QCFG="pcie/mode",1', 0.6)
        if 'OK' not in return_value:
            raise QMIError("启用RC模式异常")

        all_logger.info(f'选择rtl{mode}驱动')
        return_value = self.at_handle.send_at(f'AT+QETH="eth_driver","r{mode}"', 0.6)
        if 'OK' not in return_value:
            raise QMIError(f"选择rtl{mode}驱动异常")

        # s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} up')
        # all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} up: {s}")

        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()

        s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} up')
        all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} up: {s}")

        self.driver_check.check_usb_driver()
        time.sleep(10)

    def exit_rtl_mode(self):
        """
        1. 执行AT+QCFG="data_interface",0,0 //打开pcie net（重启生效）
        2. 执行AT+QCFG="pcie/mode",0 //启用RC模式（重启生效）
        """
        all_logger.info('exit rtl8125 mode')
        all_logger.info('开始关闭pcie net')
        return_value = self.at_handle.send_at('AT+QCFG="data_interface",0,0', 0.6)
        if 'OK' not in return_value:
            raise QMIError("关闭pcie net异常")

        all_logger.info('开始关闭RC模式')
        return_value = self.at_handle.send_at('AT+QCFG="pcie/mode",0', 0.6)
        if 'OK' not in return_value:
            raise QMIError("关闭RC模式异常")

        s = subprocess.getoutput(f'ifconfig {self.rtl8125_ethernet_name} down')
        all_logger.info(f"ifconfig {self.rtl8125_ethernet_name} down: {s}")

        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        time.sleep(10)

    def restart_eth_network_card(self, eth_test_mode='2'):
        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} down')
        all_logger.info(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} down: {s}')

        all_logger.info('wait 5 seconds')  # 时间太少可能会导致获取不到ipv6地址
        time.sleep(5)

        s = subprocess.getoutput(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} up')
        all_logger.info(f'ifconfig {self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name} up: {s}')

    def send_at_error_try_again(self, common_at, time_out_at=0.6):  # 部分指令很容易出现ERROR，但重试又正常
        all_logger.info(common_at)
        return_value_at = ''
        for i in range(10):  # 针对此指令容易返回error
            return_value_at = self.at_handle.send_at(common_at, time_out_at)
            if 'ERROR' not in return_value_at:
                return return_value_at
            time.sleep(1)
        else:
            all_logger.info(f'连续10次发送AT+QETH="ipptmac"失败： {return_value_at}')

    def check_mPDN_rule(self, vlan, apn, mac=''):
        """
        AT+QMAP="mPDN_rule"
        +QMAP: "MPDN_rule",0,0,0,0,0
        +QMAP: "MPDN_rule",1,0,0,0,0
        +QMAP: "MPDN_rule",2,0,0,0,0
        +QMAP: "MPDN_rule",3,0,0,0,0

        OK
        """
        return_value = self.send_at_error_try_again('AT+QMAP="mPDN_rule"', 60)
        all_logger.info(f'{return_value}')
        if apn and mac == '' and f'+QMAP: "MPDN_rule",0,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",0,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",1,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",1,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",2,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",2,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac == '' and f'+QMAP: "MPDN_rule",3,{apn},{vlan},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        elif apn and mac != '' and f'+QMAP: "MPDN_rule",3,{apn},{vlan},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号规则检查正常!")
        else:
            raise QMIError(f"vlan{vlan}、apn{apn}拨号规则检查异常!")

    def check_MPDN_status(self, vlan, apn, mac=''):
        """
        AT+QMAP="MPDN_status"
        +QMAP: "MPDN_status",0,0,0,0
        +QMAP: "MPDN_status",1,0,0,0
        +QMAP: "MPDN_status",2,0,0,0
        +QMAP: "MPDN_status",3,0,0,0

        OK
        """
        all_logger.info("等待10s拨号稳定")
        time.sleep(10)
        return_value = self.send_at_error_try_again('AT+QMAP="MPDN_status"', 60)
        all_logger.info(f'{return_value}')
        if mac == '' and f'+QMAP: "MPDN_status",0,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",0,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",1,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",1,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",2,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",2,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        elif mac == '' and f'+QMAP: "MPDN_status",3,{apn},0,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}拨号状态检查正常!")
        elif mac != '' and f'+QMAP: "MPDN_status",3,{apn},1,1' in return_value:
            all_logger.info(f"vlan{vlan}、apn{apn}使用MAC地址拨号状态检查正常!")
        else:
            raise QMIError(f"vlan{vlan}、apn{apn}拨号状态检查异常!")

    def common_connect_check(self, eth_test_mode):
        # 重新获取ip
        self.udhcpc_get_ip_eth(eth_test_mode)

        # get ipv4
        ipv4 = self.get_network_card_ipv4(eth_test_mode, www='False')
        # self.get_network_card_ipv6(eth_test_mode)

        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网是否正常")
        time.sleep(10)

        retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
        all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
        if '0:0:0:0:0:0:0:0' in retunr_value:
            raise QMIError("模块拨号获取IPV6地址失败！")

        # check ipv4
        if ipv4.startswith('192.168') is False:
            raise QMIError("Common IPv4 not start with 192.168.")

        # check connect ipv4
        for _ in range(3):
            try:
                self.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name)
                break
            except Exception as e:
                all_logger.info(e)
                # 重新获取ip
                self.restart_eth_network_card(eth_test_mode)
                self.udhcpc_get_ip_eth(eth_test_mode)
        else:
            raise QMIError("尝试3次重新获取IP后ping失败")

    @staticmethod
    def eth_ping_ipv6():
        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网ipv6是否正常")
        ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666', '240c::6666'], count=20, interval=1, family=6)
        for ping_data in ping_datas:
            all_logger.info(f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
            if ping_data.is_alive:
                all_logger.info('ping检查正常')
                return True
        else:
            all_logger.info('拨号后获取IP测试网络连接异常')
            return False
            # raise LinuxETHError('ping ipv6检查异常')

    def get_network_card_ipv4(self, eth_test_mode, www='False'):
        out = None
        for i in range(30):
            out = subprocess.getoutput('ifconfig {} | grep "inet " | tr -s " " | cut -d " " -f 3 | head -c -1'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            if out and www == 'False' and out.startswith("192"):  # 如果是获取内网IP
                all_logger.info(f"IPv4 internal address is: {repr(out)}")
                return out
            elif out and www == 'True' and out.startswith("192") is False:  # 如果是获取外网IP
                all_logger.info(f"IPv4 www address is: {repr(out)}")
                return out
            elif out and www == 'QSS' and out.startswith("192.168.2."):  # 如果是获取QSS IP
                all_logger.info(f"IPv4 QSS address is: {repr(out)}")
                return out
            else:
                time.sleep(1)
                continue
        else:
            s = subprocess.getoutput('ifconfig {}'.format(self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name))
            all_logger.info(s)
            if www == "True":
                raise QMIError("IP Passthrough RGMII 拨号模式，未获取到公网IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))
            else:
                raise QMIError("Common RGMII 拨号模式，未获取到192.168.开头的IP，{}".format('当前IP{}'.format(out) if out else '请检查log'))

    def eth_network_card_down(self, eth_test_mode):  # 禁用PHY网卡
        all_logger.info('eth_test_mode: {}'.format(eth_test_mode))
        now_network_card_name = self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name
        all_logger.info('now_network_card_name: {}'.format(now_network_card_name))
        # 恢复默认网卡
        ifconfig_down_value = subprocess.getoutput('ifconfig {} down'.format(now_network_card_name))  # 启用本地网卡
        all_logger.info('ifconfig {} down\r\n{}'.format(now_network_card_name, ifconfig_down_value))

    def exit_eth_mode(self, eth_test_mode):
        """
        eth_test_mode:
        1  RGMII
        2  RTL8125
        3  RTL8168
        """
        if eth_test_mode != '':
            all_logger.info(f"开始退出{self.eth_test_mode_list[eth_test_mode]}模式")
            if eth_test_mode == '2':
                self.rgmii(status="disable", voltage=1, check=False)
            elif eth_test_mode == '3':
                self.exit_rtl_mode()
            elif eth_test_mode == '4':
                self.exit_rtl_mode()
            elif eth_test_mode == '5':
                self.exit_rtl_mode()
        else:
            self.rgmii(status="disable", voltage=1)
            self.exit_rtl_mode()

    def ip_passthrough_connect_check(self, eth_test_mode, try_times=3):
        # 重新获取ip
        self.restart_eth_network_card(eth_test_mode)
        self.udhcpc_get_ip_eth(eth_test_mode)

        # get ipv4
        self.get_network_card_ipv4(eth_test_mode, www='QSS')
        # self.get_network_card_ipv6(eth_test_mode)

        # wait 10 seconds
        all_logger.info("开始检查拨号后ping外网是否正常")
        time.sleep(10)

        # check ipv4
        # if ipv4.endswith('2.2') is False:
        #     raise QMIError("IP Passthrough RGMII IPv4 start with 192.168.")

        retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
        all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
        if '0:0:0:0:0:0:0:0' in retunr_value:
            raise QMIError("模块拨号获取IPV6地址失败！")

        # check connect ipv4
        for _ in range(try_times):
            try:
                self.ping_get_connect_status(network_card_name=self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name)
                break
            except Exception as e:
                all_logger.info(e)
                # 重新获取ip
                self.restart_eth_network_card(eth_test_mode)
                self.udhcpc_get_ip_eth(eth_test_mode)
        else:
            raise QMIError(f"尝试{try_times}次重新获取IP后ping失败")

    def set_apn(self, path, apn=""):
        default_apn_str = str(self.default_apns).upper()
        if not apn:
            if 'CMNET' in default_apn_str:
                apn = "CTNET"
            elif '3GNET' in default_apn_str:
                apn = "CMNET"
            else:
                apn = "3GNET"

        self.at_handle.send_at(f'AT+CGDCONT={path},"IPV4V6","{apn}"', 3)
        time.sleep(3)
        cgdcont = self.at_handle.send_at('AT+CGDCONT?')
        all_logger.info(cgdcont)

    def open_vlan(self, vlan_num):
        all_logger.info(f"开启vlan {vlan_num}")
        return_vlan_set = self.at_handle.send_at(f'at+qmap="vlan",{vlan_num},"enable"', 6)
        all_logger.info(f'at+qmap="vlan",{vlan_num},"enable": \r\n{return_vlan_set}')
        time.sleep(60)  # 第一次设置vlan模块可能会重启
        self.driver_check.check_usb_driver()
        time.sleep(5)
        return_vlan_check = self.at_handle.send_at('at+qmap="vlan"', 3)
        if f'+QMAP: "VLAN",{vlan_num}' not in return_vlan_check:
            raise QMIError(f'检查vlan异常： {return_vlan_check} ,期望为+QMAP: "VLAN",{vlan_num}')

    def send_mpdn_rule(self, mpdn_rule=''):
        return_value = ''
        for i in range(10):  # 针对此指令容易返回error
            if mpdn_rule == '':
                return_value = self.at_handle.send_at('AT+qmap="mpdn_rule"', 60)
            else:
                return_value = self.at_handle.send_at(f'AT+qmap="mpdn_rule",{mpdn_rule}', 60)
            if 'ERROR' not in return_value:
                return return_value
            time.sleep(1)
        else:
            raise QMIError(f'连续10次发送AT+qmap="mpdn_rule"失败： {return_value}')

    def two_way_dial_set(self, eth_test_mode):
        now_network_card_name = self.rgmii_ethernet_name if eth_test_mode == "2" else self.rtl8125_ethernet_name
        # modprobe 8021q
        return_8021q = subprocess.getoutput('modprobe 8021q')
        all_logger.info('加载vlan模块modprobe 8021q:{}'.format(return_8021q))

        # ifconfig eth1 down
        ifconfig_down = subprocess.getoutput(f'ifconfig {now_network_card_name} down')
        all_logger.info(f'ifconfig {now_network_card_name} down :{ifconfig_down}')

        # ifconfig eth1 hw ether 00:0e:c6:67:78:01 up
        # ifconfig_up = subprocess.getoutput(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up')
        # all_logger.info(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up :{ifconfig_up}')

        # vconfig add eth1 2
        vconfig_up_2 = subprocess.getoutput(f'vconfig add {now_network_card_name} 2')
        all_logger.info(f'vconfig add {now_network_card_name} 2 :{vconfig_up_2}')

        # sudo ifconfig eth1.2 hw ether FF:FF:FF:FF:FF:FF up
        # sudo ifconfig eth1.3 up
        # sudo ifconfig eth1.4 up
        # ifconfig_up_2 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up')
        # all_logger.info(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up  :{ifconfig_up_2}')

        # ifconfig
        ifconfig_all_result = subprocess.getoutput('ifconfig -a')
        all_logger.info(f'ifconfig -a  :{ifconfig_all_result}')
        if f'{now_network_card_name}.2' not in ifconfig_all_result:
            raise QMIError(f"网卡状态异常：{ifconfig_all_result}")

        # sudo udhcpc -i eth1
        # sudo udhcpc -i eth1.2
        # sudo udhcpc -i eth1.3
        # sudo udhcpc -i eth1.4
        self.udhcpc_get_ip_eth(network_name=f'{now_network_card_name}')
        self.udhcpc_get_ip_eth(network_name=f'{now_network_card_name}.2')

    def mpdn_route_set(self, eth_test_mode, network_card_nums=2):
        """
        route set for mpdn
        """
        return_value0 = subprocess.getoutput('echo 1 > /proc/sys/net/ipv4/ip_forward')
        all_logger.info('echo 1 > /proc/sys/net/ipv4/ip_forward\n{}'.format(return_value0))
        time.sleep(1)
        return_value_all = subprocess.getoutput('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter')
        all_logger.info('echo 0 > /proc/sys/net/ipv4/conf/all/rp_filter\n{}'.format(return_value_all))
        time.sleep(1)
        return_value1 = subprocess.getoutput(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}/rp_filter")
        all_logger.info(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}/rp_filter : {return_value1}")
        time.sleep(1)
        for i in range(2, network_card_nums + 1):
            return_value2 = subprocess.getoutput(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}.{i}/rp_filter")
            all_logger.info(f"echo 0 > /proc/sys/net/ipv4/conf/{self.rgmii_ethernet_name if eth_test_mode == '2' else self.rtl8125_ethernet_name}.{i}/rp_filter : {return_value2}")
            time.sleep(1)

    def get_value_debug(self, commond):
        """
        Debug输入命令后返回值
        """
        # 启动线程
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        data = ''
        try:
            all_logger.info('wait 20 secs.')
            time.sleep(20)

            all_logger.info(commond)
            data = debug_port.exec_command(commond)
            all_logger.info('denug data : {}'.format(data))

        finally:
            all_logger.info('check pci end')
            debug_port.close_debug()
            return data


class CheckSmsUrc(Thread):
    def __init__(self, at_port):
        """
        检测来短信时的上报
        """
        super().__init__()
        self.flag = False
        self.at_handle = ATHandle(at_port)

    def run(self):
        try:
            self.at_handle.readline_keyword('+CMGS', '+CMT', timout=60)
            self.flag = True
        except Exception as e:
            all_logger.info(e)


class DebugPort(Thread):

    def __init__(self, debug_port, name_qgmr_version):
        super().__init__()
        self.debug_port = serial.Serial(debug_port, baudrate=115200, timeout=0.8)
        self.debug_port.write('\r\n'.encode('utf-8'))
        self.debug_open_flag = True
        self.debug_read_flag = True
        self.dq = deque(maxlen=100)
        # 是否是OCPU版本
        self.Is_OCPU_version = True if 'OCPU' in name_qgmr_version else False

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
                    if self.Is_OCPU_version:
                        passwd = 'oelinux123'
                    else:
                        passwd = getpass(qid)
                    all_logger.info(passwd)
                    self.debug_port.write('{}\r\n'.format(passwd).encode('utf-8'))
                if not self.debug_open_flag:
                    self.debug_port.close()
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
        self.debug_open_flag = False

    def ctrl_c(self):
        self.debug_port.write("\x03".encode())

    def get_latest_data(self, depth=10):
        return ''.join(list(self.dq)[-depth:])
