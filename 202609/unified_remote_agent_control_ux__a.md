# Remote Agent Control in `sase ace`

## Executive decision

The current Focus/Fleet design should not be polished into permanence. It encodes two
overlapping, asymmetric sets:

- Focus = every local agent plus followed remote agents.
- Fleet = every visible remote agent but no local agents.

That is difficult to predict, makes location determine visibility, and allows an
unfollowed remote agent that needs input to disappear from the user's normal working
surface. It also creates a second navigation concept, two ambiguous counts, durable
follow state, family-promotion rules, and a parallel set of remote commands merely to
answer a basic question: “What work needs me, and what can I do to it?” The complexity
is disproportionate for a personal fleet likely to contain a handful of machines.

The strongest design is:

1. **One Agents list across the current machine and every enrolled machine.** Remote is
   provenance, not a mode.
2. **One orthogonal machine scope:** `All`, `Here`, or a named machine. The default after
   enrollment is `All`; local rows paint immediately and cached remote rows reconcile
   asynchronously.
3. **No user-facing Focused/Unfocused remote-agent classes in v1.** Every pending
   question or gate surfaces regardless of subscription state. If notification volume
   later proves to be a problem, introduce **Watch** as a notification/retention
   preference that never controls visibility or permissions.
4. **The same actions for local and remote rows.** Stop, retry, fork, open output, and
   answer should route by the selected row's owner and capabilities. Do not make users
   discover a second “remote” command vocabulary.
5. **A persistent Machines surface** for enrollment and health, opened from a compact
   top-bar indicator or command palette. Setup instructions and unresolved failures do
   not belong in expiring toasts.

Keep `%dispatch:<machine>` as the scriptable routing syntax, but add a visible launch
target selector in the TUI so users do not have to remember or inspect prompt text to
know where a run will start.

## Scope, evidence, and confidence

This assessment covers information architecture, terminology, navigation, agent
visibility, attention, action discovery, machine setup, offline behavior, and launch
routing in the `sase ace` TUI. It does not redesign the transport or mutation journal.
Those foundations—owner-resolved identities, bounded reads, exact-instance mutations,
and no silent local fallback—remain sound.

The internal baseline is SASE commit
`7a4fb2149a1d308299d968f0f3d7c477c72dbaec`, the `sase-xe` epic and its active
completion descendants, the remote-dispatch plan, user documentation, source code, and
the committed 120×40 and 82×28 Fleet/Focus visual fixtures.[^1][^2][^3] External evidence
comes from comparable remote-development, resource-inventory, subscription, fleet
health, terminal-framework, notification, and accessibility patterns.[^5][^6][^7][^8]

Confidence is high in the information-architecture recommendation and moderate in the
exact row density and key choices. There has been no direct usability study with SASE
users. More importantly, the active completion epic records that live Fleet contracts,
pagination, counts, launch recovery, and the Athena-to-Apollo acceptance path are still
incomplete. The attractive snapshots are synthetic and should be treated as layout
evidence, not proof that the actual workflow works.[^4]

## What the current design asks users to learn

### The set algebra is not natural

The implementation makes `focus` and `fleet` the only two modes. Fleet returns cached
remote catalog rows; Focus concatenates the complete local list with only followed
remote rows.[^2] This relationship is neither a clean partition nor a simple subset:

| Agent | Focus | Fleet |
| --- | :---: | :---: |
| Local, any state | Yes | No |
| Remote, followed | Yes | Yes |
| Remote, not followed | No | Yes |

“Focus” therefore does not mean focused work consistently—local terminal history is
included whether important or not. “Fleet” does not mean the fleet consistently—the
current machine is excluded. A user cannot infer membership from the labels without
learning an implementation rule.

The mental-model problem becomes sharper from another controller. The same logical
agent may be “local” in one ACE and “remote” in another, while its importance does not
change. Location is a property of an agent relative to the viewer; it should not define
the primary navigation.

### Follow currently gates attention, not merely clutter

The refresh path asks for followed logical keys and then makes attention requests for
those keys. Unfollowed remote work is absent from Focus and is not part of that bounded
attention fetch.[^2] This turns Follow into a safety-critical responsibility assignment:
failing to follow the right row can hide a remote question or gate.

That is too much semantic weight for a star whose meaning is not visible in the main
footer. A personal control plane should fail toward showing work that needs the owner,
not toward silence. Enrollment already defines the trusted machine set. Pending human
attention within that set should pierce ordinary filters and subscription preferences,
just as local attention does.

### The visible action model does not match the promised parity

All nine added Fleet/remote keymap entries ship as `unbound`, including mode switching,
follow, machine status, retry, remote content, and remote attention.[^2][^3] The visual
fixture with a remote question selected still shows the normal local-oriented footer.
The user guide instructs users to open the command palette or configure keymaps before
using the feature.[^3]

The command palette is a good secondary access path, and Textual explicitly supports
commands scoped to the active screen. Textual's footer is designed to show bindings
available for the focused widget.[^9] But a core workflow is not discoverable when:

- the selected object visibly looks actionable;
- the footer advertises irrelevant local actions;
- the relevant commands have no defaults; and
- the documentation is the only place that explains this.

The source also exposes separate action names such as `retry_remote_agent` and
`view_remote_agent_content`. That is an implementation distinction leaking into the
interaction model. “Retry” should mean retry, with origin routing below the UI.

### Machine management is an expiring instruction, not a surface

With no machine enrolled, the Focus/Fleet strip is hidden. A command-menu action was
added after the original implementation left no in-TUI route to setup. It now emits a
12-second toast containing a multi-machine, multi-command bootstrap procedure. When
machines exist, the “machine” action merely toasts the selected alias and health; the
setup action tells the user which shell commands to remember.[^2]

This is a mismatch between component and task. Transient messages are appropriate for
low-priority feedback after an action. Material and Carbon guidance both reserve
persistent or actionable UI for tasks, errors, and instructions that a user must act
on; Carbon specifically recommends a persistent destination when users need to revisit
notifications.[^10] Enrollment is a multi-step task with secrets, verification, and
recoverable partial failure. It needs a durable modal/pane, copyable commands, progress,
and a resume path.

### The current header reports implementation state, not user state

The current strip can render `Focus 4`, `Fleet 3`, and `3 issues · partial` while the
existing Agents summary immediately above reports lifecycle counts. In the visual
fixture, `Fleet 3` is three catalog rows, not three running agents. The projection's
fallback values likewise use local row count, followed-row count, and Fleet-row count.
The word “partial” does not identify what is unknown.[^2]

One fixture deliberately appends the same host warning from summary, catalog, and
followed responses, then asserts three identical diagnostics. The screenshot therefore
shows “3 issues” for one underlying host condition.[^2] This is partly a contract bug,
but it reveals a UX rule worth making explicit: aggregate incidents by machine and
cause, not by transport call.

Useful operator questions are different:

- How many agents need me?
- How many are running or queued?
- Which machines are unavailable, and how old is their last trustworthy state?
- Is a dispatch accepted, uncertain, or rejected?

Membership totals are secondary and should not compete with those answers.

### Location and project are conflated

Remote row construction currently sets `project_display_name` to the machine alias and
uses a synthetic `/fleet/<machine>/project.yml` path. The visible machine grouping works
only by spending the project field.[^2] Meanwhile, the existing agent query language
offers `status`, `project`, `name`, `model`, `provider`, `attention`, and other fields,
but no `machine`, `location`, or followed/watch field.[^2]

Machine and project are independent dimensions. An agent can be “SASE on Apollo”; users
need both, and may want to group by project while filtering to Apollo—or group by
machine while searching a project. A first-class `machine:` facet is cleaner than a
special mode and fixes the data model at the same time.

## Lessons from comparable products

These products are not direct templates; SASE's terminal density and agent-family model
are distinctive. They are useful evidence about which concepts deserve primary
navigation.

### Remote location works well as persistent context

VS Code keeps the normal editor experience when connected remotely. A status-bar item
shows whether the current context is local or remote, names the host, and opens remote
commands when selected.[^5] This is a strong analogy for a SASE machine indicator: keep
the work surface stable, make execution context continuously visible, and put machine
operations behind that visible context.

SASE differs because one list can contain objects from several hosts simultaneously.
The implication is not “copy the status bar exactly”; it is “show host identity on each
object and provide one persistent machine control,” rather than creating a second kind
of agent browser.

### Large inventories use scope and filters over one resource model

Azure's All Resources surface spans subscriptions and lets users combine filters,
search text, columns, and saved views.[^6] Kubernetes Dashboard keeps workloads in the
same resource views and changes scope with a namespace selector.[^7] Both patterns treat
topology as a scope over resources rather than as a second resource ontology.

SASE does not need Azure-level customization in v1. It does need the same separation of
concerns:

- Agents are the resources.
- Machine is a facet and possible scope.
- Project, lifecycle, attention, model, and age remain independent facets.
- A saved or remembered scope is a view preference, not a property of an agent.

### Watching is a notification preference

GitHub describes watching as subscribing to updates and allows users to customize which
events produce notifications.[^8] Watching does not remove unwatched repositories or
issues from search and browsing. That distinction is valuable for SASE: if an explicit
subscription feature is eventually needed, call it Watch and let it control routine
notifications or retention—not catalog membership, action permissions, or the
visibility of pending human attention.

This terminology also avoids overloading “follow,” which SASE already uses for family
successors, link navigation, gate follow-ups, and monitor follow-ups.

### Fleet status is categorical and filterable

Grafana Fleet Management exposes health in the inventory, distinguishes healthy,
warning, unresponsive, error, and unknown/unavailable states, and supports status
filtering.[^11] SASE likewise needs to separate agent lifecycle from machine connection
health and observation freshness. A remote agent is not simply RUNNING when its host is
offline; it is “was running, last observed 12m ago.”

### Critical meaning needs text or shape, not color alone

The existing filled/outlined star is better than a color-only distinction. W3C guidance
requires another visible cue when color conveys state.[^12] The recommended design
extends that rule to location, attention, stale state, and disabled actions: use text or
stable glyphs alongside color, especially in monochrome terminals.

## Alternatives considered

The scores below are analytical judgments on a 1–5 scale, not usability-test results.
They make the trade-offs explicit.

| Option | Mental model | Attention safety | Discovery | Scale | Local continuity | Action clarity | Overall |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Keep Focus/Fleet + Follow | 2 | 2 | 2 | 4 | 4 | 2 | 2.6 |
| Rename to Here/Remote tabs | 3 | 2 | 3 | 4 | 4 | 3 | 3.1 |
| One cross-machine list + scope | 5 | 5 | 5 | 4 | 4 | 5 | **4.7** |
| Separate Agents and Machines browsers | 3 | 3 | 4 | 5 | 3 | 4 | 3.6 |

### Keep Focus/Fleet

This has the lowest implementation disruption and a potentially quiet local default.
It preserves the strongest prior rationale: a user-chosen working set can avoid a huge
remote catalog. But that benefit can be achieved with bounded default eligibility,
scope, and filters without teaching overlapping sets. The approach also makes a
hypothetical scale problem determine today's default UX.

### Here/Remote tabs

These labels are easier to predict because the sets are disjoint. They still force
users to switch views to discover attention on the other side, and “remote” changes
with the viewer. This is useful as a quick scope shortcut, not as primary navigation.

### One list plus machine scope

This is the clearest task model: users manage agents; the system routes operations to
their owners. It requires a real cross-host working-set query and careful nonblocking
merge behavior, but the remote facade and existing list pipeline were built for that
composition. It also makes the current machine an honest member of the fleet.

### Separate Machines browser

A machine inventory is valuable for enrollment, repair, and health. It is not a good
primary place to manage agents because users would drill into a host before seeing which
work needs them. Use it as a supporting modal or Admin Center pane, linked bidirectionally
with the unified Agents list.

## Should SASE support Focused and Unfocused remote agents?

**Not as first-class user-facing states.** The binary is solving three different
problems at once:

1. limiting remote network hydration;
2. deciding which rows appear in the ordinary list; and
3. deciding which work can notify the viewer.

Those policies should be independent.

### Hydration

Use demand tiers and bounded endpoints. The initial cross-machine request should return
only attention, active/queued/uncertain work, watched terminal work if Watch exists, and
a small recent window. History grows on demand. This controls cost without hiding
active responsibility behind a star.

### Visibility

Default to a cross-machine working set. Machine scope and query filters control what is
shown. Pending input may appear in a small “Needs you” band above filtered results so it
cannot be silently excluded; the band must show the machine and why it pierced the
filter.

### Notification preference

Do not expose one initially. Auto-surface all pending attention from enrolled machines
while ACE is open. Existing notification deduplication prevents reconnect spam. If
real-world use later produces too much routine noise, add `Watch` with these rules:

- dispatched work is auto-watched by the launching controller;
- users may watch work discovered elsewhere;
- Watch controls routine state-change notifications and how long terminal work remains
  prominent;
- pending questions, gates, dispatch uncertainty, and destructive-operation outcomes
  remain visible regardless of Watch;
- Watch applies equally to local and remote agents if it becomes a general concept;
- unwatching never changes ownership, visibility eligibility, or permissions.

The current follow store can be migrated to Watch without data loss: active follows
become watched records; tombstones suppress future automatic watching but no longer
exclude rows. This preserves durable user intent while removing it from navigation.

## Recommended information architecture

### Top level

Keep the existing `Agents | Artifacts | AXE` top-level tabs. Remove the Focus/Fleet
subtab strip. Add a compact machine indicator to the top bar:

```text
Agents | Artifacts | AXE                 @athena  Machines 2/3 ⚠
```

`@athena` makes the controller identity visible. `Machines 2/3 ⚠` means two of three
known machines are currently reachable; it opens the Machines surface. When no remote
machine is enrolled, the indicator can read `@athena · Connect` or remain `@athena`
with a visible Connect command in the command palette and Agents quick-start panel.
Reading config to render it must retain the existing zero-network, zero-worker startup
contract.

### Agents header

Use one scope control and one operational summary:

```text
scope: All machines ▾        1 needs you · 3 running · 1 queued · mac unknown
```

The scope choices are:

- `All machines` — local plus enrolled machines; default after the first enrollment.
- `Here (@athena)` — only agents owned by the controller.
- one entry per enrolled alias — `apollo`, `mac`, and so on.

The active scope is always visible. The selector can be opened by mouse, command
palette, or a configurable default shortcut. A remembered scope is fine, but a query
that contains pending attention outside that scope should produce a visible off-scope
attention indicator rather than silence.

### Agent rows

Machine is a dedicated field, not a substitute for project:

```text
┌ Needs you ──────────────────────────────────────────────────────────────┐
│ ! remote-auth-fix  sase   QUESTION   @apollo   fresh    Approve policy │
└────────────────────────────────────────────────────────────────────────┘

  local-plan         sase   RUNNING    @here      2m     Draft migration
  queue-window       sase   QUEUED     @apollo    38s    Review queue
  cached-ci          tools  WAS RUNNING @mac   seen 12m  Check flaky CI
```

Priority order should be:

1. pending human attention and uncertain destructive/dispatch outcomes;
2. starting, queued, running, and stopping work;
3. watched terminal work, if Watch is later introduced;
4. bounded recent terminal history.

Preserve existing group/family/tribe hierarchy. Project remains project. Add
`machine:<alias|here>`, and optionally `watched:true`, to the query language. Allow
grouping by machine, but do not force it; a cross-machine project group is often more
useful for a developer following one codebase.

At narrow widths, retain status, machine, and freshness before model or intent. Use
plain labels or stable glyphs (`!`, `?`, `~`) as well as color. Do not use an outlined
star on every unwatched row; absence of an optional preference should be visually quiet.

### Detail pane

The detail header should always show:

- logical agent/family name;
- project;
- owner machine and connection state;
- observation freshness;
- exact action state when a mutation or dispatch is pending.

For example:

```text
remote-auth-fix · sase · @apollo
QUESTION · observed now · target online
```

When the target is unreachable:

```text
cached-ci · tools · @mac
WAS RUNNING · last observed 12m ago · target offline
```

This is more honest than leaving the agent's lifecycle styled as currently running
beside a dim `offline` token.

### Machines surface

Open a modal or Admin Center pane from the machine indicator:

```text
Machines
> athena   HERE    online       2 running
  apollo   REMOTE  online       1 running · fresh
  mac      REMOTE  offline      last seen 12m · counts unknown

Enter: show agents   C: connect   R: rescan/status   E: repair   X: remove
```

This surface owns:

- current and enrolled machine inventory;
- reachability, protocol/capability, freshness, and count summaries;
- connect/discover/init progress;
- quarantine/identity-mismatch repair;
- rename and remove;
- a direct “Show agents on this machine” action that applies the Agents scope.

The first-time Connect flow should be a persistent wizard/checklist with copyable
target and controller commands, bootstrap-file selection, progress, and recovery from
partial success. If the TUI cannot perform a step, it should say so in place and retain
the command after focus changes. A success toast may confirm completion; the toast must
not be the procedure.

## Interaction model

### Launching

Keep `%dispatch:apollo` in the CLI and xprompt language. In ACE, render the parsed
target as an explicit prompt-bar chip or selector:

```text
Target: here ▾   Prompt: ________________________________________________
```

Choosing Apollo inserts or updates the `%dispatch:apollo` directive in the underlying
prompt, so the visible control and portable syntax remain one source of truth. Reset the
selector to `here` for a fresh prompt unless the user explicitly configures a default;
remote execution is consequential enough not to become an invisible sticky mode. The
picker should show cached eligibility and health, but submission remains authoritative.

After submit, put a pending row in the unified list immediately:

```text
dispatch.auth   sase   DISPATCHING?   @apollo   checking outcome
```

Use distinct `unsent`, `submitted/uncertain`, `accepted/queued`, and `rejected` states.
Do not label an uncertain request failed while reconciliation could still discover the
admitted run.

### Acting on a row

Reuse the ordinary verbs and keys:

- the existing Stop/Kill action routes to local process control or remote journaled
  stop based on owner;
- Retry preserves the owner by default and names it in confirmation/result copy;
- Fork defaults to the selected agent's owner, with any future “fork here” as an
  explicit alternative;
- Open output/chat/diff hydrates local files or remote content handles through the same
  visible action;
- Answer/Approve consumes the exact pending request whether local or remote.

The footer must change with selection and display the available common actions. The
command palette should show the same verbs and either omit unsupported actions or show
them disabled with a concise reason. Do not ship the primary remote path entirely
unbound. Exact keys should follow a conflict audit, but the goal is to reuse existing
local bindings rather than add nine more.

Every consequential confirmation and result includes the owner alias: “Stop
`remote-auth-fix` on Apollo?”; “Stop accepted on Apollo”; “Apollo is offline; stop was
not queued.” Remote destructive work must never be queued for surprise execution after
reconnection.

### Attention

The cross-machine summary request should return all pending questions/gates (or bounded
IDs sufficient to fetch them), not only followed keys. Insert new attention into the
current Agents list and increment the existing notification indicator. If the Agents
tab is already showing that row, update it without a redundant toast. Notification
guidance favors discoverable in-place updates while an application is foregrounded and
deduplication of repeated notifications.[^13]

An attention row outside the selected machine scope appears in a small global band or
as `1 need outside scope`, with one action to reveal it. Scope is a browsing preference,
not permission to strand a gate.

### Offline and partial state

Treat four dimensions separately:

| Dimension | Example |
| --- | --- |
| Agent lifecycle | running, done, question, queued |
| Machine connection | online, reconnecting, offline, quarantined |
| Observation freshness | now, 12m old, never observed |
| Operation certainty | none, pending, uncertain, accepted, rejected |

Rows remain in place when a host disconnects, but live actions disable with reasons.
Summaries should say `3 running + ? on mac` or `3 running · mac unknown`, not merely
`partial`. A persistent inline warning such as `mac offline · showing data from 12m ago`
opens the Machines surface. Aggregate duplicate endpoint errors into one incident keyed
by machine and cause; retain technical request diagnostics in detail/log views.

## Performance implications

A unified list does not require eager fleet history. The default server-side query can
be smaller than the current Fleet catalog:

```text
pending attention
OR active/queued/dispatch-uncertain
OR watched recent terminal (if Watch exists)
OR most-recent N terminal per fleet
```

Apply these constraints:

- local rows paint from the current direct/index path without waiting for any network;
- cached remote rows paint next;
- live reconciliation occurs asynchronously with per-host deadlines and cancellation;
- a hung host cannot delay another host or `j`/`k` paint;
- machine scope pushes down to the federation query;
- history and content paginate/hydrate on demand;
- exact counts come from authoritative summaries, not loaded rows;
- an empty machine registry starts no worker, imports no provider, schedules no remote
  timer, and performs no network I/O.

The result is a unified experience without an unbounded initial query. The current
three-page client cap and live contract mismatch should be repaired before using the
existing snapshots or benchmarks to set UX policy.[^4]

## Migration from Focus/Fleet

### Stage 1: make the live contract trustworthy

Finish the active `sase-xe.16.11`/child work: real worker envelopes, pagination,
authoritative counts, per-host freshness/errors, dispatch recovery, exact remote
identity, and live Apollo acceptance. Preserve current Focus/Fleet presentation until
those rows are reliable. Otherwise a redesigned surface will mask protocol defects with
new fixtures.

### Stage 2: create one projection

Replace `focus_rows` and `fleet_rows` with a single owner-qualified working-set
projection. Keep separate local and remote loaders internally, but merge before the
ordinary filter/group/render pipeline. Add first-class project and machine fields rather
than synthetic paths and alias-as-project.

### Stage 3: replace modes with scope

Remove the subtab strip and mode cycling. Add the visible `All / Here / machine` scope
control and `machine:` query support. Start with `All` as the default after enrollment;
allow a user preference for `Here` if field usage shows that cross-machine work is too
noisy.

### Stage 4: unify actions and machine management

Route existing action IDs by owner, delete user-facing `*_remote_agent` duplicates,
make the footer contextual, and add the Machines surface. Convert long setup and
persistent failure toasts into durable UI. Keep operation keys, capability checks,
fencing, and remote confirmations underneath.

### Stage 5: retire or reinterpret Follow

Stop using follows for list membership and attention visibility. Initially retain the
store for backward compatibility while treating active records as an internal Watch
preference. Do not expose Watch until there is evidence of notification overload or a
clear terminal-retention use case. Document the migration and ensure unfollow
tombstones cannot hide active or attention-bearing work.

## Validation plan

The next acceptance pass should measure user comprehension, not only screenshot
stability and frame latency. Test at least these tasks with participants who know SASE
but have not memorized the remote-dispatch design:

1. Find every agent currently awaiting input across three machines.
2. Determine where a selected agent is running and whether its state is fresh.
3. Stop an active Apollo agent and explain what will happen if Apollo disconnects.
4. Retry a completed remote agent on its owner.
5. Show only agents on the current machine, then only agents on Mac.
6. Connect a first remote machine starting from ACE.
7. Diagnose an identity mismatch and resume enrollment.
8. Launch to Apollo without typing `%dispatch`, then inspect the generated prompt
   directive.

Record task completion, wrong-host or wrong-action attempts, time to first correct
action, help/palette use, and answers to these comprehension questions:

- Does “All” include this machine?
- Will an unwatched agent that asks a question still appear?
- Does offline mean the remote process stopped?
- Are the displayed running counts complete?
- Will a failed-looking dispatch be retried automatically as a new run?

Performance acceptance remains necessary: local first paint must not regress; `j`/`k`
p95 stays within the existing budget during host hangs, reconnect storms, and event
bursts; and the zero-machine path performs no remote work.

## Sources

[^1]: SASE. `bead:sase-xe`, “Remote dispatch and the Focus/Fleet agents experience,” including phases `sase-xe.11`, `.13`, `.14`, and active descendants `.16` and `.16.11`; inspected September 9, 2026. Canonical plan: `plan:202609/remote_dispatch_fleet.md`.

[^2]: SASE source at commit `7a4fb2149a1d308299d968f0f3d7c477c72dbaec`: `src/sase/ace/tui/actions/agents/_fleet.py`; `src/sase/ace/tui/models/fleet_agents.py`; `src/sase/ace/tui/models/_fleet_agents_rows.py`; `src/sase/ace/agent_query/tokenizer.py`; `src/sase/default_config.yml`; `tests/ace/tui/test_fleet_agents.py`; and `tests/ace/tui/visual/snapshots/png/agents_fleet_*.png`.

[^3]: SASE. `docs/remote_dispatch.md`, especially “Launch and TUI workflow,” at commit `7a4fb2149a1d308299d968f0f3d7c477c72dbaec`; inspected September 9, 2026.

[^4]: SASE. `bead:sase-xe.16.11`, notes on incomplete Fleet contracts, counts/freshness/pagination, dispatch recovery, synthetic fixtures, and live acceptance; inspected September 9, 2026.

[^5]: Microsoft. “[Remote development over SSH](https://code.visualstudio.com/docs/remote/ssh-tutorial).” VS Code documentation; accessed September 9, 2026. The remote status item identifies context/host and opens remote commands while the editor experience stays otherwise consistent.

[^6]: Microsoft. “[View and filter Azure resource information](https://learn.microsoft.com/en-us/azure/azure-portal/manage-filter-resource-views).” Azure portal documentation, updated March 3, 2026; accessed September 9, 2026. Documents one All Resources inventory with combinable filters, text search, columns, and saved views.

[^7]: Kubernetes. “[Deploy and Access the Kubernetes Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/).” Updated February 3, 2026; accessed September 9, 2026. Workload views use a namespace selector to change scope.

[^8]: GitHub. “[Configuring notifications](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).” Accessed September 9, 2026. Defines watching as subscription to updates and separates notification preferences from browsing.

[^9]: Textual. “[Command Palette](https://textual.textualize.io/guide/command_palette/)” and “[Footer](https://textual.textualize.io/widgets/footer/).” Accessed September 9, 2026. Textual supports active-screen command discovery, while Footer displays bindings for the focused widget.

[^10]: IBM Carbon Design System. “[Notification usage](https://carbondesignsystem.com/components/notification/usage/).” Updated August 27, 2026; accessed September 9, 2026. Distinguishes transient toasts from persistent inline/actionable/callout UI and recommends a durable destination for revisiting notifications. See also Material Design, “[Snackbars](https://m2.material.io/go/design-snackbar),” accessed September 9, 2026.

[^11]: Grafana Labs. “[Check the status of your fleet](https://grafana.com/docs/grafana-cloud/observe-and-act/send-data/fleet-management/manage-fleet/collectors/collector-status/).” Accessed September 9, 2026. Fleet inventory distinguishes health categories, unknown/unavailable state, and status filtering.

[^12]: W3C Web Accessibility Initiative. “[Understanding Success Criterion 1.4.1: Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html).” WCAG 2.2 guidance; accessed September 9, 2026.

[^13]: Apple. “[Notifications](https://developer.apple.com/design/human-interface-guidelines/notifications).” Human Interface Guidelines; accessed September 9, 2026. Recommends high-value concise notifications, avoiding duplicates, and using discoverable in-place updates while the application is foregrounded.

## Recommended UX

Ship one cross-machine Agents experience and retire Focus/Fleet as user-facing modes.
The default list should contain local and remote attention, active/queued work, and a
bounded recent history, with a visible `All / Here / <machine>` scope and a first-class
machine field on every remote row. Pending questions, gates, and uncertain operations
must surface from every enrolled machine regardless of any subscription preference.

Do not support “Focused” versus “Unfocused” remote agents in v1. Preserve the existing
follow data only as migration input for a possible future **Watch** preference. If Watch
is eventually exposed, it should control routine notifications and terminal prominence,
never catalog visibility, attention visibility, ownership, or permissions.

Give local and remote agents the same visible verbs and shortcuts; route by owner below
the UI and state the machine in consequential confirmations. Add a persistent Machines
surface for connect, health, repair, and “show this machine's agents.” Keep
`%dispatch:<machine>` as the power-user contract, but mirror it with an explicit TUI
target selector. Report actionable state—`needs you`, `running`, `queued`, exact host
unknown, freshness, and dispatch certainty—instead of overlapping membership counts and
the generic word `partial`.

The implementation order should be: finish the live protocol/acceptance repair; build a
single owner-qualified projection; replace modes with machine scope; unify actions and
add Machines; then validate the redesign with task-based usability tests and the
existing performance fault matrix.
