import configparser
import base64
import json
import urllib
import urllib.request
import urllib.parse
import ssl
import requests
from colorama import Fore
from prettytable import PrettyTable
import time
import csv
import datetime
import urllib3
import re
from flask import Flask, render_template, request
import argparse
import openpyxl
from openpyxl.styles import Font
import math
import random

#忽略系统代理
requests = requests.Session()
requests.trust_env = False

#解决报错
urllib3.disable_warnings()

class Client:
	def __init__(self):
		config = configparser.ConfigParser()
		config.read('fofa.ini', encoding="utf-8")
		self.email = config.get("userinfo", "email")
		self.key = config.get("userinfo", "key")
		self.size = config.get("size", "size")
		self.full = config.get("full", "full")
		self.base_url = "https://fofa.so"
		self.base_url = "https://fofa.info"
		self.search_api_url = "/api/v1/search/all"
		self.login_api_url = "/api/v1/info/my"
		self.get_userinfo()  # check email and key

	def get_userinfo(self):
		api_full_url = "%s%s" % (self.base_url, self.login_api_url)
		param = {"email": self.email, "key": self.key}
		res = self.__http_get(api_full_url, param)
		return json.loads(res)

	def get_data(self, query_str, page=1, fields=""):
		res = self.get_json_data(query_str, page, fields)
		return json.loads(res)

	def get_json_data(self, query_str, page=1, fields=""):
		api_full_url = "%s%s" % (self.base_url, self.search_api_url)
		param = {"qbase64": base64.b64encode(bytes(query_str.encode('utf-8'))), "email": self.email, "key": self.key,
				 "page": page,
				 "fields": fields,
				 "size": self.size,
				 "full": self.full}
		res = self.__http_get(api_full_url, param)
		return res

	def __http_get(self, url, param):
		ssl._create_default_https_context = ssl._create_unverified_context
		param = urllib.parse.urlencode(param)
		url = "%s?%s" % (url, param)
		try:
			req = urllib.request.Request(url)
			res = urllib.request.urlopen(req).read().decode('utf-8')
			if "errmsg" in res:
				raise RuntimeError(res)
		except Exception as e:
			raise e
		return res

#域名查询
def host_merge(query_host,email, key):
	# try:
	items = []
	url = f"https://fofa.info/api/v1/host/{query_host}?detail=true&email={email}&key={key}"
	res = requests.get(url, timeout=30)
	time.sleep(1.5)
	data = res.json()
	for port in data['ports']:
		temps_1 = []
		if port['protocol'] == "http" or port['protocol'] == "https":
			url = f"%s://%s:%s" % (port['protocol'], data['ip'], port['port'])
			temps_1.append(data['ip'])
			temps_1.append(port['port'])
			temps_1.append(port['protocol'])
			temps_1.append(url)
			print(data['ip'], port['port'], port['protocol'], url)
		else:
			print(data['ip'], port['port'], port['protocol'], None)
			temps_1.append(data['ip'])
			temps_1.append(port['port'])
			temps_1.append(port['protocol'])
			temps_1.append(None)
		items.append(temps_1)
	return items

	# except Exception as e:
	# 	print(f"[!]错误:{e}")

#读取文件
def read_file(file_path):
	with open(file_path, "r", encoding="utf-8") as f:
		line = f.readlines()
		return line

#数据处理
def data_handle(hosts):
	all_items = []
	for host in hosts:
		host = host.strip()
		items = host_merge(host, client.email, client.key)
		all_items.append(items)
	return all_items

#读取完毕并写入文件
def writer_file(file_path, all_items):
	today = datetime.datetime.now()
	today = today.strftime('%Y%m%d%H%M%S')
	with open(f'{today}.csv', 'w', newline='') as f:
		writer = csv.writer(f)
		writer.writerow(['ip', 'port', 'protocol', 'url'])
		for data in all_items:
			print(data)
			for temp_list in data:
				writer.writerow(temp_list)

#单个页面字符串查询
def query(query_str, key, page=1):
	base64_query_str = base64.b64encode(bytes(query_str.encode('utf-8'))).decode('utf-8')
	try:
		url_full = f"https://fofa.info/api/v1/search/all?&key={key}&qbase64={base64_query_str}&fields=ip,host,port,protocol,link,title,icp&page={page}&size=10000&full=true"
		res = requests.get(url=url_full, verify=False, timeout=3)
		# print(res.text)
		result_data = json_data_deal(res.text)

		leng = math.ceil(result_data['size'] / 10000)
		if leng > 1:
			multi_page_query(query_str, key, leng)
				 
		return result_data['results']
	except Exception as e:
		print(e)

#多个页面字符串查询
def multi_page_query(query_str, key, size):
	base64_query_str = base64.b64encode(bytes(query_str.encode('utf-8'))).decode('utf-8')
	for page in range(size):
		try:
			url_full = f"https://fofa.info/api/v1/search/all?&key={key}&qbase64={base64_query_str}&fields=ip,host,port,protocol,link,title,icp&page={page}&size=10000&full=true"
			print(url_full)
			res = requests.get(url=url_full, verify=False, timeout=3)
			result_data = json_data_deal(res.text)
			print(f'现在正在读取第几页{page}', result_data['results'])
			time.sleep(1.5)
		except Exception as e:
			print(f"在读取第{page}页时出错,{e}")

def write_excel(query_str, key):
	result_data = query(query_str, key)

	#创建新的工作簿
	workbook = openpyxl.Workbook()
	sheet = workbook.active

	#创建一个font对象，设置第一行加粗
	bold_font = Font(bold=True)
	

	#写入表头
	row_index = ['ip', 'host', 'port', 'protocol', 'link', 'title' ,'icp']
	#添加数据
	sheet.append(row_index)
	try:
		for row in result_data:
			sheet.append(row)
	except TypeError as e:
		print(f"未获取到fofa数据进行写入 {e}")
	try:
		workbook.save('output.xlsx')
	except PermissionError as e:
		print(f"请检查是否excel表已打开，{e}")

#查询到多行数据处理
def multi_data_deal(query_str, key):
	size = 6
	if size > 1:
		for page in random(size):
			query(query_str, key, page=page)



#处理单个查询fofa返回的数据
def json_data_deal(res):
	try:
		res = res.strip()
		dict_data = json.loads(res)
		return dict_data
	except json.JSONDecodeError as e:
		print(f"返回的json数据解析错误:{e}")

#命令行解析
def parser():
	data_line = []
	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-q', "--query", help = "python fofa -q body='qihang'")
	group.add_argument('-l', "--file", help = "python fofa.py -l urls.txt")
	args = parser.parse_args()


	if args.query:
		query_string = args.query
		data_line.append(query_string)
		# print(data_line)
		return data_line
	elif args.file: 
		query_file = args.file
		try:
			with open(query_file, "r", encoding="utf-8") as file:
				for line in file:
					query_line = line.strip()
					data_line.append(query_line)
				# print(data_line)
				return data_line
		except Exception as e:
			print("请检查输入的文件名是否正确")

#批量查询，未完成
def query_fofa(key):
	data_line = parser()
	if len(data_line) == 1:
		query(data_line[0], key)		

#对输入字符串匹配, 未完成
def deal_with_input(input_data):
	domain_pattern = "[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+\.?"
	key = re.search(domain_pattern, input_data)
	# database = 

if __name__ == '__main__':

	#初始化fofa客户端
	client = Client()
	query_str = parser()
	# print(query_str)
	# write_excel(query_str[0], client.key)


	#单个IP查询数据处理
	res = query(query_str[0], client.key)
	
	#读取需要处理的数据
	# hosts = read_file('ten.txt')

	#查询汇总fofa的数据
	# all_items = data_handle(hosts)

	#将查询汇总的数据写入csv表格中
	# writer_file('example.csv', all_items)
	


		