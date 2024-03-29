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
import os
import time
from inntest.running import *


def test_post(ident=None, description=b"posting test"):
    """inntest.Tests.test_post([ident=IDENT][description=SUBJECT])

    Posts to the test newsgroup and verifies that the article
    appears.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.

    """
    ident = inntest.ident(ident)
    article = [b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] ' +
               nntpbits._normalize(description) + b' (ignore)',
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
    _, _, article_posted = conn.article(ident)
    if article_posted is None:
        fail("article cannot be retrieved by message-ID")
    (count, low, high) = conn.group(inntest.group)
    overviews = conn.over(low, high)
    number_in_group = None
    for overview in overviews:
        (number, overview) = conn.parse_overview(overview)
        if overview[b'message-id:'] == ident:
            number_in_group = number
            break
    if number_in_group is None:
        fail("article not found in group overview data")
    _, _, article_posted = conn.article(number_in_group)
    if article_posted is None:
        fail("article cannot be retrieved from group")


def test_post_propagates(ident=None, description=b'posting propagation test'):
    """inntest.Tests.test_post_propagates([ident=IDENT][description=SUBJECT])

    Posts to the test newsgroup and verifies that the article
    propagates to the test server (which is really us with a funny hat on).

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.
    """
    _check_post_propagation(ident, description, test_post, features='peering')


def _check_post_propagation(ident, description,
                            do_post, features=[], behavior="accept", *args, **kwargs):
    """inntest.Tests._check_post_propagation(IDENT, DESCRIPTION, DO_POST, ...)

    Call do_post(ident=IDENT, description=DESCRIPTION, ..) to post
    a message and then verify it is fed back to us.

    """
    ident = inntest.ident(ident)
    if features is None:
        features = 'peering'
    with inntest.local_server(features=features) as s:
        do_post(*args, ident=ident, description=description, **kwargs)
        next_trigger = 0
        limit = time.time()+inntest.timelimit
        while time.time() < limit:
            # If the post has been accepted, we're done.
            with s.lock:
                if ident in s.ihave_submitted:
                    break
            # Repeat the trigger if it's not helping
            if (inntest.trigger is not None
                    and next_trigger <= time.time()):
                log().debug("execute: %s" % inntest.trigger)
                rc = os.system(inntest.trigger)
                if rc != 0:
                    failhard("Trigger wait status: %#04x" % rc)
                next_trigger = time.time()+inntest.trigger_timeout
            time.sleep(0.5)
        ihave_checked = s.ihave_checked
        ihave_submitted = s.ihave_submitted
    if behavior == 'check':
        if ident not in ihave_submitted:
            fail("article never propagated")
    if behavior == 'reject':
        count = ihave_checked.count(ident)
        if count == 0:
            fail("article never submitted")
        if count > 1:
            xfail("article submitted %d times" % count)


def test_post_no_message_id():
    """inntest.Tests.test_no_message_id()

    Posts to the test newsgroup without a Message-ID header and
    verifies that the article appears.

    """
    unique = inntest.unique()
    article = [b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] no message id (ignore)',
               b'',
               unique]
    with inntest.connection() as conn:
        conn.post(article)
        count, low, high = conn.group(inntest.group)
        found = False
        for number in range(high, low-1, -1):
            r_number, r_ident, r_body = conn.body(number)
            if r_body == [unique]:
                found = True
                break
        assert found

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
    ident = inntest.ident(ident)
    if _pathhost is None:
        _pathhost = inntest.domain
    article = [b'Path: ' + _pathhost + b'!not-for-mail',
               b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] ' +
               nntpbits._normalize(description) + b' (ignore)',
               b'Message-ID: ' + ident,
               b'Date: ' + inntest.newsdate(),
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
    propagates to the test server (which is really us with a funny hat on).

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.
    """
    # Need a nondefault pathhost so it will propagate back to us
    _check_post_propagation(ident, description,
                            test_ihave,
                            features=['ihave'],  # prevent use of streaming
                            _pathhost=b'nonesuch.' + inntest.domain)


if False:
    def test_ihave_propagation_error_500(description=b'propagation error handling test (500)'):
        """inntest.Tests.test_propagation_errors([description=SUBJECT])

        Verify that handling of IHAVE propagation errors is correct.

        If DESCRIPTION is specified then it will appear in the subject
        line in the test message.
        """
        # 500 is an unrecognized command; the most likely cause is that we're talking to
        # a reader server. At any rate it's not very useful thing to test.
        _check_post_propagation(b'<reject.500@inntest.invalid>', description,
                                test_ihave,
                                features=['ihave'],  # prevent use of streaming
                                behavior='reject',
                                _pathhost=b'nonesuch.' + inntest.domain)


def test_propagation_error_501(description=b'propagation error handling test (501)'):
    """inntest.Tests.test_propagation_error_501([description=SUBJECT])

    Verify that handling of IHAVE propagation errors is correct.

    If DESCRIPTION is specified then it will appear in the subject
    line in the test message.
    """
    # 501 is a syntax error; e.g. the peer disagrees about valid message ID syntax
    _check_post_propagation(b'<reject.501.ihave@inntest.invalid>', description,
                            test_ihave,
                            features=['ihave'],  # prevent use of streaming
                            behavior='reject',
                            _pathhost=b'nonesuch.' + inntest.domain)


def test_streaming_propagation_error_501(description=b'propagation error handling test (501)'):
    """inntest.Tests.test_streaming_propagation_error_501([description=SUBJECT])

    Verify that handling of CHECK propagation errors is correct.

    If DESCRIPTION is specified then it will appear in the subject
    line in the test message.
    """
    # 501 is a syntax error; e.g. the peer disagrees about valid message ID syntax
    _check_post_propagation(b'<reject.501.check@inntest.invalid>', description,
                            test_ihave,
                            features=['streaming'],  # prevent use of streaming
                            behavior='reject',
                            _pathhost=b'nonesuch.' + inntest.domain)

# -----------------------------------------------------------------------------
# Testing RFC4644 streaming commands


def test_takethis(ident=None, description=b"takethis test", _pathhost=None):
    """inntest.Tests.test_takethis([ident=IDENT][description=SUBJECT])

    Feed a post to the test newsgroup using CHECK/TAKETHIS and
    verifies that the article appears.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.

    """
    ident = inntest.ident(ident)
    if _pathhost is None:
        _pathhost = inntest.domain
    article = [b'Path: ' + _pathhost + b'!not-for-mail',
               b'Newsgroups: ' + inntest.group,
               b'From: ' + inntest.email,
               b'Subject: [nntpbits] ' +
               nntpbits._normalize(description) + b' (ignore)',
               b'Message-ID: ' + ident,
               b'Date: ' + inntest.newsdate(),
               b'',
               b'nntpbits.Test test posting']
    with inntest.connection() as conn:
        if not conn.streaming():
            return skip("no streaming support")
        r = conn.check(article=article)
        if r != True:
            fail("CHECK rejected article: %s" % r)
        r = conn.takethis(article)
        if r != True:
            failhard("TAKETHIS rejected article: %s" % r)
        r = conn.check(article=article)
        if r != False:
            fail("CHECK unexpectedly accepted article: %s" % r)
        r = conn.takethis(article)
        if r != False:
            fail("TAKETHIS unexpectedly accepted article: %s" % r)
        _check_posted(conn, ident)


def test_takethis_propagates(ident=None, description=b'takethis propagation test'):
    """inntest.Tests.test_takethis_propagates([ident=IDENT][description=SUBJECT])

    Feed a post to the test newsgroup and verifies that the article
    propagates to the test server.

    If IDENT is specified then this value will be used as the
    message ID.

    If DESCRIPTION is specified then it will appear in the subject
    line.
    """
    # Need a nondefault pathhost so it will propagate back to us
    _check_post_propagation(ident, description,
                            test_takethis,
                            features=['peering'],
                            _pathhost=b'nonesuch.' + inntest.domain)
