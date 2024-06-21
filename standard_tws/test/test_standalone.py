r"""
在系统下发参数测试完成后，使用系统下发的参数进行测试；

需要：
1. params的地址，例如：C:\\Users\Flynn.Chen\TWS_TEST_DATA\MBIM(Windows)_SDX55_20210922_201800\common_app\params
2. 最新脚本文件的地址，例如：D:\OneDrive\Projects\PythonProject\standard_tws\windows_mbim_app.py

如果需要修改需要测试的功能项里修改对应的func参数，写死固定某个Case进行测试。
"""
import getpass
import subprocess
import logging
from threading import Thread
import time
import os


# 必填参数
script_path = r"D:\OneDrive\Projects\PythonProject\standard_tws\windows_mbim_app.py"
params_path = r"C:\Users\Flynn.Chen\TWS_TEST_DATA\MBIM(Windows)_SDX55_20210922_201800\common_app\params"

# 无需改动
logging.basicConfig(level=logging.DEBUG)
all_logger = logging.getLogger(__name__)
charset = 'GBK' if os.name == 'nt' else 'utf-8'
summary = "standalone test"
func = "standalone func"
script = "standalone script"


class FatalError(Exception):
    """Fatal Error"""


class ThreadReadStderr(Thread):
    """
    读取stderr的线程，因为Linux系统在subprocess.poll() not None的状态部分log还是不会读取完毕;
    放入线程增加读取延迟可以解决此问题。
    """
    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.pipeline_cache = []
        self.daemon = True
        self.start()

    def run(self):
        while True:
            time.sleep(0.001)
            try:
                line = self.pipeline.stderr.readline().decode(charset, 'ignore')
                if line:
                    self.pipeline_cache.append(line)
            except ValueError:  # ValueError: readline of closed file
                pass

    def get_result(self, max_len=512):
        """
        获取stderr中的字符
        :param max_len: 最大长度
        :return: stderr中的字符串
        """
        time.sleep(0.1)
        return ''.join(self.pipeline_cache)[-max_len:]


# 获取Python的统一运行目录
if os.name == 'nt':  # windows的Python统一存放路径
    python_path = os.path.join("C:\\Users", getpass.getuser(), 'python_tws', 'python.exe')
else:  # Ubuntu20.04环境
    python_path = 'python3'

# 记录log
all_logger.info('进行{}脚本测试，测试项\r\n{}: {}'.format(script, func, summary))
all_logger.info('cmd： {}'.format(f'{python_path} {script_path} "{params_path}"'))
# 运行脚本
process = subprocess.Popen(f'{python_path} {script_path} "{params_path}"',
                           shell=False if os.name == 'nt' else True,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           cwd=os.getcwd(),
                           )
# 创建一个读取stderr的线程
stderr = ThreadReadStderr(process)
# 循环读取stdout，直到程序结束
while process.poll() is None:
    time.sleep(0.001)
    stdout = process.stdout.readline().decode(charset, 'ignore')
    if stdout:
        print(stdout.strip())
# 获取stderr管道中的信息
stderr_cache = stderr.get_result()

# 根据不同的return code进行相应的操作
all_logger.info(f'stderr_cache: {stderr_cache}')
all_logger.info(f'process.returncode: {process.returncode}')
if process.returncode == 4:  # 影响APP运行的严重错误, 抛出异常，上层try语句捕获异常
    raise FatalError(stderr_cache)
elif process.returncode == 0:  # 正常结束
    upload_dict = {'Notes': '', 'ActualInfo': summary, 'QATID': func}
    all_logger.info(upload_dict)
    all_logger.info("状态码0，脚本正常结束")
else:  # 其他非0、4 状态码
    upload_dict = {'Notes': 'Fail原因:{}'.format(stderr_cache), 'ActualInfo': summary, 'QATID': func}
    all_logger.info(upload_dict)
    all_logger.info(f"状态码{process.returncode}，脚本运行异常")
