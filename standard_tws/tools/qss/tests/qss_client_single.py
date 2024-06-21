import json
import time
import websocket
from websocket import create_connection
from tools.qss.logger import logger
from qss_json import json_qss


class ConnectQSS:
    def __init__(self, qss_ip, local_ip):
        self.qss_adress = 'ws://' + qss_ip + ':' + '9527'
        self.local_ip = local_ip
        self.json_qss = json_qss

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

    def connect_qss_socket_long(self):
        websocket.setdefaulttimeout(5)  # 5s超时
        ws = websocket.WebSocketApp(self.qss_adress,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        ws.run_forever()
        # ws.run_forever(dispatcher=rel)  # Set dispatcher to automatic reconnection
        # rel.signal(2, rel.abort)  # Keyboard Interrupt
        # rel.dispatch()


if __name__ == "__main__":
    websocket.enableTrace(True)
    # qss_ip_now = '10.66.129.55'
    # qss_ip_now = '10.66.98.199'
    qss_ip_now = '10.66.98.136'
    local_ip_now = '10.66.96.143'
    servet_test = ConnectQSS(qss_ip_now, local_ip_now)
    # servet_test.connect_qss_socket_long()
    task = {"task_id": "bbded19b8f", "task_priority": 3, "task_status": 3, "task": ['00101-mme-ims.cfg', '00101-gnb-nsa-b3n78-OK.cfg'], "tesk_duration": 10, "name_group": "Eth_Backhaul", "test_devices": "RG501QEUAA_Ubuntu_USB_ETH_CMCC:10.66.98.253"}
    task = json.dumps(task)
    ws_n = servet_test.connect_qss_socket()
    time.sleep(3)
    logger.info(f'send to delete {task}')
    ws_n.send(task)
    time.sleep(1)
    message_n = ws_n.recv()
    logger.info(message_n)
    # ws.ping()
    ws_n.close()
    logger.info('test end')
    """
    """
