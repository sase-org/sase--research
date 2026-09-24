# SASE terminology renames: critique and further recommendations

_Consolidated report · 2026-09-24 · merges researchers `cld`, `mus`, and `gem` with lead
verification · sase `master` @ `71fff39d1`_

Source reports (same directory): `sase_terminology_renames__cld.md`,
`sase_terminology_renames__mus.md`, `sase_terminology_renames__gem.md`.

## Bottom line

None of the renames should be reverted. Ranked by strength:

1. **sase shell → sase turn** is the best rename.
2. **chop → job** and **ACE → TUI** are clean wins.
3. **AXE → scheduler** is right but only half-finished on the CLI.
4. **agent family → agent session** is good. It is not the weakest rename, as `mus`
   argued. It does leave a user-visible second meaning of "session" to clean up.
5. **lumberjack → routine** is the weakest. It collides with Claude Code's own
   "routines," a feature every Claude-run SASE agent sees in its context. Keep it and
   mitigate the collision.

The single most time-sensitive finding: **as currently sequenced, the turn rename forces
a second schema and fleet-protocol migration.**

- Agent `0qi` (shell → turn) is parked with `wait_for_beads: ["sase-17m"]`. It will
  start only after the whole session epic closes.
- The session epic's core-contract phase (`sase-17m.8`) has not started yet. When it
  runs, it will make `agent_session_shell*` keys, `SESSION SHELLS`, and
  `--next-fork {session,shell,none}` the emitted, schema-bumped contract.
- Python writers in 43 files under `src/` and `tests/` already use
  `agent_session_shell` spellings.
- The turn epic would then need another bump, another fleet-protocol bump, and legacy
  readers that accept three spellings forever.

Amend `sase-17m.8` now so it emits the `turn` spellings, while that phase is still
unstarted.

**Recommended new renames**, each with strong justification in §4:

| # | Today | Rename to | Why, in one line |
| --- | --- | --- | --- |
| R1 | `sase pipe` / `/sase_pipe` | **`sase handoff`** / `/sase_handoff` | It is a serial control handoff, not a Unix pipe. The industry calls this a handoff, and SASE's own help text already does. |
| R2 | "TUI session" (`sase proc list -s/--session`, session chip, `sase.sessions`) | **"TUI instance"** | After sase-17m, this is the only remaining user-facing "session" that isn't an agent session. |
| R3 | "LLM Calls" panel | **"Tool Calls"** | The rows are tool invocations. An "LLM call" is the model inference itself in every observability standard. |

Plus four "finish the job" items that are not new concepts (§5): split the named-proc
meaning of "shell" off from turns, finish the scheduler CLI, retire the `task` alias on
`sase proc`, and clean up leftover `ace:`/`axe:`/"lane" wording.

---

## 1. How renames were judged

A rename had to clear these tests:

1. **Meaning match.** The new word's industry meaning matches SASE's meaning, not just
   its general shape.
2. **The definition stops translating.** If the glossary has to say "an X is basically
   a Y," then Y is probably the name.
3. **No new collision.** This covers:
   - other SASE meanings of the word;
   - Unix/CLI vocabulary;
   - the agent's own harness. A SASE term that means something different from a
     built-in tool or skill the agent can see is a practical hazard, not just a
     theoretical one.
4. **Cost and timing.** Durable keys, typed user syntax, and `.sase` data are expensive
   to change. Prose and labels are cheap. A rename is cheapest when it rides an epic
   that already rewrites the same surface.

Stylistic dislike alone was not enough to recommend a rename.

## 2. Where the three reports disagreed, and how it was resolved

| Question | cld | mus | gem | Resolution (lead-verified) |
| --- | --- | --- | --- | --- |
| Is family → session sound? | Good, with caveats | Weakest of the set; driven by tone | Outstanding | **Good.** mus's "six incumbent meanings of session" is real, but "family" had at least as many: the sase-17m plan's keep-list covers `model_family`, provider-usage `family:`, `vcs_family`, Patch revert family, `font-family`, and OS family. The industry also backs the exact shape: the OpenAI Agents SDK defines sessions as memory that maintains "conversation history across multiple agent runs." The residual cost is one user-facing collision (R2). |
| Weakest rename? | lumberjack → routine | family → session | none | **lumberjack → routine.** Verified: Claude Code routines are "a saved Claude Code configuration: a prompt, one or more repositories, and a set of connectors," fired by schedule, API, or GitHub, and "each run creates a new session." That is a SASE *job that launches an agent*, not a SASE routine. This session's own skill list advertises `/schedule` as "scheduled cloud agents (routines)." |
| tribe → tag or label? | Keep | → label | → tag ("restores the pre-kinship term") | **Keep.** gem's history is wrong. `tribe` replaced both "agent groups" and "tags" (`plan:202607/agent_clans_families_tribes.md`) because the vocabulary was free. The tribe terminology plan explicitly keeps about nine other meanings of "tag": VCS, xprompt role, frontmatter, notification/gate, ChangeSpec footer, release, YAML/serde, telemetry, and `SASE_AGENT`. "Label" has about 11k occurrences in this repo. |
| clan → ? | Keep | Merge clan and hood into "agent group" | → swarm or team | **Keep.** "Group" means saved agent groups and was the retired `%group` directive for exactly this concept. "Swarm" is already the glossary's *Xprompt Swarm*, the fan-out launcher that *produces* a clan; epic phase workers are clan members but not a swarm. "Team" collides with Claude Code agent teams, which have a lead and messaging, while clans are rootless and execution-neutral. |
| hood → namespace? | Optional | → "name prefix" | → namespace | **Optional (§6).** It is the only kinship term with an exact standard equivalent, and the docs already say clans use "that namespace rule." It is also user syntax (`%w(hood=…)`, `%hold(hood=…)`, `sase agent sync` "agent hoods"), and the payoff is modest. |
| xprompt → skill? | Keep | → skill | not raised | **Keep.** In SASE, "skill" already names the generated, provider-facing slash command *derived from* an xprompt. Merging the source layer with its build output would create the collision mus wants to remove. Many xprompts are not skills: inline `#name` references, `#!` YAML workflows, fan-out swarms. `research:202607/xprompt_plang_rename_consolidated.md` reached the same taxonomy: prompt, xprompt, workflow, directive, skill. |
| stitch → revision or commit? | Keep | Keep | → revision or commit | **Keep.** "Commit" is wrong: the glossary says a stitch "need not have a commit" (proposal IDs such as `(2a)`). "Revision" means a single commit in Mercurial and Jujutsu, but the whole review unit in Phabricator. That is the ambiguity the change-unit research warned about. "Revision" is also already live SASE vocabulary (`sase-core-revision.txt`). |
| `sase pipe` → handoff? | Strong | not raised | Strong | **Strong (R1).** Verified in §4. |
| LLM Calls → Tool Calls? | Strong | Keep ("precise read-model term") | not raised | **Recommend (R3).** The panel's own docs say it shows "the LLM tool calls the selected agent has made," read from `tool_calls.jsonl`. mus's "precise" claim does not survive a check against industry vocabulary (§4). |
| `proc (task)` alias | not raised | not raised | Deprecate | **Agree.** It is a leftover of the completed sase-lh "Background Tasks → Procs" epic, and "task" is the bead-tier noun (§5). |

gem also cited industry claims that did not hold up and are dropped here:

- "The OpenAI Assistants API calls interactions within a thread a session." The
  Assistants API used Thread and Run.
- "Cursor, Aider, and Cline universally say agent session." This was unsourced.

Better sources are cited in §3.

## 3. Critique of the implemented and in-flight renames

### 3.1 ACE → TUI: endorse; finish the leftovers

`sase tui` explains itself. "Agentic Change Explorer" no longer described a surface
whose tabs are Agents, Artifacts, and Services.

Leftovers:

- **Config root.** It is still `ace:` (`src/sase/default_config.yml:276`). Add a `tui:`
  root in config composition, accept `ace:` as legacy input, and sunset it.
- **The team's own vocabulary hasn't moved.** Phase `sase-17m.5` is titled "ACE agent
  session surfaces," the sase-17m plan says "ACE" throughout, and today's commits use
  `feat(ace)` and `feat(ace-tui)` scopes. New plans and commit scopes should say TUI.
- **Keep the `src/sase/ace/` package name.** It holds Patch, query, and hook domain
  code, not only the TUI. Earlier research reached the same conclusion.

### 3.2 AXE → scheduler: endorse; the rename is half-finished

"Scheduler" is accurate and guessable. However, the routine and job tree exists only
under the legacy name:

- `sase axe` has `job`, `routine`, and `maintenance`.
- `sase scheduler` has only `restart`, `run`, `start`, `status`, and `stop`.

A user following the new name hits a dead end. Also:

- The config root is still `axe:` (`default_config.yml:998`).
- `docs/` still contains 154 "AXE" tokens.
- Add one glossary sentence to separate the two kinds of "scheduling": *the scheduler
  runs jobs; runner admission decides when an agent launch may start.*

### 3.3 lumberjack → routine: weakest; keep it, but mitigate

In favor:

- "The housekeeping routine runs three jobs every hour" reads naturally.
- A routine really does contain several activities on a cadence.

Against:

- **Harness collision (verified).** A Claude Code routine is a scheduled or triggered
  agent run: the analogue of a SASE job whose result launches an agent. A Claude-run
  SASE agent asked to "add a routine" has a built-in `/schedule` ("routines") skill in
  view and may reach for the wrong mechanism.
- **The process boundary is hidden.** A SASE routine is an independently supervised
  process with its own PID, restarts, and backoff. Some readers still hear "routine" as
  "subroutine."
- **The shipped config contradicts the name.** Routine descriptions still call routines
  lanes: "Fast lane that…" (`default_config.yml:1011`), "the other lanes" (`:1015`),
  "their dedicated lanes" (`:1147`).

Verdict: renaming again would cost more than it fixes. Mitigate instead:

- Write "scheduler routine" in every agent-facing skill and doc.
- Add a glossary line: *not a Claude Code routine; the nearest SASE analogue of one is a
  job that launches an agent.*
- Remove the "lane" wording.

### 3.4 chop → job: endorse; the best of the scheduler set

"Job" is the standard term (cron, CI, Kubernetes, and Slurm jobs), and the docs already
explained chops as jobs. Use "job run" for one execution. The internal `chops` package,
the SDK, `SASE_CHOP_*`, and the suppressed `sase axe chop` can migrate slowly.

### 3.5 (Not in your list) background tasks → procs: endorse; retire the alias

The sase-lh epic landed a month ago and deliberately kept `task` as a legacy alias:
`sase --full-help` shows `proc (task)`. "Task" is now the bead tier users and agents
type (`sase bead create -T "task(bug)"`), so `sase task` landing in process control is a
live trap. Sunset the alias (§5).

### 3.6 agent family → agent session: endorse, with four caveats

**Why it is right.**

- "Family" implied genealogy: branching, siblings, parents with several children. The
  concept is a strictly linear chain.
- "Family" also carried many unrelated meanings, which the plan's keep-list enumerates.
- "Session" is the ecosystem word for a durable, resumable conversation spanning
  several runs:
  - the OpenAI Agents SDK: sessions "maintain conversation history across multiple
    agent runs";
  - Google ADK: "a single, ongoing interaction";
  - the Claude Agent SDK: session resume and fork.
- It pairs naturally with "turn" (§3.7).

I rejected "thread" (Codex app-server: "Threads contain turns"; LangGraph `thread_id`)
as the alternative. SASE's TUI and performance docs use OS "threads" everywhere, and
SASE's primary provider says "session."

**Caveats (all verified):**

1. **A competing user-facing "session" survives.** The plan deliberately leaves TUI
   sessions untouched: `src/sase/sessions/` is the "Registry of live SASE TUI sessions,"
   and `sase proc list` defaults to "the TUI session of this process" and takes
   `-s/--session REF`. After the rename, `sase proc list --session latest` reads as
   "procs of the latest agent session." Fix: **R2**.
2. **Agent session vs. provider session.** One SASE agent session spans several
   provider sessions:
   - each agent turn is its own provider run;
   - `sase pipe --fresh` starts a clean context window;
   - a successor may switch model or provider.

   In Claude Code's vocabulary a session *contains* turns. In SASE, each agent turn is
   itself a whole provider session. State this inversion once in the glossary strand,
   and always write "provider session" or "transcript" for the other meaning. The
   plan's `resolve_agent_session` → `resolve_agent_transcript` rename is the right
   instinct; make it the rule.
3. **"Sase agent" and "agent session" now overlap.** The glossary says a sase agent "is
   an agent family or a single agent that does not belong to a family. It owns an
   ordered sequence of sase shells." After both renames, that becomes "a sase agent owns
   an ordered sequence of turns," which *is* the industry definition of a session.
   "A single agent that does not belong to a session" will read as a contradiction to
   industry readers.

   Reframe the glossary: *every sase agent has one agent session: its ordered sequence
   of one or more turns. A single-turn session shares its name with its only turn; when
   a second turn attaches, the bare name becomes the **session container**.* Runtime
   behavior and the `kind:session` query (which matches containers) are unchanged; only
   the definition stops contradicting the industry meaning.
4. **The kinship ladder is orphaned.** With "family" gone, clan, tribe, hood, and
   neighbor read as a leftover social metaphor, the same situation lumberjack and chop
   were in once AXE was renamed. §2 shows no standard replacement for clan or tribe
   that doesn't collide. So keep the words, but stop presenting them as a ladder.
   `docs/agent_families.md`, titled "Agent Clans, Families, and Tribes," should become
   something like "Agent Sessions, Clans, and Tribes," describing three independent
   grouping axes: sequence (session), parallel container (clan), and label (tribe).

mus's closing advice stands and is worth making a rule: **never extend "session" to any
further concept, and never use bare `session` in identifiers or keys.**

### 3.7 sase shell → sase turn: strongly endorse; the best rename of all

**Why it is right:**

- **"Shell" collides with the Unix shell everywhere in a CLI product:** `sh -c`,
  `shell=True`, shell completion, `$SHELL`. A monitor was literally a shell running in a
  shell.
- **"Turn" is already SASE's word for this unit** in the accepted decision records: "A
  SASE agent run is one provider turn" (`decisions:single-turn-agents`), and completion
  is defined per turn (`decisions:host-owned-completion`). The gate and monitor glossary
  entries already say they "kill that agent's turn," and the code has `turn_nonce` and
  `SASE_FINAL_TURN_NONCE`.
- **The industry definition matches exactly.** Codex app-server: a turn is "a single
  user request and the agent work that follows," and "threads contain turns."
- **Non-LLM turns fit through the chat-role analogy:**
  - an **agent turn** is the assistant speaking;
  - a **monitor turn** is a tool result arriving;
  - a **gate turn** is the human's move.

  A session alternating among the three is structured like a chat transcript. Put this
  analogy in the glossary strand; it answers mus's "turn is a stretch for procs and
  gates" objection.

**Caveats for 0qi's plan:**

1. **Avoid the double migration** (see Bottom line). This is the most actionable item in
   the report. `sase-17m.8` has not started; add the turn spellings to it now.
   - Serialized keys: `agent_session_turn*`, not `agent_session_shell*`.
   - Labels: `SESSION TURNS`.
   - Flags: `--next-fork {session,turn,none}`.
   - Python writers that already emit `agent_session_shell` become a second legacy
     input.

   Two legacy readers are acceptable; three are not.
2. **Split the two meanings of "shell."** The proc store's `shell_name`/`shell_kind`
   fields name *any* named proc:
   - `src/sase/service/host_spawn.py:125` writes `shell_kind="service"`;
   - stand-alone xprompt procs are proc shells with no session (task bead `sase-sa`).

   A mechanical shell → turn replacement would call the scheduler daemon a "turn."
   Only session members become turns. Named procs keep proc vocabulary: `shell_name` →
   `name`, and `sase proc list -N/--shell` → `--name`.
3. **One noun for the command member.** Today it is both "proc shell" (107 mentions)
   and "monitor." Use **monitor turn** and retire "proc shell." Do not introduce "proc
   turn," which mus and gem both floated.
4. **Two granularities of "turn."** In the Claude Agent SDK, "a turn is one round trip
   inside the loop," and `num_turns`/`max_turns` count tool-use cycles. SASE reads
   `num_turns` (`src/sase/llm_provider/usage/_claude_support_windows.py`). Never display
   a provider's `num_turns` as "turns"; call it "model round trips."
5. **Search hygiene.** "turn" is a substring of `return`. Exit-criteria greps must use
   `git grep -w` or `\bturns?\b`.

---

## 4. Recommended new renames

### R1. `sase pipe` → `sase handoff` (strong)

- **The metaphor is wrong.** A Unix pipe streams bytes between *concurrent* processes.
  `sase pipe --help` itself says it is "not a launch, a monitor, or fan-out: one
  successor, serially." It ends one turn and starts the next.
- **It is the industry term.** The OpenAI Agents SDK: "Handoffs allow an agent to
  delegate tasks to another agent," and the new agent continues the conversation.
  LangGraph and AutoGen use the same word. `sase pipe` does this, with an optional model
  switch and optional fresh context.
- **SASE already says "handoff":**
  - `sase pipe --help`: "hand-off summary," "after a successful hand-off";
  - `sase monitor`: "Hand a slow command off";
  - the core instructions: "a plan, monitor, pipe, or questions handoff";
  - code: `_pipe_handoff_json`, `maybe_handoff_monitor_from_agent`,
    `PendingHandoffError`;
  - roughly 700 lines across `src/`, `docs/`, and `tests/`.
- **It completes the turn vocabulary.** Define **handoff** as "ending the current turn
  by starting the session's next turn." Then one verb covers all three exemptions in
  `decisions:single-turn-agents`:
  - `sase handoff` hands off to an agent turn;
  - `sase monitor start` hands off to a monitor turn;
  - `sase gate create` hands off to a gate turn.
- **It is cheap now.**
  - About 15 files in `src/` and `docs/` mention `sase pipe` or `/sase_pipe`.
  - One config key: `max_agent_pipe_chain` (`default_config.yml:73`) →
    `max_handoff_chain`.
  - The session and turn epics are already rewriting this exact help text ("next family
    member," `<family>--review`).

  Keep `sase pipe` as a sunset alias and fold the rename into the turn epic.

### R2. "TUI session" → "TUI instance" (strong; forced by R-session)

- **What changes:**
  - `sase proc list -s/--session` → `-i/--instance` (keep `--session` as a hidden
    alias);
  - "session chip" → "instance chip";
  - the `sase.sessions` concept → TUI instances (renaming the package is optional);
  - prose such as "a fresh session starts…" → "a fresh TUI launch."
- **Why.** This is the only remaining user-visible meaning of "session" that competes
  with agent sessions, and it lives in the same query and CLI space users type into
  (`session:`, `kind:session`). "Instance" is the standard word for one running copy of
  an application, and the registry already describes each record as "this process."
- **Cost.** Small: one CLI flag, one chip label, a handful of importers, and docs. Fold
  it into `sase-17m.10`'s audit or a small follow-up. (The plan's "never bare `session`
  in identifiers" rule already keeps it out of code keys.)

### R3. "LLM Calls" → "Tool Calls" (strong, but reverses a six-day-old choice)

- **The label misdescribes the rows.** The panel is "a chronological timeline of the LLM
  tool calls the selected agent has made — file reads, edits, bash invocations, web
  fetches, sub-agent launches" (`docs/ace.md:5497`). In standard GenAI observability,
  an LLM call is the model inference itself:
  - OpenTelemetry GenAI separates `chat` (the model call) from `execute_tool`;
  - LangSmith and Langfuse call inference an LLM run or a generation.

  This panel shows no inference spans at all.
- **Every other layer already says "tool call":**
  - the artifact is `tool_calls.jsonl`;
  - the config block is `ace.tool_calls`;
  - the record type is `ToolCallEntry`;
  - the picker key is still `t`.

  The rename plan itself concedes that "LLM Calls are still provider tool calls." The
  label is the only layer out of step.
- **Handle the motivating collision with one glossary sentence.** The September rename
  avoided "tool" so the panel would not be confused with the `sase tool` control plane.
  The call/run split already carries that distinction: *a tool call is what the model
  asked for; a Tool Run is what `sase tool run` recorded.* The planned Bash-call → Tool
  Run linkage will need exactly that sentence anyway ("this tool call started that Tool
  Run").
- **Cost.** The user-facing label is about 170 lines, mostly `docs/ace.md`, one
  glossary strand, and goldens. The internal `llm_calls` package and widget namespace
  touch about 120 files in `src/` and `tests/`. Those can follow in the same change or
  later, since they are presentation-internal with no persisted state. Almost nothing
  has built on the new name yet. If you want to avoid the word "tool"
  entirely, "Activity" is the fallback. It is honest, but less standard.

---

## 5. Finish-the-job items (existing renames, not new concepts)

1. **Named-proc "shell" → proc vocabulary** (§3.7 caveat 2): `shell_name`/`shell_kind`
   → `name`/`kind`, and `--shell` → `--name`. Scope this into 0qi's plan explicitly.
2. **Retire "proc shell"** in favor of "monitor turn" (§3.7 caveat 3). This also closes
   task bead `sase-sa` (stale proc-shell glossary).
3. **Scheduler CLI parity.** Add `sase scheduler routine|job|maintenance`, make
   `sase axe` a pure alias, and add a `scheduler:` config root with `axe:` accepted as
   legacy.
4. **`tui:` config root** with `ace:` accepted as legacy. Say "TUI" in new plans, phase
   titles, and commit scopes.
5. **Remove "lane" from the shipped routine descriptions** and add the "not a Claude
   Code routine" glossary line.
6. **Sunset `task` as an alias of `sase proc`**, behind a sunset flag per
   `sase_flags.md`, so `task` means only the bead tier.

---

## 6. Considered and not recommended

| Candidate | Verdict | Reason |
| --- | --- | --- |
| hood → namespace, neighbor → peer | **Optional** | It is the one exact standard equivalent: a dotted-prefix group *is* a namespace, and the docs already say "namespace rule." Against it: typed syntax (`hood=` in `%wait`/`%hold`), agents-sync internals, about 1.5k mentions, and "namespace" is already used for xprompts (`#memory/foo`). Do it only if you revisit those directives. |
| tribe → tag or label | Keep | See §2. Both alternatives are heavily overloaded in this codebase. mus's Spotify-"tribe" point is real but mild, since a Spotify tribe also groups work across squads. |
| clan → group, swarm, or team | Keep | See §2: each collides with a live SASE or Claude Code concept. |
| xprompt → skill or slash command | Keep | See §2: "skill" names the derived artifact, and not every xprompt is a skill. The `x` is opaque, but the earlier research answered that by keeping the noun and optionally naming the grammar "SASE Prompt Language." |
| stitch → revision or commit | Keep | See §2. Patch and stitch form a coherent sewing pair, and stitches rarely surface to users. |
| memory web/strand → collection/entry | Keep for now | The definitions do translate ("a keyed note collection"). But the concept is about a month old (August 24), backed by accepted decision records (`decisions:memory-webs`), and each web names its own entries (term, record), so the generic word rarely reaches users. Revisit only in a memory-web redesign. |
| bead → issue or ticket | Keep | It is a proper-noun primitive inherited from Steve Yegge's *beads*, which is itself the agent-tooling precedent. The rename cost is enormous. Add a one-line onboarding gloss: "a bead is SASE's git-native issue." |
| mentor → review agent | Optional, low | `docs/mentors.md` calls mentors "automated AI code review agents," and "mentor" suggests long-term coaching. But `MENTORS:` is a durable `.sase` section, and "reviewer" already means the gate human and PR reviewers. Avoid bare "reviewer" if you ever do this. |
| **tale** (plan tier; new finding, not raised by any researcher) | Keep the name; fix two gaps | "Tale" (1.7k mentions; 23 of the last 40 plans) pairs with "epic" the way Jira's "story" does, and "story" would import user-story and story-point baggage that does not apply to a one-agent implementation plan. Two real gaps: (1) **Tale, Epic, and the plan tiers are missing from the glossary.** (2) **The tier vocabulary disagrees with itself.** Plan files say `tier: tale`, but a committed tale's bead reports `Tier: plan` (for example `sase-5s`), and the TUI also uses `plan` to mean "approved without an SDD commit." Make the bead tier say `tale`. |
| gate, monitor, proc, patch, workspace, artifact/ref, hold, drain, fleet, doctor, finalizer, usage window, oneshot | Keep | Each is standard or self-explanatory: approval/quality gate, Slurm-style job hold, Kubernetes drain, systemd oneshot. For **monitor**, always write "sase monitor" or "monitor turn" in agent-facing text, because Claude Code ships a built-in `Monitor` tool with the opposite, stay-alive contract. |
| dismiss/revive → archive/restore | Keep | "Archive" is already the terminal Patch state, and `sase restore` restores Patches. |

---

## 7. Summary

### Critique of the renames already done or coming soon

| Rename | Verdict | Main caveat |
| --- | --- | --- |
| ACE → TUI | ✅ Good | The `ace:` config root remains, and new plans and commit scopes still say "ACE." Keep the `sase.ace` package name. |
| AXE → scheduler | ✅ Good, unfinished | `routine`/`job`/`maintenance` exist only under `sase axe`. The `axe:` root and 154 "AXE" doc tokens remain. |
| lumberjack → routine | ⚠️ Weakest; keep | Collides with Claude Code routines, which correspond to a SASE job that launches an agent. Config still says "lane." Write "scheduler routine" and add a glossary disclaimer. |
| chop → job | ✅ Best of the scheduler set | Internal `chops` package, SDK, and env vars can migrate slowly. |
| background tasks → procs | ✅ Good | Sunset the `task` alias, which now collides with task beads. |
| agent family → agent session | ✅ Good (not weakest) | Rename "TUI session" (R2). Define agent session vs. provider session. Reframe the glossary so every sase agent *has* a session. Stop presenting clan/tribe as a kinship ladder. Never extend "session" further. |
| sase shell → sase turn | ✅✅ Best of all | Emit turn spellings in `sase-17m.8` to avoid a second schema/fleet migration. Keep named-proc `shell_*` out of "turn." Use "monitor turn," not "proc turn." Never show Claude's `num_turns` as turns. |

### Recommended new renames

1. **`sase pipe` → `sase handoff`** (`/sase_handoff`, `max_agent_pipe_chain` →
   `max_handoff_chain`, with `pipe` as a sunset alias). Fold it into the turn epic.
2. **"TUI session" → "TUI instance"** (`sase proc list --session` → `--instance`,
   session chip → instance chip). Fold it into `sase-17m.10` or a small follow-up.
3. **"LLM Calls" → "Tool Calls"**, plus the glossary line "tool call ≠ Tool Run."

Optional if you are already in those files: **hood → namespace**, **mentor → review
agent**. Everything else should keep its name.

---

## Sources

External (accessed 2026-09-24):

- OpenAI Agents SDK, sessions ("conversation history across multiple agent runs"):
  <https://openai.github.io/openai-agents-python/sessions/>
- OpenAI Agents SDK, handoffs: <https://openai.github.io/openai-agents-python/handoffs/>
- Google ADK, sessions ("a single, ongoing interaction"): <https://adk.dev/sessions/>
- Codex app-server, threads/turns/items: <https://learn.chatgpt.com/docs/app-server>
- Claude Code routines: <https://code.claude.com/docs/en/routines>
- Claude Agent SDK, agent loop (turn = one round trip; `num_turns`) and sessions (via
  `cld`): <https://code.claude.com/docs/en/agent-sdk/agent-loop>,
  <https://code.claude.com/docs/en/agent-sdk/sessions>
- OpenTelemetry GenAI observability (`chat` vs. `execute_tool`; via `cld`):
  <https://opentelemetry.io/blog/2026/genai-observability/>

Internal (audited reads and live checks at `71fff39d1`):

- `bead:sase-17m`, `bead:sase-17m.8`, `bead:sase-lh`, `bead:sase-5s`
- `plan:202609/agent_session_rename.md`, `plan:202609/llm_calls_rename.md`
- `plan:202607/agent_tribe_terminology.md`,
  `plan:202607/agent_clans_families_tribes.md`
- `research:202607/xprompt_plang_rename_consolidated.md`
- `research:202608/naming_the_change_unit/naming_the_change_unit.md`
- Glossary strands: agent-hood, agent-shell, agent-family, agent-clan, agent-tribe,
  sase-agent, sase-shell, proc-shell, gate-shell, sase-monitor, llm-calls, stitch,
  sase-scheduler, lumberjack/routine, xprompt-swarm
- `sase_beads.md` reference memory
- Agent `0qi` state (`wait_for_beads: ["sase-17m"]`)
- Live CLI help: `sase --full-help`, `sase pipe`, `sase axe`, `sase scheduler`,
  `sase proc list`, `sase bead create`
