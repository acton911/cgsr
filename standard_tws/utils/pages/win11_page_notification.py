from functools import partial
from pywinauto.keyboard import send_keys
from utils.operate.base import BaseOperate
from utils.functions.decorators import watchdog
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import NormalError


# 操作中心图标
notification_icon = [{"title": "任务栏", "control_type": "Pane"},
                     {"title_re": ".*系统时钟.*", "auto_id": "SystemTrayIcon"}]

# 清除所有通知
clear_notification = [{"title": "通知中心", "control_type": "Window"},
                      {"title": "清除所有通知", "auto_id": "ClearAllButtonControl", "control_type": "Group"},
                      {"title": "全部清除", "auto_id": "ClearAllButton"}]

# 打开通知中心后检查
notification_check_button = [{"title": "通知中心", "control_type": "Window"}]

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
        try:
            self.find_element(notification_icon).print_control_identifiers()
            self.click(notification_icon, notification_check_button)
        except Exception:   # noqa,如果第一次打开失败，增加二次点击打开
            self.click(notification_icon, notification_check_button)

    def check_msg_push(self, phone_number, content):
        """
        检测是否有消息推送到Windows上
        :param phone_number:检查手机号是否正确
        :param content:检查短信内容是否符合预期
        :return:
        """
        try:
            # 打开操作中心
            try:
                self.open_notification()
            except Exception:    # noqa
                send_keys('{ESC}')
                self.open_notification()

            # 检查短信内容是否存在
            if not self.check_msg_content(phone_number, content):
                all_logger.info('检测短信内容与预期不一致')
                return False
            else:
                return True

        finally:
            try:
                # 清除所有通知
                self.click_without_check(clear_notification)
            finally:
                # 按ESC键退出操作中心
                send_keys('{ESC}')

    def check_msg_content(self, phone_number, content):
        """
        检测短信内容是否符合预期
        :param phone_number: 预期的电话号码
        :param content: 预期的短信内容
        :return:
        """
        # 查看短信通知内容
        if content == '':
            check_content = {"auto_id": "Title", "control_type": "Text"}
        else:
            check_content = {"title": f"{content}", "auto_id": "Content", "control_type": "Text"}
        message_phone_number = [{"title": "通知中心", "control_type": "Window"},
                                {"auto_id": "MainListView", "control_type": "List"},
                                {"title": "来自 操作员消息 的通知", "control_type": "Group"},
                                {"title_re": f".*{self.format_phone_number(phone_number)}.*", "control_type": "ListItem"},
                                check_content]
        if content != '':
            self.find_element(message_phone_number).print_control_identifiers()
        return self.find_element(message_phone_number).exists()

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

    def clear_notify(self):
        try:
            self.open_notification()
            self.click_without_check(clear_notification)
        finally:
            send_keys('{ESC}')


if __name__ == '__main__':
    page = PageNotification()
    print(page.check_msg_push('15655129469', ''))
