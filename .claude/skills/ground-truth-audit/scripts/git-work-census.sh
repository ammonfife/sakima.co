#!/usr/bin/env bash
# git-work-census.sh — what actually changed in a repo over a window.
#
# WHY: reviewing "what happened while I was away" by reading commit subjects is
# unreliable, because automated commits (auto-sync, stop-hooks, checkpoints, WIP)
# routinely carry the substantive work while curated commits carry the small stuff.
# Message quality correlates with how automated the producer was, NOT with how
# important the change was. This ranks by lines changed per file instead, and
# reports automated and curated commits separately so you can see both.
#
# Usage:
#   git-work-census.sh [since] [repo_path] [top_n]
#
#   since      git date expression (default: "1 week ago")
#   repo_path  default: current directory
#   top_n      how many files to list (default: 30)
#
# Examples:
#   git-work-census.sh                       # last week, cwd
#   git-work-census.sh "2026-08-09 12:00"    # since an exact moment
#   git-work-census.sh "3 days ago" ~/src/app 50
#
# Tune AUTO_RE for your repo's automation conventions.

set -uo pipefail

SINCE="${1:-1 week ago}"
REPO="${2:-.}"
TOP="${3:-30}"

# Commit-subject patterns that indicate an automated producer.
AUTO_RE='auto:|auto-commit|stop-hook|pre-compact|checkpoint|^wip|\[skip ci\]|chore: refresh|snapshot'

cd "$REPO" || { echo "cannot cd to $REPO" >&2; exit 1; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "not a git repo: $REPO" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git log --since="$SINCE" --format='%H%x09%s' > "$TMP/all.tsv"

TOTAL=$(wc -l < "$TMP/all.tsv" | tr -d ' ')
if [ "$TOTAL" -eq 0 ]; then
  echo "No commits since '$SINCE' in $REPO"
  exit 0
fi

grep -iE "$AUTO_RE" "$TMP/all.tsv" | cut -f1 > "$TMP/auto.sha"  || true
grep -ivE "$AUTO_RE" "$TMP/all.tsv" | cut -f1 > "$TMP/curated.sha" || true

AUTO_N=$(wc -l < "$TMP/auto.sha" | tr -d ' ')
CUR_N=$(wc -l < "$TMP/curated.sha" | tr -d ' ')

echo "═══ WORK CENSUS — $REPO — since '$SINCE' ═══"
echo "commits: $TOTAL total · $AUTO_N automated · $CUR_N curated"
echo
echo "If the automated share is large, a subject-line review would have missed most"
echo "of the work. The ranked files below are the ground truth for what changed."
echo

# Aggregate +/- per file across a set of commits.
census() {
  local shafile="$1" label="$2"
  [ -s "$shafile" ] || { echo "  (none)"; return; }
  while read -r sha; do
    git show --numstat --format='' "$sha" 2>/dev/null
  done < "$shafile" \
  | awk -F'\t' 'NF==3 && $1 != "-" { add[$3]+=$1; del[$3]+=$2 }
       END { for (f in add) printf "%d\t%d\t%d\t%s\n", add[f]+del[f], add[f], del[f], f }' \
  | sort -rn \
  | head -"$TOP" \
  | awk -F'\t' 'BEGIN{printf "  %10s  %9s  %9s  %s\n","CHURN","+","-","FILE"}
       {printf "  %10d  %9d  %9d  %s\n", $1,$2,$3,$4}'
}

echo "─── TOP FILES BY CHURN — AUTOMATED COMMITS ($AUTO_N) ───"
echo "  (agents, hooks and checkpoints deposit output here)"
census "$TMP/auto.sha" auto
echo
echo "─── TOP FILES BY CHURN — CURATED COMMITS ($CUR_N) ───"
census "$TMP/curated.sha" curated
echo
echo "─── CURATED SUBJECTS (context for the above) ───"
cut -f2 "$TMP/curated.sha" >/dev/null 2>&1 || true
grep -ivE "$AUTO_RE" "$TMP/all.tsv" | cut -f2 | head -40 | sed 's/^/  /'
echo
echo "Next: for any file at the top of the AUTOMATED list, read it. Large new"
echo "artifacts there are usually finished work that nothing references yet —"
echo "check before building anything similar (see SKILL.md, 'check whether it exists')."
