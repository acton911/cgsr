import re
import time
import serial
from utils.functions.driver_check import DriverChecker
from utils.operate.at_handle import ATHandle
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxSMSError
from utils.functions.gpio import GPIO


class LinuxSMSManager:
    def __init__(self, at_port, dm_port, debug_port, phone_number, phone_number_pdu, phone_number_hex, phone_number_ucs2,
                 sms_phone_number, sim_imsi, sca_number, sim_iccid, sim_puk, sim_operator, sm_store, me_store):
        self.at_port = at_port
        self.dm_port = dm_port
        self.debug_port = debug_port
        self.phone_number = phone_number
        self.phone_number_pdu = phone_number_pdu
        self.phone_number_hex = phone_number_hex
        self.phone_number_ucs2 = phone_number_ucs2
        self.sms_phone_number = sms_phone_number
        self.sca_number = sca_number
        self.sim_imsi = sim_imsi
        self.sim_iccid = sim_iccid
        self.sim_puk = sim_puk
        self.sim_operator = sim_operator
        self.sm_store = sm_store
        self.me_store = me_store
        self.driver = DriverChecker(at_port, dm_port)
        self.gpio = GPIO()
        self.at_handle = ATHandle(at_port)
        self.write_index = None
        self.recv_index = None
        self.ims = False
        self.mode_pref = False
        time.sleep(5)
    
    def check_ims(self):
        """
        查询版本ims是否默认打开
        """
        result = self.at_handle.send_at('AT+QNVFR="/nv/item_files/ims/IMS_enable"', 0.3)
        if "01" in result:
            all_logger.info('IMS_enable处于启用状态')
        elif "00" in result:
            self.ims = True
            all_logger.info('IMS_enable处于禁用状态，需启用IMS_enable')
            self.at_handle.send_at('AT+QCFG="ims",1', 0.3)
            self.cfun_reset()
        else:
            all_logger.info('IMS_enable指令查询异常')
            raise LinuxSMSError('IMS_enable指令查询异常')
        self.at_handle.send_at('AT+QNVFR="/nv/item_files/ims/IMS_enable"', 0.3)
        return_value = self.at_handle.send_at('AT+QCFG="IMS"', 0.3)
        ims = ''.join(re.findall(r'QCFG: "ims",(\d)', return_value))
        if ims == "1":
            all_logger.info('启用IMS_enable正常')
        else:
            all_logger.info('启用IMS_enable异常')
            raise LinuxSMSError('启用IMS_enable异常')

    def revive_ims(self):
        if self.ims:
            self.ims = False
            self.at_handle.send_at('AT+QCFG="ims",0', 0.3)
            self.cfun_reset()
            self.at_handle.send_at('AT+QNVFR="/nv/item_files/ims/IMS_enable"', 0.3)
            return_value = self.at_handle.send_at('AT+QCFG="IMS"', 0.3)
            ims = ''.join(re.findall(r'QCFG: "ims",(\d)', return_value))
            if ims == "0":
                all_logger.info('恢复IMS_enable配置为0正常')
            else:
                all_logger.info('恢复IMS_enable异常')
                raise LinuxSMSError('恢复IMS_enable异常')
        else:
            pass
    
    def configure_cmgf(self, parameter):
        """
        配置短消息模式
        parameter: 0/1, 0:PDU模式;1:文本模式
        """
        if parameter == 0:
            self.at_handle.send_at('AT+CMGF=0', 0.3)
            return_value = self.at_handle.send_at('AT+CMGF?', 0.3)
            if '+CMGF: 0' in return_value:
                all_logger.info('配置"CMGF=0"成功')
            else:
                all_logger.info('配置"CMGF=0"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"CMGF=0"异常')
        elif parameter == 1:
            self.at_handle.send_at('AT+CMGF=1', 0.3)
            return_value = self.at_handle.send_at('AT+CMGF?', 0.3)
            if '+CMGF: 1' in return_value:
                all_logger.info('配置"CMGF=1"成功')
            else:
                all_logger.info('配置"CMGF=1"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"CMGF=1"异常')
    
    def configure_cscs(self, mode):
        """
        设置Text编码模式
        mode：GSM/UCS2/IRA
        """
        if mode == 'GSM':
            self.at_handle.send_at('AT+CSCS="GSM"', 0.3)
            return_value = self.at_handle.send_at('AT+CSCS?', 0.3)
            if '+CSCS: "GSM"' in return_value:
                all_logger.info('配置CSCS="GSM"成功')
            else:
                all_logger.info('配置CSCS="GSM"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置CSCS=GSM"异常')
        elif mode == 'UCS2':
            self.at_handle.send_at('AT+CSCS="UCS2"', 0.3)
            return_value = self.at_handle.send_at('AT+CSCS?', 0.3)
            if '+CSCS: "UCS2"' in return_value:
                all_logger.info('配置CSCS="UCS2"成功')
            else:
                all_logger.info('配置CSCS="UCS2"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置CSCS="UCS2"异常')
        elif mode == 'IRA':
            self.at_handle.send_at('AT+CSCS="IRA"', 0.3)
            return_value = self.at_handle.send_at('AT+CSCS?', 0.3)
            if '+CSCS: "IRA"' in return_value:
                all_logger.info('配置CSCS="IRA"成功')
            else:
                all_logger.info('配置CSCS="IRA"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置CSCS="IRA"异常')
    
    def configure_cpms(self, parameter):
        """
        配置短消息首选存储位置
        parameter:ME/SM
        """
        if parameter == 'ME':
            self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 0.3)
            self.at_handle.send_at('AT+CMGD=0,4', 10)
            return_value = self.at_handle.send_at('AT+CPMS?', 0.3)
            if f'+CPMS: "ME",0,{str(self.me_store)}' in return_value:
                all_logger.info('配置"ME"成功，且短信数量当前为0')
            else:
                all_logger.info('配置"ME"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"ME"异常')
        elif parameter == 'SM':
            self.at_handle.send_at('AT+CPMS="SM","SM","SM"', 0.3)
            self.at_handle.send_at('AT+CMGD=0,4', 10)
            return_value = self.at_handle.send_at('AT+CPMS?', 0.3)
            if f'+CPMS: "SM",0,{str(self.sm_store)}' in return_value:
                all_logger.info('配置"SM"成功，且短信数量当前为0')
            else:
                all_logger.info('配置"SM"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"SM"异常')
    
    def configure_csmp(self, fo, vp, pid, dcs):
        """
         设置短消息文本模式参数
         fo, vp, pid, dcs根据指令AT+CSMP进行对应传参
        """
        self.at_handle.send_at(f'AT+CSMP={fo},{vp},{pid},{dcs}', 0.3)
        return_value = self.at_handle.send_at('AT+CSMP?', 0.3)
        if f'+CSMP: {fo},{vp},{pid},{dcs}' in return_value:
            all_logger.info('配置"CSMP"成功')
        else:
            all_logger.info('配置"CSMP"异常，当前指令返回信息为{}'.format(return_value))
            raise LinuxSMSError('配置"CSMP"异常')
    
    def configure_cnmi(self, mode, mt, bm, ds, bfr):
        """
        设置Text编码模式
         mode, mt, bm, ds, bfr根据指令AT+CNMI进行对应传参
        """
        self.at_handle.send_at(f'AT+CNMI={mode},{mt},{bm},{ds},{bfr}', 0.3)
        return_value = self.at_handle.send_at('AT+CNMI?', 0.3)
        if f'+CNMI: {mode},{mt},{bm},{ds},{bfr}' in return_value:
            all_logger.info('配置"CNMI"成功')
        else:
            all_logger.info('配置"CNMI"异常，当前指令返回信息为{}'.format(return_value))
            raise LinuxSMSError('配置"CNMI"异常')
    
    def select_csdh(self, parameter):
        """
        配置短消息模式
        parameter： 0/1
        """
        if parameter == 0:
            self.at_handle.send_at('AT+CSDH=0', 0.3)
            return_value = self.at_handle.send_at('AT+CSDH?', 0.3)
            if '+CSDH: 0' in return_value:
                all_logger.info('配置"CSDH=0"成功')
            else:
                all_logger.info('配置"CSDH=0"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"CSDH=0"异常')
        if parameter == 1:
            self.at_handle.send_at('AT+CSDH=1', 0.3)
            return_value = self.at_handle.send_at('AT+CSDH?', 0.3)
            if '+CSDH: 1' in return_value:
                all_logger.info('配置"CSDH=1"成功')
            else:
                all_logger.info('配置"CSDH=1"异常，当前指令返回信息为{}'.format(return_value))
                raise LinuxSMSError('配置"CSDH=1"异常')
    
    def select_cmgl(self, mode, context):
        """
        mode:列举内容为REC UNREAD/REC READ/STO UNSENT/STO SENT
        context：匹配文本内容
        """
        re_value = self.at_handle.send_at(f'AT+CMGL={mode}', 0.3)
        if context != '' and f'{context}' in re_value:
            if f'{mode}' in ['"REC UNREAD"', '0']:
                all_logger.info("列举未读SMS正常")
            elif f'{mode}' in ['"REC READ"', '1']:
                all_logger.info("列举已读SMS正常")
            elif f'{mode}' in ['"STO UNSENT"', '2']:
                all_logger.info("列举未发SMS正常")
            elif f'{mode}' in ['"STO SENT"', '3']:
                all_logger.info("列举已发SMS正常")
            elif f'{mode}' in ['"ALL"', '4']:
                all_logger.info("列举SMS正常")
            else:
                all_logger.info("列举SMS异常")
                raise LinuxSMSError("列举SMS异常")
        elif context == '' and 'OK' in re_value:
            if f'{mode}' in ['"REC UNREAD"', '0']:
                all_logger.info("列举未读SMS正常")
            elif f'{mode}' in ['"REC READ"', '1']:
                all_logger.info("列举已读SMS正常")
            elif f'{mode}' in ['"STO UNSENT"', '2']:
                all_logger.info("列举未发SMS正常")
            elif f'{mode}' in ['"STO SENT"', '3']:
                all_logger.info("列举已发SMS正常")
            elif f'{mode}' in ['"ALL"', '4']:
                all_logger.info("列举为空")
            else:
                all_logger.info("列举SMS异常")
                raise LinuxSMSError("列举SMS异常")
        else:
            all_logger.info("指令参数异常")
            raise LinuxSMSError("指令参数异常")
    
    def write_a_b_msg(self, context):
        self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW')
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            if context == '1A':
                at_port.write(bytes.fromhex(f'{context}'))
                self.write_index_msg()
            elif context == '1B':
                re_value = at_port.write(bytes.fromhex(f'{context}'))
                all_logger.info("发送1B后返回结果为{}".format(re_value))
                if 'OK' in re_value:
                    all_logger.info("发送1B后检测到OK上报")
                else:
                    all_logger.info("发送1B后60s未检测到OK上报")
                    raise LinuxSMSError("发送1B后60s未检测到OK上报")
            else:
                all_logger.info("指令参数异常")
                raise LinuxSMSError("指令参数异常")
    
    def write_msg(self, mode, context):
        """
        在获取到>后进行短消息编写，并获取编写成功后的index
        mode:GSM/HEX
        context：短信内容
        """
        all_logger.info("写入短信内容为：{}".format(context))
        try:
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
                if mode == 'GSM':
                    at_port.write(f'{context}'.encode('utf-8'))
                    at_port.write(chr(0x1A).encode())
                    self.write_index_msg()
                elif mode == 'HEX':
                    at_port.write(bytes.fromhex(f'{context}'))
                    at_port.write(chr(0x1A).encode())
                    self.write_index_msg()
        except Exception:  # noqa
            all_logger.info("写短信失败")
            raise LinuxSMSError("写短信失败")
    
    def write_pdu_msg(self, context):
        """
        在获取到>后进行短消息编写，并获取编写成功后的index
        context：短信内容
        """
        all_logger.info("写入短信内容为：{}".format(context))
        try:
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW=12')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
                at_port.write(f'{context}'.encode('utf-8'))
                at_port.write(chr(0x1A).encode())
                self.write_index_msg()
        except Exception:  # noqa
            all_logger.info("写短信失败")
            raise LinuxSMSError("写短信失败")
    
    def write_msg_full(self):
        """
        写短信将存储空间占满
        :return:
        """
        save_size = self.at_handle.send_at('AT+CPMS?', 10)
        msg_total = int(re.findall(r'\+CPMS: "SM",\d+,(\d+)', save_size)[0])
        cur_msg = int(re.findall(r'\+CPMS: "SM",(\d+)', save_size)[0])
        self.at_handle.send_at('AT+CMGF=1', 10)
        all_logger.info('写短信占满存储空间')
        for i in range(msg_total - cur_msg):
            try:
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGW')
                self.write_msg('GSM', context='test')
            except Exception:  # noqa
                pass
            time.sleep(0.3)
        current_size = self.at_handle.send_at('AT+CPMS?', 10)
        current_num = int(re.findall(r'\+CPMS: "SM",(\d+)', current_size)[0])
        if current_num != msg_total:
            all_logger.info('短信未写满，继续写满短信')
            self.write_msg_full()
        else:
            all_logger.info('短信已写满')
    
    def sms_read_fail(self, index):
        value = self.at_handle.send_at(f'AT+CMGR={index}', 0.3)
        if '+CMS ERROR: 321' in value:
            all_logger.info("AT+CMGR读取不存在SMS上报321，正常")
        else:
            all_logger.info("AT+CMGR读取不存在SMS上报321异常")
            raise LinuxSMSError("AT+CMGR读取不存在SMS上报321异常")
    
    def sms_read(self, mode, context):
        """
        读取短信：根据REC UNREAD/REC READ/STO UNSENT/STO SENT四种状态进行分类
        """
        if mode == 'REC UNREAD':
            read_value = self.at_handle.send_at(f'AT+CMGR={self.recv_index}', 0.3)
            status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"REC UNREAD"', '0']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+CMGR读取未读SMS正常")
                else:
                    all_logger.info("AT+CMGR读取SMS状态正常，短信内容需要人工check")
            else:
                raise LinuxSMSError("AT+CMGR读取未读SMS异常")
        elif mode == 'REC READ':
            read_value = self.at_handle.send_at(f'AT+CMGR={self.recv_index}', 0.3)
            status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"REC READ"', '1']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+CMGR读取已读SMS正常")
                else:
                    all_logger.info("AT+CMGR读取SMS状态正常，短信内容需要人工check")
            else:
                all_logger.info("AT+CMGR读取已读SMS异常{}".format(read_value))
                raise LinuxSMSError("AT+CMGR读取已读SMS异常")
        elif mode == 'STO UNSENT':
            read_value = self.at_handle.send_at(f'AT+CMGR={self.write_index}', 0.3)
            status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"STO UNSENT"', '2']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+CMGR读取未发SMS正常")
                else:
                    all_logger.info("AT+CMGR读取未发SMS正常，短信内容需要人工check")
            else:
                all_logger.info("AT+CMGR读取未发SMS异常{}".format(read_value))
                raise LinuxSMSError("AT+CMGR读取未发SMS异常")
        elif mode == 'STO SENT':
            read_value = self.at_handle.send_at(f'AT+CMGR={self.write_index}', 0.3)
            status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"STO SENT"', '3']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+CMGR读取已发SMS正常")
                else:
                    all_logger.info("AT+CMGR读取已发SMS正常，短信内容需要人工check")
            else:
                all_logger.info("AT+CMGR读取已发SMS异常{}".format(read_value))
                raise LinuxSMSError("AT+CMGR读取已发SMS异常")
        elif mode in ['"ALL"', '4']:
            read_value = self.at_handle.send_at(f'AT+CMGR={self.write_index}', 10)
            if 'OK' in read_value:
                all_logger.info("AT+CMGR读取已发SMS正常")
            else:
                all_logger.info("AT+CMGR读取已发SMS异常{}".format(read_value))
                raise LinuxSMSError("AT+CMGR读取已发SMS异常")
        else:
            all_logger.info("指令参数异常")
            raise LinuxSMSError("指令参数异常")
    
    def sms_qread(self, mode, context):
        read_value = self.at_handle.send_at(f'AT+QCMGR={self.recv_index}', 0.3)
        if mode == 'REC UNREAD':
            status = ''.join(re.findall(r'QCMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"REC UNREAD"', '0']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+QCMGR读取未读SMS正常")
                else:
                    all_logger.info("AT+QCMGR读取SMS状态正常，短信内容需要人工check")
            else:
                raise LinuxSMSError("AT+QCMGR读取未读SMS异常")
        elif mode == 'REC READ':
            status = ''.join(re.findall(r'QCMGR: (\d+|\"\w+\s\w+\")', read_value))
            if status in ['"REC READ"', '1']:
                if context != '' and f'{context}' in read_value:
                    all_logger.info("AT+QCMGR读取已读SMS正常")
                else:
                    all_logger.info("AT+QCMGR读取SMS状态正常，短信内容需要人工check")
            else:
                all_logger.info("AT+QCMGR读取已读SMS异常{}".format(read_value))
                raise LinuxSMSError("AT+QCMGR读取已读SMS异常")
        else:
            all_logger.info("指令参数异常")
            raise LinuxSMSError("指令参数异常")
    
    def send_cmss_sms_vabt(self):
        """
        发送GSM格式短消息
        """
        try:
            self.at_handle.readline_keyword('+CMSS', 'OK', at_flag=True, at_cmd=f'AT+CMSS={self.write_index},"{self.phone_number}"')
            all_logger.info('模块发送短信成功')
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
            
    def send_cmss_sms(self, mode):
        """
        发送GSM格式短消息
        """
        try:
            if mode == 'GSM':
                self.at_handle.readline_keyword('+CMSS', 'OK', at_flag=True, at_cmd=f'AT+CMSS={self.write_index},"{self.phone_number}"')
            if mode == 'UCS2':
                self.at_handle.readline_keyword('+CMSS', 'OK', at_flag=True, at_cmd=f'AT+CMSS={self.write_index},"{self.phone_number_ucs2}"')
            all_logger.info('模块发送短信成功')
            self.recv_index_msg()
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def send_full_sms(self):
        """
        发送GSM格式短消息
        """
        self.at_handle.readline_keyword('+CMSS', 'OK', at_flag=True, at_cmd=f'AT+CMSS={self.write_index},"{self.phone_number}"')
        try:
            self.at_handle.readline_keyword('+QIND: "smsfull","SM"', timout=60)
            all_logger.info("模块发送短信提示存储空间已满")
        except Exception:  # noqa
            all_logger.info("模块发送短信未提示存储空间已满")
            raise LinuxSMSError("模块发送短信未提示存储空间已满")
    
    def send_cmgs_gsm_sms(self, content):
        try:
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{self.phone_number}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', 'OK', timout=30)
            all_logger.info('模块发送短信成功')
            self.recv_index_msg()
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def send_cmgs_ucs2_sms(self, content):
        try:
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+CMGS="{self.phone_number_ucs2}"')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
            self.at_handle.readline_keyword('+CMGS', 'OK', timout=30)
            all_logger.info('模块发送短信成功')
            self.recv_index_msg()
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def send_cmgs_pdu_sms(self, parameter):
        """
        发送GSM格式短消息
        """
        try:
            if parameter == 155:
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGS=155')
                with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                    _port.write(f'0011000D9168{self.phone_number_pdu}00F201A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9'.encode('utf-8'))
                    _port.write(chr(0x1A).encode())
                    self.at_handle.readline_keyword('+CMGS', 'OK', timout=30)
                    all_logger.info("发送短信成功")
                    self.recv_index_msg()
            elif parameter == 28:
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd='AT+CMGS=28')
                with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                    _port.write(f'0031000BA1{self.phone_number_pdu}00F3011031D98C56B3DD7031D98C56B3DD70'.encode('utf-8'))
                    _port.write(chr(0x1A).encode())
                    self.at_handle.readline_keyword('+CMGS', 'OK', timout=30)
                    all_logger.info("发送短信成功")
                    self.at_handle.readline_keyword('+CDS', timout=120)
                    all_logger.info("接收短信成功")
        except Exception:  # noqa
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(chr(0x1B).encode())
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def check_qcmgs(self, uid, msg_seg, msg_total):
        """
        uid：范围（0-255）
        msg_seg：范围为（0-15）
        msg_total： 的范围为（0-15）
        """
        re_value = self.at_handle.send_at(f'AT+QCMGS="{self.phone_number}",{uid},{msg_seg},{msg_total}', 0.3)
        if 'ERROR' in re_value:
            all_logger.info("指令参数异常")
        elif 'OK' in re_value:
            all_logger.info("指令响应正常")
        else:
            all_logger.info("QCMG指令异常")
            raise LinuxSMSError("QCMG指令异常")
        
    def send_qcmgs(self, mode, uid, msg_seg, msg_total, content, value):
        """
        uid：范围（0-255）
        msg_seg：范围为（0-15）
        msg_total： 的范围为（0-15）
        content： 短信内容
        value： 1：发生成功，0：发生失败
        """
        try:
            if mode == 'GSM':
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+QCMGS="{self.phone_number}",{uid},{msg_seg},{msg_total}')
            if mode == 'UCS2':
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+QCMGS="{self.phone_number_ucs2}",{uid},{msg_seg},{msg_total}')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
                if value == 1:
                    self.at_handle.readline_keyword('+QCMGS', 'OK', timout=30)
                    all_logger.info('模块发送短信成功')
                    self.recv_index_msg()
                elif value == 0:
                    self.at_handle.readline_keyword('+CMS ERROR: 305', timout=30)
                    all_logger.info('模块发送短信成功')
                else:
                    all_logger.info("指令参数异常")
                    raise LinuxSMSError("指令参数异常")
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
        
    def send_qcmgs_cds(self, uid, msg_seg, msg_total, content):
        """
        仅针对cds自动上报
        """
        try:
            self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+QCMGS="{self.phone_number_ucs2}",{uid},{msg_seg},{msg_total}')
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(f'{content}'.encode('utf-8'))
                _port.write(chr(0x1A).encode())
                self.at_handle.readline_keyword('+QCMGS', 'OK', timout=30)
                all_logger.info('模块发送短信成功')
                self.at_handle.readline_keyword('+CDS', timout=120)
                all_logger.info("接收短信成功")
        except Exception:  # noqa
            with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                _port.write(chr(0x1B).encode())
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def send_qcmgs_phone(self, uid, msg_seg, msg_total, content):
        """
        uid：范围（0-255）
        msg_seg：范围为（0-15）
        msg_total： 的范围为（0-15）
        content： 短信内容
        value： 1：发生成功，0：发生失败
        """
        try:
            if self.sms_phone_number != '':
                self.at_handle.readline_keyword('>', at_flag=True, at_cmd=f'AT+QCMGS="{self.sms_phone_number}",{uid},{msg_seg},{msg_total}')
                with serial.Serial(self.at_port, baudrate=115200, timeout=0) as _port:
                    _port.write(f'{content}'.encode('utf-8'))
                    _port.write(chr(0x1A).encode())
                    self.at_handle.readline_keyword('+QCMGS', 'OK', timout=30)
                    all_logger.info('模块发送短信成功')
            elif self.sms_phone_number == '':
                all_logger.info("DBeaver数据库未填写sms_phone_number信息")
                raise LinuxSMSError("DBeaver数据库未填写sms_phone_number信息")
            else:
                all_logger.info("DBeaver数据库未填写sms_phone_number信息异常")
                raise LinuxSMSError("DBeaver数据库未填写sms_phone_number信息异常")
        except Exception:  # noqa
            all_logger.info("模块发送短信失败")
            raise LinuxSMSError("模块发送短信失败")
    
    def write_index_msg(self):
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            start_time = time.time()
            while True:
                recv_cmgw_data = self.at_handle.readline(at_port)
                if recv_cmgw_data != '' and '+CMGW' in recv_cmgw_data:
                    self.write_index = ''.join(re.findall(r'CMGW: (\d+)', recv_cmgw_data))
                    all_logger.info('短信存储index为：{}'.format(self.write_index))
                    return self.write_index
                elif recv_cmgw_data != '' and '+CMGS' in recv_cmgw_data:
                    self.write_index = ''.join(re.findall(r'CMGS: (\d+)', recv_cmgw_data))
                    all_logger.info('短信存储index为：{}'.format(self.write_index))
                    return self.write_index
                elif time.time() - start_time > 10:
                    all_logger.info("10s未获取到短息存储位置index")
                    raise LinuxSMSError("10s未获取到短息存储位置index")
    
    def recv_index_msg(self):
        """
        获取接受到的短信的index
        """
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            start_time = time.time()
            while True:
                recv_cmgw_data = self.at_handle.readline(at_port)
                if recv_cmgw_data != '' and '+CMT' in recv_cmgw_data:
                    self.recv_index = ''.join(re.findall(r'"(?:SM|ME)",(\d)', recv_cmgw_data))
                    all_logger.info('短息存储位置index为{}\n'.format(self.recv_index))
                    return self.recv_index
                elif recv_cmgw_data != '' and '+CMTI' in recv_cmgw_data:
                    self.recv_index = ''.join(re.findall(r'"(?:SM|ME)",(\d)', recv_cmgw_data))
                    all_logger.info('短息存储位置index为{}\n'.format(self.recv_index))
                    return self.recv_index
                elif time.time() - start_time > 120:
                    self.at_handle.send_at('AT+CPMS?', 10)
                    all_logger.info("未收到短信上报")
                    raise LinuxSMSError("未收到短信上报")

    def sms_twice_read(self, mode, context, freq):
        """
        再次读取收到短信freq次
        """
        for i in range(freq):
            if mode == 'REC UNREAD':
                read_value = self.at_handle.send_at(f'AT+CMGR={self.recv_index}', 0.3)
                status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
                if status in ['"REC READ"', '1']:
                    if context != '' and f'{context}' in read_value:
                        all_logger.info("AT+CMGR读取已读SMS正常")
                    else:
                        all_logger.info("AT+CMGR读取SMS状态正常，短信内容需要人工check")
                else:
                    all_logger.info("AT+CMGR读取已读SMS异常{}".format(read_value))
                    raise LinuxSMSError("AT+CMGR读取已读SMS异常")
            elif mode == 'REC UNSENT':
                read_value = self.at_handle.send_at(f'AT+CMGR={self.write_index}', 0.3)
                status = ''.join(re.findall(r'CMGR: (\d+|\"\w+\s\w+\")', read_value))
                if status in ['"STO SENT"', '3']:
                    if context != '' and f'{context}' in read_value:
                        all_logger.info("AT+CMGR读取已发SMS正常")
                    else:
                        all_logger.info("AT+CMGR读取已发SMS正常，短信内容需要人工check")
                else:
                    all_logger.info("AT+CMGR读取已发SMS异常{}".format(read_value))
                    raise LinuxSMSError("AT+CMGR读取已发SMS异常")
            else:
                all_logger.info("指令参数异常")
                raise LinuxSMSError("指令参数异常")
    
    def sms_twice_list(self, freq):
        """
        再次读取收到短信freq次
        """
        for i in range(freq):
            re_value = self.at_handle.send_at('AT+CMGL="REC UNREAD"', 0.3)
            if 'OK' in re_value and '+CMGR: "REC UNREAD"' not in re_value:
                all_logger.info("二次列举SMS正常")
            else:
                all_logger.info("二次列举SMS异常")
                raise LinuxSMSError("二次列举SMS异常")
    
    def check_msg_number(self, parameter, num):
        """
        检查短信数量是否正常
        :param parameter: 短信存储空间位置ME or SM
        :param num: 预期收到短信数量
        :return:
        """
        value = self.at_handle.send_at('AT+CPMS?', 10)
        if f'+CPMS: "{parameter}",{num}' in value:
            all_logger.info('短信数量核对正常')
        else:
            all_logger.info(f'期望接收到{num}条短信，实际查询数量不符')
            raise LinuxSMSError(f'期望接收到{num}条短信，实际查询数量不符')
    
    def sms_init(self):
        """
        恢复默认值
        """
        self.at_handle.send_at('AT+CMGF=0', 0.3)
        self.at_handle.send_at('AT+CPMS="ME","ME","ME"', 0.3)
        self.at_handle.send_at('AT+CSCS="GSM"', 0.3)
        self.at_handle.send_at('AT+CSMP=17,167,0,0', 0.3)
        self.at_handle.send_at('AT+CNMI=2,1,0,0,0', 0.3)
        self.at_handle.send_at('AT+CMGD=0,4', 0.3)
    
    def cfun_reset(self):
        """
        CFUN1_1重启模块
        :return:
        """
        self.at_handle.send_at('AT+CFUN=1,1', 10)
        self.driver.check_usb_driver_dis()
        self.driver.check_usb_driver()
        self.read_poweron_urc()
        
    def read_poweron_urc(self, timeout=60):
        start_time = time.time()
        urc_value = []
        count = 0
        with serial.Serial(self.at_port, baudrate=115200, timeout=0) as at_port:
            while time.time() - start_time < timeout:
                read_value = self.at_handle.readline(at_port)
                if read_value != '':
                    urc_value.append(read_value)
                continue
            for urc in urc_value:
                if urc == '+QIND: PB DONE\r\n':
                    count = count + 1
            all_logger.info('{}s检测URC上报内容为{},且pb done上报{}次'.format(timeout, urc_value, count))
            
    def check_mode_pref(self):
        """
        查询版本模块是否支持WCDMA是否默认打开
        """
        result = self.at_handle.send_at('AT+QNWPREFCFG="mode_pref"', 0.3)
        if "AUTO" in result:
            all_logger.info('模组支持WCDMA')
        else:
            self.mode_pref = True
            all_logger.info('模组不支持WCDMA')

    def revive_mode_pref(self):
        """
        恢复默认网络支持
        """
        if self.mode_pref:
            self.mode_pref = False
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",LTE:NR5G', 0.3)
        else:
            self.at_handle.send_at('AT+QNWPREFCFG="mode_pref",AUTO', 0.3)
