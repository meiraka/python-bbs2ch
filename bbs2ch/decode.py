"""2ch bbs response decoder.

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

import re

WRITE_ERROR = 0
WRITE_OK = 1
WRITE_COOKIE = 2


def menu(body):
    """decode 2ch menu html to python data struct.

    :param body: 2ch menu html string
    :rtype: board url, category, board title tupled list
    """
    re_category = re.compile(u'<B>([^<]+)</B><BR>')
    re_board_url = re.compile(u'<A HREF=(http://'
                              u'[^/]+/[^/]+/)>([^<]+)<')
    current_category = None
    for line in body.split(u'\n'):
        match_category = re_category.search(line)
        if match_category:
            current_category = match_category.groups()[0]
        if current_category:
            match_board_url = re_board_url.match(line)
            if match_board_url:
                url, title = match_board_url.groups()
                yield (url, current_category, title)


def board_subject(body):
    """decode 2ch board subject.txt to python data.

    :param body: 2ch board subject string
    :rtype: thread dat id, title, rescount tupled list
    """
    re_threads = re.compile(u'(\\d+).dat<>(.+)\s\\((\\d+)\\)')
    for line in body.split(u'\n'):
        match_threads = re_threads.match(line)
        if match_threads:
            dat, title, res = match_threads.groups()
            yield (dat, title, int(res))


def thread_dat(body):
    """decode 2ch thread dat string to python data.

    :param body: 2ch board subject string
    :rtype: response name, mail, date_id, message tupled list
    """
    for line in body.split(u'\n'):
        splitted = line.split(u'<>')
        if len(splitted) == 5:
            name, mail, date_id, message, title = splitted
            yield (name, mail, date_id, message)
        elif len(splitted) == 6:
            name, mail, date_id, message, deleted, title = splitted
            yield (name, mail, date_id, message)
        elif len(splitted) >= 4:
            name = u''
            mail = u''
            date_id = u''
            message = u'can not understand this line:</br> %' % (
                line.replace(u'<>', u'&lt;&gt;'))
            yield (name, mail, date_id, message)


def thread_write(body):
    """Get write status.

    :param body: 2ch /test/bbs.cgi response body string
    :rtype: status string, true, error, cookie
    """
    re_status = re.compile(u'<\\!--\\s2ch_X:([^\\s]+)\\s-->')
    match = re_status.search(body)
    if match:
        return match.group(1).lower()


def thread_write_form(body):
    """Get 'hidden' key and value from html."""
    re_hidden = re.compile(
        u'input\\stype=hidden\\s+name="([^"]+)"\\svalue="([^"]+)"')
    hidden = None
    for i in body.split(u'<'):
        search = re_hidden.search(i)
        if search:
            hidden = search.groups()
    if hidden:
        return [(hidden[0], hidden[1])]
    else:
        return []
