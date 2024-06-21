import os
import re
import subprocess
import sys
import time
import traceback
from icmplib import ping
from utils.functions.decorators import startup_teardown
from utils.cases.linux_eth_manager import LinuxETHManager, DebugPort
from utils.functions.linux_api import PINGThread, LinuxAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxETHError
from utils.functions.iperf import iperf
from utils.functions.middleware import Middleware
from utils.log import log
from utils.functions.linux_api import enable_network_card_and_check


class LinuxETH(LinuxETHManager):

    @startup_teardown()
    def test_linux_eth_common_01_000(self):
        log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_eth_common_01_000')
        all_logger.info(f"log_save_path: {log_save_path}")
        with Middleware(log_save_path=log_save_path) as m:
            # 业务逻辑
            self.at_handler.cfun0()
            time.sleep(5)
            self.at_handler.cfun1()
            all_logger.info("wait 30 seconds, catch log end")
            time.sleep(30)

            # 停止抓Log
            log.stop_catch_log_and_save(m.log_save_path)
            log_n, log_p = m.find_log_file()

            # 发送本地Log文件
            message_types = {"LOG_PACKET": ["0xB800", "0xB0E3"]}
            interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                       "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
            data = log.load_log_from_remote(log_p, log_p, message_types, interested_return_filed)
            all_logger.info(data)

    @startup_teardown()
    def test_linux_eth_common_01_001(self):
        """
        1.使用AT+QETH指令查询参数是否与ATC文档一致
        """
        self.qeth_attr_check()

    @startup_teardown()
    def test_linux_eth_common_01_002(self):
        """
        1.使用AT+QMAP=?指令查询参数是否与ATC文档一致
        """
        self.qmap_attr_check()

    @startup_teardown()
    def test_linux_eth_common_01_003(self):
        """
        1.使用AT+QETH="rgmii"启用以太网RGMII功能，不拨号
        2.使用AT+QETH="rgmii"查询以太网rgmii状态
        3.观察PC端本地网络连接状态，并进行ping操作
        """
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            try:
                self.enter_eth_mode('2')
            finally:
                self.eth_network_card_down('2')
                self.exit_eth_mode('2')
        else:
            all_logger.info("当前设备没有RGMII8035\8211，跳过")

    @startup_teardown()
    def test_linux_eth_common_01_004(self):
        """
        1.将RTL8125小板固定在5G EVB板子上的WIFI-TE-A处，5GEVB的usb口及debug口连接PC1，拨动5GEVB上的PCIE_SEL1和PCIE_SEL2至HIGH，从RTL8125phy网口连接网线至PC2。
        2.配置pcie RC模式
        3.选择 RTL8125 网卡驱动并使能
        4.重启模块，并在debug口输入lspci查询驱动是否加载成功.查询模块内部ip地址
        """
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            try:
                self.enter_eth_mode('3')
            finally:
                self.eth_network_card_down('3')
                self.exit_eth_mode('3')
        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            try:
                self.enter_eth_mode('4')
            finally:
                self.eth_network_card_down('4')
                self.exit_eth_mode('4')
        else:
            all_logger.info("当前设备没有RTL8125\RTL8168，跳过")

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_005(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认QMAP-COMMON拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址，可正常上网
        5.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            self.common_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_006(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用COMMON拨号规则0,使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认QMAP-COMMON拨号状态，观察PC端本地连接状态以及IP地址，ping V4 V6地址各10次
        5.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            all_logger.info("开始ping V4 V6地址各10次")
            for i in range(10):
                all_logger.info(f"***************开始第{i + 1}次ping V4 V6地址***************")
                self.common_connect_check(now_mode)
                all_logger.info(f"***************第{i + 1}次ping V4 V6地址结束***************")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_007(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用QMAP-COMMON拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认QMAP-COMMON拨号状态，观察PC端本地连接状态以及IP地址，speedtest速率测试5次
        5.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            self.common_connect_check(now_mode)
            for i in range(5):
                all_logger.info(f"***************开始第{i + 1}次测速***************")
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test}")
                all_logger.info(f"***************第{i + 1}次测速结束***************")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_008(self):
        """
        1.使用AT指令查询网络状态
        2.开启vlan2（立即生效，第一次增加vlan或禁用仅存的一路vlan模块会自动重启）
        3.查询模块内的VLAN
        4.配置并启用COMMON拨号规则0，使用vlan2和第一路APN
        5.查询当前拨号规则
        6.查询默认COMMON拨号状态，观察PC端本地连接状态以及IP地址，speedtest速率测试5次
        7.禁用QMAP拨号规则0
        8.禁用vlan2
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            """
            now_mode = self.enter_eth_mode(self.self.eth_test_mode)
            self.open_vlan('2')
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,2,0,1', 3)
            time.sleep(60)  # 模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.check_mPDN_rule('2', '1')
            self.check_MPDN_status('2', '1')
            self.common_connect_check(now_mode)
            for i in range(5):
                all_logger.info(f"***************开始第{i + 1}次测速***************")
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test}")
                all_logger.info(f"***************第{i + 1}次测速结束***************")
            """
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,0,1')
            self.send_mpdn_rule('1,2,2,0,1')

            self.check_mPDN_rule('0', '1')
            self.check_mPDN_rule('2', '2')

            self.check_MPDN_status('0', '1')
            self.check_MPDN_status('2', '2')

            self.two_way_dial_set(now_mode)

            self.mpdn_route_set(now_mode, 2)

            now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
            ifconfig_get_result = subprocess.getoutput(f'ifconfig')
            all_logger.info(f'ifconfig :{ifconfig_get_result}')
            if f'{now_network_card_name}.2' not in ifconfig_get_result:
                raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')

            for i in range(5):
                all_logger.info(f"***************开始第{i + 1}次测速***************")
                speed_test = self.speedtest(network_card=f'{now_network_card_name}.2')
                if speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test}")
                all_logger.info(f"***************第{i + 1}次测速结束***************")

        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",1', 60)
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_009(self):
        """
        1.使用AT指令查询IPPassthrough-RGMII默认的MAC地址
        """
        self.ipptmac_check_default()

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_010(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址，可正常上网
        5.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_012(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址，可正常上网
        5.修改上位机MAC地址或者更换上位机
        6.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.ipptmac_set_check(now_mode)
            pc_ethernet_orig_mac = subprocess.getoutput(
                'ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(
                    self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name))
            self.at_handler.send_at(f'AT+qmap="mpdn_rule",0,1,0,1,1,"{pc_ethernet_orig_mac}"', 6)
            self.check_mPDN_rule('0', '1', pc_ethernet_orig_mac)
            self.check_MPDN_status('0', '1', pc_ethernet_orig_mac)
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            time.sleep(10)  # 避免太快返回error
            # self.at_handler.send_at('AT+QETH="ipptmac","FF:FF:FF:FF:FF:FF"', 6)
            self.send_ipptmac("FF:FF:FF:FF:FF:FF")
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_013(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址，ping V4 V6地址各10次
        5.禁用QMAP拨号规则0
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            all_logger.info("开始ping V4 V6地址各10次")
            for i in range(10):
                all_logger.info(f"***************开始第{i + 1}次ping V4 V6地址***************")
                self.ip_passthrough_connect_check(now_mode)
                all_logger.info(f"***************第{i + 1}次ping V4 V6地址结束***************")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_014(self):
        """
        1.模块注册SA网络
        2.指定带宽30M通过Iperf灌包速率测试5min
        3.关闭IPPassthrough拨号
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            all_logger.info("开始30M灌包速率测试5min")
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_015(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_016(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第二路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 2
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,2,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_017(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第三路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 3
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,3,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_018(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第四路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 4
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,4,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_019(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第五路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 5
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,5,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_020(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第六路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 6
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,6,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_021(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第七路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 7
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,7,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_022(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第八路APN
        3.查询当前拨号规则
        4.查询默认IPPassthrough拨号状态，观察debug口IP地址，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        """
        seq = 8
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,8,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_023(self):
        """
        1.使用AT指令获取网口Mac地址
        2.debug口登录root输入ifconfig 查看HWaddr的地址的mac地址
        3. 使用AT指令设置网口Mac地址
        4.查询RGMII网口Mac地址
        5. debug口登录root输入ifconfig 查看HWaddr的地址的mac地址
        """
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        time.sleep(10)
        try:
            # check old mac
            old_mac = self.at_get_mac_address()
            all_logger.info('old MAC address is : {}'.format(old_mac))

            debug_old_mac = debug_port.exec_command("ifconfig bridge0 | grep HWaddr")
            all_logger.info('\nold_mac: {}\ndebug_mac: {}'.format(old_mac, debug_old_mac))
            if old_mac not in debug_old_mac:
                raise LinuxETHError('AT+QETH="MAC_ADDRESS" 查询的默认mac地址与DEBUG查询的不一致！')

            time.sleep(5)

            # set new mac
            pc_ethernet_orig_mac = subprocess.getoutput(
                'ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(
                    self.rgmii_ethernet_name if self.eth_test_mode == '2' else self.rtl8125_ethernet_name))
            self.at_handler.send_at(f'AT+qmap="mpdn_rule",0,1,0,1,1,"{pc_ethernet_orig_mac}"', 6)

            # check new mac
            new_mac = self.at_get_mac_address()
            debug_new_mac = debug_port.exec_command("ifconfig bridge0 | grep HWaddr")
            all_logger.info('new_mac: {}\ndebug_new_mac: {}'.format(new_mac, debug_new_mac))
            if new_mac not in debug_new_mac:
                raise LinuxETHError('AT+QETH="MAC_ADDRESS" 查询的新设置mac地址与DEBUG查询的不一致！')
        finally:
            debug_port.close_debug()
            self.send_ipptmac("FF:FF:FF:FF:FF:FF")

    @startup_teardown()
    def test_linux_eth_common_01_024(self):
        """
        1.使用AT指令获取网口Mac地址
        2.debug口登录root输入ifconfig 查看HWaddr的地址的mac地址
        3. 进入fastboot模式
        4. 进入adb和fastboot所在文件夹，打开命令窗口，执行
        fastboot erase rawdata
        提示擦除成功之后，fastboot reboot重启模块
        5.使用AT指令获取RGMII网口Mac地址,并同步检查debug口bridge0地址
        6.禁用桥模式拨号
        7.再次使用桥模式拨号
        8.使用AT指令获取网口Mac地址,并同步检查debug口bridge0地址
        """
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        time.sleep(10)
        now_mode = ''
        try:
            old_mac = self.at_get_mac_address()
            all_logger.info('old MAC address is : {}'.format(old_mac))
            self.sitch_fastboot_erase_rawdata()
            erase_status = debug_port.get_latest_data()
            all_logger.info('erase status: {}'.format(erase_status))
            if 'block error' in erase_status:
                raise LinuxETHError('erase rawdata failed: {}'.format(erase_status))
            self.fastboot_reboot()

            all_logger.info("wait 20 seconds.")
            time.sleep(20)

            # check mac
            new_mac = self.at_get_mac_address()
            debug_mac = debug_port.exec_command("ifconfig bridge0 | grep HWaddr")
            all_logger.info('\nold_mac: {}\nnew_mac: {}\ndebug_mac: {}'.format(old_mac, new_mac, debug_mac))
            if new_mac not in debug_mac:
                raise LinuxETHError('AT+QETH="MAC_ADDRESS" MAC not equal to debug port bridge0 mac.')

            all_logger.info('\nold MAC address: {}\nnew MAC address: {}'.format(old_mac, new_mac))
            if old_mac == new_mac:
                raise LinuxETHError('MAC address not change after erase rawdata partition.')

            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)

            seq = 1
            self.set_apn(seq)

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)

            self.at_get_mac_address()
            debug_mac = debug_port.exec_command("ifconfig bridge0 | grep HWaddr")
            all_logger.info('\nold_mac: {}\nnew_mac: {}\ndebug_mac: {}'.format(old_mac, new_mac, debug_mac))

        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            debug_port.close_debug()

    @startup_teardown(startup=['at_handler', 'set_sim_pin'],
                      teardown=['at_handler', 'sin_pin_remove'])
    def test_linux_eth_common_01_025(self):
        """
        1.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        2.查询拨号状态
        3.解PIN
        4.查询拨号状态
        5.禁用QMAP拨号规则0
        """
        seq = 1
        now_mode = ''

        self.at_handler.send_at('AT+CFUN=0', 15)
        time.sleep(5)
        self.at_handler.send_at("AT+CFUN=1", 15)
        # noinspection PyBroadException
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        except Exception:
            msg = traceback.format_exc()
            all_logger.info("拨号失败信息msg: {}".format(msg))
            if '异常' in msg:
                all_logger.info("和预期一致，锁pin状态下拨号失败")
            else:
                raise LinuxETHError("异常！锁pin状态下拨号异常！")
            self.at_handler.at_unlock_sim_pin(1234)
            self.at_handler.check_network()
            time.sleep(20)
            self.ip_passthrough_connect_check(now_mode)

        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_026(self):
        """
        1.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.重启模块确认是否可以直接连接并上网
        4.禁用QMAP拨号规则0
        5.重复步骤1-4 10次确认是否存在问题
        """
        for i in range(10):
            all_logger.info(f"***************开始第{i + 1}次重启拨号测试***************")
            seq = 1
            self.set_apn(seq)
            now_mode = ''
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)  # 立即发AT可能会ERROR
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_027(self):
        """
        1.查询所有激活的vlan
        2.启用vlan2（默认不用vlan ID 1）
        3.启用vlan3
        4.查询所有激活的vlan
        5.禁用vlan2
        6.禁用vlan3
        7.禁用vlan0
        """
        now_mode = ''
        try:
            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            return_error = self.at_handler.send_at('at+qmap="vlan",0,"disable"', 6)
            if "ERROR" not in return_error:
                raise LinuxETHError(f"关闭vlan异常！{return_error}")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_028(self):
        """
        1.查询当前网络是否为SA
        2.配置好二路apn
        3.使用AT指令查询APN
        4.查询所有激活的vlan
        5.启用两路vlan（默认不用vlan ID 1）
        6.查询所有激活的vlan
        7.查询当前mPDN规则
        8.配置2条mPDN规则为COMMON拨号
        9.查询是否配置成功
        10.查询每条规则当前的拨号状态和ippt模式激活状态
        11.查询APN地址，抓QXDMlog，筛选OTA中PDU session establishment accept查询APN
        12.使用AT+QGPAPN=1获取实际APN/Profile id/IP地址，debug口查询rmnet_data0、rmnet_data1IP地址
        13.删除mPDN规则
        14.禁用第二路vlan
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_eth_common_01_028')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                """
                now_mode = self.enter_eth_mode(self.eth_test_mode)
                self.set_apn(6)
                return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
                all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")
                return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
                self.open_vlan('2')
                return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
                time.sleep(60)  # 模块可能会重启
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.send_at_error_try_again('AT+qmap="mpdn_rule",1,6,2,0,1', 3)
                time.sleep(60)  # 模块可能会重启
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.check_mPDN_rule('0', '1')
                self.check_mPDN_rule('2', '6')
                self.check_MPDN_status('0', '1')
                self.check_MPDN_status('2', '6')

                now_network_card_name = self.rgmii_ethernet_name if self.eth_test_mode == "2" else self.rtl8125_ethernet_name
                # modprobe 8021q
                return_8021q = subprocess.getoutput('modprobe 8021q')
                all_logger.info('加载vlan模块modprobe 8021q:{}'.format(return_8021q))

                # ifconfig eth1 hw ether 00:0e:c6:67:78:01 up
                # ifconfig_up = subprocess.getoutput(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up')
                # all_logger.info(f'ifconfig {now_network_card_name} hw ether FF:FF:FF:FF:FF:FF up :{ifconfig_up}')

                # ifconfig eth1 down
                ifconfig_down = subprocess.getoutput(f'ifconfig {now_network_card_name} down')
                all_logger.info(f'ifconfig {now_network_card_name} down :{ifconfig_down}')

                # vconfig add eth1 2
                vconfig_up_2 = subprocess.getoutput(f'vconfig add {now_network_card_name} 2')
                all_logger.info(f'vconfig add {now_network_card_name} 2 :{vconfig_up_2}')

                ifconfig_up_2 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.2 up')
                all_logger.info(f'ifconfig add {now_network_card_name}.2 up :{ifconfig_up_2}')
                # ifconfig_up_2 = subprocess.getoutput(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up')
                # all_logger.info(f'ifconfig add {now_network_card_name}.2 hw ether FF:FF:FF:FF:FF:FF up  :{ifconfig_up_2}')

                self.udhcpc_get_ip(network_name=now_network_card_name)
                self.udhcpc_get_ip(network_name=f'{now_network_card_name}.2')

                self.mpdn_route_set(now_mode, 2)

                self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
                self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
                """
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                self.at_handler.check_network()
                self.set_apn(2, 'apn2')
                return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
                all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

                return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
                self.open_vlan('2')
                return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
                return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
                if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                    raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
                self.send_mpdn_rule('0,1,0,0,1')
                self.send_mpdn_rule('1,2,2,0,1')

                self.check_mPDN_rule('0', '1')
                self.check_mPDN_rule('2', '2')

                self.check_MPDN_status('0', '1')
                self.check_MPDN_status('2', '2')

                self.two_way_dial_set(now_mode)

                self.mpdn_route_set(now_mode, 2)

                now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
                ifconfig_get_result = subprocess.getoutput(f'ifconfig')
                all_logger.info(f'ifconfig :{ifconfig_get_result}')
                if f'{now_network_card_name}.2' not in ifconfig_get_result:
                    raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

                self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
                self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')

                return_qgpapn = self.at_handler.send_at("AT+QGPAPN", 6)
                all_logger.info(return_qgpapn)
                apn_1_name = ''.join(re.findall(r'\+QGPAPN:\s1,"(.*)"', return_qgpapn))
                apn_2_name = ''.join(re.findall(r'\+QGPAPN:\s2,"(.*)"', return_qgpapn))
                all_logger.info(apn_1_name)
                all_logger.info(apn_2_name)
                if apn_1_name == '' or apn_2_name == '':
                    raise LinuxETHError(f"获取apn名称异常：{return_qgpapn}")

                return_qgpapn_1 = self.at_handler.send_at("AT+QGPAPN=1", 6)
                all_logger.info(return_qgpapn_1)
                ip_apn1 = ''.join(re.findall(r'\+QGPAPN:\s1,".*","(.*)"', return_qgpapn_1))
                ip_apn2 = ''.join(re.findall(r'\+QGPAPN:\s2,".*","(.*)"', return_qgpapn_1))
                all_logger.info(ip_apn1)
                all_logger.info(ip_apn2)
                if ip_apn1 == '' or ip_apn2 == '':
                    raise LinuxETHError(f"AT+QGPAPN=1获取IP异常：{return_qgpapn_1}")
                return_debug_value = self.get_value_debug('ifconfig -a')
                if ip_apn1 not in return_debug_value or ip_apn2 not in return_debug_value:
                    raise LinuxETHError(f"异常，AT+QGPAPN=1获取的IP: {ip_apn1}、{ip_apn2}在debug中未查询到： {return_debug_value}")
                else:
                    all_logger.info(f"已经在debug信息中找到 {ip_apn1}、{ip_apn2}")

                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
                self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
                time.sleep(60)  # disable vlan后模块可能会重启
                self.driver.check_usb_driver()
                time.sleep(3)  # 立即发AT可能会误判为AT不通
                self.exit_eth_mode(now_mode)

                enable_network_card_and_check(self.pc_ethernet_name)  # 恢复网络，传送解析log
                ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.pc_ethernet_name))  # 启用本地网卡
                all_logger.info('ifconfig {} up\r\n{}'.format(self.pc_ethernet_name, ifconfig_up_value))
                self.udhcpc_get_ip(network_name=self.pc_ethernet_name)

                all_logger.info("wait 30 seconds, catch log end")
                time.sleep(30)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"LOG_PACKET": ["0xB800", "0xB0E3"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info(data)

                apn_1_name_len = len(apn_1_name)
                for k in range(apn_1_name_len):
                    if f'({apn_1_name[k]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_1_name[k]}) 不在 {repr(data)} 之中')

                apn_2_name_len = len(apn_2_name)
                for j in range(apn_2_name_len):
                    if f'({apn_2_name[j]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_2_name[j]}) 不在 {repr(data)} 之中')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_029(self):
        self.at_handler.bound_network('NSA')
        now_mode = ''
        try:
            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_eth_common_01_029')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                self.at_handler.check_network()
                self.set_apn(2, 'apn2')
                return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
                all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

                return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
                self.open_vlan('2')
                return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
                return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
                if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                    raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
                self.send_mpdn_rule('0,1,0,0,1')
                self.send_mpdn_rule('1,2,2,0,1')

                self.check_mPDN_rule('0', '1')
                self.check_mPDN_rule('2', '2')

                self.check_MPDN_status('0', '1')
                self.check_MPDN_status('2', '2')

                self.two_way_dial_set(now_mode)

                self.mpdn_route_set(now_mode, 2)

                now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
                ifconfig_get_result = subprocess.getoutput(f'ifconfig')
                all_logger.info(f'ifconfig :{ifconfig_get_result}')
                if f'{now_network_card_name}.2' not in ifconfig_get_result:
                    raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

                self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
                self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')

                return_qgpapn = self.at_handler.send_at("AT+QGPAPN", 6)
                all_logger.info(return_qgpapn)
                apn_1_name = ''.join(re.findall(r'\+QGPAPN:\s1,"(.*)"', return_qgpapn))
                apn_2_name = ''.join(re.findall(r'\+QGPAPN:\s2,"(.*)"', return_qgpapn))
                all_logger.info(apn_1_name)
                all_logger.info(apn_2_name)
                if apn_1_name == '' or apn_2_name == '':
                    raise LinuxETHError(f"获取apn名称异常：{return_qgpapn}")

                return_qgpapn_1 = self.at_handler.send_at("AT+QGPAPN=1", 6)
                all_logger.info(return_qgpapn_1)
                ip_apn1 = ''.join(re.findall(r'\+QGPAPN:\s1,".*","(.*)"', return_qgpapn_1))
                ip_apn2 = ''.join(re.findall(r'\+QGPAPN:\s2,".*","(.*)"', return_qgpapn_1))
                all_logger.info(ip_apn1)
                all_logger.info(ip_apn2)
                if ip_apn1 == '' or ip_apn2 == '':
                    raise LinuxETHError(f"AT+QGPAPN=1获取IP异常：{return_qgpapn_1}")
                return_debug_value = self.get_value_debug('ifconfig -a')
                if ip_apn1 not in return_debug_value or ip_apn2 not in return_debug_value:
                    raise LinuxETHError(f"异常，AT+QGPAPN=1获取的IP: {ip_apn1}、{ip_apn2}在debug中未查询到： {return_debug_value}")
                else:
                    all_logger.info(f"已经在debug信息中找到 {ip_apn1}、{ip_apn2}")

                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
                self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
                time.sleep(60)  # disable vlan后模块可能会重启
                self.driver.check_usb_driver()
                time.sleep(3)  # 立即发AT可能会误判为AT不通
                self.exit_eth_mode(now_mode)

                enable_network_card_and_check(self.pc_ethernet_name)  # 恢复网络，传送解析log
                ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.pc_ethernet_name))  # 启用本地网卡
                all_logger.info('ifconfig {} up\r\n{}'.format(self.pc_ethernet_name, ifconfig_up_value))
                self.udhcpc_get_ip(network_name=self.pc_ethernet_name)

                all_logger.info("wait 30 seconds, catch log end")
                time.sleep(30)

                # 停止抓Log
                log.stop_catch_log_and_save(m.log_save_path)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"LOG_PACKET": ["0xB800", "0xB0E3"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info(data)

                apn_1_name_len = len(apn_1_name)
                for k in range(apn_1_name_len):
                    if f'({apn_1_name[k]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_1_name[k]}) 不在 {repr(data)} 之中')

                apn_2_name_len = len(apn_2_name)
                for j in range(apn_2_name_len):
                    if f'({apn_2_name[j]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_2_name[j]}) 不在 {repr(data)} 之中')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_030(self):
        self.at_handler.bound_network('LTE')
        now_mode = ''
        try:
            log_save_path = os.path.join(os.getcwd(), "QXDM_log", 'test_linux_eth_common_01_030')
            all_logger.info(f"log_save_path: {log_save_path}")
            with Middleware(log_save_path=log_save_path) as m:
                # 业务逻辑
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                self.at_handler.check_network()
                self.set_apn(2, 'apn2')
                return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
                all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

                return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
                self.open_vlan('2')
                return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
                all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
                return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
                if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                    raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
                self.send_mpdn_rule('0,1,0,0,1')
                self.send_mpdn_rule('1,2,2,0,1')

                self.check_mPDN_rule('0', '1')
                self.check_mPDN_rule('2', '2')

                self.check_MPDN_status('0', '1')
                self.check_MPDN_status('2', '2')

                self.two_way_dial_set(now_mode)

                self.mpdn_route_set(now_mode, 2)

                now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
                ifconfig_get_result = subprocess.getoutput(f'ifconfig')
                all_logger.info(f'ifconfig :{ifconfig_get_result}')
                if f'{now_network_card_name}.2' not in ifconfig_get_result:
                    raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

                self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
                self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')

                return_qgpapn = self.at_handler.send_at("AT+QGPAPN", 6)
                all_logger.info(return_qgpapn)
                apn_1_name = ''.join(re.findall(r'\+QGPAPN:\s1,"(.*)"', return_qgpapn))
                apn_2_name = ''.join(re.findall(r'\+QGPAPN:\s2,"(.*)"', return_qgpapn))
                all_logger.info(apn_1_name)
                all_logger.info(apn_2_name)
                if apn_1_name == '' or apn_2_name == '':
                    raise LinuxETHError(f"获取apn名称异常：{return_qgpapn}")

                return_qgpapn_1 = self.at_handler.send_at("AT+QGPAPN=1", 6)
                all_logger.info(return_qgpapn_1)
                ip_apn1 = ''.join(re.findall(r'\+QGPAPN:\s1,".*","(.*)"', return_qgpapn_1))
                ip_apn2 = ''.join(re.findall(r'\+QGPAPN:\s2,".*","(.*)"', return_qgpapn_1))
                all_logger.info(ip_apn1)
                all_logger.info(ip_apn2)
                if ip_apn1 == '' or ip_apn2 == '':
                    raise LinuxETHError(f"AT+QGPAPN=1获取IP异常：{return_qgpapn_1}")
                return_debug_value = self.get_value_debug('ifconfig -a')
                if ip_apn1 not in return_debug_value or ip_apn2 not in return_debug_value:
                    raise LinuxETHError(f"异常，AT+QGPAPN=1获取的IP: {ip_apn1}、{ip_apn2}在debug中未查询到： {return_debug_value}")
                else:
                    all_logger.info(f"已经在debug信息中找到 {ip_apn1}、{ip_apn2}")

                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
                self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
                time.sleep(60)  # disable vlan后模块可能会重启
                self.driver.check_usb_driver()
                time.sleep(3)  # 立即发AT可能会误判为AT不通
                self.exit_eth_mode(now_mode)

                enable_network_card_and_check(self.pc_ethernet_name)  # 恢复网络，传送解析log
                ifconfig_up_value = subprocess.getoutput('ifconfig {} up'.format(self.pc_ethernet_name))  # 启用本地网卡
                all_logger.info('ifconfig {} up\r\n{}'.format(self.pc_ethernet_name, ifconfig_up_value))
                self.udhcpc_get_ip(network_name=self.pc_ethernet_name)

                all_logger.info("wait 30 seconds, catch log end")
                time.sleep(30)

                # 获取Log
                log_name, log_path = m.find_log_file()
                all_logger.info(f"log_path: {log_path}")

                # Linux下获取qdb文件
                qdb_name, qdb_path = m.find_qdb_file()
                all_logger.info(f'qdb_path: {qdb_path}')

                # 发送本地Log文件
                message_types = {"LOG_PACKET": ["0xB800", "0xB0E3"]}
                interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
                                           "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
                data = log.load_log_from_remote(log_path, qdb_path, message_types, interested_return_filed)
                all_logger.info(data)

                apn_1_name_len = len(apn_1_name)
                for k in range(apn_1_name_len):
                    if f'({apn_1_name[k]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_1_name[k]}) 不在 {repr(data)} 之中')

                apn_2_name_len = len(apn_2_name)
                for j in range(apn_2_name_len):
                    if f'({apn_2_name[j]})' in repr(data):
                        all_logger.info('QXDM log正常')
                    else:
                        raise LinuxETHError(f'异常！ ({apn_2_name[j]}) 不在 {repr(data)} 之中')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 60)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 60)
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 60)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_031(self):
        """
        1.查看当前配置APN
        2.设置不同APN
        3.查看当前配置APN
        4,查询当前CFUN值
        5.切换CFUN为0
        6.再切换CFUN为1
        7.查看当前配置APN
        """
        self.set_apn(6)
        return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
        all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")
        self.at_handler.cfun0()
        time.sleep(1)
        self.at_handler.cfun1()
        self.at_handler.check_network()
        time.sleep(10)
        self.at_handler.check_network()
        return_apn_cfun = self.at_handler.send_at("AT+CGDCONT?", 3)
        all_logger.info(f"AT+CGDCONT?\r\n{return_apn_cfun}")
        if return_apn != return_apn_cfun:
            raise LinuxETHError("切换cfun01后apn发生了变化!  before:{return_apn}\r\n after:{return_apn_cfun}")

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_032(self):
        """
        1.使用AT指令查询网络状态
        2.配置好四路apn
        3.使用AT指令查询APN
        4.查询所有激活的vlan
        5.启用四路vlan（默认不用vlan ID 1,随机开启，最大为4096）
        6.查询所有激活的vlan
        7.查询当前mPDN规则
        8.配置4条mPDN规则，两路桥模式，两路路由模式
        9.查询是否配置成功
        10.查询每条规则当前的拨号状态和ippt模式激活状态
        11.加载vlan模块   //主机端
        12.重新拉起网卡并配置mac地址
        13.为eth1增加三路vlan，vlan id为2和3、4
        14.拉起三路网卡并配置mac地址
        15.查询网卡状态
        16.四路分别获取获取动态ip
        17.查询网卡状态，第一路和第二路地址为IP地址显示为公有地址，例如10.81等，第三路和第四路IP地址显示为私有地址，例如192.168等
        18.四路分别ping www.baidu.com
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            self.set_apn(3, 'apn3')
            self.set_apn(4, 'apn4')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            self.open_vlan('4')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('1,2,2,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('2,3,3,0,1')
            self.send_mpdn_rule('3,4,4,0,1')

            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('3', '3')
            self.check_mPDN_rule('4', '4')

            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('3', '3')
            self.check_MPDN_status('3', '4')

            self.four_way_dial_set(now_mode)

            self.mpdn_route_set(now_mode, 4)

            now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
            ifconfig_get_result = subprocess.getoutput(f'ifconfig')
            all_logger.info(f'ifconfig :{ifconfig_get_result}')
            if f'{now_network_card_name}.2' not in ifconfig_get_result or f'{now_network_card_name}.3' not in ifconfig_get_result or f'{now_network_card_name}.4' not in ifconfig_get_result:
                raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.3')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.4')

        finally:
            self.eth_network_card_down(now_mode)
            self.send_mpdn_rule('0')
            self.send_mpdn_rule('1')
            self.send_mpdn_rule('2')
            self.send_mpdn_rule('3')
            self.send_at_error_try_again('at+qmap="vlan",4,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_033(self):
        """
        mPDN-valn四路拨号CFUN切换网络测试
        1,查询当前CFUN值
        2.切换CFUN为0
        3.再切换CFUN为1
        4.切换CFUN为4
        5.再切换CFUN为1
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            self.set_apn(3, 'apn3')
            self.set_apn(4, 'apn4')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            self.open_vlan('4')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('1,2,2,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('2,3,3,0,1')
            self.send_mpdn_rule('3,4,4,0,1')

            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('3', '3')
            self.check_mPDN_rule('4', '4')

            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('3', '3')
            self.check_MPDN_status('3', '4')

            self.four_way_dial_set(now_mode)

            self.mpdn_route_set(now_mode, 4)
            now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
            ifconfig_get_result = subprocess.getoutput(f'ifconfig')
            all_logger.info(f'ifconfig :{ifconfig_get_result}')
            if f'{now_network_card_name}.2' not in ifconfig_get_result or f'{now_network_card_name}.3' not in ifconfig_get_result or f'{now_network_card_name}.4' not in ifconfig_get_result:
                raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.3')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.4')

            self.at_handler.cfun4()
            time.sleep(5)
            self.at_handler.cfun1()
            self.at_handler.check_network()
            time.sleep(60)
            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.3')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.4')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_mpdn_rule('0')
            self.send_mpdn_rule('1')
            self.send_mpdn_rule('2')
            self.send_mpdn_rule('3')
            self.send_at_error_try_again('at+qmap="vlan",4,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_034(self):
        """
        开启 mPDN-valn多路拨号同时四路测速，debug口查询cpu loading
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            self.set_apn(3, 'apn3')
            self.set_apn(4, 'apn4')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            self.open_vlan('4')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('1,2,2,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('2,3,3,0,1')
            self.send_mpdn_rule('3,4,4,0,1')

            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('3', '3')
            self.check_mPDN_rule('4', '4')

            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('3', '3')
            self.check_MPDN_status('3', '4')

            self.four_way_dial_set(now_mode)

            self.mpdn_route_set(now_mode, 4)
            now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
            ifconfig_get_result = subprocess.getoutput(f'ifconfig')
            all_logger.info(f'ifconfig :{ifconfig_get_result}')
            if f'{now_network_card_name}.2' not in ifconfig_get_result or f'{now_network_card_name}.3' not in ifconfig_get_result or f'{now_network_card_name}.4' not in ifconfig_get_result:
                raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.3')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.4')

            speed_test_1 = self.speedtest(
                network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
            if speed_test_1 <= 100:
                raise LinuxETHError(f"多路拨号主路速率异常！当前速率为{speed_test_1},小于期望最小值100")

            speed_test_2 = self.speedtest(
                f'{self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}.2')
            if speed_test_2 >= 160 or speed_test_2 == 0:
                raise LinuxETHError(f"多路拨号第一路速率异常！当前速率为{speed_test_2},小于期望小与160")

            speed_test_3 = self.speedtest(
                f'{self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}.3')
            if speed_test_3 >= 160 or speed_test_2 == 0:
                raise LinuxETHError(f"多路拨号第二路速率异常！当前速率为{speed_test_3},小于期望小与160")

            speed_test_4 = self.speedtest(
                f'{self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}.4')
            if speed_test_4 >= 160 or speed_test_4 == 0:
                raise LinuxETHError(f"多路拨号第三路速率异常！当前速率为{speed_test_4},小于期望小与160")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_mpdn_rule('0')
            self.send_mpdn_rule('1')
            self.send_mpdn_rule('2')
            self.send_mpdn_rule('3')
            self.send_at_error_try_again('at+qmap="vlan",4,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_035(self):
        """
        1.使用AT指令查询网络状态
        2.配置好四路apn
        3.使用AT指令查询APN
        4.查询所有激活的vlan
        5.启用四路vlan（默认不用vlan ID 1,随机开启，最大为4096）
        6.查询所有激活的vlan
        7.查询当前mPDN规则
        8.配置4条mPDN规则，两路桥模式，两路路由模式
        9.查询是否配置成功
        10.查询每条规则当前的拨号状态和ippt模式激活状态
        11.加载vlan模块   //主机端
        12.重新拉起网卡并配置mac地址
        13.为eth1增加三路vlan，vlan id为2和3、4
        14.拉起三路网卡并配置mac地址
        15.查询网卡状态
        16.四路分别获取获取动态ip
        17.查询网卡状态，第一路和第二路地址为IP地址显示为公有地址，例如10.81等，第三路和第四路IP地址显示为私有地址，例如192.168等
        18.四路分别ping www.baidu.com
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            self.set_apn(3, 'apn3')
            self.set_apn(4, 'apn4')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            self.open_vlan('4')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('1,2,2,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('2,3,3,0,1')
            self.send_mpdn_rule('3,4,4,0,1')

            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('3', '3')
            self.check_mPDN_rule('4', '4')

            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('3', '3')
            self.check_MPDN_status('3', '4')

        finally:
            self.eth_network_card_down(now_mode)
            self.send_mpdn_rule('0')
            self.send_mpdn_rule('1')
            self.send_mpdn_rule('2')
            self.send_mpdn_rule('3')
            self.send_at_error_try_again('at+qmap="vlan",4,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_036(self):
        """
        1.使用AT+QDMZ指令查询DMZ参数值
        2.使用AT+QDMZ指令查询DMZ参数值默认值
        """
        self.qdmz_attr_check()
        return_value = self.send_at_error_try_again('AT+QDMZ', 3)
        if '+QDMZ: 0,4' not in return_value or '+QDMZ: 0,6' not in return_value:
            raise LinuxETHError("AT+QDMZ默认值异常！")

    @startup_teardown()
    def test_linux_eth_common_01_038(self):
        """
        1.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        2.查询PC端本地连接IPv6地址（ipconfig）
        3.使用AT+QDMZ设置IPv6 dmz地址
        4.使用AT+QDMZ查询已设置的IPv6 dmz地址
        5.禁用QMAP拨号规则0
        """
        seq = 1
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            retunr_value = self.send_at_error_try_again('AT+QMAP="wwan"')
            all_logger.info(f'AT+QMAP="wwan": {retunr_value}')
            ipv6_adress = self.get_network_card_ipv6(now_mode).split()[0]
            if ipv6_adress:
                self.send_at_error_try_again(f'AT+QDMZ=1,6,{ipv6_adress}')
            else:
                raise LinuxETHError(f"ipv6获取异常: {ipv6_adress}")
            return_check = self.send_at_error_try_again('AT+QDMZ', 3)
            if ipv6_adress not in return_check:
                raise LinuxETHError(f"异常！AT+QDMZ=1,6,{ipv6_adress}设置ipv6后，AT+QDMZ查询失败：{return_check}")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_039(self):
        """
        1.使用AT+QDMZ指令删除DMZ设置值
        2.使用AT+QDMZ指令查询DMZ参数值
        """
        self.send_at_error_try_again('AT+QDMZ=0', 3)
        return_value = self.send_at_error_try_again('AT+QDMZ', 3)
        if '+QDMZ: 0,4' not in return_value or '+QDMZ: 0,6' not in return_value:
            raise LinuxETHError("AT+QDMZ默认值异常！")

    @startup_teardown()
    def test_linux_eth_common_01_040(self):
        """
        1.数传中模块断电重启
        2.重启后观察是否可正常连接并上网
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()
            time.sleep(10)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_041(self):
        """
        1,查询当前CFUN值
        2.切换CFUN为0
        3.再切换CFUN为1
        4.切换CFUN为4
        5.再切换CFUN为1
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            self.at_handler.cfun0()
            time.sleep(5)
            self.at_handler.cfun1()
            self.at_handler.check_network()
            time.sleep(10)
            self.ip_passthrough_connect_check(now_mode)
            self.at_handler.cfun4()
            time.sleep(5)
            self.at_handler.cfun1()
            self.at_handler.check_network()
            time.sleep(10)
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_042(self):
        """
        1.数传中拔掉SIM卡
        2.插入SIM卡注网后观察是否可成功上网
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            self.sim_det(True)  # 首先开启热拔插功能
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.check_simcard(False)
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handler.readline_keyword('PB DONE', timout=60)
            self.check_simcard(True)
            self.at_handler.check_network()
            time.sleep(10)
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.sim_det(False)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_043(self):
        """
        1.数传中来电
        """
        # 进行打电话，接短信测试
        self.at_handler.bound_network('LTE')
        t_ping = None
        exc_type = None
        exc_value = None
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)

            # 后台ping，并且拨通电话
            t_ping = PINGThread(times=150,
                                network_card_name=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
            t_ping.setDaemon(True)
            t_ping.start()
            self.hang_up_after_system_dial(10)
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if t_ping:
                t_ping.terminate()
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_045(self):
        """
        1.数传中来短信
        """
        # 进行打电话，接短信测试
        self.at_handler.bound_network('LTE')
        t_ping = None
        exc_type = None
        exc_value = None
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)

            # 后台ping，并且发送短信
            t_ping = PINGThread(times=150,
                                network_card_name=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
            t_ping.setDaemon(True)
            t_ping.start()
            self.send_msg()
        except Exception as e:
            all_logger.error(traceback.format_exc())
            all_logger.info(e)
            exc_type, exc_value, exc_tb = sys.exc_info()
        finally:
            if t_ping:
                t_ping.terminate()
            self.eth_network_card_down(now_mode)
            self.exit_eth_mode(now_mode)
            if exc_type and exc_value:
                raise exc_type(exc_value)

    @startup_teardown()
    def test_linux_eth_common_01_046(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.查询当前mPDN拨号状态
        4.观察PC端本地连接状态以及IP地址并上网
        5.禁用QMAP拨号规则0
        6.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        7.查询当前mPDN拨号状态
        8.观察PC端本地连接状态以及IP地址并上网
        9.禁用QMAP拨号规则0
        10.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        11.查询当前mPDN拨号状态
        12.观察PC端本地连接状态以及IP地址并上网
        13.禁用QMAP拨号规则0
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', seq)
            self.check_MPDN_status('0', seq)
            self.common_connect_check(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)

            self.enter_eth_mode(now_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_047(self):
        """
        1.默认状态下，AT+QMAP="wwan"查询网络IP地址
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.查询当前mPDN拨号状态
        4.使用AT+QMAP="wwan"查询网络IP地址，debug口ifconfig查询地址
        5.禁用QMAP拨号规则0
        6.使用AT+QMAP="wwan"查询网络IP地址
        """
        debug_port = DebugPort(self.debug_port, self.return_qgmr)
        debug_port.setDaemon(True)
        debug_port.start()
        time.sleep(10)
        ipv4_before = self.qmap_wwan_get_ip(4)
        ipv6_before = self.qmap_wwan_get_ip(6)
        if ipv4_before != '0.0.0.0' or ipv6_before != '0:0:0:0:0:0:0:0':
            raise LinuxETHError('拨号前IP查询异常！')
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', seq)
            self.check_MPDN_status('0', seq)
            self.common_connect_check(now_mode)
            ipv4_test = self.qmap_wwan_get_ip(4)
            ipv6_test = self.qmap_wwan_get_ip(6)
            debug_ip = debug_port.exec_command("ifconfig -a")
            all_logger.info('\ndebug_ip: {}'.format(debug_ip))
            if ipv4_test not in debug_ip or ipv6_test not in debug_ip:
                raise LinuxETHError('拨号中IP查询异常！DEBUG中没有对应IP!')
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)
            time.sleep(30)  # 避免指令ERROR
            ipv4_before = self.qmap_wwan_get_ip(4)
            ipv6_before = self.qmap_wwan_get_ip(6)
            if ipv4_before != '0.0.0.0' or ipv6_before != '0:0:0:0:0:0:0:0':
                raise LinuxETHError(f'拨结束后IP查询异常！{ipv4_before}、{ipv6_before}')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_049(self):
        """
        1.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        2.查询当前mPDN拨号状态
        3.查询PC端本地连接IPv6地址（ipconfig）
        4.使用AT+QMAP="DMZ"设置IPv6 dmz地址
        5.使用AT+QMAP="DMZ"查询已设置的IPv6 dmz地址
        6.关闭COMMON-RGMII拨号
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', seq)
            self.check_MPDN_status('0', seq)
            self.common_connect_check(now_mode)

            ipv4 = self.get_network_card_ipv4(self.eth_test_mode, www=False)
            set_dmz = self.send_at_error_try_again('AT+QDMZ=1,4,{}'.format(ipv4), 3)
            if 'OK' not in set_dmz:
                raise LinuxETHError("fail to set IPv4 DMZ")
            get_dmz = self.send_at_error_try_again('AT+QDMZ', 3)
            if '1,4,{}'.format(ipv4) not in get_dmz:
                raise LinuxETHError("fail to check DMZ after set")

            ipv6 = self.get_network_card_ipv6(self.eth_test_mode)
            if '\n' in ipv6:
                ipv6 = ipv6.split("\n")[0]
            set_dmz = self.send_at_error_try_again('AT+QDMZ=1,6,{}'.format(ipv6), 3)
            if 'OK' not in set_dmz:
                raise LinuxETHError("fail to set IPv6 DMZ")
            get_dmz = self.send_at_error_try_again('AT+QDMZ', 3)
            if '1,6,{}'.format(ipv6) not in get_dmz:
                raise LinuxETHError("fail to check DMZ after set")

            qdmz = self.send_at_error_try_again('AT+QDMZ=0', 3)
            if 'OK' not in qdmz:
                raise LinuxETHError("fail to reset DMZ USE AT+QDMZ=0")

            return_value = self.send_at_error_try_again('AT+QDMZ', 3)
            if '+QDMZ: 0,4' not in return_value or '+QDMZ: 0,6' not in return_value:
                raise LinuxETHError("AT+QDMZ默认值异常！")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_050(self):
        """
        1.使用AT+QDMZ指令删除DMZ设置值
        2.使用AT+QDMZ指令查询DMZ参数值
        """
        self.send_at_error_try_again('AT+QDMZ=0', 3)
        return_value = self.send_at_error_try_again('AT+QDMZ', 3)
        if '+QDMZ: 0,4' not in return_value or '+QDMZ: 0,6' not in return_value:
            raise LinuxETHError("AT+QDMZ默认值异常！")

    @startup_teardown()
    def test_linux_eth_common_01_052(self):
        """
        1.获取当前分配给上位机的私有地址
        2.设置正确了的私有地址
        3.获取当前分配给上位机的私有地址
        4.设置了错误的私有地址 ERROR
        5.重启
        6.拨号成功后查看上位机地址
        """
        now_mode = ''
        try:
            ip_before = self.qmap_lan_get_ip()
            if ip_before:
                raise LinuxETHError("异常，默认IP不为空")
            return_set_ip = self.send_at_error_try_again('AT+QMAP="lan",192.168.225.100')
            if "OK" not in return_set_ip:
                raise LinuxETHError(f'AT+QMAP="lan"设置IP异常！：{return_set_ip}')
            ip_test = self.qmap_lan_get_ip().split()[0]
            if ip_test != '192.168.225.100':
                raise LinuxETHError(f"查询所获得IP与设置的不一致！:{ip_test}")
            return_set_ip_error = self.at_handler.send_at('AT+QMAP="lan",192.168.220.88')
            if "ERROR" not in return_set_ip_error:
                raise LinuxETHError(f'AT+QMAP="lan"设置错误的IP异常，没有出现预期报错现象！：{return_set_ip_error}')
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()

            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            ip_common = self.get_network_card_ipv4(now_mode)
            if ip_common != ip_test:
                raise LinuxETHError(f"异常！设置的IP: {ip_test} 和 拨号后获得的IP: {ip_common} 不一致！")
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="LANIP",192.168.225.40,192.168.225.60,192.168.225.1,1', 6)  # 恢复lan默认值
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_053(self):
        """
        1.查询当前lan口地址池配置
        2.修改LAN口地址池配置，立即生效
        3.查询当前lan口地址池配置
        4.修改LAN口地址池配置，重启生效
        5.无
        6.查询当前lan口地址池配置
        """
        try:
            lan_duhcpc_ip_before = self.send_at_error_try_again('AT+QMAP="LANIP"')
            if '192.168.225.40,192.168.225.60,192.168.225.1' not in lan_duhcpc_ip_before:
                raise LinuxETHError(f"默认LAN接口DHCP地址池配置异常!{lan_duhcpc_ip_before}")
            debug_ip_before = self.get_value_debug('ifconfig -a')
            if '192.168.225.1' not in debug_ip_before:
                raise LinuxETHError(f"默认地址池的网关地址debug口查询异常!{debug_ip_before}")

            return_lan_duhcpc_ip_set = self.send_at_error_try_again(
                'AT+QMAP="LANIP",192.168.111.20,192.168.111.60,192.168.111.1,1', 6)
            if "OK" not in return_lan_duhcpc_ip_set:
                raise LinuxETHError(
                    f'AT+QMAP="LANIP",192.168.111.20,192.168.111.60,192.168.111.1,1设置异常！：{return_lan_duhcpc_ip_set}')
            lan_duhcpc_ip_set = self.send_at_error_try_again('AT+QMAP="LANIP"')
            if '192.168.111.20,192.168.111.60,192.168.111.1' not in lan_duhcpc_ip_set:
                raise LinuxETHError(f"配置LAN接口DHCP地址池配置异常!{lan_duhcpc_ip_set}")
            debug_ip_set = self.get_value_debug('ifconfig -a')
            if '192.168.111.1' not in debug_ip_set:
                raise LinuxETHError(f"设置地址池的网关地址debug口查询异常!{debug_ip_set}")

            return_lan_duhcpc_ip_after = self.send_at_error_try_again(
                'AT+QMAP="LANIP",192.168.225.40,192.168.225.60,192.168.225.1,0', 6)
            if "OK" not in return_lan_duhcpc_ip_after:
                raise LinuxETHError(
                    f'AT+QMAP="LANIP",192.168.225.40,192.168.225.60,192.168.225.1,0设置异常！：{return_lan_duhcpc_ip_after}')
            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()
            time.sleep(10)
            lan_duhcpc_ip_after = self.send_at_error_try_again('AT+QMAP="LANIP"')
            if '192.168.225.40,192.168.225.60,192.168.225.1' not in lan_duhcpc_ip_after:
                raise LinuxETHError(f"配置LAN接口DHCP地址池配置异常!{lan_duhcpc_ip_after}")
            debug_ip_after = self.get_value_debug('ifconfig -a')
            if '192.168.225.1' not in debug_ip_after:
                raise LinuxETHError(f"设置地址池的网关地址debug口查询异常!{debug_ip_after}")
        finally:
            self.send_at_error_try_again('AT+QMAP="LANIP",192.168.225.40,192.168.225.60,192.168.225.1,1', 6)  # 恢复lan默认值

    @startup_teardown()
    def test_linux_eth_common_01_054(self):
        """
        1.查询LAN接口DHCP MAC地址绑定信息
        2.设置绑定，绑定后分配给网卡的IP地址总是我们绑定的
        3.查询LAN接口DHCP MAC地址绑定信息
        4.重启模块
        5.查询LAN接口DHCP MAC地址绑定信息
        6.删除第一配置项
        7.查询LAN接口DHCP MAC地址绑定信息
        8.重启模块
        9.查询LAN接口DHCP MAC地址绑定信息
        """
        try:
            mac_bind_before = self.send_at_error_try_again('AT+QMAP="MAC_bind"', 3)
            if '+QMAP: "MAC_bind",' in mac_bind_before:
                raise LinuxETHError(f"默认LAN接口DHCP MAC地址绑定信息异常!{mac_bind_before}")

            return_mac_bind_set = self.send_at_error_try_again('AT+QMAP="MAC_bind",1,"01:23:45:67:89:AB","192.168.1.120"', 6)
            if "OK" not in return_mac_bind_set:
                raise LinuxETHError(
                    f'AT+QMAP="MAC_bind",1,"01:23:45:67:89:AB","192.168.1.120"设置异常！：{return_mac_bind_set}')
            mac_bind_set = self.send_at_error_try_again('AT+QMAP="MAC_bind"')
            if '+QMAP: "MAC_bind",1,"01:23:45:67:89:AB","192.168.1.120"' not in mac_bind_set:
                raise LinuxETHError(f"配置LAN接口DHCP MAC地址绑定信息异常!{mac_bind_set}")

            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()
            time.sleep(10)
            mac_bind_set_reboot = self.send_at_error_try_again('AT+QMAP="MAC_bind"')
            if '+QMAP: "MAC_bind",1,"01:23:45:67:89:AB","192.168.1.120"' not in mac_bind_set_reboot:
                raise LinuxETHError(f"配置LAN接口DHCP MAC地址绑定信息重启后异常!{mac_bind_set_reboot}")

            # AT+QMAP="MAC_bind",1,"",""
            return_mac_bind_del = self.send_at_error_try_again('AT+QMAP="MAC_bind",1,"",""', 6)
            if "OK" not in return_mac_bind_del:
                raise LinuxETHError(f'AT+QMAP="MAC_bind",1,"",""删除配置异常！：{return_mac_bind_del}')
            mac_bind_del = self.send_at_error_try_again('AT+QMAP="MAC_bind"')
            if '+QMAP: "MAC_bind",' in mac_bind_del:
                raise LinuxETHError(f"删除配置后LAN接口DHCP MAC地址绑定信息异常!{mac_bind_del}")

            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()
            time.sleep(10)
            mac_bind_del_reboot = self.send_at_error_try_again('AT+QMAP="MAC_bind"')
            if '+QMAP: "MAC_bind",' in mac_bind_del_reboot:
                raise LinuxETHError(f"删除配置后LAN接口DHCP MAC地址绑定信息后重启异常!{mac_bind_del_reboot}")

        finally:
            self.send_at_error_try_again('AT+QMAP="MAC_bind",1,"",""', 6)  # 恢复默认值

    @startup_teardown()
    def test_linux_eth_common_01_055(self):  # todo 多路拨号
        """
        1.查询当前是否启用NAT功能
        2.PC端查询网卡状态
        3.禁用NAT功能
        4.PC端查询网卡状态
        5.启用NAT功能
        6.PC端查询网卡状态
        """
        try:
            ipp_nat_before = self.at_handler.send_at('AT+QMAP="IPPT_NAT"', 3)
            if '+QMAP: "IPPT_NAT",1' not in ipp_nat_before:
                raise LinuxETHError(f"查询默认是否启用NAT功能异常!{ipp_nat_before}")

            return_ipp_nat_set = self.at_handler.send_at('AT+QMAP="IPPT_NAT",0', 6)
            if "OK" not in return_ipp_nat_set:
                raise LinuxETHError(f'AT+QMAP="IPPT_NAT",0设置异常！：{return_ipp_nat_set}')

            ipp_nat_set = self.at_handler.send_at('AT+QMAP="IPPT_NAT"')
            if '+QMAP: "IPPT_NAT",0' not in ipp_nat_set:
                raise LinuxETHError(f"配置NAT功能后查询信息异常!{ipp_nat_set}")
        finally:
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)

    @startup_teardown()
    def test_linux_eth_common_01_056(self):
        """
        1.AT+QMAP="SFE"  查询SFE软件加速功能状态
        2.启用SFE软件加速功能
        3.查询SFE软件加速功能状态
        4.debug口查询sfe的驱动
        """
        try:
            sfe_before = self.at_handler.send_at('AT+QMAP="sfe"', 3)
            if 'disable' not in sfe_before:
                raise LinuxETHError(f"查询默认SFE软件加速功能状态异常!{sfe_before}")

            return_sfe_enable = self.at_handler.send_at('AT+QMAP="sfe","enable"', 16)
            if "OK" not in return_sfe_enable:
                raise LinuxETHError(f'AT+QMAP="sfe","enable"设置异常！：{return_sfe_enable}')
            return_sfe = self.at_handler.send_at('AT+QMAP="sfe"')
            if 'enable' not in return_sfe:
                raise LinuxETHError(f"配置sfe功能后查询信息异常!{return_sfe}")

            # shortcut_fe
            debug_sfe_value = self.get_value_debug('lsmod|grep shortcut*')
            if 'shortcut_fe' not in debug_sfe_value:
                raise LinuxETHError(f"启用SFE软件加速功能后debug查询异常！{debug_sfe_value}")
        finally:
            self.at_handler.send_at('AT+QMAP="sfe","disable"', 16)

    @startup_teardown()
    def test_linux_eth_common_01_057(self):
        """
        1.配置1条mPDN规则,<auto_connect>=0
        2.规则0开始拨号
        3.查询QMAP拨号状态
        4.规则0断开拨号
        5.查询QMAP拨号状态
        6.删除规则0
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,0', 3)
            # AT+QMAP="connect",0,1
            return_connect = self.at_handler.send_at('AT+QMAP="connect",0,1', 6)
            if "OK" not in return_connect:
                raise LinuxETHError(f'AT+QMAP="connect",0,1设置异常！：{return_connect}')
            self.check_MPDN_status('0', '1')
            return_disconnect = self.at_handler.send_at('AT+QMAP="connect",0,0', 6)
            if "OK" not in return_disconnect:
                raise LinuxETHError(f'AT+QMAP="connect",0,0设置异常！：{return_disconnect}')
            return_value_dis = self.at_handler.send_at('AT+QMAP="MPDN_status"', 3)
            if '+QMAP: "MPDN_status",0,1,0,0' not in return_value_dis:
                raise LinuxETHError(f'AT+QMAP="connect",0,0断开拨号后异常{return_value_dis}')
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_058(self):
        """
        1.查询QMAP拨号自动拨号配置
        2.配置3条mPDN规则
        3.查询QMAP拨号自动拨号配置
        4.禁用QMAP拨号规则1自动拨号
        5.查询QMAP拨号自动拨号配置
        6.查询每条规则当前的拨号状态
        7.设置QMAP拨号规则2自动拨号并修改<profileID>为4
        8.查询每条规则当前的拨号状态
        9.删除3条mPDN规则
        AT+QMAP="auto_connect"
        +QMAP: "auto_connect",0,0
        +QMAP: "auto_connect",1,0
        +QMAP: "auto_connect",2,0
        +QMAP: "auto_connect",3,0

        OK
        """
        try:
            auto_connet_before = self.send_at_error_try_again('AT+QMAP="auto_connect"', 6)
            if '"auto_connect",0,0' not in auto_connet_before or '"auto_connect",1,0' not in auto_connet_before or '"auto_connect",2,0' not in auto_connet_before or '"auto_connect",3,0' not in auto_connet_before:
                raise LinuxETHError(f"查询默认自动拨号配置异常!{auto_connet_before}")

            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 6)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1,2,0,0,1', 6)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",2,3,0,0,1', 6)
            auto_connet_set = self.send_at_error_try_again('AT+QMAP="auto_connect"', 6)
            if '"auto_connect",0,1' not in auto_connet_set or '"auto_connect",1,1' not in auto_connet_set or '"auto_connect",2,1' not in auto_connet_set:
                raise LinuxETHError(f"设置自动拨号配置异常!{auto_connet_set}")

            self.send_at_error_try_again('AT+QMAP="auto_connect",1,0', 6)
            auto_connet_set_result = self.send_at_error_try_again('AT+QMAP="auto_connect"', 6)
            if '"auto_connect",1,0' not in auto_connet_set_result:
                raise LinuxETHError(f"关闭1自动拨号异常!{auto_connet_set_result}")

            rule_status = self.at_handler.send_at('At+qmap="mPDN_rule"', 6)
            if '+QMAP: "MPDN_rule",0,1,0,0,1' not in rule_status or '+QMAP: "MPDN_rule",1,2,0,0,0' not in rule_status or '+QMAP: "MPDN_rule",2,3,0,0,1' not in rule_status:
                raise LinuxETHError(f"设置自动拨号后拨号状态异常!{rule_status}")

            self.send_at_error_try_again('AT+QMAP="auto_connect",2,1,4', 6)
            auto_connet_set_result2 = self.send_at_error_try_again('At+qmap="mPDN_rule"', 6)
            if '+QMAP: "MPDN_rule",0,1,0,0,1' not in auto_connet_set_result2 or '+QMAP: "MPDN_rule",1,2,0,0,0' not in auto_connet_set_result2 or '+QMAP: "MPDN_rule",2,4,0,0,1' not in auto_connet_set_result2:
                raise LinuxETHError(f'AT+QMAP="auto_connect",2,1,4设置自动拨号后查询异常!{auto_connet_set_result2}')
        finally:
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",1', 6)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",2', 6)

    @startup_teardown()
    def test_linux_eth_common_01_059(self):
        """
        1.查询模块内LAN/VLAN接口的网关域名
        2.更改网关域名为quectel.com
        3.查询模块内LAN/VLAN接口的网关域名
        4.PC端ping quectel.com
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            domain_before = self.at_handler.send_at('AT+QMAP="domain"', 6)
            if 'mobileap.qualcomm.com' not in domain_before:
                raise LinuxETHError(f"查询模块内LAN/VLAN接口的网关域名异常!{domain_before}")

            self.at_handler.send_at('AT+QMAP="domain","quectel.com"', 6)

            time.sleep(3)
            all_logger.info("开始ping quectel.com")
            ip = LinuxAPI.get_ip_address(
                self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name, ipv6_flag=False)
            try:
                ping_data = ping('quectel.com', count=20, interval=1, source=ip)
                all_logger.info(
                    f'ping {ping_data.address}地址情况如下:发包数:{ping_data.packets_sent},收包数:{ping_data.packets_received},丢包率:{ping_data.packet_loss}')
                if ping_data.is_alive:
                    all_logger.info('ping检查正常')
                    return True
            except Exception as e:
                all_logger.info(e)
                all_logger.info('ping地址quectel.com失败')
                LinuxETHError('ping地址quectel.com失败')
        finally:
            self.eth_network_card_down(now_mode)
            self.exit_eth_mode(now_mode)
            self.at_handler.send_at('AT+QMAP="domain","mobileap.qualcomm.com"', 6)

    @startup_teardown()
    def test_linux_eth_common_01_060(self):  # 只能在windows测试，暂不实现
        """
        1.查询QMAP拨号的IPv6 DNS代理功能
        2.启用IPv6 DNS代理功能
        3.模组重启
        4.查询IPv6 DNS代理功能状态
        5.更改网关域名为240c::6666
        6.查询模块内LAN/VLAN接口的网关域名
        7.ping v6地址
        8.禁用IPv6 DNS代理功能
        9.查询IPv6 DNS代理功能状态
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            dhcpv6dns_before = self.send_at_error_try_again('at+qmap="dhcpv6dns"', 6)
            if 'disable' not in dhcpv6dns_before:
                raise LinuxETHError(f"查询默认QMAP拨号的IPv6 DNS代理功能状态异常!{dhcpv6dns_before}")

            return_dhcpv6dns_enable = self.send_at_error_try_again('at+qmap="dhcpv6dns","enable"', 6)
            if "OK" not in return_dhcpv6dns_enable:
                raise LinuxETHError(f'at+qmap="dhcpv6dns","enable"设置异常！：{return_dhcpv6dns_enable}')

            self.at_handler.cfun1_1()
            self.driver.check_usb_driver_dis()
            self.driver.check_usb_driver()
            time.sleep(10)  # 立即发AT可能会误判为AT不通
            self.at_handler.check_network()
            time.sleep(10)

            dhcpv6dns_test = self.send_at_error_try_again('at+qmap="dhcpv6dns"', 6)
            if 'enable' not in dhcpv6dns_test:
                raise LinuxETHError(f"设置QMAP拨号的IPv6 DNS代理enable重启后查询状态异常!{dhcpv6dns_test}")

            self.at_handler.send_at('AT+QMAP="domain","240c::6666"', 6)
            return_domain_v6 = self.send_at_error_try_again('AT+QMAP="domain"', 6)
            if '240c::6666' not in return_domain_v6:
                raise LinuxETHError(f"设置IPv6后查询状态异常!{return_domain_v6}")
        finally:
            self.eth_network_card_down(now_mode)
            self.exit_eth_mode(now_mode)
            self.send_at_error_try_again('at+qmap="dhcpv6dns","disable"', 6)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_061(self):
        """
        1.模块注册NSA网络
        2.配置并启用COMMON拨号规则0，使用vlan0和第一路APN
        3.指定带宽30M通过Iperf灌包速率测试5min
        4.禁用规则0
        """
        self.at_handler.bound_network('NSA')
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
            self.check_mPDN_rule('0', '1')
            self.check_MPDN_status('0', '1')
            self.common_connect_check(now_mode)
            all_logger.info("开始30M灌包速率测试5min")
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_062(self):
        """
        1.使用AT+QDMZ指令删除DMZ设置值
        2.使用AT+QDMZ指令查询DMZ参数值
        """
        self.at_handler.bound_network('NSA')
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            all_logger.info("开始30M灌包速率测试5min")
            iperf(bandwidth='30M', times=300, mode=1)
        finally:
            self.eth_network_card_down(now_mode)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_063(self):
        """
        在不插Simcard的情况拨号测试
        1.使用AT+QETH="rgmii"启用以太网IPPassthrough-RGMII功能并使用默认APN进行拨号
        """
        seq = 1
        now_mode = ''
        # noinspection PyBroadException
        try:
            self.sim_det(True)  # 首先开启热拔插功能
            self.gpio.set_sim1_det_low_level()  # 拉低sim1_det引脚使其掉卡
            self.check_simcard(False)
            now_mode = self.enter_eth_mode(self.eth_test_mode)
            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        except Exception:
            msg = traceback.format_exc()
            all_logger.info("拨号失败信息msg: {}".format(msg))
            if '失败' in msg or '异常' in msg:
                all_logger.info("和预期一致，拨号失败")
            else:
                raise LinuxETHError("异常！无卡状态下拨号异常！")
        finally:
            self.eth_network_card_down(now_mode)
            self.gpio.set_sim1_det_high_level()  # 恢复sim1_det引脚使SIM卡检测正常
            self.at_handler.readline_keyword('PB DONE', timout=60)
            self.check_simcard(True)
            self.at_handler.check_network()
            time.sleep(10)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.sim_det(False)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_067(self):
        """
        1.查询当前是否启用NAT功能
        2.禁用NAT功能
        3.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN，-使用的MAC地址为对应LAN设备的IP地址
        4.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        6.启用NAT功能
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.check_ipp_ant_default_and_set()

            self.ipptmac_set_check(now_mode)
            pc_ethernet_orig_mac = subprocess.getoutput(
                'ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(
                    self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name))
            self.at_handler.send_at(f'AT+qmap="mpdn_rule",0,1,0,1,1,"{pc_ethernet_orig_mac}"', 6)
            self.check_mPDN_rule('0', '1', pc_ethernet_orig_mac)
            self.check_MPDN_status('0', '1', pc_ethernet_orig_mac)
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            time.sleep(10)  # 避免太快返回error
            # self.at_handler.send_at('AT+QETH="ipptmac","FF:FF:FF:FF:FF:FF"', 6)
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
            self.send_ipptmac("FF:FF:FF:FF:FF:FF")
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_068(self):
        """
        1.查询当前是否启用NAT功能
        2.禁用NAT功能
        3.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        4.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        6.启用NAT功能
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.check_ipp_ant_default_and_set()

            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
            self.send_ipptmac("FF:FF:FF:FF:FF:FF")
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_01_069(self):
        """
        1.查询当前是否启用NAT功能
        2.禁用NAT功能
        3.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN，-使用的MAC地址为非对应LAN设备的IP地址
        4.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        5.禁用QMAP拨号规则0
        6.启用NAT功能
        """
        self.at_handler.bound_5G_network()
        now_mode = ''
        # noinspection PyBroadException
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.check_ipp_ant_default_and_set()

            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"8C:EC:4B:A4:F2:7B"', 3)
            self.check_mPDN_rule('0', '1', "8C:EC:4B:A4:F2:7B")
            self.check_MPDN_status('0', '1', "8C:EC:4B:A4:F2:7B")

            self.get_network_card_ipv4(now_mode, www=True)
        except Exception:
            msg = traceback.format_exc()
            all_logger.info("失败信息msg: {}".format(msg))
            if '异常' in msg or '未获取到' in msg:
                all_logger.info("和预期一致，获取不到IP")
            else:
                raise LinuxETHError("异常！获取IP异常！")
        finally:
            self.eth_network_card_down(now_mode)
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_071(self):
        """
        1.查询当前是否启用NAT功能
        2.禁用NAT功能
        3.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        4.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        5.重启模组，检查注网是否正常
        6.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        7.重复5-6步骤10次
        8.禁用QMAP拨号规则0
        9.启用NAT功能
        """
        for i in range(10):
            all_logger.info(f"***************开始第{i + 1}次重启拨号测试***************")
            seq = 1
            self.set_apn(seq)
            now_mode = ''
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                self.check_ipp_ant_default_and_set()

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)  # 立即发AT可能会ERROR
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_01_072(self):
        """
        1.查询当前是否启用NAT功能
        2.禁用NAT功能
        3.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        4.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        5.CFUN切换
        6.查询默认IPPassthrough拨号状态，PC端本地连接状态以及IP地址
        7.禁用QMAP拨号规则0
        8.启用NAT功能
        """
        seq = 1
        self.set_apn(seq)
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.check_ipp_ant_default_and_set()

            self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
            self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
            self.ip_passthrough_connect_check(now_mode)
            self.at_handler.cfun0()
            time.sleep(5)
            self.at_handler.cfun1()
            self.at_handler.check_network()
            time.sleep(10)
            self.ip_passthrough_connect_check(now_mode)
            self.at_handler.cfun4()
            time.sleep(5)
            self.at_handler.cfun1()
            self.at_handler.check_network()
            time.sleep(10)
            self.ip_passthrough_connect_check(now_mode)
        finally:
            self.eth_network_card_down(now_mode)
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
            self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            self.exit_eth_mode(now_mode)

    @startup_teardown(startup=['store_default_apn'],
                      teardown=['restore_default_apn'])
    def test_linux_eth_common_01_074(self):
        """
        1.使用AT指令查询网络状态
        2.配置好四路apn
        3.使用AT指令查询APN
        4.查询所有激活的vlan
        5.启用四路vlan（默认不用vlan ID 1,随机开启，最大为4096）
        6.查询所有激活的vlan
        7.查询当前mPDN规则
        8.配置4条mPDN规则，两路桥模式，两路路由模式
        9.查询是否配置成功
        10.查询每条规则当前的拨号状态和ippt模式激活状态
        11.加载vlan模块   //主机端
        12.重新拉起网卡并配置mac地址
        13.为eth1增加三路vlan，vlan id为2和3、4
        14.拉起三路网卡并配置mac地址
        15.查询网卡状态
        16.四路分别获取获取动态ip
        17.查询网卡状态，第一路和第二路地址为IP地址显示为公有地址，例如10.81等，第三路和第四路IP地址显示为私有地址，例如192.168等
        18.四路分别ping www.baidu.com
        """
        now_mode = ''
        try:
            now_mode = self.enter_eth_mode(self.eth_test_mode)

            self.check_ipp_ant_default_and_set()

            self.at_handler.check_network()
            self.set_apn(2, 'apn2')
            self.set_apn(3, 'apn3')
            self.set_apn(4, 'apn4')
            return_apn = self.at_handler.send_at("AT+CGDCONT?", 3)
            all_logger.info(f"AT+CGDCONT?\r\n{return_apn}")

            return_vlan_default = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_default}')
            self.open_vlan('2')
            self.open_vlan('3')
            self.open_vlan('4')
            return_vlan_all = self.send_at_error_try_again('at+qmap="vlan"', 3)
            all_logger.info(f'at+qmap="vlan": \r\n{return_vlan_all}')
            return_default_value = self.send_at_error_try_again('AT+qmap="mpdn_rule"', 6)
            if '0,0,0,0,0' not in return_default_value or '1,0,0,0,0' not in return_default_value or '2,0,0,0,0' not in return_default_value or '3,0,0,0,0' not in return_default_value:
                raise LinuxETHError("mpdn rule检查异常！{return_default_value}")
            self.send_mpdn_rule('0,1,0,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('1,2,2,1,1,"FF:FF:FF:FF:FF:FF"')
            self.send_mpdn_rule('2,3,3,0,1')
            self.send_mpdn_rule('3,4,4,0,1')

            self.check_mPDN_rule('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_mPDN_rule('3', '3')
            self.check_mPDN_rule('4', '4')

            self.check_MPDN_status('0', '1', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('2', '2', "FF:FF:FF:FF:FF:FF")
            self.check_MPDN_status('3', '3')
            self.check_MPDN_status('3', '4')

            self.four_way_dial_set(now_mode)

            self.mpdn_route_set(now_mode, 4)

            now_network_card_name = self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name
            ifconfig_get_result = subprocess.getoutput(f'ifconfig')
            all_logger.info(f'ifconfig :{ifconfig_get_result}')
            if f'{now_network_card_name}.2' not in ifconfig_get_result or f'{now_network_card_name}.3' not in ifconfig_get_result or f'{now_network_card_name}.4' not in ifconfig_get_result:
                raise LinuxETHError("网卡状态异常：{ifconfig_all_result}")

            self.linux_api.ping_get_connect_status(network_card_name=now_network_card_name)
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.2')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.3')
            self.linux_api.ping_get_connect_status(network_card_name=f'{now_network_card_name}.4')

        finally:
            self.eth_network_card_down(now_mode)
            self.at_handler.send_at('AT+QMAP="IPPT_NAT",1', 6)
            self.send_mpdn_rule('0')
            self.send_mpdn_rule('1')
            self.send_mpdn_rule('2')
            self.send_mpdn_rule('3')
            self.send_at_error_try_again('at+qmap="vlan",4,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",3,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.send_at_error_try_again('at+qmap="vlan",2,"disable"', 6)
            time.sleep(60)  # disable vlan后模块可能会重启
            self.driver.check_usb_driver()
            time.sleep(3)  # 立即发AT可能会误判为AT不通
            self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_02_001(self):
        """
        1.模块注册SA网络
        2.指定带宽30M通过Iperf灌包速率测试5min
        3.关闭COMMONII拨号
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            self.at_handler.bound_network('SA')
            try:
                self.enter_eth_mode(now_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
                self.check_mPDN_rule('0', '1')
                self.check_MPDN_status('0', '1')
                self.common_connect_check(now_mode)
                all_logger.info("开始30M灌包速率测试5min")
                iperf(bandwidth='30M', times=300, mode=1)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_002(self):
        """
        1.使用AT指令查询网络状态
        2.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        3.查询当前mPDN拨号状态
        4.观察PC端本地连接状态以及IP地址并上网
        5.禁用QMAP拨号规则0
        6.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        7.查询当前mPDN拨号状态
        8.观察PC端本地连接状态以及IP地址并上网
        9.禁用QMAP拨号规则0
        10.配置并启用IPPassthrough拨号规则0，使用vlan0和第一路APN
        11.查询当前mPDN拨号状态
        12.观察PC端本地连接状态以及IP地址并上网
        13.禁用QMAP拨号规则0
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_003(self):
        """
        1.数传中在PC中禁用本地网卡
        2.启用本地网卡后观察是否可正常连接并上网
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                self.restart_eth_network_card(now_mode)
                time.sleep(10)
                self.ip_passthrough_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_007(self):
        """
        1.使用AT指令查询RGMII自动协商默认值是否为on（启用状态）
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            return_value = self.at_handler.send_at('AT+QETH="an"')
            if 'on' not in return_value:
                raise LinuxETHError(f'AT+QETH="an"默认值异常：{return_value}')

    @startup_teardown()
    def test_linux_eth_common_02_008(self):
        """
        1.使用AT指令查询RGMII速度默认值是否为0M（以太网速率自适应）
        2.查询PC端自适应速率
        3.通过测速网测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)

                return_value = self.at_handler.send_at('AT+QETH="speed"')
                if '+QETH: "speed","0M"' not in return_value:
                    raise LinuxETHError(f'速度默认值异常：{return_value}')
                # Speed: 1000Mb/s
                return_ethtool = subprocess.getoutput(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}')
                all_logger.info(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}: {return_ethtool}')
                if 'Speed: 1000Mb/s' not in return_ethtool:
                    raise LinuxETHError("查询PC端自适应速率异常")
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test <= 100:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},小于期望最小值100")
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_009(self):
        """
        使用Linux PC执行，使用支持2.5V EVB进行测试，PC端速度设置为1.0Gbps（ ethtool -s eth0 speed 1000）
        1.重启模块后查询PC端速率
        ethtool eth0(网卡名）
        2.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000: {return_ethtool_before}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                return_ethtool = subprocess.getoutput(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}')
                all_logger.info(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}: {return_ethtool}')
                if 'Speed: 1000Mb/s' not in return_ethtool:
                    raise LinuxETHError("查询PC端自适应速率异常")

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test <= 100:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},小于期望最小值100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_010(self):
        """
        1.PC端速度设置为100Mbps全双工
        2.使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）
        3.重启模块后查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        4.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full: {return_ethtool_before}')

                return_value = self.at_handler.send_at('AT+QETH="dm"')
                if '+QETH: "dm","full"' not in return_value:
                    raise LinuxETHError(f'使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 100 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值0~100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_011(self):
        """
        1.PC端速度设置为10Mbps全双工
        2.使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）
        3.重启模块后查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        4.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full: {return_ethtool_before}')

                return_value = self.at_handler.send_at('AT+QETH="dm"')
                if '+QETH: "dm","full"' not in return_value:
                    raise LinuxETHError(f'使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 20 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值0~10")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_012(self):
        """
        1.使用AT指令设置RGMII自动协商值为off（禁用状态）
        2.使用AT指令查询RGMII速度值
        3.重新进行RGMII拨号
        4.查询PC端速率是否为1.0Gbps
        5.通过speedtest测试速率
        6.断开RGMII拨号连接
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                return_value = self.at_handler.send_at('AT+QETH="an","off"')
                if 'OK' not in return_value:
                    raise LinuxETHError(f'AT+QETH="an","off"异常：{return_value}')

                return_value_speed = self.at_handler.send_at('AT+QETH="speed"')
                if '+QETH: "speed","1000M"' not in return_value_speed:
                    raise LinuxETHError(f'速度默认值异常：{return_value_speed}')

                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_before}')

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 100 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值<100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                # AT+QETH="an","off"
                self.at_handler.send_at('AT+QETH="an","on"', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_013(self):
        """
        1.使用AT指令设置RGMII速度为100M
        2.重启模块后再次使用AT指令查询RGMII速度值是否为100M
        3.重新进行RGMII拨号
        4.查询PC端速率，设置PC端速率关闭ubuntu侧网络自协商
        5.观察PC端本地连接状态并上网，通过speedtest测试速率
        6.断开RGMII拨号连接
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                return_value = self.at_handler.send_at('AT+QETH="speed" ,"100M"')
                if 'OK' not in return_value:
                    raise LinuxETHError(f'AT+QETH="speed" ,"100M"异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                return_value_speed = self.at_handler.send_at('AT+QETH="speed"')
                if '+QETH: "speed","100M"' not in return_value_speed:
                    raise LinuxETHError(f'速度值异常：{return_value_speed}')

                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full autoneg off ')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full autoneg off : {return_ethtool_before}')

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test < 100:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值>100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_on = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full autoneg on ')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full autoneg on : {return_ethtool_on}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_02_014(self):
        """
        1.使用AT指令设置RGMII速度为10M
        2.重启模块后再次使用AT指令查询RGMII速度值是否为10M
        3.重新进行RGMII拨号
        4.查询PC端速率  ubuntu侧网络自协商关闭
        5.观察PC端本地连接状态并上网，通过speedtest测试速率
        6.断开RGMII拨号连接
        7.使用AT指令恢复默认RGMII速度为0M
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            seq = 1
            try:
                return_value = self.at_handler.send_at('AT+QETH="speed" ,"10M"')
                if 'OK' not in return_value:
                    raise LinuxETHError(f'AT+QETH="speed" ,"10M"异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                return_value_speed = self.at_handler.send_at('AT+QETH="speed"')
                if '+QETH: "speed","10M"' not in return_value_speed:
                    raise LinuxETHError(f'速度值异常：{return_value_speed}')

                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full ')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full : {return_ethtool_before}')

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 10:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值<10")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['reset_usbnet_0'])
    def test_linux_eth_common_02_015(self):
        """
        1.查询RGMII状态
        2.使用第一路APN进行RGMII拨号（使用ECM拨号的APN进行RGMII拨号，随机使用）
        3.使用第二路APN进行RGMII拨号
        4.debug口查询拨号状态
        5.上位机查询模块拨号状态，并判断电脑能否上网
        6.断开第二路连接
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '1' or self.eth_test_mode == '2':
            now_mode = '2'
        else:
            all_logger.info("当前设备没有RGMII8035、RGMII8211，跳过")
        if now_mode:
            try:
                self.at_handler.send_at('AT+QCFG="USBNET",1', timeout=3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_urc()
                all_logger.info('wait 10 seconds')
                time.sleep(10)  # 停一会再发指令，否则会返回ERROR
                self.at_handler.check_network()
                self.check_ecm_driver()
                self.linux_api.ping_get_connect_status(network_card_name='usb0')
                seq = 1
                self.set_apn(seq)

                self.enter_eth_mode(now_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_03_001(self):
        """
        1.AT+QMAPWAC=?查询结果与ATC文档一致
        2.AT+QMAPWAC?指令查询默认拨号状态
        """
        if self.eth_test_mode != '2':
            self.qmapwac_default_check()
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")

    @startup_teardown()
    def test_linux_eth_common_03_002(self):
        """
        1、开启ECM
        2、关闭自动拨号
        3、重启模块
        4、检查自动拨号是否为关闭状态
        """
        if self.Is_OCPU_version:
            if self.eth_test_mode == '0' or self.eth_test_mode == '3' or self.eth_test_mode == '1' or self.eth_test_mode == '4':
                try:
                    self.at_handler.send_at('AT+QCFG="USBNET",1', 3)
                    self.at_handler.send_at('AT+QMAPWAC=0', 3)
                    self.at_handler.cfun1_1()
                    self.driver.check_usb_driver_dis()
                    self.driver.check_usb_driver()
                    time.sleep(10)  # 立即发AT可能会误判为AT不通
                    self.at_handler.check_network()
                    time.sleep(20)
                    return_value = self.at_handler.send_at('AT+QMAPWAC?', 3)
                    if '+QMAPWAC: 0' not in return_value:
                        raise LinuxETHError(f'设置AT+QMAPWAC=0后重启查询异常：{return_value}')
                finally:
                    self.at_handler.send_at('AT+QCFG="USBNET",0', 6)
            else:
                all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")
        else:
            all_logger.info("当前非OCPU版本，跳过")

    @startup_teardown()
    def test_linux_eth_common_03_003(self):
        """
        1.将RTL8125小板固定在5G EVB板子上的WIFI-TE-A处，5GEVB的usb口及debug口连接PC1，拨动5GEVB上的PCIE_SEL1和PCIE_SEL2至HIGH，从RTL8125phy网口连接网线至PC2。
        2.配置pcie RC模式
        3.选择 RTL8125 网卡驱动并使能
        4.开启自动拨号
        5.重启模块，并在debug口输入lspci查询驱动是否加载成功.查询模块内部ip地址
        6.PC2输入ipconfig 查询ip地址，并浏览网页或ping www.baidu.com和ping -6 240c::6666
        7.关闭自动拨号
        8.重启模块，浏览网页或ping www.baidu.com
        """
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            try:
                self.enter_eth_mode('3')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('3')
            finally:
                self.eth_network_card_down('3')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('3')

        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            try:
                self.enter_eth_mode('4')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('4')
            finally:
                self.eth_network_card_down('4')
                self.exit_eth_mode('4')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('4')

        elif self.eth_test_mode == '5':
            try:
                self.enter_eth_mode('5')
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check("5")
            finally:
                self.eth_network_card_down('5')
                self.exit_eth_mode('5')
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")

    @startup_teardown()
    def test_linux_eth_common_03_004(self):
        """
        1.连接RTL8125phy开启模块拨号
        2.打流30M 5分钟
        """
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            try:
                self.enter_eth_mode('3')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('3')
                iperf(bandwidth='30M', times=300, mode=1)
            finally:
                self.eth_network_card_down('3')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('3')

        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            try:
                self.enter_eth_mode('4')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('4')
                iperf(bandwidth='30M', times=300, mode=1)
            finally:
                self.eth_network_card_down('4')
                self.exit_eth_mode('4')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('4')

        elif self.eth_test_mode == '5':
            try:
                self.enter_eth_mode('5')
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('5')
                iperf(bandwidth='30M', times=300, mode=1)
            finally:
                self.eth_network_card_down('5')
                self.exit_eth_mode('5')
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")

    @startup_teardown()
    def test_linux_eth_common_03_005(self):
        """
        1.连接RTL8125phy开启模块拨号，浏览网页或ping www.baidu.com
        2.断电重启模块观察是否自动拨号，浏览网页或ping www.baidu.com
        """
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            try:
                self.enter_eth_mode('3')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('3')
                self.reboot_module_vbat()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('3')
            finally:
                self.eth_network_card_down('3')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('3')

        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            try:
                self.enter_eth_mode('4')
                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('4')
                self.reboot_module_vbat()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('4')
            finally:
                self.eth_network_card_down('4')
                self.at_handler.send_at('AT+QMAPWAC=0', 0)
                self.exit_eth_mode('4')

        elif self.eth_test_mode == '5':
            try:
                self.enter_eth_mode('5')
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('5')
                self.reboot_module_vbat()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)
                self.common_connect_check('5')
            finally:
                self.eth_network_card_down('5')
                self.exit_eth_mode('5')
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")

    @startup_teardown()
    def test_linux_eth_common_03_008(self):
        """
        1.查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        3.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            now_mode = '3'
        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            now_mode = '4'
        elif self.eth_test_mode == '5':
            now_mode = '5'
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")
        seq = 1
        if now_mode:
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_before}')

                self.at_handler.send_at('AT+QMAPWAC=1', 3)
                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                return_ethtool = subprocess.getoutput(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}')
                all_logger.info(
                    f'ethtool {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name}: {return_ethtool}')
                if 'Speed: 1000Mb/s' not in return_ethtool:
                    raise LinuxETHError("查询PC端自适应速率异常")

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test <= 100:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},小于期望最小值100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.at_handler.send_at('AT+QMAPWAC=0', 3)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_03_009(self):
        """
        1.PC端速度设置为100Mbps全双工
        2.重启模块后查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        3.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            now_mode = '3'
        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            now_mode = '4'
        elif self.eth_test_mode == '5':
            now_mode = '5'
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 100 duplex full: {return_ethtool_before}')

                return_value = self.at_handler.send_at('AT+QETH="dm"')
                if '+QETH: "dm","full"' not in return_value:
                    raise LinuxETHError(f'使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 100 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值0~100")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_03_010(self):
        """
        1.PC端速度设置为10Mbps全双工
        2.重启模块后查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        3.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            now_mode = '3'
        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            now_mode = '4'
        elif self.eth_test_mode == '5':
            now_mode = '5'
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")
        if now_mode:
            seq = 1
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 10 duplex full: {return_ethtool_before}')

                return_value = self.at_handler.send_at('AT+QETH="dm"')
                if '+QETH: "dm","full"' not in return_value:
                    raise LinuxETHError(f'使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 20 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值0~10")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown()
    def test_linux_eth_common_03_011(self):
        """
        1.PC端速度设置为2.5Gbps全双工(接上位机PCIE 2.5G网口)
        2.重启模块后查询PC端速率（通过PC端设置-网络和Internet--更改适配器选项--双击以太网连接）
        3.观察PC端本地连接状态并上网，通过speedtest测试速率
        """
        now_mode = ''
        if self.eth_test_mode == '0' or self.eth_test_mode == '3':
            now_mode = '3'
        elif self.eth_test_mode == '1' or self.eth_test_mode == '4':
            now_mode = '4'
        elif self.eth_test_mode == '5':
            now_mode = '5'
        else:
            all_logger.info("当前设备没有RTL8125、RTL8168、QCA8081，跳过")
        if now_mode:
            seq = 1
            try:
                self.enter_eth_mode(now_mode)

                return_ethtool_before = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 2500 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 2500 duplex full: {return_ethtool_before}')

                return_value = self.at_handler.send_at('AT+QETH="dm"')
                if '+QETH: "dm","full"' not in return_value:
                    raise LinuxETHError(f'使用AT指令查询RGMII双工模式默认值是否为full（全双工模式）异常：{return_value}')

                self.at_handler.cfun1_1()
                self.driver.check_usb_driver_dis()
                self.driver.check_usb_driver()
                time.sleep(10)  # 立即发AT可能会误判为AT不通
                self.at_handler.check_network()
                time.sleep(10)

                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
                speed_test = self.speedtest(
                    network_card=self.rgmii_ethernet_name if now_mode == '2' else self.rtl8125_ethernet_name)
                if speed_test > 20 or speed_test == 0:
                    raise LinuxETHError(f"速率异常！当前速率为{speed_test},期望值0~10")
            finally:
                self.eth_network_card_down(now_mode)
                return_ethtool_apeed_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} speed 1000 duplex full: {return_ethtool_apeed_end}')

                return_ethtool_end = subprocess.getoutput(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f')
                all_logger.info(
                    f'ethtool -s {self.rgmii_ethernet_name if now_mode == "2" else self.rtl8125_ethernet_name} advertise 0x80000000002f: {return_ethtool_end}')
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)

    @startup_teardown(teardown=['at_handler', 'reset_network_to_default'])
    def test_linux_eth_common_04_001(self):
        """
        1、AT+QETH="eth_driver", "r8125"
        2、AT+QMAPWAC=1开启自动拨号
        3、AT+qcfg="usbcfg",0x2C7C,0x0801,1,1,1,1,1,1,1开启adb 功能
        4、AT+cfun=1,1重启
        5、at+qmap="mpdn_rule",0,1,0,0,1  配置路由模式
        6、at+qmap="mpdn_rule"查询配置结果
        7、查看在PC端获取的ip地址
        """
        if self.IS_BL_version:
            self.at_handler.bound_5G_network()
            now_mode = ''
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,0,1', 3)
                self.check_mPDN_rule('0', '1')
                self.check_MPDN_status('0', '1')
                self.common_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)
        else:
            all_logger.info("当前不是博联版本，跳过")

    @startup_teardown()
    def test_linux_eth_common_04_002(self):
        """
        1、AT+QETH="eth_driver", "r8125"
        2、AT+QMAPWAC=1开启自动拨号
        3、AT+qcfg="usbcfg",0x2C7C,0x0801,1,1,1,1,1,1,1开启adb 功能
        4、AT+cfun=1,1重启
        5、at+qmap="mpdn_rule",0  删除配置
        6、AT+qmap="mpdn_rule",0,1,0,1,1,"34:48:ED:0D:0D:D8"  重新配置，为桥模式（mac地址从pc端获取，ipconfig -all ，看以太网的物理地址）
        7、查看在PC端获取的ip地址
        """
        if self.IS_BL_version:
            seq = 1
            now_mode = ''
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)
                self.send_at_error_try_again('AT+qmap="mpdn_rule",0,1,0,1,1,"FF:FF:FF:FF:FF:FF"', 3)
                self.check_mPDN_rule('0', seq, "FF:FF:FF:FF:FF:FF")
                self.check_MPDN_status('0', seq, "FF:FF:FF:FF:FF:FF")
                self.ip_passthrough_connect_check(now_mode)
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)
        else:
            all_logger.info("当前不是博联版本，跳过")

    @startup_teardown()
    def test_linux_eth_common_04_003(self):
        """
        1、使能RTL8125,开启网口发AT
        2、网口连接PC ,pC为linux系统
        3、把RGMII_AT_CLIENT.c放置pc,编译    gcc RGMII_AT_Client.c -o RGMII_AT_Client(编译一次即可，不用每次都编译)(上位机为Linux系统
        工具获取：https://192.168.23.225/svn/SoftwareTesting/02_ProjectLevel/11_5G_Standard/Communal/04_ProjectAccumulation/01_TechnicalDocument/01_SDX55/04_SDX55测试指导文档集/Yocto Open相关测试指导/RGMII AT)
        4、使用编译后的工具发送AT（不支持连写）
        ./RGMII_AT_Client  AT+COPS?
        ./RGMII_AT_Client  AT+qeng=\"servingcell\"
        5、校验网口侧返回结果与AT侧返回结果是否一致
        """
        if self.IS_BL_version:
            at_client_text = """
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>


#define SERVER_IP      "192.168.225.1"
#define SERVER_PORT    1555
#define BUFFER_SIZE    2048*4

int ql_rgmii_manager_server_fd_state(int n)
{
    if(n == -1 && (errno == EAGAIN || errno == EWOULDBLOCK))
    {
        return 1;
    }
    if( n < 0  && (errno == EINTR || errno == EINPROGRESS))
    {
        return 2;
    }
    else
    {
        return 0;
    }
}

int main(int argc, char **argv)
{
    char buffer_send[BUFFER_SIZE] = {0};
    char buffer_recv[BUFFER_SIZE] = {0};
    char buffer_temp[BUFFER_SIZE] = {0};
    int rv = 0;
    int count = 0;
    int len = 0;
    int i = 0;
    char * datap = NULL;

    if(argc == 2)
    {
        if(BUFFER_SIZE-3-2 <= strlen(argv[1])) return 0;
        memcpy(buffer_send+3, argv[1], strlen(argv[1]));
        memcpy(buffer_send+3+strlen(argv[1]), "\r\n", 2);
    }
    else if(argc == 1)
        snprintf(buffer_send+3, BUFFER_SIZE-3, "at\r\n");
    else
        return 0;


	buffer_send[0] = 0xa4;
    buffer_send[1] = (uint8_t)((strlen(buffer_send+3) & (0xff00))>>8);
    buffer_send[2] = (uint8_t)(strlen(buffer_send+3) & (0x00ff));


    struct sockaddr_in client_addr;
    memset(&client_addr, 0, sizeof(client_addr));
    client_addr.sin_family = AF_INET;
    client_addr.sin_addr.s_addr = htons(INADDR_ANY);
    client_addr.sin_port = htons(0);

    int client_socket = socket(AF_INET,SOCK_STREAM,0);
    if( client_socket < 0)
    {
        printf("Create Socket Failed!\r\n");
        return 0;
    }

    if( bind(client_socket,(struct sockaddr*)&client_addr,sizeof(client_addr)))
    {
        printf("Client Bind Port Failed!\r\n");
        return 0;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    if(inet_aton(SERVER_IP, &server_addr.sin_addr) == 0)
    {
        printf("Server IP Address Error!\r\n");
        return 0;
    }
    server_addr.sin_port = htons(SERVER_PORT);
    socklen_t server_addr_length = sizeof(server_addr);

    //set_non_blocking_mode client_socket
    fcntl(client_socket, F_SETFL, fcntl(client_socket, F_GETFL, 0) | O_NONBLOCK);


    printf("RGMII-AT Client Up => %s:%d\r\n", SERVER_IP, SERVER_PORT);
    while(1)
    {
        if(connect(client_socket,(struct sockaddr*)&server_addr, server_addr_length) >= 0)
        {
            break;
        }
        printf("Can Not Connect To => %s:%d\r\n", SERVER_IP, SERVER_PORT);
        sleep(2);
    }

    if(1)
    {
        rv = send(client_socket, buffer_send, (3+(int)strlen(buffer_send+3)),0);
        printf("\r\n\r\nsend:\r\n\r\n====================================> send all:%d\r\n==> len=%d head=0x%02x\r\n\"%s\"\r\n",
                    rv, (int)strlen(buffer_send+3), (uint8_t)buffer_send[0], buffer_send+3);
        if(rv != (3+(int)strlen(buffer_send+3)))
        {
            printf("Send buf not complete\r\n");
            //return 0;
        }
    }

    printf("\r\n\r\nrecv:");
    while(1)
    {
        rv = recv(client_socket, buffer_recv, BUFFER_SIZE, 0);
        if(rv >= 3)
        {
            printf("\r\n\r\n====================================> recv all:%d", rv);

            datap = buffer_recv;
            do
            {
                len = (((uint16_t)((uint8_t)*(datap+1))<<8) | ((uint16_t)((uint8_t)*(datap+2)) & (0x00ff)));
                memset(buffer_temp, 0, sizeof(buffer_temp));
                memcpy(buffer_temp, datap+3, len);

                printf("\r\n==> len=%d head=0x%02x\r\n\"%s\"\r\n", len, (uint8_t)*(datap), buffer_temp);
                for(i=0; i<len; i++)
                {
                    printf("0x%02x ", buffer_temp[i]);
                }
                printf("\r\n");

                rv = rv-len-3;
                if(rv>0)
                    datap = buffer_recv+3+len;
                if(rv<0)
                    printf("client_socket recv not complete\r\n");

            }while(rv > 0);

            memset(buffer_recv, 0, sizeof(buffer_recv));

        }
        else if(rv > 0)
        {
            printf("client_socket recv error internal\r\n");
            break;
        }
        else
        {
            if(!ql_rgmii_manager_server_fd_state(rv))
            {
                printf("client_socket recv error\r\n");
                break;
            }

        }

        count++;
        usleep(10*1000);

        if(count == 1000)
        {
            break;
        }

    }
    printf("\r\n");
    close(client_socket);
    return 0;
}

        """
            file_path = os.path.join(os.getcwd(), 'RGMII_AT_CLIENT.c')
            with open(file_path, 'w') as f:
                f.write(at_client_text.replace('\r\n', '\\r\\n').replace('\"%s\"', '\\\"%s\\\"'))

            return_chmod = subprocess.getoutput(f'chmod 777 {file_path}')
            all_logger.info(f'chmod 777 {file_path}: {return_chmod}')

            # gcc RGMII_AT_Client.c -o RGMII_AT_Client
            return_gcc = subprocess.getoutput(f'gcc {file_path} -o RGMII_AT_Client')
            all_logger.info(f'gcc {file_path} -o RGMII_AT_Client: {return_gcc}')

            now_mode = ''
            try:
                now_mode = self.enter_eth_mode(self.eth_test_mode)

                # return_cops = subprocess.getoutput(f'./{os.getcwd()}/RGMII_AT_Client  AT+COPS?')
                # all_logger.info(f'./{os.getcwd()}/RGMII_AT_Client  AT+COPS? :{return_cops}')
                return_cops = self.rgmii_at_client_send_at(f'{os.getcwd()}/RGMII_AT_Client', 'AT+COPS?')

                if '+COPS: ' not in return_cops:
                    raise LinuxETHError("异常！发送cops后返回异常：{return_cops}")
            finally:
                self.eth_network_card_down(now_mode)
                self.send_at_error_try_again('AT+QMAP="mPDN_rule",0', 6)
                self.exit_eth_mode(now_mode)
        else:
            all_logger.info("当前不是博联版本，跳过")

    def test_linux_eth_common_04_006(self):
        """
        1.AT+QETH="mac_address",06:EA:9F:31:49:28(随机设置设置MAC地址,第1位要为偶数)
        2.无
        3、AT+QETH="mac_address"
        """
        if self.IS_BL_version:
            try:
                pc_ethernet_orig_mac = subprocess.getoutput(
                    'ifconfig {} | grep ether | tr -s " " | cut -d " " -f 3 | head -c -1'.format(
                        self.rgmii_ethernet_name if self.eth_test_mode == '2' else self.rtl8125_ethernet_name))

                self.send_at_error_try_again(f'AT+QETH="mac_address",{pc_ethernet_orig_mac}', 6)

                self.gpio.set_reset_high_level()
                time.sleep(30)
                self.gpio.set_reset_low_level()
                time.sleep(30)
                self.reboot_module_vbat()
                time.sleep(10)
                self.at_handler.check_network()
                time.sleep(10)  # 立即发AT可能会误判为AT不通

                return_value = self.send_at_error_try_again('AT+QETH="mac_address"', 6)
                if pc_ethernet_orig_mac.upper() not in return_value:
                    raise LinuxETHError(f"异常！长按reset后mac地址异常:{pc_ethernet_orig_mac}>>>>>>{return_value}")
            finally:
                time.sleep(10)  # 避免太快返回error
                self.send_ipptmac("FF:FF:FF:FF:FF:FF")
        else:
            all_logger.info("当前不是博联版本，跳过！")


if __name__ == "__main__":
    param_dict = {
        'at_port': '/dev/ttyUSBAT',
        'dm_port': '/dev/ttyUSBDM',
        'debug_port': '/dev/ttyUSB0',
        'pc_ethernet_name': 'eth2',  # 系统内网网卡
        'rgmii_ethernet_name': 'eth0',  # rgmii 网线连接的网卡名称
        'rtl8125_ethernet_name': 'eth1',  # rtl8125 网线连接的网卡名称
        'phone_number': '13275650197'
    }
    # 'phone_number': '15256905471'
    eth_test_mode = '2'  # 选择测试模式
    """
    eth_test_mode:根据具体测试机配备的PHY硬件类型来决定(resource中需要配置)
    0  随机RGMII8035\8211和RTL8125
    1  随机RGMII8035\8211和RTL8168
    2  RGMII8035\8211
    3  RTL8125
    4  RTL8168
    5  QCA8081
    """
    linux_eth = LinuxETH(**param_dict)
    s = subprocess.getoutput('ifconfig eth2 down')
    all_logger.info(f"ifconfig eth2 down: {s}")
    all_logger.info('wait 0.5 seconds')
    time.sleep(0.5)

    # linux_eth.test_linux_eth_common_01_001()  # all OK
    # linux_eth.test_linux_eth_common_01_002()  # all OK
    # linux_eth.test_linux_eth_common_01_003()  # all OK
    # linux_eth.test_linux_eth_common_01_004()  # all OK
    # linux_eth.test_linux_eth_common_01_005()  # all OK
    # linux_eth.test_linux_eth_common_01_006()  # all OK

    # linux_eth.test_linux_eth_common_01_007()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_008()  # 3 OK 2 测速过程中会出现测速失败
    # linux_eth.test_linux_eth_common_01_009()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_010()  # 2 OK 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_012()  # 2 OK 3 OK,概率性拨号失败

    # linux_eth.test_linux_eth_common_01_013()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_014()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_015()  # 2 OK 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_016()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_017()  # 2 OK 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_018()  # 2 OK 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_019()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_020()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_021()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_022()  # 2 OK 3 OK

    # ***************************************************************

    # linux_eth.test_linux_eth_common_01_023()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_024()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_025()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_026()  # 2 OK 很慢 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_027()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_028()  # 2 OK 3 OK 概率性测速失败  # -----------------------------------------

    # linux_eth.test_linux_eth_common_01_031()  # 2 OK 3 OK

    # linux_eth.test_linux_eth_common_01_036()  # 2 OK 3 OK

    # *********************************************************************

    # linux_eth.test_linux_eth_common_01_032()  #  3 OK
    linux_eth.test_linux_eth_common_01_033()  # -----------------------------------------
    linux_eth.test_linux_eth_common_01_034()  # -----------------------------------------
    linux_eth.test_linux_eth_common_01_035()  # -----------------------------------------

    # linux_eth.test_linux_eth_common_01_038()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_039()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_040()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_041()  # 2 切换cfun后获取ip失败
    # linux_eth.test_linux_eth_common_01_042()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_043()  # 2 OK 3 OK

    # linux_eth.test_linux_eth_common_01_045()  # 2 OK 3 OK,概率性拨号失败
    # linux_eth.test_linux_eth_common_01_046()  # 2 OK 3 fail
    # linux_eth.test_linux_eth_common_01_047()  # 2 OK 3 OK

    # linux_eth.test_linux_eth_common_01_049()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_050()  # 2 OK 3 OK

    # linux_eth.test_linux_eth_common_01_052()  # 2 OK 3 OK 出现指令概率性error
    # linux_eth.test_linux_eth_common_01_053()  # 2 OK 3 OK 出现指令概率性error
    # linux_eth.test_linux_eth_common_01_054()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_055()  # 待完善----------------------------------------------------
    # linux_eth.test_linux_eth_common_01_056()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_057()  # 2 OK 3 OK
    # linux_eth.test_linux_eth_common_01_058()  # 2 OK 3 OK 出现指令概率性error
    # linux_eth.test_linux_eth_common_01_059()  # 2 OK 3 OK

    # linux_eth.test_linux_eth_common_01_061()  # 注不上NSA
    # linux_eth.test_linux_eth_common_01_062()  # 注不上NSA
    #  linux_eth.test_linux_eth_common_01_063()  # 2 OK 3 OK

    linux_eth.test_linux_eth_common_01_067()  # 2 OK
    linux_eth.test_linux_eth_common_01_068()  # 2 OK
    linux_eth.test_linux_eth_common_01_069()  # 2 OK
    linux_eth.test_linux_eth_common_01_071()  # 2 第二次拨号设置mpad_rule全部error
    linux_eth.test_linux_eth_common_01_072()  # 2 切换cfun后换取不到ip
    linux_eth.test_linux_eth_common_01_074()  # 2 OK

    # &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&

    # linux_eth.test_linux_eth_common_02_001()  # 2 OK 3 k
    # linux_eth.test_linux_eth_common_02_002()  # 2 OK 3 k
    # linux_eth.test_linux_eth_common_02_003()  # 2 OK 3 k

    # linux_eth.test_linux_eth_common_02_007()  # 2 OK 3 k
    # linux_eth.test_linux_eth_common_02_008()  # 2 OK 3 k
    # linux_eth.test_linux_eth_common_02_009()  # 2 OK 3 k
    # linux_eth.test_linux_eth_common_02_010()  # 2 full模式获取公网ip失败(可能是bug) 3 k
    # linux_eth.test_linux_eth_common_02_011()  # 2 full模式获取公网ip失败(可能是bug) 3 k
    # linux_eth.test_linux_eth_common_02_012()  # 2 获取公网ip失败(可能是bug) 3 k
    # linux_eth.test_linux_eth_common_02_013()  # 2 获取公网ip失败(可能是bug) 3 k
    # linux_eth.test_linux_eth_common_02_014()  # 2 获取公网ip失败(可能是bug) 3 k
    # linux_eth.test_linux_eth_common_02_015()  # 2 OK 3 k

    # linux_eth.test_linux_eth_common_03_001()  # 2 k 3 0k
    # linux_eth.test_linux_eth_common_03_002()  # 2 k 3 需要open版本测试
    # linux_eth.test_linux_eth_common_03_003()  # 2 k 3 0k
    # linux_eth.test_linux_eth_common_03_004()  # 2 k 3 0k
    # linux_eth.test_linux_eth_common_03_005()  # 2 k 3 0k

    # linux_eth.test_linux_eth_common_03_008()  # 2 k 3 full模式获取公网ip失败(可能是bug)
    # linux_eth.test_linux_eth_common_03_009()  # 2 k 3 full模式获取公网ip失败(可能是bug)
    # linux_eth.test_linux_eth_common_03_010()  # 2 k 3 full模式获取公网ip失败(可能是bug)
    # linux_eth.test_linux_eth_common_03_011()  # 3 full模式获取公网ip失败(可能是bug)

    # linux_eth.test_linux_eth_common_04_001()  # 2 OK 3 0k
    # linux_eth.test_linux_eth_common_04_002()  # 2 OK 3 0k
    # linux_eth.test_linux_eth_common_04_003()  # 2 发送at后无返回，可能测试版本不是博联版本导致 3 k

    # linux_eth.test_linux_eth_common_04_006()  # 2 OK 3 0k

    s = subprocess.getoutput('ifconfig eth2 up')
    all_logger.info(f"ifconfig eth2 up: {s}")
    s = subprocess.getoutput('udhcpc -i eth2')
    all_logger.info(f"udhcpc -i eth2: {s}")
    all_logger.info('End test.')
