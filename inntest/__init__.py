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

Configuration:
address -- a (name,port) tuple for the news server to test.
group -- newsgroup for testing.
hierarchy -- hierarchy for testing.
email -- email address for test postings.  Default invalid@invalid.invalid.
domain -- domain for message IDs.  Default test.terraraq.uk.
localserveraddress -- address for local server as (name,port) tuple.
timelimit -- how log to wait for propagation.
trigger -- command to trigger peering, etc.


"""
from inntest.Tests import *

address=(None, 119)
domain=b'test.terraraq.uk'
email=b'invalid@invalid.invalid'
group=b'local.test'
hierarchy=None
localserveraddress=('*',1119)
timelimit=60
trigger=None
trigger_timeout=5

def _fixconfig():
    global domain, email, group, hierarchy
    domain=nntpbits._normalize(domain)
    email=nntpbits._normalize(email)
    group=nntpbits._normalize(group)
    if hierarchy is None:
        hierarchy=b'.'.join(group.split(b'.')[:-1])
    hierarchy=nntpbits._normalize(hierarchy)

localserverclass=TestServer
seed=os.urandom(32)
sequence=0
lock=threading.Lock()
