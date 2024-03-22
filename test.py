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
import xlsxwriter
import argparse
import time

import re
import math

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
			res = requests.get(url=url, headers=self.headers, proxies=self.proxy, timeout=30, verify=False)
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
		param = {"key": self.key,}

		res = self.__http_get(api_full_url, param)
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
class File_Deal(object):

	def __init__(self,data=""):

		#读取要写入的字段
		config = configparser.ConfigParser()
		config.read('fofa.ini', encoding='utf-8')

		#search写入读取的头文件
		self.fields = config.get('fields', 'fields')

		#输出文件
		now = datetime.datetime.now()
		now_str = now.strftime('%Y%m%d_%H%M%S')
		self.write_filename = f'{now_str}.xlsx'

		#需要处理的数据
		self.data = data

		#host写入读取的头文件
		self.host_headers_list = ['ip','port', 'protocol', 'country', 'host', 'domain', 'icp', 'title']
	
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

		#初始化一个excel表
		workbook = xlsxwriter.Workbook(self.write_filename)
		worksheet = workbook.add_worksheet()
		
		#定义列表头
		host_headers_list = self.host_headers_list
		
		#添加合成字段url
		host_headers_list.insert(5, 'url')
		worksheet.write_row('A1', host_headers_list)

		#打印fofa返回的数据
		# print(self.data)

		#待处理的数据
		print(data)
		data = self.data
		for line in range(len(data)):
			data_list = data[line]

			#添加合成数据url
			if "http://" in data_list[4] or "https://" in data_list[4]:
				url = data_list[4]
			elif "http" in data_list[2] or "https://" in data_list[2]:
				url = data_list[2] + "://" + data_list[4]
			else:
				url = None
			data_list.insert(5, url)

			#写入数据
			worksheet.write_row(f'A{line + 2}', data_list)

		workbook.close()

#文件读取
def read_file(file_name):

	try:
	#读取文件
		with open(file_name, "r+", encoding="utf-8") as file:
			lines = file.readlines()
			return lines
	except Exception as e:
		return f"请输入正确的文件，{e}"

#启动函数
def start():
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
		for line in query_list:
			host_query_str = line.strip()

			#使用客户端获取数据
			fofa_client = Fofa_Client(host_query_str)
			res = fofa_client.get_search_data()

			#列表数据相加
			res_list = res['results']
			data_list = data_list + res_list

		print(data_list)
			# print(res)
		#将数据合并写入文件中
		file_deal = File_Deal(data_list)
		file_deal.host_write_file()

	#批量get_host_data
	if args.bat_host_query:
		query_list = read_file(args.bat_host_query)

		data_list = []
		for line in query_list:
			
			#批量host
			host_query_str = line.strip()
			fofa_client = Fofa_Client(host_query_str)
			res = fofa_client.get_host_data()
			time.sleep(1.5)

			# print(res)
			file_deal = File_Deal(res)
			file_deal.host_write_file()


if __name__ == "__main__":
	start()
	


	#fofa模块调用
	# fofa_client = Fofa_Client("8.131.50.94")
	# res = fofa_client.get_search_data()

	#文件读写类调用
	# file_deal = File_Deal(res)
	# file_deal.host_write_file()

