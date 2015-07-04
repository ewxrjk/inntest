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
import logging,os,time

def test_post(ident=None, description=b"posting test"):
    """inntest.Tests.test_post([ident=IDENT][description=SUBJECT])

    Posts to the test newsgroup and verifies that the article
    appears.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.

    """
    ident=inntest.utils._ident(ident)
    article=[b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] ' + nntpbits._normalize(description) + b' (ignore)',
             b'Message-ID: ' + ident,
             b'',
             b'nntpbits.Test test posting']
    with inntest.connection() as conn:
        conn.post(article)
        try:
            conn.post(article)
        except Exception as e:
            if str(e) != 'POST command failed: 441 435 Duplicate':
                raise e
        _check_posted(conn, ident)

def _check_posted(conn, ident):
    """s._check_posted(CONN, IDENT)

    Look for the article IDENT in the test group, using
    CONN as the client connection.

    """
    _,_,article_posted=conn.article(ident)
    if article_posted is None:
        raise Exception("article cannot be retrieved by message-ID")
    (count,low,high)=conn.group(inntest.group)
    overviews=conn.over(low,high)
    number_in_group=None
    for overview in overviews:
        (number,overview)=conn.parse_overview(overview)
        if overview[b'message-id:'] == ident:
            number_in_group=number
            break
    if number_in_group is None:
        raise Exception("article not found in group overview data")
    _,_,article_posted=conn.article(number_in_group)
    if article_posted is None:
        raise Exception("article cannot be retrieved from group")

def test_post_propagates(ident=None, description=b'posting propagation test'):
    """inntest.Tests.test_post_propagates([ident=IDENT][description=SUBJECT])

    Posts to the test newsgroup and verifies that the article
    propagates to the test server.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.
    """
    _check_post_propagates(ident, description, test_post)

def _check_post_propagates(ident, description,
                           do_post, *args, **kwargs):
    """inntest.Tests._check_post_propagates(IDENT, DESCRIPTION, DO_POST, ...)

    Call do_post(ident=IDENT, description=DESCRIPTION, ..) to post
    a message and then verify it is fed back to us.

    """
    ident=inntest.utils._ident(ident)
    with inntest.utils._local_server() as s:
        do_post(*args, ident=ident, description=description, **kwargs)
        next_trigger=0
        limit=time.time()+inntest.timelimit
        while time.time() < limit:
            # See if the post has turned up
            with s.lock:
                if ident in s.ihave_submitted:
                    break
            # Repeat the trigger if it's not helping
            if (inntest.trigger is not None
                   and next_trigger <= time.time()):
                logging.info("execute: %s" % inntest.trigger)
                rc=os.system(inntest.trigger)
                if rc != 0:
                    logging.error("Trigger wait status: %#04x" % rc)
                next_trigger=time.time()+inntest.trigger_timeout
            time.sleep(0.5)
        if ident not in s.ihave_submitted:
            raise Exception("article never propagated")

# -------------------------------------------------------------------------
# Testing IHAVE

def test_ihave(ident=None, description=b"ihave test", _pathhost=None):
    """inntest.Tests.test_ihave([ident=IDENT][description=SUBJECT])

    Feed a post to the test newsgroup and verifies that the
    article appears.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.

    """
    ident=inntest.utils._ident(ident)
    if _pathhost is None:
        _pathhost=inntest.domain
    article=[b'Path: ' + _pathhost + b'!not-for-mail',
             b'Newsgroups: ' + inntest.group,
             b'From: ' + inntest.email,
             b'Subject: [nntpbits] ' + nntpbits._normalize(description) + b' (ignore)',
             b'Message-ID: ' + ident,
             b'Date: ' + inntest.utils._date(),
             b'',
             b'nntpbits.Test test posting']
    with inntest.connection() as conn:
        conn.ihave(article)
        try:
            conn.ihave(article)
        except Exception as e:
            if str(e) != 'IHAVE command failed: 435 Duplicate':
                raise e
        _check_posted(conn, ident)

def test_ihave_propagates(ident=None, description=b'ihave propagation test'):
    """inntest.Tests.test_ihave_propagates([ident=IDENT][description=SUBJECT])

    Feed a post to the test newsgroup and verifies that the article
    propagates to the test server.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.
    """
    # Need a nondefault pathhost so it will propagate back to us
    _check_post_propagates(ident, description,
                           test_ihave,
                           _pathhost=b'nonesuch.' + inntest.domain)
