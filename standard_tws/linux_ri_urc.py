from utils.cases.linux_ri_urc_manager import LinuxRiUrcManager


class LinuxRiUrc(LinuxRiUrcManager):
    def test_ri_urc_1(self):
        """
        USBAT口网络状态上报
        :return:
        """
        self.check_cfun_change_at_urc()

    def test_ri_urc_2(self):
        """
        来短信上报
        :return:
        """
        self.check_msg_at_urc()

    def test_ri_urc_3(self):
        """
        来电RING上报
        :return:
        """
        self.check_ring_at_urc()

    def test_ri_urc_4(self):
        """
        广播RDY上报
        :return:
        """
        self.check_reset_broadcast()

    def test_ri_urc_5(self):
        """
        广播POWERED DOWN上报
        :return:
        """
        self.powerkey_broadcast()

    def test_ri_urc_6(self):
        """
        开启延时CFUN01切换上报时URC跳变
        :return:
        """
        self.delay_cfun_urc_check()

    def test_ri_urc_7(self):
        """
        开启延时来短信上报时URC跳变
        :return:
        """
        self.delay_msg_urc_check()

    def test_ri_urc_8(self):
        """
        开启延时来电上报时URC跳变
        :return:
        """
        self.delay_ring_urc_check()


if __name__ == '__main__':
    linux_ri = LinuxRiUrc('/dev/ttyUSB3', '/dev/ttyUSB1', '/dev/ttyUSB0', '/dev/ttyUSB4', '18119613687')
    try:
        linux_ri.test_ri_urc_1()
    except Exception:
        pass

    # linux_ri.test_ri_urc_2()
    try:
        linux_ri.test_ri_urc_3()
    except Exception:
        pass
    try:
        linux_ri.test_ri_urc_4()
    except Exception:
        pass
    linux_ri.test_ri_urc_5()
    linux_ri.test_ri_urc_6()
    linux_ri.test_ri_urc_7()
    linux_ri.test_ri_urc_8()
