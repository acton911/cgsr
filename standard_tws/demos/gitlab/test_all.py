import os
import tarfile
from tempfile import TemporaryDirectory
from utils.functions.gitlab_api import GitlabAPI
import time


script = 'windows_mbim_app.py'
with TemporaryDirectory() as script_path_temp:
    # TODO: 此处改为配置文件形式
    gitlab_root_url = "https://stgit.quectel.com/"
    gitlab_token = 'cL3SbdF3x2XzmfxxyVkk'
    path = script_path_temp
    project_id = 679
    project_branch = 'develop'
    gl = GitlabAPI(gitlab_root_url=gitlab_root_url, gitlab_token=gitlab_token, path=path)
    gl.download_project_branch(project=project_id, branch=project_branch)
    cache_tar = os.path.join(script_path_temp, project_branch + '.tar')
    script_path_temp_list = os.listdir(script_path_temp)
    with tarfile.open(cache_tar) as t:
        t.extractall(path=script_path_temp)
    extract_dir = set(os.listdir(script_path_temp)).difference(script_path_temp_list).pop()
    script_path = os.path.join(script_path_temp, extract_dir, script)  # 脚本实际路径：缓存路径+解压路径+脚本名称
    print(script_path)
    time.sleep(100)
