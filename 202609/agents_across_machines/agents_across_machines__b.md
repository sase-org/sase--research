---
create_time: 2026-09-09
updated_time: 2026-09-09
status: research
---

# Remote Agents Are Not A Place: A UX Rethink For The `sase ace` Agents Tab

**Research question:** where and how should remote-dispatch agents appear in the `sase ace`
TUI, are the shipped UX choices right, and is the "Focused vs Unfocused" (followed vs
unfollowed) remote-agent distinction worth supporting at all?

**Scope and method:** independent researcher B. Read at `sase` master `7a4fb2149`. Primary
sources: epic `sase-xe` and its 12 notes, child epic `sase-xe.16` and its 3 notes, the
accepted plans `plan:202609/remote_dispatch_fleet.md` and `plan:202609/fleet_ui.md`, the
shipped ACE fleet code (`src/sase/ace/tui/actions/agents/_fleet.py`,
`_remote_lifecycle.py`, `_remote_attention.py`, `_remote_content.py`,
`src/sase/ace/tui/models/_fleet_agents_*.py`), the Agents list renderer, the command
availability table, the agent query tokenizer, the grouping mixin, the Admin Center
catalog, `src/sase/default_config.yml`, `docs/remote_dispatch.md`, and the four committed
Fleet/Focus PNG snapshots under `tests/ace/tui/visual/snapshots/png/`, which I read as
images rather than as byte fixtures. Prior consolidated research
(`research:202609/remote_dispatch_and_fleet_focus/remote_dispatch_and_fleet_focus.md`)
was read to establish the original design rationale I am arguing against; I did not
consult researcher A's peer report.

Live state sampled: one enrolled machine (`apollo`, `builtin@tailnet`,
`https://apollo.tail297af1.ts.net`); `max_running_agents: 10`; three tailnet machines
total (`athena`, `apollo`, `mac`) per the host project's core memory.

## Answer in brief

**The Focus/Fleet sub-tab axis is the wrong shape and should be deleted.** It models
*location* as a *place you navigate to*, and then has to invent a second concept
("Follow") to claw back the attention scoping it destroyed by doing so. The Agents tab's
organizing question is "what needs me?" — location is an attribute of an agent, like its
project, model, or tribe. Attributes belong in the row, the filter, and the grouping key,
not in a mode switch.

Concretely: one Agents list containing every machine's agents; `machine:` added to the
agent query language; `by machine` added to the existing `o` grouping cycle; the durable
follow store retained but reframed as a **notification subscription** managed by the
existing mute/snooze machinery rather than as a view; machine *management* moved into the
Admin Center as a **Machines** pane beside Projects; and per-machine **runner capacity**
promoted to a first-class fleet concept so `%dispatch` finally composes with `%queue`.

That is a drastic change, and I think the evidence supports it: the shipped design
bolts remote rows onto the outside of the exact pipeline (filter, fold, dismiss,
notification) that gives the Agents tab all of its power.

---

## 1. What actually shipped

The Focus/Fleet design in `plan:202609/remote_dispatch_fleet.md` is not what landed. Ten
findings, each independently verifiable.

### F1. The machine alias is stored in the row's *project* field

`src/sase/ace/tui/models/_fleet_agents_rows.py:189` sets
`project_display_name=host_alias`, and line 172 sets a synthetic
`project_file=f"/fleet/{host_alias}/project.yml"`. The real project the remote agent is
working on is discarded from the grouping axis.

This is the single deepest modeling error in the feature, and it is visible in the
narrow-width snapshot (`agents_fleet_keyboard_focus_narrow_82x28.png`): under group
`@default`, the machine `apollo` sits at exactly the same structural level as the real
project `sase`. Consequences:

- `group by project` — the Agents tab's default grouping — is meaningless for remote rows.
- Two agents on the same project running on two different machines can never group
  together, so the most natural fleet question ("what is happening on project X across
  all my machines?") is unanswerable in the UI built to answer fleet questions.
- Project accent colors, project filters (`project:` in the query language), and
  project-scoped actions all silently mean "machine" for half the list.

Everything else in this section is a symptom; this is a cause.

### F2. Remote rows bypass the filter/fold pipeline entirely

`src/sase/ace/tui/actions/agents/_loading_apply.py:402` calls
`_project_agents_for_current_mode_after_load(...)` **after** the fold boundary has already
produced `visible_agents`. The mixin (`_fleet.py:180-190`) then appends
`_agents_fleet_focus_rows` to both the unfiltered and the visible list.

So remote rows are not subject to the agent search query, the hide/dismiss rules, or the
fold boundary's counts. Grouping and rendering do run over the merged list afterwards, so
the list *looks* integrated while behaving as a second, unfiltered stream. Typing a search
query narrows local agents and leaves every followed remote row pinned in place. No test
in `tests/` covers filtering of fleet rows.

### F3. Every fleet keybinding shipped unbound

`src/sase/default_config.yml:520-527`:

```yaml
cycle_agents_subtab: "unbound"
cycle_agents_subtab_reverse: "unbound"
toggle_agent_follow: "unbound"
view_agent_in_focus: "unbound"
connect_agent_machine: "unbound"
setup_agent_machine: "unbound"
retry_remote_agent: "unbound"
view_remote_agent_content: "unbound"
answer_remote_attention: "unbound"
```

Nine actions, zero default keys. The runbook states this as intended
(`docs/remote_dispatch.md:238`: "The Focus/Fleet actions ship unbound"). The entire
feature is reachable only by mouse or command palette. In the snapshots, the keybinding
footer shows only local verbs (`enter go to PR`, `~ neighbor`, `A auto-approve`,
`r retry`, `h parent tribe`, `x dismiss`) even while the Fleet view is active — the
footer, which is the app's primary discovery surface, never mentions the mode it is in.

I read this as the strongest available signal that the design was not finished: a
keyboard-first TUI that cannot express its newest feature on the keyboard has not decided
what that feature is for.

### F4. Remote attention is fetched only for *followed* rows

In `_fleet.py:313-321`, the `attention` call is issued with
`followed_logical_keys(follow_snapshot)`. An unfollowed remote agent that asks a question
or opens a gate produces no `QUESTION`/`WAITING INPUT` distinction and no notice at all;
it falls back to the generic `needs_attention` → `WAITING INPUT` mapping
(`_fleet_agents_rows.py:294-296`) with no answerable payload.

This inverts the value proposition. The catalog view exists so you can see work you are
not already tracking — and it is precisely that work whose "I need you" signal is
suppressed.

### F5. Remote attention does not enter the notification system

`_remote_attention.py:82` terminates in `self.notify(...)` — a transient toast. Grepping
`src/sase/ace/tui/actions/agents/_notification*.py` (26 modules) for `remote`, `fleet`, or
`machine` returns nothing. The top-bar `NotificationIndicator` badge (`⚑1 ✉18` in the
snapshots) does not count remote questions or gates; the notification panel has no remote
rows; mute, snooze, bulk marks, tabs, and reclassification
(`notification_modal_mute_actions.py`, `notification_modal_snooze_actions.py`) do not
apply.

A missed toast is a lost signal. For the one job a remote-agent UI must do — tell me when
a machine I am not looking at needs me — the feature currently has no durable surface.

### F6. Remote answering and remote reading are separate worlds

A remote question is answered in a bespoke `RemoteAttentionModal`
(`src/sase/ace/tui/modals/remote_attention_modal.py`, 270 lines) rather than the modal a
local question uses. Remote content opens in a bespoke `RemoteContentModal` rather than
the detail pane or the pager.

Worse, `_remote_content.py:55` takes `raw_handles[0]` — the *first* handle only. The
command is titled "Agents: view remote chat/output/diff content"
(`_app_metadata_nav.py:275-280`) but can only ever open one of them.

### F7. Twenty-one familiar Agents commands vanish on a remote row; two silently change meaning

`_availability_agents.py:54-77` lists `_REMOTE_AGENT_LOCAL_COMMANDS` — 21 commands
disabled when the selection is remote, including `app.open_tmux`,
`app.show_agent_run_log`, `app.toggle_agent_unread`, `app.edit_agent_tribe`,
`app.rename_cl`, `leader.kill_and_edit`, and `leader.revert_agent`.

Meanwhile `app.kill_agent` is rerouted to remote stop and `app.edit_hooks` — bound to `F`
and titled "edit hooks" — is rerouted to remote **fork** (`_availability_agents.py:226`).
The same key does two unrelated things depending on where the selected agent happens to
run, with no label change.

The keyboard becomes mode-dependent on a property the user cannot see without reading the
row carefully. That is the cost of making location invisible in the interaction model
while making it loud in the visual model — exactly backwards.

### F8. The catalog is fetched eagerly, not at viewport demand

`_fleet.py:51-52` sets `_FLEET_CATALOG_PAGE_LIMIT = 100` and
`_FLEET_CATALOG_MAX_PAGES = 3`; line 391 sets `"include_terminal": True`. Entering Fleet
pulls up to 300 rows per refresh, including terminal history, from every enrolled machine.
There is no `AgentsViewport` reference anywhere in `_fleet.py`.

`plan:202609/fleet_ui.md` §3 specified "first catalog page plus additional pages requested
by `AgentsViewport`". The shipped laziness contract is coarser than the accepted one, and
it is tied to a *mode* rather than to what is on screen — which is why it had to be
coarse.

### F9. "Unavailable" and "loaded, zero results" are perceptually identical

`agents_fleet_unavailable_120x40.png` and `agents_fleet_loaded_zero_results_120x40.png`
are the same image except for a low-contrast grey caption in the far top-right corner:
`fleet config unavailable` versus `1 machine · 0 results`. Both render an entirely empty
list panel and "No agent selected".

The accepted plan required these states to be "visually distinct". They are technically
distinct and perceptually identical: the distinguishing text sits at the corner furthest
from the empty region the eye is actually looking at, and there is no recovery affordance
in either. The Agents-tab onboarding/quickstart panel is explicitly suppressed in Fleet
mode when machines exist (`_display_detail_onboarding.py:47-53`), which is why the panel
is blank rather than helpful.

### F10. Machine management has no home in the TUI at all

Epic note #1 on `sase-xe` recorded that there was no in-TUI path to enrollment. The
landing fix (note #7, item 3) added `app.setup_agent_machine`, whose entire implementation
(`_fleet.py:149-164`) is a twelve-second toast reading:

> No remote machines are enrolled. On the target, run `sase machine bootstrap --json` into
> a protected file. On this controller, run `sase machine init -B <file>` to discover,
> enroll, and verify.

And once machines *do* exist, `app.connect_agent_machine` ("Agents: show remote machine
status") is gated on a remote row being selected and prints a one-line toast
(`_fleet.py:139-147`). There is no list of machines, no health view, no repair for a
quarantined enrollment, no rename, no removal, no capacity — nothing.

This is not a small omission. The `sase machine` CLI has eleven subcommands
(`add`, `agent`, `attention`, `bootstrap`, `discover`, `init`, `list`, `remove`, `rename`,
`repair`, `status`). Zero of them have a TUI surface.

### Bonus finding: there is no capacity anywhere

`%dispatch:` completion is built from local config only
(`src/sase/dispatch/machine_catalog.py:10-29`: alias, provider ref, installation id,
endpoint, quarantine status). The fleet counts model
(`src/sase/ace/tui/models/_fleet_agents_counts.py`) carries running counts and nothing
about slots. And `docs/remote_dispatch.md:215` states that "V1 remote launch does not
combine with `%wait`, `%queue`, or `%clan`".

So at the exact moment the user decides where to send work, the interface offers the least
useful facts about the candidates, and the directive that manages capacity is mutually
exclusive with the directive that reaches other capacity. The primary *reason* to own a
second machine is unrepresented in the product.

---

## 2. Diagnosis: three modeling errors

### E1. Location was modeled as a place instead of a property

Every other dimension of a SASE agent — project, tribe, clan, family, model, provider,
status, age — is an attribute. The Agents tab has a rich, uniform machinery for
attributes: a query language with a closed field allowlist
(`src/sase/ace/agent_query/tokenizer.py:34-51`), three grouping modes with per-mode fold
registries (`_grouping.py:40`), status chips, accent palettes, and counts.

`machine` is an attribute of exactly the same kind. Modeling it as a sub-tab means it
composes with nothing: you cannot ask for "questions on apollo", you cannot group by
project across machines, you cannot save a machine-scoped query, you cannot fold a
machine, and your selection and scroll position are split across two universes that must
each be separately restored (`_fleet.py:80-96`).

The prior consolidated research rejected "Local/Remote sub-tabs" for good reasons and then
chose Focus/Fleet, which is the same shape with better names. Renaming a place does not
make it not a place.

### E2. Follow was invented to undo the damage, then wired to the wrong outcome

Once you have a view that shows *everything on every machine*, you need a way to say "just
the ones I care about". Follow is that mechanism. But look at what it actually keys on:
`FollowCreatedBy = Literal["explicit", "dispatch"]`
(`src/sase/dispatch/follow_store.py:26`) — `%dispatch` pre-writes the follow before launch
submission.

For a single-operator fleet, therefore, **"followed" ≈ "I happened to launch this from
this machine"**. The unfollowed set is: agents launched from another controller, agents
launched on the target directly, and agents explicitly unfollowed. In Bryan's fleet —
three machines, one human — the Focus/Fleet split mostly encodes *where he was sitting
when he pressed enter*, which is precisely the fact remote dispatch exists to make
irrelevant.

Meanwhile the thing Follow *is* load-bearing for — a durable, family-following
subscription that survives agent/monitor/gate shell handoffs — is genuinely valuable and
genuinely hard, and it got wired to *list membership* (F4) instead of to *notification*
(F5). The mechanism is right; the outcome it drives is wrong.

### E3. The remote path was built parallel to the local path instead of through it

Separate rows appended after the pipeline (F2), separate attention path (F5), separate
answer modal and content modal (F6), separate command availability with 21 exclusions and
2 silent overloads (F7), separate laziness tier (F8), separate empty states (F9).

`plan:202609/fleet_ui.md` opened with "Preserve the existing Agents list and detail
machinery" and "no second list implementation". No second *widget* was created — but a
second *pipeline* was, which is the part that mattered.

---

## 3. The three questions, answered

### Q1. Where should remote agents be displayed?

**In the Agents list, interleaved with local agents, tagged with their machine.** Not in a
sub-tab, not in a separate top-level tab, not in a separate panel.

Rationale: a remote agent *is* one of your agents. It is in a project, it has a family, it
asks questions, it needs approvals, it fails. Nothing about it is categorically different
from a local agent except the host that runs it — and the entire point of the epic was to
make that host swappable. A UI that keeps insisting on the distinction is arguing with its
own feature.

The separate concern — *machine* health, enrollment, and capacity — is real and belongs
somewhere else entirely (Q2 below), because a machine is not an agent and does not belong
in an agent list.

### Q2. Are the current UX choices right?

Mostly no, and I want to be specific about which parts are worth keeping, because a fair
amount of it is good.

**Keep:**

- **The durable follow store.** Family-following across sequential shells is correct and
  hard-won; SASE agents are single-turn and continuation is mechanical, so a subscription
  that dies with the first shell would miss the very approval you are waiting for
  (`decisions:single-turn-agents`). Keep the store, the tombstones, the
  explicit-unfollow-wins rule, and the dispatch pre-write.
- **Each host exports only agents it owns.** The prior research's anti-recursion rule is
  right and should stay.
- **Origin-qualified stable row handles.** Cross-machine identity collision avoidance is
  correct.
- **Capability-gated actions.** Advertising `lifecycle.stop` / `attention.answer_question`
  per row is the right contract. The failure is in presentation, not in the model.
- **Cached rows with age when a host goes offline.** Honest and correct.

**Change:**

- The Focus/Fleet strip (delete — §4).
- `project_display_name=host_alias` (F1 — fix first; almost everything else improves).
- Remote rows appended outside the filter/fold pipeline (F2).
- Attention gated on follow (F4) and terminating in a toast (F5).
- Bespoke remote modals (F6) and mode-dependent keys (F7).
- Eager 300-row catalog paging tied to a mode (F8).
- Indistinguishable empty states with no recovery (F9).
- Machine management existing only as a toast (F10).
- `☆alias` + `online · fresh` on every single row. This is the most visible everyday cost:
  the renderer (`_agent_list_render_agent.py:64-81`) appends
  `connection_health · freshness · intent` to every remote row, truncated at 48
  characters. On a healthy fleet that is roughly fourteen characters of "everything is
  normal" repeated on every line, competing with the intent text you actually want.
  **Annotate exceptions, not the norm.**

### Q3. Should we support "Focused" vs "Unfocused" remote agents?

**No — not as a user-visible view axis. Yes — as an invisible notification subscription.**

The case against the view axis:

1. **It is a provenance accident, not an intent** (§E2). Dispatch auto-follows; so
   "followed" mostly means "launched from here".
2. **It duplicates scoping the app already does better.** The agent query language already
   has `status:`, `project:`, `name:`, `model:`, `provider:`, `tribe:`, `text:`,
   `needs:input`, `attention`, `pinned`, `hidden`, `age>` and boolean operators. Adding one
   field — `machine:` — gives every scoping the Focus/Fleet split provides, plus
   compositions it can never provide (`machine:apollo AND needs:input`), plus persistence
   through the existing query profile machinery.
3. **It costs two rows of permanent chrome** (`_app_layout.py:86-110`) plus duplicated
   selection, scroll, detail, and fold state per mode (`_fleet.py:80-96`), on a tab whose
   vertical space is its scarcest resource.
4. **It made the important thing harder.** Attention is fetched only for followed rows
   (F4) *because* follow was defined as membership. If follow had been defined as
   notification, attention would naturally be fetched for everything visible.
5. **It has no keys** (F3). Eight months of design and implementation produced an axis
   nobody can reach from the keyboard, which is decent evidence that nobody could decide
   what pressing that key would be *for*.

The case for keeping the underlying subscription:

- Answering "notify me about this remote family across shell handoffs" is exactly what the
  follow store does, and there is no cheaper way to do it.
- It gives a bounded, targeted `followed_batch` call independent of catalog size, which is
  a genuinely good hydration tier — just tied to notifications rather than to a view.
- Explicit subscription is the only way to adopt work you did not launch (an agent started
  directly on `apollo`, or by a future second operator).

So: **rename Follow to Notify (or Watch) and move it onto the notification axis.** The UI
for it already exists — the notification panel has mute, snooze, bulk marks, and
reclassification. Unwatching a remote agent is muting its notifications; that is not a new
concept, it is an existing one. The follow store becomes the durable backing for a
notification subscription instead of a parallel view-membership registry.

---

## 4. Alternatives considered and rejected

**A separate top-level `Fleet` tab (beside Agents / Artifacts / AXE).** Rejected. It
duplicates every piece of list, selection, grouping, and action machinery (the accepted
plan already rejected this for the same reason), and it splits your attention across two
tabs for one job. It also makes "my agent that happens to run on apollo" live away from
your other agents, which is the exact error at a larger scale.

**Per-machine sub-tabs (`Here | apollo | mac`).** Rejected. Scales linearly with machines,
makes cross-machine questions impossible, and turns adding a machine into a layout change.
The prior research reached the same conclusion for the same reason.

**Machine as a *tribe*.** Tempting, because the snapshots already look like this and
tribes are "a user-facing label for related agents across clans and families"
(`glossary:agent-tribe`). Rejected: tribes are user-authored intent (`%id(tribe=...)`,
`#tribe:`, `sase agent tribe`), and hijacking them for a system-assigned fact would make
the user's own tribes unusable on a fleet and would break `sase agent tribe` round-tripping.

**Remote agents in the Artifacts tab's Agent pane.** Partly attractive — that pane is
already a query-driven, paged, history-oriented browser, which is a better fit for
"catalog" than the Agents tab is. But the pane is retrospective; remote agents are live,
need approvals, and belong where you triage. Recommendation: make the Artifacts Agent pane
machine-aware too (it shares the query dialect), but do not make it the primary home.

**Keep Focus/Fleet and just fix the ten findings.** This is the conservative option and it
is defensible — most of F1–F10 are independent of the mode axis. I reject it because F2,
F4, F7, and F8 all follow *from* the mode axis: rows outside the pipeline, attention gated
on membership, mode-dependent keys, and mode-tiered laziness are what you get when
location is a place. Fixing them individually while keeping the axis means fixing them
again next time.

---

## 5. Recommended UX

### R1. One list. Delete the Focus/Fleet strip.

Remove `#agents-header` and its `PanelTabStrip`, `current_agents_subtab`,
`cycle_agents_subtab{,_reverse}`, `view_agent_in_focus`, and the per-mode state
duplication. The Agents list contains local and remote agents together, always.

Reclaims two rows of permanent vertical chrome and deletes an entire state axis.

### R2. Fix the row model: machine is `origin`, project is project.

- Add `origin` / `origin_alias` as the row's machine field; stop writing `host_alias` into
  `project_display_name` and stop synthesizing `/fleet/<alias>/project.yml`.
- Populate `project_display_name` from the remote row's real project
  (`logical_locator.project.project_id` and the `project_label` already present in the
  wire payload — `_fleet_agents_rows.py:245-259` already reads them, it just prefers them
  as the *patch* name).
- Derive `agent_type` from lifecycle rather than hardcoding `AgentType.RUNNING`
  (`_fleet_agents_rows.py:170`), so remote rows land in the correct running/done/failed
  sections and obey the same recent/history rules as local rows.

Do this first. It is the cheapest change with the largest downstream effect.

### R3. Route remote rows *through* the pipeline, not around it.

Merge fleet rows into the local agent list **before** the fold/filter boundary, so the
search query, hide/dismiss rules, fold counts, and grouping all see one homogeneous list.
Remote rows that fail the query disappear like local ones do; group counts and list
contents can no longer disagree.

### R4. Machine becomes a query field and a grouping mode.

**Query:** add `machine` to `SUBSTRING_PROPERTY_KEYS`
(`src/sase/ace/agent_query/tokenizer.py:34`), with `machine:here` reserved for the local
host. Immediately available: `machine:apollo`, `NOT machine:here`,
`machine:apollo AND needs:input`, `machine:mac AND project:sase AND age>1h`. Add the same
field to the Artifacts Agent pane dialect (`query_profile/profiles/_agents.py`) so the two
surfaces keep their vocabulary aligned.

**Grouping:** add `BY_MACHINE` to `_GROUPING_CYCLE`
(`src/sase/ace/tui/actions/agents/_grouping.py:40`), label `"by machine"`. This
reconstitutes the entire Fleet view — with folds, per-group counts, group focus, `h`/`l`
navigation, and per-mode fold registries — out of machinery the user already has muscle
memory for, at the cost of one tuple entry and a group-key function.

```
 ⌂ here · 3/10 running                                    [group: by machine (o)]
 │ sase
 │ │ [agent] visual-code    (FAILED)   12m  coder
 │ │ [agent] docs-refresh   (RUNNING)   1m  codex
 ⌂ apollo · 4/10 running · 1 needs input · now
 │ sase
 │ │ [agent] remote-auth-fix  (QUESTION)  4m  repair remote dispatch auth
 │ │ [agent] queue-window     (QUEUED)    2m  review queued launch window
 ⌂ mac · ⚠ offline · last seen 12m · 1 cached
 │ │ [agent] ci-watch         (RUNNING)  41m  cached
```

And the default grouping (by project) now works across machines, which is the view that
did not previously exist at all:

```
 ⌂ @default · 7 [R3 Q1 D3]
 │ sase
 │ │ [agent] remote-auth-fix  apollo  (QUESTION)  4m  repair remote dispatch auth
 │ │ [agent] visual-code              (FAILED)   12m
 │ │ [agent] ci-watch         mac ⚠   (RUNNING)  41m  cached 12m
 │ website
 │ │ [agent] docs-refresh     apollo  (RUNNING)   1m
```

### R5. Row anatomy: annotate exceptions, not the norm.

- **Origin chip** immediately after the type badge, colored per machine from the existing
  hashed accent palette (`sase.palette_hash`, as Artifacts provider panes already do).
  **The local machine gets no chip** — absence means "here". On a fleet that is mostly
  local, this is close to zero added noise.
- **Drop `online · fresh` from healthy rows entirely.** Render staleness only when it
  exists: a dim row style plus a terse `12m` suffix when cached, `⚠` on the chip when the
  host is offline or quarantined.
- **No follow star.** Watch state is a notification property (R6) and does not need a
  per-row glyph in the default case. If a marker is wanted, mark the *exception* — a
  muted/unwatched remote row gets a dim bell-off glyph — rather than starring the majority.
- Keep the bounded intent preview, but let it have the width the removed status blob was
  consuming.
- When the origin chip cannot be shown (very narrow widths), keep the chip and drop the
  model column, not the reverse — location is more load-bearing than model at a glance.

### R6. Follow becomes Notify, and lives in the notification system.

- Keep `src/sase/dispatch/follow_store.py` and its semantics (dispatch pre-write, family
  promotion, explicit-unwatch-wins, tombstones). Rename the user-facing verb to **Watch**
  (or **Notify**), and never let it determine list membership.
- **Fetch attention for every remote row currently in the list**, not only watched ones.
  It is one batched call keyed by logical keys, and it is the single most valuable remote
  read there is.
- **Route remote questions and gates into the existing notification store** so they appear
  in the `NotificationIndicator` badge and the notification panel, and so mute, snooze,
  bulk marks, and reclassification apply. `decide_and_persist_attention_notices` already
  does the dedup by origin plus request identity; it currently just terminates in
  `self.notify` (`_remote_attention.py:82`).
- **Unwatch = mute.** No new concept, no new UI, no new keybinding.

This is the answer to Q3 in implementation form: the subscription survives, the view axis
does not, and the important behavior gets *better* rather than worse.

### R7. Unify the action surfaces.

- **Answer a remote question in the same modal as a local one**, with the origin chip in
  the modal header. Retire `RemoteAttentionModal` as a separate screen; keep its
  preview-digest validation as a guard inside the shared modal.
- **Open remote content in the detail pane and the pager**, the way local content opens,
  with a bounded-fetch adapter behind it. At minimum, fix the `raw_handles[0]` bug
  (`_remote_content.py:55`) so chat, output, and diff are each reachable.
- **Same keys, honest refusals.** A remote row should answer to `enter`, `x`, `w`, `A`,
  `r`, and the rest wherever the capability is advertised. Where it is not, do not silently
  remove the command from the palette — say `apollo does not support fork (protocol 1)`.
  Silence teaches the user that the keyboard is unreliable; a specific refusal teaches them
  the capability model.
- **Stop overloading `F` (edit hooks) as remote fork** (`_availability_agents.py:226`).
  Give fork its own named action with its own label, or extend the local fork action to
  remote rows — but never let one key mean two things based on invisible state.

### R8. Machines get a real home: Admin Center → **Machines** pane.

Add a seventh `CenterTabSpec` (`src/sase/ace/tui/modals/config_center_catalog.py:17`)
beside Config, Logs, Procs, Projects, Statistics, Updates. Model it directly on
`ProjectsPane`, which already has exactly the right shape — a list, a detail panel,
lifecycle actions, and an in-TUI **init flow** (`projects_pane_init*.py`, 1,083 lines).

The Machines pane covers the whole `sase machine` CLI:

```
 Admin Center                    1 Config  2 Logs  3 Procs  4 Projects  5 Stats  6 Updates  7 Machines

 ⌂ here (athena)      local           3/10 running
 ● apollo             tailnet         4/10 running · online · protocol 1 · hello 8s ago
 ⚠ mac                tailnet         offline · last seen 12m
 ⨯ olympus            https           quarantined: installation id mismatch      [r] repair

 [n] enroll   [d] discover   [s] status   [R] rename   [x] remove   [r] repair
```

- **Enroll** runs the controller half of `sase machine init` in the TUI: paste or pick a
  bootstrap bundle path, run discovery, show what will be enrolled, confirm, activate.
  (The target half — `sase machine bootstrap` — inherently requires a shell on the target;
  the pane should say so plainly and show the exact command to copy.)
- **Repair** surfaces `sase machine repair` for a quarantined enrollment, which today has
  no discoverable path whatsoever.
- Every operation is already journaled through the durable mutation layer, so the pane is
  a view over existing commands, not new backend surface.

This replaces the twelve-second toast (F10) with the pattern the app already uses for its
other inventory concept, and it removes machine chrome from the Agents tab entirely —
which is what makes R1 affordable.

### R9. Capacity is the missing product concept.

- Extend the fleet summary wire with per-host `running` and `max_running_agents`, and
  surface it in three places: the Machines pane, the `by machine` group header, and the
  Agents-tab capacity segment, which already reads `[1/10 running · 1 stopped]` and should
  read `[1/10 here · 4/10 apollo · mac ⚠]` once machines exist.
- Put liveness and free slots into `%dispatch:` completion rows. Today the completion
  catalog is config-only (`machine_catalog.py:10-29`), so the decision point has the worst
  information in the system.
- **Make `%dispatch` compose with `%queue`.** The current mutual exclusion
  (`docs/remote_dispatch.md:215`) is backwards: capacity is the reason the fleet exists.
  `%dispatch:apollo %queue(runners=2)` should mean "wait for two free slots *on apollo*".
- Then the feature that makes three computers feel like one fleet:
  **`%dispatch:auto`** — run this wherever a slot is free, honoring `%queue` priority
  across the fleet. This is the payoff that justifies the whole epic, and it is not
  reachable while dispatch and queueing are exclusive.

I flag R9 as the item most likely to exceed the UX scope of this question — it needs a
wire change and a core change (`decisions:rust-core-required`, and the
`rust_core_backend_boundary` memory puts admission policy in `sase-core`). But it is the
recommendation I would fight hardest for, because it is the only one that changes what the
user can *do* rather than how comfortably they can do it.

### R10. Honest, actionable states.

Never render an empty list panel as a state. Render an inline banner row *in the list*,
with a reason and a single key:

- *No machines enrolled:* `No remote machines. Press ,7 to enroll one.` (Only when the
  user has plausibly wanted one — otherwise stay silent; a purely local user should see
  nothing.)
- *Machine offline:* keep cached rows, dim them, show `mac · offline · last seen 12m` as a
  group header, and disable only the actions that genuinely cannot work.
- *Query matched nothing:* `No agents match "machine:apollo needs:input".` with the query
  echoed — distinguishable from the above at a glance, from the centre of the panel.
- *Loading:* a skeleton or spinner in the list, not a caption in the corner.
- *Config broken:* `apollo enrollment is quarantined — press ,7 to repair.`

Re-shoot the four Fleet PNG snapshots after this; the current pair (F9) would fail its own
acceptance criterion under any honest reading.

### R11. Bind the keys.

With the mode axis gone, the surviving surface is small enough to bind:

| Action | Key | Note |
| --- | --- | --- |
| cycle grouping (now includes `by machine`) | `o` | unchanged, existing |
| filter / query (now accepts `machine:`) | `f` | unchanged, existing |
| stop / retry / fork / answer / open | existing local keys | capability-gated, honest refusals |
| toggle watch (mute) on selected remote row | notification-panel mute key | existing concept |
| open Machines pane | `,7` | matches `,U` Updates precedent |

Deleted outright: `cycle_agents_subtab`, `cycle_agents_subtab_reverse`,
`view_agent_in_focus`, `connect_agent_machine`, `setup_agent_machine`. Five of the nine
unbound actions disappear rather than needing keys — which is a good sign about the shape.

Per the repo's keymap convention, `src/sase/default_config.yml` must be updated together
with `AppKeymaps`, `_BINDING_META`, availability predicates, the help modal, and command
palette metadata.

---

## 6. What this deletes

Worth stating plainly, because the value of the recommendation is largely subtractive:

- `#agents-header` and its `PanelTabStrip` (`_app_layout.py:86-110`).
- `current_agents_subtab`, its validator, its watcher, and per-mode state duplication.
- Five keymap actions and their metadata, availability, and help rows.
- `RemoteAttentionModal` as a separate screen (its digest guard moves into the shared modal).
- The parallel projection path `_agents_source_for_current_mode` /
  `_project_agents_for_current_mode_after_load` / `_sync_agents_local_source_from_current`
  / `_local_agents_from_mixed`.
- The mode-tiered catalog fetch, replaced by fold-driven paging.
- The `☆alias` prefix and the `online · fresh` suffix from every row.

Retained in full: the follow store, the federation worker and facade, the fleet protocol,
capability gating, origin-qualified identity, cached-with-age offline behavior, and the
durable mutation journal. This is a presentation-layer rethink; the backend the epic built
is largely the right backend.

---

## 7. Sequencing

1. **F1 + R2** — origin/project split and lifecycle-derived `agent_type`. Small, and every
   later step gets easier.
2. **R3** — merge remote rows before the fold/filter boundary. Unblocks query, dismiss,
   and counts.
3. **R4** — `machine:` query key and `by machine` grouping mode. At this point Focus/Fleet
   has no remaining unique capability.
4. **R6** — attention for all visible remote rows; remote notices into the notification
   store; unwatch = mute.
5. **R1** — delete the strip and the mode axis.
6. **R8** — Admin Center Machines pane.
7. **R5 + R10 + R11** — row anatomy, honest states, keybindings, re-shot snapshots.
8. **R7** — modal and action unification.
9. **R9** — capacity in the wire, `%dispatch` × `%queue`, `%dispatch:auto`. Cross-repo;
   plan separately against `sase-core`.

Steps 1–5 are strictly a simplification and can land before any new surface exists. Step 6
is the only genuinely new UI. Step 9 is the only one that needs the Rust core.

---

## 8. Risks, and what would change my mind

- **A multi-operator future.** If a second person ever launches agents on shared machines,
  "agents I follow" stops being a provenance accident and becomes real intent, and the
  Focus/Fleet split earns its keep. I judge this unlikely for a personal tailnet fleet, and
  cheap to revisit: `machine:` plus a saved query profile reproduces Focus for whoever
  wants it, without a mode.
- **Catalog scale.** One list means the default query must exclude remote history by
  default, or a fleet with thousands of historical agents will swamp the list. Mitigation
  is the same one local agents already use — the default query and the recent/history rules
  — plus fold-driven paging. If it turned out that remote history genuinely cannot be
  expressed in the local query dialect, that would be an argument for a separate browse
  surface (and the Artifacts Agent pane, not a Fleet sub-tab, would be its home).
- **Navigation performance.** The repo has j/k benches including a fleet variant
  (`tests/ace/tui/bench_tui_jk_fleet.py`) and a `tui_perf` memory note whose thresholds
  gate this area. Merging remote rows into the main pipeline changes what the bench
  measures; it must be re-baselined deliberately, not adjusted to fit.
- **I did not run the TUI.** My reading of the shipped experience rests on the four
  committed PNG snapshots and on source. Those snapshots are fixture-driven and small (3–4
  remote rows); a real fleet may look better or worse than they suggest. A live
  Athena→Apollo session — which `sase-xe.16.10` is still open to produce — should be the
  first check on any of this.
- **The epic is not finished.** `sase-xe`, `sase-xe.16`, `sase-xe.16.10`, and
  `sase-xe.16.11` are all open, with a landing blocker recorded 2026-09-09 stating that
  live receipt, visibility, output, and stop were unmet. Some of what I have called a UX
  choice may simply be unfinished work. Where that is true, the recommendation is still
  useful as a target: it says which of the remaining work is worth finishing and which is
  worth deleting.

---

## 9. Evidence index

| Claim | Source |
| --- | --- |
| Machine alias stored as project | `src/sase/ace/tui/models/_fleet_agents_rows.py:172,189` |
| Hardcoded `AgentType.RUNNING` | `_fleet_agents_rows.py:170` |
| Remote rows appended after fold boundary | `src/sase/ace/tui/actions/agents/_loading_apply.py:402`; `_fleet.py:180-190` |
| All nine fleet actions unbound | `src/sase/default_config.yml:520-527`; `docs/remote_dispatch.md:238` |
| Attention fetched only for followed rows | `_fleet.py:313-321` |
| Attention terminates in a toast | `_remote_attention.py:82`; no `remote`/`fleet` hits in `actions/agents/_notification*.py` |
| Separate remote answer/content modals | `modals/remote_attention_modal.py`; `modals/remote_content_modal.py` |
| Only `raw_handles[0]` is reachable | `actions/agents/_remote_content.py:55` |
| 21 commands disabled on remote rows | `commands/_availability_agents.py:54-77` |
| `F`/edit-hooks overloaded as remote fork | `commands/_availability_agents.py:226` |
| Eager 3×100 catalog with terminal rows | `_fleet.py:51-52,391`; no `AgentsViewport` reference |
| Unavailable ≡ zero-results visually | `tests/ace/tui/visual/snapshots/png/agents_fleet_unavailable_120x40.png`, `..._loaded_zero_results_120x40.png` |
| Quickstart suppressed in Fleet mode | `actions/agents/_display_detail_onboarding.py:47-53` |
| Enrollment is a toast | `_fleet.py:139-164`; epic `sase-xe` note #1, note #7 item 3 |
| `sase machine` has 11 subcommands, 0 TUI surfaces | `sase machine --help` |
| Completion catalog is config-only | `src/sase/dispatch/machine_catalog.py:10-29` |
| `%dispatch` excludes `%queue` | `docs/remote_dispatch.md:215` |
| Agent query field allowlist | `src/sase/ace/agent_query/tokenizer.py:34-51` |
| Three grouping modes cycled by `o` | `actions/agents/_grouping.py:40-46` |
| Admin Center has six numbered panes | `modals/config_center_catalog.py:17` |
| Projects pane already has in-TUI init | `modals/projects_pane_init*.py` (1,083 lines) |
| Follow created by explicit or dispatch | `src/sase/dispatch/follow_store.py:26` |
| Accepted Focus/Fleet spec | `plan:202609/remote_dispatch_fleet.md`; `plan:202609/fleet_ui.md` |
| Original design rationale | `research:202609/remote_dispatch_and_fleet_focus/remote_dispatch_and_fleet_focus.md` §3 |
| Epic still open, live proof unmet | `sase bead show sase-xe`, `sase-xe.16` notes #1–#3 |

---

## Recommended UX (summary)

**Delete the Focus/Fleet sub-tabs.** One Agents list holds every machine's agents,
interleaved, routed through the same filter, fold, dismiss, and notification pipeline as
local agents.

**Make the machine an attribute, not a place.** Store it as `origin`, restore the real
project to the project field, add `machine:` to the agent query language, and add
`by machine` to the `o` grouping cycle. That yields the catalog view, the per-machine view,
and the cross-machine project view — three views for one tuple entry and one query field,
all with folds, counts, and keys the user already knows.

**Keep the follow store; retire the follow *view*.** Watching a remote agent means "notify
me", not "show me here". Fetch attention for every visible remote row, route remote
questions and gates into the existing notification store and modals, and let unwatch be
the existing mute.

**Give machines a home in the Admin Center.** A Machines pane (tab 7) modeled on Projects:
enroll, discover, status, rename, remove, repair, health, and capacity. That is where
machine chrome belongs, and moving it there is what makes deleting the Agents-tab strip
affordable.

**Render exceptions, not the norm.** A colored origin chip, nothing for local, staleness
and offline shown only when true, no star on every row, and empty states that name the
problem and offer one key to fix it.

**Then make it a fleet.** Per-machine capacity in the summary wire, in the group header, in
the Agents capacity segment, and in `%dispatch:` completion — and let `%dispatch` compose
with `%queue` so `%dispatch:auto` can send work wherever a slot is free. That is the
feature that turns three computers into one machine, and it is the one the current UX
cannot express.
