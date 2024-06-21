from tools.qss.logger import logger
import os
import csv
"""
功能：批量生成mme文件
主要逻辑：
1、从mme模板中读取文件内容
2、找到plmn位置
3、修改plmn生成新的mme文件
"""
# ***************关键参数，需要修改确认***********************************************************************************************************
# 模板mme文件位置，用来复制和参考
base_mme_file_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\00101-mme-ims.cfg'
# 新mme文件plmn
mme_plmn_now = '00101'
# 当前已有的mme文件集合路径
search_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config'
# 新mme文件plmn合集列表，有则填写，没有则不用关注,需要有一列列名为plmn的数据
mme_plmns_path_now = r'E:\project\qss_config_files\standard_tws\tools\qss\files\Record.csv'
# 新生成mme文件存位置，用来存放新mme文件，没有或者路径不对，则会生成到脚本运行的路径
save_new_mme_file_path = r'E:\project\qss_config_files\standard_tws\tools\qss\files\10.66.129.204\2022-06-18\ltemme-linux-2022-06-18\config\mme_new_20230217'

# *****************默认参数，一般无需修改**********************************************************************************************************
# 其他参数，一般无需修改
mme_plmn_place_start = 'plmn: "'
mme_plmn_place_end = '",\n  mme_group_id'
colmn_name_plmn = 'plmn'


def read_csv_culmn(mme_plmns_path, colmn_name):
    if os.path.exists(mme_plmns_path):
        with open(mme_plmns_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            column = [row[colmn_name] for row in reader]
            logger.info(column)
            return column
    else:
        logger.error(f"未找到 {mme_plmns_path}")


def write_mme_files(base_mme_file_path, mme_plmn):
    old_mme_files_name = os.path.basename(base_mme_file_path)
    old_plmn = old_mme_files_name.split('-')[0]
    new_mme_files_name = old_mme_files_name.replace(old_plmn, mme_plmn)
    logger.info(new_mme_files_name)
    find_flag = False
    for _, _, files in os.walk(search_file_path):
        for file in files:
            if file == new_mme_files_name:
                find_flag = True
                break
    if find_flag:
        logger.info(f'此配置文件已存在，无需再生成:{old_mme_files_name}')
    else:
        logger.info(base_mme_file_path)
        if os.path.exists(base_mme_file_path):
            with open(base_mme_file_path, 'r', encoding='utf-8') as file_read:
                content = file_read.read()
            # logger.info(content)
            content_add = mme_plmn
            pos1 = content.find(mme_plmn_place_start)
            logger.info(pos1)
            pos2 = content.find(mme_plmn_place_end)
            logger.info(pos2)
            if pos1 != -1 and pos2 != -1:
                content_write = content[:pos1] + 'plmn: "' + content_add + content[pos2:]
            else:
                logger.error("创建mme文件异常")
                raise Exception
            if os.path.exists(save_new_mme_file_path):
                new_mme_file_path = os.path.join(save_new_mme_file_path, mme_plmn + '-mme-ims.cfg')
            else:
                new_mme_file_path = os.path.join(os.getcwd(), mme_plmn + '-mme-ims.cfg')
            with open(new_mme_file_path, 'w', encoding='utf-8') as file_write:
                file_write.write(content_write)
                logger.info(new_mme_file_path)
        else:
            logger.error(f"未找到 {base_mme_file_path}")


if os.path.exists(mme_plmns_path_now):
    mme_file_name_list = read_csv_culmn(mme_plmns_path_now, colmn_name_plmn)
    for i in mme_file_name_list:
        logger.info(i)
        write_mme_files(base_mme_file_path_now, i)
else:
    write_mme_files(base_mme_file_path_now, mme_plmn_now)
