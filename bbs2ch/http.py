"""
http client for bbs2ch.

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
import socket
import StringIO
import gzip
import urllib


def host_path(url):
    """return hostname and http path from url."""
    re_http_url = re.compile('http://(.+)')
    http_url = re_http_url.match(url)
    if http_url:
        url = http_url.groups()[0]
    host, path = url.split('/', 1)
    path = '/'+path
    return (host, path)


def urlencode(string):
    """Return % encoded string."""
    def _enc(char):
        num = ord(char)
        if num == 20:
            return u'+'
        else:
            return '{}2'
            
    return ''.join([char for char in string])


def encode_request(method, path, header, body=[], encoding='ascii'):
    """encode request data to http request string.

    :param method: http method type.
    :param path: http method argument.
    :param header: header items
    :type header: pair unicode string tuples in list
    :param body: key-value tuple list of post body items
    :type body: pair unicode string tuples in list
    :rtype: str
    """
    request_string = '%s %s HTTP/1.1' % (method, path)
    body_string = '&'.join(
        ['%s=%s' % tuple([urllib.quote(i.encode(encoding)) for i in kv])
            for kv in body])
    if body_string:
        header.append((u'Content-Type', u'application/x-www-form-urlencoded'))
        header.append((u'Content-Length', str(len(body_string))))
    print header
    header_string = '\r\n'.join(
        ['{}: {}'.format(k.encode(encoding), v.encode(encoding))
         for k, v in header])
    return '{}\r\n{}\r\n\r\n{}\r\n'.format(
        request_string, header_string, body_string)


def send(host, request, port=80, timeout=20.0):
    """send http request.

    :param host: hostname
    :param request: http request string
    :param port: http socket port
    :param timeout: http connection timeout
    :rtype: socket connection object
    """
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connection.settimeout(timeout)
    connection.connect((host, port))
    connection.send(str(request))
    return connection


def recv(connection, timeout=2.0, buffersize=2048, callback=None):
    """receive http request.

    :param connection: socket connection object from send()
    :param timeout: http connection timeout
    :param buffersize: socket recive buffer size
    :param callback: function calls with {u'recv': int, u'total': int or None}
                     when recieve data
    :rtype: str
    """
    response = ''
    zero_count = 0  # recieved zero data count
    recv_size = 0  # recieved response header + data size
    recv_total = None  # will recieved response header + data size
    connection.settimeout(timeout)
    while True:
        data = connection.recv(buffersize)
        if len(data):
            recv_size = recv_size + len(data)
        else:
            zero_count = zero_count + 1
            if zero_count > 3:
                break

        response = response + data
        if callback:
            if not recv_total:
                headerbody = response.split('\r\n\r\n', 1)
                if len(headerbody) == 2:
                    header_data = dict(_decode_header(headerbody[0]))
                    if u'Content-Length' in header_data:
                        recv_total = int(header_data[u'Content-Length'])
            callback({u'recv': recv_size, u'total': recv_total})
    return response


def _convert_http_charset_to_python_charset(charset):
    if charset.startswith('x-'):
        charset = charset.replace('x-', '')
    dirty_charsets = {'shift_jis': 'ms932'}
    return (charset if charset not in dirty_charsets
            else dirty_charsets[charset])


def _decode_header(header, fallback_encoding=None):
    """return receive response size from http response header.

    :rtype: pair unicode string tuples in list
    """
    encoding = None
    header = header.replace('\r', '')
    for items in header.split('\n'):
        kv = header.split(':', 1)
        if len(kv) == 2:
            k, v = kv
            if k == 'content-type' and 'charset' in v:
                content = dict([ckv.strip().split('=', 1)
                                for ckv in v.split(';')])
                if 'charset' in content:
                    encoding = content['charset'].lower()
                break
    else:
        encoding = fallback_encoding

    if encoding:
        encoding = _convert_http_charset_to_python_charset(encoding)

    decoded_header = header.decode(encoding if encoding else 'ascii')
    decoded_header.replace(u'\r', u'')
    for items in header.split(u'\n'):
        kv = items.split(u':', 1)
        if len(kv) == 2:
            kv = [i.strip() for i in kv]
            if kv[0] == u'Content-Type':
                kv[1] = _decode_media_type(kv[1])
            yield kv


def _decode_media_type(value):
    typeparam = value.split(u';', 1)
    if len(typeparam) == 1:
        return [i.strip() for i in typeparam[0].split(u'/', 1)] + [{}]
    else:
        return [i.strip() for i in typeparam[0].split(u'/', 1)] + [
            dict([[j.strip() for j in i.strip().split(u'=')]
                 for i in typeparam[1].split(u';')
                 if len(i.strip().split(u'=')) == 2])]


def _extract_html_encoding(html):
    """get encoding type from html string."""
    encoding = 'ascii'
    m = re.search('<meta.+charset=([^"|>|\s]+)', html, re.IGNORECASE)
    if m:
        encoding = m.group(1).replace('"', '')
    return encoding


def decode_response(response, fallback_encoding='ms932'):
    """decode socket recieved data to usable data.

    :param response: string raw response data
    :param force_encoding: encoding
    :type force_encoding: string encoding label or None
    """
    encoding = None
    header, body = response.split('\r\n\r\n', 1)
    length = len(body)
    (httpver, snum, sstring) = header.splitlines()[0].split(' ', 2)
    status = (httpver, int(snum), sstring)
    header_dict = dict(_decode_header(header, fallback_encoding))
    if (u'Content-Encoding' in header_dict and
            header_dict[u'Content-Encoding'] == u'gzip'):
        # if gziped, decode gzip and update body length
        io = StringIO.StringIO(body)
        f = gzip.GzipFile(fileobj=io)
        body = f.read()
        length = len(body)
        f.close()
    if u'Content-Type' in header_dict:
        # if content type includes charset, set encoding
        content_params = header_dict[u'Content-Type'][2]
        if u'charset' in content_params:
            encoding = _convert_http_charset_to_python_charset(
                content_params[u'charset'])
        # if content type is text/html, read encoding from html meta tag
        main, sub = header_dict[u'Content-Type'][:2]
        if (main, sub) == (u'text', u'html'):
            encoding = _convert_http_charset_to_python_charset(
                _extract_html_encoding(body))
    if not encoding:
        if fallback_encoding:
            # if force encoding, set encoding
            encoding = fallback_encoding
        else:
            encoding = 'ascii'

    body = body.decode(encoding, errors='replace')
    return (status, header_dict, body, length)
