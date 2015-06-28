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

# Commands that check or fetch part of an article by ID, number or current
_article_commands=[b'ARTICLE', b'HEAD', b'BODY', b'STAT']
# Various offsets, representing attempts to tickle overflow behavior in
# article number parsing
_number_deltas=[100000, 1<<16, 1<<31, 1<<32, 1<<33, 1<<53]

def test_errors_no_article():
    """inntest.Tests.test_errors_no_article()

    Test errors for nonexistent articles.

    """
    with nntpbits.ClientConnection(inntest.address) as conn:
        conn._require_reader() # cheating
        for cmd in _article_commands:
            code,arg=conn.transact([cmd, inntest.utils._ident()])
            if code != 430:
                raise Exception("%s: incorrect error for nonexistent article: %s"
                                % (cmd, conn.response))
        if (b'OVER' in conn.capabilities()
            and b'MSGID' in conn.capability_arguments(b'OVER')):
            code,arg=conn.transact([b'OVER', inntest.utils._ident()])
            if code != 430:
                raise Exception("OVER: incorrect error for nonexistent article: %s"
                                % (cmd, conn.response))
        if b'HDR' in conn.capabilities():
            code,arg=conn.transact([b'HDR', b'Subject', inntest.utils._ident()])
            if code != 430:
                raise Exception("OVER: incorrect error for nonexistent article: %s"
                                % (cmd, conn.response))

def test_errors_no_group():
    """inntest.Tests.test_errors_no_group()

    Test errors for nonexistent groups

    """
    with nntpbits.ClientConnection(inntest.address) as conn:
        conn._require_reader() # cheating
        for cmd in [b'GROUP', b'LISTGROUP']:
            code,arg=conn.transact([cmd, inntest.utils._groupname()])
            if code != 411:
                raise Exception("%s: incorrect error for nonexistent group: %s"
                                % (cmd, conn.response))

def test_errors_outside_group():
    """inntest.Tests.test_errors_outside_group()

    Test errors for commands issued outside a group.

    """
    with nntpbits.ClientConnection(inntest.address) as conn:
        conn._require_reader() # cheating
        for cmd in [b'NEXT', b'LAST']:
            code,arg=conn.transact(cmd)
            if code != 412:
                raise Exception("%s: incorrect error outside group: %s"
                                % (cmd, conn.response))
        for cmd in _article_commands:
            code,arg=conn.transact(cmd)
            if code != 412:
                raise Exception("%s: incorrect error outside group: %s"
                                % (cmd, conn.response))
            # 3977 9.8: article-number = 1*16DIGIT
            for number in [1, 10**15]:
                code,arg=conn.transact([cmd, str(number)])
            if code != 412:
                raise Exception("%s: incorrect error outside group: %s"
                                % (cmd, conn.response))
            for number in [10**16, '0'*16+'1']:
                code,arg=conn.transact([cmd, str(number)])
                if code != 501:
                    raise Exception("%s: incorrect error for bad article-number: %s"
                                    % (cmd, conn.response))

def test_errors_group_navigation():
    """inntest.Tests.test_errors_group_navigation()

    Test errors for group navigation commands.

    """
    with nntpbits.ClientConnection(inntest.address) as conn:
        conn._require_reader() # cheating
        count,low,high=conn.group(inntest.group)
        for cmd in _article_commands:
            for delta in _number_deltas:
                code,arg=conn.transact([cmd, '%d' % (high+delta)])
                if code != 423:
                    raise Exception("%s: incorrect error for bad article number: %s"
                                    % (cmd, conn.response))
        # The next two are, in theory, racy.  When using the full inntest
        # test rig this isn't really an issue as nothing will be
        # adding/removing articles.  It could be an issue when using a
        # heavily used group on an active server though.
        conn.stat(low)
        conn.stat()         # ensure article is selected
        code,arg=conn.transact(b'LAST')
        if code != 422:
            raise Exception("LAST: incorrect error for no previous article: %s"
                            % conn.response)
        conn.stat(high)
        conn.stat()         # ensure article is selected
        code,arg=conn.transact(b'NEXT')
        if code != 421:
            raise Exception("NEXT: incorrect error for no next article: %s"
                            % conn.response)
