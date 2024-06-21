# -*- encoding=utf-8 -*-
import io

from tapp_constructor import constructor
from utils.functions.case import *
import argparse
import multiprocessing
import pickle
from utils.functions.middleware import Middleware
from utils.log.dump import catch_dump
from utils.functions.case import FlattenNestDict
import tapp_constructor.auto_handler as ah
import tapp_constructor.Common.log as log
from datetime import datetime


class StartupOperation(constructor.SetOperation):
    def run(self):
        all_logger.info("StartupOperation")
        # 初始化脚本名称
        script = get_script_path(script_temp_path, 'startup.py')

        # pickle序列化
        params_path = os.path.join(os.getcwd(), 'args')
        with open(params_path, 'wb') as p:
            pickle.dump(args, p)

        remote_case_status = None
        # 查询Monitor中最近上传的case info
        if cur_task_id:
            all_logger.info(cur_task_id)
            remote_case = ah.query_case(cur_task_id)
            if remote_case:  # task有上传过case信息
                remote_case_id = remote_case['case_id']
                remote_case_status = remote_case['status']
                all_logger.info(remote_case_id)
                all_logger.info(f'当前case上报状态码为{remote_case_status}')

        if remote_case_status != '4':   # 如果case最近上报的状态码为4，代表刚重启完，此时无需再进行初始化操作
            # 记录log
            all_logger.info('开始初始化')
            all_logger.info('cmd： {}'.format(f'{get_python_path()} {script} "{params_path}"'))

            # 运行脚本
            return_code, exec_time, stderr_cache, stderr_detail = local_exec_new(script, params_path)

            # 打印初始化状态信息
            status_log = "[ {:>6.2f}S ]  {}".format(exec_time, "初始化成功" if not stderr_cache else stderr_detail)
            all_logger.info(status_log)

            # 如果异常，直接结束
            if return_code != 0:
                raise FatalError(f"初始化失败异常:\nstderr: {stderr_cache}\nstatus_code: {return_code}")
        else:
            all_logger.info('case最近上报的状态码为4，代表刚重启完，此时无需再进行初始化操作')


class TeardownOperation(constructor.SetOperation):
    def run(self):
        all_logger.info("TeardownOperation")
        # 初始化脚本名称
        script = get_script_path(script_temp_path, 'teardown.py')

        # pickle序列化
        params_path = os.path.join(os.getcwd(), 'args')

        # 记录log
        all_logger.info('进行结束环境清理')
        all_logger.info('cmd： {}'.format(f'{get_python_path()} {script} "{params_path}"'))

        # 运行脚本
        return_code, exec_time, stderr_cache, stderr_detail = local_exec_new(script, params_path)

        # 打印初始化状态信息
        status_log = "[ {:>6.2f}S ]  {}".format(exec_time, "进行结束环境清理成功" if not stderr_cache else stderr_detail)
        all_logger.info(status_log)

        # 如果异常，直接结束
        if return_code != 0:
            raise FatalError(f"结束环境清理失败异常:\nstderr: {stderr_cache}\nstatus_code: {return_code}")


class AutoPythonOperation(constructor.TestOperation):
    def run(self, **params):
        # 解析检查原始数据
        args_tws = auto_python_param_check(params)
        code_case = params['case_setting'].get('code_case')
        qxdm_log_path = os.path.join(os.getcwd(), 'QXDM_log', code_case)
        all_logger.info(f"qxdm_log_path: {qxdm_log_path}")

        with Middleware(log_save_path=qxdm_log_path, code_case=code_case) as m:

            try:

                # pickle序列化
                case_setting = params['case_setting']
                params_path = os.path.join(os.getcwd(), 'auto_python_params')
                with open(params_path, 'wb') as p:
                    pickle.dump(args, p)
                    pickle.dump(case_setting, p)
                # 上传测试开始信息
                seq = get_case_seq(args_tws.uuid)
                self.upload_steplog(
                    '[ {} ]  {}: {}'.format(f'{seq[0]}/{seq[1]}' if seq else '0/0', args_tws.code_case, args_tws.summary))

                # 记录log
                all_logger.info(f'进行{args_tws.script}脚本测试，测试项\r\n{args_tws.func}: {args_tws.summary}')
                all_logger.info('cmd： {}'.format(f'{get_python_path()} {args_tws.script} "{params_path}"'))

                # 判断是否DUMP
                at_port = nest_args['res'][0]['usbat']
                dm_port = nest_args['res'][0]['upgrade']
                catch_dump(at_port, dm_port)

                # 判断是否需要进行切卡操作
                if case_setting:
                    slot = case_setting.get('mainSlotList')[0][0]  # 首先获取当前测试case需要的运营商在EVB哪个卡槽上
                    change_slot(params_path, slot)

                # 运行脚本
                script_path = get_script_path(script_temp_path, args_tws.script)
                return_code, exec_time, stderr_cache, stderr_detail = local_exec_new(script_path, params_path)

                # 收集的数据
                collect_data = {
                        'part': 'auto_python',  # log来源，必备
                        "client_send_time": str(datetime.now()),
                        "client_send_timestamp": int(time.time()),
                        'script': args_tws.script,
                        'func': args_tws.func,
                        'code_case': code_case,
                        'summary': args_tws.summary,
                        'result': 0 if return_code == 0 else 1,  # 0代表PASS，1代表FAIL
                        'return_code': return_code,
                        'exec_time': int(exec_time),
                        'stderr_detail': stderr_detail
                }
                collect_data.update(static_dict)
                all_logger.info(f'collect_data: {collect_data}')
                all_logger.trace(json.dumps(collect_data))

                # 查询Monitor中最近上传的case info
                if cur_task_id:
                    all_logger.info(cur_task_id)
                    remote_case = ah.query_case(cur_task_id)
                    if remote_case:  # task有上传过case信息
                        remote_case_id = remote_case['case_id']
                        remote_case_status = remote_case['status']
                        all_logger.info(remote_case_id)
                        all_logger.info(remote_case_status)
                        if str(remote_case_status) == '4':
                            all_logger.info('已上报重启状态码,等待重启')
                            time.sleep(120)

                # 上报运行状态信息
                status_log = "[ {:>6.2f}S ]  {}".format(exec_time, "测试PASS" if not stderr_cache else stderr_detail)
                self.upload_steplog(status_log)

                # 根据不同的return code进行相应的操作
                all_logger.info(f'stderr_cache: {stderr_cache}')
                all_logger.info(f'process.returncode: {return_code}')
                if return_code == 4:  # 影响APP运行的严重错误, 抛出异常，上层try语句捕获异常
                    raise FatalError(stderr_cache)
                elif return_code == 0:  # 正常结束
                    upload_dict = {'Notes': '', 'ActualInfo': args_tws.summary, 'QATID': args_tws.func}
                    all_logger.info(upload_dict)
                    self.note_casestep_pass(self.get_test_timestamp(), **upload_dict)
                    self.commit_operation_status(status='2')  # 上传状态码'2'，代表结束本条Case
                else:  # 其他非0、4 状态码
                    upload_dict = {'Notes': f'Fail原因:{stderr_cache}', 'ActualInfo': args_tws.summary, 'QATID': args_tws.func}
                    all_logger.info(upload_dict)
                    self.note_casestep_fail(self.get_test_timestamp(), **upload_dict)
                    self.commit_operation_status(status='2')  # 上传状态码'2'，代表结束本条Case

            except Exception as err:  # 阻碍APP运行的严重错误，直接上报系统3状态码，结束APP所有剩余的Case
                if '[切卡] 切卡到包含需要的运营商SIM卡槽失败' in str(err):  # 因为切卡失败的case结束本条
                    upload_dict = {'Notes': 'Fail原因:{}'.format('初始化过程切换卡槽失败'), 'ActualInfo': args_tws.summary,
                                   'QATID': args_tws.func}
                    self.note_casestep_fail(self.get_test_timestamp(), **upload_dict)
                    self.commit_operation_status(status='2')  # 上传状态码'2'，代表结束本条Case
                else:
                    self.commit_operation_status(status='3', task_info=str(err))
                    all_logger.error(err)
                    self.log_error(err)

            m.cur_task_id = cur_task_id  # 写入当前的task_id，在__exit__方法时候判断是否要进行Log删除


class AutoPyLiteOperation(constructor.TestOperation):
    def run(self, **params):
        case_setting = params['case_setting']
        code_case = case_setting.get('code_case')
        qxdm_log_path = os.path.join(os.getcwd(), 'QXDM_log', code_case)
        all_logger.info(f"qxdm_log_path: {qxdm_log_path}")
        params_path = os.path.join(os.getcwd(), 'auto_pylite_params')
        with Middleware(log_save_path=qxdm_log_path, code_case=code_case) as m:
            with open(params_path, 'wb') as p:
                pickle.dump(args, p)
                pickle.dump(case_setting, p)

            # 判断是否DUMP
            at_port = nest_args['res'][0]['usbat']
            dm_port = nest_args['res'][0]['upgrade']
            catch_dump(at_port, dm_port)

            # 进行切卡动作
            slot = case_setting.get('mainSlotList')[0][0]  # 首先获取当前测试case需要的运营商在EVB哪个卡槽上
            change_slot(params_path, slot)

            # monkey patch to get pylite error info
            stderr_detail = io.StringIO()
            def log_error(self, info):  # noqa
                stderr_detail.write(info)
                log.app_log.error(info)
            constructor.TestOperation.log_error = log_error

            # main pylite logic
            start_timestamp = time.time()
            constructor.StandardScriptOperation().run(**params)
            exec_time = time.time() - start_timestamp
            all_logger.debug(f"stderr_detail.getvalue(): {stderr_detail.getvalue()}")

            m.cur_task_id = cur_task_id  # 写入当前的task_id，在__exit__方法时候判断是否要进行Log删除

            try:
                args_tws = FlattenNestDict(params)

                # 收集的数据
                collect_data = {
                    'part': 'auto_pylite',  # log来源，必备
                    "client_send_time": str(datetime.now()),
                    "client_send_timestamp": int(time.time()),
                    'script': args_tws.script_name,
                    'func': '',
                    'code_case': code_case,
                    'summary': args_tws.summary,
                    'result': 0 if m.get_case_result(cur_task_id) else 1,  # 0代表PASS，1代表FAIL
                    'return_code': '',
                    'exec_time': int(exec_time),
                    'stderr_detail': stderr_detail.getvalue()
                }
                collect_data.update(static_dict)
                all_logger.info(f'collect_data: {collect_data}')
                all_logger.trace(json.dumps(collect_data))
            except Exception as e:
                all_logger.info(f"pylite parse log error: {e}")


class AutoAudioOperation(constructor.TestOperation):
    def run(self, **params):

        case_setting = params['case_setting']

        # 将部分参数DUMP到文件中
        params_path = os.path.join(os.getcwd(), 'auto_audio_params')
        with open(params_path, 'wb') as p:
            pickle.dump(args, p)
            pickle.dump(case_setting, p)

        # 进行切卡动作
        slot = case_setting.get('mainSlotList')[0][0]  # 首先获取当前测试case需要的运营商在EVB哪个卡槽上
        change_slot(params_path, slot)

        # 运行Audio
        constructor.StandardAudioOperation().run(**params)


if __name__ == '__main__':
    # 参数解析
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Get Test Setting')
    parser.add_argument('--m', dest='test_setting', type=str)
    args = parser.parse_args()
    all_logger.info(f"args: {repr(args)}, type(args): {type(args)}")
    # 获取脚本路径和当前的task_id
    nest_args = eval(args.test_setting)  # 此参数是系统传参的具体参数，可以参考standard_tws/docs/nest_args.txt文件
    script_temp_path = nest_args.get("script_temp_path")
    cur_task_id = nest_args.get("task_id")
    all_logger.info(f"script_temp_path: {script_temp_path}")
    # 获取通用的需要上报的字典
    try:
        static_dict = {
            'name_real_version': nest_args.get('name_real_version', ''),
            'name_sub_version': nest_args.get('name_sub_version', ''),
            'name_ati_version': nest_args.get('name_ati_version', ''),
            'name_csub': nest_args.get('name_csub', ''),
            'name_group': nest_args.get('name_group', ''),
            'chip_platform': nest_args['res'][0]['chipPlatform'],
            'hardware_type': nest_args['res'][0]['hardwareType'],
            'ip': nest_args['res'][0]['ip'],
            'node_name': nest_args['res'][0]['node_name'],
            'device_number': nest_args['res'][0]['device_number'],
            'material_model': nest_args['res'][0]['custom_fields_name'].get("material_model"),
            'environment_temperature': nest_args['res'][0]['custom_fields_name'].get("environment_temperature"),
            'task_id': cur_task_id
        }
    except Exception as err:
        all_logger.error(f"fail to get upload_dict: {err}")
        static_dict = dict()
    # 初始化TestApp类
    app = constructor.TestApp(**vars(args))
    # 自定义Startup和Teardown类
    app.INITIALIZE_OPERATION = StartupOperation()
    app.INITIALIZE_OPERATION.enable()
    app.FINALLY_OPERATION = TeardownOperation()
    app.FINALLY_OPERATION.enable()
    # 自定义Auto Python业务
    app.AUTO_PYTHON_OPERATION = AutoPythonOperation()
    # 自定义Auto PyLite业务
    app.AUTO_PYLITE_OPERATION = AutoPyLiteOperation()
    # 自定义Auto Audio业务
    app.AUTO_AUDIO_OPERATION = AutoAudioOperation()
    # 禁用升级
    app.UPGRADE_OPERATION.disable()
    # 执行测试
    app.start()
