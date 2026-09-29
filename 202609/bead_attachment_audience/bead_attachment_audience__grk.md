---
create_time: 2026-09-29
updated_time: 2026-09-29
status: research
researcher: grk
---

# Default project-wide access to bead attachments

- **Researcher:** grk (`research.n.grk`)
- **Date:** 2026-09-29
- **Question:** After `sase-1ck` closes, how should every person working on a SASE project get the non-sensitive files attached to bead notes by default? Is moving those bytes into the public `sase--beads` sidecar a good way to do it? How should agents mark a file private?
- **Depends on:** epic `sase-1ck` (Bead note attachments; all ten phases still `IN_PROGRESS`). This is a follow-up epic, not a new phase of `sase-1ck`, unless `sase-1ck.5` has not yet created `sase-org/sase--attachments` — in that case a small amendment to `.5` is cheaper than a migration. See §9.

**Sources:** `research:202609/bead_note_attachments/attachment_storage_and_access.md`; the consolidated `sase-1ck` research (`research:202609/bead_note_attachments/bead_note_attachments.md`); the approved plan `plan:202609/bead_note_attachments.md`; live `sase-1ck` bead; sase / sase-github / sase--beads trees in this workspace; `gh` against `sase-org`; GitHub Docs on large files, LFS, secret scanning, org permissions, and repository visibility.

## Recommended solution

Keep the `sase-1ck` byte topology. Change only **who can read the git tier**.

1. **Default store = a dedicated `attachments` sidecar whose GitHub visibility matches the beads sidecar.** For `sase-org/sase` that means **public** `sase-org/sase--attachments`. It stays a hidden bare `--filter=blob:none` clone at `~/.sase/projects/<key>/repos/attachments`. Readers fetch one blob on demand (git plumbing, or a digest-verified HTTPS GET of the raw object on a public remote). Workspaces never clone it.
2. **Do not put attachment bytes in `sase--beads`.** The beads sidecar is the hot event log (`issues.jsonl` is already 19 MiB; the pack is ~106 MiB and 128k objects). It is materialized into agent workspaces on demand and `auto_sync`s. Binaries there would tax every `sase bead` and every bead-claiming agent, make purge a rewrite of the evidence log, and mix two write patterns in one packfile.
3. **`--private` is an opt-in restriction below the bead's audience**, implemented as a second reserved sidecar (`attachments-private`, GitHub `--private`) plus `-L/--local-only` for "this machine only." Agents default to the shared store.
4. **Sensitivity is a placement policy, not an LLM vibe.** Path refusal, a hard coupling of `-S` to `--private`/`-L`, a cheap secret scan before any public upload, GitHub push protection on the public sidecar, and a short skill table for when agents must pass `--private`. Screenshots of terminals are the case scanners miss; the skill tells agents to use `--private` whenever the image might show a token.
5. **Large files stay on the origin machine.** Remote-machine dispatch is enough. rclone can remain the optional `sase-1ck.6` tier; this follow-up does not need it.

That is the same architecture `sase-1ck` already specified, with the default visibility flipped from "private git sidecar" to "git sidecar as readable as the bead." The product goal is right. The proposed store (public beads) is the wrong one.

---

## 1. What is already true

### 1.1 `sase-1ck` stores metadata in beads and bytes somewhere else

The approved plan and the storage note agree:

| Layer | Where | Who can read it today (as designed) |
| --- | --- | --- |
| Note prose + `@attachment:<name>` token | public `sase--beads` event | Anyone who can read beads |
| Descriptor `{name, sha256, size_bytes, mime_type, image?, origin?}` | same public event | Anyone who can read beads |
| Bytes ≤ 50 MiB | local CAS, then **private** `sase--attachments` (hidden bare partial clone) | GitHub credentials with access to that private repo |
| Bytes > 50 MiB | optional rclone remote (SFTP-to-athena or R2) | whoever has that remote's credentials |
| `-L/--local-only` | local CAS only | the writing machine |

Descriptors are **location-free**. A later epic can add, replace, or split stores without rewriting notes. That is the load-bearing `sase-1ck` choice, and this follow-up should keep it.

Nothing in that design has landed. All ten phases are `IN_PROGRESS`. `src/sase/bead/attachments/` is not on this checkout's master, and `gh repo view sase-org/sase--attachments` does not resolve. Creating the GitHub repo is a manual `sase repo init` step behind a default-**no** prompt.

### 1.2 Every existing SASE sidecar for this project is public

Live `gh` on 2026-09-29:

| Repo | Visibility | `diskUsage` |
| --- | --- | --- |
| `sase-org/sase` | PUBLIC | 2 757 626 KB (~2.6 GiB) |
| `sase-org/sase--beads` | PUBLIC | 93 624 KB (~91 MiB) |
| `sase-org/sase--agents` | PUBLIC | 169 435 KB |
| `sase-org/sase--plans` | PUBLIC | 78 927 KB |
| `sase-org/sase--research` | PUBLIC | 347 740 KB (~340 MiB) |

`sase-org` is on the **GitHub Free** plan, with `default_repository_permission: read` and a single member (`bbugyi200`). GitHub **internal** visibility (org/enterprise members only) is an Enterprise Cloud feature; it is not available here.

The GitHub workspace provider creates sidecars with a hardcoded `gh repo create … --public`. Tests in sase-github assert `--private` is never on that command. Config may *declare* `visibility: private` (agents documents this), but the create path does not yet pass `--private`. There is no collaborator-mirroring from the primary onto sidecars.

### 1.3 Beads is a hot metadata repo, cloned into working trees on demand

`sase/sase.yml` sets `beads.auto_clone: false` and `auto_sync: true`, with a comment that the sidecar materializes on demand in `sase bead` and in the agent-launch bead claim. A workspace that touches beads still pays for a **full** clone and then for every later fetch.

On this checkout the beads sidecar is:

- 7 518 files, working tree dominated by `issues.jsonl` (19 MiB) and per-bead event streams
- git pack **105.86 MiB**, **128 287** objects
- one existing binary, `assets/beads-directory-map.png` (1.2 MiB)
- not a partial clone

The original `sase-1ck` research counted the beads sidecar cloned into 35 of 47 workspaces. `auto_clone: false` removed the *up-front* tax; it did not remove the tax on any agent that claims a bead.

### 1.4 GitHub's git limits are why `sase-1ck` capped the git tier at 50 MiB

From GitHub Docs, *About large files on GitHub*:

- 50 MiB: warning on push
- 100 MiB: hard block for a normal git object
- 25 MiB: browser-upload cap (irrelevant for plumbing, relevant for "just put it in the repo" folklore)
- 2 GiB: hard cap per push
- Recommended repo size: under 1 GB, strongly under 5 GB

GitHub LFS raises the per-file cap (2 GB on Free) and gives the org **10 GiB** of LFS storage and bandwidth on Free. LFS objects are not removed by deleting the pointer; GitHub's own docs say a leaked LFS file is gone only when the repository is deleted. The consolidated `sase-1ck` research already rejected LFS for that reason. This follow-up should too.

### 1.5 `sase-1ck` already asked the visibility question

The consolidated research's open question 1:

> Should attachments default to **private**, even though every other sidecar, including the agents sidecar that already publishes prompt-cited files, is public? I recommend private: a published screenshot cannot be un-published.

The user is answering that question: **default shareable with everyone working on the project**, with an agent-facing private opt-in. The storage note is the other half of the answer as `sase-1ck` currently stands: other people see prose, the filename, and a 🔒 chip, and the bytes stay on Bryan's machines.

The agents sidecar already publishes content-addressed bytes at `files/objects/sha256/<xx>/<sha256>` in a **public** repo. That is the in-tree precedent for "git object store of files, public, not mixed into beads events."

### 1.6 Metadata on a public bead cannot be a secret

The storage note is explicit: filename, size, MIME type, image dimensions, SHA-256, and origin hostname all land in public beads. A published SHA-256 is a **confirmation oracle** for a guessed file. Path refusal (`~/.ssh`, `.env`, `*.pem`, …) guards the bytes, not the names.

That constraint survives any store choice. A `--private` flag that still writes `{name, sha256, size}` onto a public `NoteAppended` event is "not on the internet as a download," not "this file is confidential."

---

## 2. Critique of the proposed plan

The proposed implementation: *move non-sensitive attachments from `sase--attachments` into public `sase--beads`.*

The **goal** is right. The **store** is the one `sase-1ck` spent its design effort isolating.

### 2.1 The goal and the store are different problems

"All users working on a SASE project can read non-sensitive attachments" is an **audience** requirement. "Put the bytes in `sase--beads`" is a **packaging** choice that happens to make the audience "anyone on the internet," because `sase--beads` is public.

Those line up for this one project (`sase` is public OSS). They do not line up for SASE as a product:

- A **private** primary whose beads sidecar was left at the default `visibility: public` would leak every "non-sensitive" screenshot onto the internet if those bytes lived in beads.
- A **private** beads sidecar already has the right audience (people who can clone beads). Copying bytes into it would still bloat the event clone.
- GitHub does not grant "collaborator on the primary" access to a sibling private sidecar. There is no mirroring code. Org `default_repository_permission: read` only helps **org members**, and OSS contributors are usually not members.

The audience that matches the user's words is: **anyone who can already read the bead.** For public beads that is the internet. For private beads that is the bead's GitHub readers. Attachment bytes should inherit that audience. They should not be stuffed into the bead store to piggy-back on its ACL.

### 2.2 Beads is the worst git repo we have for binaries

Putting content-addressed blobs next to `issues.jsonl` and thousands of event streams would:

- **Pull every new screenshot on every bead sync.** `auto_sync: true` plus on-demand materialization means every agent that claims a bead fetches the whole history of attachment blobs, including ones they will never open. The `sase-1ck` git tier is a promisor clone that fetches **one** blob.
- **Make purge a rewrite of the evidence log.** `sase-1ck` purge is a tombstone plus a documented `git filter-repo` of an append-only attachments repo. Doing that to beads means rewriting 128k objects and every machine's beads clone, and it races the already-hot event publisher.
- **Mix write frequencies.** Notes are small, frequent, rebase-sensitive JSONL. Screenshots are large, write-once, non-diffable blobs. Git packfiles and `git gc` hate that mix. Research is already ~340 MiB of mostly text-plus-media; it is the cautionary sibling, and it is *not* on the `sase bead` hot path.
- **Hit GitHub's repo-health guidance on the wrong repo.** Beads is 91 MiB of metadata today. A year of TUI screenshots at a few megabytes each is how a metadata repo becomes a binary dump. The primary is already ~2.6 GiB. Beads should stay the small one.
- **Break the "beads without attachments pay zero" rule.** The plan requires `show`/`read` of a bead with no attachments to import neither git nor the attachment stack. Bytes in the same clone couple those paths.
- **Give bead pages links "for free"** — the one real benefit. A public attachments sidecar gives the same links (`raw.githubusercontent.com/sase-org/sase--attachments/…/files/objects/sha256/…`) without the clone tax. Relative links inside `pages/sase-ab/README.md` are not worth 50 MiB screenshots in the event repo.

The consolidated research already rejected this option in its alternatives table: "A hot, public repo cloned into 35 workspaces. Purging means rewriting 18k+ commits." The commit count is higher now. The argument is the same.

### 2.3 "Non-sensitive" as a post-hoc split of one git history does not work

If `sase-1ck` creates a **private** `sase--attachments` and anyone attaches a file, flipping that repo to public publishes **all** historical blobs, including ones that were private-by-default on purpose. GitHub's own secret-leak docs: deleting a file, or even `filter-repo`, does not unsay a public clone that already happened.

A follow-up that "moves non-sensitive files into beads" has the same one-way door, plus a classification problem: every historical object has to be labeled after the fact by an agent that did not have a `--private` flag when it wrote.

Keep one-way doors in front of the upload, not after.

### 2.4 Private-by-default as `sase-1ck` specified it fails the new product goal

The storage note's matrix is honest: a collaborator without access to `sase--attachments` sees a 🔒 chip. `sase-org` has one member. "Available on every machine" currently means Bryan's machines.

For a public OSS project that is a product defect. A drive-by contributor reading `https://github.com/sase-org/sase--beads/blob/main/pages/sase-1ck/README.md` should be able to open the screenshot the note cites. GitHub issues work that way: attachments on a public issue are public. Jira and GitLab inherit issue security onto attachments. SASE should too.

The `sase-1ck.5` default-**no** creation prompt makes the defect worse: until someone answers `y`, every attachment is local-only and the write echo says so. Default-shared access requires the shared store to exist without heroics.

### 2.5 Verdict on the idea

| Piece | Verdict |
| --- | --- |
| "People working on the project should see non-sensitive attachments by default" | Yes. Match the bead's audience. |
| "Agents default public, with an explicit private opt-in" | Yes, with mechanical backstops. See §5. |
| "Large files may live only on the origin machine / remote dispatch" | Yes. Simplifies this epic. |
| "Implement default-shared by putting bytes in `sase--beads`" | No. Wrong repo, wrong clone, wrong purge, wrong mix of writes. |
| "Keep a private sidecar for the rest" | Yes, as a *second* store, created lazily. |

---

## 3. Three audiences

Talking about "public" vs "private" files collapses two axes. Use three audiences:

| Audience | GitHub mechanism | Who that is on `sase-org/sase` today | Who that is on a private-company SASE project |
| --- | --- | --- | --- |
| **Bead readers** | Same visibility as `sase--beads` | Anyone on the internet | Collaborators who can clone beads |
| **Restricted** | A private sibling repo | Org members (`default_repository_permission: read`) and anyone explicitly granted | Same, plus any mirroring we later add |
| **This machine** | `-L`, never uploaded | Athena / apollo / mac as origin | The writing host |

**Adjustment R1.** Default audience is **bead readers**, not "the internet" and not "the writer's machines." On this project those happen to be the internet. On a project whose beads sidecar is private, default attachments stay private with no extra flag.

`--private` drops one level (bead readers → restricted). `-L` drops to this machine. There is no flag that makes an attachment *more* public than its bead.

GitHub Free has no "internal / org-only" visibility. Restricted = a private repo. Org members already get `read` on every org repo; outside collaborators on the primary do **not**. If SASE later wants "collaborators on the primary can read restricted attachments," that is a GitHub-permission sync feature, not a reason to put binaries in beads.

---

## 4. How agents (and the product) should decide "private"

Agents will get this wrong if the only control is a prompt that says "please think about secrets." Default-shared is acceptable only with **mechanical** gates in front of the public upload.

### 4.1 Placement rules (core policy, not a suggestion)

1. **Default: bead-reader store** (public attachments sidecar when beads are public).
2. **Sensitive-path hit → refuse** unless `-S/--allow-sensitive`. Unchanged from `sase-1ck`.
3. **`-S` requires `--private` or `-L`.** A sensitive path may never land in the bead-reader store. This is the important coupling `sase-1ck` does not have, because `sase-1ck` assumed the git tier was already private.
4. **Secret scan before public `put`.** High-confidence token patterns (the same class GitHub push protection uses: AWS keys, GitHub PATs, Slack tokens, private-key PEM armor, `-----BEGIN … PRIVATE KEY-----`). A hit fails the command with "this looks like a secret; rerun with `--private` or `-L`." False positives on public fixtures should be rare at this confidence; a `--force-public` bypass is *not* recommended in v1.
5. **`--private`** writes to the private sidecar (creating it on first use, default-no consent, same tone as today's agents-sidecar prompt). If that sidecar does not exist and the user declined creation, fall through to `-L` with an honest badge, or fail closed if `require_upload` is set.
6. **`-L/--local-only`** never leaves the machine. Use it for true secrets that should not sit in *any* git history, public or private.
7. Write echo always names **audience** (`public sase-org/sase--attachments` / `private sase-org/sase--attachments-private` / `local-only on athena`).

### 4.2 Skill table for agents (the LLM-facing rule)

Ship this as the attachments paragraph in the beads skill, not as a vibe:

Use `--private` when any of the following is true:

- The file may contain credentials, tokens, cookies, session dumps, private keys, or `.env` contents.
- The file is customer data, PII, or an unpublished security finding.
- The file is a screenshot or recording of a terminal, browser, or TUI that might show a secret (scanners will not see pixels).
- The user asked for privacy, or the note is about credentials / auth failures / production data.
- You passed `-S`.

Use `-L` when the file must not be in any remote git history (the credential itself, a wallet, a customer export).

Otherwise use the default store. Screenshots of failing tests, TUI goldens, logs with no secrets, traces, and JSON fixtures are the default-shared corpus — that is what the 90 cited evidence paths in the `sase-1ck` research actually were.

If unsure about a log or a terminal screenshot, `--private`.

### 4.3 What we should not do

- **Do not ask the model to classify sensitivity as a required flag on every attach.** Default-shared plus mechanical refusal is how GitHub issues work; an extra question on every `login.png` will be ignored or overused.
- **Do not OCR every image in v1.** Terminal screenshots are handled by the skill rule above. OCR is a later hardening if the corpus shows leaks.
- **Do not treat `--private` as cryptographic confidentiality** while the public event still carries `sha256`. See R7.
- **Do not auto-promote `-L` objects to public.** `attachment push` without `--private` should refuse if the secret scan or sensitive-path bit is set.

### 4.4 GitHub as a backstop, not the gate

Push protection is on by default for **public** repositories and is free. That is a free last line for the public attachments sidecar. It does not catch screenshots, custom tokens, or `.env` values that are not in the partner-pattern list. Secret scanning of *private* repos is a paid GitHub Secret Protection feature; do not depend on it. The in-process scan in §4.1 is the real gate.

A leaked secret in a public git repo is not un-leaked by `purge` or `filter-repo`. Rotate first. Document that next to `--private`.

---

## 5. Requirement adjustments (explicit)

| # | As requested / as `sase-1ck` specified | Adjusted to | Why |
| --- | --- | --- | --- |
| **R1** | Default = files in public `sase--beads`; `sase-1ck` default = private sidecar | Default audience = **bead readers**. Bytes live in a dedicated `attachments` sidecar whose GitHub visibility **matches beads**. | Audience is the actual requirement. Store is independent. Matching beads is correct for both OSS and private projects. |
| **R2** | Implement sharing by moving bytes into `sase--beads` | Bytes stay out of beads. Dedicated hidden partial clone, same layout `sase-1ck` already chose (`files/objects/sha256/…`). | Clone tax, purge, packfile mix, `auto_sync`. See §2.2. |
| **R3** | Agents can mark an attachment private; default public | `--private` → reserved **private** sidecar, created lazily. `-L` → this machine. No `--public` override that exceeds the bead. | Two GitHub visibilities are two repos. Flags below the bead, never above. |
| **R4** | (new) | `-S/--allow-sensitive` is illegal without `--private` or `-L`. | `sase-1ck` could allow `-S` into a private git tier. A public default cannot. |
| **R5** | (new) | High-confidence secret scan before any **bead-reader** upload. | Agents miss `.env` bodies and PEM files with unusual names. Path policy is not enough. |
| **R6** | Large files via SASE remote-machine support is enough | Git tier stays ≤ 50 MiB. Above that: local CAS + `⚠ only on <origin>` + dispatch to that machine. rclone remains optional `sase-1ck.6`, out of scope here. | Matches the user's simplification. Avoids R2 credentials as a sharing mechanism. |
| **R7** | (new, wire) | Restricted attachments either **omit `sha256` from the public event** (`visibility: "private"` stub) or docs state clearly that `--private` is not confidential. Prefer omitting the hash if `sase-1ck.3` has not landed; otherwise a follow-up optional field. | Public SHA-256 of a "private" file is a confirmation oracle. |
| **R8** | Move files out of a private sidecar after `sase-1ck` | **Never flip** a private attachments repo to public after it has objects. If `sase-1ck.5` already created a private repo with files, leave it as the restricted store and add a **new** public sidecar for the default. | Git history is a one-way door. |
| **R9** | (implementation) | sase-github must grow `gh repo create --private` for the restricted sidecar. The **default** (public) sidecar works with today's hardcoded `--public`. | Today's tests assert `--private` is never passed. `sase-1ck.5`'s private-only design is the expensive GitHub change; a public default is the cheap one. |
| **R10** | `sase-1ck.9` bead pages render `🔒 name (private attachment)` | Bead-reader attachments render as **links** (GitHub blob/raw URL, digest in the query or path). Restricted ones keep the 🔒 chip. | This is the OSS payoff. Pages become evidence records. |
| **R11** | `sase-1ck.5` creates the sidecar behind default-**no** | The **bead-reader** sidecar is created with default-**yes** (or automatically on first attach, with a one-line visibility echo). The **restricted** sidecar stays default-no. | Default access cannot depend on a prompt nobody answers. |
| **R12** | "Users working on a sase project" | Operational definition: **readers of the beads sidecar.** Org membership, outside-collaborator grants, and local `sase project enable` are all imperfect proxies. | If you can read the note, you can read its default attachments. |

---

## 6. Alternatives considered

| Approach | Keep? | Notes |
| --- | --- | --- |
| **A. Bytes in `sase--beads`** (user's plan) | No | §2.2. The one benefit (page links, inherited ACL) is available from a public attachments sidecar. |
| **B. Public `sase--attachments`, hidden partial clone, default** | **Yes, the default store** | Same plumbing `sase-1ck.5` already specified. Visibility matches beads. Anonymous raw GET + sha256 verify works for OSS readers with no git creds. |
| **C. Keep `sase-1ck` private-only sidecar; auto-grant GitHub access** | No as the default | Fails OSS (contributors are not org members). Requires collaborator mirroring that does not exist. Still a 🔒 on public bead pages. Fine as the *restricted* store. |
| **D. Two git sidecars** (public default + private opt-in) | **Yes** | Matches `--private`. Private repo created lazily. Location-free descriptors already allow two stores. |
| **E. One private sidecar + encryption for "public" objects** | No | Key distribution, and "encrypted but listed in a private repo" does not help OSS readers. |
| **F. GitHub LFS on beads or on attachments** | No | 10 GiB Free quota, purge ≈ delete repo, extra `git-lfs` binary on every machine. `sase-1ck` already rejected this. |
| **G. GitHub Releases as the blob store** | No | Fine for a few large artifacts; clumsy as a content-addressed CAS of thousands of screenshots. ACL is still per-repo. |
| **H. Public R2/S3 bucket as the default** | No for v1 | Extra credentials, extra product surface. GitHub already hosts sidecars. Keep R2 as the optional large tier. |
| **I. Inherit GitHub issue-attachment semantics only** (no `--private`) | Tempting | GitHub issues have no "private file on a public issue." We could say "don't attach secrets to public beads; use `-L`." That is simpler, and might be enough for v1 if we want to defer the private sidecar. I still recommend **D**, because OSS projects *do* have "not a secret, not for the internet" screenshots (WIP UI, log with usernames). Make the private sidecar lazy so projects that never use `--private` never create it. |
| **J. Amend `sase-1ck.5` now** rather than a follow-up epic | **Yes if `.5` has not created the GitHub repo** | The repo does not exist today. Flipping the default visibility in `.5` is a config/prompt change plus sase-github `--private` support for the *restricted* path. A post-hoc migration is strictly more work. See §9. |

Partial clone vs full clone is not optional. A public attachments sidecar that was `auto_clone: true` into workspaces would recreate the beads-bloat problem. The hidden `--filter=blob:none` clone is the feature.

On a **public** remote, reads do not even need git: `GET https://raw.githubusercontent.com/<owner>/<repo>/<rev>/files/objects/sha256/<xx>/<sha256>` then verify. That is a simpler `BlobStore.get` for the bead-reader tier and is how bead pages can link. Writes still use `hash-object` / `commit-tree` / `push` as specified.

---

## 7. Recommended design (follow-up epic)

### 7.1 Stores (ordered)

```text
local CAS          ~/.sase/attachments/objects/sha256/…     always
bead-reader git    <owner>/<project>--attachments           default; visibility = beads
restricted git     <owner>/<project>--attachments-private   --private; visibility = private
this machine       (no remote)                              -L, or no store configured
```

Large objects (> `git_max_bytes`, default 50 MiB): stay in the local CAS, badge `⚠ only on <origin> · dispatch to that machine`. If `sase-1ck.6` has already landed rclone, it remains an optional extra tier; this epic does not require it.

Placement (core), extending `sase-1ck`'s `attachment_placement`:

- size > git cap and no large tier → require `-L` or fail
- `-L` → local only
- `--private` or `-S` → restricted git (and never bead-reader)
- secret-scan hit → refuse bead-reader; tell the user to pass `--private` or `-L`
- else → bead-reader git

The event still does not record a store location. `origin` stays. Add `visibility: "shared" | "restricted" | "local"` on the descriptor so renderers and pages do not have to guess. If R7 lands, restricted descriptors omit `sha256` on the public wire and the restricted sidecar holds `bead-id/name → sha256`.

### 7.2 Sidecar roles

- Add `attachments` to `RESERVED_SIDECAR_ROLES` (already in the `sase-1ck.5` spec) with **default visibility copied from beads** (today: public). `auto_clone: false`. Never materialized into workspaces. Hidden bare partial clone.
- Add `attachments-private` (or a single role with a `private` twin repo suffix `--attachments-private`) created only on first `--private` attach, default-no consent, hardcoded GitHub `--private`.
- `sase repo init` offers the bead-reader sidecar with default-**yes**, naming visibility in the prompt the way the agents sidecar already names it.
- Phases still never create GitHub repos from tests; local bare remotes with `uploadpack.allowFilter=true`.

sase-github work: `create_github_sdd_repo` grows a visibility argument. The current `--public`-only path is enough for the default sidecar and is a bug for the restricted one.

### 7.3 CLI delta on top of `sase-1ck`

```text
sase bead attach … [--private] [-L] [-S]
sase bead note|close -n|update -n|+1 -n … [--private] [-L] [-S]
```

`--private` and `-L` are mutually exclusive. `-S` without one of them is a hard error. The write echo includes audience. `attachment list` / JSON grow a `visibility` field. `attachment push` without `--private` will not promote a restricted or scan-positive object onto the bead-reader store.

### 7.4 Pages, doctor, purge

- Bead pages: shared attachments become Markdown links to the public blob (and a raw URL). Restricted: keep `🔒 name · mime · size (restricted attachment)`. Local-only: `⚠ only on <origin>`.
- Doctor: missing bead-reader store, declined private-store creation with queued `--private` objects, scan-positive objects sitting in the outbox, `🔒 no access` as a distinct badge from `✕ unavailable offline` (the storage note already flagged this gap).
- Purge: tombstone on the store that actually holds the bytes. `filter-repo` docs point at the **attachments** repo, never beads.

### 7.5 Skill / docs

- Beads skill: the table in §4.2.
- `docs/beads.md` Attachments: one paragraph on audience ("as readable as the bead, unless `--private` or `-L`").
- Mixed-fleet: enable default-shared only after every machine that writes notes runs a build that knows the new `visibility` field (same discipline as `sase-1ck`'s `core_wire` gate).

### 7.6 Suggested phases for the follow-up epic

1. **Visibility policy in core** — `visibility` on the descriptor, `-S` coupling, placement, secret-scan hook shape. Pin bump.
2. **Public attachments sidecar as the default git tier** — reserved role, default-yes init, GitHub public create (already works), lazy fetch, page links, doctor `no access` vs `offline`.
3. **Restricted sidecar + `--private`** — sase-github `--private` create, lazy init, skill text, echo, push guards.
4. **Scan + docs + GA** — in-process high-confidence scan, skill/docs, acceptance: writer on athena, reader with no special GitHub grant on another machine, public page link opens the screenshot.

If `sase-1ck.5` is re-scoped per §9, phases 1–2 collapse into that phase and this epic starts at `--private`.

---

## 8. Timing relative to `sase-1ck`

`sase-1ck` is the wrong epic to *abandon*. Grammar, CAS, wire, CLI, TUI, and purge are all still required. The follow-up is about **audience**.

`sase-org/sase--attachments` **does not exist yet**. That makes waiting until `sase-1ck` closes slightly wasteful:

- `.5` will teach sase-github to create a **private** repo, write default-no consent, and render 🔒 on every page.
- This follow-up would then either flip that repo to public (unsafe once objects exist) or add a second public repo and migrate.

**Adjustment R13 (process).** If `.5` has not yet run `gh repo create` for attachments, change `.5`'s default visibility to **match beads** (public here), keep the hidden partial clone, and leave `--private` + the private twin to the follow-up. That is a small delta on a phase that already has to invent the sidecar role. If `.5` has already created a private repo **and** objects have been pushed, do not change its visibility; add `--attachments` public as a new store and keep the existing repo as restricted (R8).

I would take the amend-`.5` path if the land agent has not created the GitHub repo. I would not reopen grammar, CAS, images, or TUI.

---

## 9. Risks

- **Default-shared is a one-way door.** Mechanical scan + `-S` coupling + skill table are the mitigation. Purge does not unsay a public clone. Rotate leaked credentials.
- **Screenshots of secrets.** Text scanners will not see them. The skill rule is the v1 control. A later optional "image attached to a note that mentions token/password" hint could be added if the corpus shows misses; do not block v1 on OCR.
- **Restricted metadata leak.** Without R7, `--private` still publishes name and hash. Prefer R7.
- **Two sidecars to operate.** Lazy-create the private one. Projects that never pass `--private` have one public attachments repo and are done.
- **GitHub Free quotas.** Public git objects do not consume LFS quota. A public attachments repo that grows past ~5 GB needs rotation (new store, location-free descriptors make that possible) or the large-file-stays-local rule.
- **Private-company default.** If someone runs SASE against a private primary but leaves beads public (today's sidecar default is public), default-shared attachments would also be public. That is a beads-visibility problem as much as an attachments problem. Mention in docs: set `repos.sidecar.builtin.beads.visibility: private` on private projects, and attachments will follow.
- **No collaborator sync.** Restricted attachments are visible to org members (`read` base permission) and to people granted on that repo. Outside collaborators on the primary will still see 🔒. Document it; do not pretend beads-in-repo would have saved them on a private project (they would need beads access too).
- **Mixed fleet.** An old writer that does not know `visibility` must not strip it from `issues.jsonl`. Same projection rule as `sase-1ck`.

---

## 10. Direct answers

**Is "everyone working on the project can read non-sensitive attachments" a good idea?** Yes. A bead that cites a screenshot the reader cannot open is the failure `sase-1ck` exists to remove, and private-by-default reintroduces it for everyone who is not Bryan.

**Would I implement it by moving bytes into `sase--beads`?** No. I would flip the **default git-tier visibility** of the dedicated attachments sidecar to match beads, keep the hidden partial clone, add `--private` as a lazy private twin, and leave large files on the origin machine.

**How should agents decide private?** They should not, mostly. Default shared. Mechanical path + secret-scan gates. `-S` forces `--private`/`-L`. A ten-line skill table covers terminal screenshots and "if unsure, `--private`."

**What would I change in the request?** R1–R13 above. The important three: (1) audience = bead readers, not "files live in beads"; (2) `-S` cannot target the public store; (3) do not flip a private repo to public after it has objects — amend `sase-1ck.5` if the GitHub repo does not exist yet, otherwise add a new public sidecar.
