# Audit of Open Memory Beads: Valid Memory-Update Recommendations

**Researcher:** mus (independent swarm report, `__mus` suffix)
**Date:** 2026-09-26 (UTC)
**Scope:** all open (`open` + `ready`) beads with task-type `memory`
**Method:** `sase bead read` on each open memory bead (audited reads), then
independent verification against current memory via `sase memory read` and
against code/docs via grep. No peer swarm report was consulted.
**Authorization routing:** per `/sase_memory_write`, this turn's prompt asks for
recommendations only, not edits — so nothing under `sase/memory/` was modified.
The recommended changes below should be executed later through the sanctioned
path (bead worker with explicit user permission + `sase memory init`).

## Census

15 open memory beads: 12 `ready`, 3 `open`.

| Bead | Status | Target | Verdict |
| --- | --- | --- | --- |
| sase-sa | ready | glossary "Proc Shell" (`sase/sase.yml`) | VALID, still stale |
| sase-sl | ready | PNG tolerance guidance (`lint_and_test.md`) | STALE — already fixed, recommend close |
| sase-st | ready | `xprompts.md` Invoke `[[ ... ]]` rule | VALID, still missing |
| sase-ya | ready | new `dispatch.md` reference note | VALID gap (no note exists) |
| sase-yd | ready | new decisions strand (machine link-write lane) | VALID, unrecorded invariant |
| sase-12x | ready | `tui_screenshot.md` resvg contract | VALID, still stale |
| sase-134 | ready | `xprompts.md` %hold + proc-queue semantics | VALID but BLOCKED on sase-11l landing |
| sase-148 | ready | `tools/AGENTS.md` ToolRun smokes paragraph | VALID, still stale (scope grew) |
| sase-16r | ready | partial-success update contract (2 notes) | VALID, still missing |
| sase-18a | ready | decisions strand + supersede record-before-admit | VALID, still unrecorded |
| sase-18h | ready | `lint_and_test.md` toobig skip | VALID, still missing |
| sase-195 | ready | `tui_perf.md` rule 12 guard-flag rewrite | VALID, still wrong |
| sase-xs | open | N/A (message board) | NO EDIT correctly requested |
| sase-xt | open | N/A (message board) | NO EDIT correctly requested |
| sase-xu | open | N/A (message board) | NO EDIT correctly requested |

## Per-bead findings

### sase-sa — VALID (verified stale)
Current `glossary:proc-shell` still reads "a named supervised proc belonging to
a sase agent". Code confirms the stand-alone case exists:
`XPROMPT_PROC_ORIGIN = "xprompt-proc"` in `src/sase/procs/models/common.py`,
`xprompt_proc` origin handling in `src/sase/procs/models/proc.py`.
Recommend rewording via `sase/sase.yml` + `sase memory init` to cover both
agent-owned monitor shells and stand-alone `%proc` shells.

### sase-sl — STALE, no change recommended
The requested fix is already in place. `lint_and_test.md` "PNG Snapshot Tests"
now states: "Comparison is exact pixel equality locally and in CI; do not treat
CI as a tolerance lane." The bead's 2026-09-18 +1 evidence predates the fix.
Recommend closing the bead without a memory edit. Note 1 of the bead already
flags the path migration (`build_and_run.md` → `lint_and_test.md`); whoever
closes it should confirm which edit landed the exact-equality sentence.

### sase-st — VALID (verified missing)
`xprompts.md` Invoke still documents only "`[[ ... ]]` multi-line text" with no
closing rule and no structural-shorthand binding note. `docs/xprompt.md` (Text
Blocks, per the bead) is the authoritative source to mirror. Small, safe edit.

### sase-ya — VALID gap
No `dispatch.md` exists in `sase/memory/`. The bead's topic list (machine
enrollment/repair, `dispatch:` config + credential store, follow-store/Focus
count semantics, `%dispatch` operation-key recovery, quarantined-host recovery)
names a real undocumented surface if epic sase-xe shipped as described. I did
not independently verify the sase-xe implementation; recommend the assignee
verify each topic against shipped code before writing. Medium scope; new
`type: reference` note.

### sase-yd — VALID, unrecorded invariant
No machine-link-write-lane strand exists in the decisions web (18 strands, none
on this topic). The proposed record is well-formed (claim, rejected
alternatives, cost, reopen condition, implementing-code pointers). Recommend
verifying `src/sase/sdd/_artifact_link_machine_store.py` and the
`project.primary_sidecar_link_dirt` doctor check still match the claim text at
write time.

### sase-12x — VALID (verified stale)
`tui_screenshot.md` Troubleshooting still says "Missing visual extra: install
the project visual dependencies". If `resvg_py` is now an unconditional runtime
dependency as the bead states, this line misdirects agents. Coordinate with
sase-16r (same file, adjacent section).

### sase-134 — VALID but BLOCKED
`xprompts.md` directive table has `%queue` but no `%hold` row — the gap is real.
However, the bead itself says to perform the update after sase-11l completes,
and sase-11l was not observed complete in this audit. Recommend holding the
bead until the implementation lands, then documenting only shipped semantics
plus the decisions strand (pull model, fail-open TTL, family-scoped release).

### sase-148 — VALID (verified stale, scope grew)
`tools/AGENTS.md:66` (plus hardlinked shims) still ends with "remain labeled
phase-pending unless `--live` is passed". Two +1 corroborations confirm, and
the second notes new hand-off case groups (`dod-14-handoff-*`,
`dod-14-live-handoff-*`) the paragraph also omits. Note: this target is
directory-scoped agent instructions, not canonical `sase/memory/` — no
`sase memory init` regeneration; edit the file and its hardlinked shims
directly.

### sase-16r — VALID (verified missing)
Neither `lint_and_test.md` nor `tui_screenshot.md` mentions update-mode
`partial` status, the WARNING block / manifest `skipped` list, `-n`
translation, the maintenance lock, or strict `--check`. `docs/development.md`
(≈lines 970–1013) and the Justfile document all of it, so the memory notes are
genuinely behind their sources of truth. Coordinate with sase-12x (same file)
and sase-18h/sase-sl history (same PNG section).

### sase-18a — VALID (verified unrecorded)
`decisions:record-before-admit` still claims "recording stays fail-open" with
only a `guarded-recipes` partial-supersession mark. The E2 fail-closed
` sase tool run -H` carve-out (foreground stays fail-open, monitor-start
reservation stays fail-open) has no strand. The bead correctly proposes the
immutable-record convention: new strand + `superseded-in-part` mark and
`[[...]]` back-link on the old record, never rewriting the accepted body.

### sase-18h — VALID (verified missing)
The Justfile already documents the exclusion ("The `toobig` line-count gate is
deliberately not a `check`/`check-full` stage", "every whole-repo lint gate
except `toobig`"), but `lint_and_test.md` still presents `just check` as
"whole-repo lint gates + diff-scoped test lane" and lists `toobig` under
`just lint` with no exclusion note. Two-sentence fix in the recipe block.

### sase-195 — VALID (verified wrong + reference implementation exists)
`tui_perf.md` rule 12 still prescribes a `finally:`-cleared guard flag.
`src/sase/ace/tui/command_line/popup.py` confirms the replacement exists
(`_pending_echoes`, `user_highlight_index`, `_set_highlight`). Rewrite rule 12
around pending-echo counts / option-identity checks; drop the `call_later`
wording unless a genuinely synchronous widget needs it.

### sase-xs / sase-xt / sase-xu — NO MEMORY EDIT (correctly classified)
All three are Bryan-authorized operational message boards (athena supervision
epochs 00a/00b/016) with explicit "Path: N/A … no memory file" and "keep open,
never ready" instructions. They are shaped as `memory` tasks only as a vehicle.
Recommend leaving them open until their supervision chains terminate, then
retaining the terminal notes as evidence for/against a dedicated message-board
bead type. That follow-up (if any) belongs in a feature bead, not in this
audit.

## Recommended set of memory file changes

Ordered to minimize edit collisions; each item needs explicit user permission
at write time plus `sase memory init` (except item 8):

1. **Glossary** (`sase/sase.yml` → `glossary.md`): reword "Proc Shell" for both
   agent-owned and stand-alone `xprompt-proc` shells (sase-sa).
2. **`xprompts.md` Invoke**: add the `[[ ... ]]` closing rule + structural
   shorthand binding (sase-st). Fold in the `%hold` row + proc-queue semantics
   only after sase-11l lands (sase-134).
3. **`lint_and_test.md`**: (a) toobig-skip sentence in the recipe block
   (sase-18h); (b) partial-success update contract in "PNG Snapshot Tests"
   (sase-16r). One edit, two beads — do together.
4. **`tui_screenshot.md`**: (a) resvg runtime-dependency Troubleshooting rewrite
   (sase-12x); (b) partial-success contract in "Golden Maintenance" (sase-16r).
   One edit, two beads — do together.
5. **`tui_perf.md` rule 12**: pending-echo/identity-check rewrite citing
   `CommandLinePopup` (sase-195).
6. **New `dispatch.md`** (`type: reference`): remote-dispatch operations
   (sase-ya), verified against shipped code at write time.
7. **Decisions web**: (a) machine-link-write-lane strand (sase-yd);
   (b) fail-closed `-H` strand + `superseded-in-part` mark and back-link on
   `record-before-admit` (sase-18a). Independent strands; one review pass.
8. **`tools/AGENTS.md` + hardlinked shims** (not canonical memory): ToolRun
   smokes rewrite — `not-run` labels, the three live cases, plus the hand-off
   case group (sase-148).
9. **Close sase-sl** with no edit (fix already landed); confirm landing commit
   while closing.

## Risks and notes

- sase-ya and sase-yd recommendations rest partly on bead-supplied
  implementation claims I did not re-verify end to end; each write should
  re-check its cited source files first.
- sase-134 must wait for the sase-11l landing; writing hold semantics early
  risks documenting unshipped behavior.
- Three beads converge on two files (`lint_and_test.md`: 18h + 16r, sl closed;
  `tui_screenshot.md`: 12x + 16r) — batch those edits to avoid conflicts.
- I deliberately did not open, read, or infer from any peer swarm report
  (`__cld`, `__grk`, `__gem`); convergences with those reports, if any, are
  independent.
