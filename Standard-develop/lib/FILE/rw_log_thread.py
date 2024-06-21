# -*- encoding=utf-8 -*-
from logging.handlers import RotatingFileHandler
from threading import Thread
from pandas import DataFrame
import time
import sys
import os
import re
import pandas as pd
import numpy as np
import logging
import platform
import json
cefs_erasetimes_list = []
ufs_erasetimes_list = []


class LogThread(Thread):
    def __init__(self, version, info, vbat, log_queue, main_queue):
        super().__init__()
        self.version = version
        self.info = info
        self.vbat = vbat
        self.log_queue = log_queue
        self.main_queue = main_queue
        self.df = DataFrame(columns=['runtimes_start_timestamp'])
        self._methods_list = [x for x, y in self.__class__.__dict__.items()]

        # 初始化log文件夹
        self.init_log_dir(self.info)

        # 初始化log文件
        self.at_log_handle = open('ATLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.dos_log_handle = open('DOSLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.debug_log_handle = open('Debug-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.result_log_handle = open('RESULTLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.network_log_handle = open('NETWORKLog-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.efsec_log_handle = open('EFSBlockEC-{}.txt'.format(self.version), "a+", encoding='utf-8', buffering=1)
        self.handles = ['self.at_log_handle', 'self.dos_log_handle', 'self.debug_log_handle',
                        'self.result_log_handle', 'self.network_log_handle', 'self.efsec_log_handle']
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

    def result_log(self, log_queue_data):
        self.result_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def network_log(self, log_queue_data):
        self.network_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

    def efsec_log(self, log_queue_data):
        self.efsec_log_handle.write('{}{}'.format(log_queue_data, '' if log_queue_data.endswith('\n') else '\n'))

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
        init_df_column = ['local_time', 'runtimes', 'rw_delete_time',
                          'rw_delete_fail_times', 'kill_adb_fail_times', 'cefs_erase_times', 'usrdata_erase_times']
        for column_name in init_df_column:
            self.df.loc[0, column_name] = np.nan

    def write_result_log(self, runtimes):
        """
        每个runtimes写入result_log的内容
        :param runtimes: 当前脚本的运行次数
        :return: None
        """
        if self.vbat: #重启模块
            result_width_standard = {0: ['local_time', 25], 1: ['runtimes', 8],
                                     2: ['rw_delete_time', 14], 3: ['rw_delete_fail_times', 20],
                                     4: ['kill_adb_fail_times', 19], 5: ['cefs_erase_times', 10], 6: ['usrdata_erase_times', 10]}
        else:
            result_width_standard = {0: ['local_time', 25], 1: ['runtimes', 8],
                                     2: ['rw_delete_time', 14], 3: ['rw_delete_fail_times', 20],
                                     4: ['kill_adb_fail_times', 19], 5: ['cefs_erase_times', 10], 6: ['usrdata_erase_times', 10]}

        # 当runtimes为1的时候，拼接所有的统计参数并写入log
        if runtimes == 1:
            header_string = ''
            for index, (para, width) in result_width_standard.items():
                header_string += format(para, '^{}'.format(width)) + '\t'  # 将变量格式化为指定宽度后加制表符(\t)
            self.result_log_handle.write(header_string + '\n')
        # 参数统计
        runtimes_start_timestamp = self.df.loc[runtimes, 'runtimes_start_timestamp']  # 写入当前runtimes的时间戳
        local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(float(runtimes_start_timestamp))))
        rw_delete_fail_times = int(self.df['rw_delete_fail_times'].sum())
        kill_adb_fail_times = int(self.df['kill_adb_fail_times'].sum())
        rw_delete_time = '' if pd.isna(self.df.loc[runtimes, 'rw_delete_time']) else round(float(self.df.loc[runtimes, 'rw_delete_time']), 2)
        if self.vbat:
            cefs_erase_times = '' if pd.isna(self.df.loc[runtimes, 'cefs_erase_times']) else int(self.df.loc[runtimes, 'cefs_erase_times'])
            usrdata_erase_times = '' if pd.isna(self.df.loc[runtimes, 'usrdata_erase_times']) else int(self.df.loc[runtimes, 'usrdata_erase_times'])

            result_list = [local_time, runtimes, rw_delete_time,
                           rw_delete_fail_times, kill_adb_fail_times, cefs_erase_times, usrdata_erase_times]
            result_list.reverse()  # 反转列表，便于弹出
            result_string = ''
            for index, (para, width) in result_width_standard.items():
                try:
                    result_string += format(result_list.pop(), '^{}'.format(width)) + '\t'  # 不要忘记\t
                except IndexError:
                    pass
            # 特殊处理DFOTA异常：当前runtimes写入前，匹配最后一行runtimes是否runtimes相等，如果相等，删除后重写
            try:
                with open('RESULTLog-{}.txt'.format(self.version), 'rb+') as f:
                    n = -1
                    while True:
                        n -= 1
                        f.seek(n, 2)  # 指针移动
                        if f.__next__() == b'\n':  # 如果当前的指针下一个元素是\n
                            end_line = f.read().decode('utf-8')
                            file_runtimes = ''.join(re.findall(r'.*?:\d+\s+(\d+)', end_line))
                            if str(runtimes) == file_runtimes:
                                f.seek(n + 1, 2)
                                f.truncate()  # 删除
                            break
            except Exception as e:
                self.at_log_handle.write('{}\n'.format(e))
            self.result_log_handle.write(result_string + '\n')

        else:
            if runtimes == 1:
                cefs_erasetimes = self.df.loc[runtimes, 'cefs_erase_times'] - self.df.loc[runtimes, 'cefs_erase_times']
                usrdata_erasetimes = self.df.loc[runtimes, 'usrdata_erase_times'] - self.df.loc[runtimes, 'usrdata_erase_times']
            else:
                cefs_erasetimes = self.df.loc[runtimes, 'cefs_erase_times'] - self.df.loc[
                    runtimes - 1, 'cefs_erase_times']
                usrdata_erasetimes = self.df.loc[runtimes, 'usrdata_erase_times'] - self.df.loc[
                    runtimes - 1, 'usrdata_erase_times']

            cefs_erasetimes_list.append(cefs_erasetimes)
            ufs_erasetimes_list.append(usrdata_erasetimes)

            result_list = [local_time, runtimes, rw_delete_time,
                           rw_delete_fail_times, kill_adb_fail_times, cefs_erasetimes, usrdata_erasetimes]
            result_list.reverse()  # 反转列表，便于弹出
            result_string = ''
            for index, (para, width) in result_width_standard.items():
                try:
                    result_string += format(result_list.pop(), '^{}'.format(width)) + '\t'  # 不要忘记\t
                except IndexError:
                    pass
            # 特殊处理DFOTA异常：当前runtimes写入前，匹配最后一行runtimes是否runtimes相等，如果相等，删除后重写
            try:
                with open('RESULTLog-{}.txt'.format(self.version), 'rb+') as f:
                    n = -1
                    while True:
                        n -= 1
                        f.seek(n, 2)  # 指针移动
                        if f.__next__() == b'\n':  # 如果当前的指针下一个元素是\n
                            end_line = f.read().decode('utf-8')
                            file_runtimes = ''.join(re.findall(r'.*?:\d+\s+(\d+)', end_line))
                            if str(runtimes) == file_runtimes:
                                f.seek(n + 1, 2)
                                f.truncate()  # 删除
                            break
            except Exception as e:
                self.at_log_handle.write('{}\n'.format(e))
            self.result_log_handle.write(result_string + '\n')

    def end_script(self, script_start_time, runtimes):
        script_start_time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(script_start_time))
        script_end_time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        rw_delete_fail_times = int(self.df['rw_delete_fail_times'].sum())
        kill_adb_fail_times = int(self.df['kill_adb_fail_times'].sum())
        rw_delete_time_avg = np.round(np.mean(self.df['rw_delete_time'].dropna()), 2)

        if self.vbat:
            # 新增统计flash擦除次数
            cefs_erase_averagetimes = self.df['cefs_erase_times'].mean()
            cefs_erase_maxtimes = self.df['cefs_erase_times'].max()
            usrdata_erase_averagetimes = self.df['usrdata_erase_times'].mean()
            usrdata_erase_maxtimes = self.df['usrdata_erase_times'].max()

            result = '\n[{}]-[{}]\n'.format(script_start_time_format, script_end_time_format) + \
                     '共运行{}H/{}次\n'.format(round((time.time() - script_start_time) / 3600, 2), runtimes) + \
                     '删除UFS分区文件失败(rw_delete_fail_times)：{}次\n'.format(rw_delete_fail_times) + \
                     'kill adb进程失败(kill_adb_fail_times)：{}次\n'.format(kill_adb_fail_times) + \
                     '删除UFS分区文件平均时间(rw_delete_time_avg)：{}S\n'.format(rw_delete_time_avg) + \
                     'cefs平均擦除次数(cefs_erase_averagetimes): {}次\n'.format(cefs_erase_averagetimes) + \
                     'cefs最大擦除次数(cefs_erase_maxtimes): {}次\n'.format(cefs_erase_maxtimes) + \
                     'usrdata平均擦除次数(usrdata_erase_averagetimes): {}次\n'.format(usrdata_erase_averagetimes) + \
                     'usrdata最大擦除次数(usrdata_erase_maxtimes): {}次\n'.format(usrdata_erase_maxtimes)

        else:
            # 统计flash参数平均值，最大值，最小值
            cefs_erasetotal = 0
            ufs_erasetotal = 0
            for i in cefs_erasetimes_list:
                cefs_erasetotal += i
            cefs_erase_averagetimes = round(cefs_erasetotal / len(cefs_erasetimes_list), 2)
            cefs_erasetimes_list.sort(reverse=True)
            cefs_erase_maxtimes = round(cefs_erasetimes_list[0], 2)

            for j in ufs_erasetimes_list:
                ufs_erasetotal += j
            usrdata_erase_averagetimes = round(ufs_erasetotal / len(ufs_erasetimes_list), 2)
            ufs_erasetimes_list.sort(reverse=True)
            usrdata_erase_maxtimes = round(ufs_erasetimes_list[0], 2)
            result = '\n[{}]-[{}]\n'.format(script_start_time_format, script_end_time_format) + \
                     '共运行{}H/{}次\n'.format(round((time.time() - script_start_time) / 3600, 2), runtimes) + \
                     '删除UFS分区文件失败(rw_delete_fail_times)：{}次\n'.format(rw_delete_fail_times) + \
                     'kill adb进程失败(kill_adb_fail_times)：{}次\n'.format(kill_adb_fail_times) + \
                     '删除UFS分区文件平均时间(rw_delete_time_avg)：{}S\n'.format(rw_delete_time_avg) + \
                     'cefs平均擦除次数(cefs_erase_averagetimes): {}次\n'.format(cefs_erase_averagetimes) + \
                     'cefs最大擦除次数(cefs_erase_maxtimes): {}次\n'.format(cefs_erase_maxtimes) + \
                     'usrdata平均擦除次数(usrdata_erase_averagetimes): {}次\n'.format(usrdata_erase_averagetimes) + \
                     'usrdata最大擦除次数(usrdata_erase_maxtimes): {}次\n'.format(usrdata_erase_maxtimes)

        print(result)
        with open('统计结果.txt', 'a', encoding='utf-8', buffering=1) as f:
            f.write('-----------压力统计结果start-----------{}-----------压力统计结果end-----------\n'.format(result))
