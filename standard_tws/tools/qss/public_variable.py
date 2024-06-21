from logger import logger

busy_time = 0
task_started = 0
qss_status = 'free'


def motify_qss_status(status_mofify):
    global qss_status
    qss_status = status_mofify
    logger.info(f'已经修改qss_status为{qss_status}')


def motify_task_started(started_mofify):
    global task_started
    task_started = started_mofify
    logger.info(f'已经修改task_started为{task_started}')


def motify_time(time_mofify):
    global busy_time
    busy_time = time_mofify
    logger.info(f'已经修改busy时间为{time_mofify}')


def time_add(time):
    global busy_time
    busy_time = busy_time + time
    logger.info(f'+{time}')


def time_pass(time):
    global busy_time
    busy_time = busy_time - time
    logger.info(f'-{time}')
