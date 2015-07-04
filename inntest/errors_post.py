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

def test_errors_bad_post():
    """inntest.Tests.test_errors_bad_post()

    Test error behavior for bad local postings.

    """
    with inntest.connection() as conn:
        conn._require_reader()
        return _test_errors_bad_post(conn, b'POST', 340, 240, 441, [])

def test_errors_bad_ihave():
    """inntest.Tests.test_errors_bad_ihave()

    Test error behavior for bad post injections.

    """
    with inntest.connection() as conn:
        return _test_errors_bad_post(conn, b'IHAVE', 335, 235, 437,
                                     [b'Path: '+inntest.domain])

def _test_errors_bad_post(conn, cmd, initial_response, ok_response,
                          error_response, extras):
    """inntest.Tests._test_errors_bad_post(CONN, CMD, INITIAL_RESPONSE, OK_RESPONSE,
                    ERROR_RESPONSE, EXTRAS)

    Test IHAVE/POST error behavior.

    """
    expected_fails=0
    def check(what, article, ident=None,
              error_response=error_response, add_body=True,
              expected_fail=False, extras=extras):
        if ident is None:
            ident=inntest.ident()
            article=[b'Message-ID: '+ident]+article
        article=extras+article
        if add_body:
            article=article+[b'', inntest.unique()]
        if cmd!=b'POST':
            cmd_list=[cmd,ident]
        else:
            cmd_list=cmd
        code,arg=conn.transact(cmd_list)
        if code==initial_response:
            conn.send_lines(article)
            code,arg=conn.wait()
        if code!=error_response:
            if expected_fail:
                logging.warn("EXPECTED FAILURE: %s: wrong response for %s: %d"
                             % (cmd, what, code))
                nonlocal expected_fails
                expected_fails+=1
            else:
                raise Exception("%s: wrong response for %s: %d"
                                % (cmd, what, code))
    ## Missing things
    check('no subject',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Date: ' + inntest.newsdate()])
    check('no from',
          [b'Newsgroups: ' + inntest.group,
           b'Subject: [nntpbits] no from test (ignore)',
           b'Date: ' + inntest.newsdate()])
    check('no newsgroups',
          [b'From: ' + inntest.email,
           b'Subject: [nntpbits] no groups test (ignore)',
           b'Date: ' + inntest.newsdate()])
    if cmd==b'IHAVE':
        check('missing date',
              [b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] missing date test (ignore)'])
        check('missing path',
              [b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] missing path test (ignore)',
               b'Date: ' + inntest.newsdate()],
              extras=[])
    check('missing body',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] missing body test (ignore)',
           b'Date: ' + inntest.newsdate()],
          add_body=False)
    ## Malformed things
    check('empty newsgroups',
          [b'Newsgroups: ',
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] empty groups test (ignore)',
           b'Date: ' + inntest.newsdate()])
    check('empty followup-to',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] empty followup test (ignore)',
           b'Followup-To:',
           b'Date: ' + inntest.newsdate()],
          expected_fail=(cmd==b'POST'))
    check('empty from',
          [b'Newsgroups: ' + inntest.group,
           b'From: ',
           b'Subject: [nntpbits] empty from test (ignore)',
           b'Date: ' + inntest.newsdate()])
    check('malformed from',
          [b'Newsgroups: ' + inntest.group,
           b'From: example',
           b'Subject: [nntpbits] malformed from test (ignore)',
           b'Date: ' + inntest.newsdate()],
          expected_fail=(cmd==b'IHAVE'))
    check('malformed from #2',
          [b'Newsgroups: ' + inntest.group,
           b'From: @example.com',
           b'Subject: [nntpbits] malformed from test #2 (ignore)',
           b'Date: ' + inntest.newsdate()],
          expected_fail=True)
    check('forbidden newsgroup',
          [b'Newsgroups: poster',
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] forbidden groups test (ignore)',
           b'Date: ' + inntest.newsdate()])
    check('malformed date',
          [b'Newsgroups: '+inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] malformed date test (ignore)',
           b'Date: your sister'])
    check('malformed injection date',
          [b'Newsgroups: '+inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] malformed injection date test (ignore)',
           b'Date: ' + inntest.newsdate(),
           b'Injection-Date: your sister'])
    check('malformed expires date',
          [b'Newsgroups: '+inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] malformed expires date test (ignore)',
           b'Date: ' + inntest.newsdate(),
           b'Expires: your sister'],
          expected_fail=(cmd==b'IHAVE'))
    for ident in [b'junk', b'<junk>', b'<junk@junk']:
        check('malformed message-id (%s)' % ident,
              [b'Newsgroups: '+inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] malformed message ID test (ignore)',
               b'Date: ' + inntest.newsdate(),
               b'Message-ID: ' + ident],
              inntest.ident())
        if cmd==b'IHAVE':
            check('malformed message-id (%s)' % ident,
                  [b'Newsgroups: '+inntest.group,
                   b'From: ' + inntest.email,
                   b'Subject: [nntpbits] malformed message ID test (ignore)',
                   b'Date: ' + inntest.newsdate(),
                   b'Message-ID: ' + ident],
                  ident,
                  error_response=435)
    check('empty body',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] empty body test (ignore)',
           b'Date: ' + inntest.newsdate(),
           b''],
          add_body=False,
          expected_fail=(cmd==b'IHAVE'))
    ## Duplicate things
    check('duplicate header',
          [b'Newsgroups: ' + inntest.group,
           b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] duplicate header test (ignore)',
           b'Date: ' + inntest.newsdate()])
    ## Semantic checks
    check('past article',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] past article test (ignore)',
           b'Date: ' + inntest.newsdate(time.time()-86400*365)])
    check('past article #2',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] past article #2 test (ignore)',
           b'Date: ' + inntest.newsdate(),
           b'Injection-Date: ' + inntest.newsdate(time.time()-86400*365)])
    check('future article',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] future article test (ignore)',
           b'Date: ' + inntest.newsdate(time.time()+86400*7)])
    check('future article #2',
          [b'Newsgroups: ' + inntest.group,
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] future article #2 test (ignore)',
           b'Date: ' + inntest.newsdate(),
           b'Injection-Date: ' + inntest.newsdate(time.time()+86400*7)])
    check('nonexistent newsgroup',
          [b'Newsgroups: ' + inntest.groupname(),
           b'From: ' + inntest.email,
           b'Subject: [nntpbits] nonexistent group test (ignore)',
           b'Date: ' + inntest.newsdate()])
    if cmd==b'POST':
        check('followup to nonexistent newsgroup',
              [b'Newsgroups: ' + inntest.group,
               b'Followup-To: ' + inntest.groupname(),
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] nonexistent group test (ignore)',
               b'Date: ' + inntest.newsdate()])
    if expected_fails > 0:
        return 'expected_fail'
