#! /usr/bin/python3
import argparse,logging,sys
import nntpbits.nntp

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
    article=sys.stdin.buffer.read()
    post(r.server, r.port, article)

def post(server, port, article):
    client=nntpbits.nntp.client()
    client.connect((server, port))
    client.post(article)
    client.quit()

if __name__ == '__main__':
    main(sys.argv[1:])
