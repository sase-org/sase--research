# E4: practical value of verified completion

**Desired end result:** After `sase tool run check`, prepared completion can commit the exact verified tree even when `check` exits nonzero solely because of previously evidenced KNOWN or FLAKY failures. This requires explicit `accept: no-new`; the default still requires a pass.

A receipt lets you check which run verified the current tree, its verdict, and its age. The host checks again immediately before committing: changed files, expired or invalid receipts, and NEW or UNKNOWN failures stop the commit and trigger recovery. Commits and bead closes record the verification evidence.

The practical payoff is landing verified work while master is red without another agent recovery turn. E4 does not skip or speed up checks; its receipts report measures whether reuse might be worthwhile later.

Sources: `plan:202609/tool_e4_verified_completion.md`; `research:202609/sase_tool_e3_e4_landing_criteria/sase_tool_e3_e4_landing_criteria.md`.
