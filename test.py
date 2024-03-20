#! /usr/bin/python
# -*- coding: UTF-8 -*-

import configparser
import requests
import traceback
import urllib
import urllib3
import base64
import json
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

#文件读写类
class File_Deal(object):
	def __init__(self):
		self.read_filename = 'urls.txt'
		self.write_filename = 'output.xlsx'


	def read_file(self):
		with open(self.read_filename, "r+", encoding='utf-8') as file:
			lines = file.readlines()
		return lines
	
	def write_file(self):
		pass



if __name__ == "__main__":

	#fofa客户端类测试
	# fofa_client = Fofa_Client("shiro")
	# res = fofa_client.get_search_data()
	# print(res)

	#文件读写类测试
	file_deal = File_Deal()
	lines = file_deal.read_file()
	print(lines)
