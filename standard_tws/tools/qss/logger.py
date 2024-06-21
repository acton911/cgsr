import logging
from logging import StreamHandler
from logging.handlers import RotatingFileHandler
from getpass import getuser
import sys
import os

# formatter
log_fmt = logging.Formatter("[%(asctime)s.%(msecs)03d] %(levelname)s %(module)s->%(lineno)d->%(funcName)s->%(message)s")

# stdout handler
stdout_handler = StreamHandler(stream=sys.stdout)
stdout_handler.setFormatter(fmt=log_fmt)
stdout_handler.setLevel(logging.INFO)

# file handler
if os.name == 'nt':
    base_path = os.path.join("C:\\", "Users", getuser(), "Desktop", "qss_server")
    if not os.path.exists(base_path):
        os.mkdir(base_path)
    filename = os.path.join(base_path, "server.log")
else:
    filename = "server.log"
file_handler = RotatingFileHandler(filename=filename, maxBytes=10485760, backupCount=10)
file_handler.setFormatter(fmt=log_fmt)
file_handler.setLevel(logging.DEBUG)

# output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
