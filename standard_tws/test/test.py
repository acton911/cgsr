import os
import gitlab
import logging

logging.basicConfig(level=logging.INFO)
all_logger = logging.getLogger(__name__)


class GitlabAPI:
    def __init__(self, gitlab_root_url="https://stgit.quectel.com/", gitlab_token='cL3SbdF3x2XzmfxxyVkk', path=os.getcwd()):
        self.url = gitlab_root_url  #
        self.token = gitlab_token
        self.path = path
        self.gl = None

    def connect(self):
        self.gl = gitlab.Gitlab(self.url, self.token)

    def download_project_branch(self, project=679, branch='develop'):
        self.connect()
        project = self.gl.projects.get(project)
        path = os.path.join(self.path, '{}.tar'.format(branch))
        files = project.repository_archive(branch)
        with open(path, 'wb') as f:
            f.write(files)
        all_logger.info(f'download branch {branch} into {path} success')


if __name__ == '__main__':
    g = GitlabAPI()
    g.connect()
    # 获取standard_tws项目
    project = g.gl.projects.get(679)
    # 获取所有的Tag
    all_logger.info(f"project.tags: {project.tags}")
    all_tags = project.tags.list(all=True)
    all_logger.info(f"all_tags: {all_tags}")
    all_logger.info(f"len(all_tags): {len(all_tags)}")
    # 获取所有的Tag名称
    all_tags_name = list(tag.name for tag in all_tags)
    all_logger.info(f"all_tags_name: {all_tags_name}")
    # 根据Case名称，筛选所有包含Case名称的Tag
    name_group = "MBIM(Windows)_SDX55"
    case_tags = [name for name in all_tags_name if name.startswith(name_group)]
    all_logger.info(f"case: {name_group}")
    all_logger.info(f"case_tags: {case_tags}")
    # 对当前Case名称的Tag进行排序，并获取最新的tag
    latest_case_tag = sorted(case_tags).pop()
    all_logger.info(f"latest_case_tags: {latest_case_tag}")

    # 下载tag文件
    files = project.repository_archive(latest_case_tag)
    with open(os.path.join(os.getcwd(), 'test.tar'), 'wb') as f:
        f.write(files)
    all_logger.info(f'download branch success')
