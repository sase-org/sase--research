# Public-by-default bead attachments without turning the bead store into a blob store

**Research date:** 2026-09-29  
**Researcher:** cdx  
**Decision target:** the follow-on epic planned after `sase-1ck`

## Executive judgment

The product goal is good: evidence attached to a shared bead should normally be
available to everyone who can work on that bead. The proposed mechanism—putting
non-sensitive bytes into the public `sase--beads` repository—is not.

I recommend preserving the architecture that `sase-1ck` is introducing: bead events
contain descriptors and attachment bytes live behind a content-addressed store seam.
Add two remote stores behind that seam:

1. a dedicated **public attachment sidecar** for deliberately public, reasonably small
   files; and
2. a **restricted attachment sidecar** for files visible only to explicitly authorized
   project collaborators.

Do not put either class of bytes in `sase--beads`. Its ordinary clone is currently
about 106 MiB with 18,292 commits and 128,287 Git objects, and it is the hot repository
for bead mutation and projection. Adding immutable binaries there would make every bead
reader and writer pay storage, fetch, maintenance, and history-rewrite costs unrelated
to bead state. A dedicated blob sidecar can remain a bare `--filter=blob:none` partial
clone and fetch one object lazily, which is exactly the shape the active epic already
plans.

The more important change is policy. Do not ask software to decide whether a file is
simply “sensitive” and treat a negative answer as permission to publish it. Secret
scanners detect some credentials; they do not prove that a screenshot, log, customer
record, licensed file, vulnerability detail, or internal hostname is suitable for the
world. Model the decision as an **audience** (`public` or `restricted`), make it durable
on the attachment descriptor, and make `auto` the default policy:

- confidently public provenance may route to the public store;
- known-risk paths or content force restricted storage or refusal;
- ambiguous content routes to restricted storage;
- an agent can request `--private` at creation time; and
- publishing an existing restricted attachment is a separate, explicit, audited
  declassification action.

This is a justified adjustment to the proposed “public unless detected sensitive”
requirement. The desired user outcome remains: non-sensitive evidence is shared by
default. The adjusted safety rule is that lack of a detector hit is not itself proof
that the evidence is public.

## Scope and sources

I reviewed the following project context through SASE's audited interfaces:

- `research:202609/bead_note_attachments/attachment_storage_and_access.md`;
- `bead:sase-1ck`;
- `plan:202609/bead_note_attachments.md`; and
- `research:202609/bead_note_attachments/bead_note_attachments.md`.

At the time of review, `sase-1ck` and all ten of its phase beads were in progress in the
current bead store. The follow-on epic should therefore recheck the landed wire and
store contracts rather than assuming every planned detail landed unchanged.

I also inspected the current SASE and sase-core source, SASE sidecar configuration and
remote-machine documentation, and the materialized `sase--beads` repository. Relevant
observations are included below. External claims use primary or authoritative sources:

- [GitHub repository visibility](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories)
- [GitHub repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [GitHub sensitive-data removal](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [GitHub secret-scanning detection scope](https://docs.github.com/en/code-security/reference/secret-security/secret-scanning-scope)
- [Git partial clone](https://git-scm.com/docs/partial-clone)
- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [FIRST Traffic Light Protocol 2.0](https://www.first.org/tlp/)

## What `sase-1ck` is building

The approved epic has several strong design choices that the follow-on should retain:

- A bead note stores readable `@attachment:<name>` tokens plus a descriptor manifest.
- Attachment bytes never enter bead events or `issues.jsonl`.
- Identity is content-addressed with SHA-256.
- The descriptor does not encode a store location. Placement is resolved from policy
  and configuration, so storage can change without rewriting a note.
- A local CAS is always written before the note event.
- The planned shared Git store is a hidden bare partial clone, not a workspace checkout.
- Readers fetch lazily and verify the digest.
- Large files can use an optional rclone backend.
- Path rules refuse obvious credential files unless the caller deliberately overrides
  the refusal.
- Public bead pages currently plan to show only metadata for private attachments.

Those choices provide the seam needed for public sharing. The follow-on does not need to
move the byte layer into the bead repository; it needs to add an audience dimension to
the descriptor and store-selection policy.

There are also four properties of the current plan that must change if public storage
is introduced:

1. The descriptor is presently `{name, sha256, size_bytes, mime_type, image?, origin?}`
   and is explicitly as public as the bead. That leaks a private attachment's filename,
   exact size, media type, origin hostname, and content hash.
2. The planned `-S/--allow-sensitive` override controls path refusal, not audience. If
   public storage becomes the default, `-S` could accidentally authorize publication
   of the very file the guard identified.
3. The planned upload outbox permits a bead event to become visible before its bytes.
   That is honest when shown as `pending_upload`, but it does not satisfy “all users can
   access shared attachments by default.”
4. `attachment push` currently mixes two different acts: making local bytes remotely
   available and potentially changing their audience. Availability and declassification
   must not share a command or an implicit fallback.

## The key semantic distinction: project access is not necessarily public access

GitHub defines a public repository as accessible to everyone on the internet, while a
private repository is limited to explicitly authorized people and some organization
members. Therefore, publishing into `sase--beads` does not mean “all SASE users working
on this project”; it means “the world, including crawlers, mirrors, and future forks.”

This matters because “non-sensitive” is weaker than “approved for unlimited public
release.” FIRST's TLP vocabulary is useful here: `TLP:CLEAR` is information with minimal
or no foreseeable misuse risk that may be shared with the world; `TLP:GREEN` is limited
to a community and is not appropriate for public channels. SASE does not need to adopt
TLP labels, but it should adopt the same conceptual boundary.

I would define the product terms as follows:

| Term | Meaning |
| --- | --- |
| **public** | Anyone who can reach the public backing store may obtain the bytes. Treat as irreversible publication. |
| **restricted** | Only principals authorized for the project's restricted attachment store may obtain the bytes. This is not “only the author.” |
| **local-only** | The bytes are not in any remote store. This is an availability state, not an audience. |
| **cached / remote / pending / unavailable** | Other availability states, orthogonal to audience. |

Using `restricted` internally avoids implying encryption or sole-user privacy. The CLI
can still offer the natural `--private` spelling as an alias.

## Critique of putting bytes in `sase--beads`

### 1. It couples the hottest metadata path to unbounded binary growth

The materialized bead sidecar measured during this research has:

| Metric | Current value |
| --- | ---: |
| Commits | 18,292 |
| Git objects | 128,287 |
| Packed `.git` size | 105.84 MiB |
| Working-tree files | 7,518 |
| `issues.jsonl` at `HEAD` | about 19.1 MiB |

The clone has no `extensions.partialClone` or `remote.origin.partialCloneFilter`
configuration; it is an ordinary full clone. SASE now materializes the beads sidecar on
demand rather than in every workspace, which reduces the number of clones, but every
machine that uses beads still needs this repository. Attaching a 20 MiB trace should not
add 20 MiB of historical payload to the synchronization path for unrelated note, search,
claim, and projection operations.

GitHub recommends a maximum individual Git object of 1 MiB, enforces 100 MiB, and
recommends repositories remain below 1 GiB when possible and below 5 GiB strongly. A
binary-oriented Git sidecar can knowingly trade against the 1 MiB recommendation, but
the bead event store should not make that trade for every user.

### 2. Git history makes a mistaken publication hard to undo

Deleting a path at the tip does not delete the blob from Git history. GitHub's own
sensitive-data procedure requires a history rewrite, coordination with other clone
owners, and sometimes Support intervention for cached views and pull-request refs. A
public fork can keep the material indefinitely. This is true in a dedicated public
attachment repository too, but isolation makes the blast radius, rewrite, rotation, and
event-store downtime much smaller.

The correct promise is therefore not “purge makes a public attachment private again.”
It is “purge prevents future SASE resolution where possible; public disclosure may be
irreversible.” The UI and docs should say this before publication, not only in a purge
runbook.

### 3. Binary churn undermines bead-store operability

The bead sidecar has special merge, rollback, rescue, projection, and background-sync
behavior. Large immutable blobs add clone time, pack churn, server-side maintenance,
and failure recovery to those control-plane operations. They also make a history rewrite
for one leaked file rewrite the repository that carries every bead event.

A dedicated store reduces the coupling:

```text
sase--beads                  attachment sidecars
-------------------------    ---------------------------------------
events + projections         public blobs       restricted blobs
small, hot, merge-aware      bare partial clone bare partial clone
authoritative note state     lazy object fetch  lazy authorized fetch
```

### 4. It provides no useful security advantage

Putting public bytes beside public descriptors is not simpler at the reader boundary.
The reader already needs the CAS, digest verification, named views, fetch caps, badges,
and large-file fallback. Selecting a public attachment remote is a small addition to the
existing `BlobStore` abstraction, whereas burdening `sase--beads` is a permanent storage
decision.

## Recommended storage topology

Use one logical attachment service with audience-aware physical stores:

```text
note event in sase--beads
  └── descriptor: name/token + audience + safe locator
        │
        ├── local CAS (always; cache and crash safety)
        │
        ├── public Git attachment sidecar (small, public objects)
        │     hidden bare partial clone; anonymous/read-only fetch is sufficient
        │
        ├── restricted Git attachment sidecar (small, restricted objects)
        │     hidden bare partial clone; provider credentials required
        │
        └── large/origin store (optional)
              remote-machine or object-store transport; preserves audience
```

### Repository naming and migration

For new projects, clear physical names would be:

- `<project>--attachments` — public; and
- `<project>--attachments-private` — restricted.

However, `sase-1ck` may already create `<project>--attachments` as a private repository
before the follow-on starts. Never flip a populated private repository to public. GitHub
warns that making a repository public exposes its code and history to everyone; making
it private later does not retract public forks.

The safe migration is:

1. Treat an existing private `<project>--attachments` as the legacy restricted store.
2. Create a new `<project>--attachments-public` repository.
3. Pin both physical repositories in project configuration so their roles are
   unambiguous.
4. Copy only explicitly declassified objects into the public store; do not bulk-move or
   change visibility.

New projects can use the cleaner names after the configuration model supports them.
Repository slugs are an implementation detail; the durable contract should be logical
roles such as `attachments.public` and `attachments.restricted`.

### Keep both repositories out of workspaces

Both stores should use the `sase-1ck` hidden-clone design. Git partial clone is intended
to omit unneeded objects and fetch missing ones on demand, but it also means readers
must handle offline and promisor-remote failures explicitly. SASE already plans those
availability badges and digest checks.

### Cap and rotate Git stores

The active epic's 50 MiB Git-tier cap is below GitHub's 100 MiB hard limit but far above
its 1 MiB recommended object size. I would start the public store with a lower default,
such as 10 MiB, retain a configurable hard ceiling no higher than 50 MiB, and expose
store-health metrics:

- logical unique bytes;
- packed repository size;
- object count and largest object;
- upload/fetch latency;
- orphan and tombstone counts; and
- an explicit “rotate/shard soon” threshold before 1 GiB.

The exact cap should be tuned from real screenshot and log evidence after `sase-1ck`
lands. The important design property is that the cap is store policy, not part of the
bead descriptor.

## Durable data model changes

### Audience must be explicit and immutable by default

Add an audience field to the core wire, for example:

```json
{
  "name": "login.png",
  "audience": "public",
  "sha256": "9f2c...e1",
  "size_bytes": 188416,
  "mime_type": "image/png",
  "image": {"width": 1280, "height": 720}
}
```

Legacy descriptors written by `sase-1ck` should reduce as `audience: restricted`,
because their designed destination is private. Do not infer audience dynamically from
which stores happen to contain the digest. Store presence can change, and a private
object must never become public merely because another machine has a permissive
configuration.

`audience` is policy, not location, so this preserves the active epic's good
location-free descriptor decision.

### Restricted metadata needs a safer public projection

The current plan publishes filename, digest, exact size, MIME type, image dimensions,
and origin hostname in `sase--beads` even when the bytes are private. That is too much
for genuinely sensitive attachments:

- a filename can disclose a customer, vulnerability, or credential type;
- a hostname can disclose infrastructure;
- size and media type aid fingerprinting; and
- a raw content digest lets an observer confirm a guessed file.

For restricted attachments, publish only what the public bead view needs:

```json
{
  "name": "private-attachment",
  "audience": "restricted",
  "private_id": "pa_7F8...random...",
  "redacted": true
}
```

Store the real filename, digest, size, MIME type, dimensions, origin, and object mapping
in the restricted sidecar, keyed by an unguessable random ID. Authorized clients hydrate
the descriptor after authenticating; unauthorized clients render a stable “restricted
attachment” placeholder.

This is more scope than simply adding a second store, but it is necessary if “private”
is intended to protect more than bytes. If the follow-on defers it, documentation must
say plainly that private attachment **metadata remains public** and that private names
and note prose must be sanitized.

Making `sha256` optional or variant-specific may require a mixed-fleet gate because an
old reader could reject a descriptor without it. That is preferable to encoding a fake
digest or silently leaking the real one. Land the new core wire, binding, and fleet
upgrade before allowing redacted restricted descriptors.

### Do not put `origin` in the public event

Origin is useful for a local-only or pending badge but does not need to be globally
public. Keep it in local state or the restricted routing manifest. A public attachment
does not need an origin after successful upload; a remote-only large attachment can use
an opaque machine handle resolved through the enrolled-machine inventory.

## Classification: what software can and cannot decide

### A denylist is a guardrail, not a classifier

The `sase-1ck` sensitive-path list is valuable. It should catch `.ssh`, `.gnupg`, `.env`,
private-key extensions, cloud credentials, `.netrc`, Git credentials, GitHub host tokens,
and project-specific patterns. But many sensitive files have ordinary names:

- `screenshot.png` may show a bearer token or private conversation;
- `crash.log` may contain customer data, absolute home paths, environment variables, or
  proprietary source;
- `report.pdf` may be licensed or embargoed;
- `dump.bin` may contain memory-resident secrets;
- `trace.json` may contain request bodies or identifiers; and
- an apparently harmless archive can contain any of the above.

GitHub push protection cannot close this gap. GitHub documents that it recognizes only
a subset of supported secret patterns, can miss legacy token forms, and skips push
protection for public pushes larger than 50 MiB. It is defense in depth, not proof of
public suitability.

### Use a positive-public policy

Make the default CLI policy `auto`, not a silent Boolean “not sensitive.” The core
policy result should be one of:

```text
allow_public | force_restricted | refuse | needs_declassification
```

Recommended rules:

#### Confidently public

A file may be public automatically when at least one strong provenance rule holds and
the content scan has no finding:

- its exact bytes already exist in a publicly reachable commit of the current project;
- it is generated solely from public project inputs by a declared, bounded SASE
  renderer intended for publication; or
- the caller explicitly supplies `--public` with a short reason and policy permits
  declassification.

The first rule is especially useful: it turns existing public Git history into evidence
rather than trying to infer sensitivity from an extension.

#### Force restricted

Route to restricted storage when any of these apply:

- the source is under a home, temp, credential, browser, mail, chat, database, or runtime
  directory rather than a public checkout;
- it is a log, trace, dump, packet capture, screenshot, database, office document, or
  archive without strong public provenance;
- it contains credential-like material, email addresses, obvious identifiers, private
  URLs, home paths, or configured organization patterns;
- it embeds EXIF/geolocation or document-author metadata not intentionally preserved;
- it is binary content the scanner cannot meaningfully inspect; or
- the author or agent expresses doubt.

#### Refuse

Refuse known credential vaults, private keys, Git credential stores, cloud credential
files, and similar crown-jewel material even for the restricted Git store. Require the
combination of `--private`, `--allow-sensitive`, and a reason to override, and warn that
a Git repository is not a secret manager.

#### Needs explicit declassification

A restricted attachment can become public only through an explicit operation that
reruns policy and records who made the decision and why. Never perform this transition
because `attachment push` found a public store first.

### Agent guidance

Agents need a simple rule they can apply without pretending to be perfect classifiers:

> Attach publicly only when the bytes are already public or were deliberately produced
> from public inputs for public distribution. Use `--private` for logs, traces,
> screenshots, runtime state, user data, external files, archives, and any uncertainty.

This guidance should be added to generated SASE skills after the follow-on lands. It is
more reliable than a long extension list.

### Human and automation defaults

I recommend these defaults:

| Caller/context | Default |
| --- | --- |
| Agent, public project | `auto`; ambiguous means restricted |
| Human TTY, public project | `auto`, with a clear destination echo before irreversible publication |
| Private project | restricted/project audience; public requires explicit `--public` |
| CI/noninteractive bulk operation | restricted unless a checked-in policy positively authorizes public output |

If the product insists on literal public-by-default for agents, require a prominent
project config opt-in such as `bead.attachments.default_audience: public`, keep the
forced-restricted and refusal rules, and document the residual risk. I do not recommend
shipping that as the global default.

## CLI and UX changes

### Creation

Add mutually exclusive audience controls to every attachment-authoring path:

```text
--public
--private                 # friendly alias for --audience restricted
--audience auto|public|restricted
```

`auto` is the default. `-S/--allow-sensitive` is not an audience selector. It should
imply restricted storage or error when combined with `--public`.

The write echo should show the resolved policy before the final event publication:

```text
🖼 login.png  184 KiB  PUBLIC · sase--attachments-public
≡ crash.log   2.1 MiB  RESTRICTED · policy: runtime log
```

For agents, include the policy reason in plain stderr and JSON so the choice is
auditable. For humans, a first-use public-publication warning is reasonable; do not add
a confirmation to every routine public attachment after the project owner has opted in.

### Availability versus publication

Keep commands semantically separate:

- `attachment push` uploads to a remote that preserves the current audience;
- `attachment publish` changes restricted to public, requires a reason, reruns scans,
  previews exposed metadata, and confirms on a TTY;
- `attachment privatize` can stop future public resolution but must warn that it cannot
  retract existing public copies; and
- `--local-only` controls availability only.

Do not silently fall back from public to restricted or from restricted to public on an
upload error. A policy change must be visible.

### Read states

Extend the active epic's availability matrix with explicit authorization states:

- `public · remote`;
- `restricted · remote`;
- `restricted · no access`;
- `pending upload`;
- `origin only`;
- `not downloaded`;
- `purged`; and
- `digest mismatch`.

“Unavailable offline” is not a substitute for “you are not authorized.” The doctor
should test public reachability anonymously where practical and restricted reachability
with current provider credentials.

## Publication ordering and consistency

The desired guarantee requires a stronger visibility barrier than the current epic's
default outbox behavior.

For a public or restricted shared attachment:

1. ingest into the local CAS and compute the descriptor;
2. apply policy and choose the audience-specific store;
3. upload the object and restricted metadata, if any;
4. verify the object can be resolved from the remote store;
5. append the bead event; and
6. publish the bead store.

An event failure after upload leaves an unreferenced object that grace-period GC can
remove. The opposite order leaves a shared bead pointing to unavailable bytes. Prefer
the harmless orphan.

This corresponds to making `require_upload` effectively true for shared attachments.
Offline authors can still choose `--local-only`, but the resulting note must say it is
not shared and must not satisfy a shared-attachment acceptance test.

Cross-store transactions cannot be truly atomic, so every operation needs an idempotent
key and repair path. The digest/public ID plus bead/note identity is sufficient. Doctor
should detect uploaded orphans, descriptors with no accessible object, wrong-audience
duplicates, and stale declassification records.

## Security beyond confidentiality

Public attachment hosting adds integrity, rendering, and abuse concerns. OWASP's file
upload guidance calls out parser exploits, archive bombs, active content, storage
exhaustion, public disclosure, and hosting illegal or dangerous content. Even if SASE
uses Git rather than a web upload form, the same trust boundary exists.

The follow-on should retain or add these controls:

- verify every fetch by digest;
- use content-addressed physical names and sanitized display names;
- never execute attachment content;
- never automatically render SVG, EPS, HTML, or other active formats;
- bound image dimensions, decompression ratios, archive inspection, preview time, and
  memory;
- serve downloads as attachments through any future HTTP gateway, with a conservative
  content type and `nosniff`;
- rate-limit remote-machine downloads and enforce per-object and per-project quotas;
- scan public candidates locally before Git publication, then treat GitHub secret
  scanning as an additional layer;
- keep provenance (`creator`, bead/note, time, policy result, scanner versions) in an
  audit record without exposing private metadata publicly; and
- support quarantine rather than deletion when a remote object fails validation.

## Large files through remote-machine support

It is reasonable to exclude large files from Git storage, but this is an explicit
exception to “all project users can access every non-sensitive attachment.” A badge must
say when an attachment is origin-only or requires enrollment with a specific remote.

The existing remote-machine code is not yet a general blob transport:

- fleet content handles fetch bounded ranges with a default 64 KiB and maximum 256 KiB;
- remote launch explicitly rejects attachments/files/images as non-portable payload;
  and
- the mobile gateway has authenticated notification-attachment downloads, but they are
  capped and tied to notification manifests rather than bead CAS objects.

A large-attachment transport can reuse the authentication and digest-validation ideas,
but it needs a new capability-scoped blob API:

- immutable object ID plus expected digest and size;
- byte-range or streaming download;
- audience authorization on every request;
- short-lived handles rather than raw host paths;
- explicit retention/availability leases;
- rate limits and concurrent-transfer caps; and
- a typed `origin_offline` / `no_access` result.

For the follow-on epic, I would keep large files simple:

1. retain the existing optional rclone/origin tier;
2. preserve the attachment's audience in that tier;
3. label origin-only files honestly;
4. do not block the small-public-store work on a general remote blob API; and
5. file the authenticated large-blob endpoint as a later phase only if real usage
   justifies it.

## Alternatives considered

### Keep the existing private sidecar and grant every user access

This is the best answer if “all users” means a known authenticated team. It avoids
public disclosure and needs only provider permission automation plus a `no_access`
doctor state. It does not satisfy anonymous users or casual contributors to a public
project.

### Store public bytes in `sase--beads`

Rejected for coupling, clone cost, operational risk, and history-rewrite blast radius.
It offers no reader simplification that the existing `BlobStore` seam does not already
provide.

### Make the current private attachment repo public

Rejected. A populated repository may already contain material uploaded under a private
expectation. A visibility flip publishes its entire reachable history, not a selected
set of objects.

### Put encrypted private objects in one public repo

This can hide bytes but introduces key distribution, rotation, revocation, multi-user
envelopes, recovery, and misleading metadata problems. Once a reader has a key and
plaintext, revocation cannot retract it. A separate restricted store is simpler and
matches SASE's provider-auth model.

### Rely on GitHub secret scanning

Rejected as the classification authority. It detects supported credential patterns and
has documented scope and size limitations; it does not classify privacy, intellectual
property, personal data, or publication intent.

### Use Git LFS

Not recommended for this design. It adds a required client and quota/accounting path,
and GitHub documents that remote LFS objects remain after history removal and normally
require repository recreation or Support to purge. The existing CAS plus lazy partial
clone is a better fit for small objects; remote/object storage is better for large ones.

## Proposed follow-on epic shape

The follow-on should begin only after `sase-1ck` is closed and its actual contracts are
re-audited. A practical sequence is:

### Phase 1: audience model and compatibility

- Add `audience` and policy-result types in sase-core.
- Treat legacy descriptors as restricted.
- Separate audience from availability in JSON, CLI, and presentation.
- Add mixed-fleet fixtures before writing the new form.
- Decide whether restricted metadata redaction lands now or is an explicit documented
  limitation.

### Phase 2: policy engine and authoring UX

- Add `auto|public|restricted` selection and `--public` / `--private` aliases.
- Add public-provenance checks, forced-restricted rules, hard refusals, configured
  patterns, and scanner hooks.
- Make `-S` incompatible with public publication.
- Emit machine-readable decisions and reasons.

### Phase 3: public store

- Add the dedicated public sidecar as a hidden bare partial clone.
- Keep the existing private store private; add migration-aware naming/pins.
- Require successful upload before bead publication for shared attachments.
- Test anonymous public read and credentialed restricted read across two SASE homes.

### Phase 4: restricted metadata

- Add opaque private IDs and a restricted metadata manifest.
- Remove public origin hostnames for new descriptors.
- Render honest unauthorized placeholders.
- Add correlation and guessed-content tests.

### Phase 5: declassification and lifecycle

- Add explicit `attachment publish --reason` and non-retraction warnings.
- Copy, verify, then update policy; never bulk-move.
- Add store health, orphan, wrong-audience, and access diagnostics.
- Document public purge as best-effort resolution removal, not recall.

### Phase 6: measurements and optional large transport

- Measure real file sizes and tune the Git cap.
- Add quota and rotation warnings.
- Extend the remote gateway only if actual large-file access needs justify it.

## Acceptance criteria for the new goal

The epic should not be considered complete until these are true:

1. A public attachment written on one clean machine is readable on a second machine
   without private-store credentials.
2. A restricted attachment cannot be fetched without restricted-store credentials and
   renders `no access`, not `offline`.
3. Restricted bytes are never written to the public store by fallback, retry, outbox,
   deduplication, or store-order changes.
4. Legacy `sase-1ck` attachments remain readable and resolve as restricted.
5. Public upload succeeds and is remotely verified before the bead event becomes
   remotely visible.
6. A public candidate with a sensitive-path or content finding is forced restricted or
   refused; `-S --public` fails.
7. Ambiguous agent-created logs, screenshots, archives, dumps, and external files are
   restricted by the default `auto` policy.
8. A file already present byte-for-byte in the public project history can route public
   automatically.
9. Publishing a restricted attachment requires an explicit reason, produces an audit
   record, previews exposed metadata, and warns that publication is irreversible.
10. Private metadata is either redacted from `sase--beads` or the limitation is made
    explicit in every relevant help/page surface before GA.
11. The bead repository's pack size does not grow with attachment payload bytes.
12. Public and restricted Git stores remain blobless on initial clone and fetch only the
    requested object.
13. Oversized files never slip into Git because of missing or malformed configuration.
14. Public purge tests demonstrate tombstoning and resolver refusal while documentation
    accurately describes surviving clones, forks, and caches.
15. A project with no public store fails or uses an explicitly badged local/restricted
    path; it never silently claims public availability.

## Recommended solution

Launch the follow-on epic, but revise its goal to: **make bead attachment audience and
availability explicit, and make deliberately public small attachments universally
readable without bloating the bead event store.**

Concretely:

1. **Keep `sase--beads` metadata-only.** Do not move attachment payloads into it.
2. **Add a dedicated public attachment sidecar** using the same hidden bare
   `--filter=blob:none`, content-addressed, lazy-fetch design as the restricted store.
3. **Keep a distinct restricted store.** If `sase-1ck` has already created a private
   `<project>--attachments`, preserve it; create a new public repository rather than
   changing its visibility.
4. **Add durable `audience: public|restricted` policy to the core descriptor.** Store
   selection must obey this field; store order or object presence must never change it.
5. **Use `auto` policy, not public-on-no-match.** Automatically publish bytes already
   proven public; force logs, traces, screenshots, runtime/external files, archives, and
   ambiguous binaries restricted; allow explicit `--public` declassification with a
   reason. Provide `--private` everywhere.
6. **Separate audience from availability.** `--local-only` and `attachment push` never
   change audience. Use a distinct, audited `attachment publish` action for
   declassification.
7. **Protect restricted metadata, not only bytes.** Prefer an opaque public locator and
   restricted manifest; at minimum remove origin hostnames and document filename/hash
   leakage until the safer wire lands.
8. **Fail closed at the publication barrier.** Upload and remotely verify a shared
   object before publishing its bead event. Offline/local-only remains available but is
   honestly badged.
9. **Keep large files outside Git.** Retain rclone/origin-only support initially; add an
   authenticated remote-machine blob endpoint later only if real use justifies it.
10. **Treat public publication as irreversible.** Scanners are defense in depth, purge
    is best effort, and changing a private repository to public is never a migration
    mechanism.

This approach achieves the useful part of the proposal—all collaborators and public
project users can retrieve intentionally public evidence by default—without making the
bead control plane a binary archive or pretending that a filename/secret denylist can
prove a file safe for the world.
