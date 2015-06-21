"""Client/server connection base class"""
import logging,re,select,socket
import nntpbits

_parse_re=re.compile(b"^([0-9]{3}) (.*)$")

class Connection(object):
    """Base class for text-based network protocols

    Construction:
    nntpbits.Connection() -> protocol endpoint object
    nntpbits.Connection(eol=EOL) -> protocol endpoint object
    nntpbits.Connection(stop=STOP) -> protocol endpoint object

    EOL must be a byte string.  The default is CRLF.

    STOP is called while waiting for IO.  It can raise an exception to
    abandon the connection.

    """

    def __init__(self, eol=b"\r\n", stop=lambda: False):
        self.eol=eol
        self.stop=stop
        self.sock=None

    def files(self, r, w):
        """p.files(r=READER, w=WRITER)

        Use binary files READER and WRITER for IO.

        """
        self.r=r
        self.w=w
        self.buffer=b''
        self.buffer_index=0
        self.eof=False
        self.connected()

    def socket(self, s):
        """p.socket(SOCKET)

        Use a connected socket SOCKET for IO.

        """
        self.sock=s
        self.files(r=None, w=s.makefile(mode='wb'))
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
        self.w.write(nntpbits._normalize(line))
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
            line=nntpbits._normalize(line)
            if len(line) > 0 and line[0] == b'.':
                self.send_line(b'.'+line, flush=False)
            else:
                self.send_line(line, flush=False)
        self.send_line(b'.')

    def _fill(self):
        if self.buffer_index < len(self.buffer):
            return True
        try:
            if self.sock is not None:
                try:
                    self.sock.setblocking(False)
                    bs=self.sock.recv(4096)
                finally:
                    self.sock.setblocking(True)
            else:
                bs=self.r.read()
            if bs is None:
                return False
            self.buffer=bs
            self.buffer_index=0
            if len(bs) == 0:
                self.eof=True
            return True
        except BlockingIOError:
            return False

    def _read_byte(self):
        while self.buffer_index >= len(self.buffer):
            while not self._fill():
                select.select([self.sock],[],[],1.0)
                self.stop()
            if self.eof:
                return None
        ch=self.buffer[self.buffer_index:self.buffer_index+1]
        self.buffer_index+=1
        return ch

    def receive_line(self, stop_check=True):
        """p.receive_line() -> LINE

        Receive a line as a bytes object.  The protocol EOL sequence
        is removed.

        Returns None if there is no more input.

        """
        if stop_check:
            self.stop()
        line=b"";
        while not self._complete(line):
            ch=self._read_byte()
            if ch is None:
                return None
            line += ch
        line=line[0:-len(self.eol)]
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
        line=self.receive_line(stop_check=False)
        while line != b".":
            if line is None:
                return None
            if len(line) > 0 and line[0] == b'.':
                line=line[1:]
            lines.append(line)
            line=self.receive_line(stop_check=False)
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
        argument using the same rules as self.nntpbits.Connection.parse.

        """
        self.response=self.receive_line()
        return self.parse(self.response)

    def transact(self, cmd):
        """p.transact(LINE) -> CODE, ARGUMENT

        Send a bytes object, appending the protocol EOL sequence.
        Then wait for a response and break it into a response code and
        argument using the same rules as self.nntpbits.Connection.parse.

        """
        self.send_line(cmd)
        return self.wait()
