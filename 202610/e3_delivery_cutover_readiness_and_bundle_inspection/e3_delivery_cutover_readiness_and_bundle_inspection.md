# E3 Explicit Delivery Cutover: Are We Ready, and How Do I See an Agent's Instruction Bundle?

> **Research query:** Are we ready to launch agents to implement the E3 epic described in
> `memory_built_instruction_migration_epics.md` in the research sidecar repo? And how can
> I figure out what a given SASE agent's instruction bundle contained, for example for a
> completed agent on the Agents tab?

![Infographic summarizing E3 readiness gates, the plan amendments, and how to inspect an agent's instruction bundle](e3_delivery_cutover_readiness_and_bundle_inspection_infographic.png)

## Bottom line

**The entry gates are met, but there is nothing to launch yet. No E3 plan and no E3
epic bead exist.** The next step is a [planning agent](#recommended-launch-sequence),
not implementation agents. Have it write the E3 plan with the amendments below. Then
approve it and launch the epic. None of the amendments needs more calendar time.

| E3 entry gate | Status | Evidence |
| --- | --- | --- |
| E1 landed, ≥3 days of runs | ✅ 7 days | `sase-1gu` closed 2026-10-06 16:05Z; the Grok fix deployed 2026-10-05 |
| E1 readout acceptable | ✅ (lead's measurement; **never recorded**) | Grok runs ending with no declaration and no handoff fell from **14% to 5%**. Claude helpers: 0 `sase final` attempts, 0 accepted ([E1 readout](#settling-the-e1-readout-disagreement)) |
| E2 parity clean | ✅ | `sase instructions render -p` exits 0, `contract_count=1`; five allowed frame/provider additions |
| E2 shadow render working | ✅ | **804** manifests since Oct 6, all `delivery.status: shadow`, **0** `*.error.json`; all three purposes exercised |
| Warm render within budget | ✅ (one small-sample exception) | Warm p95 is 99–171 ms per provider for ordinary renders. Muse declaration-recovery p95 is 291 ms, from n=5 |

**What the E3 plan must add** (ranked; details in
[What the E3 plan must change](#what-the-e3-plan-must-change)):

1. **[Make the scoreboard trustworthy](#scoreboard-readiness) before provider phases
   rely on it.** It can't see dismissed agents. It blanks every per-section count for
   transcripts over 512 KB. It counts native file sources, so a successful explicit
   delivery would read as zero. It cannot prove "exactly once".
2. **[Replace the exit criterion](#replace-the-historical-re-render-criterion)
   "re-rendering a finished agent reproduces its hash".** `render -a` compiles from
   today's sources, so it is not a history replay.
3. **[Account for provider changes since Oct 5](#provider-facts-that-moved-since-oct-5).**
   Two matter most:
   - **Claude Code 2.1.296 now loads `AGENTS.md`.** Its default `instructionFiles`
     mode falls back to `AGENTS.md` when a project has no `CLAUDE.md`. E3.3 and E4 both
     have to account for this.
   - **Codex multi-agent v2 is active.** Its full-history forks inherit the root
     context.
4. **[Fold in or sequence `sase-11s`](#overlapping-bug-bead).** It rewrites the same
   shadow `CODEX_HOME` code as E3.4.
5. **[Rollback and Rust split](#rollback-and-the-rust-split).** Create new per-provider
   `sunset` flags; the E1/E2 flags were retired on purpose. A failed render or failed
   delivery must restore both legacy delivery and native discovery. Any new manifest
   field is a sase-core change plus a pin move.
6. **[A `decisions:` block](#decisions-to-record-in-the-plan)** covering:
   - home-layer privacy;
   - foreign memory;
   - flag lifetime;
   - Claude's move from user message to system prompt.

**Seeing a bundle:** run `sase agent show NAME`, or press `%` then `d` on the Agents tab
to copy the artifacts dir. Open `<artifacts>/instructions/NN-<provider>.md` (the exact
bytes) and its `.json` manifest. **Until E3 ships, that bundle is shadow-only: no agent
has ever received it.** Agents still load the legacy native files. The Agents tab's
MEMORY lane shows those through the **`AGENTS.md as launched`** row. Full recipe in
[How to see what an instruction bundle looked like](#how-to-see-what-an-instruction-bundle-looked-like).

## Where the migration stands

| Date (2026) | Event | Ref |
| --- | --- | --- |
| Oct 5 | Epics report published (E1–E7) | research `c964178` |
| Oct 5–6 | **E1 landed**: `sase instructions` scoreboard, Grok `--rules` stopgap, Claude helper template + PreToolUse guard, ownership inventory | `sase-1gu` |
| Oct 6 | **E2 landed**: manifest wire in sase-core, Python compiler + cache, shadow render at `invoke_with_instructions`, `render -p` parity, coverage + section diff | `sase-1h3` |
| Oct 7 12:57Z | First shadow manifest on apollo | — |
| Oct 10 | **All flags retired**, including `grok_rules_delivery`, `claude_helper_channel`, `instruction_shadow_render`. Stopgaps and shadow render are now unconditional. The flag beads closed with test evidence only, with no soak readout. | `sase-1jc.10`, `2c9f761210` |
| Oct 13 | No E3 plan in `plans/202610/` and no E3 bead (`sase bead search` for "explicit delivery", "claudeMdExcludes", "auto-memory", `project_doc_max_bytes`, `trust-workspace`: nothing). No source commits touching instruction code since `2c9f761210`. | — |

The live scoreboard (`sase instructions verify --since 7d`) still shows E1's
after-state, which is the state E3 exists to change:

```
provider manifest contract home project directive native-full foreign          helpers
claude   7/7      2×       ✓    ✓       ✓         2×          auto-memory      0 attempts, 0 accepted
codex    25/25    2×       ✓    ✓       ✓         2×          —                0 spawns
muse     12/12    1×       ✗    ✓       ✓         1×          —                —
grok     22/22    1×       ✗    ✓       ✓         0           memory-v2½:False —
agy      2/2      ◌        ✗    ◌       ◌         ◌           —                —
```

`sase doctor -D -C instructions` reports WARN `instructions.delivery`. The cause is the
contract and native-full counts of 2× for Claude and Codex, which is the expected
pre-E3 drift. `instructions.helpers` is OK.

All 804 manifests were rendered on `apollo`, and `sase machine list` reports no remote
machines. So E3.2's "`%dispatch` renders on the target host" rule can only be tested,
not probed live.

## Settling the E1 readout disagreement

The reports disagreed on whether the E1 readout is acceptable:

- cld and grk: Grok's declaration rate rose to **74%** after E1. cld called Codex "the
  outlier at ~38%".
- cdx: found **five** completed Grok runs with `submission_required: true` and no
  accepted submission, and called the gate unsettled.

**Lead's finding: cdx's five cases are legitimate, and the "declared = has
`final_submission.json`" metric used by cld and grk badly undercounts compliance.**
Each of `bob-cli-7c.{1--plan, 2--code, 2--1, 3--code, 3--1}` ended its turn the same
way:

1. `sase final prepare …` (publish prepared host-completion intent);
2. `sase monitor start -p verify … -- just check`.

That is the prepared-declaration verify-monitor handoff. Each chain then ends with an
accepted submission (`7c.1--1`, `7c.2--2`, `7c.3--2`). The member that hands off to a
monitor records `outcome: completed`. That is why outcome-based exclusions don't catch
it.

I reclassified every finished, non-research root run. The categories:

- accepted submission;
- plan handoff;
- monitor handoff, with or without a prepared declaration;
- declaration not required;
- **neither a declaration nor a recognized handoff** (the real misses).

| Provider | Sep 10 – Oct 5 (pre-E1) misses | Oct 6 – Oct 13 (post-E1) misses | Naive "has `final_submission.json`" post-E1 |
| --- | ---: | ---: | ---: |
| Claude | 6/233 (3%) | ≤2/72 (3%) | 12/72 (17%) |
| Codex | 8/236 (3%) | ≤3/123 (2%) | 38/123 (31%) |
| **Grok** | **22/158 (14%)** | **≤4/80 (5%)** | 47/80 (59%) |
| Muse | 40/525 (8%) | ≤22/245 (9%) | 147/245 (60%) |

Codex's low naive rate comes from monitor handoffs: 34 plain plus 2 prepared, out of
123. It is not noncompliance. Research runs accept at 88–100% for every provider.

**Method and caveats.**

- This is a heuristic scan of `tool_calls.jsonl` text, `final_context.json`,
  `final_submission.json`, and `done.json`. No chat transcripts were read.
- Dismissed runs have no `done.json` and are included with an unknown outcome.
- A few "misses" are still running (`bob-cli-7c.8`) or were killed. Treat the post-E1
  column as an upper bound.
- The proposal's original 60% → 26% figures were not reproduced under this method.

**Implications:**

- The E1 readout is acceptable. Grok's miss rate fell by about two-thirds, and the
  Claude helper guard has had nothing to deny. Across 177 helper transcripts (cld), every one
  carries `# SASE Helper Instructions`, and there were zero `sase final` calls.
- **E3's 7-day watch metric must be handoff-aware**, or Codex's ~35% monitor-handoff
  share will swamp any real signal. Muse, at ~9%, is the provider to watch. E3.5
  changes its delivery to a prompt prefix.
- **Attach this table, re-run at plan time, to the E3 plan as the pre-cutover
  baseline.** It also closes the gap left when `sase-1jc` retired the flags without a
  soak note.

Add cld's second watch metric to the baseline: memory reads per run, from
`memory_reads.jsonl` joined to manifest runs, Oct 7–13.

| Provider | Mean audited reads per run | Share of runs with ≥1 read |
| --- | ---: | ---: |
| claude | 1.71 | 70% |
| codex | 1.65 | 89% |
| grok | 1.87 | 93% |
| muse | 0.57 | 35% |
| agy | 1.12 | 69% |

Muse reads memory about a third as often as the others. Muse currently misses the home
layer, so it is where E3 should show the clearest gain.

## What the shadow data says about E2 health

- **Volume:** 804 manifests since Oct 6.
  - Providers: muse 319, codex 193, claude 150, grok 109, agy 33.
  - Purposes: ordinary 732, declaration_recovery 54, conflict_repair 18.
  - Errors: 0.
- **Determinism:** cld counted 56 distinct bundles across 794 manifests.
  - Re-rendering from the agent's own project reproduced the recorded hash for runs by
    cdx, cld, grk, and mus.
  - Bundles are ~20 KB, about 4–5k tokens, with 27 included sections. Layer budget:
    package 5.7 KB, project 13.5 KB, home 246 B, frame 658 B.
  - That is far below Codex's 32 KiB project-doc cap and Grok's 120 KiB argv guard.
    Keep the oversize checks anyway.
- **Latency:**
  - Cache-hit p50 is 59 ms and p95 188 ms.
  - Cache misses (~20%) have p50 0.7 s and p95 2.4 s.
  - E3 adds no latency, because shadow mode already pays this cost. What changes is the
    consequence: after E3, a slow or failed render matters, so the per-invocation
    legacy fallback is load-bearing.
- **The Muse per-purpose coverage rows are a presentation quirk, not a hook gap.** mus
  raised this as a possible gap. `purpose_coverage_rows` uses all of a provider's
  sessions as each purpose's denominator (`coverage_summary.py`, `sessions=len(provider_sessions)`).
  So ordinary sessions show up as "uncovered" for `declaration_recovery` and
  `conflict_repair`. Ordinary coverage is complete. Fix the denominator before E3.6
  makes recovery-route conformance a gate.

## What the E3 plan must change

### Scoreboard readiness

_An E3.0 phase, or the head of E3.1. Priority: high._

E3's exit criteria and its 7-day watch both read `sase instructions verify`. The lead
confirmed these gaps in code or live:

| Gap | Evidence | Fix |
| --- | --- | --- |
| **Dismissed agents are invisible** | `enumerate_runs` uses `listing_snapshot`, which skips hidden or dismissed runs. `verify -a research.10.cld` exits **0** with `runs=0` and no message. `render -a` says "no runs found". `sase agent show` resolves the same agent instantly. cld found 10 Claude runs on the scoreboard against 147 Claude bundles rendered. | Enumerate archived runs (the dismissed-bundle index) or walk the manifests |
| **One large transcript blanks the whole section diff** | `ROOT_TRANSCRIPT_BYTE_CAP = 512 KiB`. When the read is partial, `section_diff_for_session` sets **every** row to 0 and `unavailable`. Instructions sit at the start of the transcript, so the cap rarely hides them. | Count what the prefix shows; reserve `◌` for "not found and truncated" |
| **Headline counters read native sources** | The Claude, Codex, and Muse observers compute contract, home, and project from native files. After the cutover they would report 0 even when explicit delivery worked. | Identify layers by manifest section, per channel |
| **"Contains" is not "exactly once"** | `sum(1 for text in flat_native if flat_body in text)` counts sources that *contain* a section. Two copies inside one source count as 1. | Count occurrences, or embed a bundle-id marker, such as an HTML comment carrying `sha256[:12]`, and count that |
| **No session association** | Matching uses provider plus render time with 5 s skew. The wire's `delivery.session_ids` is `[]` in real manifests, and `channel` and `provider_cli_version` are never set. | Populate these existing optional wire fields at delivery time |

Put this before the provider phases, not in E3.6. Otherwise E3.3–E3.5 cannot prove
their own exit criteria for Claude and Codex. While doing this, pull
`sase instructions show <agent>` forward from E6. It prints the recorded bundle and
manifest for any agent, archived ones included. It is cheap, and the soak needs it.

### Replace the historical re-render criterion

_Priority: high._

The epic's exit criterion "re-rendering a finished agent reproduces its manifest hash"
asks for something `render -a` doesn't do. It takes the agent's **facts** and compiles
**today's** project and home sources from the **current** checkout. When nothing has
changed, the hash matches. Run from another project, it reported 15 changed sections
(cld). Replace the criterion with two checks:

1. **Archived bytes:** the stored `.md` matches the manifest's `bundle.sha256`.
2. **Determinism:** identical inputs produce identical bytes. This is already tested.

True historical recompilation would need retained input versions and the matching
compiler. That is new scope, not something the current command provides.

### Provider facts that moved since Oct 5

_Priority: high for Claude and Codex._

| CLI | Oct 5 → now | E3 impact |
| --- | --- | --- |
| **Claude Code** | 2.1.289 → **2.1.296** | **New `instructionFiles` setting** (lead, from binary strings; older key `projectInstructions`). See the note below the table. `claudeMdExcludes`, `autoMemoryEnabled`, and `CLAUDE_CODE_DISABLE_AUTO_MEMORY` are all present. `--append-subagent-system-prompt-file` is still hidden from `--help`. |
| **Codex** | 0.160.1 → **0.162.1** | cdx and cld both re-probed offline with `codex debug prompt-input`. With `-c project_doc_max_bytes=0`, the project doc disappears while `$CODEX_HOME/AGENTS.md` and `developer_instructions` still load. **E3.4's split still works.** However, every recent rollout carries `<multi_agent_mode>`/`<multi_agent_role>` (**multi-agent v2**), and its full-history forks (`fork_turns` omitted or `"all"`) inherit the parent context, including the root bundle and Final Declaration contract. The plan assumed v1. |
| **Grok** | 1.0.46 → **1.0.52** | `--rules` still works. E1 already showed it lands in `system_prompt.txt` inside `<human_rules>`, so **drop that E3.1 spike**. |
| **Muse** | → **1.4.7** | `--trust-workspace` is still hard-coded (`muse_provider.py`). The "run without trust" spike is still open. |
| **agy** | → 1.3.4 | Still records nothing (`◌`). Stays declared legacy. |

`instructionFiles` takes four values:

- `"claude-md"`: load `CLAUDE.md` only;
- `"claude-md-or-agents-md"` (**default**): a project with no `CLAUDE.md` gets its
  `AGENTS.md` instead;
- `"claude-md-and-agents-md"`: load both;
- `"managed-only"`: drop project and user files.

**Amendments:**

- **E3.1 Claude spike.** Probe `instructionFiles` together with exact-path
  `claudeMdExcludes`. The excludes match by absolute path for User, Project, and Local
  types, so they can cover `AGENTS.md`. Test both filename families, symlinks, imports,
  and delayed nested loads. Verify that excluding a `CLAUDE.md` doesn't trigger the
  `AGENTS.md` fallback, and that linked-repo guides under `sase/repos/**` still load.
  `managed-only` is too blunt: it would drop the linked-repo guides that E3's exit
  criteria must keep. **Tell E4's author.** Once the `CLAUDE.md` shims are deleted,
  Claude's default will load `AGENTS.md` natively.
- **E3.4 Codex.** Declare Codex `subagent: inherits-root`, with the actor-qualified
  root-only sentence as the mitigation. Add an E3.1 probe of what a
  `fork_turns: "none"` child receives. Risk today is low: the scoreboard shows 0 Codex
  spawns.
- **Keep the other probes:**
  - Muse without trust;
  - the Claude auto-memory switch;
  - the Grok memory-v2 decision;
  - cdx's Codex fixture, as a regression test.

  Record each probe's CLI version and an honest outcome: legacy or unavailable.
- **Codex home hygiene.** Write private regular files; never follow inherited
  `AGENTS.md` or `AGENTS.override.md` symlinks. `~/.codex/AGENTS.md` must be
  byte-identical after a run. Apply `project_doc_max_bytes=0` only to SASE-managed
  invocations. Hand-written nested guides must remain reachable. The inventory marks
  the nested sase `AGENTS.md` files (TUI, tools, tape) as hand-written.

### Overlapping bug bead

_`sase-11s` overlaps E3.4. Priority: medium._

`sase-11s` is READY: a medium bug. `_create_shadow_codex_home` symlinks the shared
SQLite state and `sessions/` into each per-run `CODEX_HOME`. It is also linked to the
`sase-12r` silent-handoff-loss class. E3.4 rewrites the same function.

The bead's suggested fix gives each run a fresh `sessions/`. That would put rollouts
inside a disposable directory, while the scoreboard deliberately reads
`~/.codex/sessions`. **Fold `sase-11s` into E3.4, or land it first, with the
constraint that rollouts stay readable under the real `sessions/`.**

### Rollback and the Rust split

_Rollback, fallback, and the Rust split. Priority: medium._

- **Flags.**
  - E3.2 must create **new** per-provider `sunset` flags with `sase flag new`. The
    retired E1/E2 keys must not be revived.
  - Turning a flag off must restore E1's after-state. That includes keeping the Grok
    `--rules` stopgap and the Claude helper guard.
  - `sase flag disable` already persists a machine-local choice, so the rollback path
    works today.
  - You retired every flag within four days last week. Name a concrete removal
    condition in each flag's `--remove-when`.
- **Atomic fallback.**
  - If the render or transport validation fails, restore **both** legacy delivery
    **and** native discovery for that invocation, and notify. Suppressing native files
    and then failing to deliver must never leave an empty instruction context.
  - Cover invocations with no artifacts dir, where the boundary currently calls the
    provider directly. Also cover unknown and plugin providers, which default to
    `inherits-native`.
- **Rust/Python.**
  - The wire already has `DeliveryStatusWire::{explicit, inherits_native, inherits_root, none}`
    and optional `channel`, `session_ids`, `parent_invocation_id`, and
    `provider_cli_version` fields.
  - E3.3's "wait-continuations record `inherited`" must use `inherits_root`, or extend
    the wire deliberately.
  - `DeliveryWire` is `deny_unknown_fields`, so any new field is a sase-core change
    plus a `sase-core-revision.txt` move. Examples: per-slot subagent status,
    fallback reason, helper manifests (E2 hooks roots only).
  - Adapter argv and Markdown composition stay in Python, per the epics report's split.
    Record the split in E3.6's decision record.

### Decisions to record in the plan

These go in the plan's `decisions:` block.

- **Home-layer privacy:** whether Grok, Muse, and agy receive the home layer. It is
  246 B today, but nothing caps its growth.
- **Foreign memory:** Claude auto-memory and Grok memory v2 off in SASE runs
  (recommended). Claude auto-memory has dwindled to 2 non-empty directories (5 files,
  none newer than Sep 25). The planned harvest `memory` task bead is now tiny, but
  turning auto-memory off still saves tokens.
- **Sunset-flag lifetime and removal conditions.**
- **Claude's instructions** move from a user-message `CLAUDE.md` to
  `--append-system-prompt-file`. The epic lists this as a watch item, so record it as
  an accepted change.

### Smaller items

- **New `job` project.** It is enabled, with a generated `AGENTS.md` plus 4 shims (40
  generated files, not 35), and it is missing from `docs/instruction_inventory.md`. Add
  it to E3's parity fixtures and to E5's scope. Parity already passes there (cld).
- **File mode.** Shadow bundle `.md` files are created by `os.open(..., O_CREAT|O_EXCL|O_WRONLY)`
  without a mode, so they come out **0775** (executable). Confirmed. Pass `0o644`.
- **Muse latency.** Muse declaration-recovery warm p95 of 291 ms (n=5) exceeds the
  250 ms budget. Get a representative sample or accept it explicitly.
- **Watch start.** The 7-day watch starts when execution hosts run E3 code, meaning
  the first manifest whose `delivery.status` is not `shadow`. It does not start at
  landing. Global installs are human-only.
- **Name collision.** A different closed epic, `sase-18j` (failure triage), is also
  called "E3".

## Recommended launch sequence

1. **Launch a planning agent for E3.** Inputs:
   - the epics report's E3 section;
   - this report's [E1 readout baseline](#settling-the-e1-readout-disagreement),
     re-run at plan time;
   - the [plan amendments](#what-the-e3-plan-must-change).

   It should produce the six phases plus a scoreboard-readiness step, with explicit
   `depends_on`:
   - E3.0 scoreboard and E3.1 spikes run in parallel, and both gate E3.2;
   - E3.2 gates E3.3, E3.4, and E3.5;
   - E3.6 comes last.

   Follow the epics report's checklist: memory edits listed by file (only the
   decision record, plus one `memory` task bead), the Rust split and pin, `sunset`
   flags, separate exit criteria and watch metrics, an acceptance-record format, and
   no workspace paths.
2. **Approve and launch the epic.** Keep E3.1's answers gating the adapter phases.
   Muse can stay declared legacy if its trust spike fails.
3. **At landing, require:**
   - provider-native evidence for each switched root and helper channel;
   - both flag states;
   - atomic fallback;
   - protected repo-owned guides and global files;
   - the handoff-aware declaration readout.
4. **Watch for 7 days, then answer the flag-removal beads.** Only after that, E4. E6
   stays optional, but `sase instructions show` is worth pulling forward
   ([scoreboard readiness](#scoreboard-readiness)).

Don't split E3 into separate per-provider epics: they would collide on the shared hook,
manifest, and CLI. Don't fold E4's file deletion into E3.

## How to see what an instruction bundle looked like

### Four meanings of what it looked like

"What it looked like" means four different things:

| Question | Where the answer lives | Before E3 (today) | After E3 |
| --- | --- | --- | --- |
| **A. What bundle did SASE compile for that invocation?** | `<artifacts>/instructions/NN-<provider>.md` + `.json` manifest | Exists for root agents launched since **Oct 7 12:57Z**. **Shadow only: never delivered.** | The delivered bytes |
| **B. Which native files did it launch with?** | `agent_meta.json` → `instruction_snapshot`; the Agents-tab **`AGENTS.md as launched`** row | What it actually loaded, via the legacy path | Should no longer matter (native 0) |
| **C. What did the provider actually load?** | `sase instructions verify -a NAME`, reading the provider's own session records | Legacy files, with the contract 2× for Claude and Codex | Should equal A, exactly once |
| **D. What would it get if launched now?** | `sase instructions render -a NAME` | A fresh compile from **today's** sources | Same; not history |

### From the Agents tab

Select the completed agent, then:

- **`%` then `d`** copies its artifacts dir. Bindings: `copy_mode.prefix: percent_sign`,
  agents target `artifacts_dir: "d"`.
- **`V`** opens its metadata in the pager. The `instructions` block names the latest
  manifest (`latest.manifest`, `sha256`, `common_digest`).
- **SASE CONTEXT → MEMORY lane → `◇ AGENTS.md as launched`**, then its **`v`** hint,
  opens the pager. It shows the pinned committed version, or the stored snapshot when
  those bytes were never committed (`◌ as launched · not in git`). This is answer
  **B**, for the workspace-root `AGENTS.md` only. It is not the compiled bundle, the
  home layer, or the provider directive. Older runs may have no launch row.

**The TUI cannot open the bundle itself today.** The lead checked: no TUI code
references the `instructions/` bundle files, and `synthesize_default_artifact_files`
doesn't register them. So:

- `a` (artifact files) won't list the bundle.
- The Files deck shows diffs and attached files, not the bundle (correcting gem).

A MEMORY deck with Manifest, Ledger, and Bundle cards (picker `p` → `y`) is E6 scope.

### The exact recorded bundle from the CLI

```bash
sase agent show NAME          # prints "Artifacts dir:" (works for dismissed agents too)
A='<artifacts dir from above>'

ls "$A/instructions/"         # 00-<provider>.md/.json; 01-… for recovery, repair,
                              # or a fallback provider; NN-<provider>.error.json if a render failed
jq '.instructions' "$A/agent_meta.json"          # latest pointer, sha256, common_digest

sase pager "$A/instructions/00-<provider>.md"    # the bundle, verbatim
jq '{facts, bundle, delivery}' "$A/instructions/00-<provider>.json"
jq -r '.sections[] | [.id, .layer, .status, (.reason // ""), .tokens_est] | @tsv' \
   "$A/instructions/00-<provider>.json"          # what was in or out, and why

sha256sum "$A/instructions/00-<provider>.md"     # equals .bundle.sha256
```

Notes:

- **Read every `NN`, not just `00`.** `instructions.latest` may point at a
  declaration-recovery or conflict-repair invocation. Check each manifest's `purpose`,
  `attempt`, and `invocation_seq`, plus its provider. The sequence starts at `00`.
- **Content store.** The manifest's `bundle.store_path` points at a content-addressed,
  read-only copy: `~/.sase/instructions/bundles/<sha[:2]>/<sha>.md`. Use it if the run
  dir's copy is gone. A digest alone cannot reconstruct missing bytes.
- **Comparing bundles.**
  - Same `bundle.sha256` means byte-identical bundles.
  - Same `common_digest` with a different `sha256` means the bundles differ only in the
    provider section.
- **Excluded sections carry reasons.** For example, `home.core.sase` and
  `proj.core.sase` are `superseded_input`, and `pkg.helper.contract` is `overlay` in a
  root render.

Verified example: `sase-1kh.land--code` (Codex) → `instructions/00-codex.json`. The
bundle is 20,038 bytes, about 5,013 tokens, SHA-256 `49526658…387e`, and matches its
store copy.

### What the agent actually saw

These are answers B and C from the
[table above](#four-meanings-of-what-it-looked-like).

- **B: launch snapshot.** `agent_meta.json` → `instruction_snapshot` lists the project
  root instruction files and the first home instruction file, each with its git
  `blob_oid`. Uncommitted bytes are kept in `~/.sase/instruction_snapshots/<oid>`.
  Nested files are not captured.
- **C: observed.** `sase instructions verify -a NAME` (add `-j` for JSON, and widen
  `--since` for older runs). It reads the provider's own records:
  - Claude: `~/.claude/projects/<cwd>/<session>.jsonl` and `subagents/agent-*.jsonl`;
  - Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`;
  - Grok: `prompt_context.json` and `system_prompt.txt`;
  - Muse: `session.jsonl`;
  - agy: records nothing.

  In JSON, the per-session diff is under `observations[].section_diff`. Check
  `partial` and `unavailable` before trusting zeros: transcripts over 512 KB blank
  every row ([scoreboard readiness](#scoreboard-readiness)).
  Exit 0 does not mean delivery was correct.

### Gotchas

- **Dismissed agents:** `verify -a` silently returns `runs=0`, and `render -a` says
  "no runs found". The files are still on disk; go through `sase agent show`.
- **Use the member name the Agents tab shows.** For example, `7e--plan`, not `7e`. The
  manifest's `delivery.agent_name` keeps the launch-time name.
- **`render -a` is not a history viewer.** Use it to ask "has anything changed since
  that agent ran?" Run it from the agent's own project. stderr reports
  `bundle matches recorded <sha>` or lists changed section ids. gem's description of it
  as printing the recorded bundle is wrong.
- **Runs with no `instructions/` dir:**
  - gate and monitor turns, which never call a provider;
  - runs before Oct 7 12:57Z, where only B applies;
  - native helpers, since E2 records roots only.
- **Running agents:** the bundle is written before the call, but observation exists
  only after the provider writes its session record.

### What E3 and E6 change

After E3, answer A becomes the delivered bytes. The scoreboard should then show each
section once on the **explicit** channel, native-full 0, and helper rows carrying the
helper bundle id. E6 adds the in-TUI views. Until then, the recorded files are the
source of truth, and a `sase instructions show <agent>` pulled into E3 would turn
[the CLI recipe](#the-exact-recorded-bundle-from-the-cli) into one command.

## Where the reports disagreed and the resolution

| Topic | Positions | Resolution |
| --- | --- | --- |
| E1 readout | cld and grk: acceptable, Grok 74%. cdx: unsettled, 5 unexplained runs. | **Acceptable.** The 5 runs are prepare + verify-monitor handoffs. The handoff-aware miss rate for Grok fell from 14% to 5% ([E1 readout](#settling-the-e1-readout-disagreement)). |
| Codex declaration rate | cld: a 38% outlier to watch | **Artifact** of counting monitor handoffs; real misses ≤2% |
| Ready? | gem, grk, mus: ready, write the plan. cld: ready after four amendments. cdx: foundation ready, gate unsettled. | Gates met. No plan exists. Write the plan with the [amendments](#what-the-e3-plan-must-change). |
| Scoreboard fixes: where | cld: an E3.0 phase. cdx: alongside each channel switch. Others: E3.6. | **Before the provider phases** (E3.0, or the head of E3.1), because their exit criteria read it |
| Muse per-purpose rows | mus: maybe a hook gap. cdx, grk, cld: a presentation quirk. | **Quirk**, confirmed in `coverage_summary.py` |
| Claude `AGENTS.md` loading | cdx: recent Claude versions load it | **Confirmed** in 2.1.296: `instructionFiles`, default falls back to `AGENTS.md` |
| Bundle in the TUI | gem: Files deck (`f`) lists `instructions/*.md` | **Incorrect.** No TUI surface opens the bundle; use the `%` `d` and `V` paths |
| `render -a` | gem: prints the recorded bundle | **Incorrect.** It recompiles from current sources |
| Coverage and latency figures | gem: 47/47, warm 30–55 ms | Not reproduced. cdx, grk, cld, and mus agree on per-provider N/N and warm p95 of 99–171 ms. |
| Why Claude section diffs are blank | grk: the parser "sometimes cannot attribute" | **Cause is the 512 KB cap** plus the zero-all-rows rule (cld, confirmed) |

## About this report

The lead restated the request as follows:

> **Request.** I'm considering launching agents to implement E3 from
> [`memory_built_instruction_migration_epics.md`](../memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md#e3-explicit-delivery-cutover).
> Are we ready? And how can I see what a given SASE agent's instruction bundle looked
> like, for example for a completed agent on the Agents tab?
>
> _Lead consolidation, 2026-10-13. This report merges five independent reports
> ([cdx](e3_delivery_cutover_readiness_and_bundle_inspection__cdx.md),
> [cld](e3_delivery_cutover_readiness_and_bundle_inspection__cld.md),
> [grk](e3_delivery_cutover_readiness_and_bundle_inspection__grk.md),
> [mus](e3_delivery_cutover_readiness_and_bundle_inspection__mus.md),
> [gem](e3_delivery_cutover_readiness_and_bundle_inspection__gem.md)) with the lead's
> own checks. Everything was measured on apollo against sase `8959b0e6fc` (origin/master
> is now `78e967bd3d`, which adds only test commits) and sase-core `d30e1337`, which
> matches sase's pin._

## Evidence index

- **Epic definition:** `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`
  (E3, E6, yardstick, sequence, checklist, Rust/Python boundary).
- **Beads:** `sase-11s` (audited read). `sase bead search` for E3 terms returned none.
  `sase bead list --status in_progress` shows no epic touching the provider adapters.
  The researchers read `sase-1gu`, `sase-1h3`, `sase-1h4`, `sase-1jc(.10)`, and
  `sase-1gj`.
- **Code (sase `8959b0e6fc`):**
  - `instructions/run_index.py` (`enumerate_runs` via `listing_snapshot`, 512 KiB
    cap);
  - `instructions/coverage_diff.py` (contains-counting, partial zeroing);
  - `instructions/coverage_summary.py` (per-purpose denominator);
  - `llm_provider/_instruction_boundary.py` (`O_EXCL` without a mode, env export, the
    no-artifacts-dir path);
  - `axe/launch_evidence.py`;
  - `ace/tui/widgets/prompt_panel/_agent_memory_versions.py`;
  - `default_config.yml` (copy mode, `V`, `a`).
- **Code (sase-core `d30e1337`):** `instruction_manifest/wire.rs`, where
  `DeliveryStatusWire`, `DeliveryWire` (`deny_unknown_fields`), and
  `ObservationStatusWire` are defined.
- **Live (lead):**
  - `verify -a` and `render -a` on dismissed `research.10.cld`;
  - `sase agent show`, `sase agent list -a -j`, `sase machine list`, `sase flag --help`;
  - a manifest census of 804 files (provider, purpose, status, host, error files);
  - a handoff-aware declaration scan of `ace-run` artifacts for Sep 10 – Oct 13;
  - the five `bob-cli-7c` runs' `tool_calls.jsonl`;
  - a Codex rollout's `<multi_agent_*>` blocks;
  - Claude 2.1.296 binary strings (`instructionFiles`, `claudeMdExcludes`);
  - CLI `--version`s;
  - `jq` and `sha256sum` checks on `sase-1kh.land--code`'s bundle.
- **Researchers' live evidence** (see their reports):
  - `sase instructions verify --since 7d [-c] [-j]`;
  - `render -p` in `sase`, `bob-cli`, and `job`;
  - `doctor -D -C instructions`;
  - `codex debug prompt-input` probes (cdx, cld);
  - the 177 Claude helper transcripts and `memory_reads.jsonl` join (cld);
  - the focused test suites, 64 passed plus the slow warm-latency test (cdx).
- **Not done:** paid provider canaries, remote-host probes, the Muse-without-trust
  probe, and the auto-memory switch probe. Those remain E3.1 work.
