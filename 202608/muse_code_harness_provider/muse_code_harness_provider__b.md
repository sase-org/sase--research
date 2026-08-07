---
create_time: 2026-08-07
updated_time: 2026-08-07
status: research
---

# Adding a Muse Code LLM Provider to SASE

**Question.** What would it take to add a SASE LLM provider for Meta's new Muse Code agentic
harness? What does SASE's provider contract actually require, how well does Muse Code fit it,
where does it *not* fit, and what should be built?

**Sources.** SASE code re-verified against `sase@98114b0e2`. Muse Code facts come from public
reporting and third-party deep dives published 2026-08-05 → 2026-08-07; Muse Code shipped in
**beta two days ago** and Meta has not published a stable CLI reference. Source reliability is
graded explicitly in Part 1 — this is the single most important caveat in this report.

## Executive Summary

**Structurally, this is a small, well-trodden change.** SASE's LLM provider layer is a mature
pluggy-based extension point with five built-in providers, and Muse Code's headless mode
(`muse exec "<prompt>" --json` streaming JSONL to stdout) is nearly a structural clone of
`codex exec --json`, which SASE already supports. The provider class itself is a ~250-line file
modeled on `src/sase/llm_provider/codex.py`, plus a stream parser modeled on
`_subprocess_codex.py`, plus one line in `pyproject.toml`. Everything else — autodetect, model
routing, `%model:muse/...`, doctor readiness, retry, agent naming, ACE colors, skill deployment
— falls out of declarative hooks the registry already reads.

**The real cost is not the provider class. It is the eleven satellite touchpoints and the
unverified flag surface.** A complete provider is ~20 files, not one. And critically:
**every Muse CLI flag in this report is second-hand.** The detailed sources and the cautious
sources directly contradict each other — one deep dive documents `muse exec`, `--json`,
`--yolo`, `--session-id`, `META_API_KEY`, `.agents/skills/`, and per-command exit codes, while
another guide published the same week states that subcommands, flags, MCP support, AGENTS.md
support, auth env vars, and session-resume mechanisms are all *"not documented at launch."*
Both cannot be right. No implementation should start before someone installs `muse` and reads
`muse --help`, `muse exec --help`, and one real `--json` transcript.

**Two genuine design tensions exist beyond flag verification.** First, Muse Code's headline
feature — *persistent async background subagents that live for the whole session* — is
architecturally redundant with, and potentially in conflict with, SASE's own agent
clan/family/lane fan-out model. SASE spawns and tracks parallel agents itself; Muse wants to do
that invisibly inside one `muse exec` call, producing work SASE cannot see, name, attribute, or
bead. Second, Muse ships an OS-native sandbox (Seatbelt/bubblewrap) that SASE's other providers
don't have, and SASE's non-interactive orchestration will require disabling it — a decision with
real blast-radius implications that deserves an explicit, documented choice rather than a
copied-in `--yolo`.

**Recommendation: build it in-tree as a sixth built-in provider, in four phases, gated on a
mandatory recon phase.** Phase 0 (recon, ~1 hour, blocking) installs the CLI and captures the
real flag/event surface. Phase 1 ships a minimal working provider modeled on Codex. Phase 2 adds
tool-call and thinking capture. Phase 3 completes the satellite surfaces (doctor, docs, skills,
ACE). Phase 4 is optional subagent alignment, and should probably be deliberately *declined* for
v1 in favor of `--subagent-worktree-isolation`-off / fan-out-off, letting SASE keep owning
parallelism. Two explicit non-goals for v1: do not wire Muse's hook system, and do not attempt
tiered `large`/`small` routing until Meta ships more than one model tier.

---

## Part 1: What Muse Code Actually Is

Meta Superintelligence Labs released **Muse Code** on **2026-08-05** as a beta terminal coding
agent for macOS and Linux, powered by the co-trained **Muse Spark 1.2** model. Meta's framing is
"long-horizon, multi-agentic workflows and transparent auditability." Zuckerberg's pitch is
completing "software engineering tasks across large repos."

### 1.1 Confidence-graded fact table

Confidence reflects how many independent sources agree and whether any is primary.

| Fact | Value | Confidence |
| --- | --- | --- |
| Binary name | `muse` | **High** — consistent across all sources |
| Install | `curl -fsSL https://dev.meta.ai/install.sh \| bash` | **High** — consistent everywhere |
| Platforms | macOS + Linux; no Windows at launch | **High** |
| Default model | `muse-spark-1.2` | **High** |
| Second model tier | `muse-spark-1.2-contributor` (rate-limited, 5-hour rolling window, usage may train products) | **Medium-High** — named in official-blog-derived reporting |
| Standard pricing | $1.25/M input, $0.15/M cached input, $4.25/M output | **High** — consistent across reporting |
| Contributor pricing | ~$0.10/M input, $0.002/M cached, $0.20/M output | **Low** — one source, self-flagged as secondhand |
| Context window | 1M tokens | **Medium** — via an OpenRouter listing, not Meta docs |
| Multimodal input | text, image, video, audio, PDF | **Medium** |
| Interactive mode | bare `muse` in a repo, TUI with slash commands | **High** |
| Headless mode | `muse exec "<prompt>"` | **Medium** — one detailed source; another says undocumented |
| Headless output | `--json` streams JSONL events to stdout | **Medium** — same single detailed source |
| Persistent background subagents | Session-lifetime, not per-task; nesting depth 1; concurrency = cores − 2 | **Medium-High** — the headline feature, widely reported |
| Append-only local event log | "intent before effect", idempotency keys, replay-exact restart | **High** — Meta's own auditability pitch |
| Auth env var | `META_API_KEY` | **Medium** — one source; another says auth env vars undocumented |
| Instruction file | `AGENTS.md` (loaded on workspace trust) | **Medium** |
| Skills dirs | `.agents/skills/` (project), `~/.agents/skills` + XDG (user); legacy `.claude/skills`, `.codex/skills` | **Medium** |
| Skills import | `muse skills import --from claude \| --from codex` | **Medium** |
| Sandbox | macOS Seatbelt / Linux bubblewrap; `.git`, `.muse`, `.agents` read-only to the agent | **Medium-High** |
| Hooks | Lifecycle events incl. session start, prompt submit, tool use, permission, model call, compaction, subagent start/stop, session stop | **Medium** |
| MCP | Supported; MCP servers bypass FS/network containment | **Medium** |

### 1.2 Reported CLI surface (treat as a hypothesis, not a spec)

One deep dive documents the following. **Every item here needs verification against the
installed binary.**

| Surface | Reported |
| --- | --- |
| Subcommands | `muse exec`, `muse resume [--last]`, `muse export [--redacted]`, `muse logout`, `muse skills import` |
| Flags | `--json`, `--session-id <uuid>`, `--max-model-steps <n>`, `--yolo`, `--disable-sandbox`, `--subagent-worktree-isolation`, `--redacted` |
| Slash commands | `/plan`, `/grilling`, `/grill-with-docs`, `/taste`, `/goal`, `/agent`, `/subagents`, `/agent-note`, `/agent-followup`, `/agent-interrupt`, `/login` |
| Subagent tools | `subagent_spawn`, `subagent_status`, `subagent_send_message`, `subagent_cancel`, `subagent_wait`, `subagent_read_result` |
| Approval modes | `on-request` (default), `untrusted`, `never` |
| Network modes | `proxy-only` (default), `restricted`, `enabled` |
| Exit codes | `0` success; `1` failed/cancelled/step-limit; `2` usage error; `130`/`143` signals |
| Export schema | `export_schema_version: 1` |

### 1.3 Conspicuously absent from every source

No source documents a **model-selection flag** (`--model`?) or a **reasoning-effort control**.
Both matter directly to SASE (§3.4, §3.5). One source states flatly that "no documented method
for model selection or reasoning effort controls" exists. If that holds, SASE's `%effort` must
be declared unsupported for Muse, and tier routing collapses to a single model.

### 1.4 The source-reliability problem, stated plainly

The most useful source for this report is also the least authoritative: a third-party deep dive
whose specificity (exact exit codes, the `cores − 2` formula, `export_schema_version: 1`) reads
like someone actually ran the tool, but which is not Meta documentation. That same source
openly warns that *"two of Meta's own pages already disagree on one default."* Meanwhile a
second independent guide lists most of that surface as undocumented. The honest reading is that
Muse Code is two days old, its docs are in flux, and any flag string committed to `muse.py`
today has a real chance of being wrong or renamed within weeks.

This is not a reason to skip the work. It is a reason to make Phase 0 blocking and to keep every
flag string in one small, obvious, easily-patched constant block.

---

## Part 2: What SASE's Provider Contract Actually Requires

### 2.1 The core abstraction

`LLMProvider` (`src/sase/llm_provider/base.py`) is deliberately thin — **one** abstract method:

```python
def invoke(self, prompt, *, model_tier, suppress_output=False,
           model_override=None, options=None) -> InvokeResult
```

Providers receive an already-preprocessed prompt and return `InvokeResult(content, usage)`. All
prompt preprocessing, postprocessing, logging, and retry orchestration live in the shared layer
(`_invoke.py`). Two optional overrides: `invocation_option_args()` (reasoning effort → CLI args)
and `resolve_model_name()`.

Everything else a provider contributes is **declarative metadata** via pluggy hooks in
`_hookspec.py`. The registry (`registry.py`) walks `sase_llm` entry points once, memoizes the
metadata payload, and derives autodetect order, `model → provider` routing, agent-name suffixes,
ACE colors, doctor hints, and CLI-management inventory from it. That design is why adding a
provider is mostly filling in a table.

### 2.2 Hook-by-hook, what Muse would return

| Hook | Purpose | Proposed Muse value | Risk |
| --- | --- | --- | --- |
| `llm_invoke` | Core dispatch | delegates to `invoke()` | — |
| `llm_provider_name` | Entry-point identity | `"muse"` | — |
| `llm_provider_short_name` | Agent-name suffix (`foo.mus`) | `"mus"` | Must be unique; `mus` is free |
| `llm_resolve_model_name` | Tier → model | see §3.4 | — |
| `llm_known_model_names` | Builds `model → provider` map | `["muse-spark-1.2", "muse-spark-1.2-contributor"]` | Only 2 known models |
| `llm_model_short_aliases` | Short suffixes | `spark12`, `spark12c` | — |
| `llm_skill_template_context` | Jinja2 vars for `SKILL.md` | `provider_name: "Muse"`, `provider_tool_name: "Muse Code"`, `provider_native_ask_tool: ?` | Ask-tool name unknown |
| `llm_skill_deploy_subpath` | Primary skills dir | `".agents/skills"` (**not** the `.muse` default) | Shared dir — see §4.3 |
| `llm_additional_skill_deploy_subpaths` | Extra dirs | possibly XDG muse config | Unverified |
| `llm_cli_status_color` | ACE color | Meta blue, e.g. `#0866FF` | — |
| `llm_autodetect_priority` | Autodetect order | `20` (between `qwen=15` and `agy=30`) | Judgment call — see §3.7 |
| `llm_autodetect_cli_name` | PATH probe | `"muse"` | — |
| `llm_auth_evidence` | Doctor offline check | env `META_API_KEY`; credential path under `~/.muse` (TBD) | Path unverified |
| `llm_install_metadata` | `sase agent-cli` | `manager: "native"`, `self_update_argv: ?`, `docs_url` | No known self-update cmd |
| `llm_default_retry_config` | Retry patterns | see §3.8 | Error contract unknown |
| `llm_hidden_from_model_pickers` | omit | — | — |
| `llm_hidden_from_agent_cli_management` | omit | — | — |

### 2.3 Full touchpoint inventory

`grep -rl opencode` over `src/`, `docs/`, `pyproject.toml` gives the honest blast radius of one
provider. Adding Muse means touching every equivalent:

| # | File | What changes | Auto-derived? |
| --- | --- | --- | --- |
| 1 | `src/sase/llm_provider/muse.py` | **New.** Provider class | No |
| 2 | `src/sase/llm_provider/_subprocess_muse.py` | **New.** JSONL stream parser | No |
| 3 | `src/sase/llm_provider/_tool_call_muse.py` | **New.** Tool-call normalization | No |
| 4 | `pyproject.toml:157-163` | `muse = "sase.llm_provider.muse:MuseProvider"` | No |
| 5 | `src/sase/llm_provider/_subprocess.py:46-50` | Re-export `stream_and_parse_muse_json_output` | No |
| 6 | `src/sase/llm_provider/_tool_calls.py` | Re-export `append_muse_tool_call_event` | No |
| 7 | `src/sase/doctor/checks_providers.py:20` | `_PROVIDER_SETUP_FALLBACKS["muse"]` install/auth hints | No |
| 8 | `src/sase/ace/tui/provider_styles.py:76` | `_ProviderStyle` entry | No |
| 9 | `src/sase/integrations/provider_badges.py:11` | Emoji badge | No |
| 10 | `src/sase/llm_provider/registry.py:41` | Optional `_PROVIDER_FAMILY_COLORS["meta"]` | No |
| 11 | `docs/llms.md` | ~9 sites: file table, entry points, autodetect list, new "Muse Code Integration" section, env-var table, config comment, model table, short-alias table | No |
| 12 | `docs/agent_providers.md` | New install/auth section + `SASE_MUSE_PATH` in the override list | No |
| 13 | `docs/plugins.md:34` | Built-in provider list | No |
| 14 | `docs/configuration.md`, `docs/ace.md`, `docs/xprompt.md` | Provider enumerations | No |
| 15 | `src/sase/default_config.yml` | Comment examples only | No |
| 16 | `tests/llm_provider/test_muse_provider_core.py` | **New.** Mirrors `test_claude_provider_core.py` | No |
| 17 | Model aliases | `muse_coder` auto-registers, inherits `@coder` | **Yes** |
| 18 | `%model:muse/...` routing | From `llm_known_model_names` | **Yes** |
| 19 | Agent naming (`foo.mus`) | From `llm_provider_short_name` | **Yes** |
| 20 | `sase agent-cli` inventory | From `llm_install_metadata` | **Yes** |

Roughly **16 hand-edited files, 4 free**. The registry's declarative design is doing real work
here — items 17–20 are exactly the surfaces that would be manual in a less disciplined codebase.

---

## Part 3: Mapping Muse Code onto SASE

### 3.1 The Codex precedent

`muse exec "<prompt>" --json` → JSONL on stdout is the same shape as
`codex exec --json` → NDJSON on stdout. Compare the existing Codex invocation
(`src/sase/llm_provider/codex.py:364-375`):

```python
base_args = [
    _resolve_codex_executable(), "exec",
    "--model", model,
    "--dangerously-bypass-approvals-and-sandbox",
    "--json", "--color", "never", "--skip-git-repo-check", "-",
]
```

The proposed Muse analog:

```python
base_args = [
    _muse_bin(), "exec",
    "--json",
    "--yolo",              # ← see §4.2; approval+sandbox off for non-interactive runs
    # "--model", model,    # ← only if a model flag actually exists (§1.3)
]
```

Codex should be the template for the whole provider, not just the args: prompt-on-stdin via
`-`, the interrupt-monitor loop, `SASE_LLM_LARGE_ARGS` / `SASE_MUSE_LARGE_ARGS` escape hatches,
and `provider_timer("Waiting for Muse")`.

### 3.2 The stream parser

`_subprocess_codex.py` is ~250 lines and does five things per JSONL line: extract assistant
text, buffer reasoning into a thinking file, format tool actions, collect error events, and
accumulate usage. `_subprocess_muse.py` must do the same against Muse's event vocabulary —
**which is entirely unknown.** Muse's log records are described as carrying a *sequence number,
timestamp, record type, durability marker, and payload type*, which is richer than Codex's flat
`{"type": ..., "item": {...}}`. Expect real work here, not a copy-paste. This is the single
largest unknown-shaped chunk of the implementation and the main reason Phase 0 must capture a
real transcript.

One likely bonus: Muse's `--json` stream should surface subagent lifecycle events, giving SASE
better visibility into in-run parallelism than Codex offers.

### 3.3 Tool-call and thinking capture

SASE normalizes tool calls into a shared artifact schema (`_tool_call_common.py`), with
per-provider adapters for Claude, Codex, Qwen, and Antigravity. Muse needs
`_tool_call_muse.py` + `append_muse_tool_call_event()`. Muse's own append-only event log is
arguably a *better* source than the stdout stream — but reading it means locating and parsing
`.muse/`, a private beta format. **Parse the stdout stream, not the on-disk log**, at least
until the export schema stabilizes; `muse export --redacted` (`export_schema_version: 1`) is a
plausible Phase 4 upgrade path.

### 3.4 Model tiers — the mismatch

SASE requires every provider to map `ModelTier` `"large"` and `"small"` to concrete models.
Muse currently exposes essentially **one** model with two *billing/rate-limit* tiers:

| SASE tier | Proposed Muse model | Note |
| --- | --- | --- |
| `large` | `muse-spark-1.2` | Standard pricing |
| `small` | `muse-spark-1.2-contributor` | Same model, cheaper, rate-limited, **usage may train Meta products** |

This mapping is defensible on cost and mirrors what SASE's `@cheap`/`@cheaper` pools do
elsewhere. But it is **not** a capability tier, and the contributor tier's data-usage terms mean
it should not be a silent default for proprietary code. Recommendation: map it as above, and
document the training-data implication explicitly in `docs/llms.md` and the doctor auth hint.
If Meta ships a genuinely smaller model later, revisit.

### 3.5 Reasoning effort

No effort mechanism is documented. Follow the **Qwen precedent** exactly
(`src/sase/llm_provider/qwen.py:155-162`):

```python
def invocation_option_args(self, options):
    return effort_cli_args(options, provider_label="Muse", supported={})
```

An empty `supported` map means an explicit `%effort` raises a clear error while a
config-default effort is logged and skipped — so a global `llm_provider.default_effort` never
breaks a Muse run. This is the correct behavior and requires no new machinery.

`--max-model-steps` is *not* an effort analog and should not be mapped to one; it is a runaway
guard. Consider exposing it via `SASE_MUSE_LARGE_ARGS` instead.

### 3.6 Instruction files and skills — the one place Muse is easier

Muse reportedly reads **`AGENTS.md`**, which SASE already generates as the canonical root
instruction file (`src/sase/amd/constants.py:5`, `src/sase/memory/inventory_models.py:14-22`).
`PROVIDER_SHIM_FILES` exists only for providers that *don't* read `AGENTS.md`
(`CLAUDE.md`, `GEMINI.md`, `QWEN.md`, `OPENCODE.md`). If Muse reads `AGENTS.md` directly,
**no `MUSE.md` shim is needed** — a genuine simplification.

⚠️ Verify this before assuming it. If Muse turns out to need its own file, add `"MUSE.md"` to
`PROVIDER_SHIM_FILES` and `INSTRUCTION_ROOT_FILENAMES`; `sase memory init` handles the rest.

Skills: SASE defaults a provider's deploy dir to `~/.<provider>` and lets the plugin override
(`src/sase/main/_init_skills_sources.py:28`). Muse should override to `.agents/skills` —
noting the caveat in §4.3.

### 3.7 Autodetect priority

Current order: `claude=10`, `qwen=15`, `opencode=18`, `agy=30`, fakey last. Muse at **`20`**
places it after the three mature providers and before Antigravity — appropriate for a
two-day-old beta. Trivial to change later; nothing else depends on the number.

### 3.8 Retry configuration

`ProviderRetryConfig` needs `error_patterns` matched against provider output. Muse's error
contract is undocumented. Follow the Antigravity precedent (`agy.py:353-369`), whose comment
explicitly acknowledges the same problem: start conservative (`max_retries=3`,
`wait_times=[60, 300, 1800]`), match only obvious transport/rate-limit wording, and **avoid the
bare `429` / `Too Many Requests` strings that the Codex provider already owns** so the global
error-based retry finder stays unambiguous. Users can extend via `llm_provider.retry.muse`.

Muse's rolling 5-hour contributor-tier rate limit makes rate-limit retry unusually relevant
here — a 5-hour window is far longer than the 1800s max backoff, so a rate-limited contributor
run will exhaust retries rather than wait it out. Worth documenting.

---

## Part 4: Where Muse Doesn't Fit Cleanly

These are the parts that genuine design attention, not just typing.

### 4.1 Persistent subagents vs. SASE's own fan-out model — the deepest tension

Muse Code's headline differentiator is *persistent async background agents that live for the
whole session*, with model-accessible `subagent_spawn` / `subagent_wait` tools, `cores − 2`
concurrency, and optional git-worktree isolation.

SASE already has an opinionated, first-class model for exactly this: **agent clans, families,
lanes, and hoods**, with named agents, tribes, workspace claims, and per-agent artifacts. A
single `muse exec` call could silently fan out to 14 subagents on a 16-core box, each editing
files in the claimed workspace, none of which SASE can name, attribute, display in ACE, bead,
or account for in its token telemetry.

Three options:

1. **Suppress Muse fan-out; SASE keeps owning parallelism.** Cleanest conceptually and
   consistent with how SASE treats every other provider. Requires a flag or config to disable
   subagents — *which may not exist.* If it doesn't, this option is unavailable.
2. **Let Muse fan out inside one lane; treat it as opaque.** Zero work, immediately available,
   and the model was co-trained for it — so suppressing it may actively degrade quality. Cost:
   an accountability hole in a system whose entire premise is structured, auditable agent work.
3. **Surface Muse subagents in SASE's model.** Parse subagent lifecycle events from the JSONL
   stream and project them into ACE. Genuinely valuable, genuinely expensive, and depends on
   event shapes nobody has seen.

**Recommendation: (2) for v1, with `--subagent-worktree-isolation` left off** so all work lands
in SASE's claimed workspace where the commit finalizer can see it — and (3) filed as a follow-up
task bead once the event vocabulary is known. Do not attempt (1) unless Phase 0 finds a real
disable flag; fighting a co-trained harness feature is a bad trade.

This tension is worth naming clearly to the user because it is the one place where Muse Code's
design philosophy and SASE's genuinely overlap and compete, rather than compose.

### 4.2 The sandbox decision

Muse ships OS-native containment (Seatbelt / bubblewrap), keeps `.git`, `.muse`, `.agents`
read-only to the agent, and defaults to `on-request` approvals and `proxy-only` networking. No
other SASE provider does this.

SASE's non-interactive orchestration cannot answer approval prompts, so approvals must be
disabled — that part is forced, and matches `codex --dangerously-bypass-approvals-and-sandbox`
and `opencode --dangerously-skip-permissions` precedent. But the reported `--yolo` flag
disables **approvals *and* sandbox** together, and separately `--disable-sandbox` forces full
network egress.

Two things deserve deliberate thought rather than a copied flag:

- **`.git` read-only is a real problem.** SASE agents commit through `sase commit`. If Muse's
  sandbox makes `.git` read-only to the agent, and SASE's commit finalizer runs *inside* the
  agent's process tree, commits could fail in confusing ways. Verify in Phase 0.
- **Prefer the narrowest flag that works.** If approvals and sandbox can be disabled
  independently (e.g. approval mode `never` + sandbox retained), that is strictly better than
  `--yolo` — SASE would gain containment it doesn't have with any other provider. Test this
  explicitly; don't default to the biggest hammer because Codex needed one.

### 4.3 Shared skills directories

Muse reportedly reads `.agents/skills/` **and** legacy `.claude/skills` / `.codex/skills`. SASE
already deploys generated skills into `~/.claude/skills/` etc. So Muse may pick up SASE's
Claude-targeted skills *automatically* — convenient, but it means skills rendered with
`provider_name: "Claude"` Jinja context could reach a Muse run and tell the agent to use tools
it doesn't have. Deploying to `.agents/skills` adds a second copy with correct Muse context,
and now two differently-rendered copies of the same skill are visible to one agent.

This needs a deliberate decision. Options: deploy only to `.agents/skills` and accept legacy
bleed-through; or investigate whether Muse's discovery precedence lets the correct copy win.
Low-stakes but genuinely confusing if ignored — worth 20 minutes in Phase 3.

### 4.4 Rust core boundary

Per `CLAUDE.md`, shared backend/domain behavior belongs in `../sase-core`. **This change is
almost entirely exempt.** Provider CLI invocation, subprocess streaming, and artifact writing
are Python-side adapter concerns that live in this repo today for all five existing providers,
and no other frontend needs to shell out to `muse`. The litmus test ("would a web app need this
to match the TUI?") says no.

One partial exception: if Muse model IDs or provider identity end up in wire types shared with
sase-core, that piece crosses the boundary. Check `sase-core` for a provider/model enum during
Phase 1; if models are strings end-to-end, nothing to do.

### 4.5 Beta churn

Two days old, no stable CLI reference, Meta's own pages already self-contradicting. Mitigations:
keep all flag strings in one module-level constant block; support `SASE_MUSE_PATH` (free — the
registry derives `SASE_<PROVIDER>_PATH` automatically); keep `SASE_MUSE_LARGE_ARGS` /
`SASE_MUSE_SMALL_ARGS` as user escape hatches; and write the provider tests against *recorded
fixture transcripts* so a flag rename is a one-line fix rather than an archaeology project.

---

## Part 5: Options Considered

### In-tree built-in vs. external plugin

| | In-tree (`sase_llm: muse`) | External plugin (`sase-muse`) |
| --- | --- | --- |
| Ships with `uv tool install sase` | Yes | No — separate install |
| Access to `_subprocess_*` / `_tool_call_*` internals | Direct | Private API, no stability guarantee |
| Doctor / styles / badges entries | Natural | Cross-repo edits still required in `sase` |
| Beta churn isolation | Churn lands in core | Isolated |
| Precedent | All 5 providers are in-tree | No third-party LLM plugin exists yet |

**In-tree.** The plugin path sounds appealing for an unstable beta, but the stream parser and
tool-call normalizer must import private `_subprocess_*` / `_tool_call_*` internals, and the
doctor/styles/badges dictionaries are hardcoded in core anyway — so a plugin would need
coordinated cross-repo changes and still couple to private APIs. Every existing provider,
including the vendor-neutral OpenCode, is in-tree. Muse is not the right vehicle for pioneering
third-party LLM plugins.

### Codex-clone vs. new parser architecture

**Clone Codex.** `muse exec --json` is structurally `codex exec --json`. Reuse
`stream_json_lines`, `append_error_events`, the artifact writers, and the interrupt-monitor
loop. Muse's richer per-record envelope (sequence, durability marker, payload type) is a
*mapping* problem inside `_process_muse_json_line`, not an architectural one.

---

## Part 6: Recommended Approach

### Phase 0 — Recon (BLOCKING, ~1 hour, no code)

Nothing else starts until this is done. Every flag in this report is unverified.

1. `curl -fsSL https://dev.meta.ai/install.sh | bash`; confirm the binary is `muse` and find its
   real install path and config/credential dirs.
2. Capture `muse --help`, `muse exec --help`, `muse resume --help`, `muse export --help`.
3. **Does `--model` exist? Does any reasoning-effort flag exist?** (§1.3, §3.4, §3.5)
4. **Can approvals and sandbox be disabled independently, or only via `--yolo`?** (§4.2)
5. **Is `.git` read-only under the sandbox — and does `sase commit` still work?** (§4.2)
6. **Is there any flag or config to disable subagent fan-out?** (§4.1)
7. Run one real task headless and **save the full JSONL transcript as a test fixture.** Catalog
   every event type, especially assistant text, reasoning, tool calls, usage, errors, and
   subagent lifecycle.
8. Confirm `AGENTS.md` is actually read (§3.6) and check auth: `META_API_KEY`, credential paths.
9. Confirm exact model IDs and whether `muse-spark-1.2-contributor` is selectable per-run.

Write the findings back into this document before implementing.

### Phase 1 — Minimal working provider

- `src/sase/llm_provider/muse.py` modeled on `codex.py`: `MuseProvider`, `_TIER_TO_MODEL`,
  `_muse_bin()` honoring `SASE_MUSE_PATH`, actionable `FileNotFoundError`, identity/metadata
  hooks per §2.2, empty-`supported` effort args per §3.5, conservative retry per §3.8.
- `src/sase/llm_provider/_subprocess_muse.py`: `stream_and_parse_muse_json_output()` built on
  the shared `stream_json_lines` / `append_error_events` helpers, driven by the Phase 0 fixture.
- `pyproject.toml` entry point; `_subprocess.py` re-exports.
- `tests/llm_provider/test_muse_provider_core.py` against the recorded fixture.

**Exit criteria:** `sase` launches a real agent with `%model:muse/muse-spark-1.2`, the response
comes back, and usage is recorded.

### Phase 2 — Tool-call and thinking capture

- `_tool_call_muse.py` + `_tool_calls.py` re-export; thinking-file capture if Muse emits
  reasoning; verify artifacts render in ACE.

### Phase 3 — Satellite surfaces

- Doctor hints (`checks_providers.py`), ACE style, emoji badge; verify
  `sase doctor -C llm.auth -v` reports Muse ready.
- Skills deploy subpath + the §4.3 decision; `AGENTS.md` / shim verification per §3.6.
- Docs: new `## Muse Code Integration` section in `docs/llms.md` plus the ~8 enumeration sites;
  `docs/agent_providers.md` install/auth section and `SASE_MUSE_PATH`; `docs/plugins.md:34`.
- **Document the contributor-tier training-data implication** (§3.4) wherever the tier mapping
  appears.
- `just check-full` — this change touches the broadening set.

### Phase 4 — Optional, defer by default

- Subagent event projection into ACE (§4.1 option 3), gated on the Phase 0 event catalog.
- `muse export --redacted` as a richer artifact source than the stdout stream (§3.3).

### Explicit non-goals for v1

- **Do not wire Muse's hook system.** SASE's Claude provider already moved *away* from
  tool-call hooks toward stream parsing (`_tool_calls.py:4-7`). Don't reintroduce the pattern.
- **Do not build tiered capability routing** until Meta ships more than one model.
- **Do not parse `.muse/` on-disk logs.** Private beta format; use stdout.
- **Do not enable `--subagent-worktree-isolation`.** Work must land in SASE's claimed workspace
  where the commit finalizer can see it.

### Effort estimate

| Phase | Effort | Confidence |
| --- | --- | --- |
| 0 — Recon | ~1 hour | High |
| 1 — Provider + parser | ~1 day | Medium (parser depends on event shape) |
| 2 — Tool calls | ~half day | Medium |
| 3 — Satellites + docs | ~1 day | High |
| **Total (v1)** | **~2.5–3 days** | Medium |

The estimate is dominated by the stream parser and the docs sprawl, not the provider class.

---

## Appendix: Change Checklist

```
NEW
  src/sase/llm_provider/muse.py
  src/sase/llm_provider/_subprocess_muse.py
  src/sase/llm_provider/_tool_call_muse.py
  tests/llm_provider/test_muse_provider_core.py
  tests/llm_provider/fixtures/muse_exec_transcript.jsonl   # from Phase 0

EDIT
  pyproject.toml                                  # [project.entry-points."sase_llm"]
  src/sase/llm_provider/_subprocess.py            # re-export parser
  src/sase/llm_provider/_tool_calls.py            # re-export tool-call appender
  src/sase/doctor/checks_providers.py             # _PROVIDER_SETUP_FALLBACKS["muse"]
  src/sase/ace/tui/provider_styles.py             # _ProviderStyle
  src/sase/integrations/provider_badges.py        # emoji
  src/sase/llm_provider/registry.py               # optional family color
  src/sase/default_config.yml                     # comment examples
  docs/llms.md                                    # ~9 sites incl. new integration section
  docs/agent_providers.md                         # install/auth + SASE_MUSE_PATH
  docs/plugins.md                                 # built-in provider list
  docs/configuration.md, docs/ace.md, docs/xprompt.md   # enumerations

CONDITIONAL (verify in Phase 0)
  src/sase/amd/constants.py                       # PROVIDER_SHIM_FILES += "MUSE.md"
  src/sase/memory/inventory_models.py             # INSTRUCTION_ROOT_FILENAMES += "MUSE.md"
  → then `sase memory init`

FREE (registry-derived)
  muse_coder model alias        %model:muse/...  routing
  foo.mus agent naming          sase agent-cli inventory
  SASE_MUSE_PATH override       Models panel / picker rows
```

---

## Sources

Meta / official-adjacent:

- [Meet Muse Spark 1.2 and Muse Code — Meta AI Developers blog](https://developer.meta.com/ai/resources/blog/build-with-muse-code/)

Technical deep dives (most detailed; least authoritative — see §1.4):

- [Inside Muse Code: Subagent Fan-Out, Skills, Event Logs — Digital Applied](https://www.digitalapplied.com/blog/muse-code-deep-dive-fan-out-event-log-skills)
- [Muse Code Explained: Meta's Multi-Agent CLI — Layer3 Labs](https://www.layer3labs.io/guides/muse-code-explained)
- [Muse Code: Independent Guide to Meta's Terminal Coding Agent](https://muse-code.dev/)
- [Muse Code Beta — Meta's New Terminal Coding Agent — explainx.ai](https://www.explainx.ai/blog/meta-muse-code-coding-agent-muse-spark-1-2-launch-august-2026)
- [Meta AI Releases Muse Code (Beta) — MarkTechPost](https://www.marktechpost.com/2026/08/05/meta-superintelligence-labs-releases-muse-code/)

Launch reporting:

- [Meta launches Muse Code, an AI agent for large code bases — TechCrunch](https://techcrunch.com/2026/08/05/meta-launches-muse-code-an-ai-agent-for-large-code-bases/)
- [Meta debuts first AI coding agent to take on Anthropic and OpenAI — CNBC](https://www.cnbc.com/2026/08/05/meta-debuts-muse-code-to-take-on-anthropic-and-openai-.html)
- [Meta enters the AI coding wars with Muse Spark 1.2 and Muse Code — VentureBeat](https://venturebeat.com/orchestration/meta-enters-the-ai-coding-wars-with-muse-spark-1-2-and-muse-code-with-persistent-async-background-agents)
- [Meta wants to get inside your terminal with its new coding agent — The Register](https://www.theregister.com/ai-and-ml/2026/08/06/meta-wants-to-get-inside-your-terminal-with-its-new-coding-agent/5283717)
- [Meta launches Muse Code AI coding agent for macOS and Linux — 9to5Mac](https://9to5mac.com/2026/08/05/meta-launches-muse-code-ai-coding-agent-for-macos-and-linux/)

SASE code (`sase@98114b0e2`): `src/sase/llm_provider/{base,types,_hookspec,registry,codex,qwen,opencode,agy,model_alias_defaults.yml}`, `src/sase/llm_provider/{_subprocess,_subprocess_codex,_tool_calls}.py`, `src/sase/doctor/checks_providers.py`, `src/sase/amd/constants.py`, `src/sase/memory/inventory_models.py`, `src/sase/main/_init_skills_sources.py`, `pyproject.toml`, `docs/{llms,agent_providers,plugins}.md`.
