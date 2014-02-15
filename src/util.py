#coding:utf8
import re
import browsing

"""
util functions for bbs2ch.
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

def check_AA(string):
    """If given string contains asci art(sjis art), returns True.
    """
    if not string.find(u' 　') == -1:
        return True
    else:
        return False


def check_code(string):
    """If given string contains source code, returns True."""
    if not string.find(u'    ') == -1:
        return True
    else:
        return False


def extract_url(text):
    """ Returns url list extract from given text.
    """
    urls = []
    end = 0
    url_regex = re.compile(u'(h?)(ttp|ttps)(://[^\\s|^<]+)')
    while True:
        match = url_regex.search(text[end:])
        if match:
            f = match.groups()
            urls.append('h'+f[1]+f[2])
            end = end + match.end()-1
        else:
            break
    return urls

def get_be_id(be_number):
    """Returns 2ch be basic number.
    """
    benum = int(be_number)
    beid = ((benum/100) + ((benum/10) % 10) - (benum % 10) - 5) / (((benum/10) % 10) * (benum % 10) * 3)
    return str(beid)

def search_next_thread(thread):
    parent_board = thread.parent
    title = thread.title
    search_text_list= []
    text_length = 16
    while True:
        if text_length <= 0:
            return []
        if len(title) > text_length-1:
            for index in range(len(title)-text_length):
                search_text_list.append(title[index:index+text_length])
        else:
                search_text_list = [title]
        match_thread_list = []
        for next_thread_candidate in parent_board:
            if not next_thread_candidate.rank == 10000:
                for search_text in search_text_list:
                    if next_thread_candidate == thread:
                        break
                    if next_thread_candidate.title.count(search_text):
                        match_thread_list.append(next_thread_candidate)
                        break
        if match_thread_list:
            return match_thread_list
        else:
            text_length = text_length - 4


