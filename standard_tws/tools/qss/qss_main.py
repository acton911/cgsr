import json
import queue
import threading
import time
from qss_task_executer import QSSTaskExecuter
from qss_socket_server import QSSSocketServer
from logger import logger
import public_variable


class QSSMain:
    def __init__(self, recv_queue: queue.Queue, run_queue: queue.PriorityQueue):
        self.qss_now_task = ''
        # self.qss_status = 'free'
        self.qss_ip = ''
        self.busy_time = public_variable
        self.recv_queue = recv_queue
        self.run_queue = run_queue
        self.task_status_list = ['新建', '排队中', '正在执行', '已完成']

    def get_qss_status(self):
        return self.busy_time.qss_status, self.busy_time

    def detele_task(self, task_id):
        """
        删除任务
        :param task_id:
        :return:
        """
        logger.info(task_id)
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
            logger.info(f'未找到该任务：{task_id}\t\n{self.recv_queue.queue}')

    # def motify_task_to_end(self, task_id):
    #     """
    #     把任务从正在执行改为已完成
    #     :param task_id:
    #     :return:
    #     """
    #     q_size = self.recv_queue.qsize()
    #     for i in range(q_size):
    #         task = self.recv_queue.get()
    #         # logger.info(f'{json.loads(task[2])["task_id"]}')
    #         if json.loads(task[2])["task_id"] == task_id:
    #             logger.info(f'更新{task_id}任务状态为已完成')
    #             self.motify_task_with_priority(task, 'task_status', 3, queue_motify=self.recv_queue)
    #         else:
    #             self.recv_queue.put(task)
    #         time.sleep(0.01)
    #     else:
    #         logger.info(f'未找到该任务：{task_id}')
    #     q_size_r = self.run_queue.qsize()
    #     for i in range(q_size_r):
    #         task = self.run_queue.get()
    #         # logger.info(f'{json.loads(task[2])["task_id"]}')
    #         if json.loads(task[2])["task_id"] == task_id:
    #             logger.info(f'更新{task_id}任务状态为已完成')
    #             self.motify_task_with_priority(task, 'task_status', 3, queue_motify=self.run_queue)
    #         else:
    #             self.run_queue.put(task)
    #         time.sleep(0.01)
    #     else:
    #         logger.info(f'未找到该任务：{task_id}\t\n{self.recv_queue.queue}')

    @staticmethod
    def motify_task(task, motify_key, motify_value):
        """
        :param task:待修改json
        :param motify_key:需要修改内容的key
        :param motify_value:需要修改的内容
        :return:修改后的json
        """
        # 修改任务内容
        json_2 = json.loads(task)
        json_2[motify_key] = motify_value
        json_3 = json.dumps(json_2)
        return json_3

    def motify_task_with_priority_single(self, task_witth_priority, motify_key, motify_value, priority=''):
        """
        修改任务内容并加入队列
        :param priority: 优先级
        :param task_witth_priority:待修改带优先级的任务
        :param motify_key:待修改内容的key
        :param motify_value:需要修改的内容
        :return:
        """
        logger.info('now to motify run task')
        logger.info(json.loads(task_witth_priority[2]))
        task = task_witth_priority[2]
        task_priority = (json.loads(task_witth_priority[2])['task_priority']) if priority == '' else int(priority)
        task_index_que = task_witth_priority[1] + 1
        json_motify = self.motify_task(task, motify_key, motify_value)
        self.run_queue.put((task_priority, task_index_que, json_motify))  # 不在则加入任务队列并修改任务状态
        logger.info(self.run_queue.queue)

        logger.info('now to motify recv task')
        logger.info(json.loads(task_witth_priority[2]))
        task = task_witth_priority[2]
        task_priority = (json.loads(task_witth_priority[2])['task_priority']) if priority == '' else int(priority)
        task_index_que = task_witth_priority[1] + 1
        json_motify = self.motify_task(task, motify_key, motify_value)
        self.detele_task(json.loads(task_witth_priority[2])['task_id'])
        self.recv_queue.put((task_priority, task_index_que, json_motify))  # 不在则加入任务队列并修改任务状态
        logger.info(self.recv_queue.queue)

    def motify_task_with_priority(self, task_witth_priority, motify_key, motify_value, queue_motify=None, priority=''):
        """
        修改任务内容并加入队列
        :param priority: 优先级
        :param task_witth_priority:待修改带优先级的任务
        :param motify_key:待修改内容的key
        :param motify_value:需要修改的内容
        :param queue_motify:该修改queue
        :return:
        """
        queue_motify = queue_motify if queue_motify is not None else self.run_queue
        logger.info('now to motify task')
        logger.info(json.loads(task_witth_priority[2]))
        task = task_witth_priority[2]
        task_priority = (json.loads(task_witth_priority[2])['task_priority']) if priority == '' else int(priority)
        task_index_que = task_witth_priority[1] + 1
        json_motify = self.motify_task(task, motify_key, motify_value)
        queue_motify.put((task_priority, task_index_que, json_motify))  # 不在则加入任务队列并修改任务状态

    def run_executer(self):
        times = 0
        while True:
            start_time = time.time()
            if self.busy_time.qss_status == 'free':
                if times % 1000 == 0:  # 每10s打印一次log，避免log过多
                    logger.info('开始获取队列中的任务去执行')
                    logger.info(f'{self.run_queue.queue}')
                try:
                    ececute_task = self.run_queue.get_nowait()
                    self.busy_time.motify_qss_status('busy')  # qss开始busy
                except Exception:  # noqa
                    if times % 1000 == 0:  # 每10s打印一次log，避免log过多
                        logger.info('当前QSS设备处于free状态，任务队列中暂无任务')
                        logger.info(f'QSS正在运行的文件 {self.qss_now_task}')
                    times += 1
                    time.sleep(0.01)
                    continue
                logger.info(f'获取的任务:{ececute_task}')
                task_status = json.loads(ececute_task[2])["task_status"]
                task_get = json.loads(ececute_task[2])["task"]
                logger.info(f'获取的任务内容:{task_get}')
                logger.info(f'QSS正在执行的任务:{self.qss_now_task}')
                if task_status == 1 and self.qss_now_task != task_get:  # 此流程结束后，队列减少一个排队任务，增加一个进行中的任务
                    logger.info(task_status)
                    self.busy_time.motify_task_started(1)
                    old_task = self.qss_now_task
                    self.qss_now_task = task_get
                    logger.info(f'task:{self.qss_now_task}')
                    self.qss_ip = json.loads(ececute_task[2])["qss_ip"]
                    if json.loads(ececute_task[2])["task_priority"] < 3:
                        logger.info(f"当前任务为高优先级插队任务，优先级为:{json.loads(ececute_task[2])['task_priority']}")
                        self.motify_task_with_priority_single(ececute_task, "task_status", 2, priority='3')  # 序号+1避免一直取同一个
                    else:
                        self.motify_task_with_priority_single(ececute_task, "task_status", 2)
                    self.busy_time.motify_qss_status('busy')  # qss开始busy
                    self.busy_time.time_add(json.loads(ececute_task[2])["tesk_duration"])
                    self.busy_time.motify_task_started(0)
                    if len(self.qss_now_task) == 2:
                        if self.qss_now_task[0] in old_task:
                            logger.info("mme与上一个相同，不关闭直接使用")
                            QSSTaskExecuter(self.qss_now_task).run_qss_keep_mme(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1])
                        else:
                            QSSTaskExecuter(self.qss_now_task).run_qss(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1])
                    elif len(self.qss_now_task) == 3:
                        if not self.qss_now_task[2].endswith('.cfg'):
                            white_sim_ismi = self.qss_now_task[2]
                            QSSTaskExecuter(self.qss_now_task).run_qss(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1], imsi_sim=white_sim_ismi)
                        else:
                            if self.qss_now_task[0] in old_task:
                                logger.info(f"mme ({self.qss_now_task[0]}) 与上一个任务相同，不关闭直接使用")
                                QSSTaskExecuter(self.qss_now_task).run_qss_keep_mme(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1], self.qss_now_task[2])
                            else:
                                QSSTaskExecuter(self.qss_now_task).run_qss(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1], self.qss_now_task[2])
                    elif len(self.qss_now_task) == 4:
                        white_sim_ismi = self.qss_now_task[3]
                        QSSTaskExecuter(self.qss_now_task).run_qss(self.qss_ip, self.qss_now_task[0], self.qss_now_task[1], self.qss_now_task[2], imsi_sim=white_sim_ismi)
                    else:
                        logger.error(f'qss配置文件错误！请检查： {self.qss_now_task}')
                elif task_status == 1 and self.qss_now_task == task_get:  # 此流程结束后，队列减少一个排队任务，增加一个进行中的任务
                    logger.info(task_status)
                    logger.info(f'QSS正在执行的任务:{self.qss_now_task}')
                    logger.info(f'需要去执行的新任务内容:{task_get}')
                    logger.info('已经在运行，可以直接使用！')
                    if json.loads(ececute_task[2])["task_priority"] < 3:
                        logger.info(f"当前任务为高优先级插队任务，优先级为:{json.loads(ececute_task[2])['task_priority']}")
                        self.motify_task_with_priority_single(ececute_task, "task_status", 2, priority='3')  # 序号+1避免一直取同一个
                    else:
                        self.motify_task_with_priority_single(ececute_task, "task_status", 2)
                    self.busy_time.motify_qss_status('busy')  # qss开始busy
                    self.busy_time.time_add(json.loads(ececute_task[2])["tesk_duration"])
                elif task_status == 2 and self.qss_now_task != task_get:  # 已经运行的且不是当前任务，更新为已结束
                    logger.info(task_status)
                    logger.info(f'更新为已结束')
                    self.motify_task_with_priority_single(ececute_task, "task_status", 3)
                    time.sleep(0.5)
                elif task_status == 2 and self.qss_now_task == task_get:
                    logger.info(task_status)
                    self.motify_task_with_priority_single(ececute_task, "task_priority", 3, priority='3')  # 序号+1避免一直取同一个
                    time.sleep(0.5)
                elif task_status == 3 and self.qss_now_task != task_get:  # 已经完成且不是当前任务，则删除
                    logger.info(task_status)
                    logger.info(f'删除')
                    self.detele_task(json.loads(ececute_task[2])['task_id'])
                    time.sleep(0.5)
                elif task_status == 3 and self.qss_now_task == task_get:
                    logger.info(task_status)
                    self.motify_task_with_priority_single(ececute_task, "task_priority", 3, priority='3')  # 序号+1避免一直取同一个
                    time.sleep(0.5)
                else:
                    logger.info(task_status)
                    self.motify_task_with_priority_single(ececute_task, "task_priority", 3, priority='3')  # 序号+1避免一直取同一个
                    logger.info('next...')
                    time.sleep(0.5)
                #  控制是否busy
            else:
                logger.info(f'当前QSS设备处于busy状态，请等待 {int(self.busy_time.busy_time)} s')
                time.sleep(1)
            self.busy_time.time_pass(time.time() - start_time)
            if self.busy_time.busy_time <= 0:
                self.busy_time.motify_qss_status('free')  # qss恢复free
                self.busy_time.motify_time(0)


if __name__ == "__main__":
    q1 = queue.Queue()
    q2 = queue.PriorityQueue()
    qss_exe_path_mme_n = '/home/sdr/sdr/2021-06-17/ltemme-linux-2021-06-17'
    qss_exe_path_enb_n = '/home/sdr/sdr/2021-06-17/lteenb-linux-2021-06-17'
    main = QSSMain(q1, q2)
    t1 = threading.Thread(target=main.run_executer)
    t1.start()
    QSSSocketServer(q1, q2).run()
