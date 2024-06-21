# -*- encoding=utf-8 -*-
import subprocess
import time
import signal
from sys import path
import logging
import os
path.append(os.path.join('..', '..', '..', 'lib', 'Communal'))
path.append(os.path.join('..', '..', '..', 'lib', 'Dial'))
from functions import environment_check, pause, QuectelCMThread
environment_check()  # 检查环境
from dial_manager import DialManager
from route_thread import RouteThread
from at_thread import ATThread
from uart_thread import UartThread
from dial_process_thread import DialProcessThread
from queue import Queue
from threading import Event
from dial_log_thread_fusion import LogThread
from dial_ping_thread import PingThread
from dial_modem_thread import ModemThread

"""
脚本准备:
1. 接线方式:
    a. VBAT
       M.2: PWRKEY置高，飞线连接P_EN和DTR
       5G_EVB_V2.2: 短接PWRKEY_3.3V和RTS，短接3.8V_EN和DTR 
    b. QPOWD1
       使用AT+QPOWD=1进行关机，飞线按照开关机QPOWD1方式
    注意: 新5G_M.2_EVB仅支持Vbat:DTR置为DTR_ON 无需跳线
2. 手动禁用本地以太网,WIFI网络,或者拔掉网线
3. Python版本大于3.8

脚本逻辑:
1. 模块初始化(版本号/IMEI/CPIN/其他特殊指令)；
2. 如果选择VBAT或QPOWD1开关机-则关机->开机->找网->等待拨号加载；
3. 进行拨号连接；
4. 检查网络；
5. 检测模块温度；
6. 进行TCP/UDP/FTP/HTTP测试;
7. 重复2-6.
"""


# ======================================================================================================================
# 必选参数
uart_port = 'COM16'  # 定义串口号,用于控制DTR引脚电平或检测URC信息
at_port = 'COM30'  # 定义AT端口号,用于发送AT指令或检测URC信息
dm_port = 'COM29'  # 定义DM端口号,用于判断模块有无dump
debug_port = ''  # RM模块参数设置为''，但是需要连接跳线读取debug log，RG需要设置为DEBUG UART串口号
modem_port = 'COM31'  # 定义MODEM端口号,用于检测拨号过程中网络状态信息
restart_mode = None  # 设置是否开关机，None：每个runtimes不进行开关机，1：每个runtimes进行VBAT开关机， 2：每个runtimes进行qpowd=1开关机
cfun01 = False  # RGMII和RTL8125参数，设置是否进行CFUN0/1切换，其他拨号方式默认False
revision = 'RG500QEAAAR11A05M4G'  # 设置Revision版本号，填写ATI+CSUB查询的Revision部分
sub_edition = 'V02'  # 设置SubEdition版本号，填写ATI+CSUB查询的SubEdition部分
imei = '869710030002905'  # 模块测试前配置IMEI号
dial_mode = 'MBIM'  # 设置拨号方式 Windows: NDIS/MBIM/RGMII/RTL8125  LINUX: WWAN/MBIM/GOBINET/ECM
is_5g_m2_evb = False  # 适配RM新EVB压力挂测,True: 当前使用EVB为5G_M.2_EVB ,False:当前使用为M.2_EVB_V2.2或普通EVB(5G_EVB_V2.2)
network_driver_name = 'RG500Q-EA'  # Windows MBIM和NDIS拨号关注，如果拨号模式是NDIS，设置网卡名称'Quectel Generic'，如果MBIM，设置'Generic Mobile Broadband Adapter' 因为版本BUG的原因，MBIM拨号时候通常要设置为"RG500Q-EA"，根据实际加载情况设置
config = {
    # 自动创建的文件大小(K)
    'file_size': 1000,
    # TCP
    'tcp_server': '112.31.84.164',
    'tcp_port': 8305,
    # UDP
    'udp_server': '112.31.84.164',
    'udp_port': 8305,
    # FTP
    'ftp_server': '58.40.120.14',
    'ftp_port': 21,
    'ftp_username': 'test',
    'ftp_password': 'test',
    'ftp_path': 'flynn',
    # HTTP
    'http_server_url': 'http://112.31.84.164:8300/upload.php',
    'http_server_remove_url': 'http://112.31.84.164:8300/remove_file.php',
    'http_server_ip_port': '112.31.84.164:8300'
}
# ======================================================================================================================
# 可选参数
runtimes_temp = 0  # 设置脚本运行次数，默认0是不限次数，如果设置1000则脚本运行1000个runtimes后自动结束
timing = 0   # 设置脚本的运行时间，单位为h，默认0是不限制时间，如果设置12则脚本运行12小时后自动结束
# ======================================================================================================================
# 其他参数
runtimes = 0
version = revision + sub_edition
script_start_time = time.time()  # 脚本开始的时间，用作最后log统计
restart_mode_str = "VBAT" if restart_mode == 1 else 'QPOWD1'
dial_info = '{}_TCP_UDP_FTP_HTTP_PING'.format(restart_mode_str)  # 脚本详情字符串
evb = 'EVB' if revision.upper().startswith('RG') else 'M.2'  # RG默认evb参数为EVB，RM默认evb参数为M.2
logger = logging.getLogger(__name__)
# ======================================================================================================================
# 定义queue并启动线程
main_queue = Queue()
route_queue = Queue()
uart_queue = Queue()
process_queue = Queue()
at_queue = Queue()
log_queue = Queue()
modem_queue = Queue()
route_thread = RouteThread(route_queue, uart_queue, process_queue, at_queue)
uart_thread = UartThread(uart_port, debug_port, uart_queue, main_queue, log_queue)
process_thread = DialProcessThread(at_port, dm_port, process_queue, main_queue, log_queue)
at_thread = ATThread(at_port, dm_port, at_queue, main_queue, log_queue)
log_thread = LogThread(version, restart_mode, dial_mode, dial_info, log_queue, main_queue)
ping_thread = PingThread(runtimes, log_queue)
modem_thread = ModemThread(runtimes, log_queue, modem_port, modem_queue)
threads = [route_thread, uart_thread, process_thread, at_thread, log_thread, ping_thread, modem_thread]
for thread in threads:
    thread.setDaemon(True)
    thread.start()


def route_queue_put(*args, queue=route_queue):
    """
    往某个queue队列put内容，默认为route_queue，并且接收main_queue队列如果有内容，就接收。
    :param args: 需要往queue中发送的内容
    :param queue: 指定queue发送，默认route_queue
    :return: main_queue内容
    """
    logger.info('{}->{}'.format(queue, args))
    evt = Event()
    queue.put([*args, evt])
    evt.wait()
    _main_queue_data = main_queue.get(timeout=0.1)
    return _main_queue_data


# 脚本结束，进行结果统计
def handler(signal_num, frame=None):  # noqa
    """
    脚本结束参数统计。
    """
    route_queue_put('end_script', script_start_time, runtimes, queue=log_queue)  # 结束脚本统计log
    exit()


# ======================================================================================================================
# 初始化
greeting = '{}请确认以太网和WIFI连接断开后按Enter键继续...'.format('请确保命令行执行 quectel-CM 当前设置的拨号方式可以手动拨号成功后运行脚本\n' if os.name != 'nt' and dial_mode != 'ECM' else '')
input(greeting)
while True:  # 为了避免多人同时运行操作一个文件导致异常，初始化需要指定文件夹名称
    data = input('请输入你的英文名称（用作FTP创建文件夹，例如 flynn; 如果同时运行多个脚本，请再加上序列号，例如flynn01）:')
    if data:
        config['ftp_path'] = data
        break
subprocess.call('cls' if os.name == 'nt' else 'clear', shell=True)
signal.signal(signal.SIGINT, handler)  # 捕获Ctrl+C，当前方法可能有延迟
dial_manager = DialManager(main_queue, route_queue, uart_queue, log_queue, uart_port, evb, version, imei, dial_mode, '',
                           '', '', '', '', '', restart_mode, network_driver_name, is_5g_m2_evb, runtimes)
log_queue.put(['at_log', '{}initialize{}'.format('=' * 35, '=' * 35)])
print("\rinitialize", end="")
dial_init_fusion_status = dial_manager.dial_init_fusion()
if dial_init_fusion_status is False:  # 如果需要重新开始，运行re_init
    print('请手动关闭拨号自动连接，并检查AT+QCFG="USBNET"的返回值与脚本配置的dial_mode是否匹配(0: NDIS, 1: MBIM)，然后重新运行脚本')
    exit()
# ======================================================================================================================
# 主流程
while True:
    # 脚本自动停止判断
    runtimes += 1
    time.sleep(0.1)  # 此处停止0.1为了防止先打印runtimes然后才打印异常造成的不一致
    if (runtimes_temp != 0 and runtimes > runtimes_temp) or (timing != 0 and time.time() - script_start_time > timing * 3600):  # 如果runtimes到达runtimes_temp参数设定次数或者当前runtimes时间超过timing设置时间，则停止脚本
        route_queue_put('end_script', script_start_time, runtimes - 1, queue=log_queue)  # 结束脚本统计log
        break

    # 打印当前runtimes，写入csv
    print("\rruntimes: {} ".format(runtimes), end="")
    log_queue.put(['df', runtimes, 'runtimes', str(runtimes)])  # runtimes
    log_queue.put(['df', runtimes, 'runtimes_start_timestamp', time.time()])  # runtimes_start_timestamp
    log_queue.put(['at_log', "{}runtimes:{}{}\n".format('=' * 35, runtimes, '=' * 35)])  # at_log写入分隔符
    log_queue.put(['debug_log', "{}runtimes:{}{}\n".format('=' * 35, runtimes, '=' * 35)])  # at_log写入分隔符
    if os.name != 'nt':
        log_queue.put(['quectel_cm_log', "{}runtimes:{}{}\n".format('=' * 35, runtimes, '=' * 35)])  # at_log写入分隔符

    quectel_cm = ''
    dial_manager.runtimes = runtimes

    if restart_mode is not None:  # 如果每个Runtimes需要进行开关机

        dial_init_fusion_info = dial_manager.dial_init_fusion()
        if dial_init_fusion_info is False:
            dial_manager.dial_init_fusion()
            continue

    if os.name == 'nt':
        if dial_mode.upper() == "NDIS" or dial_mode.upper() == "MBIM":  # Windows下 MBIM 和 NDIS 拨号
            # 用win api进行连接
            main_queue_data = route_queue_put('Process', 'connect', dial_mode, runtimes)
            if main_queue_data is False:
                dial_manager.dial_init_fusion()
                continue
            # 检查和电脑IP的情况
            main_queue_data = route_queue_put('Process', 'check_ip_connect_status', dial_mode, network_driver_name, runtimes)
            if main_queue_data is False:
                dial_manager.dial_init_fusion()
                continue
        elif dial_mode.upper() == "RGMII":  # Windows下RGMII拨号
            main_queue_data = route_queue_put('Process', 'rgmii_connect_check', runtimes)
            if main_queue_data is False:
                dial_manager.dial_init_fusion()
                continue
        elif dial_mode.upper() == "RTL8125":
            main_queue_data = route_queue_put('Process', 'rtl_connect_check', runtimes)
            if main_queue_data is False:
                dial_manager.dial_init_fusion()
                continue
        else:
            print("设置的拨号模式异常，请检查拼写和大小写")
            pause()
    else:  # Linux下拨号方式
        if dial_mode.upper() == "ECM":
            main_queue_data = route_queue_put('Process', 'ecm_connect_check', runtimes)
            if main_queue_data is False:
                dial_manager.dial_init_fusion()
                continue
        else:
            # 打开quectel-CM
            quectel_cm = QuectelCMThread(log_queue)

            if dial_mode.upper() == 'WWAN':
                main_queue_data = route_queue_put('Process', 'wwan_connect_check_copy', runtimes)
                if main_queue_data is False:
                    quectel_cm.terminate()
                    dial_manager.dial_init_fusion()
                    continue
            elif dial_mode.upper() == 'GOBINET':
                main_queue_data = route_queue_put('Process', 'gobinet_connect_check_copy', runtimes)
                if main_queue_data is False:
                    quectel_cm.terminate()
                    dial_manager.dial_init_fusion()
                    continue
            elif dial_mode.upper() == 'MBIM':
                main_queue_data = route_queue_put('Process', 'mbim_connect_check_copy', runtimes)
                if main_queue_data is False:
                    quectel_cm.terminate()
                    dial_manager.dial_init_fusion()
                    continue
            else:
                print("设置的拨号模式异常，请检查拼写和大小写")
                pause()

    # 打开AT口->进行网络检测->关闭AT口
    main_queue_data = route_queue_put('AT', 'open', runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    # 开机检测ATFWD
    main_queue_data = route_queue_put('AT', 'check_atfwdok', runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    # RTL和RGMII可选进行CFUN0，1切换
    if cfun01:
        main_queue_data = dial_manager.dial_fusion_cfun_0_1()
        if main_queue_data is False:
            ping_thread.df_flag = True  # ping写入log
            modem_thread.modem_flag = True
            dial_manager.dial_init_fusion()
            continue

    ping_thread.runtimes = runtimes  # 连接成功后开始ping的标志
    modem_thread.runtimes = runtimes

    main_queue_data = route_queue_put('AT', 'check_network', False, runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    # 温度查询
    main_queue_data = route_queue_put('AT', 'check_qtemp', runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    # flash分区擦写量查询
    route_queue_put('AT', 'qftest_record', runtimes)

    # 查询统计还原次数
    main_queue_data = route_queue_put('AT', 'check_restore', runtimes)
    if main_queue_data is False:
        dial_manager.dial_init_fusion()
        continue

    # AT+QDMEM?分区内存泄露查询
    if restart_mode is None and runtimes % 50 == 0:
        time.sleep(2)
        route_queue_put('AT', 'memory_leak_monitoring', runtimes)

    # 进行多种协议测试
    main_queue_data = route_queue_put('Process', 'fusion_protocol_test', config, dial_mode, runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    main_queue_data = route_queue_put('AT', 'close', runtimes)
    if main_queue_data is False:
        ping_thread.df_flag = True  # ping写入log
        modem_thread.modem_flag = True
        dial_manager.dial_init_fusion()
        continue

    ping_thread.df_flag = True  # ping写入log
    time.sleep(1)  # 等待ping log
    modem_thread.modem_flag = True  # modem口停止网络状态check

    # 短连断开连接
    if os.name == 'nt' and dial_mode.upper() != "RGMII" and dial_mode.upper() != "RTL8125":   # windows下短拨断开拨号
        main_queue_data = route_queue_put('Process', 'disconnect', runtimes)
        if main_queue_data is False:
            dial_manager.dial_init_fusion()
            continue
    elif os.name == 'posix' and dial_mode.upper() != 'ECM':  # Linux下除了ECM拨号，其他拨号方式断开拨号
        quectel_cm.terminate()

    # LOG相关
    log_queue.put(['to_csv'])  # 所有LOG写入CSV
    log_queue.put(['write_result_log', runtimes])  # 每个runtimes往result_log文件写入log
