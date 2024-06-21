import subprocess
import serial.tools.list_ports
from utils.logger.logging_handles import all_logger


class QLogDUMP:

    qlog_path = '/root/nr/tools/qlog/QLog'  # QLog在Linux上的路径

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def port_list():
        return [port for port, _, _ in serial.tools.list_ports.comports()]

    def catch_dump(self):
        """
        通过AT口是否重新加载判断DUMP是否抓取完成.
        :param: AT口号,例如COM7
        :return: True: DUMP抓取完成, 模块重启; False: 模块60S未重启
        """

        # 如果是DUMP模式
        with subprocess.Popen(
                [self.qlog_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
        ) as process:
            try:
                out, _ = process.communicate(timeout=600)
            except subprocess.TimeoutExpired:
                all_logger.error("QLog抓取DUMP超过600S")
                process.kill()
                out, _ = process.communicate()

            out = out.decode('utf-8', 'ignore')
            all_logger.info(f"out: {out}")

            if "Catch DUMP using Sahara protocol successful" in out:
                all_logger.info("QLog DUMP抓取成功")
                return True
            else:
                return False


if __name__ == "__main__":
    with QLogDUMP() as dump:
        dump.catch_dump()
