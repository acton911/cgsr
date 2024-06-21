import os

log = None

if os.name == 'nt':
    from utils.log.quts_api import QUTS
    log = QUTS()
else:
    from utils.log.qlog_api import QLog
    log = QLog()
