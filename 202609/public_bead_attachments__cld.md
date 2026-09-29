# Public-by-Default Bead Attachments: Critique and Recommended Design

_Researcher: cld · 2026-09-29_

**Question.** After epic `sase-1ck` (bead note attachments) closes, a follow-up epic should
give every user working on a SASE project access to all non-sensitive bead attachments by
default. The proposal is to move non-sensitive attachment bytes out of the private
`sase--attachments` sidecar and into the public `sase--beads` repo. It is fine if large
files work only through SASE's remote-machine support. The open question is how to tell
whether a file is sensitive, and how agents should choose between public and private.

**Sources.**

- The `sase-1ck` bead and its plan (`plan:202609/bead_note_attachments.md`).
- `research:202609/bead_note_attachments/attachment_storage_and_access.md`, plus the
  earlier consolidated attachments report as background.
- The sase tree at `04accd59d0` and the sidecar clones.
- Live `gh` checks of `sase-org`.
- A corpus scan of all 6,598 beads (18,504 descriptions and notes).
- A scan of the published agent transcripts.
- GitHub documentation (linked at the end).

Unless a claim is labeled as an estimate or recommendation, I checked it myself.

---

## TL;DR

1. **The direction is right, but the destination is wrong.** An attachment should
   default to the **same audience as the bead it's attached to**. For `sase` that means
   public. The public bytes should go in a **dedicated public sidecar repo**, not in
   `sase--beads`. The beads repo is hot (about 530 commits a day, 18.3k commits total),
   is fully cloned into workspaces, and holds the event store. Putting blobs there would
   bloat every clone. It would also let a secret in one blob block bead publication, and
   it would make any real purge a rewrite of the event store's history.
2. **Check the premise.** `sase-org`'s base repository permission is already `read`. So
   **every org member can already read a private `sase--attachments` repo** with no extra
   setup. Going public adds nothing for org members. It helps people *outside* the org:
   readers of the public bead pages, zero-credential frontends (Telegram, mobile, CI), and
   future SASE users who aren't org members. That benefit is still worth having. But the
   real payoff is **complete public bead pages and zero-setup reads**, not collaborator
   access.
3. **SASE should decide sensitivity mechanically; the agent should not be the classifier.**
   A core policy combines three signals: provenance (where the file came from), a
   secret/credential scan, and whether the file type can be scanned at all. Agents can
   always **narrow** visibility to private. They can **never widen** a policy-private
   result. Only a human can publish one. When the policy is uncertain, the file goes
   private. A wrong private costs an org member one click. A wrong public cannot be
   undone.
4. **The risk is real, not hypothetical.** Of **11,467 already-published agent transcripts**
   in the public `sase--agents` repo, **12 contain credential-shaped strings**. Both
   distinct values come from environment dumps printed in command or test output, and
   neither is a test fixture. A "known-value" scanner would have caught both: it checks
   for the exact values of secret-named environment variables in the current process.
   **Rotate those credentials now** (§8). This is separate from the epic.
5. **Measured against the evidence agents actually cite, about 87% of files would publish
   automatically.** Excluding noise, 434 file paths are cited in beads. About 87% are in
   public-repo checkouts, SASE-owned logs, traces, and state, or scratch space, and would
   publish once scanned clean. The remaining ~13% are config dirs, databases, and a
   private notes vault. Those would stay private, and nearly all of them are harmless
   false-privates.
6. **Adjustments to the requirements** (§7): visibility follows the bead store, not
   "always public". Bytes go in a separate public repo. Attachments written under
   `sase-1ck` stay private forever unless explicitly published. Large files are
   **private by construction**, and the public tier is capped at 25 MiB. The same core
   scanner should also guard the agents-sidecar transcript publisher.

---

## 1. Where `sase-1ck` leaves things

`sase-1ck` has ten phases, all `IN_PROGRESS` since 08:13 today. Nothing has landed:
`src/sase/bead/attachments/` does not exist on master, and neither does
`sase-org/sase--attachments`. When it closes, the design will be:

- **The descriptor is public, the bytes are private.** Each note event carries
  `{name, sha256, size_bytes, mime_type, image?, origin?}` in the public beads store. The
  bytes live in:
  - a local CAS,
  - a private `attachments` sidecar (a hidden bare partial clone, up to 50 MiB), and
  - an optional rclone large store (up to 2 GiB).
- **Stores are an ordered, digest-keyed list, and descriptors are location-free.** A store
  can be added, rotated, or migrated without editing any note. This is what makes the
  follow-up epic cheap.
- **Public bead pages show `🔒 name · type · size (private attachment)` chips.** They never
  link to the bytes.
- **Sensitive *paths* are refused unless `-S`.** Examples: `~/.ssh/**`, `**/.env*`,
  `*.pem`, `**/credentials.json`. **Nothing inspects content.**

The follow-up epic is therefore about three things: **a second store, a visibility
decision, and presentation.** The CAS, grammar, wire, outbox, and viewer machinery from
`sase-1ck` can all be reused.

## 2. Facts that shape the decision

| Fact | Evidence | Why it matters |
| --- | --- | --- |
| Every sidecar is public. The org also has private repos (three). | `gh repo list sase-org` | Public is the norm; private is a supported, normal choice. |
| **Org base permission is `read`** (`default_repository_permission: read`). The org has one member. | `gh api orgs/sase-org` | Every org member already reads private org repos. A private attachments repo is "shared by default" for members. |
| `sase--beads` is **hot**: 18,292 commits, ≈3,700 in the last 7 days, 106 MiB packed. Clones fetch `+refs/heads/*`, and it is cloned into 9 of 20 workspaces on apollo. | beads clone, `git count-objects`, `sase repo list` | Blobs on any branch reach every workspace fetch. Purging means rewriting hot history. |
| Secret scanning and push protection are **disabled** on `sase--beads`, `--agents`, and `--research`. | `gh api repos/…` `security_and_analysis` | Today GitHub gives no safety net. Both features are free for public repos. |
| SASE **already publishes arbitrary file bytes publicly**: prompt-cited files are copied to `files/objects/sha256/…` in public `sase--agents`, with **no sensitivity check**. So far there are 4 objects (40 KiB). | `prompt_artifact_staging.py`, agents clone | The byte publisher to reuse already exists, and so does the unguarded risk. |
| **Agent transcripts are public**: 11,467 `chat.md` files, with tool output included. | agents clone | Text an agent *read* is often already public. Attachments add risk mainly for bytes nobody read: images, raw logs, and binaries. |
| **12 of 11,467 public transcripts contain credential-shaped strings.** Both distinct values come from env dumps and are not fixtures. 85 transcripts contain env-dump-like lines. | masked `git grep` (values never printed) | The dominant leak vector is **environment dumps in command and test output**, and pattern plus known-value scanning catches it. |
| Local SASE logs: 0 of 40 files hit. Local transcripts on apollo: 0 of 2,926. | `grep` of `~/.sase/logs`, `~/.sase/chats` | The base rate is low but not zero. This is a "rare but irreversible" risk. |
| Sidecar roles already have `visibility: public/private`, and `sase repo init` creates missing sidecars with their configured visibility. | `docs/configuration.md` §sidecars | A public attachments role is a configuration entry, not new infrastructure. |
| GitHub hard-blocks files over 100 MiB and warns over 50 MiB. It recommends repos under 1 GB, and strongly under 5 GB. Unauthenticated `raw.githubusercontent.com` reads are rate-limited (2025). | GitHub docs | This sets the public tier cap and the rotation story. Authenticated git fetches are the read path. |
| GitHub issue attachments **follow the repo's visibility** (private-repo attachments have required login since May 2023). No per-attachment privacy exists. | GitHub changelog | "An attachment is as visible as its container" is the industry default. A per-attachment private override is SASE's addition. |

**What agents actually cite** (from `sase bead list -s all -n 0 -f json`: 475 path
citations, 41 of them noise, classified by the policy proposed in §5):

| Share | Class | Proposed result |
| ---: | --- | --- |
| 36.0% | Files in workspace or sidecar checkouts (public repos) | public |
| 30.3% | SASE-owned logs, traces, reports, and state under `~/.sase` | public if the scan is clean |
| 6.3% | Scratch (`/tmp`, `/var/tmp`) | public if the scan is clean |
| 4.8% | The public dotfiles (chezmoi) checkout | public |
| 2.1% | User SASE memory and xprompts (`~/sase`) | public if the scan is clean |
| 7.6% | Config and data dirs outside any public repo (`~/.config`, `~/.local/share`, `~/.claude`, `~/.cargo`) | private |
| 1.9% | SQLite databases | private (opaque) |
| 1.7% | Other or unknown | private |
| 0.6% | The personal notes vault (a private repo reached through an SSH host alias) | private |

By extension, 434 of the citations are real paths: `py` 181, `md` 85, `json` 79, `jsonl`
48, `yml` 27, `log` 16, `txt` 11, `sqlite` 9, and `png` 4. Today's evidence is
overwhelmingly **text**, which is scannable. Images are rare now but will grow once
attaching is easy.

## 3. Critique: is public-by-default a good idea?

### 3.1 What it buys

- **Complete public bead pages.** A bug bead's screenshot renders inline on GitHub, and
  its log is one click away. Bead pages are SASE's public face. Today they would show a
  wall of `🔒` chips.
- **Zero-credential reads.** CI, a fresh machine, the Telegram photo-delivery follow-up,
  the mobile frontend, and anyone who isn't an org member can all read attachments. There
  is no "no access" state for most readers. That state is a gap the storage-and-access
  report already found in the `sase-1ck` plan.
- **Consistency with SASE's posture.** Every sidecar is public, including chats and
  prompt-cited files. Most attachments derive from content that is already public, such
  as TUI screenshots of public prompts and logs of public code.
- **No repo-creation friction for private-by-accident projects.** The default store
  follows the bead store, so a project with private beads gets private attachments with
  no extra decisions.

### 3.2 What it costs

- **Irreversibility.** A public GitHub blob is effectively permanent. Purge removes it from
  the tip; history rewrite, forks, clones, caches, and scrapers do the rest. This is the
  whole risk. Every design choice below exists to make a wrong public rare.
- **Images and binaries can't be scanned cheaply.** OCR is out of scope, so screenshot
  safety has to come from provenance. A TUI screenshot an agent rendered itself is low
  risk. An arbitrary desktop capture is not.
- **Complexity.** A second store, a classification policy, a visibility UI, and
  publish/unpublish commands. That is roughly one medium epic on top of `sase-1ck`.

### 3.3 The premise, stated precisely

"All users working on a sase project should have access by default" is **already true for
org members**, because of the org's base `read` permission. Only people outside the org
are excluded. So the honest framing of the requirement is:

> Attachments should be as visible as the bead that carries them, so the public bead
> record is self-contained, while anything that shouldn't be public stays readable to
> project members.

### 3.4 Verdict

**Yes, do it, with three conditions.** Without them I would recommend the conservative
inverse instead: private by default plus an explicit `publish`. That inverse is a
legitimate choice if the only intended audience is org members.

1. The bytes go in a **dedicated public repo**, not `sase--beads` (§4).
2. The decision is **mechanical and fails private** when uncertain. It uses a content
   scanner that includes **known-value matching** (§5).
3. **Legacy attachments never become public implicitly** (§6.1).

## 4. Where the public bytes should live

| Option | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| **A. `sase--beads` default branch** (as proposed) | No new repo. Relative links in pages work. | Every workspace clone and auto-sync fetch downloads every blob. Blob commits compete with ≈530 bead-store commits a day. A GitHub push-protection rejection, if enabled, would block **bead publication**. Purging rewrites 18k+ commits of the event store. The event store's 5 GB budget is shared with media. | **Reject** |
| **B. `sase--beads` on an orphan `attachments` branch** | No new repo. Pushes to another ref don't conflict. | Existing clones fetch `+refs/heads/*`, so every beads clone on every machine would need a refspec migration, or it downloads all media. The size budget and the "delete the repo" nuclear option are still shared. Forks carry the media. | Reject |
| **C. A dedicated public sidecar** (the `sase-1ck` store with public visibility) | Exact isolation. It is never in workspaces: it is a hidden bare `blob:none` clone, so readers fetch one blob. Its own size budget, so it can rotate (`…-2`) when it nears 1–5 GB, which location-free descriptors allow. Purge or history rewrite touches only media. Push protection can be enabled without endangering beads. `sase repo init` creates it like any sidecar. | One more repo per project (auto-created), and pages use absolute URLs. | **Recommend** |
| D. R2 public bucket, Git LFS, or GitHub Releases | CDN, no repo limits. | New credentials on every machine; LFS bandwidth quotas; Releases are API-driven and awkward. None are sidecars. | Not needed; the user accepts remote-only for large files. |

**Access properties of C are the same as `sase--beads`:** anyone can read, and writing
needs the same grant as writing beads. If you want one grant, use an org team with write
on `sase--*`. The only thing A saves over C is one automated repo creation.

**Naming (a small decision).** "Attachments are public by default" reads best if the
**default store has the plain name** and the exception is labeled: `sase--attachments`
(public, following beads) and a private role such as `private_attachments`. `sase-1ck.5`
currently reserves the role `attachments` with default `visibility: private`, and the
repo doesn't exist yet. Two paths:

- Cheapest: ask `sase-1ck.5` to name its role for the private store now.
- Otherwise: have the follow-up add the public role under a new name, and live with
  `attachments` meaning private.

Both work, because descriptors never name a store.

## 5. Deciding what is sensitive

### 5.1 Principles

1. **A mechanical policy in `sase-core`, not agent judgment.** An LLM attaching a 2 MiB
   log hasn't read line 61 of an env dump, and it tends to accept defaults. Classification
   is also a rule every frontend must match (CLI, TUI, the future web and mobile), so it
   belongs in core under `rust_core_backend_boundary`. Python gathers provenance facts
   (git, stat, and so on) and passes them in.
2. **Asymmetric overrides.** The author can always choose `private`. The policy is `auto`
   by default. Choosing `public` over a policy-private result requires a **human**: a TTY
   with confirmation, or approval of a gate raised by the agent. An agent that passes
   `public` gets a refusal that says why and names the human command.
3. **Uncertainty resolves to private.** A false-private costs an org member nothing; they
   can still read it, and it can be published later. A false-public is permanent.
4. **Private reasons stay off the public record.** The wire records only the visibility.
   The *reason* (for example "credential detected") appears in the write echo, in local
   JSON, and in local CAS metadata. It **never appears in the public descriptor**, which
   would otherwise advertise which private blobs contain secrets.
5. **Minimize.** The guidance nudges agents to attach an excerpt they generated, such as
   the failing test's section, rather than a whole raw log. Excerpts are smaller, clearer,
   and less likely to contain secrets.

### 5.2 Decision order

The core function is
`attachment_visibility_decision(facts, scan, request, bead_store_visibility, limits)`,
which returns `{visibility, reasons, refuse?}`. Its rules, in order:

| # | Signal | Result |
| --- | --- | --- |
| 0 | The bead store is private. | private (there is nothing public to target) |
| 1 | A sensitive path (the `sase-1ck` list, plus SASE's own secret state such as `<sase home>/fleet/credentials.json`, already covered by `**/credentials.json`). | **refuse** unless `-S` (unchanged). With `-S`: private. |
| 2 | The author requests `private`. | private |
| 3 | Size is above `public_max_bytes` (default 25 MiB). | private or large tier (§6.3) |
| 4 | **The scan hits**: a credential pattern, a known secret value, or an env dump. | private, with a warning and a hint to attach a redacted excerpt |
| 5 | **Private provenance**: inside a git worktree whose remote is private or can't be resolved (for example an SSH host alias the inventory can't map); a git-**ignored** file; owner-only mode (`mode & 0o044 == 0`); another SASE project whose bead store is private; a personal or config zone (`~/.config/**`, `~/.local/share/**` outside a public worktree, `~/Documents`, `~/Downloads`, `~/Desktop`, mail and chat stores, configured notes vaults). | private |
| 6 | **Opaque type**: a database, archive, core or heap dump, executable, or other `binary` class that the scanner can't read. | private |
| 7 | **An image or video with non-self provenance**: not created during this agent's run (btime/mtime ≥ run start) inside the workspace, `$TMPDIR`/`/tmp`, or SASE-owned output dirs. | private for agents. For humans on a TTY: public, with the echo shown. |
| 8 | The author requests `public` and a rule in 4–7 said private. | Human: confirm, then public. Agent: **refuse** with the reason and `sase bead attachment publish …`. |
| 9 | Otherwise: a public-repo worktree, the workspace, scratch, SASE-owned logs/traces/state, or `~/sase`, with the text scanned clean or media self-generated. | **public** (meaning the bead store's audience) |

Git facts are fail-private. `tracked`, `ignored`, and remote visibility come from the repo
inventory and a cached `gh` visibility lookup. If any probe fails, the result is private.

### 5.3 The scanner (core, streaming, text classes only, ≤ `public_max_bytes`)

Three detectors, all cheap in Rust. A 25 MiB scan takes tens of milliseconds.

1. **Known values (highest precision; catches the observed leaks).**
   - At write time, collect the values of environment variables whose names look secret:
     `*TOKEN*`, `*SECRET*`, `*_KEY`, `*PASSWORD*`, `*CREDENTIAL*`, and `GH_TOKEN`/
     `GITHUB_TOKEN`. Keep values of at least 12 characters, held only in memory.
   - Aho-Corasick-match them against the file.
   - Both leaked values in the public transcripts were exactly this: a secret-named
     variable's value printed by `env` or a pytest `env = {…}` repr.
   - No regex set generalizes as well as this, and it has essentially no false positives.
2. **Credential patterns.** Use a curated, high-precision subset of the gitleaks rules
   (MIT):
   - GitHub (`gh[pousr]_`, `github_pat_`), Anthropic, OpenAI, Google API (`AIza…`),
     AWS (`AKIA…`), Slack (`xox…`), Telegram bot tokens, Stripe, PEM private-key headers,
     and JWTs.
   - Generic `key|secret|token|password = <high-entropy value>` assignments, with an
     entropy threshold.
3. **Env-dump detector.** ≥ 5 lines of `(export )?[A-Z][A-Z0-9_]{2,}=…` within a small
   window, or a dict/JSON object with ≥ 5 well-known env keys (`PATH`, `HOME`, `SHELL`,
   `USER`, …). An env dump is private **even with no secret match**, because it is where
   secrets travel.

SVG screenshots (Textual exports) are text and get scanned. Rasters rely on provenance
(rule 7).

**Why not just enable GitHub push protection?** Enable it as well; it is free for public
repos. But it is a **backstop**, not the classifier:

- It covers only provider patterns.
- It rejects the whole push, which the uploader must handle (§6.4).
- It can't see environment-derived values that SASE knows about.

### 5.4 What agents are told

Put this in `sase_beads.md`, the `/sase_new_task` skill source, and the `attach` help:

> **Attachment visibility.** Attachments default to the bead's audience (public for
> public projects). SASE decides automatically and prints the result, for example
> `⇡ public` or `🔒 private (env dump)`. Add `-V private` when the file:
>
> 1. comes from outside this project's public repos (another project, a private repo,
>    the user's notes, mail, or chats);
> 2. contains data about people other than public contributor identities;
> 3. is a raw dump you didn't create and fully inspect (env, config, database,
>    core/heap dump, archive); or
> 4. the user or prompt calls it confidential.
>
> Prefer attaching an excerpt you generated over a whole raw log. Never try to force a
> file public. If SASE made it private and you think it shouldn't be, say so in the note;
> a human can run `sase bead attachment publish`.

This is short on purpose. The policy does the work, and the agent only adds context the
policy can't see: user intent, and whether data is about people.

### 5.5 Humans and the TUI

- The write echo always names the destination:
  `⇡ public · sase-org/sase--attachments` or
  `🔒 private · sase-org/sase--attachments-private — owner-only file`.
- In the TUI add-note modal, each pending attachment chip shows `🌐`/`🔒`, and a key
  toggles it. Toggling to public over a policy-private result shows the reason and asks
  for confirmation.
- `sase bead show` and pages render `🌐` public attachments inline or linked, and keep the
  `🔒` chip for private ones.

### 5.6 CLI surface (additions only)

```text
sase bead note|close -n|update -n|+1 -n|attach ... [-V/--visibility auto|private|public]
sase bead attachment publish   <id> <name> [-y/--yes]                  # human-only; agents raise a gate
sase bead attachment unpublish <id> <name> -r/--reason WHY [-y/--yes]  # purge from public, keep private
sase bead attachment list ... -j   # adds visibility, and the local-only reason when known
```

`-V` is currently free on `note`, `close`, `update`, and `+1`. `-P` is taken on `close`.
Recheck `attach`/`attachment` against `cli_rules.md` when the verbs land.

## 6. Wire, stores, and lifecycle

### 6.1 Wire (additive, core)

- `BeadNoteAttachmentWire.visibility: "public" | "private"`. It is **optional, and absent
  means private.**
  - Every attachment written under `sase-1ck` (all stored privately) therefore stays
    private forever. Only `attachment publish` changes that, by editing the note's
    manifest (`NoteEdited` with `Some`, which the wire already supports).
  - `public` is defined as **"the bead store's audience"**, so the same value is correct
    for projects whose beads are private.
- There is no reason field (principle 4). `BEAD_EVENT_SCHEMA_VERSION` stays 1. Old readers
  ignore the field. An old writer that rewrites a manifest drops it, which fails toward
  private: the safe direction.
- Visibility is **intent and a rendering hint, not a locator.** Readers still try every
  store in order. If a digest is public anywhere, it is public; there is no hiding it.

### 6.2 Public store layout and pages

- Reuse `GitAttachmentStore`, parameterized by role. It uses plumbing commits, a bare
  partial clone, digest verification, and commit messages without filenames.
- **Keep an extension on public objects**, for example
  `files/objects/sha256/<xx>/<sha256>.<ext>`, with a canonical `ext` per MIME from the
  core extension table.
  - GitHub's camo proxy renders README images only when the served content-type is
    `image/*`, and raw serving picks the content-type from the extension. An
    extensionless object would probably break inline images on pages.
  - **Verify this in a one-hour spike** before fixing the layout.
- Bead pages embed public images, capped (for example 4 per note, like `show`), and link
  other public files. Absolute URLs to the attachments repo are fine.

### 6.3 Placement and large files

- Placement becomes
  `attachment_placement(size, visibility, tiers, local_only)`:
  - **public**: up to `public_max_bytes`, default **25 MiB**. That matches the auto-fetch
    cap, so every public object is auto-fetchable. It keeps a world-readable repo lean:
    an estimated ~1 GB/yr at 5 attachments a day averaging 500 KiB. It also stays well
    under GitHub's 50 MiB warning.
  - **private**: the `sase-1ck` git tier (up to 50 MiB), then the large tier.
- **Large files are private by construction**, which matches the user's "remote-machine
  support only". `sase-1ck.6` already plans the rclone store (SFTP to athena over the
  tailnet). If `rclone.conf` on every machine proves annoying, the fleet gateway could add
  an authenticated `attachment_object` capability. It would serve CAS objects from a hub
  host to enrolled controllers over tailnet HTTPS, but not from `origin` directly, because
  laptops sleep. Treat that as an option, not part of this epic.

### 6.4 Upload order and failures

- Keep `sase-1ck`'s order: commit the event, upload before publication, then publish.
  Public-classified objects go to the public store. When a private store exists, the
  object can **also** go there first, so fleet reads work immediately.
- **Push protection rejection (`GH013`)** is a *permanent* failure. Do not retry it
  forever. Route the object to the private store and badge it
  `⛔ publication blocked by GitHub secret scanning`. A doctor fix edits the manifest to
  `private`.
- Optional: `bead.attachments.publish_delay` (default `0`). Public objects wait in the
  outbox with `not_before` and show `⏳ public in 8m`. During that window, `unpublish` is a
  free cancel. It is useful only if someone is watching, so it ships off by default.

### 6.5 Publish, unpublish, purge

- **`publish`**: a human (or an approved gate) uploads to public and updates the manifest.
  Humans only.
- **`unpublish`**:
  1. Tombstone and remove the object from the public tip.
  2. Ensure a private copy exists.
  3. Update the manifest to private.
  4. Print the honest caveat: forks, clones, caches, and GitHub's unreachable-object
     retention persist. Rewriting the *media* repo's history is feasible because nothing
     clones it into workspaces. Include the `git filter-repo` plus GitHub-support
     runbook. **Rotate any exposed secret first.**
- `purge` (from `sase-1ck.9`) applies to every store, as planned.

### 6.6 Rescanning

When the scanner's rule set or pattern version changes, `sase bead doctor` rescans
cached public text objects and reports any new hits. This finds leaks that older rules
missed. Everything it reports is already public, so the report must lead with **"rotate"**.

### 6.7 Flag and mixed fleet

- Put the follow-up behind a `beta` flag, for example `public_bead_attachments`. When it
  is off, every new attachment is private, exactly as in `sase-1ck`. Rendering is never
  gated.
- An older build sees a public attachment as `✕ unavailable`, because it doesn't know the
  public store. That is harmless.
- Enable the flag only after athena, apollo, and mac all run a build with the new wire.

## 7. Requirement adjustments (called out)

| # | Original | Adjusted | Why |
| --- | --- | --- | --- |
| **A1** | Non-sensitive attachments are **public**. | Non-sensitive attachments get **the bead store's audience**, which is public for `sase`. | Matches the industry norm (GitHub attachments follow repo visibility). It does the right thing for projects with private beads, and it makes pages consistent. |
| **A2** | Move public bytes into **`sase--beads`**. | Move them into a **dedicated public attachments sidecar**. | Keeps blobs out of a hot, fully cloned event-store repo. It isolates size, purge, and push-protection failures (§4). Access is the same as beads. |
| **A3** | Agents decide when a file is private, defaulting to public. | **SASE decides mechanically.** Agents may narrow to private; only humans widen. | Agents don't read whole files. Leaks are irreversible, and the observed leak vector (env dumps) is detectable by machine. |
| **A4** | (unstated) | **Attachments from `sase-1ck` stay private** unless explicitly published. Absent `visibility` means private. | Their authors attached them under a private-storage promise. |
| **A5** | Large files only via remote-machine support. | Agreed, and made explicit: **anything over 25 MiB is never public.** | GitHub limits, a lean public repo, and large blobs are the least likely to have been reviewed. |
| **A6** | (unstated) | **Private reasons never go on the public wire.** | A "contains a secret" flag on a public descriptor would point attackers straight at it. |
| **A7** | (out of scope) | **Reuse the core scanner in the agents-sidecar transcript and prompt-artifact publishers.** Track this as separate work, not inside this epic. | Those publishers are already leaking (§8). Attachments would otherwise be better guarded than the existing leak path. |

## 8. Side finding: credentials in already-public transcripts (urgent, separate)

A masked scan of the published `sase--agents` transcripts found credential-shaped strings
in **12 of 11,467** transcripts: an LLM-provider API key in 11 and a chat-bot token in 1.
Both came from environment dumps printed in command or test output. Neither value appears
in the sase tree, so they are not fixtures. The values were never printed during this
research. Specific variable names were reported to the user directly.

Recommended order:

1. **Rotate both credentials now.** Assume they are compromised. GitHub's partner program
   scans public repos and may already have notified the provider.
2. Enable secret scanning and push protection on the public sidecars. It is free for
   public repos.
3. Redact before publishing. Apply the §5.3 known-value and env-dump detectors in the
   transcript and prompt-artifact publishers (adjustment A7).
4. Only then scrub history, if you still want to. Rotation is what actually closes the
   exposure.

I did **not** file a public bead for this. The beads repo is public, and filing before
rotation would advertise live credentials. File it after rotation using `/sase_new_task`.

## 9. Risks and open questions

- **Image leaks outside rule 7.** A self-generated screenshot can still show a
  notification or a pasted token. Mitigations:
  - Agents render the SASE TUI, whose content is already public.
  - The echo is always visible.
  - `unpublish` exists.
  - An optional OCR pass could be added later if images become common. Not now.
- **False-private friction.** About 13% of today's cited paths classify private, mostly
  config files from the public dotfiles and stdlib sources. They are still readable by org
  members. If a pattern keeps misfiring, add a positive rule to core, such as "a deployed
  file whose chezmoi source is in a public repo". Don't add an agent override.
- **Repo growth.** Report logical versus physical bytes in `sase bead doctor`. Rotate to
  `sase--attachments-2` well before 5 GB; descriptors don't care.
- **Open question 1:** is the intended audience **org members only**? If so, private plus
  the base `read` permission already meets the goal with no leak risk. Public is justified
  by pages, zero-credential frontends, and non-member readers.
- **Open question 2:** should a **human on a TTY** attaching a desktop screenshot default
  to public (rule 7 as written), or should humans get the same provenance rule as agents?
  I lean public for humans. They chose the file, and the echo tells them where it went.

---

## 10. Recommended solution

**The rule.** An attachment is as visible as its bead unless SASE or its author marks it
private. SASE decides in core from provenance, a content scan, and file type, and
uncertainty resolves to private. Agents can only narrow visibility; humans can widen it.
Large files are never public.

**Immediate (before or independent of the epic).**

1. Rotate the two leaked credentials (§8). Then file the transcript-redaction bead.
2. Enable secret scanning and push protection on the public `sase--*` sidecars.
3. Optional, cheap: have `sase-1ck.5` name its role for the **private** store, so
   the plain `attachments` name is left for the public default. Nothing else in `sase-1ck`
   needs to change, because absent visibility already means private.

**Follow-up epic: public bead attachments** (after `sase-1ck` closes; beta flag
`public_bead_attachments`).

| Phase | Scope |
| --- | --- |
| 1 · `core_policy` (sase-core) | `visibility` on the descriptor wire (absent = private). `attachment_visibility_decision` (§5.2). A streaming secret scanner with known-value (Aho-Corasick), credential-pattern, and env-dump detectors. Placement takes visibility into account. Bindings and a pin bump. Tests: a decision-table matrix, and scanner fixtures that are **synthetic** (never real secrets). A one-time measurement over the published transcripts, recorded on the bead, showing it flags every known hit. |
| 2 · `provenance_cli` | Python provenance probe: worktree, tracked or ignored status, remote visibility through the inventory plus cached `gh` (fail-private), zones, mode bits, and run-start btime/mtime. `-V/--visibility` on every note verb and `attach`. Agent refusal for widening. Echo and JSON with local-only reasons. Config: `public_max_bytes`, `sensitive_patterns`, `publish_delay`. |
| 3 · `public_store` | A reserved public role that defaults to the beads sidecar's visibility. `sase repo init` creation with a consent prompt that says **PUBLIC**. `GitAttachmentStore` parameterized by role, with an extension-preserving public layout (after the camo spike). Per-store outbox. `GH013` becomes a permanent reroute to private. Two-home tests against local bare remotes. |
| 4 · `presentation` | `🌐`/`🔒` badges in `show`/`read`/JSON. Inline images and links on bead pages. A TUI modal chip with a toggle, and confirmation when widening. `attachment publish` (human, or agent via gate) and `unpublish`. |
| 5 · `lifecycle` | `sase bead doctor` rescans public objects and reports repo growth. The public purge/unpublish runbook. `publish_delay` outbox gating. |
| 6 · `ga` | Remove the flag. Docs: `docs/beads.md` visibility section and `docs/configuration.md`. The `sase_beads.md` and `/sase_new_task` guidance from §5.4 (edit the skill source only). Propose A7, reusing the scanner in the agents-sidecar publishers, as a follow-up task. |

**Acceptance.**

- A clean text log in the workspace publishes, is fetched on a second home, and renders
  inline on the page.
- The same log with an injected env dump, a secret-named variable's value, or a
  credential pattern goes private and shows the reason only locally.
- An agent asking for `-V public` on it is refused.
- A pre-epic descriptor never publishes implicitly.
- Anything over 25 MiB never touches the public store.
- A `GH013` rejection reroutes to private without blocking bead publication.
- Beads without attachments do no new work.

---

### Sources

- [GitHub Docs — Repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [GitHub Docs — About large files on GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [GitHub Changelog — Secret scanning and push protection enabled by default on new public repositories (2024-03-11)](https://github.blog/changelog/2024-03-11-secret-scanning-and-push-protection-are-enabled-by-default-on-new-public-repositories/)
- [GitHub Docs — Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection)
- [GitHub Docs — Secret scanning partner program](https://docs.github.com/code-security/secret-scanning/secret-scanning-partnership-program/secret-scanning-partner-program)
- [GitHub Changelog — Updated rate limits for unauthenticated requests (2025-05-08)](https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/)
- [GitHub Changelog — More secure private attachments (2023-05-08)](https://github.blog/changelog/2023-05-08-more-secure-private-attachments/)
- [GitHub Docs — About anonymized URLs (camo)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-anonymized-urls)
