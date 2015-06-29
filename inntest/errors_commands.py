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
from inntest.list import _list_wildmat
from inntest.errors_group import _article_commands

def test_errors_bad_commands():
    """inntest.Tests.test_errors_bad_commands()

    Test error behavior for bad commands.

    """
    ret=[None]
    with inntest.connection() as conn:
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
                                    inntest.hierarchy+b'[.]*'])
            if code!=501 and code!=215:
                raise Exception("LIST ACTIVE: wrong response for bad argument: %s"
                                % conn.response)
            if code==215:
                conn.receive_lines()
            subcommands=conn.capability_arguments(b'LIST')
            if b'HEADERS' in subcommands:
                code,arg=conn.transact(b'LIST HEADERS NOTINNNTP')
                if code!=501:
                    raise Exception("LIST HEADERS: wrong response for bad argument: %s"
                                    % conn.response)
            for subcommand in subcommands:
                if subcommand not in _list_wildmat:
                    code,arg=conn.transact([b'LIST', subcommand, b'*'])
                    if code!=501:
                        raise Exception("LIST %s: wrong response for bad argument: %s"
                                        % (subcommand, conn.response))
        check('first')
        conn._mode_reader()     # cheating
        check("second")
        for cmd in _article_commands:
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
        for cmd in [b'NEWNEWS *', b'NEWGROUPS']:
            for arg in [b'',
                        b'990101',
                        b'19990101',
                        b'990101000000',
                        b'19990101000000',
                        b'19990101 000000 BST',
                        b'19990101 000000 GMT GMT',
                        b'19990101 240000',
                        b'19990101 000000 +0000',
                        b'19990101 000000 0000',
                        b'19990101 000000 -0000',
                        b'19990101 000000 00']:
                code,arg=conn.transact([cmd,arg])
                if code!=501:
                    raise Exception("%s: wrong response for bad argument: %s"
                                    % (cmd, conn.response))
    return ret[0]
