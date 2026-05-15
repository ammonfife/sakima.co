# Personal API Ecosystem - Complete Endpoint Reference

## Base URL

`http://localhost:3000/api/v1`

## Messages Endpoints

### GET /messages/recent

Get recent messages within a time window.

**Query Parameters:**

- `limit` (number, optional, default: 10) - Max messages to return
- `hours` (number, optional, default: 24) - Time window in hours
- `contact` (string, optional) - Filter by contact name/number

**Response:**

```json
{
  "messages": [
    {
      "id": "msg-123",
      "from": "+15551234567",
      "text": "Hello world",
      "timestamp": "2026-02-04T12:00:00Z",
      "is_from_me": false,
      "thread_id": "thread-abc"
    }
  ],
  "count": 1,
  "timeframe_hours": 24
}
```

### GET /messages/search

FTS5 full-text search across all messages.

**Query Parameters:**

- `query` (string, required) - Search query (supports FTS5 syntax)
- `limit` (number, optional, default: 20) - Max results
- `contact` (string, optional) - Filter by contact

**FTS5 Query Syntax:**

- Simple: `hello`
- Multiple: `hello world` (AND)
- OR: `hello OR hi`
- Phrase: `"exact phrase"`
- Wildcard: `hel*`
- NOT: `hello NOT spam`

**Response:**

```json
{
  "results": [
    {
      "id": "msg-456",
      "from": "John Doe",
      "text": "Hello, let's meet tomorrow",
      "timestamp": "2026-02-03T15:30:00Z",
      "is_from_me": false
    }
  ],
  "count": 1,
  "query": "hello"
}
```

### GET /messages/conversation

Get full conversation history with a contact.

**Query Parameters:**

- `contact` (string, required) - Contact name or number
- `limit` (number, optional, default: 50) - Max messages

**Response:**

```json
{
  "contact": "John Doe",
  "messages": [
    {
      "id": "msg-789",
      "from": "John Doe",
      "text": "Thanks!",
      "timestamp": "2026-02-04T10:00:00Z",
      "is_from_me": false
    }
  ],
  "count": 25
}
```

### GET /messages/stats

Get statistics for all contacts.

**Response:**

```json
{
  "total_contacts": 50,
  "contacts": [
    {
      "contact": "John Doe",
      "message_count": 1523,
      "last_message": "2026-02-04T10:00:00Z",
      "days_since_contact": 0
    }
  ]
}
```

## Memory Endpoints

### GET /memory/search

Search across all memory files (daily + MEMORY.md).

**Query Parameters:**

- `query` (string, required) - Search terms
- `limit` (number, optional, default: 10) - Max results

**Response:**

```json
{
  "results": [
    {
      "file": "memory/2026-02-04.md",
      "snippet": "Database migration completed successfully...",
      "line_number": 42,
      "relevance": 0.95
    }
  ],
  "count": 1
}
```

### GET /memory/recent

Get recent memory entries.

**Query Parameters:**

- `days` (number, optional, default: 7) - Days to look back
- `limit` (number, optional, default: 10) - Max entries

**Response:**

```json
{
  "entries": [
    {
      "date": "2026-02-04",
      "file": "memory/2026-02-04.md",
      "preview": "Completed FTS5 implementation...",
      "word_count": 1250
    }
  ],
  "count": 7
}
```

## Projects Endpoints

### GET /projects

List all tracked Git repositories.

**Response:**

```json
{
  "projects": [
    {
      "name": "personal-api-ecosystem",
      "path": "/Users/benfife/clawd-garcia/projects/personal-api-ecosystem",
      "branch": "main",
      "lastCommit": {
        "sha": "abc123",
        "message": "Add FTS5 triggers",
        "date": "2026-02-04T20:00:00Z"
      }
    }
  ],
  "count": 30
}
```

### GET /projects/health

Get health status for all projects.

**Response:**

```json
{
  "healthy": 15,
  "attention_needed": 8,
  "stale": 7,
  "projects": [
    {
      "name": "personal-api-ecosystem",
      "status": "healthy",
      "uncommittedChanges": 0,
      "daysSinceCommit": 0,
      "branch": "main"
    },
    {
      "name": "old-project",
      "status": "stale",
      "uncommittedChanges": 5,
      "daysSinceCommit": 45,
      "branch": "develop"
    }
  ]
}
```

**Status Definitions:**

- `healthy` - Recent commit, no uncommitted changes
- `attention_needed` - Uncommitted changes or off main branch
- `stale` - No commits in 30+ days

### GET /projects/:name

Get detailed status for a specific project.

**Response:**

```json
{
  "name": "personal-api-ecosystem",
  "path": "/Users/benfife/clawd-garcia/projects/personal-api-ecosystem",
  "branch": "main",
  "status": "healthy",
  "uncommittedChanges": 0,
  "commits": [
    {
      "sha": "abc123",
      "message": "Add FTS5 triggers",
      "author": "Ben Fife",
      "date": "2026-02-04T20:00:00Z"
    }
  ],
  "branches": ["main", "develop"]
}
```

## Relationships Endpoints

### GET /relationships

List all contacts with statistics.

**Query Parameters:**

- `limit` (number, optional, default: 50) - Max contacts
- `sort` (string, optional, default: "activity") - Sort by: activity, health, name

**Response:**

```json
{
  "contacts": [
    {
      "contact": "John Doe",
      "message_count": 1523,
      "last_message_date": "2026-02-04T10:00:00Z",
      "days_since_contact": 0,
      "health_score": 1.0
    }
  ],
  "count": 50
}
```

### GET /relationships/health

Get relationship health overview.

**Response:**

```json
{
  "healthy": 25,
  "needs_attention": 15,
  "inactive": 10,
  "contacts": [
    {
      "contact": "Jane Smith",
      "health_score": 0.3,
      "days_since_contact": 45,
      "message_count": 234,
      "status": "needs_attention"
    }
  ]
}
```

**Health Score Formula:**
`1.0 - min(1.0, days_since_contact / 90)`

**Status Definitions:**

- `healthy` - Contacted within 30 days
- `needs_attention` - 30-90 days since contact
- `inactive` - 90+ days since contact

### GET /relationships/outreach

Get suggested contacts for outreach.

**Query Parameters:**

- `threshold_days` (number, optional, default: 30) - Days threshold
- `limit` (number, optional, default: 10) - Max suggestions

**Response:**

```json
{
  "suggestions": [
    {
      "contact": "Old Friend",
      "days_since_contact": 45,
      "message_count": 156,
      "health_score": 0.5,
      "priority": "medium",
      "last_message": "Hope you're doing well!"
    }
  ],
  "count": 5
}
```

**Priority Levels:**

- `high` - 60+ days, high message count history
- `medium` - 30-60 days
- `low` - Recent but declining frequency

### GET /relationships/:contact

Get detailed relationship context for a specific contact.

**Response:**

```json
{
  "contact": "John Doe",
  "message_count": 1523,
  "last_message_date": "2026-02-04T10:00:00Z",
  "last_message_text": "See you tomorrow!",
  "days_since_contact": 0,
  "health_score": 1.0,
  "frequency": {
    "messages_per_week": 12.5,
    "trend": "stable"
  },
  "recent_messages": [
    {
      "text": "See you tomorrow!",
      "timestamp": "2026-02-04T10:00:00Z",
      "is_from_me": false
    }
  ]
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

**Common Status Codes:**

- `200` - Success
- `400` - Bad request (missing/invalid parameters)
- `404` - Not found
- `500` - Internal server error

## Rate Limits

No rate limits currently enforced on localhost. For production deployment, consider implementing rate limiting.

## Authentication

Currently none required for localhost. For remote access, add authentication layer to API gateway.

## Database Schema

### messages table

```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT UNIQUE,
  contact TEXT,
  text TEXT,
  timestamp DATETIME,
  is_from_me BOOLEAN,
  thread_id TEXT,
  indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### messages_fts table (FTS5)

```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
  message_id,
  contact,
  text
);
```

### projects table

```sql
CREATE TABLE projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE,
  path TEXT,
  branch TEXT,
  status TEXT,
  last_commit_sha TEXT,
  last_commit_message TEXT,
  last_commit_date DATETIME,
  uncommitted_changes INTEGER,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### relationships table

```sql
CREATE TABLE relationships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact TEXT UNIQUE,
  message_count INTEGER,
  last_message_date DATETIME,
  days_since_contact INTEGER,
  health_score REAL,
  outreach_priority INTEGER,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Data Sync

**Messages**: Auto-synced via triggers on INSERT/UPDATE/DELETE  
**Projects**: Updated on API request (live Git status)  
**Relationships**: Calculated from messages table  
**Memory**: Read directly from filesystem

## Performance Notes

- **FTS5 search**: 1-3x faster than LIKE queries
- **Database size**: ~50MB for 142k messages
- **Query response time**: 50-200ms typical
- **Bottleneck**: Network latency to Turso (if using remote database)
