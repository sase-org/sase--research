# Instruction Bundles vs. a Readable `AGENTS.md`: Proceed, Re-scope, or Revert?

> **Research query:** You're unsure about the migration from agent instruction files to
> instruction bundles (epic `sase-1ko`). Your worry is that an agent's core instructions
> are no longer transparent. You used to be able to read `AGENTS.md` to see what
> project-level instructions a SASE agent got. Now new users and non-SASE agents may need
> a `sase` command to see them. You also don't see the benefits clearly. This report
> lists every immediate and long-term benefit and helps you decide whether to proceed or
> revert.

Researcher: `cld` (one of four in a swarm). Evidence gathered on 2026-10-14 against sase
`508eb963a3`, from this repo, the `sase-1ko` bead and its attachments, the E3 plan, and
four earlier consolidated reports. The [evidence index](#method-and-evidence) lists the
sources.

## Bottom line

**Don't revert E3. Change E4 instead.** Your concern is valid, but it applies to the
*next* epic, not to the one you just shipped.

1. **The transparency loss hasn't happened yet.** The repo still commits all 20
   instruction files. `sase memory init` still regenerates them. A test
   (`tests/instructions/test_render_parity.py`) checks that every section of the
   committed `AGENTS.md` is in the bundle and that the contract appears exactly once.

   The Claude bundle this agent received (`bb8aa409fd26`, 19,629 bytes) differs from the
   committed `AGENTS.md` in only four ways:
   - heading numbers and line wrapping;
   - the home layer: a `Home:` line, the `chezmoi` repo bullet, and two home
     reference notes;
   - one provider-specific "Single-Turn Instructions" section;
   - a trailing marker comment.

   Reading `AGENTS.md` still tells you nearly everything a SASE agent gets in this
   project.
2. **The loss is scheduled for E4, which hasn't been planned or approved.** The roadmap
   turns `AGENTS.md` into a stub of at most 80 lines. The full render would move into
   gitignored files that `sase instructions sync` / `just install` writes. That is the
   step that would make GitHub readers, new users, and non-SASE tools run `sase` to see
   the instructions.
3. **The technical reason for that step is gone.** The design rule that untracks the
   files (R7) rested on one "decisive fact": Codex can't suppress a committed project
   `AGENTS.md`. That turned out to be false. `-c project_doc_max_bytes=0` works, and E3
   uses it.

   In SASE runs a committed `AGENTS.md` is now suppressed for Claude (exact-path
   `claudeMdExcludes`), Codex, Grok (workspace untrusted), and Muse (no
   `--trust-workspace`). Keeping it costs nothing at runtime. It is also what E3's
   per-invocation legacy fallback loads, so deleting it would mean building E4's
   last-known-good store first.
4. **`AGENTS.md` was never the full picture.** Before E3, reading it did not tell you
   what an agent got:
   - Claude and Codex got the SASE contract twice: once from the home file and once from
     the project file, with conflicting linked-repo lists.
   - Grok got *nothing* for four weeks without anyone noticing.
   - Muse and Grok never got the home layer.
   - The provider directives were Python string constants.
   - Claude auto-memory depended on which `sase_<N>` workspace the agent landed in.

   E3 makes the per-agent question answerable for the first time:
   `sase instructions show NAME` prints the exact bytes that were delivered and checks
   them against their sha256.
5. **E3's benefits are real but mostly modest so far.** The two largest *measured* harms
   were Grok getting no instructions and Claude helpers submitting their parent's
   declaration. E1 fixed both without bundles. E3 adds:
   - exactly-once delivery;
   - the same instructions for every provider;
   - deterministic context;
   - a byte-exact record of what was delivered;
   - the base that E4–E7 build on.

   The soak started today, with about 20 finished runs, so there is no behavioral
   evidence yet either way.

| Option | What you get | Transparency | Verdict |
| --- | --- | --- | --- |
| **A. Soft revert:** `sase flag disable <p>_explicit_instructions` on each host | E1's after-state: the contract twice, no home layer for Grok or Muse, hidden directives, auto-memory | **No gain.** `AGENTS.md` was never removed. | Only if the soak shows harm (see [triggers](#what-would-change-this-recommendation)) |
| **B. Proceed as planned** (E4 stub, sync, and last-known-good store; then E5) | Every benefit, including no generated-file churn | **Real loss** for GitHub readers, new users, and non-SASE tools | Not recommended as written |
| **C. Keep E3, re-scope E4** to keep a full, CI-checked `AGENTS.md` | Every E3 benefit and most E4–E6 benefits | **Kept**, and per-agent provenance added | **Recommended** |

## What actually changed, and when

| Epic | Status | What it did | Effect on `AGENTS.md` |
| --- | --- | --- | --- |
| E1 `sase-1gu` | Closed 2026-10-06 | Scoreboard (`sase instructions verify`); Grok `--rules` stopgap; Claude helper template plus a PreToolUse guard | None (the template sentence regenerated it) |
| E2 `sase-1h3` | Closed | Compiler; shadow render of a bundle and manifest on every root invocation; `render [-p]` | None. Bundles were recorded but not delivered. |
| E3 `sase-1ko` | In progress (only `.10`, the record phase, is open) | Delivers the bundle exactly once per invocation through an explicit channel; suppresses the native SASE files; four per-provider `sunset` flags (all on); `show`, `readout`, conformance check | **Still committed and still regenerated.** Agents just don't load it. |
| E4 (proposed) | Not planned | `export` stub of at most 80 lines; `sase instructions sync` into gitignored files; last-known-good store; delete shims; Memory History "stub era" | **20 → 2 tracked files.** Full content leaves git. |
| E5–E7 | Proposed or optional | Home files and other projects; TUI MEMORY deck; `when:` audiences | E7 makes any single static file less representative |

First explicit renders in the live corpus: Codex at 10:52Z, Grok at 11:14Z, and Claude at
13:10Z on 2026-10-14. Muse's API quota is used up until 2026-10-19, so it has no live
explicit runs. The flag beads are `sase-1kv`, `sase-1ks`, `sase-1kt`, and `sase-1ku`.
Each one's removal condition is 7 clean days.

### What a SASE agent receives now, compared with `AGENTS.md`

| Content | Committed `AGENTS.md` | Root bundle (claude) | Bundles for other providers |
| --- | --- | --- | --- |
| Package contract (final declaration, workspaces, `/sase_repo`, memory routing) | ✓ | ✓ once | ✓ once |
| Project core memory, reference triggers, memory webs | ✓ | ✓ | ✓ (same `common_digest` `6b4280fc40a6`) |
| Home layer (`Home:` line, `chezmoi`, tailnet and obsidian triggers) | ✗ (lived in `~/AGENTS.md`) | ✓ | ✓ (new for Grok and Muse) |
| Provider single-turn directive | ✗ (was a Python constant passed by argv) | ✓ "Claude Single-Turn Instructions" | ✓ Codex, Grok, and Muse variants |
| Heading numbering | `## 1. Core Memory` | `## Core Memory` | same |
| Size | 18,694 B | 19,629 B (about 4.9k tokens) | 19.7–21.0 KB |

The bundles differ from one another **only** in the provider section. That is what the
shared `common_digest` proves. The pre-E3 Claude context was `~/CLAUDE.md` (4,084 B) plus
the workspace `CLAUDE.md` (18,694 B) plus the argv directive. E3 cuts it by about 3 KB, or
roughly 0.8k tokens per call.

## "Transparent" means four different questions

Your concern blends four questions. Each one moves differently.

| Question | Before E3 | Now (E3 on) | After E4 as planned | After re-scoped E4 (option C) |
| --- | --- | --- | --- | --- |
| **Q1. What will a SASE agent in this project be told?** | Read `AGENTS.md`. That was misleading: it didn't show the home file, the hidden directive, the double contract, Grok's zero load, or auto-memory. | `AGENTS.md` is still a parity-checked projection. `sase instructions render [-f provider=X]` shows the exact bundle in about 0.1 s warm (about 1.5 s cold). | `render` only. The repo holds an 80-line stub. | Same as now |
| **Q2. What exactly was agent X told?** | No reliable answer. `instruction_snapshot` recorded files on disk, not what the provider loaded. | **`sase instructions show X`**: the exact bytes, a sha256 check, and the helper bundle with `-H`. It works for dismissed agents. In-run: `$SASE_INSTRUCTIONS_FILE`. | Same | Same |
| **Q3. What does a human, a non-SASE tool, or a GitHub reader see?** | The full committed file. It includes the SASE runtime contract, so a raw `claude` or `codex` session is told to run `/sase_final`. | **Unchanged.** E3 affects only SASE-launched runs. | A stub plus "run sync". Full content needs `sase`. | The full committed file, optionally in a non-SASE-audience form |
| **Q4. What does the TUI show?** | The "AGENTS.md as launched" row | **Regressed:** that row and `instruction_snapshot` still show the native file, which explicit-delivery agents no longer load. No TUI surface opens the bundle. | Fixed in E4.4 / E6 | Fix the row as a small task |

So today, Q2 improved a lot, Q1 and Q3 stayed the same, and Q4 got worse. Only E4 as
written makes Q1 and Q3 worse.

### Your direct question: do new users and non-SASE agents now need a `sase` command?

**Not today.** A fresh clone, a GitHub reader, and a raw `claude` or `codex` session in
a checkout all still see the full committed `AGENTS.md` and `CLAUDE.md`, exactly as
before. That changes only if E4 ships as currently sketched.

For SASE users, here are the commands that answer each question:

```bash
sase instructions render                     # what an agent here would get (default provider)
sase instructions render -f provider=codex   # a specific provider's bundle
sase instructions render -s                  # section table: what's in, what's out, and why
sase instructions show NAME [-l|-H|-j]       # the bytes actually delivered to agent NAME
sase instructions verify -a NAME             # what the provider's own records show it loaded
```

### Small transparency gaps E3 left behind (all cheap to fix)

- `agent_meta.json` `instruction_snapshot` is still captured by
  `capture_instruction_snapshot` (`src/sase/axe/launch_evidence.py:260`). The readiness
  review describes the Agents-tab "AGENTS.md as launched" row as built from that
  snapshot. For explicit runs it now describes a file the agent did not load.
- The `docs/instruction_bundles.md` introduction still says Claude and Codex stay on
  legacy delivery.
- The bundle's own text still says memory notes "render into this file" and are
  "inlined … into every provider instruction shim". That wording dates from the file era.

## Benefits, immediate and long-term

The last column answers the question that matters for your decision: **does this benefit
require removing the full committed `AGENTS.md`?**

### Immediate (realized by E3, now live)

| # | Benefit | Evidence | Size | Needs `AGENTS.md` untracked? |
| ---: | --- | --- | --- | --- |
| 1 | **The contract arrives once instead of twice** for Claude and Codex, about 56% of runs. This also ends the contradictory linked-repo lists in the home and project files. | Harness probes: flag on gives `contract 1`; flag off gives `2 native` | About 3 KB (0.8k tokens) per call | No |
| 2 | **The same instructions for every provider.** Grok and Muse (about 42% of runs) now get the home layer. Grok gets the full bundle instead of E1's directive plus project text. | Shared `common_digest`; Grok probe `home ✓` | Grok and Muse runs gain tailnet, Obsidian, and chezmoi knowledge | No |
| 3 | **Provider directives become reviewable.** The four hand-maintained adapter strings are now `pkg.provider.<p>` sections that `render` shows. | `diff` of the four bundles above | A transparency *gain* | No |
| 4 | **Claude instructions move to the system prompt.** They survive `--resume` (snapshot), compaction can't summarize them away, interrupts restart with the same argv, and they outrank repo-supplied text. | E3 plan decision 6; spike (d) | Behavior effect not yet measured | No |
| 5 | **Claude helpers get a memory-built helper bundle**: memory triggers without the root contract. Before E1, Explore helpers got no project instructions at all; after E1, every helper got only a static template. The guard stays. | Helper probe: helper marker present, no root marker, 0 accepted helper declarations | About 518 helper runs per 30 days | No |
| 6 | **Deterministic context.** Claude auto-memory (which varied by `sase_<N>`), Codex memories, and Grok memory v2 are off in SASE runs. | Decision `foreign_memory = yes`; spikes | Removes per-workspace variance | No |
| 7 | **A byte-exact record of what was delivered.** Each invocation stores its bundle, manifest, sha256, and a content-addressed copy. `sase instructions show` reads them back. | `show research.1a.cld -l` gives the root and helper rows, `bytes match` | Answers Q2 for the first time | No |
| 8 | **Provable exactly-once delivery.** Marker counting gives `bundle 1×`, and the `instructions.conformance` doctor check and `readout` back it up. A four-week silent regression like Grok's would show up the same day. The scoreboard itself is from E1; the exactly-once proof needs E3's marker. | E3 exit criteria | Ongoing guard | No |
| 9 | **A smaller trust surface.** Muse runs without `--trust-workspace`. Codex's shadow `CODEX_HOME` is now an allowlist: no sqlite state, history, or memories are linked (`sase-11s`). | Codex phase; spike results | Hygiene | No (`sase-11s` applies in both flag states) |
| 10 | **Foreign and OSS repos.** The SASE contract is delivered without touching upstream files, and a repo-owned `AGENTS.md` still loads natively. | Exact-path exclude tests | Enables SASE in repos you don't own | No |
| 11 | **Atomic fallback.** A render, validation, size, or transport failure falls back to legacy delivery for that one invocation, with a deduplicated notification. An agent never starts with an empty context. | Decision 5; tests | Safety | **No. It *depends* on the native files staying.** |
| 12 | **No "forgot to regenerate" drift for SASE runs.** The bundle compiles from the workspace's memory notes at launch. | `_resolve_project_root()` | Minor | No |

### Long-term (enabled by E3, realized in E4–E7)

| # | Benefit | Epic | Needs `AGENTS.md` untracked? |
| ---: | --- | --- | --- |
| 13 | **No generated-file churn or merge conflicts.** The measured churn is smaller than the original estimate: 88 commits touched `AGENTS.md` in 60 days and only 7 in the last 14. 83 of the 88 also touched `sase/memory/` or generator source, so regeneration rides along with real edits rather than adding commits. | E4 | **Yes. This is the only benefit that strictly needs it.** Deleting the `GEMINI.md`, `QWEN.md`, and `OPENCODE.md` copies (12 of 20 files) does not. |
| 14 | **The right content for non-SASE readers.** Today the committed files and `~/CLAUDE.md` tell raw sessions to run `/sase_final`. | E4 and E5 | **No.** That needs *different content*, not untracking. The `export` render is 18,114 B with no runtime contract and could be committed in full. |
| 15 | **Home files become `interactive` renders.** The chezmoi hostname `.tmpl` is replaced by the `host` fact. `bob-cli`, `actstat`, and `job` adopt the same pipeline. | E5 | No |
| 16 | **`sase tmux-agent` launches through the same delivery hook** instead of depending on files by accident. | E5 | No |
| 17 | **In-TUI visibility:** a MEMORY deck with Manifest, Ledger, and Bundle cards, a delivery chip, and a "Seen by" index. This is the in-SASE answer to your concern. | E6 | No |
| 18 | **Audiences:** content conditional on role, provider, or phase-worker status; per-audience budgets; flag-gated instruction experiments scored on memory reads and declaration rate. | E7 (conditional) | No. But it makes any *single* static file less representative. |
| 19 | **Plugin sections** (`sase-github` and others) that appear only when the plugin is active | E7 or later | No |
| 20 | **Smaller, cache-friendly prompts.** Audience trimming plus a stable prefix with a trailing marker. | E7 | No |
| 21 | **Memory History and `sase-1e5`** ("memory as seen by agent") can key off bundle ids instead of a disk snapshot. | E4.4 / E6 | No |
| 22 | **`%dispatch` renders on the target host** with its own facts. No instruction bytes cross the wire. | Already true | No |

**The key observation: of 22 benefits, only #13 needs the full file gone, and it is the
smallest.** The roadmap ties "deliver explicitly" to "stop committing a readable file"
because of R7's original Codex constraint. That constraint no longer holds. None of the
four consolidated reports I read (R-delivery, R-fresh, the epics report, and the
readiness review) weighs GitHub or human readability of the full render as a cost. R-fresh
rejected keeping the full files for three reasons: wrong audience, 112 commits in 60
days, and conflicts across 47 workspaces. Benefit #14 addresses the first, and the
current churn data above weakens the other two.

## Costs and risks of keeping E3

- **Code volume.** `src/sase/instructions/` is 7,425 lines in 35 modules. The delivery
  modules add about 1.9k lines, the instruction tests about 6.2k lines (23 files), and
  sase-core has a v2 manifest wire. Much of that is E1 and E2 (the scoreboard and the
  compiler), which you would keep even after a revert.
- **Fragile provider surfaces.**
  - Claude's `--append-subagent-system-prompt-file` is hidden from `--help`.
  - Codex's `project_doc_max_bytes=0` behavior is undocumented.
  - Grok has a 120 KiB argv cap.
  - Muse depends on a prompt prefix.

  These are mitigated by the conformance check, the atomic fallback, and the sunset flags.
  The file-based world was fragile too: Grok's trust change silently cut its instructions
  to zero.
- **An untested behavior shift.** Claude's instructions moved from a user message to the
  system prompt. The watch metrics include spot-checking this, but there is no data yet.
- **Privacy.** With `home_layer = yes`, home details (tailnet and Obsidian triggers) now
  reach xAI and the Muse vendor too.
- **Landing friction during the epic.** The `sase-1ko` bead notes #7–#10 record other
  agents' landings failing on this epic's tests and Symvision symbols. I checked: the
  test patch target and the `_RunManifest` import are fixed at HEAD, and six of the seven
  flagged symbols are gone.
- **Thin evidence.** About 20 finished post-cutover runs. Codex explicit non-research
  shows 1 miss in 3. Muse can't soak until 10-19. Claude launch probes were pending
  install sync when the acceptance record was written.
- **Two artifacts to keep aligned** under option C. The parity test already does this,
  and it must stay in CI.

## Options in detail

### A. Soft revert (flags off)

Run `sase flag disable claude_explicit_instructions`, then the same for
`codex_explicit_instructions`, `grok_explicit_instructions`, and
`muse_explicit_instructions`, on athena, apollo, and mac. Each provider returns to E1's
after-state.

- **Kept:** the scoreboard, `show`, `readout`, manifests (now `inherits_native`), and the
  `sase-11s` fix.
- **Given back:** benefits 1–9.
- **Transparency gained:** none.

A hard revert (the commits plus the sase-core `feat!` wire v2 and the pin) costs more
and gives the same runtime behavior. Don't do it.

### B. Proceed as planned

E4 ships the export stub, `sase instructions sync`, gitignored projections, and the
last-known-good store. E5 handles the home files.

- **Gained:** benefits 13 and 14, plus every other benefit.
- **Lost:** a GitHub-readable full instruction set.
- **New machinery:** sync, the last-known-good store, and a bootstrap clause that asks
  models to run a command.

### C. Recommended: keep E3, re-scope E4 around a readable committed file

1. **Keep a full committed `AGENTS.md`,** generated by the same compiler and guarded by
   the existing parity test in CI. Choose its content:
   - **C1 (zero work):** today's runtime projection, as is.
   - **C2 (better audience):** the `mode: export` render (no `/sase_final` contract),
     plus a header like: "SASE-launched agents receive this plus the SASE runtime
     contract, a provider directive, and your home layer. Run `sase instructions render`
     to see the exact bundle." This also fixes benefit #14 for humans and non-SASE tools.
2. **Shrink the file set from 20 to 8.** Delete `GEMINI.md`, `QWEN.md`, and `OPENCODE.md`
   in all four directories: OpenCode never reads its file, and Qwen and agy double-load
   theirs. Keep `CLAUDE.md` as a one-line `@AGENTS.md` import, or delete it and rely on
   Claude 2.1.296's `AGENTS.md` fallback, which leaves 4.
3. **Drop from E4:** the stub, `sync`, the gitignored projections, the bootstrap clause,
   and the last-known-good store. The committed file stays the fallback substrate.
4. **Keep from E4–E6:** the Memory History and "as launched" row keyed to bundle ids, the
   docs and glossary updates, E5's interactive home renders, and E6's MEMORY deck.
5. **Treat E7 skeptically.** Audiences are the one direction that makes "read one file"
   impossible by design. Require the measured entry gate the roadmap already sets.

## Concrete next steps

1. **Let `sase-1ko.10` finish.** Ask that the `decisions:instructions-per-invocation`
   record state the transparency position explicitly. For example: "the committed
   `AGENTS.md` remains a parity-verified projection; untracking reopens only on a named
   trigger". Then a future E4 plan can't untrack it by default.
2. **Soak for 7 days**, with Muse starting after 10-19. Compare
   `sase instructions readout --since <first explicit>` with the attached baseline
   (pre-cutover misses: Claude 0/74, Codex 0%, Grok 6/85 (7%), Muse 11/231 (5%)). Also
   check that non-declared fallbacks stay at 0 and that `instructions.conformance` is OK.
3. **If the soak is clean, answer the flag beads with Remove.** If a provider regresses,
   disable that provider's flag only.
4. **Write E4 as option C.** If you want it now, file the "AGENTS.md as launched" fix and
   the docs and bundle-wording fixes as one small task through `/sase_new_task`. I didn't
   create one, because this research may change E4's scope.

## What would change this recommendation

- **Revert a provider (flag off)** if, after 7 days, its explicit-run misses are more
  than 2 points above baseline, any non-declared fallback appears, or spot checks show
  worse Claude behavior after the move to the system prompt.
- **Go back to the original E4 (untrack)** if any of these happens:
  - merge conflicts on generated files measurably slow landings;
  - E7 audiences ship and a single committed file becomes misleading;
  - outside contributors appear, so the stub's audience matters more than a full read.
- **Stop after E3 entirely** if the soak shows no measurable gain and you value
  simplicity. E3 plus a committed `AGENTS.md` is a defensible end state.

## Method and evidence

- **Bead `sase-1ko`** (via `sase bead read`): the description, decisions, 14 notes, spike
  results, the acceptance record `e3_acceptance_record.md` (probe rows for both flag
  states, the helper probe, declared gaps, and notes for E4), and the readout baselines.
- **Plans and research** (via `sase artifact read`):
  - `plan:202610/e3_explicit_delivery_cutover.md`;
  - `research:202610/memory_built_instruction_migration_epics/…` (the E1–E7 roadmap);
  - `research:202610/sase_md_instruction_delivery/…` (R-delivery: R1–R9, the 13 use
    cases);
  - `research:202610/fresh_clone_bootstrap_and_native_subagent_instructions/…` (R-fresh:
    the stub design and the refuted R7 fact);
  - `research:202610/e3_delivery_cutover_readiness_and_bundle_inspection/…` (the four
    meanings of "what it looked like" and the TUI row).
- **Live commands:**
  - `sase instructions render -f provider={claude,codex,grok,muse,agy}`, plus
    `-f mode=export` and `-f mode=interactive`, each diffed against `AGENTS.md`;
  - `sase instructions show research.1a.cld -l` / `-H`;
  - `sase instructions readout -s 2026-10-14T10:35:06Z -j`;
  - `sase flag list`.
- **Repo measurements:**
  - `git ls-files` finds 20 instruction files;
  - `git log --since='60 days ago' -- AGENTS.md` finds 88 commits (7 in 14 days, 83 of
    88 alongside memory or generator edits);
  - `wc -l` on `src/sase/instructions` and `tests/instructions`;
  - CI `sase init memory --no-commit`;
  - `test_render_parity.py` (the repo-level parity assertion);
  - `_instruction_boundary.py::_resolve_project_root`;
  - `launch_evidence.py` (`instruction_snapshot` is still captured).
