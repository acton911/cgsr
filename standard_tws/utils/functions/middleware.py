from utils.log import log
from utils.logger.logging_handles import all_logger
from openpyxl import load_workbook
import os
import subprocess
import getpass
import sys
import requests


class Middleware:

    def __init__(self, **kwargs):
        # 设置传入的变量
        for k, v in kwargs.items():
            setattr(self, k, v)

        # 设置不进行QXDM和QLog捕获的Case
        self.non_qxdm_case = ['fota', 'ab_system', 'upgrade', 'pretest', 'backup', 'all_atc', 'ota', 'productive',
                              'cclk', 'mbim_sar', 'allatc']
        self.non_qxdm_case.append('flynn')
        self.catch_log_flag = self.is_need_catch_log()

        # 获取QXDM config 文件名称
        if not getattr(self, "dmc_file_name", None):
            script_dir = os.path.dirname(sys.argv[0])
            all_logger.info(f"script_dir: {script_dir}")
            if os.name == 'nt':
                self.dmc_file_name = "default_template.dmc"  # Windows 默认的DMC文件
            else:
                self.dmc_file_name = 'defaultNR5G1216.cfg'

        # 拼接QXDM config路径
        if os.name == 'nt':
            self.dmc_file_path = os.path.join("C:\\", "Users", getpass.getuser(), "QXDM_conf", self.dmc_file_name)
        else:
            self.dmc_file_path = os.path.join("/home/ubuntu/Desktop/QLog/conf", self.dmc_file_name)
        all_logger.info(f"\n当前使用的Log配置文件：{self.dmc_file_name}\n路径：{self.dmc_file_path}")
        if not os.path.exists(self.dmc_file_path):
            all_logger.error(f"路径：{self.dmc_file_path} 不存在，无法抓取Log，如果是自动化设备，请统一部署，如果是调试设备，无需关注")

        # 判断是否传入log_save_path
        if not getattr(self, "log_save_path", None):
            raise TypeError("必须指定一个Log的存储路径")

        # 判断是否传入超时时间，如果没有超时时间，则默认1800S
        if not getattr(self, "timeout", None):
            self.timeout = 1800  # default timeout 1800s

        # Case运行结果
        self.case_result = None

    def is_need_catch_log(self):
        # 如果传入code_case并且code_case包含self.non_qxdm_case的字符串，则不进行QXDM Log捕获
        if getattr(self, 'code_case'):
            all_logger.info("当前已经传入code_case")
            for case in self.non_qxdm_case:
                if case in self.code_case.lower():
                    all_logger.info(f"\n{case}因为涉及自定义升级，暂不加入QXDM Log捕获内容")
                    return False
        return True

    def __getattr__(self, item):
        return self.__dict__.get(item)

    def __enter__(self):
        if self.catch_log_flag:
            # code_case不包含self.non_qxdm_case则抓取Log
            log.catch_log(self.dmc_file_path, self.log_save_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        all_logger.info(f"\nexc_type: {exc_type}; exc_val: {exc_val}; exc_tb: {exc_tb}")
        if self.catch_log_flag:  # 如果之前需要抓取Log，则进行保存和判断是否删除的动作
            # 停止Log抓取并且保存Log
            all_logger.info("stop_catch_log_and_save")
            log.stop_catch_log_and_save(self.log_save_path)
            # 判断当前是否需要删除log，如果再MiddleWare类中设置了cur_task_id，则代表需要判断是否要进行QXDM Log删除
            all_logger.info("get cur_task_id info")
            if getattr(self, "cur_task_id"):
                all_logger.info(f"cur_task_id: {self.cur_task_id}")
                case_result = self.get_case_result(self.cur_task_id)
                if case_result:
                    all_logger.info(f"m.log_save_path: {self.log_save_path}")
                    self.del_qxdm_log(self.log_save_path)

    def find_log_file(self):
        """
        QUTS和QLog的保存的Log名称不固定，需要用os.walk()查找到保存的QXDM文件
        :return: 找到了QXDM Log文件:( log_name, log_path)；没有找到QXDM Log文件("", "")
        """
        for path, dirs, files in os.walk(self.log_save_path):
            # X6X为bin文件
            for file in files:
                qxdm_file_types = (".bin", )
                if file.endswith(qxdm_file_types):
                    log_path = os.path.join(path, file)
                    log_name = os.path.basename(log_path)
                    return log_name, log_path

            # 如果没有bin文件，使用下面格式
            for file in files:
                qxdm_file_types = (".hdf", '.qmdl2', '.isf')
                if file.endswith(qxdm_file_types):
                    log_path = os.path.join(path, file)
                    log_name = os.path.basename(log_path)
                    return log_name, log_path
        else:
            return '', ''

    def find_qdb_file(self):
        """
        QLog保存包含.qdb文件，如果有qdb文件才能解析，首先要找到qdb文件，然后传参。
        :return: (qdb_name, qdb_path), or "", ""
        """
        for path, dirs, files in os.walk(self.log_save_path):
            for file in files:
                if file.endswith('.qdb'):
                    qdb_path = os.path.join(path, file)
                    qdb_name = os.path.basename(qdb_path)
                    return qdb_name, qdb_path
        else:
            return "", ""

    @staticmethod
    def del_qxdm_log(path):
        """
        删除指定目录的所有QXDM Log
        :param path: 需要删除的QXDM Log路径文件
        :return: None
        """
        if os.name == 'nt':
            del_cmd = f'del /F /S /Q {path}'
        else:
            del_cmd = f'sudo rm -rf "{path}"'
        all_logger.info(f"del_cmd: {del_cmd}")
        all_logger.info(subprocess.getstatusoutput(del_cmd))

    @staticmethod
    def get_report_path(task_id):
        """
        根据task_id从monitor的API查询当前case的日志保存路径。
        :param task_id: 当前任务的task_id
        :return: case_id
        """
        all_logger.info("request http://127.0.0.1:12100/query/case")
        query_case_url = "http://127.0.0.1:12100/query/case"
        data = {'task_id': task_id}
        r = requests.get(query_case_url, params=data)
        all_logger.info(f"r.json(): {r.json()}")
        msg = r.json().get("msg")
        if msg:
            report_path = msg.get("report_path")
            all_logger.info(f"current report_path: {report_path}")
            return report_path
        else:
            return ''

    def get_case_result(self, task_id):
        """
        找到XLSX文件后，查找TestResult字段
        :param task_id: task_id
        :return: True: Case PASS;False: Case Fail.
        """
        if self.case_result is not None:
            return self.case_result

        xlsx_file_path = self.get_report_path(task_id)
        all_logger.info(f"xlsx_file_path: {xlsx_file_path}")
        if not xlsx_file_path:
            return False

        case_result = False  # 默认False保存Log

        try:
            # 所有行放入列表
            lines = list()
            wb = load_workbook(xlsx_file_path)
            ws = wb.active
            for row in ws.rows:
                line_list = list()
                for cell in row:
                    line_list.append(cell.value)
                if line_list:
                    lines.append(line_list)

            # 取首行最后一行拼接成字典
            title, *_, result = lines
            case_result = dict(zip(title, result))

            # 字典取出结果并返回
            case_result = case_result.get('TestResult')
            case_result = False if case_result == 'FAIL' else True
            self.case_result = case_result
        except Exception as e:
            all_logger.error(e)

        return case_result


if __name__ == '__main__':
    with Middleware(log_save_path=os.getcwd()) as m:
        # 业务逻辑
        # ------------
        all_logger.info("start")
        import time
        time.sleep(10)
        all_logger.info("end")
        # ------------

        # 停止抓Log
        log.stop_catch_log_and_save(m.log_save_path)
        log_n, log_p = m.find_log_file()

        # # 发送本地Log文件
        # message_types = {"LOG_PACKET": ["0xB821"]}
        # interested_return_filed = ["DEFAULT_FORMAT_TEXT", "PACKET_NAME", "PACKET_ID", "PACKET_TYPE", "TIME_STAMP_STRING",
        #                            "RECEIVE_TIME_STRING", "SUMMARY_TEXT"]
        # log.load_log_from_remote(log_p, message_types, interested_return_filed)
        #
        # # read_from_data_view
        # data = log.read_from_remote_data_view()
        # print(data)

        # DEBUG不删除qxdm log,防止误删文件夹
        sys.exit(0)
