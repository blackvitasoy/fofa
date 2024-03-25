#! /usr/bin/python
# -*- coding: UTF-8 -*-

import configparser
import requests
import traceback
import urllib
import urllib3
import base64
import json
import datetime
import csv
import argparse
import time

import xlsxwriter
import re
import math

#请求失败重试模块
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
retry_times = 3
retry_backoff_factor = 3
session = requests.Session()
retry = Retry(total=retry_times, backoff_factor=retry_backoff_factor, status_forcelist=[500, 502, 503, 504, 429], allowed_methods=["HEAD", "GET", "OPTIONS"])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount('https://', adapter)

#取消https告警
urllib3.disable_warnings()

class Fofa_Client:

	def __init__(self, query_str=""):

		#读取配置文件
		config = configparser.ConfigParser()
		config.read('fofa.ini', encoding='utf-8')

		#邮箱和key
		self.email = config.get('userinfo', "email")
		self.key = config.get("userinfo", "key")

		#fofa 处理的字段
		self.query_str = query_str
		self.fields = config.get("fields", "fields")
		self.page = 1
		self.size = config.get("size", "size")
		self.next = ""
		self.full = config.get("full", "full")
		
		#接口url
		self.base_url = "https://fofa.info"
		self.login_api_url = "/api/v1/info/my"
		self.search_api = "/api/v1/search/all"
		self.host_api_url = "/api/v1/host/"
		self.next_api_url = "/api/v1/search/next"


		#请求header处理
		self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5666.197 Safari/537.36"}
		self.proxy = config.get("proxy", "proxy")
		if self.proxy:
			self.proxy = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
		else:
			self.proxy = {}
		# print(self.proxy)
	
	#fofa登录
	def get_userinfo(self):
		#url处理
		api_full_url = self.base_url + self.login_api_url
		param = {"email": self.email, "key": self.key}
		res = self.__http_get(api_full_url, param)
		return res

	#基础的url处理
	def __http_get(self, url, param):

		param = urllib.parse.urlencode(param)
		url = url + "?" + param

		try:
			res = session.get(url=url, headers=self.headers, proxies=self.proxy, timeout=10, verify=False)

			if "errmsg" in res:
				raise RuntimeError(res)
		except Exception as e:
			print(e)
			traceback.print_exc()

		return res.text
	
	#查询接口，无需翻页，最多10000条数据
	def get_search_data(self):

		api_full_url = self.base_url + self.search_api
		query_str = self.query_str.encode('utf-8')
		base64_query = base64.b64encode(query_str)
		param = {"key":self.key, "qbase64": base64_query, "fields": self.fields, "page":self.page, "size":self.size, "full":self.full}

		res = self.__http_get(api_full_url, param)
		res = json.loads(res)

		#该翻页功能需要用上
		# size = math.ceil(res['size'] / 10000)
		# if size > 1:
		# 	result_dict = {}
		# 	for page in range(size):
		# 		param['page'] = page + 1
		# 		res = self.__http_get(api_full_url, param)
		# 		res = json.loads(res)
		# 		result_dict.update(res)
		# 	res = result_dict

		return res
	
	#host聚合接口
	def get_host_data(self):

		host = self.query_str
		api_full_url = self.base_url + self.host_api_url + host
		param = {"detail": "true", "key": self.key}

		res = self.__http_get(api_full_url, param)
		time.sleep(1.5)
		res = json.loads(res)
		return res

	#连续翻页接口,fofa高级会员只能查询前10000
	def get_next_data(self):

		api_full_url = self.base_url + self.next_api_url
		query_str = self.query_str.encode('utf-8')
		base64_query = base64.b64encode(query_str)
		param = {"key":self.key, "qbase64": base64_query, "fields": self.fields, "size":self.size, "next":self.next,"full":self.full}

		res = self.__http_get(api_full_url, param)
		res = json.loads(res)

		#F点不足，无法处理进行翻页
		# size = math.ceil(res['size'] / 10000)
		
		#对size值进行一个循环
		# if size > 1:
		# 	result_dict = {}
		# 	print(res['next'])
		# 	for size in range(size):
		# 		self.next = res['next']
		# 		print(self.next)
		# 		param = {"key":self.key, "qbase64": base64_query, "fields": self.fields, "size":self.size, "next":self.next,"full":self.full}
		# 		res = self.__http_get(api_full_url, param)
		# 		res = json.loads(res)
		# 		result_dict.update(res)
		# 	res = result_dict
		return res

#文件写入类
class File_write(object):

	def __init__(self,data=""):

		#读取要写入的字段
		config = configparser.ConfigParser()
		config.read('fofa.ini', encoding='utf-8')

		#search写入读取的头文件
		self.fields = config.get('fields', 'fields')

		#输出文件
		now = datetime.datetime.now()
		self.now_str = now.strftime('%Y%m%d_%H%M%S')
		self.write_filename = f'{self.now_str}.xlsx'

		#需要处理的数据
		self.data = data

		#host写入读取的头文件
		self.host_headers_list = ['host','ip', 'country_name', 'country_code', 'port', 'protocol', 'url']
		# self.host_headers_list = ['host','ip', 'country_name', 'country_code', 'port', 'protocol', 'url', 'products']
	
	def search_write_file(self):

		workbook = xlsxwriter.Workbook(self.write_filename)
		worksheet = workbook.add_worksheet()

		# print(self.fields)
		#headers 文件获取
		headers = self.fields
		headers_list = headers.split(',')

		#写入文件头,并在原来的基础上添加新的一行url
		# print(headers_list)
		headers_list.insert(5, 'url')
		# print(headers_list)
		worksheet.write_row('A1', headers_list)
		
		data = self.data
		#增加新行url
		for line in range(len(data)):
			data_list = data[line]

			if 'http://' in data_list[4] or 'https://' in data_list[4]: 
				url = data_list[4]
			elif 'http' in data_list[2] or 'https' in data_list[2]:
				url = data_list[2] + "://" + data_list[4]
			else:
				url = None
			data_list.insert(5, url)

			worksheet.write_row(f'A{line + 2}', data_list)
			
		workbook.close()

	def host_write_file(self):

		# #初始化一个excel表
		# workbook = xlsxwriter.Workbook(self.write_filename)
		# worksheet = workbook.add_worksheet()
		
		# #定义列表头
		# host_headers_list = self.host_headers_list
		# print(host_headers_list)
		# worksheet.write_row('A1', host_headers_list)

		# # print(data)
		# for line in range(len(self.data)):
		# 	data_list = self.data[line]

		# 	#写入数据
		# 	worksheet.write_row(f'A{line + 2}', data_list)

		# workbook.close()
		file_name = f'{self.now_str}.csv'
		with open(file_name, 'w', newline='') as file:

			writer = csv.writer(file)
			writer.writerow(self.host_headers_list)
			writer.writerows(self.data)


#文件读取
def read_file(file_name):

	try:
	#读取文件
		with open(file_name, "r+", encoding="utf-8") as file:
			lines = file.readlines()
			return lines
	except Exception as e:
		return f"请输入正确的文件，{e}"

#输出结果
def output_result():
	#获取args命令
	parsers = argparse.ArgumentParser()
	group = parsers.add_mutually_exclusive_group()
	group.add_argument('-q', "--query", help="请输入一个查询语句")
	group.add_argument('-l', "--file", help="请输入一个查询文件")
	group.add_argument('-bhq', "--bat_host_query", help="批量根据ip和域名查询资产")
	args = parsers.parse_args()

	#对获取的参数进行判断和处理
	if args.query:
		query_str = args.query
		fofa_client = Fofa_Client(query_str)
		res = fofa_client.get_search_data()

	#批量get_search_data
	if args.file:
		query_list = read_file(args.file)

		data_list = []

		#读取每行进行处理
		leng_query_list = len(query_list)
		for i in range(leng_query_list):
			query_str = query_list[i].strip()
			print(f"正在使用fofa进行查询 {query_str},目前查询到第{i}个参数，总共需查询{leng_query_list}个参数")

			#使用客户端获取数据
			fofa_client = Fofa_Client(query_str)
			res = fofa_client.get_search_data()
			# print(f'测试,{res}')

			#列表数据相加
			res_list = res['results']
			data_list = data_list + res_list

		# print(data_list)
			# print(res)
		#将数据合并写入文件中
		file_deal = File_write(data_list)
		file_deal.search_write_file()

	#批量get_host_data
	if args.bat_host_query:
		query_list = read_file(args.bat_host_query)

		data_list = []
		#读取每行进行处理

		leng_host_query_list = len(query_list)
		for i in range(leng_host_query_list):
			host_query_str = query_list[i].strip()

			print(f"正在使用fofa host聚合接口进行查询 {host_query_str},目前查询到第{i}个参数，总共需查询{leng_host_query_list}个参数")

			fofa_client = Fofa_Client(host_query_str)
			res = fofa_client.get_host_data()
			try:
				row_list = []
				#数据重新组装
				row_list.append(res['host'])
				row_list.append(res['ip'])
				row_list.append(res['country_name'])
				row_list.append(res['country_code'])

				#循环访问port端口的数据
				for port in res['ports']:
					temp_row_list = []
					temp_row_list = list(row_list)
					# print(row_list)

					#添加port字段
					temp_row_list.append(port['port'])
					temp_row_list.append(port['protocol'])

					#添加url
					if 'http' in port['protocol'] or 'https' in port['protocol']:
						url = port['protocol'] + "://" + res['ip'] + ":" + str(port['port'])
						temp_row_list.append(url)
					else:
						temp_row_list.append(None)

					#判断port字典中是否有products键值,暂时不需要写入
					# if 'products' in port:
					# 	temp_row_list.append(port['products'])
					# else:
					# 	temp_row_list.append(None)
						
					data_list.append(temp_row_list)
			except Exception as e:
				print(e)

		#调用host写入函数进行写入
		file_write = File_write(data_list)
		file_write.host_write_file()


if __name__ == "__main__":
	output_result()
	
	# fofa_client = Fofa_Client("8.131.50.94")
	# res = fofa_client.get_host_data()
	# print(res)

	

	# data_list = res['results']
	# file_write = File_write(data_list)

	# file_write.host_write_file()
