import os
import re
import threading
import time
import jenkins
import requests
import urllib3
from ..logger.logging_handles import all_logger
from ..exception.exceptions import JenkinsError
import hashlib


# 增加小米DFOTA包制作
def merge_fota_full_images(target_file, file_name, lock):
    jenkins_url = "http://sw.jenkins.quectel.com"
    auth = ("Jeckson.yin@quectel.com", "Admin@123456")
    job_name = "merge_fota_full_images"

    all_logger.info('acquire lock')  # avoid multi thread get same work id.
    lock.acquire()

    all_logger.info('step 1: test jenkins server')
    r = requests.get(jenkins_url, auth=auth)
    r.raise_for_status()

    all_logger.info("step 2： get next build number")
    next_job = requests.get(
        "{0:s}/job/{1:s}/api/json".format(
            jenkins_url,
            job_name,
        ),
        auth=auth,
    )
    next_job.raise_for_status()
    next_build_number = next_job.json()['nextBuildNumber']
    all_logger.info("triggering build: {0:s} #{1:d}".format(job_name, next_build_number))

    all_logger.info("step 3: build with param")
    with open(target_file, 'rb') as f2:
        data, content_type = urllib3.encode_multipart_formdata([
            ('project_type', 'SDX55-delta-gentools'),
            ("target_version.zip", (f2.name, f2.read())),
            ("package_name", os.path.basename(file_name)),
            ("Submit", "Build")])

    request_url = "{0:s}/job/{1:s}/buildWithParameters".format(
        jenkins_url,
        job_name,
    )
    all_logger.info("requests url is : {}".format(request_url))
    response = requests.post(request_url, auth=auth, data=data, headers={"content-type": content_type}, verify=False)
    response.raise_for_status()
    all_logger.info("job triggered successfully")
    lock.release()  # release when job triggered success

    all_logger.info('step 4: get zip file')
    get_url = "{0:s}/job/{1:s}/{2:d}/artifact/{3:s}".format(
        jenkins_url,
        job_name,
        next_build_number,
        os.path.basename(file_name)
    )
    get_url_md5 = "{0:s}/job/{1:s}/{2:d}/artifact/md5".format(
        jenkins_url,
        job_name,
        next_build_number,
    )
    all_logger.info('get url is: {}'.format(get_url))
    timeout = 10 * 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(get_url, auth=auth, timeout=30)
            r.raise_for_status()
            with open(file_name, 'wb') as f:
                f.write(r.content)
            md5_recv = hashlib.md5()
            md5_recv.update(r.content)

            md5_r = requests.get(get_url_md5, auth=auth, timeout=30)
            md5_content = md5_r.content.decode('utf-8').split('  ')[0]

            if md5_content != md5_recv.hexdigest():
                all_logger.error('md5 校验异常 \n{}\n{}'.format(md5_recv.hexdigest(), md5_content))
                continue

            all_logger.info('get {} package success'.format(file_name))
            break
        except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout):
            all_logger.info('waiting {} package...'.format(file_name))
            time.sleep(20)
    else:
        all_logger.info("fail to get {} zip file".format(file_name))


# 增加小米DFOTA包制作
def multi_thread_merge_fota_full_images(origin_file, target_file):
    a_file_name = "a-b&;|.zip"
    b_file_name = "b-a&;|.zip"
    a_file_path = os.path.join(os.getcwd(), 'firmware', a_file_name)
    b_file_path = os.path.join(os.getcwd(), 'firmware', b_file_name)
    lock = threading.Lock()

    t1 = threading.Thread(target=merge_fota_full_images, args=(target_file, a_file_path, lock))
    t2 = threading.Thread(target=merge_fota_full_images, args=(origin_file, b_file_path, lock))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()

    timeout = 10 * 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(5)
        all_logger.info("time used: {} s".format(round(time.time() - start_time, 2)))
        files = os.listdir(os.path.join(os.getcwd(), 'firmware'))
        if a_file_name in files and b_file_name in files:
            all_logger.info('make dfota package success')
            break
    else:
        raise JenkinsError("fail to make dfota package")


def merge_version(origin_file, target_file, file_name, lock):
    jenkins_url = "http://sw.jenkins.quectel.com"
    auth = ("flynn.chen@quectel.com", "114d6e1435e6cd8dc04703a7a678a1934e")
    job_name = "merge_version"

    all_logger.info('acquire lock')  # avoid multi thread get same work id.
    lock.acquire()

    all_logger.info('step 1: test jenkins server')
    r = requests.get(jenkins_url, auth=auth)
    r.raise_for_status()

    all_logger.info("step 2： get next build number")
    next_job = requests.get(
        "{0:s}/job/{1:s}/api/json".format(
            jenkins_url,
            job_name,
        ),
        auth=auth,
    )
    next_job.raise_for_status()
    next_build_number = next_job.json()['nextBuildNumber']
    all_logger.info("triggering build: {0:s} #{1:d}".format(job_name, next_build_number))

    all_logger.info("step 3: build with param")
    with open(origin_file, 'rb') as f1:
        with open(target_file, 'rb') as f2:
            data, content_type = urllib3.encode_multipart_formdata([
                ('project_type', 'SDX55-delta-gentools'),
                ("original_version.zip", (f1.name, f1.read())),
                ("target_version.zip", (f2.name, f2.read())),
                ("package_name", os.path.basename(file_name)),
                ("multi_fota", True),
                ("Submit", "Build")])

    request_url = "{0:s}/job/{1:s}/buildWithParameters".format(
        jenkins_url,
        job_name,
    )
    all_logger.info("requests url is : {}".format(request_url))
    response = requests.post(request_url, auth=auth, data=data, headers={"content-type": content_type}, verify=False)
    response.raise_for_status()
    all_logger.info("job triggered successfully")
    lock.release()  # release when job triggered success

    all_logger.info('step 4: get zip file')
    get_url = "{0:s}/job/{1:s}/{2:d}/artifact/{3:s}".format(
        jenkins_url,
        job_name,
        next_build_number,
        os.path.basename(file_name)
    )
    get_url_md5 = "{0:s}/job/{1:s}/{2:d}/artifact/md5".format(
        jenkins_url,
        job_name,
        next_build_number,
    )
    all_logger.info('get url is: {}'.format(get_url))
    timeout = 10 * 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(get_url, auth=auth, timeout=30)
            r.raise_for_status()
            with open(file_name, 'wb') as f:
                f.write(r.content)
            md5_recv = hashlib.md5()
            md5_recv.update(r.content)

            md5_r = requests.get(get_url_md5, auth=auth, timeout=30)
            md5_content = md5_r.content.decode('utf-8').split('  ')[0]

            if md5_content != md5_recv.hexdigest():
                all_logger.error('md5 校验异常 \n{}\n{}'.format(md5_recv.hexdigest(), md5_content))
                continue

            all_logger.info('get {} package success'.format(file_name))
            break
        except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout):
            all_logger.info('waiting {} package...'.format(file_name))
            time.sleep(20)
    else:
        all_logger.info("fail to get {} zip file".format(file_name))


def multi_thread_merge_version(origin_file, target_file):
    a_file_name = "a-b&;|.zip"
    b_file_name = "b-a&;|.zip"
    a_file_path = os.path.join(os.getcwd(), 'firmware', a_file_name)
    b_file_path = os.path.join(os.getcwd(), 'firmware', b_file_name)
    lock = threading.Lock()

    t1 = threading.Thread(target=merge_version, args=(origin_file, target_file, a_file_path, lock))
    t2 = threading.Thread(target=merge_version, args=(target_file, origin_file, b_file_path, lock))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()

    timeout = 10 * 60
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(5)
        all_logger.info("time used: {} s".format(round(time.time() - start_time, 2)))
        files = os.listdir(os.path.join(os.getcwd(), 'firmware'))
        if a_file_name in files and b_file_name in files:
            all_logger.info('make dfota package success')
            break
    else:
        raise JenkinsError("fail to make dfota package")


def query_key(adb_id, qtype='adb'):
    user = 'cris.hu@quectel.com'
    passwd = 'hxc111....'
    try:
        server = jenkins.Jenkins('http://sw.jenkins.quectel.com/', username='{}'.format(user),
                                 password='{}'.format(passwd))
        server.get_whoami()
        server.get_version()
    except Exception:
        return 'login_fail'
    job_info = server.get_job_info('query_key')
    next_job_num = job_info['nextBuildNumber']  # 获取下一个job号
    params = [{'ID': '{}'.format(adb_id), 'qtype': '{}'.format(qtype)}]  # 定义参数
    server.build_job('query_key', *params)
    st = time.time()
    while True:
        time.sleep(0.001)
        last_job_num = server.get_job_info('query_key')['lastCompletedBuild']['number']  # 查询最新创建完成的job号
        if int(last_job_num) == int(next_job_num):  # 如果最新完成的job号与创建job前获取的下一个job号一致说明创建完成，直接查询结果
            break
        if time.time() - st > 60:
            return 'query_fail'
    info = server.get_build_console_output('query_key', next_job_num)
    passwd = ''.join(re.findall('您所查询的密钥为：(.*)', info))
    return passwd


def merge_SDX6X_AB_gentools(origin_file, target_file, file_name, module_version, module_id, oc_key, lock):
    """
    Jenkins制作ABFOTA差分包函数。
    step 1: test jenkins server
    step 2： get next build number
    step 3: build with param
    step 4: get zip file
    :return: None
    """
    jenkins_url = "http://sw.jenkins.quectel.com"
    auth = ("Jeckson.yin@quectel.com", "Admin@1234567")
    job_name = "merge_SDX6X_AB_gentools"

    all_logger.info('acquire lock')  # avoid multi thread get same work id.
    lock.acquire()

    all_logger.info('step 1: test jenkins server')
    r = requests.get(jenkins_url, auth=auth)
    r.raise_for_status()

    all_logger.info("step 2： get next build number")
    next_job = requests.get(
        "{0:s}/job/{1:s}/api/json".format(
            jenkins_url,
            job_name,
        ),
        auth=auth,
    )
    next_job.raise_for_status()
    next_build_number = next_job.json()['nextBuildNumber']
    all_logger.info("triggering build: {0:s} #{1:d}".format(job_name, next_build_number))

    all_logger.info("step 3: build with param")
    if oc_key == '8':
        with open(origin_file, 'rb') as f1:
            with open(target_file, 'rb') as f2:
                data, content_type = urllib3.encode_multipart_formdata([
                    ("new.zip", (f2.name, f2.read())),
                    ("multifota", True),
                    ("module_id", module_id),
                    ("module_version", module_version),
                    ("package_name", os.path.basename(file_name)),
                    ("Submit", "Build")])
        # 准备参数
        a = os.path.basename(file_name)
        b = 'amp;'
        str_list = list(a)
        str_list.insert(4, b)
        package_name = ''.join(str_list)
        all_logger.info("***********************************package_name参数为:{}***********************************".format(package_name))
        now_paragmeters = {"multifota": 'checked="true"',
                           'new.zip': os.path.basename(target_file),
                           "module_id": module_id,
                           "module_version": module_version,
                           "package_name": package_name}
        all_logger.info("******************************now_paragmeters参数为:{}**********************************" .format(now_paragmeters))
        for i in range(100):
            # 获取一个历史构建id
            before_build_number = next_job.json()['builds'][i]['number']
            # 获取本次构建的参数
            before_job = requests.get(
                # "{0:s}/job/{1:s}/{2:s}/api/json".format(
                "{0:s}/job/{1:s}/{2:s}/parameters".format(
                    jenkins_url,
                    job_name,
                    str(before_build_number),
                ),
                auth=auth,
            )
            before_job.raise_for_status()
            # 查询本次构建是否成功
            before_job_status = requests.get(
                "{0:s}/job/{1:s}/{2:s}/api/json".format(
                    jenkins_url,
                    job_name,
                    str(before_build_number),
                ),
                auth=auth,
            )
            before_job_status.raise_for_status()
            # 获取历史job id的构建结果，如果成功返回SECCESS
            bulid_status = before_job_status.json()['result']
            # all_logger.info('result:{}'.format(bulid_status))
            # 失败的项目跳过
            if bulid_status != 'SUCCESS':
                all_logger.info("Build #:" + str(before_build_number) + "构建失败,跳过!")
                continue
            # 开始比对成功项目的参数
            already_find_flag = True
            return_value = before_job.text
            # return_value = before_job_status.json()
            for j in now_paragmeters:
                if '"new.zip"' in return_value:
                    already_find_flag = False
                    break
                if now_paragmeters[j] in return_value:
                    all_logger.info("已经在Build #:" + str(before_build_number) + "中找到相同参数值:")
                    all_logger.info(j + ":" + now_paragmeters[j])
                else:
                    all_logger.info("没有在Build #:" + str(before_build_number) + "中找到相同参数值:")
                    all_logger.info(j + ":" + now_paragmeters[j])
                    already_find_flag = False
                    break
            if already_find_flag:
                all_logger.info("已经在jenkins历史中找到相同参数值的且构建成功Build: #" + str(before_build_number))
                break
        else:
            all_logger.info("没有在jenkins历史中找到相同参数值且构建成功的Build!")

        if not already_find_flag:
            request_url = "{0:s}/job/{1:s}/buildWithParameters".format(
                jenkins_url,
                job_name,
            )
    else:
        with open(origin_file, 'rb') as f1:
            with open(target_file, 'rb') as f2:
                data, content_type = urllib3.encode_multipart_formdata([
                    ("old.zip", (f1.name, f1.read())),
                    ("new.zip", (f2.name, f2.read())),
                    ("multifota", True),
                    ("module_id", module_id),
                    ("module_version", module_version),
                    ("package_name", os.path.basename(file_name)),
                    ("Submit", "Build")])
        # 准备参数
        now_paragmeters = {"multifota": 'checked="true"',
                           'old.zip': os.path.basename(origin_file),
                           'new.zip': os.path.basename(target_file),
                           "module_id": module_id,
                           "module_version": module_version,
                           "package_name": os.path.basename(file_name)}
        for i in range(5, 100):
            # 获取一个历史构建id
            before_build_number = next_job.json()['builds'][i]['number']
            # 获取本次构建的参数
            before_job = requests.get(
                # "{0:s}/job/{1:s}/{2:s}/api/json".format(
                "{0:s}/job/{1:s}/{2:s}/parameters".format(
                    jenkins_url,
                    job_name,
                    str(before_build_number),
                ),
                auth=auth,
            )
            before_job.raise_for_status()
            # 查询本次构建是否成功
            before_job_status = requests.get(
                "{0:s}/job/{1:s}/{2:s}/api/json".format(
                    jenkins_url,
                    job_name,
                    str(before_build_number),
                ),
                auth=auth,
            )
            before_job_status.raise_for_status()
            # 获取历史job id的构建结果，如果成功返回SECCESS
            bulid_status = before_job_status.json()['result']
            # all_logger.info('result:{}'.format(bulid_status))
            # 失败的项目跳过
            if bulid_status != 'SUCCESS':
                all_logger.info("Build #:" + str(before_build_number) + "构建失败,跳过!")
                continue
            # 开始比对成功项目的参数
            already_find_flag = True
            return_value = before_job.text
            for j in now_paragmeters:
                if now_paragmeters[j] in return_value:
                    all_logger.info("已经在Build #:" + str(before_build_number) + "中找到相同参数值:")
                    all_logger.info(j + ":" + now_paragmeters[j])
                else:
                    all_logger.info("没有在Build #:" + str(before_build_number) + "中找到相同参数值:")
                    all_logger.info(j + ":" + now_paragmeters[j])
                    already_find_flag = False
                    break
            if already_find_flag:
                all_logger.info("已经在jenkins历史中找到相同参数值且构建成功的Build: #" + str(before_build_number))
                break
        else:
            all_logger.info("没有在jenkins历史中找到相同参数值且构建成功的Build!")

        if not already_find_flag:
            request_url = "{0:s}/job/{1:s}/buildWithParameters".format(
                jenkins_url,
                job_name,
            )
    if not already_find_flag:
        all_logger.info("requests url is : {}".format(request_url))
        response = requests.post(request_url, auth=auth, data=data, headers={"content-type": content_type}, verify=False)
        response.raise_for_status()
        all_logger.info("job triggered successfully")
    lock.release()  # release when job triggered success
    # str(before_build_number)
    if already_find_flag:
        all_logger.info('已找到历史Build直接下载')
        all_logger.info('step 4: get zip file')
        get_url = "{0:s}/job/{1:s}/{2:d}/artifact/out/{3:s}".format(
            jenkins_url,
            job_name,
            before_build_number,
            os.path.basename(file_name)
        )
    else:
        all_logger.info('step 4: get zip file')
        get_url = "{0:s}/job/{1:s}/{2:d}/artifact/out/{3:s}".format(
            jenkins_url,
            job_name,
            next_build_number,
            os.path.basename(file_name)
        )
    all_logger.info('get url is: {}'.format(get_url))
    timeout = 10 * 60 * 3
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            r = requests.get(get_url, auth=auth, timeout=30)
            r.raise_for_status()
            with open(file_name, 'wb') as f:
                f.write(r.content)
            all_logger.info('get {} package success'.format(file_name))
            break
        except (requests.exceptions.HTTPError, requests.exceptions.ReadTimeout):
            all_logger.info('waiting {} package...'.format(file_name))
            time.sleep(20)
    else:
        all_logger.info("fail to get {} zip file".format(file_name))


def multi_thread_merge_SDX6X_AB_gentools(origin_file, target_file, prev_name_sub_version, name_sub_version, module_id, oc_key, unmatch_version=False):
    """
    Jenkins制作差分包。
    :return: None
    """
    a_file_name = "a-b&;|.zip"
    b_file_name = "b-a&;|.zip"
    if unmatch_version:
        a_file_path = os.path.join(os.getcwd(), 'firmware', 'unmatch', a_file_name)
        b_file_path = os.path.join(os.getcwd(), 'firmware', 'unmatch', b_file_name)
    else:
        a_file_path = os.path.join(os.getcwd(), 'firmware', a_file_name)
        b_file_path = os.path.join(os.getcwd(), 'firmware', b_file_name)
    lock = threading.Lock()
    all_logger.info("参数origin_file, target_file, prev_name_sub_version, name_sub_version, module_id, oc_key分别为:\r\n{}\r\n{}\r\n{}\r\n{}\r\n{}\r\n{}".format(origin_file, target_file, prev_name_sub_version, name_sub_version, module_id, oc_key))
    t1 = threading.Thread(target=merge_SDX6X_AB_gentools, args=(origin_file, target_file, a_file_path, name_sub_version, module_id, oc_key, lock))
    t2 = threading.Thread(target=merge_SDX6X_AB_gentools, args=(target_file, origin_file, b_file_path, prev_name_sub_version, module_id, oc_key, lock))
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()

    timeout = 10 * 60 * 3
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(5)
        all_logger.info("time used: {} s".format(round(time.time() - start_time, 2)))
        if unmatch_version:
            files = os.listdir(os.path.join(os.getcwd(), 'firmware', 'unmatch'))
        else:
            files = os.listdir(os.path.join(os.getcwd(), 'firmware'))
        if a_file_name in files and b_file_name in files:
            all_logger.info('make dfota package success')
            break
    else:
        raise JenkinsError("fail to make ab_system package")
