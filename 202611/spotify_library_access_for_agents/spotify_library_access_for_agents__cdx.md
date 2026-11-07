# Spotify access for SASE agents: capabilities, constraints, and a reviewable design

Independent research by **cdx** · **2026-11-07**

## Decision

The goal is worthwhile: a personal library assistant could make playlists easier to inspect and maintain, and SASE already has suitable command-plugin and human-review infrastructure. The technical work is manageable. The larger uncertainties are Spotify's authorization for AI use, access to followed playlists, and whether its official agent connector can satisfy the request without a custom integration.

**I recommend a short official-connector feasibility check, followed—only if needed and permitted—by a small, read-first SASE plugin with deterministic, gated playlist changes. I do not recommend shipping an unrestricted Spotify Web API → LLM bridge under the assumption that metadata or inference is exempt from Spotify's terms.**

This is research and a proposed design, not an implementation or a claim of account access. I consulted official documentation, inspected SASE's current contracts, inspected one independent MCP implementation, and made an unauthenticated protocol probe. I did not authenticate to Bryan's account, inspect personal listening data, modify playlists, create a repository, or consult other swarm reports.

## 1. What Spotify actually supports today

### Account and platform prerequisites

Development mode explicitly supports personal, single-account tools. The application owner must have Premium; an application supports up to five allowlisted Spotify users. Successful OAuth login alone does not prove allowlist access: API calls can subsequently return 403. Extended quota is not a sensible dependency for this project; its published eligibility includes an organization and at least 250,000 monthly active users. [Spotify quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes)

Do not copy February's app-count restriction into a November implementation. **July 2026 raised the limit from one to 25 client IDs per developer and made development quotas shared across that developer's apps.** A new client ID does not provide an independent quota budget. Quota exhaustion has a documented `QUOTA_EXCEEDED` reason. [July changelog](https://developer.spotify.com/documentation/web-api/references/changes/july-2026)

The February announcement was subsequently amended: endpoint restrictions for existing integrations were postponed on March 9, while other restrictions proceeded. That historical exception is not a reason to build a new plugin against old endpoints. Probe the actual application, and target the current API. [Announcement and amendment](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security)

### Capability map

| Requested behavior | Current interface | Necessary qualification |
| --- | --- | --- |
| List my playlists | `GET /v1/me/playlists` | Lists owned or followed playlists; paginate the entire collection. |
| Read songs in a playlist | `GET /v1/playlists/{id}/items` | Current reference limits access to owner/collaborator; another owner's followed playlist can appear in the inventory but its contents can return 403. |
| List followed podcasts | `GET /v1/me/shows` | Returns saved shows, which correspond to following a podcast in Spotify. |
| Create a playlist | `POST /v1/me/playlists` | Explicitly set `public: false`; the API default is public. |
| Rename or describe a playlist | `PUT /v1/playlists/{id}` | Must have applicable access and write scopes. |
| Add songs or episodes | `POST /v1/playlists/{id}/items` | At most 100 items per request; preserve order. |
| Remove or reorder items | `DELETE` or `PUT /v1/playlists/{id}/items` | Requires careful occurrence, position, and concurrency handling. |

Sources: [playlist inventory](https://developer.spotify.com/documentation/web-api/reference/get-a-list-of-current-users-playlists), [playlist items and owner/collaborator restriction](https://developer.spotify.com/documentation/web-api/reference/get-playlists-items), [saved shows](https://developer.spotify.com/documentation/web-api/reference/get-users-saved-shows), [Spotify's explanation of following shows](https://support.spotify.com/us/article/podcasts-and-shows/), [create](https://developer.spotify.com/documentation/web-api/reference/create-playlist), [add](https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist), [remove](https://developer.spotify.com/documentation/web-api/reference/remove-items-playlist), [update](https://developer.spotify.com/documentation/web-api/reference/reorder-or-replace-playlists-items).

Use the current `/items` paths and response models. February replaced `/tracks` paths, renamed playlist fields, and reduced search's maximum page size to ten. Some narrative examples still use older field names; pin and test against the current schema rather than relying on examples alone. March restored track and album `external_ids`. [February changes](https://developer.spotify.com/documentation/web-api/references/changes/february-2026), [March correction](https://developer.spotify.com/documentation/web-api/references/changes/march-2026)

Important semantic limits:

- “My playlists” includes **owned, collaborative, and followed** collections. These are different capabilities, not interchangeable ownership labels.
- “Followed podcasts” means saved **shows**, not saved episodes, listening history, episode downloads, or paid podcast subscriptions. The UI should say “Followed podcasts”; the adapter can use Spotify's “saved shows” terminology internally.
- Folders are not exposed or creatable through the Web API. Local tracks may appear but cannot be added through it. There is no playlist-delete endpoint; removing a playlist from the library is an unfollow operation. [Playlist concepts](https://developer.spotify.com/documentation/web-api/concepts/playlists)
- Liked Songs should be a separately named optional library view using saved tracks, not a fabricated ordinary playlist. It is outside the minimum requested scope.

**Requirement adjustment:** promise a complete playlist inventory and complete contents for accessible playlists, with explicit unavailable states for the rest. Do not promise every song in every followed or Spotify-owned playlist.

## 2. The decisive issue: permission to expose data to an AI model

Spotify's policy prohibits using Spotify content to train a model **“or otherwise ingest Spotify Content into a machine learning or AI model.”** That is broader than a training-only prohibition. The same policy also restricts content analysis and requires user control and deletion on disconnect. [Developer Policy, III.13–14 and I](https://developer.spotify.com/policy)

Spotify's terms define content to include metadata, playlists, and user data, and repeat the AI restriction. They also limit indefinite storage and caching. Consequently, “only titles,” “local inference,” and “our provider does not train on prompts” do not establish an exemption. This is my conservative implementation reading of the published language, not evidence of a Spotify enforcement decision about this exact application. [Developer Terms, II.8, IV.2.1.1, IV.3](https://developer.spotify.com/terms)

There is real nuance. Spotify publishes a **Building with AI** guide that encourages coding assistants to use its documentation and generate integration code. That supports having a SASE agent build the integration; it does not clearly grant permission to feed a user's API responses into that agent at runtime. [Building with AI](https://developer.spotify.com/documentation/web-api/tutorials/building-with-ai)

Spotify also operates approved integrations with ChatGPT and Claude, and has announced a Meta Muse integration. Their existence shows that authorized agent access is possible. It does not establish that every independent developer has equivalent rights or endpoints. [Spotify in ChatGPT](https://newsroom.spotify.com/2025-10-06/spotify-personalized-prompts-chatgpt/), [Spotify in Claude](https://newsroom.spotify.com/2026-04-23/claude-integration/), [Spotify and Muse](https://newsroom.spotify.com/2026-09-23/spotify-meta-muse-agent/)

**Requirement adjustment:** separate three permissions: Spotify account consent, Spotify's permission for the integration's AI use, and Bryan's approval of a particular mutation. An OAuth grant or `/sase_gate` approval addresses only part of that chain.

Before enabling model-visible library reads, establish an authorized official integration route or obtain clarification/permission covering private playlist metadata, saved shows, runtime inference, provider processing, and transcript retention. Do not present an export, browser scraper, or local model as an automatic policy workaround. A conventional deterministic library viewer remains technically useful, but it does not satisfy the original request for agents to see the library.

## 3. Build versus reuse

| Approach | Assessment |
| --- | --- |
| Spotify's official agent connector | First candidate to test: vendor-operated, designed for AI use. Actual inventory coverage and eligibility for SASE's clients remain unproven. |
| Small SASE command plugin over Web API | Best control of output, correctness, scopes, and approvals. Conditional on resolving AI use; maintains an upstream API dependency. |
| Existing community Spotify MCP server | Useful reference and quick prototype. Does not itself settle platform permission or enforce SASE review semantics. |
| Spotify account export | Useful occasional, dated inventory fallback. No live writes; export completeness and downstream processing permissions still need checking. |
| Browser/session automation | Poor default: fragile UI, session credentials, incomplete scrolling, uncertain API/policy guarantees. |
| Large hosted automation platform | Adds another credential holder and execution layer; little justification for one personal account unless already deployed. |

### Official connector: discovered, but not proven sufficient

Anthropic's official directory lists a connector made by Spotify at:

`https://mcp-gateway-external-pilot.spotify.net/mcp`

Its published tools include `search`, `fetch_tracks`, `create_playlist`, library mutations, and currently playing. The directory does not establish complete enumeration of private playlists, their contents, or followed shows. Its “sign-in not required” label should not be interpreted as anonymous access to private account data. [Official connector listing](https://claude.com/connectors/spotify)

**Direct observation, 2026-11-07:** an unauthenticated MCP `initialize` request with a plainly identified `sase-research` client returned HTTP 401 and an OAuth protected-resource discovery URL. The public resource metadata identified `accounts.spotify.com` as authorization server and advertised library/playback/write scopes, but not playlist-read scopes. Authorization-server metadata advertised PKCE S256 and did not advertise a dynamic registration endpoint. These observations prove discoverable OAuth infrastructure, not rejection of SASE, successful authentication, or absence of a library tool. I did not register a client, reuse another application's identity, or call account tools. [Protected-resource metadata](https://mcp-gateway-external-pilot.spotify.net/.well-known/oauth-protected-resource), [authorization metadata](https://accounts.spotify.com/.well-known/oauth-authorization-server)

A bounded follow-up should check supported client registration, authenticate through the intended flow, inspect `tools/list`, and test all three read requirements. If the official service meets them and permits the intended clients, wrap it. If it provides recommendations only, it is an alternative listening assistant, not a substitute for the requested library integration. Do not spend days reverse-engineering a partner-only gateway.

### Community implementation examined

I opened `llyfn/spotify-mcp` through `sase repo open` and inspected commit `c4af01336d4d52426e6ad35dd63ebe033e56e677` locally. It uses current `/items` endpoints, handles the July quota reason, and supports shows and playlist mutations. Those are useful signs of API currency.

However, its inspected configuration requests a broad scope set, including playback and library writes. Playlist tools execute writes directly; remove/reorder methods do not carry a reviewed base snapshot, and chunked additions have no durable per-operation recovery ledger. These are concrete gaps against this task, not a claim that the project is generally unsafe. Adopting it unchanged would leave the hardest SASE-specific work undone. [Inspected source: playlists](https://github.com/llyfn/spotify-mcp/blob/c4af01336d4d52426e6ad35dd63ebe033e56e677/src/spotify_mcp/tools/playlists.py), [configuration](https://github.com/llyfn/spotify-mcp/blob/c4af01336d4d52426e6ad35dd63ebe033e56e677/src/spotify_mcp/config.py), [HTTP client](https://github.com/llyfn/spotify-mcp/blob/c4af01336d4d52426e6ad35dd63ebe033e56e677/src/spotify_mcp/client.py)

An account export includes playlist contents and saved library entities, including shows. It can support a dated human inspection workflow when live API access is unavailable. Avoid importing unrelated history, location, and other sensitive categories from the same archive. [Spotify export contents](https://support.spotify.com/us/article/understanding-your-data/)

## 4. Proposed SASE design

The remainder is a proposed design for a permitted integration; it is not a claim that all pieces exist today.

### Package and ownership

A separate installable repository is appropriate. `sase-org/sase--spotify` can be the repository name the user proposed; use a normal distribution/import pair such as `sase-spotify` / `sase_spotify`. The double hyphen does not make it an artifact sidecar. Store code, documentation, synthetic fixtures, and a narrow agent skill there—not tokens or Bryan's library.

Expose a standalone binary and the same command under `sase spotify`. SASE already supports the `sase_commands` entry point with `main(argv, prog)`, side-effect-free `build_parser(prog)`, and optional `SASE_COMMAND_API`/`SUMMARY`. Help, completion, discovery, and diagnostics are provided by the host. No special Spotify branch should be added to the main parser. [Inspected SASE command contract](https://github.com/sase-org/sase/blob/0ba9cfc9f1ac2696cb6faeed515cd98483bcac3b/docs/reference/integrations/plugins-commands.md)

Keep OAuth/HTTP side effects, packaging, and presentation in the plugin. Follow this project's Rust boundary: new shared deterministic proposal validation, diff semantics, and operation-state transitions belong in `sase_core`, exposed through bindings. Reuse existing gate primitives. A TUI or MCP adapter must not develop a second mutation engine. Any new binding also requires the main repository's core revision pin update. This follows the audited `decisions:plugin-commands` and `decisions:rust-core-required` memory read during this research.

Start with CLI plus a skill. Add a thin MCP adapter only if an actual consumer needs it; it should delegate to the same operations and expose proposals rather than unrestricted mutations.

### Small, understandable command surface

Proposed commands, not currently installed:

```text
sase spotify connect
sase spotify status
sase spotify doctor
sase spotify playlists list --json
sase spotify playlists show <id-or-url> --json
sase spotify podcasts list --json
sase spotify changes propose <intent-file>
sase spotify changes show <change-id>
sase spotify changes review <change-id>
sase spotify changes status <change-id>
sase spotify disconnect
```

`connect` starts with read scopes. Enabling writes is a distinct reauthorization action. A name search can help identify a playlist, but ambiguous names never silently select a target. Writes bind Spotify IDs and an account identity, not display names. Use the stable `account_id` added in May for local account binding, while retaining the returned Spotify user ID for ownership comparisons. [May changelog](https://developer.spotify.com/documentation/web-api/references/changes/may-2026)

Machine output should include a schema version, account identity, retrieval time, pagination/completeness, source URLs, and typed errors. Preserve item order and duplicate occurrences. Represent tracks, episodes, local files, null/unavailable entries, and unknown future types explicitly. Never turn `403`, incomplete pagination, or a null item into an empty collection or successful complete result.

Human output should answer the question first: playlist name and owner, readable/editable status, item count if known, freshness, then contents. Keep full diagnostics behind `doctor`. A small output contract is easier for every agent provider than a dump of Spotify's entire response schema.

### Authentication for a headless SASE host

Use Authorization Code with PKCE. Client Credentials cannot authorize access to a personal library. Use a random state value and short-lived verifier, validate the callback, and handle refusal explicitly. [PKCE tutorial](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow)

Start with `playlist-read-private`, `playlist-read-collaborative`, and `user-library-read`. Add `playlist-modify-private` only for private writes, and public-write scope only when that behavior is enabled. Following podcasts does not require the followed-artists scope. [Scope definitions](https://developer.spotify.com/documentation/web-api/concepts/scopes)

A browser on Bryan's laptop cannot reach Apollo's loopback listener automatically. Provide an explicit loopback port-forward flow: the local browser returns to `http://127.0.0.1:<port>/callback`, forwarded to the host listener. Spotify permits HTTP loopback IP literals but rejects `localhost`; other redirects require HTTPS. Do not invent a device-code flow for ordinary Web API apps merely because an identity-discovery document mentions a device endpoint. [Redirect requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)

Keep credentials outside workspaces, git, artifacts, shell arguments, and agent transcripts. Use the host secret store where available, otherwise a documented restricted local store; serialize refreshes across processes and replace token files atomically. Reauthorize on invalid refresh credentials. `disconnect` clears credentials and temporary cached content and explains account-side revocation. A real account consent step remains human work even if an agent creates all repository scaffolding.

### Read reliability and data lifetime

Fetch inventory first; fetch playlist contents on demand. Share short-lived cache and request coordination across agents so a swarm does not independently crawl the same account. Display freshness and allow a deliberate refresh. Check a playlist's snapshot before/after paginated content reads; restart a bounded number of times or return `changed_during_read` instead of mixing versions. Playlist/show inventories have weaker consistency: expose retrieval boundaries and do not claim a transactional global snapshot.

Handle ordinary 429 responses with `Retry-After`, bounded backoff, and a clear retryable result. Treat `QUOTA_EXCEEDED` separately; do not create more apps or spin in retries. Spotify documents a rolling 30-second rate window separately from development quota buckets, with no fixed universal request budget to hard-code. [Rate-limit guidance](https://developer.spotify.com/documentation/web-api/concepts/rate-limits)

Suggested initial cache lifetimes—product choices, not claimed Spotify limits—are a few minutes for inventory and a shorter bounded lifetime for content used in a pending change. Retain only what the operation needs. A disconnect and retention policy must cover pending previews, recovery data, logs, and transcripts, not just the cache database. **Do not automatically register private library dumps as permanent SASE artifacts.** The research report itself contains no personal library data.

## 5. Gated playlist management that survives real failures

### Approve a frozen change

An agent proposes intent. Deterministic code resolves it into a versioned change document containing:

- Unique operation ID and account binding.
- Playlist ID, base snapshot, and a fingerprint of relevant metadata.
- Exact ordered operations and resolved track/episode URIs.
- Before/after counts, duplicate policy, scope and ownership requirements.
- Expiry, executor version, and canonical content hash.

The review UI and executor must consume that same document. “Approve cleanup” must not mean “let an agent decide what cleanup means later.” Search results must be resolved before review; execution must not rerun a fuzzy search and select a different recording.

Create a custom SASE gate with `auto: false`, a finite timeout, and `apply OR reject`. Use one apply command for the whole dependent change, not independently selectable AND options for steps that depend on one another. Offer read-only “Show full diff” and “Open playlist” actions. A reject command records a no-change result.

SASE's existing bundles hash reviewed resources, execute owned argv commands without a shell, and record durable decision acceptance separately from execution completion. Commands run in the answerer's environment, so pin an installed executor and package the manifest into the bundle; do not reference an ephemeral workspace script. A creator stages the gate, completes through `/sase_final`, and lets the host adopt the handoff. [Gate contract and recovery](https://github.com/sase-org/sase/blob/0ba9cfc9f1ac2696cb6faeed515cd98483bcac3b/docs/reference/automation/notification-gates.md), [gate skill source](https://github.com/sase-org/sase/blob/0ba9cfc9f1ac2696cb6faeed515cd98483bcac3b/src/sase/macros/skills/sase_gate.md)

### Approval is not an API transaction

Immediately before mutation, recheck identity, access, expiry, metadata, and snapshot. If the playlist changed since review, mark the proposal stale and generate a new review. Do not silently rebase an approved reorder or deletion onto new content.

Where Spotify supports `snapshot_id`, send it. But **a snapshot is not a universal compare-and-swap lock**: removal documentation explicitly permits applying a change despite intervening edits. Appends and metadata edits do not offer the same snapshot precondition. A local lock serializes this plugin's writers, not Spotify's own clients or collaborators. [Removal semantics](https://developer.spotify.com/documentation/web-api/reference/remove-items-playlist), [reorder parameters](https://developer.spotify.com/documentation/web-api/reference/reorder-or-replace-playlists-items)

This residual race argues for a limited first write release: owned private playlists, creating new private lists, and reviewed additions. Delay replace-all, arbitrary reorders, collaborative writes, public publication, and deduplication until their semantics have been proven. In particular, the current removal reference lists URI objects without a documented per-occurrence selector; do not assume an old positions-based recipe still implements “remove only the second copy.”

### Durable recovery, not blind retries

Use an operation journal with states such as `proposed → approved → applying → verified`, plus `rejected`, `expired`, `stale`, `partial`, and `outcome_unknown`. Store each batch's request identity and returned snapshot before proceeding. An execution restart first loads this journal.

A timeout can occur after Spotify accepted a non-idempotent write. Retrying an append can duplicate songs; retrying creation can create a second playlist with the same name. After an ambiguous result, re-read and reconcile against the expected ordered change. If external edits make that inconclusive, stop with `outcome_unknown` and request a new decision. Do not advertise exactly-once effects: Spotify's documented create/add interfaces provide no general idempotency key. [Create contract](https://developer.spotify.com/documentation/web-api/reference/create-playlist), [add contract](https://developer.spotify.com/documentation/web-api/reference/add-items-to-playlist)

A multi-batch operation is not atomic. Record verified progress, stop on unexpected failure, and show precisely what changed. Compensation is a new reviewed action; restoring a stale before-image could erase a user's intervening edits. A snapshot ID is not a general rollback endpoint.

SASE can restart failed gate commands, so this recovery requirement is mandatory even if a user normally presses Apply only once. Gate acceptance deduplication alone cannot prove whether a remote HTTP side effect happened.

### Be honest about the trust boundary

A local gate is excellent protection against accidental, unreviewed actions by cooperative agents. It is **not** isolation from an agent that can read the same user's write token, replace the executable, or invoke the API itself. File mode 0600 and a “use the gate” skill do not change that.

For the personal MVP, make that cooperative trust assumption explicit and keep raw write commands out of the agent surface. If “cannot write without my approval” is a hard security requirement, keep writes disabled until a separate token holder and authenticated host approval channel enforce it outside the agent's OS identity. That is additional engineering, not a property already supplied by a custom gate. Avoid building a generic credential platform prematurely; decide this boundary before the write phase.

## 6. What “beautiful” should mean here

The best interface is quiet, legible, and honest about state. Use SASE's existing gate preview rather than inventing a second approval dashboard.

An illustrative review, using invented content:

```text
♫ Add 3 songs to Evening Walk
Your playlist · Private · Checked just now

42 → 45 items       +3 additions       0 removals

+ Track A — Artist One
+ Track B — Artist Two
+ Track C — Artist Three

[Show full changes]  [Open in Spotify]

[Apply 3 additions]  [Keep playlist unchanged]
```

Show new visibility and removals prominently when later supported. Separate “Approved,” “Applying,” “Applied and verified,” and “Partially applied.” Never display success because the human approved or because an HTTP request was sent. Give stale proposals an actionable message: “This playlist changed after review. Review an updated proposal.”

Use text and icons as well as color; make long names expandable and large diffs scrollable. Retain item order. Escape control sequences and markup in Spotify metadata; descriptions are untrusted content, not instructions. Rejection should be one click and should not demand an explanation.

For a richer human preview, use legitimate Spotify attribution and original, unaltered artwork with links back. Do not assume green accents or a music-note glyph substitute for the required brand attribution; resolve terminal-only attribution before release. A small local HTML preview can supply official branding while SASE retains the decision controls. Avoid adding a persistent website solely for decoration. [Spotify design and branding](https://developer.spotify.com/documentation/design)

## 7. Delivery sequence and proof of readiness

| Stage | Deliverable | Exit condition |
| --- | --- | --- |
| Feasibility | Official connector capability/eligibility check; documented AI-use position; confirm Premium and allowlist | No unsupported promise about account access or model ingestion. |
| Read release | Plugin packaging, connect/status/doctor, playlists and podcasts, complete pagination, clear limits | Account-level human comparison succeeds for private, collaborative, followed, and large collections. |
| Write prototype | Synthetic fixtures, frozen change document, deterministic diff, custom gate, journal | Rejection/expiry/stale data produce no remote writes; restart cannot blindly replay completed changes. |
| Limited write release | Owned private creation/additions with live disposable-playlist acceptance check | Timeout recovery, partial progress, token failures, and verification behave as specified. |
| Expansion | More mutations or MCP only when justified | Each new operation has defined concurrency, duplicate, recovery, and approval semantics. |

Tests should cover behavior, not mirror implementation: a library with more than one page; an owner-inaccessible followed playlist; a saved-show versus episode distinction; duplicates and unavailable/local items; quota exhaustion; refresh contention; wrong-account tokens; malicious descriptions; edits between review and execution; and a connection failure after a write was accepted. Use synthetic fixtures in source control. Run real writes only on an explicitly approved disposable private playlist.

Open questions for the implementation kickoff—not prerequisites for completing this research—are Bryan's Premium/app status, the importance of contents of followed playlists, approved model-provider data flows, and whether the gate must resist hostile code or only prevent ordinary mistakes. No personal account assumption was made here.

The research inspected SASE checkout `0ba9cfc9f1ac2696cb6faeed515cd98483bcac3b` and the independently opened MCP commit cited above. Reference memory was read through the audited memory command. No software tests were run because this turn changes only this research report; account behavior remains to be validated after authentication.

## Recommended solution

**Proceed with the idea, but narrow and sequence it.** First test Spotify's official connector against the three concrete read requirements and its supported client/authorization model. Prefer that route if it actually meets them. Otherwise, resolve the published AI-ingestion restriction before giving SASE agents Spotify API responses.

For a permitted custom implementation, use an opt-in `sase-org/sase--spotify` command plugin exposing `sase spotify`, backed by the current Web API, minimal PKCE scopes, explicit freshness/completeness, and shared deterministic core logic. Ship reads first. Add a deliberately small set of playlist mutations through immutable custom gates and a durable recovery journal; make private creation explicit and stale review a normal, well-designed state.

If the permission or official-client route cannot be established, retain a human-facing deterministic library tool or dated export workflow and use Spotify's approved assistant integrations for conversational discovery. Do not describe that fallback as fulfilling direct SASE library access. The feature is a good personal tool when those limits are accepted; a broad autonomous music agent, unrestricted metadata bridge, or general Spotify replacement is the wrong starting point.
