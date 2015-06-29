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
import calendar,re,time

def test_date():
    """inntest.Tests.test_date()

    Tests the DATE command.

    As well as checking the syntax, verifies that the server's
    clock is reasonably accurate.

    """
    with inntest.connection() as conn:
        now=int(time.time())
        d=conn.date()
        m=re.match(b'^(\\d\\d\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)$',
                   d)
        if not m:
            raise Exception('DATE: malformed response: %s' % d)
        year=int(m.group(1))
        month=int(m.group(2))
        day=int(m.group(3))
        hour=int(m.group(4))
        minute=int(m.group(5))
        second=int(m.group(6))
        if year < 2015: raise Exception('DATE: implausible year: %s' % d)
        if month < 1 or month > 12: raise Exception('DATE: bad month: %s' % d)
        if day < 1 or day > 31: raise Exception('DATE: bad day: %s' % d)
        if hour > 23: raise Exception('DATE: bad hour: %s' % d)
        if minute > 59: raise Exception('DATE: bad minute: %s' % d)
        if second > 59: raise Exception('DATE: bad second: %s' % d)
        t=calendar.timegm([year, month, day, hour, minute, second])
        delta=abs(t-now)
        if delta > 60:
            raise Exception("DATE: inaccurate clock: %s (at %d)" % (d, now))
