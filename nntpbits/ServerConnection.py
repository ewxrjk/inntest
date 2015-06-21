import nntpbits
import logging,re,socket,threading

_command_re=re.compile(b"^(\S+)\s*(.*)$")
_message_id_re=re.compile(b'^<[^@]+@[^@]+>$')

_responses={
    100: 'Help text follows',
    101: 'Capabilities follow',
    200: 'Posting allowed',
    201: 'Posting prohibited',
    205: 'Bye',
    215: 'Information follows',
    220: 'Article follows',
    221: 'Header follows',
    222: 'Body follows',
    223: 'Article selected',
    224: 'Overview information follows',
    225: 'Headers follow',
    230: 'New message IDs follow',
    231: 'New groups follow',
    235: 'OK',
    240: 'OK',
    335: 'Send article',
    340: 'Send article',
    400: 'Service no longer available',
    401: 'Wrong mode',
    403: 'It broke',
    411: 'No such group',
    412: 'No group selected',
    420: 'No article selected',
    421: 'No next article',
    422: 'No previous article',
    423: 'No such article',
    430: 'No such article',
    435: 'Not wanted',
    436: 'Try later',
    437: 'Not wanted',
    440: 'Posting prohibited',
    441: 'Posting failed',
    480: 'Authentication required',
    483: 'Confidentiality required',
    500: 'Unknown command',
    501: 'Syntax error',
    502: 'Begone',
    503: 'Not supported',
    504: 'Invalid base64',
}

class ServerConnection(nntpbits.Connection):
    """NNTP server endpoint

    Construction:
    nntpbits.ServerConnection(SERVER) -> NNTP server connection object

    SERVER is the news server backend, usually a subclass of
    nntpbits.NewsServer.

    Call the socket() or files() method to establish a connection.
    This will cause connected() to be called; that will run in a loop
    processing commands until the peer quits or disconnects.

    The intended use is that your application subclass
    nntpbits.ServerConnection and then run an instance in an
    independent thread for each connection it receives, perhaps using
    the ServerConnection.listen() method.

    """
    def __init__(self, server, stoppable=True):
        nntpbits.Connection.__init__(self, stoppable=stoppable)
        self._reset()
        self.server=server
        self.commands={
            b'CAPABILITIES': self.capabilities,
            b'IHAVE': self.ihave,
            b'QUIT': self.quit,
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
        self.respond(200)
        r=self.receive_line()
        while r is not None:
            self.command(r)
            if self.finished:
                break
            r=self.receive_line()
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
        self.commands[nntpbits._normalize(command).upper()]=callback

    def respond(self, response, description=None, log=None, flush=True,
                detail=""):
        """s.respond(RESPONSE, DESCRIPTION)

        Send an error message to the peer.

        """
        if log is None and response >= 500:
            log=logging.error
        if description is None:
            if response in _responses:
                description=_responses[response]
            else:
                description="Derp"
        if log is not None:
            log("%s: %s %s" % (threading.get_ident(), description, detail))
        self.send_line("%d %s" % (response, description), flush=flush)

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
            return self.respond(500, "Malformed command")
        command=m.group(1).upper()
        arguments=m.group(2)
        if command not in self.commands:
            return self.respond(500, detail=command)
        self.commands[command](arguments)

    def ihave(self, arguments):
        """s.ihave(ARGUMENTS)

        Implementation of the NNTP IHAVE command."""
        if not _message_id_re.match(arguments):
            return self.respond(501)
        (rc,argument)=self.server.ihave_check(arguments)
        self.respond(rc,argument)
        if rc==335:
            article=self.receive_lines()
            (rc,argument)=self.server.ihave(arguments, article)
            self.respond(rc, argument)

    def capabilities(self, arguments):
        """s.capabilities(ARGUMENTS)

        Implementation of the NNTP CAPABILITIES command.

        """
        capabilities=list(self.capabilities)
        for cmd in [b'IHAVE', b'POST', b'NEWNEWS', b'OVER', b'HDR', b'LIST']:
            if cmd in self.commands:
                capabilities.append(cmd)
        self.respond(110, flush=False)
        self.send_lines(self.server.capabilities(capabilities))

    def quit(self, arguments):
        """s.quit(ARGUMENTS)

        Implementation of the NNTP QUIT command.

        """
        self.respond(205)
        self.finished=True
