# E3 Explicit Delivery Cutover: Are We Ready, and How to Reconstruct Any Agent's Instruction Bundle

Date: 2026-10-13 · Researcher: mus (swarm research.13) · sase checkout: workspace sase_16
Build: sase 0.17.1 (manifest compiler v1) · sase-core manifest schema v1

> Questions: (1) Are we ready to launch agents to implement E3 (Explicit delivery
> cutover) from `research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md`?
> (2) How can I figure out what a given agent's instruction bundle contents looked
> like — for a completed agent on the Agents tab, for example?

## Bottom line

**Yes, E3 is launchable now, with two pre-launch checks and one scoping decision.**

- E1 (`sase-1gu`) and E2 (`sase-1h3`) are both CLOSED (landed 2026-10-06). The E3 entry
  gates from the epic report are met: E1 has 7 days of runs (gate was ≥3 days), and
  E2's parity check is clean today.
- No E3 epic bead exists yet (searched all beads 2026-10-13; only unrelated E3s like
  `sase-18j` failure-triage exist). Creating it is the actual launch step.
- The shadow renderer is now unconditional: flag `instruction_shadow_render`
  (`sase-1h4`) was retired 2026-10-10, so every root invocation already writes
  `<artifacts>/instructions/NN-<provider>.{md,json}`. That is the reconstruction
  source answered in Part 2.
- Remaining E3 work is exactly what E3.1 (spikes) was designed to absorb: Muse
  `--trust-workspace` is still passed, Codex has no `project_doc_max_bytes=0` yet,
  and Claude auto-memory / Grok memory-v2 are still decided-but-not-implemented.
  Those are phase work, not launch blockers — but the plan must keep E3.1 first and
  must not let providers skip it.
- One watch item: `sase instructions verify --coverage -j --since 7d` today shows
  ordinary-purpose coverage at 100% for claude/codex/grok (7/7, 12/12, 14-15/15),
  zero shadow errors, and warm p95 ~40–170 ms (well under the 250 ms budget), but
  Muse `conflict_repair` / `declaration_recovery` rows list many uncovered sessions
  (e.g. bob-cli agents, `research.12.mus`). Confirm before launch whether those are
  out-of-scope purposes (E2 only hooked roots/ordinary + two finalizer routes) or a
  real hook gap — E3's architecture test must cover all three invocation sites.

## 1. What E3 is (recap from the epic report)

E3 makes every major provider get its bundle **exactly once through its explicit
channel**, suppresses SASE-owned full native files, and gives Claude helpers the
helper bundle. The report calls this "completes your stated goal for SASE agents."
Six phases, in order:

| Phase | Scope |
| --- | --- |
| E3.1 `spikes` | Can Muse run without `--trust-workspace`? Does Grok record `--rules` text? Do exact-path `claudeMdExcludes` cover home/workspace/nested while sparing `sase/repos/**`? Codex `project_doc_max_bytes=0` fixture. Auto-memory switch probe. |
| E3.2 `delivery-plan` | `llm_instruction_delivery` hook returning `DeliveryPlan` with root/subagent slots (`explicit`/`inherits-native`/`inherits-root`/`none`). Per-provider **sunset** flags with both-states tests. Render-failure falls back to legacy for one invocation + notify. `%dispatch` renders on target, refuses protocol mismatch. |
| E3.3 `claude` | Root via `--append-system-prompt-file` (directive folded in). Helper bundle replaces E1 template, guard stays. Exact-path excludes. Auto-memory off in SASE runs. Wait-continuations record `inherited`. |
| E3.4 `codex-grok` | Codex: shadow `$CODEX_HOME/AGENTS.md` becomes private file (neutral core + home); `developer_instructions` carries root overlay + directive; `project_doc_max_bytes=0` in SASE-managed projects only, fail loudly over 32 KiB. Grok: `--rules` carries full root bundle (replaces E1.2). Grok memory-v2 decided with auto-memory. |
| E3.5 `muse-agy` | Muse prompt-prefix; drop `--trust-workspace` iff E3.1 passed else declared legacy until E4. Interrupt reconstruction never nests a second bundle. agy/Qwen/OpenCode declared `inherits-native` until E4. |
| E3.6 `conformance` | Scoreboard asserts each bundle id exactly once per invocation/helper. Decision record "Instructions Are Rendered Per Invocation And Delivered By Adapters." |

Entry (per report): E1 ≥3 days readout acceptable + E2 parity clean. Exit probes:
Claude/Codex/Grok/Muse show bundle 1×, contract 1×, home ✓, native-SASE-full 0
(agy declared legacy); helper transcripts carry helper bundle id; each sunset flag
restores E1 state when off; re-render reproduces manifest hash. Then a ≥7-day soak
before E4 (whose entry additionally requires the sunset flags **removed**).

## 2. Readiness evidence (observed 2026-10-13)

### 2.1 E1 and E2 are done; entry gates met

- `sase bead read sase-1gu / sase-1h3`: both CLOSED. E1 closed 2026-10-06T16:05Z
  (6 phases), E2 closed 2026-10-06T22:09Z (7 phases + acceptance).
- E1 elapsed: 7 days > 3-day gate. E1 after-state still holds today:
  `sase instructions verify --since 7d` shows Claude 2×/✓/✓/✓/2×, Codex 2×/✓/✓/✓/2×,
  Muse 1×/✗/✓/✓/1×, Grok 1×/✗/✓/✓/0 (contract 1×, project ✓, directive ✓,
  `agents_md_files: []`), agy ◌. That matches the E1 "after" row (Grok 0→1× fixed,
  Claude/Codex still double until E3, Muse still no-home until E3).
- Claude helpers: `verify -p claude --helpers --since 7d` shows helper template ✓ on
  all 9 helper rows, 0 attempts / 0 accepted. Guard holds.
- E2 parity: `sase instructions render -p` exits 0 with
  `contract_count=1, additions=5` (the 5 additions are `frame.*` + provider section —
  reported as additions, not failures). `git ls-files | grep -cE ...` still prints
  20 (E4 has not run, as expected).
- Docs confirm the stage: `docs/instruction_bundles.md` states "Current providers do
  not read [SASE_INSTRUCTIONS_FILE]. ... use `sase instructions verify` to check
  observed loads. ... later delivery stages have not replaced the current path."
  `docs/instruction_inventory.md` assigns E3 the delivery cutover and E4 the file
  removal. No doc claims E3 shipped.

### 2.2 Shadow pipeline is live and fast

- Boundary: `src/sase/llm_provider/_instruction_boundary.py`
  (`invoke_with_instructions`) wraps every root `provider.invoke`, writes
  `instructions/NN-<provider>.md/.json`, updates `agent_meta.json/instructions`,
  exports `SASE_INSTRUCTIONS_FILE` during the call, fails open to
  `NN-<provider>.error.json`. Flag `instruction_shadow_render` retired by
  `sase-1jc.10` on 2026-10-10 — shadow is now unconditional, not flaggable.
- Coverage JSON (`--coverage -j --since 7d`, observed): ordinary purpose —
  claude 7 manifests / 7 sessions / 7 covered; codex 11 / 12 / 12; grok 13 / 15 /
  15 (one grok manifest count differs by one due to a re-render; no errors);
  muse ordinary 13 / 12 / 12. `errors_total: 0`. Warm p50/p95 per provider
  40–170 ms (claude 47/167, codex 51/101, grok 50/59, muse 56/—, agy 40/40);
  cold p50 460–780 ms. Within the 250 ms warm-p95 budget.
- Store deduplicates: this run's `00-muse.md` is byte-identical (`diff` exit 0) to
  `~/.sase/instructions/bundles/8e/8e8a8d74….md` (mode 0444). Re-render reproduces:
  `sase instructions render -a research.13.mus -j` reports
  `bundle matches recorded 8e8a8d74cbf9`, same `common_digest 6b4280fc40a6`.
- Caveat (pre-launch check #1): Muse non-ordinary purposes show uncovered sessions
  in the JSON (`conflict_repair`: 1 manifest vs 12 sessions; `declaration_recovery`:
  5 vs 12; uncovered agents include `7e--code`, `bob-cli-74.x`, `research.12.mus`,
  `sase-1kh.2--1`). E2.2–E2.3 hooked ordinary + declaration-recovery +
  conflict-repair routes, so either those sessions predate the hook or they are a
  different purpose label. The E3 plan must state which purposes the hook covers and
  add the architecture test ("no `provider.invoke` bypasses the hook") from day one.

### 2.3 E1 stopgaps still in place; E3.1 spikes still open (expected)

- Grok: `src/sase/llm_provider/grok.py:94–127,418` — `_grok_rules_text()` builds
  directive + project `AGENTS.md` once; argv extends `--rules`. No `--trust`.
  Matches E1.2 corrected fix (not the rejected `GROK_CLAUDE_AGENTS_ENABLED=0`).
- Claude helpers: `claude.py:456–476` carries
  `--append-subagent-system-prompt-file …/claude_helper_instructions.md` plus the
  PreToolUse guard (`_claude_helper_channel.py`, `_claude_helper_guard.py`); doctor
  deep check `providers.claude_helper_channel` exists.
- Codex: `codex.py` still uses per-run shadow `CODEX_HOME` only to symlink
  `~/AGENTS.md` in (`_link_home_agents_fallback`); no `project_doc_max_bytes=0`
  anywhere in the file — that is E3.4 work, pending its E3.1 fixture.
- Muse: `muse_provider.py:332` still passes `--trust-workspace` plus
  `--no-foreign-personal-context`. Dropping it is the E3.1 spike + E3.5 decision.
- Auto-memory / memory-v2: no `CLAUDE_CODE_DISABLE_AUTO_MEMORY` handling and no
  `claudeMdExcludes` plumbing found in `claude.py` (only a test `exclude_patterns`
  at :296); verify still reports `foreign: auto-memory` on Claude and `memory…` on
  Grok. Disabling both is E3.3/E3.4 work, with the one `memory` task bead to harvest
  notes.
- Flags: `sase flag list -j` today shows exactly one flag
  (`artifacts_agent_pane_retired`, sunset). No instruction sunset flags exist yet —
  correct, because E3.2 creates the per-provider sunset flags. The plan must follow
  `sase_flags.md` (sunset kill switches, not beta) and `cli_rules.md` for the
  `sase instructions` group shape.

### 2.4 Risks and what the plan must nail

1. **Hook coverage + architecture test** (pre-launch check #1 above). Name the three
   invocation sites (`_invoke.py`-equivalent, `declaration_recovery`,
   `commit_repair_conflict` per the epic report) and assert none bypasses the hook.
2. **Muse/Codex/Grok observability limits.** Scoreboard can verify Claude (transcript
   attachments), Codex (rollout `<INSTRUCTIONS>` + `--- project-doc ---`), Grok
   (`prompt_context.json` + canary since `--rules` text may not be recorded), Muse
   (`session.jsonl` first user message). agy records nothing — plan must keep the
   `◌ unverifiable` posture, never `✓`.
3. **Codex shadow-home symlink hazard.** Open bead `sase-11s` reports shadow
   `CODEX_HOME` symlinks shared sqlite state causing stale rollout paths. E3.4
   replaces the symlink trick with a private file — the plan should cite `sase-11s`
   and prove no shared-state regression.
4. **Soak discipline.** E3 exit needs a ≥7-day watch (final-declaration rate per
   provider vs E1 readout; `memory_reads.jsonl` trigger reads). Epic launches
   preassign all phases, so the soak must be an epic boundary (E3→E4), not a phase
   pause. Flag-removal beads come after the soak; E4 entry requires flags removed
   and every execution host on E3 code.
5. **Memory-edit authorization.** Each epic plan must list memory edits file-by-file
   (`/sase_memory_write` rule). E3's known edits: the "Instructions Are Rendered
   Per Invocation And Delivered By Adapters" decision record + the auto-memory
   harvest task bead. Rust split: manifest schema already in `sase-core` (E2.1 pin
   moved); E3 should state whether any Rust change + pin move is needed (delivery
   hook is Python; `when:` evaluator is E7, not E3).

**Recommendation:** approve an E3 epic plan with E3.1 spikes first (Muse trust,
Grok rules observability, excludes exact-paths, Codex debug fixture, auto-memory
switch probe), per-provider sunset flags in E3.2, then one phase per provider
group, then conformance. Do not split E3 by provider as separate epics (shared
hook/manifest/CLI would collide). Do not fold E4 file deletion into E3.

## 3. How to reconstruct what an agent's bundle looked like

All commands below are read-only. Replace `AGENT` with the Agents-tab name
(e.g. `sase-1kh.2--1`). The worked examples use runs observed 2026-10-13.

### 3.1 Fastest path (three commands)

```bash
sase agent show AGENT                 # artifacts_dir + provider/model/status
sase instructions verify -a AGENT --since 30d   # intent vs observed for that agent
sase instructions render -a AGENT -j  # fresh preview from today's sources + match report
```

`verify -a` compares the run's recorded manifests against the provider's own session
records and prints per-session detail. `render -a` compiles from **current**
project+home sources using that agent's facts (provider from its run record, or its
latest manifest when one exists); stderr says whether the fresh sha256 matches the
recorded bundle and lists changed section ids. A match means "today's sources would
produce the same bytes"; a mismatch means memory changed since — then use the
recorded files in §3.2, not the fresh preview.

Example (this run, `research.13.mus`, muse): `render -a` stderr reports
`agent research.13.mus: bundle matches recorded 8e8a8d74cbf9`.

### 3.2 Exact bytes: the recorded bundle + manifest (post-E2 runs)

Every root provider invocation since E2 writes, under the agent's artifacts dir:

```
<artifacts>/instructions/NN-<provider>.md    # exact bundle Markdown the agent would get
<artifacts>/instructions/NN-<provider>.json  # normalized manifest (indent=2, sorted keys)
<artifacts>/instructions/NN-<provider>.error.json  # only on shadow-render failure
```

Find the dir:

```bash
sase agent list -j | python3 -c \
  "import json,sys; [print(a['name'], a['artifacts_dir']) for a in json.load(sys.stdin) if a['name']=='AGENT']"
# or: sase agent show AGENT | grep -i artifact
ls -la <artifacts>/instructions/
```

Then:

```bash
cat <artifacts>/instructions/00-muse.json | python3 -m json.tool | head -n 60
  # facts (actor/mode/purpose/provider/project/host/vcs), bundle sha256 +
  # common_digest + bytes/tokens, compiler version, delivery (invocation_id,
  # rendered_at, cache, status: shadow), sections[] with per-section id/layer/
  # offset/length/sha256/sources(blob_oid, path, scope), budget.by_layer
cat <artifacts>/instructions/00-muse.md | head -n 40
  # the exact Markdown
python3 -c "import json; print(json.load(open('<artifacts>/agent_meta.json'))['instructions'])"
  # {count, latest:{seq, provider, purpose, sha256, common_digest, manifest}, schema_version}
```

Notes:

- `NN` is a per-run sequence (`O_EXCL`-allocated): `00` ordinary turn, `01…`
  declaration-recovery / conflict-repair follow-ups. A completed agent often has
  several: `sase-1kh.2--1` holds `00-muse.json/md` (ordinary) + `01-muse.json/md`
  (`purpose: declaration_recovery`). Read **all** `NN` files, not just `00`.
- `common_digest` (sha256 over `[[id, sha256], …]` for non-provider sections) is the
  cross-provider comparator: equal `common_digest` with different `sha256` means
  "same instructions except the provider section." Observed: a claude run
  (`7c.f0--plan`, `bb8aa409…`) and this muse run (`8e8a8d74…`) share
  `common_digest 6b4280fc40a6`.
- The bundle bytes also live once in the content store named by the manifest:
  `~/.sase/instructions/bundles/<sha[:2]>/<sha>.md` (0444, never pruned in E2).
  `diff <artifacts>/instructions/00-muse.md <store-path>` exits 0. Use the store
  path when the artifacts dir has been archived.
- Section table without opening the bundle: `sase instructions render -a AGENT -s`
  (id/layer/status/lifecycle/bytes/tokens/source) or read `.sections[]` in the
  recorded JSON. Per-section `sources[].blob_oid` pins the exact memory version;
  `status: superseded_input` / `shadowed` explains excluded content.

### 3.3 Observed side: what the provider actually loaded

The manifest is **intended** (shadow — E2 delivers nothing; `delivery.status:
shadow`, `observation.status: unobserved`). For what arrived, join with the
provider's own session record via `verify -a AGENT`:

| Provider | Session record `verify` reads | What proves delivery |
| --- | --- | --- |
| Claude | transcript `instructions` + `prompt_snapshot` attachments; `subagents/agent-*.jsonl` | loaded file paths + full system-prompt text → bundle hash checkable exactly; helpers show `# SASE Helper Instructions` + helper bundle id, never root's |
| Codex | rollout user message `# AGENTS.md instructions for <cwd>` | `<INSTRUCTIONS>` block + `--- project-doc ---` sections; today: home+project double (2×) |
| Grok | `prompt_context.json` (`agents_md_files`), `system_prompt.txt` | `agents_md_files: []` + `system_prompt.txt` `<human_rules>` block (E1 canary); whether `--rules` text is recorded needs the E3.1 probe |
| Muse | `session.jsonl` | first user message carries the prefix (+ bundle after E3) |
| agy | none | always `◌ unverifiable`, never `✓` |

`verify -a AGENT` prints the manifest-coverage column (`k/N`), the
contract/home/project/directive/native/foreign cells, and helper rows. Exit 0 does
**not** mean correct — read the rows (a bad `--since` exits 2).

### 3.4 When there is no `instructions/` dir

- **Gate / monitor / waiting agents:** expected. Gate and monitor turns never call a
  provider (verified: nothing under `src/sase/monitor/` or `src/sase/gate_turn/`
  calls `provider.invoke`), so no manifest exists. Example: `sase-1kh.land--gate`
  has no `instructions/` dir. Look at the parent/root agent instead.
- **Still-running agents:** the current invocation's session record may not exist
  yet. This run (`research.13.mus`, RUNNING) shows `verify -a` as `0/0 · 0 · ◌`
  with `runs=1 sessions=0` even though `00-muse.{md,json}` already exist — intent is
  recorded before/during the call, observation only after.
- **Pre-E2 runs:** no shadow manifests. Fall back to the legacy snapshot:
  `agent_meta.json/instruction_snapshot` + `~/.sase/instruction_snapshots/<oid>`
  (written by `capture_instruction_snapshot`), and the Memory-history "AGENTS.md as
  launched" row. The TUI keeps reading those for old runs.
- **Helpers:** E2 hooks roots only; helper renders are preview-only
  (`render -f actor=native_helper`). For a Claude helper today, check its
  `prompt_snapshot` for the helper-template marker + the root's `--settings` guard.

### 3.5 Caveats

- `render -a` uses **today's** memory; only the recorded `NN-*.md` is historical
  truth. Always cite the manifest's `rendered_at`, `compiler.sase_version`, and
  `bundle.sha256` when quoting contents.
- Never treat `SASE_INSTRUCTIONS_FILE` as delivery proof in E2: providers do not
  read it yet (see `docs/instruction_bundles.md` § Shadow manifests). It is the
  path to the would-be bundle during the call only.
- Home-layer bytes depend on the execution host's `~/sase/memory`; re-renders on a
  different host can differ in `home.*` sections. The manifest's `facts.host`
  records where it rendered.

## Evidence index (this report only; no peer-report content consulted)

- Epic definition: `sase artifact read
  "research:202610/memory_built_instruction_migration_epics/memory_built_instruction_migration_epics.md"`
  (lead consolidation, 2026-10-05; E3 § + yardstick + checklist + sequence).
- Beads (all `sase bead read -r "E3 readiness research"`): `sase-1gu` CLOSED
  2026-10-06T16:05Z (6/6 phases; notes #5 land-acceptance GROK+CLAUDE probes, #6–8
  baseline-v2/after-v2/acceptance-v2); `sase-1h3` CLOSED 2026-10-06T22:09Z (7/7);
  `sase-1gj` CLOSED superseded by E1; `sase-1h4` CLOSED (flag
  `instruction_shadow_render` retired by `sase-1jc.10` 2026-10-10). No bead for E3
  memory-migration cutover found in full-list grep 2026-10-13.
- Live CLI (sase 0.17.1, 2026-10-13): `sase instructions verify --since 7d`
  (runs=66 sessions=57 table quoted in §2.1); `verify -p claude --helpers`
  (9 helper rows, template ✓, 0/0); `verify --coverage -j` (ordinary 100%,
  errors 0, warm p95 ≤167 ms; muse non-ordinary uncovered list);
  `sase instructions render -s` (27 sections, 20038 B, 5013 tok, cache hit
  93 ms); `render -p` (`contract_count=1, additions=5`, exit 0);
  `sase flag list -j` (1 flag, no instruction flags);
  `git ls-files | grep -cE …` → 20.
- Code (workspace checkout, read-only greps): `_instruction_boundary.py`
  (shadow boundary, fail-open, `O_EXCL` seq, `SASE_INSTRUCTIONS_FILE`);
  `instructions/manifests.py` + `coverage_records.py` (read-back + matching);
  `grok.py:94–127,418` (`--rules` stopgap, no `--trust`); `claude.py:456–476`
  (helper template + guard); `codex.py:140–269,475` (shadow-home symlink, no
  `project_doc_max_bytes`); `muse_provider.py:332` (`--trust-workspace` still on).
- Docs: `docs/instruction_bundles.md` (E2 stage statement, bundle/manifest,
  layers, cache/store, shadow manifests, preview flags); chap
  `docs/instruction_inventory.md` (35 generated + nested/hand-written
  dispositions, E3/E4/E5 owners).
- Worked artifacts (this agent):
  `/home/bryan/.sase/projects/gh_sase-org__sase/artifacts/ace-run/202610/13/20261013162425/instructions/00-muse.{md,json}`
  (sha `8e8a8d74…`, common `6b4280fc40a6`, 21002 B, 329 lines) ≡
  `~/.sase/instructions/bundles/8e/8e8a8d74….md` (`diff` 0);
  `sase-1kh.2--1` (00 ordinary + 01 declaration_recovery);
  `7c.f0--plan` (claude, same common digest, different sha);
  `sase-1kh.land--gate` (no `instructions/` — gate turn, expected).
- Not re-measured (carried from epic report § Evidence index): run shares, Grok
  60%→26% declaration rates, Codex `project_doc_max_bytes=0` offline probe,
  ~2 s cold render, linked-repo hand counts.
