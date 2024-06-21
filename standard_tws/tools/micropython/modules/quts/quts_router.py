from flask import request, Blueprint
from modules.logger import logger
from modules.decorator import exception_logger
from .quts import QUTS
import os
import subprocess
import time

# Create quts Blueprint
quts_bp = Blueprint('quts', __name__)

# Initial QUTS real class
quts = QUTS()


# QUTS APIs
@quts_bp.post("/catch_log")
@exception_logger
def catch_log():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/catch_log post data must be JSON"}, 415

    args = request.get_json()
    dmc_file_path = args.get("dmc_file_path", None)
    log_file_path = args.get("log_save_path", None)

    if log_file_path is None and os.name != "nt":  # Ubuntu
        return {"error": "Request on http://127.0.0.1:port/catch_log post data must contain log_file_path and dmc_file_path"}, 415

    logger.info("catch_log")
    quts.catch_log(dmc_file_path, log_file_path)

    return {"msg": "success"}, 200


@quts_bp.post("/stop_catch_log_and_save")
@exception_logger
def stop_catch_log_and_save():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/stop_catch_log_and_save post data must be JSON"}, 415

    args = request.get_json()
    log_save_path = args.get("log_save_path", None)

    if log_save_path is None and os.name == 'nt':
        return {"error": "Request on http://127.0.0.1:port/stop_catch_log_and_save post data must contain log_save_path"}, 415

    logger.info("stop_catch_log_and_save")
    quts.stop_catch_log_and_save(log_save_path)

    return {"msg": "success"}, 200


@quts_bp.post("/backup_qcn")
@exception_logger
def backup_qcn():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/backup_qcn post data must be JSON"}, 415

    args = request.get_json()
    qcn_file_path = args.get("qcn_file_path", None)

    if qcn_file_path is None and os.name != "nt":  # Ubuntu
        return {"error": "Request on http://127.0.0.1:port/backup_qcn post data must contain qcn_file_path"}, 415

    logger.info("backup_qcn")
    quts.backup_qcn(qcn_file_path)

    return {"msg": "success"}, 200


@quts_bp.post("/restore_qcn")
@exception_logger
def restore_qcn():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/backup_qcn post data must be JSON"}, 415

    args = request.get_json()
    sn = args.get("sn", '')  # 此处如果TWS不填SN号
    if sn == '':  # SN为空（系统未填写SN号，直接跳出）
        return {"msg": "None"}, 200

    logger.info("restore qcn")
    status = quts.restore_qcn(sn)
    if status == 1:  # 找不到QCN文件，直接跳出
        return {'msg': "None"}, 200
    elif status == 2:  # 未知错误，跳出
        return {'msg': "Unknown"}, 200
    elif status == 3:  # quts如果被替换成QUTSCheat，则返回None
        return {'msg': "Uninstall"}, 200

    return {"msg": "success"}, 200


@quts_bp.post("/create_data_queue")
@exception_logger
def create_data_queue():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/create_data_queue post data must be JSON"}, 415

    args = request.get_json()
    message_types = args.get("message_types", None)
    interested_return_filed = args.get("interested_return_filed", None)
    data_queue_name = args.get("data_queue_name", "TEST")

    if message_types is None or interested_return_filed is None or data_queue_name is None:
        return {"error": "Request on http://127.0.0.1:port/stop_catch_log_and_save post data must contain "
                         "message_types and interested_return_filed, data_queue_name is optional"}, 415

    logger.info("create_data_queue")
    quts.create_data_queue(
        message_types=message_types,
        interested_return_filed=interested_return_filed,
        data_queue_name=data_queue_name
    )

    return {"msg": "success"}, 200


@quts_bp.post("/destroy_data_queue")
@exception_logger
def destroy_data_queue():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/destroy_data_queue post data must be JSON"}, 415

    args = request.get_json()
    data_queue_name = args.get("data_queue_name", "TEST")

    logger.info("destroy_data_queue")
    quts.destroy_data_queue(data_queue_name)

    return {"msg": "success"}, 200


@quts_bp.post("/read_from_data_queue")
@exception_logger
def read_from_data_queue():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/read_from_data_queue post data must be JSON"}, 415

    args = request.get_json()
    data_queue_name = args.get("data_queue_name", "TEST")

    logger.info("read_from_data_queue")
    ret = str(quts.read_from_data_queue(data_queue_name))

    return {"msg": ret}, 200


@quts_bp.post("/load_log_from_file")
@exception_logger
def load_log_from_file():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/load_log_from_file post data must be JSON"}, 415

    args = request.get_json()
    log_path = args.get("log_path", None)
    message_types = args.get("message_types", None)
    interested_return_filed = args.get("interested_return_filed", None)
    data_view_name = args.get("data_view_name", "TEST")

    if message_types is None or interested_return_filed is None or log_path is None or data_view_name is None:
        return {"error": "Request on http://127.0.0.1:port/stop_catch_log_and_save post data must contain "
                         "message_types and interested_return_filed, data_view_name is optional"}, 415

    logger.info("load_log_from_file")
    quts.load_log_from_file(
        log_path=log_path,
        message_types=message_types,
        interested_return_filed=interested_return_filed,
        data_view_name=data_view_name
    )

    return {"msg": "success"}, 200


@quts_bp.post("/read_from_data_view")
@exception_logger
def read_from_data_view():
    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/read_from_data_view post data must be JSON"}, 415

    args = request.get_json()
    data_view_name = args.get("data_view_name", "TEST")

    logger.info("read_from_data_view")
    ret = str(quts.read_from_data_view(data_view_name))

    return {"msg": ret}, 200


@quts_bp.post("/destroy_data_view")
@exception_logger
def destroy_data_view():

    if not request.is_json:  # judge if data is json
        return {"error": "Request on http://127.0.0.1:port/destroy_data_view post data must be JSON"}, 415

    args = request.get_json()
    data_view_name = args.get("data_view_name", "TEST")
    file_name = args.get("file_name", None)

    logger.info("destroy_data_view")
    quts.destroy_data_view(data_view_name)

    # remove saved QXDM log file in load_log_from_remote function
    if file_name:
        file_path = os.path.join(os.getcwd(), file_name)
        logger.info(f"del {file_path}")
        time.sleep(0.1)  # wait a moment to avoid PermissionError
        try:
            os.remove(file_path)
        except PermissionError:
            time.sleep(1)  # wait a moment to release file
            if os.name == 'nt':  # Windows用del命令删除
                s = subprocess.getoutput(f"del /q {file_path}")
                logger.info(f"s.output: {s}")
            else:  # Linux用rm -rf删除
                s = subprocess.getoutput(f'sudo rm -rf "{file_path}"')
                logger.info(f"s.output: {s}")

    return {"msg": "success"}, 200


@quts_bp.post("/load_log_from_remote")
@exception_logger
def load_log_from_remote():

    args = request.form
    logger.info(f"args: {args}")
    message_types = args.get("message_types", None)
    interested_return_filed = args.get("interested_return_filed", None)
    data_view_name = args.get("data_queue_name", "TEST")

    if message_types is None or interested_return_filed is None:
        return {"error": "Request on http://127.0.0.1:port/load_log_from_remote post data must contain "
                         "message_types and interested_return_filed, data_queue_name is optional"}, 415

    files = dict(request.files)
    if len(files) == 0:
        return {"error": "Request on http://127.0.0.1:port/load_log_from_remote post data must contain at least one file"}, 415

    # convert str to dict
    message_types = eval(message_types)
    interested_return_filed = eval(interested_return_filed)

    orig_log_path = None
    log_temp_path = os.getcwd()
    for file_name, content in files.items():
        # 非qdb文件为Log文件
        if not file_name.endswith(".qdb"):
            orig_log_path = os.path.join(log_temp_path, file_name)
        # 不管是什么文件，都要写入
        logger.info(f"log_temp_path: {log_temp_path}\nfile_name: {file_name}, content: {content}")
        with open(os.path.join(log_temp_path, file_name), mode='wb') as f:
            f.write(content.stream.read())

    del files

    logger.info("load_log_from_file")
    quts.load_log_from_file(
        log_path=orig_log_path,
        message_types=message_types,
        interested_return_filed=interested_return_filed,
        data_view_name=data_view_name
    )

    logger.info("read_from_data_view")
    ret = str(quts.read_from_data_view(data_view_name))

    return {"msg": ret}, 200


@quts_bp.get("/stop_quts_service")
@exception_logger
def stop_quts_service():
    quts.stop_quts_service()

    return {"msg": "success"}
