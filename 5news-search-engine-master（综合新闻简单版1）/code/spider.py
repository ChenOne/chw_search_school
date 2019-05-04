# -*- coding: utf-8 -*-
"""
Created on Wed Feb 27 14:06:10 2019

@author: Peng bing
"""

from bs4 import BeautifulSoup
import urllib.request
import xml.etree.ElementTree as ET
import configparser


# 网络爬虫
def get_news_pool(root, start, end):
    news_pool = []
    # 循环拼接url
    for i in range(start,end,-1):
        page_url = ''
        # 判断是否等于第一页，第一页URL不同,从大到小
        if i != start:
            page_url = root + '/' + '%d.htm'%(i)
            print(i)
        # 是第一页
        else:
            page_url = root + ".htm"
        print(page_url)

        try:
            # 获得响应的对象：<http.client.HTTPResponse object at 0x0000000003577908>
            response = urllib.request.urlopen(page_url)
            # if i == 25:
            #     print('===:',response)
        except Exception as e:
            print("-----%s: %s-----"%(type(e), page_url))
            continue
        # 如果需要这里需要加上一行进行转码
        # 读取源码
        html = response.read()
        soup = BeautifulSoup(html,"lxml") # http://www.crummy.com/software/BeautifulSoup/bs4/doc.zh/
        td = soup.find('ul', class_ = "ss")  # ul标签，class='ss'的
        a = td.find_all('a')   # 该 ul 标签下，获取所有的链接列表
        # print('a:',a)
        span = td.find_all('span') # 所有时间的标签,但是有两个span,第二个span是没有时间的
        span = span[::2]    # 所以进行切割，空一个取一个
        # print('span:',span)

        for i in range(len(a)):
            date_time = span[i].string   # 一个一个取所有的时间,
            # print('data:',date_time)
            url = a[i].get('href')   # 取href链接
            # print('url:',url)
            title = a[i].string    # 获取a标签的字符文本，即标题
            # print('title:',title)
            news_info = [date_time, url, title]  # 把每条信息的：[时间，url，标题]作为一条信息存入
            news_pool.append(news_info)
            # print(url)
    return(news_pool)  # 返回新闻信息池


def crawl_news(news_pool, min_body_len, doc_dir_path, doc_encoding):
    base = 'http://news.gpnu.edu.cn/info'
    i = 1
    # 逐条取出新闻url:[时间，url，标题]
    for news in news_pool:
        # 这里代码被固定了，截取到类似：/1100/2476.htm
        news_url = base + news[1][-14:]
        print(news_url)
        try:
            # 如果出错在这里加上：req = urllib.request.Request(news[1],headers) #要定义headers
            # 取时间
            response = urllib.request.urlopen(news_url)
        except Exception as e:
            # print("63行这里出错")
            print("-----%s: %s-----"%(type(e), news_url))
            continue
        # 读取源码
        html = response.read()
        # 解析
        soup = BeautifulSoup(html,"lxml") # http://www.crummy.com/software/BeautifulSoup/bs4/doc.zh/

        try:
            #
            # body = soup.find('div', class_ = "text clear").find('div').get_text()
            body = soup.find('div', class_="single-content").get_text()
        except Exception as e:
            print("-----%s: %s-----"%(type(e), news_url))
            continue

        if '//' in body:
            body = body[:body.index('//')]
        body = body.replace(" ", "")
        if len(body) <= min_body_len:
            continue

        doc = ET.Element("doc")
        ET.SubElement(doc, "id").text = "%d"%(i)
        ET.SubElement(doc, "url").text = news_url
        ET.SubElement(doc, "title").text = news[2]
        ET.SubElement(doc, "datetime").text = news[0]
        ET.SubElement(doc, "body").text = body
        tree = ET.ElementTree(doc)
        tree.write(doc_dir_path + "%d.xml"%(i), encoding = doc_encoding, xml_declaration = True)  # htm 和 xml
        i += 1
    
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('../config.ini', 'utf-8')
    root = 'http://news.gpnu.edu.cn/index/zhxw'
    news_pool = get_news_pool(root, 25, 0)
    crawl_news(news_pool, 140, config['DEFAULT']['doc_dir_path'], config['DEFAULT']['doc_encoding'])
    print('****done****!')