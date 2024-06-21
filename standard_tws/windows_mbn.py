from utils.cases.windows_mbn_manager import MbnManager
import time


class MbnCheck(MbnManager):

    def test_mbn(self):
        # ����ģ���ϲ�ѯ���ͺ�����ЩMBN
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

        # �е�ģ�飬��ѯmbnlist����mbn�Ƿ񼤻��δ�����ǣ�ѭ��
        # �򿪶���������ҳ��,��һ�ξ���
        self.page_mobile_broadband.open_sim_wirte_page()

        # ��ȡMBN�ļ�
        # self.mbn_file('all_mbn_infomarion', 'mbn.csv')
        mbn_list = ["Commercial-EE", "Commercial-SKT"]
        mbn_list_new = []
        for mbn_name in mbn_list:
            mnc_mcc_value = self.mnc_mcc_data(mbn_name)
            new_imsi = mnc_mcc_value[0] + mnc_mcc_value[1]
            iccid_value = self.iccid_data(mbn_name)
            new_iccid = iccid_value[0] + iccid_value[1]
            # �õ�IMSI,ICCID���ݺ�ʼд��
            # ���read card��ť
            self.page_mobile_broadband.click_read_card_button()
            # ���OK��ť
            self.page_mobile_broadband.click_ok_button()
            # TODO:����Forѭ����Ŀǰֻ��ҪдICCID��IMSI 15
            # д��ICCID
            self.page_mobile_broadband.input_iccid(new_iccid)
            # д��IMSI15
            self.page_mobile_broadband.input_imsi(new_imsi)
            # ���Same with GSM��ťͬ������Ϣ
            self.page_mobile_broadband.click_same_with_gsm_button()
            time.sleep(2)
            # ���Write Card��ť
            self.page_mobile_broadband.click_write_card_button()
            time.sleep(5)
            # ���OK��ť
            self.page_mobile_broadband.click_ok_button()
            # �е�ģ�����
            # mbn_info = self.send_at('at+qmbncfg="list"')
            # mbn_value = ''.join(re.findall(r'\+qmbncfg: "List",0,\d+,(\d+),"{}"'.format(mbn_name), mbn_info[0]))
            # if mbn_value == '1':
            #     print('{}ƥ��ɹ� {}'.format(mbn_name, mbn_value))
            # else:
            #     print('{}ƥ���쳣 {}'.format(mbn_name, mbn_value))
            mbn_list_new.append(mbn_name)
            if len(mbn_list) == len(mbn_list_new):
                print('�ѱ���������MBN')


if __name__ == '__main__':
    w = MbnCheck()
    w.test_mbn()
