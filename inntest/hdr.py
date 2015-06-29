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

def test_hdr_number():
    """inntest.Tests.test_hdr_id()

    Test HDR lookup by number.

    """
    with inntest.connection() as conn:
        conn._require_reader() # cheating
        if not b'HDR' in conn.capabilities():
            logging.warn("SKIPPING TEST because no HDR capability")
            return 'skip'
        articles=_post_articles(conn)
        count,low,high=conn.group(inntest.group)
        ident_to_number={}
        number_to_ident=dict(conn.hdr(b'Message-ID', low, high))
        for number in number_to_ident:
            ident_to_number[number_to_ident[number]]=number
        for header in [b'Subject',
                       b'Newsgroups',
                       b'From',
                       b'Keywords',
                       b'Date',
                       b'Organization',
                       b'User-Agent']:
            number_to_header=dict(conn.hdr(header, low, high))
            for ident,article in articles:
                r_value=number_to_header[ident_to_number[ident]]
                for line in article:
                    if line==b'':
                        break
                    m=_header_re.match(line)
                    if m.group(1) == header:
                        value=m.group(2)
                        if r_value != value:
                            raise Exception("HDR: non-matching %s header: '%s' vs '%s'"
                                            % (field, value, r_value))
