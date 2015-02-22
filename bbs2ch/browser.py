"""
browsing 2ch bbs.

Copyright (c) 2011-2014 mei raka
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

from bbs2ch import version
from bbs2ch import http
from bbs2ch import decode

DEFAULT_USERAGENT = u'Monazilla/1.00 (python-bbs2ch/%s)' % version.__VERSION__


class Menu(object):

    """Represent a bbs2ch menu."""

    def __init__(self, url,
                 gzip=True, if_modified_since=None,
                 useragent=DEFAULT_USERAGENT):
        """initialize attributes."""
        self.url = url
        self.gzip = gzip
        self.if_modified_since = if_modified_since
        self.useragent = useragent

    def __repr__(self):
        """Return repr(self) string."""
        return "<bbs2ch.browser.Menu({}, useragent={})>".format(
            repr(self.url), repr(self.useragent))

    def __eq__(self, other):
        """Return true if same url."""
        return self.url == other.url

    def __iter__(self):
        """Return board list and set if_modified_since to last modified."""
        host, path = http.host_path(self.url)
        header = [(u'Accept-Language', u'ja'),
                  (u'Connection', u'close'),
                  (u'Host', host),
                  (u'Accept', u'*/*'),
                  (u'Referer', host),
                  (u'User-Agent', self.useragent)]
        if self.gzip:
            header.append((u'Accept-Encoding', u'gzip'))
        if self.if_modified_since:
            header.append((u'If-Modified-Since', self.if_modified_since))
        request = http.encode_request(u'GET', path, header=header)
        connection = http.send(host, request)
        response = http.recv(connection)
        res_header, res_body, length = http.decode_response(response)
        if u'Last-Modified' in res_header:
            self.if_modified_since = res_header[u'Last-Modified']

        for url, category, title in decode.menu(res_body):
            yield Board(url, category, title, useragent=self.useragent)


class Board(object):

    """Represent bbs2ch board."""

    def __init__(self, url, category=u'', title=u'',
                 gzip=True, if_modified_since=None,
                 useragent=DEFAULT_USERAGENT):
        """initialize attributes."""
        self.url = url
        self.category = category
        self.title = title
        self.gzip = gzip
        self.if_modified_since = if_modified_since
        self.useragent = useragent

    def __eq__(self, other):
        """Return true if same url or same title and category."""
        return (self.url == other.url or
                (self.category == other.category and
                 self.title == other.title))

    def __repr__(self):
        """Return repr(self) string."""
        return "<bbs2ch.browser.Board({}, {}, {}, useragent={})>".format(
            repr(self.url), repr(self.category),
            repr(self.title), repr(self.useragent))

    def __iter__(self):
        """Return Thread list."""
        subject = self.url + u'subject.txt'
        host, path = http.host_path(subject)
        header = [(u'Accept-Language', u'ja'),
                  (u'Connection', u'close'),
                  (u'Host', host),
                  (u'Accept', u'*/*'),
                  (u'Referer', self.url),
                  (u'User-Agent', self.useragent)]
        if self.gzip:
            header.append((u'Accept-Encoding', u'gzip'))
        if self.if_modified_since:
            header.append((u'If-Modified-Since', self.if_modified_since))
        request = http.encode_request(u'GET', path, header=header)
        connection = http.send(host, request)
        response = http.recv(connection)
        res_header, res_body, length = http.decode_response(response)
        if u'Last-Modified' in res_header:
            self.if_modified_since = res_header[u'Last-Modified']

        for index, (dat, title, res) in enumerate(
                decode.board_subject(res_body), start=1):
            yield Thread(self.url, dat, title, index, res,
                         useragent=self.useragent)


class Thread(object):

    """Represent bbs2ch thread."""

    def __init__(self, board_url, dat,
                 title='', rank=10000, total=0,
                 bytes=0, fetched=0,
                 gzip=True, if_modified_since=None,
                 useragent=DEFAULT_USERAGENT):
        """initialize attributes."""
        self.board_url = board_url
        self.dat = dat
        self.title = title
        self.rank = rank
        self.total = total
        self.bytes = bytes
        self.fetched = fetched
        self.gzip = gzip
        self.if_modified_since = if_modified_since
        self.useragent = useragent

        server_url, board_id, _empty = self.board_url.rsplit(u'/', 2)
        self.url = '%s/test/read.cgi/%s/%s/' % (server_url, board_id, dat)

    def __eq__(self, other):
        """Return true if same board url and dat."""
        return (self.board_url == other.board_url and
                self.dat == other.dat)

    def __repr__(self):
        """Return repr(self) string."""
        return "<bbs2ch.browser.Thread({})>".format(', '.join([
            repr(self.board_url), repr(self.dat), repr(self.title),
            repr(self.rank), repr(self.total),
            repr(self.bytes), repr(self.fetched),
            repr(self.gzip), repr(self.if_modified_since),
            repr(self.title), repr(self.useragent)]))

    def __iter__(self):
        """Return Response list."""
        board_name = http.host_path(self.board_url)[1].split('/')[1]
        dat_url = u'{}dat/{}.dat'.format(self.board_url, self.dat)
        host, path = http.host_path(dat_url)
        referer = 'http://{}/test/read.cgi{}{}/'.format(
            host, board_name, self.dat)
        print dat_url

        header = [(u'Accept-Language', u'ja'),
                  (u'Connection', u'close'),
                  (u'Host', host),
                  (u'Accept', u'*/*'),
                  (u'Referer', referer),
                  (u'User-Agent', self.useragent)]

        if self.gzip:
            header.append((u'Accept-Encoding', u'gzip'))
        if self.if_modified_since:
            header.append((u'If-Modified-Since', self.if_modified_since))
        if self.fetched_bytes and self.fetched_count:
            header.append(('Range', 'bytes={}-'.format(self.fetched_bytes-1)))

        request = http.encode_request(u'GET', path, header=header)
        connection = http.send(host, request)
        response = http.recv(connection)
        res_header, res_body, length = http.decode_response(response)
        for index, (name, mail, date_id, message) in enumerate(
                decode.thread_dat(res_body), start=self.fetched_count+1):
            yield Response(index, name, mail, date_id, message)
            self.fetched_count = index
        self.fetched_bytes = length
        if u'Last-Modified' in res_header:
            self.if_modified_since = res_header[u'Last-Modified']


class Response(object):

    """Represent bbs2ch response message."""

    def __init__(self, num, name, mail, date_id, message):
        """Initialize attributes."""
        self.num = num
        self.name = name
        self.mail = mail
        self.date_id = date_id
        self.message = message
