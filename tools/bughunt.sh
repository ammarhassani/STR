#!/bin/bash
# Autonomous bug hunt over the STR codebase. Ralph-style: same prompt every
# iteration, all state in files, terminated by an exit code rather than by
# anything the agent says.
#
#   tools/bughunt.sh              20 iterations, 6h ceiling
#   tools/bughunt.sh 5            5 iterations
#   tools/bughunt.sh 1 3600       1 iteration, 1h ceiling
#
# Run it from the WORKTREE (../STR-loop), not from your main checkout. The
# worktree is why `git restore` and `git clean` inside the loop cannot reach
# your files, and why the loop cannot commit to main: git refuses to check out
# a branch that is already checked out elsewhere.

set -uo pipefail

ITERATIONS="${1:-20}"
DEADLINE="${2:-21600}"          # 6 hours

cd "$(dirname "$0")/.." || exit 1
mkdir -p .loop

branch=$(git rev-parse --abbrev-ref HEAD)
case "$branch" in
  loop/*) ;;
  *) echo "refusing: on branch '$branch'. The hooks only arm on loop/*."
     echo "  git worktree add ../STR-loop -b loop/night-1"
     exit 1 ;;
esac

# Headless `claude -p` cannot answer a permission prompt, so a missing allowlist
# does not fail loudly -- the agent works for ten minutes and is then denied the
# commit. Refuse to start rather than burn a night discovering that.
[ -f .claude/settings.json ] || {
  echo "refusing: no .claude/settings.json in this worktree."
  echo "  Without it every Bash call is denied and no iteration can commit."
  exit 1
}
grep -q '"Bash(git commit:\*)"' .claude/settings.json || {
  echo "refusing: .claude/settings.json does not allow 'git commit'."
  echo "  In headless mode 'ask' means denied, so the loop could not save work."
  exit 1
}

export STR_SEED="${STR_SEED:-$RANDOM}"
start=$(date +%s)

for i in $(seq 1 "$ITERATIONS"); do
  now=$(date +%s)
  if [ $((now - start)) -ge "$DEADLINE" ]; then
    echo "=== deadline reached after $((i - 1)) iterations ==="
    break
  fi

  echo "=== iteration $i/$ITERATIONS   seed=$STR_SEED   branch=$branch ==="

  python3.14 tests/loop_gate.py > .loop/gate.txt 2>&1
  rc=$?
  tail -6 .loop/gate.txt

  if [ $rc -eq 0 ]; then
    echo "=== LEDGER DRY at iteration $i -- suites green, nothing left ==="
    break
  fi

  # Fresh context every iteration. This is the point: one long session drifts
  # and then compacts, and compaction is where an overnight run loses the plot.
  claude -p "/str-hunt" --permission-mode acceptEdits || {
    echo "=== agent exited non-zero at iteration $i, stopping ==="
    break
  }

  STR_SEED=$((STR_SEED + 1))
done

echo
echo "=== done. audit: ==="
echo "  grep -c '^todo \|^blocked ' tests/LOOP_LEDGER.md    # 0 means finished"
echo "  git log --oneline --name-only $branch ^main"
