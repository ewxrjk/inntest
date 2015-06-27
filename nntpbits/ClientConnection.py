#
# Copyright 2015 Richard Kettlewell
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import nntpbits
import logging,re,socket

_group_re=re.compile(b"^([0-9]+) ([0-9]+) ([0-9]+) (.*)$")
_message_id_re=re.compile(b"Message-ID:\\s*(<.*@.*>)\\s*$", re.IGNORECASE)

class ClientConnection(nntpbits.Connection):
    """NNTP client endpoint

    Construction:
    nntpbits.ClientConnection() -> NNTP client object

    Optional arguments:
    address -- host,port tuple
    timeout -- connect timeout
    source_address -- host,port tuple to bind local endpoint to

    Alternatively call the connect() method to actually establish a
    connection.

    A ClientConnection may be used as a context manager.  If the
    connection is still live on exit from the suite, a QUIT command is
    automatically issued.

    """
    def __init__(self, address=None, timeout=None, source_address=None,
                 stoppable=False):
        nntpbits.Connection.__init__(self, stoppable=stoppable)
        self._reset()
        if address is not None:
            self.connect(address, timeout, source_address)

    def __enter__(self):
        return self

    def __exit__(self, et, ev, etb):
        logging.debug("ClientConnection.__exit__: %s / %s / %s" % (et, ev, etb))
        if self.r is not None or self.w is not None:
            self.quit()
        return False

    def _reset(self):
        """n._reset()

        Reset the state of this connection.

        """
        self.service=None
        self.posting=None
        self.reader=None
        self.capability_list=None
        self.capability_set=None
        self.overview_fmt=None
        self.current_group=None

    def connect(self, address, timeout=None, source_address=None):
        """n.connect(address[, timeout[, source_address]])

        Connect to a remote server.

        Arguments:
        address -- host,port tuple

        Optional:
        timeout -- connect timeout
        source_address -- host,port tuple to bind local endpoint to

        """
        logging.debug("Connecting to %s port %s" % address)
        self.socket(socket.create_connection(address, timeout,
                                             source_address))

    def connected(self):
        """n.connected()

        Called when the files() or socket() method is used to
        establish IO.

        """
        code,arg=self.wait()
        # 3977 5.1.1
        if code == 200:
            self.service=True
            self.posting=True
        elif code == 201:
            self.service=True
            self.posting=False
        elif code == 400 or code == 502:
            self.service=False
            self.disconnect()   # 5.1.1 [2]
        else:
            # 5.1.1 [1]
            raise ValueError("invalid initial connection response: %s"
                             % self.response)
        self.reader=None
        self.capability_list=None
        return self.service

    # -------------------------------------------------------------------------
    # CAPABILITIES (3977 5.2)

    def _capabilities(self):
        """n._capabilities()

        Retrieve the server's capabilities.  If it does not support
        the command an empty list is returned.  (This might be changed
        in the future.)

        """
        code,arg=self.transact(b"CAPABILITIES")
        if code == 101:
            self.capability_list=self.receive_lines()
            if self.capability_list[0] != b'VERSION 2':
                raise Exception("CAPABILITIES: unrecognized version")
        else:
            self.capability_list=[]
        self.capability_set=set()
        for cap in self.capability_list[1:]:
            caps=cap.split()
            self.capability_set.add(caps[0])

    def capabilities(self):
        """n.capabilities() -> SET

        Return the server's capabilities, as a set of bytes
        objects.

        The list is cached so it is efficient to repeatedly call this
        function.

        """
        if self.capability_set is None:
            self._capabilities()
        return self.capability_set

    def capability_arguments(self, cap):
        """n.capability_arguments(CAP) -> LIST | None

        Returns the list of arguments for capability CAP, or None if
        the server doesn't have that capability.

        """
        cap=nntpbits._normalize(cap)
        if self.capability_set is None:
            self._capabilities()
        for l in self.capability_list:
            caps=l.split()
            if caps[0]==cap:
                return caps[1:]
        return None

    # -------------------------------------------------------------------------
    # MODE READER (3977 5.3)

    def _require_reader(self):
        """n._require_reader()

        Issues the MODE READER command if it is necessary.

        """
        if self.reader is None:
            self.capabilities()
            if b"READER" in self.capability_list:
                self.reader=True
            elif b"MODE-READER" in self.capability_list:
                self._mode_reader()
            elif len(self.capability_list) > 0:
                self.reader=False
            else:
                self._mode_reader()
        if not self.reader:
            raise Exception("NNTP reader support unavailable")

    def _mode_reader(self):
        """n._mode_reader()

        Issues the MODE READER command.
        Resets the cached capability list if it succeeds.

        """
        code,arg=self.transact(b"MODE READER")
        if code == 200:
            self.reader=True
            self.posting=True
        elif code == 201:
            self.reader=True
            self.posting=False
        else:
            raise Exception("MODE READER command failed %s" % self.response)
        self.capability_list=None
        self.capability_set=None
        self.overview_fmt=None

    # -------------------------------------------------------------------------
    # QUIT (3977 5.4)

    def quit(self):
        """n.quit()

        Disconnect from the server.

        """
        self.transact(b"QUIT")
        self.disconnect()
        self._reset()

    # -------------------------------------------------------------------------
    # GROUP (3977 6.1.1)

    def group(self, group):
        """n.group(NAME) -> (count, low, high)

        Selects the group NAME.

        """
        self._require_reader()
        group=nntpbits._normalize(group)
        code,arg=self.transact(b"GROUP " + group)
        if code == 211:
            m=_group_re.match(arg)
            if not m:
                raise Exception("GROUP response malformed: %s" % self.response)
            self.current_group=group
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        elif code == 411:
            raise Exception("Group %s does not exist" % str(group))
        else:
            raise Exception("GROUP command failed: %s" % self.response)

    # -------------------------------------------------------------------------
    # LISTGROUP (3977 6.1.2)

    #TODO

    # -------------------------------------------------------------------------
    # LAST & NEXT (3977 6.1.3-4)

    def next(self):
        """n.next() -> NUMBER,ID,None | None,None,None

        Advance to the next article in the group.  Returns the newly
        selected article's number andmessage ID on success or None at
        the end of the group.

        The odd return convention is designed to fit in with the
        article, head and body methods.

        """
        return self._select(b'NEXT')

    def last(self):
        """n.last() -> NUMBER,ID,None | None,None,None

        Retreat to the previous article in the group.  Returns the
        newly selected article's message ID on success or None at the
        end of the group.

        The odd return convention is designed to fit in with the
        article, head and body methods.

        """
        return self._select(b'LAST')

    # -------------------------------------------------------------------------
    # STAT (3977 6.2.4)

    def stat(self, ident=None):
        """n.stat(ID|NUMBER) -> NUMBER,ID,None | None,None,None
        n.stat() -> NUMBER,ID,None | None,None,None

        Tests the presence of an article by number from the current
        group or by message ID; or test whether there is a currently
        selected article.

        The odd return convention is designed to fit in with the
        article, head and body methods.

        """
        if isinstance(ident, int):
            ident="%d" % ident
        if ident is None:
            return self._select(b'STAT')
        else:
            return self._select(b'STAT', nntpbits._normalize(ident))

    _stat_re=re.compile(b'^(\\d+) +(<[^>]+>)( +.*)?$')
    _select_noarticle=set([420, 421, 422, 423])

    def _select(self, *cmd):
        code,arg=self.transact(b' '.join(cmd))
        if code==223:
            m=ClientConnection._stat_re.match(arg)
            if not m:
                raise Exception("%s command malformed response: %s"
                        % (str(cmd[0]), arg))
            return (int(m.group(1)), m.group(2), None)
        if code in ClientConnection._select_noarticle:
            return None, None, None
        raise Exception("%s command failed: %s" % (str(cmd[0]), self.response))

    # -------------------------------------------------------------------------
    # ARTICLE, HEAD, BODY (3977 6.2.1-3)

    def article(self, ident=None):

        """n.article(ID|NUMBER) -> NUMBER,IDENT,LINES | None,None,None
        n.article() -> NUMBER,IDENT,LINES | None,None,None

        Retrieves an article by number from the current group, or by
        message ID specified as a bytes object (or as a string, which
        will be converted to a bytes object using the ASCII encoding);
        or retrieves the current article.

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'ARTICLE', 220)

    def head(self, ident=None):
        """n.head(ID|NUMBER) -> NUMBER,IDENT,LINES | None,None,None
        n.head() -> NUMBER,IDENT,LINES | None,None,None

        Retrieves the header of an article by number from the current
        group, or by message ID specified as a bytes object (or as a
        string, which will be converted to a bytes object using the
        ASCII encoding); or retrieves the current article's header.

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'HEAD', 221)

    def body(self, ident=None):
        """n.body(ID|NUMBER) -> NUMBER,IDENT,LINES | None,None,None

        Retrieves the body of an article by number from the current
        group, or by message ID specified as a bytes object (or as a
        string, which will be converted to a bytes object using the
        ASCII encoding); or retrieves the current article's body.

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'BODY', 222)

    def _article(self, ident, command, response):
        """n._article(NUMBER|ID, COMMAND, RESPONSE) -> NUMBER,IDENT,LINES

        Issues COMMAND to retrieve the identified article.  RESPONSE
        should be the positive response code to expect.  Returns None
        if the article doesn't exist.

        """
        self._require_reader()
        if isinstance(ident, int):
            ident="%d" % ident
        if ident is None:
            cmd=command
        else:
            cmd=command + b' ' + nntpbits._normalize(ident)
        code,arg=self.transact(cmd)
        if code == response:
            m=ClientConnection._stat_re.match(arg)
            if not m:
                raise Exception("%s command malformed response: %s"
                        % (str(command), arg))
            return int(m.group(1)), m.group(2), self.receive_lines()
        elif code == 423 or code == 430:
            return None,None,None
        else:
            raise Exception("%s command failed: %s"
                            % (str(command), self.response))

    # -------------------------------------------------------------------------
    # POST & IHAVE (3977 6.3.1-2)

    def post(self, article):
        """n.post(ARTICLE)

        Post an article.

        ARTICLE may either be a bytes object (in which case it will be
        split at CRLF or LF characters) or a list of bytes objects,
        one per line.  In the latter case, each list element must not
        include newline sequences.

        If ARTICLE is a string, then it is converted to a bytes object
        using the ASCII encoding.  The same applies to list elements
        if it is a list.

        This is the correct method for normal clients to use to post
        new articles.

        """
        self._require_reader()
        return self._post(article, b'POST', None, 340, 240)

    def ihave(self, article, ident=None):
        """n.ihave(ARTICLE[, IDENT])

        Transfer an article.

        ARTICLE may either be a bytes object (in which case it will be
        split at CRLF or LF characters) or a list of bytes objects,
        one per line.  In the latter case, each list element must not
        include newline sequences.

        If ARTICLE is a string, then it is converted to a bytes object
        using the ASCII encoding.  The same applies to list elements
        if it is a list.

        IDENT should be the articles message ID, either as a bytes
        object or a string.  If it is missing then it will be
        extracted from the article.

        This method is only suitable for use by news peers.  To post a
        new article from a normal client, use the post() method
        instead.

        """
        if ident is None:
            if isinstance(article, bytes):
                article=article.splitlines()
            for line in article:
                if line == "":
                    break
                m=_message_id_re.match(line)
                if m:
                    ident=m.group(1)
                    break
        else:
            ident=nntpbits._normalize(ident)
        if ident is None:
            raise Exception("failed to extract message ID from article")
        return self._post(article, b'IHAVE', ident, 335, 235)

    def _post(self, article, command, ident, initial_response, ok_response):
        """n._post(ARTICLE, COMMAND, IDENT, INITIAL_RESPONSE, OK_RESPONSE) -> CODE

        Post or transfer an article.

        ARTICLE is the article to send and COMMAND is the command to
        use.  IDENT should be its message ID or None.

        INITIAL_RESPONSE and OK_RESPONSE give the positive responses
        to check for in the two phases of the posting process.

        """
        article=nntpbits._normalize(article)
        if isinstance(article, bytes):
            article=article.splitlines()
        code,arg=self.transact(command if ident is None
                               else command + b' ' + ident)
        if code == 435 or code == 436:
            return code
        if code!=initial_response:
            raise Exception("%s command failed: %s"
                            % (str(command), self.response))
        self.send_lines(article)
        code,arg=self.wait()
        if code == 436 or code == 437:
            return code
        if code!=ok_response:
            raise Exception("%s command failed: %s"
                            % (str(command), self.response))
        return code

    # -------------------------------------------------------------------------
    # DATE (3977 7.1)

    def date(self):
        """n.date() -> DATE

        Return the server's idea of the current date.
        The result is a bytes object in the form YYMMDDHHMMSS.

        """
        self._require_reader()
        code,arg=self.transact(b'DATE')
        if code == 111:
            return arg
        else:
            raise Exception("DATE command failed: %s", self.response)

    # -------------------------------------------------------------------------
    # HELP (3977 7.2)

    def help(self):
        """n.help() -> LIST

        Returns the server's help output.

        """
        code,arg=self.transact(b'HELP')
        if code == 100:
            return self.receive_lines()
        else:
            raise Exception("HELP command failed: %s", self.response)

    # -------------------------------------------------------------------------
    # NEWGROUPS (3977 7.3)

    #TODO

    # -------------------------------------------------------------------------
    # NEWNEWS (3977 7.4)

    def newnews(self, wildmat, date):
        """n.newnews(WILDMAT, DATE) -> LIST

        Returns a list of messages posted to groups matching WILDMAT
        since DATE.

        DATE may be any of:
        ["YYMMDD", "HHMMSS"]
        ["YYYYMMDD", "HHMMSS"]
        "YYYYMMDDHHMMSS"
        A float or int, as returned by time.time()

        The first two are the native format for NNTP NEWNEWS; the
        third is the result of the DATE command and the date() method.
        """
        if isinstance(date, list):
            date=b''.join(nntpbits._normalize(date))
        elif isinstance(date, int) or isinstance(date, float):
            date=time.strftime("%Y%m%d%H%M%S", time.gmtime(date))
        date=nntpbits._normalize(date)
        self._require_reader()
        code,arg=self.transact([b'NEWNEWS', wildmat, date[:-6], date[-6:]])
        if code==230:
            return self.receive_lines()
        else:
            raise Exception("NEWNEWS command failed: %s", self.response)

    # -------------------------------------------------------------------------
    # LIST (3977 7.6, 6048)

    def list(self, what=b'ACTIVE', wildmat=None):
        """n.list(WHAT) -> LIST | None
        n.list(WHAT, WILDMAT) -> LIST | None

        Issues a LIST command.  WHAT should be 'ACTIVE', 'NEWSGROUPS', etc.
        WILDMAT is optional and limits the output.  See RFC3977 s4 for
        syntax.

        The return value is a list of bytes objects, or None if the
        server recognizes the list type but doesn't have the
        information.

        """
        if what is None:
            cap=b'ACTIVE'
        else:
            what=nntpbits._normalize(what).upper()
            cap=what
        # Become a reader if necessary
        if (cap not in self.capability_arguments(b'LIST')
            and b'MODE-READER' in self.capabilites()):
            self._mode_reader()
        if what is None:
            cmd=[b'LIST']
            assert wildmat is None
        else:
            cmd=[b'LIST', what]
            if wildmat is not None:
                cmd.append(nntpbits._normalize(wildmat))
        code,arg=self.transact(b' '.join(cmd))
        if code == 215:
            return self.receive_lines()
        elif code == 503:
            # Keyword recognized, but server does not (currently)
            # maintain the information.  e.g. LIST MOTD when not
            # configured.
            return None
        else:
            raise Exception("LIST %s command failed: %s" % (what, self.response))

    # -------------------------------------------------------------------------
    # OVER (3977 8.3, 8.4)

    def over(self, low, high=None):
        """n.over(LOW, HIGH) -> LIST
        n.over(ID) -> LIST

        Return overview data for a range of messages.  Each list
        element is an unparsed bytes object as returned from the
        server.

        Note that LOW and HIGH are _inclusive_ bounds, unlike the
        usual Python idiom.  If no articles are in the range then []
        is returned, even if the server returned 423.

        If an message ID is passed then only overview data for that
        message is returned (i.e. as a single-element list).  If the
        article doesn't exist then None is returned.

        """
        self._require_reader()
        if high is not None:
            code,arg=self.transact(bytes('OVER %d-%d' % (low, high), 'ascii'))
        else:
            code,arg=self.transact(b'OVER ' + nntpbits._normalize(low))
        if code == 224:
            return self.receive_lines()
        elif code == 423:
            return []
        elif code == 430 or code == 420:
            return None
        else:
            raise Exception("OVER command failed: %s" % self.response)

    def parse_overview(self, line):
        """n.parse_overview(LINE) -> NUMBER,DICT

        Parse overview data into a dictionary.

        NUMBER is the article number, from the first field.

        Keys in DICT are bytes objects with LOWER CASE header/metadata
        names, including the leading or trailing colon.  For example,
        b'subject:' and not b'Subject:' or 'Subject:'.  ield.

        Values in DICT are bytes objects.

        """
        r={}
        fields=line.split(b'\t')
        fmt=self.list_overview_fmt()
        for n in range(1,len(fields)):
            field=fields[n]
            name=fmt[n-1].lower()
            if n < 6 or name[0:1] == b':':
                r[name]=field
            else:
                n=len(name)
                if field[0:n].lower() != name:
                    raise Exception("malformed overview data for %s" % name)
                while n<len(field) and field[n] in b' \t\r\f\n':
                    n+=1
                r[name]=field[n:]
        return (int(fields[0]), r)

    def _list_overview_fmt(self):
        """n._list_overview_fmt() -> LIST

        Retrieves the overview format data, or an empty list if it
        cannot be retrieved.

        """
        if b'OVER' in self.capabilities():
            code,arg=self.transact(b"LIST OVERVIEW.FMT")
            if code == 215:
                self.overview_fmt=[x.lower() for x in self.receive_lines()]
                fixups={ b'bytes:': b':bytes', b'lines:': b':lines' }
                for i in range(0,len(self.overview_fmt)):
                    l=self.overview_fmt[i]
                    if len(l) >= 5 and l[-5:] == b':full':
                        self.overview_fmt[i]=self.overview_fmt[i][:-5]
                    if l in fixups:
                        self.overview_fmt[i]=fixups[l]
            else:
                self.overview_fmt=[]
        else:
            self.overview_fmt=[]
        return self.overview_fmt

    def list_overview_fmt(self):
        """n.list_overview_fmt() -> LIST

        Return the list of fields used by the OVER command as a list
        of lower-case bytes objects.

        If the server returns Bytes: or Lines:, these are converted to
        the RFC3977 values of :bytes and :lines.

        """
        self._require_reader()
        if self.overview_fmt is None:
            self._list_overview_fmt()
        return self.overview_fmt

    # -------------------------------------------------------------------------
    # HDR (3977 8.5, 8.6)

    _hdr_re=re.compile(b'^(\\d+) (.*)$')

    def hdr(self, header, low, high=None):
        """n.over(HEADER, LOW, HIGH) -> LIST
        n.over(HEADER, ID) -> LIST

        Return headers for a range of messages.  Each list element is
        a list containing the article number and header value.

        Note that LOW and HIGH are _inclusive_ bounds, unlike the
        usual Python idiom.  If no articles are in the range then []
        is returned, even if the server returned 423.

        If an message ID is passed then only overview data for that
        message is returned (i.e. as a single-element list).  If the
        article doesn't exist then None is returned.

        """
        self._require_reader()
        cmd=[b'HDR', nntpbits._normalize(header)]
        if high is not None:
            cmd.append(bytes("%d-%d" % (low, high), 'ascii'))
        else:
            cmd.append(nntpbits._normalize(low))
        code,argument=self.transact(cmd)
        if code == 225:
            lines=self.receive_lines()
            result=[]
            for line in lines:
                m=ClientConnection._hdr_re.match(line)
                if not m:
                    raise Exception("HDR response malformed: %s" % lie)
                result.append([int(m.group(1)), m.group(2)])
            return result
        elif code == 423:
            return []
        elif code == 430 or code == 420:
            return None
        else:
            raise Exception("HDR command failed: %s" % self.response)

    # -------------------------------------------------------------------------
    # MODE STREAM (4644 2.3)

    #TODO

    # -------------------------------------------------------------------------
    # CHECK (4644 2.4)

    #TODO

    # -------------------------------------------------------------------------
    # TAKETHIS (4644 2.5)

    #TODO


