# -*- encoding=utf-8 -*-
import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
import sys
import io
import requests
import traceback
from functools import partial, partialmethod
import json
from requests.auth import HTTPBasicAuth

# host
host_url = 'http://192.168.29.170:8000'

# ======================= patch some new method to logging class ============================

# define new logging level named trace
logging.TRACE = 25
logging.addLevelName(logging.TRACE, 'TRACE')  # noqa
logging.trace = partial(logging.log, logging.TRACE)  # noqa


def log(self, level, msg, *args, **kwargs):
    # this part is as same as logging.Logger.log method
    if not isinstance(level, int):
        if logging.raiseExceptions:
            raise TypeError("level must be an integer")
        else:
            return

    if self.isEnabledFor(level):
        self._log(level, msg, args, **kwargs)

    # self-hosted method
    if level >= logging.TRACE:  # noqa only level > TRACE
        emit_log(msg)


def make_request(test_type, payload):
    try:
        test_type = test_type.split("_")[1]  # 把auto_python先用split按照_切分成列表，再取后面的单词
        r = requests.post(
            url=f"{host_url}/api/{test_type}/",
            data=payload,
            auth=HTTPBasicAuth('log', 'logloglog'),
            timeout=5,
        )
        if r.status_code != 201 and r.status_code != 200:
            all_logger.info(f"failed to push log:\n{payload}\nr.content{r.content}")
    except requests.exceptions.RequestException as e:
        all_logger.info(f"failed to push log:{e}")
    except Exception as e:
        all_logger.info(f"failed to push log:{e} {traceback.format_exc()}")


def emit_log(msg):
    try:  # auto_python, auto_pylite and auto_stress
        msg = json.loads(msg)
        test_type = msg.get('part')
        supported_test_type = ['auto_python', 'auto_pylite', 'auto_stress']
        if test_type in supported_test_type:
            make_request(test_type, msg)
        else:
            all_logger.info(f"unsupported test type: {repr(test_type)}")

    except (json.decoder.JSONDecodeError, AttributeError):
        stream_data = log_stream.getvalue().encode('utf-8', 'ignore')
        all_logger.info(f"stream_data: {stream_data}")

    except Exception as e:
        all_logger.info(f"emit_log unknown error: {e}")

    finally:
        log_stream.seek(0)
        log_stream.truncate(0)


# replace original logging method with our new method
logging.Logger.log = log
logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)  # noqa
logging.Logger.error = partialmethod(logging.Logger.log, logging.ERROR)
logging.Logger.fatal = partialmethod(logging.Logger.log, logging.FATAL)
logging.Logger.critical = partialmethod(logging.Logger.log, logging.CRITICAL)

# ======================= define logging format and handlers ============================

# define logging fmt
log_fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(filename)s:%(lineno)d->%(funcName)s %(message)s")
# define logging handlers
# stream logger
log_stream = io.StringIO()
stream_handler = StreamHandler(stream=log_stream)
stream_handler.setFormatter(fmt=log_fmt)
stream_handler.setLevel(logging.TRACE)  # noqa
# console handler
console_handler = StreamHandler(stream=sys.stdout)
console_handler.setFormatter(fmt=log_fmt)
console_handler.setLevel(logging.INFO)
# at command handler
at_handler = RotatingFileHandler(filename='_at.log', maxBytes=10485760, backupCount=10)
at_handler.setFormatter(fmt=log_fmt)
at_handler.setLevel(logging.DEBUG)
# all log handler
all_log_handler = RotatingFileHandler(filename='_.log', maxBytes=10485760, backupCount=10)
all_log_handler.setFormatter(fmt=log_fmt)
all_log_handler.setLevel(logging.DEBUG)

# define logging instance
# set all logger
all_logger = logging.getLogger("all_log")
all_logger.setLevel(logging.DEBUG)
all_logger.addHandler(all_log_handler)
all_logger.addHandler(console_handler)
all_logger.addHandler(stream_handler)
# set at logger
at_logger = logging.getLogger("at_log")
at_logger.setLevel(logging.DEBUG)
at_logger.addHandler(all_log_handler)
at_logger.addHandler(at_handler)
at_logger.addHandler(console_handler)
at_logger.addHandler(stream_handler)

# all_logger.debug("debug")
# all_logger.info("info")
# all_logger.trace("trace")  # noqa
# all_logger.error("error")
# all_logger.fatal("fatal")
# all_logger.critical("critical")
# at_logger.debug("debug")
# at_logger.info("info")
# at_logger.trace("trace")  # noqa
# at_logger.error("error")
# at_logger.fatal("fatal")
# at_logger.critical("critical")

# data = {'part': 'auto_python',
#         'timestamp': 1661914116,
#         'script': 'linux_sms_app.py',
#         'func': 'test_sms_19_001',
#         'code_case': 'SMS_Sagemcom-19-001',
#         'summary': '针对部分项目，测试结束关闭ims，恢复默认',
#         'result': 0,
#         'return_code': 0,
#         'exec_time': 5,
#         'stderr_detail': ''}
# import json
#
# at_logger.trace(json.dumps(data))
# all_logger.trace(json.dumps(data))
