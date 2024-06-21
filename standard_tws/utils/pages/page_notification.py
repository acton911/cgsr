import time
from functools import partial
from pywinauto.keyboard import send_keys
from utils.operate.base import BaseOperate
from utils.functions.decorators import watchdog
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import NormalError
from utils.pages.page_main import PageMain


# 操作中心图标
notification_icon = [{"title": "任务栏", "class_name": "Shell_TrayWnd"},
                     {"title_re": "操作中心.*", "class_name": "TrayButton"}]

# 检测当前是否已开启操作中心
notification_button = [{"title": "管理通知", "class_name": "Button"}]

# 清楚所有通知
clear_notification = [{"title": "操作中心", "control_type": "Window"},
                      {"title": "清除所有通知", "class_name": "Button"}]

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class PageNotification(BaseOperate):
    """
    打开操作中心显示，用于查看短信推送是否正常
    """
    def open_notification(self):
        """
        打开操作中心界面
        :return:
        """
        self.click_without_check(notification_icon)

    def check_msg_push(self, phone_number, content):
        """
        检测是否有消息推送到Windows上
        :param phone_number:检查手机号是否正确
        :param content:检查短信内容是否符合预期
        :return:
        """
        try:
            # 打开网络中心界面
            try:
                PageMain().click_network_icon()
            except Exception:   # noqa
                PageMain().click_network_icon()

            time.sleep(1)

            # 打开操作中心
            self.open_notification()

            # 检查短信内容是否存在
            if not self.check_msg_content(content):
                all_logger.info('检测短信内容与预期不一致')
                return False

            # 检查手机号是否正确
            if not self.check_phone_number(phone_number):
                all_logger.info('检测发件人手机号不一致')
                return False
        finally:
            try:
                # 清除所有通知
                self.click_without_check(clear_notification)
            finally:
                # 按ESC键退出操作中心
                send_keys('{ESC}')

    def check_msg_content(self, content):
        """
        检测短信内容是否符合预期
        :param content: 预期的短信内容
        :return:
        """
        # 查看短信通知内容
        if content == '':
            return True
        message_content = [{"title": "操作中心", "control_type": "Window"},
                           {"class_name": "ListViewItem"},
                           {"title": f"{content}", "class_name": "TextBlock"}]
        return self.find_element(message_content).exists()

    def check_phone_number(self, phone_number):
        """
        检测发件人手机号是否符合预期
        :param phone_number: 预期手机号 156 5512 9469
        :return:
        """
        # 查看发件人手机号码
        phone_content = [{"title": "操作中心", "control_type": "Window"},
                         {"class_name": "ListViewItem"},
                         {"title_re": f".*{self.format_phone_number(phone_number)}.*", "class_name": "TextBlock"}]
        return self.find_element(phone_content).exists()

    @staticmethod
    def format_phone_number(phone_number):
        """
        将手机号进行格式化，符合例如156 5512 9469格式
        :return:
        """
        num_list = []
        for i in phone_number:
            if len(num_list) == 3 or len(num_list) == 8:
                num_list.append(' ')
            num_list.append(i)
        return ''.join(num_list)


if __name__ == '__main__':
    page = PageNotification()
    page.check_msg_push('15655129469', '123')
