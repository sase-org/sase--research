# Integrating `sase tool` into the Agents TUI

**Researcher:** grk · 2026-09-27 · independent swarm report
**Question:** What is the best UX for bringing the `sase tool` command into the Agents
tab (and other TUI surfaces)? Are a new Tools-deck card and a hammer-plus-count on
agent nodes the right first moves?

---

## 1. Answer up front

Ship **three zoom levels on the Agents tab**, copied from the ⊛ FINAL pattern that
already landed on the same screen, and stop there for v1.

| Zoom | Question | Surface |
| --- | --- | --- |
| **Glance** | Is this node running a named tool right now? Did the last named tool fail NEW? | A **state chip** on the agent row. Silent on success. No historical count. |
| **Diagnose** | What ran, which stage, NEW vs KNOWN, log tail, stop? | A **`Runs` card** as the first card of the existing λ Tools deck. `LLM Calls` stays the second card. |
| **Author** | Project catalog, LAST/TYPICAL, failure groups, receipts | Keep using `sase tool` / `:` for now; an Admin Center **Tools** pane is v2. |

The Tools-deck card is the right primary surface. The hammer-plus-count on nodes is the
wrong glance. The deck name `TOOLS` was emptied of LLM-call meaning on purpose when the
card was renamed **LLM Calls**; putting named-tool **Runs** in that deck is the rename
paying off. A fifth deck, a top-level TUI tab, and an Artifacts pane are the wrong
homes.

Live confirmation that the gap is real, taken on this machine while writing: `sase tool
list` reports `check` as **running**, typical **4m 13s (n=30)**. `sase tool runs -A
0t9--code` shows that agent with one live foreground `check` (`owner_kind` empty) and
two earlier `check` runs `signaled/143` at ~9 minutes. The Agents tab has no row chip,
no Runs card, and no LLM Calls linkage for that work. The operator has to leave the TUI
or parse a generic Bash row.

---

## 2. Two different objects still share the word "tool"

A **ToolRun** is the durable, machine-local record `sase tool run` writes: catalog name
(`check`, `test`, …), argv, owner, stage timeline, fingerprints, triage, receipts. It
is queried with `sase tool runs -A AGENT` and `sase tool show RUN`. Glossary: *Tool
Run*. Docs (`docs/tool.md`) already warn it is not an LLM Calls row.

An **LLM Call** is one provider tool invocation (Read, Edit, Bash, WebFetch, subagent)
from `tool_calls.jsonl`. The λ Tools deck today is exactly one card of those, glyph λ,
blurb *"LLM tool-call timeline"*, count noun `call`/`calls`
(`src/sase/ace/tui/widgets/decks/spec.py`). Empty copy still says "No LLM calls for this
agent".

Intersection is small and important: a Bash LLM call whose argv is `sase tool run
check` (or a monitor whose command was upgraded to that). Most LLM calls are not
ToolRuns. Many ToolRuns are not LLM calls: foreground `sase tool run` inside an agent,
`sase monitor start` wrapping, `sase tool run -H`, a human in a shell, `:` in the TUI
command line.

The TUI currently renders only the LLM-call side. Slow-tool rows in Main (≥20 s) and
the Tools-deck overflow hint (`^N/^P → Tools deck for the full LLM Calls timeline`)
both point at `tool_calls.jsonl`. `sase tool` has no TUI consumer. `grep` over
`src/sase/ace/` finds no ToolRun list/show calls.

That split is the design constraint. A surface that treats "the agent made N tool
calls" as the `sase tool` story will show the wrong object.

---

## 3. Jobs the TUI has to answer

Ranked by how often they happen while watching the Agents tab:

1. **Live wait.** "What is this agent blocked on?" — today: a 9-minute inline `check`
   looks like `RUNNING` plus maybe a slow Bash row. The operator wants `check 6:12` on
   the row they are already scanning.
2. **Triage after red.** "Is this NEW, or the red master I already know?" — `sase tool
   failures` already groups this (`KNOWN check / lint (symvision)` × 44 runs / 38
   agents on this machine). The selected agent's Runs card must show that verdict next
   to *this* run.
3. **Stop / follow.** "Kill that check" / "watch stages." CLI already has `stop` and
   `show -F`. The selected node's Runs card should offer the same actions without
   leaving the tab.
4. **Trace a wrapping Bash row.** "This LLM Calls `fail bash` — is it a ToolRun?" Jump
   to the run. Do not re-render stages inside the call timeline.
5. **Project weather.** "What is failing across agents?" / "Does `check` have a
   receipt?" That is catalog/history scope, not a per-node card. CLI covers it today;
   Admin Center is the TUI home later.

Job 1 is glance. Jobs 2–4 are the selected-node deck. Job 5 is a different pane.

Handed-off runs already have a *node*: a ⚙ monitor member or a named proc. Inline
foreground runs (the live `0t9--code` `check`) have no node of their own. That is why
the Agents tab, not Services, has to grow a glance.

---

## 4. What the current Agents tab already does (and is already full)

### 4.1 Row density

A compact agent row already carries, left to right: tier gutter, marks, type/provider
badges, status parenthetical (status word, wait tokens, queue rank, monitor/gate
glyphs and exit codes), the ⊛ FINAL chip, retry `↻N`, fold counts, ⚙/⋔ lane counts on
containers, bead glyph, name, owner, fleet summary, tribes, then a suffix of elapsed
time plus 🏃‍♂️ / ✅ / ❌ / ✋ / ✏️. See
`_agent_list_render_agent.py` and `_agent_list_render_agent_status.py`.

The FINAL chip is the correct analog for a ToolRun glance: it appears for attention
states, overlays `RUNNING` → `FINALIZING` while work is in flight, and **stays silent
on success**. It does not print `⊛ 3` for three finalizer instances.

A hammer plus a count would sit in that same after-paren slot, compete with ⊛, ⚙N,
and ✏️, and use a 2-cell color emoji in a row that already spends emoji budget on the
runtime suffix. The count would also collide with the Tools-deck switcher, which
already prints `tools 47` meaning LLM-call count.

### 4.2 Four decks, Tools is the single-card one

Cycle order is Main → Files → Tools → FINAL (`DECK_CYCLE`). `Ctrl+N`/`Ctrl+P` visit
**every** deck, including empty ones. `p t` / `p T` jump Tools. The Tools deck has no
views (`P` is unavailable); it always pages its one card.

FINAL just paid the cost of a fourth deck: new picker letter `n`, new glyph ⊛, new
availability probe, new switcher `status_segments` path, snapshot persistence. Adding
a fifth deck for a concern that is empty on most nodes makes every `Ctrl+N` longer
for a rare card.

Tools is the deck whose name is already right and whose body is currently one card.
Main is crowded (Context, Reply, header slow-tools, jump roster). Files is diffs.

### 4.3 Monitor / named-proc hole

`probe_tools_deck` returns empty for clans and named procs
(`decks/availability.py`). A monitor whose whole job is `sase tool run check` shows
"No LLM calls for this node". That is the node where a Runs card is the *entire*
Tools deck, and today the deck is a dead end.

### 4.4 Slow tools in Main

The header lists LLM calls ≥20 s, capped at 8, overflow pointing at the Tools deck.
Named-tool executions are almost always in that list when they were invoked via Bash.
Once a Runs card exists, those rows should grow a run-id jump; the slow-tools section
does not become the ToolRun inspector (no stages, no triage, no stop).

### 4.5 Command line already reaches the CLI

`:` runs procs. `sase tool show RUN -F` and `sase tool stop RUN` already work from
inside the TUI. Integration is not "can I type the command." It is glance +
selection-scoped diagnosis.

---

## 5. Evaluation of the two proposed ideas

### 5.1 New card on the Tools deck — yes, with a specific shape

This is the right primary surface.

**Why this deck.** The LLM Calls rename freed the word "tool" at card level while
leaving the deck named TOOLS. Named-tool Runs are the other half of that name. Split
`|` already lets an operator put Tools next to Main; `Ctrl+J`/`Ctrl+K` already move
between cards once a deck has more than one. Monitor nodes finally have something
true to show. A second card is how Tools grows from a special-case single-card deck
into the same card model Main and FINAL already use.

**Shape.** Two cards, not N cards:

| Card | id | Role |
| --- | --- | --- |
| **Runs** | `runs` | This node's ToolRuns. Newest / live first. |
| **LLM Calls** | `llm_calls` (today's card) | Provider timeline. Unchanged except linkage chips. |

Do not make one card per run the way FINAL makes one card per instance. A node has
0–few ToolRuns and they are a log, not parallel landing instances. Multiple runs
inside **Runs** should use the existing **card-block** machinery (the Reply `( )`
pattern): one block per run, land on newest, `( )` steps, optional one-row rail when
there are 2+ runs.

**Default card.** Follow FINAL's attention rule
(`final_default_card` in `decks/final/document.py`):

1. Sticky preferred card if it still exists.
2. Else **Runs** when this node has a live run or a failed-NEW run.
3. Else **LLM Calls** when calls exist (today's default).
4. Else Runs empty-state.

Selecting `0t9--code` during the live `check` measured above would open Runs. Selecting
an agent that only grepped files would still open LLM Calls.

**Switcher.** Do not print `tools 3` meaning "three ToolRuns" while `tools 47` still
means LLM calls. Reuse FINAL's `status_segments` path:

- Live named tool: `tools check` (tool name, Tools accent).
- Failed NEW: `tools ✗` (bold red).
- Otherwise keep today's call count when known (`tools 47`).
- Only-runs, no calls: `tools 1` as run count, and change the deck `count_noun` to a
  context-dependent pair, or always use the status segment for Tools.

Update the picker blurb from "LLM tool-call timeline" to "Named-tool runs and LLM
calls". Empty copy: "No named-tool runs or LLM calls for this agent".

**Keys.** `l`/`h`/`L`/`H` today expand LLM Calls detail while Tools is focused. Bind
them to the **active card**: Calls keep those levels; Runs uses them for stage-detail
depth (compact table → stages → log tail), matching `sase tool show` layers.

**Spread.** Two cards makes Tools eligible for automatic spread when both fit. Allow
it. `P` can appear once there is a real choice, the way Main/Files already work.

### 5.2 Hammer icon plus count on agent nodes — no

The glance job is "what is happening / what needs me," not "how many tools fired."

A count of LLM calls duplicates the Tools switcher. A count of ToolRuns is usually
1–3 and treats a green `check`, a KNOWN red master, and a live run as the same badge.
FINAL already learned this: success is silent; chips carry **state**.

A hammer emoji (🔨) is a wide color glyph. The row already uses emoji in the suffix
and unicode in the chrome (⚙ ⋔ ⊛ ✏️ ◆ ▤ λ). If a mark is needed beside the tool
name, use a 1-cell symbol from the same family as ⊛, or no extra glyph at all — the
catalog name `check` is the scannable token.

Container ⚙N / ⋔N counts work because they number **child nodes you can jump to**.
ToolRuns are not tree nodes (except when a monitor owns them, and then ⚙ already
counts that node). A `⚒3` on a session root would not be a jump target.

**Replace the idea with a FINAL-style chip**, specified in §7.

---

## 6. Other TUI surfaces — ranked

| Surface | Role | When |
| --- | --- | --- |
| Agents row chip | Job 1 | v1, with the card |
| Tools deck `Runs` card | Jobs 2–4 | v1 |
| LLM Calls linkage chip on wrapping Bash rows | Job 4 | v1 |
| Slow-tools header rows grow a run-id jump | Continuity | v1, cheap |
| Monitor / named-proc Tools deck | Fill the empty deck | v1 |
| Session/clan aggregation (attribute to member, like slow tools) | Root glance | v1 |
| Command palette: "Show Runs card", "Stop this node's live run" | Discoverability | v1 |
| `:` command line | Already works | — |
| Admin Center Tools pane (Runs / Failures / Catalog) | Job 5 | v2 |
| Services tab: show ToolRun id on proc/monitor rows | Hand-off identity | v2 |
| Metadata pager `V`: a TOOL RUNS section | Deep inspect | later |
| Notifications for overdue / NEW | Already designed in the CLI epic | with E6 / as needed |
| Top-level TUI tab | Structural change, three-tab IA | out |
| Fifth agent data deck | Cycle cost after FINAL | out |
| Artifacts pane / `tool:` as the live UX | ToolRuns are machine-local SQLite, not an artifact-repo document | out as primary |

Services is the wrong home for inline runs: they have no proc. Artifacts is the wrong
home because the ledger lives at `~/.sase/tools/runs.sqlite`, scoped by project
identity, with retention — it is not a sidecar document. A future `tool:<run-id>`
artifact *reference* can still be reserved for citations; it does not replace the
Agents-tab glance.

---

## 7. Glance chip spec (v1)

**Slot.** After the status parenthetical, same family as `_append_finalizer_chip`.
If both ⊛ and a live ToolRun apply, keep both: they are different lifecycles
(landing vs named tool). Truncate the ToolRun chip first on narrow rows (the tool
name + elapsed is recoverable from the Runs card; FINAL's instance id is not).

**When it appears.**

| Condition | Chip | Style |
| --- | --- | --- |
| This node has an unsettled ToolRun (`created` / `running`) | `check 6:12` | bold Tools accent `#87D7FF` |
| Last settled named-tool run for this node is failed/signaled **and** triage is NEW | `✗ check` | bold red |
| Success, KNOWN, FLAKY, ad-hoc with nothing to say | *(omit)* | — |

Elapsed uses the same compact duration formatter as the row suffix. No fake ETA in
v1; typical duration is already in `sase tool list` (`TYPICAL 4m 13s`) and can feed
an overdue `+Nm` later (E6), never a countdown.

**Inline vs hand-off.**

- **Foreground** (`owner_kind` empty, as on the live `0t9--code` run): chip the
  **agent turn** that `runs.agent` names.
- **Monitor-owned:** chip the **monitor member row**, not a second hammer on the
  parent. The parent already shows ⚙. The monitor row's chip is `check 6:12` so the
  ⚙ node explains itself.
- **Proc-owned** (`-H`): same as monitor if a session member exists; otherwise the
  chip stays on the attributed agent.

**Session root.** Aggregate member glances the way slow tools attribute child calls:
show the most severe (live > NEW fail), with the member suffix if space (`check
6:12 · --code`).

**Width.** Fixed-width-ish: tool name truncated to ~12 cells + duration. No progress
bar. No wrapping. Patch-row updates as elapsed ticks, using the existing incremental
list path (`patch_row`), not a full rebuild.

**No count.** Zero, one, or the attention run. `+N` only when two named tools are
live on the same node at once (rare).

---

## 8. Runs card spec (v1)

Render from the versioned `sase tool show` / `runs` envelopes. The TUI is
presentation: no second lifecycle, no local ETA math (`tui_perf` + the ToolRun
docs' "Textual renders only" rule).

**Header.** `RUNS  1 live · 2 settled · refreshed HH:MM:SS`, parallel to LLM Calls'
`N calls · N failures`.

**Active block (one run).** Mirror `_print_show` in `src/sase/tool/query.py`, compacted:

```text
check    running     6:12    just check
RUN      cdb3a7f5f1b88c423c8d626ebba5ae28
LAUNCH   foreground            OWNER  —     AGENT  0t9--code
STAGES
  ✓ fmt        8s
  ▸ lint      51s
  · tests      —
NEW/KNOWN/FLAKY  (when triaged)
tail of retained output
sase tool show cdb3a7f5…  ·  sase tool stop cdb3a7f5…
```

Actions on the focused block: stop (live), open pager / `: sase tool show -F`, copy
run id (`%` if that is the local copy key; otherwise palette). Do not in-TUI `rerun`
in v1 (CLI has no `rerun` yet; receipts are query-only).

**List of other runs** for the node: one compact line each (`signaled/143  8m 59s
just check`), newest first. `( )` moves blocks.

**Empty.** "No named-tool runs for this node" plus the existing deck-switch hint.
Human CLI runs attributed to no agent stay out of this card; they belong in the
Admin Center history later.

**Data.** `tool_run_list({agent, limit})` plus `tool_run_show` for the active block.
Session containers query each member name (or a future `agent` prefix match if the
store grows one). Monitor nodes query `owner_id` / `owner_kind=monitor` as well as
`agent`, so a monitor whose attribution is the starter agent still resolves when
selected.

**Linkage from LLM Calls.** If a Bash/command target parses as `sase tool run TOOL`
or carries a recorded run id, the compact row grows a chip `→ check` that switches
the same panel to Runs and selects that block. No stage duplicate on the Calls card.

---

## 9. Performance contract

This is the difference between a feature and a freeze. `tui_perf.md` is binding.

- **No SQLite on the render path.** Agent-list formatters stay pure functions of
  in-memory `Agent` (FINAL chips already follow this: `finalizer_row_state` reads a
  summary already on the model).
- **One published glance snapshot**, keyed by agent name, refreshed off-thread on
  the existing agents refresh / a change token of `~/.sase/tools/runs.sqlite`
  (mtime + size + inode, same idea as notification and usage peeks). Index *all
  running runs* plus *recent NEW failures* in one `tool_run_list` call, then join
  to rows. Do not call `tool_run_list` per visible row.
- **Detail card** uses the same debounce as other decks (`DetailPanelDebouncer`,
  150 ms). Show the cached envelope instantly; refresh in a worker; reject stale
  generations (copy `FinalDeckView`).
- **Live elapsed** ticks from `created_ts`/`running_ts` already on the snapshot,
  the way FINAL's live ticker works. Do not `show` every second.
- **Busy timeout** on the Rust bindings is 250 ms. Treat a timeout as "keep last
  snapshot," never block the pump.
- **Availability probe** for Tools must stay no-I/O: `has_content` true when the
  glance snapshot or the LLM-calls cache says so. Unknown (`None`) while the first
  peek is in flight, matching Files/Tools today.

There is no change-token peek API for ToolRuns yet (`src/sase/core/tool_run.py` is
begin/finish/list/show/summary/receipts). v1 needs a cheap list of unsettled +
attention runs, or a documented use of `tool_run_list(state=running)` plus a
bounded `failures` peek, wrapped behind a cache. Do not subprocess `sase tool`
from the TUI.

---

## 10. What this is *not*

**Not a fifth deck.** FINAL's own value write-up called out how hard a fourth deck
was (`DeckId` exhaustiveness, chrome accents, preferred-card slots). Tools can
hold the card. Picker letter `t` already exists.

**Not Main.** Slow tools and Context are the wrong zoom for stages, logs, and stop.

**Not merging Runs into the LLM Calls timeline.** Different grain, different
source, different actions. Link, do not fuse.

**Not v1 Admin Center.** Failures on this machine are already 38-agent weather.
That pane is real work (filters, suggest-bead, catalog LAST/TYPICAL) and must not
gate the Agents-tab glance. The CLI covers Job 5 until then.

**Not ETAs on the chip.** Typical duration exists (`4m 13s`, n=30 for `check` here)
and is honest as a *range later*. v1 prints elapsed only, matching the "elapsed-only
chips" recommendation in the E5 epic notes.

**Not a count of "tool calls."** That phrase in the original idea maps onto LLM
Calls, which the Tools switcher already counts.

---

## 11. Implementation sketch (for the later plan, not this report's job)

Order that keeps each step user-visible:

1. **Glance snapshot + row chip** for live foreground runs. Immediately makes
   `0t9--code`'s `check` visible in the list. Visual snapshots of compact rows.
2. **Runs card** in the Tools deck, default-card policy, empty states, monitor
   nodes included. `p t` then `Ctrl+J` if Calls was sticky.
3. **LLM Calls → Runs** jump chip; slow-tools overflow keeps pointing at Tools
   (now the right deck for both).
4. **Palette + stop action.**
5. **NEW-fail chip** once the glance snapshot includes recent triage (can ship
   with 3 if the failures query is cheap enough).
6. **v2** Admin Center Tools pane, Services id, receipt weather.

Flag it (`ace_tool_runs_deck` or similar) the way FINAL did, so chrome/keymap/help
can ship behind one switch.

Help/guide copy: Agents › Tools deck describes two cards. Footer: `p t` still
"Tools"; add `Runs` to the card hint when that card is active.

---

## 12. Recommended solution

**v1 — Agents tab only, two surfaces, one data join.**

1. **Row: attention chip, no hammer, no count.** Live: `check 6:12`. Failed NEW:
   `✗ check`. Success omitted. Foreground chips the agent turn; monitor-owned chips
   the ⚙ member. Snapshot-joined, patch-row ticked, no per-render I/O.
2. **Tools deck: add a `Runs` card in front of `LLM Calls`.** Blocks = ToolRuns,
   newest landing, `( )` to step, stage timeline + triage + tail + stop. Default to
   Runs when live or NEW-fail. Keep λ Tools, picker `t`, accent `#87D7FF`. Update
   blurb, empty copy, and switcher so call counts and run state never share one
   integer. Fill the named-proc empty deck.
3. **Link, do not duplicate.** Wrapping Bash rows and slow-tool lines jump to the
   Runs block.

**v2 — project weather.** Admin Center Tools pane (Runs / Failures / Catalog with
LAST and TYPICAL). Services rows show `run_id`. Receipt coverage is a catalog
badge there, not an agent-row icon.

**CLI remains the author surface.** `sase tool list|runs|show|stop|failures|receipt`
stay the typed API; the TUI renders cached envelopes of those same records.

This is the FINAL four-zoom idea applied to named tools, with the diagnose zoom
folded into the deck whose name was reserved for it, and with the glance copied
from ⊛ (state, silence on success) rather than from ⚙N (child-node counts) or
from a hammer tally of provider calls.
