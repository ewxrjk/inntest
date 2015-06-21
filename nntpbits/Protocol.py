"""Protocol server base class"""
import logging,re,socket

_parse_re=re.compile(b"^([0-9]{3}) (.*)$")

class Protocol(object):
    """Base class for text-based network protocols

    Construction:
    nntpbits.Protocol() -> protocol endpoint object
    nntpbits.Protocol(eol=EOL) -> protocol endpoint object

    EOL must be a byte string.  The default is CRLF.

    """

    def __init__(self, eol=b"\r\n"):
        self.eol=eol

    def files(self, r, w):
        """p.files(r=READER, w=WRITER)

        Use binary files READER and WRITER for IO.

        """
        self.r=r
        self.w=w
        self.connected()

    def socket(self, s):
        """p.socket(SOCKET)

        Use a connected socket SOCKET for IO.

        """
        self.files(r=s.makefile(mode='rb'), w=s.makefile(mode='wb'))
        s.close()

    def connected(self):
        """p.connected()

        Called when the files() or socket() method is used to
        establish IO.

        """
        pass

    def send_line(self, line, flush=True):
        """p.send_line(BYTES)

        Send a bytes object.  The protocol EOL sequence is appended.

        If BYTES is actually a string then it is converted to a bytes
        object using the ASCII encoding.

        """
        logging.debug("SEND %s" % line)
        if isinstance(line, str):
            line=bytes(line,'ascii')
        self.w.write(line)
        self.w.write(b'\r\n')
        if flush:
            self.w.flush()

    def send_lines(self, lines):
        """p.send_lines(LIST)

        Send a list of bytes objects.  The SMTP/NNTP dot-stuffing
        protocol is used.  The protocol EOL sequence is appended to
        each line.

        If any of the list elements are strings then it they are
        converted to bytes objects using the ASCII encoding.

        """
        for line in lines:
            if isinstance(line, str):
                line=bytes(line,'ascii')
            if len(line) > 0 and line[0] == b'.':
                self.w.write(b'.')
            self.w.write(line)
            self.w.write(b'\r\n')
        self.w.write(b'.\r\n')
        self.w.flush()

    def receive_line(self):
        """p.receive_line() -> LINE

        Receive a line as a bytes object.  The protocol EOL sequence
        is removed.

        Returns None if there is no more input.

        """
        line=b"";
        while not self._complete(line):
            ch=self.r.read(1)
            if len(ch) == 0:
                return None
            line += ch
        line=line[0:-len(self.eol)]
        ## TODO eof behavior
        logging.debug("RECV %s" % line)
        return line

    def _complete(self, line):
        return len(line) >= len(self.eol) and line[-len(self.eol):] == self.eol

    def receive_lines(self):
        """p.receive_lines() -> LIST

        Receive a sequence of lines as a list of bytes objects.  The
        SMTP/NNTP dot-stuffing protocol is used.  The protocol EOL
        sequence is removed from each line.

        Returns None if there is no more input.

        """
        lines=[]
        line=self.receive_line()
        while line != b".":
            if line is None:
                return None
            if len(line) > 0 and line[0] == b'.':
                line=line[1:]
            lines.append(line)
            line=self.receive_line()
        return lines

    def disconnect(self):
        """p.disconnect()

        Disconnect from the peer.

        """
        if self.r is not None:
            self.r.close()
        if self.w is not None:
            self.w.close()
        self.r=None
        self.w=None

    def parse(self, line):
        """p.parse(LINE) -> CODE,ARGUMENT

        Break a SMTP/NNTP style line into the response code and
        argument.  CODE is an int, ARGUMENT a bytes object.

        """
        m=_parse_re.match(line)
        if not m:
            raise ValueError("malformed response '%s'" % line)
        return (int(m.group(1)), m.group(2))

    def wait(self):
        """p.wait() -> CODE, ARGUMENT

        Wait for a response and break it into a response code and
        argument using the same rules as self.nntpbits.Protocol.parse.

        """
        self.response=self.receive_line()
        return self.parse(self.response)

    def transact(self, cmd):
        """p.transact(LINE) -> CODE, ARGUMENT

        Send a bytes object, appending the protocol EOL sequence.
        Then wait for a response and break it into a response code and
        argument using the same rules as self.nntpbits.Protocol.parse.

        """
        self.send_line(cmd)
        return self.wait()
