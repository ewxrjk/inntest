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
"""NNTP support utilities"""
from nntpbits.Connection import *
from nntpbits.ClientConnection import *
from nntpbits.ServerConnection import *
from nntpbits.NewsServer import *
from nntpbits.Tests import *
import threading,time

def _normalize(s):
    if isinstance(s, str):
        return bytes(s, 'ascii')
    else:
        return s

# Stopping --------------------------------------------------------------------

stopping=False
stopping_lock=threading.Lock()

class _Stop(Exception):
    def __str__(self):
        return "nntpbits._Stop"

def _maybe_stop():
    with stopping_lock:
        if stopping:
            raise _Stop()

# Waiting for outstanding threads ---------------------------------------------

outstanding_lock=threading.Lock()
outstanding=0

def start_thread(t):
    global outstanding
    with outstanding_lock:
        outstanding+=1
        try:
            t.start()
        except Exception:
            outstanding-=1
            raise

def finished_thread():
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
                return
        time.sleep(0.125)
