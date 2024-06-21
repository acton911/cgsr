import argparse
from tapp_constructor import constructor
import multiprocessing
import csv


if __name__ == '__main__':
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description='Get Test Setting')
    parser.add_argument('--m', dest='test_setting', type=str)
    args = parser.parse_args()
    my_app = constructor.TestApp(**vars(args))   # TestApp类，初始化参数是启动app的参数，默认的测试是标准的测试流程
    my_app.start()      # 启动App
