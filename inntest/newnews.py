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
import logging,time
from inntest.article import _post_articles

def test_newnews():
    """inntest.Tests.test_newnews()

    Test NEWNEWS.

    """
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        if not b'NEWNEWS' in conn.capabilities():
            logging.warn("SKIPPING TEST because no NEWNEWS capability")
            return 'skip'
        start=conn.date()
        while start==conn.date():
            time.sleep(0.25)
        articles=_post_articles(conn)
        # Multiple tests reflects optimizations in INN
        new_idents=set(conn.newnews(inntest.hierarchy+b'.*', start))
        for ident,article in articles:
            if ident not in new_idents:
                raise Exception("NEWNEWS: did not find %s" % ident)
        new_idents=set(conn.newnews(inntest.group, start))
        for ident,article in articles:
            if ident not in new_idents:
                raise Exception("NEWNEWS: did not find %s" % ident)
        new_idents=set(conn.newnews(b'!*', start))
        if len(new_idents) > 0:
            raise Exception("NEWNEWS: return articles for empty wildmat")
