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
import argparse
import logging
import re
import sys
import traceback
import nntpbits
import inntest


class CaptureHandler(logging.Handler):
    def __init__(self, level):
        super().__init__(level)
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def clear(self):
        self.records = []


def escape(s):
    return re.sub('[&<>\"\']', (lambda m: "&#%d;" % int(ord(m.group(0)))), s)


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Subject news server name',
                   default='news')
    p.add_argument('-p', '--port', help='Subject news server port',
                   type=int, default=119)
    p.add_argument('-T', '--trigger',
                   help='Subject news server trigger command')
    p.add_argument('-g', '--group', help='Test newsgroup name')
    p.add_argument('-e', '--email', help='Test email address')
    p.add_argument('-D', '--domain', help='Message-ID domain')
    p.add_argument('-l', '--localport', help='Test server port',
                   type=int, default=1119)
    p.add_argument('-t', '--timelimit', help='Per-test time limit',)
    p.add_argument('-a', '--arg', help="TEST:ARG=VALUE per-test argument",
                   type=str, dest='ARGS', action='append', default=[])
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    p.add_argument('TEST', help='Tests to run', nargs='*')
    p.add_argument('-L', '--list', help='List tests',
                   action='store_true')
    p.add_argument('-H', '--html', help='HTML output',
                   type=str, dest='HTML', default=None)
    r = p.parse_args(argv)
    logging.basicConfig(level=r.debug)
    all_tests = inntest.list_tests()
    if r.list:
        for test_name in all_tests:
            print(test_name)
        return
    if len(r.TEST) == 0:
        r.TEST = all_tests
    else:
        for test in r.TEST:
            if test not in all_tests:
                logging.error("No such test as %s" % test)
                sys.exit(1)
    args = dict([test, {}] for test in all_tests)
    for a in r.ARGS:
        m = re.match('^([^:]+):([^=]+)=(.*)$', a)
        test = m.group(1)
        if test not in r.TEST:
            if test not in all_tests:
                logging.error("No such test as %s" % test)
                sys.exit(1)
            else:
                logging.warning("Test %s will not be run" % test)
        arg = m.group(2)
        value = m.group(3)
        args[test][arg] = value
    inntest.configure(address=(r.server, r.port),
                      group=r.group,
                      email=r.email,
                      domain=r.domain,
                      localserveraddress=('*', r.localport),
                      timelimit=r.timelimit,
                      trigger=r.trigger)
    tested = 0
    total_success = 0
    partial_success = 0
    skips = []
    fails = []
    compats = []
    xfails = []
    capture = CaptureHandler(level=r.debug)
    if r.HTML:
        logging.getLogger().addHandler(capture)
        html = open(r.HTML, "w")
        html.write("<head>\n")
        html.write('<link rel=stylesheet type="text/css" href="tests.css">\n')
        html.write("<body>\n")
        html.write("<table class=tests>\n")
        html.write("<tr><td>test</td>\n")
        html.write("<td>outcome</td>\n")
        html.write("<td>xfail</td>\n")
        html.write("<td>compat</td>\n")
        html.write("<td>skip</td>\n")
        html.write("<td>log</td>\n")
    for test_name in r.TEST:
        tested += 1
        capture.clear()
        t_fails, t_xfails, t_compats, t_skips = inntest.run_test(
            test_name, **args[test_name])
        if r.HTML:
            html.write("<tr><td class=testname>%s</td>\n" % test_name)
            if len(t_fails):
                html.write("<td class=fails>%d</td>\n" % len(t_fails))
            else:
                html.write("<td class=ok>OK</td>\n")
            if len(t_xfails):
                html.write("<td class=xfails>%d</td>\n" % len(t_xfails))
            else:
                html.write("<td class=noxfails>&nbsp;</td>\n")
            if len(t_compats):
                html.write("<td class=compats>%d</td>\n" % len(t_compats))
            else:
                html.write("<td class=nocompats>&nbsp;</td>\n")
            if len(t_skips):
                html.write("<td class=skips>%d</td>\n" % len(t_skips))
            else:
                html.write("<td class=noskips>&nbsp;</td>\n")
            if len(capture.records):
                html.write("<td class=logs><pre>")
                for record in capture.records:
                    html.write(escape(record.message)+"\n")
                html.write("</pre></td>\n")
            else:
                html.write("<td class=nologs>&nbsp;</td>\n")
            html.write("</tr>\n")
        fails.extend(t_fails)
        xfails.extend(t_xfails)
        compats.extend(t_compats)
        skips.extend(t_skips)
        if len(t_fails) + len(t_xfails) + len(t_skips) == 0:
            total_success += 1
        elif len(fails) == 0:
            partial_success += 1
    logging.info("%d test cases, %d total success, %d partial success"
                 % (tested, total_success, partial_success))
    if len(skips) > 0:
        logging.warning("%d skips" % len(skips))
    if len(xfails) > 0:
        logging.warning("%d expected fails" % len(xfails))
    if len(compats) > 0:
        logging.info("%d compatibility variations" % len(compats))
    if len(fails) > 0:
        logging.error("%d fails" % len(fails))
    if r.HTML:
        html.write("</table>\n")
        html.close()
    return 1 if len(fails) > 0 else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
