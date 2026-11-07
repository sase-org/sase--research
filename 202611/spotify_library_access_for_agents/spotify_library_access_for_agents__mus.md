# Spotify access for SASE agents — research report (mus)

Date: 2026-11-07. Researcher: mus (5-researcher swarm, independent report).
Question: how should SASE agents get access to Bryan's Spotify — read playlists +
songs, followed podcasts, and (gated) playlist management — possibly via a new
`sase-org/sase--spotify` plugin repo? Design should be intuitive, reliable, and
beautiful.

## TL;DR recommendation

Yes, build it, but narrower than asked and in phases. A new **command plugin**
(`sase spotify`, in the style of `sase-listen`'s `sase_commands` mount) backed by the
Spotify Web API with Authorization-Code + PKCE login is the right shape. Phase 1:
read-only (own playlists, playlist items, followed podcasts, search, `whoami`) plus
auth plumbing. Phase 2: mutating playlist ops where **every mutation is proposed
through a custom `/sase_gate`** (preview + approve/reject), never executed inline by
default. Phase 3 (optional polish): an `@spotify`-style artifact-reference provider
and curation macros so output is beautiful, not just JSON. Do **not** build playback
control, recommendations/taste analysis, or multi-user support — Spotify removed or
restricted the endpoints those need, and they expand scope without serving the stated
goals. One naming adjustment: prefer `sase-spotify` (single dash) over
`sase-org/sase--spotify` to match installable-plugin convention (details in §7).

## 1. Is this a good idea? Critique of the plan

**Verdict: good idea, with the read side carrying ~90% of the value.** Giving agents
read access to playlists and followed shows unlocks genuinely useful workflows
("what's in my Focus playlist", "summarize new episodes of shows I follow", "build a
dinner-party playlist from songs I already like"). The write side is nice-to-have and
correctly flagged as gated — playlist mutation is destructive (reorder/replace/delete
have no undo), so the gate is not optional garnish, it is the feature.

Critiques and adjustments (each marked **[ADJUSTMENT]**):

1. **[ADJUSTMENT] Drop playback control from scope.** "Access my Spotify" tempts
   toward play/pause/queue/device control. Nothing in the goals needs it, it requires
   an active device and the `user-modify-playback-state` scope family, and agents
   driving playback is a footgun (an agent pausing your music mid-standup is not
   delightful). Explicitly out of scope.
2. **[ADJUSTMENT] "Podcasts I follow" needs a definition.** In Spotify's model there
   is no "followed podcasts" list per se — there are *saved shows* (`GET /me/shows`,
   colloquially "your podcasts") and followed artists/users/playlists. The requirement
   should read: "list my saved shows (podcasts) plus recent episodes per show." That
   is implementable with `user-library-read`. Optionally also surface followed
   *playlist* follows via the generic library check (§3).
3. **[ADJUSTMENT] Expect degraded data for playlists you don't own.** Since the
   February 2026 changes, playlist `items` are only returned for playlists the user
   owns or collaborates on; for followed-but-not-owned playlists only metadata comes
   back (verified against Spotify's official Feb 2026 migration guide — see §3). The
   design must degrade gracefully ("header renders, empty track list + explanation"),
   not error. This directly affects goal 1: "what songs are in those playlists" only
   holds for owned/collaborative playlists.
4. **[ADJUSTMENT] The gate should be per-mutation-batch, not per-command-binary.**
   The prompt suggests "a custom /sase_gate maybe" for management. Stronger: *all*
   mutating operations go through a gate by default, with the gate's action payload
   showing an exact preview (tracks to add/remove, new order) and a dry-run diff. A
   `--yes` escape hatch exists for scripts but agents must not use it without an
   already-answered gate. Read-only commands never gate (otherwise every lookup
   becomes a click, and agents stop using the tool).
5. **[ADJUSTMENT] "Beautiful" belongs in the presentation layer, not the API.**
   A CLI that emits stable JSON plus a human table renderer (SASE's existing rich
   rendering, cf. `sase gate list` / plugin catalog chips like `❯ sase listen`) plus
   one curation macro/skill is what makes this feel beautiful. Do not build a TUI tab
   in phase 1 — that pulls in `tui.md` territory (live screenshots, perf budgets) for
   little gain over good tables.

## 2. How SASE plugins work (what the new repo would plug into)

Verified against this checkout's docs (`docs/reference/integrations/plugins.md`,
`plugins-commands.md`, `docs/contribute/plugin-api.md`):

- SASE discovers optional functionality via Python **entry-point groups** (13 groups).
  The groups relevant here:
  - `sase_commands` — mounts a top-level `sase <name>` command (e.g. `sase-listen`
    ships `sase listen`). Contract: module exposing `main(argv, prog)` +
    `build_parser(prog)`, cheap to import, never imports `sase`. In-process execution,
    plugin owns its subtree and help. Names match `^[a-z][a-z0-9-]{0,31}$`.
  - `sase_artifact_refs` — declarative document providers (e.g. `@research` from
    `sase-research-artifacts`). Phase-3 material (`@spotify:playlist:<id>`).
  - `sase_macros` — prompt/macro templates (skills). A curation skill ("rebuild my
    running playlist from these seeds") fits here.
  - `sase_config` — default configuration bundle (`default_config.yml` fragment).
- Precedents: `sase-listen` (standalone binary + `sase_commands: listen` mount —
  **the closest template for this project**); `sase-github` (VCS/workspace/macros/
  task-types); `sase-telegram` (job scripts, no entry points); `sase-research-artifacts`
  (macros + artifact refs + file hooks + config — the phase-3 template).
- The plugin catalog treats the GitHub `sase--plugin` topic as the registry; install
  flows through `sase plugin install` / the Admin Center Updates tab (`uv tool`
  receipts authoritative).

Implication: a Spotify integration needs **no changes to SASE core**. It is a pure
out-of-tree plugin using public, documented extension points — low coupling, no core
review burden beyond normal plugin listing.

## 3. Spotify Web API reality check (verified 2026-11-07)

Sources: Spotify's official [February 2026 migration
guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
(fetched and read in full during this research), plus PyPI pages for the two most-used
agent-facing wrappers (`mcp-server-spotify`, `mcp-spotify`). Key facts, all from the
official guide unless noted:

- **Auth for user data must be OAuth 2.0 Authorization Code (+PKCE for a CLI).**
  Client Credentials gives only catalog data — useless for "my playlists". Tokens live
  ~1h; refresh-token rotation is mandatory plumbing, not a nice-to-have.
- **Quota modes are the decisive constraint.** Extended Quota Mode apps: unchanged
  behavior. **Development Mode apps** (what a personal plugin gets by default): owner
  must hold **Spotify Premium** (lapse = app stops); Client IDs per developer capped
  (1 at Feb 2026, raised to 25 per the July 2026 changelog); users per app capped
  (5, grandfathered for existing apps). For a single-user agent tool this is fine —
  but it means "share this plugin with friends" does not work without an Extended
  Quota application. Call this out in the README so nobody is surprised.
- **Endpoint renames (breaking for Dev Mode apps; old paths 403):**
  `/playlists/{id}/tracks` → `/playlists/{id}/items` (GET/POST/PUT/DELETE), response
  `tracks` → `items`, `items[].track` → `items[].item`, DELETE body `tracks` →
  `items`. `POST /users/{id}/playlists` → `POST /me/playlists`.
- **Generic library endpoints replace ~14 specific ones** (Dev Mode): save/follow =
  `PUT /me/library` with Spotify URIs; remove/unfollow = `DELETE /me/library`;
  contains-checks = `GET /me/library/contains`. One code path for tracks, albums,
  episodes, shows, audiobooks, artists, playlists. New code should target these; old
  endpoints keep working only in Extended Quota.
- **Removed with no replacement (Dev Mode):** batch fetches (`GET /tracks?ids=…`
  etc. → one request per item), browse (`/browse/*`), artist top-tracks, other users'
  profiles/playlists (`GET /users/{id}` gone — `GET /me` and `GET /me/playlists`
  only), audio-features/analysis/recommendations families (restricted — do not design
  "vibe analysis" features on them), several response fields (`popularity`,
  `followers`, `available_markets`, `email`, …), search `limit` max 50 → **10**
  (paginate with `offset`).
- **Rate limits tightened** (per the guide's closing guidance: "limit API calls").
  Design consequence: paginate lazily, cache `GET /me/playlists` snapshots briefly,
  never fan out one-request-per-track without batching thought.

**Endpoint map for the stated goals** (all `GET`s OAuth-scoped as noted):

| Goal | Endpoint | Scope |
|---|---|---|
| Own playlists | `GET /me/playlists` | `playlist-read-private` (+ `playlist-read-collaborative`) |
| Songs in a playlist | `GET /playlists/{id}/items` (+ `GET /playlists/{id}` for metadata) | same as above; owner/collaborator-only for items |
| Followed podcasts | `GET /me/shows` (saved shows), `GET /shows/{id}/episodes` | `user-library-read` |
| Identity check | `GET /me` | `user-read-private` |
| Search (needed for adds) | `GET /search` (limit ≤ 10, paginate) | none beyond auth |
| Create playlist | `POST /me/playlists` | `playlist-modify-public` and/or `-private` |
| Add/reorder/replace/remove | `POST /playlists/{id}/items`, `PUT /playlists/{id}/items`, `DELETE /playlists/{id}/items` | modify scopes above |
| Follow/unfollow (playlists, artists) | `PUT/DELETE /me/library` with URIs | `user-follow-modify` / library-modify family |

## 4. Options considered

| Option | Shape | Upside | Downside | Fit |
|---|---|---|---|---|
| **A. Command plugin `sase spotify`** (recommended) | `sase_commands` entry point, own CLI + token store | Matches `sase-listen` precedent; shell-composable; gates wrap commands naturally; zero core changes | Must implement OAuth loopback + refresh (solved problem, ~1 focused module) | Best |
| B. Macros-only (curl snippets in a skill) | `sase_macros` skill calling Web API directly | Smallest code | No safe token store; every agent re-solves auth; fragile against API churn; mutations un-auditable | Reject |
| C. Wrap an MCP server (`mcp-server-spotify`) | Reuse existing MCP tool server | Less code today | SASE agents are CLI-driven; adds an MCP transport SASE doesn't natively consume; inherits that server's scope/auth choices; Feb-2026 currency must still be verified per release | Fallback only |
| D. Artifact-ref provider first (`@spotify:…`) | `sase_artifact_refs` provider | Beautiful references in prompts | Providers are *readers* for documents, not CLIs; auth + mutation still need a home → really "A phase 3", not an alternative | Phase 3 |

MCP note (from PyPI): `mcp-server-spotify` (stdio/SSE/HTTP, search/playback/playlists/
library/podcasts/follow, PKCE via `127.0.0.1:8888/callback`) proves the *UX shape* works
for agents and is a good feature checklist — but SASE's extension story is entry
points, not MCP transports, so vendoring its approach inside a native command plugin
beats bridging protocols.

## 5. Proposed design (command plugin)

**Repo:** new plugin repo (naming in §7). Layout mirrors `sase-listen`: standalone
`spotify` CLI installable via `uv tool`, plus a thin `sase_command` shim module
(`main`/`build_parser`, no `sase` import).

**Auth (`sase spotify login | logout | status | whoami`):**
Authorization Code with PKCE, loopback redirect (`http://127.0.0.1:<port>/callback`,
same pattern as the MCP servers). Token cache file mode `0600` under the SASE state
dir (precedent: `~/.sase/sase_listen_feed_token` observed on this machine — same
neighborhood, distinct filename). Auto-refresh on 401 with single-flight refresh.
Minimal scopes by default (table in §3, read set + `user-read-private`); request
modify scopes only via `login --with-write` so a read-only install never holds
destructive capability. `status` shows expiry + quota-mode-unknown caveat; `whoami`
prints `GET /me` display name + product (when present).

**Read commands (never gated):** `playlists [--limit/--offset]`, `playlist show
<id> [--episodes?]`, `playlist items <id>` (with graceful owned-vs-followed note per
§3), `shows`, `show episodes <id>`, `search <q> --type track,show,…`, all with
`--json` (stable, agent default) and human tables (rich; chips for URIs). Cache
`GET /me/playlists` for minutes, not hours — playlists change.

**Write commands (always gated in agent use):** `playlist create`, `items add`,
`items remove`, `items move/reorder`, `playlist follow/unfollow` (via `PUT/DELETE
/me/library`). Every one supports `--dry-run` emitting the exact mutation preview
that the gate action will display.

**Reliability rules:** target only non-deprecated endpoints (§3 table); page
everything (`limit` 10 on search); treat missing `items` on non-owned playlists as
expected, not error; treat removed fields as absent (no `KeyError` paths); exponential
backoff on 429 honoring `Retry-After`; pin a `sase-spotify↔Web-API` compatibility
note per release (Spotify ships breaking changes yearly now: Nov 2024, Feb 2026 —
assume more).

## 6. Gate design for mutations (the `/sase_gate` part)

Follow the `sase_gate` skill contract (read `src/sase/macros/skills/sase_gate.md` in
the implementing turn): one option query reading like the decision
(`(apply AND previewed) OR reject`), single-glyph icon (🎵 or 🛡️), one-line
`presentation.title` ("Add 12 tracks to 'Focus'"), every option owning a command
(reject = no-op JSON), `feedback` explicit, `gate_timeout_seconds` set (playlist edits
should not hang forever; e.g. 24h), `presentation.notes` required.

Concretely, the agent flow for "add songs to my running playlist":

1. Agent resolves intent → runs `sase spotify search …` / `playlist items …` (read,
   ungated) and builds a precise preview.
2. Agent runs `sase spotify items add --dry-run …`, embeds that diff in a custom
   gate via `sase gate create` (query: `apply OR reject`), then waits.
3. On approve, the gate's owned command executes the real mutation; the result
   (snapshot id / new version) is reported back. `--yes` exists but agents are
   instructed (macro skill text) never to use it — approval flows through the gate
   so it is durable, auditable, and mobile-answerable.

Destructive ops (`remove`, `reorder/replace`, `unfollow`) get an additional explicit
"no undo" line in `presentation.notes`. Creation is the least scary mutation but
still gated (it writes to the user's library).

## 7. Repo recommendation (naming adjustment)

**[ADJUSTMENT] Name it `sase-spotify`, not `sase--spotify`.** The installable,
catalog-listed plugins in this ecosystem use single-dash names (`sase-github`,
`sase-telegram`, `sase-nvim`, `sase-listen`) and gain catalog listing via the
`sase--plugin` GitHub topic; double-dash (`sase--research`) reads as the sidecar/
research-artifact convention, and `sase--research` is *not* installed via
`plugin install` the same way. If the org genuinely wants a `sase--*` family for
user-data integrations, say so in the plan — but default to `sase-spotify` so
` sase plugin install spotify` and the Updates tab work unchanged. Either way, add
the `sase--plugin` topic at creation.

Also: the plugin needs **no new entry-point group and no core change** — `sase_commands`
(+ later `sase_macros`, `sase_config`, `sase_artifact_refs`) already cover it. The
one cross-repo touch is docs: a short `docs/` page + `sase.sh` link per
`docs_writing.md` when it lands (implementing agent reads that note first).

## 8. Risks and open questions

1. **Dev Mode quota ceiling.** Fine for one user; multi-user sharing needs Extended
   Quota approval from Spotify. README must state this.
2. **API churn.** Two breaking rounds in 16 months (Nov 2024, Feb 2026). Mitigation:
   thin API client module, endpoint table in-repo, live-probe CI job (own account)
   that fails fast on 403/404 shape changes.
3. **Podcast coverage gaps.** Shows/episodes access can differ by region/catalog;
   verify `GET /me/shows` + `/shows/{id}/episodes` against Bryan's actual library in
   the Phase-0 spike before promising "all podcasts I follow".
4. **Token lifetime in long agents.** 1h access tokens + refresh covers it, but a
   multi-hour run must handle refresh races (single-flight) and revoked grants
   (clear error → `login` again, never a stack trace).
5. **"Beautiful" scope creep.** Tables + one curation skill = beautiful enough for
   v1. A TUI tab or rich cards come after real usage, informed by it.
6. **Secret handling.** PKCE public-client flow avoids storing a client secret at
   all (recommended); if a confidential client is chosen instead, the secret goes
   to the OS keychain/password-store, never a dotfile. (This machine already uses
   `password-store` for adjacent secrets — follow that neighborhood.)

## 9. Recommended solution (phased)

- **Phase 0 — spike (hours, before any repo):** personal Spotify app (Dev Mode,
  Premium owner), PKCE loopback login, probe the §3 endpoint table against Bryan's
  real library; confirm shows/episodes coverage and the owned-vs-followed `items`
  behavior. Go/no-go on Phase 1.
- **Phase 1 — `sase-spotify` read-only + auth:** repo + `sase_commands: spotify`,
  login/logout/status/whoami, playlists/items/shows/episodes/search, JSON + tables,
  README with quota-mode caveat. Usable value on day one.
- **Phase 2 — gated mutations:** create/add/remove/move/follow, all `--dry-run`
  capable, macro skill text mandating the §6 gate flow, never `--yes` from agents.
- **Phase 3 — polish (only after real use):** `@spotify` artifact-ref provider,
  curation macros (e.g. "rebuild running mix"), optional Admin Center/TUI surface.

Success looks like: `sase spotify playlists` answers goal 1 in seconds, `sase spotify
shows` answers the podcast half, and the first agent-made playlist edit lands through
a 🎵 gate with a readable diff — intuitive (one command tree), reliable (current
endpoints, refresh + backoff, graceful degradation), and beautiful (tables first,
richer surfaces later).
