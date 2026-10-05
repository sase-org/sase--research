# Dynamic instruction delivery, part 2: fresh-clone bootstrap and provider subagents

> Researcher: mus (independent track of 5-researcher swarm).
> Prior work reviewed: `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`
> (lead-consolidated report, 2026-10-05) via audited `sase artifact read`.
> Peer swarm reports (`__cdx`, `__cld`, `__grk`, `__gem` for *this* question) were
> deliberately not located, opened, or consulted.
> Checkout: sase `sase_23` workspace. Installed CLIs observed: Claude Code 2.1.289,
> codex-cli 0.160.0, Muse Code 1.4.2 (1.4.2-R4684.1), Grok Build (help observed 2026-10-05).

## 0. Position on the prior research

I agree with the consolidated report's recommendations (R1–R9): author in memory notes,
compose one frozen **instruction bundle** per provider invocation from layered memory
through an optional `SASE.md` composition spec, target audiences with closed launch
facts (never `%tag`), deliver exactly once through each adapter's explicit channel, and
verify with a conformance check. The "write files into the workspace" and monolithic
`SASE.md` variants should stay rejected for the reasons the lead gives (tracked-file
commits, Grok trust/gitignore, Codex unsuppressible discovery, stale reuse, ancestor
loads, render-point timing).

This report answers only the two open questions the requester raised against that plan:

1. **Fresh-clone interactive bootstrap:** after the migration, how does a developer who
   clones `sase-org/sase` and runs bare `claude` (or `codex`/`muse`/`grok`) still get a
   reasonably good `CLAUDE.md` (or equivalent)?
2. **Provider subagents:** how does each provider's subagent population get instructions
   equivalent to — or better than — what the current static files give them?

## 1. Fresh-clone interactive bootstrap

### 1.1 What exists today

- Root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md` are **tracked,
  byte-identical, 285 lines / ~17.5 KB** (verified with `cmp` on 2026-10-05). Generation
  is `sase memory init` via `src/sase/amd/templates/AGENTS.template.md` plus
  `PROVIDER_SHIM_FILES` in `src/sase/amd/constants.py`.
- `docs/agent_providers.md` ("Instruction double-load") explicitly keeps `CLAUDE.md`
  *for the human running `claude` in the same tree*, accepting Grok's double load as the
  cost. `docs/init.md` documents `sase memory init [--check|--no-commit|-M|-C]`.
- `INSTALL.md` canonical install is `uv tool install sase` (Python 3.12+, `sase-core-rs`
  wheels; no pure-Python fallback). No `uvx` reference exists in docs/README/INSTALL
  today. `sase` is a PyPI `name = "sase"` tool install, so `uvx sase …` resolves the
  same distribution ephemerally — viable as a fallback, but untested in CI and slower
  (wheel + `sase-core-rs` fetch on first run).
- `sase tmux-agent` launches **raw interactive CLIs** (`src/sase/tmux_agent/launch.py`:
  `entry.argv` + tmux window, no SASE prompt wrapping). It therefore depends on files on
  disk exactly the way a human's bare `claude` does.

### 1.2 What R7 breaks if bootstrap is not designed

Under R7 the 20 generated files become untracked/gitignored; humans get "gitignored
local projections" via a new `sase instructions sync`, and public repos optionally
commit a 10–15 line stub. A fresh `git clone` then contains:

- the stub (if committed), else **no** `CLAUDE.md`/`AGENTS.md` at all;
- no gitignored projections (they are never committed);
- a `sase/memory/` tree that a bare provider CLI cannot render by itself.

So bare `claude` in a fresh clone degrades from "full 285-line contract" to "stub or
nothing" unless something recreates the projection. That is a real regression for the
public-repo and contributor path, even though SASE runs themselves are fixed (they get
the explicit-channel bundle and never need the files).

### 1.3 Where could "run the generator if missing" live?

| Candidate host for the instruction | Verdict | Reason |
| --- | --- | --- |
| (a) The committed **stub file itself** (10–15 lines, hand-written) | **Adopt as primary.** | It is the only thing guaranteed present in a fresh clone. It is read by every provider's native discovery. Keep it static, provider-neutral, and self-bootstrapping (see §1.4). |
| (b) Package-base layer of the SASE-run bundle | Adopt as secondary. | Every SASE agent should know the bootstrap story (e.g. "if a human asks why `claude` sees less, run `sase instructions sync`"), but this never reaches a bare interactive session, so it cannot be the mechanism. |
| (c) `sase doctor` + `sase init -c` checks | **Adopt as enforcement.** | `doctor/checks_config_repos.py` already gates on memory init; extend the existing `sase memory init --check` drift check to cover `instructions sync` projections. Read-only, CI-friendly. |
| (d) `sase init` onboarding | Adopt opportunistically. | Fresh-contributor path already runs init; add the sync there. Does not help the "I skipped init and just ran `claude`" case. |
| (e) Provider **SessionStart / hooks** that auto-generate | Reject as primary; optional convenience only. | Claude hooks can do it, but Codex/Grok/Muse/agy have no uniform hook surface, hook trust varies, and auto-writing files from inside the session reintroduces the workspace-dirt problem. Also requires the user to have installed hooks — the fresh-clone user has not. |
| (f) Shell rc / installer side effects | Reject. | SASE explicitly never edits shell startup files (Muse install note). Out of scope and surprising. |
| (g) Relying on the agent "noticing" a missing file with no stub pointer | Reject. | No evidence agents reliably do this; the Grok zero-load regression went unnoticed ~4 weeks with no alert. Bootstrap must not depend on model initiative. |

The "where though?" answer is therefore **(a) + (c) + (d)**, with (b) as documentation:
the stub tells the model *and the human* the exact command; doctor/init enforce it;
the SASE-run bundle documents it.

### 1.4 Recommended bootstrap design

1. **Commit a small static stub, not a full export.** ~10–15 lines: how to build/test,
   plus a bootstrap block. It must never say "use `/sase_final`" (that directive is
   SASE-run-only and wrong for interactive use — the same correction the prior report
   makes for Claude subagents). Sketch (wording to be finalized in implementation):

   ```markdown
   # SASE (summary for interactive use)
   This checkout's full agent instructions are generated from `sase/memory/`.
   If this file is short, the full projection has not been synced yet.
   Human: run `sase instructions sync` (or `uvx sase instructions sync` if sase is
   not installed), then re-read this file.
   Agent reading this file: if the full projection is missing, run
   `sase instructions sync` (fallback `uvx sase instructions sync`) before
   continuing, then read the regenerated file. Do not commit generated files.
   Build: … Test: …
   ```

   Prefer `sase …` first and `uvx sase …` as fallback in the same line: installed users
   avoid the ephemeral fetch; uninstalled contributors still succeed. Do not invent a
   third spelling; `uv tool install sase` remains the documented install (`INSTALL.md`).

2. **`sase instructions sync` replaces `sase memory init` for projections.** Renders
   `mode: interactive` into gitignored `AGENTS.md`/`CLAUDE.md` (+ provider equivalents
   only where native discovery needs them) in primary checkouts and `~`; never writes
   into ephemeral SASE workspaces. It must be idempotent, fast (<5s on warm cache), and
   print the regenerated paths so the agent can re-read them.
3. **Keep exactly one stub per scope that needs native discovery.** Root only, unless a
   nested scope (`tools/`, `src/sase/ace/`, `demos/tapes/`) proves independent interactive
   traffic; nested stubs multiply maintenance and are today only seen by Claude lazily.
   Convert nested files to path-scoped reference notes per the prior report, and let the
   root stub point at them.
4. **`sase tmux-agent` must not depend on files either.** Route it through the same
   delivery hook with `mode: interactive` (explicit `--append-system-prompt-file`,
   prompt prefix, or shadow home per provider) instead of relying on disk state. The
   prior report already recommends this; I confirm it from the launch path
   (`launch_agent_window` runs raw `entry.argv` — any file dependence is accidental).
5. **Enforcement without nagging.** `sase doctor` gains an `instructions` check
   (projection fresh? stub present?); `sase init -c` reports drift; CI keeps a
   `--check` job so the stub never rots. No background daemon, no shell-hook
   auto-write.

### 1.5 Edge cases and rejections

- **User has no `sase` and no network (cannot `uvx`).** Stub still gives build/test
  lines — "reasonably good" degrades gracefully to "minimal but correct."
- **Agent must not commit generated files.** The stub says so; `sync` writes only
  gitignored paths; finalizer baseline (`run_agent_runner_bootstrap.py:326` staging
  `git add -A`) must ignore them or SASE runs will commit projections.
- **Do not commit a full `export` projection.** Suppression is impossible for Codex/agy
  (no discovery-disable switch), so a committed full file reintroduces exactly-once
  violations for 30%+ of runs. Stub-only is the correct ceiling for committed bytes.
- **`uvx run sase` vs `uvx sase`.** Canonical form is `uvx sase …` (`uvx` already means
  "run"). Document one spelling.

## 2. Provider subagents

### 2.1 What "subagent" means per provider (observed 2026-10-05)

| Provider | Subagent surface | What SASE does today | What the subagent loads today |
| --- | --- | --- | --- |
| **Claude** (`claude -p`, 2.1.289) | `Task` tool (built-in Explore/Plan + custom via `--agents <json-or-file>` / `--agent`), plus background `claude agents` | Passes `--append-system-prompt <single-turn directive>`; nothing subagent-specific | Built-ins other than Explore/Plan load the `CLAUDE.md` hierarchy (vendor docs). Whether they inherit `--append-system-prompt` is **undocumented and most likely they do not**. Installed `--help` shows `--agents`, `--agent`, `--add-dir`, `--forward-subagent-text` but **no `--append-subagent-system-prompt-file`** on this build — the prior report's cited flag (`-p`-only, v2.1.261+) could not be confirmed on 2.1.289 and must be re-verified before relying on it. Net today: subagents get the full `CLAUDE.md` **including** "use `/sase_final` before ending the turn," which is wrong for a subagent (only the parent declares). |
| **Codex** (`codex exec`, 0.160.0) | No documented subagent-in-exec channel; `exec --help` exposes `-c` config overrides, profiles, `--ephemeral`, `--ignore-user-config`, no `--agents`/`--rules` equivalent. Subagents are a TUI concept; headless delegation is threads/resume/fork. | Passes `-c developer_instructions=<single-turn directive>`; shadow `CODEX_HOME` links home `AGENTS.md` | Any `codex exec` child (resume/fork/thread) reloads project `AGENTS.md` natively (one per directory root→cwd) plus `CODEX_HOME` global. Cannot suppress a present project file. So Codex subagents today get the **same duplicated contract** as parents. |
| **Muse** (`muse exec`, 1.4.2) | In-turn subagents via its Task-equivalent; `--no-subagents` is not a `muse exec` flag (it is Grok's). `muse exec --help` shows `--subagent-worktree-isolation` (compat/no-op default), `--trust-workspace`, `--no-foreign-personal-context`, `--prompt-file`, `--session-id` — **no system-prompt or subagent-prompt flag at all**. | Prompt prefix via `_muse_directive.py` (`wrap_muse_prompt`) | Subagents inherit the parent's prompt context only if the parent forwards it; the prefix is **not** a channel to them. Today they effectively get workspace files (`--trust-workspace` loads workspace rules/skills) minus foreign personal context — no SASE contract unless the parent pastes it. |
| **Grok** (Build CLI) | `--agent <NAME>`, `--agents <JSON>` inline subagent definitions, `--no-subagents`, `spawn_subagent→Task` tool mapping (`src/sase/llm_provider/_tool_call_grok.py`); `--rules <TEXT>` appends to system prompt | No `--rules`/`--trust` passed today; workspaces stay untrusted so **zero** project files load (prior-report verification) | Subagents spawned in an untrusted workspace likewise load nothing natively. `--agents <JSON>` definitions are author-controlled, so the parent can embed instructions per subagent — currently unused by SASE. |
| **agy / Qwen / OpenCode** | agy: Antigravity rules (`GEMINI.md`+`AGENTS.md` double load, 24 KB/file + 20k-token budget); Qwen/OpenCode: file-discovery CLIs with no subagent prompt flag | Prompt prefix (agy print-mode wrapper); `--append-system-prompt` (Qwen, unverified); `instructions:` config or prefix (OpenCode) | Same file inheritance as parents; no separate subagent channel. |

Key correction to internalize: **the parent's explicit channel generally does not
propagate to subagents.** System-prompt appends, prompt prefixes, and shadow homes are
parent-invocation properties. Each provider needs its own subagent path, or the parent
must inline the subagent's instructions into the delegation payload (the `Task`
description/prompt), which always works but costs tokens per delegation.

### 2.2 Recommended subagent delivery (per provider, `role: subagent` render)

Render a dedicated **subagent bundle** (`role: subagent` + parent launch facts) alongside
the parent bundle. It contains the package contract + path/memory triggers relevant to
the delegation, but **excludes** `/sase_final`, stitch/commit, monitor/pipe, and
workspace-lifecycle directives — the parent owns declaration. Hard rules and reference
triggers stay unconditional per R9; "researcher won't touch code" never hides them.

| Provider | Subagent mechanism to adopt | Why / notes |
| --- | --- | --- |
| **Claude** | (1) Re-verify `--append-subagent-system-prompt-file` (or `--system-prompt-file` + `--agents` file) on the pinned CLI; if present, pass the subagent render there. (2) Regardless, add the subagent render to custom `--agents` definitions SASE authors and to the `Task` prompt prefix SASE constructs. (3) Exclude `~/CLAUDE.md` via `claudeMdExcludes` in SASE runs so neither parent nor subagent double-loads. | The prior report's flag was not in 2.1.289 `--help`; do not ship against a flag that may be print-mode-only, renamed, or removed. Belt and suspenders: explicit flag *plus* in-payload inline, with conformance deciding which one lands exactly once. |
| **Codex** | No new flag exists. Deliver via (a) shadow-`CODEX_HOME` `AGENTS.md` carrying the subagent render (same mechanism as the parent complement/full bundle), and (b) in-payload inline of the subagent contract in any SASE-constructed resume/fork/thread prompt. Keep workspaces free of full generated files (R7) so the shadow home is the only SASE-owned source. Respect 32 KiB `project_doc_max_bytes` — fail loudly over it. | In-payload inline is the only channel that survives resume/fork reconstruction (`codex.py` rebuilds context as `prompt + Work So Far + User Message`). |
| **Muse** | No prompt flag exists. Deliver via (a) in-payload inline: SASE's `Task`-equivalent delegation wrapper prepends the subagent render (or a pointer to `SASE_INSTRUCTIONS_FILE` when the child shares the artifacts dir), and (b) keep `--trust-workspace` so workspace rules remain available. Never rely on `--no-foreign-personal-context` being lifted for subagents. | Prefix-in-parent-prompt does not reach children; the delegation payload is the channel. Keep it short: subagent render should be the leanest audience (contract + task-relevant triggers). |
| **Grok** | Pass parent bundle via `--rules` (Phase 0 fix) and subagent content via `--agents <JSON>` definitions SASE authors per delegation, falling back to in-payload inline in the `spawn_subagent`/`Task` call. Keep workspaces untrusted (never `--trust`). Note `extra_rule_dirs` ("loads regardless of trust") as a possible file-based fallback, but prefer `--rules`/`--agents` JSON — no workspace files to suppress. | Grok is the cleanest case: author-controlled JSON definitions mean first-class subagent instructions with no file-discovery games. |
| **agy/Qwen/OpenCode/plugins** | In-payload inline via the delegation wrapper; new `llm_instruction_delivery(bundle) -> DeliveryPlan` hook with a prompt-prefix default for plugin providers (prior-report design). Unknown providers keep legacy file behavior until they declare support. | No per-provider subagent flag exists; the Task-prompt wrapper is the uniform fallback. |

Conformance extends naturally: assert the subagent session record shows the subagent
bundle hash exactly once and no SASE-owned native file loaded. For Muse/Grok/Codex
where transcripts under-count subagent usage (best-effort ledgers), conformance is on
*text/tool records*, not token counts.

### 2.3 What "equivalent or better" means concretely

- **Equivalent:** every subagent can reach the same memory triggers (`sase memory read`
  routing, `sase_repo` discipline, path-scoped notes) and the same repo inventory facts
  the static files give today.
- **Better/fixed:** (i) no `/sase_final`/stitch/commit confusion in children; (ii) no
  double-loaded contradictory repo lists; (iii) Grok/Muse children go from zero/partial
  to full home+project context; (iv) phase-worker and research-vs-code trims apply to
  children via launch facts without hand-typed tags; (v) provenance (`instructions.md` /
  `instructions.json` + hash in `agent_meta`, extended with `parent_hash` and
  `role: subagent`) answers "what did this child see?" — today's snapshot cannot.

## 3. Recommended solution (combined)

**Ship the prior report's bundle + adapter plan unchanged, plus these two addenda.
Neither reopens the file-writing or monolith decisions.**

A. **Interactive bootstrap (protects the fresh clone):**
   1. Commit a 10–15 line hand-written stub at root (`AGENTS.md`; `CLAUDE.md` either as
      the same stub or a one-line `@AGENTS.md`-style pointer where the provider honors
      it — full copies end). The stub carries build/test + the
      `sase instructions sync` / `uvx sase instructions sync` bootstrap block and a
      "do not commit generated files" line, and never mentions `/sase_final`.
   2. Build `sase instructions sync` (gitignored `mode: interactive` projections; never
      in workspaces) and route `sase tmux-agent` through the delivery hook with
      `mode: interactive`.
   3. Enforce with `sase doctor instructions` + `sase init -c` drift + CI `--check`;
      document `uv tool install sase` as install and `uvx sase` as fallback (one
      spelling).

B. **Subagents (protects delegated work):**
   1. Add a `role: subagent` audience to the launch-fact schema and renderer from day
      one of Phase 3 (not Phase 4): it is facts-first (parent role + subagent flag),
      needs no new `%tag`/`traits` syntax, and fixes a live bug (children told to
      declare).
   2. Implement the per-provider table in §2.2 behind the existing per-provider feature
      flags, with in-payload `Task`-prompt inline as the universal fallback and
      explicit flags (`--agents` JSON/file, re-verified subagent prompt-file flag)
      where they exist.
   3. Record `parent_hash → child_hash` provenance and extend conformance to subagent
      session records (exactly-once on text/tool records).

**Phasing:** stub + doctor/init warnings can land pre-Phase-1 (like Grok `--rules`
stopgap); `instructions sync` + `tmux-agent` reroute with Phase 2 (file untracking);
`role: subagent` + delegation wrapper with the first Phase-3 conditionals (alongside
lean monitor/gate and phase-worker renders); labels/`traits` stay deferred per
`corpus-before-mechanism`.

**What would change this recommendation:** (i) Claude removes every subagent prompt
channel and subagents provably inherit `--append-system-prompt-file` — then the
in-payload wrapper becomes redundant for Claude; (ii) Codex ships a reliable
discovery-disable switch — then committed stubs can grow; (iii) real outside
contributors demand a full committed contract — then revisit a committed `export`
projection with per-provider suppression measured, not assumed.

## Evidence index

- Audited read: `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`
  (48 KB) via `sase artifact read`; `sase repo open research` / `sase-research-artifacts`
  for paths. No peer `__cdx/__cld/__grk/__gem` file for this question was opened.
- Filesystem: root `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`/`QWEN.md`/`OPENCODE.md` identical
  (`cmp`), 285 lines; `src/sase/amd/constants.py` (`PROVIDER_SHIM_FILES`);
  `src/sase/amd/templates/AGENTS.template.md`; `docs/agent_providers.md` ("Instruction
  double-load", provider install/auth sections); `docs/init.md` (`sase memory init`
  variants); `docs/llms.md` (Muse command construction, Grok skills/instruction file,
  subagent-adjacent tool mapping); `INSTALL.md` (`uv tool install sase`).
- Code: `src/sase/llm_provider/claude.py` (`_SINGLE_TURN_DIRECTIVE`,
  `--append-system-prompt`); `codex.py` (`developer_instructions`, shadow `CODEX_HOME`,
  `_link_home_agents_fallback`); `muse_provider.py` + `_muse_directive.py`
  (`wrap_muse_prompt`, `--trust-workspace`, `--no-foreign-personal-context`);
  `grok.py` (no `--rules`/`--trust` today); `_tool_call_grok.py`
  (`spawn_subagent→Task`); `tmux_agent/launch.py` (raw `entry.argv`).
- Live CLI probes (2026-10-05): `claude --help` (has `--agents`/`--agent`,
  `--append-system-prompt`, no visible subagent prompt-file flag on 2.1.289);
  `codex exec --help` (no subagent/rules flags); `muse exec --help` (no prompt flags;
  `--subagent-worktree-isolation` compat only); `grok --help` (`--agents` JSON,
  `--agent`, `--rules`, `--no-subagents`). Versions: `claude 2.1.289`,
  `codex-cli 0.160.0`, `muse 1.4.2-R4684.1`.
- Single-source claims marked inline as unverified where vendor docs, not a session
  record, are the only source (agy/Qwen/OpenCode double loads, Qwen append flag).


