# Agents across machines: a recommended ACE experience

**Date:** 2026-09-09. **Status:** Research and design recommendation; no product changes.

**Recommendation:** Replace Focus/Fleet with one Agents list across the current machine
and enrolled machines. Give machine identity its own field, filter, and optional grouping.
Make pending human decisions durable and discoverable across the whole fleet. Put machine
administration in Admin Center, and put an explicit target selector beside the launch
prompt. Retire Focused/Unfocused as a product concept; defer a separate Watch feature.

This deliberately revisits the earlier accepted design at the user's request. It
preserves that design's strongest foundations: owner authority, stable identities,
bounded reads, explicit placement, and recoverable operations.

## Evidence and confidence

This report combines [researcher A](agents_across_machines__a.md),
[researcher B](agents_across_machines__b.md), and independent lead research focused on
their disagreements and weak evidence. The lead reviewed SASE at
`63ec413b60492082e0a7a95e142417d74e05150b` and the opened Rust core at
`86077c6e5adf6d66f0351736940f33651089e98c`, the epic and plans through audited artifact
reads, a committed 82×28 screenshot as an image, and current primary product documentation.
A and B used the earlier SASE revision `7a4fb2149`.

This is an expert design assessment, not a usability experiment. No live dispatch,
remote mutation, benchmark, or interactive ACE session was performed for this synthesis.
The inspected epic still records incomplete live acceptance. Confidence is strongest in
the information architecture and attention requirements; exact density, defaults, and
shortcuts need task testing. The screenshot demonstrates layout, not working integration.

## What the evidence supports—and what it does not

The current membership rule is difficult to infer:

| Agent | Focus | Fleet |
| --- | --- | --- |
| Local | Included | Excluded |
| Followed remote | Included | Included |
| Unfollowed remote | Excluded | Included |

Focus includes local work regardless of its importance. Fleet excludes the controller's
own agents. Moving to another controller changes membership without changing the work.
The [original research](../remote_dispatch_and_fleet_focus/remote_dispatch_and_fleet_focus.md)
made a reasonable case for a deliberately quiet working set. That need remains valid;
an asymmetric local/remote membership rule is an unnecessarily costly way to meet it.

Independent source inspection confirms these implementation gaps:

- The load/apply path merges remote rows **after** the filter/fold boundary. Remote
  refresh has another finalization path, so the precise finding is inconsistent pipeline
  integration, rather than proof that filtering can never affect remote rows. [S1](#s1)
- Remote rows spend the project field on the machine alias. The query language has no
  `machine:` field. This blocks a faithful “project SASE across machines” view. [S1](#s1)
- Attention is requested only for followed logical keys. Refresh scheduling returns
  early outside the Agents tab. Notices finish as transient toasts; the durable ledger
  remembers announcement decisions, which is different from a durable actionable inbox. [S2](#s2)
- Nine Fleet/remote actions default to `unbound`; content selection takes only the first
  available handle; setup is presented as a twelve-second toast. [S1](#s1)[S2](#s2)

Two of B's implementation claims need correction. `AgentType.RUNNING` means a manual
run execution type; lifecycle lives separately in `status`. There are no DONE/FAILED
variants to select instead. Also, `edit_hooks` already serves as fork on the local
Agents surface, and its footer labels say “fork.” Its historical internal name does
not establish a remote-only change of meaning. Preserve familiar fork behavior while
fixing inconsistent availability and labels. [S3](#s3)

More broadly, these defects do not prove that two views inevitably cause bad filtering
or missed attention. Focus/Fleet could be repaired. The reason to replace it is the
clearer product model and smaller amount of view-specific state, not an architectural
impossibility.

## Relevant comparisons

VS Code's remote editor retains familiar work operations while making the host visible
in a persistent status control. Its newer remote-agent workflow also puts machine and
workspace selection into session creation and exposes host connection state. These are
useful precedents for visible execution context and a target picker; neither establishes
that SASE should copy VS Code's host navigation.
[Remote SSH tutorial](https://code.visualstudio.com/docs/remote/ssh-tutorial),
[remote agent sessions](https://code.visualstudio.com/docs/agents/run/remote-agent-sessions).

Carbon distinguishes persistent inline feedback from timed toasts and recommends a
revisitable destination when users must return to a notification. This supports an
attention inbox and persistent enrollment flow. A toast can acknowledge an operation;
it should not be the only place to find an unanswered gate or setup instructions.
[Carbon notification guidance](https://carbondesignsystem.com/components/notification/usage/).

GitHub defines watching as a subscription to activity and supports event-specific
notification preferences. That supports separating subscription from browsing. It does
not justify treating an old SASE unfollow as permission to hide an unresolved approval.
[GitHub notification settings](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).

Kubernetes scheduling filters for feasibility before choosing among hosts; resource,
software, policy, and data constraints all matter. The relevant inference for SASE is
that spare runner capacity alone cannot justify automatic placement.
[Kubernetes scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/).

## Decisions where the researchers differ

| Question | Consolidated decision | Reason |
| --- | --- | --- |
| Separate machine scope control, or query alone? | A compact machine control edits the existing query/filter state. | A gives beginners discoverability; B avoids a second independent mode. Advanced machine expressions display as “Custom,” rather than contradicting a selector. |
| Machines in top chrome or only Admin Center? | Admin Center → Machines, with a small health shortcut when machines are enrolled. | One administration destination, directly reachable from an offline row, launch picker, or top-bar incident. Avoid a second permanent strip. |
| Fetch attention for visible rows, or all machines? | All authorized pending attention, independently of list scope, folds, pagination, and active ACE tab. | B's visible-row rule still misses a question beyond the loaded page or outside a filter. |
| Retain Watch now? | Keep old follow records as migration/rollback input; expose no new Watch axis initially. | A's simpler default wins. Reuse existing notification controls, but do not equate unwatch with hiding unresolved work. |
| Label only remote rows? | In a mixed list, show a short machine label on every row, including `here`. | Explicit origin makes wrong-host actions less likely. Suppress repeated labels only under an unambiguous machine header; details and operations always name the owner. |
| Add capacity and automatic scheduling together? | Show measured capacity when available; defer automatic placement and dispatch/queue composition. | Capacity helps an explicit choice. Scheduling changes admission, eligibility, and recovery semantics and is separate work. |
| Is the redesign primarily presentation work? | Some is; global attention discovery and shared query/count semantics cross into Rust core. | B understates the backend work needed to deliver the unified behavior reliably. |

For a small personal fleet, one list best supports “find the work, understand its state,
act on it.” Separate Local/Remote or per-machine tabs make cross-machine triage require
navigation. A repaired Focus/Fleet remains a defensible fallback if testing demonstrates
that an explicit curated working set materially improves daily work. Even then, make it
a symmetric saved view applicable to local and remote agents.

## The proposed everyday experience

### One list and familiar views

Preserve the existing Agents, Artifacts, and AXE top-level tabs, list/detail layout,
family hierarchy, query profiles, and grouping controls. Merge already owner-resolved
remote projections into the **pure** shared filtering/grouping path. Do not feed remote
records through local PID checks, filesystem hydration, or cleanup side effects.

Default to all machines after enrollment. Initially include active work, pending
decisions, unresolved operations, and the same bounded recent-completion policy for
every origin. Older history is requested explicitly and paged; “All machines” means
all origins, not every historical execution loaded into memory. Expose “More results”
and incomplete coverage when appropriate.

Add `machine:here` and named-machine filtering, composed with existing project/status
queries. Add machine grouping to the current grouping cycle. Keep the default project
and user-authored organization; a host must not replace a project or tribe. Preserve
the selected logical agent across refresh and family handoff, and expose its current
shell in details. Count logical agents separately from occupied runner slots.

Illustrative layout, not a literal keymap specification:

```text
Agents | Artifacts | AXE           here: athena   Machines !1   Needs you 2
Machine: All v   project:sase       3 running; mac unknown   Group: project
Needs you: 2 across machines — Open inbox

sase
  auth-fix       QUESTION       apollo       Approve policy
  docs-refresh   RUNNING        here         Update docs
  ci-watch       WAS RUNNING    mac          last seen 12m ago

auth-fix · sase · apollo
Question: permit the proposed operation?            observed 3s ago
[Answer]  [Open output]  [More actions]

Target: Here v   Prompt: _______________________________________________
```

The actual list remains strict about the user's query. Off-scope attention appears as
an explicitly global count/link—“2 need you elsewhere”—rather than inserting rows that
silently violate the filter. Opening the inbox and returning restores the list's query,
selection, and scroll position. New arrivals update counts without stealing focus or
moving the selected row beneath the user's next keystroke.

In an 82-column terminal, preserve name, actionable status, origin, and stale/unknown
meaning before model or intent. Healthy rows do not need repeated “online · fresh” text.
Detail shows observation time. With no remote enrollment, retain the compact local
experience and a discoverable Machines/Connect command.

### Attention is a responsibility surface

Use the existing notification panel and badge for remote questions and gates. Reuse
local answer/approval presentation, with the owner in its header. Requests remain
discoverable until the owner reports settlement. Seeing a notification, dismissing a
toast, or reading a question must not mark the underlying request answered.

Separate the policies explicitly:

| Policy | What it changes |
| --- | --- |
| Query, fold, pin, or dismiss | The viewer's browsing organization; never remote execution. |
| Mute routine updates | Interruptions about progress/completion; pending decisions remain discoverable. |
| Snooze a decision | Its prominence until a chosen time, with a visible snoozed category/count. |
| Future Watch | Optional routine update subscription, independent of visibility and authority. |
| Answer or approve | A request to the owner against the exact decision and revision. |

Deduplicate by origin, request identity, and revision. Reconnect should reconcile the
durable inbox, not replay a toast storm. If another controller already answered, show
“Already resolved” and refresh the row. A changed approval preview requires renewed
review. Ownership and actionable permissions come from the protocol, never Follow.

**New lead finding:** the current attention endpoint accepts a bounded list of known
logical keys. An empty list intentionally reads no notification store and returns no
entries. Removing the client-side Follow check cannot create fleet-wide discovery.
Implement a bounded owner-side pending-attention inventory with continuation and
coverage/freshness, or an equivalent complete discovery contract. It must find decisions
whose agents have never appeared in this viewer's loaded catalog. [S4](#s4)

Run that lightweight attention service while ACE is open, including on Artifacts and
AXE; heavy catalog/detail hydration remains demand-driven. An unavailable machine makes
coverage unknown, not zero. Always-on delivery with ACE closed remains separate from
this recommendation, as in the original epic scope. [S5](#s5)

### Familiar operations, explicit targets

Give local and remote rows the same visible verbs: open output/chat/diff, answer,
stop, retry, and fork where supported. Preserve familiar bindings. Show conditional
actions in the footer; global actions remain in help per ACE's convention. Unsupported
actions have a discoverable reason in details or the palette. Do not promise remote
tmux/editor access or cross-host continuation just because a row shares a widget.

Retry and fork default to the selected agent's owner. A new unrelated prompt defaults
to Here. Merely selecting a remote row or filtering to a machine does not change the
launch target. Terminal dismissal remains a viewer operation; it must never become
remote stop accidentally.

Mixed-machine group actions need an explicit target preview and per-target results.
One unreachable machine must not turn partial completion into a generic “success,” and
selection changes must not retarget an operation already submitted. Preserve exact
instance fencing and owner-validated preconditions underneath the shared commands.

### Launching: machine, source, then outcome

Keep `%dispatch:<alias>` as the portable spelling. The TUI target picker and parsed
directive must stay synchronized; duplicate/conflicting directives produce an inline
error. The picker names the target and shows cached health and supported eligibility;
typing must not trigger discovery or blocking network work.

**The missing decision aid is source context.** Ordinary remote launch currently needs
a clean checkout, an upstream, and a published HEAD unless trusted launch payloads supply
revision/Patch evidence. Local attachments and collected file inputs are rejected.
Typing an artifact name in prose does not supply that structured evidence. [S6](#s6)

Show the resolved project and revision/Patch beside the target before submission, and
explain unmet prerequisites in place. Preserve the draft after refusal. Do not silently
drop attachments, substitute an older revision, publish changes, or launch locally.
The machine picker should help users understand what will run, not only where.

An immediate provisional row tracks the launch through durable identity reconciliation:

| Observed outcome | User-facing meaning and next action |
| --- | --- |
| Not submitted | Nothing was sent; fix the draft or retry submission. |
| Submission outcome unknown | The owner may have accepted it; **Check outcome** reconciles the same operation. |
| Accepted, starting/queued | The owner has acknowledged responsibility; retain the pending row until the run appears. |
| Rejected | Show the owner's reason and preserve the draft. |
| Running, then complete | Show the owner's observed lifecycle and accessible result. |

“Check outcome” is different from “Retry agent,” which creates another execution.
Reconciliation must never silently manufacture a new operation after a lost reply.
Likewise, “Stop accepted” is different from “Stopped.” If no stop was sent because the
host was already unavailable, say so; if delivery is uncertain, retain that uncertainty.
Do not introduce a new offline action queue that executes later without fresh intent.

### Machines have one persistent home

Add a Machines pane to Admin Center, modeled on its Projects inventory. Include Here
and enrolled origins, health, last successful observation, eligibility/capabilities,
available capacity information, and Connect, Check status, Repair, Rename, Remove,
and Show agents actions. A small health shortcut and contextual error links open this
same pane. Enrollment remains accessible when no remote agent exists. [S3](#s3)

Connect is a persistent resumable flow: explain target preparation, show copyable
commands, select a protected bootstrap file, review the target, activate, and verify.
Retain partial-success state and the appropriate recovery step. Removal explains that
it removes this controller's enrollment and does not stop work on the target. Repair
must respect changed installation identity; cached rows cannot be rebound to a different
machine merely because its alias matches. [S5](#s5)[S6](#s6)

Show capacity primarily in this pane and the launch picker. Label it as observed usage
and a configured limit, with age. Logical running-agent counts are not interchangeable
with occupied slots, and stale apparent headroom is not an admission promise. Defer
`%dispatch:auto`, cross-machine queue scheduling, and automatic fallback until explicit
dispatch works well and repeated manual placement demonstrates demand.

## State and implementation boundaries

Keep four independent facts in the presentation: agent lifecycle, connection health,
observation age, and operation certainty. An offline machine may still be executing.
Use “Was running · last seen 12m ago,” retain cached output, and disable only operations
that cannot currently be performed. Do not style stale data as a live guarantee.

Counts must describe their scope. “3 running; mac unknown” communicates more than
“partial”; “showing 20 of 65 matches” is a loaded-page statement, not an activity total.
Coalesce endpoint errors into one incident per machine/cause. Empty results, loading,
unavailable data, and quarantine need different messages beside the affected content,
each with an appropriate recovery action.

Preserve the Rust boundary: owner resolution, pending-attention discovery, identity,
query/count contracts, and durable operation recovery belong in core/gateway with thin
Python adapters. Layout, selection, keybindings, and visual grouping stay in ACE. The
unified list is a viewer projection; it must not recreate the retired agents-sync import
pipeline. [S5](#s5)[S7](#s7)

Performance follows data demand rather than Follow status: immediate local paint,
cached remote projection, independent per-host reconciliation, paged catalog/history,
and debounced selected-content hydration. No fixed three-page ceiling that makes later
results unreachable. Preserve selection by stable identity after every async return.
Zero enrolled machines must start no federation worker, provider import, remote timer,
or network request. Retain the existing `j`/`k` p95 target below 16 ms. [S7](#s7)

## Adoption and validation

First finish the existing epic's live protocol/recovery acceptance work. Design and
prototype the unified surface alongside it; do not spend effort perfecting disposable
Focus/Fleet chrome. Then land shared origin/project projection and complete attention
discovery, followed by one list, unified actions, Machines, and the launch target/source
presentation. Replace synthetic fixtures with real serialized contract fixtures before
using screenshots as acceptance evidence. [S5](#s5)

Preserve Follow data and explicit tombstones during migration. They must stop controlling
list membership or pending attention. Do not infer notification muting from unfollow:
the old choice expressed visibility intent. Explain the change once and retain existing
explicit notification preferences. If users later need a curated working set, extend
the shared pin/query mechanism across machines before adding another remote-only class.

Validate with SASE users unfamiliar with the dispatch implementation:

| Task or fault | Required observable result |
| --- | --- |
| A directly launched, unfollowed remote agent asks while ACE shows Artifacts and a Here-only saved query | A durable global attention entry appears without visiting Fleet, changing filters, or loading its catalog page. |
| Find SASE work across machines, then isolate Apollo | Real project grouping and machine filtering compose; returning restores navigation state. |
| Browse identical agent names on two machines; rename one machine | Selection remains stable and actions reach the correct owner/instance. |
| Launch from a dirty checkout or with local attachments | Explain the specific source constraint before sending; keep the draft. |
| Lose a launch or stop reply; restart ACE | Show uncertainty, reconcile the same operation, avoid a duplicate run or false success. |
| Another controller answers a gate while its modal is open | Explain settlement/revision conflict; never apply the stale decision. |
| One host hangs during navigation and paging | Local interaction remains responsive, healthy hosts update, missing coverage stays explicit. |
| Connect a first machine or repair partial enrollment | Complete through persistent guidance without remembering a vanished toast. |

Record completion rate, time to the first correct action, wrong-host attempts, and
whether users can explain unknown state and retry semantics. Include 82×28 and wider
layouts, monochrome rendering, family handoffs, later catalog pages, and a large recent
history. A short single-user study can identify failures; it cannot establish broad
statistical superiority. Reconsider the default view if bounded remote activity still
overwhelms daily work.

## Provenance and source map

Exactly one A and one B matched the registered dependency names and canonical suffixes.
Both were read through `sase artifact read` before moving only their copies in this
turn's opened research checkout. Their bytes were preserved; other workspaces and
immutable snapshots were not modified. No predecessor chat transcripts were read.

| Dependency | Original canonical reference | Preserved file / immutable snapshot |
| --- | --- | --- |
| `research.1q.cdx` | `research:202609/unified_remote_agent_control_ux__a.md` | [A](agents_across_machines__a.md); `file:explicit:512fb659d2c014d77d27a6e8` |
| `research.1q.cld` | `research:202609/remote_agents_are_not_a_place__b.md` | [B](agents_across_machines__b.md); `file:explicit:bfb8af43d1e4bfa8909eec46` |

SHA-256: A `81a9fa4adf11459dbe664fee94a63081fcc43f4c2ae57e28da2596fedb0f828d`;
B `4a4f19eead15af28cbef62024bbb74d0223e3946d8c4fb24b93e3c196c49e0fc`.

The following source links identify inspected revisions, not live deployments:

- <a id="s1"></a>**S1 — List and scope:** [Fleet projection/refresh](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/actions/agents/_fleet.py),
  [load/apply boundary](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/actions/agents/_loading_apply.py),
  [remote row construction](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/models/_fleet_agents_rows.py),
  [query fields](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/agent_query/tokenizer.py).
- <a id="s2"></a>**S2 — Attention/actions:** [remote attention](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/actions/agents/_remote_attention.py),
  [notice ledger](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/dispatch/attention_notices.py),
  [content selection](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/actions/agents/_remote_content.py),
  [default bindings](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/default_config.yml).
- <a id="s3"></a>**S3 — Corrected claims and existing UI:** [execution types](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/core/agent_types.py),
  [footer labels](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/widgets/_keybinding_bindings.py),
  [Admin Center catalog](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/ace/tui/modals/config_center_catalog.py).
- <a id="s4"></a>**S4 — Core contracts:** [gateway attention read and empty-request test](https://github.com/sase-org/sase-core/blob/86077c6e5adf6d66f0351736940f33651089e98c/crates/sase_gateway/src/routes.rs),
  [bounded catalog/batch and summary wire](https://github.com/sase-org/sase-core/blob/86077c6e5adf6d66f0351736940f33651089e98c/crates/sase_core/src/fleet_contract.rs).
- <a id="s5"></a>**S5 — Audited artifacts:** `bead:sase-xe`, `bead:sase-xe.16.11`,
  `plan:202609/remote_dispatch_fleet.md`, `plan:202609/fleet_ui.md`, and the
  [original consolidated research](../remote_dispatch_and_fleet_focus/remote_dispatch_and_fleet_focus.md).
  `sase bead show sase-xe.16` supplied additional current lifecycle context.
- <a id="s6"></a>**S6 — Launch/setup constraints:** [runbook](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/docs/remote_dispatch.md),
  [launch validation and durable intent](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/dispatch/launch.py),
  [mutation intent](https://github.com/sase-org/sase/blob/63ec413b60492082e0a7a95e142417d74e05150b/src/sase/dispatch/mutations.py).
- <a id="s7"></a>**S7 — Audited memory:** `tui_perf.md`, `decisions:rust-core-required`,
  `decisions:agents-sync-publish-only`, and `glossary:agent-family`; ACE's local
  `AGENTS.md` supplied the conditional-footer convention.

## Recommended UX

**Ship one Agents experience across machines.** Keep projects and families as the
working structure; make machine a visible attribute, a simple filter, and an optional
grouping. Default to active and recent work from all enrolled origins. Preserve a quiet
Here-only or saved-query view without making remote work a different class of agent.

**Do not support Focused/Unfocused remote agents as user-facing states.** Make all
authorized pending questions and gates discoverable through the existing durable
attention inbox, regardless of browsing scope, loaded pages, or subscriptions. Preserve
old follow data during migration; add Watch only if routine notification volume proves
that users need it.

**Use familiar actions with explicit ownership.** Put machine administration in
Admin Center → Machines, make launch target and source revision visible, and distinguish
unavailable observations from failed executions and uncertain operations. Show capacity
to inform explicit placement; keep automatic scheduling separate. This gives users a
single place to manage their work while keeping the consequences of remote execution clear.
