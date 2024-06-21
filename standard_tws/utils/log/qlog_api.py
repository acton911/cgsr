from utils.log.log_meta import Log
import requests
from utils.logger.logging_handles import all_logger


class QLog(Log):

    @staticmethod
    def catch_log(dmc_file_path, log_save_path):
        """
        Linux抓取Log的接口，命令后台的micropython程序开始进行Log抓取
        :param dmc_file_path: DMC文件的路径，Ubuntu的默认Qlog路径为/home/ubuntu/Desktop/QLog，DMC文件路径为/home/ubuntu/Desktop/QLog/conf，需要新的Log模板找运维人员统一部署
        :param log_save_path: 日志文件的保存路径
        :return: None
        """

        data = {"dmc_file_path": dmc_file_path,
                "log_save_path": log_save_path}

        try:

            r = requests.post("http://localhost:55555/catch_log", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS catch log init error")
            else:
                all_logger.info("start catch QXDM log")

        except Exception as e:
            all_logger.error(e)
