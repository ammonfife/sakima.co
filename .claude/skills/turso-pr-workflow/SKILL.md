---
name: pr-workflow
description: General guidelines for Commits, formatting, CI, dependencies, security
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

# PR Workflow Guide

## Commit Practices

- **Atomic commits.** Small, focused, single purpose
- **Don't mix:** logic + formatting, logic + refactoring
- **Good message** = easy to write short description of intent

Learn `git rebase -i` for clean history.

## PR Guidelines

- Keep PRs focused and small
- Run relevant tests before submitting
- Each commit tells part of the story

## CI Environment Notes

If running as GitHub Action:
- Max-turns limit in `.github/workflows/claude.yml`
- OK to commit WIP state and push
- OK to open WIP PR and continue in another action
- Don't spiral into rabbit holes. Stay focused on key task

## Security

Never commit:
- `.env` files
- Credentials
- Secrets

## Third-Party Dependencies

When adding:
1. Add license file under `licenses/`
2. Update `NOTICE.md` with dependency info

## External APIs/Tools

- Never guess API params or CLI args
- Search official docs first
- Ask for clarification if ambiguous
