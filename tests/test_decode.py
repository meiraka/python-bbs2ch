# coding: utf8
"""Test bbs2ch.decode module."""
from bbs2ch import decode


def test_menu():
    """Parse bbsmenu html."""
    body = u"""
<B>カテゴリ1</B><BR>
<A HREF=http://test2ch.net/hoge/>ほげ</A><br>
<A HREF=http://test2ch.net/fuga/>ふが</A><br>
<BR><BR><B>カテゴリ2</B><BR>
<A HREF=http://test2ch.net/foo/>foo</A><br>"""
    ret = list(decode.menu(body))
    assert (u'http://test2ch.net/hoge/', u'カテゴリ1', u'ほげ') == ret[0]
    assert (u'http://test2ch.net/fuga/', u'カテゴリ1', u'ふが') == ret[1]
    assert (u'http://test2ch.net/foo/', u'カテゴリ2', u'foo') == ret[2]
