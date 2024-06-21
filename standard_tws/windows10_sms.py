from utils.cases.windows10_sms_manager import WindowsSMSManager


class WindowsSMS(WindowsSMSManager):
    def test_windows_sms_01(self):
        """
        查询短信格式默认为PDU模式，接收后默认存储模式
        :return:
        """
        self.check_sms_format()

    def test_windows_sms_02(self):
        """
        确认SIM卡注网正常，短信中心号码正确
        :return:
        """
        self.check_sim_status()

    def test_windows_sms_03(self):
        """
        MBIM端收到 no class (00)的短消息能正常推送
        :return:
        """
        self.send_no_class_msg('19', f'0011FF0D9168{self.invert_phone_number()}0000A804F4F29C0E', 'test')
        self.check_msg_number('4')

    def test_windows_sms_04(self):
        """
        MBIM端收到 no class (00)的空短信能正常推送
        :return:
        """
        self.send_pdu_msg('15', f'0011FF0D9168{self.invert_phone_number()}0000A800', '')

    def test_windows_sms_05(self):
        """
        MBIM端收到 no class (00)的长短信能正常推送
        :return:
        """
        self.send_no_class_long_msg('155', f'0011000D9168{self.invert_phone_number()}000001A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')

    def test_windows_sms_06(self):
        """
        MBIM端收到 class 0 (F0)的短消息能正常推送，且Class0短信默认存储
        :return:
        """
        self.send_pdu_msg('19', f'0011FF0D9168{self.invert_phone_number()}00F0A804F4F29C0E', 'test')
        self.check_msg_number('1')

    def test_windows_sms_07(self):
        """
        MBIM端收到class 0 (F0)的长短信能正常推送
        :return:
        """
        self.send_pdu_msg('155', f'0011000D9168{self.invert_phone_number()}00F001A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')

    def test_windows_sms_08(self):
        """
        MBIM端收到 class 1(F1)的短消息能正常推送
        :return:
        """
        self.send_pdu_msg('19', f'0011FF0D9168{self.invert_phone_number()}00F1A804F4F29C0E', 'test')

    def test_windows_sms_09(self):
        """
        MBIM端收到class 1 (F1)的长短信能正常推送
        :return:
        """
        self.send_pdu_msg('155', f'0011000D9168{self.invert_phone_number()}00F101A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')

    def test_windows_sms_10(self):
        """
        MBIM端收到 class 2(F2)的短消息能正常推送
        :return:
        """
        self.send_pdu_msg('19', f'0011FF0D9168{self.invert_phone_number()}00F2A804F4F29C0E', 'test')

    def test_windows_sms_11(self):
        """
        MBIM端收到class 2 (F2)的长短信能正常推送
        :return:
        """
        self.send_pdu_msg('155', f'0011000D9168{self.invert_phone_number()}00F201A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')

    def test_windows_sms_12(self):
        """
        MBIM端收到 class 3(F3)的短消息能正常推送
        :return:
        """
        self.send_pdu_msg('19', f'0011FF0D9168{self.invert_phone_number()}00F3A804F4F29C0E', 'test')

    def test_windows_sms_13(self):
        """
        MBIM端收到class 3 (F3)的长短信能正常推送
        :return:
        """
        self.send_pdu_msg('155', f'0011000D9168{self.invert_phone_number()}00F301A0537A584E8FC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD76C3E522B0986C46ABD96EB85C041693CD6835DB0D978BC062B219AD66BBE17211584C36A3D56C375C2E028BC966B49AED86CB456031D98C56B3DD70B9082C269BD16AB61B2E1781C564335ACD1629BAC9', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')

    def test_windows_sms_14(self):
        """
        确认当前存储空间满了后仍能继续接收短信
        (存储空间满后再接收短信会删除之前已读的短信，如果都是未读短信，存储满了的情况，不会删除短信)
        :return:
        """
        self.send_multiple_msg(2, '19', f'0011FF0D9168{self.invert_phone_number()}00F3A804F4F29C0E', 'test')
        self.write_msg_full()
        self.send_full_msg()

    def test_windows_sms_15(self):
        """
        发类型为：GSM, no class的短信(部分运营商不支持class0。CMCC不再支持class0，测试前先确认是否支持)
        MBIM端收到短信
        :return:
        """
        self.send_gsm_msg('no_class')

    def test_windows_sms_16(self):
        """
        发类型为：GSM, class 0的短信
        MBIM端收到短信
        :return:
        """
        self.send_gsm_msg('class_0')

    def test_windows_sms_17(self):
        """
        发类型为：GSM, class 1的短信
        MBIM端收到短信
        :return:
        """
        self.send_gsm_msg('class_1')

    def test_windows_sms_18(self):
        """
        发类型为：GSM, class 2的短信
        MBIM端收到短信
        :return:
        """
        self.send_gsm_msg('class_2')

    def test_windows_sms_19(self):
        """
        发类型为：GSM, class 3的短信
        MBIM端收到短信
        :return:
        """
        self.send_gsm_msg('class_3')

    def test_windows_sms_20(self):
        """
        发送特殊字符^`_ ~@#$%&()*[]|\\和0x00-0x19字符短信
        :return:
        """
        self.send_hex_msg()

    def test_windows_sms_21(self):
        """
        设置短信编码格式为UCS2
        发类型为：UCS2,no class的短信
        MBIM端收到短信
        :return:
        """
        self.send_ucs2_msg()

    def test_windows_sms_22(self):
        """
        设置短信编码格式为IRA
        发IRA类型短信，MBIM端收到短信
        :return:
        """
        self.send_ira_msg()

    def test_windows_sms_23(self):
        """
        SA网络发送ims短信，自发自收
        :return:
        """
        self.at_handle.bound_network('SA')
        self.send_gsm_msg('no_class')

    def test_windows_sms_24(self):
        """
        NSA网络发送IMS短信，自发自收
        :return:
        """
        try:
            self.at_handle.bound_network('NSA')
            self.send_gsm_msg('no_class')
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="nr5g_disable_mode",0')

    def test_windows_sms_25(self):
        """
        LTE网络发送IMS短信，自发自收,支持VOLTE的卡
        :return:
        """
        try:
            self.at_handle.bound_network('LTE')
            self.send_gsm_msg('no_class')
        finally:
            self.at_handle.send_at('AT+QNWPREFCFG="MODE_PREF",AUTO ', 10)

    def test_windows_sms_26(self):
        """
        LTE网络发送IMS短信，自发自收,不支持VOLTE的卡
        :return:
        """
        pass

    def test_windows_sms_27(self):
        """
        WCDMA网络发送短信，自发自收
        :return:
        """
        self.send_wcdma_msg()

    def test_windows_sms_28(self):
        """
        Only SIM1状态接收短信
        :return:
        """
        self.change_slot('1')
        self.send_gsm_msg('no_class')

    def test_windows_sms_29(self):
        """
        Only SIM2状态接收短信
        :return:
        """
        try:
            self.change_slot('2')
            self.sim_2_send_msg()
        finally:
            self.change_slot('1')

    def test_windows_sms_30(self):
        """
        有数据传输时接收短信
        :return:
        """
        self.send_msg_with_ping()

    def test_windows_sms_31(self):
        """
        网卡驱动禁用状态接收短信，网卡启用后能正常推送不会丢失
        :return:
        """
        self.send_msg_with_disable_adapter()

    def test_windows_sms_32(self):
        """
        模块睡眠状态接收短信
        :return:
        """
        self.send_msg_with_low_power()


if __name__ == '__main__':
    test = WindowsSMS('COM6', 'COM4', 'COM39', '15655129469', 'RG500Q-EA', 'CU')
    # test.test_windows_sms_15()
    # test.test_windows_sms_16()
    # test.test_windows_sms_17()
    # test.test_windows_sms_18()
    # test.test_windows_sms_19()
    test.test_windows_sms_21()
