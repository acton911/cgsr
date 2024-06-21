# -*-coding:UTF-8 -*-
import time
from selenium import webdriver
from selenium.webdriver.common.by import By


chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')  # 这个配置很重要
driver = webdriver.Chrome(chrome_options=chrome_options, executable_path='/home/ubuntu/Desktop/Function_qss/20221114/standard_tws-develop/test/chromedriver')  # 如果没有把chromedriver加入到PATH中，就需要指明路径

driver.get("http://192.168.2.1")
driver.maximize_window()
time.sleep(1)

# click start
driver.find_element(By.ID, "startStopBtn").click()
time.sleep(30)

# get resutl
pingText = driver.find_element(By.ID, "pingText").text
jitText = driver.find_element(By.ID, "jitText").text
dlText = driver.find_element(By.ID, "dlText").text
ulText = driver.find_element(By.ID, "ulText").text

print("*********************************************")
print('Ping(ms):')
print(pingText)
print('Jitter(ms):')
print(jitText)
print('Download(Mbps):')
print(dlText)
print('Upload(Mbps):')
print(ulText)
print("*********************************************")
