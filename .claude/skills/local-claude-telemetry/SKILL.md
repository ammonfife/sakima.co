---
name: local-claude-telemetry
description: Read and analyze the local-only Claude Code data streams on this machine — full session transcripts (~/.claude/projects/*.jsonl), local OTel usage metrics (~/.claude/local-metrics/data/metrics.jsonl), local OTel usage events (~/.claude/local-metrics/data/events.jsonl), and debug logs (~/.claude/debug/). Use when you need token/cost/usage analytics, session forensics, per-model consumption, tool-usage patterns, or to verify the local collector is healthy. All data is local-only; nothing here is sent to Anthropic (Statsig/Sentry telemetry is disabled machine-wide as of 2026-07-09).
---

# Local Claude telemetry & transcripts

As of 2026-07-09 this machine sends Anthropic only what's required to function
(API requests + auth, feature-flag fetches, auto-update checks). Everything else
is captured locally in four streams:

| Stream | Path | Contents |
|---|---|---|
| Session transcripts | `~/.claude/projects/<project-slug>/<session-id>.jsonl` | Every prompt, response, tool call/result per session |
| Usage metrics | `~/.claude/local-metrics/data/metrics.jsonl` | OTLP JSON: `claude_code.session.count`, `.token.usage` (by model/type), `.cost.usage`, `.lines_of_code.count`, etc. |
| Usage events | `~/.claude/local-metrics/data/events.jsonl` | OTLP JSON log records: user prompts submitted, tool decisions, API request events (model, tokens, duration) |
| Debug logs | `~/.claude/debug/<session-id>.txt` | Only when a session runs with `--debug` (or `DEBUG=1`) |

Rotation: metrics/events rotate at 50MB, 10 backups (`metrics-<ts>.jsonl`). Read the
rotated files too for history. Local pipeline started 2026-07-09 — no OTel data exists
before that date; for older history use transcripts.

## Collector health (check first if files are stale)

```bash
lsof -iTCP:4317 -sTCP:LISTEN | grep otelcol   # should show otelcol-c on 127.0.0.1
# restart if needed:
launchctl unload ~/Library/LaunchAgents/com.benfife.otel-local.plist
launchctl load   ~/Library/LaunchAgents/com.benfife.otel-local.plist
tail ~/.claude/local-metrics/collector.err.log
```

Binary: `~/.claude/local-metrics/bin/otelcol-contrib` (v0.156.0).
Config: `~/.claude/local-metrics/otel-config.yaml` (OTLP in on 4317 grpc / 4318 http → file exporters).
Claude Code emits via env in `~/.claude/settings.json` (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_*` → 127.0.0.1:4317). Applies to every CLI session and all agents automatically.

## Reading metrics (OTLP JSON is nested — use jq/python)

Total tokens by model and type across all datapoints:
```bash
jq -r '.resourceMetrics[].scopeMetrics[].metrics[] | select(.name=="claude_code.token.usage") | .sum.dataPoints[] | [(.attributes | map(select(.key=="model"))[0].value.stringValue), (.attributes | map(select(.key=="type"))[0].value.stringValue), (.asDouble // .asInt)] | @tsv' ~/.claude/local-metrics/data/metrics.jsonl | awk -F'\t' '{a[$1"\t"$2]+=$3} END {for (k in a) print k"\t"a[k]}' | sort
```

Cost per session:
```bash
jq -r '.resourceMetrics[].scopeMetrics[].metrics[] | select(.name=="claude_code.cost.usage") | .sum.dataPoints[] | [(.attributes | map(select(.key=="session.id"))[0].value.stringValue), .asDouble] | @tsv' ~/.claude/local-metrics/data/metrics.jsonl
```

Metric datapoint attributes include `session.id`, `model`, `type` (input/output/cacheRead/cacheCreation), `user.id`, `organization.id` — so usage is attributable per account/org locally.

## Reading events

```bash
jq -r '.resourceLogs[].scopeLogs[].logRecords[] | [(.attributes | map(select(.key=="event.name"))[0].value.stringValue // .body.stringValue)] | @tsv' ~/.claude/local-metrics/data/events.jsonl | sort | uniq -c
```
Event names include `user_prompt`, `tool_decision`, `api_request`. Each record carries session id, timestamp, and event-specific attributes (tool name, decision, model, duration_ms, tokens).

## Transcripts (the richest source; predates the OTel pipeline)

- One dir per project cwd (slugified), one JSONL per session. ~861+ files, ~1GB.
- Also see the `read-cli-sessions` and `session-logs` skills for established transcript tooling.
- Correlate: OTel `session.id` == transcript filename == `sessionId` field inside lines.

## Caveats

- Do NOT "fix" privacy env: `DISABLE_TELEMETRY=1` (Statsig) coexists with `CLAUDE_CODE_ENABLE_TELEMETRY=1` (local OTel). Both are intentional. Removing OTEL_* vars silently stops local capture.
- events.jsonl records prompt *events*; full prompt text lives in transcripts, not OTel.
- Files are 0640; run as benfife.
