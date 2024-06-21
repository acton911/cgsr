from utils.functions import QWinRT_dll
# from enum import Enum


q_ok = 0
q_timeout = (-1)
q_error = (-2)
q_wait_infinite = (-1)


class QMbnWinRtHelp(QWinRT_dll.MbnWinRtHelp):
    def send_text_msg_sms(self, tonumber, msg) -> bool:
        if super().SendTextMsgSMS(tonumber, msg) == 1:
            return True
        else:
            return False

    def register_text_receive_sms(self) -> bool:
        if super().RegisterTextReceiveSMS() == 1:
            return True
        else:
            return False

    def unregister_text_receive_sms(self):
        super().UnRegisterTextReceiveSMS()

    # timeout 设置超时等待；q_wait_infinite  可阻塞等待  用此接口 获取接受信息文本，需要先RegisterTextReceiveSMS
    def get_text_msg_sms(self, timeout) -> dict:
        return super().GetTextMsgSMS(timeout)
