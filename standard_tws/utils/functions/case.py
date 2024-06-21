# -*- encoding=utf-8 -*-
# 关于TWS和Case相关操作的基础函数库
import configparser
import sys
from tempfile import TemporaryDirectory
from utils.functions.gitlab_api import GitlabAPI
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import FatalError
from utils.operate.at_handle import ATHandle
from threading import Thread
from collections.abc import Iterable
import json
import tarfile
import os
import re
import time
import getpass
import requests
import subprocess
from tapp_constructor.auto_handler import MessageType, request_api, API, TOOL_NAME


charset = 'GBK' if os.name == 'nt' else 'utf-8'


def is_laptop(qgmr_version):
    """
    根据AT+QGMR查询的版本号判断是否为笔电，放在case里面是方便所有Case调用，后续也方便修改
    :param qgmr_version: AT+QGMR的返回值
    :return: True：是笔电; False：不是笔电
    """
    all_logger.info(f"is_laptop qgmr_version: {qgmr_version}")
    # 老的笔电判断 RM520NGLAPR01A03M4G_01.001.01.001_V03
    if '520' in qgmr_version or '530' in qgmr_version:
        if qgmr_version[8:10] == 'AP':
            return True
    # 2022-05-27新增的判断 RM520NGLAAR01A05M4G_02.001.02.001_V01
    if '520NGLAA' in qgmr_version and '_02.' in qgmr_version:
        return True
    # 2022-11-08新增判断，RM520NGLAA _03，LTE接手笔电修改
    if '520NGLAA' in qgmr_version and '_03.' in qgmr_version:
        return True

    all_logger.info("当前非笔电版本")
    return False  # 非笔电


def upload_msg(msg_type, tool_name, task_id, msg):
    """
    Func: upload_msg
    Desp: 消息上传，调用monitor的消息推送api，发送消息
    Params: msg_type 枚举类MessageType成员 消息类型
            tool_name str类型 工具名称
            task_id  str类型 task_id
            msg str类型 上传的消息文本
    Return：None
    Raise: UploadMsgError
    """
    try:
        if not isinstance(msg_type, MessageType):
            raise FatalError('Failed to upload message, unsupported message type: %s' % str(msg_type))
        upload_data = {
            'type': msg_type.value,
            'tool_name': tool_name,
            'taskid': task_id,
            'msg': msg
        }
        request_api(API.UPLOAD_MSG, upload_data)
    except Exception as e:
        all_logger.error(e)


def upload_step_log(task_id, log_text):
    upload_msg(MessageType.INFO, TOOL_NAME, task_id, log_text)


def get_case_json_file():
    """
    获取系统下发的所有CASE的JSON字符串，例如：ec6d4550dce.json
    :return: 如果找到，则返回文件路径，没找到返回False
    """
    for file in os.listdir():
        if file.endswith('.json') and not file.startswith('device'):  # 如果是json文件，并且不是device_data.json
            file_name = os.path.join(os.getcwd(), file)
            all_logger.info(f"case json file is: {file_name}")
            return file_name
    all_logger.info(f"can not find json file: {os.listdir()}")
    return False


def get_case_seq(uid):
    """
    获取所有的Case个数，获取当前Case在所有Case中的序号。
    :param uid: Case的uuid
    :return: (7, 25) 如果uuid能找到，返回7代表在所有Case的序号，25表示所有的Case数。
    """
    file = get_case_json_file()
    if file:
        try:
            with open(file, encoding='utf-8') as f:
                cases = json.load(f)
                cases_num = len(cases)
                for num, case in enumerate(cases):
                    if uid == case.get("uuid"):
                        return num + 1, cases_num  # 返回一个元组，例如：(7, 25)
        except Exception as e:
            all_logger.info(f'parse {file} failed: {e}')
    return 0  # 如果uuid没有匹配上


def api_get_case_seq(task_id):
    """
    ！仅当前task_id正在运行时候可以查询
    向monitor请求当前执行到第几个Case，总共有几个Case。
    :param task_id:
    :return:
    """
    for i in range(10):
        try:
            query_case_url = "http://127.0.0.1:12100/query/case"
            data = {'task_id': task_id}
            r = requests.get(query_case_url, params=data)
            ret = r.json()
            all_logger.info(ret)
            if r.status_code == 200 and ret.get('code') == 210:
                msg = ret.get('msg')
                case_index = msg.get('case_index') + 1  # 从index 0开始，当前case计数的话从1开始
                sum_cases = msg.get('sum_cases')  # Case总数
                return case_index, sum_cases
            time.sleep(1)
        except Exception as e:
            all_logger.error(f"http://127.0.0.1:12100/query/case查询当前task_id: {task_id}返回异常：{e}")
    else:
        raise FatalError(f"http://127.0.0.1:12100/query/case查询当前task_id: {task_id}返回值异常")


def get_python_path():
    """
    获取Windows和Ubuntu的统一python目录，用于制定本地Python环境运行。
    :return: 当前环境的Python路径。
    """
    # 获取Python的统一运行目录
    if os.name == 'nt':  # windows的Python统一存放路径
        python_path = os.path.join("C:\\Users", getpass.getuser(), 'python_tws', 'python.exe')
    else:  # Ubuntu20.04环境
        python_path = 'python3'
    return python_path


def auto_python_param_check(params):
    """
    Auto Python运行时将用到的TWS下发参数进行检查，如果有异常，直接报错。
    :param params: TWS tapp_constructor Tapp类 run方法的传参
    :return: 解析后的TWS系统参数
    """
    all_logger.info(f"params: {params}\ntype(params):{type(params)}")
    if isinstance(params, dict) is False:
        raise FatalError(f"Auto Python Params 非字典类型，请确认：\nparams:{params}\ntype(params):{type(params)}")

    args = FlattenNestDict(params)
    if not args.uuid:
        raise FatalError("TWS系统Case相关参数未下发uuid，请和TWS系统人员确认")
    if not args.func:
        raise FatalError("TWS系统Case lib中当前Case未配置Context或Context中未设置func参数")
    if not args.script:
        raise FatalError("TWS系统Case lib中当前Case未配置Context或Context中未设置script参数")
    if not args.code_case:
        raise FatalError("TWS系统Case参数异常，未返回当前Case的Case Number，请检查Case和原始参数")
    if not args.summary:
        raise FatalError("TWS系统Case参数异常，未返回当前Case的Summary，请检查Case和原始参数")

    # 写入文件记录
    with open('tws_params.txt', 'a', encoding='utf-8', errors='replace', buffering=1) as f:
        f.write(f'str(params): {str(params)}\r\n')
        f.write(f'uuid: {args.uuid}\r\n')
        f.write(f'func: {args.func}\r\n')
        f.write(f'script: {args.script}\r\n')
        f.write(f'code_case: {args.code_case}\r\n')
        f.write(f'summary: {args.summary}\r\n\r\n')

    return args


def get_git_params():
    """
    解析common_config.ini文件中的git参数，不同项目仅需修改common_config.ini中的git参数为项目实际git。
    :return: 解析的各种参数
    """
    config = configparser.ConfigParser()
    config.read('common_config.ini')
    git = config['Git']
    gitlab_root_url = git['url']
    gitlab_token = git['token']
    project_id = git.getint('project_id')
    project_branch = git['project_branch']
    return gitlab_root_url, gitlab_token, project_id, project_branch


def get_temp_path():
    """
    自定义缓存路径。
    :return:
    """
    # 拼接temp_dir路径
    if os.name == "nt":
        temp_dir = os.path.join("C:\\", "Users", getpass.getuser(), 'script_temp')
    else:
        temp_dir = os.path.join("/root", 'script_temp')

    # 如果没有，则创建
    if os.path.exists(temp_dir) is False:
        all_logger.info(f"make temp_dir: {temp_dir}")
        os.mkdir(temp_dir)
    all_logger.info(f"temp_dir: {temp_dir}")

    return temp_dir


def download_unzip_script(script_path_temp, script_name):
    """
    下载解压gitlab的脚本，存到缓存中
    :param script_path_temp: TemporaryDirectory()创建的缓存路径
    :param script_name: 需要执行的脚本名称
    :return: 下载解压后的脚本路径
    """
    gitlab_root_url, gitlab_token, project_id, project_branch = get_git_params()
    gl = GitlabAPI(gitlab_root_url=gitlab_root_url, gitlab_token=gitlab_token, path=script_path_temp)
    gl.download_project_branch(project=project_id, branch=project_branch)
    cache_tar = os.path.join(script_path_temp, project_branch + '.tar')
    # 解压并获取解压的路径
    script_path_temp_list = os.listdir(script_path_temp)
    with tarfile.open(cache_tar) as t:
        t.extractall(path=script_path_temp)
    extract_dir = set(os.listdir(script_path_temp)).difference(script_path_temp_list).pop()
    # 拼接脚本实际路径：缓存路径 + 解压路径 + 脚本名称
    script_path = os.path.join(script_path_temp, extract_dir, script_name)
    all_logger.info("script_path: {}".format(repr(script_path)))
    return script_path


def local_exec_new(script_path, params_path):
    start_timestamp = time.time()
    # 获取Python路径
    python_path = get_python_path()

    # 运行脚本
    all_logger.info(f'local_exec_new: {python_path} {script_path} "{params_path}"\ncwd:{os.getcwd()}')
    process = subprocess.Popen(f'{python_path} "{script_path}" "{params_path}"',
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
    exec_time = time.time() - start_timestamp
    # 获取stderr管道中的信息
    stderr_cache = stderr.get_result()  # ThreadReadStderr中读取的最后512字节信息
    stderr_detail = ''.join(re.findall(r'.*$', stderr_cache))  # Stderr中最后一行报错信息
    return_code = process.returncode
    return return_code, exec_time, stderr_cache, stderr_detail


def local_exec(script_name, params_path):
    """
    创建缓存文件夹->获取源脚本->解压源脚本->使用本地环境运行脚本
    :param script_name: 需要运行的脚本名称
    :param params_path: 参数序列化后文件的地址
    :return: 1. return_code：脚本执行后的状态码，由utils.exception.ExitCode1/ExitCode4控制返回值
             2. exec_time：脚本的执行时间
             3. stderr_cache：stderr中的最后512字节错误信息
             4. stderr_detail：stderr中的最后一行报错信息
    """
    start_timestamp = time.time()
    with TemporaryDirectory() as script_path_temp:
        # 下载tar包到缓存后解压
        script_path = download_unzip_script(script_path_temp, script_name)

        # 获取Python路径
        python_path = get_python_path()

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
        exec_time = time.time() - start_timestamp
        # 获取stderr管道中的信息
        stderr_cache = stderr.get_result()  # ThreadReadStderr中读取的最后512字节信息
        stderr_detail = ''.join(re.findall(r'.*$', stderr_cache))  # Stderr中最后一行报错信息
        return_code = process.returncode
        return return_code, exec_time, stderr_cache, stderr_detail


def need_upgrade(at_port, ati, csub, qgmr):
    """
    检测是否需要进行版本升级。
    :param at_port: AT口
    :param ati: ATI版本号
    :param csub: AT+CSUB版本号
    :param qgmr: AT+QGMR版本号
    :return: True：需要升级；False：不需要升级
    """
    try:
        all_logger.info("打开AT口判断当前版本是否升级")
        at_handle = ATHandle(at_port)
        version = at_handle.send_at('ATI+CSUB')
        qgmr_status = at_handle.send_at('AT+QGMR', 3)
        if ati not in version or csub.replace('-', '') not in version or qgmr not in qgmr_status:
            all_logger.info(f"版本号检测不一致，期望ATI: {ati}，CSUB：{csub.replace('-', '')}，QGMR：{qgmr}\n当前版本号：{version} {qgmr_status}")
            return True
        all_logger.info(f"版本号检测成功，期望ATI: {ati}，CSUB：{csub.replace('-', '')}，QGMR:{qgmr}\n当前版本号：{version} {qgmr_status}")
        return False
    except Exception as e:
        all_logger.info(f"版本号检测异常：{e}")
        return True


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


class FlattenNestDict:
    """
    将嵌套的字典（字典套字典）展开并将变量存储到类中。
    """
    def __init__(self, items):
        self.setter(items)

    def setter(self, item):
        if isinstance(item, dict) is False:  # 非字典元素，直接raise
            raise NotImplementedError("暂时不支持非字典元素展开")
        for key, value in item.items():
            if isinstance(value, dict):  # 如果k:v, v还是字典，继续展开
                self.setter(value)
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):  # 如果是Iterable的元素，并且不是str&bytes
                setattr(self, key, value)
                for v in value:
                    if isinstance(v, dict):  # 如果k:v, v还是字典，继续展开
                        self.setter(v)
            else:
                setattr(self, key, value)

    def __getattr__(self, item):
        return self.__dict__.get(item, '')


def change_slot(params_path, slot):
    """
    检查是否需要切换卡槽，需要就切
    :param params_path: 参数序列化后存放的路径
    :param slot: 需要切换的卡槽
    :return:
    """
    if os.name == 'nt' and sys.getwindowsversion().build > 20000:       # Win11,默认为笔电项目，需要设置上报口为Modem
        all_logger.info('笔电项目，暂不需切卡')
        return
    import pickle
    import serial
    # 首先解析原始参数
    try:
        # pickle反序列化
        with open(params_path, 'rb') as p:
            # original_setting
            content = pickle.load(p).test_setting  # noqa
            if not isinstance(content, dict):
                content = eval(content)
        at_port = content['res'][0]['usbat']
        all_logger.info(f'当前AT口为{at_port}')
    except SyntaxError:
        all_logger.info("[切卡] 切卡到包含需要的运营商SIM卡槽失败\n系统参数解析异常：\n原始路径: \n {}".format(repr(params_path)))
        raise Exception("[切卡] 切卡到包含需要的运营商SIM卡槽失败\n系统参数解析异常：\n原始路径: \n {}".format(repr(params_path)))
    # 2023-03-22 由于T750平台无需切卡，所以增加判断
    try:
        if 'T750' in content['res'][0]['chipPlatform']:
            all_logger.info('T750平台无需切卡')
            return
    except Exception as e:
        all_logger.info(e)
    version = content['version_name']
    if 'UCL' in version:
        all_logger.info('UCL项目不支持AT+QUIMSLOT指令，不做切卡操作')
        return True     # 该版本暂时标记不进行切卡操作
    for i in range(10):
        try:
            __at_port = serial.Serial(at_port, baudrate=115200, timeout=0)
            __at_port.close()
            break
        except Exception as e:
            all_logger.info(e)
            time.sleep(1)
            continue
    else:
        all_logger.info('[切卡] 切卡到包含需要的运营商SIM卡槽失败,打开AT口失败')
        raise Exception('[切卡] 切卡到包含需要的运营商SIM卡槽失败,打开AT口失败')
    try:
        at_handle = ATHandle(at_port)
        slot_value = ''
        for i in range(10):
            slot_value = at_handle.send_at('AT+QUIMSLOT?', 30)
            if '+QUIMSLOT:' in slot_value:
                break
            time.sleep(1)
        all_logger.info('[切卡] {}'.format(slot_value))
        if f'+QUIMSLOT: {slot}' in slot_value:
            all_logger.info('[切卡] 当前卡槽包含需要测试的运营商SIM卡，无需切换')
        else:
            all_logger.info('[切卡] 当前卡槽不包含需要测试的运营商SIM卡，需要切换卡槽')
            value_cache = at_handle.send_at(f'AT+QUIMSLOT={slot}', 30)
            all_logger.info('[切卡] {}'.format(value_cache))
            at_handle.readline_keyword('PB DONE', timout=50)
    except Exception:    # noqa
        all_logger.info('[切卡] 切卡到包含需要的运营商SIM卡槽失败,切换卡槽后，未检测到上报PB DONE')
        raise Exception('[切卡] 切卡到包含需要的运营商SIM卡槽失败,切换卡槽后，未检测到上报PB DONE')


def get_script_path(path, name):
    """
    从某个路径查找指定的文件名称
    :param path: 需要查找的路径
    :param name: 需要查找的文件名
    :return: 路径
    """
    file_list = []
    for p, _, files in os.walk(path):
        for file in files:
            file_list.append(file)
            if file == name:
                return os.path.join(p, name)
    all_logger.info(f'{path}文件夹下存在文件:{file_list}')
    raise FatalError(f"在{path}文件夹内未找到{name}文件")


if __name__ == '__main__':
    pass
