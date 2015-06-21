#! /usr/bin/python3
import argparse,logging,socket,sys,threading,time
import nntpbits

def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Server name',
                   default='news')
    p.add_argument('-p', '--port', help='Server port',
                   type=int, default=119)
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    r=p.parse_args(argv)
    logging.basicConfig(level=r.debug)
    addrs=socket.getaddrinfo(r.server, r.port, 0, socket.SOCK_STREAM, 0,
                             socket.AI_PASSIVE|socket.AI_ADDRCONFIG)
    for addr in addrs:
        (family, type, proto, canonname, sockaddr)=addr
        s=socket.socket(family,type,proto)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(sockaddr)
        s.listen(socket.SOMAXCONN)
        def worker(s):
            nntpbits.ServerConnection.listen(s)
        t=threading.Thread(target=worker, args=[s],daemon=True)
        t.start()
    while True:
        time.sleep(86400)

if __name__ == '__main__':
    main(sys.argv[1:])
