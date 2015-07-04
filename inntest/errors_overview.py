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
import inntest,nntpbits
from inntest.errors_group import _number_deltas
from inntest.running import *

def test_errors_group_overview():
    """inntest.Tests.test_errors_group_overview()

    Test range behavior for group overview commands.

    """
    done=False
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        count,low,high=conn.group(inntest.group)
        if b'OVER' in conn.capabilities():
            done=True
            for delta in _number_deltas:
                overviews=conn.over(low+delta, high+delta)
                if len(overviews)!=0:
                    fail("OVER: unexpected overview data: delta=%d"
                         % delta)
            overviews=conn.over(high, low)
            if len(overviews)!=0:
                fail("OVER: unexpected overview data: reverse range")
        if b'HDR' in conn.capabilities():
            done=True
            for delta in _number_deltas:
                headers=conn.hdr(b'Newsgroups', low+delta, high+delta)
                if len(headers)!=0:
                    fail("HDR: unexpected header data: delta=%d"
                         % delta)
            headers=conn.over(high, low)
            if len(headers)!=0:
                fail("HDR: unexpected header data: reverse range")
        if not done:
            skip("no OVER or HDR capability")
