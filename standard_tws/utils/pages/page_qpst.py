import os
from pywinauto import Application
from utils.operate.base import BaseOperate
from pywinauto.keyboard import send_keys
from ..functions.decorators import watchdog
from ..logger.logging_handles import all_logger
from ..exception.exceptions import NormalError
from functools import partial

# 获取计算机名，qpst标题栏会有显示
host_name = os.popen('hostname').read().strip().lower()

# 打开qpst后获取右下角添加端口按钮
top_port_info = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
                 {'title': "Ports", 'control_type': "TabItem"}]

add_button = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
              {'title': "Add New Port...", 'control_type': "Button"}]

close_button = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
                {'title': "关闭", 'control_type': "Button"}]

# 获取port输入框
port_info = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
             {'title': "Add New Port", 'control_type': "Window"},
             {'auto_id': "236", 'control_type': "Edit"}]

# 获取port_lab输入框
port_label_info = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
                   {'title': "Add New Port", 'control_type': "Window"},
                   {'auto_id': "231", 'control_type': "Edit"}]

# 获取OK按钮
ok_button = [{'title': 'QPST Configuration ({})'.format(host_name), 'control_type': 'Window'},
             {'title': "Add New Port", 'control_type': "Window"},
             {'auto_id': "1", 'control_type': "Button"}]

# 重写装饰器
watchdog = partial(watchdog, logging_handle=all_logger, exception_type=NormalError)


class Qpst(BaseOperate):
    def __init__(self):
        super().__init__()

    @watchdog('打开QPST界面')
    def open_qpst(self):
        """
        打开qpst界面并获取Add New Port按钮
        :return:
        """
        Application(backend='uia').start(r'"C:\Program Files (x86)\Qualcomm\QPST\bin\QPSTConfig.exe')
        if self.find_element(add_button).exists():
            return self.find_element(add_button)
        for i in range(10):
            try:
                self.click(top_port_info, add_button)
                return self.find_element(add_button)
            except Exception:   # noqa
                pass
        else:
            self.close_qpst()
            all_logger.info('未找到add_button按钮')
            raise NormalError('未找到add_button按钮')

    @watchdog('点击添加按钮')
    def click_add_port(self):
        """
        点击添加按钮
        :return:
        """
        self.open_qpst().click()

    @watchdog('port栏输入dm口')
    def input_port(self, dm_port):
        """
        输入dm口信息
        :param dm_port:
        :return:
        """
        self.click_without_check(port_info)
        send_keys('{}'.format(dm_port))
        self.click_without_check(port_label_info)
        send_keys('{}'.format(dm_port))
        ok = BaseOperate().find_element(ok_button)
        ok.click()

    @watchdog('关闭QPST')
    def close_qpst(self):
        """
        关闭QPST
        :return:
        """
        close = BaseOperate().find_element(close_button)
        close.click()
