# Clone Bootstrap and Provider-Subagent Instructions

**Date:** 2026-10-05 · **Researcher:** grk · **sase checkout:** this workspace
(`sase_21`) · **CLIs:** Claude Code 2.1.289, codex-cli 0.160.0, grok 1.0.46, Muse 1.4.2

> **Questions this report answers.** The prior instruction-delivery research is treated
> as settled. Two gaps remain: (1) after generated `CLAUDE.md` / `AGENTS.md` files are
> untracked, how a developer who clones `sase-org/sase` and runs a raw provider CLI
> (`claude`, `codex`, `grok`, …) still gets a reasonably good instruction file; (2) how
> a provider's own subagents receive instructions that are equivalent to, or better
> than, what they get from today's committed files.

**Builds on:**
`research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`
(the "prior report"). I agree with that report's requirement adjustments R1–R9, the
facts-first audience model, adapter delivery, and the decision not to write full
generated files into SASE workspaces.

## Bottom line

Do not ask the model to generate its own instruction file. That idea fails the
bootstrap, loads too late, and writes the wrong audience into the tree.

**Issue 1 — clone / interactive CLI.** Keep a small committed **stub** in every
provider filename SASE already ships (`AGENTS.md`, `CLAUDE.md`, and the other shims).
The stub is the only thing a clone is guaranteed to have. Full interactive
instructions are a **host-side** render (`sase instructions sync`, also called from
`just install` and `sase init`) into gitignored overlays the CLIs already understand:
`CLAUDE.local.md` (already gitignored), `AGENTS.override.md` for Codex, `.grok/rules/`
for Grok. A one-line pointer in the stub ("if `sase` is on PATH, run `sase
instructions sync` and restart") is a human fallback, not the delivery path.

**Issue 2 — provider subagents.** Treat them as a distinct audience
(`role: subagent`), not as miniature SASE agents. They must get repo conventions and
memory triggers, and they must not get `/sase_final` or the single-turn directive.
Deliver that render through each adapter's **child channel** at `provider.invoke`. For
Claude that channel is real on the installed CLI: SASE already launches `claude -p`,
and `claude -p --append-subagent-system-prompt-file <missing>` on 2.1.289 errors with
`Append subagent system prompt file not found`. Today's committed `CLAUDE.md` is
actually worse for some children: Explore and Plan skip it.

The two issues share one rule: **the parent SASE turn and the interactive human
checkout are different audiences from the provider child.** One renderer, three
`mode`/`role` facts, three envelopes.

## What I am not re-litigating

The prior report already has the right architecture for SASE-launched agents:

- Render one bundle per provider invocation from layered memory.
- Deliver it through an explicit adapter channel, not by rewriting workspace files.
- Untrack the twenty generated instruction files (R7), because Codex cannot suppress a
  present project `AGENTS.md`.
- Target audiences with closed launch facts. No `%tag`.

This report only decides the two follow-through problems that R7 and "explicit
channels" create: the public clone, and the children a provider CLI spawns inside a
SASE turn.

## Issue 1 — A clone, then `claude`

### What happens today

`sase memory init` (the post-commit hook named in `glossary:agent-instruction-file`)
renders root `AGENTS.md` from memory and copies it byte-for-byte to `CLAUDE.md`,
`GEMINI.md`, `QWEN.md`, and `OPENCODE.md`. Those twenty files are tracked. A clone of
`sase-org/sase` therefore already contains a full `CLAUDE.md`. `CONTRIBUTING.md` and
`just install` never mention instruction files; they do not need to, because git is
the delivery path.

`docs/agent_providers.md` keeps `CLAUDE.md` for a second reason: a human running
`claude` in the tree. That is the path this gap is about. It is not a SASE agent
launch. It is an interactive, multi-turn provider session in a primary checkout.

### What R7 would break

If generated files are untracked and gitignored, a clone has no `CLAUDE.md`. Claude
Code's default project-instructions mode (`claude-md-or-agents-md`) then:

- loads project `AGENTS.md` only when **no** `CLAUDE.md` exists in cwd or any
  ancestor;
- ignores project `AGENTS.md` when `~/CLAUDE.md` exists, which it does on any machine
  that already uses Claude Code with a home file.

So a committed `AGENTS.md`-only stub is not enough for the common Claude user. They
need a project `CLAUDE.md` (stub or full), or a local overlay Claude will load next to
whatever home file they already have.

Grok 1.0.46 in this workspace still prints `Project trusted: no` and
`Project Instructions (0)`. An interactive `grok` in a newly cloned, still-untrusted
folder loads nothing from the repo until the human grants trust. Codex and Muse do
load a present `AGENTS.md` (Muse only after `--trust-workspace` / a trust grant).

### Why "instruct the agent to generate the file" is the wrong primary mechanism

The instinct is: put a sentence somewhere that says "if `CLAUDE.md` is missing, run
`sase instructions sync` / `uvx sase instructions sync`". Three facts kill it as the
main path.

1. **Bootstrap paradox.** The sentence has to live in a file that is present on a
   bare clone. That file is the stub. Once you have a stub, you no longer need the
   model to author a full `CLAUDE.md` in order to have *something*. The stub can
   point at the host command; the host command should still be what actually writes
   the full overlay.
2. **Load timing.** Claude loads `CLAUDE.md` at session start and re-reads it after
   compaction (`load_reason: compact` on `InstructionsLoaded`). A first-turn agent
   that writes `CLAUDE.md` does not change what this session already loaded. The
   human has to restart. A SessionStart hook that *writes* a file has the same race
   against the eager load; a SessionStart hook that returns `additionalContext` can
   inject text, but that is a Claude-only extra envelope, not a file other providers
   will see.
3. **Wrong audience, dirty tree.** A SASE-shaped render includes `/sase_final` and
   the single-turn contract. That is incorrect for an interactive `claude` session.
   If the agent writes a tracked `CLAUDE.md`, the next commit includes generated
   instructions again, which is the churn R7 is trying to end. If it writes a
   gitignored file, the host could have written that file before launch.

`uvx sase` is a reasonable *install* fallback (`docs/getting_started.md` already
documents `uv tool install sase`), but it is a poor *session* fallback: it uses the
published wheel, which will lag the checkout the contributor is actually working in,
and it does not exist for `instructions sync` until that command ships.

**Where the sentence belongs, if we keep it at all:** the committed stub, as a
restart instruction for a human (and for an interactive agent that notices it is
running on the stub). Not in packaged SASE core memory, not in a launched-agent
bundle, not only in `CONTRIBUTING.md`.

### Options

| Option | Verdict | Why |
| --- | --- | --- |
| Model writes `CLAUDE.md` after reading a stub sentence | **Reject as primary** | Late, circular, wrong audience, dirty tree |
| Claude SessionStart / Setup hook generates the file | **Claude-only belt** | Useful as `additionalContext` inject if `sase` is installed; does not help Codex/Grok/Muse; must not be the only path |
| Git `post-checkout` / `post-merge` hook | **Optional later** | Fails closed when `sase` is not on PATH; surprising for a public clone; no hooks are configured in this repo today (only samples) |
| Keep committing the full generated files | **Reject as end state** | Codex cannot suppress them (R7); 111 commits / 60 days of instruction-file churn |
| Committed stub + host-side `sase instructions sync` into gitignored overlays | **Adopt** | Present on every clone; full render for people who installed SASE; no `/sase_final` in the stub; SASE workspaces never see the overlay |
| Wrapper (`bin/claude` that syncs then execs) | Reject | Contributors type `claude`, not a wrapper; `sase tmux-agent` can wrap, raw CLIs cannot |

### Recommended clone design

Three layers, in this order of what a clone actually has:

**Layer A — committed stub (always present).** Keep the current shim set of
filenames, but replace the generated encyclopedia with a 15–25 line hand-written
stub, identical across `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `QWEN.md` /
`OPENCODE.md` so today's "same contents in every filename" invariant still holds for
the tracked files. Contents:

- this is a SASE checkout; full agent instructions are generated, not authored here;
- contributor setup: `uv venv && just install` (from `CONTRIBUTING.md`);
- materialize local instructions: `sase instructions sync` (after install) or
  `uvx sase instructions sync` (published CLI);
- how to build and test (`just check` vs `just check-full`);
- explicit: this interactive session is **not** a SASE turn — do not run
  `/sase_final`, do not submit a finalizer declaration;
- pointer to `docs/` and `sase/memory/` as the source of truth.

The stub must not include the SASE runtime contract. That is what made a committed
full file poisonous for Codex (duplicate `/sase_final`) and for interactive Claude
(told to end the turn).

**Layer B — gitignored interactive overlay (people who installed SASE).**
`sase instructions sync` renders `mode: interactive` and writes overlays the CLIs
already load, instead of overwriting the stub:

| Provider | Overlay | Why this file |
| --- | --- | --- |
| Claude | `CLAUDE.local.md` | Already in `.gitignore` as "Private Claude Instructions". Claude loads it as local scope, after the project stub, so a home `~/CLAUDE.md` no longer blanks the project. |
| Codex | `AGENTS.override.md` at repo root (gitignore it) | Codex's documented per-directory override; "at most one file per directory", override wins over `AGENTS.md`. |
| Grok | `.grok/rules/sase-interactive.md` (gitignore `.grok/rules/`) | `extra_rule_dirs` / `.grok/rules/` load regardless of folder trust, which is the actual Grok bug in workspaces and a gift for a newly cloned untrusted folder. |
| Muse / agy | gitignored `AGENTS.md` only in the **primary checkout**, never in a workspace | Muse walks `AGENTS.md` then `CLAUDE.md`; a gitignored full `AGENTS.md` in the primary checkout is fine because SASE agents run in workspace clones that do not carry gitignored files. |

Call `sase instructions sync` from `just install` and from `sase init`. Do not write
these overlays into ephemeral workspaces. `sase tmux-agent` should go through the
delivery hook with `mode: interactive` and not depend on the files.

**Layer C — mechanical Claude belt (optional, same release).** `.claude/settings.json`
is currently `{}`. A SessionStart hook that, when `sase` is on PATH, runs a
`--check`-style sync and returns the interactive render as `additionalContext` covers
the "I typed `claude` before `just install` finished" case without teaching the model
to write files. Skip the hook when `sase` is missing, so a casual clone still just
sees the stub. Do not use this hook to dump `AGENTS.md` into context once Claude is
reading files directly — the Claude memory docs warn that a SessionStart echo of
`AGENTS.md` double-loads.

### What "reasonably good" means for a clone without SASE

A visitor who clones the public repo and runs `claude` with no `sase` binary should
still be able to: install the project, run tests, and avoid SASE-turn rituals. They
should not be expected to know memory routing, beads, or `/sase_final`. The stub is
that bar. The full interactive overlay is for contributors who have SASE, which is
the same population that can run `just install`.

## Issue 2 — Provider subagents

### Two different children

SASE already has its own children: `/sase_run`, research swarms, monitors, gates.
Those are SASE agents. They get a bundle at `provider.invoke` like any other SASE
turn. This section is **not** about them.

This section is about **provider-native subagents**: Claude's Agent tool (Explore,
Plan, general-purpose, `--agents`), Codex's `spawn_agent` / `.codex/agents/*.toml`,
Grok's `spawn_subagent` / `--agents JSON`, Muse's child agents / `--agents`
overlay. They run inside one SASE provider turn, in a fresh context window, and they
return a summary to the parent.

They are common. This Grok session itself exposes `spawn_subagent`. Claude's Explore
agent is the default way Claude searches a tree. Codex documents that `AGENTS.md` or
a skill can request delegation.

### What they get today (worse than the committed files suggest)

| Provider | Parent (SASE) | Child today | Child after a naive "exclude native files + parent-only envelope" |
| --- | --- | --- | --- |
| **Claude** | `CLAUDE.md` hierarchy as a user-message attachment, plus `--append-system-prompt` single-turn directive | Built-ins other than Explore/Plan load the `CLAUDE.md` hierarchy. Explore and Plan **skip** it. Children do **not** inherit `--append-system-prompt` (SDK table: "The subagent doesn't receive the parent's system prompt"). So children get `/sase_final` from the file, and Explore/Plan get neither the file nor the directive. | If we `claudeMdExcludes` the files and only append on the parent, **every** child gets nothing SASE-owned unless we also pass a child channel. |
| **Codex** | shadow `$CODEX_HOME/AGENTS.md` (home layer) + project `AGENTS.md` | Custom agents add `developer_instructions`. Docs do not say children skip `AGENTS.md`. They inherit sandbox and, in CLI, the parent's live runtime overrides. | Untracking project `AGENTS.md` leaves children on whatever is in the shadow home. If that file is the parent bundle, children inherit `/sase_final`. |
| **Grok** | nothing in this workspace (`Project Instructions (0)`); `--rules` unused by the adapter | Child is a new session with its agent type / persona. Project files still require trust, which SASE does not grant. `--agents JSON` can set a child prompt. `extra_rule_dirs` load regardless of trust. | `--rules` on the parent is unverified for children. If it does not inherit, children stay at zero. If it does, they get `/sase_final`. |
| **Muse** | `--trust-workspace` plus a prompt prefix (single-turn directive) | Children share the lead's checkout. Project `AGENTS.md` loads because the workspace is trusted. Prompt-prefix inheritance is not documented. `--agents JSON` is an ephemeral overlay. | Untracking `AGENTS.md` plus a parent-only prefix likely zeroes children. |

So: today's committed files accidentally feed **some** Claude children the full SASE
contract (including `/sase_final`, which a child must not run) and feed **Explore /
Plan nothing**. Grok children in SASE workspaces already get nothing. A parent-only
explicit channel, without a child channel, makes Claude and Muse children worse than
today.

### The child render

`role: subagent` (already in the prior report's launch-fact table) is the right
audience. It is not a SASE agent. Hard rules for this render:

- **Include:** repo conventions (gotchas, rust-core boundary), reference-memory
  triggers, path-scoped notes (today's nested `tools/` and `src/sase/ace/` files),
  "report a summary, do not commit, do not declare, do not start monitors/gates".
- **Exclude:** `/sase_final`, the single-turn print-mode directive, bead-creation
  policy that belongs on the parent, finalizer language.
- **R9 still applies:** a `when:` must not hide the runtime contract from a SASE
  *agent*. A subagent is not a SASE agent; omitting `/sase_final` here is not a
  violation of R9, it is the point of the audience.

This is **better** than today for Explore/Plan (they finally see repo conventions)
and **better** for general-purpose (they stop being told to end a SASE turn they
do not own).

### Delivery per provider

The parent bundle and the child bundle are two files written next to each other in
`$SASE_ARTIFACTS_DIR` (`instructions.md` and `instructions.subagent.md`), hashed,
and passed in the same `_invoke.py` delivery plan.

**Claude (25% of runs). Verified on 2.1.289.**

SASE already launches:

```text
claude -p --verbose --model … --append-system-prompt <single-turn> …
```

Official CLI reference: `--append-subagent-system-prompt-file` "only applies in
non-interactive mode with `-p`", v2.1.261+. It is absent from `claude --help`
(the reference says `--help` does not list every flag). A live parse check:

```text
claude -p --append-subagent-system-prompt-file /tmp/sase-no-such-file.txt echo-test
# Error: Append subagent system prompt file not found: /tmp/sase-no-such-file.txt
```

The flag is real. Pass the subagent render on it, next to
`--append-system-prompt-file` for the parent. Exclude native `CLAUDE.md` /
`~/CLAUDE.md` with `claudeMdExcludes` in `--settings`. Nested Explore/Plan then
receive the child render even though they skip files — a strict improvement.

`--agents` JSON remains a fallback if a future CLI drops the append-subagent flag.
In `-p` mode it accepts a file (v2.1.281+). Definitions can set `omitClaudeMd: true`
(v2.1.271+) so children do not also load a stub. Do not rely on `--agents` as the
v1 path: it replaces named types, and it is easier to get wrong than a session-wide
append.

Forked subagents reuse the conversation prompt and **do not** get
`--append-subagent-system-prompt-file`. That is acceptable: a fork is the same
turn, and already has the parent bundle.

**Codex (31%).**

Reuse the shadow `CODEX_HOME` the adapter already builds
(`src/sase/llm_provider/codex.py`). Split the two audiences across the two
channels Codex already has:

- Shadow `$CODEX_HOME/AGENTS.md` = **subagent-safe** shared contract (the child
  render). Project stub, if committed, stays tiny. Children that re-discover
  `AGENTS.md` get conventions without `/sase_final`.
- Parent `developer_instructions` = SASE-turn overlay (`/sase_final`, single-turn).
  The adapter already passes `developer_instructions` for the single-turn
  directive.

Optional: write `.toml` custom agents into the shadow home
(`explorer` / `worker`) whose `developer_instructions` add role flavor on top of
the shared shadow `AGENTS.md`. Do not commit `.codex/agents/` in the sase repo
for this; it is per-invocation.

Until R7 lands, complement mode stays: shadow home carries only what the still-
tracked project `AGENTS.md` lacks, and that tracked file still poisons children
with `/sase_final`. That is an argument to land the Claude child channel and the
R7 untrack in the same window for Codex, not to delay the child render.

**Grok (13%).**

Keep workspaces untrusted (do not pass `--trust`). Deliver the parent bundle with
`--rules`. Deliver the child render with `--agents <JSON>` on the built-in types
(`general-purpose`, `explore`, `plan`) so a `spawn_subagent` gets a prompt even
when project files are empty. Independently, write the child render into a
per-invocation directory and pass it as `[paths] extra_rule_dirs` via the Grok
config the adapter controls — those files load without trust.

**Verify before flipping the Grok flag:** whether a child session includes the
parent `--rules` text. If it does, `--rules` must be the child-safe render and the
turn overlay must ride only in the parent user prompt (Grok has no second
append-system-prompt). If it does not, `--rules` can be the full parent bundle and
`--agents` / `extra_rule_dirs` carry the child.

**Muse (29%).**

Parent: keep the existing prompt-prefix path, with the parent bundle inlined.
Children: `--agents <JSON>` ("Supply one ephemeral agent-definition overlay").
Do not trust prompt-prefix inheritance; it is undocumented. Muse children share
the checkout, so a leftover tracked `AGENTS.md` would still load under
`--trust-workspace`. R7 removes that. Until R7, the overlay must be written to
*replace* child behavior, not to complement a full generated file.

**agy / Qwen / OpenCode.** Same pattern as the prior report's parent table, plus
the plugin hook `llm_instruction_delivery(bundle, *, audience) -> DeliveryPlan`
with `audience in {parent, subagent}`. Default: prefix the parent prompt, and if
the provider has no child channel, disable native subagents for that invocation
rather than silently launching children with no SASE contract.

### Do not disable provider subagents as the v1 strategy

`--no-subagents` (Grok), denying the Agent tool (Claude), and `agents.enabled =
false` (Codex) would make the child-channel problem disappear. It would also
remove Explore-style cheap search, which is the main reason these tools exist.
SASE's own `/sase_run` is the right way to spawn **another SASE turn**. It is the
wrong way to implement "grep this tree in a side context". Keep native subagents
on, and give them a child render.

## How the two issues interact

R7 (untrack generated files) is what makes both gaps real. The fixes have to land
in the same epic as the untrack, per provider flag:

```text
untrack CLAUDE.md  ──needs──►  Claude child channel
                               + committed stub
                               + CLAUDE.local.md sync for humans

untrack AGENTS.md  ──needs──►  Codex shadow home = child-safe
                               + parent developer_instructions = turn overlay
                               + committed stub small enough that a native
                                 project load is harmless
```

If Claude's child channel were missing, the prior report's own reopen condition
applies: keep a native Claude projection and exclude only `~/CLAUDE.md`. That
condition is **not** true on 2.1.289: the child flag parses. Implement the flag
path.

The committed stub is the one tracked file that both interactive clones and
provider children might still natively load (Codex, Muse, agy, Claude if excludes
fail). Keeping it free of `/sase_final` is the safety net that makes a missed
exclude non-fatal.

## Recommended solution

Keep the prior report's phases. Fold these two gaps into them rather than adding a
new epic.

### Phase 0 (days)

Unchanged from the prior report (Grok `--rules` parent stopgap, `sase doctor
instructions`). Add one measurement: in a Claude `-p` SASE run, spawn Explore and
general-purpose and record whether each saw `/sase_final` and whether each saw
repo gotchas. That is the baseline the child channel has to beat.

### Phase 1 (bundle renderer + adapter delivery)

- Renderer grows `role: subagent` and `mode: interactive` as first-class facts.
  Three frozen files per SASE invocation: parent, subagent, and (only for
  `sase instructions sync` / `tmux-agent`) interactive.
- Claude adapter: `--append-system-prompt-file` (parent) +
  `--append-subagent-system-prompt-file` (child) + `claudeMdExcludes`. This is
  implementable on the installed CLI.
- Codex adapter: shadow `AGENTS.md` = child-safe; `developer_instructions` =
  turn overlay.
- Grok adapter: `--rules` parent; `--agents` JSON + `extra_rule_dirs` child;
  still no `--trust`.
- Muse adapter: parent prefix + `--agents` overlay.
- Provenance records both hashes. Conformance asserts the parent hash once in
  the parent session, and the child hash in each child session the provider
  exposes.

### Phase 2 (untrack + clone bootstrap) — this is where R7 becomes safe

Do not untrack until Phase 1's child channels are on for that provider.

1. Replace the twenty generated files with the committed stub (one authoring
   source, copied to the shim names so the glossary invariant still holds for
   *tracked* files).
2. Gitignore `CLAUDE.local.md` (already), `AGENTS.override.md`, `.grok/rules/`.
3. Ship `sase instructions sync`; call it from `just install` and `sase init`.
4. Optional Claude SessionStart belt.
5. Convert nested `tools/` / `src/sase/ace/` / `demos/tapes/` files to
   path-scoped reference notes, as the prior report said. Those notes belong in
   the **child** render as well as the parent: they are the only way Explore
   sees Ace footer rules today, because Explore skips `CLAUDE.md` and Codex/Grok
   never read nested files.

### Phase 3+

Unchanged: lean monitor/gate renders, research vs code, matrix budgets. The
subagent render is already in Phase 1 because untracking depends on it.

### Success criteria (additive to the prior report)

- A fresh clone with no `sase` binary: `claude` / `codex` / `grok` load the stub
  and are not told to run `/sase_final`.
- A contributor clone after `just install`: `CLAUDE.local.md` (and siblings)
  exist, are gitignored, and contain the interactive render.
- A SASE Claude `-p` run: general-purpose and Explore both contain the child
  hash; neither contains `/sase_final`; the parent contains `/sase_final` once.
- A SASE Codex run after R7: project-doc is at most the stub; shadow home is
  child-safe; parent `developer_instructions` carry the turn overlay once.
- Workspace `git status` is never dirtied by instruction generation.

### What would change this recommendation

- **`--append-subagent-system-prompt-file` stops working, or starts applying
  outside `-p` only.** Fall back to `--agents` file definitions with
  `omitClaudeMd: true`. If that also fails, keep a native Claude projection and
  exclude only `~/CLAUDE.md` (the prior report's reopen condition).
- **Grok children inherit `--rules` and there is no way to split parent-only
  text.** Put the turn overlay in the parent user prompt (already the Muse
  pattern) and keep `--rules` child-safe.
- **Outside contributors actually show up on `sase-org/sase` and need more than
  the stub without installing SASE.** Grow the stub, still without `/sase_final`.
  Do not recommit a full export projection.
- **A contributor workflow appears that never runs `just install` or `sase
  init`.** Then, and only then, add a `post-checkout` hook that no-ops without
  `sase`. Do not add it speculatively; this repo has no live git hooks today.

## Evidence

**This checkout, 2026-10-05**

- `grok inspect` in `sase_21`: `Project trusted: no`, `Project Instructions (0)`.
- `claude -p --append-subagent-system-prompt-file /tmp/sase-no-such-file.txt echo-test`
  → `Error: Append subagent system prompt file not found` (flag parsed on 2.1.289;
  absent from `claude --help`).
- `src/sase/llm_provider/claude.py`: SASE launches `claude -p … --append-system-prompt`.
- `src/sase/llm_provider/codex.py`: per-run shadow `CODEX_HOME` with optional
  `~/AGENTS.md` symlink; `developer_instructions` already used for the single-turn
  directive.
- `src/sase/llm_provider/grok.py`: no `--rules`, no `--trust`, no `--agents`.
- Tracked instruction files: 20, listed by `git ls-files '*AGENTS.md' '*CLAUDE.md'
  …`.
- `.gitignore` already contains `CLAUDE.local.md` and `.claude/settings.local.json`.
  `.claude/settings.json` is `{}`. `.git/hooks` has only samples.
- `just install` installs the editable venv and required plugins; it does not
  generate instruction files.
- `CONTRIBUTING.md` documents `just install` / `just check` and does not mention
  `CLAUDE.md`.
- `docs/getting_started.md`: `uv tool install sase`.
- `sase memory read glossary:agent-instruction-file`: tracked shims must share
  contents; `sase init` (post-commit) is the current generator.

**Vendor docs, same day**

- Claude subagents: Explore/Plan skip `CLAUDE.md`; other built-ins load it;
  children do not inherit the parent system prompt; `--append-subagent-system-prompt[-file]`
  is `-p` only; `omitClaudeMd` on definitions; `CLAUDE.local.md` is the local
  scope; default mode ignores `AGENTS.md` when any ancestor `CLAUDE.md` exists.
  Sources: `code.claude.com/docs/en/sub-agents`, `cli-reference`, `memory`.
- Codex subagents: custom agents require `developer_instructions`; children
  inherit sandbox and CLI runtime overrides; project `AGENTS.md` discovery is
  unchanged. Source: `learn.chatgpt.com/codex/agent-configuration/subagents`.
- Grok: trust required for project files; `--rules`, `--agents JSON`,
  `--no-subagents`; `extra_rule_dirs` ignore trust and gitignore. Sources:
  `~/.grok/docs/user-guide/12-project-rules.md`, `16-subagents.md`,
  `26-config-reference.md`.
- Muse: `--agents JSON` overlay; `--trust-workspace`; children share the
  checkout; project rules ignored until trusted. Source: Meta Muse Code
  configuration / extending docs.

**Carried from the prior report, not re-measured:** run shares, the 790-token
home/project duplication, Codex's 32 KiB cap, the 111-commit churn figure.
