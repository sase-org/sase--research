# SASE Sites — Design Research

**Date:** 2026-07-29
**Question:** How should SASE implement "sites" — taking inspiration from OpenAI's Codex Sites — such that (1) a single
site can encapsulate all knowledge held in a project's `agents`, `beads`, `plans`, and `research` sidecars behind
multiple tabs, and (2) a `/sase_sites` xprompt skill lets agents fetch and create new sites? Should this be built on a
new SASE web server?

**Method:** Read the Codex/ChatGPT Sites product documentation and secondary coverage. Then audited the SASE tree for
every piece of relevant existing machinery: sidecar storage records (`docs/sdd_storage.md`), agent-hood publication
(`docs/agents_sidecar.md`, `src/sase/agents_sync/rendering*.py`), generated bead pages (`src/sase/bead_pages/`),
cross-repo hosted links (`src/sase/sdd/hosted_links.py`), the artifact-reference grammar (`src/sase/artifact_refs.py`,
`sase_core/src/artifact_ref/`), Rust-backed document and bead search (`src/sase/plan_search/facade.py`,
`sase_core/src/bead/search.rs`), the existing axum HTTP server and daemon (`sase_core/crates/sase_gateway/`), the
docs-site build and Cloudflare deploy path (`mkdocs.yml`, `wrangler.jsonc`, `.github/workflows/docs-deploy.yml`), ACE's
tab model (`src/sase/ace/tui/tab_order.py`, `artifact_tabs.py`), and the generated-skill pipeline
(`src/sase/xprompts/skills/`). Finally, measured the actual corpus on this machine to size the problem.

**Headline finding:** SASE already ships a site. It is ~21,000 cross-linked Markdown documents rendered
deterministically into four Git sidecars and browsed on GitHub. The gap is not data plumbing — the knowledge graph and
its edges already exist and are already maintained transactionally. The gap is **presentation and query**: no unified
index, no search, no filtering, no tabs, no cross-sidecar navigation, and a corpus that has outgrown what GitHub's
Markdown viewer can serve. That reframes "SASE sites" as a *new frontend over an existing, already-Rust-backed model*,
which in turn determines almost every architectural decision below.

---

## 1. What Codex Sites Actually Is

Sites (shipped in Codex, GA'd as ChatGPT Sites on 9 July 2026 for paid plans) lets an agent create, host, refine, and
share websites, web apps, and games without the user touching deployment infrastructure. The mechanics worth studying:

| Mechanic | How Codex does it |
| --- | --- |
| **Invocation** | `@Sites` plugin, or the word "website" in a prompt. The agent gets create/save/deploy/inspect operations. |
| **Two-phase publish** | "Save a version" builds a deployable candidate *without* publishing. "Deploy a version" publishes it. Every deployment URL is a production URL. |
| **Version identity** | A saved version is associated with the Git commit used for the build, so the code behind a deployment is reviewable. |
| **State manifest** | `.openai/hosting.json` holds `project_id` plus storage binding names (e.g. `d1`, `r2`). |
| **Persistence** | Optional: D1 (relational), R2 (objects), or no durable storage at all. Guidance is explicit — *don't* ask for durable storage unless the site must remember real product data. |
| **Access tiers** | Owner/admin → selected users/groups → workspace-wide → public. Public is off by default in Enterprise. Optional "Sign in with ChatGPT" for identity-aware features. |
| **Lifecycle** | Sites are persistent and outlive the chat that created them. Managed from a dashboard with analytics. |
| **Iteration** | Refine by prompt against a live preview, with screenshots and files as context. |
| **Limits** | Per-plan usage caps; no private networks, no background services, some frameworks unsupported. |

### What to steal

1. **Save/deploy separation with commit-tied versions.** This is the single best idea in the product and it maps
   perfectly onto SASE's existing habits: deterministic generated output, tied to a source revision, reviewable before
   it goes anywhere.
2. **Explicit graduated visibility, private by default.** SASE already has this instinct — `sase repo init` demands a
   fresh interactive `y`/`yes` before creating a public sidecar, and the `agents` sidecar has a documented
   `visibility: private` opt-in. A site must inherit that posture, not weaken it.
3. **A manifest as the site's identity.** A small declarative file is the site; everything else is derived.
4. **"Don't ask for durable storage unless you need it."** Applied to SASE: a site should be a *projection*, not a
   database with its own truth. All truth stays in the sidecars.
5. **Sites outlive the chat.** A SASE site must be a durable, Git-tracked artifact like a plan or a bead page — not
   scratch output in an agent's workspace.

### What to reject

1. **Arbitrary generated web apps.** Codex Sites generates and hosts *code*. For SASE that would be a large step
   backwards: non-deterministic output, unreviewable diffs, no golden tests, arbitrary JS to audit, and a hosting
   surface with real attack surface. SASE's entire generated-artifact discipline is "identical inputs produce
   byte-identical files" (`docs/agents_sidecar.md`). A site should be a *declarative projection*, not an app.
2. **Storage bindings (D1/R2).** SASE's data is already in Git. Adding a second source of truth per site is exactly the
   thing Codex's own guidance warns against.
3. **A hosted multi-tenant control plane.** SASE is a local-first workstation tool with an explicit
   no-generic-remote-surface policy (`docs/mobile_gateway.md`: "The gateway never exposes a generic file, shell, or RPC
   surface"). Sites should not introduce SASE's first hosted service.
4. **Prompt-driven visual iteration as the primary loop.** SASE's canonical corpus site should be *generated*, not
   art-directed. Reserve prompt-driven iteration for the authored-site kind only.

### Adjacent prior art

DeepWiki (Cognition) auto-generates a browsable, Mermaid-diagrammed, chat-queryable wiki for any GitHub repo by building
an index over the repo and generating pages via RAG. Two lessons: (a) the "replace one URL segment and get a site"
affordance is powerful, and (b) *the index is the product* — pages are cheap once the graph exists. SASE differs
crucially in that it does **not** need an LLM to discover its graph. The edges are already written down.

---

## 2. What SASE Already Has

This section is the load-bearing part of the analysis. Nearly every component a site needs already exists.

### 2.1 Four corpora, already deterministic and cross-linked

| Corpus | Location | Shape |
| --- | --- | --- |
| `plans` | `<workspace>/sase/repos/plans` | `<YYYYMM>/*.md` plans (frontmatter `title`, `tier: tale\|epic`) + `<YYYYMM>/prompts/*.md` snapshots |
| document roles (e.g. `research`) | `<workspace>/sase/repos/<role>` | `<YYYYMM>/*.md` + `*_infographic.png`, generic per-role — **not** hardcoded to `research` |
| `beads` | `<workspace>/sase/repos/beads` | `config.json`, `metadata.json`, `issues.jsonl`, `events/` at the repo root, plus generated `pages/<lineage>/…` |
| `agents` | `~/.sase/projects/<key>/repos/agents` (machine-level, never in a workspace) | strict v2: `users/…/machines/…/hoods/…`, `agents/<global-name>/{README,meta,state,prompt,commits,chat}`, `families/<name>.md` |

The graph edges are already materialized and maintained:

- **Plan header block** (`docs/sdd_storage.md`, `src/sase/sdd/plan_header_*.py`) — fixed-order `PROMPT`, `PARENT`,
  `AGENTS`, `COMMITS` bullets, re-derived from durable state rather than accumulated, capped with a visible
  `… and N more` rather than silently truncated.
- **Bead pages** (`src/sase/bead_pages/`) — lineage roots take `README.md` so GitHub renders the directory; every
  descendant is `<full-id>.md`; pages carry status/owner/plan link, a phase table, a Mermaid lineage graph, and a commit
  table. Addressing is *lexical and derivable offline* (`bead_pages/paths.py`), which is why a `SASE_BEAD` commit trailer
  can link to a page the same commit has not published yet.
- **Agent and family pages** (`src/sase/agents_sync/rendering_*.py`) — breadcrumb, summary, files, commits, variables,
  neighbors, with `member-<role>` anchors and a family lineage diagram; strictly deterministic optional-section order.
- **Cross-repo hosted links** (`src/sase/sdd/hosted_links.py`) — a memoizing resolver that turns plan/agent/commit/bead
  identities into GitHub URLs, degrading to unlinked labels rather than guessing.
- **Commit trailers** — `SASE_BEAD` and `SASE_AGENT` tie primary-repo commits back into the graph.

### 2.2 Rust-backed query and search already exist

- `sase_core::plan` (`read.rs`, `search.rs`, `refs.rs`, `artifact_link.rs`) and the Python facade
  `src/sase/plan_search/facade.py` already search the plans + document-role corpora, SDD-store-prioritized, with a
  filter-query layer.
- `sase_core::bead` (`read.rs`, `search.rs`, `jsonl.rs`, `events.rs`, `history.rs`) owns bead reads, search, and history.
- `sase_core::query` powers ACE's query language (`docs/query_language.md`) with batch operations.
- `sase_core::artifact_ref` owns a **kind-tagged reference grammar** — `commit`, `chat`, `bug`, `file`, `document` — with
  canonicalization, scanning, and resolution status (`exact`, `drifted`, `ambiguous`). Python's `artifact_refs.py` layers
  machine/project context on top.
- `sase_core::agent_scan` / `agent_identity` / `agent_family` / `machine_hood` own agent inventory and identity.

That last item matters more than it looks: **SASE already has a canonical, Rust-owned URL scheme for every artifact
kind.** A site's permalinks should be that grammar, not a new one.

### 2.3 An HTTP server already exists

`sase_core/crates/sase_gateway/` is an axum 0.7 server (~11k lines) with:

- 30 routes under `/api/v1/…` (`routes.rs:499-544`), a `fallback(unknown_route)`, and a committed API contract snapshot
  (`contract.rs`).
- Pairing challenge → bearer token flow, token storage, audit log (`storage.rs`).
- Server-sent events at `/api/v1/events` (`async-stream`).
- A **bind policy that refuses non-loopback binds** unless `--allow-non-loopback/-L` is passed explicitly
  (`server.rs:36-48`).
- A `sase-daemon` with a Unix socket, `host_identity`, foreground/background modes, and a feature flag
  `mobile_http_enabled` (`daemon.rs:24-40`) — i.e. **the daemon is already designed to host more than one HTTP feature**.
- Python lifecycle glue via `sase mobile gateway start` and fixed JSON-over-stdin host bridges
  (`src/sase/integrations/mobile_*.py`).

Available Rust workspace deps already include `axum`, `tower-http`, `tokio`, `rusqlite` (bundled SQLite), `sha2`,
`serde_json`, `chrono`. No Markdown crate yet.

### 2.4 A static-site build and deploy pipeline already exists

`mkdocs.yml` (mkdocs-material, `strict: true`, `site_dir: site`) → `just docs-check` → `wrangler.jsonc` serving
`site/` as Workers static assets → `.github/workflows/docs-deploy.yml` deploying to Cloudflare on push to `master`, with
`CLOUDFLARE_API_TOKEN` already configured and a post-deploy smoke check. `docs/_headers` and `docs/_redirects` are in
place. The site is `https://sase.sh/`.

So: SASE already knows how to build a static site and put it on Cloudflare. That is a large amount of borrowed
infrastructure and organizational muscle memory.

### 2.5 Presentation assets and skill generation already exist

- `sase repo init` writes deterministic per-sidecar `README.md` plus an `assets/<role>-directory-map.png` infographic
  (`src/sase/directory_map_assets.py`), repairing the image without clobbering derived content. Research notes already
  carry `*_infographic.png` companions. There is an established practice of generated explanatory media.
- Skills are **generated**, not hand-written: sources live in `src/sase/xprompts/skills/*.md` with `skill: true`
  frontmatter, rendered per provider by `sase skill init` through `SKILL.frame.template.md`, and deployed to chezmoi
  under a commit-first provenance guard (`.sase-skills-manifest.json`).
- ACE's tab model is centralized: `TAB_ORDER = ("agents", "changespecs", "axe")` with `changespecs` being the
  user-facing **Artifacts** tab, whose sub-tabs are `("commits", "plans", "chats", "bugs", "prs")` with per-sub-tab accent
  colors already chosen (`artifact_tabs.py:15-32`).

### 2.6 There is no existing "site" concept

A grep across `src/sase` for a site/sites noun finds only incidental matches (`sibling_repos.py`, `git_lock_retry.py`,
etc.). `default_config.yml` has no `site` key. This is greenfield naming space — with one collision to avoid, noted in
§4.8.

---

## 3. The Corpus Is Bigger Than It Looks

Measured on this machine for the `sase` project alone (2026-07-29):

| Corpus | Documents | Notes |
| --- | --- | --- |
| Plans | **3,303** `.md` | excludes prompt snapshots |
| Prompt snapshots | **2,800** `.md` | `<YYYYMM>/prompts/` |
| Research | **299** `.md` | plus infographics |
| Bead pages | **2,311** `.md` | over **2,320** beads, 407 event files |
| Agents sidecar | **12,585** `.md` | 5,389 agent dirs, 2,984 chats, 706 family pages; **33,693 files total** |
| Project docs | **77** `.md` | `docs/` |
| **Total** | **≈ 21,400 Markdown documents** | **≈ 80 MiB of Markdown** |

Three consequences fall straight out of these numbers, and they eliminate the two most obvious implementations.

**(a) mkdocs cannot do this.** mkdocs-material renders each page in Python and builds one monolithic client-side search
index. 77 pages is comfortable; 21,400 is not. Build time would go from seconds to many minutes, the search index would
be tens of MiB, and `strict: true` would turn every stale cross-sidecar link in 21,400 documents into a build failure.
Pointing the existing docs pipeline at the sidecars is *not* a viable shortcut, even though it looks like the cheapest
path.

**(b) Naive static export bumps hosting limits.** Cloudflare Workers static assets allow **20,000 files per version on
the free plan and 100,000 on paid**, with a 25 MiB per-file cap (raised September 2025; requires Wrangler ≥ 4.34.0).
One project's Markdown corpus alone already exceeds the free-plan file limit before HTML expansion, assets, or search
shards. Any static design needs a deliberate answer for the long tail — see §5.3.

**(c) The graph is worth more than the pages.** 21,400 documents is unbrowsable by hand. Search, filtering, lineage
navigation, and cross-corpus pivots *are* the product. That is an argument for an index-first design, and against a
"render every file to HTML and call it a site" design.

---

## 4. Design Space

### 4.1 Option A — Point mkdocs at the sidecars

Add the sidecar roots as extra `docs_dir` sources, extend `nav`, build with the existing pipeline.

- **Pro:** zero new infrastructure; reuses `just docs-check`, wrangler, the deploy workflow, and a theme the team knows.
- **Con:** fails on scale (§3a). `strict: true` becomes unusable. `nav` cannot express 21,400 pages. No incremental
  rebuild. No dynamic filtering. Agent data lives at machine level outside any workspace, so it cannot be a `docs_dir`
  sibling without copying. Verdict: **rejected as the primary design**, though it remains the right home for the
  *hand-written narrative* docs at `sase.sh`.

### 4.2 Option B — A new Python web server (FastAPI/uvicorn/Starlette)

- **Pro:** fastest to prototype; all the corpus adapters are already Python.
- **Con:** directly violates the recorded Rust core backend boundary — *"if a web app, CLI, editor integration, or another
  frontend would need the behavior to match the TUI, treat it as core backend logic."* A site is exactly the web app in
  that sentence. It would also add a second HTTP dependency stack, a second server lifecycle, a second auth story, and a
  second bind policy alongside the axum gateway that already solved all four. Verdict: **rejected.**

### 4.3 Option C — Extend the existing Rust gateway/daemon with a sites router, plus a deterministic static exporter

Add `sase_core::site` (model + index + render) and a `/sites` router in `sase_gateway`, gated by a new
`sites_http_enabled` daemon flag alongside `mobile_http_enabled`. Same process, same bind policy, same pairing/bearer
auth, same audit log, same SSE stream. Separately, a `sase site build` path renders the same model to a deterministic
static directory.

- **Pro:** honors the Rust boundary; reuses ~11k lines of hardened server code including the loopback refusal and the
  contract snapshot; one daemon lifecycle; `rusqlite` already available for the index; deterministic export matches every
  existing SASE generated-artifact convention; static output is shareable and offline-readable without running anything.
- **Con:** Rust work is slower to iterate than Python; needs a Markdown→HTML crate added to the workspace; needs a
  frontend asset story.
- Verdict: **recommended.**

### 4.4 Option D — Static generator only, no server

- **Pro:** simplest operationally; nothing to run; perfectly matches the existing bead-pages/agents-sync publication
  model.
- **Con:** no live view of running agents (the Overview tab's most valuable content is real-time), no incremental
  preview loop while an agent authors a site, and every read of private agent data requires a full rebuild. Verdict:
  **half the answer** — keep it as one of two render targets, not the whole design.

### 4.5 Option E — Hosted multi-tenant SASE Sites service

- **Pro:** closest to the Codex product; sharing is trivial.
- **Con:** SASE's first hosted service, with account/tenancy/billing/abuse surface, against a local-first product with an
  explicit no-generic-remote-surface stance. Verdict: **rejected for now.** The static export target plus the existing
  Cloudflare account gets 90% of the sharing value at ~0% of the operational cost.

### 4.6 Key decision: static-first, server for live

Adopt **one model, two render targets** — deliberately mirroring `mkdocs serve` vs `mkdocs build`, a split the team
already has intuitions for:

| Target | Command | Purpose | Data |
| --- | --- | --- | --- |
| **Live** | `sase site serve` | authoring loop, private data, running agents, instant queries, SSE live-reload | reads the index + live state |
| **Static** | `sase site build` → `sase site deploy` | durable, reviewable, shareable, offline, Git-committable | frozen at a source revision |

The static target is the *primary* one — it is what makes a site a SASE artifact rather than a running process.

### 4.7 Key decision: two site kinds

The user's two asks are genuinely two products. Conflating them would produce a muddle.

**Kind `project` — the generated project site.** One per project. Fully derived from the corpora; never hand-edited;
regenerated idempotently, byte-identically. This is ask #1: "all knowledge from these repos in one site, with multiple
tabs." Tabs (§5.2) mirror ACE.

**Kind `custom` — authored sites.** Named, agent-created, Codex-Sites-shaped: a launch hub, a review workspace, an epic
dashboard, a research gallery, a retro board. This is ask #2, and it is what `/sase_sites` primarily serves.

The `project` site is effectively "site zero" — a built-in `custom`-shaped definition that ships with SASE, so there is
one rendering engine and one widget vocabulary, not two.

### 4.8 Key decision: don't call it a codex

Tempting, but `codex` is already a first-class SASE agent-provider name (`AGENTS.md` is the Codex agent instruction
file; Codex is a supported runtime). Introducing "the project codex" as a SASE noun would collide in docs, config keys,
completions, and query tokens. **Use `sase site` and the kind names `project` / `custom`.**

### 4.9 Key decision: authored sites are declarative projections, not web apps

This is the most important divergence from Codex Sites, and it is what makes the feature tractable.

An authored site is a `SiteSpec`: a small YAML manifest plus optional narrative Markdown. Its data comes from **the
existing ACE query language** (`docs/query_language.md`, `sase_core::query`) evaluated against the site index. Widgets
are drawn from a fixed vocabulary:

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
        sort: id
      - kind: graph
        root: sase-26
  - id: reports
    title: Reports
    widgets:
      - kind: document_list
        role: research
        query: "mobile"
```

Widget vocabulary: `markdown`, `table`, `document_list`, `metric_row`, `timeline`, `board`, `graph`, `gallery`,
`commit_log`, `agent_roster`, `embed`. That covers every artifact type Codex users reportedly build (dashboards, project
trackers, review workspaces, launch hubs, galleries) while keeping output deterministic, diffable, PR-reviewable,
golden-testable, and free of arbitrary JS.

Why this is the right trade:

- An agent writes ~30 lines of YAML plus prose instead of a web app. Cheaper, faster, and far more likely to be correct.
- The diff in a PR is readable. A generated React app's diff is not.
- Golden-output tests work, matching how `agents_sync` and `bead_pages` are already tested.
- No arbitrary code execution in the hosting surface.
- Agents already know the query language from ACE, so the learning curve is near zero.

**Escape hatch:** allow `kind: raw` for a site that is just static assets an agent authored directly. Keep it explicitly
flagged, excluded from the default `project` site, and refused for `visibility: public` without an interactive consent
prompt. Do not build this in phase one.

### 4.10 Key decision: derive corpus tabs from the store record, not a hardcoded list

`docs/sdd_storage.md` is explicit that document sidecar roles are **generic**: "Every other enabled `repos.sidecar` role
is a document sidecar… `research` is only the document role seeded by default; it has no storage-level privilege." A
project can declare `designs`, `postmortems`, anything. Each gets its own clone, `sase repo path` resolution, agent env
var, plan-search kind, and ACE Plans kind.

So the site's corpus tabs must be **derived from the resolved store record's role map**, exactly as plan search and ACE
already do. Hardcoding a Research tab would immediately be wrong for any project that declares a different role.

---

## 5. Recommended Architecture

### 5.1 The Site Index (the actual product)

New Rust module `sase_core::site`, owning:

- **Node types**, keyed by the existing artifact-ref grammar extended with corpus kinds: `plan`, `prompt`, `document`
  (per role), `bead`, `agent`, `family`, `commit`, `chat`, `changespec`, `bug`, `file`.
- **Edge types**, all *derived from data that already exists* — no inference, no LLM:
  - plan → prompt, plan → parent plan, plan → agents, plan → commits (the plan header block)
  - bead → plan, bead → phase beads, bead → commits, bead → agents (bead pages + event store)
  - agent → prompt/chat/commits/variables, agent → family, agent → neighbors (agents-sidecar v2 snapshots)
  - commit → bead, commit → agent (`SASE_BEAD` / `SASE_AGENT` trailers)
  - document → any of the above (artifact-ref scanning, already implemented in `artifact_ref/scanner.rs`)
- **Persistence:** SQLite at `~/.sase/projects/<key>/site/index.db` via `rusqlite`, following the `beads.db` precedent —
  a *derived cache*, never a source of truth, safe to delete and rebuild, and `.gitignore`d like `beads.db*` already is.
- **Incremental build:** key each document by Git blob SHA (or `mtime`+`size` for the machine-level agents clone) so a
  rebuild re-parses only what changed. This is what makes a 21,400-document corpus workable, and it is the same
  content-addressing discipline `agents_sync` already applies to snapshots.
- **Determinism:** sorted iteration, no wall-clock in output, no random IDs, stable anchors — matching the existing
  contract that "identical inputs produce byte-identical files."

Reuse rather than reimplement: `sase_core::plan::read/search`, `sase_core::bead::read/search/events`,
`sase_core::agent_scan`, `sase_core::artifact_ref::scanner`, `sase_core::query`.

### 5.2 Project-site tabs

Mirror ACE so the two surfaces teach each other, and derive the corpus tabs from the store record (§4.10):

| Tab | Content | Primary source |
| --- | --- | --- |
| **Overview** | project pulse: open/closed beads, epic progress, recent commits, active and recent agents, latest plans | index + live state |
| **Plans** | month-sharded plan browser; tier filter (`tale`/`epic`); header-block provenance rendered as real navigation; full text | plans sidecar |
| **Beads** | lineage trees, phase tables, status/size/type filters, existing Mermaid graphs | beads sidecar |
| **Agents** | hood → family/clan → member browsing; prompts, chats (gated), commits, variables, neighbors | agents sidecar |
| **Artifacts** | commits, ChangeSpecs/PRs, chats, bugs — the same five sub-tabs ACE already defines, with the accent colors already chosen | index + ChangeSpecs |
| *(per role)* | one tab per document sidecar role — **Research** for the default seed, plus any project-declared role | document sidecars |
| **Docs** | the project's own `docs/` tree, if present | primary repo |
| **Graph** | the cross-corpus knowledge graph, navigable | index |
| **Search** | unified search across everything above | index |

Reuse `ARTIFACTS_SUBTAB_ORDER` and `ARTIFACTS_ACCENTS` verbatim so the web and TUI palettes cannot drift — the same
single-source-of-truth reasoning that produced `tab_order.py`.

### 5.3 Static export strategy at 21,400 documents

Do **not** emit one HTML file per source document by default. Instead:

1. **Pre-render** the shell, all tab landing pages, the graph, and every *high-value* page: plans, bead pages, research
   and other document-role notes, family pages. That is roughly 3,300 + 2,311 + 299 + 706 ≈ **6,600 pages** — comfortably
   within limits and fully crawlable/linkable.
2. **Shard the long tail** into JSON fetched on demand: prompt snapshots (2,800), agent READMEs (5,389), and agent chats
   (2,984) become per-month/per-hood shards rather than ~11,000 separate HTML files. These are exactly the buckets that
   are both largest and least often deep-linked.
3. **Shard the search index** by corpus and month, with the prefix structure built in Rust. Never emit one monolithic
   index.
4. **Scope flags** for the rest: `sase site build --months 6`, `--since <rev>`, `--corpus plans,beads`,
   `--exclude-chats`. Report what was excluded in the build summary — SASE's convention is that a bounded projection says
   so out loud (`… and N more`, publication diagnostics) rather than truncating silently.

Result: a default project-site build lands around 7-8k files, well inside the free-plan 20,000 limit with headroom for
assets, and inside 100,000 on paid even with every option enabled.

### 5.4 Serving

Add a `sites` router to `sase_gateway`, behind a new `DaemonConfig.sites_http_enabled` flag next to `mobile_http_enabled`:

```
GET  /sites/                          # site directory (project site + authored sites)
GET  /sites/:site/                    # site shell
GET  /sites/:site/api/tabs
GET  /sites/:site/api/query?q=…       # ACE query language against the index
GET  /sites/:site/api/node/:ref       # artifact-ref addressed node
GET  /sites/:site/api/search?q=…
GET  /sites/:site/events              # SSE: index changes, live-reload
```

Inherit *unchanged*: the non-loopback bind refusal, the pairing → bearer-token flow, token storage, the audit log, the
contract snapshot discipline in `contract.rs`, and the fixed-operation principle (no generic file/shell/RPC surface).
Serve static assets with `tower-http`'s `ServeDir`; add a Markdown crate (`pulldown-cmark` or `comrak`) to the workspace
for Markdown→HTML, and keep Mermaid client-side since bead pages already emit Mermaid source.

Frontend assets: a small hand-written vanilla bundle — no npm framework. The repo's only JS dev dependency today is
`prettier`, and there is no JS build step anywhere. Adding a React/Vite toolchain for this would be the largest new
maintenance burden in the whole proposal for the least differentiated value. Ship CSS + a tiny client-side router +
fetch, formatted by the prettier that is already configured.

### 5.5 Publishing, versions, and visibility

Steal Codex's save/deploy split, and bolt it to SASE's existing consent machinery.

**Visibility ladder** (default `local`):

| Level | Meaning |
| --- | --- |
| `local` | `sase site serve` only. Never leaves the machine. |
| `sidecar` | Built output committed to a `site` sidecar repo (`<owner>/<repo>--site`), browsable in Git. Optionally GitHub Pages. |
| `public` | Deployed to Cloudflare (own Worker/route, e.g. `sites.sase.sh/<project>`), reusing the existing account and `wrangler` know-how but **not** the `sase.sh` Worker. |

**Versions:** `sase site build` produces a content-addressed **version** recorded against the source revision of every
contributing repo — a direct analogue of Codex's commit-associated saved version, and of the digest discipline
`agents_sync` already uses. `sase site versions` lists them; `sase site deploy <version>` publishes one. Never
build-and-deploy in a single implicit step.

**Consent:** deploying above `local` requires explicit interactive authorization, modeled on `sase repo init`'s public-
sidecar prompt — which already establishes that "non-interactive input and `sase init --yes` cannot grant this
resource-specific authorization." Agents must not be able to deploy; see §6.

**Privacy — this is the sharpest risk in the whole feature.** `docs/agents_sidecar.md` is emphatic: the agents sidecar
carries prompts, chat transcripts, and sanitized output variables, and "they are visible to anyone who can read the
agents sidecar, so do not use output variables for secrets." A project site that naively unifies all four corpora and
goes public would publish every prompt and chat the project has ever produced — **2,984 chat transcripts on this machine
alone.** Therefore:

1. The `project` site **excludes agent prompts, chats, and output variables by default**. Opt in per-corpus with an
   explicit flag, not a config default.
2. `sase site build` must **refuse** `visibility: sidecar|public` when the project's `agents` sidecar is configured
   `visibility: private` or `disabled: true`. Deriving a public site from a deliberately private corpus is a
   privacy regression with a Git-durable blast radius.
3. `sase doctor` gains a check for site visibility vs. corpus visibility drift.
4. Reuse the existing privacy language verbatim rather than inventing new wording.

### 5.6 Code placement (Rust core boundary)

| Concern | Home |
| --- | --- |
| Site model, index schema/build/query, version hashing, manifest parsing, deterministic HTML/JSON render | `sase-core/crates/sase_core/src/site/` |
| `/sites` router, SSE, static asset serving | `sase-core/crates/sase_gateway/src/sites.rs` |
| Python bindings | `sase_core_py` → `src/sase/site/facade.py` |
| CLI (`sase site …`), config schema, sidecar role resolution, Git commit routing, consent prompts, deploy invocation | `src/sase/site/` |
| ACE integration (open the site for the selected row) | `src/sase/ace/tui/actions/` |
| GitHub `site` sidecar creation / Pages enablement | `sase-github` plugin repo |
| Frontend assets (CSS/JS/templates) | `sase-core/crates/sase_core/src/site/assets/`, embedded in the binary |

Litmus test from the recorded boundary memory — *"if a web app… would need the behavior to match the TUI, treat it as
core backend logic"* — puts the index, query, and render squarely in Rust core. Adding a `site` sidecar role is a
cross-repo change (`sase`, `sase-core`, `sase-github`), matching the boundary note's instruction to update the Rust
wire/API and tests first, then the Python callers.

### 5.7 CLI surface

Following the recorded CLI rules — alphabetically sorted subcommands, a short alias for every public long option,
excellent `-h`, colored output, and the bare-group-defaults-to-`list` convention wired centrally in
`_default_list_subcommands()`:

```
sase site                       # → sase site list (with the standard delegation notice)
sase site build [name]          # render a version; -m/--months, -s/--since, -c/--corpus, -x/--exclude, -o/--out
sase site check                 # validate every SiteSpec + report drift; -j/--json
sase site deploy [name]         # publish a version; -V/--version, -t/--target; requires consent
sase site index                 # rebuild/refresh the index; -f/--full, -j/--json
sase site list                  # sites for the project; -a/--all, -j/--json
sase site new <name>            # scaffold a SiteSpec; -T/--template, -t/--title
sase site open [name]           # print the resolved site source path (mirrors `sase repo open`)
sase site serve [name]          # daemon sites router; -p/--port, -b/--bind, -L/--allow-non-loopback
sase site show <name>           # one site's spec, version history, deploy state; -j/--json
sase site versions [name]       # recorded versions; -j/--json
```

Config under a new `site:` key: `default_visibility`, `index.refresh_ttl_seconds`, `serve.{bind_address,port}`,
`build.{months,exclude}`, `deploy.target`. Add `repos.sidecar` support for a `site` role.

---

## 6. The `/sase_sites` Skill

Follow the generated-skill pipeline exactly: author `src/sase/xprompts/skills/sase_sites.md` with `skill: true`
frontmatter, render per provider with `sase skill init`, and respect the commit-first provenance guard
(`--diff`/`--dry-run` while iterating; commit and land, *then* `sase skill init --force` from a clean merged tree).

**Model it on `/sase_repo`, not on a reference card.** `sase_repo` works because it establishes a hard contract: *use
the skill first, then use the printed path as the only path*. Sites need the same discipline, because the failure mode —
an agent hand-writing HTML into the export directory, or editing generated `project`-site output — is otherwise very
likely.

Skill contents:

1. **Fetch** — `sase site list`, `sase site show <name> --json`, `sase site open <name>` prints the source path; that
   printed path is the only path for reads and writes. Never locate a site's sources any other way.
2. **Create** — `sase site new <name> -T <template>` scaffolds the `SiteSpec`; the agent then edits `site.yml` and the
   narrative Markdown beside it. Templates: `dashboard`, `board`, `review`, `gallery`, `report`.
3. **The widget vocabulary and the query language.** The bulk of the skill body. Include the full widget list with a
   worked example each, and point at `docs/query_language.md` for data sources. This is where the skill earns its keep:
   an agent that knows the vocabulary produces a good site on the first attempt.
4. **Verify** — `sase site check` before finishing; `sase site build <name>` to confirm it renders. Both are read-only
   with respect to published state.
5. **Hard boundaries**, stated plainly:
   - Never edit the generated `project` site — it is derived; change the generator or the corpus instead.
   - Never write into a build output directory.
   - **Never deploy.** Publishing above `local` is a user decision. If a deploy is warranted, propose it through
     `/sase_gate` and let the user confirm — consistent with the existing rule that agents never create commits,
     branches, or PRs directly.
   - Site sources are committed through `/sase_git_commit` → `sase commit` like any other change.
6. **Privacy note** — authored sites can surface agent prompts, chats, and output variables. Do not include those
   corpora in a site intended for sharing. Reuse the agents-sidecar privacy wording.

Also add a `#site` / `#sites` xprompt so a launch can request site work directly (`#gh:sase %auto #pr:launch_hub
#site:mobile_launch build a launch hub for the mobile epic`), and register the skill in the memory-generated skill
listing.

---

## 7. Recommended Plan

An epic with six phases. Phases 1-3 deliver ask #1; phase 4 delivers ask #2; phase 5 makes it shareable.

**Phase 0 — Spike and scope lock (small).** Prototype the index build in Rust against the real corpus on this machine.
Measure cold and incremental build time and `index.db` size for 21,400 documents. Confirm the Markdown crate choice
(`pulldown-cmark` vs `comrak` — the latter if GitHub-flavored tables and footnotes matter, which they do given the
existing page corpus). Record the measured numbers in the plan; they set the perf floor, in the style of
`docs/perf_runbook.md`. Decide the `site` sidecar role name and settle the `project`/`custom` kind vocabulary.

**Phase 1 — `sase_core::site` index + minimal static build (medium).** Node/edge schema, SQLite persistence,
incremental keying by blob SHA. Ingest plans, document roles, and beads first (workspace-local, simplest). `sase site
index` and `sase site build` for a `project` site with Overview, Plans, and Beads tabs. Deterministic golden-output
tests modeled on the `agents_sync`/`bead_pages` suites. Local visibility only; no server, no deploy.

**Phase 2 — Agents corpus, search, graph, remaining tabs (medium).** Ingest the machine-level agents sidecar with
prompts/chats/variables **excluded by default**. Sharded search index. Graph tab. Artifacts tab reusing
`ARTIFACTS_SUBTAB_ORDER` and `ARTIFACTS_ACCENTS`. Per-role document tabs derived from the store record. Long-tail JSON
sharding and the `--months`/`--since`/`--corpus`/`--exclude` scope flags with an explicit exclusion summary.

**Phase 3 — `sase site serve` (medium).** `sites_http_enabled` on `DaemonConfig`; the `/sites` router; SSE live-reload;
query and node APIs; contract snapshot extension. ACE integration: open the site page for the selected agent, bead,
plan, or commit. Reuse the gateway's bind policy and auth without modification.

**Phase 4 — Authored sites and the `/sase_sites` skill (medium).** `SiteSpec` schema and validation, the widget
vocabulary, templates, `sase site new/open/show/check`, and the generated skill. Ship the skill only after the CLI is
stable, per the CLI/skill contract-synchronization rule.

**Phase 5 — Publishing (medium).** The `site` sidecar role (touches `sase-github`), content-addressed versions recorded
against contributing revisions, `sase site versions`, `sase site deploy`, the visibility ladder, consent prompts, the
refuse-public-when-agents-private rule, and `sase doctor` checks. A `sites-deploy` GitHub workflow modeled on
`docs-deploy.yml`.

**Phase 6 — Continuous freshness (small).** Post-commit incremental index refresh, following the best-effort,
never-raises pattern of `bead_pages/publication.py` and the durable outbox pattern of `agents_sync/publication_outbox.py`.
Optional axe chop for periodic full rebuilds.

### Cheap interim win, worth doing regardless

Before phase 1 lands, a **root index page across sidecars** — a generated `README.md` section in each sidecar linking to
its siblings, plus a project-level landing document — costs almost nothing and immediately improves cross-corpus
navigation on GitHub. It reuses the `sase repo init` README-generation path that already exists. It is not a substitute
for the site (no search, no filtering, no tabs), but it is a real improvement available in a single small change.

---

## 8. Risks and Open Questions

| Risk | Mitigation |
| --- | --- |
| **Privacy blast radius.** 2,984 chats and 5,389 agent prompts could be published irreversibly into Git. | Exclude by default; refuse public build when the agents sidecar is private; doctor check; explicit consent. §5.5 |
| **Scale creep.** The corpus grew to 21,400 documents in months; it will keep growing. | Index-first design, incremental builds, sharded output, scope flags with loud exclusion reporting. |
| **Determinism regressions.** A site is a generated artifact; nondeterminism breaks golden tests and produces noisy Git diffs. | No wall-clock/random in output; sorted iteration; content-addressed versions; golden tests from phase 1. |
| **A new JS toolchain.** | Vanilla assets, no framework, formatted by the existing prettier. Revisit only with evidence. |
| **Scope confusion between the two site kinds.** | Distinct kind names, distinct docs sections, one engine. §4.7 |
| **Cross-repo coordination** (`sase`, `sase-core`, `sase-github`). | Rust wire/API and tests first, then Python callers, per the boundary memory. Phase 5 isolates the plugin change. |

Open questions for you:

1. **Multi-project sites.** Should one site be able to span several SASE projects (a personal "everything" site)? The
   index is per-project by design; a cross-project site is a straightforward composition later, but it changes the URL
   scheme. Recommend deferring.
2. **Deploy target.** A separate Cloudflare Worker (`sites.sase.sh`), a route on the existing `sase.sh` Worker, or
   GitHub Pages on a `--site` sidecar? Recommend a separate Worker: it keeps the docs site's deploy blast radius
   untouched and its smoke test meaningful.
3. **Should the `sase` project's own site be public?** It would be a strong demo of SASE-on-SASE, and much of the corpus
   is already in public sidecars — but it would publish 2,984 chat transcripts unless explicitly excluded. Worth deciding
   deliberately rather than by default.
4. **Chat interface.** DeepWiki's chat-over-the-index is genuinely useful at this corpus size. Out of scope here, but the
   index is exactly the retrieval substrate it would need. Worth noting as a natural phase 7.

---

## 9. Bottom Line

Do not build a new SASE web server. Build a **site index in `sase_core`**, render it two ways — a deterministic static
export as the primary artifact, and a `/sites` router on the **existing** `sase_gateway`/`sase-daemon` for the live
authoring loop — and express both the generated project site and agent-authored sites as **declarative `SiteSpec`
projections over that index**, with data sourced through the ACE query language that already exists.

SASE's knowledge graph is already written down, already deterministic, already transactional, and already cross-linked.
Sites should read it, not rebuild it. The work is an index, a renderer, and a widget vocabulary — plus the discipline to
keep 2,984 chat transcripts from accidentally becoming a public website.

---

## Sources

- [Sites — ChatGPT/Codex documentation](https://learn.chatgpt.com/docs/sites)
- [OpenAI Sites: A Detailed Guide to Codex's New Hosted Website and App Builder — Kingy AI](https://kingy.ai/news/openai-sites-a-detailed-guide-to-codexs-new-hosted-website-and-app-builder/)
- [OpenAI Codex Sites Explained: Who Can Use It & Limits (2026) — Taskade](https://www.taskade.com/blog/codex-sites-explained)
- [Codex Sites is now ChatGPT Sites: cost, access, limits — Stacktree](https://stacktr.ee/blog/sites-in-codex-explained)
- [Increased static asset limits for Workers — Cloudflare changelog](https://developers.cloudflare.com/changelog/2025-09-02-increased-static-asset-limits/)
- [Static Assets — Cloudflare Workers docs](https://developers.cloudflare.com/workers/static-assets/)
- [DeepWiki — Devin Docs](https://docs.devin.ai/work-with-devin/deepwiki)
- [DeepWiki Complete Guide (2026) — Codersera](https://codersera.com/blog/deepwiki-complete-guide-2026/)
- In-repo: `docs/sdd_storage.md`, `docs/agents_sidecar.md`, `docs/architecture.md`, `docs/mobile_gateway.md`,
  `docs/query_language.md`, `mkdocs.yml`, `wrangler.jsonc`, `.github/workflows/docs-deploy.yml`,
  `src/sase/bead_pages/`, `src/sase/agents_sync/`, `src/sase/sdd/hosted_links.py`, `src/sase/artifact_refs.py`,
  `src/sase/plan_search/facade.py`, `src/sase/ace/tui/tab_order.py`, `src/sase/ace/tui/artifact_tabs.py`,
  `src/sase/xprompts/skills/`
- In `sase-core`: `crates/sase_gateway/src/{routes,server,daemon,contract}.rs`,
  `crates/sase_core/src/{artifact_ref,plan,bead,query}/`
