import hashlib
import json
import time
import websocket
from websocket import create_connection
from tools.qss.logger import logger


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
    def create_qss_task_json(name_group, node_name, ip, tesk_duration=300, task_status=0, task=None):
        """
        修改任务内容并加入队列
        :param name_group:发起任务的用例名称(可以从下发消息中获取)
        :param node_name:发起任务的设备名称(可以从下发消息中获取)
        :param ip:发起任务的设备IP地址(可以从下发消息中获取)
        :param tesk_duration:任务持续时间或者需要增加的时间
        :param task_status:任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
        :param task:任务内容(需要开启网络的mme、enb、ims等文件名称)
        """
        # 新建一个唯一的task_id
        md5 = hashlib.md5()
        start_time_str = str(int(time.time()))[:10]
        md5.update(f'{name_group}{node_name}{start_time_str}'.encode('utf-8'))
        task_id = md5.hexdigest()[:10]

        task_priority_list = [1, 2, 3, 4, 5]  # 优先级
        task_priority = task_priority_list[2]  # 默认优先级为中

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
        }
        json_qss = json.dumps(json_qss_dict)  # 转为json
        logger.info(f'task json : {json_qss}')
        return json_qss

    def on_message(self, ws, message):
        ws.send(f'{self.json_qss}')
        logger.info(f'message:{message}')
        time.sleep(5)
        if 'this band is opened' in message:
            ws.close()
            logger.info('关闭连接')

    @staticmethod
    def on_error(ws, error):
        ws.send('hello2')
        logger.info(f'error:{error}')

    @staticmethod
    def on_close(ws, close_status_code, close_msg):
        ws.send('hello3')
        logger.info(f'close_status_code:{close_status_code}')
        logger.info(f'close_msg:{close_msg}')
        logger.info("### closed ###")

    @staticmethod
    def on_open(ws):
        ws.send('Hello, Server')
        logger.info("Opened connection")
        websocket.enableTrace(True)

    @staticmethod
    def on_ping(ws, message):
        logger.info(ws)
        logger.info(f'message:{message}')
        logger.info("Got a ping! A pong reply has already been automatically sent.")

    @staticmethod
    def on_pong(ws, message):
        logger.info(ws)
        logger.info(f'message:{message}')
        logger.info("Got a pong! No need to respond")

    def connect_qss_socket(self):
        logger.info('connect to qss server...')
        ws = create_connection(self.qss_adress)
        # logger.info(ws.recv())
        logger.info('send a sessage...')
        ws.send(f'Hello, Server, this is {self.local_ip}')
        logger.info('recving...')
        recving_sessage = ws.recv()
        logger.info(recving_sessage)
        if 'qss server recved' in recving_sessage:
            logger.info('connect to qss server success')
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
            logger.error(e)
            return False
        return True

    def end_task(self):
        motify_task = self.motify_task(self.json_qss, 'task_status', 3)
        logger.info(f'task now : {motify_task}')
        ws_n = self.connect_qss_socket()
        time.sleep(3)
        logger.info(f'send to end {motify_task}')
        message_fail = []
        for _ in range(3):
            ws_n.send(motify_task)
            time.sleep(1)
            message_n = ws_n.recv()
            logger.info(message_n)
            if 'is deleted' in message_n:
                logger.info('结束成功，已经删除任务')
                ws_n.close()
                return True
            message_fail.append(message_n)
            time.sleep(3)
        else:
            logger.error(f'结束失败，未收到已结束信息: {message_fail}')
            ws_n.close()
            return False

    def delay_task(self, delay_time=300):
        motify_task_mid = self.motify_task(self.json_qss, 'task_status', 2)
        motify_task = self.motify_task(motify_task_mid, 'tesk_duration', delay_time)
        logger.info(f'task now : {motify_task}')
        ws_n = self.connect_qss_socket()
        time.sleep(3)
        logger.info(f'send to delay {motify_task}')
        message_fail = []
        for __ in range(3):
            ws_n.send(motify_task)
            time.sleep(1)
            message_n = ws_n.recv()
            logger.info(message_n)
            if 'delay task joined' in message_n:
                logger.info('增加测试时间成功')
                ws_n.close()
                return True
            message_fail.append(message_n)
            time.sleep(3)
        else:
            logger.error(f'增加测试时间失败，未收到相关信息: {message_fail}')
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


if __name__ == "__main__":
    websocket.enableTrace(True)
    # qss_ip_now = '10.66.98.199'
    qss_ip_now = '10.66.98.136'
    local_ip_now = '10.66.96.143'
    # ['00101-mme-ims.cfg', '00101-gnb-nsa-b3n78-OK.cfg']、['00101-mme-ims.cfg', '00101-nsa-b2n41-OK.cfg']
    # ['00101-mme-ims.cfg', '00101-gnb-sa-n78.cfg']00101-gnb-sa-n78-DLmax.cfg
    param_dict = {
        'name_group': 'Eth_Backhaul',  # 发起任务的用例名称(可以从下发消息中获取)
        'node_name': 'RG501QEUAA_Ubuntu_USB_ETH_CMCC',  # 发起任务的设备名称(可以从下发消息中获取)
        'ip': local_ip_now,  # 发起任务的设备IP地址(可以从下发消息中获取)
        'tesk_duration': 300,  # 任务持续时间或者需要增加的时间
        'task_status': 0,  # 任务的状态，需要完成的目的(默认为0，0为新建，2为增加测试时间，3为结束测试删除测试任务)
        'task': ['00101-mme-ims.cfg', '00101-gnb-sa-n78-DLmax.cfg'],  # 任务内容(需要开启网络的mme\enb\ims等文件名称列表)
    }
    qss_json_now = ConnectQSS.create_qss_task_json(**param_dict)
    servet_test = ConnectQSS(qss_ip_now, local_ip_now, qss_json_now)

    start_result = servet_test.start_task()
    if start_result:
        logger.info("开始成功")
    else:
        logger.info("开始失败")
        raise Exception
    time.sleep(300)

    delay_result = servet_test.delay_task(60)
    if delay_result:
        logger.info("延时成功")
    else:
        logger.info("延时失败")
        raise Exception
    time.sleep(60)

    for i in range(3):
        end_result = servet_test.end_task()
        if end_result:
            logger.info("结束成功")
            break
        time.sleep(60)
    else:
        logger.info("结束失败")
        raise Exception
