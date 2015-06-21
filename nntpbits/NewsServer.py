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
import logging,select,socket,threading,time,traceback

class NewsServer(object):
    """NewsServer() -> NNTP server object
    NewsServer(CLASS) -> NNTP server object

    Constructs a generic news server.

    This class is intended to act as base class for a news server with
    more interesting behavior.

    The CLASS argument should be a subclass of
    nntpbits.ServerConnection, and is used to support inbound NNTP
    connections.

    Override methods are responsible for locking (if required).  Use
    self.lock, which is created by the constructor.

    """
    def __init__(self, conncls=nntpbits.ServerConnection):
        self.conncls=conncls
        self.lock=threading.Lock()

    # -------------------------------------------------------------------------
    # Listening

    def listen_socket(self, s, daemon=True):
        """ns.listen(SOCKET, [daemon=DAEMON])

        If the argument is a socket then accepts connections on that
        socket and services them via server connections in subthreads.

        This method never returns.  (It could raise an exception,
        though.)

        """
        s.setblocking(False)
        while True:
            nntpbits._maybe_stop()
            select.select([s],[],[],1.0)
            try:
                (ns,a)=s.accept()
            except BlockingIOError:
                continue
            def worker(ns, a):
                try:
                    logging.info("%x: connected %s"
                                 % (threading.get_ident(), a))
                    self.conncls(self).socket(ns)
                    logging.info("%x: disconnected %s"
                                 % (threading.get_ident(), a))
                except nntpbits._Stop:
                    logging.debug("%x: client stopped %s"
                                  % (threading.get_ident(), a))
                except Exception as e:
                    logging.error("%x: client error: %s %s"
                                  % (threading.get_ident(), e, a))
                    logging.error("%x: %s"
                                  % (threading.get_ident(), traceback.format_exc()))
                finally:
                    nntpbits.finished_thread()
            t=threading.Thread(target=worker, args=[ns,a], daemon=daemon)
            nntpbits.start_thread(t)

    def listen_address(self, address, port, wait=False, daemon=True):
        """ns.listen(ADDRESS, PORT[, wait=WAIT][, daemon=DAEMON])

        Resolves ADDRESS:PORT into a list of addresses and invokes
        ns.listen_socket in a subthread for each of them.

        ADDRESS would normally be a local address (by name or number).
        The special address '*' means both the IPv4 and IPv6 all-hosts
        addresses, and the special address '*localhost' means both the
        IPv4 and IPv6 localhost addresses (even if 'localhost' does
        not resolve to both).

        If the WAIT argument is set to True then this method doesn't
        return but instead blocks.

        """
        if address == '*':
            addresses = ['0.0.0.0','::']
        elif address == '*localhost':
            addresses = ['127.0.0.1','::1']
        else:
            addresses = [address]
        addrs=[]
        for address in addresses:
            addrs.extend(socket.getaddrinfo(address, port,
                                            0, socket.SOCK_STREAM, 0,
                                            socket.AI_PASSIVE
                                            |socket.AI_ADDRCONFIG))
        for addr in addrs:
            (family, type_, proto, canonname, sockaddr)=addr
            s=socket.socket(family,type_,proto)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(sockaddr)
            s.listen(socket.SOMAXCONN)
            def worker(s, sockaddr):
                try:
                    logging.info("%x: listener started %s"
                                 % (threading.get_ident(), sockaddr))
                    self.listen_socket(s, daemon=daemon)
                except nntpbits._Stop:
                    logging.debug("%x: listener stopped %s"
                                  % (threading.get_ident(), sockaddr))
                except Exception as e:
                    logging.error("%x: listener error %s %s"
                                  % (threading.get_ident(), e, sockaddr))
                    logging.error("%x: %s"
                                  % (threading.get_ident(),
                                     traceback.format_exc()))
                finally:
                    nntpbits.finished_thread()
            t=threading.Thread(target=worker, args=[s,sockaddr], daemon=daemon)
            nntpbits.start_thread(t)
        while wait:
            nntpbits._maybe_stop()
            time.sleep(1)

    # -------------------------------------------------------------------------
    # CAPABILITIES

    def capabilities(self, caps):
        """ns.capabilities(CAPABILITIES) -> CAPABILITIES

        Returns a (possibly modified) list of server capabilities.

        """
        return caps

    # -------------------------------------------------------------------------
    # POST

    def post_check(self, article):
        """ns.post_check() -> (RESPONSE, ARGUMENT)

        Implementation of the first half of the POST command.

        The return value is an NNTP response and argument, normally
        340 if posting is permitted and 440 if not; or 401 if this is
        a peering-only server.

        """
        return (440, "Posting not available")

    def post(self, article):
        """ns.post(ARTICLE) -> (RESPONSE, ARGUMENT)

        Implementation of the second half of the POST command.

        ARTICLE is a list of bytes objects.  The return value is an
        NNTP response and argument.  The response should be 240 for
        success and 441 for an error.

        """
        return (441, "Posting not available")

    # -------------------------------------------------------------------------
    # IHAVE

    def ihave_check(self, ident):
        """ns.ihave_check(IDENT) -> (RESPONSE, ARGUMENT)

        Implementation of the first half of the IHAVE command.  IDENT
        is a bytes object containing the message ID submitted by the
        peer.

        The return value is an NNTP response and argument.  The
        response should be 335 if the article is acceptable, 435 if
        not, 436 to request a retry later or 480 if IHAVE is not
        permitted.

        """
        return (480, "Peering not available")

    def ihave(self, ident, article):
        """ns.ihave(IDENT, ARTICLE) -> (RESPONSE, ARGUMENT)

        Implementation of the second half of the IHAVE command.

        IDENT is a bytes object containing the message ID submitted by
        the peer and ARTICLE is a list of bytes objects.  The return
        value is an NNTP response and argument.  The response should
        be 235 on success, 436 to request a retry and 437 if the
        article was rejected.

        """
        return (480, "Peering not available")
