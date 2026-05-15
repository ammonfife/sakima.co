---
name: skill-standards
description: The core standards and formatting rules for creating or editing BigMac skills.
---

# BigMac Skill Writing Standards

All skills shared across the BigMac mesh (via `bigmac-skills`) must adhere to the following cross-platform compatibility rules. 

## 1. Mandatory Compatibility Preface
Every skill must begin with a preface block that reminds the agent to check for compatibility and to update the skill with their platform-specific block if one is missing.

**Example Preface:**
> [!IMPORTANT]
> **Cross-Platform Skill**: This skill is shared across Claude Code, OpenClaw, Gemini, and Codex. 
> Before executing, check the "Platform Blocks" below. If your current platform is missing, or if a command fails due to your unique toolset, **UPDATE THIS SKILL** by adding an `If you are [Platform]...` block detailing how your platform should execute it.

## 2. Platform-Specific Blocks
Instead of hardcoding tools specific to one agent (e.g., assuming `str_replace_editor` is universally available), skills should branch their instructions based on the platform reading them.

**Example Format:**

### If you are Claude (Claude Code / OpenClaw)
- Use your native `str_replace_editor` for targeted edits.
- You can spawn background tasks directly using `Bash run_in_background`.

### If you are Gemini (Antigravity / Google)
- Use your native `multi_replace_file_content` or `replace_file_content` tools.
- Background tasks should use the `run_command` tool with `WaitMsBeforeAsync` set appropriately.

### If you are Codex / Grok
- Use your respective file-editing APIs and terminal execution pipelines.

## 3. Graceful Degradation
If a skill requires an external CLI (like `gh`, `turso`, `security`) and the platform lacks the environment setup to run it, the agent must record the failure and append a platform-specific workaround or fallback instruction to the skill document.
