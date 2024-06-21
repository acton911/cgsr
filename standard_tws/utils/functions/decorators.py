import sys
from functools import wraps
from ..logger.logging_handles import all_logger
import time
import traceback


def watchdog(message="", logging_handle=None, exception_type=None):
    """
    如果函数运行异常或者被包装的函数返回False时，往外部抛出异常并记录log。
    其他模块使用使用需要传入对应的logging handler和想引发的异常类型，并用partial包装。
    eg:
        watchdog = partial(watchdog, logging_handle=mbim_logger, exception_type=MBIMException)
    :param logging_handle: 需要打印的logging的handler
    :param exception_type: 需要触发的异常类型
    :param message: 被包装函数运行的log，记录到logging中，同时也用作异常抛出使用。
    :return: None
    """
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            logging_handle.info(message)
            return_value = False
            try:
                return_value = func(*args, **kwargs)
            except Exception as e:
                logging_handle.error("{}\r\n{}".format(e, traceback.format_exc()))
            finally:
                if return_value is not False:
                    return return_value
                else:
                    raise exception_type("异常: {}".format(message))
        return inner
    return decorator


def startup_teardown(*, startup=None, teardown=None, sleep=1):
    """
    ! 被包装的函数需要属于类。
    1. 运行被包装的函数前如果startup是方法，则首先运行startup方法；
    2. 打印被包装的函数函数所属的类，方法名
    3. 被包装的函数运行后，如果teardown是方法，首先运行teardown，然后结束。
    :param startup: 运行被包装的函数前需要执行的函数
    :param teardown: 运行被包装的函数后需要执行的函数
    :param sleep: 函数运行后需要等待的时间。
    :return: None
    """
    def parser(cls, funcs):
        func, remain_params = funcs[0], funcs[1:]
        func_entity = getattr(cls, func, None)
        return parser(func_entity, remain_params) if len(remain_params) else func_entity

    def inner(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            exc_type, exc_val, _ = None, None, None

            if isinstance(startup, list):

                all_logger.info("{} {}.{}.{}.startup {}".format(
                    "=" * 20,
                    func.__module__,
                    self.__class__.__name__,
                    func.__name__,
                    "=" * 20)
                )

                try:
                    parser(self, startup)()
                except Exception as e:
                    all_logger.error("{}.startup异常：{}".format(func.__name__, e))

            all_logger.info("{} {}.{}.{} {}".format(
                "=" * 20, func.__module__,
                self.__class__.__name__,
                func.__name__,
                "=" * 20)
            )

            try:
                func(self, *args, **kwargs)
            except Exception:  # noqa
                exc_type, exc_val, _ = sys.exc_info()
                all_logger.error("\n{}\n".format(traceback.format_exc()))
            finally:
                if isinstance(teardown, list):
                    all_logger.info("{} {}.{}.{}.teardown {}".format(
                        "=" * 20,
                        func.__module__,
                        self.__class__.__name__,
                        func.__name__,
                        "=" * 20)
                    )
                    try:
                        parser(self, teardown)()
                    except Exception as e:
                        all_logger.error("{}.teardown异常：{}".format(func.__name__, e))

                if exc_type and exc_val:
                    raise exc_type(exc_val)

            time.sleep(sleep)
        return wrapper
    return inner
