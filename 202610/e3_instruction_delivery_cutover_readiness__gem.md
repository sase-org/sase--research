# E3 Instruction Delivery Cutover Readiness and Instruction Bundle Inspection

> **Research Report**  
> **Researcher:** `research.13.gem`  
> **Date:** 2026-10-13  
> **Topic:** Evaluation of readiness for launching Epic E3 (*Explicit Delivery Cutover*) from the memory-built instruction migration roadmap, and instructions for inspecting an agent's instruction bundle contents on the SASE "Agents" tab.

---

## 1. Executive Summary & Verdict

### 1.1 Readiness Verdict: Ready for Planning & Launch
**The system is technically and empirically ready for Epic E3 (Explicit Delivery Cutover).**

All structural prerequisites and entry gates established in the consolidated roadmap ([`memory_built_instruction_migration_epics.md`](file:///home/bryan/.local/state/sase/workspaces/sase-org/sase/sase_17/sase/repos/research/202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md)) are fully satisfied:
1. **Epic E1 (Instruction Scoreboard and Stopgaps, bead `sase-1gu`)** landed on 2026-10-06 and has soaked in production for **7 full days** (well exceeding the required 3-day minimum). Its readout is verified: Grok receives the SASE contract 1×, project instructions, and the single-turn directive via `--rules`; Claude native helpers have logged **0 accepted declarations** under the PreToolUse guard and subagent system prompt template.
2. **Epic E2 (Instruction Bundles in Shadow Mode, bead `sase-1h3`)** landed on 2026-10-06. The `sase-core` manifest wire schema is pinned, the Python compiler is compiling 27 discrete memory sections, the invocation boundary wraps 100% of root provider invocations, and `sase instructions render -p` demonstrates clean 100% parity against legacy files with zero missing sections.
3. **Manifest Coverage & Performance**: Live verification via `sase instructions verify -c` confirms **100% manifest coverage** across all recent runs (47/47 manifests across Claude, Codex, Grok, Muse, and Antigravity) with zero errors and warm render latencies between 30 ms and 50 ms (far below the 250 ms p95 budget).
4. **Flag Cleanup Convergence**: Under Epic `sase-1jc` (2026-10-10), feature flags were audited and retired across the repo; shadow rendering and the Grok/Claude stopgaps are now unconditional.

### 1.2 Key Procedural Caveat
While the runtime and compiler are ready, **an approved plan file (`plan:202610/e3_explicit_delivery_cutover.md`) does not yet exist in `sase/repos/plans/202610/`**. In accordance with SASE rules, an epic plan must be authored, reviewed, approved, and created as an epic bead (with preassigned phase beads) before implementation agents are launched.

---

## 2. Evaluation of Readiness for Epic E3

### 2.1 E3 Goals and Scope
From `memory_built_instruction_migration_epics.md`, the objective of Epic E3 is:
> *Every major provider gets the bundle **exactly once** through its explicit channel, SASE-owned full native files are suppressed, and Claude helpers get the helper bundle. This completes your stated goal for SASE agents.*

E3 transitions SASE from **shadow rendering** (where bundles and manifests are generated and recorded into run artifacts without being sent to LLMs) to **active explicit delivery** (where adapters pass the rendered bundle directly to each LLM, suppressing native repository `AGENTS.md` and `CLAUDE.md` files).

### 2.2 Audit of E3 Entry Conditions

| Entry Criterion | Required Standard | Current System State | Status |
| :--- | :--- | :--- | :--- |
| **E1 Soak Period** | $\ge 3$ days of real runs | Landed 2026-10-06; **7 days of production runs** observed as of 2026-10-13 | **PASS** |
| **E1 Grok Readout** | Contract 1×, project ✓, directive ✓ | `sase instructions verify` shows Grok at `1× / ✗ / ✓ / ✓ / 0` (contract 1×, home ✗, project ✓, directive ✓, native-full 0) | **PASS** |
| **E1 Claude Helper Readout** | 0 accepted helper declarations | `sase instructions verify` shows 0 attempts, 0 accepted; `doctor` check `instructions.helpers` reports OK | **PASS** |
| **E2 Parity Clean** | `sase instructions render -p` passes | Exits code 0 with 100% section parity across frame, package, project, and home layers | **PASS** |
| **Manifest Coverage** | 100% across all providers | `sase instructions verify -c` reports 47/47 covered runs with 0 errors | **PASS** |
| **Warm Render Latency** | Warm p95 $< 250$ ms | Warm p50/p95 observed between 31 ms and 55 ms | **PASS** |
| **Architecture Invariant** | No bypass of invocation hook | Architecture tests enforce all three `provider.invoke` sites route through `invoke_with_instructions` | **PASS** |

### 2.3 Doctor Diagnostics
Running deep diagnostics on the instructions check group (`sase doctor -D -C instructions`) reports:
```text
Instructions
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Status ┃ Check                 ┃ Summary                         ┃ Next Step ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ WARN   │ instructions.delivery │ delivery drift: claude          │ -         │
│        │                       │ (contract 2×, native-full 2×);  │           │
│        │                       │ codex (contract 2×, native-full │           │
│        │                       │ 2×)                             │           │
│ OK     │ instructions.helpers  │ no accepted helper declarations │ -         │
└────────┴───────────────────────┴─────────────────────────────────┴───────────┘
```
The `WARN` on `instructions.delivery` is the documented baseline drift (Claude and Codex loading both home and project files natively, resulting in a 2× contract duplication). Resolving this warning by replacing native file loading with explicit delivery is the exact functional objective of Epic E3.

### 2.4 E3 Implementation Phases & Pre-Launch Checklist

When authoring `plan:202610/e3_explicit_delivery_cutover.md`, the plan should incorporate the 6 phases defined in the consolidated report:

1. **Phase E3.1 (`spikes`)**:
   - Run lightweight probes (`xsmall` agents) to verify:
     - Can Muse run safely without `--trust-workspace`?
     - Does Grok record `--rules` text anywhere in session metadata?
     - Do exact-path `claudeMdExcludes` cover workspace, home, and nested files while sparing `sase/repos/**`?
     - Verify Codex `project_doc_max_bytes=0` in SASE-managed projects.
     - Live probe confirming Claude auto-memory disable switch (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` / `autoMemoryEnabled: false`).
2. **Phase E3.2 (`delivery-plan`)**:
   - Introduce the `llm_instruction_delivery` hook returning a `DeliveryPlan` declaring `root` and `subagent` slots (`explicit` | `inherits-native` | `inherits-root` | `none`).
   - Define per-provider `sunset` flags (`claude_explicit_delivery`, `codex_explicit_delivery`, etc.) allowing immediate rollback if an adapter misbehaves.
   - Fail-open fallback: On compilation/render failure, fall back to legacy native delivery for that invocation and emit an operator notification.
3. **Phase E3.3 (`claude`)**:
   - Deliver root bundle via `--append-system-prompt-file`.
   - Deliver helper bundle to Claude subagents, retaining the PreToolUse guard.
   - Suppress native files via exact-path `claudeMdExcludes`.
   - Disable auto-memory in SASE workspaces.
4. **Phase E3.4 (`codex-grok`)**:
   - Codex: Configure `$CODEX_HOME/AGENTS.md` to hold neutral core + home; pass root overlay via `developer_instructions`; set `project_doc_max_bytes=0`.
   - Grok: Pipe full root bundle into `--rules`.
5. **Phase E3.5 (`muse-agy`)**:
   - Muse: Prefix prompt delivery; drop `--trust-workspace` if spike confirmed; ensure interrupt reconstruction never nests duplicate bundles.
   - agy, Qwen, OpenCode: Declare as `inherits-native` (legacy) pending stub retirement in E4.
6. **Phase E3.6 (`conformance`)**:
   - Update `sase instructions verify` to assert each bundle ID appears exactly once per invocation and helper.
   - Record decision record *"Instructions Are Rendered Per Invocation And Delivered By Adapters"*.
   - File follow-up `memory` task bead to harvest foreign auto-memory notes.

---

## 3. How to Inspect a Completed Agent's Instruction Bundle

A user looking at a completed agent (for example, on the SASE TUI "Agents" tab) can inspect the exact instruction bundle contents through three complementary methods: directly from the run artifacts, via CLI inspection tooling, or within the TUI.

### 3.1 On the Filesystem: Stored Run Artifacts
Under the E2 architecture (`src/sase/llm_provider/_instruction_boundary.py`), every root provider invocation shadow-renders its memory bundle and saves it directly into the agent's run artifacts directory:

```text
~/.sase/projects/<project>/artifacts/ace-run/<YYYYMM>/<DD>/<timestamp>/
├── agent_meta.json
├── instructions/
│   ├── 00-<provider>.md    <-- The EXACT full Markdown bundle compiled for invocation 0
│   ├── 00-<provider>.json  <-- The instruction manifest JSON for invocation 0
│   ├── 01-<provider>.md    <-- Follow-up invocation (e.g. declaration recovery)
│   └── 01-<provider>.json
└── tool_calls.jsonl
```

#### What is inside `instructions/00-<provider>.md`?
This file is the literal Markdown text compiled from all active memory units at launch time for that specific agent turn:
- **Frame Layer**: Header and document metadata.
- **Package Layer**: Core SASE contracts, workspace rules, linked repository declarations, and the actor-specific final declaration contract.
- **Project Layer**: Project-level conventions, gotchas, decision records roster, glossary terms roster, and task types.
- **Home Layer**: User-specific configuration (if applicable).
- **Overlays**: Actor overlay (`sase_root` vs `native_helper` vs `interactive`).

#### What is inside `instructions/00-<provider>.json`?
This file contains the normalized **instruction manifest** schema defined in `sase-core`:
- `facts`: Actor (`sase_root`), purpose (`ordinary`), mode (`runtime`), provider, project, host, VCS.
- `bundle`: Total bytes, estimated token count, `sha256`, `common_digest` (content hash excluding provider-specific sections), and the ordered list of all 27 sections with their individual hashes.
- `delivery`: Invocation UUID, attempt number, agent name, agent type, model name, and timestamp.

#### `agent_meta.json` Integration
The root `agent_meta.json` file records an `instructions` summary:
```json
"instructions": {
  "schema_version": 1,
  "count": 1,
  "latest": {
    "seq": 0,
    "provider": "muse",
    "purpose": "ordinary",
    "sha256": "8e8a8d74cbf982f6283f41afa80e2d64e22246862d2e9d35f96a6f9d64cd25f1",
    "common_digest": "6b4280fc40a67a470899ee92c0b84e995d37a984f057a80c904d4963653acea6",
    "manifest": "instructions/00-muse.json"
  }
}
```

---

### 3.2 Via the CLI: `sase instructions render`

You can inspect the bundle of any completed agent using `sase instructions render -a <agent-name>`:

1. **View the Full Bundle Text**:
   ```bash
   sase instructions render -a <agent-name>
   ```
   *Behavior:* SASE resolves the agent's run record from `~/.sase/projects/...`, loads its recorded facts and latest manifest, and prints the full Markdown bundle to stdout. If the recorded bundle matches current memory, it outputs:
   ```text
   agent <agent-name>: bundle matches recorded <sha>
   ```
   If memory files have changed since that agent ran, it reports which specific section IDs differ.

2. **View the Section Breakdown Table**:
   ```bash
   sase instructions render -a <agent-name> -s
   ```
   *Behavior:* Prints a formatted terminal table showing all 27 constituent sections:
   - Section ID (e.g. `pkg.sase_contract`, `proj.core_memory`, `proj.web_glossary`)
   - Layer (`frame`, `package`, `project`, `home`)
   - Status (`included`, `superseded`, `overlay`)
   - Lifecycle (`neutral`, `root`, `helper`)
   - Size in bytes and estimated token counts
   - Source path

3. **View the Normalized Manifest JSON**:
   ```bash
   sase instructions render -a <agent-name> -j
   ```
   *Behavior:* Emits the full JSON manifest document.

4. **Verify Delivery Observability**:
   ```bash
   sase instructions verify -a <agent-name>
   ```
   *Behavior:* Displays the observed delivery report for that specific agent session from the provider's native logs.

---

### 3.3 On the SASE "Agents" Tab (TUI)

#### Current State (Post-E2)
On the "Agents" tab in the SASE TUI:
1. **Selecting the Agent**: Use `j` / `k` to highlight the completed agent.
2. **Accessing Artifacts via the Files Deck (`f`)**:
   - Press `f` to switch to the **FILES deck**.
   - The files list includes all generated artifacts under the agent's run directory.
   - Navigate to `instructions/00-<provider>.md` or `instructions/00-<provider>.json` and open/view it.
3. **Checking Provenance via the RECORD Deck (`r`)**:
   - Press `r` to switch to the **RECORD deck**.
   - The Provenance card displays the agent's run directory path and artifact locations.

#### Future Dedicated TUI Visibility (Epic E6)
Epic E6 (*TUI Instruction Visibility*) is specifically scoped in the migration roadmap to add first-class instruction views directly into the Agents tab:
- **Identity Header Chip**: A badge in the session header showing delivery status (quiet when OK, `‼` on delivery drift, `∅` if missing).
- **Dedicated MEMORY Deck (`p` then `y`)**: Press `p` to open the deck picker and `y` to select the MEMORY deck, which presents three cards:
  1. **Manifest Card**: Visual breakdown of layers, section IDs, facts, and digests.
  2. **Ledger Card**: Unified audit joining the manifest, observed loads, and memory trigger reads (`memory_reads.jsonl`).
  3. **Bundle Card**: Direct Textual viewer displaying the full rendered instruction bundle Markdown.
- **CLI Inspection**: `sase instructions show <agent-name>`.

---

## 4. Recommendations & Next Steps

1. **Proceed with Epic E3 Plan Authoring**:
   - All empirical prerequisites are met.
   - Author `plan:202610/e3_explicit_delivery_cutover.md` using the consolidated report's phase specifications and checklists.
2. **Ensure Per-Provider Sunset Flags**:
   - While Epic `sase-1jc` retired historical flags, E3 must introduce new per-provider `sunset` flags (default ON) to ensure safe, localized rollback capability without requiring code reverts.
3. **Keep agy on Legacy Delivery**:
   - As established in the roadmap, Antigravity (`agy`) does not support native file suppression or explicit system prompt appending via CLI arguments. Keep `agy` declared as `inherits-native` until E4, when it transitions to prefix delivery alongside the stub.
