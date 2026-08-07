---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Adding Meta Muse Code as a SASE LLM Provider

**Question.** What would it take to add Meta's Muse Code agentic harness as a SASE LLM
provider? Where does it fit SASE's provider contract, where does it not, and what should
be built?

**Consolidates** `muse_code_harness_provider__a.md` (report A) and
`muse_code_harness_provider__b.md` (report B), plus lead-researcher verification.

**Evidence status.** Every Muse CLI fact below was verified directly against the shipped
Linux x86-64 binary of **`0.1.0-R708.1`** (SHA-256
`50937b6470cd0edf28eb683c352a5e7af3bcb1b015cd9a3b21dbf79d22af8182`, matching the
official release manifest), run under isolated `XDG_*` roots. SASE facts were
re-verified against `sase@41103b594`. Claims that still require an authenticated Meta
account are collected in §8 and appear nowhere else — nothing in the recommendation
depends on them.

Muse Code is a beta released 2026-08-05. Treat the CLI surface as a dated snapshot
pinned to the release above, not a stable upstream contract.

## 1. Executive summary

Muse Code is an unusually good fit for SASE's provider boundary. It has a first-class
headless mode with machine-readable output, explicit workspace/model/effort/permission
flags, native `AGENTS.md` support, and a native personal-skills root that maps cleanly
onto SASE's existing skill deployment hook. No new hooks and **no Rust core changes**
are required.

The work is breadth, not depth: two new modules plus ~14 satellite edits, mostly docs.

Report A and report B disagreed on several load-bearing points. Direct binary inspection
resolved all of them, and in most cases in report A's favor — report B's central claim
that Muse exposes no model or reasoning-effort control is **incorrect**.

**Recommendation (detail in §7): build a native, in-tree `muse exec --json` provider in
three stages, with no autodetect priority and no default sandbox teardown.** Report B's
blocking recon phase is now largely _complete_ — this document is its output. The only
genuine remaining blocker is one authenticated trace capture to pin the usage and
tool-call event shapes.

## 2. Conflicts between the two reports, resolved

| Question                        | Report A                     | Report B                      | Verified answer                                                                                                  |
| ------------------------------- | ---------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Does `--model` exist?           | Yes                          | "No source documents one"     | **Yes** — `--model <ID>` on `muse` and `muse exec`                                                               |
| Reasoning-effort control?       | Yes, `none…ultra`            | None; declare unsupported     | **Yes** — `--reasoning-effort none\|minimal\|low\|medium\|high\|xhigh\|ultra`, default `high`                    |
| SASE `max` mapping              | `max` → `ultra`              | Empty `supported` map         | **`max` → `ultra`**; Muse rejects `max` by name                                                                  |
| `llm_skill_deploy_subpath`      | `.config/muse`               | `.agents/skills`              | **`.config/muse`** — Muse's user root is `$CONFIG_DIR/skills/<id>/`; B's value yields a doubled `skills` segment |
| Prompt transport                | `--prompt-file`              | stdin `-`, like Codex         | **`--prompt-file`** — `exec` reserves stdin for `--api-key-stdin`                                                |
| Does `--yolo` exist?            | Implied equivalent           | Yes                           | **Yes**, and its three components are separately available                                                       |
| Approvals/sandbox separable?    | Assumed together             | Open Phase-0 question         | **Separable** — `--disable-approval` works with the sandbox retained                                             |
| `.git` read-only under sandbox? | Not raised                   | Real; may break `sase commit` | **Real**, but the blast radius is narrower than B thought (§6.1)                                                 |
| Autodetect                      | `cli_name` only, no priority | Priority `20`                 | **No priority** — `cli_name` alone still yields doctor + `agent-cli` inventory                                   |
| Current priority baseline       | —                            | `claude=10`, omits codex      | **`claude=0`, `codex=10`, `qwen=15`, `opencode=18`, `agy=30`, `fakey=1000`**                                     |
| `muse-spark-1.2-contributor`    | Reject as unverified         | Map to `small` tier           | **Unverified** — no offline evidence; do not ship as `small` (§8)                                                |
| sase-core changes?              | Not raised                   | "Check for a provider enum"   | **None** — providers are plain strings in sase-core; no enum exists                                              |
| ACE style + emoji badge         | Optional polish              | Required edits                | **Optional** — unknown providers already fall back to a neutral style and a `None` badge                         |
| `muse skills import`            | Not raised                   | `--from claude\|codex`        | **Exists**, as described                                                                                         |

Report B's two structural contributions survive intact and are the backbone of §5: the
Codex-clone framing, and the honest satellite-touchpoint inventory.

## 3. What Muse Code actually is

A terminal coding agent from Meta Superintelligence Labs, powered by the co-trained Muse
Spark 1.2 model. Installed via `curl -fsSL https://dev.meta.ai/install.sh | bash`, which
places a launcher at `${MUSE_INSTALL_DIR:-~/.local/bin}/muse`. The launcher polls
`https://api.meta.ai/muse-code/channels/muse-stable` and downloads a checksummed static
binary; macOS and Linux, x86-64 and ARM64.

The harness — not just the model — is the product: a main agent plus persistent
session-lifetime background subagents, an append-only event log with durability markers,
replay-exact restart, context compaction, and bundled skills (`plan`, `grill`,
`grill-and-record`, `taste`, `git`, `doctor`, `read-session`, `import`, `create-skill`,
`create-plugin`, `manage-settings`). The binary also carries `read_memory`/`add_memory`,
`cron_create`/`cron_delete`/`cron_list`, `create_goal`/`update_goal`/`report_progress`,
`monitor`, and the `subagent_*` tool family, plus a plugin system under
`$XDG_DATA_HOME/muse/plugins`.

This is why report A's rejection of "just point OpenCode at the Meta model API" is
correct: that tests model quality but integrates none of the harness. Meta's own
benchmark methodology runs Muse Spark 1.2 _inside Muse Code_ while competitors run in
their own products — the harness is part of the claim.

**Launcher env knobs** (verified in `muse-launcher.sh`): `MUSE_NO_AUTO_UPDATE`,
`MUSE_SYNC_UPDATE`, `MUSE_UPDATE_INTERVAL_SECONDS`, `MUSE_AUTH_PATH`,
`MUSE_CHANNEL_URL`, `MUSE_DOWNLOAD_HOST`, `MUSE_RELEASE_INFO`, `MUSE_LOGIN`,
`MUSE_CLIENT_ID`, `MUSE_AUTH_URL`. (`MUSE_INSTALL_DIR` is honored by the _installer_,
not the launcher.)

**Auth:** `META_API_KEY`, or `muse auth set` / `muse login` credentials under
`${XDG_CONFIG_HOME:-~/.config}/muse/`, or `muse exec --api-key-stdin`.

**Subcommands:** `resume`, `exec`, `export`, `trace`, `skills`, `sandbox`,
`session-message`, `auth`, `login`, `logout`, `init`.

## 4. The verified headless contract

```text
muse exec [OPTIONS] [PROMPT]
  --json                              # JSONL events on stdout
  --prompt-file <PATH>                # prompt from file (stdin stays free)
  --api-key-stdin
  --provider <echo|meta>              # default: meta
  --preset <native-basic|miniswe>
  --model <ID>
  --reasoning-effort <none|minimal|low|medium|high|xhigh|ultra>   # default: high
  --base-url <URL>
  --workspace <PATH>
  -w, --worktree [<off|create|existing>]                         # default: off
  --session-id <UUID>
  --user-input-auto-resolve           # offer request_user_input, auto-cancel prompts
  --no-foreign-personal-context       # exclude foreign personal rules/skills
  --context-compaction-strategy <ID>  # 3 named strategies
  --context-compaction-{soft,hard}-threshold <FRAC>
  --max-model-steps <N>  --max-tool-output-bytes <N>
  --parallel-tool-calls / --no-parallel-tool-calls
  --allow-workspace-switch  --disable-web-tools  --no-session-log  --image <PATH>

Safety (approval and sandbox are ON by default):
  --yolo                              # = trust-workspace + disable-approval + disable-sandbox
  --trust-workspace  --disable-approval  --disable-sandbox
  --approval-mode <untrusted|on-request|never>    --approval-judge <off|on>
  --sandbox-network <restricted|enabled|proxy-only>              # default: proxy-only
  --disable-write  --disable-shell  --enable-shell-tool
```

Notes that matter for the adapter:

- **`-w/--worktree` already defaults to `off`.** Report A's "never request a Muse
  worktree" needs no flag — just don't pass one.
- **`--subagent-worktree-isolation` is a documented compatibility no-op.** Its own help
  text says the capability defaults on, only an affirmative per-child request asks for
  isolation, and omission stays shared. Report B listed "do not enable it" as a v1
  non-goal on the belief it would move work out of SASE's workspace; the default is
  already shared, so the non-goal is right but for the wrong reason.
- **Exit code 2 is a usage error** (confirmed by triggering one), distinct from run
  failure.

### Reasoning effort — full canonical coverage

SASE's canonical vocabulary (`src/sase/xprompt/effort.py:20`) is
`none, minimal, low, medium, high, xhigh, max`. Muse accepts the same list with `ultra`
in place of `max`, and rejects `max` explicitly:

```text
unsupported reasoning effort `max`; expected none|minimal|low|medium|high|xhigh|ultra
```

So `effort_cli_args` gets a complete map — six levels 1:1 plus `max → ultra`:

```python
_EFFORT_CLI_ARGS = {
    level: ["--reasoning-effort", level]
    for level in ("none", "minimal", "low", "medium", "high", "xhigh")
} | {"max": ["--reasoning-effort", "ultra"]}
```

Muse would cover all seven canonical levels, where Codex rejects `none`/`max`
(`codex.py:32-38`) and Qwen supports none at all. One observability caveat from report A
stands: Muse defaults to `high` internally, so a run with no resolved effort will show
blank in SASE while Muse actually used `high`.

## 5. The JSONL event model

Captured from a real `--provider echo --json` run (35 events). Every envelope carries:

```json
{
  "schema_version": 1, "id": "…", "sequence": 20,
  "stream": { "kind": "session", "id": "…" },
  "recorded_at": 1780531400000035,
  "record_type": "status",          // event | status | reconciliation
  "durability": "ephemeral",        // durable | ephemeral
  "causation_id": "…",
  "payload_type": "run.output.delta",
  "payload_schema_version": 1,
  "payload": { "kind": "run_output_delta", "text": "…", "run_stream": {…} }
}
```

Observed `payload_type` families: `runtime.command.*`, `session.run.linked`,
`session.workspace_branch.observed`, `turn.input.user`, `run.lifecycle.started`,
`run.output.delta`, `run.terminal.completed`, `task.stream.linked`, `task.lifecycle.*`
(`proposed`, `accepted`, `scheduled`, `started`, `side_effect_intent`, `completed`,
`failed`).

stdout is pure JSONL; human diagnostics (workspace root, trust source, foreign-context
notices) go to **stderr**. Both reports assumed this; it is confirmed.

**Parser rules, in priority order:**

1. `run.terminal.completed.payload.text` is the authoritative answer. Use
   `run.output.delta.payload.text` only for live streaming into `live_reply.md`, so a
   replayed delta cannot duplicate output.
2. **`task.lifecycle.failed` does not mean the run failed.** The echo capture emitted it
   four times (`"model did not reach a terminal state within 2 step(s)"`) and still
   exited `0` with `run.terminal.completed`. A Codex-style `append_error_events` that
   treats any failure event as an error will manufacture spurious failures. Gate run
   success on `run.terminal.*` plus the exit code, and treat task-level failures as
   diagnostics.
3. `durability: "durable"` marks the replayable record set; `ephemeral` marks
   live-display noise. This is a cleaner filter than payload-type allowlisting and
   survives new event types.
4. `payload.terminal` and `payload.reason` on `run.terminal.*` distinguish terminal
   outcomes — parse those rather than pattern-matching text.
5. Tolerate unknown `payload_type` values and higher `schema_version` /
   `payload_schema_version` numbers; on failure, surface the observed versions rather
   than returning an empty success.

**Sessions.** With logging on, Muse writes
`${XDG_DATA_HOME:-~/.local/share}/muse/sessions/YYYY/MM/DD/<UUID>/` containing
`session.jsonl`, `cron.db`, and — verified — a `subagent/<uuid>/` directory per
subagent. That per-subagent lineage on disk is the concrete hook for the
subagent-attribution follow-up in §6.2.

`muse export --session <UUID> --out <path>` emits a self-contained
`export_schema_version: 1` document including tool calls/results, approvals, model ids,
`ses_`/`trajectory_` ids, fork/subagent lineage, and **verbatim encrypted reasoning** —
so `--redacted` matters for anything SASE retains. `muse trace inspect` accepts a
`--fixture`, which makes Muse's own logs replayable offline; useful for building test
fixtures.

`muse resume` is interactive only. There is no headless `exec --resume`, so SASE cannot
put Muse's exact restart path in its retry loop; keep the existing
accumulated-continuation-prompt behavior and retain Muse's log for manual recovery.

## 6. Where Muse does not fit cleanly

### 6.1 The sandbox, and what it actually threatens

Muse defaults approvals **and** an OS sandbox **on** (embedded bubblewrap on Linux,
Seatbelt on macOS), with `--sandbox-network proxy-only`. Verbatim from the binary:

> Under the workspace root and runtime temp root, `.git`, `.muse`, and `.agents` stay
> read-only; system temp roots remain full read/write except sandbox-owned enforcer
> files.

Report B flagged this as a risk to `sase commit` and was right that it is real, but the
mechanism is narrower than it assumed. SASE's commit finalizer runs **in SASE's own
Python process after `invoke()` returns** (`_invoke.py:308` → `run_commit_finalizer`,
which shells out to `git` via `subprocess.run` in `commit_finalizer_git.py`). That is
outside Muse's sandbox entirely and is unaffected.

The actual exposure is any commit the **agent itself** performs mid-run — the
`sase_git_commit` skill running `sase commit` as a Muse shell tool would hit a read-only
`.git`.

Because approvals and the sandbox are independently controllable, there are two coherent
modes rather than one forced `--yolo`:

- **Default (SASE parity):** `--trust-workspace --disable-approval --disable-sandbox`.
  Matches what SASE already does for Codex and OpenCode, and keeps in-run `sase commit`
  working. Document that Muse then has the same host authority as the SASE process.
- **Opt-in hardened mode:**
  `--trust-workspace --disable-approval --sandbox-network enabled`, sandbox retained.
  Approvals must go — a headless run cannot answer them — but SASE gains containment it
  has with no other provider. Suitable for read-only research agents that never commit.
  Offer it as config, not the default, so the uniform-runtime rule holds.

This is a better resolution than either report reached: A assumed the blanket teardown,
B wanted the narrowest flag but could not confirm one existed.

### 6.2 Persistent subagents vs. SASE's clan/family/lane model

Report B's deepest point, and it stands. Muse's headline feature is session-lifetime
background subagents with `subagent_spawn`/`wait`/`cancel` tools. One `muse exec` can
fan out to agents SASE cannot name, attribute, bead, or render in ACE — inside a system
whose premise is structured, auditable agent work. SASE counts the whole thing as one
agent slot.

Both reports independently landed on the same answer, which is the right one: **accept
the opacity for v1.** The model was co-trained with the harness; suppressing fan-out
trades away the reason to adopt Muse. Two things make this cheaper than it looks:

- Work stays in SASE's claimed workspace by default (worktree off, subagent isolation
  shared), so the commit finalizer sees everything.
- `task.stream.linked` / `task.lifecycle.*` events and the on-disk `subagent/<uuid>/`
  directories give a concrete, already-verified path to projecting subagents into ACE
  later. File that as a follow-up bead once the event vocabulary is exercised under real
  auth.

One item neither report raised: Muse has `cron_*` tools and a per-session `cron.db`, so
a run can in principle schedule work outliving the SASE invocation. Worth a look during
the authenticated spike.

### 6.3 Skill bleed — reproduced live, and it resolves cleanly

Both reports theorized about this; it is real and observable. Running the binary with
**fully isolated** `XDG_*` roots still produced:

```text
muse: Including your 17 Claude Code personal skills — manage with /settings.
```

`muse skills list --json` shows Muse discovering skills from `$HOME/.claude/skills`
**and** `$HOME/.codex/skills` — i.e. it reads those paths directly, not via XDG — and
the shadowed set is precisely SASE's own generated skills (`sase_git_commit`,
`sase_changespecs`, `sase_chats`, `sase_gate`, …), each reported as `skill-shadowed`.
Without intervention, a Muse run silently inherits skills rendered with
`provider_name: "Claude"` Jinja context, telling the agent to use tools it does not
have.

The fix is clean, and better than either report predicted. Muse's user skills root is
`$CONFIG_DIR/skills/<id>/SKILL.md` — verified by `muse skills install --scope user`,
which reported `$CONFIG_DIR/skills/bob_query` and wrote
`$XDG_CONFIG_HOME/muse/skills/bob_query/SKILL.md`. Since SASE's hook appends
`skills/<name>/SKILL.md` to a home-relative subpath
(`_init_skills_sources.py:target_path_for_subpath`):

```python
def llm_skill_deploy_subpath(self) -> str:
    return ".config/muse"      # → ~/.config/muse/skills/<name>/SKILL.md
```

This is exactly the OpenCode pattern (`opencode.py:120-121`) and works under chezmoi,
where only the first segment is dotfile-mangled. Report B's `".agents/skills"` would
have produced `~/.agents/skills/skills/<name>/SKILL.md` — wrong root and a doubled
segment.

A precedence test settles the rest: after installing a Muse-native copy,
`muse skills list` picked it as the winner and reported **both**
`$HOME/.claude/skills/…` and `$HOME/.codex/skills/…` copies as `skill-shadowed`. So
deploying to `.config/muse` makes the correctly-rendered copy win by itself. Pass
`--no-foreign-personal-context` as belt-and-braces (it does suppress the notice) rather
than as the primary mechanism.

### 6.4 Instruction files

Muse reads `AGENTS.md` natively (`muse init` scaffolds it; workspace rules load on
trust). `PROVIDER_SHIM_FILES` (`amd/constants.py:11`) exists only for providers that
_don't_ — `CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`. **No `MUSE.md` shim is
needed**, and adding one would grow the memory-maintenance surface for nothing. Both
reports agreed; confirmed.

### 6.5 Beta churn

The launcher can replace the binary hourly, while SASE's parser is tested against one
event shape. Mitigations, merged from both reports:

- Pass `MUSE_NO_AUTO_UPDATE=1` for SASE-launched subprocesses; users update Muse outside
  a run.
- Keep every flag string in one module-level constant block.
- Record the observed `muse --version` in run metadata; key fixtures by release.
- Test against recorded fixture transcripts so a rename is a one-line fix.
- `SASE_MUSE_PATH` is derived for free (`_registry_metadata.py:11-20`); keep
  `SASE_MUSE_LARGE_ARGS` / `SASE_MUSE_SMALL_ARGS` as escape hatches.

## 7. Recommended approach

Build a **native, in-tree `muse exec --json` provider** — report B's in-tree argument is
correct and unaffected by anything I verified: the stream parser and tool-call
normalizer must import private `_subprocess_*` / `_tool_call_*` internals, and the
doctor/style/badge dictionaries live in core regardless, so an external plugin would
need coordinated cross-repo edits _and_ private-API coupling. All existing providers are
in-tree.

### Stage 1 — Working provider (the bulk of the value)

- `src/sase/llm_provider/muse.py`, modeled on `codex.py`: command construction,
  tier/effort mapping, `SASE_MUSE_PATH` resolution with an actionable
  `FileNotFoundError`, temp prompt-file lifecycle, metadata hooks, interrupt +
  accumulated-context restart.
- `src/sase/llm_provider/_subprocess_muse.py`: JSONL parsing on the shared
  `stream_json_lines` helpers, implementing the five §5 parser rules. Re-export from
  `_subprocess.py`.
- `pyproject.toml` entry point: `muse = "sase.llm_provider.muse:MuseProvider"`.
- Metadata: name `muse`, short name `mus` (free), `cli_name` `"muse"`,
  `llm_skill_deploy_subpath` → `".config/muse"`, a Meta-blue `llm_cli_status_color`,
  install metadata (`display_name` "Muse Code", `version_argv ["--version"]`, version
  regex against `Muse Code 0.1.0 (0.1.0-R708.1)`).
- `_PROVIDER_SETUP_FALLBACKS["muse"]` in `doctor/checks_providers.py`. **This is
  required, not cosmetic:** `setup_hint()` sources the `auth:` line _only_ from that
  dict — no hook publishes it. Note also that a `docs_url` in install metadata overrides
  the fallback's `install:` text (`install from <docs_url>`), so put the curl one-liner
  in the fallback and omit `docs_url` if you want the exact install command shown.
- Tests against a recorded fixture, including the `task.lifecycle.failed`-with-exit-0
  case.

The invocation:

```bash
MUSE_NO_AUTO_UPDATE=1 muse exec \
  --json --workspace "$SASE_WORKSPACE" \
  --trust-workspace --disable-approval --disable-sandbox \
  --user-input-auto-resolve --no-foreign-personal-context \
  --session-id "$INVOCATION_UUID" --prompt-file "$SECURE_TEMP_PROMPT" \
  [--model …] [--reasoning-effort …]
```

Model and effort flags append only when SASE resolved a value. Until the model catalog
is confirmed under auth (§8), map **both** tiers to the standard Muse Spark 1.2 model or
let Muse choose; `small` then carries no cost guarantee, which is honest.

**Ship it explicit-only: declare `llm_autodetect_cli_name` but omit
`llm_autodetect_priority`.** `muse` is a generic executable name and SASE's autodetect
only checks PATH presence, so an unrelated `muse` could be selected. Omitting the
priority keeps the provider out of `autodetect_candidates` (`registry.py:101-103`) while
`provider_cli_available()` still uses `cli_name` for doctor and `sase agent-cli`
inventory (`registry.py:235`) — report A's design, and the mechanism checks out. Users
select via `llm_provider.provider: muse`, `%model:muse/…`, or `SASE_MUSE_PATH`.

Start with **no** Muse-specific retry config. Muse has its own transport retries; let a
nonzero exit fall into SASE's generic path and add patterns once real failures are
characterized. If patterns are added later, avoid the bare `429` / `Too Many Requests`
strings Codex already owns.

### Stage 2 — Parity

Tool-call normalization (`_tool_call_muse.py` + re-export), thinking capture if Muse
emits reasoning deltas, usage extraction, a small session-locator artifact (UUID +
release — not the raw export, which contains verbatim encrypted reasoning). Parse the
**stdout stream**, not `.muse/` on disk. Then the satellite surfaces: optional ACE style
and emoji badge, and the docs sweep — `docs/llms.md` (~9 enumeration sites plus a new
integration section), `docs/agent_providers.md` (install/auth + `SASE_MUSE_PATH`),
`docs/plugins.md`, `docs/configuration.md`, `docs/ace.md`, `docs/xprompt.md`,
`default_config.yml` comments. Run `just check-full` — this touches the broadening set.

### Stage 3 — Operational hardening

Subagent projection into ACE from `task.*` events and `subagent/<uuid>/` dirs; the
opt-in sandboxed mode from §6.1; nested-agent resource measurement (two concurrent Muse
runs: CPU, memory, git-lock pressure) before Muse is ever considered for autodetect or
shipped role aliases.

### Explicit non-goals for v1

Do not wire Muse's hook system (SASE's Claude provider deliberately moved _away_ from
tool-call hooks toward stream parsing). Do not parse `.muse/` on disk. Do not add a
`MUSE.md` shim. Do not build capability-tier routing on an unverified second model. Do
not touch `../sase-core` — providers are plain strings there, no enum to extend.

### Effort

Report B's estimate holds and improves: its blocking ~1h recon is now done, and the two
biggest unknowns it priced in (event vocabulary, flag surface) are resolved. **Stage 1 ≈
1 day; Stage 2 ≈ 1–1.5 days, docs-dominated; Stage 3 optional.** The remaining risk is
concentrated in usage/tool-call event shapes, which one authenticated run retires.

## 8. What still needs an authenticated Meta account

Everything here is deliberately out of Stage 1's critical path:

1. **Model catalog.** Confirm the live standard model id. Neither report could verify
   `muse-spark-1.2-contributor`; I found no offline evidence of it either. Report B
   mapped it to SASE's `small` tier on secondhand reporting that its usage may train
   Meta products — do not ship that as a default. If it exists, admit it only as an
   explicitly selected, clearly documented opt-in.
2. **Usage event shape** — the binary contains usage event families that an echo run
   never exercises. Return `usage=None` until captured.
3. **Tool-call and reasoning event shapes** under the real provider.
4. **Rate-limit and error terminal events**, before writing any retry patterns.
5. **Subagent lifecycle events** under a real fan-out, and whether `cron_*` scheduling
   can outlive a run.
6. **Pricing and context window** — reported by third parties, absent from primary
   sources.

Capture one authenticated run per case, sanitized, as release-keyed fixtures. That is
the only work that must precede Stage 2.

## 9. Change checklist

```text
NEW
  src/sase/llm_provider/muse.py
  src/sase/llm_provider/_subprocess_muse.py
  src/sase/llm_provider/_tool_call_muse.py            # Stage 2
  tests/llm_provider/test_muse_provider_core.py
  tests/llm_provider/fixtures/muse_exec_*.jsonl       # release-keyed

EDIT
  pyproject.toml                            # [project.entry-points."sase_llm"]
  src/sase/llm_provider/_subprocess.py      # re-export parser
  src/sase/llm_provider/_tool_calls.py      # re-export appender (Stage 2)
  src/sase/doctor/checks_providers.py       # _PROVIDER_SETUP_FALLBACKS["muse"] — required
  docs/llms.md  docs/agent_providers.md  docs/plugins.md
  docs/configuration.md  docs/ace.md  docs/xprompt.md
  src/sase/default_config.yml               # comment examples

OPTIONAL POLISH (neutral fallbacks already handle absence)
  src/sase/ace/tui/provider_styles.py       # _ProviderStyle
  src/sase/integrations/provider_badges.py  # emoji
  src/sase/llm_provider/registry.py         # _PROVIDER_FAMILY_COLORS["meta"]

FREE (registry-derived)
  muse_coder alias · %model:muse/… routing · foo.mus agent naming
  SASE_MUSE_PATH override · agent-cli inventory · Models panel rows

NOT NEEDED (verified)
  MUSE.md shim · PROVIDER_SHIM_FILES · INSTRUCTION_ROOT_FILENAMES
  ../sase-core changes · llm_autodetect_priority
```

## Sources

**Primary, verified directly.** Muse `0.1.0-R708.1` Linux x86-64 binary (`--version`,
`--help`, `exec --help`, `skills --help`, `export --help`, `trace --help`,
`sandbox --help`); a real `--provider echo --json` JSONL capture;
`muse skills list --json` and `muse skills install --scope user` precedence tests;
effort-validation probes; `https://dev.meta.ai/install.sh`;
`https://api.meta.ai/muse-launcher.sh`; the `muse-stable` channel and release manifest.

**Meta.**
[Muse Code and Muse Spark 1.2 announcement](https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2)
·
[Muse Spark 1.2 methodology](https://research.meta.ai/static/muse-spark-1-2-methodology)
·
[Meta AI Developers blog](https://developer.meta.com/ai/resources/blog/build-with-muse-code/)

**Third-party** (used only where primary sources are silent; see report B §1.4 on their
reliability): Digital Applied deep dive · Layer3 Labs · muse-code.dev · MarkTechPost ·
TechCrunch · VentureBeat · The Register · CNBC.

**SASE** (`sase@41103b594`):
`src/sase/llm_provider/{base,_hookspec,registry,_registry_metadata,_effort_args,_invoke,codex,qwen,opencode,agy,commit_finalizer_git}.py`
· `src/sase/xprompt/effort.py` · `src/sase/main/_init_skills_sources.py` ·
`src/sase/doctor/checks_providers.py` · `src/sase/amd/constants.py` ·
`src/sase/memory/inventory_models.py` · `src/sase/ace/tui/provider_styles.py` ·
`src/sase/integrations/provider_badges.py` · `pyproject.toml` · `../sase-core/crates/`
(provider identity is untyped strings).
