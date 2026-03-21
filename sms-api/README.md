# Sakima SMS Bot

Inbound SMS keyword routing via **Surge.app** → FastAPI webhook → replies via Surge API.

## Commands

| Text this      | Gets this                                      |
|----------------|------------------------------------------------|
| `CERT 12345`   | Coin name, grade, price guide (PCGS/NGC lookup)|
| `PRICE 12345`  | Price guide / our ask price for a cert         |
| `BID 12345`    | Our current buy/bid price                      |
| `HOURS`        | Business hours & contact info                  |
| `HELP`         | Full command list                              |
| *(anything)*   | "Text HELP for available commands"             |

Fuzzy matching: case-insensitive, whitespace-tolerant, alias keywords (`LOOKUP`, `VALUE`, `BUY`).

---

## Setup

### 1. Get a Surge API Key

1. Log in to [surge.app](https://surge.app) dashboard
2. Go to **API Keys** (or **Account → API**)
3. Create a key and note it

Store it:
```bash
secrets set surge_api_key YOUR_KEY_HERE
```

> ⚠️ The code scaffolds with `PLACEHOLDER` if the key is missing — SMS replies won't send until this is set.

### 2. Deploy to Cloud Run

```bash
cd ~/github/ammonfife/sakima.co/sms-api
./deploy.sh
```

The script:
- Builds a Docker image tagged for GCP project `heimdall-8675309`
- Pushes to GCR
- Deploys to Cloud Run (`sakima-sms` service)
- Prints the webhook URL when done

Prerequisites: `docker`, `gcloud` authenticated to `heimdall-8675309`.

### 3. Configure Surge Webhook

After deploy, the script prints a URL like:
```
https://sakima-sms-xxxxxxxxxx-uc.a.run.app/webhook/sms
```

In **Surge dashboard**:
1. Go to **Phone Numbers**
2. Click your Sakima number
3. Under **Inbound Messaging → Webhook URL**, paste the URL above
4. Set **HTTP Method** to `POST`
5. Save

Surge will POST inbound SMS to your webhook. The bot replies via the Surge send-message API.

---

## Architecture

```
Customer texts → Surge.app → POST /webhook/sms
                                    │
                              handlers/router.py
                                    │
            ┌───────────────────────┼───────────────────────┐
            │           │           │           │           │
         cert.py    price.py     bid.py     hours.py    help.py
            │                       │
      Turso DB (inventory)    Redis (cache, 30min TTL)
      PCGS public API
      NGC public API
```

## Coin Lookup Chain

`CERT`/`PRICE`/`BID` all use the same 3-step lookup:

1. **Sakima Turso DB** (`coins` table) — if you have inventory loaded, replies with your data + pricing
2. **PCGS public cert API** — `https://api.pcgs.com/publicapi/coindetail/GetCoinDetailByCertNo?CertNo=`
3. **NGC public cert API** — `https://api.ngccoin.com/v1/coins/`

Results are cached in Redis (Upstash) for 30min to reduce API calls.

## Adding Coin Inventory to Turso

Run the existing sync script or add a `coins` table:
```sql
CREATE TABLE IF NOT EXISTS coins (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cert        TEXT NOT NULL,
  service     TEXT,       -- PCGS / NGC
  description TEXT,
  grade       TEXT,
  price_guide REAL,
  ask_price   REAL,
  bid_price   REAL,
  created_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_coins_cert ON coins(cert);
```

## Local Dev

```bash
cd sms-api
pip install -r requirements.txt

export SURGE_API_KEY=your_key
export TURSO_URL=libsql://sakima-ammonfife.aws-us-west-2.turso.io
export TURSO_TOKEN=your_token
export REDIS_HOST=cheerful-man-36063.upstash.io
export REDIS_TOKEN=your_token

python main.py
# Webhook: http://localhost:8080/webhook/sms
# Health:  http://localhost:8080/health
```

Test with curl:
```bash
curl -X POST http://localhost:8080/webhook/sms \
  -H "Content-Type: application/json" \
  -d '{"from":"+18015551234","to":"+18015559999","body":"CERT 12345678"}'
```

## Environment Variables

| Variable      | Description                         | Required |
|---------------|-------------------------------------|----------|
| `SURGE_API_KEY` | Surge.app API key for sending SMS  | ✅ Yes   |
| `TURSO_URL`   | Sakima Turso DB URL (libsql://)     | Optional |
| `TURSO_TOKEN` | Turso auth token                    | Optional |
| `REDIS_HOST`  | Upstash Redis hostname              | Optional |
| `REDIS_TOKEN` | Upstash Redis token                 | Optional |
| `PORT`        | HTTP port (default 8080)            | Optional |

Without Turso/Redis, the bot still works — cert lookups fall through to PCGS/NGC APIs and caching is skipped.
