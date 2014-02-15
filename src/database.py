#!/usr/bin/python
"""
database management for 2ch bbs.
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
import os
import sqlite3

import static

class Database(object):
	"""
	sqlite3 database class for 2ch bbs.
	"""

	def __init__(self,database_path='db'):
		""" Init database.
		Argumenuts:
			database_path -- sqlite3 database file path
		"""
		self.path = database_path
		database_exists = os.path.exists(database_path)
		self.__database = sqlite3.connect(database_path)
		self.__cursor = self.__database.cursor()
		if not database_exists:
			sql_boards = """
				CREATE TABLE IF NOT EXISTS
				boards
				(
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					url,
					category TEXT,
					title TEXT,
					is_open INTEGER,
					favorite INTEGER,
					last_acquired INTEGER
				);
			"""
			self.__cursor.execute(sql_boards)
			sql_threads = """
				CREATE TABLE IF NOT EXISTS
				threads
				(	id INTEGER PRIMARY KEY AUTOINCREMENT,
					board_id INTEGER,
					dat TEXT,
					title TEXT,
					rank	INTEGER,
					total INTEGER,
					acquired INTEGER,
					last_read INTEGER,
					is_open INTEGER,
					favorite INTEGER,
					range_bytes INTEGER,
					last_modified TEXT,
					last_acquired INTEGER,
					scroll_position INTEGER
				);
			"""
			self.__cursor.execute(sql_threads)
			sql_thread_board_id_index = """
				CREATE INDEX board_id_index ON threads
				(board_id);"""
			self.__cursor.execute(sql_thread_board_id_index)
			sql_responses = """
				CREATE TABLE IF NOT EXISTS
				responses
				(
					thread_id_res TEXT PRIMARY KEY,
					thread_id INTEGER,
					res_number INTEGER,
					favorite INTEGER,
					name TEXT,
					mail TEXT,
					date_id TEXT,
					message TEXT);
			"""
			self.__cursor.execute(sql_responses)
			sql_responses_thread_id_index = """
				CREATE INDEX thread_id_index ON responses
				(thread_id);"""
			self.__cursor.execute(sql_responses_thread_id_index)
			self.__database.commit()

	def change_board_url(self,board_id,current_url):
		"""Change previous board url to given url.
		
		Arguments:
			current_url -- current board url
		"""
		board_info = self.get_board(board_id)
		sql_update_url = """
			UPDATE boards
			set url=?
			where id=?
		"""
		self.__cursor.execute(sql_update_url,(current_url,board_id))
		self.__database.commit()

	def update_boards(self,board_list):
		"""Update board list of 2ch bbs menu.

		Arguments:
			board_list -- list object which came back from browse.Browser.menu()
		"""
		sql_insert_boards = """
			INSERT OR REPLACE INTO boards(url,category,title,is_open,favorite,last_acquired)
			VALUES(?,?,?,0,0,0)
		"""
		sql_update_boards = """
			UPDATE boards
			set url=?,category=?,title=?
			where id=?
		"""
	
		menu = self.get_boards()
		for category,url,title in board_list:
			for i in menu:
				if i['url'] == url or i['title'] == title:
					self.__cursor.execute(sql_update_boards,
						(url,category,title,i['id']))
					break
			else:
				self.__cursor.execute(sql_insert_boards,(url,category,title))
		self.__database.commit()
		
	def get_boards(self):
		sql = """
			SELECT * from boards;
		"""
		self.__cursor.execute(sql)
		return self.__get_board_info_list()

	def __get_board_info_list(self):	
		menu = [
				dict(
					id=id,
					url=url,
					category=category,
					title=title,
					is_open=not is_open==0,
					favorite=not favorite==0,
					last_acquired=last_acquired
					)
				for id,url,category,title,is_open,favorite,last_acquired in self.__cursor
			]
		return menu

	def update_board(self,id,is_open=None,favorite=None,last_acquired=None):
		"""Update board information.

		Arguments:
			id -- board id.
			is_open -- if True, set is_open=True. if False, set is_open=False. if None, do nothing
			favorite -- if True, set favorite=True. if False, set favorite=False. if None, do nothing
		"""
		sql_open = """
			UPDATE boards
			set is_open=?
			where id=?
		"""
		sql_favorite = """
			UPDATE boards
			set favorite=?
			where id=?
		"""
		sql_last_acquired = """
			UPDATE boards
			set last_acquired=?
			where id=?
		"""
	
		if not is_open == None:
			if is_open:
				is_open = 1
			else:
				is_open = 0
			self.__cursor.execute(sql_open,(is_open,id))
		if not favorite == None:
			if favorite:
				favorite = 1
			else:
				favorite = 0
			self.__cursor.execute(sql_favorite,(favorite,id))
		if not last_acquired == None:
			self.__cursor.execute(sql_last_acquired,(last_acquired,id))
		if not is_open == None or \
				not favorite == None or \
				not last_acquired == None:
			self.__database.commit()	


	def get_board(self,id):
		"""Get board information.
		
		Arguments:
			id -- board id.
		"""
		sql = "SELECT * from boards WHERE id=?"
		self.__cursor.execute(sql,(id,))
		for id,url,category,title,is_open,favorite,last_acquired in self.__cursor:
			is_open = True if not is_open == 0 else False
			favorite = True if not favorite == 0 else False
			return dict(id=id,url=url,category=category,title=title,is_open=is_open,favorite=favorite,last_acquired=last_acquired)
			
	#thread list functions.

	def remove_old_threads(self):
		sql = """
			DELETE FROM threads
			WHERE is_open=0 and favorite=0 and rank=? and acquired=0;
			"""
		self.__cursor.execute(sql,(static.MISSING_DAT_RANK,))
		self.__database.commit()

	def update_threads(self,board_id,thread_list):
		"""Update thread list of given board id.
	
		Arguments:
			board_id -- board id.
		"""
		sql_insert = """
			INSERT OR REPLACE INTO
			threads(board_id,dat,title,rank,total,acquired,
			last_read,is_open,favorite,range_bytes,last_modified,
			last_acquired,scroll_position)
			VALUES(?,?,?,?,?,0,
			0,0,0,-1,-1,
			-1,0)
		"""
		sql_update = """
			UPDATE threads
			set total=?,rank=?
			where id=?
		"""
		sql_rank_reset = """
			UPDATE threads
			set rank=? 
			WHERE board_id=?
		"""
		threads = self.get_threads(board_id)
		self.__cursor.execute(sql_rank_reset,(static.MISSING_DAT_RANK,board_id))
		for index,(dat,title,total) in enumerate(thread_list):
			rank = index + 1
			for i in threads:
				if str(i['dat']) == str(dat):
					self.__cursor.execute(sql_update,(total,rank,i['id']))
					break
			else:
				self.__cursor.execute(sql_insert,(board_id,dat,title,rank,total))
		self.__database.commit()

	def get_threads(self,board_id):

		sql_url = '''SELECT * from threads 
				WHERE board_id=? and (rank<? or favorite>0 or is_open>0)
				ORDER BY rank ASC;'''
		self.__cursor.execute(sql_url,(board_id,static.MISSING_DAT_RANK))
		return self.__get_thread_info_list()

	def get_threads_full(self,board_id):

		sql_url = '''SELECT * from threads 
				WHERE board_id=?
				ORDER BY rank ASC;'''
		self.__cursor.execute(sql_url,(board_id,))
		return self.__get_thread_info_list()


	def __get_thread_info_list(self):
		"""Generates response list from sqlite queried cursor.
		"""
		threads = [
				dict(
						id=id,
						board_id=board_id,
						dat=dat,
						title=title,
						rank=rank,
						total=total,
						acquired=acquired,
						last_read=last_read,
						is_open=not is_open==0,
						favorite=not favorite==0,
						range_bytes=range_bytes,
						last_modified=last_modified,
						last_acquired=last_acquired,
						scroll_position=scroll_position
					)
				for id,board_id,dat,title,rank,total,acquired,last_read,is_open,favorite,range_bytes,last_modified,last_acquired,scroll_position in self.__cursor
				]
		return threads

	def __get_response_info_list(self):
		responses = [
			dict(
				number=res_number,
				favorite=favorite,
				name=name,
				mail=mail,
				date_id=date_id,
				message=message
				)
			for k,thread_id,res_number,favorite,name,mail,date_id,message in self.__cursor
				]
		return responses



	def get_custom_boards(self,where):
		sql = "SELECT * from boards WHERE %s" % where
		self.__cursor.execute(sql,())
		return self.__get_board_info_list()

	def get_custom_threads(self,where):
		sql = "SELECT * from threads WHERE %s" % where
		self.__cursor.execute(sql,())
		return self.__get_thread_info_list()

	def get_custom_responses(self, where):
		sql = "SELECT * from responses WHERE %s" % where
		self.__cursor.execute(sql,())
		return self.__get_response_info_list()

	#thread functions.

	def set_thread_info(self,id,rank=None,is_open=None,last_read=None,
			favorite=None,last_acquired=None):
		""" Sets thread properties.
		"""
		sql_update_thread = """
			UPDATE threads
			set rank=?
			where id=?
		"""
		if rank:
			self.__cursor.execute(sql_update_thread,(rank,id))

		sql_update_thread = """
			UPDATE threads
			set is_open=?
			where id=?
		"""
		if not is_open is None:
			if is_open:
				is_open = 1
			else:
				is_open = 0
			self.__cursor.execute(sql_update_thread,(is_open,id))

		sql_update_thread = """
			UPDATE threads
			set last_read=?
			where id=?
		"""
		if last_read:
			self.__cursor.execute(sql_update_thread,(last_read,id))
		sql_update_thread = """
			UPDATE threads
			set last_acquired=?
			where id=?
		"""
		if last_acquired:
			self.__cursor.execute(sql_update_thread,(last_acquired,id))
		
		sql_update_thread = """
			UPDATE threads
			set favorite=?
			where id=?
		"""
		if not favorite is None:
			if favorite:
				favorite = 1
			else:
				favorite = 0
			self.__cursor.execute(sql_update_thread,(favorite,id))
	
		self.__database.commit()
		
	


		pass
	def get_thread_info(self,id):
		""" Returns thread properties.
		"""
		sql = """
			SELECT * FROM threads
			JOIN boards 
			ON threads.board_id=boards.id 
			WHERE threads.id=?;
		"""
		self.__cursor.execute(sql,(id,))
	

	
		for  id,board_id,dat,title,rank,total,acquired,last_read,is_open,favorite,range_bytes,last_modified,last_acquired,scroll_position,  b,board_url,board_category,board_title,board_open,board_favorite,board_last_acquired in self.__cursor:
			if is_open == 0:
				is_open = False
			else:
				is_open = True
			if favorite == 0:
				favorite = False
			else:
				favorite = True
			if range_bytes == -1:
				range_bytes = 0
			if last_modified == '-1':
				last_modified = u''
			if last_acquired == '-1':
				last_acquired = u''
	
			return dict(
					id=id,
					board_id=board_id,
					dat=dat,
					title=title,
					rank=rank,
					total=total,
					acquired=acquired,
					last_read=last_read,
					is_open=is_open,
					favorite=favorite,
					range_bytes=range_bytes,
					last_modified=last_modified,
					last_acquired=last_acquired,
					board_url=board_url)

	#responses functions.
	
	def update_responses(self,thread_id,range_bytes,last_modified,responses):
		""" Inserts or updates responses of thread.

		Arguments:
			thread_id
			responses -- list object which came from browse.Browser.thread()['response_list']
		"""
		sql_update_thread = """
			UPDATE threads
			set range_bytes=?,last_modified=?,total=?,acquired=?
			where id=?
		"""
		self.__cursor.execute(sql_update_thread,
				(range_bytes,last_modified,
				len(responses),len(responses),
				thread_id))

		sql_insert = """
			INSERT OR REPLACE INTO
			responses(thread_id_res,thread_id,res_number,favorite,name,mail,date_id,message)
			VALUES(?,?,?,0,?,?,?,?)
		"""
		for index,(name,mail,date_id,message) in enumerate(responses):
			thread_id_res = unicode(thread_id)+u'/'+unicode(index+1)
			self.__cursor.execute(sql_insert,(thread_id_res,int(thread_id),
				index+1,name,mail,date_id,message))
		self.__database.commit()

	def add_responses(self,thread_id,range_bytes,last_modified,responses):
		""" Adds responses of thread.

		"""
		info = self.get_thread_info(thread_id)
		if len(responses) == 0:
			return
		sql_update_thread = """
			UPDATE threads
			set range_bytes=?,last_modified=?,acquired=?,total=?
			where id=?
		"""
		acquired = len(responses)+info['acquired']
		self.__cursor.execute(sql_update_thread,(info['range_bytes']+int(range_bytes),last_modified,acquired,acquired,thread_id))

		sql_insert = """
			INSERT OR REPLACE INTO 
			responses(thread_id_res,thread_id,res_number,favorite,name,mail,date_id,message)
			VALUES(?,?,?,0,?,?,?,?)
		"""
		for index,(name,mail,date_id,message) in enumerate(responses):
			rank = index+1+info['acquired']
			thread_id_res = unicode(thread_id)+u'/'+unicode(rank)
			self.__cursor.execute(sql_insert,(thread_id_res,int(thread_id),
				rank,name,mail,date_id,message))
		self.__database.commit()

	


	def get_responses(self,thread_id,number=None):
		if not number == None:
			sql = """
				SELECT * FROM responses WHERE thread_id=? and res_number=?
			"""
			self.__cursor.execute(sql,(thread_id,number+1))
			for k,thread_id,res_number,favorite,name,mail,date_id,message in self.__cursor:
				return 	dict(
					number=res_number,
					favorite=favorite,
					name=name,
					mail=mail,
					date_id=date_id,
					message=message
					)
			
	
		sql = """
			SELECT * FROM responses WHERE thread_id=?
		"""
		self.__cursor.execute(sql,(thread_id,))
		responses = [
			dict(
				number=res_number,
				favorite=favorite,
				name=name,
				mail=mail,
				date_id=date_id,
				message=message
				)
			for k,thread_id,res_number,favorite,name,mail,date_id,message in self.__cursor
				]
		return responses

	def close(self):
		self.__database.close()

	def __del__(self):
		try:
			self.close()
		except:
			pass

