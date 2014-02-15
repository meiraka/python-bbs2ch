#coding:utf8
"""
http cookie controller for 2ch bbs.
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



import datetime

class Error(Exception):
    pass

class Cookie(object):
    def __init__(self, cookie_file=u'cookie'):
        self.__cookie_file = cookie_file
        self.__cookie = []
        self.__load_cookies()

    def __load_cookies(self):
        try:
            f = open(self.__cookie_file, 'r')
            string = f.read()
            f.close()
        except:
            return
        for line in string.split('\n'):
            try:
                name, expires, domain, path, secure = line.split(';')
                name = name.strip()
                expires = expires.strip().split('=', 1)[1]
                domain = domain.strip().split('=', 1)[1]
                path = path.strip().split('=', 1)[1]
                secure = secure.strip()
                self.__cookie.append(dict(name=name,
                        expires=expires,
                        domain=domain,
                        path=path,
                        secure=secure))
            except ValueError:
                pass

    def save_cookies(self):
        string = ''
        for cookie in self.__cookie:
            if cookie['expires']:
                string = string + cookie['name'] + ';'
                string = string + 'expires=' + cookie['expires'] + ';'
                string = string + 'domain=' + cookie['domain'] + ';'
                string = string + 'path=' + cookie['path'] + ';'
                string = string + cookie['secure'] + '\n'
            
        f = open(self.__cookie_file, 'w')
        f.write(string)
        f.close()

    def set_cookies(self, headers, host, path):
        headers = str(headers)
        for line in headers.split(u'\n'):
            try:
                header, values = line.split(':', 1)
                if header == 'Set-Cookie':
                    values_list = values.split(';')
                    values_dict = dict(
                            name='',
                            expires='',
                            domain=str(host),
                            path=str(path),
                            secure=''
                            )
                    values_dict['name'] = values_list[0].strip()
                    #get value from line
                    if values_list[-1] == '' or values_list[-1] == 'secure':
                        values_dict['secure'] = str(values_list[-1])
                        del values_list[-1]
                    for value in values_list[1:]:
                        value = value.strip()
                        key, data = value.split('=', 1)
                        values_dict[str(key)] = str(data)
                    #check older values
                    for index in range(len(self.__cookie)):
                        cookie = self.__cookie[index]
                        if cookie['name'].split('=')[0] == values_dict['name'].split('=')[0] and \
                            cookie['domain'] == values_dict['domain'] and \
                            cookie['path'] == values_dict['path']:
                            self.__cookie[index] = values_dict
                            break
                    else:
                        self.__cookie.append(values_dict)
            except ValueError:
                pass
        self.__check_date()


    def __check_date(self):
        new_cookies = []
        today = datetime.datetime(2020, 1, 1).today()
        for cookie in self.__cookie:
            expires = cookie['expires']
            date = expires.split(' ')[1]
            year = int(date.split('-')[-1])
            cookie_date = datetime.datetime(year, 12, 30)    #超てきとう
            if today < cookie_date:
                new_cookies.append(cookie)            
        self.__cookie = new_cookies
            

    def cookie(self, host, path):
        matched = {}
        for cookie in self.__cookie:
            if not host.find(cookie['domain']) == -1 and \
                path.startswith(cookie['path']):
                matched[cookie['name'].split('=')[0]] = cookie
        string = ''
        for k, values in matched.iteritems():
            string = string  + values['name'] + ';'
        return string
            
            
if __name__ == '__main__':
    import sys
    import python2ch
    p2ch = python2ch.Python2ch()
    cookie = Cookie()
    
    def write(board_url, dat_id, message, hidden=''):
        p = board_url.split('//')[1]
        host, uri = p.split('/', 1)
        c = cookie.cookie(host, '/test/bbs.cgi')
        ret = p2ch.write(board_url, dat_id, '', 'sage', message, c, hidden)
        cookie.set_cookies(ret['response_headers'], host, '/test/bbs.cgi')
        cookie.save_cookies()
        print  ret[u'request_headers']  
        print  ret[u'request_body']  
        print  ret[u'response_headers']  
        print ret[u'response_body']

    if sys.argv[1] == u'--write' and len(sys.argv) > 3:
        if len(sys.argv) == 5:
            write(sys.argv[2], sys.argv[3], sys.argv[4].decode('utf8'))
        if len(sys.argv) == 6:
            write(sys.argv[2], sys.argv[3], sys.argv[4].decode('utf8'), sys.argv[5])
    
