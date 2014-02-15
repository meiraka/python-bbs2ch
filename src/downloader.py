import socket
import os
import urllib
import sqlite3
import time
"""download and cache web files.
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

ERROR = 'error'
SUCCESS = 'success'
PROGRESS = 'progress'

class Downloader(object):
    """
    Download manager for bbs2ch.
    """
    def __init__(self, dl_dir='', user_agent='bbs2ch'):
        self.__downloading = {}
        self.user_agent=user_agent

        if not dl_dir == '' and not dl_dir[-1] == '/':
            dl_dir = dl_dir+'/'
        self.__dl_dir = dl_dir
        if not dl_dir == '' and not os.path.exists(dl_dir):
            os.makedirs(dl_dir)
        sql = """
            CREATE TABLE IF NOT EXISTS
            downloads
            (
                id INTEGER,
                url TEXT PRIMARY KEY,
                type TEXT,
                header TEXT
            );
        """
        self.__database = sqlite3.connect(self.__dl_dir+'database')
        self.__cursor = self.__database.cursor()
        self.__cursor.execute(sql)
        self.path = dl_dir


    def __readdb(self, url):
        sql = """
            SELECT * from downloads
            WHERE url=?
            """
        database = self.__database
        cursor = database.cursor()    
        cursor.execute(sql, (url, ))
        for file_id, url, file_type, header in cursor:
            status = ''
            for line in header.split('\n'):
                k, v = header.split(':', 1)
                if k.lower() == 'status':
                    status = v.strip()
                    break
            return FileInfo(url=url, path=self.__dl_dir+'files/'+str(file_id), type=file_type, headers=header, status=status)

    def __deldb(self, url):
        sql = """
            DELETE FROM downloads
            WHERE url=?
            """
        database = self.__database
        cursor = database.cursor()
        cursor.execute(sql, (url, ))

    def has_file(self, url):
        dic = self.__readdb(url)
        if dic:
            return dic
        else:
            return {}

    def __writedb(self, url, headers, body, database=None):
        """Writes file information to database.
        """
        sql = """
            INSERT OR REPLACE INTO
            downloads
            (id, url, type, header)
            VALUES(?, ?, ?, ?);
        """
        database = self.__database
        cursor = database.cursor()
        header = ''
        for k, v in headers.iteritems():
            header = header + k + ': ' + v + '\n'
        header = header[:-1]
        file_id = int(time.time()*100)
        if not os.path.exists(self.__dl_dir+'files/'):
            os.makedirs(self.__dl_dir+'files/')
        f = open(self.__dl_dir+'files/'+str(file_id), 'wb')
        f.write(body)
        f.close()
        content_type = ''
        status = v
        for k, v in headers.iteritems():
            if k.lower() == 'content-type':
                content_type = v
            if k.lower() == 'status':
                status = v.strip()
        cursor.execute(sql, (file_id, url, content_type, header))
        database.commit()
        return FileInfo(
                url=url,
                path=self.__dl_dir+'files/'+str(file_id),
                status=status,
                type=content_type, headers=header
            )
    

    def download(self, url, force=False):
        """ download file from url.

        Arguments:
            url - http url
            force
        """
        if self.__downloading.has_key(url):
            return FileInfo(url=url, status=PROGRESS)
        else:
            self.__downloading[url] = True
        
        path = self.__readdb(url)
        if path:
            if force:
                self.__deldb(url)
            elif path['status'].startswith('200') or path['type'].startswith('image'):
                return path
            else:
                self.__deldb(url)
        url2 = url.replace('http://', '')
        host, uri = url2.split('/', 1)
        host = host
        uri = '/' + uri 
        headers  = [
            ('Host', host),
            ('Accept', '*/*'),
            ('User-Agent', self.user_agent),
            ('Connection', 'close'),
            ('Referer', 'http://'+host+'/')
            ]
        string = ''
        for key, value in headers:
            string = string + key + ': ' + value + '\r\n'
        string = string[:-1]
        request = 'GET ' +  uri + ' HTTP/1.1'
        response = ''
        count = 0
        recvcount = 0
        try:
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.settimeout(5)
            connection.connect((host, 80))
            connection.send(request+'\r\n'+string+'\r\n\r\n')
            while True:
                data = connection.recv(2048)
                if not data:
                    count = count + 1
                else:
                    recvcount+=len(data)
                    count = 0
                if count > 7:
                    break
                response = response + data
            connection.close()
        except Exception, err:
            return FileInfo(url=url, status=str(err))
            


        try:
            headers, body = response.split('\r\n\r\n', 1)
        except:
            return FileInfo(url=url, status='broken http protocol')
        
        headers = headers.replace('\r', '')
        header_dict = {}
        for header in headers.split('\n'):
            splitted = header.split(':', 1)
            if len(splitted) == 2:
                key, value = splitted
                header_dict[key] = value.strip()
        header_dict['status'] = headers.split('\n')[0].split(' ', 1)[1]
        d = self.__writedb(url, header_dict, body)
        del self.__downloading[url]
        return d


            
    
class FileInfo(dict):
    def __init__(self, **kwargs):
        dict.__init__(self, kwargs)
