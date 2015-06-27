INN Test Utilities
==================

This is a test system for
[INN](http://www.eyrie.org/~eagle/software/inn/).  It’s not very
complete yet.  It requires Python 3.4.

Basics
------

1. Edit `config` to meet your local settings.
2. Create `tnews` user and group.  (You can select a different name in
   config.)
3. Run `test-all` to build, install and test INN.

If anything goes wrong and you can’t see why, consult `*.log` files.

Individual Configurations
-------------------------

A more fine-grained approach is to run `build` to build INN and then
run individual test scripts to install and test with particular
configurations.

The test configurations are:

1. `test-innfeed` - default test configuration
2. `test-nntpsend` - test with nntpsend and buffindexed overview

Manual Control
--------------

You can start and stop the server in its current configuration, and
run tests by hand:

    ./start
    ./test-nntpbits
    # ... edit, repeat ...
    ./shutdown

Using valgrind
--------------

Either set `VALGRIND=true` in `config`, or pass it in as environment variable:

    VALGRIND=true ./test-innfeed

Coverage
--------

You can enable code coverage recording, with a suitable compiler.
Example:

    CC="gcc --coverage" CFLAGS="-g -O0" ./test-all

Note that since `./build` does `make check` the results will include
coverage information from that too.  If you want to exclude this data
by manually running `./build` with options above and then remove the
`*.gcda` files:

    find ../inn-build -name '*.gcda' -delete

gcov likes to write its `*.gcda` files into the build directory, so
make sure that it, and all its subdirectories, are writable by the
user the news server runs as.

I use [Viewgcov](https://github.com/ewxrjk/viewgcov) to inspect the
results.  Start it in the build directory and select File->Refresh.

Sanitizers
----------

You can enable sanitizers, if you have a suitable compiler.  Examples:

    CC="gcc -fsanitize=address,undefined" \
      CFLAGS="-g -O1 -fno-optimize-sibling-calls -fno-omit-frame-pointer -fno-sanitize-recover" \
      ./test-all

Note that the build process runs `make check`, so that had better be
‘clean’ under your chosen sanitizer options.  It’s likely to be easier
to debug any issues directly rather than via inntest.

Look in `$PREFIX/log/errlog` for error log output from innd.

nntpbits Framework
------------------

The tests are actually run by `tests.py`, which in turn uses
`nntpbits/Tests.py` to do the work.  This is part of a general NNTP
support framework; see the other files inside `nntpbits` for details,
or experiment with the utilities `post.py`, `getgroup.py` and
`server.py` which all use it.

Copyright
---------

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
