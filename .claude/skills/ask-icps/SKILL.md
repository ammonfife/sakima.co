---
name: ask-icps
description: Get feedback on any feature, design, or decision from 5 customer ICPs + 3 expert advisors + Bob. Spawns parallel subagents representing each persona to give their honest reaction.
user-invocable: true
---

# /ask-icps

Get customer and expert feedback on any feature, design decision, pricing change, or product direction. Spawns up to 8 parallel subagents — 5 ICP customers + 3 expert advisors — who each respond from their specific perspective.

## Usage

```
/ask-icps Should we add a $0.10 per-lookup fee or keep it free?
/ask-icps What do you think of the current scan → list flow?
/ask-icps Would you pay $79/mo for this? What would make it worth it?
/ask-icps We're thinking about adding smart glasses support. Worth it?
```

## Personas

### Customer ICPs (in `.claude/agents/`)
| Agent | Archetype | Key Lens |
|-------|-----------|----------|
| `icp-ben` | Power dealer / platform builder | Speed, revenue, data flywheel, zero-shot |
| `icp-weekend-dealer` | Part-time Whatnot seller (100-500 coins) | Simplicity, cost, mobile-first |
| `icp-show-booth` | Physical coin show dealer | Labels, offline, speed at the table |
| `icp-flipper` | eBay arbitrage buyer | Margins, comps, list-to-flip speed |
| `icp-collector` | Hobbyist collector (doesn't sell much) | Collection tracking, price alerts, learning |

### Expert Advisors (in `.claude/agents/`)
| Agent | Role | Key Lens |
|-------|------|----------|
| `expert-cro` | Chief Revenue Officer | Revenue path, monetization, moat |
| `expert-architect` | Systems Architect (hacker-first) | Simplest path, ship fast, blast radius |
| `expert-cloudops` | Cloud Operations | Reliability, cost, monitoring, scaling |

### Team Member
| Agent | Role |
|-------|------|
| `bob` | Bob — Lovable agent / coin business operator. Knows the codebase, the scanner, the extension, and the customers. |

## How It Works

When invoked with a question:
1. Launch 5 ICP agents + 3 expert agents + Bob in parallel (9 total, or fewer if the question only applies to some)
2. Each agent reads the question and responds from their persona's perspective
3. Responses are collected and presented as a panel discussion
4. Conflicting opinions are highlighted — disagreement is the point
5. A synthesis at the end identifies: consensus items, split decisions, and blind spots

## Rules
- ICPs should respond as CUSTOMERS, not engineers. They care about the experience, not the implementation.
- Experts should respond as ADVISORS, giving honest strategic/technical/operational advice.
- Bob responds as a team member who knows the full context.
- No persona should just agree with another — if they genuinely disagree, say so.
- Each response should be 3-5 sentences MAX. This is a panel, not an essay contest.
- Tag each response with the persona's name and emoji.

## Implementation

The invoking agent should:
```
for agent in [icp-ben, icp-weekend-dealer, icp-show-booth, icp-flipper, icp-collector, expert-cro, expert-architect, expert-cloudops]:
  Agent(subagent_type=agent, prompt="{question}", run_in_background=true)
Agent(subagent_type=bob, prompt="Bob, react to this from your perspective: {question}", run_in_background=true)
```

Then collect all responses and present as a formatted panel.
