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
import logging
import traceback

_fails = []
_xfails = []
_compats = []
_skips = []
_testname = None

_log = None


def log(newlog=None):
    """log() -> LOGGER
    log(LOGGER) -> LOGGER

    Get or set the logging.Logger to use within the test system.

    """
    global _log
    if newlog is not None:
        _log = newlog
    return _log


class _Failed(Exception):
    pass


def list_tests():
    """inntest.list_tests() -> LIST

    Returns a list of tests.
    """
    tests = []
    for member in dir(inntest):
        if member[0:5] == 'test_':
            tests.append(member)
    return tests


def run_test(test_name, *args, **kwargs):
    """inntest.run_test(NAME, ...) -> FAILS, XFAILS, COMPATS, SKIPS

    Run the test NAME.

    """
    global _fails, _xfails, _compats, _skips, _testname
    _fails = []
    _xfails = []
    _compats = []
    _skips = []
    _testname = test_name
    if _log is None:
        log(logging.getLogger(__name__))
    method = getattr(inntest, test_name, None)
    if method is None:
        raise Exception("no such test as '%s'" % test_name)
    try:
        _log.info("Running test %s" % test_name)
        method(*args, **kwargs)
    except _Failed as e:
        _log.error("%s" % traceback.format_exc())
    except Exception as e:
        _log.error("Test %s failed: %s" % (test_name, e))
        _log.error("%s" % traceback.format_exc())
        _fails.append(e)
    _log.info("Completed test %s" % test_name)
    return (_fails, _xfails, _compats, _skips)


def fail(description):
    """inntest.running.fail(DESCRIPTION)

    Log a non-fatal failure.

    A failure means an unexpected difference from the specification.
    """
    _log.warn("FAILURE: %s" % (description))
    _fails.append(description)


def failhard(description):
    """inntest.running.failhard(DESCRIPTION)

    Log a fatal failure.  Raises an exception rather than
    returning.

    A failure means an unexpected difference from the specification.
    failhard() is only used instead of fail() when the test cannot proceed
    further.

    """
    _log.error("FAILURE: %s" % (description))
    _fails.append(description)
    raise _Failed(description)


def xfail(description):
    """inntest.running.xfail(DESCRIPTION)

    Log a non-fatal expected failure.

    An expected failure means a known difference but unjustified
    different from the specification.
    """
    _log.warn("EXPECTED FAILURE: %s" % (description))
    _xfails.append(description)


def xfailhard(description):
    """inntest.running.xfailhard(DESCRIPTION)

    Log a fatal expected failure.  Raises an exception rather than
    returning.

    An expected failure means a known difference but unjustified different from
    the specification.  xfailhard() is only used instead of xfail() when the
    test cannot proceed further.

    """
    _log.error("EXPECTED FAILURE: %s" % (description))
    _xfails.append(description)
    raise _Failed(description)


def compat(description):
    """inntest.running.compat(DESCRIPTION)

    Log a compatibility variation from the specification.

    A compatibility variation means a known difference from the specification
    for which a justification is given.  The justification might be that the
    specification is wrong, or compatibility with some other system that does
    not meet the specification.  (The justification need not be correct - for
    instance compatibility with a system that is no longer used, or with a
    completely hypothetical system is sufficient.)

    """
    _log.error("COMPATIBILITY: %s" % (description))
    _compats.append(description)


def skip(description):
    """inntest.running.skip(DESCRIPTION)

    Log a skipped test."""
    _log.warn("SKIPPED: %s" % (description))
    _skips.append(description)
