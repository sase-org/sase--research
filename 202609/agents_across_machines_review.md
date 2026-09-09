# Agents across machines: independent review of the consolidated recommendation

**Date:** 2026-09-09. **Status:** Independent review; no product changes.

**Subject:** `research:202609/agents_across_machines/agents_across_machines.md` and its
two researcher companions (A and B).

**Verdict:** Agree with the core UX direction, with higher confidence than the report
itself claims — its load-bearing factual claims all re-verify at newer revisions, and a
comparison class none of the three analyses examined (the 2025–26 agent-product
generation) independently converged on the same shape. Adopt it with six amendments,
the most important of which is a sequencing correction: as currently defined, the
epic's live Athena→Apollo acceptance proof validates the Focus/Fleet chrome the
recommendation deletes.

## Method

This review was performed at sase `8c8dfc3f6` and sase-core `5fc84c5`, both **newer**
than the revisions the consolidated report inspected (`63ec413b6` / `86077c6`), so it
also checks whether the report has already gone stale. Work done independently:

- Re-verified every implementation claim the recommendation rests on, in source at
  HEAD (line references below).
- Re-verified the report's two corrections of researcher B, and its S4 lead finding in
  the sase-core gateway.
- Checked the live epic state (`sase bead show sase-xe`, `sase-xe.16`).
- Read the `tui_perf.md` and `sase_artifacts.md` reference memories and the relevant
  glossary strands.
- Added an external comparison class the three analyses did not use: multi-context
  agent-session management in shipped agent products (GitHub Copilot, JetBrains,
  Claude Code).

No live TUI session, dispatch, or usability test was run; like the report under review,
this is an expert assessment of information architecture and evidence, not a usability
result.

## Verification: the evidence holds at HEAD

Only two commits landed after the report's inspected sase revision
(`baead1f50`, `8c8dfc3f6`), and neither weakens any finding. Every claim I checked
re-verifies:

| Claim | Verified at HEAD |
| --- | --- |
| Machine alias stored in the project field; synthetic `/fleet/<alias>/project.yml`; hardcoded `AgentType.RUNNING` | `src/sase/ace/tui/models/_fleet_agents_rows.py:171,173,190` |
| Remote rows merged after the fold/filter boundary | `src/sase/ace/tui/actions/agents/_loading_apply.py:398` → `_fleet.py:180` |
| All nine Fleet/remote actions unbound; documented as intended | `src/sase/default_config.yml:520-528`; `docs/remote_dispatch.md:240` |
| Attention fetched only for followed logical keys | `_fleet.py:295,313-317` |
| Remote attention terminates in transient toasts | `_remote_attention.py:82,88,107` |
| Content selection takes only the first handle | `_remote_content.py:53-55` |
| No `machine:` field in the agent query language | `src/sase/ace/agent_query/tokenizer.py:34` |
| `%dispatch` excludes `%wait`/`%queue`/`%clan`; controller strips them | `docs/remote_dispatch.md:215` |
| `%dispatch` completion catalog is config-only — no liveness, no capacity | `src/sase/dispatch/machine_catalog.py:10-29` |

The report's two **corrections of researcher B are themselves correct**:
`AgentType.RUNNING = "run"` is a manual-run execution type, not a lifecycle state
(`src/sase/core/agent_types.py:11`), and `app.edit_hooks` is already documented as fork
in the availability layer's own comment (`commands/_availability_agents.py:22,136,226`).
The consolidated report's practice of adversarially checking its own inputs worked.

The **S4 lead finding verifies exactly** in sase-core, at a revision newer than the one
the report read. The gateway's attention read resolves the caller-supplied batch of
logical keys and, when none resolve, returns an empty snapshot without touching the
notification store; the code comments it explicitly: "With no resolved followed row, no
notification read happens at all: attention stays scoped to logical keys this viewer
already follows" (`crates/sase_gateway/src/routes.rs:1361-1406`). This is the report's
most consequential technical point and it is right: deleting the client-side Follow
check cannot produce fleet-wide attention discovery. A new owner-side pending-attention
inventory contract is genuinely required, and it belongs in core/gateway per
`decisions:rust-core-required`.

Epic state also matches: `sase-xe` is reopened with all fifteen phases closed,
`sase-xe.16` in progress, `sase-xe.16.10` (the live Athena→Apollo proof) still open,
and `sase-xe.16.11` (setup correctness and live acceptance) in progress. Commit
`8c8dfc3f6` ("consume Rust federation counts", bead `sase-xe.16.11.6.1`) moved fleet
count consumption onto the Rust wire — evidence that the "shared query/count semantics
cross into Rust core" boundary call in the report is already the accepted trajectory,
not new scope.

## New evidence: the agent-product generation converged on the same shape

A and B drew comparisons from remote editing (VS Code), resource inventories (Azure,
Kubernetes), subscriptions (GitHub notifications), and fleet health (Grafana). None of
the three looked at the closest neighbors: products whose object *is* a coding-agent
session running somewhere else.

- **GitHub Copilot's agents panel** (shipped August 2025) is one list of agent sessions
  across all repositories, reachable from every page, with status, steering, and
  jump-to-PR per row. Repository — the "where" — is a row attribute, not a mode.
- **JetBrains IDEs added a "unified sessions view"** (May 2026) that merges CLI-agent
  and cloud-agent sessions into a single list — an explicit walk-back of separate
  surfaces per execution context.
- **Claude Code's claude.ai/code session list** shows cloud sessions and Remote
  Control sessions from the user's other machines in one list, each row labeled by
  kind/origin, with a status indicator.

Three vendors, arriving independently under real usage, all landed on: one
work-centric list; execution location as a labeled attribute; a global
needs-input/review signal that does not depend on which view is open. That is the
consolidated recommendation almost verbatim, from a comparison class with far higher
transfer validity than Kubernetes dashboards. It is the strongest external
corroboration available and the report should cite it.

## The disputed decisions: scoring the tie-breaks

Where A and B disagreed, I assessed each consolidated tie-break independently:

| Decision | My assessment |
| --- | --- |
| Machine control edits query state (not a second mode) | **Agree.** Avoids B's two-modes objection while keeping A's discoverability; "Custom" for advanced expressions is the right escape hatch. |
| Machines live in Admin Center, small health shortcut only | **Agree.** The `ProjectsPane` precedent (list + detail + in-TUI init flow) is real and directly reusable; a second permanent strip would repeat the Focus/Fleet chrome mistake. |
| Fetch **all** authorized pending attention, not visible-row attention | **Agree, strongly.** B's visible-row rule reintroduces the F4 failure one layer up: a question beyond the loaded page or outside a filter vanishes. This is the tie-break that matters most, and S4 shows it is the one that costs core work. Pay it. |
| Defer Watch; keep follow data as migration input | **Agree.** No corpus of notification overload exists yet — the same logic as `decisions:corpus-before-mechanism`. |
| Label every row including `here` | **Agree with a tighter trigger** (amendment C4 below). |
| Show capacity; defer automatic placement | **Agree on auto; disagree on bundling queue composition into the deferral** (amendment C2). |
| Redesign crosses into Rust core, not presentation-only | **Agree; verified** (S4, plus `8c8dfc3f6` showing counts already moved to the Rust wire). |

## What should change

### C1. Fix the acceptance-path sequencing (most important)

The report says "first finish the existing epic's live protocol/recovery acceptance
work" and separately "do not spend effort perfecting disposable Focus/Fleet chrome."
As written, those two instructions collide: `sase-xe.16.10`'s description defines the
live proof as launching remote agents with `%dispatch:apollo` **"and driving them from
Athena's TUI"** — i.e., through the Focus/Fleet chrome slated for deletion. Phases
`sase-xe.16.8` (Fleet/Focus PNG snapshots) and `.16.9` (fleet benches) are already
closed against that same mode-specific surface; the redesign invalidates both.

Resolve it explicitly, one of two ways:

1. **Re-scope the TUI leg of `sase-xe.16.10`** to the behaviors that survive the
   redesign — launch admission, receipt reconciliation, output read, stop, answer —
   driven through the protocol/CLI/facade layer (`sase machine`, `%dispatch`, the
   remote facade), which is redesign-proof. Treat any Focus/Fleet screen interaction
   as incidental, not acceptance evidence.
2. **Land researcher B's steps 1–3 first** (origin/project row-model split, merge
   before the fold/filter boundary, `machine:` + machine grouping) — they are small,
   strictly simplifying, and independent of the new attention contract — then run the
   live proof against the surface that will be kept.

Either is fine; the current ambiguity is not, because it spends the epic's scarcest
resource (live acceptance effort) on disposable chrome and will force a third round of
snapshots and bench re-baselining.

### C2. Unbundle per-owner `%queue` composition from deferred scheduling

The report defers "dispatch/queue composition" together with `%dispatch:auto` and
cross-machine queues. These are not the same size. `%queue(runners=, priority=)` is
runner-queue **admission**, and admission is already owner-local: the owner enforces
`max_running_agents` and its own queue for local launches. Letting
`%dispatch:apollo %queue(runners=2)` carry the directive through to the owner and have
the owner apply its existing local admission is a bounded change — stop stripping the
directive (`docs/remote_dispatch.md:215`), validate it, and surface "queued on apollo"
in the provisional-row table, which already has an "Accepted, starting/queued" state
waiting for it. No placement decision, no cross-machine scheduler, no new recovery
semantics.

This delivers the largest share of B's R9 payoff — the reason a second machine exists —
while still deferring exactly the parts (auto-placement, fleet-wide queues, automatic
fallback) whose admission and recovery semantics are genuinely new. Keeping the full
bundle deferred concedes too much to caution; B is right that this is the only item
that changes what the user can *do*.

### C3. Design the attention inventory as one contract with many consumers

The new owner-side pending-attention inventory (S4's replacement) should be specified
from day one as the single discovery contract for at least three consumers: the ACE
inbox, the existing `sase machine attention` CLI (`docs/remote_dispatch.md:240`), and —
when the deferred always-on delivery work eventually happens — push channels such as
the already-linked Telegram plugin. The report scopes the endpoint to ACE's needs.
That is cheap to widen now (bounded inventory, continuation, coverage/freshness are
consumer-agnostic) and expensive to retrofit later. The deferral of closed-ACE
delivery stays; only the contract's shape changes.

### C4. Sharpen the origin-label rule to "label when multi-origin"

The report labels every row including `here` in a mixed list; B labels only
exceptions. B's blank-means-here rule fails B's own F7 test — it makes action routing
depend on state the row does not show — so the report's side of the argument is right.
But "every row, always" over-pays on the common single-origin cases. The crisp rule:
**show the origin column whenever the current list result contains more than one
origin; suppress it entirely when the result is single-origin.** That automatically
covers pre-enrollment, a `machine:` filtered list, Here scope, and rows under an
unambiguous machine group header (the report's existing suppression case), while
guaranteeing the label is present in exactly the situations where a wrong-host action
is possible. Details and confirmations always name the owner regardless.

### C5. Bind the implementation to the established perf machinery by name

The report's performance section states the right outcomes (paint order, per-host
independence, zero-machine zero-work, 16 ms `j`/`k` p95) but not the mechanisms, and
this codebase has a documented history of new code paths bypassing them
(`tui_perf.md`). Three bindings worth making explicit in whatever plan follows:

- The unified projection must flow through the existing fast path —
  `_refilter_agents()` cached paint plus `_schedule_agents_async_refresh()` coalesced
  reload — not a new refresh path (tui_perf rule 5), and remote row updates should use
  the selective `patch_row()` machinery, not full rebuilds (rule 6).
- The all-tabs attention service must respect the idle refresh-token gating (rule 14)
  and the revalidate-vs-recompute cadence split (rule 10): a quiet tick reloads no
  surfaces and performs no fleet recompute.
- `bench_tui_jk_fleet.py` measures the old two-pipeline shape; merging remote rows
  before the fold boundary changes what it measures. Re-baseline it deliberately as
  its own step — do not adjust thresholds to fit.

Minor chrome note, same spirit: the illustrative 82-column layout spends a top-bar
`Needs you 2` badge *and* a full-width "Needs you: 2 across machines" band. On a
28-row terminal, show the band only when off-scope attention exists; otherwise the
badge suffices.

### C6. Keep the query dialects aligned (dropped from B)

B's recommendation to add `machine:` to the Artifacts Agent pane's query dialect
alongside the Agents tab tokenizer did not survive into the consolidated report. It
should: the two surfaces sharing vocabulary is what makes the pane the natural
overflow home for deep remote history browsing — the report's own answer to the
catalog-scale risk.

## Where I looked for disagreement and did not find it

For honesty about the review's adversarial effort: I specifically pressure-tested the
default-to-All-machines choice (defensible for a single operator because eligibility
is bounded to active + pending + bounded recent; the "quiet working set" need is met
by scope and saved queries, and the agent-product comparisons all default the same
way), the retirement of Follow as a visibility concept (F4/E2 verified; for one
operator, followed ≈ "launched from here", which dispatch exists to make irrelevant),
the Admin Center placement (the alternative — a persistent machine strip — repeats the
mistake being deleted), and the refusal to treat repaired Focus/Fleet as the
recommendation (the report is candid that repair is possible and rejects it on product
grounds, not feigned impossibility — the intellectually honest form of the argument).
No change recommended on any of these.

One residual caution the report itself states and I re-affirm: nothing here is a
usability result. The validation table (durable attention without visiting a view,
wrong-host attempt counts, lost-reply reconciliation, settled-elsewhere conflicts) is
the right harness; run it before treating density, defaults, and shortcuts as settled.

## Bottom line

The consolidated report's direction — one Agents list with machine as a first-class
attribute, fleet-wide durable attention, Admin Center machine management, explicit
launch target and source context, capacity shown but placement deferred — is correct,
and it is now corroborated four ways: three independent internal analyses, and the
convergent evolution of GitHub, JetBrains, and Claude Code's own session surfaces.
Adopt it. Before implementation planning: resolve the C1 acceptance-path collision in
the epic's remaining beads, pull per-owner `%queue` composition forward (C2), and
widen the attention-inventory contract to non-ACE consumers (C3). C4–C6 can be folded
into the eventual implementation plan as written.

## Sources

**Verified in source at sase `8c8dfc3f6`:** `src/sase/ace/tui/models/_fleet_agents_rows.py`;
`src/sase/ace/tui/actions/agents/_loading_apply.py`, `_fleet.py`,
`_remote_attention.py`, `_remote_content.py`; `src/sase/ace/tui/commands/_availability_agents.py`;
`src/sase/ace/agent_query/tokenizer.py`; `src/sase/core/agent_types.py`;
`src/sase/dispatch/machine_catalog.py`; `src/sase/default_config.yml`;
`docs/remote_dispatch.md`; commit `8c8dfc3f6` (`feat(fleet): consume Rust federation
counts`, bead `sase-xe.16.11.6.1`).

**Verified in sase-core at `5fc84c5`** (opened via `sase repo open`):
`crates/sase_gateway/src/routes.rs:1361-1406` (`fleet_attention_read`).

**Audited artifact reads:** `research:202609/agents_across_machines/agents_across_machines.md`
and companions `__a` / `__b`.

**Beads:** `sase bead show sase-xe`, `sase-xe.16` (2026-09-09).

**Audited memory reads:** `sase_artifacts.md`, `sase_beads.md`, `tui_perf.md`;
glossary strands for agent clan/family/hood/node/tribe, sase node, artifact, ref.

**External:**
[GitHub — tracking Copilot's sessions / agents panel](https://docs.github.com/en/copilot/how-tos/agents/copilot-coding-agent/tracking-copilots-sessions);
[GitHub changelog — unified sessions view in JetBrains IDEs (2026-05-13)](https://github.blog/changelog/2026-05-13-introducing-copilot-cli-agent-and-unified-sessions-view-in-github-copilot-for-jetbrains-ides/);
[GitHub changelog — coding agent sessions from VS Code (2025-07-14)](https://github.blog/changelog/2025-07-14-start-and-track-github-copilot-coding-agent-sessions-from-visual-studio-code/);
Claude Code claude.ai/code session list (cloud + Remote Control sessions across
machines, per current product documentation and reporting).
