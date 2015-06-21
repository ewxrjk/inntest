#! /usr/bin/python3
import argparse,logging,sys
import nntpbits

stopped=False

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
    server=nntpbits.NewsServer()
    try:
        server.listen_address(r.server, r.port, wait=True, daemon=True, stop=stop)
    except KeyboardInterrupt:
        global stopped
        logging.info("stopping server")
        stopped=True
        sys.exit(0)

def stop():
    if stopped:
        raise Exception("stop server")

if __name__ == '__main__':
    main(sys.argv[1:])
