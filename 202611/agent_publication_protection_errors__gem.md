# Root Cause Analysis: Agent Publication Errors and False-Positive Publication Protection

**Date:** 2026-11-02  
**Author:** researcher `research.5p.gem`  
**Status:** Complete  
**Scope:** Investigation of recurring `publication:agent_publication` check errors in `~/.sase/axe/error_digests/digest_20261102_125554.txt`, tracing origin agents, mechanism, and root cause.

---

## 1. Executive Summary & Root Cause Diagnosis

The recurring agent publication errors logged in `digest_20261102_125554.txt` (71 errors recorded between 12:01:08 and 12:55:42 EDT on 2026-11-02) are caused by a **false-positive credential scan in the core secret scanner**, compounded by a **zero-attempt parking loop in the publication job**.

### Key Findings

1. **Root Cause (The Scanner Bug):**
   In `crates/sase_core/src/note_attachment/scanner.rs` (line 178), the regular expression for OpenAI API keys is defined without word boundaries:
   ```rust
   fn openai_re() -> &'static Regex {
       static RE: OnceLock<Regex> = OnceLock::new();
       RE.get_or_init(|| Regex::new(r"sk-[A-Za-z0-9_-]{20,}").unwrap())
   }
   ```
   Because `openai_re` lacks a leading word boundary `\b`, and because hyphens `-` are included inside the character class `[A-Za-z0-9_-]`, **any English word ending in `sk` followed by a hyphen and a hyphenated identifier longer than 20 characters triggers a false-positive credential match for `openai-key`**. Specifically:
   - English words like `task-` and `disk-` end with `sk-`. The substring `sk-<rest-of-identifier>` matches `openai_re` whenever `<rest-of-identifier>` is $\ge 20$ characters.
   - `blocked-task-why-visual__mus-cf5c493312ed` matched `sk-why-visual__mus-cf5c493312ed` (30 chars).
   - `scripts/test-task-status-cycler-relation-successors.cjs` matched `sk-status-cycler-relation-successors` (34 chars).
   - `scripts/test-task-status-cycler-pomodoro-completion.cjs` matched `sk-status-cycler-pomodoro-completion` (34 chars).
   - Historically in `tailnet`: `disk-cleanup-2026-10-28-0ccbd4bd364a.md` matched `sk-cleanup-2026-10-28-0ccbd4bd364a` (34 chars).

2. **Triggering Agents in `gh_bobs-org__bob-cli`:**
   Three distinct SASE agents authored artifacts and prompts containing legitimate hyphenated phrases with `task-`:
   - **`bbugyi200.athena.research.5n.mus`** (2026-11-01 18:45 EDT): Swarm research report named `research:202611/blocked-task-why-visual__mus.md` (artifact file `blocked-task-why-visual__mus-cf5c493312ed.md`). Recorded in `output_variables.artifacts` inside `agent_meta.json`. When `gate_run_files()` scanned `meta.json`, it triggered `openai-key`. Because `meta` is a structural run kind, the entire run was withheld: `run withheld by publication protection`.
   - **`bbugyi200.athena.bob-cli-fs.8.1.3--2`** (2026-11-02 08:47 EDT): Monitored test run prompt contained `scripts/test-task-status-cycler-relation-successors.cjs`. Prompt scanning triggered `openai-key`, resulting in: `prompt archive withheld by publication protection`.
   - **`bbugyi200.athena.bob-cli-fx.2--2`** (2026-11-02 11:08 EDT): Monitored git status prompt contained `scripts/test-task-status-cycler-pomodoro-completion.cjs`. Triggered `openai-key` on both primary (`revision`) and linked repo (`linked`) publication requests, resulting in: `prompt archive withheld by publication protection` (2 entries).

3. **The Indefinite Error Loop (Architectural Bug):**
   - Under commit `c687d8b6eb` (*"park withheld publications without charging quarantine"*), items withheld by publication protection deliberately do **not** increment their retry counter (`attempts` stays `0`). They are parked to avoid discarding potentially valid work permanently.
   - However, in `src/sase/agents_sync/_commit_publication_drain.py`, withheld items append their reason to `result.item_errors`, causing `outcome.error` to be set to `"run withheld by publication protection; prompt archive withheld by publication protection; ..."`
   - In `src/sase/agents_sync/publication_job.py`, any non-null `outcome.error` is counted as an execution error (`summary.errors += 1`).
   - In `src/sase/scripts/sase_chop_agent_publication.py`, `tick.errors > 0` forces `result.status = "check_error"`.
   - Because the AXE scheduler runs `publication:agent_publication` every minute, and the 4 items in `gh_bobs-org__bob-cli` remain permanently in the active outbox with 0 attempts, AXE records a new `check_error` every 40–60 seconds, filling the error digests indefinitely.

4. **Transient Early Errors (Errors 1–5):**
   At the start of the digest (12:01 EDT), an agent `bob-cli-fs.2.1.land` had 2 outbox entries failing with `"could not restore deferred prompt archive ... missing local source"`. Unlike publication-protected items, missing-source errors **do** charge attempts. At 12:01:17 EDT, they reached attempt 3 and were quarantined (`quarantined: true`), leaving exclusively the 4 publication-protection errors for the remaining 66 digest entries.

---

## 2. Background: SASE Publication Architecture

To understand how these errors manifest, it is helpful to trace the lifecycle of agent publication.

```mermaid
flowchart TD
    A["Agent Completes Turn (/sase_final)"] --> B["Enqueue to agents-publication-outbox.json"]
    B --> C["AXE Scheduler: agent_publication chop (every 1 min)"]
    C --> D["_drain_project(project_key)"]
    D --> E["Scan files for secrets (sase_core::scanner)"]
    E -->|Clean| F["Publish to Sidecar Repo (gh-pages / repo-agents)"]
    E -->|Hit (openai-key)| G["Mark Blocked in agents-publication-protection.json"]
    G --> H["Withhold Run / Prompt Archive"]
    H --> I["Park Item (attempts = 0, no quarantine charge)"]
    I --> J["_commit_publication_drain populates item_errors"]
    J --> K["publication_job increments summary.errors"]
    K --> L["Chop Result status = check_error"]
    L --> M["AXE Error Digest: Error X/71"]
    M -->|Next Minute| C
```

### Components

1. **Outbox (`agents-publication-outbox.json`):**
   Located at `~/.sase/projects/<project_key>/agents-publication-outbox.json`. When an agent turn finishes with git stitches or artifact links, publication requests are enqueued with `scope: "revision"` (for the primary workspace) or `scope: "linked"` (for linked/sidecar repositories).
   Items remain active as long as `quarantined == false` and `terminal == false`.

2. **Scanner & Protection Ledger (`agents-publication-protection.json`):**
   Before bytes are written to published sidecars (e.g. `bobs-org/bob-cli--agents`), `gate_run_files()` and `scan_archive_text_bytes()` run `scan_publication_bytes()`, calling into the Rust core binding `publication_scan_disposition()`.
   If the Rust scanner finds a credential pattern, it produces `status: "blocked"` with reason `scanner_hit`. The verdict is recorded in `agents-publication-protection.json` so the exact SHA256 is never retried automatically.

3. **Structural Gating (`_STRUCTURAL_RUN_KINDS`):**
   In `src/sase/agents_sync/_publication_snapshot_gating.py`:
   ```python
   _STRUCTURAL_RUN_KINDS = ("meta", "state", "commits")
   ```
   If any structural kind is blocked, the entire run is dropped from the snapshot (`record=None`, `withheld_reason="blocked"`), which raises `HoodWithheldError`, returning `"run withheld by publication protection"`.

4. **Quarantine Exemption:**
   In `src/sase/agents_sync/prompt_archive/protection.py`:
   ```python
   def should_charge_prompt_protection_failure(error: str) -> bool:
       return error not in {PROMPT_PROTECTION_BLOCKED, PROMPT_PROTECTION_UNVERIFIED}
   ```
   And similarly for hood/run withholding: items withheld by protection policy are considered parked waiting for manual sanitization or a changed digest. They do not increment `attempts`.

5. **AXE Publication Chop (`publication:agent_publication`):**
   `src/sase/scripts/sase_chop_agent_publication.py` invokes `run_publication_job()` on all enabled projects. If `summary.errors > 0`, the job returns `status: "check_error"`.

---

## 3. Dissecting the Error Digest (`digest_20261102_125554.txt`)

All 71 errors in `digest_20261102_125554.txt` originated from a single job:
- **Routine:** `publication`
- **Job:** `agent_publication`
- **Exit Code:** `0` (the Python process exits clean, but returns structured status `check_error`)
- **Period:** 2026-11-02 12:01:08 to 2026-11-02 12:55:42 EDT (~54 minutes, ~1 run per 45 seconds).

### Subprocess Output Analysis

In runs 6 through 71, the output is identical on every tick:
```text
[agent_publication] gh_bobs-org__bob-cli: run withheld by publication protection; prompt archive withheld by publication protection; prompt archive withheld by publication protection; prompt archive withheld by publication protection
agent_publication: projects=4 hood_drained=0 link_drained=0 referenced_by_drained=0 active_remaining=14 lock_busy=0 deferred_projects=0 errors=1

Structured job result: check_error · agent_publication: projects=4 hood_drained=0 link_drained=0 referenced_by_drained=0 active_remaining=14 lock_busy=0 deferred_projects=0 errors=1 · proposals=0
```

Notice the four semicolon-separated clauses:
1. `run withheld by publication protection` (1 item)
2. `prompt archive withheld by publication protection` (3 items)

In runs 1 through 5, two additional errors appeared:
```text
could not restore deferred prompt archive for bbugyi200.athena.bob-cli-fs.2.1.land@fdc34de9bf82: prompt archive is unresolved and a missing local source does not prove there was no prompt obligation;
could not restore deferred prompt archive for bbugyi200.athena.bob-cli-fs.2.1.land@07e115192e51: prompt archive is unresolved and a missing local source does not prove there was no prompt obligation
```
These two items belonged to agent `bob-cli-fs.2.1.land`. At 12:01:17 EDT, they reached `attempts: 3` and were quarantined into `quarantined: true`. Once quarantined, they dropped out of `active_agent_publications()`.

This left **exactly 4 items** actively blocking `gh_bobs-org__bob-cli`.

---

## 4. Deep Forensic Analysis of the 4 Withheld Requests

Examining `/home/bryan/.sase/projects/gh_bobs-org__bob-cli/agents-publication-outbox.json` reveals the 4 active items with `last_error`:

| # | Outbox Item ID | Global Agent | Scope | Last Error | Source Artifact Path / Context |
|---|----------------|--------------|-------|------------|--------------------------------|
| 1 | `bd823edf96ce...` | `bbugyi200.athena.research.5n.mus` | `linked` | `run withheld by publication protection` | `.../blocked-task-why-visual__mus-cf5c493312ed.md` in `agent_meta.json` |
| 2 | `3758ed6e0256...` | `bbugyi200.athena.bob-cli-fs.8.1.3` | `linked` | `prompt archive withheld by publication protection` | `scripts/test-task-status-cycler-relation-successors.cjs` in prompt |
| 3 | `aeb2f741da80...` | `bbugyi200.athena.bob-cli-fx.2` | `revision` | `prompt archive withheld by publication protection` | `scripts/test-task-status-cycler-pomodoro-completion.cjs` in prompt |
| 4 | `6c325d6c4a30...` | `bbugyi200.athena.bob-cli-fx.2` | `linked` | `prompt archive withheld by publication protection` | `scripts/test-task-status-cycler-pomodoro-completion.cjs` in prompt |

### Item 1: `research.5n.mus` (Run Withheld)

- **Agent:** `research.5n.mus`
- **Booted / Stopped:** 2026-11-01 18:40:45 to 18:45:27 EST (23:40 to 23:45 UTC)
- **Model:** `muse-spark-1.3-contributor`
- **Task:** 5-researcher swarm investigating task blocked states and styling in Obsidian.
- **The Trigger:**
  `research.5n.mus` saved its research report to:
  `research:202611/blocked-task-why-visual__mus.md`
  The host artifact registry materialized this file at:
  `/home/bryan/.sase/artifacts/agents/gh_bobs-org__bob-cli/20261101183900/blocked-task-why-visual__mus-cf5c493312ed.md`
  This path was stored in `agent_meta.json` under `output_variables.artifacts[0].path` (line 369).
- **The Hit:**
  When `gate_run_files` evaluated `meta.json`:
  ```json
  "path": "/home/bryan/.sase/artifacts/agents/gh_bobs-org__bob-cli/20261101183900/blocked-task-why-visual__mus-cf5c493312ed.md"
  ```
  The substring `sk-why-visual__mus-cf5c493312ed` is 30 characters and starts with `sk-`.
  The regex `sk-[A-Za-z0-9_-]{20,}` matched it as `openai-key`.
  Because `meta.json` is a structural run file, the entire run was withheld.

### Item 2: `bob-cli-fs.8.1.3` (Prompt Archive Withheld)

- **Agent:** `bob-cli-fs.8.1.3--2`
- **Booted / Stopped:** 2026-11-02 08:42:02 to 08:47:24 EST (13:42 to 13:47 UTC)
- **Model:** `gpt-6-luna`
- **Task:** Implementation phase bead for relation successors.
- **The Trigger:**
  The agent prompt contained the monitored command result:
  ```text
  npm run build && node --test scripts/test-task-status-cycler-relation-successors.cjs scripts/test-task-status-cycler-successor-wiring.cjs
  ```
- **The Hit:**
  The file name `scripts/test-task-status-cycler-relation-successors.cjs` contains:
  `test-ta` + `sk-status-cycler-relation-successors`.
  The suffix `sk-status-cycler-relation-successors` is 34 characters and matches `openai_re`.
  The prompt document was flagged as containing `openai-key` on line 11.

### Items 3 & 4: `bob-cli-fx.2` (Prompt Archives Withheld)

- **Agent:** `bob-cli-fx.2--2`
- **Booted / Stopped:** 2026-11-02 11:02:19 to 11:08:16 EST (16:02 to 16:08 UTC)
- **Model:** `muse-spark-1.3-contributor`
- **Task:** Implementation phase bead for task status cycler pomodoro features.
- **The Trigger:**
  The prompt recorded git status output containing:
  ```text
  modified:   scripts/test-task-status-cycler-pomodoro-completion.cjs
  ```
- **The Hit:**
  `test-ta` + `sk-status-cycler-pomodoro-completion`.
  The suffix `sk-status-cycler-pomodoro-completion` is 34 characters and matches `openai_re`.
  Because this agent touched both the primary repo (`bob-cli`) and linked repo (`bob-plugins`), two outbox items were created (`revision` and `linked`). Both included this prompt archive; both were blocked on line 141.

---

## 5. Architectural Provenance: SASE Agents That Introduced the Code

Tracing the commits that created this subsystem:

### 1. Introduction of the Flawed Regex
- **Commit:** `7806f587b0971816fe2623db835dde4582925063` (repo: `sase-core`)
- **Date:** 2026-09-30 08:51:54 EDT
- **SASE Bead:** `sase-1d5.1`
- **SASE Agent:** `bbugyi200.athena.sase-1d5.1`
- **Subject:** `feat(attachments): core attachment audience policy and scanner`
- **What it did:** Introduced `crates/sase_core/src/note_attachment/scanner.rs`. Defined `openai_re` as `r"sk-[A-Za-z0-9_-]{20,}"` without word boundaries or character restrictions.

### 2. Introduction of Publication Protection Policy
- **Commit:** `416db28904d080f5fc1ed884dfc256a4d0427fa6` (repo: `sase-core`)
- **Commit:** `f4591e9106830fb5e558d71f506b4a2d9fe9791b` (repo: `sase`)
- **Date:** 2026-10-26 17:06:51 EDT & 17:10:05 EDT
- **SASE Bead:** `sase-1oh.5.1.1`
- **SASE Agent:** `bbugyi200.athena.sase-1oh.5.1.1` (Model: `codex/gpt-6-luna`)
- **Subject:** `feat(core): add publication protection policy` / `feat(agents-sync): add publication protection state`
- **What it did:** Connected the Rust attachment scanner to publication bytes scanning via `publication_scan_disposition()`. Added `agents-publication-protection.json` ledger.

### 3. Introduction of Gated Transcripts & Run Structural Checks
- **Commit:** `67edb9677d23a2cdc93b71d944c551336f6416e3` (repo: `sase`)
- **Date:** 2026-10-26 20:17:09 EDT
- **SASE Bead:** `sase-1oh.5.1.2`
- **SASE Agent:** `bbugyi200.athena.sase-1oh.5.1.2` (Model: `muse/muse-spark-1.3-contributor`)
- **Subject:** `feat(agents-sync): withhold unsafe transcript bytes without breaking clean publication`
- **What it did:** Added `gate_run_files()` and `_STRUCTURAL_RUN_KINDS = ("meta", "state", "commits")`. Made scanner hits on `meta.json` withhold the entire run.

### 4. Introduction of Prompt Archive Protection
- **Commit:** `0f76e05de4dfcef4655a2eae0f9ca74e44f68211` (repo: `sase`)
- **Date:** 2026-10-27 00:54:31 EDT
- **SASE Bead:** `sase-1oh.5.1.3`
- **SASE Agent:** `bbugyi200.athena.sase-1oh.5.1.3` (Model: `grok/grok-4.6`)
- **Subject:** `feat(agents-sync): withhold unsafe prompt-archive text without breaking clean publication`
- **What it did:** Added scanning of prompt documents before staging, unstaging blocked items with `PROMPT_PROTECTION_BLOCKED`.

### 5. Introduction of the Zero-Attempt Parking Loop
- **Commit:** `c687d8b6ebba66fc41a3ba600ba789af9cfcdc93` (repo: `sase`)
- **Date:** 2026-10-27 07:07:10 EDT
- **SASE Plan:** `202610/agents_publication_withheld_gaps_closeout.md`
- **SASE Agent:** `bbugyi200.athena.sase-1oh.5.1.land--3--code` (Model: `grok/grok-4.6`)
- **Subject:** `fix(agents-sync): park withheld publications without charging quarantine`
- **What it did:** Configured withheld publications to park without charging attempts, but did not update the drainage caller to treat parked items as a non-error.

### 6. Introduction of the Recurring AXE Background Publication Job
- **Commit:** `4356cffaa1678646cab8a2d9c40375a90186a5fa` (repo: `sase`)
- **Date:** 2026-10-30 00:26:51 EDT
- **SASE Bead:** `sase-1pt.6`
- **SASE Agent:** `bbugyi200.athena.sase-1pt.6` (Model: `codex/gpt-6-luna`)
- **Subject:** `feat(agents-sync): add background publication job`
- **What it did:** Added `sase_chop_agent_publication.py` and scheduled `publication:agent_publication` via AXE to drain requests continuously. When `_drain_project` returns `outcome.error`, it marks `errors=1` and `check_error`.

---

## 6. Chronological Timeline of Events

| Timestamp (EDT) | Context / Entity | Event |
|---|---|---|
| **2026-09-30 08:51** | Agent `sase-1d5.1` (sase-core) | Authored `scanner.rs` with `openai_re` regex lacking word boundary (`r"sk-[A-Za-z0-9_-]{20,}"`). |
| **2026-10-26 17:10** | Agent `sase-1oh.5.1.1` (sase & core) | Integrated secret scanner into publication protection and ledger. |
| **2026-10-26 20:17** | Agent `sase-1oh.5.1.2` (sase) | Added `gate_run_files()`; structural run files (`meta.json`) withhold entire run on scanner hit. |
| **2026-10-27 00:54** | Agent `sase-1oh.5.1.3` (sase) | Added prompt-archive protection; prompt text scanned before staging. |
| **2026-10-27 07:07** | Agent `sase-1oh.5.1.land--3--code` | Exempted withheld items from retry/quarantine charges (`attempts` remains 0). |
| **2026-10-28 07:41** | Agent `14x--code` (tailnet) | Created `disk-cleanup-2026-10-28-0ccbd4bd364a.md`. First recorded false-positive trigger on `sk-cleanup-2026-10-28-...`. |
| **2026-10-30 00:26** | Agent `sase-1pt.6` (sase) | Added periodic background publication job `agent_publication` to AXE lumberjack. |
| **2026-11-01 18:45** | Agent `research.5n.mus` (bob-cli) | Completed research report `blocked-task-why-visual__mus.md`. Artifact path matched `sk-why-visual...`. Run withheld (Item #1). |
| **2026-11-02 08:47** | Agent `bob-cli-fs.8.1.3--2` (bob-cli) | Prompt recorded `scripts/test-task-status-cycler-relation-successors.cjs`. Matched `sk-status-cycler...`. Prompt withheld (Item #2). |
| **2026-11-02 11:08** | Agent `bob-cli-fx.2--2` (bob-cli) | Prompt recorded `scripts/test-task-status-cycler-pomodoro-completion.cjs`. Matched `sk-status-cycler...`. 2 outbox items withheld (Items #3 & #4). |
| **2026-11-02 11:58** | Agent `bob-cli-fs.2.1.land` (bob-cli) | Enqueued 2 requests with missing local prompt archive sources. |
| **2026-11-02 12:01:08** | AXE Chop `20261102T120040_451045` | **Error 1/71 in digest.** Failed on 4 withheld items + 2 missing source items. |
| **2026-11-02 12:01:17** | Outbox Quarantine | `bob-cli-fs.2.1.land` reached attempt 3 and was quarantined (`quarantined: true`). |
| **2026-11-02 12:01:50** | AXE Chop `20261102T120123_798098` | **Error 2/71 in digest.** Missing source items cleared; now fails solely on the 4 withheld items. |
| **2026-11-02 12:01 – 12:55** | AXE Chops (runs 3 to 71) | `agent_publication` runs every 45–60s. Every run attempts to drain the 4 parked items, withholds them, increments `errors`, and logs `check_error`. |
| **2026-11-02 12:55:42** | AXE Chop `20261102T125514_920019` | **Error 71/71 in digest.** Final error entry in `digest_20261102_125554.txt`. |

---

## 7. Recommended Remediation Plan

To permanently resolve both the false positives and the error loop:

### 1. Fix the Core Secret Scanner (`sase-core`)
In `crates/sase_core/src/note_attachment/scanner.rs`:
Update `openai_re` to enforce word boundaries and restrict characters to valid OpenAI key formats:
```rust
fn openai_re() -> &'static Regex {
    static RE: OnceLock<Regex> = OnceLock::new();
    RE.get_or_init(|| {
        // Enforce word boundary \b and standard OpenAI key prefixes/character lengths
        Regex::new(r"\bsk-[A-Za-z0-9]{20,}\b|\bsk-proj-[A-Za-z0-9_-]{20,}\b").unwrap()
    })
}
```
*(Note: standard legacy keys are alphanumeric without hyphens; project keys start with `sk-proj-`). Most importantly, the leading `\b` prevents matching suffixes of words like `task-` or `disk-`.*

### 2. Differentiate Parked Content from System Errors (`sase`)
In `src/sase/agents_sync/_commit_publication_drain.py` and `publication_job.py`:
When an item is withheld by publication protection, it is parked by policy. If a project has *only* parked/withheld items and no unhandled infrastructure failures (like lock timeouts or git push errors), `publication_job.py` should record the parked status in telemetry without incrementing `summary.errors`. This prevents AXE from reporting `check_error` every minute for content awaiting human triage.

### 3. Clear Stale False-Positive Ledger Entries (`gh_bobs-org__bob-cli`)
Once the Rust core scanner is updated:
1. Remove the false-positive entries from `~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-protection.json`.
2. Clear the `last_error` on the 4 affected items in `~/.sase/projects/gh_bobs-org__bob-cli/agents-publication-outbox.json`.
3. Run `sase agent sync` on `bob-cli` to allow clean publication to complete.
