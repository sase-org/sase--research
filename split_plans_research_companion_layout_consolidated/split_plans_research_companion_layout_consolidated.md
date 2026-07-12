# Split Plans / Research Companion Layout

*Phase 7 smoke test — consolidated report, 2026-07-11*

**Result: Pass.** Two independent agents each wrote a report and infographic into the research
companion; both confirmed the split layout is present, resolvable, and writable.

## Question

How does SASE store SDD artifacts once a managed GitHub project has been split into **plans** and
**research** companion repositories, and how do consumers resolve each kind?

## Summary

Newly initialized or migrated managed GitHub projects no longer keep SDD content in a single
`<repo>--sdd` store. They use a **schema-version 2** store record with `storage: companion_repos`
that names two public companions and their remotes:

- `<owner>/<repo>--plans` — approved plans, prompt snapshots, and bead state.
- `<owner>/<repo>--research` — durable research reports and generated media.

That store record — **not** clone or remote existence — is the layout authority. Legacy
single-root records are untouched and keep working.

## Layout

| Kind       | Path                                         | Cloned            |
| ---------- | -------------------------------------------- | ----------------- |
| `plans`    | `<workspace>/sase/repos/<repo>--plans`       | Eagerly (default) |
| `beads`    | `<workspace>/sase/repos/<repo>--plans/beads` | With plans        |
| `research` | `<workspace>/sase/repos/<repo>--research`    | Lazily, on demand |

Both companions are independent Git roots that sit as siblings under `sase/repos/`, keeping durable
SDD artifacts near the source checkout without mixing their lifecycles. Each uses month-based
directories at its root: the plans companion holds `<YYYYMM>/*.md` and `<YYYYMM>/prompts/*.md` with
`beads/` beside them and is synchronized during normal workspace preparation; the research companion
stores each `<YYYYMM>/` report next to its `*_infographic.png` and stays dormant until a consumer
ensures it.

## Resolution

`sase sdd path` is a read-only resolver; `-e/--ensure` clones or synchronizes the companion backing
the selected kind. Launched agents receive `SASE_SDD_DIR` plus `SASE_SDD_PLANS_DIR`,
`SASE_SDD_RESEARCH_DIR`, and `SASE_SDD_BEADS_DIR`.

```bash
sase sdd path                     # effective root for the current project
sase sdd path research            # research root (read-only, no clone)
sase sdd path research --ensure   # materialize the research clone, print its root
```

## Initialization & migration

Split initialization is a single **record-last transaction**:

1. Serialize setup and preflight both public repository names.
2. Create or adopt each repository and clone it at the linked-repository location.
3. Write deterministic per-repository README and infographic assets, then commit and push drift.
4. Only after **both** repositories succeed, write the schema-version 2 split store record.

Legacy artifacts move separately through `sase sdd migrate` (`--check` / `--diff` are read-only).
The apply path takes the materialization lock, detects destination conflicts, pushes both
repositories, and retires the local legacy clone only after success. A failed transaction leaves no
positive record, so the next write simply retries.

## Recommendation

Treat the store record as authoritative: resolve every path through `sase sdd path` rather than
assuming a fixed directory, and let research stay lazy — only `--ensure` when research is actually
needed. Deprecated `sdd.storage` / `sdd.version_controlled` keys are ignored and stripped;
`sase doctor` reports where to remove them.

![Split companion layout](../202607/split_companion_layout_smoke_20260711_infographic.png)

## Sources

- Agent A report (`research.@.cdx`): `split_plans_research_companion_layout_consolidated__a.md`
  (alternate infographic: `../202607/split_plans_research_companion_layout_infographic.png`).
- Agent B report (`research.@.cld`): `split_plans_research_companion_layout_consolidated__b.md`.
- `docs/sdd_storage.md` — provider policy, split companions, offline behavior (claims re-verified
  against this doc during consolidation).
- `sase/repos/sase--research/README.md` — research companion layout conventions.
- Commits `4c40d5af8`, `0bbd3cb50`, `4976cdbd8`, `75ee0fb6a`, `ccdd10482` (sase-5q.2–5q.5).
