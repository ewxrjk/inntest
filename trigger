#! /bin/sh
#
# Trigger script invoke from nntpbits tests
#
set -e
. ./config
${REALLY} su ${USER} -s /bin/sh -c "$PREFIX/bin/ctlinnd -s flush ''"
${REALLY} su ${USER} -s /bin/sh -c "$PREFIX/bin/nntpsend -P ${LOCALPORT}"
