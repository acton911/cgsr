import time
from pywinauto import Desktop
from ..exception.exceptions import FrameworkError
from ..logger.logging_handles import all_logger
import keyboard


class BaseOperate:
    def __init__(self):
        self.uia_app = Desktop(backend='uia')

    def find_element(self, params):
        """
        拼接元素。
        如果传入的参数是字典，直接调用self.uia_app的window方法。
        如果传入的参数是列表，使用parser函数解析成需要查找的实体。
        :param params: 需要查找的元素，列表或字典。
        :return:需要查找的元素实体。
        """
        def parser(window, param):
            func, remain_params = param[0], param[1:]
            func.update({'found_index': 0})  # 实验性功能：使用index=0的元素
            if window is None:
                window_entity = self.uia_app.window(**func)
            else:
                window_entity = window.window(**func)
            return parser(window_entity, remain_params) if len(remain_params) else window_entity

        all_logger.debug(params)
        element_entity = None
        if isinstance(params, dict):
            params.update({'found_index': 0})  # 实验性功能：使用index=0的元素
            element_entity = self.uia_app.window(**params)
        elif isinstance(params, list):
            element_entity = parser(None, params)
        return element_entity

    def page_down(self, **kwargs):
        """
        翻页：首先点击参数传入的页面，然后输入Page Down。
        :param kwargs: 需要点击的元素
        :return: None
        """
        all_logger.debug(kwargs)
        page = self.find_element(kwargs)
        page.click_input()
        page.type_keys("{PGDN}")

    def click(self, click_param, check_param, check_disappear=False, timeout=10):
        """
        点击某个元素，检查点击后是否有元素出现或者消失。
        传入参数示例：
        :param click_param: 需要点击的元素
        :param check_param: 点击后需要检查的元素
        :param check_disappear: 默认False，点击后检查某个元素出现；True: 点击后检查某个元素消失。
        :param timeout: 默认10S，检查点击后元素出现的超时时间。
        :return: None
        """
        all_logger.debug("click_param:{}\ncheck_param:{}".format(click_param, check_param))

        # 点击操作
        next_app = self.find_element(click_param)
        if not next_app.exists(timeout=10):
            raise FrameworkError("需要点击的元素 {} 不存在".format(click_param))
        try:
            next_app.click()
            all_logger.info("clicked")
        except Exception:  # noqa
            next_app.click_input()
            all_logger.info("clicked")

        if not check_disappear:
            check_app = self.find_element(check_param)
            if check_app.exists(timeout=timeout):
                return True
            else:
                raise FrameworkError("点击后条件 {} 不存在".format(check_param))
        else:
            for _ in range(30):
                check_app = self.find_element(check_param)
                if check_app.exists() is False:
                    return True
                else:
                    time.sleep(1)
            else:
                raise FrameworkError("点击后条件 {} 未消失".format(check_param))

    def click_without_check(self, kwargs):
        """
        查找某个元素，点击后不做其他操作。
        :param kwargs: 需要点击的元素
        :return: None
        """
        all_logger.debug(kwargs)
        element = self.find_element(kwargs)
        try:
            element.click()
        except AttributeError:
            element.click_input()

    def click_input_sth(self, click_element, input_element):
        """
        点击某个元素，然后输入字符。例如点击SIM PIN框，输入1234。
        传入参数示例：
        :param click_element: 需要点击的元素
        :param input_element: 需要输入的元素
        :return:None
        """
        all_logger.debug("click_element:{}\ninput_element:{}".format(click_element, input_element))
        element = self.find_element(click_element)
        if not element.exists(timeout=10):
            raise FrameworkError("需要点击的元素 {} 不存在".format(click_element))
        try:
            element.click()
        except AttributeError:
            element.click_input()
        input_element = iter(list(input_element))
        for key in input_element:
            keyboard.send(key)

    def click_disable_checkbox(self, kwargs):
        """
        点击一个checkbox，如果是未勾选状态，则不做任何动作；
        如果是勾选状态，则取消勾选checkbox。
        :param kwargs: 需要点击的元素。
        :return: None
        """
        all_logger.debug(kwargs)
        element = self.find_element(kwargs)
        for i in range(3):
            if element.get_toggle_state():
                element.toggle()
            if element.get_toggle_state():
                time.sleep(1)
                continue
            else:
                return True
        else:
            raise FrameworkError("连续三次取消勾选 {} 元素失败".format(kwargs))

    def click_enable_checkbox(self, kwargs):
        """
        点击一个checkbox，如果是未勾选状态，则勾选；
        如果是勾选状态，则不进行任何操作。
        :param kwargs: 需要点击的元素。
        :return: None
        """
        all_logger.debug(kwargs)
        element = self.find_element(kwargs)
        for i in range(3):
            if not element.get_toggle_state():
                element.toggle()
            if not element.get_toggle_state():
                time.sleep(1)
                continue
            else:
                return True
        else:
            raise FrameworkError("连续三次取消勾选 {} 元素失败".format(kwargs))
