"""
filtering bbs2ch data.
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
import sqlite3
import time
import util

class NoiseBlocker():
    def __init__(self, database_path):
        self.__regex_dict = {}
        self.__database_path = database_path
        self.path = database_path
        self.__regex_id = re.compile(u'ID:([^\\s]+)')
        self.__regex_be = re.compile(u'BE:([^\\-]+)\\-([^\\(]+)\\(([^\\)]+)\\)')
        self.__database = sqlite3.connect(self.__database_path)
        self.__cursor = self.__database.cursor()
        sql = """
            CREATE TABLE IF NOT EXISTS
            noise_response
            (
                noise_type TEXT,
                noise_word TEXT,
                word_type TEXT,
                filter_type TEXT,
                filter_reason TEXT,
                dat TEXT,
                board_url TEXT,
                time INTEGER,
                recursion INTEGER,
                PRIMARY KEY(noise_type, noise_word, filter_type, dat, board_url)
            );
            """
        self.__database.execute(sql)
        sql = """
            CREATE TABLE IF NOT EXISTS
            noise_responses
            (
                thread_name TEXT,
                thread_name_type TEXT,
                response_name TEXT,
                response_name_type TEXT,
                response_mail TEXT,
                response_mail_type TEXT,
                response_message TEXT,
                response_message_type TEXT,
                add_id INTEGER,
                filter_type TEXT,
                filter_reason TEXT,
                dat TEXT,
                board_url TEXT,
                time INTEGER,
                recursion INTEGER,
                PRIMARY KEY(thread_name, response_name, response_mail, response_message, thread_name_type, response_name_type, response_mail_type, response_message_type, dat, board_url)
            );
            """
        self.__database.execute(sql)
    
        self.__database.commit()

    def add_block_rule(self,
            thread_name='', thread_name_type='skip',
            response_name='', response_name_type='skip',
            response_mail='', response_mail_type='skip',
            response_message='', response_message_type='skip',
            filter_type='normal',
            add_id=True, filter_reason='',
            dat='all', board_url='all', time=0, recursion=False):
        """Adds noise blocker rule."""
        sql = """
            INSERT OR REPLACE INTO
            noise_responses (
                thread_name, thread_name_type,
                response_name, response_name_type,
                response_mail, response_mail_type,
                response_message, response_message_type,
                add_id, filter_type, filter_reason,
                dat, board_url, time, recursion)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        database = sqlite3.connect(self.__database_path)
        database.execute(sql, (thread_name, thread_name_type,
                response_name, response_name_type,
                response_mail, response_mail_type,
                response_message, response_message_type,
                add_id, filter_type, filter_reason,
                dat, board_url, time, recursion))
        database.commit()

    def check_thread(self, thread):
        sql = """
            SELECT * from noise_responses
            WHERE (dat=? or dat='all') and (board_url=? or board_url='all')
        """
        database = self.__database
        cursor = self.__cursor
        block_id = []
        t_dat = thread.dat if hasattr(thread, 'dat') else 'all'
        t_board_url = thread.board_url if hasattr(thread, 'board_url') else 'all'
        cursor.execute(sql, (t_dat, t_board_url))
        for        thread_name, thread_name_type, \
                response_name, response_name_type, \
                response_mail, response_mail_type, \
                response_message, response_message_type, \
                add_id, filter_type, filter_reason, \
                dat, board_url, time, recursion in cursor:
            if re.search(thread_name, thread.title):
                id_count = {}
                message = re.compile(response_message).search
                for response in thread:
                    if message(response.message):
                        match = self.__regex_id.search(response.date_id)
                        if match:
                            id = match.groups()[0]
                            if not id_count.has_key(id):
                                id_count[id] = 0
                            id_count[id] = id_count[id] + 1
                block_id = [id for id, count in id_count.iteritems()]
                self.add_blocker('id', block_id, filter_type=filter_type, filter_reason=filter_reason, dat=dat, board_url=board_url, time=time, recursion=recursion) 
    
    
    def add_blocker(self, noise_type, noise_word, method='search', filter_type='normal', filter_reason='', dat='all', board_url='all', recursion=False):
        """Adds noise filter.

        Arguments:
            noise_type -- string noise type.
                type list is:
                    mail
                    message
                    name
                    id
            noise_word -- regex string noise

        """
        sql = """
            INSERT OR REPLACE INTO
            noise_response (noise_type, noise_word, word_type, filter_type, filter_reason, dat, board_url, time, recursion)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        database = self.__database
        if type(noise_word) == list:
            for word in noise_word:
                database.execute(sql, (noise_type, word, method, filter_type, filter_reason, dat, board_url, int(time.time()), False))
        else:
            database.execute(sql, (noise_type, noise_word, method, filter_type, filter_reason, dat, board_url, int(time.time()), False))
        database.commit()

    def list(self):
        pass

    def remove_blocker(self, noise_filter):
        pass

    def get_filter(self):
        sql = """
            SELECT * from noise_response
    
        """
        database = self.__database
        cursor = self.__cursor
        cursor.execute(sql, ())
        return [ i for i in cursor]

    def delete(self, rows):
        sql = """
            DELETE from noise_response WHERE noise_type=? and noise_word=? and word_type=? and filter_type=? and filter_reason=? and dat=? and board_url=? and time=? and recursion=?
        """
        for i in rows:
            self.__cursor.execute(sql, tuple(i))
        self.__database.commit()
        
        

    def filtering(self, thread):
        """Returns filtered response list.
            Arguments:
                thread -- bbs2ch.browsing.Browser object.
            Returns:
                list of bbs2ch.browsing.ResponseInfo object.
        """
        sql = """
            SELECT * from noise_response
            WHERE (dat=? or dat='all') and (board_url=? or board_url='all')
    
        """
        #database = sqlite3.connect(self.__database_path)
        #cursor = database.cursor()
        t_dat = thread.dat if hasattr(thread, 'dat') else 'all'
        t_board_url = thread.board_url if hasattr(thread, 'board_url') else 'all'
        database = self.__database
        cursor = self.__cursor
        cursor.execute(sql, (t_dat, t_board_url))
        responses = thread.list()
        for noise_type, noise_word, word_type, filter_type, filter_reason, dat, board_url, t, r in cursor:
            if noise_type == 'response':
                response_regex = re.compile(re.escape(noise_word))
            if noise_type == 'name':
                name_regex = re.compile(re.escape(noise_word))

            for response in responses:
                if not response.date_id == 'hidden.' or not response.has_key('hidden'):
                    if noise_type == 'id':
                        match = self.__regex_id.search(response.date_id)
                        if match:
                            id = match.groups()[0]
                            if noise_word == id:
                                response.name = 'hidden.'
                                response.mail = 'hidden.'
                                response.date_id = filter_reason
                                response.message = ''
                                if filter_type == 'stealth':
                                    response['hidden'] = True
                    elif noise_type == 'be' and response.number == 1:
                        match = self.__regex_be.search(response.date_id)
                        if match:
                            beid = util.get_be_id(match.groups()[0])
                            if noise_word == beid:
                                response.name = ''
                                response.mail = ''
                                response.date_id = filter_reason
                                response.message = '''go back. 
</br>
you must not see this thread.
</br>
cause:%s


''' % filter_reason
                                response['hidden'] = True
                                    
                    elif noise_type == 'response':
                        if response_regex.search(response.message):
                            response.name = 'hidden.'
                            response.mail = 'hidden.'
                            response.date_id = filter_reason
                            response.message = ''
                            if filter_type == 'stealth':
                                response['hidden'] = True
                    elif noise_type == 'name':
                        if name_regex.search(response.name):
                            response.name = 'hidden.'
                            response.mail = 'hidden.'
                            response.date_id = filter_reason
                            response.message = ''
                            if filter_type == 'stealth':
                                response['hidden'] = True

        return responses
                            
                            
