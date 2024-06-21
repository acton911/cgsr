import argparse
import time
from tapp_constructor import constructor, log
from utils.logger.logging_handles import all_logger
from utils.functions.screen_capture import ScreenCapture
from windows_mbim import WindowsMBIM
from comtypes.gen.UIAutomationClient import *  # noqa


class MyTestOperation(constructor.TestOperation):  # TestOperation,自定义测试业务类继承该类，重写run方法
    def run(self, **params):

        # App执行测试业务会传入参数case_setting, dict类型
        video = None
        try:
            # 获取记录参数
            all_logger.info("===========params: {}".format(type(params)))
            # original_setting
            original_setting = eval(params['original_setting']) if params.get('original_setting', None) else constructor.original_setting
            all_logger.info("original_setting: {} , type{}".format(original_setting, type(original_setting)))
            # main device
            main_device = original_setting['res'][0]
            all_logger.info("main_device: {} , type{}".format(main_device, type(main_device)))
            # minor device
            minor_device = original_setting['res'].pop()
            all_logger.info("minor_device: {} , type{}".format(minor_device, type(minor_device)))
            # all device
            devices = original_setting['res']
            all_logger.info("devices: {} , type{}".format(devices, type(devices)))
            # task id
            main_task_id = original_setting['task_id']
            all_logger.info("main_task_id: {} , type{}".format(main_task_id, type(main_task_id)))
            all_logger.info("params: {} , type{}".format(params, type(params)))
            # case_setting
            case_setting = eval(params['case_setting']) if params.get('case_setting', None) else original_setting['case_setting']  # 取得case_setting
            all_logger.info("case_setting: {} , type{}".format(case_setting, type(case_setting)))
            # script context
            script_context = case_setting["script_context"]  # 脚本所有TWS系统传参
            all_logger.info("script_context: {} , type{}".format(script_context, type(script_context)))
            # debug
            all_logger.info("WindowsMBIM: {} , type{}".format(WindowsMBIM, type(WindowsMBIM)))

            # 解压的属性
            at_port = main_device['usbat']  # TWS系统返回的AT口的端口号
            dm_port = "COM{}".format(script_context['dm_port'])  # 获取DM口端口号
            ipv6_address = script_context['ipv6_address']  # ipv6服务器的地址
            mbim_driver_name = script_context['mbim_driver_name']  # 设备管理器中mbim驱动的名称
            func = script_context['func']

            # 上传当前case的summary
            # self.upload_steplog(case_setting['summary'])

            params_dict = {
                "at_port": at_port,
                "dm_port": dm_port,
                "ipv6_address": ipv6_address,
                "mbim_driver_name": mbim_driver_name,
            }
            video = ScreenCapture(func)
            video.start()

            # 执行相应的case
            flag = False
            test_time = self.get_test_timestamp()
            fail_reason = ''
            try:
                all_logger.info('进行测试项:{}: {}'.format(func, case_setting['summary']))
                exec("WindowsMBIM(**{}).{}()".format(params_dict, func))
            except Exception as e:
                fail_reason = e
                all_logger.error(e)
                flag = True
            case_title = {'Notes': 'Fail原因:{}'.format(fail_reason) if flag else '', 'ActualInfo': case_setting['summary'], 'QATID': func}

            # 保存视频
            video.flag = True
            time.sleep(1)
            if flag is False:
                video.remove()

            # if flag:
            #     self.note_casestep_fail(test_time, **case_title)
            # else:
            #     self.note_casestep_pass(test_time, **case_title)
            # self.commit_operation_status(status='2')        # 上传状态码'2'，代表正常结束
            log.app_log.info('INFO LOG')  # INFO日志记录
        except Exception as e:
            if getattr(video, "flag", None):  # 异常后保存视频
                video.flag = True
                time.sleep(1)
            str('#').center(108, '=')
            self.log_error(repr(e))       # App log 记录 error 级别
            # self.commit_operation_status(status='3',        # 上传状态码'3'，代表异常，最好将错误信息也上传
            #                              task_info=str(e))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get Test Setting')
    parser.add_argument('--m', dest='test_setting', type=str)
    parser.add_argument('-o', dest='original_setting', type=str)
    parser.add_argument('-c', dest='case_setting', type=str)
    args = parser.parse_args()
    print(args)
    # MyTestOperation().run(**vars(args))

    # my_app = constructor.TestApp(**vars(args))  # TestApp类，初始化参数是启动app的参数，默认的测试是标准的测试流程
    # my_operation = MyTestOperation()  # 实例化
    # my_app.AUTO_PYTHON_OPERATION = my_operation  # python业务
    # my_app.UPGRADE_OPERATION.disable()  # 禁用升级业务
    # my_app.start()  # 执行测试
