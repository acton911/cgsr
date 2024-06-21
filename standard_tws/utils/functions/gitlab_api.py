import os
import gitlab
from utils.logger.logging_handles import all_logger


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
    GitlabAPI().download_project_branch()
