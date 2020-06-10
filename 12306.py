import time
import re
import sys
import datetime
import base64

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image


#  创建有窗口的driver
driver_path = "D:\\tools\\chromedriver_win32\\chromedriver.exe"  # chromedriver.exe的相对路径
driver = webdriver.Chrome(executable_path=driver_path)


#  创建无窗口的driver
# driver_path = "Tool/chromedriver.exe"  # chromedriver.exe的相对路径
# chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument('--headless')
# # chrome_options.add_argument('--disable-gpu')
# driver = webdriver.Chrome(options=chrome_options, executable_path=driver_path)


#  处理出发地框
def choice_from_station():
    station = input('请输入您的出发地（不写具体站，只写地名）：')
    from_station = driver.find_element_by_id('fromStationText')
    from_station.click()
    from_station.clear()
    from_station.send_keys(station)
    from_station.send_keys(Keys.ENTER)


#  处理目的地框
def choice_to_station():
    station = input('请输入您的目的地（不写具体站，只写地名）：')
    to_station = driver.find_element_by_id('toStationText')
    to_station.click()
    to_station.clear()
    to_station.send_keys(station)
    to_station.send_keys(Keys.ENTER)


#  输入日期并对输入的正确性进行判断
def isrightdata():
    now_data = datetime.datetime.now()
    i = 0  # 判断日期是否正确的标记变量,i=1时代表正确
    one_month_day = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    #  判断是否为瑞年
    if now_data.year % 4 == 0 and now_data.year % 100 != 0 or now_data.year % 400 == 0:
        is_auspicious_year = 1
    else:
        is_auspicious_year = 0

    while i == 0:
        to_data = input('请输入您要买哪天的票(月和日之间用英文逗号,分隔)：').split(',')
        to_month, to_day = list(map(lambda x: int(x), to_data))  # 将日期转化为int

        #  计算当前日期与出发日期的天数差
        if is_auspicious_year == 1 and now_data.month == 2:
            if now_data.month == to_month:
                between_day = to_day - now_data.day + 1
            else:
                between_day = one_month_day[now_data.month - 1] + 1 - now_data.day + 1 + to_day
        else:
            if now_data.month == to_month:
                between_day = to_day - now_data.day + 1
            else:
                between_day = one_month_day[now_data.month - 1] - now_data.day + 1 + to_day

        if to_month != now_data.month and to_month != now_data.month + 1:  # 输入的月份不是当月或下一个月
            print("输入的日期错误，请重新输入！")
            continue
        elif to_month == now_data.month and to_day < now_data.day:  # 输入的是当月，但是日期小于当天
            print("输入的日期错误，请重新输入！")
            continue
        elif between_day < 1 or between_day > 30:  # 12306只放30天内的票
            print("输入的日期错误，请重新输入！")
            continue
        elif to_month < 1 or to_month > 12:  # 月份不是1-12
            print("输入的日期错误，请重新输入！")
            continue
        elif to_day < 1 or to_day > one_month_day[now_data.month - 1]:  # 日期小于1或者大于当月天数
            print("输入的日期错误，请重新输入！")
            continue
        else:
            i = 1

    return (to_month, to_day)


#  处理选择日期的框
def choice_data():
    data = datetime.datetime.now()
    now_month = data.month
    to_month, to_day = isrightdata()
    driver.find_element_by_xpath("//input[@id='train_date']").click()
    if now_month == to_month:
        driver.find_element_by_xpath("//div[@class='cal-wrap']/"
                                      "div[@class='cal']//div[@class='cal-cm']/div[{}]".format(to_day)).click()
    else:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//div[@class='cal-wrap']/"
                                     "div[@class='cal cal-right']//div[@class='cal-cm']/div[{}]".format(to_day)))
        )
        driver.find_element_by_xpath("//div[@class='cal-wrap']/"
                                     "div[@class='cal cal-right']//div[@class='cal-cm']/div[{}]".format(to_day)).click()


#  处理不同的座位信息
def which_seat(wanted_train, train):
    which_train = re.match(r"([ZDGKTC1-9]).*", wanted_train).group(1)  # 判断用户要购买的是哪种车次，根据车名的开头字母判断
    #  直达
    if which_train == 'Z' or which_train == 'K' or which_train == 'T' or which_train.isdigit():
        while True:
            which_seat_number = int(input("请输入你想要购买的车票类型，输入1为高级软卧，2为软卧，3为硬卧，4为硬座，5为无座："))
            if which_seat_number == 1:
                return (train.find_element_by_xpath("./td[5]").text, '高级软卧')
            elif which_seat_number == 2:
                return (train.find_element_by_xpath("./td[6]").text, '软卧')
            elif which_seat_number == 3:
                return (train.find_element_by_xpath("./td[8]").text, '硬卧')
            elif which_seat_number == 4:
                return (train.find_element_by_xpath("./td[10]").text, '硬座')
            elif which_seat_number == 5:
                return (train.find_element_by_xpath("./td[11]").text, '无座')
            else:
                print('输入错误，请重新输入！')
                continue
    #  高铁
    elif which_train == 'G' or which_train == 'C':
        while True:
            which_seat_number = int(input("请输入你想要购买的车票类型，输入1为商务座，2为一等座，3为二等座："))
            if which_seat_number == 1:
                return (train.find_element_by_xpath("./td[2]").text, '商务座')
            elif which_seat_number == 2:
                return (train.find_element_by_xpath("./td[3]").text, '一等座')
            elif which_seat_number == 3:
                return (train.find_element_by_xpath("./td[4]").text, '二等座')
            else:
                print('输入错误，请重新输入！')
                continue
    #  动车
    elif which_train == 'D':
        while True:
            which_seat_number = int(input("请输入你想要购买的车票类型，输入1为一等座，2为二等座，3为无座，4为一等卧，5为二等卧："))
            if which_seat_number == 1:
                return (train.find_element_by_xpath("./td[3]").text, '一等座')
            elif which_seat_number == 2:
                return (train.find_element_by_xpath("./td[4]").text, '二等座')
            elif which_seat_number == 3:
                return (train.find_element_by_xpath("./td[11]").text, '无座')
            elif which_seat_number == 4:
                return (train.find_element_by_xpath("./td[6]").text, '一等卧')
            elif which_seat_number == 5:
                return (train.find_element_by_xpath("./td[8]").text, '二等卧')
            else:
                print('输入错误，请重新输入！')
                continue
    else:
        print("不能处理这种车次")
        sys.exit()


#  订单页面选择座位
def choose_seat(seat_name):
    select_tag = Select(driver.find_element_by_xpath("//select[@id='seatType_1']"))  # 获取下拉表单的文本内容
    select_texts = driver.find_element_by_xpath("//select[@id='seatType_1']").text
    select_texts = re.sub(r"\s", '', select_texts)  # 去掉空白字符
    select_texts = select_texts.split('）')
    i = 0  # 下拉标签内容在列表中的索引
    for text in select_texts:
        if len(re.findall(r"{}".format(seat_name), text)) == 1:
            select_tag.select_by_index(i)
            break
        else:
            i = i + 1


#  获取二维码，登陆
def login():
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, "//img[@id='J-qrImg']"))
    )  # 等待二维码出现
    src = driver.find_element_by_xpath("//img[@id='J-qrImg']").get_attribute('src')  # 得到二维码的src，base64包含在里面
    image_64 = re.search(r"base64,(.*)", src).group(1)  # 得到图片base64
    image_content = base64.b64decode(image_64)  # 解密，转化为二进制
    with open('QR.png', 'wb') as fp:
        fp.write(image_content)
    image = Image.open('QR.png')
    image.show()
    print('请在3分钟内扫描二维码，登陆账户')


#  在首页登陆
def index_login():
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, "//li[@id='J-header-login']/a[1]"))
    )  # 登陆按钮是否可以被点击
    driver.find_element_by_xpath("//li[@id='J-header-login']/a[1]").click()  # 点击登陆按钮
    login()
    WebDriverWait(driver, 180).until(
        EC.url_to_be('https://kyfw.12306.cn/otn/view/index.html')
    )
    print('登陆成功，可以关闭二维码了！')
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='modal-ft']/a"))
    )  # 判断登陆成功后弹出框的确定按钮是否可以点击
    driver.find_element_by_xpath("//div[@class='modal-ft']/a").click()  # 点击弹出框的确定
    driver.find_element_by_xpath("//li[@id='J-index']").click()  # 跳转到首页
    WebDriverWait(driver, 10).until(
        EC.url_to_be('https://www.12306.cn/index/index.html')
    )  # 判断是否回到了首页


#  选择乘客
def choose_passenger():
    i = 0  # 判断输入乘客是否正确的标记变量,i=1时代表正确
    while i == 0:
        passenger = input("请输入购票人姓名：")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'quickQueryPassenger_id'))
        )
        driver.find_element_by_id('quickQueryPassenger_id').click()  # 点一下输入框
        for j in range(6):
            driver.find_element_by_id('quickQueryPassenger_id').send_keys(Keys.BACK_SPACE)  # 删除输入框中的提示信息
        driver.find_element_by_id('quickQueryPassenger_id').send_keys(passenger)  # 输入乘客
        driver.find_element_by_id('submit_quickQueryPassenger').click()  # 点击搜索
        wanted_passenger = driver.find_elements_by_xpath("//input[@id='normalPassenger_0']")
        if len(wanted_passenger) == 0:
            print('您当前登陆的账号没有该乘客信息，请检查输入的乘客姓名是否正确！')
            continue
        else:
            i = 1  # 不再继续循环
            wanted_passenger[0].click()  # 选中输入乘客


# 确认下单
def confirm_to_buy():
    while True:
        confirm_buy = int(input('您确认买票吗？输入1为确认买票，0为结束程序不买票：'))
        if confirm_buy == 1:
            driver.find_element_by_id('qr_submit_id').click()  # 确认下单
            print("买票成功，您可以去付款了！")
            time.sleep(5)  # 订单提交中
            driver.quit()
            sys.exit()
        elif confirm_buy == 0:
            driver.quit()
            sys.exit()
        else:
            print('输入错误，重新输入！')


#  买票
def buy_ticket(one_train, is_stu, seat_name):
    action = ActionChains(driver)
    reserve_button = one_train.find_element_by_xpath("./td[last()]/a")  # 预订按钮
    action.double_click(reserve_button)  # 双击预订按钮
    action.perform()
    login_box_visible = driver.find_element_by_class_name('modal-login').get_attribute('style')
    if login_box_visible != 'display: none;':  # 判断登陆信息是否过期，是否会弹出登陆框
        print('登陆信息失效，请重新登陆！')
        login()
        WebDriverWait(driver, 10).until(
            EC.url_to_be('https://kyfw.12306.cn/otn/confirmPassenger/initDc')
        )  # 是否来到确认订单页面
        print("登陆成功！")
    WebDriverWait(driver, 10).until(
        EC.url_to_be('https://kyfw.12306.cn/otn/confirmPassenger/initDc')
    )  # 是否来到确认订单页面
    choose_passenger()  # 选择乘客
    if is_stu == 'T':  # 处理是否购买学生票的弹出框
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'dialog_xsertcj_ok'))
        )
        driver.find_element_by_id('dialog_xsertcj_ok').click()
    else:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'dialog_xsertcj_cancel'))
        )
        driver.find_element_by_id('dialog_xsertcj_cancel').click()
    choose_seat(seat_name)  # 在确认订单处选择座位类型
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'submitOrder_id'))
    )
    driver.find_element_by_id('submitOrder_id').click()  # 提交订单
    confirm_to_buy()


#  抢票功能
def snatch_ticket(number_in_list, seat_name, is_stu):
    is_buy_ticket = input("当前是待放票状态，是否现在进行抢票，输入1为进行抢票，输入任何其它字符为结束程序：")
    if is_buy_ticket == '1':
        delay_second = 3  # 到放票时间还有多少秒去抢票
        #  到距离放票还有delay_second秒时再去抢票
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='t-list']//"
                                                      "tr[contains(@id,'ticket_')][{}]".format(number_in_list)))
        )  # 判断列车是否可以被定位
        one_train = driver.find_element_by_xpath("//div[@class='t-list']//"
                                                 "tr[contains(@id,'ticket_')][{}]".format(number_in_list))
        can_buy_text = one_train.find_element_by_xpath("./td[last()]").text  # 获取预订盒子所对应的文本内容
        can_buy_time = re.findall(r"\d+", can_buy_text)  # 提取数字
        now_time = datetime.datetime.now()
        if len(can_buy_time) == 1:
            time_difference = (int(can_buy_time[0]) - now_time.hour - 1) * 60 * 60 + \
                              (60 - now_time.minute) * 60 - now_time.second  # 获取两个时刻的时间差
            if time_difference > delay_second:
                time.sleep(time_difference - delay_second)
        elif len(can_buy_time) == 2:
            time_difference = (int(can_buy_time[0]) - now_time.hour - 1) * 60 * 60 + \
                              (60 - now_time.minute + int(can_buy_time[1])) * 60 - now_time.second
            if time_difference > delay_second:
                time.sleep(time_difference - delay_second)
        else:
            driver.quit()
            sys.exit(1)

        # 不断执行点击查询事件，直到可以预订
        while True:
            try:
                WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.ID, 'query_ticket'))
                )  # 判断查询按钮是否可以被点击
                inquire_button = driver.find_element_by_id('query_ticket')
                inquire_button.click()  # 点击查询按钮
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='t-list']//"
                                                              "tr[contains(@id,'ticket_')][{}]".format(number_in_list)))
                )  # 判断列车是否可以被定位，必须再次去定位one_train，因为在点击完查询按钮后上次定位的one_train已经不依赖于当前页面
                one_train = driver.find_element_by_xpath("//div[@class='t-list']//"
                                                         "tr[contains(@id,'ticket_')][{}]".format(number_in_list))
                can_buy_text = one_train.find_element_by_xpath("./td[last()]").text  # 获取预订盒子所对应的文本内容
                next_page = one_train.find_elements_by_xpath("./td[last()]/a")  # 预订按钮是否可以点击
                if len(next_page) == 1:
                    buy_ticket(one_train, is_stu, seat_name)
                else:
                    if can_buy_text == '预订':
                        print("网速太慢，没抢到票！")
                        driver.quit()
                        sys.exit()
                    else:
                        continue  # 还未放票
            except SystemExit:  # sys.exit()结束程序是抛出了SystemExit，若是此处不加该语句异常被try捕捉，并不会退出程序
                return

            except:  # 查询频繁会超时报错，继续查询
                continue

    else:  # 用户不抢票时，直接退出程序
        driver.quit()
        sys.exit()


#  选择车次并下单
def choice_train(is_stu):
    i = 0  # 标记变量
    number_in_list = 0  # 判断想要乘坐的车次在列表中是第几个
    driver.switch_to.window(driver.window_handles[1])  # 来到车次页面
    while i == 0:
        wanted_train = input("您要买哪趟火车呢:")
        all_trains = driver.find_elements_by_xpath("//div[@class='t-list']//tr[contains(@id,'ticket_')]")
        for one_train in all_trains:  # 利用循环，一个一个的去看是否是想要乘坐的车次
            number_in_list = number_in_list + 1
            train_name = one_train.find_element_by_xpath(".//a[@class='number']").text
            if wanted_train == train_name:  # 当前定位到的是想要乘坐的车次
                is_have_seat, seat_name = which_seat(wanted_train, one_train)  # 处理不同的座位信息
                if is_have_seat == '有' or is_have_seat.isdigit():  # 有票或者是数字
                    buy_ticket(one_train, is_stu, seat_name)
                elif is_have_seat == '*':  # 待放票状态
                    snatch_ticket(number_in_list=number_in_list, seat_name=seat_name, is_stu=is_stu)
                else:
                    print('没有这种票了！')
                    driver.quit()
                    sys.exit()
                i = 1  # 代表输入的车次正确，在车次列表中可以找到
                break  # 已经找到目的车次，不再继续向下匹配车次名
        if i != 1:
            print('没有该车次，请检查您要买的车次名称是否输入完全正确')


def main():
    print('程序准备中，片刻就好！')
    driver.get('https://www.12306.cn/index/index.html')
    index_login()
    choice_from_station()  # 选出发站
    choice_to_station()  # 选目的站
    choice_data()  # 选日期
    while True:
        is_stu = input('是否买学生票（T或F）：')
        if is_stu == 'T':  # 是否购买学生票
            driver.find_element_by_id('isStudentDan').click()
            break
        elif is_stu == 'F':
            break
        else:
            continue
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@class='btn btn-primary form-block']"))
        )  # 判断查询按钮是否可以被点击
    driver.find_element_by_xpath("//a[@class='btn btn-primary form-block']").click()  # 点击查询按钮
    choice_train(is_stu)
    driver.quit()


if __name__ == '__main__':
    main()
