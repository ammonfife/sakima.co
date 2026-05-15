---
name: transaction-correctness
description: How WAL mechanics, checkpointing, concurrency rules, recovery work in tursodb
---

> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.

# Transaction Correctness Guide

Turso uses WAL (Write-Ahead Logging) mode exclusively.

Files: `.db`, `.db-wal` (no `.db-shm` - Turso uses in-memory WAL index)

## WAL Mechanics

### Write Path
1. Writer appends frames (page data) to WAL file (sequential I/O)
2. COMMIT = frame with non-zero db_size in header (marks transaction end)
3. Original DB unchanged until checkpoint

### Read Path
1. Reader acquires read mark (mxFrame = last valid commit frame)
2. For each page: check WAL up to mxFrame, fall back to main DB
3. Reader sees consistent snapshot at its read mark

### Checkpointing
Transfers WAL content back to main DB.

```
WAL grows → checkpoint triggered (default: 1000 pages) → pages copied to DB → WAL reused
```

Checkpoint types:
- **PASSIVE**: Non-blocking, stops at pages needed by active readers
- **FULL**: Waits for readers, checkpoints everything
- **RESTART**: Like FULL, also resets WAL to beginning
- **TRUNCATE**: Like RESTART, also truncates WAL file to zero length

### WAL-Index
SQLite uses a shared memory file (`-shm`) for WAL index. **Turso does not** - it uses in-memory data structures (`frame_cache` hashmap, atomic read marks) since multi-process access is not supported.

## Concurrency Rules

- One writer at a time
- Readers don't block writer, writer doesn't block readers
- Checkpoint must stop at pages needed by active readers

## Recovery

On crash:
1. First connection acquires exclusive lock
2. Replays valid commits from WAL
3. Releases lock, normal operation resumes

## Turso Implementation

Key files:
- [WAL implementation](../../../core/storage/wal.rs) - WAL implementation
- [Page management, transactions](../../../core/storage/pager.rs)

### Connection-Private vs Shared

**Per-Connection (private):**
- `Pager` - page cache, dirty pages, savepoints, commit state
- `WalFile` - connection's snapshot view:
  - `max_frame` / `min_frame` - frame range for this connection's snapshot
  - `max_frame_read_lock_index` - which read lock slot this connection holds
  - `last_checksum` - rolling checksum state

**Shared across connections:**
- `WalFileShared` - global WAL state:
  - `frame_cache` - page-to-frame index (replaces `.shm` file)
  - `max_frame` / `nbackfills` - global WAL progress
  - `read_locks[5]` - read mark slots (TursoRwLock with embedded frame values)
  - `write_lock` - exclusive writer lock
  - `checkpoint_lock` - checkpoint serialization
  - `file` - WAL file handle
- `DatabaseStorage` - main `.db` file
- `BufferPool` - shared memory allocation

## Correctness Invariants

1. **Durability**: COMMIT record must be fsynced before returning success
2. **Atomicity**: Partial transactions never visible to readers
3. **Isolation**: Each reader sees consistent snapshot
4. **No lost updates**: Checkpoint can't overwrite uncommitted changes

## References

- [SQLite WAL](https://sqlite.org/wal.html)
- [WAL File Format](https://sqlite.org/walformat.html)
