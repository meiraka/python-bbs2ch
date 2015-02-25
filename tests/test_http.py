"""Test bbs2ch.http module."""
from bbs2ch import http


def test_host_path():
    """Return hostname and path from url."""
    assert (u'hoge.com', '/') == http.host_path(u'http://hoge.com/')


def test_encode_request_get():
    """Return http request string."""
    header = [(u'Key', u'Value'),
              (u'Key2', u'Value2')]

    assert ('GET / HTTP/1.1\r\n'
            'Key: Value\r\n'
            'Key2: Value2\r\n'
            '\r\n'
            '\r\n' ==
            http.encode_request('GET', u'/', header))


def test_encode_request_post():
    """Return http request string.

    if body is not empty, add header to Content-length and Content-Type.
    """
    header = [(u'Key', u'Value'),
              (u'Key2', u'Value2')]

    body = [(u'key', u'value'),
            (u'key2', u'value2')]

    assert ('POST / HTTP/1.1\r\n'
            'Key: Value\r\n'
            'Key2: Value2\r\n'
            'Content-Type: application/x-www-form-urlencoded\r\n'
            'Content-Length: 21\r\n'
            '\r\n'
            'key=value&key2=value2\r\n'
            ==
            http.encode_request(u'POST', u'/', header, body))
