import os
import re
import time
import subprocess
from utils.operate.at_handle import ATHandle
from utils.logger.logging_handles import all_logger
from utils.exception.exceptions import LinuxESIMError
from utils.functions.driver_check import DriverChecker


class LinuxESIMManager:
    def __init__(self, at_port, dm_port, wwan_path, profile_info):
        self.at_port = at_port
        self.dm_port = dm_port
        self.wwan_path = wwan_path
        self.profile_info = profile_info.split(',')  # 三个激活码，期望A和B为同运营商，C为不用运营商
        self.activation_code_A = self.profile_info[0].strip().replace('$', r'\$')
        self.activation_code_B = self.profile_info[2].strip().replace('$', r'\$')
        self.iccid_A = self.profile_info[1].strip()
        self.iccid_B = self.profile_info[3].strip()
        self.at_handle = ATHandle(at_port)
        self.driver_check = DriverChecker(at_port, dm_port)
        self.at_handle.send_at('AT+QUIMSLOT=2')
        self.set_qmi()
        self.open_lpa()

    def set_qmi(self):
        """
        设置qmi拨号方式
        """
        all_logger.info(os.popen('lsusb -t').read())
        if 'qmi_wwan' in os.popen('lsusb -t').read():
            all_logger.info('当前已是WWAN拨号，无需切换拨号方式')
            return
        self.modprobe_driver()
        self.load_wwan_driver()
        self.at_handle.send_at('AT+QCFG="USBNET",0', 3)
        self.cfun_reset()
        all_logger.info(os.popen('lsusb -t').read())
        if 'qmi_wwan' in os.popen('lsusb -t').read():
            all_logger.info('切换WWAN拨号成功')
        else:
            all_logger.info('切换WWAN拨号失败')
            raise LinuxESIMError('切换WWAN拨号失败')

    def load_wwan_driver(self):
        """
        编译WWAN驱动
        :return: None
        """
        # chmod 777
        all_logger.info(' '.join(['chmod', '777', self.wwan_path]))
        s = subprocess.run(' '.join(['chmod', '777', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make clean
        all_logger.info(' '.join(['make', 'clean', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'clean', '--directory', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

        # make install
        all_logger.info(' '.join(['make', 'install', '--directory', self.wwan_path]))
        s = subprocess.run(' '.join(['make', 'install', '--directory', self.wwan_path]), shell=True, capture_output=True, text=True)
        all_logger.info(s.stdout)

    @staticmethod
    def modprobe_driver():
        """
        卸载GobiNet驱动
        :return: True
        """
        for i in range(3):
            all_logger.info('modprobe -r GobiNet卸载Gobinet驱动')
            all_logger.info(os.popen('modprobe -r GobiNet').read())
            all_logger.info('modprobe -r qmi_wwan卸载qmi_wwan驱动')
            all_logger.info(os.popen('modprobe -r qmi_wwan').read())
            check_modprobe = os.popen('lsusb -t').read()
            all_logger.info('卸载驱动后查看驱动情况:\n')
            all_logger.info(check_modprobe)
            if 'GobiNet' not in check_modprobe:
                all_logger.info('驱动卸载成功')
                return True
        raise LinuxESIMError('卸载Gobinet驱动失败')

    def cfun_reset(self):
        """
        CFUN11重启
        """
        self.at_handle.cfun1_1()
        self.driver_check.check_usb_driver_dis()
        self.driver_check.check_usb_driver()
        self.at_handle.check_urc()
        time.sleep(5)

    def open_lpa(self):
        """
        开启LPA功能
        """
        for i in range(3):
            self.at_handle.send_at('AT+QESIM="lpa_enable",1', 10)
            if '1' not in self.at_handle.send_at('AT+QESIM="lpa_enable"', 10):
                continue
            else:
                all_logger.info('已开启LPA功能')
                return

    def close_lpa(self):
        """
        关闭LPA功能
        """
        for i in range(3):
            self.at_handle.send_at('AT+QESIM="lpa_enable",0', 10)
            if '0' not in self.at_handle.send_at('AT+QESIM="lpa_enable"', 10):
                continue
            else:
                all_logger.info('已关闭LPA功能')
                return

    def delete_profile(self):
        """
        删除现有的profile文件
        """
        profile_value = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
        re_value = re.findall(r'\+QESIM: "profile_brief",(\d+)', profile_value)
        cur_profile_num = int(''.join(re_value))
        if cur_profile_num != 0:
            for i in range(cur_profile_num):    # 首先确定是否激活，如果已激活先去激活再激活
                check_value = self.at_handle.send_at('AT+QESIM="profile_detail",1', 10)
                re_value = int(''.join(re.findall(r'\+QESIM: "profile_detail",.*,(\d),', check_value)))
                if re_value == 1:
                    self.at_handle.send_at('AT+QESIM="disable_profile",1', 10)
                    time.sleep(3)
                for j in range(30):
                    return_val = self.at_handle.send_at('AT+QESIM="delete_profile",1', 10)
                    if 'ERROR' not in return_val:
                        break
                    else:
                        self.at_handle.send_at('AT+QESIM="disable_profile",1', 10)
                    time.sleep(2)
        else:
            all_logger.info('当前不存在profile文件，无需删除')
            return
        time.sleep(3)
        after_profile_num = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
        re_value = re.findall(r'\+QESIM: "profile_brief",(\d+)', after_profile_num)
        cur_profile_num = int(''.join(re_value))
        if cur_profile_num != 0:
            all_logger.info('profile文件删除失败')
            raise LinuxESIMError('profile文件删除失败')
        else:
            all_logger.info('所有profile文件删除成功')

    def add_profile(self, profile):
        """
        添加profile文件，并校验是否正确
        :param profile:需要添加的profile文件
        """
        profile_dict = {self.activation_code_A: self.iccid_A, self.activation_code_B: self.iccid_B}
        for i in range(3):  # 可能一次添加不成功
            add_info = os.popen(f'quectel_lpad -A {profile}').read()
            if '100%' in add_info:
                all_logger.info('Profile文件添加成功')
                break
            else:
                all_logger.info(f'第{i+1}次添加Profile失败，共尝试添加3次')
        else:
            all_logger.info('Profile文件添加失败')
            raise LinuxESIMError('Profile文件添加失败')
        profile_id_info = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
        profile_id = ''.join(re.findall(r'\+QESIM: "profile_brief",(\d+)', profile_id_info))
        check_profile_info = self.at_handle.send_at(f'AT+QESIM="profile_detail",{profile_id}', 10)
        re_qccid = ''.join(re.findall(r'\+QESIM: "profile_detail",(\d+)', check_profile_info))
        if re_qccid == profile_dict[profile]:
            all_logger.info('Profile添加后比对ICCID正常')
        else:
            all_logger.info(f'Profile文件添加后对比ICCID异常,AT查询值为{re_qccid}，系统下发为{profile_dict[profile]}')
            raise LinuxESIMError('Profile文件添加后对比ICCID异常')

    def check_order(self):
        """
        检查AT指令
        """
        first_order = self.at_handle.send_at('AT+QESIM=?', 10)
        second_order = self.at_handle.send_at('AT+QESIM?', 10)
        third_order = self.at_handle.send_at('AT+QESIM', 10)
        if first_order.count('QESIM') != 10:
            all_logger.info('AT+QESIM=?返回值有误，请检查')
            raise LinuxESIMError('AT+QESIM=?返回值有误，请检查')
        if 'ERROR' not in second_order or 'ERROR' not in third_order:
            all_logger.info('未开启LPA功能的情况下，发送ESIM相关指令未返回ERROR')
            raise LinuxESIMError('未开启LPA功能的情况下，发送ESIM相关指令未返回ERROR')

    def close_lpa_order_check(self):
        """
        关闭LPA功能后指令检查
        """
        order_list = ["profile_brief", '"profile_detail",1', '"enable_profile",1', '"disable_profile",1',
                      "eid", '"nickname",1,"Quectel"', '"def_svr_addr","esim.wo.com.cn"', '"delete_profile",1']
        for order in order_list:
            return_value = self.at_handle.send_at(f'AT+QESIM={order}', 10)
            if 'ERROR' not in return_value:
                all_logger.info(f'未开启LPA功能，指令{order}执行未返回ERROR, 期望返回ERROR')
                raise LinuxESIMError(f'未开启LPA功能，指令{order}执行未返回ERROR, 期望返回ERROR')

    def check_lpa(self, is_open):
        """
        检查LPA功能是否开启
        :param is_open:预期是否开启，True：开启，False：关闭
        """
        return_value = self.at_handle.send_at('AT+QESIM="lpa_enable"', 10)
        if is_open:     # 预期返回1
            if '1' not in return_value:
                all_logger.info('期望LPA功能已开启，实际未开启')
                raise LinuxESIMError('期望LPA功能已开启，实际未开启')
        else:
            if '0' not in return_value:
                all_logger.info('期望LPA功能关闭，实际未关闭')
                raise LinuxESIMError('期望LPA功能关闭，实际未关闭')

    def check_illegal_order(self):
        """
        检查非法指令
        """
        first_order = self.at_handle.send_at('AT+QESIM="lpa_enable",-1', 10)
        second_order = self.at_handle.send_at('AT+QESIM="lpa_enable",2', 10)
        if 'ERROR' not in first_order or 'ERROR' not in second_order:
            all_logger.info('输入非法指令期望返回ERROR，实际未返回ERROR')
            raise LinuxESIMError('输入非法指令期望返回ERROR，实际未返回ERROR')

    def check_profile_num(self):
        """
        检查profile文件数量
        """
        return_value = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
        profile_num = ''.join(re.findall(r'\+QESIM: "profile_brief",(\d+)', return_value))
        if int(profile_num) != 1:
            all_logger.info(f'当前使用AT指令查询profile数量不为1,为{profile_num}')
            raise LinuxESIMError(f'当前使用AT指令查询profile数量不为1,为{profile_num}')

    def check_profile_detail(self, is_correct=True):
        """
        查询错误的profile文件详情
        :param is_correct:预期是否正确，True：正确，False：错误
        """
        if is_correct:
            return_value = self.at_handle.send_at('AT+QESIM="profile_detail",1', 10)
            if self.iccid_A not in return_value:
                all_logger.info('查询profile文件详情，ICCID号与预期不符')
                raise LinuxESIMError('查询profile文件详情，ICCID号与预期不符')
        else:
            return_value = self.at_handle.send_at('AT+QESIM="profile_detail",7', 10)
            if 'ERROR' not in return_value:
                all_logger.info('查询错误的profile文件详情未返回ERROR')
                raise LinuxESIMError('查询错误的profile文件详情未返回ERROR')

    def activate_profile(self, profile):
        """
        激活Profile文件
        :param profile: 需要激活的profile文件
        """
        self.at_handle.send_at(f'AT+QESIM="enable_profile",{profile}', 10)
        time.sleep(3)
        for i in range(30):
            re_value = ''
            check_value = self.at_handle.send_at(f'AT+QESIM="profile_detail",{profile}', 10)
            try:
                re_value = int(''.join(re.findall(r'\+QESIM: "profile_detail",.*,(\d),', check_value)))
            except Exception:   # noqa
                pass
            if re_value == 1:
                all_logger.info('激活Profile文件成功')
                return
            time.sleep(2)
        else:
            all_logger.info('激活profile文件失败')
            raise LinuxESIMError('激活profile文件失败')

    def disable_profile(self, profile):
        """
        去激活Profile文件
        :param profile: 需要去激活的profile文件
        """
        for i in range(30):
            re_value = ''
            self.at_handle.send_at(f'AT+QESIM="disable_profile",{profile}', 10)
            check_value = self.at_handle.send_at(f'AT+QESIM="profile_detail",{profile}', 10)
            try:
                re_value = int(''.join(re.findall(r'\+QESIM: "profile_detail",.*,(\d),', check_value)))
            except Exception:    # noqa
                pass
            if re_value == 0:
                all_logger.info('去激活Profile文件成功')
                break
            time.sleep(2)
        else:
            all_logger.info('去激活profile文件失败')
            raise LinuxESIMError('去激活profile文件失败')

    def check_profile_activate(self, profile, is_activate):
        """
        检查Profile文件是否已激活
        :param profile:查询的profile文件号
        :param is_activate:期望是否已激活：True：期望已激活; False：期望未激活
        """
        check_value = self.at_handle.send_at(f'AT+QESIM="profile_detail",{profile}', 10)
        re_value = int(''.join(re.findall(r'\+QESIM: "profile_detail",.*,(\d),', check_value)))
        if is_activate:
            if re_value != 1:
                all_logger.info('profile文件未处于激活状态')
                raise LinuxESIMError('profile文件未处于激活状态')
            else:
                all_logger.info('profile文件处于激活状态，正常')
        else:
            if re_value != 0:
                all_logger.info('profile文件未处于去激活状态')
                raise LinuxESIMError('profile文件未处于去激活状态')
            else:
                all_logger.info('profile文件处于去激活状态，正常')

    def repeat_activate(self, profile, is_activate):
        """
        重复激活或去激活profile
        :param profile:激活的profile文件号
        :param is_activate: True:重复激活 False：重复去激活
        """
        if is_activate:
            return_value = self.at_handle.send_at(f'AT+QESIM="enable_profile",{profile}', 10)
            if 'ERROR' not in return_value:
                all_logger.info('再次激活已激活状态的profile文件，未返回ERROR')
                raise LinuxESIMError('再次激活已激活状态的profile文件，未返回ERROR')
        else:
            return_value = self.at_handle.send_at(f'AT+QESIM="disable_profile",{profile}', 10)
            if 'ERROR' not in return_value:
                all_logger.info('再次激活已激活状态的profile文件，未返回ERROR')
                raise LinuxESIMError('再次激活已激活状态的profile文件，未返回ERROR')

    def nickname_profile(self, profile='1', nickname='', is_correct=True):
        """
        给profile文件取名
        :param profile:修改昵称的profile文件号
        :param nickname:需要修改的昵称
        :param is_correct:昵称是否正常
        """
        if is_correct:  # 正常修改昵称的情况
            for i in range(30):
                self.at_handle.send_at(f'AT+QESIM="nickname",{profile},"{nickname}"', 10)
                check_value = self.at_handle.send_at(f'AT+QESIM="profile_detail",{profile}', 10)
                re_nickname = ''.join(re.findall(r'\+QESIM: "profile_detail",.*,\d+,"(\w+)"', check_value))
                if nickname == re_nickname:
                    all_logger.info('修改Profile文件名称成功')
                    break
                time.sleep(2)
            else:
                all_logger.info('修改profile名称失败')
                raise LinuxESIMError('修改profile名称失败')
        else:
            for i in range(30):
                return_value = self.at_handle.send_at(f'AT+QESIM="nickname",{profile},"{nickname}"', 10)
                if 'ERROR' in return_value:
                    all_logger.info('修改不规范昵称返回ERROR')
                    break
                time.sleep(2)
            else:
                all_logger.info('修改不规范昵称未返回ERROR')
                raise LinuxESIMError('修改不规范昵称未返回ERROR')

    def check_server_address(self):
        """
        检查SM-DP服务器地址
        """
        return_val = self.at_handle.send_at('AT+QESIM="def_svr_addr"', 10)
        if 'esim.wo.com.cn' not in return_val:
            all_logger.info('检查默认服务器地址不为esim.wo.com.cn')
            raise LinuxESIMError('检查默认服务器地址不为esim.wo.com.cn')

    def set_server_address(self, address, is_correct=True):
        """
        设置服务器地址
        :param address： 需要设置的地址
        :param is_correct： 需要设置的地址是否正确
        """
        if is_correct:
            for i in range(30):
                self.at_handle.send_at(f'AT+QESIM="def_svr_addr","{address}"', 10)
                check_val = self.at_handle.send_at('AT+QESIM="def_svr_addr"', 10)
                re_address = ''.join(re.findall(r'\+QESIM: "def_svr_addr","(\S+)"', check_val))
                if address == re_address:
                    all_logger.info('设置新的服务器地址成功')
                    break
                time.sleep(2)
            else:
                all_logger.info('设置新的服务器地址失败')
                raise LinuxESIMError('设置新的服务器地址失败')
        else:
            for i in range(30):
                check_val = self.at_handle.send_at(f'AT+QESIM="def_svr_addr","{address}"', 10)
                if 'ERROR' in check_val:
                    all_logger.info('设置错误的服务器地址返回ERROR')
                    break
                time.sleep(2)
            else:
                all_logger.info('设置错误的服务器地址未返回ERROR')
                raise LinuxESIMError('设置错误的服务器地址未返回ERROR')

    def delete_single_profile(self):
        """
        删除单个profile文件查看结果
        """
        return_val = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
        ori_profile_num = int(''.join(re.findall(r'\+QESIM: "profile_brief",(\d+)', return_val)))
        for i in range(30):
            self.at_handle.send_at(f'AT+QESIM="delete_profile",{ori_profile_num}', 10)
            return_val = self.at_handle.send_at('AT+QESIM="profile_brief"', 10)
            cur_profile_num = ''
            try:
                cur_profile_num = int(''.join(re.findall(r'\+QESIM: "profile_brief",(\d+)', return_val)))
            except Exception:   # noqa
                pass
            if ori_profile_num - 1 == cur_profile_num:
                all_logger.info('删除一个profile文件后数量正确')
                if 'ERROR' not in self.at_handle.send_at(f'AT+QESIM="profile_detail",{ori_profile_num}'):
                    all_logger.info('已删除的profile文件仍能查询信息')
                    raise LinuxESIMError('已删除的profile文件仍能查询信息')
                break
            time.sleep(2)
        else:
            all_logger.info('删除一个profile文件后数量不正确')
            raise LinuxESIMError('删除一个profile文件后数量不正确')

    def set_cfun(self, mode):
        """
        设置CFUN值
        :param mode: 需要设置的CFUN值
        """
        for i in range(3):
            if mode == 0:
                self.at_handle.send_at('AT+CFUN=0', 15)
            elif mode == 1:
                self.at_handle.send_at('AT+CFUN=1', 15)
            elif mode == 4:
                self.at_handle.send_at('AT+CFUN=4', 15)
            info = self.at_handle.send_at('AT+CFUN?', 10)
            if str(mode) in ''.join(re.findall(r'\+CFUN: (\d+)', info)):
                return True
        else:
            raise LinuxESIMError('切换CFUN={}失败'.format(mode))

    def check_module_info(self, is_correct=True):
        """
        检测ICCID,EID,IMSI号等
        :param is_correct: 是否可以正常查询到ESIM卡相关信息
        """
        iccid = self.at_handle.send_at('AT+QCCID', 10)
        imsi = self.at_handle.send_at('AT+CIMI', 10)
        eid = self.at_handle.send_at('AT+QESIM="eid"', 10)
        if is_correct:
            re_iccid = ''.join(re.findall(r'\+QCCID: (\d+\S+)', iccid))
            if self.iccid_A != re_iccid:
                all_logger.info(f'ICCID查询不一致，AT指令查询为{re_iccid}，系统下发为{self.iccid_A}')
            if 'ERROR' in imsi:
                all_logger.info('查询IMSI号返回ERROR')
                raise LinuxESIMError('查询IMSI号返回ERROR')
            if 'ERROR' in eid:
                all_logger.info('查询EID号返回ERROR')
                raise LinuxESIMError('查询EID号返回ERROR')
        else:
            if 'ERROR' not in iccid and 'ERROR' not in imsi and 'ERROR' not in eid:
                all_logger.info('CFUN为0的情况下，查询ESIM卡相关信息未返回ERROR')
                raise LinuxESIMError('CFUN为0的情况下，查询ESIM卡相关信息未返回ERROR')

    def check_no_net(self):
        """
        验证当前是否无法注网
        """
        for i in range(10):
            cops_value = self.at_handle.send_at('AT+COPS?', 10)
            re_val = int(''.join(re.findall(r'\+COPS: (\d+)', cops_value)))
            if re_val != 0:
                all_logger.info('模块当前COPS查询返回值不为0')
                raise LinuxESIMError('模块当前COPS查询返回值不为0')
            time.sleep(0.5)

    def change_cfun(self):
        """
        重复切换CFUN值0，1，4
        """
        for i in range(5):
            self.set_cfun(0)
            time.sleep(1)
            self.set_cfun(4)
            time.sleep(1)
            self.set_cfun(1)
            time.sleep(1)
        time.sleep(5)
