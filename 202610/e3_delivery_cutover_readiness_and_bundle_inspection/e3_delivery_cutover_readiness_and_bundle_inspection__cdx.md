# E3 instruction delivery cutover: readiness and historical inspection

Independent research by **cdx**, 2026-10-13. This investigation used the shared migration proposal, audited prerequisite bead records, the current sase and sase-core checkouts, local runtime metadata, focused tests, official provider documentation, and an offline Codex probe. No other report or chat from the current research swarm was consulted.

## Recommendation

**The implementation foundation is ready. The formal E3 entry gate still needs an acceptable E1 completion readout, and the epic text needs updating before the full implementation swarm launches.** Prepare the refreshed E3 plan now. Preserve its probe-first dependencies, and record the remaining entry-gate decision before authorizing the complete cutover.

E1 and E2 have landed; current parity passes; every observed root session in the bounded sample has a shadow manifest; no explicit shadow-render errors were recorded; and the focused correctness tests pass. The outstanding concerns are delivery-channel conformance, current provider discovery behavior, historical replay semantics, and evidence that the E1 fixes restored reliable completion. These belong in the E3 plan and its acceptance record. E4 file removal and E6's full visibility UI can remain separate.

The shared [migration proposal](memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md#e3-explicit-delivery-cutover) requires at least three days of acceptable E1 runs and clean E2 parity. The elapsed-time requirement is met. **Elapsed time and green instruction coverage do not establish an acceptable completion-rate readout.**

## What is already ready

| Prerequisite | Evidence | Assessment |
| --- | --- | --- |
| E1 scoreboard and stopgaps | `sase-1gu` closed 2026-10-06T16:05:33Z. Its audited acceptance notes report Grok delivery, Claude helper-template/guard probes, inventory, and corrected before/after evidence. | Landed. |
| E2 compiler and recording | `sase-1h3` closed 2026-10-06T22:09:16Z. The compiler, cache, CLI parity, Rust manifest, and invocation-boundary changes are present. | Landed. |
| Current source parity | `sase instructions render -p -j` exited 0; `contract_count=1`, with five allowed scaffolding/provider additions. | Clean for the current sase/home inputs. |
| Root invocation plumbing | Ordinary, declaration-recovery, and conflict-repair callers use `invoke_with_instructions`. Architecture tests police direct `provider.invoke` calls. | A useful cutover seam exists. |
| Rust wire and binding | Manifest schema v1 includes `explicit`, `inherits_native`, `inherits_root`, and `none`. The checked-out core HEAD matches sase's pin: `d30e1337a848f0bef8978153de3731badee00d46`. | No prerequisite binding gap found. |
| Correctness checks | 64 selected tests passed; the separately selected slow warm-latency test also passed. | Focused evidence is green. |

The main checkout examined was `8959b0e6fc6b048ee60f79731e676db994cb2ce7`. The installed `sase` command identified its host build as `0.17.1+2505.g731b7b18b`; `.venv` tests imported this workspace's code. Thus runtime observations and source tests have distinct, recorded provenance. I did not change runtime delivery or source code.

The present implementation is explicitly **shadow-only**. It records bundle Markdown and JSON, sets `SASE_INSTRUCTIONS_FILE` temporarily, and restores the environment after invocation. Providers do not consume that variable. A render exception logs/writes diagnostic evidence and leaves legacy delivery operational. With no artifact directory, the boundary calls the provider directly. These facts are visible in the [boundary](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/llm_provider/_instruction_boundary.py) and [bundle documentation](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/docs/instruction_bundles.md).

## Current operational evidence

I ran:

```bash
sase instructions verify -c -n 50 --since 7d -j
```

The snapshot was generated at **2026-10-13T20:27:10Z**. The window began 2026-10-06T20:27:04Z, with a maximum of 50 selected runs per provider. It covers locally indexed runs across projects, rather than the complete fleet.

| Provider | Root manifest coverage | Observed contract | Home | Project | Native full SASE projections | Warm ordinary render p95 |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| Claude | 7/7 | 2× | yes | yes | 2× | 167.0 ms |
| Codex | 25/25 | 2× | yes | yes | 2× | 99.5 ms |
| Grok | 22/22 | 1× | no | yes | 0 | 121.1 ms |
| Muse | 12/12 | 1× | no | yes | 1× | 171.2 ms |
| agy | 2/2 runs | unverifiable | absent | unverifiable | unverifiable | 40.7 ms |

`errors_total` was zero. Claude's observed helpers reported zero finalization attempts and zero accepted helper declarations. Its foreign-memory column still reports auto-memory. Grok's sample reported its memory-v2 flag false. These match the intended E1/E2 state: E3's home delivery, deduplication, and foreign-memory decisions remain useful work.

Coverage means a same-provider manifest precedes the observed session start, allowing five seconds of skew. It proves recording coverage; it does not prove delivery of that manifest. agy coverage is a run-level proxy because its provider session contents are unavailable. The command reports delivery defects while still exiting 0. See the [provider verification contract](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/docs/agent_providers.md#verifying-instruction-delivery).

Two qualifications matter:

- Muse declaration-recovery warm p95 was **290.7 ms**, from five recorded manifests, above the suggested 250 ms budget. Its ordinary p95 was comfortably below budget, and the controlled warm-cache test passed. Establish a representative recovery baseline or explicitly accept this small-sample result; do not describe every purpose as meeting budget.
- Coverage rows reuse all of a provider's root sessions as the denominator for each purpose. Therefore Muse's ordinary 12/12 alongside recovery 5/12 and repair 1/12 does **not** mean six ordinary sessions lack manifests. The [coverage implementation](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/coverage_summary.py) makes that aggregation explicit.

### The E1 completion readout remains unsettled

I examined completion metadata, without reading conversation text, for the newest bounded Grok runs in that seven-day window. Excluding `research.*`, there were 27 finished runs: 18 `completed`, six `monitored`, and three `gated`.

Among the 18 `completed` runs, eight had `final_submission_host.json`. Five had `final_context.json` with `submission_required: true`, no accepted-submission file, and `finalizer_status.phase: planned` with the commit instance at attempt zero. Four lacked a final context; one had a context saying no submission was required and no accepted file.

The five cases needing explanation were:

| Agent | Run started, UTC |
| --- | --- |
| `bob-cli-7c.1--plan` | 2026-10-13 13:55:24 |
| `bob-cli-7c.2--code` | 2026-10-13 14:49:25 |
| `bob-cli-7c.2--1` | 2026-10-13 15:41:11 |
| `bob-cli-7c.3--code` | 2026-10-13 16:23:09 |
| `bob-cli-7c.3--1` | 2026-10-13 17:37:57 |

This is **an entry-gate concern, not a calculated compliance rate or a proven root cause**. Final-context state can change, evidence can move, host finalization has its own lifecycle, and the sample is concentrated in one project's work. Resolve those possibilities on the owning host before interpreting the cases as provider noncompliance. Conversely, marking runs completed is insufficient evidence that required declarations were accepted. The proposal's historical 60%/26% rates were not independently reproduced in this investigation.

E1's live acceptance notes provide good mechanical guard evidence, and today's sample has zero observed helper acceptances. Together those support the helper fix, but they do not replace a dated watch readout for Grok's non-research completion behavior.

The E1/E2 flags were retired by approved epic `sase-1jc`, phase `.10`, on October 10. In particular, the `sase-1h4` closure explicitly says shadow recording remains shadow-only. Flag removal therefore does not establish that E3 already ran, or independently demonstrate the original seven-day shadow watch criterion.

## Changes needed in the E3 plan

### 1. Update the scoreboard for the new delivery channels

The current headline Claude, Codex, and Muse observers calculate contract, home, and project presence from **native file sources**. Their explicit-channel readers exist for per-section comparison, but the headline counters still reflect the legacy path. After moving Codex's root contract to a developer message, for example, these counters would report zero native contracts even when explicit delivery succeeded.

E3 must update observation and doctor criteria alongside each channel switch. Identify home/project contributions by manifest sections, rather than requiring today's legacy file H1s to survive a merged document. Compare root and helper bundles against their own actor facts. Keep the distinction between native full projections and a deliberately retained neutral/helper-safe file.

Evidence: the [Codex observer](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/codex.py), [Claude observer](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/claude.py), and [Muse observer](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/muse.py).

### 2. Strengthen exactly-once evidence and session identity

Today's per-section comparison counts source strings that **contain** a section body. Two copies inside one source string still produce one hit. It also skips document scaffolding and headings. This is useful E2 parity evidence, but cannot alone prove E3's bundle-exactly-once requirement.

Record a stable invocation/bundle identity, actual delivery slots, execution-provider identity, and explicit session associations. Count repeated bundle/section occurrences within each source; test duplicate prefixes and interrupt reconstruction. A retry, fallback provider, resumed session, and native helper must have distinct, accurately linked records. Use the schema's existing `inherits_root` spelling, or extend the Rust wire deliberately if a separate continuation status is needed; the proposal's prose `inherited` is not currently an accepted status.

The existing matcher uses provider and render time; it does not use a populated manifest session-id association. Partial provider records also need honest unavailable states. A completed example checked here, `sase-1kh.land--code`, had native contract 2× and manifest coverage 1/1, but per-section rows were unavailable because the bounded transcript was marked partial. Zero counts in those unavailable rows cannot be treated as proof of omission.

Evidence: [section comparison](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/coverage_diff.py), [manifest matching](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/instructions/coverage_records.py), and [Rust wire](https://github.com/sase-org/sase-core/blob/d30e1337a848f0bef8978153de3731badee00d46/crates/sase_core/src/instruction_manifest/wire.rs).

### 3. Replace the historical re-render criterion

The proposal says re-rendering a finished agent reproduces its manifest hash. The current `render -a AGENT` takes that agent's facts but reads **today's sources from the current checkout and home**. It does not restore the original memory, compiler, configuration, plugins, or provider directive. From another project's checkout it can even combine historical facts with the wrong current project sources.

Use two distinct acceptance checks: retrieve archived bytes and validate their recorded SHA-256; and verify deterministic compilation for identical inputs. Historical recompilation requires retained input versions and the matching compiler/configuration. That is additional scope, not a promise the current preview command satisfies. For inspection, the archived bundle already solves the practical problem.

Evidence: [render handler](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/main/instructions_handler.py) and [preview semantics](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/docs/instruction_bundles.md#previewing-bundles).

### 4. Re-probe current provider discovery and preserve owned guides

Installed versions were Codex **0.162.1**, Claude Code **2.1.296**, Grok **1.0.52**, and Muse **1.4.7-R6101.1**.

An offline `codex debug prompt-input` probe used a disposable `CODEX_HOME` containing a marker in its private `AGENTS.md`, plus a marker in `developer_instructions`. With `project_doc_max_bytes=32768`, both markers and the repository instructions appeared. With zero, both markers remained and the project instructions disappeared. Both commands exited 0 and made no model request. This confirms that the proposed split is viable on the installed Codex version. It does not test native children, inherited override symlinks, or a complete production bundle. OpenAI's [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) documents both controls; its [instruction discovery guide](https://learn.chatgpt.com/docs/agent-configuration/agents-md) describes the default 32 KiB project cap.

Ensure the Codex neutral file contains all intended neutral project/home sections, including reference triggers and web descriptors. Write private regular files instead of following inherited `AGENTS.md`/`AGENTS.override.md` symlinks, and ensure an inherited override cannot displace the new neutral file. Protect the real global file and apply project suppression only to managed invocations. Clarify how nested hand-written guides stay accessible when automatic project discovery is suppressed.

Current Claude documentation adds a discovery surface missing from the old plan: recent versions can load `AGENTS.md` directly. Exclusion patterns apply to those files too. Enumerate exact SASE-owned projection paths and test both filename families, symlinks, imports, and delayed nested loads, while keeping repo-owned guides available. The same documentation supports `autoMemoryEnabled: false` and `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. These require deployed-version canaries; reading documentation is not a delivery probe. [Claude memory and exclusion documentation](https://code.claude.com/docs/en/memory).

The [ownership inventory](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/docs/instruction_inventory.md) labels the nested sase `AGENTS.md` files as hand-written and their shims as projections. Blanket removal or exclusion would lose meaningful TUI/tool/tape guidance.

### 5. Make fallback and rollback atomic

There is no implemented `llm_instruction_delivery` hook or `DeliveryPlan` in the inspected source. E3 still needs those slots and adapter integration. The old `instruction_shadow_render`, `grok_rules_delivery`, and `claude_helper_channel` switches no longer exist. Introduce the proposed new per-provider sunset switches against today's unconditional E1/E2 behavior; switching off must preserve the Grok stopgap and Claude helper guard.

If rendering or transport validation fails, restore **both** legacy delivery and legacy discovery for that invocation and record/notify the reason. Suppressing native files and then failing to deliver a bundle must never leave an empty instruction context. Preserve non-managed and unknown-plugin-provider behavior and cover invocations without artifact directories. Keep full files until E4 and retain rollback throughout the post-E3 soak.

### 6. Keep the remaining spikes and policy decisions explicit

Before adapter phases depend on the delivery plan, collect current-version evidence for Muse without `--trust-workspace`, exact Claude exclusions and helper delivery, Grok rules visibility and memory-v2 control, and Codex helper inheritance. Muse can remain declared legacy if its trust spike fails; agy/Qwen/OpenCode remain declared legacy as proposed.

Decide home-layer sharing and provider foreign-memory policy in the E3 decision record. Today's home contribution is only 246 bytes in this render, largely reference descriptions, but that does not authorize unrestricted expansion or imply that future home content is equally small. Render on the dispatch target and validate protocol compatibility. I made no remote calls or paid provider canaries in this research.

Shared delivery-policy/wire behavior belongs in sase-core with bindings and a pin move if extended. Adapter argv and Python composition can use the existing boundary. Keep E6's shared ledger projection in Rust when it is implemented.

## How to inspect a completed agent's instructions today

Three records answer different questions:

| Question | Available surface | Historical meaning |
| --- | --- | --- |
| What did its root `AGENTS.md` look like at launch? | Agents tab → `SASE CONTEXT` → `MEMORY` → launch row | Captured project root file. |
| What bundle did E2 compile for this provider invocation? | Stored `instructions/NN-provider.md` and matching JSON | Complete intended shadow bundle, including composed package/home/project sections. |
| What did the provider actually load? | `sase instructions verify -a NAME` and provider-native evidence | Observed legacy delivery, subject to evidence availability. |
| What would that agent receive from today's sources? | `sase instructions render -a NAME` | Fresh preview; historical facts with current sources. |

### From the Agents tab

Select the completed agent, expand its context header as needed, and find the launch `AGENTS.md` row in the `MEMORY` lane. Press **`v`**, then select the row's displayed hint. The pager opens the pinned committed version, or a stored read-only snapshot when the bytes were never committed. Version chips indicate `≡ now`, a historical `vK`, uncommitted launch bytes, or unavailable evidence. Older runs can have no launch row.

This row resolves the workspace-root `AGENTS.md` from launch evidence; a recorded launch HEAD is a fallback. It does not show the combined home/project bundle, provider directive, helper bundle, or proof of provider loading. Home instruction snapshots may also be captured in run metadata, but the displayed launch row selects the root project file. Evidence: [launch capture](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/axe/launch_evidence.py), [row resolution](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/src/sase/ace/tui/widgets/prompt_panel/_agent_memory_versions.py), and [user-facing history documentation](https://github.com/sase-org/sase/blob/8959b0e6fc6b048ee60f79731e676db994cb2ce7/docs/memory_history.md#in-the-tui).

### Retrieve the exact recorded bundle

Use the agent's actual run name, including any suffix. `sase agent list -a` lists completed agents; `sase agent show NAME` prints its **Artifacts dir**. A bead id is not always a locally discoverable agent name. Inspection commands scan bounded local indexes, so old, remote, or unavailable runs may require their recorded artifact location or the owning host.

Then use that printed directory:

```bash
sase agent show NAME

# Copy the actual Artifacts dir from the output:
run_dir='/actual/artifacts/directory'

jq '.instructions' "$run_dir/agent_meta.json"
manifest_rel=$(jq -r '.instructions.latest.manifest // empty' \
  "$run_dir/agent_meta.json")
manifest_path="$run_dir/$manifest_rel"

# Inspect facts, purpose, provider, sections, offsets, and recorded digests:
sase pager "$manifest_path"

# The historical Markdown sibling contains the intended bundle bytes:
bundle_path="${manifest_path%.json}.md"
sase pager "$bundle_path"
sha256sum "$bundle_path"
jq -r '.bundle.sha256, .bundle.store_path, .delivery.status' "$manifest_path"
```

If `manifest_rel` is empty, there is no latest manifest pointer; inspect that run's recorded files and error records rather than constructing an empty path. If the Markdown sibling is missing, check the manifest's `bundle.store_path` for the content-addressed copy and validate its hash. A digest cannot reconstruct missing bytes.

**Inspect every invocation when needed.** `instructions.latest` points to the latest manifest, which could describe declaration recovery or conflict repair. The initial invocation and provider fallback may have different sequence/provider names. Inspect all recorded pairs and their `purpose`, `attempt`, `invocation_seq`, and execution provider. The sequence currently begins at `00`; do not hard-code `01`.

A completed example checked here, `sase-1kh.land--code`, points to `instructions/00-codex.json`, with a matching Markdown sibling and bundle SHA-256 `49526658010c050fd544e4679f4c7405b8be85597724c4d0446d8832b744387e`. Today's same-project preview reproduced that hash because the relevant inputs matched. That one match does not make `render -a` a historical replay command.

The current preview was **20,038 bytes**, approximately **5,013 tokens**, with 27 included sections. Layer budgets were package 5,655 bytes, project 13,479, home 246, and frame 658. Those sizes fit comfortably below the proposed 32 KiB threshold for this input set; retain an explicit oversize check for larger projects.

### Check observed delivery separately

```bash
sase instructions verify -a NAME
sase instructions verify -a NAME -j
sase instructions render -a NAME -s
```

In JSON, per-session comparison is under `observations[].section_diff`; its `manifest` field also locates the historical manifest. Inspect `partial` and `section_diff.unavailable` before interpreting section counts. Extend `--since` for older runs, subject to the bounded index limit. Neither CLI success nor manifest coverage alone proves that each intended section was delivered.

There is currently no dedicated instruction-bundle deck and no `sase instructions show` subcommand. The proposal assigns those to E6, together with Manifest/Ledger/Bundle cards and `Seen by`. You can inspect complete stored shadow bundles through paths today; the convenient integrated bundle view remains future work.

## Practical launch conditions

1. Attach and review a dated E1 watch readout, explaining the five Grok metadata cases and separating accepted root declarations, recovery, legitimate handoffs, and unavailable evidence.
2. Refresh E3's plan with explicit-channel scoreboard updates, exact-occurrence conformance, archived-byte inspection, current Claude discovery, new rollback switches, and no-artifact-directory behavior.
3. Keep E3.1 as a dependency gate for the adapter phases; record every capability probe with CLI version and an honest legacy/unavailable outcome.
4. At landing, require provider-native evidence for each switched root/helper channel, both rollback states, atomic failure fallback, protected repo-owned guides/global files, and target-host dispatch behavior.
5. Preserve E4/E6 separation and the post-E3 seven-day soak. Retain sunset switches until their removal decision is supported by operational evidence.

## Verification performed

```bash
.venv/bin/python -m pytest -q \
  tests/instructions/test_compiler.py \
  tests/instructions/test_compiler_cache.py \
  tests/instructions/test_invoke_boundary.py \
  tests/instructions/test_render_parity.py \
  tests/instructions/test_scoreboard_sessions.py \
  tests/core/test_instruction_manifest.py
# 64 passed, 1 slow test deselected, 81.20 seconds

.venv/bin/python -m pytest -q -m slow \
  tests/instructions/test_compiler_cache.py::test_warm_render_latency_budget
# 1 passed, 9.43 seconds
```

The selected tests cover actor overlays, provider-only differences, byte determinism, cache inputs and corruption, fixture and current-tree parity, invocation routes/fallback/fail-open behavior, manifest validation, and coverage matching. No full CI run, source implementation, fleet deployment, auto-memory harvesting, or paid provider probe was performed. The remaining work above is evidence needed for the proposed migration, rather than a claim that the new delivery path already exists.
