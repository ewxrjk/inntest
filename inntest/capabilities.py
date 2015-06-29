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

def test_capabilities():
    """inntest.Tests.test_capabilites()

    Tests the CAPABILITIES command.

    """
    with inntest.connection() as conn:
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
