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

    """
    def __init__(self, conncls=nntpbits.ServerConnection):
        self.conncls=conncls
        self.lock=threading.Lock()

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
                self.conncls().socket(ns)
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
