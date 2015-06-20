import nntpbits
import re,socket

_group_re=re.compile(b"^([0-9]+) ([0-9]+) ([0-9]+) (.*)$")
_message_id_re=re.compile(b"Message-ID:\\s*(<.*@.*>)\\s*$", re.IGNORECASE)

class Client(nntpbits.Protocol):
    """NNTP client endpoint

    Construction:
    nntpbits.Client() -> NNTP client object

    Call the connect() method to actually establish a connection.

    """
    def __init__(self):
        nntpbits.Protocol.__init__(self)
        self._reset()

    def _reset(self):
        self.service=None
        self.posting=None
        self.reader=None
        self.capability_list=None
        self.current_group=None

    def connect(self, address, timeout=None, source_address=None):
        """n.connect(address[, timeout[, source_address]])

        Connect to a remote server.

        The arguments are the same as socket.create_connection.

        """
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

    def _capabilities(self):
        code,arg=self.transact(b"CAPABILITIES")
        if code == 101:
            self.capability_list=self.receive_lines()
        else:
            self.capability_list=[]

    def capabilities(self):
        """n.capabilities() -> LIST

        Return the server's capability list.

        The list is cached so it is efficient to repeatedly call this
        function.

        """
        if self.capability_list is None:
            self._capabilities()
        return self.capability_list

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
        if isinstance(ident, str):
            article=bytes(ident,'ascii')
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
        if isinstance(article, str):
            article=bytes(article,'ascii')
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

    def group(self, group):
        """n.group(NAME) -> (count, low, high)

        Selects the group NAME.

        """
        self._require_reader()
        if isinstance(group, str):
            group=bytes(group,"ascii")
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
        if isinstance(ident, str):
            ident=bytes(ident,'ascii')
        code,arg=self.transact(command + b' ' + ident)
        if code == response:
            return self.receive_lines()
        elif code == 423 or code == 430:
            return None
        else:
            raise Exception("%s command failed: %s"
                            % (str(command), self.response))

    def quit(self):
        """n.quit()

        Disconnect from the server.

        """
        self.transact(b"QUIT")
        self.disconnect()
        self._reset()
