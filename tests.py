#! /usr/bin/python3
import argparse,logging,sys
import nntpbits

def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Subject news server name',
                   default='news')
    p.add_argument('-p', '--port', help='Subject news server port',
                   type=int, default=119)
    p.add_argument('-T', '--trigger', help='Subject news server trigger command',
                   default=None)
    p.add_argument('-g', '--group', help='Test newsgroup name',
                   default='local.test')
    p.add_argument('-e', '--email', help='Test email address',
                   default='invalid@invalid.invalid')
    p.add_argument('-D', '--domain', help='Message-ID domain',
                   default='test.terraraq.uk')
    p.add_argument('-l', '--localport', help='Test server port',
                   type=int, default=1119)
    p.add_argument('-t', '--timelimit', help='Per-test time limit',
                   type=int, default=60)
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    p.add_argument('TEST', help='Tests to run', nargs='*')
    p.add_argument('-L', '--list', help='List tests',
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
    t=cls(r.server, r.port, group=r.group, email=r.email, domain=r.domain,
          localserver=('*', r.localport), timelimit=r.timelimit,
          trigger=r.trigger)
    tested=0
    ok=0
    failed=[]
    for test_name in r.TEST:
        logging.info("Running test %s" % test_name)
        try:
            tested+=1
            t.run_test(test_name)
            ok+=1
        except Exception as e:
            logging.error("Test %s failed: %s" % (test_name, e))
            logging.error("%s" % traceback.format_exc())
            failed+=test_name
    logging.info("%d/%d tests succeeded" % (ok, tested))
    if len(failed) > 0:
        logging.error("failed tests: %s" % ", ".join(failed))
    else:
        logging.info("SUCCESS")
    return 1 if ok < tested else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
