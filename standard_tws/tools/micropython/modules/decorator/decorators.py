from functools import wraps
import traceback
from modules.logger import logger


def exception_logger(func):
    """
    获取异常，使用logging打印后抛出异常
    """
    @wraps(func)
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logger.error(traceback.format_exc())
            raise
    return inner
