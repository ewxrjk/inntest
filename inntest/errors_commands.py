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
import inntest
import nntpbits
from inntest.list import _list_wildmat
from inntest.errors_group import _article_commands
from inntest.running import *


def test_errors_bad_commands():
    """inntest.Tests.test_errors_bad_commands()

    Test error behavior for bad commands.

    """
    ret = [None]
    with inntest.connection() as conn:
        def check(which):
            code, arg = conn.transact(b'NOTINNNTP')
            if code != 500:
                fail("Wrong response for bad command: %s"
                     % conn.response)
            for cmd in [b'MODE', b'LIST']:
                code, arg = conn.transact([cmd, b'NOTINNNTP'])
                if code != 501:
                    fail("%s: wrong response for bad argument: %s"
                         % (cmd, conn.response))
            # INN accepts this, presumably relying on 3977 s4.3
            code, arg = conn.transact([b'LIST ACTIVE',
                                       inntest.hierarchy+b'[.]*'])
            if code != 501 and code != 215:
                fail("LIST ACTIVE: wrong response for bad argument: %s"
                     % conn.response)
            if code == 215:
                conn.receive_lines()
            subcommands = conn.capability_arguments(b'LIST')
            if b'HEADERS' in subcommands:
                code, arg = conn.transact(b'LIST HEADERS NOTINNNTP')
                if code != 501:
                    fail("LIST HEADERS: wrong response for bad argument: %s"
                         % conn.response)
            for subcommand in subcommands:
                if subcommand not in _list_wildmat:
                    code, arg = conn.transact([b'LIST', subcommand, b'*'])
                    if code != 501:
                        fail("LIST %s: wrong response for bad argument: %s"
                             % (subcommand, conn.response))
        check('first')
        conn._mode_reader()     # cheating
        check("second")
        for cmd in _article_commands:
            code, arg = conn.transact([cmd, b'1', b'2', b'3'])
            if code != 501:
                fail("%s: wrong response for bad argument: %s"
                     % (cmd, conn.response))
            code, arg = conn.transact([cmd, b'junk'])
            if code != 501:
                fail("%s: wrong response for bad argument: %s"
                     % (cmd, conn.response))
            code, arg = conn.transact([cmd, b'junk@junk'])
            if code != 501:
                fail("%s: wrong response for bad argument: %s"
                     % (cmd, conn.response))
        for cmd in [b'NEWNEWS *', b'NEWGROUPS']:
            for arg in [b'',
                        b'990101',
                        b'19990101',
                        b'990101000000',
                        b'19990101000000',
                        b'19990101 000000 BST',
                        b'19990101 000000 GMT GMT',
                        b'19990101 240000',
                        b'19990101 000000 +0000',
                        b'19990101 000000 0000',
                        b'19990101 000000 -0000',
                        b'19990101 000000 00']:
                code, arg = conn.transact([cmd, arg])
                if code != 501:
                    fail("%s: wrong response for bad argument: %s"
                         % (cmd, conn.response))
    return ret[0]


_invalid_reader = [
    [b'GROUP', 501],
    [B'GROUP this.that 1-10', 501],
    [b'LISTGROUP this.that 1-10 the.other', 501],
    [b'LISTGROUP this.that 1-10-20', 501],
    [b'LISTGROUP this.that junk', 501],
    [b'LAST ORDERS', 501],
    [b'NEXT CUBE', 501],
    [b'POST LETTER', 501],
    [b'POST <junk@example.com>', 501],
    [b'DATE ME', 501],
    [b'HELP ME', 501],
    [b'NEWGROUPS', 501],
    [b'NEWNEWS', 501],
]
_invalid_transit = [
    [b'IHAVE', 501, 435],
    [b'IHAVE junk', 501, 435],
    [b'IHAVE <junk', 501, 435],
    [b'IHAVE <junk@example.com', 501, 435],
    [b'IHAVE <junk@example.com> wombats', 501, 435],
]
_invalid_streaming = [
    [b'CHECK', 501, 438],
    [b'CHECK junk', 501, 438],
    [b'CHECK <junk', 501, 438],
    [b'CHECK <junk@example.com', 501, 438],
    [b'CHECK <junk@example.com> wombats', 501, 438],
    [b'TAKETHIS', 501, 439],
    [b'TAKETHIS junk', 501, 439],
    [b'TAKETHIS <junk', 501, 439],
    [b'TAKETHIS <junk@example.com', 501, 439],
    [b'TAKETHIS <junk@example.com> wombats', 501, 439],
]
_invalid_common = [
    [b'MODE NONSENSE', 501],
    [b'QUIT SMOKING', 501],
]

for cmd in [b'ARTICLE', b'HEAD', b'BODY', b'STAT']:
    for arg in [b'junk',
                b'<junk',
                b'<junk@example.com',
                b'junk@example.com>',
                b'1 2',
                b'1a',
                b'00000000000000001',
                b'<junk@example.com> wombats']:
        _invalid_reader.append([cmd + b' ' + arg, 501])


def test_errors_syntax_reader():
    """inntest.Tests.test_errors_syntax_reader()

    Test for correct response to a variety of syntax errors in reader
    mode.

    """
    with inntest.connection() as conn:
        conn._mode_reader()
        return _test_errors_syntax(conn, _invalid_common + _invalid_reader)


def test_errors_syntax_transit():
    """inntest.Tests.test_errors_syntax_transit()

    Test for correct response to a variety of syntax errors in transit
    mode.

    """
    with inntest.connection() as conn:
        return _test_errors_syntax(conn, _invalid_common + _invalid_transit)


def test_errors_syntax_streaming():
    """inntest.Tests.test_errors_syntax_streaming()

    Test for correct response to a variety of syntax errors in
    streaming commands.

    """
    with inntest.connection() as conn:
        if not conn.streaming():
            return skip()
        return _test_errors_syntax(conn, _invalid_streaming)


def _test_errors_syntax(conn, cases):
    for case in cases:
        cmd = case[0]
        response = case[1]
        if cmd[:8] == b'TAKETHIS':  # ugly special case
            conn.send_line(cmd)
            conn.send_line(b'.')
            code, arg = conn.wait()
        else:
            code, arg = conn.transact(cmd)
        # INN violates RFC3977 and sends 435/438/439 for malformed message IDs.
        # For example innfeed (incorrectly) retries on 501 responses.
        if len(case) > 2 and code == case[2]:
            compat("%s: expected %d got %s"
                   % (str(cmd, 'ascii'), case[1],
                      str(conn.response, 'ascii')))
        else:
            if code != response:
                fail("%s: expected %d got %s"
                     % (str(cmd, 'ascii'), response,
                        str(conn.response, 'ascii')))
