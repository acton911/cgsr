# import time
# import sys
# import traceback
# from utils.functions.decorators import startup_teardown
# from utils.logger.logging_handles import all_logger
import time

from utils.cases.linux_sms_manger import LinuxSMSManager


class LinuxSMS(LinuxSMSManager):
	def test_sms_00_001(self):
		"""
		打开ims
		:return:
		"""
		self.check_ims()
	
	def test_sms_01_001(self):
		"""
		写GSM no class类型短信自发自收
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms('GSM')
		self.sms_init()
		
	def test_sms_01_002(self):
		"""
		发送GSM class3类型最大长度短信成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=197, pid=0, dcs=243)
		self.write_msg('GSM', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')
		self.send_cmss_sms('GSM')
		self.sms_init()
		
	def test_sms_01_003(self):
		"""
		读取未读&已读短信，查看 <stat>状态显示为"REC UNREAD"和"REC READ"
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.at_handle.send_at('AT+CMGD=0,4', 10)
		self.select_csdh(0)
		self.write_msg('GSM', 'test read&unread')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', 'test read&unread')
		self.sms_twice_read('REC UNREAD', 'test read&unread', 1)
		self.sms_init()
		
	def test_sms_01_004(self):
		"""
		读取已发送&未发送短信，查看<stat>状态显示为"STO SENT"和"STO UNSENT"
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.at_handle.send_at('AT+CMGD=1,4', 10)
		self.write_msg('GSM', 'test sto sent')
		self.sms_read('STO UNSENT', 'test sto sent')
		self.select_cmgl('"STO UNSENT"', 'test sto sent')
		self.send_cmss_sms('GSM')
		self.sms_read('STO SENT', 'test sto sent')
		self.select_cmgl('"STO SENT"', 'test sto sent')
		self.sms_init()
		
	def test_sms_01_005(self):
		"""
		AT+CMGL已读、未读功能测试
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.at_handle.send_at('AT+CMGD=1,4', 10)
		self.write_msg('GSM', 'test')
		self.send_cmss_sms('GSM')
		self.select_cmgl('"REC UNREAD"', 'test')
		self.sms_twice_list(1)
		self.select_cmgl('"REC READ"', 'test')
		self.sms_init()
	
	def test_sms_02_001(self):
		"""
		写入数据后输入HEX数据"08"，查看回显正确
		"""
		self.configure_cmgf(1)
		self.write_msg('HEX', '414108')
		self.sms_read('STO UNSENT', 'A')
		self.sms_init()

	def test_sms_02_002(self):
		"""
		写入HEX数据"1A"，查看回显正确
		"""
		self.configure_cmgf(1)
		self.write_a_b_msg('1A')
		self.sms_read('STO UNSENT', '')
		self.sms_init()

	def test_sms_02_003(self):
		"""
		写入HEX数据"1B"，查看回显正确
		"""
		self.configure_cmgf(1)
		self.write_a_b_msg('1B')
		self.sms_init()

	def test_sms_02_004(self):
		"""
		GSM字符集设置0x00-0x1A字符能正确输入
		"""
		self.configure_cmgf(1)
		self.write_msg('HEX', '000102030405060708090A0B0C0D0E0F101112131415161718191A')
		self.sms_read('STO UNSENT', '')
		self.sms_init()

	def test_sms_02_005(self):
		"""
		GSM字符集设置0x1C-0x7F字符能正确输入
		"""
		self.configure_cmgf(1)
		self.write_msg('HEX', '1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F')
		self.sms_read('STO UNSENT', '')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '')
		self.sms_init()

	def test_sms_03_001(self):
		"""
		发GSM, no class类型短信成功，且有短信的消息报告
		"""
		self.configure_cmgf(1)
		self.configure_csmp(fo=49, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.send_cmgs_gsm_sms('GSM no class - 1234567812345678')
		self.sms_init()
		
	def test_sms_04_001(self):
		"""
		写发GSM, class 0（闪信）类型短消息成功
		"""
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=240)
		self.configure_cnmi(mode=2, mt=2, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'Start_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456789_0123456_End')
		self.send_cmss_sms('GSM')
		self.check_msg_number('ME', 1)
		self.sms_init()
	
	def test_sms_04_002(self):
		"""
		普通短信以闪信形式上报
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=241)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.configure_cpms('ME')
		self.at_handle.send_at('AT+CMGD=0,4', 10)
		self.send_cmgs_gsm_sms('SM class 1')
		self.check_msg_number('ME', 1)
		self.sms_init()
	
	def test_sms_04_003(self):
		"""
		GSM字符集下测试闪信的CMT和CDS提示测试
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_csmp(fo=49, vp=196, pid=0, dcs=240)
		self.configure_cnmi(mode=2, mt=2, bm=0, ds=1, bfr=0)
		self.send_cmgs_gsm_sms('Hello')
		self.sms_init()
	
	def test_sms_05_001(self):
		"""
		写发UCS2 class 2类型短消息成功
		"""
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=144, pid=0, dcs=26)
		self.configure_cscs('UCS2')
		self.configure_cpms('SM')
		self.write_msg('GSM', '005500430053003200200063006C0061007300730032002000740065007300746D4B8BD5007E00210040002300240025005E0026002A00280029002D003D007C007B007D005B005D003C003E003F002F002700270022003B003A')
		self.send_cmss_sms('UCS2')
		self.sms_init()
		
	def test_sms_05_002(self):
		"""
		直接发送UCS2 class 3类型短信成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('UCS2')
		self.configure_csmp(fo=17, vp=143, pid=0, dcs=27)
		self.send_cmgs_ucs2_sms('5F0059CB2026202600250026FF09003300350036003400370036003500340037573064924E2A5BF96E56592753A653CD653B50127B9751712026202600260026002A0023002AFF08002500340035003400350036003400330036003200370026002A0025002A00280026005E0023002900250024005E002500260025002A548C53F7597D573065B97ED3675F')
		self.sms_init()
	
	def test_sms_06_001(self):
		"""
		写入IRA字符短信并发送成功
		"""
		self.configure_cscs('IRA')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=196, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', '123456789ABCDEFGabcdefg')
		self.sms_read('STO UNSENT', '123456789ABCDEFGabcdefg')
		self.send_cmss_sms('GSM')
		self.sms_init()
	
	def test_sms_06_002(self):
		"""
		写入IRA特有字符(GSM不包含)成功
		"""
		self.configure_cscs('IRA')
		self.configure_cmgf(1)
		self.write_msg('GSM', '_')
		self.sms_read('STO UNSENT', '_')
		self.configure_cmgf(0)
		self.sms_read('STO UNSENT', '0891683108501505F0116400800000A70111')
		self.configure_cmgf(1)
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '_')
		self.write_msg('GSM', '$')
		self.configure_cmgf(0)
		self.sms_read('STO UNSENT', '0891683108501505F0116400800000A70102')
		self.configure_cmgf(1)
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '$')
		self.sms_init()
	
	def test_sms_06_003(self):
		"""
		AT+CMGW写入HEX数据"08"成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('IRA')
		self.write_msg('HEX', '414108')
		self.sms_read('STO UNSENT', 'A')
		self.sms_init()
	
	def test_sms_06_004(self):
		"""
		AT+CMGW写入HEX数据"1A"成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('IRA')
		self.write_msg('HEX', '41411A')
		self.sms_read('STO UNSENT', 'AA')
		self.sms_init()
		
	def test_sms_06_005(self):
		"""
		AT+CMGW写入HEX数据"1B"成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('IRA')
		self.write_msg('HEX', '1B')
		self.sms_init()
		
	def test_sms_06_006(self):
		"""
		AT+CMGW写入HEX数据00-1A成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('IRA')
		self.write_msg('HEX', '00080A0D1A')
		self.sms_read('STO UNSENT', '')
		self.sms_init()
		
	def test_sms_06_007(self):
		"""
		AT+CMGW写入HEX数据1C-7F成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('IRA')
		self.write_msg('HEX', '2122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5F6162636465666768696A6B6C6D6E6F707172737475767778797A')
		self.sms_read('STO UNSENT', '')
		self.sms_init()
	
	def test_sms_07_001(self):
		"""
		写发GSM, no class类型短信成功
		"""
		self.configure_cmgf(0)
		self.configure_cpms('SM')
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.sms_read('STO UNSENT', '0891683108501505F011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.sms_twice_read('REC UNSENT', '0891683108501505F011FF009100004704F4F29C0E', 1)
		self.sms_init()
	
	def test_sms_07_002(self):
		"""
		直接发送GSM, class 2(F2)类型最长短信(155)成功
		"""
		self.configure_cmgf(0)
		self.configure_cpms('SM')
		self.configure_cscs('GSM')
		self.send_cmgs_pdu_sms(155)
		self.sms_read('REC UNREAD', '')
		self.sms_twice_read('REC UNREAD', '', 1)
		self.sms_init()
	
	def test_sms_07_003(self):
		"""
		CMGL=0/1列举未读/已读短信成功
		"""
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.select_cmgl(0, '0891683108501505F0040D91685151957494F200002280715161422304F4F29C0E')
		self.select_cmgl(0, '0891683108501505F0040D91685151957494F200002280715161422304F4F29C0E')
		self.select_cmgl(1, '0891683108501505F0040D91685151957494F200002280715161422304F4F29C0E')
		self.sms_init()
	
	def test_sms_07_004(self):
		"""
		CMGL=2/3列举未发送/已发送短信成功
		"""
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.select_cmgl(2, '0891683108501505F011FF009100004704F4F29C0E')
		self.select_cmgl(2, '0891683108501505F011FF009100004704F4F29C0E')
		self.select_cmgl(3, '0891683108501505F011FF009100004704F4F29C0E')
		self.sms_init()
		
	def test_sms_07_005(self):
		"""
		CMGL=2/3列举未发送/已发送短信成功
		"""
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.select_cmgl(4, '0891683108501505F011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.select_cmgl(4, '0891683108501505F011FF009100004704F4F29C0E')
		self.select_cmgl(4, '0891683108501505F011FF009100004704F4F29C0E')
		self.sms_init()
		
	def test_sms_08_001(self):
		"""
		CMGL=2/3列举未发送/已发送短信成功
		"""
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=1, bfr=0)
		self.send_cmgs_pdu_sms(28)
		self.sms_init()
		
	def test_sms_09_001(self):
		"""
		Text模式下AT+CMGD=<index> 删除单条短信成功
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.send_cmgs_gsm_sms('test')
		self.send_cmgs_gsm_sms('test')
		self.select_cmgl('"ALL"', '')
		self.check_msg_number('ME', 2)
		self.at_handle.send_at('AT+CMGD=0', 10)
		self.at_handle.send_at('AT+CMGD=1', 10)
		self.check_msg_number('ME', 0)
		self.sms_read_fail(1)
		self.sms_init()
		
	def test_sms_09_002(self):
		"""
		AT+CMGD=<index>,1 <index>不在已读范围内时,<index>短信不会被删除
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('SM')
		self.send_cmgs_gsm_sms('test')
		self.select_cmgl('"ALL"', '')
		self.write_msg('GSM', '12345')
		self.select_cmgl('"ALL"', '')
		self.check_msg_number('SM', 2)
		self.at_handle.send_at('AT+CMGD=1,1', 10)
		self.select_cmgl('"ALL"', '')
		self.check_msg_number('SM', 1)
		self.at_handle.send_at('AT+CMGD=1,4', 10)
		self.sms_init()
		
	def test_sms_09_003(self):
		"""
		AT+CMGD=<index>,2删除所有已读和已发短信
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('SM')
		self.write_msg('GSM', 'test')
		self.send_cmss_sms('GSM')
		self.select_cmgl('"ALL"', '')
		self.select_cmgl('"ALL"', '')
		self.check_msg_number('SM', 2)
		self.at_handle.send_at('AT+CMGD=1,2', 10)
		self.select_cmgl('"ALL"', '')
		self.sms_read_fail(0)
		self.sms_init()
	
	def test_sms_09_004(self):
		"""
		AT+CMGD=<index>,3 删除所有已读，已发，未发短信(只剩未读短信)
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('SM')
		self.write_msg('GSM', '12')
		self.write_msg('GSM', '34')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '34')
		self.send_cmss_sms('GSM')
		self.at_handle.send_at('AT+CMGD=1,3', 10)
		self.select_cmgl('"ALL"', '')               #当前未处理短信是否为未读状态
		self.check_msg_number('SM', 1)
		self.sms_init()
	
	def test_sms_09_005(self):
		"""
		AT+CMGD=<index>,4 删除所有短信
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.write_msg('GSM', 'test')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', 'test')
		self.at_handle.send_at('AT+CMGD=0,4', 10)
		self.check_msg_number('ME', 0)
		self.configure_cmgf(0)
	
	def test_sms_10_001(self):
		"""
		smsfull配置为0短信写满存储空间没有任何URC上报；
		smsfull配置为1，向短信存储空间写短信，写满有短信满URC上报
		"""
		self.at_handle.send_at('AT+QINDCFG="smsfull",0', 10)
		self.configure_cmgf(1)
		self.configure_cpms('SM')
		self.configure_cscs('GSM')
		self.write_msg_full()
		self.at_handle.send_at('AT+QINDCFG="smsfull",1', 10)
		self.at_handle.send_at('AT+QINDCFG="smsfull"', 10)
		self.send_full_sms()
		self.at_handle.send_at('AT+CMGD=0,4', 30)
		self.sms_init()
	
	def test_sms_11_001(self):
		"""
		非法参数设置测试
		"""
		self.check_qcmgs('255', '0', '16')
		self.check_qcmgs('0', '16', '7')
		self.check_qcmgs('256', '0', '0')
		self.check_qcmgs('0', '0', '')
		self.check_qcmgs('0', '2', '')
		self.check_qcmgs('1', '15', '15')
		
	def test_sms_11_002(self):
		"""
		发送长短信单条最长短信(153个字符)成功,发送超过长短信单条最长(大于153个字符)短信失败
		"""
		self.at_handle.send_at('AT+QCMGS=?', 0.3)
		self.at_handle.send_at('AT+QCMGR=?', 0.3)
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.send_qcmgs('GSM', '120', '1', '3', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END', 1)
		self.send_qcmgs('GSM', '120', '1', '3', 'START01234567890123456789013456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456END', 0)
		self.sms_init()
	
	def test_sms_11_003(self):
		"""
		发送GSM, no class长短信给手机成功
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs_phone('120', '1', '7', 'test1')
		self.send_qcmgs_phone('120', '2', '7', 'test2')
		self.send_qcmgs_phone('120', '3', '7', 'test3')
		self.send_qcmgs_phone('120', '4', '7', 'test4')
		self.send_qcmgs_phone('120', '5', '7', 'test5')
		self.send_qcmgs_phone('120', '6', '7', 'test6')
		self.send_qcmgs_phone('120', '7', '7', 'test7')
		self.sms_init()
		
	def test_sms_11_004(self):
		"""
		本机分条读长短信内容显示正确
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs('GSM', '120', '1', '7', 'test1', 1)
		self.sms_qread('REC UNREAD', 'test1')
		self.send_qcmgs('GSM', '120', '2', '7', 'test2', 1)
		self.sms_qread('REC UNREAD', 'test2')
		self.send_qcmgs('GSM', '120', '3', '7', 'test3', 1)
		self.sms_qread('REC UNREAD', 'test3')
		self.send_qcmgs('GSM', '120', '4', '7', 'test4', 1)
		self.sms_qread('REC UNREAD', 'test4')
		self.send_qcmgs('GSM', '120', '5', '7', 'test5', 1)
		self.sms_qread('REC UNREAD', 'test5')
		self.send_qcmgs('GSM', '120', '6', '7', 'test6', 1)
		self.sms_qread('REC UNREAD', 'test6')
		self.send_qcmgs('GSM', '120', '7', '7', 'test7', 1)
		self.sms_qread('REC UNREAD', 'test7')
		self.sms_init()

	def test_sms_11_005(self):
		"""
		发送单条特殊字符长短信成功
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs('GSM', '120', '1', '1', '> ~!@#$%^&*()_+\{};:"\'?/<>.,', 1)
		self.sms_init()
		
	def test_sms_11_006(self):
		"""
		发送多条特殊字符长短信，分条读取显示内容正确
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs('GSM', '120', '1', '2', '~!@#$%^&*()_+\{};:"\'?/<>.,', 1)
		self.sms_qread('REC UNREAD', '~!@#$%^&*()_+\{};:"\'?/<>.,')
		self.sms_qread('REC READ', '~!@#$%^&*()_+\{};:"\'?/<>.,')
		self.send_qcmgs('GSM', '120', '2', '2', '~!@#$%^&*()_+\{};:"\'?/<>.,', 1)
		self.sms_qread('REC UNREAD', '~!@#$%^&*()_+\{};:"\'?/<>.,')
		self.sms_qread('REC READ', '~!@#$%^&*()_+\{};:"\'?/<>.,')
		self.sms_init()
		
	def test_sms_12_001(self):
		"""
		发送长短信单条最长短信（268个字节）成功,发送超过单条最长短信报错
		"""
		self.configure_cscs('UCS2')
		self.configure_cmgf(1)
		self.send_qcmgs('UCS2', '120', '1', '1', '0053007400610072007400300031003200330034003500360037003800390030003100320033003400350036003700380039003000310032003300340035003600370038003900300031003200330034003500360037003800390030003100320033003400350036003700380039003000310032003300340035003600370038003900300031', 1)
		self.sms_qread('REC UNREAD', '')
		self.send_qcmgs('UCS2', '120', '1', '1', '005300740061007200740030003100320033003400350036003700380039003000310032003300340035003600370038003900300031003200330034003500360037003800390030003100320033003400350036003700380039003000310032003300340035003600370038003900300031003200330034003500360037003800390030003100', 0)
		self.sms_init()
	
	def test_sms_12_002(self):
		"""
		读长短信
		"""
		self.configure_cscs('UCS2')
		self.configure_cmgf(1)
		self.send_qcmgs('UCS2', '120', '1', '2', '00530074006100720074', 1)
		self.sms_qread('REC UNREAD', '00530074006100720074')
		self.send_qcmgs('UCS2', '120', '2', '2', '00530074006100720074', 1)
		self.sms_qread('REC UNREAD', '00530074006100720074')
		self.sms_init()
	
	def test_sms_12_003(self):
		"""
		设置短信发送报告上报，读取短信报告状态是否正常
		"""
		self.configure_cscs('UCS2')
		self.configure_cmgf(1)
		self.configure_cnmi(mode=1, mt=1, bm=0, ds=1, bfr=0)
		self.configure_csmp(fo=49, vp=71, pid=0, dcs=8)
		self.send_qcmgs_cds('120', '1', '2', '00530074006100720074')
		self.send_qcmgs_cds('120', '1', '2', '00530074006100720074')
		self.sms_init()
		
	def test_sms_13_001(self):
		"""
		发送GSM, no class类型单条最长(153字节)长短信成功
		"""
		self.configure_cscs('IRA')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs('GSM', '120', '1', '3', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END', 1)
		self.sms_qread('REC UNREAD', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END')
		self.send_qcmgs('GSM', '120', '2', '3', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END', 1)
		self.sms_qread('REC UNREAD', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END')
		self.send_qcmgs('GSM', '120', '3', '3', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END', 1)
		self.sms_qread('REC UNREAD', 'START0123456789012345678901345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345END')
		self.sms_init()
		
	def test_sms_13_002(self):
		"""
		发送特殊字符长短信正常
		"""
		self.configure_cscs('IRA')
		self.configure_cmgf(1)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.send_qcmgs('GSM', '120', '1', '3', '~!@#$%^&*()_+\{};:"\'?/<>.,', 1)
		self.sms_qread('REC UNREAD', '~!@#$%^&*()_+\{};:"\'?/<>.,')
		self.sms_init()

	def test_sms_14_001(self):
		"""
		CFUN 0/1切换后,可以正常短信收发回复短信中心号码ACK确认方法
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('PB DONE', timout=30)
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.send_cmgs_gsm_sms('1111')
		self.sms_init()
		
	def test_sms_14_002(self):
		"""
		CFUN 4/1切换后,可以正常短信收发
		"""
		self.configure_cscs('GSM')
		self.configure_cmgf(1)
		self.at_handle.cfun4()
		time.sleep(5)
		self.at_handle.cfun1()
		time.sleep(5)
		self.send_qcmgs('GSM', '120', '1', '3', 'test1', 1)
		self.sms_qread('REC UNREAD', 'test1')
		self.send_qcmgs('GSM', '120', '2', '3', 'test2', 1)
		self.sms_qread('REC UNREAD', 'test2')
		self.send_qcmgs('GSM', '120', '1', '3', 'test3', 1)
		self.sms_qread('REC UNREAD', 'test3')
		self.sms_init()
	
	def test_sms_15_002(self):
		"""
		关机中来短信
		"""
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms_vabt()
		self.gpio.set_vbat_high_level()
		self.driver.check_usb_driver_dis()
		self.gpio.set_vbat_low_level_and_pwk()
		self.driver.check_usb_driver()
		self.at_handle.readline_keyword('PB DONE', timout=300)
		self.check_msg_number('ME', 1)
		self.sms_init()
		
	def test_sms_15_003(self):
		"""
		未解PIN中来短信
		"""
		
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.at_handle.set_sim_pin()
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms_vabt()
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('SIM PIN', timout=10)
		self.at_handle.sin_pin_remove()
		self.at_handle.readline_keyword('CMTI', 'PB DONE', timout=120)
		self.check_msg_number('ME', 1)
		self.sms_read('REC UNREAD', 'GSM no class#$DGFHffh#1')
		self.sms_init()
		
	def test_sms_16_001(self):
		"""
		SA网络下,发送text格式短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('SA')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('PB DONE', timout=30)
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', 'GSM no class#$DGFHffh#1')
		self.revive_mode_pref()
		self.sms_init()
		
	def test_sms_16_002(self):
		"""
		SA网络下，发送PDU短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('SA')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('PB DONE', timout=30)
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '0891683108501505F011FF009100004704F4F29C0E')
		self.revive_mode_pref()
		self.sms_init()
		
	def test_sms_16_003(self):
		"""
		LTE网络下,发送text格式短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('LTE')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('PB DONE', timout=30)
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', 'GSM no class#$DGFHffh#1')
		self.revive_mode_pref()
		self.sms_init()
		
	def test_sms_16_004(self):
		"""
		LTE网络下，发送PDU短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('LTE')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.readline_keyword('PB DONE', timout=30)
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', '0891683108501505F011FF009100004704F4F29C0E')
		self.revive_mode_pref()
		self.sms_init()
		
	def test_sms_16_005(self):
		"""
		WCDMA网络下,发送text格式短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('WCDMA')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(1)
		self.configure_cscs('GSM')
		self.configure_cpms('ME')
		self.configure_csmp(fo=17, vp=71, pid=0, dcs=0)
		self.configure_cnmi(mode=2, mt=1, bm=0, ds=0, bfr=0)
		self.write_msg('GSM', 'GSM no class#$DGFHffh#1')
		self.send_cmss_sms('GSM')
		self.sms_read('REC UNREAD', 'GSM no class#$DGFHffh#1')
		self.revive_mode_pref()
		self.sms_init()
		
	def test_sms_16_006(self):
		"""
		WCDMA网络下,发送PDU短信
		"""
		self.check_mode_pref()
		self.at_handle.bound_network('WCDMA')
		self.at_handle.cfun0()
		time.sleep(5)
		self.at_handle.cfun1()
		self.at_handle.send_at('AT+QNWINFO', 0.3)
		self.configure_cmgf(0)
		self.configure_cscs('GSM')
		self.write_pdu_msg('0011FF009100004704F4F29C0E')
		self.send_cmss_sms('GSM')
		self.sms_read('STO UNREAD', '0891683108501505F011FF009100004704F4F29C0E')
		self.revive_mode_pref()
		self.sms_init()
	
	def test_sms_16_008(self):
		"""
		IMS短信收发
		"""
		
	def test_sms_17_001(self):
		"""
		开启SIM卡热插拔，拔插SIM卡后，短信发送正常
		"""
		
	def test_sms_17_002(self):
		"""
		SIM卡热插拔开启，拔SIM卡，更换不同运营商SIM卡，短信发送仍正常
		"""
	
	def test_sms_18_001(self):
		"""
		新增AT+QIMSCFG="service" 开启ims服务指令测试
		"""
	
	def test_sms_18_002(self):
		"""
		关闭ims短信服务功能
		"""
	
	def test_sms_18_003(self):
		"""
		关闭ims通话功能
		"""
	
	def test_sms_18_004(self):
		"""
		测试关闭ims指令不生效
		"""
		
	def test_sms_19_001(self):
		"""
		针对部分项目，测试结束关闭ims，恢复默认
		"""
		self.revive_ims()


if __name__ == '__main__':
	params_dict = {
		"at_port": '/dev/ttyUSBAT',
		"dm_port": '/dev/ttyUSBDM',
		"debug_port": '/dev/ttyUSBDEBUG',
		"phonenumber": '13225606517',
		"phonenumber_PDU": '3122656015F7',
		"phonenumber_HEX": '3133323235363036353137',
		"phonenumber_UCS2": '00310033003200320035003600300036003500310037',
		"sca_number": '8613010305500',
		"sim_imsi": '460015602228965',
		"sim_iccid": '98681012086175093482',
		"sim_puk": '51989916',
		"sim_operator": 'CU',
		"operator_servicenumber": '10010',
		"dev_sm_store": '255',
		"dev_me_store": '50'
	}
	
	linux_sms = LinuxSMS(**params_dict)
	linux_sms.test_sms_00_001()
	linux_sms.test_sms_01_001()
	linux_sms.test_sms_01_002()
	linux_sms.test_sms_01_003()
	linux_sms.test_sms_01_004()
	linux_sms.test_sms_01_005()
	linux_sms.test_sms_02_001()
	linux_sms.test_sms_02_002()
	linux_sms.test_sms_02_003()
	linux_sms.test_sms_02_004()
	linux_sms.test_sms_02_005()
	linux_sms.test_sms_03_001()
	linux_sms.test_sms_04_001()
	linux_sms.test_sms_04_002()
	linux_sms.test_sms_04_003()
	linux_sms.test_sms_05_001()
	linux_sms.test_sms_05_002()
	linux_sms.test_sms_06_001()
	linux_sms.test_sms_06_002()
	linux_sms.test_sms_06_003()
	linux_sms.test_sms_06_004()
	linux_sms.test_sms_06_005()
	linux_sms.test_sms_06_006()
	linux_sms.test_sms_06_007()
	linux_sms.test_sms_07_001()
	linux_sms.test_sms_07_002()
	linux_sms.test_sms_07_003()
	linux_sms.test_sms_07_004()
	linux_sms.test_sms_07_005()
	linux_sms.test_sms_08_001()
	linux_sms.test_sms_09_001()
	linux_sms.test_sms_09_002()
	linux_sms.test_sms_09_003()
	linux_sms.test_sms_09_004()
	linux_sms.test_sms_09_005()
	linux_sms.test_sms_10_001()
	linux_sms.test_sms_11_001()
	linux_sms.test_sms_11_002()
	linux_sms.test_sms_11_003()
	linux_sms.test_sms_11_004()
	linux_sms.test_sms_11_005()
	linux_sms.test_sms_11_006()
	linux_sms.test_sms_12_001()
	linux_sms.test_sms_12_002()
	linux_sms.test_sms_12_003()
	linux_sms.test_sms_13_001()
	linux_sms.test_sms_13_002()
	linux_sms.test_sms_14_001()
	linux_sms.test_sms_14_002()
	linux_sms.test_sms_15_002()
	linux_sms.test_sms_15_003()
	linux_sms.test_sms_16_001()
	linux_sms.test_sms_16_002()
	linux_sms.test_sms_16_003()
	linux_sms.test_sms_16_004()
	linux_sms.test_sms_16_005()
	linux_sms.test_sms_16_006()
	linux_sms.test_sms_16_008()
	linux_sms.test_sms_17_001()
	linux_sms.test_sms_17_002()
	linux_sms.test_sms_18_001()
	linux_sms.test_sms_18_002()
	linux_sms.test_sms_18_003()
	linux_sms.test_sms_18_004()
	linux_sms.test_sms_19_001()
	