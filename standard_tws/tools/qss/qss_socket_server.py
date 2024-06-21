import json
import queue
import time
from logger import logger
import websockets
import asyncio
from threading import Thread
import public_variable


class QSSSocketServer(Thread):
    def __init__(self, recv_queue: queue.Queue, run_queue: queue.Queue):
        super().__init__()
        self.recv_queue = recv_queue
        self.run_queue = run_queue
        self.qss_server_ip = '0.0.0.0'
        self.qss_server_port = '9527'
        self.que_index = 1

    def query_task_content(self, task_id, content):
        """
        查询指定任务的指定内容
        :param task_id:任务ID
        :param content:需要查询的内容
        :return:
        """
        logger.info(task_id)
        queue_now = self.recv_queue.queue
        for i in range(self.recv_queue.qsize()):
            task = queue_now[i]
            logger.info(json.loads(task[2])["task_id"])
            if json.loads(task[2])["task_id"] == task_id:
                logger.info(f'已找到{task_id}任务')
                logger.info(f'所查询内容为:{json.loads(task[2])[content]}')
                # self.recv_queue.put(task)
                return json.loads(task[2])[content]
            # else:
            #     self.recv_queue.put(task)
        else:
            logger.info(f'未找到该任务：{task_id}\t\n{self.recv_queue.queue}')

    def detele_task(self, task_id):
        """
        删除任务
        :param task_id:
        :return:
        """
        logger.info('delete recv')
        for i in range(self.recv_queue.qsize()):
            task = self.recv_queue.get()
            logger.info(self.recv_queue.queue)
            logger.info(json.loads(task[2])["task_id"])
            if json.loads(task[2])["task_id"] == task_id:
                logger.info(f'已经删除{task_id}任务')
                logger.info(self.recv_queue.queue)
                break
            else:
                self.recv_queue.put(task)
        else:
            logger.info(f'未找到该任务：{task_id}')
        logger.info('delete run')
        for j in range(self.run_queue.qsize()):
            task = self.run_queue.get()
            logger.info(self.run_queue.queue)
            logger.info(json.loads(task[2])["task_id"])
            if json.loads(task[2])["task_id"] == task_id:
                logger.info(f'已经删除{task_id}任务')
                logger.info(self.run_queue.queue)
                break
            else:
                self.run_queue.put(task)
        else:
            logger.info(f'未找到该任务：{task_id}')

    def motify_task_to_end(self, task_id):
        """
        把任务从正在执行改为已完成
        :param task_id:
        :return:
        """
        for i in range(self.recv_queue.qsize()):
            task = self.recv_queue.get()
            if json.loads(task[2])["task_id"] == task_id:
                logger.info(f'更新{task_id}任务状态为已完成')
                self.motify_task_with_priority(task, 'task_status', 3)
            else:
                self.recv_queue.put(task)
        else:
            logger.info(f'未找到该任务：{task_id}')

    def motify_task_with_priority(self, task_witth_priority, motify_key, motify_value):
        """
        修改任务内容并加入队列
        :param task_witth_priority:待修改带优先级的任务
        :param motify_key:待修改内容的key
        :param motify_value:需要修改的内容
        :return:
        """
        logger.info('now to motify task')
        logger.info(json.loads(task_witth_priority[2]))
        task = task_witth_priority[2]
        task_priority = json.loads(task_witth_priority[2])['task_priority']
        task_index_que = task_witth_priority[1]
        json_motify = self.motify_task(task, motify_key, motify_value)
        self.recv_queue.put((task_priority, task_index_que, json_motify))  # 不在则加入任务队列并修改任务状态
        # self.run_queue.put((task_priority, task_index_que, json_motify))  # 不在则加入任务队列并修改任务状态

    # 握手
    @staticmethod
    async def serverHands(websocket):
        while True:
            recv_text = await websocket.recv()
            logger.info("recv text :  " + recv_text)
            if "Hello, Server" in recv_text:
                logger.info("connect to client success")
                await websocket.send(f"qss server recved : {recv_text} ")
                return True
            else:
                await websocket.send(f"connected fail : {recv_text}")

    # 接收从客户端发来的消息
    async def serverRecv(self, websocket):
        while True:
            logger.info('wait to recv message...')
            recv_text = await websocket.recv()
            logger.info(f"recv: {recv_text}")
            if self.is_json(recv_text):
                recv_text_loads = json.loads(recv_text)
                recv_task_status = recv_text_loads['task_status']
                if recv_text_loads['task_id'] in str(self.recv_queue.queue):  # 任务是否在队列中
                    query_task_status = self.query_task_content(recv_text_loads['task_id'], 'task_status')
                    if query_task_status == 2:  # 队列中的任务状态为正在执行的任务，更新为3并通知客户端可以使用了
                        if recv_task_status == 0:
                            self.motify_task_to_end(recv_text_loads['task_id'])
                            logger.info(f'此任务已经开启，可以开始使用：{recv_text_loads["task"]}')
                            await websocket.send(f'this band is opened : {recv_text_loads["task"]}')
                        elif recv_task_status == 2:
                            self.motify_task_to_end(recv_text_loads['task_id'])
                            logger.info(f'已收到增加测试时间请求任务：{recv_text_loads["task"]}')
                            self.detele_task(recv_text_loads['task_id'])  # 先删除原有任务，再补上一个高优先级任务
                            json_motify = self.motify_task(recv_text, 'task_status', 1)
                            json_motify2 = self.motify_task(json_motify, 'task_priority', 2)
                            self.recv_queue.put((2, self.que_index, json_motify2))  # 因为是增加测试时间，直接提高优先级让它插队
                            self.run_queue.put((2, self.que_index, json_motify2))  # 因为是增加测试时间，直接提高优先级让它插队
                            logger.info("*"*99)
                            logger.info(json_motify2)
                            logger.info("*"*99)
                            self.que_index += 1
                            logger.info(self.recv_queue.queue)
                            await websocket.send(f"delay task joined: {recv_text}")
                        elif recv_task_status == 3:
                            logger.info(f"已收到客户端任务完成信息，删除队列中的{recv_text_loads['task_id']}")
                            public_variable.motify_time(time_mofify=0)
                            self.detele_task(recv_text_loads['task_id'])
                            await websocket.send(f"task {recv_text_loads['task_id']} is deleted")
                    elif query_task_status == 3:  # 队列中的任务状态为已完成的任务，主要用来确认是否要增加测试时间
                        if recv_task_status == 0:
                            self.motify_task_to_end(recv_text_loads['task_id'])
                            logger.info(f'此任务已经开启，可以开始使用：{recv_text_loads["task"]}')
                            await websocket.send(f'this band is opened : {recv_text_loads["task"]}')
                        elif recv_task_status == 3:  # 结束测试，删除队列中的任务
                            logger.info(f"已收到客户端任务完成信息，删除队列中的{recv_text_loads['task_id']}")
                            public_variable.motify_time(time_mofify=0)
                            self.detele_task(recv_text_loads['task_id'])
                            await websocket.send(f"task {recv_text_loads['task_id']} is deleted")
                        elif recv_task_status == 2:  # 请求增加测试时间
                            self.motify_task_to_end(recv_text_loads['task_id'])
                            logger.info(f'已收到增加测试时间请求任务：{recv_text_loads["task"]}')
                            self.detele_task(recv_text_loads['task_id'])  # 先删除原有任务，再补上一个高优先级任务
                            json_motify = self.motify_task(recv_text, 'task_status', 1)
                            json_motify2 = self.motify_task(json_motify, 'task_priority', 2)
                            self.recv_queue.put((2, self.que_index, json_motify2))  # 因为是增加测试时间，直接提高优先级让它插队
                            self.run_queue.put((2, self.que_index, json_motify2))  # 因为是增加测试时间，直接提高优先级让它插队
                            logger.info("*"*99)
                            logger.info(json_motify2)
                            logger.info("*"*99)
                            self.que_index += 1
                            logger.info(self.recv_queue.queue)
                            await websocket.send(f"delay task joined: {recv_text}")
                        else:
                            logger.info(f'query_task_status{query_task_status}')
                            logger.info(f'recv_task_status{recv_task_status}')
                            logger.info(f'此任务已经在队列中:\r\nrecv:{recv_text}\r\nqueue:{self.recv_queue.queue}')
                            await websocket.send(f"task is in waitting: {recv_text}")
                    else:
                        logger.info(f'query_task_status{query_task_status}')
                        logger.info(f'此任务已经在队列中:\r\nrecv:{recv_text}\r\nqueue:{self.recv_queue.queue}')
                        await websocket.send(f"task is in waitting: {recv_text}")
                else:
                    if recv_task_status == 0:  # 新建的任务加入
                        logger.info(recv_text_loads['task_priority'])
                        json_motify = self.motify_task(recv_text, 'task_status', 1)
                        self.recv_queue.put((recv_text_loads['task_priority'], self.que_index, json_motify))  # 不在则加入任务队列并修改任务状态
                        logger.info("*"*99)
                        logger.info(json_motify)
                        logger.info("*"*99)
                        self.run_queue.put((recv_text_loads['task_priority'], self.que_index, json_motify))  # 不在则加入任务队列并修改任务状态
                        self.que_index += 1
                        logger.info(self.recv_queue.queue)
                        logger.info('sleep 0.5')
                        time.sleep(0.5)  # 等待任务被拿到开始执行
                        for i in range(6000):
                            if public_variable.task_started == 1:  # 如果任务还没有完全运行起来，继续等待
                                time.sleep(0.01)
                            else:
                                logger.info(public_variable.task_started)
                                logger.info('任务已经执行起来')
                                break
                        await websocket.send(f"task joined: {recv_text}")
                    else:
                        #  不是新建任务也不在队列中，则不管
                        logger.info(f"task not found: {recv_text}")
                        logger.info(self.recv_queue.queue)
                        await websocket.send(f"task not found: {recv_text}")
            else:
                logger.info(f'接收到的内容不是json：{recv_text}')
            # await websocket.send(f"already recv {recv_text}")
            logger.info(self.recv_queue.queue)

    @staticmethod
    def motify_task(task, motify_key, motify_value):
        # 修改任务内容
        json_2 = json.loads(task)
        json_2[motify_key] = motify_value
        json_3 = json.dumps(json_2)
        return json_3

    # 握手并且接收数据
    async def serverRun(self, websocket, path):
        logger.info(path)
        await self.serverHands(websocket)
        await self.serverRecv(websocket)

    def run(self):
        logger.info("======server main begin======")
        server = websockets.serve(self.serverRun, self.qss_server_ip, self.qss_server_port)  # pylint: disable=W,R,E
        asyncio.get_event_loop().run_until_complete(server)
        asyncio.get_event_loop().run_forever()

    @staticmethod
    def is_json(myjson):
        try:
            json.loads(myjson)
        except Exception as e:
            print(e)
            return False
        return True


if __name__ == "__main__":
    recv_queue_now = queue.Queue()
    run_queue_now = queue.Queue()
    QSSSocketServer(recv_queue_now, run_queue_now).run()
    logger.info('test_end')
