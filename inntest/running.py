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
import inntest
import logging,traceback

_fails=[]
_xfails=[]
_skips=[]
_testname=None

class _Failed(Exception):
    pass

def list_tests():
    """inntest.list_tests() -> LIST

    Returns a list of tests.
    """
    tests=[]
    for member in dir(inntest):
        if member[0:5] == 'test_':
            tests.append(member)
    return tests

def run_test(test_name, *args, **kwargs):
    """inntest.run_test(NAME, ...) -> FAILS, XFAILS, SKIPS

    Run the test NAME.

    """
    global _fails, _xfails, _skips, _testname
    _fails=[]
    _xfails=[]
    _skips=[]
    _testname=test_name
    method=getattr(inntest, test_name, None)
    if method is None:
        raise Exception("no such test as '%s'" % test_name)
    try:
        logging.info("Running test %s" % test_name)
        method(*args, **kwargs)
    except _Failed as e:
        logging.error("%s" % traceback.format_exc())
    except Exception as e:
        logging.error("Test %s failed: %s" % (test_name, e))
        logging.error("%s" % traceback.format_exc())
        _fails.append(e)
    return (_fails, _xfails, _skips)

def fail(description):
    """inntest.running.fail(DESCRIPTION)

    Log a non-fatal failure."""
    logging.warn("Test %s FAILURE: %s" % (_testname, description))
    _fails.append(description)

def failhard(description):
    """inntest.running.failhard(DESCRIPTION)

    Log a fatal failure.  Raises an exception rather than
    returning.

    """
    logging.error("Test %s FAILURE: %s" % (_testname, description))
    _fails.append(description)
    raise _Failed(description)

def xfail(description):
    """inntest.running.xfail(DESCRIPTION)

    Log a non-fatal expected failure."""
    logging.warn("Test %s EXPECTED FAILURE: %s" % (_testname, description))
    _xfails.append(description)

def xfailhard(description):
    """inntest.running.xfailhard(DESCRIPTION)

    Log a fatal expected failure.  Raises an exception rather than
    returning.

    """
    logging.error("Test %s EXPECTED FAILURE: %s" % (_testname, description))
    _xfails.append(description)
    raise _Failed(description)

def skip(description):
    """inntest.running.skip(DESCRIPTION)

    Log a skipped test."""
    logging.warn("Test %s SKIPPED: %s" % (_testname, description))
    _skips.append(description)
