# Rename `%proc` to `%tool` and extend it for `sase tool`: research

**Researcher mus · 2026-09-25 · sase master (workspace sase_21) · core pin per `sase-core-revision.txt`**
**Input:** request to rename the `%proc` prompt directive to `%tool` plus unspecified
feature additions to better support `sase tool`; context from
`research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` (consolidated report,
2026-09-17) and the live tree.
**Method:** independent investigation of the directive implementation, the `sase tool`
implementation, and the seams a rename would touch. No peer swarm report was consulted.

---

## 1. Summary

Renaming `%proc` to `%tool` is directionally right but, stated as a pure rename, it is
the wrong unit of work. The two names describe **different executors**, not two
spellings of one thing:

- `%proc` today authors a **raw process unit** (inline bash/python body) dispatched
  straight to the durable **proc supervisor** (`proc-shell`, origin `xprompt-proc`).
  It deliberately bypasses the ToolRun ledger.
- `sase tool run` executes a **catalog tool or ad-hoc argv** through the **ToolRun
  executor**, which mints the durable machine-local ToolRun record (fingerprints,
  stage timeline, retention, receipts/triage later).

A rename that keeps the old executor gains nothing and buys a vocabulary collision
with three existing meanings of "tool" (§3). A rename that also switches executors is
not a rename at all — it is a **directive-to-ledger integration**, and should be
planned, sequenced, and accepted as one.

**Recommendation (detail in §7): do not do a flag-day rename. Add `%tool` alongside
`%proc` as the catalog-first directive routed through the ToolRun executor, desugar
`%proc` bodies to ad-hoc ToolRuns so there is one recording path, then retire `%proc`
as a deprecated alias on the established `%name`→`%id` migration-error precedent —
after `sase-s7` (`typed_launch_units` retirement) lands, not before.**

---

## 2. What `%proc` is today (verified on this tree)

- **Status:** beta behind the `typed_launch_units` flag (`src/sase/feature_flags/registry.py`;
  retirement bead `sase-s7`, currently OPEN). With the flag off, explicit `%proc` is
  rejected with an enable-flag instruction, hidden from completion, never forwarded to
  a model. The shipping epic `sase-s6` is IN_PROGRESS with all 8 phases CLOSED (i.e.
  built, landing/rollout outstanding) — so `%proc` is young, documented, and has a
  small user base. That makes now the cheapest moment for a spelling change, if one is
  wanted.
- **Forms** (`docs/xprompt.md`, `src/sase/xprompt/_directive_collect.py`,
  `_directive_extract.py`):
  `%proc("just check")`, `%proc(bash=...|python=...)` with `timeout=`,
  `idle_timeout=`, `cwd=`, `workspace=`, `label=`, and the fenced form
  `%proc(opts...)::` + one bash/python fence. Exactly one `%proc` and one script
  `%if::` per launch unit; bodies are opaque (no `%`/`#`/Jinja/`$()` expansion).
- **Planning:** each fanout slot is one launch unit; a slot with `%proc` becomes a
  process unit and cannot carry agent prompt prose. `%id:<name>` becomes the proc's
  `shell_name`; the canonical proc id is store-allocated.
- **Execution** (`src/sase/agent/launch_proc_runtime.py`): the admission coordinator
  reserves a `proc-shell` (origin `xprompt-proc`), starts the detached supervisor,
  which acquires an operational-lease workspace when `workspace=true`, materializes a
  private `0600` script, execs by argv (`/bin/bash --noprofile --norc <script>` or
  the SASE interpreter — never shell interpolation), and settles through the resumable
  path. Timeouts run from child start, not from wait/lease time. A standalone `%proc`
  unit **never allocates an agent runner slot, session, `done.json`, or finalizer**.
- **Gating preserved:** `%if::` predicates, `%wait` (including `%wait(proc=)`),
  `%queue` capacity *check* (not a claim; dispatched procs hold no runner capacity),
  `%hold`, `%dispatch` machine targets, `%clan`/`%id` identity binding all compose
  with `%proc` units.
- **Contract ownership:** parsing/classification lives in the Rust core binding
  (`sase_core_rs`: `xprompt_proc_origin`, `proc_dispatch_wire_schema_version`,
  `ProcUnitWire` via `src/sase/core/agent_launch_facade.py` /
  `agent_launch_wire*.py`). Per the Rust-core boundary rule, any directive change
  starts in sase-core, then the pin (`sase-core-revision.txt`), bindings, Python
  callers, LSP/TUI completion, docs, and tests — in that order.

## 3. What `sase tool` is today (verified on this tree)

- **Catalog** (`src/sase/config/tools.py`, `sase/sase.yml` `tools:`): project-layer
  only, complete entries, normalized through Rust. Entry shape: `argv` array (no
  implicit shell), `description`, `stages: run_silent`, `inputs` (files), `env`,
  `args: deny|allow`, `fingerprint.toolchain`. Live entries: `check`, `check-full`,
  `install`, `test`, `test-visual`. Ad-hoc runs require `sase tool run -- ARGV...`
  and are recorded but receipt-less (roadmap E1/E4 distinction).
- **CLI** (`src/sase/main/parser_tool.py`, `tool_handler.py`,
  `src/sase/tool/`): `list` (LAST + TYPICAL, em dash for missing samples),
  `run` (`-q/-v/-T`, `-H` hand-off, `-k/-x` stage controls for `run_silent` tools),
  `runs`, `show` (`-j/-l/-F`), `stop`, `wait`, plus hidden `_adopt` for the handoff
  claim path. Exit codes: 0 accepted, 1 not started, 2 usage/refusal.
- **Ledger:** one semantic run = one ToolRun id with explicit attempt chains; one
  process owner (inline child, monitor in-agent, plain durable proc standalone);
  link stored **tool-side only** (`monitor_id`/`proc_id` on the ToolRun — the roadmap's
  §3.2 rule, so `sase-11y`'s proc-wire work is not disturbed). Retention ~180/60/14
  days; `sase disk` ownership. Recording is fail-open; admission (E7) is fail-closed.
- **Vocabulary load on "tool" (caution):** the word already means (a) provider LLM
  tool calls (recently moved to **LLM Calls** precisely to free the word — roadmap
  §2.7, now `ace/tui/llm_calls/` + `tool_calls.jsonl` writer), (b) Tool Catalog
  entries, (c) ToolRuns. `%tool` would add a fourth, prompt-authoring sense. That is
  survivable only if `%tool` *means* "(b) executed with (c)'s recording" — i.e. the
  directive is defined as the catalog's prompt surface, not as a synonym for "a
  process".

## 4. What "add some features to better support `sase tool`" has to mean

The request leaves the feature list open. From the tree, the minimum coherent set for
a catalog-first directive is:

1. **Catalog reference:** `%tool(check)`, `%tool(test -- <extra>)` honoring the
   entry's `args:` policy (extras appended only when allowed); unknown names are hard
   errors listing catalog names.
2. **Ad-hoc form:** `%tool::` fence or `%tool(-- ...)` mapping to `sase tool run --
   ARGV...` semantics (recorded, receipt-less) — this is the natural new home of
   today's raw `%proc` bodies.
3. **Execution controls:** hand-off (`-H` equivalent: monitor leg in-agent, plain
   visible proc standalone — never the `service` marker, per the roadmap), stage
   controls (`-k/-x`), tail lines, label/shell-name, `cwd`/`workspace`, timeouts,
   `%queue` check passthrough.
4. **Ledger integration:** the unit mints a ToolRun *before* dispatch (record-first
   invariant), inherits fingerprints/inputs/toolchain capture from the catalog entry,
   emits the run id in coordinator output (`journal.jsonl`/`receipt.json`), and stays
   `show -F`/`wait`/`stop`-able through the existing facades.
5. **Unchanged composition:** `%if::`, `%wait` (agent/unit/proc/bead/hood/time),
   `%hold`, `%dispatch`, `%queue`, `%id` shell naming keep their semantics; the
   ToolRun link stays tool-side only.

Anything beyond this (receipts E4, triage E3, forecasts E6, admission E7) comes free
*by routing through the executor* — the directive must not reimplement any of it.

## 5. Critique: is the rename a good idea?

**The instinct is good; the framing is risky.**

For:

- `%proc` names the *mechanism* (proc supervisor); users think in *tools* (`check`,
  `test`). A catalog-first directive is more discoverable and teaches one path from
  prompt to ledger to TUI.
- Timing is unusually cheap: beta-flagged, small corpus, precedent for renames with
  migration errors (`%name`→`%id`, `%tribe` removal, `%time` removal all live in
  `_DEPRECATED_DIRECTIVE_MESSAGES`).
- The roadmap already wants prompt-initiated work recorded (E1 "record everything
  from day one"); prompt-authored procs that bypass the ledger are a hole in that
  corpus (load samples, fingerprints, durations E6/E7 will need).

Against / risks:

- **It is not a rename.** Switching the executor from proc-supervisor-direct to
  ToolRun-executor changes recording, retention, identity, stop/kill routing, output
  modes, and TUI visibility. Reviewers accepting a "rename" will under-scrutinize an
  executor migration. Name it honestly: a directive-to-ledger integration.
- **Collision without definition.** Bare `%tool` next to `sase tool`, Tool Catalog,
  ToolRun, and residual `tool_calls.jsonl` needs one crisp glossary sentence or every
  plan and strand inherits the ambiguity the LLM-Calls rename just removed.
- **Seam count is large for a "rename":** Rust directive contract + completion rows,
  Python parser/collect/extract/scan, `PromptDirectives.proc_code/proc_options`
  fields, launch admission planner + proc runtime vs tool executor + adopt path,
  `%wait(proc=)` resolution, `xprompt-proc` origin string, proc-shell TUI section +
  prompt-widget + LSP snippet recipes, `test_xprompt_directive_completion_parity`
  parity tests, `docs/xprompt.md` + directive matrix + glossary (`proc`, `proc-shell`,
  `tool-catalog`, `tool-run`) + `sase/sase.yml` docs. Missing any one breaks parity
  tests or authoring surfaces.
- **In-flight conflicts:** `sase-s7` owns the flag's removal; `sase-11y` owns nearby
  proc-wire/config/TUI seams; `sase-124`/TUI freshness constrains new surfaces;
  `sase-s6` itself is not fully landed. A rename mid-landing multiplies
  merge/ratcher risk (the roadmap's measured top driver of remediation chains).
- **No evidence of user demand in the request:** no cited confusion, no corpus of
  mis-authored `%proc`s, no adoption metric. The E1 adoption/bypass metric would be
  the natural place to justify this.

**Would I take a different approach?** Yes, in sequence if not in destination: keep
the destination (one catalog-first spelling) but arrive via **addition then
retirement**, and consider seriously whether the end state keeps *both* spellings
permanently with distinct meanings (raw-body `%proc` vs catalog `%tool`). The
deciding question is whether ad-hoc bodies deserve a catalog-independent spelling;
§7 picks the unification (ad-hoc `%tool` replaces raw `%proc`) because the ledger
already records ad-hoc runs and one recording path beats two.

## 6. Options considered

| # | Option | Sketch | Pros | Cons |
| - | ------ | ------ | ---- | ---- |
| A | Flag-day rename | `%proc` → `%tool`, same executor, compat shim or hard break | Smallest diff; cheap while beta | Gains zero ledger integration; pure churn across Rust/Python/LSP/TUI/docs; collides with "tool" without defining it |
| B | **Additive then retire (recommended)** | New `%tool` (catalog + ad-hoc, ToolRun-routed) beside `%proc`; `%proc` desugars to ad-hoc `%tool`; `%proc` becomes migration-error alias after `sase-s7` | No breakage during landing; each phase independently verifiable; one recording path at the end; follows `%name`→`%id` precedent | Two spellings coexist for ~1 release; slightly more docs |
| C | Keyword, no new directive | `%proc(tool=check)` / `%proc(tool="test -- ...")` | Zero new directive name; smallest contract delta | Directive name still says mechanism, not catalog; `tool=` vs body-positional ambiguity; completion rows get convoluted; doesn't fix discoverability |
| D | Permanent siblings | `%proc` = raw proc units forever; `%tool` = catalog refs forever | Each spelling honest about its executor | Two recording paths forever (ledger hole persists); users must learn when recording happens; corpus stays split for E6/E7 |

Rejected: routing `%tool` through oneshot *service* procs (roadmap §3.2 forbids —
service rows are hidden; tool procs must stay visible); adding a `tool` field to the
proc wire (link lives tool-side only); auto-creating beads/receipts from the
directive (E3/E4 own those; the directive only records).

## 7. Recommended solution

**B: additive `%tool`, single ToolRun recording path, `%proc` retired as an alias.**

1. **Vocabulary first (small task, before code):** via `/sase_memory_write`, one
   glossary sentence — *"`%tool` is the prompt-surface spelling of a Tool Catalog
   entry (or ad-hoc argv) executed as one ToolRun"* — and touch-ups to the
   `tool-catalog` / `tool-run` / `proc-shell` strands. Stay out of `src/sase/axe/**`.
2. **Contract (sase-core first):** add the `%tool` directive form to the Rust
   directive contract (name, catalog-ref vs ad-hoc-body vs fence shapes, keywords:
   `timeout=`, `idle_timeout=`, `cwd=`, `workspace=`, `label=`, plus catalog
   `args` passthrough), bindings, and the `sase-core-revision.txt` floor ratchet
   inside the epic that needs it. Python parser/collect/extract/scan,
   `PromptDirectives.tool_code/tool_options` (names TBD), planner, and the
   ToolRun-routed dispatch follow. `%wait(proc=)` and the `xprompt-proc` origin
   semantics are untouched.
3. **Executor (the point of the work):** `%tool` units dispatch through the ToolRun
   executor (`execute_tool_run` / adopt path), not the raw proc runtime: catalog
   entries run at the project root with their inputs/toolchain fingerprint; ad-hoc
   bodies use invocation-cwd semantics; `-H` reuses the existing handoff (monitor
   in-agent, plain visible proc standalone). No new supervisor, no new store, no new
   queue, no new notification path — facades over owners, per the roadmap's "zero
   new supervisors" invariant.
4. **Authoring surfaces in the same epic:** LSP + prompt-widget completion rows
   (gated on `typed_launch_units` until `sase-s7` retires it), parity tests, and
   `docs/xprompt.md` (directive table + matrix + typed-units section) updated
   together — parity tests fail otherwise.
5. **Migration (after `sase-s7`):** `%proc` becomes a deprecated spelling that
   desugars to ad-hoc `%tool` with a targeted migration message (extend
   `_DEPRECATED_DIRECTIVE_MESSAGES`, mirroring `%name`/`%tribe`); removal deletes the
   old branch only. `%proc(...)` with a catalog-looking name should suggest the
   `%tool` form in the error.
6. **Acceptance (green-master-independent, per roadmap D7):** authoring `%tool(check)`
   in a prompt produces a listed ToolRun (`runs`/`show` reprint it); ad-hoc
   `%tool::` fence records without receipts; `-H` variant is followable/stoppable;
   `%proc("...")` still works pre-retirement and warns post-retirement; parity +
   contract tests pass; no `check-full`-green requirement.

**Sequencing:** after `sase-s6` lands and clear of concurrent `sase-11y` proc-wire
edits; the E1 corpus work should already be recording so `%tool` runs contribute
from day one. Do not bundle E3/E4/E6/E7 behavior into this change — routing through
the executor is what makes those epics apply to prompt-initiated work automatically.

**Sizing:** medium epic (~5–6 phases): vocabulary + contract, executor routing,
authoring/parity, docs/glossary, migration + retirement. One beta flag only
(`typed_launch_units`, already open — no new flag), removed before landing per
`sase_flags`.

## 8. Open questions for the lead

1. Confirm `%tool(check)` honoring `args: deny` (extras rejected) vs `allow` is the
   intended UX, and that ad-hoc `%tool` stays receipt-less like CLI ad-hoc runs.
2. Confirm the `-H` default for `%tool` units: foreground like `sase tool run`, or
   handed off like today's detached `%proc` dispatch? (Either is implementable; the
   default is a product call.)
3. Confirm permanent retirement of `%proc` vs permanent siblings (option D) — the
   recommendation unifies, but D is defensible if raw units must never touch the
   ledger.
4. Confirm this waits for `sase-s6` landing + `sase-s7` retirement rather than
   landing concurrently.

## 9. Sources checked

- `docs/xprompt.md` (directive table, completion matrix, typed-launch-units section)
- `src/sase/xprompt/_directive_types.py`, `_directive_collect.py`,
  `_directive_extract.py`, `_directive_scan.py`, `code_value.py`, `processor.py`
- `src/sase/agent/launch_proc_runtime.py`, `src/sase/core/agent_launch_facade.py`,
  `agent_launch_wire*.py`, `src/sase/feature_flags/registry.py`
- `src/sase/main/parser_tool.py`, `tool_handler.py`, `src/sase/config/tools.py`,
  `src/sase/tool/` (executor, adopt, handoff, control, query), `sase/sase.yml`
  (`tools:`), `sase tool list` live output
- `research:202609/sase_tool_epic_roadmap/sase_tool_epic_roadmap.md` §§1–8
- Glossary strands `proc`, `proc-shell`, `tool-run`, `tool-catalog`, `llm-calls`;
  beads `sase-s6` (all phases CLOSED, epic IN_PROGRESS), `sase-s7` (OPEN) via
  `sase bead read` with stated reasons
