#!/bin/bash
# rotate-certs.sh — pick N fresh known-good certs per grader, excluding any used
# in the last 2 runs. Writes selection to --out and appends to rolling history
# at ~/clawd/data/test-extensions-cert-rotation.json (last 20 runs kept).

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

HIST=~/clawd/data/test-extensions-cert-rotation.json
[ -f "$HIST" ] || echo '{"runs":[]}' > "$HIST"

SUPA_PW=$(security find-generic-password -s supabase_lkup_db_password -w 2>/dev/null)
[ -n "$SUPA_PW" ] || { echo "FAIL: supabase_lkup_db_password not in keychain" >&2; exit 1; }

PSQL_BIN=/opt/homebrew/opt/libpq/bin/psql
[ -x "$PSQL_BIN" ] || PSQL_BIN=$(which psql)
[ -x "$PSQL_BIN" ] || { echo "FAIL: psql not found" >&2; exit 1; }

# Collect recently-used certs (last 2 runs worth)
EXCLUDE=$(python3 -c "
import json
h=json.load(open('$HIST'))
recent=[]
for r in h.get('runs', [])[-2:]:
    for g,certs in r.get('by_grader', {}).items():
        recent += [c['id'] for c in certs]
print(','.join(\"'\"+c+\"'\" for c in set(recent)) or \"''\")
")

# Query Supabase for fresh known-good certs per grader
export PGPASSWORD="$SUPA_PW"
PGURL="postgresql://postgres.vsotvatntzlrzrhemayh@aws-0-us-west-2.pooler.supabase.com:5432/postgres?sslmode=require"

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

GRADERS=(NGC PCGS CAC ANACS ICG)
BY_GRADER_JSON="{"
FIRST=1

for G in "${GRADERS[@]}"; do
    # cert_number from id (strip "<SVC>-" prefix)
    QUERY="SELECT id, coin_id, grade, regexp_replace(id, '^[^-]+-', '') AS cert_number
           FROM public.certs
           WHERE is_valid = true
             AND service = '$G'
             AND coin_id IS NOT NULL
             AND grade IS NOT NULL
             AND id NOT IN ($EXCLUDE)
           ORDER BY random()
           LIMIT $COUNT;"

    ROWS=$("$PSQL_BIN" "$PGURL" -t -A -F '|' -c "$QUERY" 2>/dev/null || echo "")
    CERTS_JSON="["
    CERT_FIRST=1
    while IFS='|' read -r ID COIN GRADE CERTNO; do
        [ -z "$ID" ] && continue
        [ $CERT_FIRST -eq 0 ] && CERTS_JSON="$CERTS_JSON,"
        CERT_FIRST=0
        # JSON-escape value parts (keep ASCII-safe)
        CERTS_JSON="$CERTS_JSON{\"id\":\"$ID\",\"coin_id\":\"$COIN\",\"grade\":\"$GRADE\",\"cert_number\":\"$CERTNO\"}"
    done <<< "$ROWS"
    CERTS_JSON="$CERTS_JSON]"

    [ $FIRST -eq 0 ] && BY_GRADER_JSON="$BY_GRADER_JSON,"
    FIRST=0
    BY_GRADER_JSON="$BY_GRADER_JSON\"$G\":$CERTS_JSON"
done
BY_GRADER_JSON="$BY_GRADER_JSON}"

RUN_ID=$(date -u +%Y-%m-%dT%H-%M-%SZ)
printf '{"run_id":"%s","by_grader":%s}\n' "$RUN_ID" "$BY_GRADER_JSON" > "$OUT"

# Append to history and trim to last 20
python3 -c "
import json
h=json.load(open('$HIST'))
new=json.load(open('$OUT'))
h['runs'].append(new)
h['runs']=h['runs'][-20:]
json.dump(h,open('$HIST','w'),indent=2)
"

echo "# rotated certs: $COUNT per grader, output $OUT" >&2
