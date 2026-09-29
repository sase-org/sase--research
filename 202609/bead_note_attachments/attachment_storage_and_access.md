---
create_time: 2026-09-29
updated_time: 2026-09-29
status: research
---

# Bead Note Attachments: Where The Bytes Live, And Who Can Read Them

**Question:** Epic `sase-1ck` adds `@<path>` file attachments to bead notes. Where will
they be stored — in the beads sidecar? And will other users on other machines who work on
the same SASE projects have access to them?

**Sources:** the `sase-1ck` bead and its approved plan
(`plan:202609/bead_note_attachments.md`), the consolidated research report
(`research:202609/bead_note_attachments/bead_note_attachments.md`), the sase code at
`9b29def73c`, and live `gh` checks of the `sase-org` organization.

## Short answer

|                                                 | Answer                                                                                                                                                                                                                                                              |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **In the beads sidecar?**                       | **Only the metadata.** The note text (holding an `@attachment:<name>` token) and a small descriptor go into the beads event store. **The bytes never do**: `sase--beads` is public and is cloned into most workspaces.                                              |
| **Where do the bytes go?**                      | A local content-addressed store (CAS) on the writing machine, then a **new private sidecar, `sase-org/sase--attachments`**, for files up to 50 MiB. An optional **rclone store** takes larger files.                                                               |
| **Can other users on other machines read them?** | **Only if they can authenticate to those private stores.** In practice today, that means your own machines only. Anyone else sees the prose, the filename, and a 🔒 chip, but not the file. The "available on every machine" promise really means "on every machine with access." |

## The storage map

```text
sase bead note sase-ab "Crash after login @./login.png"
   │
   ├─ PUBLIC   sase-org/sase--beads  ← note text + descriptor
   │           {name, sha256, size_bytes, mime_type, image{w,h}, origin: "athena"}
   │
   └─ BYTES  (tried in order; the descriptor never names a location)
      ① local CAS      ~/.sase/attachments/objects/sha256/<xx>/<sha256>   always, written first
      ② git tier       sase-org/sase--attachments  (PRIVATE)              ≤ 50 MiB
                       as a hidden bare partial clone at ~/.sase/projects/<key>/repos/attachments
      ③ large tier     bead.attachments.large_store → an rclone remote    ≤ 2 GiB (optional)
                       (SFTP to athena over the tailnet, or Cloudflare R2)
      ④ -L local-only  stays in ① only, shown as "⚠ only on athena"
```

- **Readers fetch lazily and verify every digest.** Files up to 25 MiB
  (`auto_fetch_max_bytes`) download on `show` or `read`. Larger files show
  `⇣ not downloaded` until you run `attachment path` or pass `-d`.
- **The attachments sidecar is never cloned into workspaces.** It exists only as a
  machine-level bare `--filter=blob:none` clone, so a read fetches exactly one blob.
- **Uploads happen before the bead store is published.** In the normal case, no other
  machine sees a note before its bytes. If an upload fails, the object waits in the
  outbox and the note shows `⇡ pending upload (athena)`.

## Who sees what

| Reader                                                    | Prose | Descriptor     | Bytes ≤ 50 MiB           | Bytes > 50 MiB                        |
| --------------------------------------------------------- | :---: | :------------: | :----------------------: | :-----------------------------------: |
| You, on athena, apollo, or mac                            |  ✅   |       ✅       | ✅ lazy fetch            | ✅ if `rclone.conf` is set up on that machine |
| A collaborator with read access to `sase--attachments`    |  ✅   |       ✅       | ✅                       | only with credentials for the rclone remote   |
| Anyone else (the public `sase--beads` repo, bead pages)   |  ✅   | ✅ as a 🔒 chip |            ❌            |                  ❌                   |
| Any reader, for a `-L` or never-uploaded attachment        |  ✅   |       ✅       | ❌ `⚠ only on <origin>`  |       ❌                              |

**For another person, access is purely a GitHub (and rclone) permission.** The sidecar
role is declared in the checked-in `sase/sase.yml`, so a collaborator's SASE picks up the
configuration automatically. The hidden clone authenticates with their own git
credentials.

## What is true today

1. **Nothing has landed yet.** All ten phases are `IN_PROGRESS`. `src/sase/bead/attachments/`
   does not exist on `master`, and `sase-org/sase--attachments` does not exist on GitHub.
   Creating it is a **manual `sase repo init` step** behind a prompt that defaults to "no".
   Until a shared store exists, every attachment is local-only, and the write echo says so
   each time.
2. **"Other users" is currently an empty set.** `sase-org` has exactly one member,
   `bbugyi200`, who is also the only collaborator on `sase--beads`. So "available on every
   machine" means your three machines.

## Caveats before you invite anyone

- **Metadata is public.** The filename, size, MIME type, image dimensions, SHA-256, and
  origin hostname all land in the public beads repo. A published SHA-256 also lets anyone
  **confirm a guessed file**. Sensitive-path refusal (`~/.ssh`, `.env`, `*.pem`, …) guards
  the bytes, not the names.
- **The large tier is set up per machine.** With the recommended SFTP-to-athena remote, a
  collaborator also needs a tailnet invite and an SSH account on athena. R2 with scoped
  keys is the more shareable choice.
- **Purge is not un-share.** `attachment purge` removes the object from the tip and writes
  a tombstone, but git history keeps the blob until a manual `git filter-repo`. Any reader
  who already fetched the file keeps a copy in their CAS.
- **Gap: the plan has no "no access" state.** A reader without GitHub access falls into
  `✕ unavailable offline`, which is misleading. A writer without push access would queue
  the object in the outbox forever as `⇡ pending upload`. A distinct
  `🔒 no access (sase-org/sase--attachments)` badge, plus a doctor finding, would fit in
  phase 5 (`sase-1ck.5`, `shared_store`).

## To share attachments with a collaborator

1. Run `sase repo init` and accept creation of the private `sase-org/sase--attachments`
   repo.
2. Grant the collaborator **read** access to that repo, or **write** if they will attach
   files.
3. For files over 50 MiB, give them scoped R2 credentials, or a tailnet invite plus an
   SFTP account.
4. Make sure every machine runs a build that includes `core_wire` before the
   `bead_note_attachments` flag is enabled. This is the plan's mixed-fleet rule.
