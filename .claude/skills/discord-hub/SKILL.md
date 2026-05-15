---
name: discord-hub
description: "Send messages, edit posts, and respond to interactions through the Discord REST API. Use when the user wants to interact with Discord channels, post to a guild, or build a bot response."
---

# Discord Hub

HTTP-based helpers for Discord API operations. See `references/discord-request-templates.md` for ready-to-use request bodies.

## Common operations

- **Create message:** `POST /channels/{channel_id}/messages` with `{"content": "...", "allowed_mentions": {"parse": []}}`
- **Edit message:** `PATCH /channels/{channel_id}/messages/{message_id}`
- **Interaction response:** `POST /interactions/{interaction_id}/{interaction_token}/callback`

## Auth

Bot tokens live in keychain: `security find-generic-password -a discord-bot -s discord-bot-token -w`.

Set the `Authorization: Bot <token>` header on all requests.

## Rate limits

Discord returns `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers. Respect them — repeated 429s get the bot temp-banned.
