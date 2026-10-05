# Memory-Rendered Agent Instructions: Interactive Bootstrap and Subagent Delivery

> **Research query:** Migrate every existing agent instruction file so that SASE builds
> each agent's instructions from memory files right before it launches that agent. The
> requester accepts the recommendations in
> `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`. This
> report covers two questions that research left open, and ends with a recommended
> solution:
>
> 1. **Interactive use.** When another developer clones the sase repo and runs `claude`
>    (or any other supported provider CLI) outside SASE, how do we make sure that session
>    still has a reasonably good `CLAUDE.md` or equivalent? One idea is to tell agents to
>    run a `sase` or `uvx sase` command that generates the file when it is missing. Is
>    that a good idea, and where would the instruction live?
> 2. **Subagents.** How does each provider's subagents get instructions that match what
>    they get today, or that fix what is wrong today?

_Researcher `cld` · 2026-10-05 · sase `b6114d4f95` · Claude Code 2.1.289, codex-cli
0.160.0, grok 1.0.46, agy 1.2.17, Muse Code 1.4.2, qwen 0.25.0, opencode 1.18.34._

## Bottom line

**Question 1, interactive use.** The idea is right, but it can't be the whole answer,
and the instruction has a single natural home: **the committed root `AGENTS.md`**. That
is the only file every supported CLI reads natively in a fresh clone. Claude reaches it
through a two-line `CLAUDE.md`. So:

- Stop committing the full generated files.
- Commit a **small, generated `AGENTS.md` written for non-SASE readers**, plus a
  `CLAUDE.md` that only imports it. This stub carries a **bootstrap clause**: "full
  instructions are in `.sase/instructions/…`; if that file is missing or stale, run
  `just agent-instructions` (or `uvx sase instructions sync`), then read it."
- Make that path mechanical wherever the provider allows it, so it doesn't depend on the
  model choosing to obey:
  - **Claude** imports the generated file through `@.sase/instructions/claude.md`. I
    verified that a gitignored import target loads and a missing one is silently
    skipped.
  - **Codex** reads a gitignored `AGENTS.override.md` *instead of* `AGENTS.md`.
  - `just install` and an optional Claude SessionStart hook keep the generated files
    fresh.

**Question 2, subagents.** The prior plan has a gap here. **Native instruction files
flow down to subagents, but explicit channels (system-prompt flags, `--rules`, prompt
prefixes) mostly do not.** I verified this for Claude and Grok, and code reading shows
the same for Qwen. Moving delivery from files to flags, which is the prior report's R1,
therefore **strips instructions from subagents** unless each adapter also gets a
subagent channel.

Today's subagent instructions are also already wrong, and I measured the harm in the
last 30 days of Claude subagent transcripts:

- **General-purpose subagents get the full root contract.** 13 of 200 invoked
  `/sase_final`. At least two **submitted an accepted final declaration on behalf of
  their parent's turn**. One of those had been spawned only to "Reply with exactly:
  ack2".
- **Explore subagents get no project instructions at all.** They read `sase/memory/*.md`
  directly 7× as often as general-purpose subagents (11% vs 1.5%), bypassing audited
  `sase memory read`.

The fix is a separate **`role: subagent` render** delivered through each provider's
subagent channel. For Claude that is `--append-subagent-system-prompt-file` plus
`claudeMdExcludes`, both verified to reach Explore and general-purpose subagents. It is
backed by a **mechanical root-only guard**: a PreToolUse hook that denies `sase final …`
when the hook input carries an `agent_id`, which I verified Claude provides.

## New evidence

These results go beyond the prior report. All tests used throwaway directories that I
deleted afterwards.

| # | Finding | Evidence | Confidence |
| ---: | --- | --- | --- |
| E1 | **Claude: `--append-system-prompt` reaches only the root agent. `--append-subagent-system-prompt` reaches Explore and general-purpose subagents but not the root.** | `claude -p --append-system-prompt ROOT-APPEND-33 --append-subagent-system-prompt SUB-APPEND-44`; the root and both subagent types reported which markers they saw. | Verified (2.1.289) |
| E2 | **Claude: `CLAUDE.md`, including its `@imports`, reaches general-purpose subagents but not Explore.** This matches the docs: "Explore and Plan skip your CLAUDE.md files". | Same test, plus a probe of two subagents spawned from this session: Explore saw neither SASE heading; general-purpose saw both copies and two "SASE Final Declaration" sections. | Verified |
| E3 | **Claude: `claudeMdExcludes` passed via `--settings` removes `CLAUDE.md` for the root and for general-purpose subagents.** | Second `claude -p` test. | Verified |
| E4 | **Claude: a SessionStart hook's stdout reaches the root only. A SubagentStart hook's `additionalContext` reaches only the subagents its matcher selects.** | Second test, with the SubagentStart matcher set to `Explore`. | Verified |
| E5 | **Claude: PreToolUse hook input carries `agent_id` and `agent_type` for tool calls made inside a subagent, and neither for the root's calls.** | Third test, logging PreToolUse input for one root Bash call and one subagent Bash call. | Verified |
| E6 | **Claude: an `@import` of a gitignored file loads. An `@import` of a missing file is silently skipped,** leaving the literal `@path` line visible. | First `claude -p` test. The docs don't cover this case. | Verified |
| E7 | **Grok: `--rules` text does not reach subagents.** The child's system prompt lacks the marker. | `grok -p … --rules ROOT-RULES-77`; checked root and child session dirs (`audience: primary` vs `subagent`). | Verified (1.0.46) |
| E8 | **Grok subagents inherited native rules files while they still loaded.** A 2026-09-07 explore child recorded the same two `agents_md_files` as its parent. | Helper agent's search of `~/.grok/sessions/*/prompt_context.json`. | Verified, historical |
| E9 | Grok: an inline `--agents` JSON entry that shadows `general-purpose` with `promptMode: extend` did **not** inject text into the default child. | My test. The JSON shape may be wrong; the docs give no schema. | Tested, inconclusive |
| E10 | **Codex: `-c project_doc_max_bytes=0` drops all project `AGENTS.md` content and keeps the global `$CODEX_HOME/AGENTS.md`.** This contradicts the prior report's "no knob disables project discovery". It is undocumented. | Helper agent, using `codex debug prompt-input` against a temporary `CODEX_HOME`. | Verified, undocumented |
| E11 | Codex: hooks are stable. Both `SessionStart` and `SubagentStart` accept `additionalContext`. Project `.codex/` hooks load only for trusted projects, and each hook must pass a per-hash trust review. | Helper agent: docs (now at `learn.chatgpt.com`) plus binary strings. | Docs + binary |
| E12 | Codex: subagents are essentially unused in SASE. There were **0 spawned threads in the last 30 days** out of 1,652 rollouts, and 13 ever. The default `fork_turns=all` copies the parent's whole history, including the `AGENTS.md` block and `developer_instructions`, into the child. | Helper agent: `state_5.sqlite` `thread_spawn_edges` and rollouts from 2026-06 and 2026-07. | Verified |
| E13 | **Claude subagents in SASE: 518 transcripts in 30 days** (311 Explore, 200 general-purpose, 7 web-fetch). **13 general-purpose subagents invoked the `/sase_final` skill**, and **at least 2 submitted accepted declarations** for their parent's turn. | Python scan of `~/.claude/projects/*/*/subagents/agent-*.jsonl` and `.meta.json`. | Verified |
| E14 | **Explore subagents bypass memory rules.** 34 of 311 (11%) read `sase/memory/*.md` directly, against 3 of 200 (1.5%) for general-purpose. Use of `sase memory read`: 1% vs 10%. | Same scan. Some reads may have been requested by the parent, so this is a correlation. | Measured |
| E15 | **Codex and Claude provide a subagent-start hook that can inject context. Grok and agy don't.** Grok's SessionStart stdout is ignored and its SubagentStart is passive. agy has only Pre/PostInvocation. | Helper agents: `~/.grok/docs/user-guide/10-hooks.md`, the agy builtin docs, Codex docs. | Docs |
| E16 | **Today's committed `CLAUDE.md` is not actually good for outside humans.** It orders behavior only a SASE turn can follow: `/sase_final`, `/sase_memory_read`, `/sase_repo`, `sase_<N>` workspace rules. A fresh developer has none of those skills installed. | Read of root `AGENTS.md` and the `PROVIDER_SHIM_FILES` copies. | Verified |
| E17 | `docs/agent_providers.md` ("Instruction double-load", around line 244) is stale. Grok in SASE workspaces loads *zero* files, not two. | Prior lead verification plus E7 and E8. | Verified |
| E18 | A full home + project render (`sase memory init --check`) takes **about 1.9 s**. | Timed run. | Measured |
| E19 | In 60 days, 112 commits touched root `AGENTS.md`. Only **38** of them touched core or reference flat notes. The rest came from web rosters (glossary 52, decisions 20), the generated `README.md`, `sase.md`, and the generator itself. | `git log` classification. | Measured |

## Question 1: interactive use in a fresh clone

### What a fresh clone gives each provider today

Today the repo commits 20 instruction files: a full root render and four byte-identical
copies (`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`), plus three nested
directories with the same five files each. A fresh clone therefore gets *some*
instructions with no setup. But the content is the **SASE-run contract**, which is wrong
for an interactive session (E16):

- It says "use your `/sase_final` skill as the last action". There is no SASE turn and no
  such skill.
- It says to read memory "with your `/sase_memory_read` skill". The skill isn't
  installed, though the `sase memory read` CLI would work after `just install`.
- It describes ephemeral `sase_<N>` workspaces, linked-repo rules for repos the developer
  doesn't have, and `sase artifact read` for sidecars that aren't cloned.

So "keep the committed files for humans", the reason `docs/agent_providers.md` gives for
the double load, protects a file that is only half right for humans.

### Constraints that shape the answer

| Constraint | Consequence |
| --- | --- |
| A file generated *during* a session is not loaded natively; the agent has to `Read` it. | The bootstrap instruction must say "generate it, **then read it**", not only "generate it". |
| The only file **every** provider reads natively in a fresh clone is root `AGENTS.md`. Codex, agy, Qwen and OpenCode read it always; Grok and Muse once the folder is trusted. Claude ≥2.1.277 reads it only when no `CLAUDE.md` exists in the cwd **or any ancestor**. | The bootstrap clause lives in committed `AGENTS.md`. Committed `CLAUDE.md` stays as an import shim, because an ancestor `CLAUDE.md` (for example `~/CLAUDE.md` on athena) turns off Claude's native `AGENTS.md`. |
| Claude `@imports` of gitignored files load; missing imports are silently skipped (E6). | `CLAUDE.md` can import a generated file unconditionally, which costs nothing before the first sync. |
| Codex reads `AGENTS.override.md` *in place of* `AGENTS.md` in the same directory. | A gitignored override upgrades Codex to the full render automatically. Grok, Muse and agy don't read that name, so nothing loads twice. |
| Grok skips gitignored rules files, and its hooks can't inject startup context. | Grok, Muse and agy users rely on the bootstrap clause, meaning they read the file themselves. That is acceptable for the interactive case. |
| Claude SessionStart output is capped at 10,000 characters and the full render is about 17–21 KB. Codex project hooks need trust plus per-hash review. | Hooks can refresh the file and point to it, but they can't carry the whole render. They belong in a helper role, not as the primary channel. |
| The interactive render must be hermetic: no `~/.config/sase`, no sidecars, no owner identity (bare `sase init` needs a TTY for that), and no SASE state. | `sase instructions sync` must be a pure function of the repo, the packaged templates, and optional home config. |
| SASE runs must not double-load whatever is committed. | The committed stub has to be small, and each adapter suppresses it where it can (see [neutralizing the stub in SASE runs](#neutralizing-the-committed-stub-in-sase-runs)). |

### Options

| Option | Fresh-clone quality | SASE-run cost | Churn | Verdict |
| --- | --- | --- | --- | --- |
| **A. Keep committing full generated files** (status quo) | Medium. It's complete but tells humans to use SASE-only skills (E16). | Double loads unless every adapter suppresses them. Muse and agy can't. | 112 commits in 60 days, and merge conflicts across 47 workspaces | Reject |
| **B. Commit nothing; document `sase instructions sync`** | Poor until the developer reads CONTRIBUTING | None | None | Reject. Agents in a fresh clone get nothing. |
| **C. Thin committed stub plus "run sase if missing"** (the requester's idea) | Good for any provider with a shell tool, *if* the model obeys | Small; the stub can load twice harmlessly | Low | Adopt as the **universal fallback** |
| **D. C, plus native upgrades** (Claude `@import`, Codex `AGENTS.override.md`), plus refresh in `just install` | Good, and automatic for Claude and Codex, about 56% of SASE runs and most interactive use | Small | Low | **Adopt** |
| **E. Committed SessionStart hooks only** (`.claude/settings.json`, `.codex/hooks.json`) | Claude and Codex only. Grok can't do it, and Codex needs trust review. Runs code at session start for every contributor. | Must be guarded off in SASE runs (they fire in `-p`, E4) | None | Optional helper on top of D |
| **F. Hand-written stub** (the prior report's Phase 2 suggestion) | Good on day one, then drifts | Small | None, but it can drift silently | Prefer a **generated** stub that CI checks, so other SASE-managed repos get one from `sase init` too |

### Verdict on "tell agents to run sase if the file is missing"

**Good idea, with four changes:**

1. **Where:** in committed root `AGENTS.md`, as the first section, because it is the only
   file a fresh-clone agent is guaranteed to read. README and CONTRIBUTING are for
   humans, and agents read them unreliably. Skills don't exist yet on a fresh machine.
   Provider settings can't reach Grok.
2. **"Missing" must also mean "stale".** A gitignored file goes stale on the next
   `git pull`. The generated file should embed an input digest, and
   `sase instructions sync --check` should compare it.
3. **"Then read it."** The current session never loads a file generated during the
   session. The clause also tells an agent that already has the content (Claude through
   the import, Codex through the override) to skip the step. A sentinel heading makes
   that check possible.
4. **No silent installs.** The command should be one that works offline after
   `just install` (`uv run sase …` inside the repo). The `uvx sase …` fallback should be
   offered only with the user's consent, and pinned to the minimum version the repo
   declares. In default permission modes, Claude and Codex already ask before running
   it, which is the right behavior.

### Recommended design

#### Committed files: two at the root, none nested

**`AGENTS.md`** is generated by `sase instructions export` in `mode: export` and checked
in CI.

- **Budget:** about 80 lines and about 1.5k tokens, enforced by `sase instructions check`.
- **Content:** a short orientation, the bootstrap clause, build and test commands, and
  core-memory conventions that hold for *any* contributor. In sase today those are
  `gotchas` and `rust_core_backend_boundary`.
- **Excludes:** the SASE runtime contract, the home layer, repo inventories, web
  rosters, and the reference trigger list. Those go only into the generated local file.
  Leaving out rosters and triggers keeps the committed file's churn near zero: by E19, at
  most the 38 core-or-reference commits out of 112 could touch it, and in practice only
  edits to the few export notes will.

**`CLAUDE.md`** is two lines:

```markdown
@AGENTS.md
@.sase/instructions/claude.md
```

The other files go away:

- Delete `GEMINI.md` (agy reads `AGENTS.md`), `QWEN.md` (Qwen reads `AGENTS.md`), and
  `OPENCODE.md` (never read).
- Convert the nested `tools/`, `src/sase/ace/`, and `demos/tapes/` sets into path-scoped
  reference notes, as the prior report proposed.
- Grok, when trusted, reads `CLAUDE.md` too. It sees two literal `@…` lines, which is
  harmless.

A sketch of the generated stub's opening:

```markdown
<!-- Generated by `sase instructions export` from sase/memory/. Do not edit. -->
# sase - Agent Instructions (summary)

## Start here: full instructions are generated

This file is a short summary. The full instructions for this checkout are generated from
`sase/memory/` into `.sase/instructions/` (gitignored).

- If your context already contains the heading "sase - Interactive Agent Instructions",
  they are loaded: skip the rest of this section.
- Otherwise, run `just agent-instructions` (inside a dev env), or ask the user before
  running `uvx --from 'sase>=0.18' sase instructions sync`. Then read the file it prints. It reports
  whether an existing file is stale.
- If `sase` can't run, continue with this file alone and say so.

## Build and test
...
```

#### Generated, gitignored files

`sase instructions sync` renders `mode: interactive` into these files:

| File | Read by | Content |
| --- | --- | --- |
| `.sase/instructions/claude.md` | Claude, through the import (E6) | Full interactive render. It omits the home layer when `~/CLAUDE.md` already loads as an ancestor, so nothing is duplicated. |
| `AGENTS.override.md` (repo root) | Codex, natively, in place of `AGENTS.md` | Full interactive render, which already includes the stub's content. It includes the home layer, because interactive Codex doesn't walk above the git root. |
| `.sase/instructions/agents.md` | Grok, Muse, agy, Qwen, OpenCode, through the bootstrap clause | Full interactive render |

`.sase/` is already gitignored (`.gitignore:61`). Add `AGENTS.override.md` to
`.gitignore`.

The interactive render differs from the SASE-run bundle in specific ways:

- **It drops** the final declaration, single-turn rules, workspace rules, and handoff,
  plan, and questions skill rules.
- **It switches** skill references to CLI equivalents (`sase memory read <note> -r …`)
  unless a `skills_installed` fact says the skills are deployed.
- **It adds one sentence:** "This is an interactive session, not a SASE provider turn;
  `/sase_final` does not apply."
  - This matters even on Bryan's machine. Globally deployed SASE skills are visible in
    *every* interactive session, and their descriptions assert SASE-turn obligations.
  - Example: a plain `grok -p` I ran in `/tmp` announced "I'll check the required
    finalizer step", apparently because `~/.grok/skills/sase_final` was visible.

#### Requirements for `sase instructions sync`

1. **Hermetic.** It reads only the repo's memory, the packaged templates, and home memory
   or config if present. It never touches the SASE state dir or sidecars, never prompts
   for owner identity, and never needs a TTY.
2. **Never writes into SASE workspaces.** It detects them through the existing
   `.sase/checkout.json` or occupant markers and exits with a message. Primary checkouts
   and other clones are fine.
3. **Digest header and staleness modes.** It writes an input-digest header and supports
   `--check` (non-zero exit when stale) and `--if-stale` (cheap no-op when fresh).
4. **Fast.** About 2 s is acceptable (E18). It prints the path or paths to read.
5. **Version floor.** It honors a declared minimum version (for example
   `sase/sase.yml: min_sase_version`) so a stale `uvx` cache doesn't produce an old
   render.

#### Keeping the files fresh

Three mechanisms cover it, and none is required for correctness because the bootstrap
clause is always there:

- **`just install`** runs `sase instructions sync`. CONTRIBUTING already sends
  developers there. Add a `just agent-instructions` recipe for the bootstrap clause to
  name.
- **Optional git hooks.** `post-merge` and `post-checkout` hooks run
  `sase instructions sync --if-stale`. They are installed by `just install` and can be
  opted out of.
- **Optional Claude SessionStart hook** in the already committed `.claude/settings.json`
  (currently `{}`). It runs `sase instructions sync --if-stale --notify claude`. It exits
  0 silently when a SASE-run marker is set (for example `SASE_ARTIFACTS_DIR`), because
  hooks fire in `-p` (E4), or when `sase` is not on `PATH`. When it refreshes the file,
  it prints a short note well under the 10k cap: "Instructions changed since this session
  loaded `CLAUDE.md`; read `.sase/instructions/claude.md`." A Codex equivalent in
  `.codex/hooks.json` is possible, but trust plus hash review makes it more friction than
  it is worth.

#### Neutralizing the committed stub in SASE runs

The stub is small and its content is a subset of the SASE bundle, so a leftover double
load costs at most about 1.5k tokens. Suppress it where that's cheap:

| Provider | Suppression in SASE runs |
| --- | --- |
| Claude | `claudeMdExcludes` through `--settings` for the workspace `CLAUDE.md` and `AGENTS.md`, `~/CLAUDE.md`, and the import target (E3). Repo-owned files in foreign repos stay unexcluded. |
| Codex | `-c project_doc_max_bytes=0` in SASE-managed repos (E10). Because it is undocumented, the conformance check must cover it. Foreign repos keep native discovery. |
| Grok | Already untrusted, so nothing loads. Keep it that way (prior report). |
| Muse, agy | Accept the small stub load. Muse needs `--trust-workspace` for other project assets, and agy has no switch. |

This also changes the prior report's R7 reasoning. Its "decisive fact", that Codex can't
suppress a present project `AGENTS.md`, is false according to E10. R7 still holds for
the other reasons: wrong content for humans, churn, and conflicts. But it now argues for
a *small committed stub* rather than for committing nothing.

#### Bryan's own primary checkout and the home layer

The same `sync` serves the primary checkout. Home files (`~/CLAUDE.md`, `~/AGENTS.md`)
stay for interactive sessions outside any repo, such as athena administration in `~`.
Per-provider projections are what let `sync` avoid sending the home layer twice: the
Claude file omits it because `~/CLAUDE.md` already loads, and the Codex override
includes it. `sase tmux-agent` should still launch through the adapter delivery hook in
`mode: interactive` (prior report), so it doesn't depend on files.

## Question 2: subagent instructions

### The principle: files flow down, flags don't

| Provider | Do native files reach subagents? | Does the explicit root channel reach subagents? | Subagent-specific channel |
| --- | --- | --- | --- |
| Claude | General-purpose and custom: **yes**. Explore and Plan: **no** (E2). | `--append-system-prompt`: **no** (E1) | `--append-subagent-system-prompt[-file]`, `-p` only, every non-fork subagent including nested ones (E1). SubagentStart `additionalContext`, matchable by type (E4). |
| Codex | Fresh child: re-discovered (yes). Default fork: copied from parent history (yes). | `developer_instructions`: copied on fork; on `fork_turns=none`, unverified | SubagentStart `additionalContext` (E11). Custom roles in `agents/*.toml` with `developer_instructions`. The undocumented `subagent_developer_instructions` key exists in the binary. |
| Grok | **Yes**, while files load (E8) | `--rules`: **no** (E7) | None that injects context. Candidates: shadow `$GROK_HOME` home rules, or agent definitions that shadow built-ins by name. Both need a spike (E9). |
| Muse | Unverified | Prompt prefix: no, children get their own task prompt | The `--agents <JSON>` overlay, whose prompt is "appended as one developer context block". Unverified. |
| agy | Custom agents inherit ambient rules by default. Built-in children start "with a clean slate". | Prompt prefix: no | `rules:` frontmatter on custom agents. No start hook. |
| Qwen | Yes (code reading) | `--append-system-prompt`: no (code reading) | SubagentStart `additionalContext` |

So **R1 (deliver, don't write) silently regresses subagents** on every provider whose
root channel is a flag or a prefix, unless the delivery plan has a second slot.

### What subagents get today, and what it costs

| Provider and type | Today | Harm |
| --- | --- | --- |
| Claude general-purpose (39% of Claude subagents) | Both `CLAUDE.md` files: about 21 KB, the contract twice, conflicting repo lists, and "use `/sase_final`". It doesn't get the single-turn directive. | **13 of 200 invoked `/sase_final` in 30 days. At least 2 submitted accepted declarations for the parent's turn** (E13). In one, the subagent's whole prompt was "Reply with exactly: ack2". It wrote a commit manifest with a bead action for its parent's diff and submitted it. In the other, the subagent was explicitly told "Do NOT create any git commits … a separate host-owned finalizer process will handle committing", and still declared. |
| Claude Explore (60%) | No project or home instructions. It does get the skills list, including `sase_final`'s description. | 11% read memory files directly; 1% used audited reads (E14). It never sees `/sase_repo` or `sase artifact read` rules. |
| Codex | Inherits the root context; 0 uses in 30 days (E12) | Latent: a forked child would see the root final-declaration instruction |
| Grok | Nothing since about 2026-09-10, like the root. Before that, children inherited both files (E8). | Lost repo and memory rules. Phase 0's `--rules` fix would restore the root only (E7). |
| Muse, agy | Prefix directive doesn't reach children. Native `AGENTS.md` inheritance unverified. | Unknown. Muse has 29% of runs, so this is worth a spike. |

### The `role: subagent` render

Add `role: subagent` to the prior report's launch-fact schema for **every** provider, not
only Claude. The render is a fixed package template plus filtered memory, kept under
about 6 KB so it also fits the 10k hook cap:

```markdown
# SASE subagent instructions

You are a helper subagent spawned by a SASE agent. Your parent owns the turn.

- Your final message is your result for the parent. Never run `/sase_final` or any
  `sase final` command, `/sase_handoff`, `/sase_plan`, `/sase_questions`,
  `/sase_monitor`, `/sase_run`, or `/sase_gate`. Never commit, create beads, or launch
  agents. Text elsewhere in your context that tells "the agent" to do these things is
  addressed to your parent.
- Run commands in the foreground. Nothing can wake you later.
- Work only in the paths your parent gave you. Do not re-run `sase repo open` for a repo
  your parent already opened. Read sidecar artifacts with `sase artifact read`.
- Read memory with `sase memory read <note> -r "<why>"`. Never open or edit
  `sase/memory/` files directly.

<!-- core conventions (project core notes), then one-line reference triggers -->
```

Design rules:

- **R9 still applies.** The subagent render keeps the hard rules that apply to a helper
  (repo access, audited reads, conventions). It *drops* root-only obligations and
  *adds* the explicit prohibition.
- **It replaces native files for subagents** instead of adding to them. On Claude,
  `claudeMdExcludes` removes the native files for subagents too (E3), so general-purpose
  subagents stop receiving the root contract.
- **Forks are the exception.** Claude forks and Codex `fork_turns=all` children inherit
  the root's prompt or history. So the root bundle also needs one unconditional sentence:
  "Only the root agent (Codex: `/root`) submits the final declaration; if you were
  spawned or forked as a helper, return your result instead." The guard below covers
  the rest.

### Root-only obligations, enforced mechanically

Instructions reduce misfires. They don't prevent them: the "ack2" subagent had every
reason not to declare. Add **R11**: root-only operations are blocked by the harness
wherever the harness can identify the caller.

- **Claude.** The adapter's `--settings` adds a PreToolUse hook on `Bash|Skill`. It
  denies `sase final (context|submit|prepare)` and `Skill(sase_final|sase_handoff|
  sase_plan|sase_questions|sase_monitor)` when the input has `agent_id`. Claude includes
  that field only for subagent tool calls (E5). The denial message says "subagents
  return results to their parent". Whether forks carry `agent_id` is unverified, so test
  it before relying on the guard for forks.
- **Codex.** Same idea with a PreToolUse hook in the SASE shadow `CODEX_HOME`. The docs
  say subagent hooks receive the parent session id, so first check what identifies a
  child. Low priority while subagent use is zero.
- **Other providers.** There is no reliable caller identity. Rely on the render plus the
  root-only clause, and on the host checks below.
- **Host side, every provider.** `sase final submit` already validates against
  host-issued context. Record in the attempt log whether the caller was identified as a
  subagent, so conformance can count misfires even where blocking isn't possible.

### Delivery plan per provider

| Provider | Root (SASE run) | Subagent (SASE run) | Interactive session | Status |
| --- | --- | --- | --- | --- |
| **Claude** | `--append-system-prompt-file` bundle, plus `claudeMdExcludes` | `--append-subagent-system-prompt-file` render, plus the PreToolUse guard | General-purpose subagents get native `CLAUDE.md` → `claude.md`. Optionally, a committed SubagentStart hook gives Explore and Plan the render. | All mechanisms verified (E1 to E6) |
| **Codex** | Shadow `CODEX_HOME/AGENTS.md` bundle, plus `project_doc_max_bytes=0` | Root-only clause now. Later, a SubagentStart hook in the shadow home, with its trust hash pre-seeded in the copied `config.toml`. Avoid `--dangerously-bypass-hook-trust`, which also disables trust for the user's own hooks. | `AGENTS.override.md` | Suppression tested (E10). Hook path documented but untested under `exec`. |
| **Grok** | `--rules` bundle, workspace untrusted | **Spike:** a shadow `$GROK_HOME` with the render as a home rules file. Home rules load "regardless of folder trust", and children re-render rules. Or a shadowing `general-purpose.md` agent with `promptMode: extend` in the shadow home's `agents/`. | Bootstrap clause, or `extra_rule_dirs` in the user's own config | Root verified (E7). Child channel open (E9). |
| **Muse** | Prompt prefix (as today) | **Spike:** an `--agents` overlay for `general-purpose`, or `settings.run.developer_prompt` | Bootstrap clause | Unverified |
| **agy** | Prompt prefix | Root-only clause; accept that built-in children run clean | Bootstrap clause | Low priority (0.9% of runs) |
| **Plugin providers** | `llm_instruction_delivery(bundle)` | The same hook returns a `subagent` slot, or declares `none` explicitly | — | New hook-contract field |

Add **R10**: every adapter's `DeliveryPlan` has a `root` slot and a `subagent` slot. A
provider with no subagent channel must declare one of three statuses: `inherits-root`,
`inherits-native`, or `none`. `sase doctor instructions` reports that status, so a gap is
visible instead of silent.

### Conformance for subagents

Extend the prior report's conformance check:

- **Claude.** In `subagents/agent-*.jsonl` and `.meta.json`, the subagent render hash
  appears in the system prompt, no native `CLAUDE.md` loaded, and there are zero
  `sase final` tool calls.
- **Grok.** A child `prompt_context.json` with `audience: subagent` shows the expected
  rules source.
- **Codex.** `thread_spawn_edges` count, plus the child's instruction items.

Success metrics:

- Subagent `/sase_final` invocations go from 13 per 30 days to 0.
- Subagent-submitted declarations go to 0.
- Explore's rate of direct memory-file reads falls from 11% toward general-purpose's
  1.5%.
- Grok children show the render again.

## Changes to the prior recommendation

1. **Corrections:**
   - Codex *can* suppress project `AGENTS.md` (E10).
   - Grok's Phase 0 `--rules` fix restores the root only (E7).
   - Claude subagent inheritance is no longer "to verify"; E1 to E5 settle it.
   - The committed files are not a good human fallback today (E16).
   - `docs/agent_providers.md` "Instruction double-load" needs rewriting (E17).
2. **New requirements:**
   - **R10:** two-slot `DeliveryPlan` (above).
   - **R11:** root-only operations are enforced mechanically where the caller is
     identifiable (above).
   - **R12:** the committed instruction surface is a generated, budgeted `mode: export`
     `AGENTS.md`, plus a two-line `CLAUDE.md` import shim. It must be correct for a
     non-SASE session and must carry the bootstrap clause. This replaces "untrack all,
     optionally hand-write a stub".
   - **R13:** `sase instructions sync` is hermetic and refuses to run in workspaces. It
     writes per-provider gitignored projections with input digests and supports
     `--check` and `--if-stale`.
3. **Re-sequencing:** the Claude subagent fix doesn't depend on the bundle renderer.
   Ship it in Phase 0, because it addresses observed harm.

## Recommended solution

**Render one bundle per invocation from memory, as the prior report recommends, but with
three additions:**

- **Every adapter delivers two renders:** `root` and `subagent`.
- **Root-only operations are guarded mechanically**, not only by instructions.
- **The repo commits only a small generated export stub** whose first section bootstraps
  a fresh clone. The full interactive instructions are generated locally into gitignored
  per-provider files that Claude and Codex load natively.

### Phase 0: stopgaps for observed harm (days)

1. **Claude subagents, now.** Add `--append-subagent-system-prompt-file` in
   `src/sase/llm_provider/claude.py` (next to the `--append-system-prompt` at around
   line 436). The file content comes from a packaged subagent template: the prohibitions,
   memory and repo rules, and core notes. Pass `--settings` with the PreToolUse
   root-only guard. Don't exclude native `CLAUDE.md` yet, because general-purpose
   subagents still need the conventions until Phase 1. The appended prohibition and the
   guard override the "use `/sase_final`" text.
2. **Grok.** Ship the prior report's `--rules` root fix. Also run the spike on a
   shadow-`$GROK_HOME` rules file for children; it mirrors the existing shadow
   `CODEX_HOME` pattern. If the spike fails, note that Grok children run without
   instructions.
3. **Root-only clause.** Add one sentence to the shared contract note (`sase.md`), for
   forks and Codex children.
4. **Docs.** Fix `docs/agent_providers.md` "Instruction double-load". File a bug bead
   with E13 as evidence (go through `/sase_new_task`).

### Phase 1: bundle renderer with two-slot delivery

This is the prior report's Phase 1, plus:

- the `role: subagent` fact and template;
- a `DeliveryPlan` with `root` and `subagent` slots for every adapter, using the
  [delivery table above](#delivery-plan-per-provider);
- `claudeMdExcludes` and `project_doc_max_bytes=0`, turned on per provider in the same
  release as that provider's explicit delivery;
- subagent rows added to conformance.

### Phase 2: export stub plus interactive sync

This replaces the prior report's "untrack all" phase:

1. Add `sase instructions export` (committed `AGENTS.md`, `mode: export`, budgeted, CI
   `--check`) and the two-line `CLAUDE.md`. Delete the `GEMINI.md`, `QWEN.md` and
   `OPENCODE.md` copies and the nested sets. Update `PROVIDER_SHIM_FILES`
   (`src/sase/amd/constants.py:13`) and `sase memory init` accordingly. Users' own
   SASE-managed repos get the same pair from `sase init`.
2. Add `sase instructions sync` (R13) and a `just agent-instructions` recipe, call it
   from `just install`, gitignore `AGENTS.override.md`, and write the bootstrap clause
   into the export template.
3. Optional: the guarded Claude SessionStart refresh hook in `.claude/settings.json`,
   and the `post-merge`/`post-checkout` hooks.
4. Update `glossary:agent-instruction-file`, `docs/init.md`, `docs/agent_providers.md`,
   and CONTRIBUTING through `/sase_memory_write` where memory is involved.

### Phases 3 and later

Unchanged from the prior report: audiences, a `when:` evaluator in `sase-core`, and
traits only on demand. The subagent audience is the first conditional to ship, since
Phase 0 shows it has measured value.

### What would change this recommendation

- **The Grok and Muse child-channel spikes both fail.** Then those providers' children
  run with the root-only clause and no instructions. For Grok, reconsider limited native
  delivery: an untracked rules file in a shadow home.
- **Claude removes `--append-subagent-system-prompt-file`, or it stops reaching Explore.**
  Fall back to a SubagentStart hook that injects a pointer under 10k characters plus the
  file.
- **Codex's undocumented `project_doc_max_bytes=0` stops suppressing.** Accept the small
  stub double load; the stub is small precisely so that this case stays cheap.
- **Outside contributors appear and want more than the stub.** Raise the export budget
  and include reference triggers. Each step up costs some churn (E19).

## Open questions and spikes

| Question | How to settle it |
| --- | --- |
| Do Claude forks carry `agent_id` in hook input? | Log PreToolUse input from a forked subagent (the E5 setup with a fork). |
| Does Codex `SessionStart` or `SubagentStart` fire under `codex exec`, and do hook trust hashes survive the shadow-home symlink? | One `codex exec` run with a marker hook in a temporary shadow home. |
| Do Grok children load shadow-`$GROK_HOME` home rules? | `GROK_HOME=<shadow>` with `rules/marker.md`, spawn a child, grep the child's session files. |
| How do Muse task subagents inherit `AGENTS.md`, `--agents`, and `run.developer_prompt`? | Muse headless run with a forced `subagent_spawn` and markers in each channel. |
| Does Claude reload `@imports` after compaction? | Interactive test with `/compact`. The docs say the root `CLAUDE.md` is re-read, but don't mention imports. |

## Evidence index

- **Claude tests (2.1.289), four `claude -p` runs in throwaway git repos, all deleted.**
  They checked markers in `CLAUDE.md`, gitignored and missing `@imports`,
  `--append-system-prompt`, `--append-subagent-system-prompt`, `claudeMdExcludes` via
  `--settings`, SessionStart and SubagentStart (`matcher: Explore`) hooks, and a
  PreToolUse logger. The hidden flags were confirmed in the binary with `strings`.
- **Subagent probes from this session.** One general-purpose and one Explore subagent
  self-reported their context (E2).
- **Claude transcript scan.** `~/.claude/projects/*/*/subagents/agent-*.jsonl` and
  `.meta.json`, modified on or after 2026-09-05: 518 files.
  - "ack2" case: the sase_19 workspace session `a672cef7…`, subagent
    `agent-ad999a85200342362`. Its description was "Second placeholder no-op while
    waiting". It produced "Accepted final declaration for: commit".
  - Explicit-no-commit case: the sase_15 workspace session `a3fc9f67…`, subagent
    `agent-abdfdeab431b9d75e`.
- **Grok tests (1.0.46).** `grok -p … --rules …` and `--agents …` in a throwaway repo;
  `~/.grok/sessions/<dir>/<id>/{prompt_context.json,system_prompt.txt}`. Docs:
  `~/.grok/docs/user-guide/{12-project-rules,16-subagents,10-hooks,05-configuration,14-headless-mode}.md`.
- **Codex (helper agent).** `codex debug prompt-input` with a temporary `CODEX_HOME`;
  `state_5.sqlite` `thread_spawn_edges`; rollouts from 2026-06-12 and 2026-07-11; docs at
  `learn.chatgpt.com` (hooks, config, multi-agent). SASE adapter:
  `src/sase/llm_provider/codex.py` (developer_instructions at line 470,
  `_link_home_agents_fallback` at line 207).
- **Muse, agy, Qwen, OpenCode (helper agent).** `muse_provider.py:336-342`
  (`--trust-workspace`, `--no-foreign-personal-context`), `agy.py:476-522`, the agy
  builtin `agy-customizations` docs, the Qwen bundled JS, and OpenCode binary strings.
  Marked unverified where noted.
- **Claude docs (helper agent), `code.claude.com/docs/en/`.** Pages: hooks (10,000-char
  cap; SessionStart and SubagentStart `additionalContext`), sub-agents ("Explore and
  Plan skip your CLAUDE.md files"; `omitClaudeMd`), memory (AGENTS.md conditions;
  `claudeMdExcludes`; imports), and cli-reference (`--append-subagent-system-prompt[-file]`
  v2.1.205/v2.1.261, `-p` only).
- **sase repo.**
  - Paths: `src/sase/amd/constants.py:13`, `src/sase/llm_provider/claude.py:50,436`,
    `.gitignore:61` (`.sase/`), `docs/agent_providers.md:244`, `docs/init.md`,
    `CONTRIBUTING.md`, `INSTALL.md`.
  - The 20 tracked instruction files.
  - The `git log` churn classification (E19).
  - The `sase memory init --check` timing (E18).
- **Prior work.**
  `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`. This
  report accepts its R1 to R9 except where the
  [changes section](#changes-to-the-prior-recommendation) amends them.
