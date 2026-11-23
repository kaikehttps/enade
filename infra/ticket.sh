#!/bin/sh
set -eu
p="$1"; shift
kinit -kt /run/cred/service.keytab "$p@ENADE.LAB"
(while sleep 1800; do kinit -kt /run/cred/service.keytab "$p@ENADE.LAB" || exit 1; done) &
exec "$@"

