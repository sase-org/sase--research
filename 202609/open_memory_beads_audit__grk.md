# Open memory beads: valid update recommendations

**Researcher:** `research.d.grk` (independent swarm report)
**Date:** 2026-09-26
**Tree:** sase `266c8b37bc` (`test(terminology): add agent-session regression guard for sase-17m.10`, 2026-09-25)
**Question:** Which open memory beads still recommend a real, still-stale memory-file change, and which memory files should Bryan actually edit?

This report does not consult other swarm reports. Findings come from `sase bead list` / `sase bead read`, audited `sase memory read`, and the current tree.

## Recommendation (up front)

Apply **ten memory/instruction edits in one authorized batch**, then run `sase memory init`. Close **one** bead as already applied. Defer **one** bead until the still-open hold landing epic finishes. Do **not** treat the three `open` message-board beads as memory work.

Highest-leverage file set, in the order I would land them:

1. `sase/memory/glossary/proc-shell.md` — stand-alone `%proc` shells
2. `sase/memory/xprompts.md` — `[[...]]` close rule + shorthand binding; later `%hold` / `%proc` queue
3. `sase/memory/lint_and_test.md` — toobig skip + screenshot update `partial` contract
4. `sase/memory/tui_screenshot.md` — resvg runtime contract + the same `partial` contract
5. `sase/memory/tui_perf.md` — rewrite rule 12
6. `sase/memory/decisions/machine-link-writes-off-primary.md` — new strand
7. `sase/memory/decisions/` — new fail-closed `-H` strand, plus a second superseded-in-part mark on `record-before-admit.md`
8. `sase/memory/dispatch.md` — new compact reference note, plus a `%dispatch` row in `xprompts.md`
9. `tools/AGENTS.md` and its four identical provider copies — ToolRun smoke `not-run` wording

Do not recreate `sase/memory/build_and_run.md`. Do not edit `sase/sase.yml` for glossary terms. Do not dump `docs/remote_dispatch.md` or `docs/xprompt.md` into core memory.

---

## Scope and method

The `memory` task type is: a sase memory note or skill that is out of date. Required fields are `path` (relative to `memory/`) and `proposed_change`. Closing still needs explicit user permission plus `sase memory init`.

Catalog at audit time:

| Status | Count | Role in this audit |
| --- | ---: | --- |
| `ready` | 12 | Pending memory recommendations; audited in full |
| `open` | 3 | All three are operational message boards, not memory edits |
| `claimed` / `in_progress` / `snoozed` | 0 | — |
| `closed` | 11 | Inventory only; already applied |

"Open memory beads" in the prompt is read as every non-closed `task_type=memory` bead (15). The three beads with status `open` are called out separately because they are a different object.

A recommendation is **valid to apply** when all of these hold:

- The target is a real memory note, strand, web descriptor, or agent-instruction file that agents still read.
- Current memory still lacks the correction, or still states the old claim.
- Current code or public docs still support the correction.
- The change is a memory/instruction edit, not an operational log or a product epic.
- The shape fits memory-write policy: rewrite an existing note when one exists; keep new notes `type: reference`; keep always-loaded text short.

A recommendation is **stale / close without a memory edit** when the tree already contains the correction.

A recommendation is **deferred** when the supporting epic is still mutating the contract.

A recommendation is **not a memory update** when the bead itself says no memory file should change.

---

## Verdict table

| Bead | Status | Size | Stated path | Verdict | Apply now? |
| --- | --- | --- | --- | --- | --- |
| `sase-sa` | ready | S | `sase/sase.yml` | Valid; **path is wrong**. Edit `glossary/proc-shell.md`. | Yes |
| `sase-sl` | ready | S | `build_and_run.md` | **Already applied** in `lint_and_test.md` by `1c246dc748` (2026-09-18). Path is also deleted. | No — close |
| `sase-st` | ready | S | `xprompts.md` | Valid. Invoke section still omits the close rule and shorthand binding. | Yes |
| `sase-xs` | open | L | `N/A: operational message board` | Not a memory update. | No |
| `sase-xt` | open | L | `N/A: operational message board` | Not a memory update. | No |
| `sase-xu` | open | L | `N/A: operational message board` | Not a memory update. | No |
| `sase-ya` | ready | M | `dispatch.md` | Valid new `type: reference` note. Keep it short; public runbook already exists. | Yes, compact |
| `sase-yd` | ready | S | `decisions/machine-link-writes-off-primary.md` | Valid new decisions strand. Implementing code is in tree. | Yes |
| `sase-12x` | ready | S | `tui_screenshot.md` | Valid. Troubleshooting still says "Missing visual extra". | Yes |
| `sase-134` | ready | M | `xprompts.md` | Valid, **defer**. `%queue` is already in the note; `%hold` is not. Epic `sase-11l` is still in progress via child `sase-11l.11`. | After hold landing |
| `sase-148` | ready | S | `tools/AGENTS.md` (+ shims) | Valid instruction-file fix; **proposed_change is stale** (3 live cases / 35 total). Not a `sase/memory/` path. | Yes, rewritten |
| `sase-16r` | ready | S | `lint_and_test.md` | Valid; also needs `tui_screenshot.md` Golden Maintenance. Coordinate with `sase-18h` and `sase-12x`. | Yes |
| `sase-18a` | ready | S | `decisions/record-before-admit.md` | Valid. New strand plus a second superseded-in-part mark. `docs/tool.md` already has the rule. | Yes |
| `sase-18h` | ready | XS | `lint_and_test.md` | Valid. `just check` / `just check-full` still described as "every whole-repo lint gate". | Yes |
| `sase-195` | ready | S | `tui_perf.md` | Valid. Rule 12 still prescribes a synchronously cleared guard flag. | Yes |

Closed memory beads (already done; not re-opened here): `sase-rz`, `sase-se`, `sase-t5`, `sase-tq`, `sase-v7`, `sase-vv`, `sase-x9`, `sase-109`, `sase-11q`, `sase-15w`, `sase-16q`.

---

## Collision map

Several valid beads edit the same files. Land them as batches, not as independent drive-bys.

| File | Beads | How to combine |
| --- | --- | --- |
| `lint_and_test.md` | `sase-sl` (done), `sase-16r`, `sase-18h` | One edit: toobig exception in the recipe/two-speed sections; `partial` update contract in PNG Snapshot Tests. Leave the already-landed exact-pixel sentence alone. |
| `tui_screenshot.md` | `sase-12x`, `sase-16r` | One edit: Troubleshooting resvg contract + Golden Maintenance `partial` contract. |
| `xprompts.md` | `sase-st` now; `sase-134` later; small `%dispatch` row with `sase-ya` | Do the Invoke/`[[...]]` repair now. Add a one-line `%dispatch` pointer when `dispatch.md` is created. Hold `%hold` / proc-queue default-weight until `sase-11l.11` closes. |
| `decisions/` | `sase-yd`, `sase-18a` | Two new strands. Independent. `sase-18a` also marks `record-before-admit.md`. |
| `glossary/proc-shell.md` | `sase-sa` | Alone. Do not touch `sase/sase.yml`. |
| `tools/AGENTS.md` + four copies | `sase-148` | Not regenerated by `sase memory init`. Edit all five; they are identical copies (separate inodes, same bytes). |

---

## Per-bead evidence

### `sase-sa` — Proc Shell still belongs to an agent — APPLY

Current strand `sase/memory/glossary/proc-shell.md`:

> A proc shell is a named supervised proc **belonging to a sase agent**, with durable output and lifecycle state. A session-attached proc shell (`shell_kind: "proc"`) is a sase monitor …

The bead quoted an older "family-attached" sentence. That half was already rewritten (session rename + gate-shell carve-out). The "belonging to a sase agent" clause is still false.

Stand-alone `%proc` units still ship as lifecycle `proc-shell` with origin `xprompt-proc` (`src/sase/agent/launch_proc_runtime.py`, `src/sase/ace/tui/models/agent_proc_shells.py`, `docs/xprompt.md`). They belong to no agent, allocate no agent runner, and render as their own Agents-tab row kind.

The bead path `sase/sase.yml` is leftover from when glossary terms lived in config. Canonical source is the glossary strand. Epic `sase-s6` is still `in_progress`, but the stand-alone proc-shell behavior is already in the tree and in public docs.

### `sase-sl` — PNG ratio-only CI tolerance — CLOSE, already applied

At the 2026-09-18 +1 (`f7ea41d3b2`) the PNG paragraph still said CI allowed a small ratio-only renderer drift tolerance. The same day, `1c246dc748` (`feat(visual): land screenshot maintenance recipe…`) rewrote the section to:

> Comparison is exact pixel equality locally and in CI; do not treat CI as a tolerance lane.

That is the correction the bead asked for. `sase/memory/build_and_run.md` is gone (migrated 2026-08-28). CI `.github/workflows/ci.yml` `visual-test` still runs bare `just fix-tui-screenshots --check` with no `SASE_VISUAL_PNG_*` env. Those env vars remain local macOS escape hatches in `docs/development.md`; they do not need to re-enter agent memory.

Close `sase-sl` as done. Do not recreate `build_and_run.md`.

### `sase-st` — `[[...]]` close rule — APPLY

`sase/memory/xprompts.md` Invoke still says only:

> Args: … `[[ ... ]]` multi-line text.

`docs/xprompt.md` Text Blocks (the long form this epic already updated) states the close rule and the structural shorthand binding. An agent who reads only memory cannot tell whether a `]]` inside prose ends the argument. Still stale. Keep the memory wording compact; do not paste the full docs section.

### `sase-xs` / `sase-xt` / `sase-xu` — message boards — NOT MEMORY

These are the only beads with status `open`. Each `path` is a sentinel (`N/A: operational message board; no memory file`) and each `proposed_change` says no memory-file edit is requested. They were a 2026-09-06/07 proof of concept for using a memory task as an append-only supervision ledger, kept `open` so they would not raise Memory TaskTriage.

Last notes are from 2026-09-07. They are not valid memory-update recommendations. Leave them out of this memory batch. Whether to close the expired boards is a process decision, not a `sase/memory/` change.

### `sase-ya` — remote dispatch reference note — APPLY, keep short

No `dispatch.md` exists under `sase/memory/`. `sase memory` grep finds no dispatch/enrollment coverage. Public docs do: `docs/remote_dispatch.md` and `docs/xprompt.md` § Remote Dispatch. Epic `sase-xe` is still `open` (reopened once), so the new note must stick to shipped public-docs facts, not in-flight Focus/Fleet UX.

A full runbook in memory would be a tax on every future `sase memory read`. Create a compact `type: reference` note and point at the runbook. Also add a one-line `%dispatch` row to the `xprompts.md` directive table so agents discover the note.

### `sase-yd` — machine link writes off primary — APPLY

`sase/memory/decisions/` has no `machine-link-writes-off-primary.md`. The invariant is implemented: `resolve_machine_artifact_link_store` / `hidden_sidecar_clone_dir` in `src/sase/sdd/_artifact_link_machine_store.py` and `src/sase/_linked_repo_paths.py`. A decisions strand is the right shape (claim, alternatives, cost, reopen). Do not fold this into a subsystem overview.

### `sase-12x` — resvg is unconditional — APPLY

`tui_screenshot.md` Troubleshooting still starts with "Missing visual extra: install the project visual dependencies". `resvg_py==0.3.3` is a main `pyproject.toml` dependency. `src/sase/ace/tui/visual_render.py` raises:

> The SASE installation is incomplete or stale. Run `sase update`, or reinstall the Python environment that owns the `sase` entry point.

The `visual` extra still pins the golden-suite stack; that is a different install. The screenshot rasterizer path is the one this bead is about.

### `sase-134` — `%hold` and proc `%queue` — DEFER

`xprompts.md` already documents `%queue` for launches (capacity, priority, weight). It has **no** `%hold` row. `docs/xprompt.md` already has a Hold Directive section and the proc-queue rule "an omitted weight counts as `0`" (agent launches default to `1.0`).

Parent epic `sase-11l` is `in_progress`. Phases `.1`–`.10` are closed. Child epic `sase-11l.11` ("Complete hold admission and visibility after the landing audit") is still `in_progress`. The bead itself says: perform the update after `sase-11l` completes, and do not claim unfinished landing repairs are complete.

Keep the bead. Do not write `%hold` into memory in this batch.

When `sase-11l.11` closes, the remaining memory work is:

- `%hold` directive row + the selector/TTL/fail-open/no-`%repeat`/`%dispatch` composition rules, mirrored from the then-current `docs/xprompt.md`
- `%proc` + `%queue`: omitted weight counts as `0`; no queue fields skips the check; a dispatched proc holds no runner capacity
- a new decisions strand for the pull model / fail-open TTL / session-scoped release

### `sase-148` — ToolRun smokes `phase-pending` — APPLY, rewrite the wording

`tools/AGENTS.md:66` still ends:

> Later-phase live owner cases remain labeled phase-pending unless `--live` is passed.

The harness docstring and `NOT_RUN = "not-run"` say otherwise. `tools/CLAUDE.md`, `GEMINI.md`, `OPENCODE.md`, and `QWEN.md` are byte-identical copies (not hardlinks). Two +1s (sase-17p.land, sase-18j.land) already recorded that the live set grew.

Do **not** use the stored `proposed_change` ("three live cases", "35 cases"). Those counts are frozen to epic `sase-135`. Current live cases labeled `not-run` without `--live`:

- `dod-8-live-monitor`, `dod-8-live-proc`, `dod-13-overhead`
- `dod-14-live-handoff-stop`, `dod-14-live-handoff-viewers`, `dod-14-live-handoff-crash`, `dod-14-live-handoff-delivery`, `dod-14-live-monitor-handoff`

Name the groups. Do not freeze a total case count. This file is directory-scoped instruction, not `sase/memory/`; `sase memory init` will not rewrite it.

### `sase-16r` — screenshot update `partial` contract — APPLY

`lint_and_test.md` PNG Snapshot Tests and `tui_screenshot.md` Golden Maintenance still omit:

- update mode exits 0 with status `partial` when goldens are left untouched
- agents must read the WARNING block / `skipped` list / `pruning_skipped_reason`
- `-n N` after `--` becomes `SASE_PYTEST_WORKERS`; `-n` inside `PYTEST_ADDOPTS` is still rejected
- a second run waits on the maintenance lock (default 2 hours)
- `--check` stays strict and never writes

`Justfile` `check-full` comments already describe the `partial` exit. `docs/development.md` is the long form. Memory still lags.

### `sase-18a` — fail-closed `sase tool run -H` — APPLY

`decisions/record-before-admit.md` still claims "recording stays fail-open even where admission later becomes fail-closed", and is already `superseded-in-part` by `decisions/guarded-recipes` (the bypass/enforcement clause). E2 narrowed recording itself for explicit hand-off.

`docs/tool.md` already states the shipped rule: explicit `-H` is fail-closed; foreground `sase tool run` stays fail-open; monitor-start reservation stays fail-open because the monitor id is already durable.

Add a new decisions strand. Mark `record-before-admit` superseded-in-part **again** for the fail-open-recording clause only. Do not rewrite the original claim in place beyond the mark + `[[...]]` back-link.

### `sase-18h` — `just check` skips toobig — APPLY

`lint_and_test.md` still presents `just check` / `just check-full` as "every whole-repo lint gate". `Justfile` is explicit:

> The `toobig` line-count gate is deliberately not a `check`/`check-full` stage … It still runs in `just lint`, which CI's lint and master-gate jobs run, and on demand via `just toobig`.

`just lint`'s comment that it includes toobig is already correct. Only the check recipes need the exception.

### `sase-195` — OptionList guard flag — APPLY

`tui_perf.md` rule 12 still says: set a guard flag and clear it synchronously in `finally:`; `call_later` races the queued echo.

`CommandLinePopup` (`src/sase/ace/tui/command_line/popup.py`) already uses `_pending_echoes` + `_set_highlight` + option-identity checks, because `OptionHighlighted` is a queued message and the `finally:` flag is already clear when the handler runs. The rule as written teaches the bug that epic `sase-17x.13` spent a phase proving.

---

## Recommended memory file changes

Apply these as one authorized memory batch. After the `sase/memory/` edits, run `sase memory init` and `sase memory init --check`. Closing each bead still needs your explicit permission.

### 1. `sase/memory/glossary/proc-shell.md` (`sase-sa`)

Replace the body with:

```markdown
A proc shell is a named supervised proc with durable output and lifecycle state.

A session-attached proc shell (`shell_kind: "proc"`) belongs to a sase agent. It is a
sase monitor and may carry timeout, workspace-claim, and follow-up policy.

A stand-alone `%proc` launch unit is also stored as lifecycle `proc-shell` with origin
`xprompt-proc`. It belongs to no agent, is never nested under a session, allocates no
agent runner or agent artifact, and is projected on the Agents tab as its own row kind
(the header counts `N agents · M procs`).

A gate shell's execution-phase proc does not make it a proc shell: it stays
`shell_kind: "gate"` throughout, pending or executing.
```

Keep `Sase Monitor` as the session-attached specialization. Do not edit `sase/sase.yml`.

### 2. `sase/memory/xprompts.md` Invoke (`sase-st`, plus a `%dispatch` pointer for `sase-ya`)

In the Invoke bullet list, replace the bare `` `[[ ... ]]` multi-line text `` mention and the shorthand bullets with:

- Args: `#name(a, b)`, `#name(k=v)` (positional first), quoted comma/special values, `[[ ... ]]` multi-line text. A `[[` block closes at the first `]]` whose next non-whitespace character is an argument terminator (`,`, `)`, `}`, `|`, or end of the argument region); a `]]` anywhere else is content. Prefer an explicit quoted argument when a `]]` must be followed by a terminator.
- Shorthand free text (`#name: text`, `#name:: text`, `#name(args): text`) is bound structurally, not rewritten into `#name([[...]])` and re-lexed, so commas, `]]`, `+`, and unbalanced parens in prose stay inside the value. `+` decodes to a space only on the bare unquoted `#name:a,b` colon form.

In the Directives table, add one compact row (do not paste the runbook):

| `%dispatch:<alias>` | | Route this launch to one enrolled, non-quarantined remote machine. Once. `local` is reserved. See [[dispatch.md]]. |

Do **not** add `%hold` in this batch.

### 3. `sase/memory/lint_and_test.md` (`sase-18h` + `sase-16r`)

**Recipe block and two-speed section.** Keep `just lint` as the recipe that includes toobig. Qualify `just check` and `just check-full`:

- `just check` — every whole-repo lint gate **except `toobig`**, plus the diff-scoped test lane
- `just check-full` — every whole-repo lint gate **except `toobig`**, plus the full test suite, plus local TUI screenshot update
- CI enforces toobig through `just lint`; the `toobig_split` routine owns splits; `just toobig` is on demand

**PNG Snapshot Tests.** Keep the exact-pixel sentence from `1c246dc748`. Add:

- Update mode (`just fix-tui-screenshots`, `just update-visual-snapshots`, and the update stage of local `just check-full`) salvages per node and per golden. When it leaves goldens untouched (unrecovered failing nodes, unstable captures, concurrent edits, or stale removal skipped on incomplete evidence), it still exits 0 with status `partial`.
- After a `partial` run, read the WARNING block or the manifest `skipped` list and `pruning_skipped_reason`. Do not treat skipped goldens as current. Do not read `counts:` alone as "nothing to update".
- `-n N` / `--numprocesses N` after `--` becomes the governed `SASE_PYTEST_WORKERS` request. `-n` inside `PYTEST_ADDOPTS` is still rejected.
- A second run in the same checkout waits for the maintenance lock (bounded, default 2 hours) instead of refusing at once.
- `--check` (`just test-visual`, CI `visual-test`) never writes and exits 1 on required drift.

### 4. `sase/memory/tui_screenshot.md` (`sase-12x` + `sase-16r`)

**Troubleshooting.** Replace the "Missing visual extra" bullet with:

- Missing `resvg_py`: it is an unconditional runtime dependency. A missing import means the installed SASE environment is incomplete or stale — run `sase update`, or reinstall/upgrade the Python environment that owns the `sase` entry point. Do not install a second renderer. The `visual` extra is the golden-suite pin set, not the screenshot rasterizer.

**Golden Maintenance.** Repeat the `partial` / WARNING / `-n` / lock / strict `--check` bullets so a reader of this child note does not have to infer them from `lint_and_test.md`. Keep the existing "generation is not approval" rule.

### 5. `sase/memory/tui_perf.md` rule 12 (`sase-195`)

Replace rule 12 with:

> **Guard programmatic widget updates.** `OptionList` posts `OptionHighlighted` as a queued message, so a guard flag set around `highlighted = X` and cleared in `finally:` is already clear when the handler runs and never catches the echo. Survive the queue: count pending programmatic echoes per row and decrement when the echo arrives; drop messages whose `Option` is no longer in the current list; or compare against the last programmatic index / a generation counter. `CommandLinePopup` (`src/sase/ace/tui/command_line/popup.py`, `_pending_echoes` / `_set_highlight` / `user_highlight_index`) is the reference implementation. `clear_options` clears the highlight without posting a message. Drop the `call_later` wording unless a widget whose echo is actually synchronous still needs it.

### 6. New `sase/memory/decisions/machine-link-writes-off-primary.md` (`sase-yd`)

New decisions strand. Suggested keyword: `Machine Artifact-Link Writes Stay Off The Primary`. Body from the bead, condensed:

- **Claim.** SASE machine (background) artifact-link mutations never target the sidecar clones nested under a project's primary workspace checkout. The machine write lane is the hidden host-owned clone at `~/.sase/projects/<key>/repos/<role>` (`hidden_sidecar_clone_dir`). Primary-nested `repos/<role>` clones are human-owned and converge through pull-based `sync_primary_sidecar_role`.
- **Why not the alternatives.** Committing from the primary with a defaulted `user` origin makes host jobs indistinguishable from the human and strands worktree dirt when the ownership gate refuses an honest `machine` origin. Relaxing `authorize_store_mutation`'s primary-#0 refusal would weaken the fail-closed ownership contract for every caller. Writing to a numbered workspace clone ties durable host state to an evictable lease.
- **Cost.** A second on-disk clone per document sidecar role per project; machine writes become visible in the primary only after auto-sync.
- **Reopens when.** Hidden host-owned clones stop being materializable on demand, or the ownership contract gains a first-class machine lane into primary-nested clones.
- **Code.** `src/sase/sdd/_artifact_link_machine_store.py`, `AccessKind.HOST_OWNED_SIDECAR`, `project.primary_sidecar_link_dirt`.
- Link `plan:202609/machine_link_mutations_off_primary.md` and neighboring decisions strands as `[[...]]`.

### 7. New fail-closed hand-off strand + mark `record-before-admit.md` (`sase-18a`)

Create e.g. `sase/memory/decisions/explicit-handoff-is-fail-closed.md`:

- **Claim.** Explicit `sase tool run -H` is fail-closed: if the ToolRun reservation cannot be committed, nothing starts and the command exits 1 naming the foreground form, because the printed run id is the only handle the caller gets and must be durable. Foreground `sase tool run` stays fail-open. A monitor start's reservation stays fail-open (the monitor id is already the durable handle; it falls back to E1.5 wrapping with one reason line).
- **Why not fail-open for `-H`.** A caller that received a printed id that never landed has no handle and no child.
- **Cost.** `-H` callers must retry or fall back to foreground form when the ledger cannot be written; monitor and foreground legs stay available.
- **Reopens when.** `-H` grows a second durable handle that survives a lost reservation, or monitor-start stops having a durable id of its own.

On `sase/memory/decisions/record-before-admit.md`:

- Extend `metadata.superseded_by` to a list: `decisions/guarded-recipes` **and** the new strand.
- Add a second body mark: the clause "recording stays fail-open even where admission later becomes fail-closed" is retired **for explicit `-H` hand-offs only**. Leave the rest of the record standing. Author a `[[...]]` back-link. Do not rewrite the original claim paragraph in place.

### 8. New `sase/memory/dispatch.md` (`sase-ya`)

`type: reference`, parent `sase/memory/xprompts.md`. Compact. Suggested description: "Read before enrolling a remote machine, launching with `%dispatch`, or recovering a quarantined/unreachable host."

Cover only agent-facing invariants, each in a few sentences, with `docs/remote_dispatch.md` as the runbook:

1. Enrollment/repair: bootstrap bundle, installation-identity pinning, quarantine, `sase machine repair`.
2. `dispatch:` config shape: providers / machines / discovery; `credential_ref` into the `0600` fleet credential store. Tailnet membership is not authorization.
3. Follow-store and Focus/Fleet running-count semantics: viewer-local follows, family promotion, unfollow tombstones, partial counts.
4. `%dispatch:<alias>`: one alias, once, no short alias; source strips only `%dispatch`; v1 remote launch cannot combine with `%wait` / `%queue` / `%clan` / an active `%hold`; retrying an uncertain request is idempotent.
5. Quarantined or unreachable host: inspect status, repair, do not assume a local uncommitted tree exists on the target.

Because `sase-xe` is still open, do not document in-flight Focus/Fleet UX that is not already in `docs/remote_dispatch.md` / `docs/xprompt.md`.

### 9. `tools/AGENTS.md` and the four identical shims (`sase-148`)

Replace the last sentence of ToolRun smokes with:

> Default mode labels live cases `not-run` unless `--live` is passed. Live cases are the owner-supervisor group (`dod-8-live-monitor`, `dod-8-live-proc`, `dod-13-overhead`) and the hand-off live group (`dod-14-live-handoff-stop`, `dod-14-live-handoff-viewers`, `dod-14-live-handoff-crash`, `dod-14-live-handoff-delivery`, `dod-14-live-monitor-handoff`). `--live` runs those too. No case is labeled `phase-pending`.

Keep the following E3 triage paragraph. Copy the same ToolRun-smokes paragraph to `tools/CLAUDE.md`, `tools/GEMINI.md`, `tools/OPENCODE.md`, and `tools/QWEN.md`.

### 10. After the `sase/memory/` edits

```bash
sase memory init
sase memory init --check
```

`sase memory init` regenerates `AGENTS.md`, provider shims, and `sase/memory/README.md`. It does **not** rewrite `tools/AGENTS.md`.

---

## Do not do in this batch

- Recreate `sase/memory/build_and_run.md` (`sase-sl`).
- Edit `sase/sase.yml` for glossary terms (`sase-sa`).
- Write `%hold` into `xprompts.md` or add a hold decisions strand until `sase-11l.11` closes (`sase-134`).
- Promote `dispatch.md` or the new decisions strands to `type: core`.
- Treat `sase-xs` / `sase-xt` / `sase-xu` as memory work, or mark them `ready` (that would raise an unrelated Memory TaskTriage gate).
- Copy `docs/xprompt.md` or `docs/remote_dispatch.md` wholesale into memory.

---

## Suggested bead follow-through (process, not file content)

Once the files above are edited and `sase memory init --check` is clean, the beads to close with permission are: `sase-sa`, `sase-st`, `sase-ya`, `sase-yd`, `sase-12x`, `sase-148`, `sase-16r`, `sase-18a`, `sase-18h`, `sase-195`, and `sase-sl` (close `sase-sl` even if you apply nothing else — the PNG exact-pixel sentence is already in `lint_and_test.md`).

Leave `sase-134` `ready` until `sase-11l.11` closes, then apply section 2's deferred `%hold` / proc-queue remainder.

Leave `sase-xs`, `sase-xt`, `sase-xu` as they are unless you want to retire the message-board experiment on purpose.
