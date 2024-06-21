import os
import gitlab
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


url = r'https://stgit.quectel.com/5G-SDX55/standard_tws'
token = 'cL3SbdF3x2XzmfxxyVkk'


gl = gitlab.Gitlab('https://stgit.quectel.com/', token)

# 获取项目
project = gl.projects.get(679)
logger.info(project)

# 下载项目某个分支文件
branch_name = 'develop'
path = os.path.join(os.getcwd(), '{}.tar'.format(branch_name))
files = project.repository_archive(branch_name)
with open(path, 'wb') as f:
    f.write(files)
logger.info(f'download branch {branch_name} into {path} success')

# 获取某个分支的详情
develop = project.branches.get('develop')
