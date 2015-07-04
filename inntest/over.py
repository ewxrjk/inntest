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
from inntest.article import _post_articles, _check_article

def test_over_id():
    """inntest.Tests.test_over_id()

    Test OVER lookup by <message id>.

    NOTE: this has never been run since INN doesn't support OVER
    MSGID.

    """
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        if not b'OVER' in conn.capabilities():
            logging.warn("SKIPPING TEST because no OVER capability")
            return 'skip'
        if not b'MSGID' in conn.capability_arguments(b'OVER'):
            logging.warn("SKIPPING TEST because no OVER MSGID capability")
            return 'skip'
        articles=_post_articles(conn)
        count,low,high=conn.group(inntest.group)
        for ident,article in articles:
            overviews=conn.over(ident)
            number,overview=conn.parse_overview(overviews[0])
            _check_article(b'OVER', ident, article,
                           overview, None,
                           overview[b'message-id:'],
                           overview=True)

def test_over_number():
    """inntest.Tests.test_over_id()

    Test OVER lookup by number.

    """
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        if not b'OVER' in conn.capabilities():
            logging.warn("SKIPPING TEST because no OVER capability")
            return 'skip'
        articles=_post_articles(conn)
        count,low,high=conn.group(inntest.group)
        overviews=conn.over(low,high)
        ov={}
        for overview in overviews:
            number,overview=conn.parse_overview(overview)
            ov[overview[b'message-id:']]=overview
        allowmissing=set([h
                          for h in [b'newsgroups:', b'keywords:',
                                    b'organization:', b'user-agent:']
                          if h not in conn.list_overview_fmt()])
        for ident,article in articles:
            if not ident in ov:
                raise Exception("OVER: didn't find article %s"
                                % ident)
            _check_article(b'OVER', ident, article,
                           ov[ident], None, ov[ident][b'message-id:'],
                           allowmissing,
                           overview=True)
