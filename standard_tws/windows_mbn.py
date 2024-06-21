from utils.cases.windows_mbn_manager import MbnManager
import time


class MbnCheck(MbnManager):

    def test_mbn(self):
        # 先在模块上查询该型号有哪些MBN
        # mbn_src = self.send_at('at+qmbncfg="list"')
        # print('mbn_src: ', mbn_src[0])
        # mbn_list = []
        # for data in mbn_src[1]:
        #     if 'qmbncfg: "List"' in data:
        #         mbn = ''.join(re.findall(r'\+qmbncfg: "List",\d+,\d+,\d+,(.*),.*,.*', data))
        #         if 'ROW_Commercial' == mbn.replace('"', ''):
        #             continue
        #         elif 'ROW_Generic_3GPP_PTCRB_GCF' == mbn.replace('"', ''):
        #             continue
        #         elif 'Spark_Commercial' == mbn.replace('"', ''):
        #             continue
        #         mbn_list.append(mbn.replace('"', ''))

        # 切到模块，查询mbnlist，看mbn是否激活，若未激活标记，循环
        # 打开读卡器工具页面,打开一次就行
        self.page_mobile_broadband.open_sim_wirte_page()

        # 获取MBN文件
        # self.mbn_file('all_mbn_infomarion', 'mbn.csv')
        mbn_list = ["Commercial-EE", "Commercial-SKT"]
        mbn_list_new = []
        for mbn_name in mbn_list:
            mnc_mcc_value = self.mnc_mcc_data(mbn_name)
            new_imsi = mnc_mcc_value[0] + mnc_mcc_value[1]
            iccid_value = self.iccid_data(mbn_name)
            new_iccid = iccid_value[0] + iccid_value[1]
            # 拿到IMSI,ICCID数据后开始写卡
            # 点击read card按钮
            self.page_mobile_broadband.click_read_card_button()
            # 点击OK按钮
            self.page_mobile_broadband.click_ok_button()
            # TODO:整个For循环，目前只需要写ICCID和IMSI 15
            # 写入ICCID
            self.page_mobile_broadband.input_iccid(new_iccid)
            # 写入IMSI15
            self.page_mobile_broadband.input_imsi(new_imsi)
            # 点击Same with GSM按钮同步下信息
            self.page_mobile_broadband.click_same_with_gsm_button()
            time.sleep(2)
            # 点击Write Card按钮
            self.page_mobile_broadband.click_write_card_button()
            time.sleep(5)
            # 点击OK按钮
            self.page_mobile_broadband.click_ok_button()
            # 切到模块这边
            # mbn_info = self.send_at('at+qmbncfg="list"')
            # mbn_value = ''.join(re.findall(r'\+qmbncfg: "List",0,\d+,(\d+),"{}"'.format(mbn_name), mbn_info[0]))
            # if mbn_value == '1':
            #     print('{}匹配成功 {}'.format(mbn_name, mbn_value))
            # else:
            #     print('{}匹配异常 {}'.format(mbn_name, mbn_value))
            mbn_list_new.append(mbn_name)
            if len(mbn_list) == len(mbn_list_new):
                print('已遍历完所有MBN')


if __name__ == '__main__':
    w = MbnCheck()
    w.test_mbn()
