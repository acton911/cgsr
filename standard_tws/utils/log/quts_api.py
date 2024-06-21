import requests
from utils.logger.logging_handles import all_logger
from utils.log.log_meta import Log


class QUTSError(Exception):
    """QUTS相关异常"""


class QUTS(Log):

    @staticmethod
    def catch_log(dmc_file_path, log_save_path):
        """
        Windows下QUTS初始化QUTS接口开始抓Log
        :param dmc_file_path: 指定Log的模板，Windows默认在 "C:\\Users\\<username>\\QXDM_conf"，需要新的Log模板找运维人员统一部署
        :param log_save_path: 指定Log的保存路径
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

    # 此部分调用quts的同时调用本地的DataQueue进行日志解析，包含create_data_queue、read_from_data_queue、destroy_data_queue三个部分
    @staticmethod
    def backup_qcn(qcn_file_path):
        """
        Windows下QUTS初始化QUTS接口开BACK UP QCN
        :param qcn_file_path: 备份qcn的文件名和位置, 例如E:\\Auto\\mbim_sar\20220526\\standard_tws-develop\\QCN_BACKUP\\windows_laptop_mbim_sar_01_001\\qcn_mbim_sar_before_upgrade.xqcn
        :return: None
        """

        data = {"qcn_file_path": qcn_file_path}

        try:

            r = requests.post("http://localhost:55555/backup_qcn", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS backup qcn init error")
            else:
                all_logger.info("start backup qcn")

        except Exception as e:
            all_logger.error(e)

    # 此部分调用quts的同时调用本地的DataQueue进行日志解析，包含create_data_queue、read_from_data_queue、destroy_data_queue三个部分
    @staticmethod
    def create_data_queue(message_types, interested_return_filed, data_queue_name="TEST"):
        """
        Windows 端在调用catch_log之后，创建一个data_queue对数据进行筛选，符合要求的数据会被存储到对应的data_queue，之后调用
        read_from_data_queue从data_queue中读取数据。
        :param message_types: 需要筛选的数据类型，例如 {"LOG_PACKET": ["0xB821", "0xB808", "0xB80A", "0xB800"]} 筛选驻网相关的Log
        :param interested_return_filed: 保存筛选后的Log的字段，默认不用修改 ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
        :param data_queue_name: data_queue的名称，不重要，默认可以不修改
        :return: None
        """

        data = {
            "data_queue_name": data_queue_name,
            "message_types": message_types,
            "interested_return_filed": interested_return_filed
        }

        try:

            r = requests.post("http://localhost:55555/create_data_queue", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS set DataQueue error")

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def read_from_data_queue(data_queue_name="TEST"):
        """
        从data_queue中读取所有捕获的log
        :param data_queue_name: data_queue的名称，可以保持默认不用修改
        :return: None
        """

        data = {"data_queue_name": data_queue_name}

        try:

            r = requests.post("http://localhost:55555/read_from_data_queue", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS read from DataQueue error")

            return repr(r.content)

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def destroy_data_queue(data_queue_name="TEST"):
        """
        ！！！现在destroy_data_queue为了防止脚本忘记调用已经放入read_from_data_queue中，不必重复调用
        删除data_queue和一些用到的临时变量
        :param data_queue_name: data_queue的名称，初始用到的data_queue是什么名称，这里就传入什么名称
        :return: None
        """

        data = {"data_queue_name": data_queue_name}

        try:

            r = requests.post("http://localhost:55555/destroy_data_queue", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS destroy DataQueue error")

        except Exception as e:
            all_logger.error(e)

    # 此部保存Log后调用本地的DataView进行日志解析，load_log_from_file、read_from_data_view、destroy_data_view三个部分
    @staticmethod
    def load_log_from_file(log_path, message_types, interested_return_filed):
        """
        在调用使用stop_catch_log_and_save保存Log文件之后，使用此方法加载Log文件。
        :param log_path: Log文件在本机的路径
        :param message_types: 感兴趣的QXDM Log ID，可以在QXDM Log抓取界面查看，例如 {"LOG_PACKET": ["0xB821"]}，寻找UE能力相关的log
        :param interested_return_filed: 感兴趣的消息类型，默认 ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
        :return: None
        """

        data = {
            "log_path": log_path,
            "message_types": message_types,
            "interested_return_filed": interested_return_filed
        }

        try:

            r = requests.post("http://localhost:55555/load_log_from_file", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS load logs from file error")

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def read_from_data_view(data_view_name="TEST"):
        """
        在使用load_log_from_file之后，调用此方法查看筛选过后的Log信息。
        :param data_view_name: data_view的名称，一般保持默认即可
        :return: None
        """

        data = {"data_view_name": data_view_name}

        try:
            r = requests.post("http://localhost:55555/read_from_data_view", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS read from data view error")

            return repr(r.content)

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def destroy_data_view(data_view_name="TEST", file_name=None):
        """
        ！！！现在destroy_data_view为了防止忘记删除log文件，已经合入了read_from_data_view中，不再需要重复调用
        删除本地的data_view，并删除相关方法实例化的一些变量，释放内存
        :param data_view_name: data_view的名称
        :param file_name: 需要删除的Log的文件名
        :return: None
        """

        data = {"data_view_name": data_view_name}

        if file_name:
            data["file_name"] = file_name

        try:
            r = requests.post("http://localhost:55555/destroy_data_view", json=data)

            if r.status_code != 200:
                return QUTSError("QUTS destroy data view error")

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def restore_qcn(sn):
        """
        模块的SN号，用来查找QCN
        :param sn: SN号
        :return: None
        """

        data = {"sn": sn}
        all_logger.info(f'开始进行QCN恢复，SN：{sn}')

        try:

            r = requests.post("http://localhost:55555/restore_qcn", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS restore qcn error")
            else:
                msg = r.json().get("msg")
                all_logger.info(f"msg: {msg}")
                if msg == "None":
                    all_logger.error(f"未找到SN为{sn}的QCN文件，未执行QCN恢复")
                    return False
                elif msg == 'Unknown':
                    all_logger.error("恢复QCN时发生未知错误，请检查MicroPython的Log")
                    return False
                elif msg == "success":
                    all_logger.info("模块恢复QCN成功")
                    return True
                else:
                    all_logger.info("未安装QUTS，不支持QCN恢复")
                    return False

        except Exception as e:
            all_logger.error(f"请更新micropython版本: {e}")
            return False
