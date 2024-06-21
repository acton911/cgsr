import sys
from icmplib import ping, multiping # noqa
from requests_toolbelt.adapters import source
import requests
from utils.functions.gpio import GPIO
from utils.operate.at_handle import ATHandle
from utils.operate.reboot_pc import Reboot
from utils.functions.driver_check import DriverChecker
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import QMIError, ATError, LinuxAPIError
from utils.functions.linux_api import LinuxAPI, QuectelCMThread
import subprocess
import time
import os
import re
from tools.qss.qss_client import ConnectQSS, WriteSimcard
from functools import partial
from ..functions.decorators import watchdog

watchdog = partial(watchdog, logging_handle=all_logger, exception_type=LinuxAPIError)


class linuxAPNandAuthFunctionsManager:
    def __init__(self, at_port, dm_port, debug_port, wwan_path, network_card_name, extra_ethernet_name, params_path, qss_ip, local_ip, node_name, mme_file_name, enb_file_name, ims_file_name,  rgmii_ethernet_name, rtl8125_ethernet_name, eth_test_mode, pc_ethernet_name):
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

    def open_qss_white(self):
        # 将卡写00101
        return_imsi = self.write_simcard.get_cimi()
        if return_imsi.startswith('00101'):
            all_logger.info(f"当前卡imsi为{return_imsi}，可直接使用")
        else:
            self.at_handle.cfun0()
            time.sleep(3)
            self.at_handle.cfun1()
            time.sleep(60)  # 先等待一会，否则直接写卡可能失败
            self.write_simcard.write_white_simcard('00101', '8949024')

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

    def dial(self, times=10, is_success=True):
        """
        拨号后进行Ping业务
        times: ping的时长
        is_success: 是否成功拨号后再ping
        :return: None
        """
        q = None
        exc_type = None
        exc_value = None
        try:
            ifconfig_down_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{ifconfig_down_value}')
            time.sleep(20)
            q = QuectelCMThread(netcard_name=self.network_card_name)
            q.setDaemon(True)
            self.at_handle.check_network()
            # 拨号
            q.start()
            time.sleep(60)
            self.check_route()
            time.sleep(2)
            all_logger.info('start')
            if is_success:
                self.ping_get_connect_status(network_card_name=self.network_card_name, times=times)
            else:
                self.get_ip_address(False)
            self.check_cgact()
        except Exception as e:
            all_logger.info(e)
            exc_type, exc_value, _ = sys.exc_info()
        finally:
            q.ctrl_c()
            q.terminate()
            ifconfig_up_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
            all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{ifconfig_up_value}')
            udhcpc_value = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
            all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{udhcpc_value}')
            self.linux_api.check_intranet(self.extra_ethernet_name)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    def local_net_down(self):
        """
        关闭本地网
        :return: None
        """
        return_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} down')
        # os.popen('ifconfig {} down'.format(self.local_network_card_name))
        all_logger.info(f'ifconfig {self.extra_ethernet_name} down\r\n{return_value}')
        for i in range(10):
            ifconfig_value = subprocess.getoutput('ifconfig')
            if self.extra_ethernet_name not in ifconfig_value:
                all_logger.info('关闭本地网成功')
                return True
            else:
                time.sleep(3)
                continue
        else:
            raise QMIError('关闭本地网失败')

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

    def get_ip_address(self, is_success=False):
        """
        执行ifconfig -a检测IP地址是否正常
        is_success: True: 要求可以正常检测到IP地址；False: 要求检测不到IP地址
        :return: None
        """
        ip = ''
        for i in range(30):
            ifconfig_value = os.popen('ifconfig -a').read()
            try:
                re_ifconfig = re.findall(fr'{self.network_card_name}.*\n(.*)', ifconfig_value)[0].strip()
                ip = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', re_ifconfig)[0]
            except IndexError:
                pass
            if is_success:
                if ip:
                    all_logger.info(f'获取IP地址正常,IP地址为{ip}')
                    return True
                else:
                    if i == 29:
                        raise QMIError(f'获取IP地址异常,未获取到IP地址,ifconfig -a返回{ifconfig_value}')
            else:
                if not ip:
                    all_logger.info('IP地址正常,当前未获取到IP地址')
                    return True
                else:
                    if i == 29:
                        raise QMIError(f'异常,当前未进行拨号,但获取到IP地址{ip}')
            time.sleep(2)

    def local_net_up(self):
        """
        开启本地网
        :return: None
        """
        return_value = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
        all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{return_value}')

    def check_intranet(self, intranet_ip='192.168.11.252'):
        all_logger.info('start check intranet')
        intranet_flag = True
        i = 0
        while i < 10:
            time.sleep(3)
            i = i + 1
            return_value = subprocess.getoutput(f'ping {intranet_ip} -c 10')
            all_logger.info(f"{return_value}")
            if '100% packet loss' in return_value or 'unknown' in return_value or 'unreachable' in return_value \
                    or 'failure' in return_value:
                all_logger.info(f"fail to ping {intranet_ip}")
                return_value1 = subprocess.getoutput('ifconfig')  # get ip
                all_logger.info(f'ifconfig\r\n{return_value1}')
                all_logger.info('the intranet connect FAIL!')
                all_logger.info('Trying to connect...')
                # killall quectel-CM
                return_value2 = subprocess.getoutput('killall quectel-CM')
                all_logger.info(f'killall quectel-CM\r\n{return_value2}')
                return_value3 = subprocess.getoutput(f'ifconfig {self.extra_ethernet_name} up')
                all_logger.info(f'ifconfig {self.extra_ethernet_name} up\r\n{return_value3}')
                time.sleep(3)
                return_value4 = subprocess.getoutput(f'udhcpc -i {self.extra_ethernet_name}')  # get ip
                all_logger.info(f'udhcpc -i {self.extra_ethernet_name}\r\n{return_value4}')
                intranet_flag = False
            else:
                all_logger.info('the intranet connect successfully!')
                intranet_flag = True
                break
        if not intranet_flag:
            raise QMIError('The intranet connect FAIL, please check the intranet!')

    def check_cgact(self):
        """
        检测CGACT第一路是否激活
        :return: None
        """
        all_logger.info('check cgact')
        cgact_value_return = self.at_handle.send_at('AT+CGACT?', timeout=0.3)
        if cgact_value_return != '':
            cgact_value_re = ''.join(re.findall(r'\+CGACT:1,1', cgact_value_return))
            all_logger.info(cgact_value_re)
        else:
            raise QMIError('CGACT default activation failure')

    def set_cgdcont(self, set_apn, ip_type="IPV4V6"):
        """
        配置APN相关参数
        set_apn:要配置的APN
        ip_type：类型，如：IPV4,IPV6,IPV4V6
        """
        first_cgdcont_data = self.at_handle.send_at('at+cgdcont=1,"{}","{}"'.format(ip_type, set_apn))
        if 'OK' in first_cgdcont_data:
            all_logger.info('第一路鉴权登录配置成功')
        else:
            raise ATError('第一路鉴权登录配置失败')
        self.at_handle.send_at('AT+CGDCONT?', timeout=0.3)

    def set_qicsgp(self, apn, username, password, authentication):
        """
        配置TCP/IP上下文参数
        """
        qicsgp_data = self.at_handle.send_at('AT+QICSGP=1,3,"{}","{}","{}",{}'.format(apn, username, password, authentication))
        if 'OK' in qicsgp_data:
            all_logger.info('配置第一路APN鉴权')
        else:
            raise ATError('配置')
        self.at_handle.send_at('AT+QICSGP=1', timeout=0.3)

    def set_cgdcont_fail(self, set_apn, ip_type="IPV4V6"):
        """
              配置APN相关参数
              set_apn:要配置的APN
              ip_type：类型，如：IPV4,IPV6,IPV4V6
        """
        first_cgdcont_data = self.at_handle.send_at('at+cgdcont=1,"{}","{}"'.format(ip_type, set_apn))
        if 'ERROR' in first_cgdcont_data:
            all_logger.info('返回结果符合预期')
        else:
            raise ATError('返回结果不符合预期')
        cgdcont_data = self.at_handle.send_at('AT+CGDCONT?', timeout=0.3)
        if set_apn not in cgdcont_data:
            all_logger.info('APN配置符合符合预期')
        else:
            raise ATError('配置第一路成功')

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
    @watchdog("进行PING连接测试")
    def ping_get_connect_status(ipv6_flag=False, network_card_name="wwan0", times=20, flag=True):
        ip = LinuxAPI.get_ip_address(network_card_name, ipv6_flag)
        all_logger.info(f"DNS: {subprocess.getoutput('cat /etc/resolv.conf')}")
        if not flag:
            ping('www.baidu.com', count=times, interval=1, source=ip)
            time.sleep(1)
        else:
            if not ipv6_flag:
                target_ip_list = ['www.baidu.com', '192.168.2.1', 'www.qq.com', 'www.sina.com', '8.8.8.8']
                for i in range(5):
                    try:
                        ping_data = ping(target_ip_list[i], count=times, interval=1, source=ip)
                        all_logger.info(
                            f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
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
                        ping_datas = multiping(['www.baidu.com', 'www.qq.com', 'www.sina.com', '8.8.8.8'], count=times,
                                               interval=1, source=ip)
                        for ping_data in ping_datas:
                            all_logger.info(
                                f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                            if ping_data.is_alive:
                                all_logger.info('重新获取IP后ping检查正常')
                                return True
                        else:
                            raise LinuxAPIError('重新获取IP后ping检查异常')
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
                            return True
                        else:
                            all_logger.info('拨号后request请求失败')
                            raise LinuxAPIError('拨号后ping检查异常，request请求异常')
            elif ipv6_flag:
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times,
                                       interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(
                        f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return True
                else:
                    all_logger.info('拨号后获取IP测试网络连接异常，尝试重新获取IP后测试')
                    ip = LinuxAPI.get_ip_address(network_card_name, ipv6_flag)
                ping_datas = multiping(['2402:f000:1:881::8:205', '2400:3200::1', '2400:da00::6666'], count=times,
                                       interval=1, source=ip, family=6)
                for ping_data in ping_datas:
                    all_logger.info(
                        f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                    if ping_data.is_alive:
                        all_logger.info('ping检查正常')
                        return True
                else:
                    all_logger.info('ping ipv6检查异常')
                    raise LinuxAPIError('ping ipv6检查异常')
















