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
"""NNTP support utilities

Classes:
  nntpbits.NewsServer -- base class for news servers
  nntpbits.ClientConnection -- an NNTP client connection
  nntpbits.ServerConnection -- an NNTP server connection
  nntpbits.Connection -- base class for connections
"""
from nntpbits.Connection import *
from nntpbits.ClientConnection import *
from nntpbits.ServerConnection import *
from nntpbits.NewsServer import *
import threading,time

def _normalize(s):
    """_normalize(STR|BYTES) -> BYTES

    Converts the argument to a bytes object.

    """
    if isinstance(s, list):
        return [_normalize(line) for line in s]
    if not isinstance(s, bytes):
        return bytes(s, 'ascii')
    else:
        return s

# Stopping --------------------------------------------------------------------

stopping=False
stopping_lock=threading.Lock()

class _Stop(Exception):
    """Exception class raised stop threads."""
    def __str__(self):
        return "nntpbits._Stop"

def _maybe_stop():
    """_maybe_stop()

    Raise an exception if threads are to stop.

    """
    with stopping_lock:
        if stopping:
            raise _Stop()

# Waiting for outstanding threads ---------------------------------------------

outstanding_lock=threading.Lock()
outstanding=0

def start_thread(t):
    """start_thread(THREAD)

    Update counters and start a thread.

    """
    global outstanding
    with outstanding_lock:
        outstanding+=1
        try:
            t.start()
        except Exception:
            outstanding-=1
            raise

def finished_thread():
    """finished_thread()

    Called in a thread to reduce update counters.

    """
    global outstanding
    with outstanding_lock:
        outstanding-=1

def stop():
    """Stop nntpbits threads

    This is a whole-process action, so currently only one news server
    per process is supported.

    """
    global outstanding
    global stopping
    with stopping_lock:
        stopping=True
    while True:
        with outstanding_lock:
            if outstanding == 0:
                break
        time.sleep(0.125)
    with stopping_lock:
        stopping=False
