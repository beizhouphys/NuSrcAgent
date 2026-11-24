---
name: nusrcagent
description: Run and review NuSrcAgent IceCube single-source analyses, catalog-wide single-source analyses and stacking analyses. Use for source and catalog requests or follow-ups on saved analysis tasks.
---

# NuSrcAgent in Claude Code

Work from the NuSrcAgent checkout root. Read `AGENTS.md` and `.agents/skills/nusrcagent/SKILL.md` before planning or running an analysis. Follow the shared workflow and read its references from their original locations. Apply instructions addressed to Codex to this Claude Code session.

Use the project Python environment and the wrapper named in the shared workflow. Let the wrapper check inputs, run the fit and review its artifacts. Run only a task that reaches `READY`.

At `AWAITING_FLUX`, report the reviewed primary result and end the turn with the continuation question. Pass the user's actual reply to the flux command in a later turn if they ask to continue.
