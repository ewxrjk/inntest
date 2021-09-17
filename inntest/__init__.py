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
"""NNTP tests

"""
from inntest.utils import *

from inntest.article import *
from inntest.capabilities import *
from inntest.date import *
from inntest.errors_commands import *
from inntest.errors_group import *
from inntest.errors_overview import *
from inntest.errors_post import *
from inntest.hdr import *
from inntest.help import *
from inntest.listgroup import *
from inntest.list import *
from inntest.newgroups import *
from inntest.newnews import *
from inntest.over import *
from inntest.post import *

from inntest.running import list_tests, run_test

address = (None, 119)
domain = b'test.terraraq.uk'
email = b'invalid@invalid.invalid'
group = b'local.test'
hierarchy = None
localserveraddress = ('*', 1119)
timelimit = 60
trigger = None
trigger_timeout = 5
nnrp_user = b'user'
nnrp_password = b'password'
nntp_user = None
nntp_password = None


def configure(**kwargs):
    """inntest.configure(...)

    Set configuration for the test system.

    Keywords arguments:
    address -- a (name,port) tuple for the news server to test.
    group -- newsgroup for testing.
    hierarchy -- hierarchy for testing.
    email -- email address for test postings.  Default invalid@invalid.invalid.
    domain -- domain for message IDs.  Default test.terraraq.uk.
    localserveraddress -- address for local server as (name,port) tuple.
    timelimit -- how log to wait for propagation.
    trigger -- command to trigger peering, etc.
    nnrp_user -- NNRP login username
    nnrp_password -- NNRP login password
    nntp_user -- NNTP login username
    nntp_password -- NNTP login password

    """

    global address, domain, email, group, hierarchy, localserveraddress
    global timelimit, trigger, trigger_timeout
    for name, value in kwargs.items():
        if value is None:
            continue
        if name == 'address':
            address = value
        elif name == 'domain':
            domain = nntpbits._normalize(value)
        elif name == 'email':
            email = nntpbits._normalize(value)
        elif name == 'group':
            group = nntpbits._normalize(value)
        elif name == 'hierarchy':
            hierarchy = nntpbits._normalize(value)
        elif name == 'localserveraddress':
            localserveraddress = value
        elif name == 'timelimit':
            timelimit = int(value)
        elif name == 'trigger':
            trigger = value
        elif name == 'trigger_timeout':
            trigger_timeout = int(value)
        elif name == 'nnrp_user':
            nnrp_user = nntpbits._normalize(value)
        elif name == 'nnrp_password':
            nnrp_password = nntpbits._normalize(value)
        else:
            raise Exception("inntest.configure: unrecognized argument: %s"
                            % name)
    if hierarchy is None:
        hierarchy = b'.'.join(group.split(b'.')[:-1])


def connection():
    """inntest.connection()

    Return a connection to the news server to test.

    """
    return nntpbits.ClientConnection(inntest.address,
                                     nnrp_user=nnrp_user,
                                     nnrp_password=nnrp_password,
                                     nntp_user=nntp_user,
                                     nntp_password=nntp_password)
