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
import logging
import re
import socket
import threading

# Regexp matching a command
_command_re = re.compile(b"^(\S+)\s*(.*)$")
# Regexp matching a message ID
_message_id_re = re.compile(b'^<[^@]+@[^@]+>$')

# Text for standard response codes
_responses = {
    100: 'Help text follows',
    101: 'Capabilities follow',
    200: 'Posting allowed',
    201: 'Posting prohibited',
    203: 'Streaming allowed',
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

    By default no useful commands are enabled.  Use a selection of the
    following methods to enable them:
    enable_ihave() -- enable basic peering commands
    enable_streaming() -- enable RFC4644 fast peering commands

    """

    def __init__(self, server, stoppable=True):
        nntpbits.Connection.__init__(self, stoppable=stoppable)
        self._reset()
        self.server = server
        self.commands = {
            b'CAPABILITIES': self.capabilities,
            b'MODE': self.mode,
            b'QUIT': self.quit,
        }
        self.capabilities = [b"VERSION 2",
                             b"IMPLEMENTATION inntest"]
        self.log = logging.getLogger(__name__)

    def enable_ihave(self, state=True):
        """s.enable_ihave([STATE])

        Enables (or disables if STATE=False) the IHAVE command.

        """
        if state == True:
            self.commands[b'IHAVE'] = self.ihave
        else:
            self.commands.pop(b'IHAVE')

    def enable_streaming(self, state=True):
        """s.enable_streaming([STATE])

        Enables (or disables if STATE=False) the RFC4644 streaming
        commands.

        """
        if state == True:
            self.commands[b'CHECK'] = self.check
            self.commands[b'TAKETHIS'] = self.takethis
        else:
            self.commands.pop(b'CHECK')
            self.commands.pop(b'TAKETHIS')

    def enable(self, feature, state=True):
        """s.enable(FEATURE[, STATE])

        Enables (or disables if STATE=False) a named feature, or a list
        of features.  Valid features are:
        ihave -- just the IHAVE command
        streaming -- RFC4644 streaming commands
        peering -- all peering commands
        """
        if isinstance(feature, list):
            for item in feature:
                self.enable(item, state)
        else:
            if feature.lower() == 'ihave':
                self.enable_ihave(state)
            elif feature.lower() == 'streaming':
                self.enable_streaming(state)
            elif feature.lower() == 'peering':
                self.enable_ihave(state)
                self.enable_streaming(state)
            else:
                raise Exception("unrecognized feature '%s'" % feature)

    def _reset(self):
        """s._reset()

        Reset object state.

        """
        self.finished = False

    def connected(self):
        """s.connected()

        Main NNTP server loop.  Invokes s.command() with successive
        commands received from the peer.  Returns after the peer
        disconnects or sends the QUIT command.

        """
        try:
            self.respond(200)
            r = self.receive_line()
            while r is not None:
                self.command(r)
                if self.finished:
                    break
                r = self.receive_line()
        except BrokenPipeError:
            pass
        except ConnectionResetError:
            pass
        finally:
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
        self.commands[nntpbits._normalize(command).upper()] = callback

    def respond(self, response, description=None, log_type=None, flush=True,
                detail=""):
        """s.respond(RESPONSE, DESCRIPTION)

        Send a response message to the peer.

        """
        if log_type is None and response >= 500:
            log_type = 'error'
        if description is None:
            if response in _responses:
                description = _responses[response]
            else:
                description = "Derp"
        if isinstance(description, bytes):
            description = str(description, 'ascii')
        if log_type is not None:
            method = getattr(self.log, log_type)
            method("%x: %s %s"
                   % (threading.get_ident(), description, detail))
        self.send_line("%d %s" % (response, description), flush=flush)

    def command(self, cmd):
        """s.command(CMD)

        Process a command (as a bytes object).

        If the syntax of CMD is valid then the command is looked up in
        s.commands.  The key will be an upper-case bytes object.  If
        found then the value will be called with the argument as a
        bytes object.

        """
        m = _command_re.match(cmd)
        if not m:
            return self.respond(500, "Malformed command")
        command = m.group(1).upper()
        arguments = m.group(2)
        if command not in self.commands:
            return self.respond(500, detail=command)
        self.commands[command](arguments)

    def ihave(self, arguments):
        """s.ihave(ARGUMENTS)

        Implementation of the NNTP IHAVE command.

        """
        if not _message_id_re.match(arguments):
            return self.respond(501)
        (rc, argument) = self.server.ihave_check(arguments)
        self.respond(rc, argument)
        if rc == 335:
            article = self.receive_lines()
            (rc, argument) = self.server.ihave(arguments, article)
            self.respond(rc, argument)

    def check(self, arguments):
        """s.check(ARGUMENTS)

        Implementation of the NNTP CHECK command.

        """
        if not _message_id_re.match(arguments):
            return self.respond(501)
        (rc, argument) = self.server.ihave_check(arguments)
        if rc == 335:
            return self.respond(238, arguments)
        elif rc == 435:
            return self.respond(431, arguments)
        elif rc == 436:
            return self.respond(438, arguments)
        return self.respond(rc, argument)

    def takethis(self, arguments):
        """s.takethis(ARGUMENTS)

        Implementation of the NNTP TAKETHIS command.

        """
        if not _message_id_re.match(arguments):
            return self.respond(501)
        article = self.receive_lines()
        (rc, argument) = self.server.ihave_check(arguments)
        if rc == 335:
            (rc, argument) = self.server.ihave(arguments, article)
            if rc == 235:
                return self.respond(239, arguments)
            if rc == 437:
                return self.respond(439, arguments)
        elif rc == 435:
            return self.respond(439, arguments)
        if rc == 436:
            self.respond(400)
            self.finished = True
        return self.respond(rc, argument)

    _mode_re = re.compile(b'^\\s*(\\S*)\s*$')

    def mode(self, arguments):
        """s.mode(ARGUMENTS)

        Implementation of NNTP MODE command."""
        m = ServerConnection._mode_re.match(arguments)
        if not m:
            return self.respond(501)
        mode = m.group(1).upper()
        if mode == b'STREAM' and b'TAKETHIS' in self.commands:
            return self.respond(203)
        return self.respond(501, 'Unrecognized/unsupported mode')

    def capabilities(self, arguments):
        """s.capabilities(ARGUMENTS)

        Implementation of the NNTP CAPABILITIES command.

        """
        capabilities = list(self.capabilities)
        for cmd in [b'IHAVE', b'POST', b'NEWNEWS', b'OVER', b'HDR', b'LIST']:
            if cmd in self.commands:
                capabilities.append(cmd)
        if [b'TAKETHIS'] in self.commands:
            capabilities.append(b'STREAMING')
        self.respond(110, flush=False)
        self.send_lines(self.server.capabilities(capabilities))

    def quit(self, arguments):
        """s.quit(ARGUMENTS)

        Implementation of the NNTP QUIT command.

        """
        self.respond(205)
        self.finished = True
