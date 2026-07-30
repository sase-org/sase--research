---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Artifacts: Capture Policy and Retention

Consolidated from two independent research passes (`__a`, codex/gpt-5.6-sol; `__b`, claude/opus) plus a third
verification pass. All measurements below were re-derived independently on 2026-07-30 against the live store
(`~/.sase/artifacts/index.jsonl`, 4,288 rows) and the working tree at `sase_16`.

---

## Bottom line

Both reports independently reached the same top-level conclusion, and the verification pass confirms it: **the artifact
*identity* problem is solved; the artifact *intake* problem is not.** The reference grammar, resolver, read CLI, record
enrichment, Files pane, and `@`-completion all landed in the last ten days and are in the right architectural place.
Building more reference surface would solve last week's problem.

The verification pass sharpens the diagnosis beyond what either report reached:

> **94.2% of the artifact store's bytes (623.6 MB across 3,999 records) are copies of files that are tracked in a git
> repository SASE already knows about. Zero of those 3,999 records were declared by an agent.**

Report `__b` framed this as a 73% snapshot-golden problem. That undercounts it by 21 points and points at the wrong
predicate. The demo GIFs under `demos/out/` (up to 12.3 MB each, captured four-plus times at different revisions), the
`docs/images/` PNGs, and the research-sidecar infographics all exhibit the identical pathology and are all
version-controlled. The right rule is not "stop capturing snapshots." It is **"never copy bytes that version control
already stores"** — one predicate, uniform coverage, 21 points more effective.

Everything else follows from that. The recommended path is: fix intake, make declaration non-destructive so declaration
is actually usable, then add retention to drain what has already pooled, then spend the completed resolver on the
consumers still blocked on it. Composition features (bundles, contracts, aliases, attestations) are real but presuppose
a curated corpus that does not exist yet.

---

## 1. What both reports established (verified)

Re-measured independently; both reports' figures reproduce within one record of drift.

| Measure | Value | Notes |
| :--- | ---: | :--- |
| Indexed records | 4,288 | `__a` 4,287, `__b` 4,287 — drift is this session's own capture |
| Stored bytes | 662.0 MB | |
| Window | 25 days (2026-07-06 → 2026-07-30) | |
| Explicit (agent-declared) | 217 rows / **5.56 MB** (0.84% of bytes) | |
| Default (heuristic-captured) | 4,071 rows / **656.5 MB** (99.2% of bytes) | |
| Snapshot-sourced captures | 3,950 rows / 481.4 MB / **403 distinct labels** / **0 explicit** | |
| Dead `source_path` | explicit 12/217 (5.5%) · default 1,215/4,071 (**29.8%**) | heuristic cohort rots 5× faster |
| Missing stored files / bad digests | **0 / 0** | store integrity is perfect |
| Duplicate-digest groups / redundant rows | 94 / 107 | |
| Reclaimable by exact dedup | **35.8 MB (5.4%)** | both reports agree on the number |
| Kinds | image 4,051 · markdown 212 · file 25 | |
| Text-bearing corpus | 214 rows / **0.32 MB** | search target is trivially small |

Both reports are also correct that **there is no lifecycle at all**: `sase artifact` exposes `create`, `doctor`, `list`,
`open`, `path`, `show` and nothing that removes anything; `doctor` is integrity-only; `default_config.yml`'s `artifacts:`
block configures the Artifacts *tab*, not the store.

Two claims unique to one report each, both verified true:

- **`__a`: `sase artifact create` destroys the source.** Confirmed. `src/sase/artifact_cli/create.py:36` hardcodes
  `move=True`; `_store_file` then calls `source.unlink()` (`artifact_file_explicit.py:220,234`). The library default is
  `move=False`, the automatic-capture path passes `move=False` (`:131`), and **no `--copy`/`--move` flag is exposed**.
  `__b` missed this entirely.
- **`__b`: capture is a regex sweep over prompt text.** Confirmed. `artifact_file_defaults.py` globs `*_prompt.md` in
  the agent's artifacts dir and copies every resolvable media path *mentioned anywhere in the prompt*, with
  `explicit=False`. There is no authorship test. `__a` never examines the capture path — the most consequential gap in
  that report.

---

## 2. The corrected diagnosis: version control, not snapshots

Classifying every record by whether its `source_path`, taken relative to its originating workspace, is tracked in a
repo SASE knows:

| Bucket | Rows | Bytes | % of store |
| :--- | ---: | ---: | ---: |
| Tracked in the main repo | 3,985 | 600.8 MB | **90.8%** |
| Tracked in a sidecar (research/plans) | 14 | 22.8 MB | **3.4%** |
| Untracked workspace file | 66 | 32.3 MB | 4.9% |
| Outside any workspace | 223 | 6.1 MB | 0.9% |
| **Reproducible from version control** | **3,999** | **623.6 MB** | **94.2%** |
| — of those, explicitly declared | **0** | 0 | — |

The tracked cohort is not one pathology but four instances of one: 392 tracked snapshot goldens, 28 tracked files under
`demos/`, 43 under `docs/images/`, and 192 tracked infographics in the research sidecar. The non-snapshot default cohort
alone is 121 rows / 175.0 MB across only **51 distinct labels** — the same repeat-capture signature, at the same ratio,
on files that are equally durable in git. `sase_ace_multi_model_fanout.gif` appears four times at 12.27, 8.54, 3.84 and
1.94 MB: four revisions of one tracked demo, 26.6 MB, none declared.

This also settles why exact-content dedup cannot help (§3.1): repeat captures are *different revisions*, so they are not
byte-identical — but git already stores precisely that revision chain, losslessly, which is the actual point.

**Calibration.** `__b` argues the growth rate (26.5 MB/day → ~9.7 GB/year) makes this "untenable as a shipped default."
That overstates the disk case. `~/.sase` totals 4.36 GB, of which the artifact-file store is 666 MB (15%); the per-run
agent artifact directories under `~/.sase/projects/gh_sase-org__sase/artifacts` are **2.49 GB — 3.7× larger**. Disk is
not the crisis. `__b`'s *other* argument is the correct one and should carry the case: the Files sub-tab and
`sase artifact list` present a corpus that is **93% noise by count**, so every affordance shipped in the last tranche is
being spent on documents no one asked to keep. The 5.56 MB anyone actually declared is buried under 656 MB nobody did.

---

## 3. Conflicts between the two reports, resolved

### 3.1 Content-addressed storage — `__a` ranks it #3, `__b` says don't. `__b` is right.

Both measured the same thing: 94 duplicate-digest groups, 107 redundant rows, **35.8 MB (5.4%)** recoverable. `__a`
ranks a SHA-256 blob layer third; `__b` names it explicitly under "what not to do."

The evidence is decisive against `__a` here. CAS addresses 5.4% of the store at the cost of a storage-layout migration;
the version-control predicate addresses 94.2% at the cost of one function. And CAS structurally *cannot* collapse the
dominant cost, because the repeat captures differ by revision.

`__a`'s secondary arguments for CAS — retention becomes reference counting, integrity becomes inherent, export gets
cheaper — are sound as design arguments and not as savings arguments. They would justify CAS only if something else
already required it. Nothing does. **Defer indefinitely; revisit only if a future feature needs blob identity for its
own reasons.**

### 3.2 Root cause — `__a` starts at lifecycle, `__b` starts at capture. `__b` is right, but they are complements.

`__a`'s plan drains the pool without closing the tap: its Phase A is retention fields, pin/promote, stats, and dry-run
GC, with no mention of why 656 MB arrived. `__b`'s ordering is correct — fixing intake makes the retention job roughly
20× smaller *and* far less frightening, because the pruning target stops being "662 MB of mostly-unclassified media" and
becomes "623 MB of provably reproducible copies."

But `__a` is right that retention is needed regardless: the 623.6 MB already pooled will not drain itself, and a capture
predicate is not retroactive. `__b` says this too. Ship both, in that order.

### 3.3 `commit:<repo>@<sha>` cannot do what `__b` asks of it — and the fix is not a grammar change

`__b`'s recommendation #1 says: when a mentioned file is tracked, "record a `commit:<repo>@<sha>` reference instead of
copying bytes, **using the grammar that already exists**." Tested against the live grammar, that does not work:

```text
commit:sase@c135dcbd6              -> ok   payload {repo, sha}
commit:sase@c135dcbd6#tests/x.png  -> ERROR  "commit references do not support fragments"
```

A commit ref carries `{repo, sha}` and nothing else, and fragments are rejected for that kind (`file:`, `chat:`,
`research:` and friends do accept `#L12-L18` line fragments). Naming *a file inside* a commit needs `repo + sha + path`,
which the grammar cannot express. Worse, extending it would contradict `__b`'s own §6 — "do not extend the reference
grammar further yet."

**Resolution: extend the artifact *record*, not the grammar.** Add three nullable VCS-provenance fields —
`vcs_repo`, `vcs_sha`, `vcs_relpath` — alongside the existing `source_path`. When capture sees a tracked file, it writes
a record with those fields populated and **no stored bytes**; the resolver materializes content on demand via
`git show <sha>:<relpath>` against the canonical repo checkout (resolved through repo *identity*, not the recorded
ephemeral workspace path, which is gone 30% of the time).

This is a well-trodden path in this codebase: the prior tranche added exactly three record fields (`sha256`,
`size_bytes`, `mime_type`) and backfilled them to 100% coverage via `doctor --fix`. The migration mechanism is proven
and the grammar stays frozen, which is what `__b` actually wanted.

### 3.4 Lineage — `__a`'s run manifests vs `__b`'s consumption log. Take `__b`'s wedge, `__a`'s schema.

`__a` proposes a per-run `artifact_manifest.json` recording inputs, outputs, roles, and contracts. `__b` proposes an
append-only consumption event logged where `@`-refs already expand to concrete paths at launch.

Production provenance is *already* recorded richly on every record (`agent_name`, `workflow`, `raw_timestamp`,
`agent_artifacts_dir`, `workspace_dir`, `project`). So `__a`'s manifest largely duplicates data that exists, to gain the
one thing that does not: consumption. `__b`'s version gets that same missing half as an append at a call site that
already exists — a fraction of the work for the decisive part of the value, and it is what makes pruning defensible
rather than merely aggressive.

Take `__b`'s mechanism now. Keep `__a`'s typed-role vocabulary (`source`, `report`, `image`, `test-result`) as the shape
of the logged edge, so the later increment is additive rather than a rewrite. Both reports independently reject
rebuilding the generic artifact graph deleted on 2026-05-06 (12,898 deletions); that rejection stands.

### 3.5 Composition features — `__a`-only, and premature

Bundles, declared output contracts, versioned collections with aliases, provenance attestations, and MCP/A2A export
adapters are `__a`'s items 4–8. They are well-argued and the external survey behind them (W&B TTLs and aliases, GitLab's
explicit *Keep*, OCI's descriptor/subject split, A2A's multi-part artifact, MCP's size-annotated resource links) is the
most valuable original contribution in either report — it is where the record-vs-blob separation and the
"default expiry plus an auditable promotion mechanism" pattern come from, and both should shape the retention design.

But every one of those features presupposes a curated corpus. Bundling, aliasing, and attesting over a store that is 93%
noise by count optimizes the wrong layer. Attestations in particular are the weakest fit: they exist to cross a trust
boundary, and this is a single-user home server. Defer the whole tranche behind capture and retention; revisit bundles
first, since the multi-part deliverable (report + infographic + data) is a real and recurring shape in this repo's own
research output.

---

## 4. What already exists that de-risks this

Neither report checked the following, and all four findings lower the cost or risk of the recommendations.

**A Rust-backed deletion path already exists — for the other tier.** `sase_core_rs` exports `delete_agent_artifacts`,
`delete_agent_artifact_index_row`, and `delete_agent_artifact_index_row_bounded`, driven from
`ace/tui/actions/agents/_dismissing.py` and a four-module Agent Cleanup panel (`X` on the Agents tab) with per-agent,
marked, group, tribe, clan, and custom scoping. So SASE has a mature, Rust-owned, UI-driven GC for the 2.49 GB
agent-directory tier and **nothing at all** for the 666 MB artifact-file tier. Retention is not a new pattern to invent;
it is a proven one to extend to the tier that was skipped. Design it once, in Rust core, so both tiers share it — the
`rust_core_backend_boundary` litmus test applies directly, and the mobile gateway is exactly the second frontend it
predicts.

**A retention-config precedent already exists.** `default_config.yml` ships `tasks.history_limit: 100` — "Running tasks
are never pruned… the oldest finished tasks (and their logs) are removed first." That is precisely the shape both
reports propose (count-based cap plus a protected class). Reuse the vocabulary rather than inventing one.

**SQLite is already in this subsystem.** `~/.sase/agent_artifact_index.sqlite` (76 MB) and `chats_catalog.sqlite`
(13.9 MB) exist. `__a` hedges that search "does not require a database"; `__b` says `--grep` needs no index. Both are
right that the 0.32 MB text corpus needs nothing fancy — but if an index ever helps, the dependency and the pattern are
already here.

**The bead backlog is clear.** The only artifact-related bead is `sase-b3` (fuzzy artifact-reference completion), whose
work landed in commits `b6b51f239`/`835536a84`. No planned work competes with any recommendation below.

**Declaration is being adopted, not ignored.** Explicit creations per day over the last week: 20, 24, 15, 18, **36, 34**.
The declared cohort is small in *bytes* (markdown is small) and growing steadily in *use*. The correct reading of "5% of
records are explicit" is not "agents won't declare" — it is "the heuristic drowns a healthy signal."

**The causal link neither report drew.** Because `sase artifact create` unlinks the source, it is unusable for exactly
the artifacts that matter most — a research report, a plan, a doc that must stay in the repo to be committed. An agent
that declares such a file loses it from the working tree. That plausibly explains both why the explicit cohort is small
and why a permissive heuristic sweep exists to compensate. **Copy-by-default is therefore not a safety nit; it is the
precondition that makes "declare, don't sweep" a viable policy.** `__a` ranked it as a sub-bullet of its #1; it deserves
to be sequenced ahead of the capture predicate, because it is a two-line change that removes the reason the sweep is
load-bearing.

---

## 5. Ranked recommendations

Ordered by (value × confidence) ÷ cost. Items 1–3 are one coherent tranche and should ship together or in immediate
succession; 1 removes the excuse for the sweep, 2 closes the tap, 3 drains the pool.

### 1. Make `sase artifact create` copy by default — *XS, highest confidence*

Flip `move=True` → `move=False` at `artifact_cli/create.py:36`; add an explicit `--move` opt-in; print both source and
stored paths. Update the `sase_artifact_file` skill, which currently instructs agents to create a file and register it —
a sequence that silently deletes their work. Two lines plus docs, and it unblocks item 2 by making declaration the
obviously-correct path for durable deliverables.

### 2. Make capture mean authorship, and never copy what version control stores — *S–M, largest effect*

Replace the regex-match-and-keep in `artifact_file_defaults.py` with a capture predicate. Keep bytes only when the path
is **not** resolvable from version control. When it is tracked, write a record with `vcs_repo`/`vcs_sha`/`vcs_relpath`
populated and no stored bytes (§3.3) — the record, its label, and its provenance survive; only the redundant copy goes.
Evaluate at finalization, after the commit finalizer runs, so a file the agent authored *and committed* resolves to its
committed revision while a file it authored and left uncommitted is still copied.

Secondary clauses, in priority order after the VCS test: keep if the source lies inside the agent's own artifacts
directory or was created/modified during the run; keep if declared explicitly. Add a per-agent capture cap as a circuit
breaker (23 agents produced more than 50 artifacts each, topping out at 179).

This addresses 94.2% of intake while preserving every one of the 217 records anyone asked for. **Ship this before
anything else in the tranche — it is the only item that makes the others smaller.**

### 3. Give the store a lifecycle: report → dry-run → opt-in retention — *M*

Three stages, strictly in order:

1. **Report.** Extend `doctor` with economics: bytes by kind/project/agent, growth rate, redundant-capture counts,
   version-control-reproducible share, and what a policy *would* reclaim. Read-only and immediately useful.
2. **`sase artifact prune --dry-run`** with predicates matching the measurements: by age, by kind, by
   redundant-label-generation (keep the newest N captures per label), by size, by VCS-reproducibility. Move to a trash
   directory with a grace period before purge; never hard-delete in v1.
3. **Retention config** under `artifacts:`, defaulting to *disabled*, following the `tasks.history_limit` vocabulary.

Hard protections regardless of policy: never prune `explicit=True`; never prune anything referenced by a bead, plan, or
ChangeSpec; never prune anything with recorded consumption (item 5). Build the deletion primitives in Rust core beside
`delete_agent_artifacts` (§4) so the agent-directory tier and the mobile gateway inherit them.

Applying item 2's predicate retroactively to the existing 3,999 tracked-source records is this item's job, and can ship
as a one-shot `doctor --fix` migration once the trash stage is trusted.

### 4. Serve artifact content through the mobile gateway — *S–M, unblocks the first non-TUI consumer*

`docs/mobile_gateway.md:461` still calls `artifact_dir` "an opaque host path"; the gateway serves no artifact content.
The resolver that would fix this now exists in `sase-core` with a stable wire schema, and `mime_type` is at 100%
coverage. Replace the opaque path with resolver-backed endpoints: list an agent's artifacts, resolve a reference, stream
content. This is wiring, not design, and it is the cheapest available proof that putting the resolver in core paid off.

### 5. Record artifact consumption at `@`-ref expansion — *S, converts a store into a graph*

Append `(ref, resolved path, consuming agent, timestamp, role)` where references already expand to concrete paths at
launch. Expose "used by N agents" in `show` and a `--unused` filter on `list`. Small, and it is what makes item 3's
pruning defensible rather than merely aggressive. Use `__a`'s typed-role vocabulary on the edge so later lineage work is
additive (§3.4).

### 6. Add `--grep` content search to `sase artifact list` — *S*

The text-bearing corpus is 214 records / 0.32 MB — read-and-grep is instant and needs no index. Render hits as
`file:<id>#L12-L18`, reusing the line fragments the grammar already supports, so a search result is itself a resolvable
reference. Today `-q` matches labels and paths only, so an agent told "find the research note about X" cannot search
for X.

### 7. Persist artifact references on beads and ChangeSpecs — *M, reruns a proven playbook*

The `sase-9z` epic made bead→plan links durable via `plans:` refs. The grammar now covers seven kinds, but beads and
ChangeSpecs still persist none of them. Highest value for `research:` and `file:` refs, which have no durable home in
any spec today.

### 8. Finish the prior tranche's residue — *XS, bundle with anything*

The raw-`cat` fallback at `ace/tui/graphics/_viewer_loop_media.py:233` and `ace/tui/actions/hints/_files.py:256`
(`viewer = "bat" if shutil.which("bat") else "cat"`) still has no `--` argument boundary and no binary/control-sequence
neutralization on the `bat`-absent path.

### Deferred, with reasons

- **Content-addressed blob storage** — 5.4% of the problem, structurally unable to touch the other 94% (§3.1).
- **Bundles, output contracts, versioned collections, aliases** — sound designs that presuppose a curated corpus; revisit
  after items 2–3, bundles first (§3.5).
- **Provenance attestations, MCP/A2A export adapters** — trust- and interop-boundary features with no boundary to cross
  on a single-user host. Keep `__a`'s survey as the design reference for when one appears.
- **Further reference-grammar extension** — seven kinds and line fragments are enough. Spend the grammar on consumers
  (items 4, 7) before widening it.
- **Semantic/vector search** — both reports reject it and both are right; 0.32 MB of text does not need embeddings.

---

## 6. Open questions

1. **Should a tracked-file capture keep a record at all, or nothing?** Item 2 keeps a byte-free record with VCS
   provenance, which costs ~0 and preserves the "this agent looked at this" signal. The alternative — capture nothing —
   is simpler but loses that. Recommend the record.
2. **Retention default.** Ship disabled (nothing reclaimed until asked) or with a generous default such as "keep explicit
   forever, keep the newest 3 captures per label, keep everything under 90 days"? `__b` raises this; the answer should
   probably be *disabled in v1, generous default in v2*, once the trash stage has been exercised.
3. **Is 25 days the true history?** The oldest record is 2026-07-06 and the subsystem was renamed on 2026-07-17
   (`2443fc80e feat!: rename explicit artifacts to artifact files`), so the index may have been rebuilt. Worth
   confirming before designing a policy around the observed growth rate.
4. **Should retention cover the 2.49 GB agent-directory tier in the same pass?** It is 3.7× larger and already has the
   Rust primitives and a cleanup UI. Doing both at once is more design work but avoids building the policy layer twice.

---

## Appendix: method and divergences

All figures re-derived on 2026-07-30 by direct traversal of `~/.sase/artifacts/index.jsonl` (4,288 rows, unwrapped from
the `{schema_version, artifact}` envelope) and the on-disk store, plus `git ls-files` against the main repo and the
research sidecar. Version-control classification maps each `source_path` to its path relative to the originating
`sase_<N>` workspace and tests membership in the current tracked set — the same test that determines whether a
`git show <sha>:<relpath>` reference would resolve. Grammar claims in §3.3 come from calling
`sase_core_rs.artifact_ref_parse` directly. Shipped-status claims were verified by reading the named source files and
invoking `sase artifact --help`.

Where the source reports diverge from this one:

- Both reports state 4,287 records; the live index is 4,288 (this session's own capture — a small demonstration of §2).
- `__b` states 216 explicit records / 213 text records; the live values are 217 and 214, same drift.
- `__a` states that automatic default capture uses the safer copy path while `create` moves. Verified correct.
- `__a` does not examine the capture heuristic at all, and consequently ranks storage-layout work (CAS) third where the
  evidence puts intake policy first.
- `__b` scopes the problem to snapshot goldens (73%); the version-control framing raises it to 94.2% and yields a
  simpler predicate.
- `__b`'s `commit:<repo>@<sha>` substitution does not work against the current grammar; §3.3 supplies a replacement that
  honors `__b`'s own constraint against extending it.
