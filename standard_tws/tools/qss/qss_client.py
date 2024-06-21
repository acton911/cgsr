import hashlib
import json
import re
import time
import websocket
from websocket import create_connection
from utils.logger.logging_handles import all_logger
from utils.operate.at_handle import ATHandle


class QSSClinetError(Exception):
    """
    QSS client异常
    """


class ConnectQSS:
    def __init__(self, qss_ip, local_ip, json_qss):
        self.qss_adress = 'ws://' + qss_ip + ':' + '9527'
        self.local_ip = local_ip
        self.json_qss = json_qss

    @staticmethod
    def motify_task(task, motify_key, motify_value):
        # 修改任务内容
        json_2 = json.loads(task)
        json_2[motify_key] = motify_value
        json_3 = json.dumps(json_2)
        return json_3

    @staticmethod
    def create_qss_task_json(name_group, node_name, ip, qss_ip, tesk_duration=300, task_status=0, task=None):
        """
        修改任务内容并加入队列
        :param name_group:发起任务的用例名称(可以从下发消息中获取)
        :param node_name:发起任务的设备名称(可以从下发消息中获取)
        :param ip:发起任务的设备IP地址(可以从下发消息中获取)
        :param tesk_duration:任务持续时间或者需要增加的时间
        :param task_status:任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
        :param task:任务内容(需要开启网络的mme、enb、ims等文件名称)
        :param qss_ip:QSS的ip
        """
        # 新建一个唯一的task_id
        md5 = hashlib.md5()
        start_time_str = str(int(time.time()))[:10]
        md5.update(f'{name_group}{node_name}{start_time_str}'.encode('utf-8'))
        task_id = md5.hexdigest()[:10]

        task_priority_list = [1, 2, 3, 4, 5, 6]  # 优先级P0-P5
        task_priority = task_priority_list[2]  # 默认优先级为中P2

        test_devices = node_name + ':' + ip

        task_status_list = [0, 1, 2, 3]  # 新建-排队中-执行中-已完成
        task_status = task_status_list[task_status]

        json_qss_dict = {
            'task_id': task_id,  # 任务唯一ID
            'task_priority': task_priority,  # 任务优先级
            'task_status': task_status,  # 任务状态
            'task': task,  # 任务内容
            'tesk_duration': tesk_duration,  # 任务持续时间 + 增加测试时间
            'name_group': name_group,  # 任务所属case
            'test_devices': test_devices,  # 任务所属设备
            'qss_ip': qss_ip,
        }
        json_qss = json.dumps(json_qss_dict)  # 转为json
        all_logger.info(f'task json : {json_qss}')
        return json_qss

    def on_message(self, ws, message):
        ws.send(f'{self.json_qss}')
        all_logger.info(f'message:{message}')
        time.sleep(5)
        if 'this band is opened' in message:
            ws.close()
            all_logger.info('关闭连接')

    @staticmethod
    def on_error(ws, error):
        ws.send('hello2')
        all_logger.info(f'error:{error}')

    @staticmethod
    def on_close(ws, close_status_code, close_msg):
        ws.send('hello3')
        all_logger.info(f'close_status_code:{close_status_code}')
        all_logger.info(f'close_msg:{close_msg}')
        all_logger.info("### closed ###")

    @staticmethod
    def on_open(ws):
        ws.send('Hello, Server')
        all_logger.info("Opened connection")
        websocket.enableTrace(True)

    @staticmethod
    def on_ping(ws, message):
        all_logger.info(ws)
        all_logger.info(f'message:{message}')
        all_logger.info("Got a ping! A pong reply has already been automatically sent.")

    @staticmethod
    def on_pong(ws, message):
        all_logger.info(ws)
        all_logger.info(f'message:{message}')
        all_logger.info("Got a pong! No need to respond")

    def connect_qss_socket(self):
        all_logger.info('connect to qss server...')
        ws = create_connection(self.qss_adress)
        # logger.info(ws.recv())
        all_logger.info('send a sessage...')
        ws.send(f'Hello, Server, this is {self.local_ip}')
        all_logger.info('recving...')
        recving_sessage = ws.recv()
        all_logger.info(recving_sessage)
        if 'qss server recved' in recving_sessage:
            all_logger.info('connect to qss server success')
            return ws
        else:
            ws.close()
            raise Exception('connect to qss server fail')

    @staticmethod
    def ping_to_server(ws):
        ws.ping()
        ws.ping("This is an optional ping payload")

    def start_task(self):
        try:
            self.connect_qss_socket_long()
        except Exception as e:
            all_logger.error(e)
            return False
        return True

    def end_task(self):
        motify_task = self.motify_task(self.json_qss, 'task_status', 3)
        all_logger.info(f'task now : {motify_task}')
        ws_n = self.connect_qss_socket()
        all_logger.info(f'send to end {motify_task}')
        message_fail = []
        for i in range(3):
            ws_n.send(motify_task)
            time.sleep(1)
            message_n = ws_n.recv()
            all_logger.info(message_n)
            if 'is deleted' in message_n:
                all_logger.info('结束成功，已经删除任务')
                ws_n.close()
                return True
            message_fail.append(message_n)
            time.sleep(3)
        else:
            all_logger.error(f'结束失败，未收到已结束信息: {message_fail}')
            ws_n.close()
            return False

    def delay_task(self, delay_time=300):
        motify_task_mid = self.motify_task(self.json_qss, 'task_status', 2)
        motify_task = self.motify_task(motify_task_mid, 'tesk_duration', delay_time)
        all_logger.info(f'task now : {motify_task}')
        ws_n = self.connect_qss_socket()
        time.sleep(3)
        all_logger.info(f'send to delay {motify_task}')
        message_fail = []
        for i in range(3):
            ws_n.send(motify_task)
            time.sleep(1)
            message_n = ws_n.recv()
            all_logger.info(message_n)
            if 'delay task joined' in message_n:
                all_logger.info('增加测试时间成功')
                ws_n.close()
                return True
            message_fail.append(message_n)
            time.sleep(3)
        else:
            all_logger.error(f'增加测试时间失败，未收到相关信息: {message_fail}')
            ws_n.close()
            return False

    def connect_qss_socket_long(self):
        websocket.setdefaulttimeout(5)  # 5s超时
        ws = websocket.WebSocketApp(self.qss_adress,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.run_forever()


class WriteSimcard:
    def __init__(self, at_port):
        self.at_port = at_port
        self.at_handle = ATHandle(at_port)

    def get_white_simcard_imsi(self, imsi):
        """
        预算写卡imsi信息(只计算出最后的结果，不做任何写卡操作)
        """
        write_imsi = self.get_imsi_command_need(imsi)
        result_imsi_turn = self.turn_str_sround_by_two(write_imsi)
        result_imsi_turn_list = []
        for i in range(1, len(result_imsi_turn)):
            result_imsi_turn_list.append(result_imsi_turn[i])
        new_simcard_imsi = ''.join(result_imsi_turn_list)

        all_logger.info(f'\r\nnew_simcard_imsi :  {new_simcard_imsi}')
        return new_simcard_imsi

    def get_white_simcard_ccid(self, ccid):
        """
        预算写卡ccid信息(只计算出最后的结果，不做任何写卡操作)
        """
        write_ccid = self.get_ccid_command_need(ccid)
        new_simcard_ccid = self.turn_str_sround_by_two(write_ccid)

        all_logger.info(f'new_simcard_ccid : {new_simcard_ccid}')
        return new_simcard_ccid

    def write_white_simcard(self, imsi, ccid, plmn=''):
        """
        读白卡信息
        AT+CIMI读取IMSI信息
        AT+(Q)ICCID读取ICCID信息

        写入白卡信息
        at+csim=26,"0020000A083838383838383838"  --鉴权获取ADM权限
        at+csim=14,"00A4000C027FF0"   --选择DF文件
        at+csim=14,"00A4000C026F07"   --选择IMSI(6F07文件)
        at+csim=28,"00D600000908{write_imsi}"  --联通46001举例，写入数据4906100123456789
        at+csim=14,"00A40804022FE2"  --选择ICCID文件
        at+csim=30,"00D600000A{write_ccid}"  --98681001234567891234
        at+csim=22,"00A4080C063F007FF06FAD"  --选择EFAD文件
        at+csim=18,"00D60000040000000{plmn_len}"   --plmn长度<=5 plmn_len = 2, >5 plmn_len = 3

        白卡添加EHPLMN
        at+csim=26,"0020000A083838383838383838"  --鉴权获取ADM权限
        at+csim=14,"00A4000C023F00"   --选择MF文件
        at+csim=14,"00A4000C027FF0"   --选择DF文件
        at+csim=14,"00A4000C026FD9"  --选择EHPLMN文件
        at+csim=22,"00D6000006{reversalvalue}FFFFFF"   //联通46001举例，reversalvalue = 64F010

        白卡删除FPLMN
        at+csim=14,"00A4000C023F00"  --选择MF文件
        at+csim=14,"00A4000C027FF0"  --选择DF文件
        at+csim=14,"00A4000C026F7B"  -- 选择FPLMN文件
        at+csim=22,"00D6000006FFFFFFFFFFFF" --更新数据,全删

        读白卡信息
        AT+CIMI读取IMSI信息
        AT+(Q)ICCID读取ICCID信息
        """
        # 读白卡信息
        self.get_cimi()
        self.get_ccid()

        # 写入白卡信息
        self.send_swite_commond_and_check('at+csim=26,"0020000A083838383838383838"')  # 鉴权获取ADM权限
        self.send_swite_commond_and_check('at+csim=14,"00A4000C027FF0"')  # 选择DF文件
        self.send_swite_commond_and_check('at+csim=14,"00A4000C026F07"')  # 选择IMSI(6F07文件)
        if len(imsi) == 15 or len(imsi) == 5 or len(imsi) == 6:
            write_imsi = self.get_imsi_command_need(imsi)
            self.send_swite_commond_and_check(f'at+csim=28,"00D600000908{write_imsi}"')  # 联通46001举例，写入数据4906100123456789
        else:
            raise QSSClinetError(f"imsi格式错误，请确认imsi值是否正确：{imsi}")
        self.send_swite_commond_and_check('at+csim=14,"00A40804022FE2"')  # 选择ICCID文件
        if 8 >= len(ccid) >= 6 or len(ccid) == 20:
            write_ccid = self.get_ccid_command_need(ccid)
            self.send_swite_commond_and_check(f'at+csim=30,"00D600000A{write_ccid}"')  # 写入20位的ccid
        else:
            raise QSSClinetError(f"ccid格式错误，请确认ccid值是否正确：{ccid}")
        self.send_swite_commond_and_check('at+csim=22,"00A4080C063F007FF06FAD"')  # 选择EFAD文件
        if plmn != '' and len(imsi) == 15:
            plmn_len = 3 if len(plmn) > 5 else 2
        elif plmn == '' and len(imsi) <= 6:
            plmn_len = 3 if len(imsi) > 5 else 2
        else:
            raise QSSClinetError(f"plmn格式错误，请确认plmn值是否正确：{plmn}")
        self.send_swite_commond_and_check(f'at+csim=18,"00D60000040000000{plmn_len}"')  # 选择EFAD文件

        # 白卡添加EHPLMN
        self.send_swite_commond_and_check('at+csim=26,"0020000A083838383838383838"')  # 鉴权获取ADM权限
        self.send_swite_commond_and_check('at+csim=14,"00A4000C023F00"')  # 选择MF文件
        self.send_swite_commond_and_check('at+csim=14,"00A4000C027FF0"')  # 选择DF文件
        self.send_swite_commond_and_check('at+csim=14,"00A4000C026FD9"')  # 选择FPLMN文件
        plmn_vlue = ''
        if plmn != '' and len(imsi) == 15:
            plmn_vlue = plmn
        if len(plmn_vlue if plmn_vlue != '' else imsi) == 6:  # 6位数直接使用
            plmn_vlue = plmn_vlue if plmn_vlue != '' else imsi
        elif len(plmn_vlue if plmn_vlue != '' else imsi) == 5:  # 5位数需要加一个F
            s1, s2, s3, s4, s5 = plmn_vlue if plmn_vlue != '' else imsi
            plmn_vlue = s1 + s2 + s3 + 'F' + s4 + s5
        else:
            raise QSSClinetError(f"plmn格式错误，请确认plmn值是否正确：{plmn_vlue}")
        reversalvalue = self.turn_str_sround_by_two(plmn_vlue)
        self.send_swite_commond_and_check(f'at+csim=22,"00D6000006{reversalvalue}FFFFFF"')  # 写plmn, 联通46001举例，reversalvalue = 64F010

        # 白卡删除FPLMN
        self.send_swite_commond_and_check('at+csim=14,"00A4000C023F00"')  # 选择MF文件
        self.send_swite_commond_and_check('at+csim=14,"00A4000C027FF0"')  # 选择DF文件
        self.send_swite_commond_and_check('at+csim=14,"00A4000C026F7B"')  # 选择FPLMN文件
        self.send_swite_commond_and_check('at+csim=22,"00D6000006FFFFFFFFFFFF"')  # 更新数据,全删

        # 切换cfun，重新加载卡
        self.at_handle.send_at("AT+CFUN=0", 10)
        time.sleep(3)
        self.at_handle.send_at("AT+CFUN=1", 10)
        time.sleep(10)
        time.sleep(120)  # 暂时规避x6x切卡异常重启的bug
        # 读白卡信息
        new_simcard_imsi = self.get_cimi()
        new_simcard_ccid = self.get_ccid()

        return new_simcard_imsi, new_simcard_ccid

    def get_ccid_command_need(self, ccid):
        ccid_command_need = ''
        if len(ccid) == 20:  # 直接给完整的ccid值
            change_part = self.turn_str_sround_by_two(ccid)
            ccid_command_need = ccid_command_need + change_part

        if len(ccid) == 6:  # 6位数的ccid开头
            ccid = ccid + '00000123456789'
            change_part = self.turn_str_sround_by_two(ccid)
            ccid_command_need = ccid_command_need + change_part

        if len(ccid) == 7:  # 7位数的ccid开头
            ccid = ccid + '0000123456789'
            change_part = self.turn_str_sround_by_two(ccid)
            ccid_command_need = ccid_command_need + change_part

        if len(ccid) == 8:  # 8位数的ccid开头
            ccid = ccid + '000123456789'
            change_part = self.turn_str_sround_by_two(ccid)
            ccid_command_need = ccid_command_need + change_part

        return ccid_command_need

    def get_imsi_command_need(self, imsi):
        """
        将imsi或者plmn生成写卡需要的格式字符串
        """
        imsi_command_need = imsi[0] + '9'
        if len(imsi) == 15:  # 直接给完整的imsi值
            change_part = self.turn_str_sround_by_two(imsi[1:])
            imsi_command_need = imsi_command_need + change_part

        if len(imsi) == 5:  # 5位数的plmn,例如46001

            imsi = imsi[1:] + '0000123456'
            change_part = self.turn_str_sround_by_two(imsi)
            imsi_command_need = imsi_command_need + change_part

        if len(imsi) == 6:  # 6位数的plmn，例如311480
            imsi = imsi[1:] + '000123456'
            change_part = self.turn_str_sround_by_two(imsi)
            imsi_command_need = imsi_command_need + change_part

        return imsi_command_need

    @staticmethod
    def turn_str_sround_by_two(str_change):
        """
        将字符串中的奇、偶数元素调换位置
        """
        all_logger.info(f"now to change : {str_change}")
        str_list = []
        for i in range(len(str_change)):
            str_list.append(str_change[i])
            if i % 2 != 0:
                str_change_mid = str_list[i]
                str_list[i] = str_list[i - 1]
                str_list[i - 1] = str_change_mid
        str_change_result = "".join(str_list)
        all_logger.info(f"change result : {str_change_result}")
        return str_change_result

    def send_swite_commond_and_check(self, command):
        command_result = ''
        for i in range(3):
            rerurn_command = self.at_handle.send_at(command, 3)
            all_logger.info(rerurn_command)
            command_result = ''.join(re.findall(r'CSIM:\s\d+,"(.*)"', rerurn_command))
            if command_result.startswith('90') or command_result.startswith('61'):
                all_logger.info(f"{command} 执行成功，返回码为: {command_result}")
                break
            time.sleep(10)
        else:
            all_logger.info(f"连续3次 {command} 执行失败，返回码为: {command_result}")
            raise QSSClinetError(f"连续3次 {command} 执行失败，返回码为: {command_result}")

    def get_ccid(self):
        rerurn_ccid = self.at_handle.send_at("AT+CCID", 3)
        ccid_value = ''.join(re.findall(r'CCID:\s(.*)', rerurn_ccid))
        if ccid_value != '':
            all_logger.info(f"当前CCID为 : {ccid_value}")
            return ccid_value
        else:
            all_logger.info("获取CCID失败！")
            return False

    def get_cimi(self):
        rerurn_cimi = self.at_handle.send_at("AT+CIMI", 3)
        cimi_value = ''.join(re.findall(r'(\d.*)', rerurn_cimi))
        if cimi_value != '':
            all_logger.info(f"当前CIMI为 : {cimi_value}")
            return cimi_value
        else:
            all_logger.info("获取CIMI失败！")
            return False


if __name__ == "__main__":
    write_simcard = WriteSimcard('COM13')
    # 预算所写卡信息
    get_new_simcard_imsi_n = write_simcard.get_white_simcard_imsi('46001')
    get_new_simcard_ccid_n = write_simcard.get_white_simcard_ccid('898601')
    # 写卡
    new_simcard_imsi_n, new_simcard_ccid_n = write_simcard.write_white_simcard('46001', '898601')

    all_logger.info(get_new_simcard_imsi_n)
    all_logger.info(get_new_simcard_ccid_n)
    all_logger.info(new_simcard_imsi_n)
    all_logger.info(new_simcard_ccid_n)

    websocket.enableTrace(True)
    qss_ip_now = '10.66.98.199'
    local_ip_now = '10.66.96.143'
    # ['00101-mme-ims.cfg', '00101-gnb-nsa-b3n78-OK.cfg']、['00101-mme-ims.cfg', '00101-nsa-b2n41-OK.cfg']
    param_dict = {
        'name_group': 'Eth_Backhaul',  # 发起任务的用例名称(可以从下发消息中获取)
        'node_name': 'RG501QEUAA_Ubuntu_USB_ETH_CMCC',  # 发起任务的设备名称(可以从下发消息中获取)
        'ip': local_ip_now,  # 发起任务的设备IP地址(可以从下发消息中获取)
        'tesk_duration': 300,  # 任务持续时间或者需要增加的时间
        'task_status': 0,  # 任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
        'task': ['00101-mme-ims.cfg', '00101-gnb-nsa-b3n78-OK.cfg'],  # 任务内容(需要开启网络的mme\enb\ims等文件名称列表)
    }
    qss_json_now = ConnectQSS.create_qss_task_json(**param_dict)
    servet_test = ConnectQSS(qss_ip_now, local_ip_now, qss_json_now)

    start_result = servet_test.start_task()
    if start_result:
        all_logger.info("开始成功")
    else:
        all_logger.info("开始失败")
        raise Exception
    time.sleep(300)

    delay_result = servet_test.delay_task(60)
    if delay_result:
        all_logger.info("延时成功")
    else:
        all_logger.info("延时失败")
        raise Exception
    time.sleep(60)

    end_result = servet_test.end_task()
    if end_result:
        all_logger.info("结束成功")
    else:
        all_logger.info("结束失败")
        raise Exception
