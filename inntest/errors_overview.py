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
from inntest.errors_group import _number_deltas
from inntest.running import *


def test_errors_group_overview():
    """inntest.Tests.test_errors_group_overview()

    Test range behavior for group overview commands.

    """
    done = False
    with inntest.connection() as conn:
        conn._require_reader()  # cheating
        count, low, high = conn.group(inntest.group)
        # INN fails these tests for delta >= 2^32; it parses the
        # range into a 64-bit value but then stuffs it into an int
        # uncritically.
        #
        # RFC3977 s8 says article numbers MUST be in the range
        # 1-2147483647 so we are testing quality of implementation
        # rather than compliance here.
        if b'OVER' in conn.capabilities():
            done = True
            for delta in _number_deltas:
                l, h = low+delta, high+delta
                code, arg = conn.transact([b'OVER', b'%d-%d' % (l, h)])
                overviews = []
                if code == 224:
                    overviews = conn.receive_lines()
                elif code == 423:
                    pass
                elif code == 501:
                    if l < 0x7FFFFFFF and h < 0x7FFFFFFF:
                        fail("OVER: unexpected response for %d-%d: %s"
                             % (l, h, conn.response))
                else:
                    fail("OVER: unexpected response for %d-%d: %s"
                         % (l, h, conn.response))
                if len(overviews) != 0:
                    fail("OVER: unexpected overview data for %d-%d"
                         % (l, h))
            overviews = conn.over(high, low)
            if len(overviews) != 0:
                fail("OVER: unexpected overview data: reverse range")
        if b'HDR' in conn.capabilities():
            done = True
            for delta in _number_deltas:
                l, h = low+delta, high+delta
                code, arg = conn.transact(
                    [b'HDR', b'Newsgroups', b'%d-%d' % (l, h)])
                headers = []
                if code == 225:
                    headers = conn.receive_lines()
                elif code == 423:
                    pass
                elif code == 501:
                    if l < 0x7FFFFFFF and h < 0x7FFFFFFF:
                        fail("HDR: unexpected response for %d-%d: %s"
                             % (l, h, conn.response))
                else:
                    fail("HDR: unexpected response for %d-%d: %s"
                         % (l, h, conn.response))
                if len(headers) != 0:
                    fail("HDR: unexpected header data: %d-%d"
                         % (l, h))
            headers = conn.over(high, low)
            if len(headers) != 0:
                fail("HDR: unexpected header data: reverse range")
        if not done:
            skip("no OVER or HDR capability")
