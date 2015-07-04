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
import logging,re

def test_article_id():
    """inntest.Tests.test_article_id()

    Test article lookup by <message id>.

    """
    with inntest.connection() as conn:
        articles=_post_articles(conn)
        for cmd,parse in _article_lookup_commands():
            logging.debug("test_article_id %s" % cmd)
            method=getattr(conn, cmd)
            for ident,article in articles:
                r_number,r_ident,r=method(ident)
                if ident != r_ident:
                    raise Exception("%s: returned wrong ident (%s vs %s)"
                                    % (cmd, ident, r_ident))
                r_header,r_body,r_ident=parse(r)
                _check_article(cmd, ident, article,
                               r_header, r_body, r_ident)

def test_article_number():
    """inntest.Tests.test_article_id()

    Test article lookup by number.

    """
    with inntest.connection() as conn:
        articles=_post_articles(conn)
        count,low,high=conn.group(inntest.group)
        ident_to_number={}
        r_number,r_ident,_=conn.stat()
        while r_ident:
            for ident,article in articles:
                if r_ident == ident:
                    ident_to_number[ident]=r_number
            r_number,r_ident,_=conn.next()
        for cmd,parse in _article_lookup_commands():
            logging.debug("test_article_number %s" % cmd)
            for ident,article in articles:
                number=ident_to_number[ident]
                r_number,r_ident,r=getattr(conn, cmd)(number)
                if ident != r_ident:
                    raise Exception("%s: returned wrong ident (%s vs %s)"
                                    % (cmd, ident, r_ident))
                if number != r_number:
                    raise Exception("%s: returned wrong number (%d vs %d)"
                                    % (number, ident, r_number))
                r_header,r_body,r_ident=parse(r)
                _check_article(cmd, ident, article,
                               r_header, r_body, r_ident)

def _article_lookup_commands():
    return[['article', _parse_article],
           ['head', _parse_article],
           ['body', lambda body: (None, body, None)],
           ['stat', lambda ident: (None, None, ident)]]

def _check_article(cmd, ident, article,
                   r_header, r_body, r_ident,
                   allow_missing=set([]),
                   overview=False):
    """_check_article(CMD, IDENT, ARTICLE,
               R_HEADER, R_BODY, R_IDENT) -> None|'expected_failed'

Verifies that the received r_HEADER, R_BODY and R_IDENT match the
expected ARTICLE and IDENT.  CMD is the command used to fetch them.

Optional arguments:
allowing_missing -- set of headers that are allowed to be missing
overview -- apply overview-specific transformations

    """

    header,body,_=_parse_article(article)
    # Ident should match
    if r_ident is not None:
        logging.debug("%s <-> %s" % (ident, r_ident))
        if r_ident != ident:
            raise Exception("%s: ID mismatch (%s vs %s)"
                            % (cmd, ident, r_ident))
    # Headers we supplied should match
    if r_header is not None:
        for field in header:
            if field not in r_header:
                if field in allow_missing:
                    continue
                raise Exception("%s: missing %s header"
                                % (cmd, field))
            value=header[field]
            r_value=r_header[field]
            if overview:
                value=re.sub(b'\n', b'', value)
                value=re.sub(b'\t', b' ', value)
            logging.debug("%s: %s <-> %s" % (field, value, r_value))
            if inntest.trim(r_value) != inntest.trim(value):
                raise Exception("%s: non-matching %s header: '%s' vs '%s'"
                                % (cmd, field, value, r_value))
    # Body should match
    if r_body is not None:
        if body != r_body:
            raise Exception("%s: non-matching body: '%s' vs '%s'"
                                % (cmd, body, r_body))

_header_re=re.compile(b'^([a-zA-Z0-9\\-]+:)\\s+(.*)$')

def _parse_article(article):
    """inntest.Tests._parse_article(ARTICLE) -> HEADER,BODY,IDENT

    Parses an article (as a list of bytes objects) into the header
    (a dict mapping lower-cases bytes header names to values), a
    body (a list of bytes objects) and the message ID.

    As with ClientConnection.parse_overview, header names include
    the trailing colon.

    The body and/or message ID are None if missing.

    """
    header={}
    field=None
    body=None
    for line in article:
        if body is not None:
            body.append(line)
            continue
        if line==b'':
            body=[]
            continue
        if line[0:1] in b' \t':
            if field is None:
                raise Exception("Malformed article: %s" % article)
            header[field]+=b'\n'+line
            continue
        m=_header_re.match(line)
        if not m:
            raise Exception("Malformed article: %s" % article)
        field=m.group(1).lower()
        header[field]=m.group(2)
    return header,body,header[b'message-id:']

def _post_articles(conn):
    """inntest.Tests._post_articles(CONN)

    Post some articles for test purposes.

    """
    articles=[]
    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] articles-simple (ignore)',
             b'Message-ID: ' + ident,
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] articles-keywords (ignore)',
             b'Message-ID: ' + ident,
             b'Keywords: this, that, the other',
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] articles-date (ignore)',
             b'Message-ID: ' + ident,
             b'Date: ' + inntest.newsdate(),
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] articles-organization (ignore)',
             b'Message-ID: ' + ident,
             b'Organization: ' + inntest.unique(),
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] articles-user-agent (ignore)',
             b'Message-ID: ' + ident,
             b'User-Agent: test.terraraq.uk',
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email + b'   ',
             b'Subject: [nntpbits] articles-trailing-space (ignore)\t',
             b'Message-ID: ' + ident,
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: \t' + inntest.email,
             b'Subject: [nntpbits] articles-leading-space (ignore)',
             b'Message-ID:     ' + ident,
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    ident=inntest.ident()
    article=[b'Newsgroups: ' + inntest.group,
             b'From: inntest',
             b' <' + inntest.email + b'>',
             b'Subject: [nntpbits] articles-folding-space (ignore)',
             b' (folded)',
             b'Message-ID: ' + ident,
             b'',
             inntest.unique()]
    conn.post(article)
    articles.append([ident, article])

    # Lots of junk headers to blow HEADER_DELTA limit in nnrpd/post.c
    ident=inntest.ident()
    article=([b'Newsgroups: ' + inntest.group,
              b'From: \t' + inntest.email,
              b'Subject: [nntpbits] articles-madeup-headers (ignore)',
              b'Message-ID: ' + ident]
             +[b'Nonsense: whatever']*40+
             [b'',
              inntest.unique()])
    conn.post(article)
    articles.append([ident, article])

    return articles
