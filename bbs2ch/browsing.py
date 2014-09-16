#!/usr/bin/python
# vim:fileencoding=utf8

"""
high level 2ch bbs browsing interface.
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
import time

import browse
import cookie
import database
import static
import sqlite3


class Error(Exception):
    pass


class NotFoundError(Error):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class ConnectionError(Error):
    def __init__(self, request, message):
        self.request = request
        self.message = message

    def __str__(self):
        return repr(self.message)


class DatabaseError(Error):
    def __init__(self, error):
        self.error = error
    def __str__(self):
        return repr(self.error)


class Base(object):
    """Base class for all browsing objects.

    maneges and provides readonly libraries and parent-child model.

    Attributes:
        method   -- primitive methods to access 2ch host
        cookie   -- simple cookie reader/writer
        database -- 2ch database
    """
    def __init__(self, parent, method=None, cookie=None, database=None):
        """Stores parent and libraries objects.
        """
        if not method:
            method = parent.method
        if not cookie:
            cookie = parent.cookie
        if not database:
            database = parent.database
        self.__shared_cache = dict(
            parent = parent,
            method = method,
            cookie = cookie,
            database = database
            )

    def database_onthread(self):
        """Returns database object that runs on
        current running thread.

        if not using database in main thread, use this function to get
        database instance.
        because sqlite3 is not thread-safe database.
        """
        return database.Database(self.database.path)

    def __top(self):
        """Returns top level object.
        """
        if 'top' in self.__shared_cache:
            return self.__shared_cache['top']
        obj = self
        while True:
            new_obj = obj.parent
            if new_obj is None:
                break
            else:
                obj = new_obj
        self.__shared_cache['top'] = obj
        return obj

    def __readonly(key):
        def get(self):
            if key in self.__shared_cache:
                return self.__shared_cache[key]
            else:
                raise ValueError(key)
        return (get, )

    parent   = property(*__readonly('parent'))
    top      = property(__top)
    method   = property(*__readonly('method'))
    cookie   = property(*__readonly('cookie'))
    database = property(*__readonly('database'))


class Browser(Base):
    """2ch Browser.

    Attributes:
        user_agent  browser user-agent string
    """

    OPEN_MENU = u'open_menu'
    OPEN_BOARD = u'open_board'
    def __init__(self,
            cookie_path='cookie',
            database_path='db',
            menu_url=u'http://menu.2ch.net/bbsmenu.html'):
        """Generates cookie and 2ch database.
        """
        # self.__properties value cab access as self.[key].
        Base.__init__(self, None,
            browse.Browser(),
            cookie.Cookie(cookie_path),
            database.Database(database_path))
        self.__cache_menu = Menu(self, menu_url)
        self.__cache_custom_boards = {}
        self.__cache_custom_threads = {}
        self.__cache_custom_responses = {}
        
    def menu(self):
        return self.__cache_menu

    def custom_boards(self, title, where):
        """Creates a custom board list.

        Arguments:
            title -- object title.
            where -- sql
        """
        if not (title, where) in self.__cache_custom_boards:
            self.__cache_custom_boards[(title, where)] = CustomBoards(self, title, where)
        return self.__cache_custom_boards[(title, where)]

    def custom_threads(self, title, where):
        """Creates a custom thread list.

        Arguments:
            title -- object title.
            where -- sql
        """
        if not (title, where) in self.__cache_custom_threads:
            self.__cache_custom_threads[(title, where)] = CustomThreads(self, title, where)
        return self.__cache_custom_threads[(title, where)]

    def custom_responses(self, title, where):
        """Creates a custom response list.

        Arguments:
            title -- object title.
            where -- sql
        """
        if not (title, where) in self.__cache_custom_responses:
            self.__cache_custom_responses[(title, where)] = CustomResponses(self, title, where)
        return self.__cache_custom_responses[(title, where)]

    def open(self, url, callback=None, update=True):
        """Open a given url and returns an appropriate instance.

        Arguments:
            callback(status_id) -- callback function when calls:
                :OPEN_MENU: if menu has no given url board
                :OPEN_BOARD: if board has no given url thread
        """

        def find_key(obj, attr, value, retry=True):
            """Search [i for i in obj if getattr(i, attr) == value]
            """
            iterobj = obj.list_full() if hasattr(obj, 'list_full') else obj
            for i in iterobj:
                if str(getattr(i, attr)) == str(value):
                    return i
            if retry and update:
                obj.update()
                return find_key(obj, attr, value, False)
            return None

        # thread search
        thread = re.compile(u'//([^/]+)/test/read.cgi/([^/]+)/(\\d+)/.*')
        match = thread.search(url)
        if match:
            #is 2ch bbs thread url.
            server, board_name, dat = match.groups()
            board_url = u'http://' + server + u'/' + board_name + '/'
            board = find_key(self.__cache_menu, u'url', board_url)
            if board:
                thread = find_key(board, 'dat', dat)
                if thread:
                    return thread
        # board search
        # skip retry self.__cache_menu.update()
        board = find_key(self.__cache_menu, u'url', url, retry=bool(match))
        if board:
            return board
        return None

    def reduce_database_size(self):
        db = self.database_onthread()
        try:
            db.remove_old_threads()
        except sqlite3.OperationalError, err:
            raise DatabaseError(err)

    def ____user_agent():
        def get(self):
            return self.method.default_name

        def set(self, value):
            self.method.default_name = value

        return (get, set)

    user_agent = property(*____user_agent())
    

class Menu(Base):
    """bbs 2ch board list.

    """
    def __init__(self, parent, url):
        """Init properties.
        """
        Base.__init__(self, parent)
        self.__properties = dict(url=url)
        self.__updating = False
        self.__cache = {}

    def __iter__(self):
        return iter(self.list())

    def board(self, board_id, database=None):
        """Returns bbs2ch.browsing.Board object.
        
        Arguments:
            board_id -- board id in bbs2ch.database.Database object
        """
        if not board_id in self.__cache:
            if not database:
                database = self.database_onthread()
            self.__cache[board_id] = Board(self, board_id, database)
        return self.__cache[board_id]

    def update(self, callback=None):
        """Update board list.

        Arguments:
            callback -- it calls when recv function is executed.

        """
        if self.__updating:
            return
        self.__updating = True
        db = self.database_onthread()
        menu = self.method.menu(self.url, callback)
        try:
            update = db.update_boards(menu)
        except sqlite3.OperationalError, err:
            self.__updating = False
            raise DatabaseError(err)
        for board_info in db.get_boards():
            board = self.board(board_info['id'], database=db)
            board.update_properties(db)
        self.__updating = False

    def list(self):
        """Returns Browsing.Board list.

        Returns:
             list includes Browsing.Board.
        """
        db = self.database_onthread()
        boards = [self.board(board_info['id'], database=db)
                  for board_info in db.get_boards()
                  if not board_info['category'] == 'unknown']
        return boards

    def __generate_property(key):
        def get(self):
            if key in self.__properties:
                return self.__properties[key]
            else:
                raise ValueError(key)
        def set(self, value):
            if key in self.__properties:
                self.__properties[key] = value
            else:
                raise ValueError(key)

        return (get, set)

    url = property(*__generate_property('url'))


class Board(Base):
    """
    bbs2ch board object.

    readonly properties:
        category -- unicode category name
        title -- unicode board title name
        url -- string board url
    read/write properties:
        favorite -- boolean favorite bit
    """

    def __init__(self, parent, board_id, database=None):
        """Init properties.
        """
        Base.__init__(self, parent, database=database)
        self.__properties = dict(
            id = board_id
            )
        self.__threads = {}
        self.__updating = False
        self.__cache = {}
        self.update_properties(database)

    def __iter__(self):
        """Returns threads iterator.
        """
        return iter(self.list())

    def thread(self, thread_id, database=None):
        """Generates a Thread object.
        """
        if not thread_id in self.__cache:
            if not database:
                database = self.database_onthread()
            if not database.get_thread_info(thread_id):
                raise ThreadNotFoundError(thread_id)
            self.__cache[thread_id] = Thread(self, thread_id, database=database)
        return self.__cache[thread_id]

    def update(self, callback=None):
        """Updates this board.
        """
        if self.__updating:
            return
        self.__updating = True
        db = self.database_onthread()
        board_info = db.get_board(self.id)
        url = board_info['url']
        try:
            threads = self.method.board(url, callback)
        except browse.ConnectionError, err:
            db.close()
            self.__updating = False
            raise ConnectionError(err.request, err.message)
        if threads['response_status'] == '302':
            url = self.method.get_new_board_url(url)
            if url:
                db.change_board_url(self.id, url)
                threads = self.method.board(url, status_callback)
        try:
            db.update_threads(self.id, threads['thread_list'])
            db.update_board(self.id, last_acquired=int(time.time()))
        except sqlite3.OperationalError, err:
            self.__updating = False
            raise DatabaseError(err)
        self.update_properties(db)
        for thread_info in db.get_threads(self.id):
            self.thread(thread_info['id'], database=db).update_properties(db)
        db.close()
        self.__updating = False

    def list(self):
        """Get Thread list of this board.
        """
        threads = []
        db = self.database_onthread()
        threads = [self.thread(thread_info['id'], database=db) for thread_info in db.get_threads(self.id)]
        return threads

    def list_full(self):
        """Get full Thread list of this board.

        Includes missing dat Thread.
        """
        threads = []
        db = self.database_onthread()
        threads = [self.thread(thread_info['id'], database=db) for thread_info in db.get_threads_full(self.id)]
        return threads

    def update_properties(self, database=None):
        """update properties from database.

        this function will usally call by another function.
        """
        if not database:
            database = self.database_onthread()
        for k, v in database.get_board(self.id).iteritems():
            self.__properties[k] = v
        if not self.__properties['last_acquired']:
            self.__properties['last_acquired'] = 0
        else:
            self.__properties['last_acquired'] = int(
                self.__properties['last_acquired'])

    def __readonly(key):
        def get(self):
            if key in self.__properties:
                return self.__properties[key]
            else:
                raise ValueError(key)
        return get

    def __set_favorite(self, value):
        db = self.database_onthread()
        db.update_board(self.id, favorite=value)
        self.update_properties()

    category =      property(__readonly('category'))
    id =            property(__readonly('id'))
    is_open =       property(__readonly('is_open'))
    last_acquired = property(__readonly('last_acquired'))
    title =         property(__readonly('title'))
    url =           property(__readonly('url'))
    favorite =      property(__readonly('favorite'), __set_favorite)


class Thread(Base):
    """bbs2ch Thread object.

    readonly properties:
        url -- unicode url
        dat -- int dat id
        title -- unicode thread title
        rank -- int thread rank
        total -- int responses count
        acquired -- int acquired responses count
        range_bytes -- int acquired thread size
        last_modified -- unicode last modified date
        last_acquired -- unicode last acquired date
        board_url -- unicode parent board url
        alive -- bool is alive in parent board
    read/write properties:
        last_read -- int last read response index
        favorite -- boolean favorite bit
    """
    UPDATE = 'update'
    UPDATE_SUCCESS = 'update_success'
    UPDATE_RANGE_NOT_SATISFIABLE = 'update_range_not_satisfiable'
    UPDATE_PARTIAL = 'update_partial'
    UPDATE_NOT_MODIFIED = 'update_not_modified'
    UPDATE_FAIL = 'update_fail'
    UPDATE_NOT_FOUND = 'update_not_found'

    UPDATING = 'updating thread'
    
    WRITE = 'write'
    WRITE_SUCCESS = browse.WRITE_SUCCESS
    WRITE_WARNING = browse.WRITE_WARNING
    WRITE_FAIL = browse.WRITE_FAIL
    WRITE_STOP = browse.WRITE_STOP
    WRITE_CONFIRM = browse.WRITE_CONFIRM

    def __init__(self, parent, thread_id, database=None):
        """Init Thread Object.

        Do not use constructor, use Browser.thread(thread_id)
        """
        Base.__init__(self, parent, database=database)
        self.__hidden = ''
        self.__updating = False
        self.__properties = dict(
            id = thread_id
            )
        self.update_properties(database)

    def __iter__(self):
        return iter(self.list())

    def update(self, callback=None):
        """Update responses of this thread.

        Arguments:
            background -- if True, run in another thread
            callback -- if it does not None, it calls when update was finished.
        """
        if self.__updating:
            return
        if self.rank >= static.MISSING_DAT_RANK:
            return
        self.__updating = True
        status = None
        db = self.database_onthread()
        #get thread information
        info = db.get_thread_info(self.id)
        #check last_modified of this thread.
        if info['last_modified'] == u'':
            #if last_modified is empty, browser has never get responses.
            #get responses nomally.
            try:
                responses = self.method.thread(info['board_url'], info['dat'], status_callback=callback)
            except browse.ConnectionError, err:
                self.__updating = False
                raise ConnectionError(err.request, err.message)
            #check response status
            if responses['response_status'] == u'302':
                #not found
                self.parent.update()
                info = db.get_thread_info(self.id)
                try:
                    responses = self.method.thread(info['board_url'], info['dat'], status_callback=callback)
                except browse.ConnectionError, err:
                    self.__updating = False
                    raise ConnectionError(err.request, err.message)

            if responses['response_status'] == u'200' and \
                    not len(responses['response_list']) == 0:
                #if HTTP 200 OK, update databases
                try:
                    db.update_responses(info['id'],
                        responses['range_bytes'],
                        responses['last_modified'],
                        responses['response_list'])
                except sqlite3.OperationalError, err:
                    self.__updating = False
                    raise DatabaseError(err)
                status = self.UPDATE_SUCCESS
            else:
                #else do nothing
                status = self.UPDATE_NOT_FOUND
        else:
            #last_modified is not empty,
            #try to get partial contents.
            try:
                responses = self.method.thread(info['board_url'],
                    info['dat'],
                    (info['last_modified'], int(info['range_bytes'])),
                    status_callback=callback
                    )
            except browse.ConnectionError, err:
                self.__updating = False
                raise ConnectionError(err.request, err.message)

            #check response
            if responses['response_status'] == u'302':
                self.parent.update()
                info = db.get_thread_info(self.id)
                try:
                    responses = self.method.thread(info['board_url'],
                        info['dat'],
                        (info['last_modified'], int(info['range_bytes'])),
                        status_callback=callback
                        )
                except browse.ConnectionError, err:
                    self.__updating = False
                    raise ConnectionError(err.request, err.message)

            if responses['response_status'] == u'302':
                status = self.UPDATE_NOT_FOUND
            elif responses['response_status'] == u'304':
                #not modified.
                #do nothing.
                status = self.UPDATE_NOT_MODIFIED
            elif responses['response_status'] == u'416':
                #some posts are removed.
                #get new posts.
                try:
                    responses = self.method.thread(info['board_url'], info['dat'], status_callback=callback)
                except browse.ConnectionError, err:
                    self.__updating = False
                    raise ConnectionError(err.request, err.message)

                if not len(responses['response_list']) == 0:
                    try:
                        db.update_responses(info['id'],
                            responses['range_bytes'],
                            responses['last_modified'],
                            responses['response_list'])
                    except sqlite3.OperationalError, err:
                        self.__updating = False
                        raise DatabaseError(err)
                    status = self.UPDATE_SUCCESS
                else:
                    status = UPDATE_NOT_MODIFIED

            elif responses['front'] == '\n':
                #partial content, add responses to database
                try:
                    db.add_responses(info['id'],
                        responses['range_bytes'],
                        responses['last_modified'],
                        responses['response_list'])
                except sqlite3.OperationalError, err:
                    self.__updating = False
                    raise DatabaseError(err)
                status = self.UPDATE_SUCCESS
            else:
                #some posts are removed and added.
                #get new posts.
                try:
                    responses = self.method.thread(info['board_url'], info['dat'])
                except browse.ConnectionError, err:
                    self.__updating = False
                    raise ConnectionError(err.request, err.message)

                if not len(responses['response_list']) == 0:
                    try:
                        db.update_responses(info['id'],
                            responses['range_bytes'],
                            responses['last_modified'],
                            responses['response_list'])
                    except sqlite3.OperationalError, err:
                        self.__updating = False
                        raise DatabaseError(err)
                    status = self.UPDATE_SUCCESS
                else:
                    status = self.UPDATE_NOT_MODIFIED
        try:
            db.set_thread_info(self.id, last_acquired=int(time.time()))
        except sqlite3.OperationalError, err:
            self.__updating = False
            raise DatabaseError(err)

        self.update_properties(db)
        info = db.get_thread_info(self.id)
        self.__updating = False
        return (status, info)
        
    def write(self, name, mail, message):
        """Write response to this thread.

        Arguments:
            name -- post user name
            mail -- post user mail address
            message -- post user main message
            callback -- if it is not None, it calls when finish write.
        """
        p = self.board_url.split('//')[1]
        host, uri = p.split('/', 1)
        cookie = self.cookie.cookie(host, '/test/bbs.cgi')
        response = self.method.write(self.board_url,
            self.dat, name, mail, message, cookie, self.__hidden)
        self.cookie.set_cookies(response['response_headers'], host, '/test/bbs.cgi')
        self.cookie.save_cookies()
        if response['hidden']:
            self.__hidden = response['hidden']
        return response
                        
    def list(self, number=None):
        """Get responses.

        Returns:
            list of browsing.ResponseInfo.
        """
        db = self.database_onthread()
        if not number == None:
            return ResponseInfo(db.get_responses(self.id, number))
        responses = [
                ResponseInfo(response)
                for response in db.get_responses(self.id)
                ]
        return responses

    def update_properties(self, database=None):
        if not database:
            database = self.database_onthread()
        self.__properties = database.get_thread_info(self.id)

    def __property_func(key, write=False):
        def get(self):
            if key == 'last_acquired':
                if self.__properties[key]:
                    return int(self.__properties[key])
                else:
                    return 0
            return self.__properties[key]
    
        def set(self, value):
            db = self.database_onthread()
            db.set_thread_info(self.id, **{key: value})
            self.update_properties(db)
        if write:
            return (get, set)
        else:
            return (get, )

    def __get_url():
        def get(self):
            url = self.board_url.split('://', 1)
            host, board_name = url[1].split('/', 1)
            board_name = '/' + board_name
            return 'http://' + host + '/test/read.cgi' + board_name + self.dat + '/'
        return (get, )

    def __get_alive():
        def get(self):
            return not(self.dat == static.MISSING_DAT_RANK)

        return (get, )

    #set properties
    board_url =     property(*__property_func('board_url'))
    dat =           property(*__property_func('dat'))
    url =           property(*__get_url())
    title =         property(*__property_func('title'))
    rank =          property(*__property_func('rank'))
    total =         property(*__property_func('total'))
    acquired =      property(*__property_func('acquired'))
    last_read =     property(*__property_func('last_read', write=True))
    open =          property(*__property_func('is_open', write=True))
    range_bytes =   property(*__property_func('range_bytes'))
    last_modified = property(*__property_func('last_modified'))
    last_acquired = property(*__property_func('last_acquired'))
    favorite =      property(*__property_func('favorite', write=True))
    id =            property(*__property_func('id'))
    alive =         property(*__get_alive())


class CustomBoards(Base):
    UPDATE = 'update'
    UPDATING = 'updating'

    def __init__(self, parent, title, where):
        Base.__init__(self, parent)
        self.__properties = dict(
            title = title,
            where = where,
            url = 'sql:' + where,
            )
        self.__boards = {}
        self.__list = []

    def __eq__(self, obj):
        return hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj)

    def __ne__(self, obj):
        return not(hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj))

    def __iter__(self):
        return iter(self.list())

    def update(self):
        pass

    def __board(self, board_id, db=None, callback=None):
        """Returns bbs2ch.browsing.Board object.
        
        Arguments:
            board_id -- board id in bbs2ch.database.Database object
            db -- bbs2ch.database.Database object
            callback -- if it does not None, it calls when board
                    was generated.
        """
        if not db:
            db = self.database_onthread()
        menu = self.parent.menu()
        if not board_id in self.__boards:
            self.__boards[board_id] = menu.board(board_id, db)
        if callback:
            callback(self.__boards[board_id])
        return self.__boards[board_id]
    
    def list(self):
        db = self.database_onthread()
        boards = [self.__board(board_info['id'], db) for board_info in db.get_custom_boards(self.where)]
        return boards

    def __readonly(key):
        def get(self):
            if key in self.__properties:
                return self.__properties[key]
            else:
                raise ValueError(key)
        return get

    title = property(__readonly('title'))
    where = property(__readonly('where'))
    url =   property(__readonly('url'))
    

class CustomThreads(Base):
    """
    Creates Custom queried Thread list.
    
    """

    def __init__(self, parent, title, where):
        """Init properties.

        Arguments:
            parent - parent object. browsing.Browser.
            title - this objects title like normal board.
            where - sqlite3 query.
        """
        Base.__init__(self, parent)
        self.__boards = {}
        self.__threads = {}
        self.__properties = dict(
            title = title,
            where = where,
            url = 'sql:' + where,
            )
        self.__list = []
        self.__updating = False

    def __eq__(self, obj):
        return hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj)

    def __ne__(self, obj):
        return not(hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj))

    def __iter__(self):
        return iter(self.list())

    def __thread(self, thread_id, db=None, callback=None):
        """Returns Thread object.

        Sets __boards[parent_board_id] = parent_board
        """
        if not db:
            db = self.database_onthread()
        if not thread_id in self.__threads:
            thread_info = db.get_thread_info(thread_id)
            board_id = thread_info['board_id']
            menu = self.parent.menu()
            if not board_id in self.__boards:
                self.__boards[board_id] = menu.board(board_id, db)
            self.__threads[thread_id] = self.__boards[board_id].thread(thread_id, db)
        if callback:
            callback(self.__threads[thread_id])
        return self.__threads[thread_id]

    def __update_boards(self, boards, callback):
        if self.__updating:
            return False
        self.__updating = True
        total = len(boards)
        current = 1
        for board in boards:
            if callback:
                callback('', 'recv board', current, total)
            try:
                board.update()
            except:
                self.__updating = False
                return False
            current = current + 1
        if callback:
            callback('', 'finish', 1, 1)
        self.__updating = False
        return True

        
    def update(self, callback):
        """Update threads parent boards to get latest thread infomation.
        """
        boards = [board for id, board in self.__boards.iteritems]
        self.__update_boards(boards, callback)

    def minimum_update(self, last_acquired, callback):
        """Update threads parent boards if board.last_acquired < last_acquired.
        """
        boards = [board for id, board in self.__boards.iteritems() if board.last_acquired < last_acquired]
        self.__update_boards(boards, callback)
        

    def list(self):
        db = self.database_onthread()
        threads_info = db.get_custom_threads(self.where)
        thread_list = [self.__thread(thread_info['id'], db) for thread_info in threads_info]
        return thread_list

    def __readonly(key):
        def get(self):
            if key in self.__properties:
                return self.__properties[key]
            else:
                raise ValueError(key)
        return get

    def __calc_last_acquired(self):
        self.list() # update board list.
        oldest_last_acquired = int(time.time())
        for id, board in self.__boards.iteritems():
            if oldest_last_acquired > board.last_acquired:
                oldest_last_acquired = board.last_acquired
        return oldest_last_acquired
            

    title = property(__readonly('title'))
    where = property(__readonly('where'))
    url =   property(__readonly('url'))
    last_acquired = property(__calc_last_acquired)


class CustomResponses(Base):
    """
    Creates Custom queriedR Reponse list.
    
    """

    def __init__(self, parent, title, where):
        """Init properties.

        Arguments:
            parent - parent object. browsing.Browser.
            title - this objects title like normal board.
            where - sqlite3 query.
        """
        Base.__init__(self, parent)
        self.__boards = {}
        self.__threads = {}
        self.__properties = dict(
            title = title,
            where = where,
            url = 'sql:' + where
            )
        self.__list = []

    def __eq__(self, obj):
        return hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj)

    def __ne__(self, obj):
        return not(hasattr(obj, 'url') and hasattr(obj, 'title') and \
            self.url == obj.url and self.title == obj.title and \
            type(self) == type(obj))

    def __iter__(self):
        return iter(self.list())

    def update(self, callback):
        pass

    def list(self):
        db = self.database_onthread()
        responses_info = db.get_custom_responses(self.where)
        response_list = [ResponseInfo(response_info) for response_info in responses_info]
        return response_list

    def __readonly(key):
        def get(self):
            if key in self.__properties:
                return self.__properties[key]
            else:
                raise ValueError(key)
        return get

    title = property(__readonly('title'))
    where = property(__readonly('where'))
    url =   property(__readonly('url'))
    

class ResponseInfo(dict):
    __getattr__ = dict.__getitem__
'''
    def __setattr__(self, key, value):
        if self.has_key(key):
            err = "Attribute '"+key+"' is a read only proparty"
            raise AttributeError(err)

'''
