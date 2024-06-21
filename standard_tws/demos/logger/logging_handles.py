import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
import sys


log_fmt = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s %(module)s->%(lineno)d->%(funcName)s->%(message)s")

# console handler
console_handler = StreamHandler(stream=sys.stdout)
console_handler.setFormatter(fmt=log_fmt)
console_handler.setLevel(logging.INFO)
# at command handler
at_handler = RotatingFileHandler(filename='_at.log', maxBytes=10485760, backupCount=10)
at_handler.setFormatter(fmt=log_fmt)
at_handler.setLevel(logging.DEBUG)
# all log handler
all_log_handler = RotatingFileHandler(filename='_all.log', maxBytes=10485760, backupCount=10)
all_log_handler.setFormatter(fmt=log_fmt)
all_log_handler.setLevel(logging.DEBUG)

# set all logger
all_logger = logging.getLogger("all_log")
all_logger.setLevel(logging.DEBUG)
all_logger.addHandler(all_log_handler)
all_logger.addHandler(console_handler)

# set at logger
at_logger = logging.getLogger("at_log")
at_logger.setLevel(logging.DEBUG)
at_logger.addHandler(all_log_handler)
at_logger.addHandler(at_handler)
at_logger.addHandler(console_handler)
