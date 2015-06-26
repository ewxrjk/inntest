#! /usr/bin/python3
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
import argparse,logging,os,sys
import nntpbits

def main(argv):
    p=argparse.ArgumentParser()
    p.add_argument('-s', '--server', help='Server name',
                   default='news')
    p.add_argument('-p', '--port', help='Server port',
                   type=int, default=119)
    p.add_argument('GROUP', help='Group name', type=str)
    p.add_argument('-d', '--debug', help='Enable debugging',
                   action='store_const', const='DEBUG', default='INFO')
    r=p.parse_args(argv)
    logging.basicConfig(level=r.debug)
    dump_group(r.server, r.port, r.GROUP)

def dump_group(server, port, group):
    with nntpbits.ClientConnection((server,port)) as client:
        (count, low, high)=client.group(group)
        linesep=bytes(os.linesep, 'ascii')
        for number in range(low, high+1):
            _,_,article=client.article(number)
            if article is not None:
                with open("%s:%d" % (group,number), "wb") as f:
                    for line in article:
                        f.write(line)
                        f.write(linesep)
                    f.flush()

if __name__ == '__main__':
    main(sys.argv[1:])
