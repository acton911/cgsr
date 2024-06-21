# 使用Middleware进行QUTS的log抓取和保存测试
from utils.functions.middleware import Middleware
import os
from utils.logger.logging_handles import all_logger
from utils.log import log
import sys

with Middleware(log_save_path=os.getcwd()) as m:
    # 业务逻辑
    # ------------
    all_logger.info("start")
    import time

    time.sleep(10)
    all_logger.info("end")
    # ------------

    # 停止抓Log
    log.stop_catch_log_and_save(m.log_save_path)
    log_n, log_p = m.find_log_file()

    # # 发送本地Log文件
    # message_types = {"LOG_PACKET": ["0xB821"]}
    # interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
    #                            "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
    # log.load_log_from_remote(log_p, message_types, interested_return_filed)
    #
    # # read_from_data_view
    # data = log.read_from_remote_data_view()
    # print(data)

    # DEBUG不删除qxdm log,防止误删文件夹
    sys.exit(0)
