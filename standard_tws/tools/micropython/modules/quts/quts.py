import os
from modules.logger import logger


class QUTSCheat:
    """
    如果测试的PC既没有安装QUTS，也没有/home/ubuntu/Desktop/QLog文件夹，则使用这个虚拟类，保证API统一调用不报错。
    """
    def __init__(self, *args, **kwargs):
        pass

    def catch_log(self, *args, **kwargs):
        pass

    def stop_catch_log_and_save(self, *args, **kwargs):
        pass

    def backup_qcn(self, *args, **kwargs):
        pass

    def stop_quts_service(self, *args, **kwargs):
        pass

    @staticmethod
    def restore_qcn(*args, **kwargs):
        return 3  # 没有安装QUTS返回3

# Windows使用QUTS API：
# 1. 需要保证QXDM和QUTS安装，安装后QUTS Service相关目录在C:\Program Files (x86)\Qualcomm\QUTS\Support\python
# 2. Windows的QUTS使用的QXDM Log抓取模板放在 C:\Users\Flynn.Chen\QXDM_conf下面，默认需要有default_template.dmc文件

# Ubuntu使用QUTS API
# 1. QLog文件夹默认在/home/ubuntu/Desktop/QLog
# 2. QLog的QXDM Log模板存在/home/ubuntu/Desktop/QLog/conf文件夹下


if os.name == 'nt':  # Windows
    installed_qxdm = os.path.exists(r'C:\Program Files (x86)\Qualcomm\QUTS\Support\python')
    if not installed_qxdm:  # 如果没有安装QXDM，使用假的QXDM，避免micropython异常
        logger.error("\n未安装QXDM，如果需要使用QXDM API，请安装QXDM或使用在线Log解析服务" * 3)
        QUTS = QUTSCheat  # 替换为假的QXDM接口
    else:
        from .quts_windows import QUTS
else:  # Ubuntu
    qlog_exists = os.path.exists(r'/home/ubuntu/Desktop/QLog')
    if not qlog_exists:  # 如果没有安装QLog，使用假的QLog，避免异常
        logger.error("\n未安装QLog，如果需要使用QLog API，请安装QLog或者使用在线Log解析服务" * 3)
        QUTS = QUTSCheat  # 替换为假的QXDM接口
    else:
        from .quts_linux import QUTS

# 打印相关注释内容
logger.info(QUTS)
logger.debug(dir(QUTS))
