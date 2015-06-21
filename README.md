INN Test Utilities
==================

This is a test system for INN.  It's not very complete yet.  It
requires Python 3.4.

1. Edit `config` to meet your local settings.
2. Create `tnews` user and group.  (You can select a different name in
   config.)
3. Run `test-all` to build, install and test INN.
4. Alternatively run `build` to build it and then indidivual test
   scripts to install and test with particular configurations.

The test configurations are:

1. `test-innfeed` - default test configuration
2. `test-nntpsend` - test with nntpsend and buffindexed overview

If anything goes wrong and you can't see why, consult `*.log` files.

The tests are actually run by `tests.py`, which in turn uses
`nntpbits/Tests.py` to do the work.  This is part of a general NNTP
support framework; see the other files inside `nntpbits` for details,
or experiment with the utilities `post.py`, `getgroup.py` and
`server.py` which all use it.

With the exception of the Python suppressions, this work is:

Copyright 2015 Richard Kettlewell

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
