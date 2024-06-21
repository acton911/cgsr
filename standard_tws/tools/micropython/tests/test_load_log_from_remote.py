from pylite_base.log import log

# 发送本地Log文件
message_types = {"QTRACE": ["LRRC/HighFreq/High/LRRC"]}
# message_types = {"LOG_PACKET": ["0x156E"]}
interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING", "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
data = log.load_log_from_remote(r"C:\Users\Flynn.Chen\Desktop\QXDM无qdb信息无法解析\20220730_134006_0001.qmdl2", r'C:\Users\Flynn.Chen\Desktop\QXDM无qdb信息无法解析\8dd7590a-5845-d421-6a15-3eca1d4aef80.qdb', message_types, interested_return_filed)
print(data)
