"""NNTP support utilities"""
from nntpbits.Connection import *
from nntpbits.ClientConnection import *
from nntpbits.ServerConnection import *
from nntpbits.NewsServer import *
from nntpbits.Tests import *

def _normalize(s):
    if isinstance(s, str):
        return bytes(s, 'ascii')
    else:
        return s
