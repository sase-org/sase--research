# Bead Attachment Audience: Public-by-Default Attachments After `sase-1ck`

_Lead researcher: cld (merges cdx, cld, grk, mus, and gem, plus independent
verification) · 2026-09-29_

Sibling reports in this directory: `bead_attachment_audience__{cdx,cld,grk,mus,gem}.md`.
This report merges them, settles their disagreements, and adds facts none of them
checked. Claims marked **(verified)** were re-checked while this report was written,
against the sase tree, sase-core, sase-github, the agents sidecar, or GitHub.

**Question.** After epic `sase-1ck` (bead note attachments) closes, a follow-up epic
should give everyone working on a SASE project access to all non-sensitive bead
attachments by default. The proposal:

- Move non-sensitive bytes from the planned private `sase--attachments` sidecar into the
  public `sase--beads` repo.
- Support large files only through SASE's remote-machine support.
- Default agents to public attachments, with a way to mark one private.

The user doesn't yet know how agents should decide when to use private.

**Context read:** `research:202609/bead_note_attachments/attachment_storage_and_access.md`,
bead `sase-1ck` and phase `sase-1ck.5`, `plan:202609/bead_note_attachments.md`, and the
earlier consolidated report `research:202609/bead_note_attachments/bead_note_attachments.md`.

---

## TL;DR

1. **The goal is right. The destination is wrong. All five researchers agree, and so do
   I.** An attachment should be as readable as the bead that carries it, which for
   `sase` means public. The bytes belong in a **dedicated public attachments sidecar**,
   not in `sase--beads`. The beads repo is SASE's hot, fully cloned event log. Blobs
   there would slow every bead sync. Purging one of them would mean rewriting the event
   history. And a secret-scanning rejection would block bead publication.
2. **Check the premise.** `sase-org` is on GitHub Free, has one member, and its base
   permission is `read` **(verified)**. So every org member can already read a private
   attachments repo. Going public adds nothing for org members. It helps people outside
   the org: readers of public bead pages, zero-credential frontends (Telegram, mobile,
   CI, a fresh machine), and future contributors who aren't members. That is worth
   having, but it is the actual benefit, and the design should aim at it.
3. **SASE should decide what's sensitive, not the agent.** A core `auto` policy combines
   provenance, a content scan, and file type, and **uncertainty resolves to private**.
   Agents can always narrow an attachment to private. They can never widen a result the
   policy made private; only a human can publish it, directly or by approving a gate. A
   wrong private costs one click. A wrong public can't be undone.
4. **The risk is already real.** The public `sase--agents` repo contains one distinct
   LLM-provider API key in **12** transcripts and one chat-bot token in **1**
   **(verified by counting only; no values printed)**. Neither is a test fixture: no
   such string exists in the sase tree. Secret scanning and push protection are
   **disabled** on every public `sase--*` repo **(verified)**. **Rotate both
   credentials now**, whatever you decide about attachments.
5. **Large files never go public.** They stay on enrolled machines: in the origin's
   CAS, optionally replicated to athena by the `sase-1ck.6` rclone tier, and used by
   dispatching work to that machine. Remote-machine support is not a blob transport
   today **(verified)**, so this needs little new code only if "use" means dispatch.
6. **`sase-1ck` needs one small change now.** sase-github can only create **public**
   repos, and sase's sidecar init refuses to create a repo whose visibility doesn't
   match the config **(both verified)**. So `sase-1ck.5`'s private `attachments` sidecar
   can't be created through `sase repo init` as currently scoped. Fix that in
   `sase-1ck`, and use the fix to free the plain `attachments` name for the public
   default (§8).

---

## 1. Verified ground truth

| Fact | Evidence | Why it matters |
| --- | --- | --- |
| Of `sase-1ck`'s phases, only **`.2` (local CAS)** has landed (`a3b1088d5e`, `src/sase/bead/attachments/{blob_store,ingest,store,images}.py`). sase-core has no bead attachment wire yet. `sase-org/sase--attachments` does not exist. | `git log`, sase-core grep, `gh repo view` | The wire and store roles can still be shaped cheaply. No private objects exist that would need migrating. |
| `sase-org`: **Free** plan, `default_repository_permission: read`, one member (`bbugyi200`). The org has three private repos. | `gh api orgs/sase-org` | A private repo is already "shared by default" with org members. "Internal" visibility (Enterprise only) is unavailable. |
| The primary and all four `sase--*` sidecars (`beads`, `agents`, `plans`, `research`) are **public**. **Secret scanning and push protection are disabled on all five.** | `gh api repos/sase-org/<r>` `security_and_analysis` | There is no GitHub backstop today. Both features are free for public repos. |
| `sase--beads`: 18,292 commits, 128,287 objects, ~106 MiB packed, `issues.jsonl` ~19 MiB, full clone, `auto_sync: true`, materialized on demand (12 of 20 workspaces on this host). | cdx, grk, and cld measured the same numbers independently; `sase repo list` | Every blob committed there reaches every machine that touches beads. |
| **sase-github hardcodes `gh repo create … --public`.** Preflight always reports `visibility="public"`, and a test asserts `--private` is never passed. | `sase_github/workspace/sdd_repo.py:165`, `sdd_sidecar.py:55,67`, `tests/test_workspace_plugin.py:1211` | See the next row. |
| sase's sidecar init **fails closed** when the provider would create a repo with a visibility other than the configured one ("Update the provider plugin and rerun `sase repo init`"). | `src/sase/sdd/_sidecar_init.py:142–150` | `sase-1ck.5`'s `visibility: private` role can't be created until sase-github learns `--private`, and the `.5` bead doesn't mention that work. A **public** attachments sidecar works with today's provider. |
| Remote-machine support moves **no files**. Fleet content reads default to 64 KiB (max 256 KiB), and `%dispatch` rejects attachments, files, and images before submission. | `sase_gateway/src/contract.rs:1340`, `docs/remote_dispatch.md:219` | Large files must stay on enrolled machines. A reader gets at them by running work there, not by downloading. |
| GitHub raw serving: an **extensionless** object is served as `text/plain` with `nosniff`, and a `.png` as `image/png`. | `curl -I` against `sase--agents/files/objects/…` and a research PNG | Public objects need a file extension to render inline on bead pages. The CAS layout `sase-1ck` reuses is extensionless. |
| SASE already publishes arbitrary bytes and tool output: prompt-cited files go to `sase--agents/files/objects/sha256/…`, alongside 11,468 public transcripts. | agents clone | SASE is already public-by-default for text. Attachments add risk mainly for bytes nobody read: images, raw logs, and binaries. |
| **Leaked credentials:** 1 distinct LLM-provider API key in 12 files, 1 bot token in 1 file, and no match in the sase tree. | count-only `git grep` on the agents clone | The dominant leak vector is environment dumps in tool output (cld). A scanner that knows the current secret values catches it. |
| `~/.sase/telegram_bot_token` is an **owner-only (0600) secret file** that `sase-1ck`'s sensitive-path list does not match. `~/.sase` also holds personal-content zones (`telegram/`, `notifications/`, `mobile_gateway/`, prompt and command history). | `stat`, `ls` (no contents read) | "SASE-owned state is public-safe" is false as a blanket rule. The owner-only mode check (cld) catches this file; a path denylist alone does not. |

## 2. Critique of the proposal

### 2.1 The goal: yes, once the audience is named precisely

"Everyone working on the project" and "the world" are different audiences.
`sase--beads` is world-readable, so putting bytes there means the world: scrapers, forks,
and search, not just collaborators. For the `sase` project those audiences mostly
coincide. It's public OSS, and SASE already publishes prompts, transcripts, plans, and
research. For SASE as a product they don't. A company project with a private primary
and the default public beads sidecar would leak every "non-sensitive" screenshot.

The right rule is the one issue trackers use: **an attachment is as visible as its
container.** GitHub issue attachments follow repo visibility, and Jira and GitLab
inherit issue security (grk, cld). So the default audience is **bead readers**. That
means public for `sase`, and private automatically for any project whose beads sidecar
is private.

### 2.2 Bytes in `sase--beads`: no (5 of 5, plus this report)

- **It taxes the hot path.** Beads is a full clone with `auto_sync`, and any agent
  that claims a bead materializes it. Every screenshot would reach every bead-touching
  workspace on every machine. `sase-1ck`'s hidden `--filter=blob:none` clone fetches
  only the one blob a reader opens.
- **Purge becomes an event-log rewrite.** Erasing a leaked blob means `filter-repo` on
  the repo that carries every bead event, with 18k+ commits and every machine's clone
  affected. In a dedicated attachments repo the same rewrite touches only media.
- **Push protection would block bead publication.** Once it is enabled (and it should
  be), a rejected blob push to beads would stall note, claim, and close publishing.
- **An orphan `attachments` branch doesn't help.** Clones fetch `+refs/heads/*`, so
  every beads clone would need a refspec migration (cld).
- **There is no offsetting benefit.** The only gain is relative links on bead pages.
  A public attachments sidecar gives absolute links with none of the cost.
- **A small-object exception doesn't help either.** mus considered allowing only files
  of 2–5 MiB or less in beads, then rejected it, and so do I. It is a second policy to
  explain, and it grows as attaching gets easy.

### 2.3 "Agents default to public; they opt into private": no, not as the classifier

- Agents don't read the whole file they attach. Line 3,420 of a log can hold a bearer
  token. A screenshot can show a notification.
- The observed leak isn't hypothetical. Environment dumps in tool output have already
  put two live-looking credentials into a public repo.
- A path denylist guards names, not contents. It already misses SASE's own token file.
- Publication is irreversible. Tombstones don't reach forks, clones, caches, or GitHub's
  retention of unreachable objects. The only real remedy is to **rotate** the secret.

The fix is not to make agents cautious by default; mus's "explicit flag or private" rule
would recreate the lock-chip wall. The fix is a **mechanical policy that fails private**,
with the agent adding only what the machine can't see: user intent, and whether the data
is about people.

### 2.4 Large files through remote machines: yes, but it's a scoping rule, not a transport

It's the right simplification: large files never go public, and there are no egress
bills or LFS quotas. But today "remote-machine support" can dispatch an agent to a
machine. It can't ship bytes (§1). §6 shows how to make this honest with almost no new
code.

### 2.5 Would I take a different approach?

Only if the intended audience is **org members only**. In that case, keep `sase-1ck`
exactly as planned (private sidecar), fix sase-github `--private`, and grant access
through the org's base `read` permission. That has zero leak risk and zero
classification work. It is the right choice for a closed team. Your stated aims are
public bead pages, OSS readers, and zero-setup frontends, so I recommend the public
default described below. It's roughly one medium epic on top of `sase-1ck`.

## 3. Where the reports disagreed, and how I resolved it

| Issue | Positions | Resolution |
| --- | --- | --- |
| **Default for agents** | grk: public, and a scan hit refuses. cld: `auto` from provenance plus scan (~87% of cited evidence publishes). cdx: `auto`, but logs, screenshots, and archives are restricted without public provenance. mus: agents must pass an explicit flag, or it's private. gem: images are "inherently public-safe". | **cld's `auto` policy, with narrower public zones** (§4). cdx is too strict: SASE's own logs are ~30% of cited evidence and scan well. **gem is wrong about images:** pixels can't be scanned, so images need provenance. mus's rule would make most attachments private. |
| **Where private bytes live** | cdx, cld, grk, mus: a private git sidecar. gem: remote-machine SFTP. | **A private git sidecar**, the one `sase-1ck.5` already builds. A tailnet-only store excludes collaborators and puts private availability at the mercy of laptops sleeping. |
| **Private metadata on the public wire** | cdx: an opaque id plus a restricted manifest. grk: omit `sha256`. cld: keep reasons off the wire. mus: keep as is. | Always keep **reasons** off the wire (cld). **Redact** the hash, origin, and dimensions of private attachments in a dedicated phase (§5.3). Until that lands, say plainly that names and prose are public. |
| **Upload ordering** | cdx: upload and verify before the event (fail closed). Others: keep `sase-1ck`'s order (event commit, then upload, then publish) with the outbox. | **Keep `sase-1ck`'s order.** Outbox entries carry their audience, and nothing ever falls back across audiences. A pending badge is honest; blocking offline authors isn't needed. |
| **Public size cap** | cdx 10 MiB, cld 25, grk/mus/gem 50. | **25 MiB**, which equals `auto_fetch_max_bytes`, so every public object auto-fetches. Tune it from real usage. |
| **Per-file control syntax** | gem: `@private:./x` / `@public:./x` in note text. Others: flags. | **Flags only** (`--private` / `--public`). New `@kind:` prefixes would collide with citation grammar and add a typo-to-public failure mode. For mixed notes, attach the private file with `sase bead attach --private`. |
| **Large files** | gem: rclone SFTP. grk: origin only, plus dispatch. mus: an origin-online fetch tier. cdx/cld: rclone now, a fleet blob API later. | Origin CAS plus a dispatch hint in v1, with the optional rclone tier from `sase-1ck.6` (§6). |
| **Timing and naming** | grk: amend `.5` now to public. cld: rename `.5`'s role now. cdx/mus: add a new public repo after the close. | **Rename in `.5` and add `--private` support now. Do not flip `.5` to public** before the policy engine exists (§8). |

## 4. Deciding what is sensitive

### 4.1 Two orthogonal axes

| Term | Meaning |
| --- | --- |
| **public** | Readable by anyone who can read the bead store; for `sase`, the world. Treat it as irreversible publication. |
| **private** | Readable only by principals on the project's private attachments repo (today: org members). Not "only the author", and not encrypted. |
| **local-only** (`-L`) | An **availability** state, not an audience. The bytes never leave the machine. |
| cached, pending, not downloaded, no access, purged | Availability states, independent of audience. |

### 4.2 Decision order (core: `attachment_audience_decision`)

Python gathers facts: git status, stat, zones, and run start time. The rule belongs in
sase-core because every frontend must agree on it (`rust_core_backend_boundary`). The
first matching rule wins.

| # | Signal | Result |
| --- | --- | --- |
| 0 | The bead store is private. | private (nothing public to target) |
| 1 | **Sensitive path**: `sase-1ck`'s list, **plus SASE's own secret files** (`<sase home>/telegram_bot_token`, gateway and fleet credentials, and similar) and configured patterns. | **refuse**. With `-S`: private or `-L` only, **never public**. |
| 2 | The author passes `--private` or `-L`. | private / local |
| 3 | Size > `public_max_bytes` (25 MiB). | private tiers (§6) |
| 4 | **Scan hit** (§4.3). | private. The echo names the reason and suggests attaching a redacted excerpt. |
| 5 | **Private provenance**: owner-only mode (`mode & 0o044 == 0`); git-ignored; inside a worktree whose remote is private or unresolvable; personal or config zones (`~/.config`, `~/.local/share`, `~/Documents`, `~/Downloads`, `~/Desktop`, mail, chat, notes vaults); **SASE personal-content zones** (`telegram/`, `notifications/`, `mobile_gateway/`, prompt and command history). | private |
| 6 | **Opaque type**: a database, archive, core or heap dump, executable, or other unscannable binary. | private |
| 7 | **Image or video** not produced during this run in the workspace, managed tmp, or a SASE output directory, and not tracked in a public repo. | private |
| 8 | **Positive public evidence**: tracked and unmodified in a public-remote checkout (cdx's strongest rule: the exact bytes are already public); or scan-clean text or self-generated media from the workspace, scratch, or SASE's registered publishable output zones (logs, tool-run logs, perf traces, TUI screenshots). | **public** (the bead store's audience) |
| 9 | Anything else. | **private** (fail-private) |

- **Git probes fail private.** If the remote visibility or tracked state can't be
  determined (for example, an SSH host alias the inventory can't map), the rule
  resolves to private.
- **Widening is a human act.** An agent passing `--public` over a policy-private result
  gets a refusal that names the reason and the exact `sase bead attachment publish`
  command, which it can offer through a gate (`/sase_gate`). Gates end the agent's turn
  and never block it, which fits the `gates-never-block` decision. A human on a TTY
  confirms; `--public -y` skips the confirmation.
- **Duplicates keep their intent.** If the same digest was already stored privately by an
  explicit `--private`, a later `auto` attach of those bytes stays private and warns.
- **Reasons stay local.** They appear in the echo, local JSON, and CAS metadata. Never
  put them on the public descriptor: "credential detected" would point attackers
  straight at the blob (cld).

### 4.3 The scanner (core, streaming, text classes only, ≤ 25 MiB)

1. **Known values:** the values (12 or more characters) of secret-named environment
   variables (`*TOKEN*`, `*SECRET*`, `*_KEY`, `*PASSWORD*`, `*CREDENTIAL*`), plus the
   contents of SASE's own secret files. Match them with Aho-Corasick, and hold them in
   memory only. This is the highest-precision detector, and it is the one that would
   have caught the observed leaks.
2. **Credential patterns:** a high-precision subset of the MIT-licensed gitleaks rules.
   Cover GitHub, Anthropic, OpenAI, Google (`AIza…`), AWS, Slack, Telegram bot tokens,
   Stripe, PEM private keys, and JWTs, plus `key|secret|token|password = <high-entropy>`.
3. **Env dumps:** five or more `NAME=value` lines in a short window, or a dict or JSON
   object with five or more well-known env keys. An env dump goes private **even with no
   secret match**, because that is where secrets travel.

- Textual SVG screenshots are text and get scanned. Raster images rely on rule 7. OCR
  stays out of v1.
- Enable **GitHub push protection** on the public attachments repo, and on every public
  sidecar today, as a backstop. It isn't the classifier: it covers only provider
  patterns, and it can't know SASE's environment values.
- A `GH013` rejection is a **permanent** failure. Route the object to private, badge it
  `⛔ blocked by secret scanning`, and never retry it forever.

### 4.4 What agents are told (the whole answer to "how do they decide")

> **Attachment visibility.** Attachments default to the bead's audience (public for
> public projects). SASE classifies each file and prints the result (`🌐 public` or
> `🔒 private (env dump)`). Add `--private` when the file:
>
> 1. comes from outside this project's public repos (another project, a private repo,
>    the user's notes, mail, or chats);
> 2. contains data about people other than public contributor identities;
> 3. is a screenshot or recording you didn't render yourself, or one that could show a
>    token, notification, or private conversation;
> 4. is a raw dump you didn't create and read in full (env, config, database,
>    core/heap dump, archive); or
> 5. the user or prompt calls it confidential, or the bead is about credentials, auth,
>    or production data.
>
> Prefer an excerpt you generated over a whole raw log. Note prose and filenames are
> public even when the bytes are private, so never describe a secret in them. Never
> force a file public. If SASE made it private and you think it shouldn't be, say so in
> the note and offer a publish gate.

Put this in the beads skill source and the `/sase_new_task` source, per the
generated-skills rules, and in `attach --help`.

### 4.5 Expected effect

cld classified the 434 real file paths cited in beads today. About **87%** would publish
automatically under its policy. The main sources are public checkouts (36%), SASE-owned
logs and state (30%), scratch (6%), and the dotfiles checkout (5%). The carve-outs I added
(SASE personal-content zones and non-self images) touch only a small slice. **This is an
estimate, not a re-measurement.** Most false-privates are config files. They stay
readable to org members and can be published with one command.

## 5. Stores, wire, and lifecycle

### 5.1 Topology

```text
note event in sase--beads  (prose + descriptor: name, visibility, …; never bytes)
   │
   ├─ local CAS             always first; cache and crash safety
   ├─ public git sidecar    <project>--attachments          visibility = beads; ≤ 25 MiB
   │                        hidden bare --filter=blob:none clone; anonymous reads
   ├─ private git sidecar   <project>--attachments-private  created lazily on first --private
   └─ large / origin        origin CAS (+ optional sase-1ck.6 rclone tier to athena)
```

- **Public layout keeps an extension:** `files/objects/sha256/<xx>/<sha>.<ext>`, with a
  canonical `ext` per MIME type from the core extension table. The curl check in §1
  shows why: without it, pages can't embed images. Spike the page-embed path (camo
  proxy) before fixing the layout.
- **Reuse `GitAttachmentStore`, parameterized by role.** It already uses plumbing
  commits, filename-free commit messages, digest verification, and quarantine. A public
  remote can also serve reads as a digest-verified HTTPS GET, with no git credentials.
- **Creation.** The public role is created by `sase repo init` with a consent prompt
  that says **PUBLIC** and defaults to yes. It works with today's sase-github. The
  private role needs `gh repo create --private` in sase-github (§8).
- **Rotation.** Location-free descriptors allow a new store (`…-2`) well before GitHub's
  1–5 GB guidance. `sase bead doctor` reports logical and physical bytes.

### 5.2 Wire (additive)

- **`visibility: "public" | "private"` is optional on the descriptor, and absent means
  private.** Every attachment written under `sase-1ck` stays private unless explicitly
  published. An old writer that rewrites a manifest drops the field, which fails
  private, the safe direction. `BEAD_EVENT_SCHEMA_VERSION` stays 1.
- **Visibility is intent, not a locator.** Writers route by it, and **store order,
  object presence, and outbox retries must never change it.** Readers still try every
  store in order.

### 5.3 Private metadata (a dedicated, deferrable phase)

Today's descriptor puts the filename, size, MIME type, image dimensions, SHA-256, and
origin hostname on the public wire, even for private bytes. The SHA-256 is a
**confirmation oracle**: anyone can check a guessed low-entropy file against it.

For private attachments, the public descriptor should carry only
`{name, visibility: private, private_id}`. The hash, size, MIME type, dimensions, and
origin move to a manifest in the private store, keyed by the random `private_id`.

Old readers require `sha256`, so this needs a mixed-fleet gate like `sase-1ck`'s
`core_wire` rule. It's worth doing but not blocking. Until it lands, docs and `--help`
must say that **private protects bytes, not names or prose.**

### 5.4 Ordering, commands, and badges

- **Keep `sase-1ck`'s order:** commit the event under the lock, upload before
  publication, then publish. The outbox records each object's audience. A public upload
  never falls back to private except on the permanent `GH013` path, which is visible.
  A private upload never falls back to public.
- **`attachment push`** makes bytes available. It **never changes audience**.
- **`attachment publish <id> <name>`** is for humans or approved gates. It rescans,
  previews exactly what becomes public, warns that publication is irreversible, and
  updates the manifest through `NoteEdited` (`Some`). No history is rewritten.
- **`attachment unpublish`** tombstones the object in the public store, makes sure a
  private copy exists, and flips the manifest. It prints the honest caveat: forks,
  clones, and caches persist, so **rotate first**. It also prints the `filter-repo`
  runbook for the **attachments** repo, never beads.
- **Badges.** Add `🌐` and `🔒` for audience. Add a distinct
  `🔒 no access (<repo>)` state, instead of the misleading `✕ unavailable offline`, and
  a doctor finding for writers without push access (both gaps come from the
  storage-and-access note). Add `⧉ on <origin>` for large objects.
- **Pages.** Embed public images (capped per note) and link other public files. Keep
  the `🔒` chip for private ones.
- **Doctor.** Rescan cached public text objects whenever scanner rules change, and lead
  any finding with "rotate". Also report repo growth, no-access states, and orphans.

## 6. Large files

- **Never public.** Anything over 25 MiB goes to private tiers.
- **v1 needs no new transport.** Bytes stay in the origin's CAS with a `⧉ on athena`
  badge. `sase bead attachment path` on another machine prints the exact
  `%dispatch:athena …` hint. `%dispatch` can't carry the file, but an agent dispatched
  to the origin reads it locally.
- **Optional replication.** If `sase-1ck.6` lands its rclone tier (SFTP to athena over
  the tailnet), use it as the private large tier. Athena is always on; laptops sleep.
- **Later, only if usage justifies it:** a capability-scoped streaming blob endpoint on
  the fleet gateway, following cdx's list: digest and size pinned, audience-checked,
  short-lived handles, and rate limits. Today's 256 KiB content reads are not that.
- **Be honest about durability.** An origin-only object dies with its disk.

## 7. Requirement adjustments (called out)

| # | As requested | Adjusted to | Why |
| --- | --- | --- | --- |
| **A1** | Non-sensitive attachments are available to all project users. | Default audience = **bead readers**: public for `sase`, private for projects with private beads. | This is the audience you actually named. It is correct for OSS and company projects, and it matches issue-tracker norms. |
| **A2** | Move public bytes into `sase--beads`. | A **dedicated public attachments sidecar** (hidden partial clone). Beads stays metadata-only. | Hot-repo cost, event-log purge, and push-protection coupling (§2.2). The access is the same as beads. |
| **A3** | Agents decide; default public; opt into private. | **SASE decides mechanically (`auto`). Agents may narrow to private; only humans widen.** | Agents don't read whole files, the leak is irreversible, and the observed leak vector is machine-detectable. |
| **A4** | "Public unless sensitive." | **Public only with positive evidence; uncertainty → private.** | A negative detector result is not proof a file is safe for the world (cdx). |
| **A5** | (unstated) | `sase-1ck` attachments **stay private** unless explicitly published. Absent `visibility` means private. | They were attached under a private-storage promise. |
| **A6** | Large files only via remote machines. | Agreed. **Nothing over 25 MiB is public.** v1 = origin CAS plus dispatch, with optional rclone to athena. | GitHub limits, and big blobs are the least reviewed. Today's fleet can't move bytes. |
| **A7** | (unstated) | `-S/--allow-sensitive` can **never** target the public store. | The override was designed for a private-only store. |
| **A8** | (unstated) | Private **reasons** never go on the public wire. Private **hash and origin** are redacted in a later phase; until then, docs say names and prose are public. | A public hash is a guess-confirmation oracle. A public reason is a treasure map. |
| **A9** | Follow-up only after `sase-1ck` closes. | Plus one **small `sase-1ck` fix now** (§8). | `.5` can't create its private repo as scoped, and fixing it can free the plain name. |
| **A10** | (out of scope) | **Rotate the leaked credentials, and enable push protection now.** Reuse the core scanner in the agents-sidecar transcript and prompt-file publishers as separate work. | The existing leak path is worse guarded than attachments would be. |

## 8. Timing relative to `sase-1ck`

Your plan (follow-up after the close) is sound. Grammar, CAS, wire, CLI, TUI, and purge
are all still needed. But `sase-1ck.5` has a latent gap, and it is also the cheapest
place to settle naming:

- **Recommended now:** have `sase-1ck.5`:
  1. name its reserved role `attachments_private` (repo `<project>--attachments-private`);
  2. add `--private` creation to sase-github, with a provider preflight that reports the
     requested visibility, and flip the test that forbids `--private`.

  That is work `.5` needs anyway. It leaves the plain `attachments` name for the public
  default, and nothing else in `sase-1ck` changes, because absent `visibility` already
  means private.
- **Do not** flip `.5` to a public default now, as grk suggests. Publishing by default
  before the scanner and provenance policy exist would rely on the path denylist alone,
  and §1 shows that denylist already misses a real token file.
- **If you'd rather not touch `sase-1ck`:** don't create any `sase--attachments` repo
  until the follow-up. `sase repo init` would refuse anyway. Accept local-only
  attachments in the meantime. **Never flip a populated private repo to public**; that
  publishes its entire history.

## 9. Recommended solution

**The rule.** An attachment is as visible as its bead unless SASE or its author marks it
private.

- SASE decides in core from provenance, a content scan, and file type.
- Uncertainty resolves to private.
- Agents can only narrow; humans widen.
- Large files are never public.
- `sase--beads` never holds bytes.

**Now, independent of the epic**

1. Rotate the leaked LLM-provider key and bot token. After that, file the redaction
   follow-up with `/sase_new_task`. Filing first would advertise live credentials.
2. Enable secret scanning and push protection on every public `sase--*` repo.
3. Apply the `sase-1ck.5` naming and `--private` fix (§8), or hold off creating any
   attachments repo.

**Follow-up epic: public bead attachments** (after `sase-1ck` closes, behind a beta flag
such as `public_bead_attachments`; rendering is never gated)

| Phase | Scope |
| --- | --- |
| 1 · `core_audience` (sase-core) | The optional `visibility` wire field (absent = private). `attachment_audience_decision` (§4.2) and the streaming scanner (§4.3). Placement by audience and size. The SASE secret-file and zone tables. Bindings and a pin bump. Decision-table tests with **synthetic** secrets only. A one-time count-only run over the published transcripts, proving the scanner flags every known hit. |
| 2 · `provenance_cli` | The provenance probe: tracked and unmodified, ignored, remote visibility through the inventory plus cached `gh` (fail-private), mode bits, zones, and run start time. `--private`/`--public` on `note`, `close -n`, `update -n`, `+1 -n`, and `attach` (check short flags against `cli_rules.md`). Refuse agent widening and offer a gate. Echo and JSON with local-only reasons. `-S` coupling. Config: `public_max_bytes`, `sensitive_patterns`. |
| 3 · `public_store` | The public role following beads visibility, with default-yes creation. The extension-preserving layout (after the camo spike). The role-parameterized `GitAttachmentStore`. The audience-tagged outbox. `GH013` rerouted to private. Anonymous reads. Two-home tests on local bare remotes. |
| 4 · `presentation_lifecycle` | `🌐`/`🔒`/`no access`/`⧉` badges in `show`, `read`, JSON, and the TUI (a chip toggle, with confirmation to widen). Page embeds and links. `publish` and `unpublish`. Doctor rescans, growth, and access checks. |
| 5 · `private_metadata` (deferrable) | Redacted private descriptors (`private_id` plus a private manifest) behind a mixed-fleet gate, with correlation and guessed-content tests. |
| 6 · `ga` | Remove the flag. Update `docs/beads.md` and `docs/configuration.md`. Add the §4.4 guidance to the skill sources. Propose reusing the scanner in the agents-sidecar publishers as a follow-up task. |

**Acceptance**

- A clean workspace log publishes, is fetched on a second SASE home **without private
  credentials**, and renders or links on the bead page. A self-rendered TUI screenshot
  embeds inline.
- The same log with an injected env dump, a secret env value, or a credential pattern
  goes private. The reason appears only locally. An agent's `--public` on it is refused
  with a publish-gate hint.
- `-S` with `--public` fails. Neither `~/.sase/telegram_bot_token` nor an owner-only
  file ever goes public.
- A pre-epic descriptor never publishes implicitly. No fallback, retry, dedup, or
  store-order change ever moves bytes across audiences.
- Nothing over 25 MiB touches the public store. Large objects show `⧉ on <origin>` and
  a dispatch hint.
- A restricted attachment renders `🔒 no access`, not "offline", for a reader without
  a grant.
- The `sase--beads` pack size doesn't grow with attachment bytes. Beads without
  attachments do no new work.
