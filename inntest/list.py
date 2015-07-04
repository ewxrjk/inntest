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
import re
from inntest.running import *

def test_list(wildmat=None):
    """inntest.test_list()

    Tests the LIST command.

    Uses CAPABILITIES to enumerate all the LIST subcommands
    supported and verifies that their output follows the right
    syntax.  Then (if possible) switches to reader mode and
    repeats the exercise.
    """
    with inntest.connection() as conn:
        def check():
            subcommands=conn.capability_arguments(b'LIST')
            for kw in subcommands:
                _test_list(conn, kw)
            # Default subcommand is ACTIVE
            if b'ACTIVE' in subcommands:
                _test_list(conn, None)
        check()
        if b'MODE-READER' in conn.capabilities():
            conn._mode_reader() # cheating
            check()

def test_list_wildmat(hierarchy=None):
    """inntest.test_list_wildmat()

    Tests the LIST command with wildmats

    Uses CAPABILITIES to enumerate all the LIST subcommands
    supported and, for those that can accept a wildmat argument,
    verifies that their output follows the right syntax.  Then (if
    possible) switches to reader mode and repeats the exercise.

    """
    if hierarchy is None:
        hierarchy=inntest.hierarchy
    test_list(wildmat=hierarchy+b'.*')

def test_list_wildmat_single(hierarchy=None):
    """inntest.test_list_wildmat_single()

    Tests the LIST command with single-match wildmats

    Uses CAPABILITIES to enumerate all the LIST subcommands
    supported and, for those that can accept a wildmat argument,
    verifies that their output follows the right syntax.  Then (if
    possible) switches to reader mode and repeats the exercise.

    This reflects an optimization in INN's nnrpd.

    """
    test_list(wildmat=inntest.group)

def test_list_headers():
    """inntest.test_list_wildmat()

    Tests extra details of the LIST HEADERS command

    """
    with inntest.connection() as conn:
        conn._require_reader()
        subcommands=conn.capability_arguments(b'LIST')
        if b'HEADERS' not in subcommands:
            return 'skip'
        _test_list(conn, b'HEADERS MSGID')
        _test_list(conn, b'HEADERS RANGE')

# LIST subcommands that can take a wildmat
_list_wildmat=set([ b'ACTIVE',
                    b'ACTIVE.TIMES',
                    b'NEWSGROUPS',
                    b'COUNTS',
                    b'SUBSCRIPTIONS'])
# LIST subcommands that we'll accept a 503 response for
_list_optional=set([ b'MOTD',
                     b'COUNT',
                     b'DISTRIBUTIONS',
                     b'MODERATORS',
                     b'SUBSCRIPTIONS' ])

# Regexps that LIST subcommand output must match
# For subcommands that can take a wildmat, first capture
# group is newsgroup name.
_list_active_re=re.compile(b'^(\\S+) +(\\d+) +(\\d+) +([ynmxj]|=\S+)$')
_list_active_times_re=re.compile(b'^(\\S+) +(\d+) +(.*)$')
_list_distrib_pats_re=re.compile(b'^(\\d+):([^:]+):(.*)$')
_list_newsgroups_re=re.compile(b'^(\\S+)[ \\t]+(.*)$')
_list_headers_re=re.compile(b'^(:?\\S+)$')
_list_headers_msgid_re=_list_headers_re
_list_headers_range_re=_list_headers_re
# RFC6048 extras
_list_counts_re=re.compile(b'^(\\S+) +(\\d+) +(\\d+) +(\\d+) +([ynmxj]|=\S+)$')
_list_distributions_re=re.compile(b'^(\\S+)[ \t]+(.*)$')
_list_moderators_re=re.compile(b'^([^:]+):(.*)$') # TODO %%/%s rules
_list_motd_re=re.compile(b'')                     # anything goes
_list_subscriptions_re=re.compile(b'^(\\S+)$')

def _test_list(conn, kw, wildmat=None):
    """inntest._test_list(CONN, KW, [WILDMAT])

    Test a LIST subcommand on connection CONN.

    KW is the subcommand and WILDMAT is an optional wildmat
    pattern to supply.

    """
    # verify(GROUP) -> BOOL tests whether the group is acceptable
    # based on WILDMAT.
    if wildmat is None:
        verify=lambda s: True
    else:
        if kw not in _list_wildmat:
            skip("LIST %s, don't know how to check output"
                 % kw)
            return
        verify=_wildmat_to_function(wildmat)
    lines=conn.list(kw, wildmat)
    if kw is None:
        kw=b'ACTIVE'
    if lines is None:
        if kw in _list_optional:
            return
        failhard("LIST %s: unexpected 503" % kw)
    # Find the regexp to verify/parse lines
    name='list_'+str(kw, 'ascii').replace(' ', ' ').replace('.', '_').lower()
    regex_name='_'+name+'_re'
    regex=getattr(inntest.list, regex_name, None)
    if regex is not None:
        for line in lines:
            m=regex.match(line)
            if not m:
                fail("LIST %s: malformed line: %s" % (kw, line))
            elif not verify(m.group(1)):
                fail("LIST %s: malformed group name: %s" % (kw, line))
    method_name='_check_' + name
    method=getattr(inntest.list, method_name, None)
    if method is not None:
        return method(lines, kw)

def _check_list_overview_fmt(lines, kw):
    """inntest._check_list_overview_fmt(LINES, KW)

    Verify that the OVERFMT.FMT data is valid.

    """
    _overview_initial=[b'Subject:',
                       b'From:',
                       b'Date:',
                       b'Message-ID:',
                       b'References:']
    for i in range(0, len(_overview_initial)):
        if _overview_initial[i].lower() != lines[i].lower():
            fail("LIST OVERVIEW.FMT: header %d wrong: %s"
                 % (i+1, lines[i]))
    if lines[5].lower() != b'bytes:' and lines[5].lower() != b':bytes':
        fail("LIST OVERVIEW.FMT: header %d wrong: %s"
             % (6, lines[i]))
    if lines[6].lower() != b'lines:' and lines[6].lower() != b':lines':
        fail("LIST OVERVIEW.FMT: header %d wrong: %s"
             % (7, lines[i]))
    for i in range(7, len(lines)):
        if not lines[i].lower().endswith(b':full'):
            fail("LIST OVERVIEW.FMT: header %d partial: %s"
                 % (i+1, lines[i]))

def _check_list_motd(lines, kw):
    """inntest._check_list_motd(LINES, KW)

    Verify that the MOTD data is valid.

    """
    for line in lines:
        try:
            line.decode()
        except Exception as e:
            fail("LIST MOTD: %s response is not valid UTF-8"
                 % which)

def _wildmat_pattern_to_re(pattern):
    """inntest._wildmat_pattern_to_re(PATTERN) -> RE

    Convert a single wildmat pattern (essentially, a restricted
    version of glob syntax) to a compiled regexp.

    """
    pos=0
    regex='^'
    for ch in pattern:
        if ch=='*':
            regex+='.*'
        elif ch=='?':
            regex+='.'
        else:
            regex+=ch
    regex+='$'
    return re.compile(regex)

def _wildmat_to_function(wildmat):
    """inntest._wildmat_to_function(WILDMAT) -> FUNCTION
    where: FUNCTION(GROUP) -> BOOL

    Convert a wildmat to a function that tests whether a group
    name matches the wildmat. GROUP may be str or a bytes object.q

    """
    if isinstance(wildmat, bytes):
        wildmat=str(wildmat, 'UTF-8')
    elements=[]
    for pattern in wildmat.split(','):
        if pattern[0] == '!':
            sense=False
            pattern=pattern[1:]
        else:
            sense=True
        elements.append([sense, _wildmat_pattern_to_re(pattern)])
    def function(s):
        if isinstance(s, bytes):
            s=str(s, 'UTF-8')
        latest=False
        for sense,regex in elements:
            if regex.match(s):
                latest=sense
        return latest
    return function
