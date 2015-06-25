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
import nntpbits
import base64,calendar,hashlib,inspect,logging,os,re,struct,threading,time

class TestServer(nntpbits.NewsServer):
    def __init__(self, conncls=nntpbits.ServerConnection):
        nntpbits.NewsServer.__init__(self, conncls=conncls)
        self.ihave_checked=[]
        self.ihave_submitted={}

    def __enter__(self):
        return self

    def __exit__(self, et, ev, etb):
        logging.debug("TestServer.__exit__: %s / %s / %s" % (et, ev, etb))
        nntpbits.stop()

    def ihave_check(self, ident):
        with self.lock:
            self.ihave_checked.append(ident)
        return (335, b'OK')

    def ihave(self, ident, article):
        with self.lock:
            if ident in self.ihave_submitted:
                return (435, b'Duplicate')
            self.ihave_submitted[ident]=article
        return (235, b'OK')

class Tests(object):
    """nntpbits.Tests(ADDRESS, PORT) -> test state object

    ADDRESS, PORT is the news server to test.

    Optional keyword arguments:
    group -- newsgroup for testing.  Default local.test
    hierarchy -- hierarchy for testing.  Default inferred from group.
    email -- email address for test postings.  Default invalid@invalid.invalid
    domain -- domain for message IDs.  Default test.terraraq.uk
    localserver -- address for local server as (address,port) tuple
    timelimit -- how log to wait for propagation
    trigger -- command to trigger peering, etc

    GROUP should be a newsgroup to use for testing.  The default is
    local.test.

    EMAIL should be the email address to use in the From: field.  The
    default is invalid@invalid.invalid.

    GROUP and EMAIL may be bytes objects or strings.

    """
    def __init__(self, address, port,
                 domain=b'test.terraraq.uk',
                 email=b'invalid@invalid.invalid',
                 group=b"local.test",
                 hierarchy=None,
                 localserver=('*',1119),
                 timelimit=60,
                 trigger=None):
        self.address=address
        self.port=port
        self.group=nntpbits._normalize(group)
        if hierarchy is None:
            self.hierarchy=b'.'.join(self.group.split(b'.')[:-1])
        else:
            self.hierarchy=nntpbits._normalize(hierarchy)
        self.email=nntpbits._normalize(email)
        self.domain=nntpbits._normalize(domain)
        self.localserveraddress=localserver
        self.localserverclass=TestServer
        self.localserver=None
        self.timelimit=timelimit
        self.trigger=trigger
        self.seed=os.urandom(48)
        self.sequence=0
        self.lock=threading.Lock()

    def _unique(self):
        with self.lock:
            sequence=self.sequence
            self.sequence+=1
        h=hashlib.sha384()
        h.update(self.seed)
        h.update(struct.pack("<q", sequence))
        return base64.b64encode(h.digest())

    def _ident(self, ident=None):
        if ident is None:
            return b'<' + self._unique() + b'@' + self.domain + b'>'
        else:
            return nntpbits._normalize(ident)

    def _date(self):
        return bytes(time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                                   time.gmtime()),
                     'ascii')

    # -------------------------------------------------------------------------
    # Enumerating and running tests

    @classmethod
    def list_tests(cls):
        """nntpbits.Tests.list_tests() -> LIST

        Returns a list of tests.
        """
        tests=[]
        for member in dir(cls):
            if member[0:5] == 'test_':
                tests.append(member)
        return tests

    def run_test(self, test_name, *args, **kwargs):
        """t.run_test(NAME, ...)

        Run the test NAME.

        """
        method=getattr(self, test_name, None)
        if method is None:
            raise Exception("no such test as '%s'" % test_name)
        return method(*args, **kwargs)

    # -------------------------------------------------------------------------
    # Local server support

    def _local_server(self):
        self.localserver=TestServer()
        self.localserver.listen_address(self.localserveraddress[0],
                                        self.localserveraddress[1],
                                        wait=False,
                                        daemon=True)
        return self.localserver

    # -------------------------------------------------------------------------
    # Testing POST

    def test_post(self, ident=None, description=b"posting test"):
        """t.test_post([ident=IDENT][description=SUBJECT])

        Posts to the test newsgroup and verifies that the article
        appears.

        If IDENT is specified then this value will be used as the
        message ID.

        If DESCRIPTION is specified then it will appear in the subject
        line.

        Returns True on success and False on failure.

        """
        ident=self._ident(ident)
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] ' + nntpbits._normalize(description) + b' (ignore)',
                 b'Message-ID: ' + ident,
                 b'',
                 b'nntpbits.Test test posting']
        conn=nntpbits.ClientConnection()
        conn.connect((self.address, self.port))
        conn.post(article)
        self._check_posted(conn, ident)
        conn.quit()

    def _check_posted(self, conn, ident):
        article_posted=conn.article(ident)
        if article_posted is None:
            raise Exception("article cannot be retrieved by message-ID")
        (count,low,high)=conn.group(self.group)
        overviews=conn.over(low,high)
        number_in_group=None
        for overview in overviews:
            (number,overview)=conn.parse_overview(overview)
            if overview[b'message-id:'] == ident:
                number_in_group=number
                break
        if number_in_group is None:
            raise Exception("article not found in group overview data")
        article_posted=conn.article(number_in_group)
        if article_posted is None:
            raise Exception("article cannot be retrieved from group")

    def test_post_propagates(self, ident=None, description=b'posting propagation test'):
        """t.test_post_propagates([ident=IDENT][description=SUBJECT])

        Posts to the test newsgroup and verifies that the article
        propagates to the test server.

        If IDENT is specified then this value will be used as the
        message ID.

        If DESCRIPTION is specified then it will appear in the subject
        line.

        Returns True on success and False on failure.
        """
        self._check_post_propagates(ident, description, self.test_post)

    def _check_post_propagates(self, ident, description,
                               do_post, *args, **kwargs):
        ident=self._ident(ident)
        with self._local_server() as s:
            do_post(*args, ident=ident, description=description, **kwargs)
            if self.trigger is not None:
                logging.info("executing trigger: %s" % self.trigger)
                rc=os.system(self.trigger)
                if rc != 0:
                    logging.error("Trigger wait status: %#04x" % rc)
            limit=time.time()+self.timelimit
            while time.time() < limit:
                with s.lock:
                    if ident in s.ihave_submitted:
                        break
                time.sleep(0.5)
            if ident not in s.ihave_submitted:
                raise Exception("article never propagated")

    # -------------------------------------------------------------------------
    # Testing IHAVE

    def test_ihave(self, ident=None, description=b"ihave test", _pathhost=None):
        """t.test_ihave([ident=IDENT][description=SUBJECT])

        Feed a post to the test newsgroup and verifies that the
        article appears.

        If IDENT is specified then this value will be used as the
        message ID.

        If DESCRIPTION is specified then it will appear in the subject
        line.

        Returns True on success and False on failure.

        """
        ident=self._ident(ident)
        if _pathhost is None:
            _pathhost=self.domain
        article=[b'Path: ' + _pathhost + b'!not-for-mail',
                 b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] ' + nntpbits._normalize(description) + b' (ignore)',
                 b'Message-ID: ' + ident,
                 b'Date: ' + self._date(),
                 b'',
                 b'nntpbits.Test test posting']
        conn=nntpbits.ClientConnection()
        conn.connect((self.address, self.port))
        conn.ihave(article)
        self._check_posted(conn, ident)
        conn.quit()

    def test_ihave_propagates(self, ident=None, description=b'ihave propagation test'):
        """t.test_ihave_propagates([ident=IDENT][description=SUBJECT])

        Feed a post to the test newsgroup and verifies that the article
        propagates to the test server.

        If IDENT is specified then this value will be used as the
        message ID.

        If DESCRIPTION is specified then it will appear in the subject
        line.

        Returns True on success and False on failure.
        """
        self._check_post_propagates(ident, description,
                                    self.test_ihave,
                                    _pathhost=b'nonesuch.' + self.domain)

    # -------------------------------------------------------------------------
    # Testing LIST

    def test_list(self, wildmat=None):
        """t.test_list()

        Tests the LIST command.

        Uses CAPABILITIES to enumerate all the LIST subcommands
        supported and verifies that their output follows the right
        syntax.  Then (if possible) switches to reader mode and
        repeats the exercise.
        """
        conn=nntpbits.ClientConnection()
        conn.connect((self.address, self.port))
        for kw in conn.capabilities_list():
            self._test_list(conn, kw)
        if b'MODE-READER' in conn.capabilities():
            conn._mode_reader() # cheating
            for kw in conn.capabilities_list():
                self._test_list(conn, kw, wildmat)
        # TODO check with nontrivial wildmat
        conn.quit()

    def test_list_wildmat(self, hierarchy=None):
        """t.test_list_wildmat()

        Tests the LIST command with wildmats

        Uses CAPABILITIES to enumerate all the LIST subcommands
        supported and, for those that can accept a wildmat argument,
        verifies that their output follows the right syntax.  Then (if
        possible) switches to reader mode and repeats the exercise.

        """
        if hierarchy is None:
            hierarchy=self.hierarchy
        self.test_list(wildmat=hierarchy+b'.*')

    # LIST subcommands that can take a wildmat
    _list_wildmat=[ b'ACTIVE',
                    b'ACTIVE.TIMES',
                    b'NEWSGROUPS',
                    b'COUNTS',
                    b'SUBSCRIPTIONS']

    # Regexps that LIST subcommand output must match
    _list_active_re=re.compile(b'^(\\S+) +(\\d+) +(\\d+) +([ynmxj]|=\S+)$')
    _list_active_times_re=re.compile(b'^(\\S+) +(\d+) +(.*)$')
    _list_distrib_pats_re=re.compile(b'^(\\d+):([^:]+):(.*)$')
    _list_newsgroups_re=re.compile(b'^(\\S+)[ \\t]+(.*)$')
    _list_headers_re=re.compile(b'^(:?\\S+)$')
    # RFC6048 extras
    _list_counts_re=re.compile(b'^(\\S+) +(\\d+) +(\\d+) +(\\d+) +([ynmxj]|=\S+)$')
    _list_distributions_re=re.compile(b'^(\\S+)[ \t]+(.*)$')
    _list_moderators_re=re.compile(b'^([^:]+):(.*)$') # TODO %%/%s rules
    _list_motd_re=re.compile(b'')                     # anything goes
    _list_subscriptions_re=re.compile(b'^(\\S+)$')

    def _test_list(self, conn, kw, wildmat=None):
        if wildmat is None:
            verify=lambda s: True
        else:
            if kw not in self._list_wildmat:
                return
            verify=Tests._wildmat_to_method(wildmat)
        try:
            lines=conn.list(kw, wildmat)
        except Exception as e:
            # Can't check this one, but not worth failing a test for
            logging.error(e)
            return
        name='list_'+str(kw, 'ascii').replace('.', '_').lower()
        regex_name='_'+name+'_re'
        regex=getattr(self, regex_name, None)
        if regex is not None:
            for line in lines:
                m=regex.match(line)
                if not m:
                    raise Exception("LIST %s: malformed line: %s" % (kw, line))
                if not verify(m.group(1)):
                    raise Exception("LIST %s: malformed group name: %s" % (kw, line))
            return
        method_name='_check_' + name
        method=getattr(self, method_name, None)
        if method is None:
            logging.error("don't know how to check LIST %s" % (kw))
        else:
            return method(lines, kw)

    def _check_list_overview_fmt(self, lines, kw):
        _overview_initial=[b'Subject:',
                           b'From:',
                           b'Date:',
                           b'Message-ID:',
                           b'References:']
        for i in range(0, len(_overview_initial)):
            if _overview_initial[i].lower() != lines[i].lower():
                raise Exception("LIST OVERVIEW.FMT: header %d wrong: %s"
                                % (i+1, lines[i]))
        if lines[5].lower() != b'bytes:' and lines[5].lower() != b':bytes':
            raise Exception("LIST OVERVIEW.FMT: header %d wrong: %s"
                            % (6, lines[i]))
        if lines[6].lower() != b'lines:' and lines[6].lower() != b':lines':
            raise Exception("LIST OVERVIEW.FMT: header %d wrong: %s"
                            % (7, lines[i]))
        for i in range(7, len(lines)):
            if not lines[i].lower().endswith(b':full'):
                raise Exception("LIST OVERVIEW.FMT: header %d partial: %s"
                                % (i+1, lines[i]))

    @staticmethod
    def _wildmat_pattern_to_re(pattern):
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

    @staticmethod
    def _wildmat_to_method(wildmat):
        if isinstance(wildmat, bytes):
            wildmat=str(wildmat, 'UTF-8')
        elements=[]
        for pattern in wildmat.split(','):
            if pattern[0] == '!':
                sense=False
                pattern=pattern[1:]
            else:
                sense=True
            elements.append([sense, Tests._wildmat_pattern_to_re(pattern)])
        def method(s):
            if isinstance(s, bytes):
                s=str(s, 'UTF-8')
            latest=False
            for sense,regex in elements:
                if regex.match(s):
                    latest=sense
            return latest
        return method

    # -------------------------------------------------------------------------
    # Testing DATE

    def test_date(self):
        """t.test_date()

        Tests the DATE command.

        As well as checking the syntax, verifies that the server's
        clock is reasonably accurate.

        """
        conn=nntpbits.ClientConnection()
        conn.connect((self.address, self.port))
        now=int(time.time())
        d=conn.date()
        m=re.match(b'^(\\d\\d\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)(\\d\\d)$',
                   d)
        if not m:
            raise Exception('DATE: malformed response: %s' % d)
        year=int(m.group(1))
        month=int(m.group(2))
        day=int(m.group(3))
        hour=int(m.group(4))
        minute=int(m.group(5))
        second=int(m.group(6))
        if year < 2015: raise Exception('DATE: implausible year: %s' % d)
        if month < 1 or month > 12: raise Exception('DATE: bad month: %s' % d)
        if day < 1 or day > 31: raise Exception('DATE: bad day: %s' % d)
        if hour > 23: raise Exception('DATE: bad hour: %s' % d)
        if minute > 59: raise Exception('DATE: bad minute: %s' % d)
        if second > 59: raise Exception('DATE: bad second: %s' % d)
        t=calendar.timegm([year, month, day, hour, minute, second])
        delta=abs(t-now)
        if delta > 60:
            raise Exception("DATE: inaccurate clock: %s (at %d)" % (d, now))
        conn.quit()

    # -------------------------------------------------------------------------
    # Testing HELP

    def test_help(self):
        """t.test_help()

        Tests the HELP command.

        """
        conn=nntpbits.ClientConnection()
        conn.connect((self.address, self.port))
        def check(which):
            lines=conn.help()
            for line in lines:
                try:
                    line.decode()
                except Exception as e:
                    raise Exception("HELP: %s response is not valid UTF-8"
                                    % which)
        check("first")
        conn._mode_reader()     # cheating
        check("second")
        conn.quit()
