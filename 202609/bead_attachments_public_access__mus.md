# Bead attachments: public-by-default access — critique and recommended design (__mus)

**Researcher:** mus · **Date:** 2026-09-29 · **Swarm:** independent report (did not consult `__cdx`/`__cld`/`__grk`/`__gem` peers)

**Question:** Should all users working on a SASE project get all (non-sensitive) bead
attachments by default, implemented by moving non-sensitive bytes from the planned
private `sase--attachments` sidecar into the public `sase--beads` repo? Large files may
be remote-machine-only. Agents would opt into private attachments (default public), but
it is unclear how they decide.

**Sources read (audited where required):**
`research:202609/bead_note_attachments/attachment_storage_and_access.md`,
`plan:202609/bead_note_attachments.md` (884 lines),
`research:202609/bead_note_attachments/bead_note_attachments.md` (consolidated report),
`sase-1ck` epic bead + `sase-1ck.5` phase bead, `sase/sase.yml` sidecar roles,
`docs/beads.md` (Bead Pages), `docs/agents_sidecar.md`, `docs/configuration.md`,
`src/sase/bead/` tree, `src/sase/attachments/` (unrelated markdown-PDF module),
`src/sase/_linked_repo_paths.py` (`hidden_sidecar_clone_dir`).

## TL;DR

The goal is right; the proposed mechanism is wrong in one specific way. **Do not put
bytes in the `sase--beads` repo.** Put public bytes in a **separate public byte repo**
(new `attachments-public` sidecar role, hidden bare partial clone, lazy fetch) and keep
`sase--beads` as events + descriptors only. Keep the rest of the `sase-1ck` topology
(local CAS → git tier → large/remote tier, location-free descriptors, tombstone purge).
Ship **explicit per-attachment visibility** (`--visibility public|private`, config
default, TTY confirm, non-TTY must be explicit), a **hard sensitive-path + content gate
that forces private**, and a **remote-machine tier for large files** (origin-online
fetch, honest badge, no durability promise). Do not ship agent default-public with only
a denylist; agents are the worst judges of sensitivity and the leak is irreversible in a
public git repo.

## 1. What sase-1ck actually builds (ground truth)

From the plan and the storage/access note:

- Note text stores `@attachment:<name>` tokens + a manifest of descriptors
  `{name, sha256, size_bytes, mime_type, image?, origin?}`. **Descriptors are as public
  as the bead itself; bytes are private.** No paths, store locations, or machine-local
  ids in the event.
- Bytes: local CAS first (`~/.sase/attachments/objects/sha256/<xx>/<sha>`, `views/`,
  `tmp/`, `locks/`, `tombstones/`), then a **new private sidecar
  `sase-org/sase--attachments`** (hidden bare `--filter=blob:none` clone, ≤ 50 MiB,
  validated ≤ 95 MiB), then an optional **rclone large store** (≤ 2 GiB). `-L` is an
  explicit badged local-only choice.
- Fetch is lazy, digest-verified, capped at 25 MiB auto-fetch; larger needs explicit
  `attachment path` / `-d`. Uploads are pre-publication with an outbox fallback
  (`⇡ pending upload`); `require_upload: true` is the fail-closed option.
- Nothing has landed: all ten phases `IN_PROGRESS`, `src/sase/bead/attachments/` does
  not exist, `sase--attachments` does not exist on GitHub. Until a shared store exists,
  everything is local-only.
- `sase--beads`, `--agents`, `--plans`, `--research` are all **public**; the beads
  sidecar is hot (consolidated report: cloned into 35 of 47 workspaces; storage note:
  "cloned into most workspaces"). The agents sidecar already publishes prompt-cited file
  bytes at `files/objects/sha256/<xx>/<sha256>` — the CAS precedent — and sidecar roles
  support `visibility: private` + hidden host-owned clones.

So the "private by default" shape is deliberate (consolidated report adjustment R6):
every sidecar is public, a leaked secret in public git cannot be taken back, hence a
private byte tier + sensitive-path refusal + purge-by-tombstone.

## 2. Is public-by-default a good idea? (critique)

**Yes to the goal, no to the location.** The friction being removed is real: today a
collaborator without `sase--attachments` access sees prose + filename + 🔒 chip but no
bytes, needs a repo grant plus per-machine rclone setup, and the writer gets an
outbox-forever `⇡ pending upload` with no distinct "no access" badge (a noted plan gap).
For the current single-member org (`sase-org`: one member) and small trusted teams,
private-by-default means every useful screenshot/log is one grant away from useful.
Zero-config sharing is the right target.

But "move non-sensitive attachments to the public `sase--beads` repo" conflates two
decisions: (a) *visibility* (public vs team-only) and (b) *colocation* (bytes inside the
event repo vs a dedicated byte repo). (a) is defensible; (b) is not. Five concrete
objections to (b):

1. **Hot-repo bloat.** The beads repo is cloned into workspaces and synced on the bead
   fast path. Every image/log/trace blob committed there inflates every clone, fetch,
   workspace init, and per-SHA fast-gate CI run. The plan deliberately uses a hidden
   bare partial clone for bytes so a read fetches exactly one blob. Putting bytes in
   `sase--beads` forfeits that: even with `blob:none`, the hot path now carries the
   object count, and any full clone (bootstrap, new machine, CI) pays for all of history.
   A separate public byte repo preserves lazy-fetch without taxing bead sync.
2. **Lifecycle mismatch.** Bead events are append-only forever; bytes need
   purge/prune/GC (tombstones at `files/tombstones/…`, `attachment purge`, cache
   pruning under `local_cache_max_bytes: 10 GiB`). Mixing them means a
   `git filter-repo` to truly erase a leaked secret rewrites event history too, while a
   tombstone-only "purge" leaves the blob in history — in a *public* repo that history
   is already forked/cached/scraped. Separation lets the byte repo GC aggressively
   without touching the event log.
3. **Pages and projections.** Bead pages (`pages/<root>/…` in `--beads`) are generated
   Markdown projections rebuilt from events + commit history. Blobs in the same repo
   pollute page diffs, roster churn, and hosted rendering for zero benefit.
4. **Limits don't disappear.** GitHub warns at 50 MiB and blocks at 100 MiB; the plan's
   50 MiB / ≤ 95 MiB git-tier cap applies equally to a public repo. "Move to beads"
   does not solve large files — the remote-machine/rclone tier is still needed.
5. **Blast-radius expansion for no access gain.** Filename, size, MIME, dimensions,
   SHA-256, and origin are *already* public in the descriptor. Adding bytes removes the
   last barrier while gaining nothing over a separate public byte repo with the same
   visibility: both are world-readable, but only the separate repo keeps bead sync fast
   and purge/GC independent.

There is one narrow exception worth preserving: prior research (`__grk` v2, cited in the
consolidation) proposed ≤ 2 MiB objects in the beads sidecar. A **small-object
exception** (e.g. ≤ 2–5 MiB) inside `sase--beads` would bound bloat while covering the
observed corpus (70 `.json`, 13 `.log`, 7 `.txt`, 7 `.png` cited paths — small). I still
recommend against it: the corpus will shift once attaching is easy, the cap becomes a
second policy to explain, and the separate public repo already serves small files with
identical UX. If the follow-up epic insists on beads-repo bytes, cap it hard and revisit
after measuring.

### World-readable vs project-scoped — name the threat model

"All users working on a sase project" sounds scoped, but `sase--beads` is **public to
the world**, not to project members. Public-by-default means scrapers, forks, future
employers, and GitHub search — not just collaborators. If the real requirement is
"every collaborator, but not the world," the correct tool is a **private repo + team
ACL** (grant read to collaborators, write to attachers), exactly what `sase--attachments`
already designs, plus auto-grant on `sase repo init`. Only choose world-public if that
is actually acceptable for screenshots, logs, traces, and dumps. Most teams should offer
*both*: a public tier and a team-private tier (see §5).

## 3. Sensitivity: how to decide public vs private

This is the hardest part, and the proposal ("agents opt into private, default public,
unsure how they decide") is under-specified in the dangerous direction.

### Why default-public + denylist fails for agents

- Agents attach precisely the files most likely to contain secrets: `.env`, shell
  history, `hosts.yml`, crash logs with tokens/cookies/auth headers, `credentials.json`,
  browser profiles, mobile captures, full chat transcripts, screenshots with visible
  tokens, core dumps with memory. A filename denylist (`~/.ssh/**`, `**/.env`,
  `*.pem`, `*.key`, `*id_rsa*`, `*.kdbx`, `**/credentials.json`, `**/.netrc`,
  `**/.aws/credentials`, `**/.git-credentials`, `**/.config/gh/hosts.yml` plus
  `sensitive_patterns`) catches *paths*, not *contents*. A renamed copy (`/tmp/debug.txt`
  containing `AWS_SECRET=…`), a log line (`Authorization: Bearer …`), or a screenshot
  of a token sails through.
- Public git is **append-only in practice**: tombstone purge removes the tip object but
  git history keeps the blob until manual `filter-repo`, and any fetcher keeps a CAS
  copy. Rotation, not purge, is the only remediation. Fail-open defaults maximize the
  rate at which that remediation is needed.
- A published SHA-256 lets anyone **confirm a guessed file** even without bytes; with
  bytes public, confirmation becomes possession.

### What works (layered, fail-closed core with configurable default)

1. **Explicit visibility per attachment, not a silent default.** Add
   `--visibility public|private` (and/or `--public` / `--private` shorthands; check
   short-letter collisions per parser — `-a` is `--author`, `-N` is taken — per plan
   §CLI). Config `bead.attachments.default_visibility` sets the TTY default. On a TTY
   with no flag, confirm (`Public? [y/N]` showing destination repo + size). In
   non-TTY/agent mode, **require the flag or fall back to private** — never silently
   publish. This gives the user their "default public" interactive UX without giving
   agents a fail-open default.
2. **Hard gate, not hint.** Sensitive-path match *forces* private or refuses: a public
   request for a denylisted path fails with the exact `--visibility private` retry
   (current plan's `-S/--allow-sensitive` becomes `--allow-sensitive` + private-only;
   never allow `--allow-sensitive` + public). Extend the gate with lightweight content
   signals: PEM headers, `BEGIN … PRIVATE KEY`, high-entropy token regexes (AWS, GitHub,
   Slack, generic bearer), `.env`-shaped `KEY=VALUE` runs, SQLite/kdbx magic, browser
   cookie stores. Content hit → same force-private/refuse. Document these as
   best-effort: a miss is still the author's fault, but the common cases are caught.
3. **Agent decision checklist (ship in help + docs + TUI hint).** Use private when ANY
   is true: credentials/tokens/keys/cookies/auth headers present or plausibly present;
   personal data, customer data, or internal-only URLs; full environment/dump files;
   screenshots/recordings showing any of the above; the file came from `$HOME`, browser
   profile, keychain, or cloud credential paths; unsure. Default worked example:
   `sase bead attach sase-ab ./shot.png --visibility public` vs
   `sase bead attach sase-ab /tmp/auth.log --visibility private`. Add a
   `sase doctor` finding for visibility misconfigurations and a pre-publication
   "publishing N bytes to public repo X — confirm" echo (the plan already echoes
   destination/visibility per file; keep it and make it prominent).
4. **Project-level default, not global.** Upstream default stays `private` (safe for new
   users); the user's org sets `default_visibility: public` in `sase/sase.yml` after
   accepting world-readable risk. Agents in that project still follow rule 1 (explicit
   flag or private fallback), so the org default affects humans, not headless leaks.

## 4. Large files via remote-machine support: fine, with caveats

"Large files only ever supported via remote machine" is acceptable and simplifies the
design — drop (or defer) the rclone large tier in favor of an **origin-online tier**:

- Descriptor already carries `origin` (hostname). Add availability state
  `remote-machine-only` (e.g. `⧉ on athena — fetch when online`) distinct from
  `local_only`, `pending_upload`, and `unavailable offline` (filling the plan's "no
  access" gap).
- `sase bead attachment path <id> <name>` / `-d` attempts: local CAS → public/private
  git tiers → **machine fetch from origin** (tailnet SSH / enrolled remote machine;
  `sase machine` enrollment is the existing primitive) → error with exact retry. Fetch
  is digest-verified into the CAS like any other tier.
- Caveats to document loudly: **no durability** (origin disk loss = data loss; outbox
  does not replicate); **availability = origin online** (laptop closed = unavailable);
  **ACL = machine access** (tailnet invite + SSH account per consumer — heavier than a
  GitHub repo grant; R2 with scoped keys is more shareable, per the storage note).
  Recommend best-effort background replication for origins that are servers (athena),
  and treat laptop-origin large files as ephemeral-by-design. The 25 MiB auto-fetch cap
  and 2 GiB large max remain sensible bounds.

## 5. Alternatives considered

| Option | Verdict |
| ------ | ------- |
| **A. Bytes into `sase--beads` (proposed)** | Reject (§2). Same world-visibility as B with worse sync, lifecycle, and pages costs. |
| **B. Separate public byte repo (recommended).** New `attachments-public` sidecar role, public, hidden bare partial clone, same `files/objects/…` layout + tombstones. Placement routes by visibility. | **Adopt.** Identical sharing UX to A, none of the hot-repo costs, independent GC, same lazy-fetch/auth story as the private tier. |
| **C. Private repo + team ACL only (no world-public).** Grant collaborators read/write on `sase--attachments`. | Best when "project users" ≠ "world." Offer alongside B (two git tiers: team-private + world-public). If only one tier is funded, prefer C over A for least privilege; the user's request explicitly wants world-default, so B is the literal answer. |
| **D. Encrypted bytes in public repo.** Publish ciphertext + per-team keys. | Reject for now. Key distribution/rotation/revocation is a second system; capability URLs or age-box per-file keys add real complexity for little over B+C. Revisit only for regulated data. |
| **E. Git LFS / external blob store for beads repo.** | Reject. LFS still bloats pointer churn, needs LFS auth everywhere, breaks bare-partial assumptions, and doesn't fix purge/history. |

## 6. Requirement adjustments (explicit)

| # | As requested | Adjusted to | Why |
|---|--------------|-------------|-----|
| R1 | Non-sensitive bytes → public `sase--beads` repo | Non-sensitive bytes → **new public byte sidecar** (partial clone, lazy fetch); `sase--beads` stays events + descriptors | §2: sync cost, lifecycle, pages, GC independence; same sharing UX |
| R2 | All project users get all non-sensitive attachments by default | Yes for the public tier (world-readable = project users included); add a **team-private tier** for project-but-not-world files | Names the threat model; least privilege for the middle class of files |
| R3 | Large files remote-machine-only | Accept, as an **origin-online tier** with its own badge, fetch path, and no-durability disclaimer; defer/replace rclone large tier | Simpler; honest about offline/loss windows; reuses `sase machine` enrollment |
| R4 | Agents opt into private, default public; unsure how they decide | **Explicit `--visibility` + config default (humans) / private fallback (agents) + hard sensitive gate + checklist + doctor**; upstream default `private`, org may set `public` | Fail-open agent default leaks irreversibly to public git; path denylist alone is insufficient |
| R5 | (new) | Descriptors gain a `visibility` label (public/private/remote) but stay in the public event log; **stores stay config-ordered and digest-keyed**, never recorded per-event | Preserves location-free promotion (local-only → shared without editing notes) while making UX/badge/doctor decisions deterministic |
| R6 | (new) | Promotion/migration is explicit (`attachment push` / republish); existing private objects never auto-flip to public | Immutability + audit: flipping visibility rewrites sharing, so it must be an action, not a default |

## 7. Recommended solution (follow-up epic after sase-1ck closes)

Scope: **do not start until `sase-1ck` (all 10 phases incl. `ga`) lands.** This is a
sharing-policy epic on top of a working attachment pipeline, not a parallel
implementation.

1. **Public byte tier.** Add reserved sidecar role `attachments-public` (public
   visibility, `files/objects/sha256/<xx>/<sha>` + `files/tombstones/…`, bare partial
   clone at `~/.sase/projects/<key>/repos/attachments-public`, plumbing BlobStore,
   placement routing by `visibility`, capped lazy fetch, `⇣`/`⧉`/`🔒` badges, doctor
   reachability + outbox backlog). Keep `sase--beads` byte-free. Optionally add a
   team-private tier as a second git entry (same code path, different remote/ACL).
2. **Visibility UX + policy.** `--visibility public|private` on `attach`/`note`/`close`/
   `update`/`+1`; `bead.attachments.default_visibility` config; TTY confirm; non-TTY
   explicit-or-private; sensitive-path + content gate forces private; write echo shows
   `⇡ <org>/<repo> (public|private)` per file; JSON carries `visibility` +
   `availability` + `local_path`-when-cached (never bytes).
3. **Remote-machine large tier.** Origin-online fetch via enrolled machines; `⧉ on
   <origin>` badge; `attachment path`/`-d` fetch path; doctor reports origin
   reachability; docs state no-durability + online requirements + tailnet/SSH setup.
4. **No-access states + doctor.** Distinct `🔒 no access (<repo>)` badge and
   outbox-forever diagnosis (the storage note's gap), for both public and private tiers.
5. **Migration + docs.** Existing private/outbox/local-only objects never auto-publish;
   `attachment push [--visibility …]` promotes explicitly (new upload + manifest update
   via `NoteEdited.attachments: Some`, never history rewrite). Update
   `docs/beads.md`, `docs/configuration.md`, help texts ("`@` attaches a snapshot…"
   plus visibility paragraph), and the agent checklist. Seed `sensitive_patterns` with
   the plan's list and document the org's `default_visibility: public` opt-in with its
   world-readable warning.
6. **Verification.** Small boolean matrix: public/private × small/large ×
   online/offline-origin; cross-machine fetch on athena→apollo/mac; corpus re-run
   (≈0.3% path-shaped notes); mixed-fleet old-reader ignore test (optional wire field);
   purge-tombstone + `filter-repo` procedure drill; secret-fixture gate tests
   (denylist + content scanners force private).

**Bottom line:** grant the user's goal — zero-grant public sharing by default — but
implement it as a **separate public byte tier with explicit visibility and a hard
sensitivity gate**, not bytes in the beads repo. Pair it with a team-private tier for
project-not-world files and a remote-machine tier for large files. That keeps bead sync
fast, purge/GC independent, and leaks fail-closed while making the common case
(screenshot/log/trace to a collaborator) just work.
