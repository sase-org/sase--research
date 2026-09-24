# SASE concept renames: critique of the 2026 wave and what else to rename

_Researcher `cld`, 3-researcher swarm · 2026-09-24 · sase `master` @ `075225d53`_

## Bottom line

The six renames are, on balance, the right direction. Two are excellent (**chop → job**,
**sase shell → sase turn**), three are good but have loose ends
(**ACE → TUI**, **AXE → scheduler**, **agent family → agent session**), and one is
defensible but the weakest (**lumberjack → routine**). None should be reverted.

The in-flight pair (session and turn) needs three corrections before it ships:

1. **Stop minting durable `shell` spellings inside sase-17m.** The session epic already
   writes `agent_session_shell`, `agent_session_shell_kind`, `agent_session_shell_id`,
   and `agent_session_shell_state` (see `src/sase/core/agent_scan_wire_agent_session_shell.py`).
   Its core-contract phase (sase-17m.8, not landed) will bump schemas and the fleet
   protocol to emit them. The turn rename would then need a second schema bump, a
   second fleet-protocol bump, and a legacy reader that accepts three spellings forever.
   Put the `turn` spellings into sase-17m.8 so that only one bump happens.
2. **"Session" already means something user-visible in SASE.** It names live TUI
   instances: `sase proc list -s/--session`, session chips such as `ace·sase#14 4f2a`,
   and the `sase.sessions` registry. The sase-17m plan leaves those unchanged on
   purpose. After the rename, `sase proc list --session latest` will read as "procs of
   the latest agent session." Rename the TUI meaning (new rename R3).
3. **"Shell" means two things today, and only one of them is a turn.** The proc store
   uses `shell_name` and `shell_kind` for any named proc, including service daemons
   (`shell_kind="service"`). A mechanical shell → turn rename would call the scheduler
   daemon a "turn." Only session members become turns. Named procs keep proc
   vocabulary.

**New renames I recommend** (§3 gives the reasoning):

| # | Today | Rename to | Strength |
| --- | --- | --- | --- |
| R1 | `sase pipe` / `/sase_pipe` | **`sase handoff`** / `/sase_handoff` | Strong |
| R2 | "LLM Calls" panel | **"Tool Calls"** | Strong |
| R3 | "TUI session" (`--session`, session chip) | **"TUI instance"** | Strong (forced by the session rename) |

Three candidates are worth doing only if you are already editing that surface:
**hood → namespace**, **mentor → review agent**, and **memory web/strand →
collection/entry**. Everything else I examined should keep its name (§5).

---

## 1. Method and criteria

I read the glossary web, the sase-17m epic and its plan
(`plan:202609/agent_session_rename.md`), agent `0qi`'s prompt, the accepted decision
records on single-turn agents and host-owned completion, and prior naming research
through audited reads:

- `scheduler_tui_naming`
- `scheduler_loop_naming_reassessment`
- `naming_the_change_unit`
- `sase_shell_named_procs`
- `xprompt_plang_rename`
- the tag → tribe plan

I also checked the live CLI (`sase --full-help` and per-command help), code, and docs at
`075225d53`. External definitions come from primary documentation, listed under
Sources.

A rename had to clear these tests:

1. **Meaning match.** The industry meaning of the new word matches SASE's meaning, not
   just its general shape.
2. **The definition stops translating.** If every glossary entry and doc intro has to
   say "an X is basically a Y," Y should probably be the name. You applied this test to
   chop → job; I applied it to every candidate.
3. **Collisions, including in the agent's own context.** SASE agents run inside Claude
   Code, Codex, and similar tools. A SASE term that means something different from a
   built-in tool or skill the agent can also see, such as Claude Code's `Monitor` tool
   or its routines, confuses agents in practice, not just in theory.
4. **Cost and timing.** Durable keys, user-typed syntax, and the `.sase` file format are
   expensive to change. Prose and TUI labels are cheap.
5. **Set coherence.** Names that share one metaphor should move together. You used this
   argument for AXE, lumberjack, and chop.

---

## 2. Critique of the implemented and in-flight renames

### 2.1 ACE → TUI (`sase tui`): endorse; finish the leftovers

`sase tui` explains itself, and the old expansion ("Agentic Change Explorer") no longer
described a surface whose tabs are Agents, Artifacts, and Services
(`src/sase/ace/tui/widgets/tab_bar.py:20-24`). Removing `sase ace` outright, with no
hidden alias, is bold but fine for a single-user CLI.

Loose ends:

- **Config root.** The config root is still `ace:` (`default_config.yml:276`), so users
  configure "tui" behavior under `ace:`. Add `tui:` in sase-core config composition,
  accept `ace:` as legacy input, and put this behind the same kind of sunset flag you
  used elsewhere.
- **Prose form.** Docs say "sase's TUI" 836 times and "the SASE TUI" once. The
  possessive reads acceptably in isolation but fails in compounds. Prefer "the SASE
  TUI" on first mention and "the TUI" after. This is cosmetic and low priority.
- **Package name.** `src/sase/ace/` holds Patch, query, and hook domain code, not only
  the TUI. Do not rename the package wholesale. The earlier research was right about
  this.

### 2.2 AXE → scheduler: endorse; the rename is half-finished

"Scheduler" is accurate and guessable. However, the public surface still sends users
back to `axe`:

- **Subcommands.** The routine and job tree exists only under the legacy name:
  `sase axe routine|job|maintenance`. `sase scheduler` offers only
  `restart|run|start|status|stop`. Canonical and legacy spellings should have the same
  reach. Add `sase scheduler routine|job|maintenance` and make `sase axe` a pure alias.
- **Config and prose.** The config root is still `axe:` (`default_config.yml:997`), and
  docs still contain 158 "AXE" tokens, for example "AXE job" and "scheduled AXE work."
- **Admission boundary.** Add one glossary sentence: *the scheduler runs jobs; runner
  admission decides when an agent launch may start.* Launch capacity is also
  "scheduling" in casual speech.

### 2.3 lumberjack → routine: defensible; keep it, but know its cost

Arguments for:

- "The housekeeping routine runs `error_digest`, `managed_tmp_reap`, and
  `disk_pressure` every hour" reads naturally.
- A person's daily routine really does contain several activities on a cadence, so
  "a routine contains jobs" is not backwards. The earlier reports overstated that
  objection.

Arguments against:

- **A live collision in the agent's own toolchain.** In Claude Code, a routine is "a
  saved Claude Code configuration: a prompt, one or more repositories, and a set of
  connectors … run automatically," triggered by a schedule, an API call, or GitHub
  events. Each run creates a new session. That is the counterpart of a **SASE job that
  launches an agent**, not a SASE routine. Every Claude-run SASE agent sees the
  `/schedule` ("routines") skill in its context. An agent asked to "add a routine" will
  reach for the wrong mechanism.
- **The runtime boundary is hidden.** A SASE routine is a supervised process with its
  own PID, state, restarts, and backoff. "The hooks routine crashed and was restarted"
  takes some explanation.
- **Descriptions contradict the name.** The shipped routine descriptions still call
  routines lanes: "Fast lane that…" (`default_config.yml:1010`), "the other lanes"
  (`:1014`), "dedicated lanes" (`:1146`). The docs call a routine an "individual
  scheduler loop."

Verdict: renaming again would cost more than it fixes. Mitigate instead:

- Write "scheduler routine" in every agent-facing skill and doc.
- Add a glossary line: *not a Claude Code routine; the closest SASE analogue to a Claude
  Code routine is a job whose result launches an agent.*
- Replace the "lane" wording in `default_config.yml`.

### 2.4 chop → job: endorse; the best of the scheduler set

This is the standard term, and the docs already explained chops as jobs. Use "job run"
for one execution. The remaining work is internal and dual-published: the
`src/sase/chops` package and SDK, `SASE_CHOP_*`, and the suppressed `sase axe chop`. That
is fine to do slowly.

### 2.5 agent family → agent session: endorse, with four caveats

**Why it is right.** "Family" implied genealogy: branching, siblings, parents with
several children. The concept is a strictly linear chain of members. "Family" also
collided with six other meanings in the codebase: Patch revert family, `model_family`,
`vcs_family`, provider-usage family, OS family, and CSS `font-family`. "Session" is the
word the ecosystem uses for "a durable conversation you can resume or fork." Claude's
Agent SDK defines a session as "the conversation history the SDK accumulates while your
agent works." It also pairs naturally with "turn" (§2.6).

I considered **"thread"** as an alternative:

- Codex app-server: "A thread is a conversation … that contains turns."
- LangGraph uses `thread_id`, and the Assistants API used Thread and Run.

I reject it. OS threads are everywhere in SASE's TUI and performance documentation
("UI thread," worker threads), and SASE's primary provider says "session."

The caveats:

1. **SASE already has user-facing "sessions"** (fix: R3). `src/sase/sessions/registry.py`
   is the "Registry of live SASE TUI sessions." `sase proc list` defaults to "the TUI
   session of this process" and takes `-s/--session REF`. The Procs tab shows a
   "session chip." `docs/ace.md:5165` says "A fresh session starts in metadata-only"
   when it means a new TUI launch. The plan freezes all of these. That keeps the
   identifier-level rule ("never bare `session` in identifiers") intact, but it leaves
   two user-visible meanings of one word, and the new meaning is the one users will
   type in queries (`session:`, `kind:session`).
2. **Agent session vs. provider session.** One SASE agent session can span several
   provider sessions:
   - `sase pipe --fresh` starts a clean context window;
   - a successor turn can switch provider or model;
   - `#fork` starts a new provider session.

   The glossary strand should say so in one sentence, and prose should always write
   "provider session" or "transcript" for the other meaning. The plan's
   `resolve_agent_session` → `resolve_agent_transcript` rename is the right instinct;
   make it a rule.
3. **"A single agent that does not belong to a session" is un-idiomatic.** Industry
   readers assume every agent run *is* a session, even one with a single turn. Suggested
   glossary framing: *every sase agent has an agent session, an ordered sequence of one
   or more turns. A single-turn session shares its name with its only turn. When a
   second turn attaches, the bare name becomes the **session container**.* This keeps
   today's behavior and the `kind:session` query (which matches containers) but removes
   the odd phrasing.
4. **The kinship ladder is broken.** Family, clan, and tribe read as widening kin
   groups. With "family" gone, clan, tribe, hood, and neighbor become an orphaned social
   vocabulary, the same situation lumberjack and chop were in after AXE was renamed. I
   looked hard for replacements (§5) and found none that is clearly more standard
   without colliding. Keep clan and tribe, but stop presenting them as a ladder:
   `docs/agent_families.md` is titled "Agent Clans, Families, and Tribes." Retitle it
   to something like "Agent Sessions, Clans, and Tribes," and describe them as
   independent grouping axes: sequence, parallel container, and label.

### 2.6 sase shell → sase turn: strongly endorse; the most valuable rename of the six

Why it is right:

- **"Shell" collides with the Unix shell everywhere in a CLI product.** Examples include
  `sh -c`, `shell=True`, shell completion, `$SHELL`, and "Shell cwd was reset." The
  earlier research compiled monitors to `["/bin/sh","-c",…]`, so a monitor was literally
  "a shell running in a shell."
- **"Turn" is already SASE's word for this unit** in the accepted decision records:
  - "A SASE agent run is exactly one provider turn" (`decisions:single-turn-agents`);
  - "A turn completes when the host's selected finalizers are satisfied"
    (`decisions:host-owned-completion`);
  - the gate glossary: "kills that agent's turn."

  The code agrees: `turn_nonce`, `SASE_FINAL_TURN_NONCE`, `finalizer_owned_turn`. The
  rename aligns the member noun with the rules that govern it.
- **The industry definition matches.** Codex app-server: "A turn is a single user
  request and the agent work that follows," with threads containing turns. OpenAI Agents
  SDK: a run "represents a single logical turn in a chat conversation."
- **Non-LLM turns fit.** Map them to chat roles: an **agent turn** is the assistant, a
  **monitor turn** is a tool result, and a **gate turn** is the human. A session
  alternating among those three is exactly how a chat transcript is structured. Put that
  analogy in the glossary strand.

Caveats for 0qi's plan:

1. **Claude's SDK uses "turn" at a different level.** In the Claude Agent SDK, "a turn
   is one round trip inside the loop": a tool-use cycle. `max_turns` and `num_turns`
   count those, so one SASE agent turn contains many Claude turns. SASE already reads
   `num_turns` (`src/sase/llm_provider/usage/_claude_support_windows.py:146`). Rule:
   never show a provider's `num_turns` as "turns" in SASE UI. Call it "model round
   trips" or "loop iterations."
2. **Split the two meanings of "shell."**
   - **Session members** (agent, monitor, gate) become turns.
   - **Named procs.** The proc store's `shell_name`/`shell_kind` fields
     (`src/sase/procs/request.py:40` defaults `shell_kind="proc"`;
     `src/sase/service/host_spawn.py:125` writes `shell_kind="service"`) and
     `sase proc list -N/--shell` belong to the named-proc concept. Rename that side to
     proc vocabulary (`name`, `--name`), not to `turn`. A service daemon is not a turn in
     anyone's session.
3. **Pick one noun for the command member.** Today it is both "proc shell" (99 hits)
   and "monitor" (the glossary says a session-attached proc shell *is* a sase monitor).
   Use **monitor turn** and retire "proc shell." Say "a monitor turn runs as a named
   proc" when the substrate matters.
4. **Avoid the double migration.** This is the most actionable point in the report.
   The session plan's vocabulary table introduces "session shell," `SESSION SHELLS`,
   "session-attached shell," `AgentSessionShellWire`, `agent_session_shell*` keys, and
   `--next-fork {session,shell,none}`. Every durable spelling it emits becomes a
   permanent legacy reader for the turn epic. Where sase-17m has not yet flipped
   emitted output (sase-17m.8 core-contract; the fleet-protocol and schema bumps), emit
   `agent_session_turn*`, `SESSION TURNS`, and `--next-fork {session,turn,none}`
   directly. Where Python writers (sase-17m.3) already emit `agent_session_shell`,
   accept it as a second legacy input. Do not add a third.
5. **Search hygiene.** "turn" is a substring of `return`, so every plain-substring audit
   will flood. Use `git grep -w`, `\bturns?\b`, and scoped identifier patterns in the
   exit-criteria greps.

---

## 3. New renames recommended

### R1. `sase pipe` → `sase handoff` (strong)

- **The metaphor is wrong.** A Unix pipe connects concurrently running processes that
  stream data. `sase pipe --help` itself says it is "not a launch, a monitor, or
  fan-out: one successor, serially." It ends one turn and starts the next. That is a
  handoff.
- **Industry standard.** In the OpenAI Agents SDK, handoffs are the primitive for
  transferring control to another agent that continues the conversation ("If the LLM
  requests a handoff, we update the current agent and input, and re-run the loop").
  LangGraph uses the same word. `sase pipe` does the same thing, with an optional model
  switch and optional clean context.
- **SASE already says "handoff".** Examples:
  - `sase pipe --help`: "hand-off summary," "after a successful hand-off"
  - `sase monitor --help`: "Hand a slow command off"
  - decision records: "a plan or questions handoff"
  - about 628 `handoff` lines across `src/`, `docs/`, and `tests/`: `maybe_handoff_monitor_from_agent`,
    `maybe_handoff_gate_from_agent`, `SHELL_HANDOFF_OUTCOMES`, `PendingHandoffError`
- **It completes the turn vocabulary.** Define **handoff** as "ending the current turn
  by starting the session's next turn." Then:
  - `sase handoff` hands off to an agent turn;
  - `sase monitor start` hands off to a monitor turn;
  - `sase gate create` hands off to a gate turn.

  One verb covers all three mechanisms that the single-turn decision exempts.
- **It is cheap, and now is the right time.** About 12 files mention `sase pipe` or
  `/sase_pipe`, plus one config key (`max_agent_pipe_chain`, `default_config.yml:73`,
  which becomes `max_handoff_chain`). The session and turn epics are already rewriting
  exactly this help text ("next family member," "family chain"). Keep `sase pipe` as a
  sunset alias.

### R2. "LLM Calls" panel → "Tool Calls" (strong)

- **The name misdescribes the rows.** The panel is "a chronological timeline of the LLM
  tool calls the selected agent has made — file reads, edits, bash invocations…"
  (`docs/ace.md:5497`). Its header counts calls and failures, and its empty state says
  "No tool calls recorded." In standard observability vocabulary, an LLM call is the
  model inference itself. OpenTelemetry GenAI uses `chat` for a model call and
  `execute_tool` for a tool call; Langfuse and LangSmith use "generation" or "LLM run."
  The panel shows none of those.
- **SASE already uses the right term everywhere else.** The artifact is
  `tool_calls.jsonl`, and the beta Agent Decks feature calls the same content the
  "Tools" deck.
- **The "tool" collision is manageable.** The September 18 rename away from "agent
  tools" was presumably meant to avoid confusion with SASE's Tool Catalog and Tool Runs.
  The call/run split carries that distinction: *a tool call is what the model asked
  for; a Tool Run is what `sase tool run` recorded.* That is one glossary sentence. If
  you want to avoid the word "tool" entirely, "Trace" is the fallback, but it
  over-promises: the panel has no model spans.
- **Cost.** About 166 lines across `src/`, `docs/`, and `tests/`, mostly `docs/ace.md` and one glossary strand. The name is
  six days old, so almost nothing has built on it.

### R3. "TUI session" → "TUI instance" (strong; required by the session rename)

- **What changes:**
  - `sase.sessions` → `sase.tui_instances` (or keep the package and rename the
    concept);
  - `sase proc list -s/--session` → `-i/--instance`;
  - "session chip" → "instance chip";
  - TUI prose ("a fresh session starts…") → "a fresh TUI launch."
- **Why.** This removes the only user-visible meaning of "session" that competes with
  agent sessions. "Instance" is the standard word for one running copy of an app, and
  the registry already describes each record as "this process."
- **Cost.** Small: 7 importers of `sase.sessions`, one CLI flag (keep `--session` as a
  hidden alias), and a few docs lines. The sase-17m plan leaves "session" unqualified in
  exactly this place, so fold it into sase-17m.10's audit or a small follow-up epic.

### Scope corrections to the in-flight epics (not new concepts, but do them)

- Named-proc `shell_*` fields and `--shell` → proc `name` and `--name` (§2.6.2).
- Retire "proc shell"; use "monitor turn" (§2.6.3).
- `sase scheduler routine|job|maintenance`; `scheduler:` and `tui:` config roots with
  legacy `axe:` and `ace:` input (§2.1, §2.2).
- Remove the "lane" wording from the shipped routine descriptions (§2.3).

---

## 4. Optional candidates (moderate; only if you are already touching the surface)

| Candidate | Case for | Case against | Verdict |
| --- | --- | --- | --- |
| **agent hood → agent namespace** | The glossary defines a hood as the set of agents sharing a `<name>.` prefix, which is literally a namespace. `docs/agent_families.md` itself says clans "use that namespace rule." | 758 hits, including agents-sync internals (`HoodSnapshot`, `OwnerHoodEntry`) and user syntax (`%w(hood=…)`, `wait_for_hoods`). "Namespace" already has about 961 hits in other senses (xprompt namespaces and others). "Hood/neighbor" is short and memorable. | Optional. If done, keep "neighbors" for the TUI roster. |
| **mentor → review agent / review profile** | `docs/mentors.md:5`: "Mentors are automated AI code review agents." The industry calls this AI code review, and "mentor" suggests long-term guidance rather than per-commit findings. | `MENTORS:` is a section in durable `.sase` files, so this needs a data migration. "Reviewer" already means the human answering a gate and GitHub PR reviewers, and `@review` is a tribe. | Optional, low priority. Avoid bare "reviewer"; use "review agent." |
| **memory web / strand → memory collection / entry** | Every definition translates it ("a keyed note collection"). Astro content collections are a close precedent (`<collection>/<id>.md` addressed by collection plus id). "Web" highlights linking, but every memory can link; the actual distinction is keyed, on-demand addressing. | Each web already names its own entries (`strand_noun`: term, record), so the generic word rarely reaches users. The concept is new and backed by immutable decision records. | Skip unless you redesign memory webs. |

---

## 5. Considered and kept

- **Patch / stitch.** "Patch" is standard. "Stitch" is non-standard, but it shares a
  coherent sewing metaphor with Patch (a patch is sewn on with stitches). The standard
  alternatives collide: Gerrit's "patch set" conflicts with Patch, and "revision"
  conflicts with VCS and core revisions. Keep.
- **Bead.** It comes from Steve Yegge's *beads* (credited in `docs/acknowledgements.md`
  and the README), which is itself the precedent in agent tooling. Keep.
- **Xprompt.** The `xprompt_plang_rename` research holds: it is a count noun, a CLI
  namespace, and a config key, and the alternatives collide. Keep.
- **Gate.** "Approval gate" and "quality gate" are standard CI/CD vocabulary. LangGraph's
  `interrupt()` and the OpenAI SDK's "interruptions" name a pause, not a durable
  decision record with commands. Keep.
- **Monitor.** It collides with Claude Code's built-in `Monitor` tool, which streams
  events into a live session: the opposite of ending the turn. The SASE skill already
  says to use it "INSTEAD of any built-in monitor." With "monitor turn" as the member
  noun and `sase monitor` as the CLI, the collision is contained. Keep, and always write
  "sase monitor" or "monitor turn" in agent-facing text.
- **Clan.** Standard alternatives don't fit:
  - "Group" collides with saved agent groups.
  - "Swarm" is already the name of the xprompt that fans out, and epic phase workers
    (who are clan members) are not a swarm.
  - "Team" implies a lead and messaging, as in Claude Code agent teams; clans are
    rootless and execution-neutral.

  Keep.
- **Tribe.** It is a user-facing label, but it was moved off "tag" in July because
  "tag" had about ten other meanings. "Label" has the same problem (monitor labels,
  proc labels, display labels). Keep.
- **Others kept:** proc, service, service proc, oneshot, workspace, artifact and ref,
  fork, finalizer, doctor, fleet, and usage window are all standard or self-explanatory.
- **Dismiss/revive** could become "archive/restore," the term Claude, Codex, and ChatGPT
  use. But "archive" is already the terminal Patch state (`-archive.sase`) and
  `sase restore` restores Patches. Not worth it.
- **"Orchestrator"** (the scheduler's parent process) can stay. Say "supervises" in
  prose so readers don't confuse it with agent orchestration.

---

## 6. Summary

### Critique of the renames already done or coming soon

| Rename | Verdict | Main caveat |
| --- | --- | --- |
| ACE → TUI (`sase tui`) | ✅ Good | `ace:` config root and "sase's TUI" prose remain; don't rename the `sase.ace` package wholesale. |
| AXE → scheduler | ✅ Good, unfinished | `routine`/`job`/`maintenance` only exist under `sase axe`; the `axe:` config root and 158 "AXE" doc tokens remain. |
| lumberjack → routine | ⚠️ Defensible, weakest | Collides with Claude Code routines (≈ a SASE job that launches an agent); config descriptions still say "lane." Keep, and write "scheduler routine." |
| chop → job | ✅ Best of the scheduler set | Internal `chops` package/SDK and env vars can migrate slowly. |
| agent family → agent session | ✅ Good | Rename the existing "TUI session" (R3); define agent session vs. provider session; define single-turn sessions; stop presenting clan/tribe as a kinship ladder. |
| sase shell → sase turn | ✅✅ Best of all six | Don't let sase-17m ship durable `agent_session_shell*` keys and schema bumps that the turn epic must then migrate again. Keep named-proc `shell_*` out of "turn." Use "monitor turn," not "proc turn." Qualify Claude's `num_turns`. |

### Recommended new renames

1. **`sase pipe` → `sase handoff`** (skill `/sase_handoff`; config
   `max_agent_pipe_chain` → `max_handoff_chain`; keep `pipe` as a sunset alias). Fold
   it into the turn epic, which rewrites the same help text anyway.
2. **"LLM Calls" → "Tool Calls"** (TUI panel, picker, docs, glossary strand). Add the
   glossary line "tool call ≠ Tool Run."
3. **"TUI session" → "TUI instance"** (`sase.sessions` concept, `sase proc list
   --session` → `--instance`, session chip → instance chip).

Optional, if you are already in those files: **hood → namespace**, **mentor → review
agent**. Everything else should keep its name.

---

## Sources

External definitions (accessed 2026-09-24):

- Codex App Server: threads, turns, items. <https://developers.openai.com/codex/app-server>
  and <https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md>
- OpenAI Agents SDK, running agents (a run is "a single logical turn"; handoffs re-run
  the loop). <https://openai.github.io/openai-agents-python/running_agents/>
- OpenAI Agents SDK, handoffs. <https://openai.github.io/openai-agents-python/handoffs/>
- OpenAI Agents SDK, human-in-the-loop approvals and interruptions.
  <https://openai.github.io/openai-agents-js/guides/human-in-the-loop/>
- Claude Agent SDK, sessions (definition; resume and fork).
  <https://code.claude.com/docs/en/agent-sdk/sessions>
- Claude Agent SDK, agent loop ("A turn is one round trip inside the loop";
  `max_turns`, `num_turns`). <https://code.claude.com/docs/en/agent-sdk/agent-loop>
- Claude Code routines. <https://code.claude.com/docs/en/routines>
- Claude Code agent teams. <https://code.claude.com/docs/en/agent-teams>
- LangGraph interrupts. <https://docs.langchain.com/oss/python/langgraph/interrupts>
- OpenTelemetry GenAI observability (`chat` vs. `execute_tool` operations).
  <https://opentelemetry.io/blog/2026/genai-observability/>

Internal (audited reads):

- `bead:sase-17m`, `bead:sase-17m.8`
- `plan:202609/agent_session_rename.md`
- `plan:202607/agent_tribe_terminology.md`
- `research:202609/scheduler_tui_naming/scheduler_tui_naming.md`
- `research:202609/scheduler_loop_naming_reassessment.md`
- `research:202608/naming_the_change_unit/naming_the_change_unit.md`
- `research:202608/sase_shell_named_procs/sase_shell_named_procs.md`
- `research:202607/xprompt_plang_rename_consolidated.md`
- glossary web; `decisions:single-turn-agents`; `decisions:host-owned-completion`
- agent `0qi`'s submitted prompt (its artifacts directory)
