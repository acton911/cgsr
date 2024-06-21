import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
import sys
import os

# formatter
log_fmt = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s %(module)s->%(lineno)d->%(funcName)s->%(message)s")

# stdout handler
stdout_handler = StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(fmt=log_fmt)
stdout_handler.setLevel(logging.INFO)

# file handler
orig_path = os.path.abspath(os.path.dirname(sys.argv[0]))  # 脚本的源路径
filename = os.path.join(orig_path, "app.log")
file_handler = RotatingFileHandler(filename=filename, maxBytes=10485760, backupCount=10)
file_handler.setFormatter(fmt=log_fmt)
file_handler.setLevel(logging.DEBUG)

# output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)

logger.info(f"log save path: {filename}")
