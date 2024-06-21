from utils.functions.middleware import Middleware
from utils.log import log
import sys

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

path = r"C:\Users\Flynn.Chen\Desktop\QXDM无qdb信息无法解析"

with Middleware(log_save_path=path) as m:
    # 获取Log
    log_name, log_path = m.find_log_file()
    logger.info(f"log_path: {log_path}")

    # Linux下获取qdb文件
    qdb_name, qdb_path = m.find_qdb_file()
    logger.info(f'qdb_path: {qdb_path}')
    qdb_n, qdb_p = m.find_qdb_file()

    # Interested message type
    message_types = {"QTRACE": ["LRRC/HighFreq/High/LRRC"]}
    interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]

    # Load log data
    data = log.load_log_from_remote(log_path, qdb_p, qdb_path, message_types, interested_return_filed)
    logger.info(f"data: {data}")

    sys.exit(1)  # 避免误删log
