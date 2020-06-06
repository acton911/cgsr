"""
写一个爬虫一般都需要简单的几步
1、爬虫数据：（本例用request）
2、解析数据：（本例子用xpath）
3、存储数据：（本例子直接用数据流）
"""
import requests
from lxml import etree
import re


savepath = ".\\剑来.txt"                       # 数据保存的地址. \\代表本目录下
url = "https://www.52bqg.com/book_45912/"      # 笔趣阁小说网剑来目录网址
headers = {
    "User-Agent":"Mozilla/5.0(Windows NT 10.0;Win64; x64)"
}                                    # 具体看自己的信息


def main():
    content(url)


def content(url):
    respones = requests.get(url, headers=headers)         # requests库方法get方式请求网站
    text = respones.content.decode('gbk')                 # 用GBK解码（具体看网页的编码格式）爬取网页信息
    # print(text)
    html = etree.HTML(text)                               # 用文本的方式解析，返回的一个列表
    a_list = html.xpath('//div[@id="list"]/dl/dd/a/@href') # XPath解析，找到一个id叫list的div 在目录网址中获取具体每章的链接
    for index in a_list:                                   # for循环得出每一章网址
        # 具体每一章的网址
        download_book(url+str(index))                      # 在笔趣阁网址后面加入每一章网址每一章都执行download_book（）


def download_book(url):
    respone = requests.get(url, headers=headers)
    text = respone.content.decode('gbk')
    # print(re)
    html = etree.HTML(text)
    # print(html)
    timu = html.xpath('//div[@class="bookname"]/h1/text()')    # 获取每一章章节名，用text()获取文本
    links = html.xpath('//div[@id="content"]/text()')          # 获取章节内容，用text()获取文本
    savedata(savepath=savepath, msg=timu[0])                   # 保存章节名【0】只是找到第一个章节名就行了
    for index in links:

        print('\n')
        savedata(savepath=savepath, msg = index)               # 执行savedata保存章节内容
        print('\n\n')


def savedata(savepath, msg):
    with open(savepath, 'a', encoding='UTF-8') as f:            # open打开流，用尾部追加（'a'）的方式储存
        f.write(msg)                                            # write写入
    f.close                                                     # 关闭流


if __name__=='__main__':           # 主函数入口
    main()
    print('下载完成：')    # 全部下完执行打印下载完成