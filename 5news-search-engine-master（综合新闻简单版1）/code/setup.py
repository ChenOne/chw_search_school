# -*- coding: utf-8 -*-
"""
Created on Wed Feb 27 14:06:10 2019

@author: Peng bing
"""

from spider import get_news_pool
from spider import crawl_news
from index_module import IndexModule
from recommendation_module import RecommendationModule
from datetime import *
import urllib.request
import configparser


def get_max_page(root):
    # 给url
    response = urllib.request.urlopen(root)
    # 响应给你内容,进行字符串的转换
    html = str(response.read())
    # 找到总页数的变量名
    # html = html[html.find('var maxPage =') : ]
    # html = html[html.find('table',class_='headStylebtk01rn6ds').find('tr').find('td').get_text()]
    # html = html[1:html.find('条')]
    html = '25'

    # max_page = int(html[html.find('=') + 1 : ])
    max_page = int(html)
    print('最大的页数：',max_page)
    return(max_page)

def crawling():
    print('-----start crawling time: %s-----'%(datetime.today()))
    config = configparser.ConfigParser()
    config.read('../config.ini', 'utf-8')
    # 新闻的标题列表页：如综合要闻页：http://news.gpnu.edu.cn/index/zhxw.htm
    root = 'http://news.gpnu.edu.cn/index/zhxw'
    # max_page = get_max_page(root + '.shtml')
    print('***',root + '.htm')
    max_page = get_max_page(root+'.htm')

    news_pool = get_news_pool(root, max_page, max_page - 5)
    print("=========这是分隔线=========")
    crawl_news(news_pool, 140, config['DEFAULT']['doc_dir_path'], config['DEFAULT']['doc_encoding'])
    
if __name__ == "__main__":
    print('-----start time: %s-----'%(datetime.today()))
    
    #抓取新闻数据
    crawling()
    
    #构建索引
    print('-----start indexing time: %s-----'%(datetime.today()))
    im = IndexModule('../config.ini', 'utf-8')
    im.construct_postings_lists()
    
    #推荐阅读
    print('-----start recommending time: %s-----'%(datetime.today()))
    rm = RecommendationModule('../config.ini', 'utf-8')
    rm.find_k_nearest(5, 25)
    print('-----finish time: %s-----'%(datetime.today()))