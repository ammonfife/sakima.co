#!/bin/bash
# rotate-queries.sh — pick N fresh search queries from lib/query-seed.json,
# excluding any used in the last 2 runs. Writes selection to --out and appends
# to rolling history at ~/clawd/data/test-extensions-query-rotation.json.

set -euo pipefail

COUNT=5
OUT=""
for arg in "$@"; do
    case $arg in
        --count=*) COUNT="${arg#*=}" ;;
        --out=*)   OUT="${arg#*=}" ;;
    esac
done

[ -z "$OUT" ] && { echo "FAIL: --out=<path> required" >&2; exit 1; }

LIB=$(dirname "$0")
SEED="$LIB/query-seed.json"
[ -f "$SEED" ] || { echo "FAIL: seed $SEED missing" >&2; exit 1; }

HIST=~/clawd/data/test-extensions-query-rotation.json
[ -f "$HIST" ] || echo '{"runs":[]}' > "$HIST"

# Pick fresh queries (exclude last 2 runs) and write output + append history
python3 - <<PY
import json, random, os
seed = json.load(open("$SEED"))['queries']
hist = json.load(open("$HIST"))
recent = set()
for r in hist.get('runs', [])[-2:]:
    for q in r.get('queries', []):
        recent.add(q)

avail = [q for q in seed if q not in recent]
if len(avail) < $COUNT:
    avail = seed  # wrap around if exhausted

random.shuffle(avail)
picked = avail[:$COUNT]

run_id = os.environ.get('RUN_ID') or ''
out = {'run_id': run_id, 'queries': picked}
json.dump(out, open("$OUT", 'w'), indent=2)

hist['runs'].append(out)
hist['runs'] = hist['runs'][-20:]
json.dump(hist, open("$HIST", 'w'), indent=2)
print(f"# rotated {len(picked)} queries -> $OUT", file=__import__('sys').stderr)
PY
