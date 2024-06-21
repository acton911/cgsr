import os
import subprocess
import win32com.client
import serial.tools.list_ports
import time
import shutil
from utils.logger.logging_handles import all_logger


class QPSTAtmnServer:
    def __init__(self):
        self._quit()
        self.qpst_instance = win32com.client.Dispatch("QPSTAtmnServer.Application")
        self.qpst_instance._FlagAsMethod("GetCOMPortList")  # noqa
        self.qpst_instance._FlagAsMethod("AddPort")  # noqa

    def __enter__(self):
        self._quit()
        self.qpst_instance = win32com.client.Dispatch("QPSTAtmnServer.Application")
        self.qpst_instance._FlagAsMethod("GetCOMPortList")  # noqa
        self.qpst_instance._FlagAsMethod("AddPort")  # noqa
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self._quit()

    @staticmethod
    def _quit():
        """
        Quit all QPST services before init QPSTAtmnServer.
        :return: None
        """
        subprocess.getoutput('taskkill /f /t /im QPST*')
        subprocess.getoutput('taskkill /f /t /im Atmn*')
        subprocess.getoutput('taskkill /f /t /im Search*')

    def add_port(self, port):
        """
        在QPST的界面中加入一个端口
        :param port: DUMP口
        :return: None
        """
        self.qpst_instance.AddPort(port, 'Auto add')

    def close(self):
        """
        关闭QPSTAtmnServer
        :return:
        """
        self.qpst_instance.Quit()
        del self.qpst_instance

    @staticmethod
    def port_list():
        return [port for port, _, _ in serial.tools.list_ports.comports()]

    def catch_dump(self, at_port):
        """
        通过AT口是否重新加载判断DUMP是否抓取完成.
        :param at_port: AT口号,例如COM7
        :return: True: DUMP抓取完成, 模块重启; False: 模块60S未重启
        """
        # 判断是否抓完DUMP重启
        all_logger.info("正在抓取DUMP...")
        start = time.time()
        while True:
            ports = self.port_list()
            if at_port in ports:
                all_logger.info("DUMP抓取完成, 模块已自动开机")
                return True

            # 每5秒检测
            all_logger.info("等待5S")
            time.sleep(5)

            # 判断超时
            if time.time() - start > 180:
                all_logger.error("DUMP抓取超时, 模块未自动重启, 请定位原因")
                return False

    @staticmethod
    def copy_dump_log(dest):
        """
        指定DUMP Log需要保存的文件夹
        :param dest: DUMP Log需要保存的文件夹
        :return: None
        """
        src = r'C:\ProgramData\Qualcomm\QPST\Sahara'

        # 判断是否有DUMP PATH
        dump_path = os.path.join(dest, "DUMP")
        if not os.path.exists(dump_path):
            os.makedirs(dump_path)

        # 拼接保存的路径
        next_dir = time.strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(dump_path, next_dir)

        # 保存
        shutil.copytree(src, save_path)


if __name__ == '__main__':
    with QPSTAtmnServer() as atmn:
        atmn.add_port("COM9")
        atmn.catch_dump("COM7")
        atmn.copy_dump_log(r"C:\Users\Flynn.Chen\Desktop")
