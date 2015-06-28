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
import base64,hashlib,logging,os,struct,threading,time

seed=os.urandom(32)
sequence=0
lock=threading.Lock()

def _unique(alphabet=None):
    """inntest.utils._unique() -> BYTES

    Returns a unique (but not necessarily unpredictable) string.
    This is used for picking message IDs.

    Optional argument:
    alphabet -- set of characters that may appear in the result.

    """
    while True:
        with lock:
            global sequence
            latest=sequence
            sequence+=1
        h=hashlib.sha256()
        h.update(seed)
        h.update(struct.pack("<q", latest))
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

def _groupname():
    return inntest.hierarchy+b'.'+_unique(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")

def _ident(ident=None):
    """inntest.utils._ident([IDENT]) -> IDENT

    Returns a message ID.  If IDENT is None, one is picked;
    otherwise IDENT is used.

    """
    if ident is None:
        return b'<' + _unique() + b'@' + inntest.domain + b'>'
    else:
        return nntpbits._normalize(ident)

def _date(when=None):
    """inntest.utils._date() -> BYTES

    Returns the date in a format suitable for use in news
    articles.

    """
    if when==None:
        when=time.time()
    return bytes(time.strftime("%a, %d %b %Y %H:%M:%S +0000",
                               time.gmtime(when)),
                 'ascii')

# -------------------------------------------------------------------------
# Local server support

class TestServer(nntpbits.NewsServer):
    """inntest.util.TestServer() -> SERVER

    News server class that accepts all articles fed to it.
    """
    def __init__(self, conncls=nntpbits.ServerConnection):
        nntpbits.NewsServer.__init__(self, conncls=conncls)
        self.ihave_checked=[]
        self.ihave_submitted={}

    def __enter__(self):
        return self

    def __exit__(self, et, ev, etb):
        if et is not None:
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

def _local_server():
    """inntest.utils._local_server() -> SERVER

    Create an inntest.utils.TestServer and bind it to the local server
    address.  This is used by propagation tests.

    """
    ls=TestServer()
    ls.listen_address(inntest.localserveraddress[0],
                      inntest.localserveraddress[1],
                      wait=False,
                      daemon=True)
    return ls
