#! /usr/bin/python3
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
import argparse,logging,re,sys,traceback
import nntpbits,inntest

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
    p.add_argument('-a', '--arg', help="TEST:ARG=VALUE per-test argument",
                   type=str, dest='ARGS', action='append', default=[])
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    p.add_argument('TEST', help='Tests to run', nargs='*')
    p.add_argument('-L', '--list', help='List tests',
                   action='store_true')
    r=p.parse_args(argv)
    logging.basicConfig(level=r.debug)
    cls=inntest.Tests
    all_tests=cls.list_tests()
    if r.list:
        for test_name in all_tests:
            print(test_name)
        return
    if len(r.TEST) == 0:
        r.TEST=all_tests
    else:
        for test in r.TEST:
            if test not in all_tests:
                logging.error("No such test as %s" % test)
                sys.exit(1)
    args=dict([test,{}] for test in all_tests)
    for a in r.ARGS:
        m=re.match('^([^:]+):([^=]+)=(.*)$', a)
        test=m.group(1)
        if test not in r.TEST:
            if test not in all_tests:
                logging.error("No such test as %s" % test)
                sys.exit(1)
            else:
                logging.warn("Test %s will not be run" % test)
        arg=m.group(2)
        value=m.group(3)
        args[test][arg]=value
    inntest.address=(r.server,r.port)
    inntest.group=r.group
    inntest.email=r.email
    inntest.doman=r.domain
    inntest.localserveraddress=('*', r.localport)
    inntest.timelimit=r.timelimit
    inntest.trigger=r.trigger
    inntest._fixconfig()        # TODO yuck
    t=cls()
    tested=0
    ok=0
    skipped=[]
    failed=[]
    expected_fail=[]
    for test_name in r.TEST:
        logging.info("Running test %s" % test_name)
        try:
            tested+=1
            state=t.run_test(test_name, **args[test_name])
            if state=='skip':
                skipped.append(test_name)
            elif state=='expected_fail':
                expected_fail.append(test_name)
            else:
                ok+=1
        except Exception as e:
            logging.error("Test %s failed: %s" % (test_name, e))
            logging.error("%s" % traceback.format_exc())
            failed.append(test_name)
    logging.info("%d/%d tests succeeded" % (ok, tested))
    if len(skipped) > 0:
        logging.warn("SKIPPED tests: %s" % ", ".join(skipped))
    if len(expected_fail) > 0:
        logging.warn("EXPECTED FAIL tests: %s" % ", ".join(expected_fail))
    if len(failed) > 0:
        logging.error("FAILED tests: %s" % ", ".join(failed))
    elif len(expected_fail) > 0:
        logging.info("QUALIFIED SUCCESS")
    else:
        logging.info("SUCCESS")
    return 1 if ok + len(skipped) < tested else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
