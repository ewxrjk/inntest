#! /usr/bin/python3
import argparse,logging,os,sys
import nntpbits

def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Server name',
                   default='news')
    p.add_argument('-p', '--port', help='Server port',
                   type=int, default=119)
    p.add_argument('GROUP', help='Group name', type=str)
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    r=p.parse_args(argv)
    logging.basicConfig(level=r.debug)
    dump_group(r.server, r.port, r.GROUP)

def dump_group(server, port, group):
    client=nntpbits.Client()
    client.connect((server, port))
    (count, low, high)=client.group(group)
    linesep=bytes(os.linesep, 'ascii')
    for number in range(low, high+1):
        article=client.article(number)
        if article is not None:
            with open("%s:%d" % (group,number), "wb") as f:
                for line in article:
                    f.write(line)
                    f.write(linesep)
                f.flush()
    client.quit()

if __name__ == '__main__':
    main(sys.argv[1:])
