---
narration: 1
title: Which Recent SASE Tasks Matter Most
source: research:202610/task_bead_48h_impact_ranking/task_bead_48h_impact_ranking__final.md
source_blob: 49e57245a23bc522e0753038ab953d94b2a172cc
date: 2026-10-07
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The short answer

Which recent task beads deserve attention first? This audit covers tasks created or corroborated in the last 48 hours. It combines 5 independent reports with fresh verification by the lead researcher.

The audit found 23 qualifying tasks. Of these, 11 were created in the window, 13 were corroborated, and 1 qualified both ways. Rankings measure the impact of work still left to do. Already delivered fixes receive separate treatment.

The decisive finding is that none of 117 check runs passed. Of those runs, 111 failed and 6 were signaled. The last successful check on athena was October 4. These measurements cover athena only, and repeat runs can inflate counts. Counts of distinct agents provide a better measure of reach.

The strongest immediate recommendations are 2 small fixes: repair the private-module lint failure and the launch-approval import cycle. Then address releases and the recurring import-budget failure.

## The ranked work

First is the private-module problem in the symvision lint stage. It appeared in 65 of the 117 window check runs. In 21 runs, it was the only failing signature. A mechanical module rename would remove a broad verification blocker. A permanently failing stage also hides new regressions.

Second is the circular import that breaks launch approval. Both of the last 2 approved launches failed. A fresh interpreter still reproduces the failure. Each occurrence loses work the user approved. The repair must make imports independent of order and test them in a fresh process.

Third is the core release and dependency floor. Installing sase silently resolves to version 0.1.0, while version 0.17.1 cannot resolve. The declared core floor lacks 100 required capabilities. The source pin has not reached a release tag. Release the core containing that pin, update the supported dependency window, then publish sase and update plugin floors. Publishing requires the owner.

Fourth is the text user interface import budget. It failed across 68 runs and 66 agents over 14 days. Repeated cap increases have not solved it. Adopt an explicit budget policy and defer eager imports. Allowing equality at the cap would only restart the creep.

Fifth is read-only bead resolution that can initialize stores and commit scaffolding. Source inspection confirms the path. The harm requires a directory without an existing store; no destructive incident was observed. Read operations should open existing stores or report them unavailable.

Sixth is absent-store tests finding the host's live store. It has 15 lifetime corroborations, the most in this set. Fix resolver isolation, including the related plan-resolver test.

Seventh is prompt-bar macro argument detection after quoted commas or closing parentheses. The interface disagrees with the core parser. Reuse the core's structural argument spans and add shared fixtures.

Eighth is the peak-memory test flake. It affected 38 runs across 38 agents. Production evidence does not support a broader measurement problem. Of 632 production runs, the only zero reading came from a no-op command. Clarify the sampling contract, then fix the sampler or assertion.

Ninth is the deck scroll-settle flake. It affected 15 runs, with 13 more on a sibling test. One change to how tests await settled scrolling would likely clear several failures.

Tenth is command-line tests asserting temporary paths truncated by Rich. These fail deterministically when run directly. Bundle their isolation repair with the absent-store tests.

## What to do next

Avoid relaunching work already delivered. The beads-pane refresh is fixed and needs remeasurement. Slow cloning is mostly fixed; its remaining cause belongs to an active epic. The prompt-focus flake is very likely fixed but needs a parallel confirmation. Link validation is mitigated and needs narrowing or closure.

The audit also filed a task for broken failure-owner matching. None of 897 window triage items named an owner, even when an open task matched the failure. This amplifies repeated rediscovery and misleading regression labels.

Start with the private-module and launch fixes. Verify delivered work, complete the owner-led release, and repair import budgets and resolver isolation. Then address owner matching, prompt parsing, and the remaining flakes.
