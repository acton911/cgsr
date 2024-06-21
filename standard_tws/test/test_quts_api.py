from utils.functions.middleware import Middleware
from utils.log import log
from utils.operate.at_handle import ATHandle
import time


# Analyse local log

log_path = r"C:\Users\Flynn.Chen\Desktop\test.hdf"
message_types = {"LOG_PACKET": ["0xB821"]}
interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]

log.load_log_from_file(log_path, message_types, interested_return_filed)

data = log.read_from_data_view()
# print(data)
# ue_CategoryDL = "ue-CategoryDL-r12 12"
# ue_CategoryUL = "ue-CategoryUL-r12 13"
# dl_256QAM_r12 = "dl-256QAM-r12 supported"
# if ue_CategoryDL in repr(data) and ue_CategoryUL in repr(data) and dl_256QAM_r12 in repr(data):
#     print("UE 能力检查正常")
#
# log.destroy_data_view()
#
# # read QXDM msg real-time
#
# at_port = "COM7"
# at_handle = ATHandle(at_port)
# at_handle.send_at("AT+CFUN=0", timeout=3)
# time.sleep(3)
# # log.catch_log()
# log.create_data_queue(message_types, interested_return_filed)
# at_handle.send_at("AT+CFUN=1", timeout=3)
# at_handle.check_network()
# data = log.read_from_data_queue()
# print(data)
#
# # 因为如果正常状态会强制删除Log文件，所以这里暂时是直接退出，不走__exit__
# import sys
# sys.exit(1)
