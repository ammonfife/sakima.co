---
name: session-upload
description: Upload session archives, git bundles, BigMac Scope recordings, or any large file to the dedicated Cloudflare R2 bucket (bigmac-sessions). Returns a durable URL. Registers the upload in Turso facts for cross-session discoverability. Trigger on "upload to R2", "upload session", "upload large file", "save to R2", "put in R2", "upload bundle", "send to cloud storage", "upload scope recording".
type: workflow
---

> [!IMPORTANT]
> **Cross-Platform Skill**: Shared across Claude Code, OpenClaw, Gemini, Codex.
> - Claude Code / OpenClaw: use `Bash` tool + helper script `~/clawd/scripts/session-upload.sh`
> - Gemini: use `run_command` equivalents
> - Codex/Grok: use terminal pipeline

---

# session-upload — Cloudflare R2 Uploader

Uploads files to the dedicated **`bigmac-sessions`** R2 bucket (intentionally separate from the lkup-config and other lkup R2 buckets). Returns a durable URL and registers the upload as a Turso fact.

**R2 Account ID:** `187de0c1d881a4a2254008f31d8e93d4`
**R2 Endpoint:** `https://187de0c1d881a4a2254008f31d8e93d4.r2.cloudflarestorage.com`
**Target bucket:** `bigmac-sessions` (NOT the lkup-config bucket — never mix these)

---

## Step 0 — Read credentials from vault

```bash
R2_ACCESS_KEY_ID=$(bigmac-secrets get cloudflare_r2_access_key_id)
R2_SECRET_ACCESS_KEY=$(bigmac-secrets get cloudflare_r2_secret_access_key 2>/dev/null || \
                       bigmac-secrets get cloudflare_r2_access_key_secret 2>/dev/null)
R2_ACCOUNT_ID="187de0c1d881a4a2254008f31d8e93d4"
CF_API_TOKEN=$(bigmac-secrets get cloudflare_api_token)
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
```

---

## Step 1 — Ensure `bigmac-sessions` bucket exists (idempotent)

Run once (safe to re-run — creation is idempotent):

```bash
# Via wrangler (preferred, already authenticated)
wrangler r2 bucket create bigmac-sessions --account-id 187de0c1d881a4a2254008f31d8e93d4 2>/dev/null || true

# OR via CF API if wrangler auth is missing
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/187de0c1d881a4a2254008f31d8e93d4/r2/buckets" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"bigmac-sessions"}' | jq -r '.success, .errors'
```

---

## Step 2 — Detect input type

| Input | Action |
|---|---|
| Local file path (`/path/to/file.zip`) | Upload directly |
| Directory (`~/clawd/data/session-archives/ID-date/`) | Zip then upload |
| Glob pattern (`~/clawd/data/session-ID-events-page*.json`) | Zip all matches then upload |
| Session ID (bare string like `abc12345`) | Find `~/clawd/data/session-archives/{ID}*/` and upload |

```bash
LOCAL="$1"
KEY="${2:-}"  # optional override

# Resolve session ID to archive directory
if [[ ! -e "$LOCAL" && ${#LOCAL} -le 40 ]]; then
    FOUND=$(ls -d ~/clawd/data/session-archives/${LOCAL}*/ 2>/dev/null | head -1)
    if [[ -n "$FOUND" ]]; then
        LOCAL="$FOUND"
    fi
fi

# Zip directories
if [[ -d "$LOCAL" ]]; then
    BASENAME=$(basename "$LOCAL")
    ZIPFILE="${TMPDIR:-/tmp}/${BASENAME}-$(date +%s).zip"
    zip -r "$ZIPFILE" "$LOCAL" -x "*.DS_Store" -x "*/__pycache__/*"
    LOCAL="$ZIPFILE"
fi

# Resolve key from path if not provided
if [[ -z "$KEY" ]]; then
    FILENAME=$(basename "$LOCAL")
    KEY="misc/$(date +%Y-%m-%d)/$FILENAME"
fi
```

**Key path conventions:**
```
bigmac-sessions/
  sessions/{session-id}/{filename}             # session archives, JSONLs, transcripts
  bundles/{repo}/{branch}-{timestamp}.bundle   # git bundles
  scope/{hostname}-{timestamp}.json            # BigMac Scope recordings
  misc/{YYYY-MM-DD}/{filename}                 # anything else
```

---

## Step 3 — Upload (try in order, stop on first success)

### Method 1: rclone (preferred — progress bar, multipart, large file safe)

```bash
rclone copyto "$LOCAL" \
  ":s3,access_key_id=${R2_ACCESS_KEY_ID},secret_access_key=${R2_SECRET_ACCESS_KEY},endpoint=${R2_ENDPOINT}:bigmac-sessions/${KEY}" \
  --progress --s3-no-check-bucket
```

### Method 2: wrangler r2 object put (simpler, good for files <1 GB)

```bash
wrangler r2 object put "bigmac-sessions/${KEY}" \
  --file "$LOCAL" \
  --account-id 187de0c1d881a4a2254008f31d8e93d4
```

### Method 3: curl single-part PUT via S3 presigned URL (last resort, files <5 GB)

```bash
# Requires AWS Signature V4 — generate with openssl or use the Python helper below
python3 - <<'PYEOF'
import boto3, os
s3 = boto3.client('s3',
    aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
    endpoint_url=os.environ['R2_ENDPOINT'])
url = s3.generate_presigned_url('put_object',
    Params={'Bucket':'bigmac-sessions','Key': os.environ['KEY']}, ExpiresIn=3600)
print(url)
PYEOF
# Then: curl -X PUT --upload-file "$LOCAL" "$PRESIGNED_URL"
```

---

## Step 4 — Report URL and size

```bash
FILE_SIZE=$(du -sh "$LOCAL" | cut -f1)
DURABLE_URL="${R2_ENDPOINT}/bigmac-sessions/${KEY}"
echo ""
echo "Uploaded: r2://bigmac-sessions/${KEY}"
echo "URL:      ${DURABLE_URL}"
echo "Size:     ${FILE_SIZE}"
```

**Note on public access:** By default R2 objects are private. If the bucket has a public domain configured, the URL is `https://bigmac-sessions.{account-id}.r2.cloudflarestorage.com/{key}`. When a custom domain is set up (e.g., `https://sessions.bigmac.dev/{key}`), it will be noted in Turso facts. Pass `--public` flag to `session-upload.sh` to document the intent.

---

## Step 5 — Register in Turso facts

```bash
TOKEN=$(security find-generic-password -a bigmac -s turso-bigmac-token -w 2>/dev/null)
TURSO_URL="https://bigmac-ammonfife.aws-us-west-2.turso.io/v2/pipeline"
FACT_BODY="R2 upload: bigmac-sessions/${KEY} (${FILE_SIZE}) — source: ${ORIGINAL_LOCAL}"

curl -s "$TURSO_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"requests\":[{\"type\":\"execute\",\"stmt\":{
    \"sql\":\"INSERT INTO facts(body,tags,created_by,created_at) VALUES(?,?,?,strftime('%s','now'))\",
    \"args\":[
      {\"type\":\"text\",\"value\":\"$(echo "$FACT_BODY" | sed "s/'/\\''/g")\"},
      {\"type\":\"text\",\"value\":\"session-upload,r2,bigmac-sessions\"},
      {\"type\":\"text\",\"value\":\"claude\"}
    ]
  }}]}" | jq -r '.results[0].response.result.rows | length | "Turso fact rows inserted: \(.)"' 2>/dev/null || echo "Turso fact written (jq not available for verification)"
```

---

## Helper script

The quickest path for agents: `~/clawd/scripts/session-upload.sh`

```bash
# Usage examples:
bash ~/clawd/scripts/session-upload.sh /path/to/file.zip
bash ~/clawd/scripts/session-upload.sh ~/clawd/data/session-archives/abc12345-2026-05-09/
bash ~/clawd/scripts/session-upload.sh ~/clawd/data/scope-recording.json scope/mymac-$(date +%s).json
bash ~/clawd/scripts/session-upload.sh abc12345   # resolve session ID automatically
```

---

## Flags

| Flag | Effect |
|---|---|
| `[path]` | Local file, directory, glob, or session ID |
| `[remote-key]` | Optional custom R2 object key (default: auto-derived) |
| `--public` | Document URL as intended for public access in Turso fact |
| `--zip` | Force zip even for single files (auto-enabled for directories) |
| `--session-id ID` | Explicit session ID to find archive for |
| `--bucket NAME` | Override bucket (default: `bigmac-sessions`) |

---

## Bucket separation note

`bigmac-sessions` is intentionally separate from the lkup-config R2 bucket (`lkup-config.lkup.info`).
- lkup-config: coin scanner configs, eBay cookies, images for lkup.info frontend
- bigmac-sessions: session archives, git bundles, BigMac Scope recordings, cross-machine transfer blobs

Never upload BigMac/BIGMAC agent artifacts to lkup buckets.

---

## Related skills

- `/session-archive` — bundle session artifacts into `~/clawd/data/session-archives/` first, then use this skill to push to R2
- `/bigmac-scope` — record network/event captures; use `/session-upload` to persist the exported JSON to R2
- `/capture-cloud-session` — captures cloud session transcript to `~/clawd/data/`; use this skill to archive off-machine
