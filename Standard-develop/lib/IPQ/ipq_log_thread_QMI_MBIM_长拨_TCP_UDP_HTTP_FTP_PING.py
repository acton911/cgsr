# -*- encoding=utf-8 -*-
from logging.handlers import RotatingFileHandler
from threading import Thread
from pandas import DataFrame
import time
import sys
import os
import re
import numpy as np
import logging
import platform
import json
import pandas as pd


class LogThread(Thread):
    def __init__(self, version, info, log_queue, main_queue):
        super().__init__()
        self.version = version
        self.info = info
        self.log_queue = log_queue
        self.main_queue = main_queue
        self.df = DataFrame(columns=['runtimes_start_timestamp'])
        self._methods_list = [x for x, y in self.__class__.__dict__.items()]

        # 初始化log文件夹
        self.init_log_dir(self.info)

        # 初始化log文件
        self.at_log_handle = open('ATLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.dos_log_handle = open('DOSLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.ipq_log_handle = open('IPQLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.debug_log_handle = open('Debug-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.result_log_handle = open('RESULTLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.network_log_handle = open('NETWORKLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.handles = ['self.at_log_handle', 'self.dos_log_handle', 'self.debug_log_handle',
                        'self.result_log_handle', 'self.network_log_handle', 'self.ipq_log_handle']
        self.thread_timestamp = time.time()

        # 初始化往at_log写入当前脚本的名称
        _, file_name = os.path.split(os.path.realpath(sys.argv[0]))
        self.at_log_handle.write("测试类型: {}-{}\n".format(file_name, self.info))
        self.at_log_handle.write('测试环境：{}-{}-{}\n'.format(platform.platform(), platform.machine(), sys.version))
        try:
            with open('../../../../lib/Communal/version.json') as f:
                version_info = json.loads(f.read())
        except FileNotFoundError:
            with open('../version.json') as f:
                version_info = json.loads(f.read())
        self.at_log_handle.write('脚本版本：{}-{}\n'.format(version_info['date'], version_info['commit_id']))

        # 初始化logger
        handler = RotatingFileHandler('_.log', 'a', 1024 * 1024 * 100, 10, delay=False)
        handler.setFormatter(logging.Formatter('[%(asctime)s.%(msecs)03d] %(levelname)s %(module)s->%(lineno)d->%(funcName)s->%(message)s'))
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    def run(self):
        while True:
            module, *param = self.log_queue.get()
            if (time.time() - self.thread_timestamp) > 300:
                self.log_size_checker()
                self.thread_timestamp = time.time()
            if module in self._methods_list:
                if 'end_script' == module:
                    evt = param.pop()
                    getattr(self.__class__, '{}'.format(module))(self, *param)
                    self.main_queue.put(True)
                    evt.set()
                else:
                    getattr(self.__class__, '{}'.format(module))(self, *param)

    def log_size_checker(self):
        for handle in self.handles:
            exec(f"""if {handle}.tell() > 1024 * 1024 * 100:
                        {handle}.close()
                        file_name = {handle}.name
                        file_name = (file_name + '.1') if file_name[-1] not in '0123456789' else '{{}}.{{}}'.format('.'.join(file_name.split('.')[:2]), int(file_name.split('.')[-1]) + 1)
                        {handle} = open(file_name, "a+", encoding='utf-8', buffering=1)""")

    def at_log(self, log_queue_data):
        self.at_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def dos_log(self, log_queue_data):
        self.dos_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def debug_log(self, log_queue_data):
        self.debug_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def ipq_log(self, log_queue_data):
        self.ipq_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def result_log(self, log_queue_data):
        self.result_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def network_log(self, log_queue_data):
        self.network_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def all(self, log_queue_data):
        content_print = re.sub(r'\[.*?]\s*(Run|run)times\s*:\s*\d+\s+', '', log_queue_data)
        content_at = re.sub(r'(Run|run)times\s*:\s*\d+\s+', '', log_queue_data)
        print(content_print)
        self.at_log_handle.write(content_at + '\n')
        self.dos_log_handle.write(log_queue_data + '\n')

    def df(self, runtimes, column_name, content):
        self.df.loc[runtimes, column_name] = content  # 推送数据到DataFrame
        if 'error' in column_name:  # 如果有错误上报立刻写入csv
            self.df.to_csv('_cache.csv', index=False)  # 保存到csv文件并且去除索引

    def to_csv(self):
        self.df.to_csv('_cache.csv', index=False)  # 保存到csv文件并且去除索引

    def init_log_dir(self, info):
        """
        初始化log存放的文件夹，将当前的时间作为文件夹的名称
        :param info: 当前脚本的类型
        :return: None
        """
        local_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        file_path = os.path.join(os.getcwd(), '{}-{}'.format(local_time, info))
        os.mkdir(file_path)  # 创建文件夹
        os.chdir(file_path)  # 进入创建的文件夹

        # 避免KeyError, init_df_column中列表的值都为下面参数统计中用到的值
        init_df_column = ['local_time', 'runtimes', 'tcp_fail_times', 'udp_fail_times',
                          'ftp_fail_times', 'http_fail_times', 'ping_package_loss_rate']
        for column_name in init_df_column:
            self.df.loc[0, column_name] = np.nan

    def write_result_log(self, runtimes):
        """
        每个runtimes写入result_log的内容
        :param runtimes: 当前脚本的运行次数
        :return: None
        """
        # AT+QCFG="data_interface"失败次数          data_interface_value_error_times
        # ipq没有检测到Enable bridge snooping次数    ipq_start_fail_times
        # ipq pcie加载异常次数                       ipq_pcie_check_fail_times
        result_string = ''
        result_width_standard = {0: ['local_time', 25], 1: ['runtimes', 8],
                                 2: ['tcp_fail_times', 14], 3: ['udp_fail_times', 14],
                                 4: ['ftp_fail_times', 14], 5: ['http_fail_times', 15],
                                 6: ['ping_package_loss_rate', 22], 7: ['cefs_erase_times', 10],
                                 8: ['usrdata_erase_times', 10]}
        # 当runtimes为1的时候，拼接所有的统计参数并写入log
        if runtimes == 1:
            header_string = ''
            for index, (para, width) in result_width_standard.items():
                header_string += format(para, '^{}'.format(width)) + '\t'  # 将变量格式化为指定宽度后加制表符(\t)
            self.result_log_handle.write(header_string + '\n')
        # 需要统计的参数计算
        runtimes_start_timestamp = self.df.loc[runtimes, 'runtimes_start_timestamp']  # 写入当前runtimes的时间戳
        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(runtimes_start_timestamp))))
        tcp_fail_times = int(self.df['tcp_fail_times'].sum())
        udp_fail_times = int(self.df['udp_fail_times'].sum())
        ftp_fail_times = int(self.df['ftp_fail_times'].sum())
        http_fail_times = int(self.df['http_fail_times'].sum())
        cefs_erase_times = '' if pd.isna(self.df.loc[runtimes, 'cefs_erase_times']) else int(
            self.df.loc[runtimes, 'cefs_erase_times'])
        usrdata_erase_times = '' if pd.isna(self.df.loc[runtimes, 'usrdata_erase_times']) else int(
            self.df.loc[runtimes, 'usrdata_erase_times'])
        ping_package_loss_rate = '{:.2f}%'.format(self.df.loc[runtimes, 'ping_package_loss_rate']) if pd.notna(self.df.loc[runtimes, 'ping_package_loss_rate']) else ''
        result_list = [local_time, runtimes, tcp_fail_times, udp_fail_times,
                       ftp_fail_times, http_fail_times, ping_package_loss_rate, cefs_erase_times, usrdata_erase_times]
        result_list.reverse()  # 反转列表，便于弹出
        for index, (para, width) in result_width_standard.items():
            try:
                result_string += format(result_list.pop(), '^{}'.format(width)) + '\t'  # 不要忘记\t
            except IndexError:
                pass
        self.result_log_handle.write(result_string + '\n')

    def end_script(self, script_start_time, runtimes):
        script_start_time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(script_start_time))
        script_end_time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        tcp_fail_times = int(self.df['tcp_fail_times'].sum())
        udp_fail_times = int(self.df['udp_fail_times'].sum())
        ftp_fail_times = int(self.df['ftp_fail_times'].sum())
        http_fail_times = int(self.df['http_fail_times'].sum())
        ping_package_loss_rate = np.round(np.mean(self.df['ping_package_loss_rate'].dropna()), 2)
        # 新增统计flash擦除次数
        cefs_erase_averagetimes = int(self.df['cefs_erase_times'].mean())
        cefs_erase_maxtimes = int(self.df['cefs_erase_times'].max())
        usrdata_erase_averagetimes = int(self.df['usrdata_erase_times'].mean())
        usrdata_erase_maxtimes = int(self.df['usrdata_erase_times'].max())

        result = '\n[{}]-[{}]\n'.format(script_start_time_format, script_end_time_format) + \
                 '共运行{}H/{}次\n'.format(round((time.time() - script_start_time) / 3600, 2), runtimes) + \
                 'TCP异常次数(tcp_fail_times)：{}次\n'.format(tcp_fail_times) + \
                 'UDP异常次数(udp_fail_times)：{}次\n'.format(udp_fail_times) + \
                 'FTP异常次数(ftp_fail_times)：{}次\n'.format(ftp_fail_times) + \
                 'HTTP异常次数(http_fail_times)：{}次\n'.format(http_fail_times) + \
                 'ping平均丢包率(ping_package_loss_rate): {}%\n'.format(ping_package_loss_rate) + \
                 'cefs平均擦除次数(cefs_erase_averagetimes): {}次\n'.format(cefs_erase_averagetimes) + \
                 'cefs最大擦除次数(cefs_erase_maxtimes): {}次\n'.format(cefs_erase_maxtimes) + \
                 'usrdata平均擦除次数(usrdata_erase_averagetimes): {}次\n'.format(usrdata_erase_averagetimes) + \
                 'usrdata最大擦除次数(usrdata_erase_maxtimes): {}次\n'.format(usrdata_erase_maxtimes)

        print(result)
        with open('统计结果.txt', 'a', encoding='utf-8', buffering=1) as f:
            f.write('-----------压力统计结果start-----------{}-----------压力统计结果end-----------\n'.format(result))
