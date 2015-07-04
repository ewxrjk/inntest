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
import logging
from inntest.article import _post_articles,_header_re

def test_listgroup():
    """inntest.Tests.test_listgroup()

    Test LISTGROUP.

    """
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        if not b'HDR' in conn.capabilities():
            logging.warn("SKIPPING TEST because no HDR capability")
            return 'skip'
        articles=_post_articles(conn)
        seen=set()
        conn.group(inntest.group)
        count,low,high,numbers=conn.listgroup()
        assert count >= len(numbers)
        for index in range(1, len(numbers)):
            assert numbers[index] > numbers[index-1]
        for number in numbers:
            assert number >= low
            assert number <= high
            _,_,lines=conn.head(number)
            for line in lines:
                m=_header_re.match(line)
                if m and m.group(1).lower()==b'message-id:':
                    seen.add(m.group(2))
                    break
        for ident,article in articles:
            if not ident in seen:
                raise Exception("LISTGROUP: failed to list %s" % ident)
