import requests
from utils.logger.logging_handles import all_logger
import os


class QUTSError(Exception):
    """QUTS相关异常"""


class Log:
    """
    Windows(QUTS)和Ubuntu(QLog)进行Log解析的通用API部分，QLog继承Log，对不同点进行了重新定义
    """

    def __init__(self):
        self.quts_server = "10.66.98.120"  # QUTS Remote Server Address

    def catch_log(self, *args):
        """定义Log捕获函数，Windows和Ubuntu参数略有不同，定义在子类(Log)里"""
        pass

    @staticmethod
    def stop_catch_log_and_save(log_save_path):
        """
        停用QUTS Service并保存Log到指定的文件夹
        :param log_save_path: QUTS 保存的指定的文件夹
        :return: None
        """
        all_logger.info("stop_catch_log_and_save")

        data = {"log_save_path": log_save_path}
        try:

            r = requests.post("http://localhost:55555/stop_catch_log_and_save", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS save log error")
            else:
                all_logger.info("QUTS save log success")

        except Exception as e:
            all_logger.error(e)

    @staticmethod
    def stop_quts_service():
        """
        停止QLog占用DM口，部分APP初始化升级和Case中升级需要调用此方法，避免端口占用。
        :return:
        """

        try:
            all_logger.info("stop_quts_service")

            r = requests.get("http://localhost:55555/stop_quts_service")

            if r.status_code != 200:
                all_logger.error(r.content)

        except Exception as e:
            all_logger.error(e)

    def load_log_from_remote(self, file_path, qdb_path, message_types, interested_return_filed, data_view_name="TEST"):
        """
        stop_catch_log_and_save后，使用find_log_file方法找到Log文件后，将Log文件发送到远程服务器进行解析。
        :param file_path: stop_catch_log_and_save方法保存的Log
        :param qdb_path: QLog生成的.qdb文件的路径，如果是Windows，传入空即可
        :param message_types: 感兴趣的QXDM Log ID，可以在QXDM Log抓取界面查看，例如 {"LOG_PACKET": ["0xB821"]}，寻找UE能力相关的log
        :param interested_return_filed: 感兴趣的消息类型，默认 ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
        :param data_view_name: DataView名称
        :return: None
        """
        # file_content example {file_name: open(r"C:\Users\Flynn.Chen\Desktop\CFUN1驻网.hdf", 'rb')}

        def nested_dict_values2str(d):
            # dict(zip(d.keys(), [str(i) for i in d.values()]))  # one-line
            new_dict = dict()
            for k, v in d.items():
                new_dict[k] = str(v)
            return new_dict
        file_name = os.path.basename(file_path)
        file_content = open(file_path, 'rb')

        files = {file_name: file_content}
        if qdb_path:
            qdb_name = os.path.basename(qdb_path)
            qdb_content = open(qdb_path, 'rb')
            qdb = {qdb_name: qdb_content}
            files.update(qdb)

        data = {
            "message_types": message_types,
            "interested_return_filed": interested_return_filed
        }

        try:

            data = nested_dict_values2str(data)  # Caution! post-requests is sent "application/x-www-form-urlencoded" can't contain nested dict  # noqa
            r = requests.post(f"http://{self.quts_server}:55555/load_log_from_remote", data=data, files=files)

            if r.status_code != 200:
                all_logger.error("QUTS load log from remote error")

            return repr(r.content)

        except Exception as e:
            all_logger.error(e)

    def read_from_remote_data_view(self, data_view_name="TEST"):
        """
        !!!为了解决服务端竞态，已经合入load_log_from_remote
        从刚才创建的DataView中取出对应的值
        :param data_view_name: 创建的DataView的名称，一般保持默认TEST就好，不用修改。
        :return: DataView中解析的值
        """

        data = {"data_view_name": data_view_name}

        try:
            r = requests.post(f"http://{self.quts_server}:55555/read_from_data_view", json=data)

            if r.status_code != 200:
                all_logger.error("QUTS read from data view error")

            return repr(r.content)

        except Exception as e:
            all_logger.error(e)

    def destroy_remote_data_view(self, data_view_name="TEST", file_name=None):
        """
        删除解析过的DataView，释放相关变量。
        :param data_view_name: 需要删除的DataView名称
        :param file_name:需要删除的FileName，不指定则只删除实例化的部分变量
        :return: None
        """

        data = {"data_view_name": data_view_name}

        if file_name:
            data["file_name"] = file_name

        try:
            r = requests.post(f"http://{self.quts_server}:55555/destroy_data_view", json=data)

            if r.status_code != 200:
                return QUTSError("QUTS destroy data view error")

        except Exception as e:
            all_logger.error(e)


if __name__ == '__main__':
    # 发送本地Log文件
    message_types = {"QTRACE": ["LRRC/HighFreq/High/LRRC"]}
    interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE",
                               "TIME_STAMP_STRING",
                               "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
    log = Log()
    data = log.load_log_from_remote(r"C:\Users\Flynn.Chen\Desktop\QXDM无qdb信息无法解析\20220730_134006_0001.qmdl2", '', message_types, interested_return_filed)
    print(data)
