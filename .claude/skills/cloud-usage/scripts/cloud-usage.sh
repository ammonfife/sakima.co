#!/usr/bin/env bash
set -euo pipefail

# cloud-usage.sh V2 — Unified cloud billing/usage report
# Queries: GCP (9 projects), Cloudflare, Supabase, E2B, Turso, GitHub,
#          Claude Max, OpenAI, Lovable, Surge, GoDaddy, Google Workspace, Upstash
# Output: ~/cloud-usage-report.json + pretty stdout (sorted by cost desc, annual projection)

REPORT_FILE="$HOME/cloud-usage-report.json"
PROVIDER_FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider) PROVIDER_FILTER="$2"; shift 2;;
    -h|--help)
      echo "Usage: cloud-usage.sh [--provider <name>]"
      echo "Providers: gcp, cloudflare, supabase, e2b, turso, github, claude, openai, lovable, surge, godaddy, workspace, upstash"
      exit 0;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
TODAY=$(date -u +%Y-%m-%d)
THIRTY_DAYS_AGO=$(date -u -v-30d +%Y-%m-%d)

should_run() {
  [[ -z "$PROVIDER_FILTER" || "$PROVIDER_FILTER" == "$1" ]]
}

# Temp dir for intermediate files
TMPDIR_WORK=$(mktemp -d)
trap "rm -rf $TMPDIR_WORK" EXIT

###############################################################################
# GCP — 9 projects on billing account 01DF3E-B36319-1B1ACA
###############################################################################
collect_gcp() {
  local out="$TMPDIR_WORK/gcp.json"

  GCP_PROJECTS=("heimdall-8675309" "ammon-ai" "mailduringshutdown" "basecase-analytics" "runsignup-data" "heimdall-277921" "monitoring-dev" "prod2-svc" "pr-846b")

  # Budget
  gcloud billing budgets list --billing-account=01DF3E-B36319-1B1ACA --format=json \
    > "$TMPDIR_WORK/gcp_budget.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/gcp_budget.json"

  # Cloud Run for primary projects
  for proj in heimdall-8675309 ammon-ai; do
    gcloud run services list --project="$proj" --format="json(metadata.name,status.conditions)" \
      > "$TMPDIR_WORK/gcp_cr_${proj}.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/gcp_cr_${proj}.json"
  done

  # Compute instances for projects that have VMs
  for proj in heimdall-8675309 mailduringshutdown; do
    gcloud compute instances list --project="$proj" --format="json(name,zone,status)" \
      > "$TMPDIR_WORK/gcp_vm_${proj}.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/gcp_vm_${proj}.json"
  done

  # Cloud SQL
  gcloud sql instances list --project=heimdall-8675309 --format="json(name,state,settings.tier)" \
    > "$TMPDIR_WORK/gcp_sql.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/gcp_sql.json"

  # Scheduler
  gcloud scheduler jobs list --project=heimdall-8675309 --location=us-central1 --format="json(name,state)" \
    > "$TMPDIR_WORK/gcp_sched.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/gcp_sched.json"

  # List all projects to confirm linkage
  printf '%s\n' "${GCP_PROJECTS[@]}" > "$TMPDIR_WORK/gcp_projects.txt"

  TMPDIR_WORK="$TMPDIR_WORK" python3 << 'PYEOF' > "$out"
import json, os
D = os.environ["TMPDIR_WORK"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

budget = load(f"{D}/gcp_budget.json", [])
cr_heimdall = load(f"{D}/gcp_cr_heimdall-8675309.json", [])
cr_ammon = load(f"{D}/gcp_cr_ammon-ai.json", [])
comp_h = load(f"{D}/gcp_vm_heimdall-8675309.json", [])
comp_m = load(f"{D}/gcp_vm_mailduringshutdown.json", [])
sql = load(f"{D}/gcp_sql.json", [])
sched = load(f"{D}/gcp_sched.json", [])

with open(f"{D}/gcp_projects.txt") as f:
    projects = [l.strip() for l in f if l.strip()]

all_vms = comp_h + comp_m
running_vms = [v for v in all_vms if v.get("status") == "RUNNING"]
stopped_vms = [v for v in all_vms if v.get("status") != "RUNNING"]
running_sql = [s for s in sql if s.get("state") == "RUNNABLE"]
stopped_sql = [s for s in sql if s.get("state") != "RUNNABLE"]

budget_amount = None
for b in budget:
    amt = b.get("amount", {}).get("specifiedAmount", {})
    if amt.get("units"):
        budget_amount = float(amt["units"])

# Estimate monthly cost from active resources
est_monthly = 0.0
notes = []

if running_vms:
    est_monthly += len(running_vms) * 25.0
    notes.append(f"{len(running_vms)} running VMs (~${len(running_vms)*25}/mo)")
if running_sql:
    est_monthly += len(running_sql) * 10.0
    notes.append(f"{len(running_sql)} running Cloud SQL (~${len(running_sql)*10}/mo)")

# Cloud Run services with min-instances > 0 cost money
total_cr = len(cr_heimdall) + len(cr_ammon)
if total_cr:
    # Most are at 0 min-instances so idle cost is near $0
    # But API calls (Gemini via ammon-ai) generate real cost
    notes.append(f"{total_cr} Cloud Run services ({len(cr_heimdall)} heimdall, {len(cr_ammon)} ammon-ai)")

# ammon-ai Gemini spend was ~$270/mo but openclaw disabled 2026-04-08
# Conservative estimate: ~$2/mo residual if disabled
est_monthly += 2.0
notes.append("ammon-ai Gemini: ~$2/mo residual (openclaw disabled 2026-04-08)")

if not running_vms and not running_sql:
    notes.append("All VMs and SQL stopped/idle")

result = {
    "provider": "gcp",
    "projects": projects,
    "billing_account": "01DF3E-B36319-1B1ACA",
    "budget_monthly_usd": budget_amount,
    "estimated_monthly_usd": round(est_monthly, 2),
    "manual_verification_url": "https://console.cloud.google.com/billing/01DF3E-B36319-1B1ACA",
    "resources": {
        "cloud_run_services_heimdall": len(cr_heimdall),
        "cloud_run_services_ammon_ai": len(cr_ammon),
        "compute_vms_running": len(running_vms),
        "compute_vms_stopped": len(stopped_vms),
        "cloud_sql_running": len(running_sql),
        "cloud_sql_stopped": len(stopped_sql),
        "scheduler_jobs": len(sched),
    },
    "resource_details": {
        "cloud_run_heimdall": [c.get("metadata",{}).get("name","?") for c in cr_heimdall],
        "cloud_run_ammon_ai": [c.get("metadata",{}).get("name","?") for c in cr_ammon],
        "vms_running": [v.get("name","?") for v in running_vms],
        "vms_stopped": [v.get("name","?") for v in stopped_vms],
        "sql_stopped": [s.get("name","?") for s in stopped_sql],
    },
    "notes": notes,
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# Cloudflare
###############################################################################
collect_cloudflare() {
  local out="$TMPDIR_WORK/cloudflare.json"
  local CF_TOKEN CF_ACCT="187de0c1d881a4a2254008f31d8e93d4"
  CF_TOKEN=$(gcloud secrets versions access latest \
    --secret=cloudflare_api_token --project=heimdall-8675309 2>/dev/null || echo "")

  if [[ -z "$CF_TOKEN" ]]; then
    echo '{"provider":"cloudflare","error":"no_token","estimated_monthly_usd":5.0}' > "$out"
    echo "$out"; return
  fi

  curl -sf -H "Authorization: Bearer $CF_TOKEN" \
    "https://api.cloudflare.com/client/v4/accounts/$CF_ACCT/workers/scripts" \
    > "$TMPDIR_WORK/cf_workers.json" 2>/dev/null || echo '{"result":[]}' > "$TMPDIR_WORK/cf_workers.json"

  curl -sf -H "Authorization: Bearer $CF_TOKEN" \
    "https://api.cloudflare.com/client/v4/accounts/$CF_ACCT/d1/database" \
    > "$TMPDIR_WORK/cf_d1.json" 2>/dev/null || echo '{"result":[]}' > "$TMPDIR_WORK/cf_d1.json"

  curl -sf -H "Authorization: Bearer $CF_TOKEN" \
    "https://api.cloudflare.com/client/v4/accounts/$CF_ACCT/r2/buckets" \
    > "$TMPDIR_WORK/cf_r2.json" 2>/dev/null || echo '{"result":{"buckets":[]}}' > "$TMPDIR_WORK/cf_r2.json"

  # Workers analytics via GraphQL (30d window)
  curl -sf -X POST "https://api.cloudflare.com/client/v4/graphql" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"{ viewer { accounts(filter: {accountTag: \\\"$CF_ACCT\\\"}) { workersInvocationsAdaptive(limit: 1000, filter: {date_geq: \\\"$THIRTY_DAYS_AGO\\\", date_leq: \\\"$TODAY\\\"}) { sum { requests errors subrequests } dimensions { scriptName } } } } }\"}" \
    > "$TMPDIR_WORK/cf_analytics.json" 2>/dev/null \
    || echo '{"data":null}' > "$TMPDIR_WORK/cf_analytics.json"

  TMPDIR_WORK="$TMPDIR_WORK" CF_ACCT="$CF_ACCT" python3 << 'PYEOF' > "$out"
import json, os

D = os.environ["TMPDIR_WORK"]
CF_ACCT = os.environ["CF_ACCT"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

workers = load(f"{D}/cf_workers.json", {"result":[]}).get("result", [])
d1 = load(f"{D}/cf_d1.json", {"result":[]}).get("result", [])
r2_raw = load(f"{D}/cf_r2.json", {"result":{"buckets":[]}}).get("result", {})
r2_buckets = r2_raw.get("buckets", []) if isinstance(r2_raw, dict) else []

raw = load(f"{D}/cf_analytics.json", {"data": None})
data = (raw.get("data") or {}).get("viewer", {}).get("accounts", [{}])[0].get("workersInvocationsAdaptive", [])
by_script = {}
total_req = 0
total_err = 0
for entry in data:
    name = entry.get("dimensions", {}).get("scriptName", "unknown")
    s = entry.get("sum", {})
    reqs = s.get("requests", 0)
    errs = s.get("errors", 0)
    by_script[name] = by_script.get(name, 0) + reqs
    total_req += reqs
    total_err += errs

result = {
    "provider": "cloudflare",
    "account_id": CF_ACCT,
    "plan": "Workers Paid ($5/mo)",
    "estimated_monthly_usd": 5.00,
    "manual_verification_url": f"https://dash.cloudflare.com/{CF_ACCT}",
    "resources": {
        "workers": len(workers),
        "worker_names": [w.get("id", "?") for w in workers],
        "d1_databases": len(d1),
        "d1_names": [d.get("name", "?") for d in d1],
        "r2_buckets": len(r2_buckets),
        "r2_names": [b.get("name", "?") for b in r2_buckets],
    },
    "usage_30d": {
        "total_requests": total_req,
        "total_errors": total_err,
        "by_script": dict(sorted(by_script.items(), key=lambda x: -x[1])[:20]),
    },
    "included_monthly": {
        "requests": 10_000_000,
        "cpu_ms_per_request": 30_000,
        "d1_rows_read": 25_000_000_000,
    },
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# Supabase
###############################################################################
collect_supabase() {
  local out="$TMPDIR_WORK/supabase.json"
  local SUPA_TOKEN
  SUPA_TOKEN=$(security find-generic-password -s supabase-access-token -w 2>/dev/null || echo "")

  if [[ -z "$SUPA_TOKEN" ]]; then
    echo '{"provider":"supabase","error":"no_token","estimated_monthly_usd":25.0}' > "$out"
    echo "$out"; return
  fi

  curl -sf -H "Authorization: Bearer $SUPA_TOKEN" \
    "https://api.supabase.com/v1/projects" \
    > "$TMPDIR_WORK/supa_projects.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/supa_projects.json"

  TMPDIR_WORK="$TMPDIR_WORK" python3 << 'PYEOF' > "$out"
import json, os
D = os.environ["TMPDIR_WORK"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

projects = load(f"{D}/supa_projects.json", [])
active = [p for p in projects if p.get("status") == "ACTIVE_HEALTHY"]
inactive = [p for p in projects if p.get("status") != "ACTIVE_HEALTHY"]

# Pro tier for lkup.info
est_monthly = 25.0

result = {
    "provider": "supabase",
    "plan": "Pro (lkup.info $25/mo), Free (others)",
    "estimated_monthly_usd": est_monthly,
    "manual_verification_url": "https://supabase.com/dashboard/org/default/billing",
    "projects": {
        "active": [{"id": p["id"], "name": p.get("name","?")} for p in active],
        "inactive": [{"id": p["id"], "name": p.get("name","?")} for p in inactive],
    },
    "project_count_active": len(active),
    "project_count_inactive": len(inactive),
    "notes": [
        "Pro tier: vsotvatntzlrzrhemayh (lkup.info) at $25/mo",
        f"{len(active)} active, {len(inactive)} inactive projects",
    ],
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# E2B
###############################################################################
collect_e2b() {
  local out="$TMPDIR_WORK/e2b.json"
  local E2B_KEY
  E2B_KEY=$(security find-generic-password -s E2B_API_KEY -a benfife -w 2>/dev/null || echo "")

  if [[ -z "$E2B_KEY" ]]; then
    echo '{"provider":"e2b","error":"no_token","estimated_monthly_usd":0}' > "$out"
    echo "$out"; return
  fi

  curl -sf -H "X-API-Key: $E2B_KEY" \
    "https://api.e2b.dev/sandboxes" \
    > "$TMPDIR_WORK/e2b_sandboxes.json" 2>/dev/null || echo "[]" > "$TMPDIR_WORK/e2b_sandboxes.json"

  TMPDIR_WORK="$TMPDIR_WORK" python3 << 'PYEOF' > "$out"
import json, os
D = os.environ["TMPDIR_WORK"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

sandboxes = load(f"{D}/e2b_sandboxes.json", [])
by_template = {}
for s in sandboxes:
    t = s.get("templateID", "unknown")
    by_template[t] = by_template.get(t, 0) + 1

result = {
    "provider": "e2b",
    "plan": "Usage-based (free credit remaining)",
    "estimated_monthly_usd": 0.0,
    "manual_verification_url": "https://e2b.dev/dashboard",
    "running_sandboxes": len(sandboxes),
    "by_template": by_template,
    "sandbox_ids": [s.get("sandboxID", "?") for s in sandboxes[:20]],
    "notes": [
        "E2B does not expose a billing/usage history API",
        f"{len(sandboxes)} sandboxes running right now",
        "Free credit balance: check dashboard manually",
    ],
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# Turso
###############################################################################
collect_turso() {
  local out="$TMPDIR_WORK/turso.json"
  local TURSO_TOKEN TURSO_URL="libsql://bigmac-ammonfife.aws-us-west-2.turso.io"
  TURSO_TOKEN=$(security find-generic-password -s turso-bigmac-token -a bigmac -w 2>/dev/null || echo "")

  if [[ -z "$TURSO_TOKEN" ]]; then
    echo '{"provider":"turso","error":"no_token","estimated_monthly_usd":0}' > "$out"
    echo "$out"; return
  fi

  local TURSO_HTTP
  TURSO_HTTP=$(echo "$TURSO_URL" | sed 's|libsql://|https://|')

  curl -sf -X POST "$TURSO_HTTP/v2/pipeline" \
    -H "Authorization: Bearer $TURSO_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"requests":[{"type":"execute","stmt":{"sql":"SELECT (SELECT COUNT(*) FROM facts) as facts, (SELECT COUNT(*) FROM policies) as policies, (SELECT COUNT(*) FROM sessions) as sessions, (SELECT COUNT(*) FROM skills) as skills, (SELECT COUNT(*) FROM todos) as todos, (SELECT COUNT(*) FROM memory) as memory, (SELECT COUNT(*) FROM secrets) as secrets"}},{"type":"close"}]}' \
    > "$TMPDIR_WORK/turso_counts.json" 2>/dev/null || echo '{}' > "$TMPDIR_WORK/turso_counts.json"

  TMPDIR_WORK="$TMPDIR_WORK" python3 << 'PYEOF' > "$out"
import json, os
D = os.environ["TMPDIR_WORK"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

raw = load(f"{D}/turso_counts.json", {})
tables = {}
try:
    results = raw.get("results", [{}])
    if results:
        r = results[0]
        cols = [c.get("name","") for c in r.get("response",{}).get("result",{}).get("cols",[])]
        rows = r.get("response",{}).get("result",{}).get("rows",[[]])
        if rows and cols:
            for i, c in enumerate(cols):
                val = rows[0][i]
                tables[c] = int(val.get("value", 0)) if isinstance(val, dict) else val
except Exception:
    tables = {"error": "parse_failed"}

total_rows = sum(v for v in tables.values() if isinstance(v, int))

result = {
    "provider": "turso",
    "plan": "Free tier",
    "estimated_monthly_usd": 0.0,
    "manual_verification_url": "https://turso.tech/app",
    "database": "bigmac-ammonfife",
    "region": "aws-us-west-2",
    "table_row_counts": tables,
    "total_rows": total_rows,
    "notes": [
        "Free tier: 9GB storage, 500M rows read/mo, 25M rows written/mo",
        f"{total_rows} total rows across {len(tables)} tables",
    ],
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# GitHub Actions
###############################################################################
collect_github() {
  local out="$TMPDIR_WORK/github.json"

  gh api /user/settings/billing/actions \
    > "$TMPDIR_WORK/gh_billing.json" 2>/dev/null || echo '{}' > "$TMPDIR_WORK/gh_billing.json"

  gh api /repos/ammonfife/BIGMAC/actions/cache/usage \
    > "$TMPDIR_WORK/gh_bigmac_cache.json" 2>/dev/null || echo '{}' > "$TMPDIR_WORK/gh_bigmac_cache.json"

  gh api "/repos/ammonfife/BIGMAC/actions/runs?per_page=30&created=>$THIRTY_DAYS_AGO" \
    > "$TMPDIR_WORK/gh_runs.json" 2>/dev/null || echo '{"total_count":0}' > "$TMPDIR_WORK/gh_runs.json"

  TMPDIR_WORK="$TMPDIR_WORK" python3 << 'PYEOF' > "$out"
import json, os
D = os.environ["TMPDIR_WORK"]

def load(f, default):
    try:
        with open(f) as fh:
            return json.load(fh)
    except Exception:
        return default

billing = load(f"{D}/gh_billing.json", {})
bc = load(f"{D}/gh_bigmac_cache.json", {})
runs = load(f"{D}/gh_runs.json", {"total_count": 0})

result = {
    "provider": "github",
    "plan": "Free tier (2000 min/mo)",
    "estimated_monthly_usd": 0.0,
    "manual_verification_url": "https://github.com/settings/billing",
    "billing": {
        "total_minutes_used": billing.get("total_minutes_used", 0),
        "total_paid_minutes_used": billing.get("total_paid_minutes_used", 0),
        "included_minutes": billing.get("included_minutes", 2000),
    },
    "cache_usage_bigmac": {
        "size_bytes": bc.get("active_caches_size_in_bytes", 0),
        "count": bc.get("active_caches_count", 0),
    },
    "workflow_runs_30d": runs.get("total_count", 0),
    "notes": [
        "Free tier: 2000 min/mo for private repos",
        f"{billing.get('total_minutes_used', 0)} minutes used this billing cycle",
    ],
}
print(json.dumps(result))
PYEOF
  echo "$out"
}

###############################################################################
# Fixed subscription line items
###############################################################################
collect_claude() {
  cat > "$TMPDIR_WORK/claude.json" << 'JSON'
{
  "provider": "claude",
  "plan": "Claude Max subscription",
  "estimated_monthly_usd": 200.00,
  "manual_verification_url": "https://console.anthropic.com/settings/billing",
  "notes": ["Claude Max plan ~$200/mo"]
}
JSON
  echo "$TMPDIR_WORK/claude.json"
}

collect_openai() {
  cat > "$TMPDIR_WORK/openai.json" << 'JSON'
{
  "provider": "openai",
  "plan": "ChatGPT Plus + API",
  "estimated_monthly_usd": 20.00,
  "manual_verification_url": "https://platform.openai.com/settings/organization/billing/overview",
  "notes": ["ChatGPT Plus ~$20/mo"]
}
JSON
  echo "$TMPDIR_WORK/openai.json"
}

collect_lovable() {
  cat > "$TMPDIR_WORK/lovable.json" << 'JSON'
{
  "provider": "lovable",
  "plan": "Lovable.dev subscription",
  "estimated_monthly_usd": 20.00,
  "manual_verification_url": "https://lovable.dev/settings/billing",
  "notes": ["Lovable.dev ~$20/mo"]
}
JSON
  echo "$TMPDIR_WORK/lovable.json"
}

collect_surge() {
  cat > "$TMPDIR_WORK/surge.json" << 'JSON'
{
  "provider": "surge",
  "plan": "Surge SMS service",
  "estimated_monthly_usd": 10.00,
  "manual_verification_url": "https://app.surgeapp.co/billing",
  "notes": ["Surge SMS ~$10/mo"]
}
JSON
  echo "$TMPDIR_WORK/surge.json"
}

collect_godaddy() {
  cat > "$TMPDIR_WORK/godaddy.json" << 'JSON'
{
  "provider": "godaddy",
  "plan": "16 domains ($377/yr amortized)",
  "estimated_monthly_usd": 31.42,
  "manual_verification_url": "https://account.godaddy.com/billing",
  "domain_count": 16,
  "annual_cost_usd": 377.00,
  "notes": ["16 domains, $377/yr = ~$31.42/mo amortized"]
}
JSON
  echo "$TMPDIR_WORK/godaddy.json"
}

collect_workspace() {
  cat > "$TMPDIR_WORK/workspace.json" << 'JSON'
{
  "provider": "workspace",
  "plan": "Google Workspace (2 users)",
  "estimated_monthly_usd": 14.00,
  "manual_verification_url": "https://admin.google.com/ac/billing",
  "users": 2,
  "notes": ["Google Workspace ~$7/user/mo x 2 users"]
}
JSON
  echo "$TMPDIR_WORK/workspace.json"
}

collect_upstash() {
  cat > "$TMPDIR_WORK/upstash.json" << 'JSON'
{
  "provider": "upstash",
  "plan": "Free tier (phone-home Redis only)",
  "estimated_monthly_usd": 0.00,
  "manual_verification_url": "https://console.upstash.com/billing",
  "notes": ["Free tier Redis, used only for BIGMAC sandbox phone-home channel"]
}
JSON
  echo "$TMPDIR_WORK/upstash.json"
}

###############################################################################
# Main: collect all and merge
###############################################################################
echo "=== Cloud Usage Report V2 ==="
echo "Generated: $NOW"
echo ""

PROVIDER_FILES=()

if should_run gcp;        then PROVIDER_FILES+=("$(collect_gcp)"); fi
if should_run cloudflare; then PROVIDER_FILES+=("$(collect_cloudflare)"); fi
if should_run supabase;   then PROVIDER_FILES+=("$(collect_supabase)"); fi
if should_run e2b;        then PROVIDER_FILES+=("$(collect_e2b)"); fi
if should_run turso;      then PROVIDER_FILES+=("$(collect_turso)"); fi
if should_run github;     then PROVIDER_FILES+=("$(collect_github)"); fi
if should_run claude;     then PROVIDER_FILES+=("$(collect_claude)"); fi
if should_run openai;     then PROVIDER_FILES+=("$(collect_openai)"); fi
if should_run lovable;    then PROVIDER_FILES+=("$(collect_lovable)"); fi
if should_run surge;      then PROVIDER_FILES+=("$(collect_surge)"); fi
if should_run godaddy;    then PROVIDER_FILES+=("$(collect_godaddy)"); fi
if should_run workspace;  then PROVIDER_FILES+=("$(collect_workspace)"); fi
if should_run upstash;    then PROVIDER_FILES+=("$(collect_upstash)"); fi

# Merge into final report
NOW="$NOW" REPORT_FILE="$REPORT_FILE" python3 - "${PROVIDER_FILES[@]}" << 'PYEOF'
import json, sys, os

REPORT_FILE = os.environ["REPORT_FILE"]
NOW = os.environ.get("NOW", "unknown")
files = sys.argv[1:]
providers = []

for f in files:
    try:
        with open(f) as fh:
            data = json.load(fh)
            providers.append(data)
    except Exception as e:
        providers.append({"error": str(e), "file": f})

# Sort by cost descending
providers.sort(key=lambda p: -(p.get("estimated_monthly_usd", 0) if isinstance(p.get("estimated_monthly_usd"), (int, float)) else 0))

total = sum(
    p.get("estimated_monthly_usd", 0)
    for p in providers
    if isinstance(p.get("estimated_monthly_usd"), (int, float))
)

report = {
    "generated": NOW,
    "summary": {
        "total_monthly_usd": round(total, 2),
        "total_annual_usd": round(total * 12, 2),
        "provider_count": len(providers),
    },
    "providers": {p.get("provider","unknown"): p for p in providers},
    "providers_sorted": [
        {
            "provider": p.get("provider","?"),
            "monthly_usd": p.get("estimated_monthly_usd", 0) if isinstance(p.get("estimated_monthly_usd"), (int, float)) else 0,
            "plan": p.get("plan", "?"),
        }
        for p in providers
    ],
}

with open(REPORT_FILE, "w") as f:
    json.dump(report, f, indent=2)

# Pretty print — sorted by cost descending
print(f"{'PROVIDER':<17} | {'MONTHLY':>10} | {'ANNUAL':>10} | PLAN")
print("-"*17 + "-+-" + "-"*10 + "-+-" + "-"*10 + "-+-" + "-"*30)

for p in providers:
    name = p.get("provider","?").upper()
    est = p.get("estimated_monthly_usd", 0)
    if isinstance(est, (int, float)):
        est_str = f"${est:,.2f}"
        ann_str = f"${est*12:,.2f}"
    else:
        est_str = str(est)[:10]
        ann_str = "N/A"
    err = p.get("error")
    plan = p.get("plan", "?")[:30]
    if err:
        plan = f"ERROR: {err}"[:30]
    print(f"{name:<17} | {est_str:>10} | {ann_str:>10} | {plan}")

print("-"*17 + "-+-" + "-"*10 + "-+-" + "-"*10 + "-+-" + "-"*30)
print(f"{'TOTAL':<17} | ${total:>9,.2f} | ${total*12:>9,.2f} |")
print()

# Cloudflare request summary
cf = report["providers"].get("cloudflare", {})
usage = cf.get("usage_30d", {})
if usage and usage.get("total_requests"):
    total_req = usage["total_requests"]
    total_err = usage["total_errors"]
    print(f"CLOUDFLARE WORKERS (30d): {total_req:,} requests, {total_err:,} errors")
    top = list(usage.get("by_script", {}).items())[:5]
    for script, count in top:
        print(f"  {script}: {count:,}")
    print()

# E2B sandbox summary
e2b = report["providers"].get("e2b", {})
if e2b.get("running_sandboxes") is not None:
    print(f'E2B SANDBOXES RUNNING: {e2b["running_sandboxes"]}')
    for tpl, cnt in e2b.get("by_template", {}).items():
        print(f"  template {tpl}: {cnt}")
    print()

# Turso table stats
turso = report["providers"].get("turso", {})
tc = turso.get("table_row_counts", {})
if tc and not tc.get("error"):
    total_rows = turso.get("total_rows", 0)
    print(f"TURSO ROWS: {total_rows:,} total across {len(tc)} tables")
    for t, c in sorted(tc.items(), key=lambda x: -(x[1] if isinstance(x[1], int) else 0)):
        val = c if isinstance(c, int) else c
        print(f"  {t}: {val:,}" if isinstance(val, int) else f"  {t}: {val}")
    print()

# GCP resource summary
gcp = report["providers"].get("gcp", {})
res = gcp.get("resources", {})
if res:
    print("GCP RESOURCES:")
    for k, v in res.items():
        print(f"  {k}: {v}")
    print()

print(f"Full report: {REPORT_FILE}")
PYEOF
