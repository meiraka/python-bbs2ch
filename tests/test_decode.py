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


def test_board_subject():
    """Parse board subject.txt."""
    body = u"""
100.dat<>スレッド1 (2)
200.dat<>スレッド2 (1000)"""
    ret = list(decode.board_subject(body))
    assert (u'100', u'スレッド1', 2) == ret[0]
    assert (u'200', u'スレッド2', 1000) == ret[1]
