#!/bin/sh
# Install the bug-hunt guard rails into this clone.
#
# .git/hooks is not tracked, so the hooks cannot live only there: a fresh clone
# would silently have no guard rails at all, and tests_gate_integrity.py would
# fail asserting the ones it expects. The reviewable copy is tools/hooks/ --
# these are a security control, so they belong in code review like anything
# else. This copies them into place.
#
# The hooks arm only on loop/* branches. Commits on main are unaffected.
#
#   tools/install_hooks.sh

set -e
cd "$(dirname "$0")/.."

common=$(git rev-parse --git-common-dir)
case "$common" in
  /*) ;;
  *) common="$PWD/$common" ;;
esac

mkdir -p "$common/hooks"
for h in pre-commit commit-msg pre-push; do
  cp "tools/hooks/$h" "$common/hooks/$h"
  chmod +x "$common/hooks/$h"
  echo "installed $h -> $common/hooks/$h"
done
