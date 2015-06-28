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
import logging,os,time
from inntest.list import _list_active_re

def test_newgroups(create="ctlinnd -s newgroup %s",
                   remove="ctlinnd -s rmgroup %s"):
    """inntest.Tests.test_newgroups(CREATE, REMOVE)

    Test NEWGROUPS.

    The CREATE argument should contain the string '%s', which will
    be substituted with a newsgroup name to create.  Similarly
    REMOVE will be used to remove it.

    """
    with nntpbits.ClientConnection(inntest.address) as conn:
        conn._require_reader() # cheating
        start=conn.date()
        while start==conn.date():
            time.sleep(0.25)
        group=inntest.utils._groupname()
        cmd=create % str(group, 'ascii')
        logging.info("executing: %s" % cmd)
        rc=os.system(cmd)
        if rc != 0:
            raise Exception("Create command failed (%d)" % rc)
        try:
            found=False
            for line in conn.newgroups(start):
                m=_list_active_re.match(line)
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
