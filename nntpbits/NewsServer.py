import nntpbits
import logging,socket,threading,time

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
        while True:
            (ns,a)=s.accept()
            def worker(ns, a):
                logging.info("%x: %s connected"
                             % (threading.get_ident(), a))
                self.conncls(self).socket(ns)
                logging.info("%x: %s disconnected"
                             % (threading.get_ident(), a))
            t=threading.Thread(target=worker, args=[ns,a], daemon=daemon)
            t.start()

    def listen_address(self, address, port, wait=False, daemon=True):
        """ns.listen(NAME, PORT[, wait=WAIT][, daemon=DAEMON])

        Resolves NAME:PORT into a list of addresses and invokes
        ns.listen_socket in a subthread for each of them.

        If the WAIT argument is set to True then this method doesn't
        return but instead blocks.

        """
        addrs=socket.getaddrinfo(address, port, 0, socket.SOCK_STREAM, 0,
                                 socket.AI_PASSIVE|socket.AI_ADDRCONFIG)
        for addr in addrs:
            (family, type, proto, canonname, sockaddr)=addr
            s=socket.socket(family,type,proto)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(sockaddr)
            s.listen(socket.SOMAXCONN)
            t=threading.Thread(target=self.listen_socket, args=[s],daemon=True)
            t.start()
        while wait:
            time.sleep(86400)

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
        return (440, "Posting not implemented")

    def post(self, article):
        """ns.post(ARTICLE) -> (RESPONSE, ARGUMENT)

        Implementation of the second half of the POST command.

        ARTICLE is a list of bytes objects.  The return value is an
        NNTP response and argument.  The response should be 240 for
        success and 441 for an error.

        """
        return (441, "Posting not implemented")

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
        return (480, "Peering not implemented")

    def ihave(self, ident, article):
        """ns.ihave(IDENT, ARTICLE) -> (RESPONSE, ARGUMENT)

        Implementation of the second half of the IHAVE command.

        IDENT is a bytes object containing the message ID submitted by
        the peer and ARTICLE is a list of bytes objects.  The return
        value is an NNTP response and argument.  The response should
        be 235 on success, 436 to request a retry and 437 if the
        article was rejected.

        """
        return (480, "Peering not implemented")
