# -*- coding: utf-8 -*-
"""
Created on Wed Feb 27 14:06:10 2019

@author: Peng bing
"""

import jieba
import math
import operator
import sqlite3
import configparser
from datetime import *

class SearchEngine:
    stop_words = set()
    
    config_path = ''
    config_encoding = ''
    
    K1 = 0  # 可调参数
    B = 0   # 可调参数
    N = 0   # 文档数量
    AVG_L = 0  #平均文档长度

    conn = None
    
    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding

        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        f = open(config['DEFAULT']['stop_words_path'], encoding = config['DEFAULT']['stop_words_encoding'])
        words = f.read()

        self.stop_words = set(words.split('\n'))
        self.conn = sqlite3.connect(config['DEFAULT']['db_path'])
        self.K1 = float(config['DEFAULT']['k1'])
        self.B = float(config['DEFAULT']['b'])
        self.N = int(config['DEFAULT']['n'])
        self.AVG_L = float(config['DEFAULT']['avg_l'])
        

    def __del__(self):
        self.conn.close()
    
    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False
            
    def clean_list(self, seg_list):
        cleaned_dict = {}
        n = 0
        for i in seg_list:
            i = i.strip().lower()
            if i != '' and not self.is_number(i) and i not in self.stop_words:
                n = n + 1
                if i in cleaned_dict:
                    cleaned_dict[i] = cleaned_dict[i] + 1
                else:
                    cleaned_dict[i] = 1
        return n, cleaned_dict


    def fetch_from_db(self, term):
        c = self.conn.cursor()
        c.execute('SELECT * FROM postings WHERE term=?', (term,))
        return(c.fetchone())

    '''
        根据BM25公式，我们可以很快计算出不同文档t对查询Q的得分情况，
    然后按得分高低排序给出结果.
        下面是给定一个查询句子sentence，根据BM25公式给出文档排名的函数:
        首先将句子分词得到所有查询词项，然后从数据库中取出词项对应的倒排记录表，
    对记录表中的所有文档，计算其BM25得分，最后按得分高低排序作为查询结果
    '''
    def result_by_BM25(self, sentence):
        seg_list = jieba.lcut(sentence, cut_all=False)
        n, cleaned_dict = self.clean_list(seg_list)
        BM25_scores = {}

        for term in cleaned_dict.keys():
            r = self.fetch_from_db(term)
            if r is None:
                continue
            df = r[1]
            w = math.log2((self.N - df + 0.5) / (df + 0.5))
            docs = r[2].split('\n')

            for doc in docs:
                docid, date_time, tf, ld = doc.split('\t')
                docid = int(docid)
                tf = int(tf)
                ld = int(ld)
                s = (self.K1 * tf * w) / (tf + self.K1 * (1 - self.B + self.B * ld / self.AVG_L))
                if docid in BM25_scores:
                    BM25_scores[docid] = BM25_scores[docid] + s
                else:
                    BM25_scores[docid] = s

        BM25_scores = sorted(BM25_scores.items(), key = operator.itemgetter(1))
        BM25_scores.reverse()

        if len(BM25_scores) == 0:
            return 0, []
        else:
            return 1, BM25_scores


    '''类似的，我们还可以对所有文档按时间先后顺序排序，越新鲜的新闻排名越高'''
    def result_by_time(self, sentence):
        # jieba.lcut的默认参数只有三个,jieba源码如下
        # lcut(self, sentence, cut_all=False, HMM=True)
        # 分别为:输入文本 是否为全模式分词 与是否开启HMM进行中文分词
        # 精确模式， 返回中文文本sentence分词后的列表
        seg_list = jieba.lcut(sentence, cut_all=False)
        n, cleaned_dict = self.clean_list(seg_list)
        time_scores = {}
        for term in cleaned_dict.keys():
            r = self.fetch_from_db(term)
            if r is None:
                continue
            docs = r[2].split('\n')

            for doc in docs:
                docid, date_time, tf, ld = doc.split('\t')
                if docid in time_scores:
                    continue

                news_datetime = datetime.strptime(date_time, "%Y-%m-%d")
                now_datetime = datetime.now()
                td = now_datetime - news_datetime
                docid = int(docid)
                td = (timedelta.total_seconds(td) / 3600) # hour
                time_scores[docid] = td

        time_scores = sorted(time_scores.items(), key = operator.itemgetter(1))
        if len(time_scores) == 0:
            return 0, []
        else:
            return 1, time_scores


    '''按新闻的热度排序，越热门的新闻排名越高。'''
    # 关于热度公式，我们认为一方面要兼顾相关度，
    # 另一方面也要考虑时间因素，所以是BM25打分和时间打分的一个综合
    def result_by_hot(self, sentence):
        seg_list = jieba.lcut(sentence, cut_all=False)
        n, cleaned_dict = self.clean_list(seg_list)
        hot_scores = {}
        for term in cleaned_dict.keys():
            r = self.fetch_from_db(term)
            if r is None:
                continue
            df = r[1]
            w = math.log2((self.N - df + 0.5) / (df + 0.5))
            docs = r[2].split('\n')

            for doc in docs:
                docid, date_time, tf, ld = doc.split('\t')
                docid = int(docid)
                tf = int(tf)
                ld = int(ld)

                news_datetime = datetime.strptime(date_time, "%Y-%m-%d")
                now_datetime = datetime.now()
                td = now_datetime - news_datetime
                BM25_score = (self.K1 * tf * w) / (tf + self.K1 * (1 - self.B + self.B * ld / self.AVG_L))
                td = (timedelta.total_seconds(td) / 3600) # hour
                hot_score = math.log(BM25_score) + 1 / td

                if docid in hot_scores:
                    hot_scores[docid] = hot_scores[docid] + hot_score
                else:
                    hot_scores[docid] = hot_score

        hot_scores = sorted(hot_scores.items(), key = operator.itemgetter(1))
        hot_scores.reverse()

        if len(hot_scores) == 0:
            return 0, []
        else:
            return 1, hot_scores


    def search(self, sentence, sort_type = 0):
        if sort_type == 0:
            return self.result_by_BM25(sentence)
        elif sort_type == 1:
            return self.result_by_time(sentence)
        elif sort_type == 2:
            return self.result_by_hot(sentence)


if __name__ == "__main__":
    se = SearchEngine('../config.ini', 'utf-8')
    flag, rs = se.search('北京雾霾', 0)
    print(rs[:10])