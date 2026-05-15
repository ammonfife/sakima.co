#!/bin/bash
# bump-versions.sh — bumps each extension's manifest.json patch version by +0.0.1
# and appends a CHANGELOG.md entry. Emits JSON of old→new mappings.
# Per Ben 2026-04-20 hard rule: Chrome caches extension JS — version bumps force
# fresh load. Must commit after for cache-bust invariant to hold.

set -euo pipefail

LKUP=${LKUP:-$HOME/github/ammonfife/lkup.info}
AUCTION=${AUCTION:-$HOME/github/ammonfife/auction_tools}

ONLY=""
RUN_ID=""
for arg in "$@"; do
    case $arg in
        --only=*) ONLY="${arg#*=}" ;;
        --run-id=*) RUN_ID="${arg#*=}" ;;
    esac
done

TARGETS=(
    # lkup.info repo (canonical — prefer these over auction_tools)
    "unified|$LKUP/extension/manifest.json"
    "lkup_helper|$LKUP/extension/lkup_helper/manifest.json"
    "coin-cert-scraper|$LKUP/extension/coin-cert-scraper/manifest.json"
    "live-labels|$LKUP/extension/live-labels/manifest.json"
    # bigmac (separate repo)
    "bigmac-scope|$HOME/github/ammonfife/bigmac-scope/manifest.json"
    # auction_tools fallbacks — until lifted into lkup.info
    "whatnot-price-overlay|$AUCTION/browser_extensions/whatnot-price-overlay-extension/manifest.json"
    "whatnot-inventory-tracker|$AUCTION/browser_extensions/whatnot-inventory-tracker/manifest.json"
)

BUMPS_JSON="["
FIRST=1

for t in "${TARGETS[@]}"; do
    NAME="${t%%|*}"
    PATH_JSON="${t#*|}"

    # --only filter
    if [ -n "$ONLY" ] && ! echo ",$ONLY," | grep -q ",$NAME,"; then
        continue
    fi
    if [ ! -f "$PATH_JSON" ]; then
        echo "# skip missing: $PATH_JSON" >&2
        continue
    fi

    # Read old version
    OLD=$(python3 -c "import json; print(json.load(open('$PATH_JSON'))['version'])")
    # Bump patch: X.Y.Z -> X.Y.(Z+1); X.Y -> X.Y.1
    NEW=$(python3 -c "
v='$OLD'.split('.')
while len(v)<3: v.append('0')
v[2]=str(int(v[2])+1)
print('.'.join(v[:3]))
")

    # Atomic write (temp + rename)
    python3 -c "
import json
p='$PATH_JSON'
d=json.load(open(p))
d['version']='$NEW'
t=p+'.tmp'
with open(t,'w') as f: json.dump(d,f,indent=2)
import os; os.rename(t,p)
"

    # Append CHANGELOG entry
    DIR=$(dirname "$PATH_JSON")
    CHANGELOG="$DIR/CHANGELOG.md"
    [ -f "$CHANGELOG" ] || printf "# CHANGELOG\n\n" > "$CHANGELOG"
    printf "\n## v%s — %s (test-extensions run %s)\n- Version bump for Chrome cache-bust; no code changes\n" \
        "$NEW" "$(date -u +%Y-%m-%d)" "$RUN_ID" >> "$CHANGELOG"

    # Append to JSON output
    [ $FIRST -eq 0 ] && BUMPS_JSON="$BUMPS_JSON,"
    FIRST=0
    BUMPS_JSON="$BUMPS_JSON{\"name\":\"$NAME\",\"path\":\"$PATH_JSON\",\"old\":\"$OLD\",\"new\":\"$NEW\"}"

    echo "# bumped $NAME: $OLD → $NEW" >&2
done

BUMPS_JSON="$BUMPS_JSON]"
printf '{"run_id":"%s","bumps":%s}\n' "$RUN_ID" "$BUMPS_JSON"
