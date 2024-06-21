# 注意：可能会因为版本原因造成QLog抓取失败，例如Revision: RM520NGLAARO1A06M4GV01
import signal
import os
import time
from threading import Thread
from modules.logger import logger
import subprocess
import threading


class QUTS:
    def __init__(self):
        self.qlog = None
        self.log_watchdog = None

    def set_log_watchdog(self, log_save_path):
        """
        创建一个Log的定时器，如果超过指定时间，则停止抓取Log
        :param log_save_path:
        :return:
        """
        logger.info(f"set log save watchdog. save path: {log_save_path}")
        self.log_watchdog = threading.Timer(1800, function=self.stop_catch_log_and_save, args=(log_save_path,))
        self.log_watchdog.setDaemon(True)
        self.log_watchdog.start()

    def cancel_log_watchdog(self):
        """
        如果正常结束，则取消看门狗。
        :return:
        """
        if getattr(self, 'log_watchdog', None) and getattr(self.log_watchdog, "cancel", None):
            logger.info("cancel log save watchdog.")
            self.log_watchdog.cancel()
            self.log_watchdog = None

    def catch_log(self, dmc_file_path, log_save_path=os.getcwd()):
        # 如果已经有QLog线程，删除Log文件
        qlog_status = self.stop_catch_log_and_save()
        if qlog_status:
            self.del_all_qxdm_log(log_save_path)

        # 启动QLog线程
        self.qlog = QLogThread(dmc_file_path, log_save_path)

        # 设置Log的看门狗，默认超时时间1800s，也就是1800s后即使Case结束，Log也自动结束
        self.set_log_watchdog(log_save_path)

    def stop_catch_log_and_save(self, *args):
        # 取消log watchdog
        self.cancel_log_watchdog()

        # self.qlog不是process，直接跳出
        if self.qlog is None:
            logger.error("ignore stop_catch_log_and_save")
            return False

        # self.qlog是process，尝试发送ctrl+c退出
        logger.info(args)
        self.qlog.ctrl_c()
        self.qlog = None
        return True

    def stop_quts_service(self):
        # 取消log watchdog
        self.cancel_log_watchdog()

        # self.qlog不是process，直接跳出
        if self.qlog is None:
            return True

        # self.qlog是process，尝试发送ctrl+c退出
        self.qlog.ctrl_c()
        self.qlog.del_log()  # 强制停止需要删除Log，一般在初始化的时候强制关闭QLog或者在Case中需要进行升级前进行调用
        self.qlog = None
        return True

    @staticmethod
    def del_all_qxdm_log(path=os.getcwd()):
        """
        删除目录下的所有QXDM Log文件
        :return: None
        """

        if os.name == 'nt':
            del_cmd = f'del /F /S /Q "{path}"'
        else:
            del_cmd = f'sudo rm -rf "{path}"'

        for path, _, files in os.walk(path):
            for file in files:
                if file.endswith(('.hdf', '.qmdl2', 'isf', '.bin', '.qdb')):
                    cmd = del_cmd.format(os.path.join(path, file))  # noqa
                    logger.info(f"del cmd: {cmd}")
                    logger.info(subprocess.getstatusoutput(cmd))


class QLogThread(Thread):
    """
    QLog后台记录Log
    """

    def __init__(self, dmc_file_path, log_save_path=os.getcwd()):
        super().__init__()
        self.qlog_dir = "/home/ubuntu/Desktop/QLog"  # QLog在自动化测试机上的路径
        self.dm_port = "/dev/ttyUSBDM"  # 此处是DM口的端口号，自动化设备默认为/dev/ttyUSBDM
        self.dmc_file_path = dmc_file_path
        self.log_save_path = log_save_path
        self.create_path()  # 创建Log PATH
        self.cmd = f"{self.qlog_dir}/QLog -p {self.dm_port} -s {log_save_path} -m 512 -f {self.dmc_file_path}"
        logger.info(self.cmd)
        self.daemon = True
        self.process = None  # 后续用来创建协程
        self.start()  # 启动线程

    def create_path(self):
        if not os.path.exists(self.log_save_path):
            os.makedirs(self.log_save_path)

    def run(self):
        input_cmd = self.cmd.split(' ')
        self.process = subprocess.Popen(input_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while self.process.poll() is None:
            time.sleep(0.001)
            line = self.process.stdout.readline()
            logger.info("[QLog] {}".format(line.decode('utf-8', 'ignore')))

    def ctrl_c(self):

        if self.process.poll() is None:
            logger.info("send ctrl+c signal")
            self.process.send_signal(signal.SIGINT)

        start = time.time()
        while self.process.poll() is None:
            # check every 0.1s
            time.sleep(0.1)

            if time.time() - start > 10:
                logger.error("process cant stop itself, process.kill()")
                self.process.kill()
                logger.error("wait.")
                self.process.wait()
                logger.error("process killed.")

    def del_log(self):
        for file in os.listdir(self.log_save_path):
            if file.endswith((".qdb", ".qmdl2")):
                file_path = os.path.join(self.log_save_path, file)
                logger.info(f'sudo rm -rf "{file_path}"')
                logger.info(subprocess.getoutput(f'sudo rm -rf "{file_path}"'))


if __name__ == "__main__":
    logger.info(subprocess.getoutput("sudo rm -rf /home/ubuntu/Flynn/files/"))
    qlog = QLogThread(dmc_file_path='/home/ubuntu/Desktop/QLog/conf/defaultNR5G1216.cfg', log_save_path="/home/ubuntu/Flynn/files/")
    time.sleep(20)
    qlog.ctrl_c()
