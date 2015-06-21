import nntpbits
import base64,hashlib,inspect,os,struct,threading

class Tests(object):
    """nntpbits.Tests(CONN) -> test state object

    CONN should be an nntpbits.ClientConnection.

    Optional keyword arguments:
    group -- newsgroup for testing.  Default local.test
    email -- email address for test postings.  Default invalid@invalid.invalid
    domain -- domain for message IDs.  Default test.terraraq.uk

    GROUP should be a newsgroup to use for testing.  The default is
    local.test.

    EMAIL should be the email address to use in the From: field.  The
    default is invalid@invalid.invalid.

    GROUP and EMAIL may be bytes objects or strings.

    """
    def __init__(self,
                 conn,
                 domain=b'test.terraraq.uk',
                 email=b'invalid@invalid.invalid',
                 group=b"local.test"):
        self.conn=conn
        self.group=nntpbits._normalize(group)
        self.email=nntpbits._normalize(email)
        self.domain=b'test.terraraq.uk'
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

    def _ident(self):
        return b'<' + self._unique() + b'@' + self.domain + b'>'

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
        if ident is None:
            ident=self._ident()
        else:
            ident=nntpbits._normalize(ident)
        article=[b'Newsgroups: ' + self.group,
                 b'From: ' + self.email,
                 b'Subject: [nntpbits] ' + nntpbits._normalize(description) + b' (ignore)',
                 b'Message-ID: ' + ident,
                 b'',
                 b'nntpbits.Test test posting']
        self.conn.post(article)
        article_posted=self.conn.article(ident)
        if article_posted is None:
            raise Exception("article cannot be retrieved by message-ID")
        (count,low,high)=self.conn.group(self.group)
        overviews=self.conn.over(low,high)
        number_in_group=None
        for overview in overviews:
            (number,overview)=self.conn.parse_overview(overview)
            if overview[b'message-id:'] == ident:
                number_in_group=number
                break
        if number_in_group is None:
            raise Exception("article not found in group overview data")
        article_posted=self.conn.article(number_in_group)
        if article_posted is None:
            raise Exception("article cannot be retrieved from group")
