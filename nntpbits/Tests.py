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
    """nntpbits.TestServer() -> SERVER

    News server class that accepts all articles fed to it.
    """
    def __init__(self, conncls=nntpbits.ServerConnection):
        nntpbits.NewsServer.__init__(self, conncls=conncls)
        self.ihave_checked=[]
        self.ihave_submitted={}

    def __enter__(self):
        return self

    def __exit__(self, et, ev, etb):
        logging.debug("TestServer.__exit__: %s / %s / %s" % (et, ev, etb))
        nntpbits.stop()
        return False

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
        self.timelimit=timelimit
        self.trigger=trigger
        self.trigger_timeout=5
        self.seed=os.urandom(32)
        self.sequence=0
        self.lock=threading.Lock()

    def _unique(self, alphabet=None):
        """t._unique() -> BYTES

        Returns a unique (but not necessarily unpredictable) string.
        This is used for picking message IDs.

        Optional argument:
        alphabet -- set of characters that may appear in the result.

        """
        while True:
            with self.lock:
                sequence=self.sequence
                self.sequence+=1
            h=hashlib.sha256()
            h.update(self.seed)
            h.update(struct.pack("<q", sequence))
            # base64 is 3 bytes into 4 characters, so truncate to a
            # multiple of 3.
            unique=base64.b64encode(h.digest()[:18])
            suitable=True
            if alphabet is not None:
                for u in unique:
                    if u not in alphabet:
                        suitable=False
                        break
            if suitable:
                return unique

    def _groupname(self):
        return self.hierarchy+b'.'+self._unique(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

    def _ident(self, ident=None):
        """t._ident([IDENT]) -> IDENT

        Returns a message ID.  If IDENT is None, one is picked;
        otherwise IDENT is used.

        """
        if ident is None:
            return b'<' + self._unique() + b'@' + self.domain + b'>'
        else:
            return nntpbits._normalize(ident)

    def _date(self):
        """t._date() -> BYTES

        Returns the date in a format suitable for use in news
        articles.

        """
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
        """s._local_server() -> SERVER

        Create an nntpbits.TestServer and bind it to the local server
        address.  This is used by propagation tests.

        """
        ls=TestServer()
        ls.listen_address(self.localserveraddress[0],
                          self.localserveraddress[1],
                          wait=False,
                          daemon=True)
        return ls

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
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn.post(article)
            self._check_posted(conn, ident)

    def _check_posted(self, conn, ident):
        """s._check_posted(CONN, IDENT)

        Look for the article IDENT in the test group, using
        CONN as the client connection.

        """
        _,_,article_posted=conn.article(ident)
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
        _,_,article_posted=conn.article(number_in_group)
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
        """t._check_post_propagates(IDENT, DESCRIPTION, DO_POST, ...)

        Call do_post(ident=IDENT, description=DESCRIPTION, ..) to post
        a message and then verify it is fed back to us.

        """
        ident=self._ident(ident)
        with self._local_server() as s:
            do_post(*args, ident=ident, description=description, **kwargs)
            next_trigger=0
            limit=time.time()+self.timelimit
            while time.time() < limit:
                # See if the post has turned up
                with s.lock:
                    if ident in s.ihave_submitted:
                        break
                # Repeat the trigger if it's not helping
                if (self.trigger is not None
                       and next_trigger <= time.time()):
                    logging.info("execute: %s" % self.trigger)
                    rc=os.system(self.trigger)
                    if rc != 0:
                        logging.error("Trigger wait status: %#04x" % rc)
                    next_trigger=time.time()+self.trigger_timeout
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
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn.ihave(article)
            self._check_posted(conn, ident)

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
        # Need a nondefault pathhost so it will propagate back to us
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
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            def check():
                subcommands=conn.capability_arguments(b'LIST')
                for kw in subcommands:
                    self._test_list(conn, kw)
                # Default subcommand is ACTIVE
                if b'ACTIVE' in subcommands:
                    self._test_list(conn, None)
            check()
            if b'MODE-READER' in conn.capabilities():
                conn._mode_reader() # cheating
                check()

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
    # RFC6048 extras
    _list_counts_re=re.compile(b'^(\\S+) +(\\d+) +(\\d+) +(\\d+) +([ynmxj]|=\S+)$')
    _list_distributions_re=re.compile(b'^(\\S+)[ \t]+(.*)$')
    _list_moderators_re=re.compile(b'^([^:]+):(.*)$') # TODO %%/%s rules
    _list_motd_re=re.compile(b'')                     # anything goes
    _list_subscriptions_re=re.compile(b'^(\\S+)$')

    def _test_list(self, conn, kw, wildmat=None):
        """t._test_list(CONN, KW, [WILDMAT])

        Test a LIST subcommand on connection CONN.

        KW is the subcommand and WILDMAT is an optional wildmat
        pattern to supply.

        """
        # verify(GROUP) -> BOOL tests whether the group is acceptable
        # based on WILDMAT.
        if wildmat is None:
            verify=lambda s: True
        else:
            if kw not in self._list_wildmat:
                logging.warn("SKIPPING TEST of LIST %s, don't know how to check output"
                             % kw)
                return 'skip'
            verify=Tests._wildmat_to_function(wildmat)
        lines=conn.list(kw, wildmat)
        if kw is None:
            kw=b'ACTIVE'
        if lines is None:
            if kw in Tests._list_optional:
                return
            raise Exception("LIST %s: unexpected 503" % kw)
        # Find the regexp to verify/parse lines
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
        method_name='_check_' + name
        method=getattr(self, method_name, None)
        if method is None:
            logging.debug("don't know how to check LIST %s" % (kw))
        else:
            return method(lines, kw)

    def _check_list_overview_fmt(self, lines, kw):
        """t._check_list_overview_fmt(LINES, KW)

        Verify that the OVERFMT.FMT data is valid.

        """
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

    def _check_list_motd(self, lines, kw):
        """t._check_list_motd(LINES, KW)

        Verify that the MOTD data is valid.

        """
        for line in lines:
            try:
                line.decode()
            except Exception as e:
                raise Exception("LIST MOTD: %s response is not valid UTF-8"
                                % which)

    @staticmethod
    def _wildmat_pattern_to_re(pattern):
        """t._wildmat_pattern_to_re(PATTERN) -> RE

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

    @staticmethod
    def _wildmat_to_function(wildmat):
        """t._wildmat_to_function(WILDMAT) -> FUNCTION
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
            elements.append([sense, Tests._wildmat_pattern_to_re(pattern)])
        def function(s):
            if isinstance(s, bytes):
                s=str(s, 'UTF-8')
            latest=False
            for sense,regex in elements:
                if regex.match(s):
                    latest=sense
            return latest
        return function

    # -------------------------------------------------------------------------
    # Testing DATE

    def test_date(self):
        """t.test_date()

        Tests the DATE command.

        As well as checking the syntax, verifies that the server's
        clock is reasonably accurate.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
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

    # -------------------------------------------------------------------------
    # Testing HELP

    def test_help(self):
        """t.test_help()

        Tests the HELP command.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
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

    # -------------------------------------------------------------------------
    # Testing CAPABILTIES

    def test_capabilities(self):
        """t.test_capabilites()

        Tests the CAPABILITIES command.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            def check(which):
                cap = conn.capabilities()
                if len(cap) == 0:
                    raise Exception("CAPABILITIES: %s response empty/missing"
                                    % which)
                lcaps=conn.capability_arguments(b'LIST')
                if b'READER' in cap:
                    if not b'ACTIVE' in lcaps:
                        raise Exception("CAPABILITIES: %s: READER but no LIST ACTIVE"
                                        % which)
                    if not b'NEWSGROUPS' in lcaps:
                        raise Exception("CAPABILITIES: %s: READER but no LIST NEWSGROUPS"
                                        % which)
                if b'OVER' in cap:
                    if not b'READER' in cap:
                        raise Exception("CAPABILITIES: %s: OVER but no READER"
                                        % which)
                    if not b'OVERVIEW.FMT' in lcaps:
                        raise Exception("CAPABILITIES: %s: OVER but no LIST OVERVIEW.FMT"
                                        % which)
            check("first")
            if b'MODE-READER' in conn.capabilities():
                conn._mode_reader()     # cheating
                if not b'READER' in conn.capabilities():
                    raise Exception("CAPABILITIES: no READER after MODE READER")
                check("second")

    # -------------------------------------------------------------------------
    # Testing ARTICLE/HEAD/BODY/STAT

    def test_article_id(self):
        """t.test_article_id()

        Test article lookup by <message id>.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            articles=self._post_articles(conn)
            for cmd,parse in Tests._article_lookup_commands():
                logging.debug("test_article_id %s" % cmd)
                method=getattr(conn, cmd)
                for ident,article in articles:
                    r_number,r_ident,r=method(ident)
                    if ident != r_ident:
                        raise Exception("%s: returned wrong ident (%s vs %s)"
                                        % (cmd, ident, r_ident))
                    r_header,r_body,r_ident=parse(r)
                    self._check_article(cmd, ident, article,
                                        r_header, r_body, r_ident)

    def test_article_number(self):
        """t.test_article_id()

        Test article lookup by number.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            articles=self._post_articles(conn)
            count,low,high=conn.group(self.group)
            ident_to_number={}
            r_number,r_ident,_=conn.stat()
            while r_ident:
                for ident,article in articles:
                    if r_ident == ident:
                        ident_to_number[ident]=r_number
                r_number,r_ident,_=conn.next()
            for cmd,parse in Tests._article_lookup_commands():
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
                    self._check_article(cmd, ident, article,
                                        r_header, r_body, r_ident)

    @staticmethod
    def _article_lookup_commands():
        return[['article', Tests._parse_article],
               ['head', Tests._parse_article],
               ['body', lambda body: (None, body, None)],
               ['stat', lambda ident: (None, None, ident)]]

    def _check_article(self, cmd, ident, article,
                       r_header, r_body, r_ident,
                       _allow_missing=set([])):
        header,body,_=Tests._parse_article(article)
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
                    if field in _allow_missing:
                        continue
                    raise Exception("%s: missing %s header"
                                    % (cmd, field))
                value=header[field]
                r_value=r_header[field]
                logging.debug("%s: %s <-> %s" % (field, value, r_value))
                if r_value != value:
                    raise Exception("%s: non-matching %s header: '%s' vs '%s'"
                                    % (cmd, field, value, r_value))
        # Body should match
        if r_body is not None:
            if body != r_body:
                raise Exception("%s: non-matching body: '%s' vs '%s'"
                                    % (cmd, body, r_body))

    _header_re=re.compile(b'^([a-zA-Z0-9\\-]+:)\\s+(.*)$')

    @staticmethod
    def _parse_article(article):
        """Tests._parse_article(ARTICLE) -> HEADER,BODY,IDENT

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
            m=Tests._header_re.match(line)
            if not m:
                raise Exception("Malformed article: %s" % article)
            field=m.group(1).lower()
            header[field]=m.group(2)
        return header,body,header[b'message-id:']

    def _post_articles(self, conn):
        """t._post_articles(CONN)

        Post some articles for test purposes.

        """
        articles=[]
        ident=self._ident()
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] articles-simple (ignore)',
                 b'Message-ID: ' + ident,
                 b'',
                 self._unique()]
        conn.post(article)
        articles.append([ident, article])

        ident=self._ident()
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] articles-keywords (ignore)',
                 b'Message-ID: ' + ident,
                 b'Keywords: this, that, the other',
                 b'',
                 self._unique()]
        conn.post(article)
        articles.append([ident, article])

        ident=self._ident()
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] articles-date (ignore)',
                 b'Message-ID: ' + ident,
                 b'Date: ' + self._date(),
                 b'',
                 self._unique()]
        conn.post(article)
        articles.append([ident, article])

        ident=self._ident()
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] articles-organization (ignore)',
                 b'Message-ID: ' + ident,
                 b'Organization: ' + self._unique(),
                 b'',
                 self._unique()]
        conn.post(article)
        articles.append([ident, article])

        ident=self._ident()
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] articles-user-agent (ignore)',
                 b'Message-ID: ' + ident,
                 b'User-Agent: test.terraraq.uk',
                 b'',
                 self._unique()]
        conn.post(article)
        articles.append([ident, article])

        return articles

    # -------------------------------------------------------------------------
    # Testing OVER

    def test_over_id(self):
        """t.test_over_id()

        Test OVER lookup by <message id>.

        NOTE: this has never been run since INN doesn't support OVER
        MSGID.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            if not b'OVER' in conn.capabilities():
                logging.warn("SKIPPING TEST because no OVER capability")
                return 'skip'
            if not b'MSGID' in conn.capability_arguments(b'OVER'):
                logging.warn("SKIPPING TEST because no OVER MSGID capability")
                return 'skip'
            articles=self._post_articles(conn)
            count,low,high=conn.group(self.group)
            for ident,article in articles:
                overviews=conn.over(ident)
                number,overview=conn.parse_overview(overviews[0])
                self._check_article(b'OVER', ident, article,
                                    overview, None, overview[b'message-id:'])

    def test_over_number(self):
        """t.test_over_id()

        Test OVER lookup by number.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            if not b'OVER' in conn.capabilities():
                logging.warn("SKIPPING TEST because no OVER capability")
                return 'skip'
            articles=self._post_articles(conn)
            count,low,high=conn.group(self.group)
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
                self._check_article(b'OVER', ident, article,
                                    ov[ident], None, ov[ident][b'message-id:'],
                                    allowmissing)

    # -------------------------------------------------------------------------
    # Testing HDR

    def test_hdr_number(self):
        """t.test_hdr_id()

        Test HDR lookup by number.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            if not b'HDR' in conn.capabilities():
                logging.warn("SKIPPING TEST because no HDR capability")
                return 'skip'
            articles=self._post_articles(conn)
            count,low,high=conn.group(self.group)
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
                        m=Tests._header_re.match(line)
                        if m.group(1) == header:
                            value=m.group(2)
                            if r_value != value:
                                raise Exception("HDR: non-matching %s header: '%s' vs '%s'"
                                                % (field, value, r_value))

    # -------------------------------------------------------------------------
    # Testing NEWNEWS

    def test_newnews(self):
        """t.test_newnews()

        Test NEWNEWS.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            if not b'NEWNEWS' in conn.capabilities():
                logging.warn("SKIPPING TEST because no NEWNEWS capability")
                return 'skip'
            start=conn.date()
            while start==conn.date():
                time.sleep(0.25)
            articles=self._post_articles(conn)
            new_idents=set(conn.newnews(self.hierarchy+b'.*', start))
            for ident,article in articles:
                if ident not in new_idents:
                    raise Exception("NEWNEWS: did not find %s" % ident)

    # -------------------------------------------------------------------------
    # Testing NEWGROUPS

    def test_newgroups(self,
                       create="ctlinnd -s newgroup %s",
                       remove="ctlinnd -s rmgroup %s"):
        """t.test_newgroups(CREATE, REMOVE)

        Test NEWGROUPS.

        The CREATE argument should contain the string '%s', which will
        be substituted with a newsgroup name to create.  Similarly
        REMOVE will be used to remove it.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            start=conn.date()
            while start==conn.date():
                time.sleep(0.25)
            group=self._groupname()
            cmd=create % str(group, 'ascii')
            logging.info("executing: %s" % cmd)
            rc=os.system(cmd)
            if rc != 0:
                raise Exception("Create command failed (%d)" % rc)
            try:
                found=False
                for line in conn.newgroups(start):
                    m=Tests._list_active_re.match(line)
                    if not m:
                        raise Exception("NEWGROUPS: malformed response: %s" % line)
                    if m.group(1)==group:
                        found=True
                        if not found:
                            raise Exception("NEWGROUPS: new group not listed")
            finally:
                cmd=remove % str(group, 'ascii')
                logging.info("executing: %s" % cmd)
                rc=os.system(cmd)
                if rc != 0:
                    raise Exception("Remove command failed (%d)" % rc)

    # -------------------------------------------------------------------------
    # Testing LISTGROUP

    def test_listgroup(self):
        """t.test_listgroup()

        Test LISTGROUP.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            if not b'HDR' in conn.capabilities():
                logging.warn("SKIPPING TEST because no HDR capability")
                return 'skip'
            articles=self._post_articles(conn)
            seen=set()
            conn.group(self.group)
            for number in conn.listgroup():
                _,_,lines=conn.head(number)
                for line in lines:
                    m=Tests._header_re.match(line)
                    if m.group(1).lower()==b'message-id:':
                        seen.add(m.group(2))
                        break
            for ident,article in articles:
                if not ident in seen:
                    raise Exception("LISTGROUP: failed to list %s" % ident)

    # -------------------------------------------------------------------------
    # Negative testing

    # Commands that check or fetch part of an article by ID, number or current
    _article_commands=[b'ARTICLE', b'HEAD', b'BODY', b'STAT']
    # Various offsets, representing attempts to tickle overflow behavior in
    # article number parsing
    _number_deltas=[100000, 1<<16, 1<<31, 1<<32, 1<<33, 1<<53]

    def test_errors_no_article(self):
        """t.test_errors_no_article()

        Test errors for nonexistent articles.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            for cmd in Tests._article_commands:
                code,arg=conn.transact([cmd, self._ident()])
                if code != 430:
                    raise Exception("%s: incorrect error for nonexistent article: %s"
                                    % (cmd, conn.response))
            if (b'OVER' in conn.capabilities()
                and b'MSGID' in conn.capability_arguments(b'OVER')):
                code,arg=conn.transact([b'OVER', self._ident()])
                if code != 430:
                    raise Exception("OVER: incorrect error for nonexistent article: %s"
                                    % (cmd, conn.response))
            if b'HDR' in conn.capabilities():
                code,arg=conn.transact([b'HDR', b'Subject', self._ident()])
                if code != 430:
                    raise Exception("OVER: incorrect error for nonexistent article: %s"
                                    % (cmd, conn.response))

    def test_errors_no_group(self):
        """t.test_errors_no_group()

        Test errors for nonexistent groups

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            for cmd in [b'GROUP', b'LISTGROUP']:
                code,arg=conn.transact([cmd, self._groupname()])
                if code != 411:
                    raise Exception("%s: incorrect error for nonexistent group: %s"
                                    % (cmd, conn.response))

    def test_errors_outside_group(self):
        """t.test_errors_outside_group()

        Test errors for commands issued outside a group.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            for cmd in [b'NEXT', b'LAST']:
                code,arg=conn.transact(cmd)
                if code != 412:
                    raise Exception("%s: incorrect error outside group: %s"
                                    % (cmd, conn.response))
            for cmd in Tests._article_commands:
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

    def test_errors_group_navigation(self):
        """t.test_errors_group_navigation()

        Test errors for group navigation commands.

        """
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            count,low,high=conn.group(self.group)
            for cmd in Tests._article_commands:
                for delta in Tests._number_deltas:
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

    def test_errors_group_overview(self):
        """t.test_errors_group_overview()

        Test range behavior for group overview commands.

        """
        skip='skip'
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            conn._require_reader() # cheating
            count,low,high=conn.group(self.group)
            if b'OVER' in conn.capabilities():
                skip=None
                for delta in Tests._number_deltas:
                    overviews=conn.over(low+delta, high+delta)
                    if len(overviews)!=0:
                        raise Exception("OVER: unexpected overview data: delta=%d"
                                        % delta)
                overviews=conn.over(high, low)
                if len(overviews)!=0:
                    raise Exception("OVER: unexpected overview data: reverse range")
            if b'HDR' in conn.capabilities():
                skip=None
                for delta in Tests._number_deltas:
                    headers=conn.hdr(b'Newsgroups', low+delta, high+delta)
                    if len(headers)!=0:
                        raise Exception("HDR: unexpected header data: delta=%d"
                                        % delta)
                headers=conn.over(high, low)
                if len(headers)!=0:
                    raise Exception("HDR: unexpected header data: reverse range")
            if skip=='skip':
                logging.warn("SKIPPING TEST because no OVER or HDR capability")
            return skip

    def test_errors_bad_commands(self):
        """t.test_errors_group_overview()

        Test error behavior for bad commands.

        """
        ret=[None]
        with nntpbits.ClientConnection((self.address, self.port)) as conn:
            def check(which):
                code,arg=conn.transact(b'NOTINNNTP')
                if code!=500:
                    raise Exception("Wrong response for bad command: %s"
                                    % conn.response)
                for cmd in [b'MODE', b'LIST']:
                    code,arg=conn.transact([cmd, b'NOTINNNTP'])
                    if code!=501:
                        raise Exception("%s: wrong response for bad argument: %s"
                                        % (cmd, conn.response))
                # INN accepts this, presumably relying on 3977 s4.3
                code,arg=conn.transact([b'LIST ACTIVE',
                                        self.hierarchy+b'[.]*'])
                if code!=501 and code!=215:
                    raise Exception("LIST ACTIVE: wrong response for bad argument: %s"
                                    % conn.response)
                if code==215:
                    conn.receive_lines()
            check('first')
            conn._mode_reader()     # cheating
            check("second")
            for cmd in Tests._article_commands:
                code,arg=conn.transact([cmd, b'1', b'2', b'3'])
                if code!=501:
                    raise Exception("%s: wrong response for bad argument: %s"
                                    % (cmd, conn.response))
                code,arg=conn.transact([cmd, b'junk'])
                if code!=501:
                    raise Exception("%s: wrong response for bad argument: %s"
                                    % (cmd, conn.response))
                code,arg=conn.transact([cmd, b'junk@junk'])
                if code!=501:
                    raise Exception("%s: wrong response for bad argument: %s"
                                    % (cmd, conn.response))
        return ret[0]
