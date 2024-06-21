# 该模块为上传至系统上的app中内容，主要用于下载自动化case脚本，并执行Common_app
import configparser
import getpass
import os
import subprocess
import multiprocessing
import sys
import tarfile
from tempfile import TemporaryDirectory
import gitlab


fake_common_app_source_code = r"""# -*- encoding=utf-8 -*-
from tapp_constructor import constructor
import argparse
import multiprocessing


class StartupOperation(constructor.SetOperation):
    def run(self):
        self.upload_steplog("\b从stgit.quectel.com下载脚本失败：\n1. 请检查测试机是否有拨号连接并断开连接\n2. ping stgit.quectel.com检查是否正常\n在断开拨号连接后依然ping不通，请在“5G-自动化用例改造群”里反馈问题")
        self.commit_operation_status(status='3')  # 上传状态码'3'，代表结束整个Case


if __name__ == '__main__':
    # 参数解析
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Get Test Setting')
    parser.add_argument('--m', dest='test_setting', type=str)
    args = parser.parse_args()
    # 获取脚本路径和当前的task_id
    script_temp_path = eval(args.test_setting).get("script_temp_path")
    cur_task_id = eval(args.test_setting).get("task_id")
    # 初始化TestApp类
    app = constructor.TestApp(**vars(args))
    # 自定义Startup类
    app.INITIALIZE_OPERATION = StartupOperation()
    app.INITIALIZE_OPERATION.enable()
    # 禁用升级
    app.UPGRADE_OPERATION.disable()
    # 执行测试
    app.start()
"""


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


def get_local_tag_file():
    if os.name == 'nt':
        tag_config_path = os.path.join("C:\\Users", getpass.getuser(), 'tag')
    else:
        tag_config_path = os.path.join('/root', 'tag')

    # 没有发现tag文件，返回0
    if os.path.exists(tag_config_path) is False:
        return 0

    # 尝试读取tag
    with open(tag_config_path, 'rb') as f:
        tag_version = f.read().decode('utf-8')

    if tag_version != "":  # 如果不是空文件，返回文件内容
        return tag_version
    else:  # 如果是空文件，返回1
        return 1


def download_unzip_script(script_path_temp, script_name, dict_args):
    """
    下载解压gitlab的脚本，存到缓存中
    :param script_path_temp: TemporaryDirectory()创建的缓存路径
    :param script_name: 需要执行的脚本名称
    :param dict_args: dict类型的args
    :return: 下载解压后的脚本路径
    """
    try:
        # 参数获取
        gitlab_root_url, gitlab_token, project_id, project_branch = get_git_params()  # 获取project的GIT相关参数
        current_case = dict_args.get("name_group")  # 获取当前运行的Case名

        # Gitlab相关
        gl = GitlabAPI(gitlab_root_url=gitlab_root_url, gitlab_token=gitlab_token, path=script_path_temp)
        tag = get_local_tag_file()
        if tag == 0:  # 如果没有tag文件
            print(f"[execute app] 当前未发现tag文件，使用{project_branch}分支的最新文件")
            gl.download_project_branch(project=project_id, branch=project_branch)
            cache_tar = os.path.join(script_path_temp, project_branch + '.tar')
        elif tag == 1:  # 如果有tag文件，并且是空文件，默认使用case名的最新的tag
            latest_case_tag = gl.get_latest_tag_with_case_name(current_case, project_id)  # 根据Case名称获取系统最新的Tag
            branch = project_branch if latest_case_tag is None else latest_case_tag  # 如果没有查询到对应的Case有Tag，则使用默认的分支，否则用最新的Tag
            print(f"[execute app] 发现tag文件，tag文件内容为空，当前Case: {current_case}，最新tag：{latest_case_tag}，将使用{branch}进行测试")
            gl.download_project_branch(project=project_id, branch=branch)
            cache_tar = os.path.join(script_path_temp, branch + '.tar')
        else:  # 如果有tag文件，并且指定了版本，使用指定的版本进行测试
            print(f"[execute app] 发现tag文件，tag文件内容：{tag}，将使用{tag}进行测试")
            gl.download_project_branch(project=project_id, branch=tag)
            cache_tar = os.path.join(script_path_temp, tag + '.tar')

        # 解压并获取解压的路径
        script_path_temp_list = os.listdir(script_path_temp)
        with tarfile.open(cache_tar) as t:
            t.extractall(path=script_path_temp)
        extract_dir = set(os.listdir(script_path_temp)).difference(script_path_temp_list).pop()
        # 拼接脚本实际路径：缓存路径 + 解压路径 + 脚本名称
        script_path = os.path.join(script_path_temp, extract_dir, script_name)
        print("[execute app] script_path: {}".format(repr(script_path)))
        return script_path
    except Exception as e:  # 如果获取失败了，写入一个虚拟的common_app.py，这个common_app引发'3'异常，上传Log后结束
        print(f"从GITLAB获取脚本失败：{e}")
        script_path = os.path.join(os.getcwd(), "common_app.py")
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(fake_common_app_source_code)
        return script_path


class GitlabAPI:
    def __init__(self, gitlab_root_url="https://stgit.quectel.com/", gitlab_token='cL3SbdF3x2XzmfxxyVkk', path=os.getcwd()):
        self.url = gitlab_root_url  #
        self.token = gitlab_token
        self.path = path
        self.gl = None
        self.project = None

    def connect(self):
        self.gl = gitlab.Gitlab(self.url, self.token)

    def download_project_branch(self, project=679, branch='develop'):
        self.connect()
        self.project = self.gl.projects.get(project)
        path = os.path.join(self.path, '{}.tar'.format(branch))
        files = self.project.repository_archive(branch)
        with open(path, 'wb') as f:
            f.write(files)
        print(f'[execute app] download branch {branch} into {path} success')

    def get_latest_tag_with_case_name(self, case_name, project):
        """
        根据Case名称，获取对应项目中最新的Case名称对应的Tag
        :param case_name: 当前Case的名称
        :param project: gitlab的project id
        :return: 当前Case最新的Tag，None：对应Case可能一个Tag都没有
        """
        # 获取所有的Tag
        self.connect()
        self.project = self.gl.projects.get(project)
        all_tags = self.project.tags.list(all=True)
        print(f"all_tags: {all_tags}, len(all_tags): {all_tags}")
        # 获取所有的Tag名称
        all_tags_name = list(tag.name for tag in all_tags)
        print(f"all_tags_name: {all_tags_name}")
        # 根据Case名称，筛选所有包含Case名称的Tag
        case_tags = [name for name in all_tags_name if name.startswith(case_name)]
        if case_tags:
            print(f"case: {case_name}")
            print(f"case_tags: {case_tags}")
            # 对当前Case名称的Tag进行排序，并获取最新的tag
            latest_case_tag = sorted(case_tags).pop()
            print(f"latest_case_tags: {latest_case_tag}")
            return latest_case_tag
        else:
            return None


if __name__ == '__main__':
    multiprocessing.freeze_support()

    # 获取打印参数
    args = sys.argv[2]
    print(f"[execute app] args: {repr(args)}\n[execute app] type(args): {type(args)}")

    # 获取Python环境和脚本缓存路径
    python_path = fr"C:\Users\{getpass.getuser()}\python_tws\python.exe" if os.name == 'nt' else 'python3'
    temp_script_path = fr'C:\Users\{getpass.getuser()}\AppData\Local\Temp\script_temp' if os.name == 'nt' else r'/tmp/script_temp'

    # 下载脚本并运行
    if not os.path.exists(temp_script_path):
        os.mkdir(temp_script_path)
    with TemporaryDirectory(dir=temp_script_path) as git_script_path_temp:
        # 添加script_temp_path，用于后续直接从temp中调用脚本
        args_dict = eval(args)
        args_dict.update({"script_temp_path": fr"{git_script_path_temp}"})  # 添加script_temp_path
        args = str(args_dict)
        # 下载tar包到缓存后解压
        git_script_path = download_unzip_script(git_script_path_temp, 'common_app.py', args_dict)
        # 使用参数运行
        print(f'[execute app] 执行common_app指令为{python_path} {git_script_path} --m {args}')
        cmd = [python_path, git_script_path, '--m', args]
        process = subprocess.Popen(cmd)
        process.communicate()
