# Fresh-Clone Bootstrap and Native-Subagent Instructions: Consolidated Report

> **Research request:** Migrate every existing agent instruction file so that SASE
> builds each agent's instructions from memory files right before launching that agent.
> The requester accepts the recommendations in
> `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`. Two
> questions remain:
>
> 1. **Fresh clones.** When another developer clones the sase repo and runs `claude` (or
>    any other supported provider CLI), how do we make sure that interactive session has
>    a reasonably good `CLAUDE.md` or equivalent? One idea is to tell agents to run a
>    `sase` or `uvx run sase` command that generates the file when it is missing. Where
>    would that instruction live?
> 2. **Subagents.** How does each provider's own subagents get instructions that match
>    what they get today, or that fix what is wrong today?
>
> The request asks for an analysis of each issue and a recommended solution.

_Lead consolidation · 2026-10-05 · merges the `cdx`, `cld`, `grk`, `mus`, and `gem`
reports in this directory, plus new verification by the lead. sase checkout
`3569571a73`. Installed CLIs: Claude Code 2.1.289, codex-cli 0.160.0, grok 1.0.46, Muse
1.4.2, agy 1.2.17._

## Bottom line

**Question 1: fresh clones.** Your instinct is right, but it can't be the whole answer.
The instruction does have one natural home: **a small committed root `AGENTS.md`**, plus a
two-line `CLAUDE.md` that imports it. Those are the only files every supported CLI finds
in a bare clone. So:

- Stop committing the full generated files.
- Commit a short, generated stub written for non-SASE readers. Its first section is a
  **bootstrap clause**: "If your context doesn't already contain the generated
  instructions, run `just agent-instructions` (or ask before running
  `uvx --from 'sase>=X' sase instructions sync`), then **read** the file it prints."
- Make the common path mechanical rather than model-dependent:
  - **Claude** imports a gitignored generated file through `@.sase/instructions/claude.md`.
  - **Codex** reads a gitignored `AGENTS.override.md` in place of `AGENTS.md`.
  - `just install` produces both, so the bootstrap clause becomes a fallback for Grok,
    Muse, agy, and anyone who skipped setup.

Generating a file *during* a session never changes what that session already loaded. So
the clause must say "generate, then read", and it must never write a tracked file.

**Question 2: subagents.** The prior plan has a real gap here. **Native instruction files
flow down to provider subagents, but explicit channels mostly do not.** System-prompt
flags, Grok's `--rules`, and prompt prefixes don't reach them. This was verified for
Claude and Grok. Moving delivery from files to flags (the prior report's R1) would
therefore strip instructions from subagents unless each adapter also has a **subagent
channel**.

Today's subagent instructions are already broken, and the harm is measured:

- **Claude general-purpose subagents get the full root contract**, including "use
  `/sase_final`". In 30 days, 13–15 of 200 invoked it, and **2 submitted accepted final
  declarations for their parent's turn**. One had been spawned only to reply "ack2".
- **Claude Explore subagents get no project instructions at all.**

**Recommendation in one paragraph:** keep the prior architecture, with three additions.

1. Each SASE invocation renders a **root bundle and a subagent bundle** from one shared
   core plus a lifecycle overlay. Each adapter delivers both through a two-slot delivery
   plan, and declares the subagent slot's status honestly when it has no channel.
2. **Only the root declares**, and this is enforced mechanically where the harness can
   identify the caller. For Claude that is a PreToolUse hook keyed on `agent_id`.
3. The repo commits only a **generated, budgeted export stub** with the bootstrap clause.
   `sase instructions sync` renders a **`mode: interactive`** projection into gitignored,
   SASE-owned files that Claude and Codex load natively.

**Ship the Claude subagent fix now.** It doesn't depend on the renderer, and it addresses
the measured harm.

## What changed since the prior report

| Prior belief | Status on 2026-10-05 | Evidence |
| --- | --- | --- |
| "Codex has no knob to disable project `AGENTS.md`" (the "decisive fact" behind R7) | **False.** `-c project_doc_max_bytes=0` drops project `AGENTS.md` **and** `AGENTS.override.md` and keeps `$CODEX_HOME/AGENTS.md`. The behavior is undocumented, so conformance must watch it. | cld (E10), re-verified by the lead with `codex debug prompt-input` and markers |
| Claude subagent inheritance is "to verify" | **Settled.** `--append-system-prompt` reaches only the root. `--append-subagent-system-prompt[-file]` reaches Explore and general-purpose subagents but not the root. `CLAUDE.md` reaches general-purpose subagents but not Explore or Plan. | cld live tests (E1–E3). grk confirmed the flag parses. gem found it in the binary. mus couldn't find it because it is **hidden from `--help`**. |
| A Phase 0 Grok `--rules` fix restores Grok | **Restores the root only.** `--rules` text does not reach Grok subagents. | cld (E7). gem's claim that subagents inherit it had no test behind it. |
| Committed `CLAUDE.md` is a good fallback for humans | **It isn't.** It orders SASE-turn behavior: `/sase_final`, `sase_<N>` workspaces, sidecar reads. The **home** `~/CLAUDE.md` has the same problem. It is a render of `~/sase/memory` that includes the full "SASE Final Declaration" block, so every interactive Claude session under `~` is told to finalize a turn it doesn't have. | cld (E16); lead (home file) |
| Subagents matter for every provider | **In practice this is a Claude problem.** Claude: 518 subagent runs in 30 days. Codex: 0 spawned threads in 30 days (1,652 rollouts). Muse: 0 subagent tool calls in 2,401 sessions since 09-28. Grok: 4 subagent sessions out of 706 in 30 days. | cld (Claude, Codex); lead (Muse, Grok, Claude re-count) |
| (gem) "Muse prohibits subagents" | **Misread.** `_muse_directive.py:115` says "Never use cron, workflow, subagent, or snooze tools **to wait**". That bans subagents as a waiting mechanism, not subagents in general. Muse simply doesn't use them. | Lead |

## Part 1 — A fresh clone, then `claude`

### 1.1 What a clone gets today, and after the migration

**Today:** 20 tracked instruction files.

- The root has a 285-line render plus byte-identical `CLAUDE.md`, `GEMINI.md`, `QWEN.md`,
  and `OPENCODE.md` copies.
- `tools/`, `src/sase/ace/`, and `demos/tapes/` each have the same set of five.

A clone works without setup, but the content is the **SASE-run contract**. It is wrong
for an interactive session: it tells the model to use skills the developer doesn't have,
to respect ephemeral workspaces that don't exist, and to read sidecars that aren't cloned
(cld E16).

**After R7 with nothing else:** the clone has no `CLAUDE.md`. Claude's default mode
reads project `AGENTS.md` only when no `CLAUDE.md` exists in the working directory or any
ancestor. So a developer with a literal `~/CLAUDE.md` gets nothing from the project.
(gem overstates this as "virtually every Claude user". The usual user file is
`~/.claude/CLAUDE.md`, which isn't an ancestor. But the case is real on athena.) Grok in
a fresh, untrusted folder loads nothing until the human grants trust.

### 1.2 Constraints that shape the answer

| Constraint | Consequence |
| --- | --- |
| A file created *during* a session is not loaded natively for the rest of that session. Claude, for example, re-reads `CLAUDE.md` only after compaction. | The clause must say "generate it, **then read it**". |
| Root `AGENTS.md` is the only file every provider reads natively in a clone. Codex, agy, Qwen, and OpenCode always read it. Grok and Muse read it once trusted. Claude reads it through an import. | The bootstrap clause lives in committed `AGENTS.md`. `CLAUDE.md` stays as an import shim. |
| Claude: an `@import` of a **gitignored** file loads, and an `@import` of a **missing** file is silently skipped. | `CLAUDE.md` can import the generated file unconditionally. Before the first sync this costs nothing. Verified by cld (E6) and again by the lead. |
| Claude also loads `CLAUDE.local.md` (lead-verified). But by convention that file is the **developer's own** private-instructions file, and `.gitignore:58` already reserves it. | SASE must not own or overwrite `CLAUDE.local.md`. grk and gem proposed using it; use a SASE-owned import target instead. |
| Codex reads `AGENTS.override.md` *in place of* `AGENTS.md` in the same directory (lead-verified). | A gitignored override gives Codex the full render automatically. It must contain the stub's content too, and sync must not overwrite one SASE didn't write. |
| Grok skips gitignored files during discovery. Project `.grok/rules/` requires trust. Only `$GROK_HOME/rules/` and `extra_rule_dirs` ignore trust and gitignore. The `GROK_CONFIG` overlay cannot add a discovery source. | grk's gitignored `.grok/rules/` overlay would **not** load. Interactive Grok relies on the bootstrap clause or a SASE launcher. Grok docs: `12-project-rules.md`, `05-configuration.md`. |
| No provider natively reads `AGENTS.local.md`. Grok's docs name it as an example of an unrecognized file. | gem's `AGENTS.local.md` overlay would be dead weight. |
| Claude SessionStart output is capped at 10,000 characters, and a full render is 17–21 KB. Hooks fire in `-p` mode too. | Hooks can refresh the file and point to it, but can't carry it. Any committed hook must no-op inside SASE runs. |
| An outside developer has no SASE home, sidecars, owner identity, or skills. | The interactive render must be **hermetic** and must name CLI forms (`sase memory read …`) rather than skills, unless the skills are known to be installed. |

### 1.3 Verdict on "tell agents to run sase if the file is missing"

**Adopt it as the universal fallback, with five amendments.** All five researchers agree
it can't be the only mechanism, because a missing file can't tell an agent to create
itself.

1. **Where it lives:** the **first section of committed root `AGENTS.md`**, which
   `CLAUDE.md` imports. Other places don't work:
   - README and CONTRIBUTING are for humans, and agents read them unreliably. Mirror the
     command there for humans anyway.
   - Skills aren't installed on a fresh machine.
   - Provider settings can't reach Grok.
   - The SASE-run bundle never reaches a raw session.
2. **Generate, then read.** The clause names the exact file to read afterwards. The
   command prints that path. A **sentinel heading** lets the agent skip the step when the
   content is already loaded:
   - Claude through the import;
   - Codex through the override;
   - a SASE run through its bundle.
3. **Write only gitignored, SASE-owned paths.** Never overwrite a tracked file, which
   would recreate the churn R7 removes and dirty every PR. gem and grk both flagged this.
   mus's sketch ("re-read this file" after syncing over the committed stub) has exactly
   this flaw.
4. **Use the right command, with no silent installs.**
   - **Inside the sase repo:** `just agent-instructions`, which wraps
     `uv run sase instructions sync`. It works offline after `just install`.
   - **Any SASE-managed repo:** `sase instructions sync` when it is installed.
   - **Published fallback:** `uvx --from 'sase>=<min>' sase instructions sync`, only
     with the user's consent. The version floor stops a stale `uvx` cache from rendering
     an old schema. Note that `uvx run sase` mixes two interfaces: `uvx` already means
     `uv tool run`.
5. **Missing is enforced by the clause; staleness is handled mechanically.** A gitignored
   file goes stale on the next `git pull`. The generated file carries an input-digest
   header. `sync --if-stale` is a cheap no-op when the file is fresh, so the clause can
   say "run it" without cost. `just install`, optional git hooks, and the optional Claude
   hook keep the file fresh without relying on the model.

**Render to stdout, or write a file?** cdx preferred `sase instructions render --mode
interactive` to stdout, which avoids writes. Use files as the primary path:

- Tool-output truncation varies by provider, and a 17–21 KB render is near common caps.
- A file lets Claude and Codex load the content **natively in every later session**.

Keep `render` to stdout as the read-only alternative when the agent can't write.

### 1.4 Recommended design

#### Committed: two files at the root, none nested

**`AGENTS.md`** is a **generated** `mode: export` stub, checked in CI with
`sase instructions export --check`.

- **Budget:** at most 80 lines and about 1.5k tokens, enforced. Target about 40 lines.
- **Content:**
  1. one line of orientation;
  2. the bootstrap clause;
  3. build and test commands (`just install`, `just check`; `just check-full` only when
     asked);
  4. the core conventions that hold for *any* contributor. In sase today those are the
     `gotchas` and `rust_core_backend_boundary` notes.
- **Excludes:** the SASE runtime contract, `/sase_final`, the home layer, repo
  inventories, web rosters, and the reference trigger list.

Excluding rosters and triggers keeps churn near zero. Of 112 commits touching root
`AGENTS.md` in 60 days, only 38 touched core or reference notes; the rest were rosters
and generator changes (cld E19).

**Why generated rather than hand-written** (grk, gem, and mus wanted hand-written):

- SASE is a product. **Every SASE-managed repo** needs the same pair from `sase init`,
  not only sase.
- The bootstrap clause and its commands are SASE-version-owned text.
- The conventions already live in memory notes.
- CI `--check` is the drift guard cdx asks for.

**`CLAUDE.md`** is two lines:

```markdown
@AGENTS.md
@.sase/instructions/claude.md
```

Everything else goes:

- Delete `GEMINI.md` (agy reads `AGENTS.md`), `QWEN.md` (Qwen reads `AGENTS.md`), and
  `OPENCODE.md` (never read).
- Convert the three nested sets into path-scoped reference notes, as the prior report
  proposed.
- A trusted Grok reads `CLAUDE.md` too and sees two literal `@…` lines, which is harmless.

A sketch of the stub's opening:

```markdown
<!-- Generated by `sase instructions export` from sase/memory/. Do not edit. -->
# sase — Agent Instructions (summary)

## Start here: full instructions are generated
If your context already contains the heading "sase — Interactive Agent Instructions" or
"SASE Run Instructions", skip this section. Otherwise run `just agent-instructions`
(inside a dev env; offline), or ask the user before running
`uvx --from 'sase>=<min>' sase instructions sync`. Then read the file it prints. Never
commit generated instruction files. If sase can't run, continue with this file and say so.
This is an interactive session, not a SASE provider turn: `/sase_final` does not apply.

## Build and test
...
```

#### Generated and gitignored: written by `sase instructions sync`

| File | Read by | Content |
| --- | --- | --- |
| `.sase/instructions/claude.md` | Claude, through the import | Full interactive render. It omits the home layer when a home `CLAUDE.md` already loads as an ancestor. |
| `AGENTS.override.md` (root; add it to `.gitignore`) | Codex, natively, *instead of* `AGENTS.md` | Full interactive render, which includes the stub's content |
| `.sase/instructions/agents.md` | Grok, Muse, agy, Qwen, OpenCode, through the bootstrap clause | Full interactive render |

`.sase/` is already gitignored (`.gitignore:61`).

**How the interactive render differs from the SASE-run bundle:**

- It **drops** the final declaration, single-turn and workspace rules, the handoff, plan,
  questions, and monitor obligations, and the sidecar artifact rules.
- It **switches** skill references to CLI equivalents unless a `skills_installed` fact is
  true.
- It **adds** one line: "interactive session, not a SASE turn".

That last line matters even on athena. Globally deployed SASE skills are visible in every
interactive session, and their descriptions assert turn obligations. cld saw a plain
`grok -p` in `/tmp` announce a finalizer step for this reason.

#### `sase instructions sync` requirements

1. **Hermetic.** It reads repo memory, packaged templates, and optional home memory. It
   never reads the SASE state dir or sidecars, never prompts, and never needs a TTY.
2. **Never runs in SASE workspaces.** It detects them through `.sase/checkout.json` or the
   occupant markers and exits. Workspace prep should also delete these projection paths,
   so a reused workspace never carries a stale one.
3. **Never overwrites a file without SASE's generated header.** This protects a
   developer's own `AGENTS.override.md`.
4. **Digest header, plus `--check` and `--if-stale`.** It prints the paths to read.
   About 2 s per render is fine (cld E18).
5. **Honors `min_sase_version`** declared by the repo.

#### Keeping files fresh, and deterministic delivery

- **`just install`** runs `sync`. CONTRIBUTING already sends contributors there.
  `sase init` does the same for other SASE-managed repos.
- **Optional `post-merge` and `post-checkout` hooks** run `sync --if-stale`. They are
  installed by `just install`, can be opted out of, and are silent when `sase` is missing.
- **Optional Claude SessionStart hook** in the committed `.claude/settings.json`, which is
  currently `{}`.
  - It runs `sync --if-stale` and prints a short pointer when the file changed.
  - It must exit 0 silently when a SASE-run marker is set (for example
    `SASE_ARTIFACTS_DIR`) or when `sase` isn't on `PATH`.
  - Don't make it the primary path. It is Claude-only, runs code for every contributor,
    and is capped at 10k characters.
- **Deterministic interactive launch (cdx).** Route `sase tmux-agent` through the same
  adapter delivery hook with `mode: interactive`. Today it runs raw `entry.argv` and
  depends on files by accident (mus). Optionally add a foreground equivalent. This is the
  "guaranteed before the first token" path for people who launch through SASE.

#### The home layer

`~/AGENTS.md` and `~/CLAUDE.md` are renders of `~/sase/memory`, managed by chezmoi. Today
they contain the full SASE runtime contract.

Once Claude and Codex SASE runs get the home layer through their bundles (Phase 1), with
`~/CLAUDE.md` excluded and the shadow-home symlink replaced, these home files should
become **`mode: interactive` renders**. They then keep serving athena administration in
`~` without telling interactive sessions to finalize a turn.

#### Neutralizing the stub in SASE runs

| Provider | In SASE-managed repos |
| --- | --- |
| Claude | `claudeMdExcludes` via the adapter's `--settings` covers the workspace `CLAUDE.md` and `AGENTS.md`, `~/CLAUDE.md`, and the import target. Repo-owned files in foreign repos stay loaded. |
| Codex | `-c project_doc_max_bytes=0` (lead-verified). It also suppresses any stray `AGENTS.override.md`, which answers cdx's worry about reused checkouts. Foreign repos keep native discovery. |
| Grok | Already untrusted, so nothing loads. Keep it that way. |
| Muse, agy | Accept the stub load: at most about 1.5k tokens, and a subset of the bundle. Muse needs `--trust-workspace` for other assets, and agy has no switch. |

This clarifies the prior report's "no SASE-owned native file loads" (cdx): **no full SASE
projection loads natively.** A tiny committed stub may load, and it must short-circuit
when the bundle's sentinel is present.

### 1.5 Options considered

| Option | Verdict |
| --- | --- |
| Keep committing full generated files | **Reject.** Wrong audience for humans, 112 commits in 60 days, conflicts across 47 workspaces. |
| Commit nothing; document `sync` | **Reject.** A missing file can't bootstrap itself (all five). |
| Stub tells the agent to regenerate and **overwrite** the tracked file | **Reject.** Dirties `git status`, recommits churn, and doesn't affect the running session. |
| Hand-written stub, identical across every shim filename (grk) | **Reject the extra filenames and the hand-writing.** Two files suffice. A generated stub serves every SASE-managed repo. |
| `CLAUDE.local.md` as the Claude overlay (grk, gem) | **Reject.** The file belongs to the developer. Use a SASE-owned import target. |
| Committed stub with bootstrap clause, plus native upgrades (Claude import, Codex override), plus `just install` refresh (cld, extended) | **Adopt.** |
| SessionStart hooks as the only bootstrap | **Optional helper only** (cld, cdx, grk, mus agree). |
| Wrapper binary (`bin/claude`) | **Reject.** People type `claude`. The SASE launcher covers the deterministic case. |

## Part 2 — Provider-native subagents

### 2.1 Three execution identities

| Identity | Project and memory rules | Completion | Render |
| --- | --- | --- | --- |
| SASE root invocation | Full bundle | Owns the final declaration and handoffs | New render at provider selection |
| Another agent launched through SASE (`/sase_run`, swarms, monitors) | Its own full bundle | Its own declaration | Its own render. Out of scope here. |
| **Provider-native helper** (Claude's Agent tool, Codex `spawn_agent`, Grok `spawn_subagent`, Muse and agy children) or a history fork | The same applicable core | **Returns results to its parent** | Rendered from the parent's frozen inputs, with a helper overlay |

"Equivalent" does not mean byte-identical (cdx). A helper keeps:

- repo rules;
- audited memory and artifact reads;
- conventions;
- path and reference triggers.

It **replaces** root lifecycle obligations with a hand-back contract. Copying today's
unconditional `/sase_final` rule into a helper reproduces the bug.

### 2.2 The principle: files flow down, flags don't

| Provider | Do native files reach subagents? | Does the root's explicit channel reach them? | Subagent-specific channel |
| --- | --- | --- | --- |
| Claude | General-purpose and custom: **yes**. Explore and Plan: **no**. | `--append-system-prompt`: **no** (verified) | `--append-subagent-system-prompt[-file]`, `-p` only, every non-fork subagent including nested ones (verified). SubagentStart `additionalContext`, matchable by type (verified). |
| Codex | Fresh children re-discover them. Forks copy the parent's history. | `developer_instructions` are **copied to children** (`build_agent_shared_config`, cdx source read at the 0.160.0 tag) | `features.multi_agent_v2.subagent_developer_instructions`, and per-role `developer_instructions`. **v2 is off by default** (`multi_agent` stable/on, `multi_agent_v2` stable/off; lead). SubagentStart hooks need trust plus hash review. |
| Grok | **Yes**, while files loaded (a 2026-09-07 child recorded its parent's two files) | `--rules`: **no** (verified, cld E7) | No injecting start hook. Candidates: shadow `$GROK_HOME/rules/` (home rules load regardless of trust), and roles or personas in a shadow config. `GROK_CONFIG` can't set them. `--agents` JSON was inconclusive. |
| Muse | Unverified | Prompt prefix: no | `--agents` overlay (unverified) |
| agy | Custom agents inherit ambient rules. Built-in children start clean. | Prompt prefix: no | `rules:` frontmatter on custom agents |
| Qwen | Yes (code reading) | `--append-system-prompt`: no (code reading) | SubagentStart `additionalContext` |

### 2.3 What subagents get today, how often, and the harm

| Population | Volume | What it gets today | Harm |
| --- | --- | --- | --- |
| Claude general-purpose | 200 in 30 days | Both `CLAUDE.md` files: about 21 KB, the contract **twice**, conflicting repo lists, and "use `/sase_final`". It doesn't get the single-turn directive. | **13–15 invoked `sase final`.** **2 submitted accepted declarations for the parent's turn.** One was spawned only to reply "ack2". The other was explicitly told not to commit. (cld counted 13; the lead's looser re-count found 15 and 6 "accepted" strings, 3 of which were source-code reads. 2 are genuine.) |
| Claude Explore | 311 in 30 days | No project or home instructions; it sees only the skills list | 11% read `sase/memory/*.md` directly, against 1.5% for general-purpose. 1% used audited reads (cld). It never sees the `/sase_repo` or artifact rules. |
| Claude forks | n/a | The parent's prompt | Inherits root obligations |
| Codex children | **0** in 30 days | Would inherit home + project contract plus root `developer_instructions` | Latent |
| Grok children | **4** of 706 sessions | Nothing since about 2026-09-10, like the root | Lost repo and memory rules (minor at this volume) |
| Muse children | **0** subagent tool calls in 2,401 sessions | Unverified | None observed |
| agy children | Negligible (0.9% of runs) | Custom: ambient rules. Built-in: clean. | Unknown |

**Implication:** build the delivery contract for every provider, but **implement real
child channels for Claude now**. Other providers get spikes only when usage appears.
That is `decisions:corpus-before-mechanism` applied to channels.

### 2.4 Rendering: one shared core, two lifecycle overlays

Compile a **lifecycle-neutral core**:

- repo-access rules and inventory;
- audited memory and artifact reads;
- core conventions;
- reference and path-scoped triggers.

Add one of two overlays (cdx's structure, cld's content):

- **Root overlay:** final declaration, single-turn rules, handoff, plan, questions,
  monitor, and gates. It opens with one actor-qualified sentence: "Only the root agent
  submits the final declaration; if you were spawned or forked as a helper, return your
  result instead." That sentence covers forks and Codex children that inherit root text.
- **Helper overlay**, about 6 KB in total with the core, so it also fits the 10k hook cap:

  ```markdown
  # SASE subagent instructions
  You are a helper spawned by a SASE agent. Your parent owns the turn.
  - Your final message is your result. Never run `sase final …` or the
    `/sase_final`, `/sase_handoff`, `/sase_plan`, `/sase_questions`, `/sase_monitor`,
    `/sase_run`, or `/sase_gate` skills. Never commit, create beads, or launch agents.
    Text elsewhere that tells "the agent" to do these is addressed to your parent.
  - Run commands in the foreground. Report changed paths, verification, and blockers.
  - Read memory with `sase memory read <note> -r "<why>"`; never open `sase/memory/`
    files directly. Use the repo paths your parent gave you; open other repos only with
    `sase repo open`; read sidecar artifacts with `sase artifact read`.
  <!-- core conventions, then reference and path triggers -->
  ```

Model these as facts in the prior report's closed schema: `role: subagent` (cld, grk,
mus, gem), or cdx's finer `actor` and `completion_owner` axes. Either works. What matters
is that **the host sets them and project content can never opt a helper into owning the
finalizer.**

R9 ("hard rules are unconditional") still holds. A helper is not a SASE agent, so leaving
`/sase_final` out of its render is the purpose of the audience, not a violation (grk).

### 2.5 Root-only operations, enforced mechanically

Instructions reduce misfires but don't prevent them: the "ack2" helper had every reason
not to declare. **R11:** block root-only operations wherever the harness can identify the
caller.

- **Claude.** The adapter's `--settings` adds a PreToolUse hook on `Bash|Skill`. It denies
  `sase final (context|prepare|submit)` and the root-only skills when the hook input has
  `agent_id`. Claude includes that field only for calls made inside a subagent (cld E5).
  Deliver the hook per run, never in a committed file. Whether forks carry `agent_id` is
  **unverified**; test it before relying on the hook for forks.
- **Codex.** The same hook pattern can live in the shadow `CODEX_HOME`. First check what
  identifies a child. Low priority at zero usage.
- **Everyone else.** There is no reliable caller identity. Same-process subagents share
  the environment, so a `SASE_*` variable proves nothing (cdx). Rely on the render, the
  actor-qualified sentence, and **host-side attempt logging** so conformance can count
  misfires.

### 2.6 Delivery plan per provider

**R10:** every adapter's `DeliveryPlan` has a `root` slot and a `subagent` slot. A
provider without a child channel must declare `inherits-native`, `inherits-root`, or
`none`, and `sase doctor instructions` shows that status.

| Provider | Root (SASE run) | Subagent (SASE run) | Status and priority |
| --- | --- | --- | --- |
| **Claude** | `--append-system-prompt-file` (core + root overlay), plus `claudeMdExcludes` | `--append-subagent-system-prompt-file` (core + helper overlay), plus the PreToolUse guard. Explore and Plan get instructions for the first time. Fallback if the flag disappears: `--agents` file definitions with `omitClaudeMd`, or a SubagentStart hook with a pointer. | **Ship in Phase 0.** All mechanisms are verified on 2.1.289. |
| **Codex** | Shadow `$CODEX_HOME/AGENTS.md` carries the **neutral core**, which fresh and forked children also see. Root `developer_instructions` carry the root overlay; the adapter already uses this channel for the single-turn directive. Add `project_doc_max_bytes=0`. | v1, the default: children copy the root overlay, so the actor-qualified sentence carries the load. When v2 is enabled: `subagent_developer_instructions` carries the helper overlay. Custom roles may override it, so adapt them in run-local config. | `inherits-root` now. Low priority (0 spawns). This combines grk's channel split with cdx's source finding that grk's split alone leaks the root overlay to v1 children. |
| **Grok** | `--rules` (core + root overlay). Keep workspaces untrusted. | **Spike:** a shadow `$GROK_HOME` whose `rules/sase-core.md` carries the core, loaded for root and children regardless of trust. `--rules` would then carry only the root overlay. Caveat: Grok auth is OAuth `auth.json`, so the shadow home must symlink it like the Codex shadow home does, and must be tested against refresh-token rotation. The lead didn't run this spike for that reason. | `none` until the spike passes. Low priority (4 of 706). |
| **Muse** | Prompt prefix (core + root overlay) | None needed yet. Spike the `--agents` overlay only if usage appears. | `none`. No usage. |
| **agy** | Prompt prefix | Root-only clause. gem's run-scoped `.agents/rules/` file is a candidate under R1's fallback-channel clause, but needs cleanup and no-churn guarantees. Defer. | `none`. 0.9% of runs. |
| **Qwen, OpenCode** | As in the prior report | SubagentStart (Qwen) or per-agent config (OpenCode), if usage ever appears | Declared, about 0 runs |
| **Plugin providers** | `llm_instruction_delivery(bundles) -> DeliveryPlan` | The same hook fills the `subagent` slot or declares its status | New hook-contract field |

**Best-effort fallback for any `none` provider** (mus's in-payload idea, made cheap):

- Write the helper render to `$SASE_ARTIFACTS_DIR` and export
  `SASE_SUBAGENT_INSTRUCTIONS_FILE`.
- The root overlay says: "when you delegate to a native subagent, begin its prompt with:
  *you are a helper; read `$SASE_SUBAGENT_INSTRUCTIONS_FILE` first*."

This costs one sentence per delegation rather than an inlined render. It is
model-mediated, so label it best effort (cdx).

**Don't disable native subagents** as the strategy. Explore-style cheap search is the
reason they exist, and `/sase_run` is the wrong tool for "grep this in a side context"
(grk). Disabling stays a per-provider option only if conformance shows misfires on a path
that has no channel.

### 2.7 "Equivalent or better", concretely

| Population | Today | After | Net |
| --- | --- | --- | --- |
| Claude general-purpose | about 21 KB, contract ×2, `/sase_final` | about 6 KB helper render, native files excluded, guard | **Better:** no misfires, about 70% fewer instruction tokens, one consistent repo list |
| Claude Explore and Plan | nothing | helper render | **Better:** memory and repo rules for the first time |
| Claude forks | parent prompt | parent bundle, actor-qualified root rule, guard (if `agent_id` is present) | Equivalent or better |
| Codex children | home + project contract ×2, root directive | neutral core once, actor-qualified root overlay; v2 helper overlay when enabled | Better |
| Grok children | nothing | nothing until the spike; then the core via shadow home rules | Equal, then better |
| Muse, agy children | unverified or partial | declared status plus pointer fallback | Equal |
| Interactive `claude` general-purpose subagents (human sessions) | the SASE contract, wrongly | the stub plus the interactive render, natively, with no `/sase_final` | Better |
| Interactive Explore | nothing | nothing; an optional committed SubagentStart hook could add a pointer | Equal |

### 2.8 Conformance

Extend `sase doctor instructions` and the conformance check:

- **Claude.** In `subagents/agent-*.jsonl`, the helper render's section ids appear in the
  system prompt, no native SASE file loaded, and there are **zero** `sase final` calls.
- **Grok.** Child `prompt_context.json` (`audience: subagent`) shows the expected rule
  source.
- **Codex.** `thread_spawn_edges` count plus the child's instruction items.

Record `parent_hash → child_hash` in provenance. Where a provider doesn't expose child
context, record **unverified**. Don't infer delivery from the bytes SASE wrote (cdx).

## Where the researchers disagreed, and how this report resolves it

| Question | Positions | Resolution and basis |
| --- | --- | --- |
| Does `--append-subagent-system-prompt-file` exist? | cld, grk, gem: yes. mus: not found in `--help`. | **Yes, hidden from `--help`.** cld's live marker tests and grk's parse error are direct evidence. |
| Does Grok `--rules` reach subagents? | gem: yes. grk: unverified. cld: no (tested). | **No.** cld's marker test. gem had no evidence. |
| Can Codex suppress project `AGENTS.md`? | mus, grk, prior report: no. cld: yes (undocumented). | **Yes.** Lead re-verified, including the override file. Conformance must watch it. |
| Muse subagents | gem: prohibited by harness. Others: unknown, spike. | **Not prohibited, just unused.** gem misread "to wait". There were 0 calls in 2,401 sessions. |
| Committed surface | cld: generated export `AGENTS.md` plus a two-line import `CLAUDE.md`. cdx: small `AGENTS.md` plus `@AGENTS.md`. grk: hand-written stub in all five names. gem: ~35-line hand-written `CLAUDE.md` and `AGENTS.md`. mus: 10–15-line stub. | **Two files, generated, budgeted, CI-checked** (§1.4). |
| Claude overlay | cld: SASE-owned import target. grk, gem: `CLAUDE.local.md`. | **Import target.** Both load (lead), but `CLAUDE.local.md` belongs to the developer. |
| Grok interactive overlay | grk: gitignored `.grok/rules/`. Others: bootstrap clause. | **Bootstrap clause or SASE launcher.** Grok skips gitignored files, and project rules need trust. |
| Codex override in reused checkouts | cdx: avoid `AGENTS.override.md`. cld: use it. | **Use it in primary checkouts.** `project_doc_max_bytes=0` suppresses it in SASE runs, sync refuses workspaces, and prep deletes it. |
| Stdout or file | cdx: render to stdout. Others: files. | **Files primary, stdout secondary** (§1.3). |
| Codex child split | grk: shadow `AGENTS.md` child-safe, root overlay in `developer_instructions`. cdx: v2 `subagent_developer_instructions`. | **Both.** grk's split is right for the core. Per cdx's source read, v1 children copy `developer_instructions`, so add the actor-qualified sentence, and use the v2 override when v2 is on. |
| Disable subagents without a channel? | grk: for minor providers. cdx: in guaranteed mode. cld: declare status. | **Declare status, use the pointer fallback, and disable only on observed misfires.** Usage is near zero off Claude. |
| When the subagent fix ships | cld: Phase 0. grk: Phase 1. mus: Phase 3. gem: Phase 1. | **Phase 0 for Claude.** Measured harm; independent of the renderer. |

## Requirement amendments

These are added to the prior report's R1–R9.

> **R7 (amended).** Generated *full* instruction files stop being committed. The reason is
> wrong audience, churn, and conflicts, not Codex suppression, which is possible. See R12.

> **R10. Two-slot delivery.** Every `DeliveryPlan` has `root` and `subagent` slots. A
> missing child channel is declared (`inherits-native` | `inherits-root` | `none`) and
> reported.

> **R11. Only the root declares, mechanically where possible.** Harness hooks block
> root-only operations for identified helpers. Elsewhere the host logs attempts, and the
> root overlay states the rule in actor-qualified form.

> **R12. The committed surface is a generated, budgeted `mode: export` stub.** It is a
> root `AGENTS.md` plus a two-line import `CLAUDE.md`. It must be correct for non-SASE
> sessions, carries the bootstrap clause, and never contains turn obligations.

> **R13. `sase instructions sync` is hermetic and conservative.** It writes only
> SASE-owned gitignored paths and refuses SASE workspaces. It never overwrites files it
> didn't generate. It has a digest header, `--check` and `--if-stale`, and a version
> floor.

> **R14. Three audiences never mix turn obligations.** These are SASE root, native
> helper, and interactive. Only the SASE root render contains the final-declaration
> contract. This also applies to the home files.

## Recommended solution

**Keep the prior report's per-invocation bundle and adapter delivery, with three
additions:**

- a root and a subagent render from one shared core;
- mechanical root-only enforcement;
- a generated export stub whose first section bootstraps fresh clones into a gitignored
  interactive projection that Claude and Codex load natively.

### Phase 0: stopgaps for observed harm (days, independent of the renderer)

1. **Claude subagents.** In `src/sase/llm_provider/claude.py`, next to the existing
   `--append-system-prompt` (around line 436), add
   `--append-subagent-system-prompt-file`. Its content is a packaged helper template
   (prohibitions, memory and repo rules, core notes). Also add `--settings` with the
   PreToolUse root-only guard. **Don't** exclude native `CLAUDE.md` yet: general-purpose
   helpers still need the conventions until Phase 1, and the appended prohibition plus
   the guard override the inherited "use `/sase_final`".
2. **Grok root.** Ship the prior report's `--rules` fix.
3. **Actor-qualified root-only sentence** in the shared contract note. This is a memory
   edit, so it goes through `/sase_memory_write`.
4. **Doctor.** Ship `sase doctor instructions` with subagent rows: Claude helper
   `sase final` count, and Grok, Codex, and Muse child counts.
5. **Track the follow-ups.**
   - File a bug bead with the evidence of the 2 accepted helper declarations, through
     `/sase_new_task`.
   - Fix the stale "Instruction double-load" section of `docs/agent_providers.md`.

### Phase 1: bundle renderer with two-slot delivery

This is the prior report's Phase 1, plus:

- the core/overlay split and the `role: subagent` (or `actor`) fact;
- R10 delivery plans per the §2.6 table;
- `claudeMdExcludes` and `project_doc_max_bytes=0`, each turned on in the same release as
  that provider's explicit delivery;
- `SASE_SUBAGENT_INSTRUCTIONS_FILE` plus the pointer fallback;
- subagent rows in provenance and conformance.

### Phase 2: export stub, interactive sync, and the home layer

This replaces the prior report's "untrack all" phase. Untrack a provider's files only
after its Phase 1 delivery is on (grk).

1. `sase instructions export`: committed `AGENTS.md`, `mode: export`, budgeted, CI
   `--check`, replacing the `sase init memory --no-commit` drift step. Add the two-line
   `CLAUDE.md`. Delete the other copies and the nested sets. Update
   `PROVIDER_SHIM_FILES` (`src/sase/amd/constants.py`). `sase init` gives other
   SASE-managed repos the same pair.
2. `sase instructions sync` (R13): `just agent-instructions`, called from `just install`.
   Gitignore `AGENTS.override.md`, and make workspace prep delete projection paths.
3. Route `sase tmux-agent` through the delivery hook with `mode: interactive`.
4. Switch home `~/AGENTS.md` and `~/CLAUDE.md` to `mode: interactive` renders of home
   memory. They are chezmoi-managed, so make the change in the `chezmoi` repo through
   `/sase_repo`.
5. Optional: the guarded Claude SessionStart refresh hook, and `post-merge` and
   `post-checkout` hooks.
6. Update `glossary:agent-instruction-file`, `docs/init.md`, `docs/agent_providers.md`,
   and CONTRIBUTING. Memory changes go through `/sase_memory_write`.

### Phase 3 and later

Unchanged from the prior report: audiences, the `when:` evaluator in `sase-core`, and
traits on demand. Add:

- the Grok shadow-home child spike, when Grok child usage is non-trivial;
- Muse and agy child channels, only when usage appears;
- the Codex v2 helper override, when v2 is enabled.

### Governance

Add a decision record next to the prior report's proposed "Instructions Are Rendered Per
Invocation And Delivered By Adapters", roughly **"Native Helpers Return; Only Roots
Declare"**. It should record:

- R10, R11, and R14;
- the three audiences;
- the reopen conditions under [What would change this](#what-would-change-this).

It extends `decisions:host-owned-completion`.

### Success criteria

- Claude helper `sase final` calls go from 13–15 per 30 days to **0**, and helper-accepted
  declarations go to 0.
- Explore's rate of direct memory-file reads falls from 11% toward 1.5%.
- Every Claude helper transcript shows the helper render. No root render or native SASE
  file appears in it.
- **Fresh clone, no SASE installed:** `claude`, `codex`, and a trusted `grok` load the
  stub, get build and test guidance, and are never told to run `/sase_final`.
- **After `just install`:** Claude and Codex load the interactive render natively, and
  `git status` stays clean.
- Workspace `git status` is never dirtied by instruction generation, and the committed
  stub changes only when export notes or the template change.

### What would change this

- **Claude removes `--append-subagent-system-prompt-file`, or it stops reaching
  Explore.** Fall back to `--agents` file definitions with `omitClaudeMd`, or a
  SubagentStart pointer hook.
- **Claude forks lack `agent_id`.** Rely on the actor-qualified sentence and host logging
  for forks. Consider disabling forks in SASE runs if misfires continue.
- **Codex's undocumented `project_doc_max_bytes=0` stops suppressing.** Accept the small
  stub double load. The stub is small precisely so this case stays cheap.
- **Grok or Muse child usage grows and their spikes fail.** Then disable native
  subagents for that provider in SASE runs. The cost is small, because those children
  currently get nothing anyway.
- **Real outside contributors appear and need more than the stub.** Raise the export
  budget, for example to add reference triggers, and accept the extra churn. Never add
  turn obligations.

## Open spikes

| Question | How to settle it |
| --- | --- |
| Do Claude forks carry `agent_id` in PreToolUse input? | Repeat cld's E5 logger setup with a forked helper. |
| Do Grok children load shadow `$GROK_HOME/rules/*.md`, and does OAuth refresh survive a symlinked `auth.json`? | `GROK_HOME=<shadow>` with a marker rule; spawn a child; grep the child's `prompt_context.json` and `system_prompt.txt`. Run it on an expendable credential first. |
| Does Claude reload `@imports` after compaction? | Interactive `/compact` test. The docs promise only the root `CLAUDE.md`. |
| Muse child inheritance (`AGENTS.md`, `--agents`, `run.developer_prompt`) | Only if Muse starts using subagents. Use a forced spawn with markers. |
| Do Codex SessionStart and SubagentStart fire under `codex exec` in a shadow home? | One `codex exec` run with a marker hook. Only needed if Codex child usage appears. |

## Evidence index

**Lead verification (2026-10-05):**

- **Codex.** `codex debug prompt-input` in a temporary repo with markers in `AGENTS.md`,
  `AGENTS.override.md`, and `$CODEX_HOME/AGENTS.md`:
  - default: home + override (override replaces `AGENTS.md`);
  - with `-c project_doc_max_bytes=0`: home only.
  - `codex features list`: `multi_agent stable true`, `multi_agent_v2 stable false`.
- **Claude.** One `claude -p --model haiku` run in a temporary repo. The two-line
  `CLAUDE.md` (`@AGENTS.md`, `@.sase/instructions/claude.md` under a gitignored `.sase/`)
  plus `CLAUDE.local.md` produced all three markers.
- **Claude subagent re-count.** `~/.claude/projects/*/*/subagents/agent-*.jsonl`, 30
  days: 518 files (311 Explore, 200 general-purpose, 7 web-fetch); 15 general-purpose
  helpers called `sase final` or the skill. Of 6 transcripts containing "Accepted final
  declaration", 3 were source reads and 2 were genuine submissions (the "ack2" case in a
  sase_19 session, and a sase_15 `%queue` migration helper).
- **Usage.**
  - Grok: 706 `prompt_context.json` files since 09-05, 702 `primary` and 4 `subagent`.
  - Muse: 2,401 `session.jsonl` since 09-28; tool tally is shell, edit, read, skill,
    write, search, web; **no** subagent tool.
- **Grok docs.** `~/.grok/docs/user-guide/12-project-rules.md` (home rules,
  `extra_rule_dirs` ignore trust and gitignore; gitignored files skipped;
  `AGENTS.local.md` not recognized), `05-configuration.md` (the `GROK_CONFIG` allowlist
  can't add discovery sources), `16-subagents.md` (roles, personas, `resume_from`
  re-renders the system prompt). `~/.grok/config.toml`: OAuth auth, no API key.
- **sase source.**
  - `src/sase/llm_provider/_muse_directive.py:115` ("…subagent, or snooze tools to
    wait");
  - `claude.py:436` (`--append-system-prompt`);
  - `codex.py:207-242` (shadow home symlinks, `_link_home_agents_fallback`);
  - `.gitignore:58` (`CLAUDE.local.md`), `.gitignore:61` (`.sase/`);
  - `.claude/settings.json` = `{}`;
  - `~/sase/memory/` exists, and `~/CLAUDE.md` = `~/AGENTS.md` (3.9 KB), containing the
    SASE Final Declaration block.

**From the researcher reports (not re-measured by the lead):**

- **cld:** Claude channel tests E1–E6; Grok `--rules` test E7; Codex 0 spawns (E12);
  Explore memory-read rates (E14); churn classification (E19); render timing (E18).
- **cdx:** Codex 0.160.0 source (`child_config.rs`, `role.rs`, `spawn.rs`,
  `feature_configs.rs`) for developer-instruction inheritance and the v2 override;
  Claude resumed-prompt semantics; acceptance-test matrix.
- **grk:** `--append-subagent-system-prompt-file` parse error on 2.1.289; the Codex
  channel split; untrack-ordering dependency.
- **mus:** `sase tmux-agent` launches raw `entry.argv`; `uvx` spelling; doctor and init
  enforcement placement.
- **gem:** binary strings for the hidden Claude flags; the agy `.agents/rules`
  fallback-channel idea; the ancestor-`CLAUDE.md` trap framing.

**Prior work:**
`research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`. This
report accepts its R1–R9 as amended above, and supersedes its statements that Codex
cannot suppress project `AGENTS.md` and that Claude subagent inheritance is unverified.
