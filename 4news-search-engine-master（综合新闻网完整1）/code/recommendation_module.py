# -*- coding: utf-8 -*-
"""
Created on Wed Feb 27 14:06:10 2019

@author: Peng bing
"""

from os import listdir
import xml.etree.ElementTree as ET
import jieba
import jieba.analyse
import sqlite3
import configparser
from datetime import *
import math

import pandas as pd
import numpy as np
from sklearn.metrics import pairwise_distances

# 推荐模块的思路是度量两两新闻之间的相似度，取相似度最高的前5篇新闻作为推荐阅读的新闻。
# 基于 TF-IDF 算法的关键词抽取
# 推荐模块
class RecommendationModule:
    stop_words = set()
    k_nearest = []
    
    config_path = ''
    config_encoding = ''
    
    doc_dir_path = ''
    doc_encoding = ''
    stop_words_path = ''
    stop_words_encoding = ''
    idf_path = ''
    db_path = ''
    
    def __init__(self, config_path, config_encoding):
        self.config_path = config_path
        self.config_encoding = config_encoding
        config = configparser.ConfigParser()
        config.read(config_path, config_encoding)
        
        self.doc_dir_path = config['DEFAULT']['doc_dir_path']
        self.doc_encoding = config['DEFAULT']['doc_encoding']
        self.stop_words_path = config['DEFAULT']['stop_words_path']
        self.stop_words_encoding = config['DEFAULT']['stop_words_encoding']
        self.idf_path = config['DEFAULT']['idf_path']
        self.db_path = config['DEFAULT']['db_path']

        f = open(self.stop_words_path, encoding = self.stop_words_encoding)
        words = f.read()
        self.stop_words = set(words.split('\n'))

    # 写k邻居矩阵
    def write_k_nearest_matrix_to_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''DROP TABLE IF EXISTS knearest''')
        c.execute('''CREATE TABLE knearest
                     (id INTEGER PRIMARY KEY, first INTEGER, second INTEGER,
                     third INTEGER, fourth INTEGER, fifth INTEGER)''')

        for docid, doclist in self.k_nearest:
            c.execute("INSERT INTO knearest VALUES (?, ?, ?, ?, ?, ?)", tuple([docid] + doclist))

        conn.commit()
        conn.close()


    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False


    # 需要构建文档词项矩阵
    def construct_dt_matrix(self, files, topK = 200):
        # 关键词提取所使用停用词（Stop Words）文本语料库可以切换成自定义语料库的路径。
        # jieba.analyse.set_stop_words(file_name)  #file_name为自定义语料库的路径。
        jieba.analyse.set_stop_words(self.stop_words_path)
        # 关键词提取所使用逆向文件频率（IDF）文本语料库可以切换成自定义语料库的路径。
        # jieba.analyse.set_idf_path(file_name) #file_name为自定义语料库的路径
        jieba.analyse.set_idf_path(self.idf_path)
        M = len(files)
        N = 1
        terms = {}
        dt = []
        for i in files:
            root = ET.parse(self.doc_dir_path + i).getroot()
            title = root.find('title').text
            body = root.find('body').text
            docid = int(root.find('id').text)

            # 参数1：sentence 为待提取的文本
            # 参数2：topK 为返回几个 TF/IDF 权重最大的关键词，默认值为 20
            # 参数3：withWeight 为是否一并返回关键词权重值，默认值为 False)
            tags = jieba.analyse.extract_tags(title + '。' + body, topK=topK, withWeight=True)
            #tags = jieba.analyse.extract_tags(title, topK=topK, withWeight=True)
            cleaned_dict = {}

            for word, tfidf in tags:
                word = word.strip().lower()
                if word == '' or self.is_number(word):
                    continue
                cleaned_dict[word] = tfidf
                if word not in terms:
                    terms[word] = N
                    N += 1
            dt.append([docid, cleaned_dict])
        dt_matrix = [[0 for i in range(N)] for j in range(M)]
        i =0

        for docid, t_tfidf in dt:
            dt_matrix[i][0] = docid
            for term, tfidf in t_tfidf.items():
                dt_matrix[i][terms[term]] = tfidf
            i += 1

        dt_matrix = pd.DataFrame(dt_matrix)
        dt_matrix.index = dt_matrix[0]
        print('dt_matrix shape:(%d %d)'%(dt_matrix.shape))
        return dt_matrix

    # 计算k邻居矩阵
    def construct_k_nearest_matrix(self, dt_matrix, k):
        tmp = np.array(1 - pairwise_distances(dt_matrix[dt_matrix.columns[1:]], metric = "cosine"))
        similarity_matrix = pd.DataFrame(tmp, index = dt_matrix.index.tolist(), columns = dt_matrix.index.tolist())

        for i in similarity_matrix.index:
            tmp = [int(i),[]]
            j = 0
            while j < k:
                max_col = similarity_matrix.loc[i].idxmax(axis = 1)
                similarity_matrix.loc[i][max_col] =  -1
                if max_col != i:
                    tmp[1].append(int(max_col)) #max column name
                    j += 1
            self.k_nearest.append(tmp)


    def gen_idf_file(self):
        files = listdir(self.doc_dir_path)
        n = float(len(files))
        idf = {}

        for i in files:
            root = ET.parse(self.doc_dir_path + i).getroot()
            title = root.find('title').text
            body = root.find('body').text
            seg_list = jieba.lcut(title + '。' + body, cut_all=False)
            seg_list = set(seg_list) - self.stop_words

            for word in seg_list:
                word = word.strip().lower()
                if word == '' or self.is_number(word):
                    continue
                if word not in idf:
                    idf[word] = 1
                else:
                    idf[word] = idf[word] + 1

        idf_file = open(self.idf_path, 'w', encoding = 'utf-8')
        for word, df in idf.items():
            idf_file.write('%s %.9f\n'%(word, math.log(n / df)))
        idf_file.close()


    def find_k_nearest(self, k, topK):
        self.gen_idf_file()
        files = listdir(self.doc_dir_path)
        dt_matrix = self.construct_dt_matrix(files, topK)
        self.construct_k_nearest_matrix(dt_matrix, k)
        self.write_k_nearest_matrix_to_db()


if __name__ == "__main__":
    print('-----start time: %s-----'%(datetime.today()))
    rm = RecommendationModule('../config.ini', 'utf-8')
    rm.find_k_nearest(5, 25)
    print('-----finish time: %s-----'%(datetime.today()))
    