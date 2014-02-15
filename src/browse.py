#!/usr/bin/python
"""
a primitive module for browsing 2ch bbs.
Copyright (c) 2011-2013 mei raka
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL mei raka BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import re
import socket
import StringIO
import time
import urllib
import gzip

import version

WRITE_SUCCESS = 0
WRITE_WARNING = 1
WRITE_FAIL = 2
WRITE_STOP = 3
WRITE_CONFIRM = 4


class Error(Exception):
	pass

class ConnectionError(Error):
	def __init__(self,request,message):
		self.request = request
		self.message = message

	def __str__(self):
		return repr(self.message)

class ReceiveError(Error):
	def __init__(self,request,message):
		self.request = request
		self.message = message

	def __str__(self):
		return repr(self.message)

class DecodeError(Error):
	pass
class UnknownError(Error):
	pass

class Browser(object):
	def __init__(self):
		self.default_name = 'bbs2ch '+ str(version.__VERSION__)
		self.__re_http_url = re.compile('http://(.+)')

	def __split_url(self,url):
		http_url = self.__re_http_url.match(url)
		if http_url:
			url = http_url.groups()[0]
		host,path = url.split('/',1)
		path = '/'+path
		return (host,path)

	def __generate_headers(self,add_headers=None):
		headers = [
			('Accept-Language','ja'),
			('User-Agent','Monazilla/1.00 (python-bbs2ch/%s)' % version.__VERSION__),
			('Connection','close')
			]
		if add_headers:
			headers = add_headers + headers
		string = ''
		for key,value in headers:
			string = string + key + ': ' + value + '\r\n'
		return string[:-1]

	def __generate_request(self,uri,method='GET'):
		return method+ ' ' + str(uri) + ' HTTP/1.1'

	def __http_connection(self,host,request_headers,request_body='',range_bytes='',encode='ms932',callback=None):
		try:
			if callback:
				callback_ = callback
				callback = lambda *args,**kwargs:callback_(host+'\r\n'+request_headers+'\r\n\r\n'+request_body+'\r\n',*args,**kwargs)
			connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			connection.settimeout(20.0)
			if callback:
				callback('connect',0,0)
			connection.connect((host, 80))
			if callback:
				callback('request',0,0)
			connection.send(request_headers+'\r\n\r\n'+request_body+'\r\n')
			#connection.shutdown(1)
			response = self.__get_response(connection,callback)
			connection.close()
			if callback:
				callback('close',1,1)
			try:

				if callback:
					callback('decode',0,0)
				decoded_response = self.__decode_response(response,range_bytes=range_bytes,encode=encode)

				if callback:
					callback('decode',1,1)
					callback('finish',1,1)
				return decoded_response
			except ValueError,err:
				if callback:
					callback('error',1,1)
				raise DecodeError()
		except socket.gaierror,err:
			errno,error = err
			request = request_headers+'\r\n\r\n'+request_body
			if callback:
				callback('error',1,1)
			raise ConnectionError(request,error)
		except socket.timeout,err:
			request = request_headers+'\r\n\r\n'+request_body
			if callback:
				callback('error',1,1)
			raise ConnectionError(request,err)
			

	def __get_response(self,connection,callback=None):
		response = ''
		count = 0
		recv_total = 0
		total_size = 0
		header_size = 0
		while True:
			data = connection.recv(2048)
			if not data:
				count = count + 1
			else:
				recv_total = recv_total + len(data)
			if count > 3:
				break
			response = response + data
			if callback and not total_size:
				total = self.__get_size(response)
				if total:
					header_size,total_size = total
					callback('recv',recv_total,total_size+header_size+4)
				else:
					callback('recv',recv_total,0)
			elif callback:
				callback('recv',recv_total,total_size+header_size+4)
		return response

	def __get_size(self,response):
		splitted = response.split('\r\n\r\n',1)
		if len(splitted) == 2:
			headers,body = splitted
			for header in headers.split('\n'):
				splitted = header.split(':',1)
				if len(splitted) == 2:
					field,value = splitted
					field = field.lower()
					if field == 'content-length':
						return (len(headers) ,  int(value.strip()))
		return None

	def __decode_response(self,response,range_bytes='',encode='ms932'):
		headers,body = response.split('\r\n\r\n',1)
		headers = headers.decode(encode)
		headers = headers.replace('\r','')
		front = ''
		for header in headers.split(u'\n'):
			header = header.strip()
			if header == u'Content-Encoding: gzip':
				body,length = self.__decode_gzip(body)
				break
		else:
			if range_bytes:
				try:
					front = body[0]
					body = body[1:]
				except:
					pass
			length = len(body)
			body = body.decode(encode,errors='replace')
		if range_bytes:
			return (headers,body,length,front)
		else:
			return (headers,body,length)

	def __decode_gzip(self,archive):
		io = StringIO.StringIO(archive)
		f = gzip.GzipFile(fileobj=io)
		string = f.read()
		return (string.decode('ms932',errors='replace'),len(string))

	def get_new_board_url(self,board_url):
		host,uri = self.__split_url(board_url)
		request = self.__generate_request(uri)
		add_headers = [
			('Host',host),
			('Accept','*/*'),
			('Referer',host),
			('Accept-Encoding','gzip'),
			]
		request_headers = self.__generate_headers(add_headers)
		response_headers,response_body,length = self.__http_connection(
				host,request+'\r\n'+request_headers)
		url = re.compile(u'window.location.href="(http://[^/]+/[^/]+/)"</script>')
		for line in response_body.split(u'\n'):
			match = url.search(line)
			if match:
				return match.groups()[0]
		return u''
		


	def menu(self,menu_url=u'http://menu.2ch.net/bbsmenu.html',status_callback=None):
		"""Get board list."""
		#split menu_url to host and url
		host,uri = self.__split_url(menu_url)
		request = self.__generate_request(uri)
		add_headers = [
			('Host',host),
			('Accept','*/*'),
			('Referer',host),
			('Accept-Encoding','gzip'),
			]
		request_headers = self.__generate_headers(add_headers)
		response_headers,response_body,length = self.__http_connection(
				host,request+'\r\n'+request_headers,callback=status_callback)
		#Set filter regex for 2ch.net and bbspink.com
		re_category = re.compile(u'<BR><BR><B>([^<]+)</B><BR>')
		re_category2 = re.compile(u'<b>([^<]+)</b>')
		re_2ch_board_url = re.compile(u'<A HREF=(http://[^\\.]+\\.2ch.net/[^/]+/)>([^<]+)<')
		re_pink_board_url = re.compile(u'<A HREF=(http://[^\\.]+\\.bbspink.com/[^/]+/)>([^<]+)<')
		re_another_board_url = re.compile(u'<a href="([^"]+)"[^>]*>([^<]+)<.*')
		menu_list = []
		current_category = u'unknown'
		for line in response_body.split(u'\n'):
			match_category = re_category.match(line)
			match_category2 = re_category2.search(line)
			match_2ch_board_url = re_2ch_board_url.match(line)
			match_pink_board_url = re_pink_board_url.match(line)
			match_another_board_url = re_another_board_url.match(line)
			if match_category:
				current_category = match_category.groups()[0]
			if match_category2:
				current_category = match_category2.groups()[0]

			if match_2ch_board_url:
				url,name = match_2ch_board_url.groups()
				menu_list.append((current_category,url,name))
			if match_pink_board_url:
				url,name = match_pink_board_url.groups()
				menu_list.append((current_category,url,name))
			if match_another_board_url:
				url,name = match_another_board_url.groups()
				menu_list.append((current_category,url,name))
		return menu_list

	def board(self,board_url,status_callback=None):
		subject = board_url + u'subject.txt'
		host,uri = self.__split_url(subject)
		request = self.__generate_request(uri)
		add_headers = [
			('Host',host),
			('Accept','*/*'),
			('Referer',board_url),
			('Accept-Encoding','gzip'),
			]
		request_headers = self.__generate_headers(add_headers)
		try:
			response_headers,response_body,length = self.__http_connection(
					host,
				request+'\r\n'+request_headers,
				callback=status_callback)
		except IOError:
			time.sleep(2)
			add_headers = [
				('Host',host),
				('Accept','*/*'),
				('Referer',board_url),
				]
			request_headers = self.__generate_headers(add_headers)
			response_headers,response_body,length = self.__http_connection(
					host,
					request+'\r\n'+request_headers,
					callback=status_callback)
			

		re_threads = re.compile(u'(\\d+).dat<>(.+)\s\\((\\d+)\\)')
		thread_list = []
		for line in response_body.split(u'\n'):
			match_threads = re_threads.match(line)
			if match_threads:
				thread_list.append(match_threads.groups())
		http,response_status,response_reason = response_headers.split('\n')[0].split(' ',2)
		return dict(	request_headers=request+'\n'+request_headers,
				request_body=u'',
				response_headers=response_headers,
				response_body=response_body,
				response_status=response_status,
				response_reason=response_reason,
				thread_list=thread_list)

	def get_be_id(self,benum):
		benum = int(benum)
		beid = ((benum/100) + ((benum/10) % 10) - (benum % 10) - 5) / (((benum/10) % 10) * (benum % 10) * 3)
		return str(beid)
		'''
		be_url = 'http://be.2ch.net/test/p.php?i='+be_id+'&u=d:'+thread_url
		host,uri = self.__split_url(be_url)
		request = self.__generate_request(uri)
		add_headers = [
			('Host',host),
			('Accept','*/*'),
			('Referer',thread_url),
			]
		request_headers = self.__generate_headers(add_headers)
		response_headers,response_body,length = self.__http_connection(
				host,
				request+'\r\n'+request_headers,encode='euc-jp')
		print response_headers
		print response_body
		'''


	def thread(self,board_url,dat_id,modified_and_range=None,status_callback=None):
		"""Get 2ch bbs thread response data.

		Arguments:
			board_url -- string board url
			dat_id -- string dat number
			modified_and_range -- tuppled string last modified date
				and string range bytes

		Returns:
			dict object
				request_headers -- string request headers
				request_body -- string request body
				response_headers -- unicode response headers
				response_body -- unicode response body
				response_status -- unicode response status code
				response_reason -- unicode response reason
				thread_title -- unicode thread title
				range_bytes -- unicode body size
				last_modified -- unicode last modified date
				response_list -- list includes user responses

		Example:
			#Get thread from 'http://hibari.2ch.net/software/'
			# '1314425987'.
			browser = browse.Browser()
			ret = browser.thread('http://hibari.2ch.net/software/'
					,'1314425987')

			#and print thread data.
			for index,name,mail,date_id,message in enumerate(ret['response_list']):
				print index,
				print name, mail, date_id
				print message

			#then, reload thread.
			mod_and_range = (ret['last_modified']
					,ret['range_bytes'])
			ret = p2ch.thread('http://hibari.2ch.net/software/'
					,'1314425987',mod_and_range)

			#if it was not modified, return 304
			ret['response_status']		#Returns 304
			#if some responses removed, return 416,
			#you must reload all data.
			ret['response_status']		#Returns 416
			ret = p2ch.thread('http://hibari.2ch.net/software/'
					,'1314425987')
			#if new responses found, return 206
			ret['response_status']		#Returns 206
		"""
		board_name = self.__split_url(board_url)[1]
		dat_url = board_url + u'dat/' + dat_id+'.dat'
		host,uri = self.__split_url(dat_url)
		request = self.__generate_request(uri)
		add_headers = [
			('Host',host),
			('Accept','*/*'),
			('Referer','http://'+host+'/test/read.cgi'+board_name+dat_id+'/'),
			('Accept-Encoding','gzip')
			]
		if modified_and_range:
			del add_headers[-1]
			modified,range_bytes = modified_and_range
			add_headers.append(('If-Modified-Since',modified))
			add_headers.append(('Range','bytes='+str(range_bytes-1)+'-'))
		request_headers = self.__generate_headers(add_headers)
		front = ''
		try:
			if modified_and_range:
				response_headers,response_body,length,front = self.__http_connection(
					host,request+'\r\n'+request_headers,range_bytes=modified_and_range,callback=status_callback)
			else:
				response_headers,response_body,length = self.__http_connection(
					host,request+'\r\n'+request_headers,callback=status_callback)
		except IOError,err:
			add_headers = [
				('Host',host),
				('Accept','*/*'),
				('Referer','http://'+host+'/test/read.cgi'+board_name+dat_id+'/'),
				]
			if modified_and_range:
				modified,range_bytes = modified_and_range
				add_headers.append(('If-Modified-Since',modified))
				add_headers.append(('Range','bytes='+str(range_bytes-1)+'-'))

			request_headers = self.__generate_headers(add_headers)
			if modified_and_range:
				response_headers,response_body,length,front = self.__http_connection(
					host,request+'\r\n'+request_headers,range_bytes=modified_and_range,callback=status_callback)
			else:
				response_headers,response_body,length = self.__http_connection(
					host,request+'\r\n'+request_headers,callback=status_callback)
		response_list = []
		thread_title = u''
		http,response_status,response_reason = response_headers.split('\n')[0].split(' ',2)
		last_modified = ''
		for line in response_headers.split('\n'):
			splitted = line.split(':',1)
			if splitted[0] == 'Last-Modified':
				last_modified = splitted[1].strip()
				
		
		for line in response_body.split('\n'):
			splitted = line.split(u'<>')
			if len(splitted) == 5:
				name,mail,date_id,message,title = splitted
				if title:
					thread_title = title
				response_list.append((name,mail,date_id,message))
			elif len(splitted) == 6:
				name,mail,date_id,message,deleted,title = splitted
				response_list.append((name,mail,date_id,message))
			elif len(splitted) >= 4:
				name = self.default_name
				mail = ''
				date_id = ''
				message = u'%s can not understand this line:</br>' % self.default_name + line.replace(u'<>',u'&lt;&gt;')
				response_list.append((name,mail,date_id,message))
		return dict(	request_headers=request_headers,
				request_body='',
				front = front,
				response_headers=response_headers,
				response_body=response_body,
				response_status=response_status,
				response_reason=response_reason,
				thread_title=thread_title,
				response_list=response_list,
				range_bytes=unicode(length),
				last_modified=last_modified
				)

	def write(self,board_url,dat_id,FROM,mail,MESSAGE,cookie='',hidden=''):
		host,board_name = self.__split_url(board_url)
		FROM = urllib.quote(FROM.encode('ms932'))
		mail = urllib.quote(mail.encode('ms932'))
		MESSAGE = urllib.quote(MESSAGE.encode('ms932'))
		request_body = 'bbs='+board_name.split('/')[1]+'&key='+dat_id+'&time='+str(time.time()-1000).split('.')[0]+ \
			'&FROM='+FROM+'&mail='+mail+'&MESSAGE='+MESSAGE+'&submit=%8F%91%82%AB%8D%9E%82%DE'
		if hidden:
			request_body = request_body + '&' + hidden

		request = self.__generate_request('/test/bbs.cgi','POST')
		add_headers = [	('Host',host),
				('Accept','*/*'),
				('Referer','http://'+host+'/test/read.cgi'+board_name+dat_id+'/'),
				('Content-Length',str(len(request_body))),
				('Accept-Encoding','gzip'),
				]
		if cookie:
			add_headers.append(('Cookie',cookie))
		request_headers = self.__generate_headers(add_headers)
		response_headers,response_body,length = self.__http_connection(
			host,request+'\r\n'+request_headers,request_body)

		hidden = self.__check_hidden(response_body)
		status = self.__check_status(response_body)

		return dict(	request_headers=request_headers,
				request_body=request_body,
				response_headers=response_headers,
				response_body=response_body,
				hidden=hidden,
				status=status)

	def __check_status(self,body):
		"""Get write status"""
		re_status = re.compile(u'<\\!--\\s2ch_X:([^\\s]+)\\s-->')
		match = re_status.search(body)
		if match:
			status = match.groups()[0]
			if status == u'true':
				return WRITE_SUCCESS
			elif status == u'false':
				return WRITE_WARNING
			elif status == u'error':
				return WRITE_FAIL
			elif status == u'check':
				return WRITE_STOP
			elif status == u'cookie':
				return WRITE_CONFIRM
			else:
				return status
		else:
			return 100

	def __check_hidden(self,body):
		"""Get 'hidden' key and value from html"""
		re_hidden = re.compile(u'input\\stype=hidden\\s+name="([^"]+)"\\svalue="([^"]+)"')
		hidden = None
		for i in body.split(u'<'):
			search = re_hidden.search(i)
			if search:
				hidden =  search.groups()
		if hidden:
			hidden = hidden[0] + u'=' + hidden[1] 
			hidden = hidden.encode('ms932')
		else:
			hidden = ''
		return hidden

