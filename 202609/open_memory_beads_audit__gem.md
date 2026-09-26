# Research Report: Comprehensive Audit of Open Memory Task Beads

**Author:** researcher gem (`research.d.gem`)  
**Date:** 2026-09-26  
**Artifact Target:** `research:202609/open_memory_beads_audit__gem.md`  
**Workspace:** `sase-org/sase`  

---

## 1. Executive Summary

This research report provides an exhaustive independent audit of all **15 open task beads** of type `memory` currently residing in the SASE bead store (`sase bead list -T memory -s open,claimed,ready,in_progress`).

Each bead has been evaluated against:
1. Current canonical long-term memory notes under `sase/memory/` (audited via `sase memory read`).
2. Current project codebase, configuration (`sase/sase.yml`, `pyproject.toml`, `Justfile`), test fixtures, and CLI implementations.
3. Upstream and sibling epic landing histories, dependency graphs, and blocking statuses.
4. SASE memory governance policies, including immutable decision record conventions, memory-web structure, and single-turn agent execution constraints.

### High-Level Audit Findings

The 15 open beads partition into four distinct categories:

1. **Actionable and Valid Now (8 beads):**
   - `sase-sa`: Glossary definition for "Proc Shell" still claims proc shells belong to agents, omitting stand-alone `%proc` units (`xprompt-proc`).
   - `sase-st`: `xprompts.md` fails to document `[[ ... ]]` text block delimiter termination rules and structural shorthand binding.
   - `sase-yd`: Architectural invariant from epic `sase-y3` (machine artifact-link mutations occur only in hidden host-owned clones, never in primary checkouts) lacks a decisions-web strand.
   - `sase-12x`: `tui_screenshot.md` contains obsolete troubleshooting guidance referring to a "missing visual extra" for `resvg_py`, which is now an unconditional runtime dependency.
   - `sase-148`: `tools/AGENTS.md` (and provider shims) claims un-run smoke cases are labeled `phase-pending`, whereas `tools/smoke_sase_tool_runs` now labels them `not-run`.
   - `sase-16r`: `lint_and_test.md` and `tui_screenshot.md` predate epic `sase-169` and lack the partial-success (exit 0 `partial`), WARNING block inspection, and lock-wait update contracts.
   - `sase-18a`: E2 durable ToolRun hand-off made explicit `sase tool run -H` fail-closed, contradicting `decisions:record-before-admit`'s blanket claim that recording is always fail-open.
   - `sase-18h`: `lint_and_test.md` claims `just check` runs every whole-repo lint gate, omitting that `toobig` is intentionally skipped and delegated to CI's `just lint` and the `toobig_split` routine.
   - `sase-195`: `tui_perf.md` Rule 12 prescribes an ineffective `finally:` guard flag for `OptionList` highlight assignments; Textual queues `OptionHighlighted` events asynchronously, requiring queue-surviving echo counts (as implemented in `CommandLinePopup`).

2. **Blocked on In-Flight Epics (2 beads):**
   - `sase-134`: Proposes documenting `%hold` directives and proc queue semantics in `xprompts.md` and a new decision strand. The bead's description explicitly instructs waiting for parent epic `sase-11l` to complete. Child epic `sase-11l.11` is currently active and in-progress repairing hold admission edge cases. Applying this memory change now would document unreleased/unsettled semantics.
   - `sase-ya`: Proposes creating a new reference note `dispatch.md` for remote dispatch operations. While valid in concept, remote dispatch is actively undergoing fleet parity and bootstrap hardening under epics `sase-xe.16` and `sase-133`. Creating `dispatch.md` should be coordinated with the landing of those epics to prevent stale reference documentation.

3. **Already Implemented / Obsolete (1 bead):**
   - `sase-sl`: Proposes correcting visual PNG tolerance guidance in `build_and_run.md`. `build_and_run.md` was migrated to `lint_and_test.md`, which already states: *"Comparison is exact pixel equality locally and in CI; do not treat CI as a tolerance lane."* No drift tolerance claims remain. This bead is obsolete and should be closed.

4. **Non-Memory Operational Records (3 beads):**
   - `sase-xs`, `sase-xt`, `sase-xu`: Co-opted as operational message boards for sequential supervisor agent chains (epochs 00a, 00b, 016) monitoring Athena agent runs on September 6–7, 2026. All three explicitly state: *"This user-authorized experiment does not request a memory edit."* No memory files should be altered for these beads.

---

## 2. Complete Inventory Table

| Bead ID | Title | Stated Path | Actual Target File | Category | Priority | Recommended Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`sase-sa`** | Glossary "Proc Shell" still says proc shell belongs to an agent | `sase/sase.yml` | `sase/memory/glossary/proc-shell.md` | **Valid Now** | High | Update glossary strand; run `sase memory init`. |
| **`sase-sl`** | Correct visual PNG tolerance guidance in build_and_run memory | `build_and_run.md` | `sase/memory/lint_and_test.md` | **Obsolete** | None | Close bead as already resolved; no file changes. |
| **`sase-st`** | `xprompts.md` Invoke documents `[[ ... ]]` without closing rule | `xprompts.md` | `sase/memory/xprompts.md` | **Valid Now** | High | Update Invoke bullet with termination and binding rules. |
| **`sase-xs`** | Message board: supervise athena agents (epoch 00a) | `N/A` | None | **Non-Memory** | None | Close/retriage operational log; no memory edit. |
| **`sase-xt`** | Message board: autonomous agent watch (epoch 00b) | `N/A` | None | **Non-Memory** | None | Close/retriage operational log; no memory edit. |
| **`sase-xu`** | Message board: athena agent supervision (epoch 016) | `N/A` | None | **Non-Memory** | None | Close/retriage operational log; no memory edit. |
| **`sase-ya`** | Add reference memory note for remote dispatch | `dispatch.md` | `sase/memory/dispatch.md` | **Blocked / Premature** | Medium | Defer creation until epic `sase-xe.16` / `sase-133` settle. |
| **`sase-yd`** | Record decision strand: machine link writes off primary | `decisions/machine-link-writes-off-primary.md` | `sase/memory/decisions/machine-link-writes-off-primary.md` | **Valid Now** | High | Create decisions strand; update decisions index. |
| **`sase-12x`** | Update tui_screenshot memory for runtime resvg dependency | `tui_screenshot.md` | `sase/memory/tui_screenshot.md` | **Valid Now** | High | Update Troubleshooting section in `tui_screenshot.md`. |
| **`sase-134`** | Document hold admission and proc queue semantics | `xprompts.md` | `sase/memory/xprompts.md` | **Blocked** | High (when unblocked) | Hold until parent epic `sase-11l` / `sase-11l.11` closes. |
| **`sase-148`** | `tools/AGENTS.md` ToolRun smokes says phase-pending; harness says not-run | `tools/AGENTS.md` | `tools/AGENTS.md` (+ shims) | **Valid Now** | Medium | Replace "phase-pending" with "not-run" and note `--live`. |
| **`sase-16r`** | Screenshot memory: document fix-tui-screenshots partial update contract | `lint_and_test.md` | `lint_and_test.md` & `tui_screenshot.md` | **Valid Now** | High | Update PNG Snapshot and Golden Maintenance sections. |
| **`sase-18a`** | Record fail-closed tool run -H rule; mark record-before-admit superseded | `decisions/record-before-admit.md` | `decisions/tool-run-handoff-fail-closed.md` & `record-before-admit.md` | **Valid Now** | High | Author new strand and mark existing strand superseded in part. |
| **`sase-18h`** | Document that just check skips toobig | `lint_and_test.md` | `sase/memory/lint_and_test.md` | **Valid Now** | High | Add explicit clarification in `lint_and_test.md`. |
| **`sase-195`** | `tui_perf.md` rule 12: synchronously cleared flag fails on queued echoes | `tui_perf.md` | `sase/memory/tui_perf.md` | **Valid Now** | High | Rewrite Rule 12 to prescribe queue-surviving echo counts. |

---

## 3. Detailed Audit by Bead

### 3.1 Bead `sase-sa`: Stand-Alone Proc Shells in Glossary

- **Bead Details:** Created 2026-08-23 by `sase-s6.land`. Status: `ready`. Size: `small`.
- **Stated vs. Actual Path:** Stated path was `sase/sase.yml` under `glossary.terms.Proc Shell`. Following the memory webs migration, glossary terms are authoritatively stored as individual strand Markdown files under `sase/memory/glossary/`. The actual target is `sase/memory/glossary/proc-shell.md`.
- **Current Memory State:**
  ```markdown
  A proc shell is a named supervised proc belonging to a sase agent, with durable output
  and lifecycle state. A session-attached proc shell (`shell_kind: "proc"`) is a sase
  monitor and may carry timeout, workspace-claim, and follow-up policy. A gate shell's
  execution-phase proc does not make it a proc shell: it stays `shell_kind: "gate"`
  throughout, pending or executing.
  ```
- **Codebase Truth:**
  Epic `sase-s6` implemented typed launch units (`src/sase/agent/launch_proc_runtime.py`, `src/sase/procs/service.py`). A `%proc` launch unit creates a proc shell with origin `xprompt-proc`. It belongs to no agent, allocates no agent runner, is not associated with an agent session, and is displayed as an independent row kind in the Agents tab (`src/sase/ace/tui/models/agent_proc_shells.py`).
- **Audit Verdict:** **VALID**. The opening phrase "belonging to a sase agent" is technically inaccurate and confusing for agents working with standalone proc units.
- **Action:** Update `sase/memory/glossary/proc-shell.md` to define a proc shell as a named supervised proc with durable output and lifecycle state that may belong to a sase agent or run stand-alone via `%proc`. Run `sase memory init` to re-sync generated files.

---

### 3.2 Bead `sase-sl`: Visual PNG Tolerance Guidance

- **Bead Details:** Created 2026-08-24 by `0c3`. Status: `ready`. Size: `small`.
- **Stated Path:** `build_and_run.md`. Note 1 records that plan `plan:202608/lint_and_test_memory.md` migrated `build_and_run.md` to `lint_and_test.md`.
- **Current Memory State:**
  In `sase/memory/lint_and_test.md`, lines 82–85:
  ```markdown
  CI's dedicated `visual-test` job runs `just fix-tui-screenshots --check` and
  never writes goldens. Comparison is exact pixel equality locally and in CI; do not treat
  CI as a tolerance lane. The fixtures pin color and the bundled Fira Code / DejaVu / Noto
  Emoji renderer stack.
  ```
- **Codebase Truth:** The old ratio-only renderer drift tolerance documentation has already been purged from the active memory corpus. Exact pixel equality is explicitly stated.
- **Audit Verdict:** **OBSOLETE / ALREADY APPLIED**. No text in the current memory repository claims CI allows ratio drift tolerance.
- **Action:** Close `sase-sl` with resolution `already_done`. No memory file modifications needed.

---

### 3.3 Bead `sase-st`: Multi-Line `[[ ... ]]` Delimiters and Shorthands in `xprompts.md`

- **Bead Details:** Created 2026-08-24 by `sase-sn.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `sase/memory/xprompts.md`.
- **Current Memory State:**
  ```markdown
  - Args: `#name(a, b)`, `#name(k=v)` (positional first), quoted comma/special values,
    `[[ ... ]]` multi-line text.
  - Shorthands: `#name:arg`, `#name:a,b`, `` #name:`arg with spaces` ``, `#name+` =
    `#name:true`; line `#name: text` captures to blank line, `#name:: text` to next
    line-boundary directive.
  ```
- **Codebase Truth:**
  Epic `sase-sn` established shared Rust and Python argument scanners. In `docs/xprompt.md` (lines 741–752), the definitive parsing rules are documented:
  1. A `[[` block closes at the first `]]` whose next non-whitespace character is an argument terminator (`,`, `)`, `}`, `|`, or end of scanned region). Prose containing internal `]]` (e.g., Markdown links or glossary keys) does not prematurely terminate the argument unless followed by a terminator character.
  2. Shorthand free-text payloads (`#name: text`, `#name:: text`, `#name(args): text`) are bound structurally rather than re-lexed into `[[ ... ]]`, preserving prose characters like commas, `]]`, `+`, and unbalanced parentheses.
- **Audit Verdict:** **VALID**. Agents reading only `xprompts.md` have repeatedly struggled with quoting rules, escaping `]]` unnecessarily or encountering parse errors.
- **Action:** Update the Invoke section of `sase/memory/xprompts.md` to state the terminator rule and structural binding guarantee.

---

### 3.4 Beads `sase-xs`, `sase-xt`, `sase-xu`: Athena Supervisor Message Boards

- **Bead Details:**
  - `sase-xs`: Epoch 00a, created 2026-09-06 by `00a`. Status: `open`.
  - `sase-xt`: Epoch 00b, created 2026-09-07 by `00b`. Status: `open`.
  - `sase-xu`: Epoch 016, created 2026-09-07 by `016`. Status: `open`.
- **Stated Path:** `N/A: operational message board; no memory file`.
- **Audit Findings:**
  All three beads were created as operational handoff batons for a sequential supervisor agent loop monitoring test execution and recovery on machine Athena. Their descriptions state:
  > *"This is Bryan's explicitly requested proof of concept: use a memory task bead as an append-only message board for a sequential chain of SASE agents supervising all agents running on athena. This is an operational coordination record, not a request to edit a memory file or implement a new bead type."*
- **Audit Verdict:** **INVALID AS MEMORY RECOMMENDATIONS**. These beads contain no memory update proposals. They were created under task type `memory` solely as a temporary mechanism to avoid certain task triage gates.
- **Action:** Do not make any memory changes. These beads should be closed as completed operational runs or archived by the user.

---

### 3.5 Bead `sase-ya`: Reference Memory for Remote Dispatch

- **Bead Details:** Created 2026-09-07 by `sase-xe.land`. Status: `ready`. Size: `medium`.
- **Stated Path:** `dispatch.md` (to be created under `sase/memory/dispatch.md`).
- **Proposed Change:** Author a new reference memory note documenting:
  - Machine enrollment and repair (`sase machine enroll`, bootstrap bundle, token pinning).
  - Dispatch configuration format (`dispatch:` in config, credential storage under `~/.sase/credentials/`).
  - Follow-store and Focus/Fleet count semantics (viewer-local follows, promotion, tombstones).
  - `%dispatch` operation-key recovery.
  - Quarantined and unreachable host recovery procedures.
- **Codebase Truth:** Remote dispatch was introduced in epic `sase-xe`, but follow-up epics `sase-xe.16` ("Complete remote dispatch"), `sase-133` ("Remote dispatch Agents-tab parity"), and `sase-xe.16.11` are still active.
- **Audit Verdict:** **VALID BUT PREMATURE / CURRENTLY IN FLUX**. Documenting an active subsystem whose wire protocols and TUI parity are still landing risks creating immediate documentation drift.
- **Action:** Defer writing `sase/memory/dispatch.md` until epic `sase-xe.16` and `sase-133` complete and land.

---

### 3.6 Bead `sase-yd`: Decision Strand for Machine Link Writes Off Primary

- **Bead Details:** Created 2026-09-08 by `sase-y3.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `decisions/machine-link-writes-off-primary.md`.
- **Codebase Truth:**
  Epic `sase-y3` landed the architectural rule that background machine mutations to artifact-link stores must never touch the human primary workspace (`~/.sase/projects/<key>/repos/<role>` vs `hidden_sidecar_clone_dir`). This invariant is enforced in `src/sase/sdd/_artifact_link_machine_store.py` (`resolve_machine_artifact_link_store`) and `src/sase/workspace_provider/` (`AccessKind.HOST_OWNED_SIDECAR`).
- **Audit Verdict:** **VALID**. The bead provides a fully drafted, high-quality decision record conforming to the Decision Web specification (Claim, Alternatives, Cost, Reopen Condition). SASE memory currently has no record of this invariant.
- **Action:** Create `sase/memory/decisions/machine-link-writes-off-primary.md` and link it in the decisions index.

---

### 3.7 Bead `sase-12x`: Runtime `resvg` Dependency in `tui_screenshot.md`

- **Bead Details:** Created 2026-09-18 by `0mr.f0--code`. Status: `ready`. Size: `small`.
- **Stated Path:** `sase/memory/tui_screenshot.md`.
- **Current Memory State:**
  ```markdown
  - Missing visual extra: install the project visual dependencies; the screenshot command
    should report an actionable renderer/import error rather than falling back to a second
    renderer.
  ```
- **Codebase Truth:**
  `pyproject.toml` declares `"resvg_py==0.3.3"` under core `dependencies`. It is no longer an optional "extra". An `ImportError` on `resvg_py` indicates an incomplete or broken virtualenv, not a missing opt-in extra.
- **Audit Verdict:** **VALID**. The current Troubleshooting advice instructs agents and users to perform an obsolete installation step (`.[visual]`) that no longer exists.
- **Action:** Update `sase/memory/tui_screenshot.md` Troubleshooting section.

---

### 3.8 Bead `sase-134`: Hold Admission and Proc Queue Semantics

- **Bead Details:** Created 2026-09-18 by `sase-11l.land`. Status: `ready`. Size: `medium`.
- **Stated Path:** `xprompts.md`.
- **Audit Findings:**
  Bead description explicitly notes:
  > *"The code feature remains in landing repair; perform this update after sase-11l completes. Scope is a bounded reference-note addition and one decision strand, so size medium."*
  Inspection of the live bead store confirms that parent epic `sase-11l` is `IN_PROGRESS` and actively working child epic `sase-11l.11` ("Complete hold admission and visibility after the landing audit").
- **Audit Verdict:** **VALID BUT CURRENTLY BLOCKED**. Applying memory updates for `%hold` before `sase-11l.11` settles violates the landing protocol.
- **Action:** Keep bead `sase-134` open and blocked on `sase-11l.11`. Do not apply memory edits yet.

---

### 3.9 Bead `sase-148`: `tools/AGENTS.md` Smoke Labels

- **Bead Details:** Created 2026-09-20 by `sase-135.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `tools/AGENTS.md` (and shims `tools/CLAUDE.md`, `tools/GEMINI.md`, `tools/OPENCODE.md`, `tools/QWEN.md`).
- **Current Text:**
  ```markdown
  Later-phase live owner cases remain labeled phase-pending unless `--live` is passed.
  ```
- **Codebase Truth:**
  Phase 7 of epic `sase-135` refactored `tools/smoke_sase_tool_runs` to emit `not-run` for the three live cases (`dod-8-live-monitor`, `dod-8-live-proc`, `dod-13-overhead`) unless `--live` is supplied. No test emits `phase-pending`.
- **Audit Verdict:** **VALID**. Although `tools/AGENTS.md` is a scoped instruction file rather than a note in `sase/memory/`, it directly directs agents working in `tools/`.
- **Action:** Update line 65 of `tools/AGENTS.md` and synchronize the shims.

---

### 3.10 Bead `sase-16r`: `fix-tui-screenshots` Partial-Success Contract

- **Bead Details:** Created 2026-09-23 by `sase-169.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `lint_and_test.md` and `tui_screenshot.md`.
- **Current Memory State:** Neither note mentions update mode's exit-0 `partial` status, WARNING blocks, `-n` worker mapping, or lock waiting.
- **Codebase Truth:**
  Epic `sase-169` overhauled `tests/ace/tui/visual/_visual_maintenance_cli.py`:
  1. Update runs salvage healthy goldens and exit 0 with status `partial` when some fail or skip.
  2. Agents must read the WARNING block or manifest `skipped` list rather than assuming exit 0 means all snapshots were updated.
  3. `--numprocesses N` / `-n N` after `--` is governed and mapped to `SASE_PYTEST_WORKERS`.
  4. Concurrent runs wait for the maintenance lock (default 2 hours).
- **Audit Verdict:** **VALID**. Crucial for preventing agents from misinterpreting a `partial` visual update as a complete pass.
- **Action:** Update `lint_and_test.md` (PNG Snapshot Tests) and `tui_screenshot.md` (Golden Maintenance).

---

### 3.11 Bead `sase-18a`: Fail-Closed Explicit ToolRun Hand-Off

- **Bead Details:** Created 2026-09-24 by `sase-17p.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `decisions/record-before-admit.md`.
- **Current Memory State:**
  `decisions/record-before-admit.md` states:
  > *"...recording adds no new supervisor, and recording stays fail-open even where admission later becomes fail-closed."*
- **Codebase Truth:**
  Epic `sase-17p` (E2 durable ToolRun hand-off) changed this rule for explicit handoffs. As documented in `docs/tool.md` (lines 205–209):
  > *"`sase tool run -H` is **fail-closed**: if the reservation cannot be committed, nothing starts (exit 1)... Foreground `sase tool run` stays **fail-open**... A monitor start's reservation is **fail-open**..."*
- **Audit Verdict:** **VALID**. A new decision strand is required, and `record-before-admit.md` must be marked superseded in part.
- **Action:** Create `sase/memory/decisions/tool-run-handoff-fail-closed.md` and mark `decisions/record-before-admit.md` superseded in part with a back-link.

---

### 3.12 Bead `sase-18h`: `just check` Skips `toobig`

- **Bead Details:** Created 2026-09-24 by `0rp--code`. Status: `ready`. Size: `xsmall`.
- **Stated Path:** `lint_and_test.md`.
- **Current Memory State:**
  `lint_and_test.md` claims:
  > *"`just check` runs every whole-repo lint gate plus a diff-scoped test lane..."*
- **Codebase Truth:**
  `Justfile` (lines 713–716, 748) explicitly excludes `toobig` from both `check` and `check-full`. `toobig` is enforced in CI via `just lint`, and automated file splitting is owned by the `toobig_split` routine.
- **Audit Verdict:** **VALID**. Agents encountering `toobig` CI failures are frequently confused because local `just check` passed cleanly.
- **Action:** Amend `lint_and_test.md` to state that `just check` and `just check-full` skip `toobig`.

---

### 3.13 Bead `sase-195`: Rule 12 `OptionList` Highlight Echoes in `tui_perf.md`

- **Bead Details:** Created 2026-09-25 by `sase-17x.13.land`. Status: `ready`. Size: `small`.
- **Stated Path:** `tui_perf.md`.
- **Current Memory State:**
  ```markdown
  12. **Guard programmatic widget updates.** `OptionList` emits `OptionHighlighted` echoes
      on programmatic `highlighted = X` assignments. Set a guard flag and clear it
      synchronously (`finally:`) — clearing via `call_later` races the queued echo and
      causes cursor jumps/freezes.
  ```
- **Codebase Truth:**
  Phase `sase-17x.13.5` demonstrated that Textual posts `OptionHighlighted` to the message queue. A synchronous `finally:` block executes immediately, clearing the guard flag *before* the queued message arrives at the handler. In `src/sase/ace/tui/command_line/popup.py`, the proper fix was implemented: tracking pending echoes in a dict (`_pending_echoes: dict[int, int]`).
- **Audit Verdict:** **VALID**. The current rule provides provably defective advice that introduces UI glitches when implemented as written.
- **Action:** Rewrite Rule 12 in `sase/memory/tui_perf.md`.

---

## 4. Recommended Set of Memory File Changes

The following concrete changes are recommended for immediate application:

### Change 1: `sase/memory/glossary/proc-shell.md` (re: `sase-sa`)

Update `sase/memory/glossary/proc-shell.md` to broaden the definition of Proc Shell:

```markdown
A proc shell is a named supervised proc with durable output and lifecycle state.
A proc shell may belong to a sase agent (a session-attached monitor carrying timeout,
workspace-claim, and follow-up policy) or run stand-alone (dispatched by a `%proc` launch
unit with origin `xprompt-proc`, belonging to no agent and projected as its own row kind
in the Agents tab). A gate shell's execution-phase proc does not make it a proc shell: it
stays `shell_kind: "gate"` throughout, pending or executing.
```

*Post-edit action:* Run `sase memory init` to propagate to `AGENTS.md` and provider shims.

---

### Change 2: `sase/memory/xprompts.md` (re: `sase-st`)

In `sase/memory/xprompts.md`, update the `Args:` and `Shorthands:` items in the **Invoke** section:

```markdown
- Args: `#name(a, b)`, `#name(k=v)` (positional first), quoted comma/special
  values, `[[ ... ]]` multi-line text. A `[[` block closes at the first `]]`
  whose next non-whitespace character is an argument terminator (`,`, `)`, `}`,
  `|`, or end of the argument region); a `]]` anywhere else is content. A `]]`
  that must be followed by a terminator needs an explicit quoted argument
  instead.
- Shorthands: `#name:arg`, `#name:a,b`, `` #name:`arg with spaces` ``, `#name+` =
  `#name:true`; line `#name: text` captures to blank line, `#name:: text` to next
  line-boundary directive. Shorthand free text (`#name: text`, `#name:: text`,
  `#name(args): text`) is bound structurally rather than re-lexed, so commas,
  `]]`, `+`, and unbalanced parens in prose stay inside the value. `+` decodes to
  a space only on the bare unquoted `#name:a,b` colon form.
```

---

### Change 3: `sase/memory/lint_and_test.md` (re: `sase-18h` and `sase-16r`)

1. In the introductory overview, update paragraph 2:

```markdown
`just check` runs every whole-repo lint gate except `toobig` plus a diff-scoped
test lane (`just test-scoped`) that selects tests via a static import-graph
closure. (CI enforces `toobig` through `just lint`, while the `toobig_split` routine
owns automated file splits). The scoped run is serial unless a middle gear wins it a
small, bounded suite-gate lease, and it never queues behind other agents' runs
either way.
```

2. In the **PNG Snapshot Tests** section, add the partial-success update contract:

```markdown
Update mode (`just fix-tui-screenshots`, `just update-visual-snapshots`, and the
update stage of local `just check-full`) salvages per node and per golden. When
unrecovered failing nodes, unstable captures, or concurrent edits prevent updating
certain goldens, it still exits 0 with status `partial`. After a `partial` run, agents
must read the WARNING block or the manifest's `skipped` list and `pruning_skipped_reason`;
do not assume exit 0 means all goldens updated. `-n N` / `--numprocesses N` after `--`
is translated to the governed `SASE_PYTEST_WORKERS`. A second run in the same checkout
waits for the maintenance lock (bounded, default 2 hours) instead of refusing at once.
CI's dedicated `visual-test` job (`--check`) stays strict and never writes goldens.
```

---

### Change 4: `sase/memory/tui_screenshot.md` (re: `sase-12x` and `sase-16r`)

1. In **Troubleshooting**, replace the first bullet:

```markdown
- Missing resvg dependency: `resvg_py` is an unconditional runtime dependency for
  normal installs; a missing import indicates an incomplete or stale SASE environment.
  Run `sase update` or reinstall/upgrade the Python environment owning the `sase`
  entry point. The single canonical renderer contract remains.
```

2. In **Golden Maintenance**, expand the update mode contract:

```markdown
Update mode salvages per node and per golden, exiting 0 with status `partial` when
goldens are skipped (unrecovered failures, unstable captures, incomplete evidence).
Inspect the WARNING block and manifest `skipped` list after a `partial` run. `-n N`
after `--` sets governed `SASE_PYTEST_WORKERS`. Runs in the same checkout wait for the
maintenance lock (default 2 hours). `--check` (`just test-visual`, CI `visual-test`)
strictly refuses drift.
```

---

### Change 5: `sase/memory/tui_perf.md` (re: `sase-195`)

Replace Rule 12:

```markdown
12. **Guard programmatic widget updates against queued echoes.** `OptionList` emits
    `OptionHighlighted` as an asynchronous queued message on programmatic `highlighted = X`
    assignments. A guard flag cleared synchronously in `finally:` never catches the echo
    because the handler executes long after the flag is cleared. Instead, use a check that
    survives the message queue: count pending programmatic echoes per row
    (decrementing as each echo arrives) and discard messages whose `Option` is no longer
    in the current list, or check against the last programmatic index or a generation
    counter. See `CommandLinePopup` (`src/sase/ace/tui/command_line/popup.py`,
    `_pending_echoes`) for the reference implementation. `clear_options()` clears highlights
    without posting messages.
```

---

### Change 6: `sase/memory/decisions/machine-link-writes-off-primary.md` (re: `sase-yd`)

Create new strand `sase/memory/decisions/machine-link-writes-off-primary.md`:

```markdown
---
type: decision
status: accepted
date: 2026-09-08
deciders: Bryan
links:
  - decisions:corpus-before-mechanism
  - decisions:host-owned-completion
---

# Machine Artifact-Link Mutations Occur Off Primary Sidecar Clones

aka machine link writes off primary, hidden sidecar link writes

**Claim.** SASE machine (background) artifact-link mutations never target the sidecar
clones nested under a project's primary (human) workspace checkout. The machine write
lane is the hidden host-owned clone at `~/.sase/projects/<key>/repos/<role>`
(`hidden_sidecar_clone_dir`), following the agents-sidecar precedent; the primary's
nested `repos/<role>` clones are human-owned and converge only through the existing
pull-based `sync_primary_sidecar_role` auto-sync.

**Why.** Committing from the primary (the pre-epic behavior, reached by a defaulted `user`
mutation origin) makes host background jobs indistinguishable from the human and strands
worktree dirt when the ownership gate refuses an honest `machine` origin. Relaxing
`authorize_store_mutation`'s primary-#0 refusal would weaken the fail-closed ownership
contract for every caller, not just link maintenance. Writing to a numbered workspace
clone ties durable host state to an evictable lease.

**Cost.** A second on-disk clone per document sidecar role per project, and machine writes
become visible in the primary only after auto-sync runs.

**Reopens when.** Hidden host-owned clones stop being materializable on demand, or the
ownership contract gains a first-class machine lane into primary-nested clones.

## References

- Epic plan: `plan:202609/machine_link_mutations_off_primary.md`
- Implementing code: `src/sase/sdd/_artifact_link_machine_store.py`, `src/sase/workspace_provider/`
```

---

### Change 7: `sase/memory/decisions/tool-run-handoff-fail-closed.md` & `record-before-admit.md` (re: `sase-18a`)

1. Create new strand `sase/memory/decisions/tool-run-handoff-fail-closed.md`:

```markdown
---
type: decision
status: accepted
date: 2026-09-24
deciders: Bryan
links:
  - decisions:record-before-admit
  - decisions:guarded-recipes
---

# Explicit ToolRun Hand-Off Is Fail-Closed

aka fail-closed tool run -H, durable hand-off reservation

**Claim.** Explicit `sase tool run -H` is fail-closed: if the ToolRun reservation
cannot be committed, nothing starts and the command exits 1 naming the foreground form.
Foreground `sase tool run` stays fail-open, and monitor-start ToolRun reservation stays
fail-open.

**Why.** In explicit hand-off (`-H`), the printed ToolRun ID is the sole handle the caller
receives to follow, wait on, or inspect the command. If recording failed open, the command
would execute untracked and the caller would hold an unresolvable ID. In foreground execution,
standard I/O streams directly to the caller, so execution value is preserved even without a
record. In a monitor start, the monitor ID is already durable and acts as the fallback handle.

**Cost.** An explicit handoff invocation fails if the ToolRun database is locked or corrupted,
requiring the caller to retry or execute in foreground.

**Reopens when.** A lightweight, zero-latency in-memory reservation handle can be safely
federated across processes without SQLite transaction guarantees.

## References

- Plan decision: `plan:202609/tool_e2_durable_handoff.md`
- Documentation: `docs/tool.md`
```

2. In `sase/memory/decisions/record-before-admit.md`, append to the header metadata:

```markdown
> **Partly superseded** by `decisions/guarded-recipes` and `decisions/tool-run-handoff-fail-closed`.

> _Superseded in part:_ The claim that "recording stays fail-open even where admission
> later becomes fail-closed" is narrowed. Explicit hand-off (`sase tool run -H`) is
> fail-closed when reservation fails, because the run ID is the caller's sole handle.
> Foreground and monitor-start recording remain fail-open.
> See [[decisions/tool-run-handoff-fail-closed]].
```

---

### Change 8: `tools/AGENTS.md` and Shims (re: `sase-148`)

In `tools/AGENTS.md` and shims (`tools/CLAUDE.md`, `tools/GEMINI.md`, `tools/OPENCODE.md`, `tools/QWEN.md`), update the **ToolRun smokes** paragraph:

```markdown
`tools/smoke_sase_core_rs_tool_runs` is an isolated real-binding round trip against the
installed `sase_core_rs` wheel. `tools/smoke_sase_tool_runs` is the black-box harness:
it talks to the real store and CLI for catalog, foreground run, signals, lost-run
recovery, fail-open recording, and query contracts. The three live cases
(`dod-8-live-monitor`, `dod-8-live-proc`, `dod-13-overhead`) are labeled `not-run`
unless `--live` is passed; passing `--live` runs all 35 cases.
```

---

## 5. Summary of Recommended Bead Dispositions

| Bead ID | Recommended Bead Action | Justification |
| :--- | :--- | :--- |
| `sase-sa` | Apply change & **Close** | Proc shell glossary definition corrected for stand-alone procs. |
| `sase-st` | Apply change & **Close** | Text block syntax and shorthand binding documented in `xprompts.md`. |
| `sase-yd` | Apply change & **Close** | Decision strand for machine link writes recorded. |
| `sase-12x` | Apply change & **Close** | `resvg_py` runtime dependency reflected in `tui_screenshot.md`. |
| `sase-148` | Apply change & **Close** | Smoke test harness labels corrected in `tools/AGENTS.md`. |
| `sase-16r` | Apply change & **Close** | Partial-success screenshot contract documented in `lint_and_test.md` and `tui_screenshot.md`. |
| `sase-18a` | Apply change & **Close** | Fail-closed tool handoff strand recorded and `record-before-admit.md` linked. |
| `sase-18h` | Apply change & **Close** | `toobig` exclusion from `check`/`check-full` documented in `lint_and_test.md`. |
| `sase-195` | Apply change & **Close** | Rule 12 in `tui_perf.md` corrected for asynchronous Textual messages. |
| `sase-sl` | **Close** (No change) | Already implemented in `lint_and_test.md`. |
| `sase-xs` | **Close / Archive** | Operational supervisor log from Sep 6; not a memory task. |
| `sase-xt` | **Close / Archive** | Operational supervisor log from Sep 7; not a memory task. |
| `sase-xu` | **Close / Archive** | Operational supervisor log from Sep 7; not a memory task. |
| `sase-134` | **Keep Open (Blocked)** | Blocked on parent epic `sase-11l` / `sase-11l.11` completion. |
| `sase-ya` | **Keep Open (Deferred)** | Defer until remote dispatch epics (`sase-xe.16`, `sase-133`) stabilize. |

---
