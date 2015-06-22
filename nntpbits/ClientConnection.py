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

    Call the connect() method to actually establish a connection.

    """
    def __init__(self, stoppable=False):
        nntpbits.Connection.__init__(self, stoppable=stoppable)
        self._reset()

    def _reset(self):
        self.service=None
        self.posting=None
        self.reader=None
        self.capability_list=None
        self.overview_fmt=None
        self.current_group=None

    def connect(self, address, timeout=None, source_address=None):
        """n.connect(address[, timeout[, source_address]])

        Connect to a remote server.

        The arguments are the same as socket.create_connection.

        """
        logging.debug("Connecting to %s port %s" % address)
        self.socket(socket.create_connection(address, timeout,
                                             source_address))

    def connected(self):
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
    # CAPABILITIES

    def _capabilities(self):
        code,arg=self.transact(b"CAPABILITIES")
        if code == 101:
            self.capability_list=self.receive_lines()
        else:
            self.capability_list=[]

    def capabilities(self):
        """n.capabilities() -> LIST

        Return the server's capability list, as a list of bytes
        objects.

        The list is cached so it is efficient to repeatedly call this
        function.

        """
        if self.capability_list is None:
            self._capabilities()
        return self.capability_list

    def capabilities_list(self):
        """n.capabilities_list() -> LIST

        Returns the list of LIST capabilities, as a list of bytes
        objects.

        As for capabilities(), the list is cached.

        """
        for cap in self.capabilities():
            if cap[0:4] == b'LIST':
                return cap.split()[1:]
        return []

    # -------------------------------------------------------------------------
    # MODE READER

    def _require_reader(self):
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
        code,arg=self.transact(b"MODE READER")
        if code == 200:
            self.reader=True
            self.posting=True
        elif code == 201:
            self.reader=True
            self.posting=False
        else:
            raise Exception("MODE READER command failed %s" % self.response)
        self.capability_list = None

    # -------------------------------------------------------------------------
    # POST & IHAVE

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
        self._post(article, b'POST', None, 340, 240)

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
        ident=nntpbits._normalize(ident)
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
        if ident is None:
            raise Exception("failed to extract message ID from article")
        return self._post(article, b'IHAVE', ident, 335, 235)

    def _post(self, article, command, ident, initial_response, ok_response):
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
    # GROUP

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
    # ARTICLE, HEAD, BODY

    def article(self, ident):
        """n.article(NUMBER) -> [LINE] | None
        n.article(ID) -> [LINE] | None

        Retrieves an article by number from the current group, or by
        message ID specified as a bytes object (or as a string, which
        will be converted to a bytes object using the ASCII encoding).

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'ARTICLE', 220)

    def head(self, ident):
        """n.head(NUMBER) -> [LINE] | None
        n.head(ID) -> [LINE] | None

        Retrieves the header of an article by number from the current
        group, or by message ID specified as a bytes object (or as a
        string, which will be converted to a bytes object using the
        ASCII encoding).

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'HEAD', 221)

    def body(self, ident):
        """n.body(NUMBER) -> [LINE] | None
        n.body(ID) -> [LINE] | None

        Retrieves the body of an article by number from the current
        group, or by message ID specified as a bytes object (or as a
        string, which will be converted to a bytes object using the
        ASCII encoding).

        The return value is either a list of lines (as bytes objects,
        without any line endings) or None if the article does not exist.

        """
        return self._article(ident, b'BODY', 222)

    def _article(self, ident, command, response):
        self._require_reader()
        if isinstance(ident, int):
            ident="%d" % ident
        code,arg=self.transact(command + b' ' + nntpbits._normalize(ident))
        if code == response:
            return self.receive_lines()
        elif code == 423 or code == 430:
            return None
        else:
            raise Exception("%s command failed: %s"
                            % (str(command), self.response))

    # -------------------------------------------------------------------------
    # OVER

    def _list_overview_fmt(self):
        if b'OVER' in self.capabilities():
            code,arg=self.transact(b"LIST OVERVIEW.FMT")
            if code == 215:
                self.overview_fmt=self.receive_lines()
                fixups = { b'bytes:': b':bytes', b'lines:': b':lines' }
                for i in range(0,len(self.overview_fmt)):
                    l = self.overview_fmt[i].lower()
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

        Return the list of fields used by the OVER command.

        If the server returns Bytes: or Lines:, these are converted to
        the RFC3977 values of :bytes and :lines.

        """
        if self.overview_fmt is None:
            self._list_overview_fmt()
        return self.overview_fmt

    def over(self, low, high):
        """n.over(LOW, HIGH) -> LIST

        Return overview data for a range of messages.  Each list
        element is an unparsed bytes object as returned from the
        server.

        Note that LOW and HIGH are _inclusive_ bounds, unlike the
        usual Python idiom.

        """
        code,arg=self.transact(bytes('OVER %d-%d' % (low, high), 'ascii'))
        if code == 224:
            return self.receive_lines()
        elif code == 423:
            return []
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

    # -------------------------------------------------------------------------
    # LIST

    def list(self, what=b'ACTIVE', wildmat=None):
        what=nntpbits._normalize(what).upper()
        # Become a reader if necessary
        if (what not in self.capabilities_list()
            and b'MODE-READER' in self.capabilites()):
            self._mode_reader()
        cmd=[b'LIST', what]
        if wildmat is not None:
            cmd.append(nntpbits._normalize(wildmat))
        code,arg=self.transact(b' '.join(cmd))
        if code == 215:
            return self.receive_lines()
        else:
            raise Exception("LIST %s command failed: %s" % (what, self.response))

    # -------------------------------------------------------------------------
    # QUIT

    def quit(self):
        """n.quit()

        Disconnect from the server.

        """
        self.transact(b"QUIT")
        self.disconnect()
        self._reset()
