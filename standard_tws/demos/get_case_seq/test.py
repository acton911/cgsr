import enum
import json

import requests

TORNADO_URL = 'http://127.0.0.1:11100/tornado'      # tornado api url
QFLASH = 'http://127.0.0.1:5000'    # qflash api url
M_MESSAGE = 'http://127.0.0.1:12100/Mmsg'    # monitor message api url
QLOG = 'http://127.0.0.1:11220'    # qLOG api url
# 请求类型枚举
class RequestMethod(enum.Enum):
    """
    接口请求method
    """
    GET = 0
    POST = 1

# 接口枚举
class API(enum.Enum):
    """
    接口url、method
    """
    TORNADO_QUERYSTATUS = (TORNADO_URL + '/querystatus', RequestMethod.GET, [])
    TORNADO_RUN = (TORNADO_URL + '/run', RequestMethod.POST, ['case_source', 'comport', 'task_id', 'perform_comport'])
    TORNADO_QUERYTASK = (TORNADO_URL + '/querytask', RequestMethod.GET, ['task_temp_id'])
    TORNADO_STOP = (TORNADO_URL + '/stop', RequestMethod.POST)
    QFLASH_RUN = (QFLASH + '/update', RequestMethod.POST)
    QFLASH_QUERY = (QFLASH + '/get_update_result', RequestMethod.GET)
    QFLASH_STOP = (QFLASH + '/stop', RequestMethod.POST)
    UPLOAD_MSG = (M_MESSAGE + '/upload', RequestMethod.POST, ['tool_name', 'taskid', 'type', 'msg'])
    UPLOAD_APP_STATUS = ('http://127.0.0.1:12100/upload/appstatus', RequestMethod.POST, ['task_id', 'status', 'app_exception_info'])
    UPLOAD_CASE_STATUS = ('http://127.0.0.1:12100/upload/casestatus', RequestMethod.POST, ['task_id', 'case_id', 'status', 'report_path', 'msg'])
    UPLOAD_UPGRADEPORT = ('http://127.0.0.1:12100/upload/upgradecomport', RequestMethod.POST, ['task_id', 'comport'])
    UPDATE_CASE_LOG = ('http://127.0.0.1:12100/update/caselog', RequestMethod.POST)
    QUERY_CASE = ('http://127.0.0.1:12100/query/case', RequestMethod.GET, ['task_id'])
    QUERY_UPGRADEPORT = ('http://127.0.0.1:12100/query/upgradecomport', RequestMethod.GET, ['task_id'])
    QLOG_RUN = (QLOG + '/start_qlog', RequestMethod.POST)
    QLOG_QUERY = (QLOG + '/get_qlog_result', RequestMethod.GET)
    QLOG_STOP = (QLOG + '/stop_qlog', RequestMethod.POST)



def request_api(api, data):
    try:
        api_info = api.value
        if api_info[1] == RequestMethod.GET:
            default_headers = requests.Session().headers
            default_headers.__delitem__("Connection")
            return requests.get(api_info[0], params=data, headers=default_headers)
        elif api_info[1] == RequestMethod.POST:
            default_headers = requests.Session().headers
            default_headers.__delitem__("Connection")
            post_request_header = {'Content-Type': 'application/json'}
            return requests.post(api_info[0], data=json.dumps(data), headers=post_request_header)
    except Exception as e:
        raise


def query_case(task_id):
    r = request_api(API.QUERY_CASE, {'task_id': task_id})
    r_data = r.json()
    return r_data

if __name__ == '__main__':
    print(query_case("1468504871534596098"))
