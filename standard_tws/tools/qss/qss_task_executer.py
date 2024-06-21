import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
from logger import logger
import os
import tarfile
from tempfile import TemporaryDirectory
from gitlab_api import GitlabAPI
import time
from qss_client import WriteSimcard

executor = ThreadPoolExecutor(10)


class QSSTaskExecuter(Thread):
    def __init__(self, qss_now_task):
        super().__init__()
        self.qss_now_task = qss_now_task

    def run(self):
        logger.info(f'task  {self.qss_now_task}  start')
        time.sleep(5)
        logger.info(f'task  {self.qss_now_task}  end')

    def get_qss_file(self, script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name='', imsi_sim=''):
        mme_cmd = ''
        enb_cmd = ''
        ims_cmd = ''
        try:
            gitlab_root_url = "https://stgit.quectel.com/"
            gitlab_token = '5ydQV6h-13h2swCedsaz'
            # gitlab_token = 'FnEKerAsX4kyx6eGYnVv'
            project_id = 679
            path = script_path_temp
            project_branch = 'qss_config_files'
            gl = GitlabAPI(gitlab_root_url=gitlab_root_url, gitlab_token=gitlab_token, path=path)
            gl.download_project_branch(project=project_id, branch=project_branch)
            cache_tar = os.path.join(script_path_temp, project_branch + '.tar')
            script_path_temp_list = os.listdir(script_path_temp)
            with tarfile.open(cache_tar) as t:
                t.extractall(path=script_path_temp)
            extract_dir = set(os.listdir(script_path_temp)).difference(script_path_temp_list).pop()
            script_path = os.path.join(script_path_temp, extract_dir)
            logger.info(script_path)
            qss_files_path = os.path.join(script_path, 'tools', 'qss', 'files', qss_ip)
            logger.info(qss_files_path)
            mme_execute_path = ''
            enb_execute_path = ''
            qss_driver_path = ''
            if not os.path.isdir(qss_files_path):
                logger.info(f"此QSS的配置文件不存在： {qss_ip}")
                return False
            # logger.info('666666666666666666666')
            # time.sleep(1000)
            for path, dirs, files in os.walk(qss_files_path):
                for dir_n in dirs:
                    if 'ltemme-linux-' in dir_n:
                        logger.info(f'mme execute path: {os.path.join(path, dir_n)}')
                        mme_execute_path = os.path.join(path, dir_n)
                    if 'lteenb-linux-' in dir_n:
                        logger.info(f'enb execute path: {os.path.join(path, dir_n)}')
                        enb_execute_path = os.path.join(path, dir_n)
                    if 'trx_sdr-linux-' in dir_n:
                        logger.info(f'qss driver path: {os.path.join(path, dir_n)}')
                        qss_driver_path = os.path.join(path, dir_n)
                if mme_execute_path != '' and enb_execute_path != '':
                    for file in files:
                        if file == qss_mme_file_name:
                            logger.info(f'mme path: {os.path.join(path, file)}')
                            mme_file_path = os.path.join(path, file)
                            mme_cmd = f'{mme_execute_path}/ltemme {mme_file_path}'
                    for file in files:
                        if file == qss_enb_file_name:
                            logger.info(f'enb path: {os.path.join(path, file)}')
                            enb_file_path = os.path.join(path, file)
                            enb_cmd = f'{enb_execute_path}/lteenb {enb_file_path}'
                    if qss_ims_file_name != '':
                        for file in files:
                            if file == qss_ims_file_name:
                                logger.info(f'ims path: {os.path.join(path, file)}')
                                ims_file_path = os.path.join(path, file)
                                ims_cmd = f'{mme_execute_path}/lteims {ims_file_path}'
            logger.info(f'cmds :\r\nmme_cmd: {mme_cmd}\r\nenb_cmd: {enb_cmd}\r\nims_cmd: {ims_cmd}')
            # 杀死正在运行的配置文件
            subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {mme_execute_path} && killall -9 ltemme', shell=True)
            time.sleep(0.1)
            subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {mme_execute_path} && killall -9 lteims', shell=True)
            time.sleep(0.1)
            subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {enb_execute_path} && killall -9 lteenb*', shell=True)
            time.sleep(0.1)
            # 安装驱动
            s1 = subprocess.run(' '.join(['make', 'clean', '--directory', os.path.join(qss_driver_path, '\kernel')]), shell=True, capture_output=True, text=True)  # noqa
            logger.info(s1.stdout)
            time.sleep(0.1)
            s2 = subprocess.run(' '.join(['make', '--directory', os.path.join(qss_driver_path, '\kernel')]), shell=True, capture_output=True, text=True)  # noqa
            logger.info(s2.stdout)
            time.sleep(0.1)
            s3 = subprocess.run(f'{qss_driver_path}/install.sh {enb_execute_path} enb', shell=True)
            logger.info(s3.stdout)
            time.sleep(0.1)
            # 往ue_db写入sim卡信息
            if imsi_sim != '' and len(imsi_sim) >= 5:
                imsi_sim_now = imsi_sim
            else:
                imsi_sim_now = ''.join(re.findall(r'(\d\d\d\d\d+)', qss_mme_file_name))
            self.add_simcard_info_ue_db(imsi_sim_now, mme_execute_path)
        except Exception as e:
            logger.error(e)
            return False
        finally:
            if enb_cmd == '' or mme_cmd == '':
                logger.error(f"获取enb、mme文件失败！{enb_cmd}{mme_cmd}")
                return False
            elif ims_cmd == '' and enb_cmd != '' and mme_cmd != '':
                return enb_cmd, mme_cmd
            else:
                return ims_cmd, enb_cmd, mme_cmd

    def get_qss_file_keep_mme(self, script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name='', imsi_sim=''):
        mme_cmd = ''
        enb_cmd = ''
        ims_cmd = ''
        try:
            gitlab_root_url = "https://stgit.quectel.com/"
            gitlab_token = '5ydQV6h-13h2swCedsaz'
            # gitlab_token = 'FnEKerAsX4kyx6eGYnVv'
            project_id = 679
            path = script_path_temp
            project_branch = 'qss_config_files'
            gl = GitlabAPI(gitlab_root_url=gitlab_root_url, gitlab_token=gitlab_token, path=path)
            gl.download_project_branch(project=project_id, branch=project_branch)
            cache_tar = os.path.join(script_path_temp, project_branch + '.tar')
            script_path_temp_list = os.listdir(script_path_temp)
            with tarfile.open(cache_tar) as t:
                t.extractall(path=script_path_temp)
            extract_dir = set(os.listdir(script_path_temp)).difference(script_path_temp_list).pop()
            script_path = os.path.join(script_path_temp, extract_dir)
            logger.info(script_path)
            qss_files_path = os.path.join(script_path, 'tools', 'qss', 'files', qss_ip)
            logger.info(qss_files_path)
            mme_execute_path = ''
            enb_execute_path = ''
            qss_driver_path = ''
            if not os.path.isdir(qss_files_path):
                logger.info(f"此QSS的配置文件不存在： {qss_ip}")
                return False
            # logger.info('666666666666666666666')
            # time.sleep(1000)
            for path, dirs, files in os.walk(qss_files_path):
                for dir_n in dirs:
                    if 'ltemme-linux-' in dir_n:
                        logger.info(f'mme execute path: {os.path.join(path, dir_n)}')
                        mme_execute_path = os.path.join(path, dir_n)
                    if 'lteenb-linux-' in dir_n:
                        logger.info(f'enb execute path: {os.path.join(path, dir_n)}')
                        enb_execute_path = os.path.join(path, dir_n)
                    if 'trx_sdr-linux-' in dir_n:
                        logger.info(f'qss driver path: {os.path.join(path, dir_n)}')
                        qss_driver_path = os.path.join(path, dir_n)
                if mme_execute_path != '' and enb_execute_path != '':
                    for file in files:
                        if file == qss_mme_file_name:
                            logger.info(f'mme path: {os.path.join(path, file)}')
                            mme_file_path = os.path.join(path, file)
                            mme_cmd = f'{mme_execute_path}/ltemme {mme_file_path}'
                    for file in files:
                        if file == qss_enb_file_name:
                            logger.info(f'enb path: {os.path.join(path, file)}')
                            enb_file_path = os.path.join(path, file)
                            enb_cmd = f'{enb_execute_path}/lteenb {enb_file_path}'
                    if qss_ims_file_name != '':
                        for file in files:
                            if file == qss_ims_file_name:
                                logger.info(f'ims path: {os.path.join(path, file)}')
                                ims_file_path = os.path.join(path, file)
                                ims_cmd = f'{mme_execute_path}/lteims {ims_file_path}'
            logger.info(f'cmds :\r\nmme_cmd: {mme_cmd}\r\nenb_cmd: {enb_cmd}\r\nims_cmd: {ims_cmd}')
            # 杀死正在运行的配置文件
            # subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {mme_execute_path} && killall -9 ltemme', shell=True)
            # time.sleep(3)
            subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {mme_execute_path} && killall -9 lteims', shell=True)
            time.sleep(0.1)
            subprocess.Popen(f'chmod 777 * -R {script_path_temp} && cd {enb_execute_path} && killall -9 lteenb*', shell=True)
            time.sleep(0.1)
            # 安装驱动
            s1 = subprocess.run(' '.join(['make', 'clean', '--directory', os.path.join(qss_driver_path, '\kernel')]), shell=True, capture_output=True, text=True)  # noqa
            logger.info(s1.stdout)
            time.sleep(0.1)
            s2 = subprocess.run(' '.join(['make', '--directory', os.path.join(qss_driver_path, '\kernel')]), shell=True, capture_output=True, text=True)  # noqa
            logger.info(s2.stdout)
            time.sleep(0.1)
            s3 = subprocess.run(f'{qss_driver_path}/install.sh {enb_execute_path} enb', shell=True)
            logger.info(s3.stdout)
            time.sleep(0.1)
            # 往ue_db写入sim卡信息
            if imsi_sim != '' and len(imsi_sim) >= 5:
                imsi_sim_now = imsi_sim
            else:
                imsi_sim_now = ''.join(re.findall(r'(\d\d\d\d\d+)', qss_mme_file_name))
            self.add_simcard_info_ue_db(imsi_sim_now, mme_execute_path)
        except Exception as e:
            logger.error(e)
            return False
        finally:
            if enb_cmd == '':
                logger.error(f"获取enb文件失败！{enb_cmd}{mme_cmd}")
                return False
            elif ims_cmd == '' and enb_cmd != '':
                return enb_cmd
            else:
                return ims_cmd, enb_cmd

    def run_qss_keep_mme(self, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name='', imsi_sim=''):
        """
        开网时不关闭mme、直接开新的enb
        """
        with TemporaryDirectory() as script_path_temp:
            # 下载tar包到缓存后解压
            try:
                if qss_ims_file_name != '':
                    qss_ims_cmd, qss_enb_cmd = self.get_qss_file_keep_mme(script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name, imsi_sim=imsi_sim)
                else:
                    qss_enb_cmd = self.get_qss_file_keep_mme(script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name)
                # 运行脚本
                subprocess.Popen(f'chmod 777 * -R {script_path_temp}', shell=True)
                time.sleep(0.1)
                executor.submit(self.run_qss_single, qss_enb_cmd)
                time.sleep(0.1)
                if qss_ims_file_name != '':
                    executor.submit(self.run_qss_single, qss_ims_cmd)
            except Exception as e:
                logger.error(e)
                return False

    def run_qss(self, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name='', imsi_sim=''):
        """
        创建缓存文件夹->获取源qss开网配置文件->解压qss开网配置文件->使用本地环境开网qss
        """
        with TemporaryDirectory() as script_path_temp:
            # 下载tar包到缓存后解压
            try:
                if qss_ims_file_name != '':
                    qss_ims_cmd, qss_enb_cmd, qss_mme_cmd = self.get_qss_file(script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name, qss_ims_file_name, imsi_sim=imsi_sim)
                else:
                    qss_enb_cmd, qss_mme_cmd = self.get_qss_file(script_path_temp, qss_ip, qss_mme_file_name, qss_enb_file_name)
                # 运行脚本
                subprocess.Popen(f'chmod 777 * -R {script_path_temp}', shell=True)
                time.sleep(0.1)
                executor.submit(self.run_qss_single, qss_mme_cmd)
                time.sleep(0.1)
                executor.submit(self.run_qss_single, qss_enb_cmd)
                time.sleep(0.1)
                if qss_ims_file_name != '':
                    executor.submit(self.run_qss_single, qss_ims_cmd)
            except Exception as e:
                logger.error(e)
                return False

    @staticmethod
    def run_qss_single(qss_cmd):
        logger.info(f"now to run : {qss_cmd}")
        subprocess.Popen(qss_cmd, shell=True)

    @staticmethod
    def add_simcard_info_ue_db(imsi_sim, ue_db_file_path, ue_db_file_name='0826-ue_db-ims.cfg'):
        mcc = imsi_sim[:3]
        if len(imsi_sim) >= 6:
            mnc = imsi_sim[3:6]
        elif len(imsi_sim) == 5:
            mnc = '0' + imsi_sim[3:5]
        else:
            logger.error(f'imsi信息异常！{imsi_sim}')
            return False
        ismi_ue_db = imsi_sim if len(imsi_sim) == 15 else WriteSimcard("_").get_white_simcard_imsi(imsi_sim)

        simcard_info_ue_db = "},{" + f"""
            sim_algo: "milenage",
            imsi: "{ismi_ue_db}",
            opc: "000102030405060708090A0B0C0D0E0F",
            amf: 0x9001,
            sqn: "000000000000",
            K: "00112233445566778899AABBCCDDEEFF",
            impu: ["sip:{ismi_ue_db}", "tel:{ismi_ue_db[:6]}{ismi_ue_db[-3:]}"],
            impi: "{ismi_ue_db}@ims.mnc{mnc}.mcc{mcc}.3gppnetwork.org",
            multi_sim: false,
        """
        logger.info(os.path.join(ue_db_file_path, 'config'))
        for p, d, f in os.walk(os.path.join(ue_db_file_path, 'config')):
            for file in f:
                if file == ue_db_file_name:
                    logger.info(file)
                    ue_db_file_name = os.path.join(p, file)
                    logger.info(ue_db_file_name)
                    with open(ue_db_file_name, 'r', encoding='utf-8') as file_read:
                        content = file_read.read()
                    if ismi_ue_db in content:
                        logger.info("ue_db已存在此imsi信息，可直接使用")
                        break
                    content_add = simcard_info_ue_db
                    pos = content.find("},")
                    if pos != -1:
                        content_write = content[:pos] + content_add + content[pos:]
                    else:
                        logger.error("往ue_db写入sim信息异常")
                        break
                    with open(ue_db_file_name, 'w', encoding='utf-8') as file_write:
                        file_write.write(content_write)
                        logger.info(ue_db_file_name)
                    break
            else:
                logger.error(f"未找到 {ue_db_file_name}")
                return False


# cd /home/{{ username.stdout}}/Desktop/{{ monitor_name }} && DISPLAY=:0 gnome-terminal -- bash -c 'source ~/.bashrc;./daemon;exec bash'
if __name__ == "__main__":
    qss_exe_path_mme_n = '/home/sdr/sdr/2021-06-17/ltemme-linux-2021-06-17'
    qss_exe_path_enb_n = '/home/sdr/sdr/2021-06-17/lteenb-linux-2021-06-17'
    qss_mme_flie_name = '00101-mme-ims.cfg'
    qss_enb_flie_name = '00101-gnb-nsa-b3n78-OK.cfg'
    imsi = '666666'
    qss_ip_n = '10.66.98.136'
    QSSTaskExecuter(1).run_qss(qss_ip_n, qss_mme_flie_name, qss_enb_flie_name, imsi_sim=imsi)
