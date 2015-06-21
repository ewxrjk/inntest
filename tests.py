#! /usr/bin/python3
import argparse,logging,sys
import nntpbits

def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Server name',
                   default='news')
    p.add_argument('-p', '--port', help='Server port',
                   type=int, default=119)
    p.add_argument('-g', '--group', help='Test newsgroup name',
                   default='local.test')
    p.add_argument('-e', '--email', help='Test email address',
                   default='invalid@invalid.invalid')
    p.add_argument('-D', '--domain', help='Message-ID domain',
                   default='test.terraraq.uk')
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    p.add_argument('TEST', help='Tests to run', nargs='*')
    p.add_argument('-l', '--list', help='List tests',
                   action='store_true')
    r=p.parse_args(argv)
    cls=nntpbits.Tests
    if r.list:
        for test_name in cls.list_tests():
            print(test_name)
        return
    if len(r.TEST) == 0:
        r.TEST=cls.list_tests()
    logging.basicConfig(level=r.debug)
    client=nntpbits.ClientConnection()
    client.connect((r.server, r.port))
    t=cls(client, group=r.group, email=r.email, domain=r.domain)
    for test_name in r.TEST:
        t.run_test(test_name)
    client.quit()

if __name__ == '__main__':
    main(sys.argv[1:])
