from utils.pages.page_mobile_broadband import PageMobileBroadband
from utils.functions.windows_api import WindowsAPI
import pymysql
import pandas as pd
import serial
import time
import random
import re


class MbnManager:

    def __init__(self):
        self.page_mobile_broadband = PageMobileBroadband()
        self.windows_api = WindowsAPI()

    def mbn_file(self, table_name, file_name):
        # 数据库配置
        mysql_settings = {
            'host': '10.66.94.173',
            'port': 3306,
            'db': 'db_quectel_project_mbn',
            'user': 'root',
            'password': 'Quectel123'
        }
        # 生成文件
        conn = pymysql.connect(**mysql_settings)
        data_sql = pd.read_sql(
            f"SELECT BaseLine , MBNName , MCC_MNC , IIN FROM {table_name} where BaseLine like '%SDX55%'", conn)
        data_sql.to_csv(fr'C:\Users\q\Desktop\{file_name}')
        print('MBN文件生成完成...')
        return True

    def mbn_mcc_mnc_info(self, file_name, mbn_name):
        df_mbn = pd.read_csv(fr'C:\Users\q\Desktop\{file_name}')['MBNName'].values  # MBN列表
        df_mcc_mnc = pd.read_csv(fr'C:\Users\q\Desktop\{file_name}')['MCC_MNC'].values  # MCC_MNC列表
        dict_mbn_mnc_mcc = dict(zip(df_mbn, df_mcc_mnc))
        mnc_mcc = []  # ['0']
        # 遍历字典的key, 也就是MBN name
        for key, value in dict_mbn_mnc_mcc.items():
            value_mbn_mnc_mcc = dict_mbn_mnc_mcc[f'{key}']
            if key == mbn_name and '/' in value_mbn_mnc_mcc:  # '460-01/460-09/460-06'
                # TODO: 此处有坑 '460-01/460-09/460-06'
                value_mbn_mnc_mcc_replace = value_mbn_mnc_mcc.replace('-', '')
                value_mbn_mnc_mcc_split = value_mbn_mnc_mcc_replace.split('/')
                for i in value_mbn_mnc_mcc_split:
                    mnc_mcc.append(i)
            elif key == mbn_name and ' ' in value_mbn_mnc_mcc and ',' not in value_mbn_mnc_mcc:  # '460-01 460-03'
                value_mbn_mnc_mcc_replace = value_mbn_mnc_mcc.replace('-', '')
                value_mbn_mnc_mcc_split = value_mbn_mnc_mcc_replace.split(' ')
                for i in value_mbn_mnc_mcc_split:
                    mnc_mcc.append(i)
            elif key == mbn_name and ',' in value_mbn_mnc_mcc:  # '460-01, 460-03'
                value_mbn_mnc_mcc_replace = value_mbn_mnc_mcc.replace('-', '')
                value_mbn_mnc_mcc_split = value_mbn_mnc_mcc_replace.split(', ')
                for i in value_mbn_mnc_mcc_split:
                    mnc_mcc.append(i)
            elif key == mbn_name and ',' not in value and '/' not in value and ' ' not in value:  # '302-610'
                # TODO: 此处有坑,字符串全部替换为空
                if value_mbn_mnc_mcc == '0':
                    raise Exception('表格IMSI异常:{}'.format(value_mbn_mnc_mcc))
                else:
                    value_mbn_mnc_mcc_replace = value_mbn_mnc_mcc.replace('-', '')
                    mnc_mcc.append(value_mbn_mnc_mcc_replace)
        return mnc_mcc

    def mbn_iin_info(self, file_name, mbn_name):
        df_mbn = pd.read_csv(fr'C:\Users\q\Desktop\{file_name}')['MBNName'].values  # MBN列表
        df_iin = pd.read_csv(fr'C:\Users\q\Desktop\{file_name}')['IIN'].values  # IIN列表
        dict_mbn_iin = dict(zip(df_mbn, df_iin))
        iin = []
        # 遍历字典的key, 也就是MBN name
        for key, value in dict_mbn_iin.items():
            value_mbn_iin = dict_mbn_iin[f'{key}']
            if key == mbn_name and ' ' in value:  # 891480 891004 891005 891012
                # ICCID=IIN+x, 共20位, 表格只有6或7位需要补全
                value_mbn_iin_split = re.split(' ', value_mbn_iin)
                for i in value_mbn_iin_split:
                    iin.append(i)
            elif key == mbn_name and '/' in value:  # 898601/898606/898609
                # ICCID=IIN+x, 共20位, 表格只有6或7位需要补全
                value_mbn_iin_split = re.split('/', value_mbn_iin)
                for i in value_mbn_iin_split:
                    iin.append(i)
            elif key == mbn_name and ' ' not in value and '/' not in value:  # 898601
                # ICCID=IIN+x, 共20位, 表格只有6或7位需要补全
                iin.append(value_mbn_iin)
        return iin


    def send_at(self, command, timeout=5):
        # 发送AT指令
        buf = ''
        buf_list = []
        at_start = time.time()
        at_port_open = serial.Serial(port='com52', baudrate=115200, timeout=timeout)
        at_port_open.write('{}\r\n'.format(command).encode('utf-8'))
        while time.time() - at_start < timeout:
            time.sleep(0.001)
            return_value = at_port_open.readline().decode('utf-8')  # 'AT+CIMI\r\r\n'
            buf_list.append(return_value.replace("'", ''))
            buf += repr(return_value).replace("'", '')  # AT+CIMI\r\r\n00580103254769\r\n\r\nOK\r\n
            if buf != '':
                if 'OK' in buf:
                    return buf, buf_list
        else:
            raise Exception('指令执行异常退出')

    def mnc_mcc_data(self, mbn_name):
        # ISMI=00D6000009080 + xx=15位
        value_mbn_mnc_mcc = self.mbn_mcc_mnc_info('mbn.csv', mbn_name)
        print('value_mbn_mnc_mcc: ', value_mbn_mnc_mcc)
        for mbn_mnc_mcc in value_mbn_mnc_mcc:
            # IMSI=MCC+MNC+MSIN, 共15位, 表格只有5或6位需要补全
            if len(mbn_mnc_mcc) == 6:
                # TODO: 所有MNC_MCC都跑一遍
                int_random = "".join(random.choice("0123456789") for i in range(9))
                # print('检测到{}->MNC_MNC: {} 随机数: {}'.format(mbn_name, mbn_mnc_mcc, int_random))
                return mbn_mnc_mcc, int_random
            elif len(mbn_mnc_mcc) == 5:
                int_random = "".join(random.choice("0123456789") for i in range(10))
                # print('检测到{}->MNC_MNC: {} 随机数: {}'.format(mbn_name, mbn_mnc_mcc, int_random))
                return mbn_mnc_mcc, int_random

    def iccid_data(self, mbn_name):
        # ICCID=00D600000A + xx=20位
        value_mbn_iin = self.mbn_iin_info('mbn.csv', mbn_name)
        for mbn_iin in value_mbn_iin:
            if len(mbn_iin) == 6:
                int_random = "".join(random.choice("0123456789") for i in range(14))
                # print('检测到{}-->IIN: {} 随机数: {}'.format(mbn_name, mbn_iin, int_random))
                return mbn_iin, int_random
            elif len(mbn_iin) == 7:
                int_random = "".join(random.choice("0123456789") for i in range(13))
                # print('检测到{}-->IIN: {} 随机数: {}'.format(mbn_name, mbn_iin, int_random))
                return mbn_iin, int_random
