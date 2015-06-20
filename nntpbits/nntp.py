import nntpbits.protocols
import socket

class client(nntpbits.protocols.Protocol):
    """NNTP client endpoint

    Construction:
    nntpbits.nntp.client() -> NNTP client object

    Call the connect() method to actually establish a connection.

    """
    def __init__(self):
        nntpbits.protocols.Protocol.__init__(self)
        self._reset()

    def _reset(self):
        self.service=None
        self.posting=None
        self.reader=None
        self.capability_list=None

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
            raise Exception("MODE READER failed %s" % self.response)
        self.capability_list = None

    def post(self, article):
        """n.post(ARTICLE)

        Post an article.

        ARTICLE may either be a byte string (in which case it will be
        split at CRLF or LF characters) or a list of byte strings, one
        per line.  In the latter case, the byte strings must not
        include newline sequences.

        """
        self._require_reader()
        if isinstance(article, bytes):
            article=article.splitlines()
        code,arg=self.transact(b"POST")
        if code!=340:
            raise Exception("POST not permitted: %s" % self.response)
        self.send_lines(article)
        code,arg=self.wait()
        if code!=240:
            raise Exception("POST failed: %s" % self.response)

    def quit(self):
        """n.quit()

        Disconnect from the server.

        """
        self.transact(b"QUIT")
        self.disconnect()
        self._reset()
