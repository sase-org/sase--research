# Dynamic Memory-Built Instructions: How to Split the Work (If at All)

**Researcher:** mus · **Date:** 2026-10-05 · **Swarm:** epic-split decision
**Question:** migrate all existing agent instruction files to per-launch,
memory-rendered instruction bundles, and decide how to split that work into epics
with clear exit criteria and verifiable results — or justify not splitting it.

## Bottom line

**Split the work, but split by capability layer, not by provider and not by report
section.** I recommend **six sequenced epics** (E1–E6 below), each independently
shippable, each with a per-provider flag where it changes runtime behavior, and with
**three legitimate stopping points** (after E1, after E3, after E5). Do not create one
epic per provider, one epic per prior-report phase, or a single big-bang epic. The
reasons are structural: the failure modes are per-invocation delivery bugs that only a
shared renderer plus per-adapter envelopes can fix together, while the highest-cost
pieces (audiences in Rust, the TUI ledger deck, the home-layer cross-repo move) are
severable and must not gate the bug fixes.

Prior research reviewed (audited reads, shared input material):

- `research:202610/sase_md_instruction_delivery/sase_md_instruction_delivery.md`
  (consolidated SASE.md / bundle report)
- `research:202610/instruction_bundles_provider_parity_and_memory_ledger.md`
  (parity matrix + receipt/ledger + TUI design)
- `research:202610/fresh_clone_bootstrap_and_native_subagent_instructions/fresh_clone_bootstrap_and_native_subagent_instructions.md`
  (export stub + two-slot subagent delivery)

I agree with the core architecture in all three: layered memory stays the content
store; an optional `SASE.md` composition spec declares layout, not prose; audiences
come from closed launch facts first with no `%tag`; delivery is per-invocation through
each adapter's explicit channel with exactly-once conformance; generated full files
stop being committed. The issues I found (§2) change epic boundaries and exit criteria,
not that direction.

## 1. Method and independent verification

I read the three consolidated reports above via `sase artifact read` (audited) and
checked the load-bearing claims against this checkout (`sase_17`) rather than trusting
report text:

- `AGENTS.md` / `CLAUDE.md` are 285-line identical renders; `sase/memory/sase.md`
  exists as a `type: core` note — so the `SASE.md` vs `sase/memory/sase.md` name
  collision the first report flags is real and must be retired before any spec work.
- `src/sase/llm_provider/codex.py` already builds a per-run shadow `CODEX_HOME`
  (line ~225) — the Codex envelope has a natural home; the bundle replaces a symlink
  payload, not a new mechanism.
- `src/sase/llm_provider/muse_provider.py` passes `--trust-workspace` and
  `--no-foreign-personal-context` today — the Muse delivery change is a flag-level
  edit plus prefix composition, small and independently flaggable.
- `src/sase/llm_provider/_invoke.py:101` (`invoke_agent`) is the single render point
  the reports assume; finalizer follow-ups call `provider.invoke` directly, so any
  "render at invoke" epic must cover both call sites or it leaks stale renders.
- `src/sase/amd/` (generator) and `src/sase/memory/` (renderer, read log) exist as
  separate Python surfaces — a renderer epic has a real seam to build on without
  touching adapters first.

I did not open any `__cdx/__cld/__grk/__gem` report from this swarm.

## 2. Issues in the prior recommendations that change the split

These are genuine corrections or scoping risks, not stylistic nits. Each one moves an
exit criterion or an epic boundary in §4.

1. **R7's stated rationale is now wrong, but R7 itself still holds for a different
   reason.** The first report's "decisive fact" (Codex cannot suppress a present
   project `AGENTS.md`) was falsified: `project_doc_max_bytes=0` does suppress it
   (re-verified by the fresh-clone lead with `codex debug prompt-input`). The amended
   R7 keeps untracking on churn/audience grounds. Epic consequence: E5's exit criteria
   must not cite "Codex can't suppress" — cite instead the budgeted-stub size, the
   complement-mode deletion, and `git status` cleanliness, all directly checkable.
2. **File-writing fallbacks are dead for Grok, not merely disfavored.** Grok skips
   gitignored files and untrusted project rules; only `$GROK_HOME` rules and
   `extra_rule_dirs` ignore trust. Any epic that proposes "write the bundle into the
   workspace as fallback" for Grok will silently deliver nothing. E3 must define
   Grok as explicit-channel-or-nothing (`--rules`, stay untrusted, never `--trust`)
   and record its subagent slot as `none` until the shadow-home spike resolves.
3. **The Claude subagent channel is hidden from `--help` and version-sensitive.**
   `--append-subagent-system-prompt-file` parses but does not appear in 2.1.289
   `--help`. Any Claude delivery epic must pin the verified version in its exit
   criteria and name the fallback (`--agents` definitions) as an explicit branch,
   not a footnote — otherwise the epic can "pass" on a version where the flag is
   silently ignored.
4. **System-prompt vs user-message moves change compliance, not just plumbing.**
   Claude moves from user-message attachment to system prompt; Muse/agy stay in the
   user message. The reports note this but under-weight it in phasing. E3 must carry
   a behavioral metric (`/sase_final` compliance, trigger-read rate) per provider,
   with a per-provider rollback criterion — otherwise a channel regression looks like
   a clean delivery (`✓1×` with worse adherence).
5. **`mode: export` vs launch-fact `mode` needs one namespace decision up front.**
   The fresh-clone report uses `mode: {sase, interactive, export}` as a launch fact
   and also as a render variant. If `export` is both a fact value and a command
   (`sase instructions export`), E2 must freeze that vocabulary in the schema before
   E5's stub work starts, or `render --as` previews and stub CI checks will drift.
6. **Complement mode is a correctness trap if it outlives its epic.** Codex
   "bundle-minus-what-the-native-file-carries" requires the renderer to know the
   tracked file's content hash at render time. If E3's complement mode persists after
   E5 untracks the files, every render pays for a dead code path and risks
   under-delivery. E5's exit criteria must include deleting complement mode, not just
   untracking files.
7. **The TUI MEMORY deck + Rust `ledger_view` is the largest cost and the least
   urgent correctness work.** It is also the only piece that forces the
   `sase-core` boundary (schema/evaluator/ledger join in Rust, composition in
   Python). Bundling it with the renderer or delivery epics guarantees the bug fixes
   wait on the slowest review loop (Rust pin + LSP + TUI). It must be last (E6) and
   severable: E1–E5 are complete and valuable with only CLI conformance.
8. **The home-layer move crosses a repo boundary.** Home `~/AGENTS.md`/`~/CLAUDE.md`
   are chezmoi-managed; the change lands in the `chezmoi` repo via `/sase_repo`, not
   in this checkout. An epic that mixes "untrack project files" with "migrate home
   files" cannot have one `just check` gate. E5 must separate the project-stub gate
   (this repo) from the home-migration gate (chezmoi repo + target-host matrix).
9. **agy/Qwen/OpenCode conformance is unverifiable by construction.** agy
   trajectories do not record rules; Qwen/OpenCode channels are prompt prefixes. The
   parity report correctly proposes `◌ unverifiable`, but epic exit criteria must
   then forbid claiming `✓` for these providers — their gate is "receipt written +
   no native SASE file loads," never "bundle observed once."
10. **Budgets need a measured baseline before they become gates.** The router ratchet
    (≤100 lines / ≤1,600 tokens project layer, per audience) is cited as a matrix
    gate, but no epic measures today's per-audience totals first. E2 must record the
    baseline numbers as artifacts; E6's `--matrix` gate is vacuous without them.

## 3. Should this be split at all?

**Yes — but into few, ordered, capability-layered epics, not many small ones.**

For splitting:

- **Independent rollback requires it.** Each provider's delivery switch can regress
  compliance (§2.4). Per-provider flags inside one delivery epic (E3) give four
  independent rollbacks; a big-bang switch gives one flag day with correlated risk.
- **Early signal compounds.** E1 (observed-mode receipts + `sase doctor
  instructions`) makes today's duplicate/empty deliveries visible *before* any
  behavior change. That display is what de-risks E3 and what proves E5.
- **Two pieces are genuinely independent.** The Claude subagent guard (E4) and the
  fresh-clone stub/sync (E5) touch different code paths (adapter flags vs
  export/sync CLI) and different repos (this repo vs chezmoi). Serializing them
  wastes calendar time; parallelizing them is safe if E2's schema lands first.
- **Review loops differ by an order of magnitude.** Python adapter edits review in
  days; `sase-core` schema + LSP + TUI deck review takes weeks (pin move, editor
  metadata, widget tests). Gating bug fixes on the slow loop is pure cost.

Against splitting (and how I contain each risk):

- **Over-splitting into per-provider epics** multiplies flag-combination states and
  one-provider-only knowledge. Containment: one delivery epic (E3) with per-provider
  flags and a shared conformance gate, not four epics.
- **Splitting renderer from delivery** can produce a renderer nobody calls. 
  Containment: E2's exit criteria require live dual-write (today's files *plus*
  receipt/bundle artifacts on every invocation) without switching any envelope —
  the renderer is exercised in production from day one.
- **Splitting audiences from the `when:` evaluator** can strand `SASE.md` parsing
  with no consumer. Containment: E2 ships the frozen launch-fact vocabulary and the
  `when:` schema with zero conditional sections active; E6 only adds sections.
  The schema epic is verifiable (`render --matrix` over the fact space) without any
  audience content.

The failure mode I most want to avoid is **five epics that are really one epic with
four status meetings**: renderer-without-provenance, delivery-without-conformance,
stub-without-sync, audiences-without-budgets. Every epic below owns its observable
proof (§4); anything that cannot name its proof is not an epic.

## 4. Recommended epics

Ordering: E1 → E2 → (E3, E4 in parallel behind flags) → E5 → E6. E2's frozen
fact/`mode` vocabulary is the only hard predecessor for E3–E5. Stopping points: after
E1 (visibility with no behavior change), after E3 (bugs fixed, files still committed),
after E5 (migration complete; E6 is optional polish + audiences).

### E1 — Observed-mode receipts + `sase doctor instructions` (days, no behavior change)

**Scope.** Build the receipt shape and the conformance readers against *today's*
file-based delivery. Map the launched `AGENTS.md` into sections, parse each
provider's session record (Claude transcript attachments, Codex rollout
`<INSTRUCTIONS>`/`--- project-doc ---`, Grok `prompt_context.json`
`agents_md_files`, Muse `session.jsonl` prefix), and report copies per provider.
Add the bug beads the reports already justify (Grok zero-load, Claude/Codex
double-load with conflicting repo lists, Muse/agy missing home layer). No renderer,
no flag flips, no file untracking.

**Exit criteria (all checkable by the lead in one session).**

1. `sase doctor instructions` on a recent week of runs prints per-provider copy
   counts showing the known bugs: Claude `2×`, Codex `2×`, Grok `0`, Muse missing
   home layer. If it shows `1×` anywhere, the reader is wrong, not the world.
2. `sase instructions show <agent>` prints an observed-mode receipt (sections +
   `observed` block, `intended` marked absent) for at least one run per major
   provider; agy rows show `◌ unverifiable`, never `✓`.
3. `just check` passes; the new parsers have unit tests over checked-in redacted
   fixtures (one transcript/rollout/`prompt_context.json`/`session.jsonl` each).
4. Bug beads exist with the measurements attached; `docs/agent_providers.md`
   "Instruction double-load" section is corrected.

**Verifiable result:** the TUI/CLI can *display* every bug the migration claims to
fix, before fixing any of them. E3's "chips turn green" claim is meaningless without
this baseline.

### E2 — Bundle renderer + provenance + preview (the point of no return for vocabulary)

**Scope.** Python renderer behind a thin seam at `provider.invoke` (both the main
path and both finalizer follow-up paths): package base (retiring
`sase/memory/sase.md` into it — resolving the name collision), plugin hook, home
layer, project layer, launch facts placed last. Content-addressed bundle store,
`instructions.md`/`.json` per invocation, hash in `agent_meta`,
`SASE_INSTRUCTIONS_FILE` export, `sase instructions render --as <agent|facts>` and
`--matrix`, and `sase instructions check` (CI + pre-commit, fail-at-check-time
semantics). **Dual-write:** every invocation writes bundle artifacts *and* today's
files load exactly as today — no envelope changes, so this epic cannot regress any
provider. Freeze the launch-fact vocabulary including `mode: {sase, interactive,
export}`, the `when:` schema with zero active conditional sections, and the per
audience budget baseline (record today's totals as artifacts per §2.10).

**Exit criteria.**

1. `sase instructions render --as provider=codex,role=root` and `--matrix`
   reproduce today's per-provider file bytes as a subset of the bundle (byte-diff
   against launched `AGENTS.md` shows only additions, no silent drops) on a pinned
   checkout.
2. Five consecutive real runs (one per major provider) each carry
   `instructions.md`/`.json` with `bytes`, `tokens`, section ids + blob oids, and a
   `common_digest` identical across providers for the same facts (provider sections
   excluded).
3. `sase instructions check` fails CI on unknown fact keys/values
   (`provider: codx` is an error, not a silent false) and on a missing required slot.
4. Budget baseline artifact exists (per-audience line/token counts); `just check`
   passes; last-known-good fallback + notification path has a test (render failure
   with and without a cached bundle).

**Verifiable result:** `diff <(sase instructions render …) AGENTS.md` is reviewable,
and every agent carries a receipt pointing at exact bytes — while every provider
still behaves exactly as today.

### E3 — Explicit per-provider delivery behind flags (the bug-fix epic)

**Scope.** One epic, one flag per provider, shared conformance gate. Claude:
`--append-system-prompt-file` + `claudeMdExcludes` in the same release (same-release
pairing is load-bearing — explicit delivery without native suppression *is* the
double-load). Codex: shadow-`CODEX_HOME` bundle, complement mode against the still
tracked file, `project_doc_max_bytes=0` set in the same release. Grok: `--rules`,
stay untrusted, never `--trust`. Muse: prompt-prefix composition, drop or keep
`--trust-workspace` per the pre-build spike result. agy/Qwen/OpenCode: prefix/default
hook, `◌` conformance. Every flag flips only with its conformance reader from E1
asserting exactly-once (or the defined `◌`/partial state for agy/Grok-subagent).
Carry the behavioral metric: `/sase_final` compliance and trigger-read rate per
provider for two weeks post-flip, with a written per-provider rollback threshold.

**Exit criteria (per provider, all must hold before its flag defaults on).**

1. `sase doctor instructions` shows `✓1×` (or the defined `◌`/partial) for that
   provider over the trailing 7 days, with zero SASE-owned native loads.
2. Grok final-declaration rate recovers toward the ~60% pre-regression baseline;
   Claude/Codex duplicate-contract tokens (~790/run) are gone from session records.
3. Behavioral metric holds: no provider's `/sase_final` compliance or
   trigger-read rate regresses beyond its threshold; otherwise that provider rolls
   back independently while the others stay on.
4. The Claude subagent-flag version pin and the Muse `--trust-workspace` spike
   outcome are recorded in the epic's test comments (which version, what was
   observed), not just in prose.

**Verifiable result:** per-provider `doctor` output the lead can re-run, plus a
before/after token and compliance table. This is the epic a skeptic re-checks first.

### E4 — Two-slot subagent delivery + root-only enforcement (parallelizable with E3)

**Scope.** Mostly a Claude epic in practice (518 helper runs/30d vs ~0 for
Codex/Muse, 4 for Grok — the usage counts justify scoping the mechanical work to
Claude first). Root + helper renders from one shared core; helper render drops
`/sase_final` and turn obligations; PreToolUse hook keyed on `agent_id` blocks
root-only operations for identified helpers; actor-qualified root-only sentence in
the shared contract (a memory edit via `/sase_memory_write`); `SASE_SUBAGENT_…`
pointer fallback; subagent rows in provenance and conformance. Grok/Codex/Muse child
slots declared honestly (`none`/`inherits-*`) with spikes time-boxed, not blocking.

**Exit criteria.**

1. Claude helper `sase final` invocations go from ~13–15/30d to 0, and
   helper-accepted declarations go to 0, over a full 30-day window (or a
   proportional window the lead accepts in writing — the window is the criterion).
2. Zero helper transcripts contain the root render or a native SASE file; Explore
   direct memory-file reads fall toward the 1.5% target from 11%.
3. `sase doctor instructions` gains subagent rows; `just check` passes.

**Verifiable result:** two counts the lead can recompute from logs, not a design
doc. If the counts do not move, the render split did not work regardless of how
clean the templates look.

### E5 — Untrack generated files + export stub + sync + home migration (two gates)

**Scope.** (a) Project surface, this repo: `sase instructions export` writes the
committed budgeted stub (root `AGENTS.md` + two-line `CLAUDE.md` import shim, no
turn obligations, bootstrap "generate then read" clause), CI `--check`, deletion of
other copies and nested sets, `PROVIDER_SHIM_FILES` update, complement-mode
**deletion** (§2.6), `sase instructions sync` (hermetic, conservative, `--check` /
`--if-stale`, digest header, refuses workspaces), `just agent-instructions` from
`just install`, `tmux-agent` through the delivery hook with `mode: interactive`.
(b) Home surface, chezmoi repo: home files become `mode: interactive` renders.
These are separate gates with separate checkouts — do not merge them into one
"untrack everything" commit.

**Exit criteria.**

1. Project gate: `git status` stays clean across 20 consecutive mixed-provider runs
   (the lead's actual check: run the swarm, then `git status --porcelain` shows no
   instruction files); the tracked stub is ≤15 lines budgeted and never mentions
   `/sase_final`; fresh clone without SASE installed loads the stub under
   `claude`, `codex`, and trusted `grok` and gets build/test guidance with no turn
   obligations (a 3-cell test matrix, recorded).
2. After `just install`, Claude and Codex load the interactive render natively and
   `git status` stays clean; `sync --check` passes in CI.
3. Complement mode is deleted (grep shows no `complement_of` in the renderer), not
   merely unused.
4. Home gate (chezmoi repo): target-host matrix (`%dispatch` self/other) renders
   with the target's own facts; no interactive session is told to finalize a turn
   (the `~/CLAUDE.md` failure the fresh-clone lead found is covered by a test).

**Verifiable result:** the lead's own clone-and-run matrix plus `git status`
cleanliness — the two things a status report cannot fake.

### E6 — Audiences (`when:`, `SASE.md`, sase-core) + ledger/TUI (last, severable)

**Scope.** Only after E5: move the frozen schema/evaluator/spec parsing into
`sase-core` (schema, evaluator, validation; composition stays Python behind the
binding), move the `sase-core-revision.txt` pin, add LSP validation/completion and
TUI preview parity, ship the first measured conditionals (lean monitor/gate,
phase-worker rule, helper render, research-vs-code density, commit-method text),
enforce the router ratchet per audience via `check --matrix`, and build the ledger
join (`intended × observed × pulled`) plus the MEMORY deck / Context-lane / "Seen
by" surfaces. `traits:` labels only when a real section needs a non-fact label
(`corpus-before-mechanism`); prompt escape hatch only after that, through the Rust
directive registry.

**Exit criteria.**

1. `sase instructions check --matrix` renders every reachable audience, asserts hard
   rules + baseline triggers present in each (R9), and enforces budgets; a
   deliberately over-budget fixture fails CI.
2. Receipt→ledger→bundle→pinned-pager chain works from one CLI command and one TUI
   path showing identical states (Rust view shared, Python only renders).
3. First conditionals ship with measured deltas (tokens/run, read rates) and
   flag-gated experiment support; audience sprawl guardrails (closed facts, R9,
   matrix) are documented in the decision record.
4. `just check` **and** the repo's configured full gate pass (this is the only epic
   that touches Rust + TUI + docs + memory together).

**Verifiable result:** a matrix report plus TUI screenshots against pinned receipts.
If E6 slips, E1–E5 still deliver every bug fix; nothing in E6 is load-bearing for
correctness.

## 5. What not to do

- **No per-provider epics.** Four delivery epics quadruplicate the conformance,
  provenance, and rollback logic and invite divergent bundle semantics. One E3 with
  four flags.
- **No "TUI first" ordering.** The ledger deck without receipts (E1) and bundles
  (E2) has nothing to display; building it first produces mockups against imaginary
  data.
- **No monolith `SASE.md` content migration.** Any epic phrased "move all text into
  SASE.md" re-creates the router-solved encyclopedia and bypasses audited reads. The
  content never moves; only layout/conditions are declared.
- **No `%tag` or tribe-as-selector work.** The name is burned (`%t` ≡ `%tribe`,
  legacy `tag` metadata reads as tribe). E2 freezes facts; labels wait for a proven
  need.
- **No committed full `export` projection for real contributors "just in case."**
  The Codex-suppression knob makes it technically possible, but the churn/conflict
  cost is certain while the outside-contributor benefit is hypothetical. Revisit only
  on the stated trigger: real sustained outside contribution.

## 6. Suggested bead/phase structure for the lead

| Epic | Size | Can parallelize with | Stop? |
| --- | --- | --- | --- |
| E1 observed receipts + doctor | S (days) | — | **Yes: visibility only** |
| E2 renderer + provenance + preview | M (1–2 wks) | — (blocks E3–E5 vocabulary) | No |
| E3 per-provider delivery flags | M (1–2 wks + 2-wk metric window) | E4 | **Yes: bugs fixed** |
| E4 subagent two-slot + guard | S–M | E3 | No (or stop if helper counts already 0) |
| E5 stub + sync + home | M (two gates) | E4 after E2 | **Yes: migration done** |
| E6 audiences + ledger/TUI | L (Rust + TUI) | — | Optional polish |

Each epic's "definition of done" is its §4 exit criteria verbatim — paste them into
the bead. The lead's re-verification for E1/E3/E5 is deliberately CLI-shaped
(`sase doctor instructions`, `sase instructions show/render/check`, `git status`,
clone matrix) so confirmation needs no code reading.

*Independence note: conclusions above are my own from the three consolidated reports
plus direct checkout inspection. I did not read this swarm's peer reports.*


