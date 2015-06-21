import nntpbits
import base64,hashlib,inspect,logging,os,struct,threading,time

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
                 localserver=('*',1119),
                 timelimit=60,
                 trigger=None):
        self.address=address
        self.port=port
        self.group=nntpbits._normalize(group)
        self.email=nntpbits._normalize(email)
        self.domain=b'test.terraraq.uk'
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
    # Tests

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
        conn.quit()

    def test_post_propagates(self, ident=None, description=b'propagation test'):
        """t.test_post_propagates([ident=IDENT][description=SUBJECT])

        Posts to the test newsgroup and verifies that the article
        propagates to the test server.

        If IDENT is specified then this value will be used as the
        message ID.

        If DESCRIPTION is specified then it will appear in the subject
        line.

        Returns True on success and False on failure.
        """
        ident=self._ident(ident)
        with self._local_server() as s:
            self.test_post(ident, description)
            if self.trigger is not None:
                rc=os.system(self.trigger)
                if rc != 0:
                    logging.error("Trigger wait status: %#04x" % rc)
            limit=time.time()+self.timelimit
            while time.time() < limit:
                with s.lock:
                    if ident in s.ihave_submitted:
                        break
            if ident not in s.ihave_submitted:
                raise Exception("article never propagated")
