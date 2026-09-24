# SASE terminology rename critique: completed, in-flight, and candidate renames

Researcher: mus (independent swarm report, `__mus` suffix).
Date: 2026-09-24. Context: epic bead `sase-17m` (agent family → agent session),
agent `0qi` (sase shell → sase turn), and the earlier
axe → scheduler, lumberjack → routine, chop → job, ace → tui renames.
Method: read the `sase-17m` plan and epic, the live glossary strands, CLI help,
and the repo's own identifier/docs inventory; judged every term against (a) collision
with an established industry meaning, (b) collision with Unix/shell vocabulary, and
(c) cost of migration. A rename is recommended below only where (a) or (b) is
concrete and demonstrable, not merely stylistic.

## 1. Critique of renames already done or in flight

### 1.1 axe → scheduler: approve, strongest of the set

- Old term had no industry meaning (a chopping tool; faintly violent) and collided
  with nothing except the project's own lumberjack/chop metaphor cluster.
- New term matches the industry: `systemd` timers, cron-style schedulers, "scheduled
  routines/jobs" in every CI system, and the Services-tab "Scheduled Routines" panel
  that users already see. The glossary definition ("starts one process per routine,
  routines run jobs") now reads like any standard scheduler doc.
- Minor residual risk: bare "scheduler" also means OS process scheduler and
  Kubernetes-style schedulers, but the qualified `sase scheduler` form used in docs
  and CLI disambiguates adequately. Keeping `AXE` as a lookup alias (as done for
  lumberjack/chop) is the right sunset posture.
- Verdict: correct rename, keep.

### 1.2 lumberjack → routine, chop → job: approve both

- The old cluster (axe/lumberjack/chop) was whimsical and faintly violent; none of
  the three terms told a new user what the thing does. "One short, script-only unit
  of automation" is exactly what the industry calls a **job** (cron jobs, CI jobs,
  queue jobs), and "an independently supervised process that runs jobs on a fixed
  interval" is a defensible **routine** (cf. "daily routine", routine maintenance).
- `job` is the better half of the pair: unambiguous, searchable, standard.
  `routine` is slightly more generic (it can also mean "subroutine" to some
  readers), but inside the `scheduler → routine → job` hierarchy it is clear, and
  no better single word (daemon? worker? schedule?) fits without colliding with
  `service proc` vocabulary.
- Alias retention (lumberjack/chop as lookup aliases) is correct given state paths
  and legacy docs.
- Verdict: correct renames, keep.

### 1.3 ace → tui: approve

- `ace` was an opaque internal acronym with zero descriptive value and no industry
  currency; every competitor and docs site says TUI (Textual, Bubble Tea, k9s,
  lazygit all describe themselves as TUIs). `sase tui`, "the TUI", "Procs tab in
  sase's TUI" are immediately legible to any terminal-tool user.
- Cost was real (docs/ace.md, PNG goldens, keymap schema) but one-time and
  mechanical. No semantic collision is introduced: nothing else in the project is
  called a TUI.
- Verdict: correct rename, keep.

### 1.4 agent family → agent session: the weakest rename in the set, proceed with caution

- The motivation is understandable: "family" is folksy, non-standard, and its
  anthropological cluster (clan/hood/tribe/family) reads as insider jargon. Nobody
  outside SASE says "agent family" for a sequential chain of runs.
- But "session" is arguably the most overloaded noun in the project's vicinity,
  and the project's own plan admits it: phase `sase-17m.1` ("free the agent session
  name") exists precisely because `session` already meant provider transcript
  sessions (`session_id`), tmux sessions, TUI sessions (`sase.sessions`,
  `sase proc --session`), question sessions, proc sessions, snippet sessions, and
  usage windows. A rename whose first phase is de-collision against six incumbent
  meanings starts in debt.
- Industry check is also mixed. "Session" is standard for *an interactive
  connection or a transcript window* (Claude Code sessions, OpenAI conversations,
  tmux/screen sessions, SSH sessions) — i.e. for the temporal/container framing,
  not for "a strictly sequential chain of named runs where the bare name is the
  container". The new term is therefore an improvement in tone but not a precise
  industry match for the actual semantics. Alternatives that match the semantics
  more closely would have been `agent thread` (sequential chain; cf. mail/Slack
  threads, OpenAI thread runs), `run chain` / `run group`, or simply `agent`
  with the chain as members — but each has its own collisions, so this is a
  judgment call, not a clear win.
- The plan's mitigations are sound and should be kept as hard requirements, not
  softened later: never use bare `session` in identifiers/keys (always
  `agent_session`), keep sunset aliases for durable data, keep redirect stubs for
  `families/` sidecar paths. If those hold, the rename is tolerable; if bare
  `session` leaks into CLI flags or JSON keys, the cure becomes worse than the
  disease because `session_id` (provider transcript) versus `agent_session_id`
  (chain container) will confuse every future debugger.
- Verdict: weakest justification of the set; acceptable only with the plan's
  `agent_session`-never-bare-`session` identifier rule enforced permanently.
  Do not extend "session" to any further concept.

### 1.5 sase shell → sase turn: approve for agent shells, qualify for proc/gate shells

- The core justification is strong and independent of fashion: `shell` collides
  head-on with the Unix shell (sh/bash/zsh). "Agent shell", "proc shell", "gate
  shell" all read to an outsider as "some kind of command shell", which is wrong
  for an LLM run and misleading for the rest. Removing `shell` from user-facing
  vocabulary is the single highest-value de-collision still available.
- `turn` is the industry-standard word for one LLM interaction step (conversation
  turns, "agent turn", "model turn" in every harness from Claude Code to
  OpenAI-style agent loops). For *agent shells* (one concrete LLM/provider run)
  the rename is therefore exact: "agent turn" needs no explanation.
- The stretch is proc shells and gate shells: a supervised background command or a
  durable human-approval step is not a "turn" in the conversational sense, and the
  industry does not call background executions "turns". `monitor turn` and `gate
  turn` will read slightly metaphorically. That is still far better than the
  status quo (`monitor shell`, `gate shell` read as shell-programs), and the
  uniform `<session>--<suffix>` member naming keeps the implementation coherent —
  but user-facing copy should prefer the qualified forms (`agent turn`, `monitor
  turn`, `gate turn`, `proc turn`) and avoid bare "turn" where a proc/gate
  distinction matters (settlement states, `--next` follow-ups).
- Watch one interaction: after both renames land, "session turn" composition
  ("the session's current turn") is fine, but documentation must keep the
  transcript sense of turn (one prompt→response exchange inside a run) distinct
  from the member sense (one run in the chain). A one-sentence disambiguation in
  the replacement glossary strand will prevent a new folk ambiguity.
- Verdict: approve, with qualified forms in user copy and a disambiguation note
  for the two senses of "turn".

## 2. Candidate further renames

Bar applied: recommend only on demonstrated collision or misdescription, with the
migration cost named. Stylistic dislike alone is not a recommendation.

### 2.1 Recommend: retire the clan / hood / tribe folksiness (highest-value remaining cluster)

Three related terms share one defect — anthropological metaphor with no industry
meaning — and two of them are mutually redundant:

- **clan vs hood**: a clan is "a named rootless container for parallel agents"
  while a hood is "agents sharing a `<name>.` prefix". One is declared
  (`%clan:`), the other emergent (name prefix), but to any user they are "the
  group of related agents". The codebase shows ~4.4k clan vs ~730 hood hits:
  both are load-bearing, yet no new user can guess the difference. Industry
  vocabulary here is `group` / `namespace` (cf. process groups, k8s namespaces,
  thread groups). Recommendation: merge the user-facing concept to **agent
  group** (declared membership) and keep the prefix rule as an unnamed
  implementation detail, or at minimum rename hood → `name prefix` / `name
  group` in user copy so the two stop sounding like synonyms from different
  novels.
- **tribe** (user-facing label across clans/families, `@`-prefixed): collides
  with the well-known Spotify "tribe" (an org unit of squads), which misleads
  exactly the tech audience being courted, and continues the kinship metaphor
  the renames are otherwise exiting. Industry word is **label** (Gmail labels,
  k8s labels) or **tag** — and the project already has "project tags"
  (`+<project>`). Recommendation: rename tribe → **label** (or `agent label`),
  keeping `@` rendering and the `sase agent tribe` CLI as a sunset alias.
- Cost is real (Agents-tab panels, `%id(tribe=)`, sidecar pages), so phase it
  like `sase-17m`: additive aliases first, cutover second. But this is the one
  cluster where the "standard terms" program is currently incomplete: scheduler /
  routine / job / TUI / session / turn will sit inside clan/hood/tribe chrome,
  undermining the whole effort.

### 2.2 Recommend: xprompt → a standard word (skill / slash-command / prompt template)

- `xprompt` has no industry meaning, is unpronounceable in conversation
  ("ex-prompt"? "cross-prompt"?), and collides visually with `prompt` (the thing
  users type) and with "X-" prefixed experimental/ex-treme naming. Meanwhile the
  industry has converged: Claude-style **skills**, slash-commands, and prompt
  templates cover exactly the `.md → single step` / `.yml → multi-step`
  behavior the glossary describes.
- The project already generates "agent skills (aka xprompt skills)" from
  `src/sase/xprompts/skills/` — i.e. the word "skill" is already in the tree,
  creating a standing synonym the project itself maintains. Recommendation: adopt
  **skill** as the user-facing term (keeping `xprompt` as a config-key/lookup
  alias through one deprecation cycle), or `slash-command` if the trigger-syntax
  aspect is meant to dominate. Either is standard; `xprompt` is not.
- Justification strength: high on collision/confusion grounds (the skill synonym
  already exists in-tree), medium cost (config keys, directories, docs).

### 2.3 Recommend (narrow): gate shell → gate turn only via the turn rename; do not rename bare "gate"

- Bare `gate` is fine and should stay: approval gates / CI gates / quality gates
  are standard industry vocabulary for "work pauses until a human decides", and
  the `sase gate` bundle semantics (options, branches, `response.json`) match
  that meaning. No rename recommended for `gate`, `sase gate`, or gate kinds.
- `gate shell` specifically should fall out through the `0qi` turn rename
  (`gate turn`), not through a separate gate renaming project. A second, bespoke
  gate-member term would fragment the new uniform member vocabulary.

### 2.4 Consider but do not yet rename: bead, stitch, patch

- **bead** (~11k source hits plus the entire SDD store vocabulary: bead types,
  tiers, lifecycles) is the most idiosyncratic term in the project — the industry
  says issue / task / ticket / work item (Linear, Jira, GitHub Issues). It is
  also the most expensive term to rename and the most identity-laden (beads are a
  designed differentiator: git-portable issues with typed task flavors). No
  collision exists because no industry term is spelled "bead"; the cost is
  confusion-to-newcomers only. Recommendation: **do not rename**; instead spend
  one paragraph of onboarding copy ("a bead is SASE's git-portable issue/ticket")
  wherever beads are introduced. Revisit only if the tracker surface is ever
  rebuilt anyway.
- **stitch** (~1.3k hits; the ordered change record inside a Patch) is similarly
  idiosyncratic, but it denotes a real semantic gap the industry under-names
  (a commit-proposal record that may precede its commit, `(2a)`-style). `commit`
  is already correctly reserved for real VCS commits. Recommendation: **do not
  rename**; document the stitch-vs-commit distinction once, prominently.
- **patch** (~10.8k hits; the local unit of change wrapping a PR) is mildly
  overloaded (Unix `patch(1)`, "patch release"), but "patch" for a change bundle
  is legitimate industry usage (cf. `git format-patch`, "submit a patch",
  Gerrit changes called patches). Recommendation: **do not rename**.

### 2.5 Do not rename: proc, monitor, artifact/artifact reference, workspace, node, tool run/catalog, usage window, LLM calls

- **proc**: an abbreviation, but `proc` for a supervised process is Unix-honest
  (`/proc`, proc tables) and short CLI vocabulary (`sase proc`) benefits from
  brevity. The pile-up (`proc`, `proc shell`→`proc turn`, `service proc`,
  `oneshot service proc`) should be managed by glossary cross-links, not by
  renaming the root. Keep.
- **monitor** (`sase monitor`, family-attached proc shell for long commands):
  generic, but accurate — it supervises one long command and launches a follow-up
  — and distinct from observability "monitoring" in context. The turn rename
  (`monitor turn`) already fixes its worst surface (`monitor shell`). Keep.
- **artifact / artifact reference / `@kind:arg` refs**: "artifact" is overloaded
  in CI (build outputs), but in the docs/KB sense (a durable citable record) it
  matches industry usage (cf. "knowledge artifacts", "artifact" in RAG
  pipelines). The `@`-citation syntax is distinctive and worth keeping. Keep.
- **workspace**: fully standard (agent workspaces, git worktrees, Codespaces all
  use it); the glossary's repo-vs-workspace-vs-checkout distinctions are exactly
  right. Keep as the exemplar of what "standard" looks like.
- **node** (TUI row), **tool run / tool catalog**, **usage window**, **LLM
  calls**: all either internal (node), standard (tool run/catalog match CI
  "runs"; usage windows match provider "limits" language), or precise
  read-model terms (LLM Calls). Keep all.

## 3. Closing verdict

- Already done and right: **axe → scheduler, lumberjack → routine, chop → job,
  ace → tui**. No reversals recommended; finish removing stragglers
  (e.g. `docs/axe.md`, `docs/agent_families.md` successors) on the normal
  sunset path.
- In flight: **shell → turn** is well justified (Unix-shell collision is the
  strongest single argument in this whole program); land it with qualified forms
  and a two-senses-of-turn note. **family → session** is the riskiest rename
  undertaken — motivated more by tone than by collision, and it buys a permanent
  overloading tax on the word "session". Since `sase-17m` is already mid-flight
  with most phases in progress, the pragmatic advice is to finish it under the
  existing `agent_session`-never-bare-`session` rule rather than re-litigate,
  and to freeze any further expansion of "session".
- New renames recommended, in priority order:
  1. Consolidate **clan / hood** → group vocabulary and rename **tribe** →
     label (the kinship cluster is now the least-standard surface left).
  2. Rename user-facing **xprompt** → skill (or slash-command), keeping config
     aliases through a deprecation cycle.
  3. Let **gate shell** become **gate turn** via `0qi`; do not touch bare
     **gate**.
- Explicitly not recommended: bead, stitch, patch, proc, monitor,
  artifact/reference, workspace, node, tool run/catalog, usage window, LLM calls.
