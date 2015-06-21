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
            b'CAPABILITIES': self.capabilities,
        }
        self.capabilities=[b"VERSION 2",
                           b"IMPLEMENTATION inntest"]

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

    def register(self, command, callback):
        """s.register(COMMAND, CALLBACK)

        When COMMAND is received, CALLBACK(ARGUMENTS) will be called.
        It must carry out the complete implementation of the command,
        i.e. checking argument syntax and issuing any response.

        This method can be used either to add new commands or to
        over-ride existing ones.  (The latter could also be done by
        overriding them as subclass methods.)

        """
        if isinstance(command, str):
            command=bytes(command,'ascii')
        self.commands[command.upper()]=callback

    def error(self, description):
        """s.error(DESCRIPTION) -> CONTINUE

        Called when the client does something wrong.  DESCRIPTION is a
        string describing the problem.

        The return values should be True to carry on accepting
        commands, or False to disconnect.

        """
        logging.error("%s: %s" % (threading.get_ident(), description))
        return True

    def command(self, cmd):
        """s.command(CMD)

        Process a command (as a bytes object).

        If the syntax of CMD is valid then the command is looked up in
        s.commands.  The key will be an upper-case bytes object.  If
        found then the value will be called with the argument as a
        bytes object.

        """
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
        """s.quit(ARGUMENTS)

        Implementation of the NNTP QUIT command.

        """
        self.send_line(b"205 Bye")
        self.finished=True

    def capabilities(self, arguments):
        """s.capabilities(ARGUMENTS)

        Implementation of the NNTP CAPABILITIES command.

        """
        capabilities=list(self.capabilities)
        for cmd in [b'IHAVE', b'POST', b'NEWNEWS', b'OVER', b'HDR', b'LIST']:
            if cmd in self.commands:
                capabilities.append(cmd)
        self.send_line("110 Capabilities", flush=False)
        self.send_lines(capabilities)

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
