import nntpbits
import logging,re,socket,threading

_command_re=re.compile(b"^(\S+)\s*(.*)$")

class Server(nntpbits.Protocol):
    """NNTP server endpoint

    Construction:
    nntpbits.Server() -> NNTP server object

    Call the socket() or files() method to establish a connection.
    This will cause connected() to be called; that will run in a loop
    processing commands until the peer quits or disconnects.

    The intended use is that your application subclass nntpbits.Server
    and then run an instance in an independent thread for each
    connection it receives, perhaps using the Server.listen() method.

    """
    def __init__(self):
        nntpbits.Protocol.__init__(self)
        self._reset()
        self.commands={
            b'QUIT': self.quit,
        }

    def _reset(self):
        self.finished=False

    def connected(self):
        """s.connected()

        Main NNTP server loop.  Invokes s.command() with successive
        commands received from the peer.  Returns after the peer
        disconnects or sends the QUIT command.

        """
        self.send_line(b"200 Hello")
        r = self.receive_line()
        while r is not None:
            self.command(r)
            if self.finished:
                break
            r = self.receive_line()
        self.disconnect()

    def error(self, description):
        """s.error(DESCRIPTION) -> CONTINUE

        Called when the client does something wrong.  DESCRIPTION is a
        string describing the problem.

        The return values should be True to carry on accepting
        commands, or False to disconnect.

        """
        logging.error(description)
        return True

    def command(self, cmd):
        """s.command(CMD)

        Process a command (as a bytes object)."""

        m=_command_re.match(cmd)
        if not m:
            self.send_line("500 Syntax error")
            self.finished=not self.error("Cannot parse command: %s" % cmd)
            return
        command=m.group(1).upper()
        arguments=m.group(2)
        if command not in self.commands:
            self.send_line("500 Unrecognized command")
            self.finished=not self.error("Unrecognized command: %s" % cmd)
            return
        self.commands[command](arguments)

    def quit(self, arguments):
        self.send_line(b"205 Bye")
        self.finished=True

    @classmethod
    def listen(cls, s, daemon=True):
        """CLASS.listen(SOCKET, [daemon=DAEMON])

        Accept inbound connections on SOCKET and for each connection,
        create an instance of CLASS and use it to service that
        connection.

        This method never returns.  (It could raise an exception,
        though.)

        """
        while True:
            (ns,a)=s.accept()
            def worker(ns, a):
                logging.info("%x: %s connected"
                             % (threading.get_ident(), a))
                cls().socket(ns)
                logging.info("%x: %s disconnected"
                             % (threading.get_ident(), a))
            t=threading.Thread(target=worker, args=[ns,a], daemon=daemon)
            t.start()
