---
create_time: 2026-07-29
updated_time: 2026-07-29
status: research
---

# SASE Sites: Consolidated Design Research

## Research question

How should SASE implement "sites" — taking inspiration from Codex/ChatGPT Sites — so that (1) one site encapsulates the
knowledge held in a project's `agents`, `beads`, `plans`, and document sidecars behind multiple tabs, and (2) a
`/sase_sites` xprompt skill lets agents fetch and create new sites? Should this be a new SASE web server?

## Provenance and method

This note consolidates two independent research reports written concurrently without knowledge of each other, plus a
third verification pass:

- `sase_sites_platform__a.md` (agent `research.q.cdx`, codex/gpt-5.6-sol) — product model: site identity, immutable
  versions, deployment records, portable bundles, security ceilings.
- `sase_sites_platform__b.md` (agent `research.q.cld`, claude/opus) — corpus measurement, existing-machinery audit,
  declarative `SiteSpec` projections, privacy blast radius.
- This report — verified every load-bearing claim in both, resolved six conflicts, and surfaced **four prior SASE
  research notes that neither report cited**, one of which already decided a question both reports answered differently.

Everything below marked *verified* was re-measured or re-read at `f39b0c405` (sase) and the current `sase-core` checkout.

## Executive summary

**Do not build a new web server.** Three independent lines of SASE research now converge on extending the existing Rust
`sase_gateway`; a fourth (`202604/sase_web_client_research.md`) proposed a separate `sase_server` crate and was already
superseded on this exact point.

The five decisions that matter:

1. **The index is the product, not the pages.** SASE's knowledge graph is already written down and already deterministic.
   What is missing is retrieval. Build `sase_core::site` as a derived SQLite+FTS5 index first; it is independently
   valuable before a single line of HTML exists.
2. **Serve from the existing gateway; export static as the shareable artifact.** One model, two render targets.
3. **Two site kinds.** `project` (generated portal over the corpora) and `custom` (agent-authored). Authored sites are
   *declarative projections* — a small `SiteSpec` over a fixed widget vocabulary — not generated web apps.
4. **Steal Codex's save/deploy split and its narrow default access; reject its hosting model.** Versions are pinned to
   the exact commit of every contributing repository. Deploy only changes which saved version is active.
5. **Privacy is the feature's sharpest risk, not a footnote.** A naive unified site would publish 2,984 chat transcripts
   and 5,389 agent prompts irreversibly into Git.

The strongest sequencing insight, which neither report drew out: **ship the search index alone first.** It is the one
genuinely absent capability, it is consumable by ACE and the CLI immediately, and it de-risks everything downstream.

---

## 1. Verified evidence base

### 1.1 The corpus is the constraint (verified, `sase` project, 2026-07-29)

| Corpus | Documents | Bytes | Notes |
| --- | --- | --- | --- |
| Plans | 3,303 `.md` | — | excludes prompt snapshots |
| Prompt snapshots | 2,800 `.md` | — | `<YYYYMM>/prompts/` |
| *(plans sidecar total)* | *6,103* | *33.5 MiB* | |
| Bead pages | 2,312 `.md` | 3.6 MiB | 407 event files |
| Document roles (`research`) | 301 `.md` | 6.1 MiB | plus infographics |
| Agents sidecar | 12,585 `.md` | 36.6 MiB | 33,693 files total; 2,984 chats; 706 family pages |
| Project docs | 77 `.md` | 1.9 MiB | `docs/` |
| **Total** | **21,378** | **81.6 MiB** | |

Report `__b`'s figures were accurate to within rounding. Report `__a` did not measure the corpus at all, which is why it
under-weights scale. Only 3 projects are enabled and `sase` dominates (15 workspace claims), so this is the worst case
and sites scale per-project.

Three consequences:

- **mkdocs cannot do this.** `mkdocs.yml` is `strict: true` with `docs_dir: docs` over 77 pages. Per-page Python
  rendering, one monolithic client-side search index, and a hand-maintained `nav` do not survive 21,378 documents, and
  `strict` would turn every stale cross-sidecar link into a build failure. Keep mkdocs for the narrative docs at
  `sase.sh`. *(Report `__a` never considered this option; it is the most tempting wrong answer.)*
- **Naive static export hits hosting limits.** Cloudflare Workers static assets allow 20,000 files free / 100,000 paid.
  One project's Markdown already exceeds the free limit before HTML expansion.
- **Search, filtering and pivots are the product.** 21,378 documents is unbrowsable by hand.

### 1.2 What already exists (verified)

**A hardened HTTP server.** `sase-core/crates/sase_gateway` is 10,997 lines of axum 0.7 with 27 route registrations
under `/api/v1`, a 956-line committed contract snapshot (`contract.rs`), pairing → bearer-token auth with hashed device
tokens and an audit log (`storage.rs`), SSE at `/api/v1/events`, and a **non-loopback bind refusal** —
`server.rs:73` gates on `config.bind.ip().is_loopback() || config.allow_non_loopback`, defaulting to `false`. The daemon
already carries a per-feature flag, `mobile_http_enabled` (`daemon.rs:37`), i.e. **it is already designed to host more
than one HTTP feature.** Attachment serving already enforces `canonicalize` plus a 20 MiB cap (`routes.rs:1345,73`).
`docs/mobile_gateway.md:5`: "gateway never exposes a generic file, shell, or RPC surface."

**A derived-SQLite-index pattern, already mature.** `sase_core/src/agent_scan/index.rs` implements a full agent artifact
index: `AGENT_ARTIFACT_INDEX_SCHEMA_VERSION`, `rebuild_agent_artifact_index`, `upsert_…`, `delete_…`,
`query_agent_artifact_index`, plus stale-row repair. `rusqlite 0.32` (bundled) is a workspace dep and is used in six
core modules. **This is a much stronger precedent than the `beads.db` citation in report `__b`** — the site index should
follow this exact shape.

**FTS5 is already proven in-tree.** `sase_core/src/agent_archive/mod.rs:641`:
`CREATE VIRTUAL TABLE dismissed_bundle_search_fts USING fts5(bundle_path UNINDEXED, archive_search_text)`. The search
substrate the site index needs is available and already in production use. Neither report found this.

**A role-parameterized reference grammar.** `artifact_ref/wire.rs:41-45` defines `ArtifactRefKindWire` as `Commit`,
`Chat`, `Bug`, `File`, and `Document { role: String }`. The `Document { role }` variant confirms report `__b`'s §4.10
point structurally: document sidecar roles are generic, so **corpus tabs must be derived from the resolved store record's
role map, never hardcoded to `research`.** Site permalinks should be this grammar, not a new one.

**Cross-repo graph edges, already materialized.** Plan header blocks (`PROMPT`/`PARENT`/`AGENTS`/`COMMITS`, re-derived
rather than accumulated), bead lineage pages with Mermaid graphs and lexically-derivable addressing, agent/family pages
with neighbors, `SASE_BEAD`/`SASE_AGENT` commit trailers, and `hosted_links.py` resolving cross-repo URLs while degrading
to unlinked labels rather than guessing. No LLM inference is needed to discover this graph.

**A static build + Cloudflare deploy pipeline.** `mkdocs.yml` → `just docs-check` → `wrangler.jsonc` (Worker `sase`,
`assets.directory: "site"`) → `.github/workflows/docs-deploy.yml` (wrangler-action v4.30.0, `CLOUDFLARE_API_TOKEN`
configured, PDF handbook build, post-deploy smoke check) → `https://sase.sh/`.

**Consent and privacy precedents.** `docs/sdd_storage.md:118` — creating a public sidecar requires interactive
confirmation and "Non-interactive input and `sase init --yes` cannot grant" it. `docs/agents_sidecar.md:14` documents the
`agents` sidecar's `visibility: private` opt-in.

**The generated-skill pipeline.** Sources in `src/sase/xprompts/skills/*.md` with `skill: true`, rendered per provider by
`sase skill init` through `SKILL.frame.template.md`, deployed to chezmoi behind a commit-first provenance guard
(`.sase-skills-manifest.json`). Both reports described this correctly.

**Greenfield naming.** All 37 `site`/`sites` matches in `src/sase` are incidental ("call sites", "import sites").
`default_config.yml` has no `site` key. `sase bead search "site"` finds no existing site bead or epic.

### 1.3 The critical negative finding: search today is a linear scan

Both reports state that "Rust-backed search already exists" and recommend reusing it. That materially overstates what is
there. `sase_core/src/bead/search.rs:59,85` lowercases the query and then does
`.filter(|field| field.value.to_lowercase().contains(needle))` — an O(corpus) substring scan with no index. Plan search
(`plan/search.rs:87,119`) is the same shape over freshly-read plan documents.

That is fine for a TUI filter box over a working set. It is not a search engine for 21,378 documents and 81.6 MiB, and it
will not serve an interactive web search box. **Reuse the ranking/filter-query semantics and the wire types; the storage
and retrieval layer must be new.** This strengthens the index-first recommendation considerably and is the single most
important correction to both reports.

### 1.4 Smaller verified corrections

- **`ServeDir` is not currently available.** `tower-http = { version = "0.5", features = ["trace"] }` — report `__b`'s
  §5.4 static-asset plan needs the `fs` feature added first.
- **`site/` is already taken.** It is mkdocs' `site_dir`, wrangler's `assets.directory`, and gitignored at
  `.gitignore:12`. `sase site build` must not default there, and the docs-site/`sase site` distinction needs explicit
  documentation to avoid confusing `just docs-check` with `sase site build`.
- Report `__b`'s "30 routes" is 27 `.route()` registrations; "~11k lines" is 10,997. Immaterial.
- Report `__a`'s cited URL `developers.openai.com/codex/sites` 308-redirects to report `__b`'s
  `learn.chatgpt.com/docs/sites`. They cited the same document; there was no source conflict.

---

## 2. Prior SASE research neither report cited

This is the largest gap in both reports. Four existing notes bear directly on the question, and one had already decided
the headline issue.

**`202607/sase_mobile_app_motivation.md` §"Converge, don't fork: `sase_gateway` vs. the future `sase-server`"** — already
resolved the new-server question: *"The mobile gateway is already that shape (axum, REST, SSE, versioned contract,
command-shaped mutations). Building both independently would create two divergent API surfaces over the same domain.
Recommendation: treat `sase_gateway` as the seed of the shared frontend server."* It also prescribes the discipline:
new read endpoints specified **once** for both the Android app and a future web client, snapshot-gated schema in CI,
additive-only `/api/v1` changes, core-native Rust handlers where logic already lives in `sase_core` and fixed Python
bridge ops where host logic owns behavior.

→ **Sites must be specified inside that same shared v1 contract, not as a parallel surface.** Neither report said this,
and it is the difference between sites strengthening the gateway and sites forking it.

**`202604/sase_web_client_research.md`** — proposed `crates/sase_server/` (axum + utoipa OpenAPI) with a
**Vite + React + TypeScript SPA** (TanStack Query/Router/Virtual/Table), loopback-only, ephemeral port, session token
plus `Host`-header validation against DNS rebinding, and `~/.sase/run/server.json` singleton discovery. The *server* half
is superseded by the convergence decision above; the *frontend* and *hardening* halves remain the standing reference.

**`202605/markdown_to_html_rich_artifacts.md`** — **directly contradicts report `__b`'s Markdown plan.** It works through
the same Rust-core boundary litmus test and concludes: keep Markdown→HTML in **Python `markdown-it-py`** +
`mdit-py-plugins` + `linkify-it-py` with `nh3` sanitization for v1, because the conversion is one library call whereas
moving it to Rust means adopting `pulldown-cmark`/`comrak` + `ammonia` + `syntect` through PyO3 *and* diverging from what
mkdocs renders for the docs site. It names its two re-evaluation triggers (Android needing render without a Python
interpreter; a Rust/WASM web client). It also already specifies the output contract sites need: self-contained `.html`
with inlined CSS and base64 images, **no JS**, stable anchor IDs, `<meta charset>` first, viewport meta, CSP via
`<meta http-equiv>`, sandboxed `iframe` (`allow-same-origin allow-popups`, no `allow-scripts`), and a cache key including
a renderer-version hash.

→ **Adopt this. Do not add a Rust Markdown crate.** Report `__b`'s §5.4/§5.6 should be split: the *index and query* go to
Rust; *Markdown→HTML* stays Python and reuses this pipeline.

**`202605/textual_serve_ace_web_access.md`** — recommends `sase ace web` wrapping `textual-serve` as an *optional* local
web-access mode, explicitly *"not a substitute for web-native artifact viewing, mobile APIs, or shared backend
contracts."* Neither report listed this in its design space. It is by far the cheapest route to "read SASE in a browser"
and is complementary — but it yields no shareable, searchable, linkable site, so it does not satisfy either ask.

Also adjacent: bead `sase-aw.1` ("Reader core — copy, editor, viewer hand-off, reference-aware chrome") and recent
commits `a4d026ba7` / `f39b0c405` are building an in-TUI artifact reader right now. Sites should share its artifact-ref
addressing and reader semantics rather than diverge.

---

## 3. Codex Sites: what to steal, what to reject

Verified against `learn.chatgpt.com/docs/sites`. Both reports characterized the product accurately; the merged and
corrected picture:

| Mechanic | Codex behavior (verified) |
| --- | --- |
| Save vs deploy | "Save a version" builds a reviewable candidate **tied to the source Git commit**; "Deploy a version" publishes it. Every deployment URL is production. |
| Identity manifest | `.openai/hosting.json` holds `project_id` plus D1/R2 binding names. **Secrets and env vars belong in the Sites panel, not that file or a committed `.env`.** |
| Access modes | `admins_only`, `workspace_all`, `custom`. A new Site is "limited to its owner and workspace admins until you change its access." |
| Storage | Optional D1 (relational) / R2 (objects). Guidance: don't ask for durable storage unless the site must remember real product data. |
| Limits | **Does not connect to live organization data.** No private networks, databases, background services, or some frameworks. No data/inference residency at launch. Plan-specific usage caps. |
| Lifecycle | Sites are persistent and outlive the chat; managed from a dashboard. |

**Steal:** (1) save/deploy separation with commit-pinned versions — the single best idea, and it maps onto SASE's
existing "identical inputs produce byte-identical files" discipline; (2) narrow default access, widened only by an
explicit separate act; (3) a small manifest *is* the site, everything else is derived; (4) "don't add durable storage
unless you need it" — a SASE site is a projection, all truth stays in the sidecars; (5) sites outlive the run that
created them, so a site needs an opaque durable ID and agents must never infer identity by title or slug matching.

**Reject:** (1) **arbitrary generated web apps** — non-deterministic output, unreviewable diffs, no golden tests,
arbitrary JS to audit; (2) storage bindings — a second source of truth per site; (3) a hosted multi-tenant control plane
— SASE is local-first with an explicit no-generic-remote-surface policy; (4) prompt-driven visual iteration as the
primary loop — reserve it for authored sites only.

**The limitation is the opportunity.** Codex Sites cannot reach live org data, so an automation must gather changes and
prepare a version. SASE owns the local sidecar lifecycle, so it can detect new commits, build a draft version, and notify
the owner — while still requiring review before deployment. Report `__a` identified this well.

**Naming:** do not call this a "codex." `codex` is already a first-class SASE agent-provider name and `AGENTS.md` is its
instruction file; the noun would collide in docs, config keys, completions, and query tokens. Use `sase site` with kinds
`project` / `custom`. (Report `__b`'s catch.)

---

## 4. Conflicts between the two reports, resolved

| # | Conflict | `__a` (cdx) | `__b` (cld) | Resolution |
| --- | --- | --- | --- | --- |
| 1 | New web server? | Reuse & generalize `sase_gateway`; add `sase web start` | Reuse gateway behind `sites_http_enabled` | **Agreed, and independently confirmed** by the mobile note's converge-don't-fork decision. Prefer `__b`'s per-feature flag (matches `mobile_http_enabled`) over renaming the surface to `sase web` in v1 — renaming is a separate, larger change. |
| 2 | Markdown→HTML | Not addressed | Add Rust `pulldown-cmark`/`comrak` | **`__b` is wrong.** `202605/markdown_to_html_rich_artifacts.md` already decided Python `markdown-it-py` + `nh3` for v1 with a reasoned boundary analysis and named re-evaluation triggers. Follow it. |
| 3 | Frontend stack | React/Vite or smaller TS stack; "a presentation decision" | Vanilla CSS+JS; no npm framework (only `prettier` today) | **Split by surface.** Static document pages: no-JS self-contained HTML per the markdown note — `__b`'s instinct is right. Interactive shell (search, filters, graph): keep it small and vanilla for v1, because adding Vite/React *solely* for sites is disproportionate; but design the API so the future shared web client renders sites as one of its routes. Do not build a throwaway, and do not import a toolchain ahead of the web client. |
| 4 | Built output in Git? | No `--sites` sidecar in v1; bundles in `~/.sase/sites/` | Visibility ladder includes a committed `<repo>--site` sidecar | **Separate sources from output.** *Sources* (`SiteSpec` YAML + prose) are small and reviewable → Git, in the primary repo. *Built output* is large and churny → artifact store, gitignored. `__a`'s objection is valid and applies to output only. A `--site` sidecar is then merely one optional publish target, and a **separate Cloudflare Worker is the better public target** since `wrangler.jsonc` already claims `site/`. |
| 5 | Site kinds | One generated portal with selectable tabs | `project` (generated) + `custom` (authored `SiteSpec`) | **`__b`.** The user's ask #2 is explicitly "create *new* sites," which `__a`'s model cannot express. Adopt `__b`'s two kinds and widget vocabulary, with `project` as "site zero" so there is one engine. |
| 6 | Static vs served | Server-primary; bundle is a portable export for `fetch` | Static export is *primary*; server for the live loop | **`__b`'s framing, `__a`'s record model.** Static export is what makes a site a durable SASE artifact. But adopt `__a`'s version/deployment/source-lock records wholesale — `__b`'s "content-addressed version" is underspecified by comparison. |
| 7 | Meaning of "fetch" | Download & verify a portable bundle | Print the resolved source path, mirroring `sase repo open` | **Both, distinctly named.** `sase site open` prints the source path (the `/sase_repo` contract agents need); `sase site export` produces the portable bundle. Never overload one verb. |

Report `__b` is also the more CLI-compliant proposal: verified against `memory/cli_rules.md`, its surface is
alphabetically sorted with a short alias per long option and a bare-group-defaults-to-`list` design. `__a`'s is neither.

---

## 5. Recommended architecture

### 5.1 The site index (`sase_core::site`) — build this first

- **Nodes** keyed by the existing `ArtifactRefKindWire` grammar extended with corpus kinds: `plan`, `prompt`,
  `document{role}`, `bead`, `agent`, `family`, `commit`, `chat`, `changespec`, `bug`, `file`.
- **Edges**, all derived from data that already exists — no inference, no LLM: plan→prompt/parent/agents/commits (header
  block); bead→plan/phases/commits/agents (pages + event store); agent→prompt/chat/commits/variables/family/neighbors
  (v2 snapshots); commit→bead/agent (trailers); document→anything (`artifact_ref/scanner.rs`).
- **Persistence:** SQLite at `~/.sase/projects/<key>/site/index.db` via `rusqlite`, **with FTS5 virtual tables**
  following `agent_archive/mod.rs:641`, and the schema-versioned rebuild/upsert/query shape of `agent_scan/index.rs`. A
  derived cache — never a source of truth, safe to delete, gitignored like `beads.db*`.
- **Incremental:** key each document by Git blob SHA (`mtime`+`size` for the machine-level agents clone) so rebuilds
  re-parse only what changed.
- **Determinism:** sorted iteration, no wall-clock or random IDs in output, stable anchors.
- Reuse `plan::read`, `bead::read/events`, `agent_scan`, `artifact_ref::scanner`, `query`. Reuse search *semantics* and
  wire types from `plan::search`/`bead::search` — but not their scan-based retrieval (§1.3).

**This module is shippable and valuable on its own.** Real search over 21,378 documents, consumable by ACE and the CLI,
with no site, no server, and no HTML.

### 5.2 Product records (from `__a`)

Three separate records, because conflating them is how freshness bugs and accidental publishes happen:

- **Site** — durable opaque `id`, `slug`, `title`, owning project, enabled tabs, access policy, `active_version_id`.
  Metadata is mutable. Internally keyed by ProjectSpec key; **API and UI must display the configured `PROJECT_NAME`,
  never the storage key.**
- **Saved version** — immutable, with a **source lock naming the exact commit SHA of every contributing repository**
  (primary, agents, beads, plans, each document role), plus content digests and build diagnostics. A build must read
  those exact committed trees even if the clones advance mid-index. Uncommitted changes are never silently included; a
  local-only preview must say so. For shared deployment, every source commit must be reachable from its recorded
  upstream.
- **Deployment** — points one audience/URL at one saved version. Deploy never builds. Rollback is deploying an older
  version.

Portable bundle layout: `manifest.json`, `documents.jsonl`, `relationships.jsonl`, `search/`, `assets/<sha256>`,
`public/`. Written to a temp dir, validated, fsynced, atomically renamed.

### 5.3 Authored sites are declarative projections

A `SiteSpec` is a small YAML manifest plus optional narrative Markdown, with data sourced through the **existing ACE
query language** (`docs/query_language.md`, `sase_core::query`) against the index, rendered from a fixed widget
vocabulary: `markdown`, `table`, `document_list`, `metric_row`, `timeline`, `board`, `graph`, `gallery`, `commit_log`,
`agent_roster`, `embed`.

```yaml
# sase/sites/mobile_launch/site.yml
name: mobile_launch
title: SASE Mobile MVP Launch Hub
kind: custom
visibility: local
tabs:
  - id: overview
    title: Overview
    widgets:
      - kind: metric_row
        metrics: [beads_open, beads_closed, commits_30d, agents_active]
        query: "bead:sase-26.*"
      - kind: markdown
        source: overview.md
  - id: phases
    title: Phases
    widgets:
      - kind: table
        query: "bead:sase-26.* status:open"
        columns: [id, title, status, size, agents, commits]
      - kind: graph
        root: sase-26
```

An agent writes ~30 lines of YAML instead of a web app: cheaper, more likely correct on the first attempt, readable in a
PR diff, golden-testable exactly as `agents_sync` and `bead_pages` already are, and free of arbitrary JS in the hosting
surface. Agents already know the query language from ACE.

Defer `kind: raw` (agent-authored static assets). If it ever lands: explicitly flagged, excluded from the `project` site,
and refused for public visibility without interactive consent.

### 5.4 Project-site tabs

Mirror ACE so the surfaces teach each other, reusing `ARTIFACTS_SUBTAB_ORDER` and `ARTIFACTS_ACCENTS` from
`ace/tui/artifact_tabs.py` verbatim so web and TUI palettes cannot drift:

**Overview** (project pulse; index + live state) · **Plans** (month-sharded, tier filter, header-block provenance as real
navigation) · **Beads** (lineage trees, phase tables, existing Mermaid) · **Agents** (hood → family/clan → member;
prompts/chats gated) · **Artifacts** (ACE's five sub-tabs) · **one tab per document role, derived from the store record**
(§1.2) · **Docs** · **Graph** · **Search**.

Every detail page carries: backlinks, the saved version, source role/path/commit with a hosted link when resolvable, a
stale-source indicator, and a stable route independent of the display title. Routes use escaped typed IDs so the same
string in two corpora cannot collide.

### 5.5 Static export at 21,378 documents

Do **not** emit one HTML file per source document.

1. **Pre-render** the shell, tab landings, graph, and every high-value page: plans (3,303) + bead pages (2,312) +
   document-role notes (301) + family pages (706) ≈ **6,600 pages** — crawlable, linkable, inside the free-plan limit.
2. **Shard the long tail** into on-demand JSON: prompt snapshots (2,800), agent READMEs (5,389), chats (2,984). These are
   simultaneously the largest and least deep-linked buckets.
3. **Shard the search index** by corpus and month; never emit one monolithic index.
4. **Scope flags** — `--months`, `--since`, `--corpus`, `--exclude-chats` — and **report what was excluded in the build
   summary.** SASE's convention is that a bounded projection says so out loud (`… and N more`) rather than truncating
   silently.

A default build lands around 7–8k files. Output goes to an artifact store, **not `site/`** (§1.4).

### 5.6 Serving

Add a `sites` router to `sase_gateway` behind a new `DaemonConfig.sites_http_enabled`, alongside `mobile_http_enabled`:

```text
GET /sites/                     # site directory
GET /sites/:site/               # shell
GET /sites/:site/api/tabs
GET /sites/:site/api/query?q=…  # ACE query language against the index
GET /sites/:site/api/node/:ref  # artifact-ref addressed
GET /sites/:site/api/search?q=…
GET /sites/:site/events         # SSE: index change, live-reload
```

Inherit **unchanged**: the non-loopback bind refusal, pairing → bearer flow, token storage, audit log, the
`contract.rs` snapshot discipline, and the fixed-operation principle (no generic file/shell/RPC surface). Specify these
endpoints in the **same shared v1 contract** that serves the Android app and the future web client (§2). Add
`tower-http`'s `fs` feature for `ServeDir`. Keep Mermaid client-side — bead pages already emit Mermaid source. Adopt the
web-client note's `Host`-header validation against DNS rebinding.

### 5.7 Code placement

| Concern | Home |
| --- | --- |
| Site model, index schema/build/query, FTS5, version hashing, `SiteSpec` parsing, source-lock validation, bundle integrity, access-ceiling decisions | `sase-core/crates/sase_core/src/site/` |
| `/sites` router, SSE, asset serving | `sase-core/crates/sase_gateway/src/sites.rs` |
| **Markdown→HTML rendering, sanitization, page templating** | **Python** (`markdown-it-py` + `nh3`), reusing the artifact-HTML pipeline — per §2 |
| Python bindings | `sase_core_py` → `src/sase/site/facade.py` |
| CLI, config schema, role resolution, consent prompts, deploy invocation | `src/sase/site/` |
| ACE integration (open the site page for the selected row) | `src/sase/ace/tui/actions/` |
| GitHub `site` sidecar / Pages, if ever needed | `sase-github` plugin repo |

Source resolution should go through `collect_repo_inventory()` (report `__a`'s good catch) — never accept
client-supplied filesystem roots, and never find the agents sidecar by guessing a sibling path. Until inventory moves to
Rust, use a fixed JSON-over-stdin host bridge returning a typed source descriptor, exactly as the gateway already does
for host operations (`docs/mobile_gateway.md:86`).

### 5.8 CLI surface

Per `memory/cli_rules.md` — alphabetized, a short alias for every long option, bare group defaults to `list` via
`_default_list_subcommands()`:

```text
sase site                    # → sase site list (with the standard delegation notice)
sase site build [name]       # render a version; -m/--months, -s/--since, -c/--corpus, -x/--exclude, -o/--out
sase site check              # validate every SiteSpec + report drift; -j/--json
sase site deploy [name]      # publish a saved version; -V/--version, -t/--target; requires consent
sase site export [name]      # portable verified bundle; -V/--version, -o/--out
sase site index              # rebuild/refresh the index; -f/--full, -j/--json
sase site list               # sites for the project; -a/--all, -j/--json
sase site new <name>         # scaffold a SiteSpec; -T/--template, -t/--title
sase site open [name]        # print the resolved site source path (mirrors `sase repo open`)
sase site search <query>     # search the index; -k/--kind, -j/--json
sase site serve [name]       # sites router on the daemon; -p/--port, -b/--bind, -L/--allow-non-loopback
sase site show <name>        # spec, version history, deploy state; -j/--json
sase site versions [name]    # recorded versions; -j/--json
```

New `site:` config key: `default_visibility`, `index.refresh_ttl_seconds`, `serve.{bind_address,port}`,
`build.{months,exclude}`, `deploy.target`. Document the `sase site build` vs `just docs-check` distinction explicitly.

---

## 6. Privacy: the sharpest risk

Combining individually-accessible sources into one searchable portal **increases disclosure risk even when no new bytes
are introduced** — full-text search and backlinks make sensitive material dramatically easier to find. On this machine
the exposure is concrete: **2,984 chat transcripts and 5,389 agent prompts.** `docs/agents_sidecar.md` is explicit that
the sidecar carries prompts, transcripts, and sanitized output variables visible to anyone who can read it.

Requirements:

1. **Access ceiling, enforced per version:** `max site audience ≤ most restrictive included source audience`. Wider
   publication must either exclude the restrictive corpus or apply an explicit redaction profile — never a single generic
   confirmation that republishes full transcripts.
2. **Agent inclusion profiles:** `metadata` (names, states, times, relationships, counts) · `summaries` · `full`
   (prompts, chats, variables). `full` is owner-only. The `project` site **excludes agent prompts, chats, and output
   variables by default**; opt in per-corpus with an explicit flag, never a config default.
3. **`sase site build` must refuse** `sidecar`/`public` visibility when the `agents` sidecar is configured
   `visibility: private` or disabled. Deriving a public site from a deliberately private corpus is a privacy regression
   with a Git-durable blast radius.
4. **Consent** for anything above `local` follows `sase repo init`'s public-sidecar prompt: interactive only,
   resource-specific, and ungrantable by `--yes` or non-interactive input (`docs/sdd_storage.md:118`).
5. **`sase doctor` check** for site-visibility vs corpus-visibility drift.
6. **Rendering:** sanitize Markdown and disallow executable raw HTML; treat all prompts, chats, notes and research as
   untrusted content and never as instructions; resolve media only from the locked Git tree; content-address copied
   assets with MIME/size allowlists; reuse the gateway's traversal/symlink/regular-file/token/size defenses; never expose
   `.git`, working-tree paths, env files, credentials, or untracked files; emit CSP and sandboxed iframes per the
   markdown note.
7. **Auth:** loopback default; `HttpOnly`/`SameSite` sessions rather than tokens in query strings; authenticate HTML,
   API, *and* asset routes; audit create/save/deploy/access-change/refresh/export/delete.
8. **v1 is read-only** with respect to the knowledge repos. Viewing a page must never mutate a sidecar. Later mutations
   go through existing typed gateway operations with the same auth, validation and audit trail.

Reuse the existing privacy wording verbatim rather than inventing new phrasing.

---

## 7. The `/sase_sites` skill

Author `src/sase/xprompts/skills/sase_sites.md` with `skill: true`; render with `sase skill init`; respect the
commit-first provenance guard (`--diff`/`--dry-run` while iterating, then land, then `sase skill init --force` from a
clean merged tree). Ship it only after the CLI is stable, per the CLI/skill contract-synchronization rule.

**Model it on `/sase_repo`, not on a reference card.** `/sase_repo` works because it establishes a hard contract: use the
skill first, then treat the printed path as the only path. Sites need the same discipline, because the failure mode — an
agent hand-writing HTML into a build directory or editing generated `project`-site output — is otherwise very likely.

Skill contents:

1. **Fetch** — `sase site list`, `sase site show <name> --json`; `sase site open <name>` prints the source path, and
   that printed path is the only path for reads and writes. `sase site export` for a portable bundle. Never traverse
   repos or download over HTTP to materialize a site.
2. **Create** — `sase site new <name> -T <template>` scaffolds the `SiteSpec`; the agent then edits `site.yml` and the
   prose beside it. Templates: `dashboard`, `board`, `review`, `gallery`, `report`.
3. **The widget vocabulary and the query language** — the bulk of the body, with a worked example per widget and a
   pointer to `docs/query_language.md`. This is where the skill earns its keep: an agent that knows the vocabulary
   produces a good site on the first attempt.
4. **Verify** — `sase site check`, then `sase site build <name>` to confirm it renders. Both read-only w.r.t. published
   state.
5. **Hard boundaries** — never edit the generated `project` site (change the generator or the corpus); never write into
   a build output directory; **never deploy** (propose it through `/sase_gate` and let the user confirm, consistent with
   agents never creating commits, branches or PRs directly); commit site sources through `/sase_git_commit`; preserve
   opaque IDs and never infer identity by title or slug; create sites private and undeployed unless the user explicitly
   asked otherwise; never put secrets in a `SiteSpec`, prompt, or manifest.
6. **Privacy note** — authored sites can surface agent prompts, chats and variables; do not include those corpora in a
   site intended for sharing. Reuse the agents-sidecar wording.

Because the skill is CLI-backed, every runtime gets identical behavior, validation, locking, privacy checks, and audit
trail — honoring the **Uniform Agent Runtimes** rule. The feature must not depend on the Codex Sites connector being
present; Codex Sites is at most an optional deployment adapter later.

Also add a `#site`/`#sites` xprompt so launches can request site work directly.

---

## 8. Recommended plan

**Phase 0 — Spike and lock (small).** Prototype the index in Rust against the real 21,378-document corpus; measure cold
and incremental build time and `index.db` size; record the numbers as the perf floor in the style of
`docs/perf_runbook.md`. Confirm FTS5 through `rusqlite` bundled (already proven at `agent_archive/mod.rs:641`). Lock
naming (`sase site`, kinds `project`/`custom`), the build-output path (**not `site/`**), and the Python-renderer decision
from §2.

**Phase 1 — `sase_core::site` index + `sase site index|search` (medium).** Node/edge schema over the artifact-ref
grammar; SQLite + FTS5 following `agent_scan/index.rs`; incremental keying by blob SHA. Ingest plans, document roles and
beads first (workspace-local, simplest). Golden-output tests modeled on the `agents_sync`/`bead_pages` suites. **No
server, no HTML, no deploy — and already the single biggest missing capability delivered.**

**Phase 2 — Static project site (medium).** Tabs per §5.4 with corpus tabs derived from the store record; Python
`markdown-it-py` rendering reusing the artifact-HTML pipeline; pre-render/shard strategy per §5.5; scope flags with loud
exclusion reporting. Ingest the machine-level agents sidecar with prompts/chats/variables **excluded by default**.
`local` visibility only.

**Phase 3 — `sase site serve` (medium).** `sites_http_enabled`; the `/sites` router; SSE live-reload; query and node
APIs; `tower-http` `fs`; contract-snapshot extension specified in the shared v1 contract. ACE integration: open the site
page for the selected agent, bead, plan or commit. Gateway bind policy and auth reused without modification.

**Phase 4 — Authored sites and `/sase_sites` (medium).** `SiteSpec` schema and validation, widget vocabulary, templates,
`sase site new/open/show/check`, and the generated skill.

**Phase 5 — Versions, deploy, publish (medium).** Source-locked content-addressed versions per §5.2; `sase site
versions/export/deploy`; rollback; the visibility ladder (`local` → static bundle → **separate Cloudflare Worker**, with
a committed `--site` sidecar as an optional and discouraged alternative); consent prompts; the
refuse-public-when-agents-private rule; `sase doctor` drift check; a `sites-deploy` workflow modeled on
`docs-deploy.yml`.

**Phase 6 — Continuous freshness (small).** Post-commit incremental index refresh following the best-effort, never-raises
pattern of `bead_pages/publication.py` and the durable outbox of `agents_sync/publication_outbox.py`. Draft-refresh jobs
that build a new version and emit `site_version_ready` **without auto-deploying**. Optional axe chop for periodic full
rebuilds.

### Two cheap wins available immediately

- **Cross-sidecar root index** (report `__b`): a generated README section in each sidecar linking to its siblings, plus a
  project landing document, reusing the existing `sase repo init` README path. No search or tabs, but a real
  navigation improvement in one small change.
- **`sase ace web`** (from `202605/textual_serve_ace_web_access.md`): if the near-term need is "read SASE from a browser"
  rather than "publish a shareable site," this is dramatically cheaper than any phase above and complementary to all of
  them. Worth deciding explicitly rather than by omission.

---

## 9. Open questions

1. **Is the search index the real goal?** If what you mostly want is fast retrieval over 21,378 documents, Phase 1 alone
   delivers it and Phases 2–6 are optional polish. Worth deciding before committing to the full arc.
2. **Should the `sase` project's own site be public?** A strong SASE-on-SASE demo, and much of the corpus is already in
   public sidecars — but it would publish 2,984 chat transcripts unless explicitly excluded. Decide deliberately.
3. **Deploy target:** separate Cloudflare Worker (recommended — keeps the `sase.sh` deploy blast radius and its smoke
   test intact, and `wrangler.jsonc` already claims `site/`), a route on the existing Worker, or Pages on a sidecar?
4. **Multi-project sites.** The index is per-project by design; a cross-project "everything" site is a straightforward
   later composition but changes the URL scheme. Recommend deferring — only 3 projects are enabled and `sase` dominates.
5. **Multi-machine truth.** The agents sidecar is `users/…/machines/…/hoods/…`, so a site built on one machine reflects
   only synced state. See `202605/multi_machine_sync.md`. The version source lock makes this visible rather than silent,
   but the product answer ("whose view is this site?") is undecided.
6. **Chat over the index.** DeepWiki-style retrieval chat is genuinely useful at this corpus size, and the index is
   exactly the substrate it needs. Natural Phase 7; out of scope here.

---

## 10. Bottom line

Do not build a new web server — three separate SASE research threads now agree, and the existing `sase_gateway` already
solved auth, bind policy, SSE, contracts, and audit. Build a **site index in `sase_core`** (SQLite + FTS5, following the
`agent_scan/index.rs` and `agent_archive` precedents), render it two ways — deterministic static export as the durable
artifact, and a `/sites` router on the existing gateway for the live loop — and express both the generated project site
and agent-authored sites as **declarative `SiteSpec` projections** over that index, with data sourced through the ACE
query language and Markdown rendered by the Python pipeline SASE already chose.

SASE's knowledge graph is already written down, already deterministic, already transactional, already cross-linked. Sites
should read it, not rebuild it. What is genuinely missing is **retrieval** — today's "search" is a linear substring scan
— so ship the index first. The rest is a renderer, a widget vocabulary, and the discipline to keep 2,984 chat transcripts
from accidentally becoming a public website.

---

## Sources

**Codex/ChatGPT Sites:** [Sites docs](https://learn.chatgpt.com/docs/sites) (canonical; `developers.openai.com/codex/sites`
308-redirects here) · [OpenAI Academy: ChatGPT Sites](https://openai.com/academy/chatgpt-sites/) ·
[OpenAI Help: Creating and managing ChatGPT Sites](https://help.openai.com/en/articles/20001339) ·
[Kingy AI guide](https://kingy.ai/news/openai-sites-a-detailed-guide-to-codexs-new-hosted-website-and-app-builder/) ·
[Taskade](https://www.taskade.com/blog/codex-sites-explained) ·
[Stacktree](https://stacktr.ee/blog/sites-in-codex-explained)

**External architecture:** [Backstage TechDocs architecture](https://backstage.io/docs/features/techdocs/architecture/) ·
[Docusaurus versioning](https://docusaurus.io/docs/versioning) ·
[Cloudflare static asset limits changelog](https://developers.cloudflare.com/changelog/2025-09-02-increased-static-asset-limits/) ·
[Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/) ·
[DeepWiki](https://docs.devin.ai/work-with-devin/deepwiki)

**Prior SASE research (previously uncited):** `202607/sase_mobile_app_motivation.md` (§"Converge, don't fork") ·
`202604/sase_web_client_research.md` · `202605/markdown_to_html_rich_artifacts.md` ·
`202605/textual_serve_ace_web_access.md` · `202605/multi_machine_sync.md`

**SASE (`f39b0c405`):** `src/sase/repo_inventory.py` · `src/sase/_linked_repo_config.py` · `src/sase/sdd/_store_types.py`
· `src/sase/sdd/hosted_links.py` · `src/sase/sdd/plan_header_*.py` · `src/sase/agents_sync/rendering_*.py` ·
`src/sase/bead_pages/` · `src/sase/artifact_refs.py` · `src/sase/plan_search/facade.py` ·
`src/sase/ace/tui/tab_order.py` · `src/sase/ace/tui/artifact_tabs.py` · `src/sase/xprompts/skills/` ·
`src/sase/default_config.yml` · `mkdocs.yml` · `wrangler.jsonc` · `.github/workflows/docs-deploy.yml` ·
`docs/sdd_storage.md` · `docs/agents_sidecar.md` · `docs/mobile_gateway.md` · `docs/query_language.md`

**`sase-core`:** `crates/sase_gateway/src/{routes,server,daemon,contract,storage}.rs` ·
`crates/sase_core/src/agent_scan/index.rs` · `crates/sase_core/src/agent_archive/mod.rs` ·
`crates/sase_core/src/artifact_ref/wire.rs` · `crates/sase_core/src/{plan,bead,query}/` · `Cargo.toml`

**SASE long-term memory:** `memory/cli_rules.md` · `memory/generated_skills.md` · `memory/rust_core_backend_boundary.md`
