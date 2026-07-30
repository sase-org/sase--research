---
create_time: 2026-07-30
updated_time: 2026-07-30
status: research
---

# SASE Artifacts: Lifecycle, Capture Economics, and the Next Frontier

**Scope.** New improvement directions for SASE artifacts, measured against the working tree and the live artifact store
on 2026-07-30. This is a successor to `artifact_refs_and_inspector.md` (2026-07-29), not a restatement of it — that
report's agenda has largely shipped, and the binding constraint has moved.

---

## Bottom line

**The identity problem is solved. The economics problem is not.**

Yesterday's research diagnosed artifacts as "a path is not a durable name" and proposed a nine-item agenda. In the ~10
days spanning that work, seven of its nine items landed: kind-tagged references with fragment anchors, a read CLI, the
three missing record fields, a Files sub-tab, a real reader modal, a copy-as palette with OSC 52, and `@`-reference
completion in the prompt bar. That layer is now genuinely good.

What the measurements expose instead is that **SASE has an artifact ingestion policy of "capture anything that looks
like a media path," and no lifecycle policy at all.** The consequences are concrete:

| | |
| :--- | ---: |
| Store size | **662.0 MB** across **4,287** records |
| Window covered | **25 days** (2026-07-06 → 2026-07-30) |
| Mean growth | **26.5 MB/day** → **~9.7 GB/year**, unbounded |
| Records that are agent-declared (`explicit`) | **216 (5.0%)**, totalling **5.6 MB (0.8% of bytes)** |
| Records auto-captured by heuristic | **4,071 (95.0%)**, totalling **656.5 MB (99.2% of bytes)** |
| Captured from visual-snapshot test dirs | **3,950 records / 481.4 MB — 73% of the entire store** |
| — distinct logical files among those | **403** (so **3,547** are repeat captures) |
| — that are byte-identical to a *current* git golden | **391** |
| — that were explicitly declared by an agent | **0** |

**73% of the artifact store is repeat copies of 403 version-controlled PNG test goldens that no agent ever asked to
keep.** The curated corpus — everything an agent deliberately declared — is 5.6 MB. The store is 117× larger than its
own signal.

There is no `prune`, no retention config, no expiry, and no delete verb anywhere in the subsystem. `sase artifact
doctor` can backfill fields and re-verify digests, but it cannot remove a single byte.

So the next tranche is not more reference plumbing. It is: **fix what gets captured, add a lifecycle, then spend the
now-complete resolver on the consumers still blocked on it.**

---

## 1. What shipped since 2026-07-29 (verified)

The prior report's agenda, checked against the tree:

| # | Prior recommendation | Status |
| :--- | :--- | :--- |
| 1 | Tranche-zero defect fixes (copy mode, marks, `Y`, `cat`, `research` kind) | **mostly shipped** — copy-as palette and marks landed; see §5.4 for residue |
| 2 | Kind-tagged artifact reference grammar | **shipped** — `commit`/`chat`/`bug`/`file`/`bead`/`agent`/`document`, wire schema v2, fragment anchors (`lines`/`page`/`time`) |
| 3 | Read CLI + three record fields | **shipped** — `list`/`show`/`path`/`open`/`doctor`; `sha256`, `size_bytes`, `mime_type` at **100% coverage (4,287/4,287)** |
| 4 | `PreviewPanelModal` as a real reader | **shipped** — rendered-Markdown mode, in-document search, copy delivery, `$EDITOR` handoff, `CopyModeForwardingMixin` |
| 5 | Reach the rich viewer from the panel | **shipped** — Files sub-tab with its own keymap block in `default_config.yml` |
| 6 | Unified "Copy as…" palette + OSC 52 transport | **shipped** — `actions/clipboard/_delivery.py` emits OSC 52 with a 64 KiB guard and subprocess fallback |
| 7 | Marks and bulk actions across sub-tabs | **partial** |
| 8 | Artifact refs in the prompt bar | **shipped** — grouped `@` menu, fuzzy matching with highlight, entity refs resolve in prompt paths, bounded catalog caching |
| 9 | Vocabulary, footer, Jump All | **partial** |

The reference substrate is done and is in the right place — parsing, rendering, and resolution live in `sase-core`
behind `sase_core_rs`, with Python holding only wire models (`src/sase/artifact_ref_models.py`) and presentation. This
respects the `rust_core_backend_boundary` memory and needs no revisiting.

**Index integrity is also perfect.** Scanning `~/.sase/artifacts/`:

- Files on disk: **4,287** — exactly the index count.
- **Orphans (on disk, unindexed): 0.**
- **Index rows whose stored file is missing: 0.**

The store keeps its promises. That is precisely why the remaining problems are not integrity problems.

---

## 2. The capture heuristic is the root cause

### 2.1 Mention is treated as authorship

Default artifact capture is a **regex sweep over the agent's own prompt files**. `artifact_file_defaults.py` globs
`*_prompt.md` in the agent's artifacts directory (`_prompt_source_files`, :304) and applies:

```python
_PROMPT_MEDIA_SUFFIX_PATTERN = "|".join(_PROMPT_IMAGE_SUFFIXES | _PROMPT_VIDEO_SUFFIXES)
rf"""(?P<path>(?:~|/|\.{{1,2}}/|[A-Za-z0-9_.-]+)[^\s"'`<>]*?\.(?:{_PROMPT_MEDIA_SUFFIX_PATTERN}))"""
```

Every resolvable image or video path **mentioned anywhere in a prompt** is copied into the permanent store with
`explicit=False` (`_default_artifact_file`, :385).

There is no test of authorship. An agent that is *asked to look at* a golden PNG, *told about* a snapshot diff, or
handed a path for context mints a permanent 120 KB copy of a file that is already in git. The heuristic cannot
distinguish "I made this" from "someone showed me this," and it defaults to keeping.

### 2.2 What that costs, measured

| Cohort | Records | Bytes | Dead `source_path` |
| :--- | ---: | ---: | ---: |
| **Explicit** (agent-declared) | 216 | **5.6 MB** | 12 / 216 (**5.6%**) |
| **Default** (heuristic) | 4,071 | **656.5 MB** | 1,213 / 4,071 (**29.8%**) |

The explicit cohort is small, durable, and lands in persistent SDD sidecars. The heuristic cohort is 117× its size by
bytes and rots at 5× the rate, because **95% of all captured sources sit under ephemeral `sase_<N>` workspaces** that
get recycled.

Narrowing to the dominant contributor:

- **3,950 records / 481.4 MB** have a `source_path` under a `snapshots/png` directory.
- They span only **403 distinct labels**. The top label, `agents_collapsed_panel_120x40.png`, was captured **32 times**.
- **3,547 of the 3,950 are repeat captures** of a golden that had already been captured.
- **0 of the 3,950 were explicitly declared.**

Drop the snapshot captures and the entire rest of the store is **337 records / 180.6 MB**.

### 2.3 Why content-hash dedup is the wrong fix

The tempting fix — content-address the store — barely helps:

- Distinct `sha256` values: **4,180 / 4,287.**
- SHAs with duplicates: **94.** Redundant copies: **107.** Recoverable: **~36 MB (5%).**

The 3,547 repeat snapshot captures mostly are *not* byte-identical, because each capture caught the golden at a
different revision as it evolved. Deduplication cannot collapse them. **But git already stores exactly that revision
history**, which is the real point: these files are already durably addressable, and the grammar to name them —
`commit:<repo>@<sha>` — now exists.

The fix is not to store them more cleverly. It is to **not store them**, and reference them instead.

---

## 3. There is no lifecycle at all

Verified absences across the subsystem:

- **No retention configuration.** `default_config.yml` has an `artifacts:` block, but it configures the Artifacts *tab's*
  panes, not the store. No max-age, max-size, or per-kind policy exists.
- **No prune, GC, expire, or delete verb.** `sase artifact` exposes `create`, `doctor`, `list`, `open`, `path`, `show`.
  Nothing removes anything. (The `_prune_*` symbols in `event_refresh/_artifact_delta.py` prune an in-memory TTL
  registry of expected deletions — unrelated to storage.)
- **`doctor` is integrity-only** — `--fix` backfills enrichment fields, `--verify` re-hashes stored files. It reports
  nothing about size, growth, redundancy, or what is safe to discard.

The store has been accumulating for 25 days. At 26.5 MB/day it reaches roughly **9.7 GB/year** with no mechanism that
would ever reclaim a byte. This is tractable on a home server today and untenable as a shipped default.

The signal-to-noise cost lands before the disk cost, though. The Files sub-tab and `sase artifact list` present 4,287
rows of which **3,950 are test goldens** — so the browsing surface that shipped last week is showing users a corpus
that is 92% noise by count. Every affordance built in items 4–8 of the prior agenda is being spent on the wrong
documents.

---

## 4. Consumers still blocked, and a graph that isn't recorded

### 4.1 The mobile gateway is still handed an opaque path

`docs/mobile_gateway.md:461` still describes `artifact_dir` as "a host path… clients should treat a non-null
`artifact_dir` as an opaque host path for display, retry context, and host-bridge follow-up." It serves **no artifact
content**.

Yesterday's report flagged this consumer as blocked on the missing resolver. **That resolver now exists**, is in
`sase-core` where every frontend can reach it, and has a stable wire schema. The gateway is the first non-TUI consumer
and is now unblocked but unwired — the cheapest possible proof that putting the resolver in core paid off.

### 4.2 Production is recorded; consumption never is

Every record carries rich provenance about its *producer*: `agent_name`, `workflow`, `raw_timestamp`,
`agent_artifacts_dir`, `workspace_dir`, `project`. Nothing anywhere records that an artifact was **used**.

This matters more now than it did a week ago, because `@`-reference expansion at launch (prior item 8, shipped) created
the exact interception point where consumption becomes observable: when a ref expands into a concrete path in a prompt,
that is an artifact being handed to an agent. Recording it would yield:

- **"What used this?"** — the inverse query, which no surface can answer today.
- **Safe pruning.** A consumed artifact is evidence in some agent's history; an unconsumed 32nd copy of a golden is not.
  Consumption data makes retention decisions defensible rather than heuristic.
- **Lineage.** Artifact → agent → artifact chains, which is what makes a multi-agent run auditable after the fact.

This is a small append at a point that already exists, and it is the difference between a store and a graph.

### 4.3 No content search

`sase artifact list -q` filters case-insensitive substrings over **label and paths only** — never file contents. The
text-bearing corpus is **213 records totalling 0.3 MB**. That is small enough that a naive read-and-grep is instant and
needs no index, and it is exactly the cohort with the highest per-byte value (markdown reports, explicit deliverables).
An agent handed "find the research note about X" has no way to search for X.

---

## 5. Smaller findings

**5.1 Reference persistence stops at plans.** The `sase-9z` epic made bead→plan links durable via `plans:` refs. The
generalized grammar now covers six more kinds, but beads and ChangeSpecs still persist no artifact references — the
mechanism proven for one kind was never spent on the others.

**5.2 Cross-project artifacts are effectively single-project.** 4,270 of 4,287 records belong to `gh_sase-org__sase`;
13 to `bob-cli`; 4 to `home`. Project scoping works but is untested at any real multi-project scale.

**5.3 Producer concentration is extreme.** 587 distinct agents produced artifacts, but **23 agents produced more than
50 each**, topping out at 179. Those are overwhelmingly the visual-snapshot workers of §2.2 — a per-agent capture cap
would be a crude but effective circuit breaker.

**5.4 Residue from the prior tranche zero.** The raw-`cat` fallback still exists at
`ace/tui/graphics/_viewer_loop_media.py:233` and `ace/tui/actions/hints/_files.py:256` (`viewer = "bat" if
shutil.which("bat") else "cat"`) — still no `--` argument boundary and no binary/control-sequence neutralization on the
`bat`-absent path. Small, cheap, still open.

---

## 6. What not to do

- **Do not build a content-addressed store.** Measured recovery is ~36 MB of 662 MB (§2.3). It solves 5% of the problem
  at the cost of a storage-layout migration.
- **Do not rebuild an artifact graph subsystem.** The 2026-05-05 artifact graph was deleted 24 hours later
  (12,898 deletions). Consumption logging (§4.2) is an append to an existing call site, not a subsystem — keep it that
  way.
- **Do not extend the reference grammar further yet.** Seven kinds, fragments, and drift recovery are enough. Spend the
  grammar on consumers (§4.1, §5.1) before widening it.
- **Do not delete anything automatically in v1.** Retention should ship as report → dry-run → opt-in. The store is
  currently 100% intact and that trust is worth preserving through the change that first makes deletion possible.
- **Do not solve this with a bigger disk.** The dominant cost is that the browsing surfaces are 92% noise, and disk
  space does not fix a signal-to-noise ratio.

---

## 7. Ranked recommendations

Ordered by (value × confidence) ÷ cost. Items 1 and 2 are complements — 1 stops the inflow, 2 drains what has already
pooled — and together they address 73% of the store.

### 1. Make capture mean authorship, not mention — *S–M, highest confidence, largest effect*

Replace the bare regex-match-and-keep in `artifact_file_defaults.py` with a capture predicate. Keep a mentioned media
file only when at least one holds:

- its `source_path` lies inside the agent's own artifacts directory or was created/modified during the agent's run;
- it is **not** a tracked file in a known repo — if it is, record a `commit:<repo>@<sha>` reference instead of copying
  bytes, using the grammar that already exists;
- the agent declared it explicitly (today's `explicit=True` path, unchanged).

Add a per-agent capture cap as a circuit breaker (§5.3). This cuts intake by roughly 73% while preserving every one of
the 216 records anyone actually asked for, and it is a single predicate at a single call site.

**Ship this first — it is the only item that makes the others smaller.**

### 2. Give the store a lifecycle: `sase artifact prune` + retention policy — *M*

Three staged pieces, in order:

1. **Report.** Extend `doctor` to surface economics: bytes by kind/project/agent, growth rate, redundant-capture
   counts, and what a policy *would* reclaim. Read-only, immediately useful.
2. **`sase artifact prune --dry-run`** with predicates matching the measurements — by age, by kind, by
   redundant-label-generation (keep the newest N captures of a given label), by size.
3. **Retention config** under `artifacts:` with an explicit opt-in default of *disabled*.

Hard protections regardless of policy: never prune `explicit=True`; never prune anything referenced by a bead, plan, or
ChangeSpec; never prune anything with recorded consumption (item 4).

### 3. Serve artifact content through the mobile gateway — *S–M, unblocks the first non-TUI consumer*

Replace the opaque `artifact_dir` host path with resolver-backed endpoints: list artifacts for an agent, resolve a
reference, stream content with the correct `mime_type` (now populated at 100%). Every piece of the backend this needs
already exists in `sase-core`; this is wiring, and it is the proof that the resolver's placement was correct.

### 4. Record artifact consumption at `@`-ref expansion — *S, converts the store into a graph*

Log an append-only consumption event where references already expand to concrete paths at launch: `(ref, resolved
path, consuming agent, timestamp)`. Then expose `sase artifact show <ref>` → "used by N agents" and a `--unused`
filter on `list`. Small, and it is what makes item 2's pruning defensible instead of merely aggressive.

### 5. Add content search to `sase artifact list` — *S*

A `--grep PATTERN` that reads text-like artifacts (213 records / 0.3 MB — no index required) and reports matching
records with line context. Reuse the existing fragment anchors so a hit renders as `file:<id>#L12-L18`, which is
already a resolvable reference.

### 6. Persist artifact references on beads and ChangeSpecs — *M, reruns a proven playbook*

Apply the `sase-9z` pattern to the generalized grammar: persist refs on new records, render logical-ref-plus-resolved-
path in `show`, and validate with a doctor. Highest value for `research:` and `file:` refs, which currently have no
durable home in any spec.

### 7. Finish the prior tranche's residue — *S, bundle with anything*

Neutralize the raw-`cat` fallback (§5.4): add `--`, bound the read, detect binary, strip control sequences.

---

## 8. Open questions

1. **Does an agent merely *reading* a golden PNG deserve a stored copy at all?** Item 1 assumes no. If the answer is
   sometimes yes — e.g. to preserve what the agent actually saw when the golden later changes — then the reference
   should carry the resolved `commit:<repo>@<sha>` at read time rather than the bytes, which costs ~0 and is strictly
   more informative.
2. **Retention default.** Ship disabled (safe, no reclamation until asked) or ship with a generous default like
   "keep explicit forever, keep the newest 3 captures per label, keep everything under 90 days"?
3. **Is the 25-day window the true history?** The store's oldest record is 2026-07-06, consistent with the sharded
   artifact migration. Worth confirming nothing older was silently dropped before designing a retention policy around
   the observed growth rate.
4. **Should item 1 be retroactive?** The predicate fixes new intake. Applying it to the existing 3,950 snapshot
   captures is exactly item 2's job — but it could equally ship as a one-shot `doctor --fix` migration.

---

## Appendix: method

All figures were measured on 2026-07-30 against the live store at `~/.sase/artifacts/index.jsonl` (4,287 records) and
the working tree at `sase_19`. Corpus statistics come from direct traversal of the index and the on-disk store; the
git-golden comparison hashes the 392 tracked PNGs under `tests/ace/tui/visual/snapshots/png` and matches them against
recorded `sha256` values. Shipped-status claims in §1 were verified by reading the named source files and by invoking
`sase artifact --help` and its subcommands, not from commit messages alone.
