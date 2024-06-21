"""
必须配合monitor启动后才能运行
"""
import pickle
from tapp_constructor import constructor
import io
import logging
import tapp_constructor.Common.log as log

logging.basicConfig(level=logging.DEBUG)
all_logger = logging.getLogger(__name__)


class AutoPyLiteOperation(constructor.TestOperation):

    def run(self):
        all_logger.info("enter")
        with open('joker_params', 'rb') as f:
            params = pickle.load(f)

        constructor.current_test_case = {"id_case": params['case_setting']['id_case']}
        constructor.main_task_id = "1641622888517734402"
        constructor.current_test_case['type_exec'] = 'aa'
        constructor.original_setting = dict()
        constructor.original_setting['token'] = 'EDFCB630692FF342FEE5603F61A65A79E5653C75D359EC67'

        # monkey patch to get pylite error info
        stderr_detail = io.StringIO()
        def log_error(self, info):  # noqa
            stderr_detail.write(info)
            log.app_log.error(info)
        constructor.TestOperation.log_error = log_error

        # main pylite logic
        constructor.StandardScriptOperation().run(**params)

        all_logger.debug(f"stderr_detail.getvalue(): {stderr_detail.getvalue()}")


if __name__ == '__main__':
    pylite = AutoPyLiteOperation()
    pylite.run()