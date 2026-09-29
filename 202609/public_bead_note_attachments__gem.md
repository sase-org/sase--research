# Public Bead Note Attachments & Privacy Architecture

**Author:** Researcher `gem` (5-Researcher Swarm)  
**Date:** September 2026  
**Project:** SASE (`sase-org/sase`)  
**Context:** Post-`sase-1ck` Bead Note Attachments Strategy  

---

## 1. Executive Summary & Verdict

### The Goal
The objective is to enable all contributors working on a SASE project to access all non-sensitive bead note attachments by default, eliminating the access barriers in epic `sase-1ck` where attachments are restricted to authenticated members of a private sidecar repository.

### The Proposal Under Critique
1. Move non-sensitive attachment bytes from the private `sase-org/sase--attachments` sidecar repository directly into the public `sase-org/sase--beads` repository.
2. Support large files (> 50 MiB) solely through SASE's enrolled remote machine support (e.g., SFTP over Tailscale to `athena`).
3. Allow agents to specify private attachments when needed, but default all attachments to public, with an undefined mechanism for determining file sensitivity.

### The Core Verdict
- **Goal Alignment:** **Strongly Approved.** Defaulting non-sensitive attachments to be accessible to all project collaborators eliminates significant friction, avoids manual repository provisioning during onboarding, and ensures reproducible diagnostics across team members and public open-source contributors.
- **Implementation Mechanism (Bytes in `sase--beads`):** **Strongly Rejected (Architectural Anti-Pattern).** Committing binary blobs directly into `sase--beads` severely degrades workspace cloning performance across ephemeral workspaces (`sase_<N>`), couples an actively projected JSONL/Markdown issue store with a content-addressed binary store, and irreversibly breaks `sase bead attachment purge` because history-rewriting tools (`git filter-repo`) would alter commit SHAs across the entire issue tracker.
- **Sensitivity Policy (Agent-Discretion "Default Public"):** **Rejected as a Security Risk.** LLMs are non-deterministic and cannot be trusted as the sole line of defense against credential leakage. Defaulting to public storage without deterministic Data Loss Prevention (DLP) guards will inevitably expose API keys, environment variables, authentication headers, and internal hostnames in immutable public Git history.
- **Large Files via Remote Machines:** **Strongly Approved.** Confining files > 50 MiB to enrolled remote machine infrastructure avoids public egress bandwidth costs, respects GitHub repository limits, and leverages SASE's existing authenticated peer-to-peer Tailscale/SSH mesh.

### The Recommended Solution
Instead of moving bytes into `sase--beads`, SASE should maintain a dedicated attachments sidecar repository, but **make `sase--attachments` public by default** (matching the visibility of `sase--beads`), configured as a machine-level bare partial clone (`git clone --bare --filter=blob:none`). Sensitivity must be governed by a **three-tier defense-in-depth framework** combining deterministic path refusal, automated entropy/regex secret scanning, media-type heuristics, and explicit agent syntax (`@private:./path` / `-P`). Private attachments route to the authenticated remote machine store or an opt-in private sidecar.

---

## 2. Review of Context & Epic `sase-1ck` Foundation

### 2.1 The `sase-1ck` Baseline
Epic `sase-1ck` (*Bead note attachments*) established the foundational storage model for inline `@<path>` file references in bead notes:
- **Public Bead Metadata:** Note text containing `@attachment:<name>` tokens and lightweight metadata descriptors (`{name, sha256, size_bytes, mime_type, image, origin}`) are appended to the public `sase--beads` event stream and projected to `issues.jsonl`.
- **Local Content-Addressed Store (CAS):** Written first on the local machine under `~/.sase/attachments/objects/sha256/<xx>/<sha256>`, providing zero-copy caching and extension-preserving symlink views.
- **Private Git Tier (`sase--attachments`):** For files $\le 50\text{ MiB}$, blobs are pushed to a private GitHub repository (`sase-org/sase--attachments`) managed as a bare partial clone (`--filter=blob:none`) at the host level (`~/.sase/projects/<key>/repos/attachments`).
- **Large File Tier (`large_store`):** For files $> 50\text{ MiB}$ up to $2\text{ GiB}$, an rclone-backed remote (SFTP to `athena` over Tailscale, or Cloudflare R2) receives the payload.

### 2.2 The Friction Identified in `attachment_storage_and_access.md`
As documented in `research:202609/bead_note_attachments/attachment_storage_and_access.md`, the `sase-1ck` design introduces notable barriers for collaboration:
1. **Empty Set Collaborators:** External contributors or team members without explicit GitHub read access to `sase-org/sase--attachments` see only the note prose, filename, and a misleading `🔒` chip or `✕ unavailable offline` badge. They cannot retrieve error logs, repro traces, or screenshots.
2. **Administrative Overhead:** The private repository requires manual provisioning via `sase repo init`, distinct GitHub permission assignments, and per-machine credential synchronization.
3. **Imbalance Between Issue and Evidence Visibility:** While the issue tracker (`sase--beads`) is public and collaborative, the diagnostic evidence supporting those issues is locked in private silos.

---

## 3. In-Depth Critique: Why Moving Attachments to `sase--beads` Is a Mistake

The intuition behind moving non-sensitive attachments into `sase--beads` is clear: `sase--beads` is already shared with all collaborators, so co-locating attachments solves access with zero new repositories. However, from a distributed systems and Git storage perspective, this approach has critical flaws.

### 3.1 Workspace Proliferation and Clone Amplification
SASE's execution model is built upon ephemeral workspace directories (`sase_1`, `sase_2`, ... `sase_22`).
- Each workspace clones or checks out the repository set.
- Although `sase--beads` currently materializes on demand (`auto_clone: false`), any agent or human running bead commands (`sase bead show`, `sase bead list`, `sase bead create`) triggers synchronization.
- **Packfile Bloat:** Git is designed for diffable text. Binary files (screenshots, PNGs, archives, logs) do not delta-compress effectively. Committing dozens of 2–10 MiB attachments creates massive packfiles.
- Over a year of active agent operations (where swarms generate repro screenshots, profiling traces, and visual diffs), `sase--beads` will grow from its current lightweight ~19 MiB size into multiple gigabytes.
- Every developer, CI runner, and agent workspace will pay the latency and disk penalty of downloading historical attachment packfiles just to read task titles and status flags.

### 3.2 Coupling Working-Tree Projections with CAS Blob Storage
`sase--beads` has a specific architectural responsibility: it is an **event-sourced operational database**.
- It maintains structured events (`events/`) and human/machine projections (`issues.jsonl`, `pages/<id>/README.md`).
- Files in `sase--beads` are checked out into a working directory.
- If binary attachment blobs are placed in `sase--beads`, the working tree must either check them out (multiplying disk usage by the number of active workspaces) or configure Git sparse checkout and partial cloning within the primary issue tracking repo. This creates severe operational complexity, git hook fragility, and potential checkout lockups.

### 3.3 Catastrophic Impact on Deletion & Purge (`git filter-repo`)
Phase 9 of `sase-1ck` explicitly specifies `sase bead attachment purge` for removing accidentally committed, copyrighted, or sensitive objects:
- In Git, deleting a file from the tip does not delete it from history. Complete eradication requires rewriting Git history using `git filter-repo` or BFG.
- **If attachments live in a separate sidecar:** Rewriting `sase--attachments` deletes the blob from the object store without altering a single commit SHA or event in `sase--beads`. Notes simply render the attachment as `(purged)`.
- **If attachments live in `sase--beads`:** Running `git filter-repo` on `sase--beads` rewrites every commit hash from the purge point forward. This breaks:
  1. All cloned workspaces across all fleet machines (requiring manual `git reset --hard` or re-cloning).
  2. All external links, commit hashes referenced in audit trails, and ChangeSpec dependencies.
  3. Continuous integration anchors and mirrors.
- **Verdict:** Storing binary files in the same Git history as canonical issue tracking records renders data retention and GDPR compliance operationally hazardous.

### 3.4 GitHub Platform Constraints
GitHub enforces a strict 100 MiB per-file limit and strongly recommends keeping repository sizes under 1 GiB, with performance degradation and push-blocking warnings at 5 GiB. An issue tracker that hosts binary attachments directly will inevitably collide with these boundaries.

---

## 4. The Superior Alternative: Public Dedicated Attachments Sidecar

Instead of putting binary files into `sase--beads`, SASE should keep the architectural decoupling introduced in `sase-1ck`, but **change the default visibility of the `sase--attachments` sidecar repository to PUBLIC**.

```mermaid
flowchart TD
    subgraph Client ["Client Machine (Athena / Apollo / Mac)"]
        CLI["sase bead note / attach"]
        CAS["Local CAS (~/.sase/attachments/)"]
        BareClone["Hidden Bare Partial Clone<br/>(--filter=blob:none)"]
    end

    subgraph GitHub ["GitHub (sase-org)"]
        PublicBeads["sase--beads (PUBLIC)<br/>• Events & Note Prose<br/>• Metadata Descriptors<br/>• Size: ~20 MiB"]
        PublicAtt["sase--attachments (PUBLIC)<br/>• CAS Blobs (<= 50 MiB)<br/>• Bare Promisor Store<br/>• Lazy On-Demand Fetch"]
    end

    subgraph RemoteFleet ["SASE Remote Fleet"]
        RemoteMachine["Enrolled Machine (athena)<br/>• SFTP over Tailscale<br/>• Large Files (> 50 MiB)<br/>• Private / Authenticated"]
    end

    CLI -->|1. Write Metadata| PublicBeads
    CLI -->|2. Ingest Bytes| CAS
    CAS -->|3. Push Blobs| BareClone
    BareClone -->|4. Push Tip| PublicAtt
    CAS -.->|Large Files| RemoteMachine
```

### 4.1 How Git Promisor Partial Clones Solve the Public Access Problem
By configuring `sase--attachments` as a public repository with Git partial clone semantics:
1. **Zero-Byte Clone Overhead:** Collaborators clone the repository with `--filter=blob:none`. This downloads only commit objects and trees (a few kilobytes). Not a single megabyte of binary data is downloaded during project initialization.
2. **Anonymous HTTPS Lazy Promisor Fetch:** Because the repository is public on GitHub, any contributor—whether a core maintainer or an external open-source contributor—can fetch blobs on demand via standard HTTPS without SSH keys, personal access tokens, or organization invitations.
3. **On-Demand Hydration:** When a user executes `sase bead show -i` or `sase bead attachment open <id> <name>`, SASE requests the blob SHA from the local bare promisor clone. Git transparently fetches only that specific blob from GitHub into the local CAS.
4. **Workspace Isolation:** Ephemeral workspaces never clone `sase--attachments`. The bare clone lives once per machine at `~/.sase/projects/<key>/repos/attachments`, shared across all local workspaces.

---

## 5. The Sensitivity Dilemma: How to Classify and Guard Private Data

The user's prompt notes:
> *"I'm not sure how we should identify whether or not a file is sensitive or not. I'm thinking that agents should have the ability to specify that an attachment be private somehow, but they should default to using public attachments. I'm not sure how they should decide when to use a private attachment though."*

Relying on LLM agents to exercise discretion under a "default public" policy is inherently dangerous.

### 5.1 Why Agent Discretion Fails
1. **Blindness to Incidental Secrets:** When an agent captures a runtime failure, it might attach a 5,000-line server log. The agent's focus is debugging a stack trace; it will routinely overlook an `Authorization: Bearer eyJ...` header, a `DATABASE_URL=postgres://user:pass@internal...` string, or an internal corporate IP address nested in line 3,420.
2. **Prompt Injection and Compliance Gaps:** An agent can be coaxed or misled by external task input into believing an environment dump is required diagnostic context.
3. **Irreversibility of Public Exposure:** In Git, a push to a public repository is instantaneously mirrored and ingested by public scrapers. An LLM error cannot be "recalled."

### 5.2 The Three-Tier Defense-in-Depth Framework

To make public attachments safe, sensitivity must be determined by a multi-layered system where deterministic software filters guard against mistakes, safe media types default to public, and agents follow strict heuristics.

```mermaid
flowchart TD
    File["Input File (@path)"] --> PCheck{"Passes Deterministic<br/>Refusal Rules?"}
    PCheck -- No --> Refuse["REFUSE ATTACHMENT<br/>(Refuse ~/.ssh, .env, *.pem)"]
    
    PCheck -- Yes --> MediaCheck{"Media Type / Content"}
    
    MediaCheck -- Visual Media (.png, .jpg, .svg) --> ScanSafe["Classify as PUBLIC<br/>(Visual Artifact)"]
    MediaCheck -- In-Tree Git File --> ScanSafe
    MediaCheck -- Text / Logs / Dumps / Binaries --> DLP{"Automated DLP Scanner<br/>(Regex / Entropy / Keywords)"}
    
    DLP -- Secret Found --> SecFound{"Explicit --allow-sensitive?"}
    SecFound -- No --> Refuse
    SecFound -- Yes --> ForcePrivate["Force PRIVATE Store"]
    
    DLP -- Clean --> AgentTag{"Explicit Agent / Human Tag"}
    AgentTag -- "@private:path" or "-P" --> ForcePrivate
    AgentTag -- Default / "@public:path" --> ScanSafe

    ScanSafe --> PushPublic["Push to Public sase--attachments"]
    ForcePrivate --> PushPrivate["Route to Private Tier<br/>(Remote Machine SFTP or Private Repo)"]
```

#### Tier 1: Deterministic Path & Secret Screening (Automated Gatekeeper)
Before any attachment is accepted for public storage, SASE must execute deterministic checks in `sase-core`:
1. **Path-Based Hard Refusal:** Refuse files originating from or matching known sensitive paths:
   - `~/.ssh/*`, `~/.gnupg/*`, `~/.aws/*`, `~/.netrc`
   - `*.pem`, `*.key`, `*.pkcs12`, `*.pfx`, `*.keystore`, `id_rsa*`
   - `.env`, `.env.*`, `*credentials*`, `*secret*`, `*token*`
   - Shell history files (`.*_history`)
2. **Automated DLP Secret Scanner:** For text attachments (`.log`, `.txt`, `.json`, `.yaml`, `.xml`, etc.), execute an in-process regex/entropy scanner prior to staging:
   - Pattern checks for known credential signatures: AWS keys (`AKIA[0-9A-Z]{16}`), GitHub PATs (`ghp_`, `github_pat_`), JWT tokens (`eyJ[A-Za-z0-9_-]+\.`), generic `Bearer [A-Za-z0-9_\-\.~+/]+=*`, private key headers (`BEGIN PRIVATE KEY`).
   - If a pattern matches, public attachment is **strictly refused**. The CLI echoes:
     ```text
     Error: Refusing to publish @./server.log to public attachments store.
     Automated DLP scan detected potential secret on line 142 (pattern: Bearer token).
     To attach privately, use: sase bead note <id> "..." --private
     ```

#### Tier 2: Safe-by-Default Media Classification
Files should be automatically categorized by risk profile based on MIME type and repository origin:
- **Inherently Public-Safe:**
  - Visual image media: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`. (These represent UI screenshots, visual test diffs, and architectural diagrams—the primary use case for public bead attachments).
  - Clean In-Tree Git Artifacts: Any file located within the repository workspace that is already tracked by Git. (If it is already committed to the public repo, attaching it to a bead note cannot leak new secrets).
- **High-Risk (Requires DLP Cleansing or Defaults to Private):**
  - Text logs (`*.log`), memory/heap dumps (`*.hprof`, `core.*`), packet captures (`*.pcap`), SQLite databases (`*.db`, `*.sqlite`), and process environment exports.

#### Tier 3: Explicit Agent & Human Syntax
Agents and humans must have clear syntactical controls:
1. **Grammar Extensions in Note Text:**
   - Standard: `@./path` (evaluates through DLP; visual media defaults to public, logs pass scan).
   - Explicit Private: `@private:./path` (bypasses public store; forces storage in private tier).
   - Explicit Public: `@public:./path` (asserts public intent; still fails if Tier 1 hard refusal triggers).
2. **CLI Options:**
   - `sase bead note <id> "..." -P/--private`: Forces all attachments in this note to the private tier.
   - `sase bead attach <id> <path> --private`: Attaches a file directly to the private tier.
3. **Descriptor Wire Schema Update:**
   Update the wire descriptor in `sase-core` to record visibility explicitly:
   ```json
   {
     "name": "login_trace.log",
     "sha256": "41aa89c...07",
     "size_bytes": 1048576,
     "mime_type": "text/plain",
     "visibility": "private",
     "origin": "athena"
   }
   ```

### 5.3 Concrete Decision Rules for LLM Agents
To guide agents deterministically, the following prompt instructions must be injected into the `sase_new_task` and bead authoring skills:

> **Agent Rules for Bead Attachments:**
> 1. **Default to Public for Visuals:** Always attach UI screenshots, rendering diffs, diagrams, and reproduction graphics as public attachments (`@./screenshot.png`).
> 2. **Default to Private for System State:** Always use `@private:./path` or `--private` when attaching application log files, stack traces containing request headers, memory dumps, database fixtures, or configuration files.
> 3. **Never Attach Raw Credentials:** Never attach `.env` files, private keys, or credential stores, even with `--private`.
> 4. **When in Doubt, Mark Private:** If there is any uncertainty regarding whether a file contains proprietary business data, user information, or network topology, mark it private.

### 5.4 Where Do Private Attachments Live?
If `sase--attachments` is public, where are private attachments stored?
1. **Primary Private Tier: Authenticated Remote Machine (`athena` SFTP):**
   - SASE already maintains enrolled remote machines via Tailscale/SSH (`sase machine init`).
   - Private attachments can be routed directly to the remote machine's content-addressed store.
   - Only machines on the authorized tailnet can fetch these bytes.
2. **Optional Secondary Private Tier: `sase-org/sase--attachments-private`:**
   - For enterprise teams requiring cloud-hosted private Git storage, an optional private sidecar repository can be configured. If unconfigured, private attachments remain local-only (`-L`) or on the remote machine store.

---

## 6. Large File Strategy: Evaluation of Remote Machine Support

The user's prompt notes:
> *"It's fine if large files are only ever supported via sase's remote machine support."*

This is a sound constraint.

### 6.1 Why Public Storage for Large Files Is Harmful
1. **GitHub Hard Limits:** GitHub blocks pushes with files exceeding 100 MiB. Even with Git LFS, bandwidth quotas on free/standard accounts are quickly exhausted.
2. **Cloud Egress Vulnerabilities ("Surprise Bill Attack"):** Hosting multi-gigabyte files (e.g., virtual machine disks, large dataset dumps, recordings) on a public Cloudflare R2 or AWS S3 bucket with public download URLs exposes the account owner to unbounded bandwidth consumption or distributed denial-of-wallet attacks.
3. **Network Congestion:** Collaborators on slow or metered connections should never inadvertently download multi-hundred-megabyte binaries during casual bead reviews.

### 6.2 The Elegance of Enrolled Remote Machine Storage
In `sase-1ck` Phase 6, the large-file tier was architected around `bead.attachments.large_store` using an rclone remote, specifically recommending **SFTP to `athena` over Tailscale**:
- **Zero Cloud Costs:** Direct peer-to-peer data transfers over Tailscale consume zero billable cloud egress.
- **Intrinsic Mutual Authentication:** Access is governed by Tailscale ACLs and SSH key authorization. Only enrolled machines can pull large objects.
- **Bandwidth Throttling & Lazy Downloading:** SASE defaults to `auto_fetch_max_bytes = 25 MiB`. Files exceeding this threshold require explicit download (`sase bead attachment fetch <id> <name>` or `-d`), preventing accidental downloads.

---

## 7. Adjustments to Requirements

To achieve the user's ultimate goal while avoiding architectural failure modes, the following adjustments to the user's requirements are justified:

| Original Requirement / Idea | Adjusted Requirement | Justification |
| :--- | :--- | :--- |
| **Move non-sensitive attachments to `sase--beads` repo.** | **Keep dedicated `sase--attachments` sidecar, but set default visibility to PUBLIC.** | Prevents massive Git packfile bloat in the primary issue tracker, preserves fast workspace checkout times, and prevents history corruption during attachment purge operations. |
| **Agents default to public attachments based on discretion.** | **Automated Defense-in-Depth:** Deterministic path refusal + DLP secret scanner + media-type classification + explicit agent rules. | LLMs cannot reliably detect subtle secrets, tokens, and PII. Deterministic software guards prevent irreversible credential leaks into public Git history. |
| **Unspecified private storage location.** | **Route private attachments to the Authenticated Remote Machine Store (Tailscale SFTP)** or an optional `sase--attachments-private` sidecar. | Leverages existing authenticated machine fleet infrastructure without requiring complex per-file client-side encryption. |
| **Support large files only via remote machine support.** | **Adopted as specified.** Retain Phase 6 rclone SFTP tier for files $> 50\text{ MiB}$. | Completely prevents Git repo bloat and eliminates public cloud egress billing risks. |

---

## 8. Recommended Solution & Next Epic Implementation Blueprint

Following the closure of epic `sase-1ck`, the subsequent epic—tentatively titled **`sase-pubatt` (Public Bead Attachments & Sensitivity Governance)**—should be structured into the following sequential phases:

```mermaid
flowchart LR
    Phase1["Phase 1: Wire & Grammar<br/>(Visibility Schema, @private Syntax)"]
    Phase2["Phase 2: DLP Scanner<br/>(Secret & Entropy Engine)"]
    Phase3["Phase 3: Public Sidecar<br/>(sase--attachments Public Init)"]
    Phase4["Phase 4: Store Routing<br/>(Dual-Tier Git/SFTP Dispatch)"]
    Phase5["Phase 5: Agent Skills & UX<br/>(System Prompts, Doctor, Audit)"]

    Phase1 --> Phase2 --> Phase3 --> Phase4 --> Phase5
```

### Phase 1: Core Grammar, Schema, and Visibility Metadata (`sase-core`)
- Extend the attachment descriptor in Rust `sase-core` with an explicit `visibility` field (`public` | `private`, defaulting to `public` for safe media).
- Update the grammar parser in `sase-core`:
  - Support `@private:<path>` and `@public:<path>` prefix notation.
  - Retain boundary `@` parsing rules and escape rules (`@@`).
- Add `-P/--private` flags to `BeadNoteOptions` and `BeadAttachOptions`.

### Phase 2: In-Process DLP & Secret Screening Engine (`sase-core`)
- Implement a deterministic scanner in `sase-core` that evaluates files before staging:
  - Match against high-entropy substrings and known API key patterns (AWS, GitHub, Slack, OpenAI, generic Bearer tokens, PEM headers).
  - Inspect path basenames against blacklisted configuration/secret files (`.env*`, `*credentials*`, `id_*`).
- Enforce strict refusal: any file matching Tier 1 criteria is rejected from public attachment unless overridden to private storage.

### Phase 3: Public Attachments Sidecar Initialization (`sase`)
- Update `sase repo init`:
  - When initializing a public project (where `sase--beads` is public), prompt to create `sase-org/sase--attachments` with **public** visibility by default.
  - Clone as a bare partial clone (`--bare --filter=blob:none`) under `~/.sase/projects/<key>/repos/attachments`.
  - Configure the Git remote for anonymous HTTPS fetch so unauthenticated collaborators can read blobs without GitHub credentials.

### Phase 4: Dynamic Store Routing & Remote Machine Tier
- Implement dual-store routing in `sase/bead/attachments/store_manager.py`:
  - Objects flagged `visibility: public` and $\le 50\text{ MiB}$ dispatch to `GitAttachmentStore` (`sase--attachments`).
  - Objects flagged `visibility: private` dispatch to `bead.attachments.private_store` (configured either as an SFTP remote machine on the tailnet or an authenticated private GitHub sidecar).
  - Objects $> 50\text{ MiB}$ dispatch to `RcloneAttachmentStore` (remote machine SFTP).

### Phase 5: Agent Skills, Diagnostic Doctor, and TUI Badges
- Update `src/sase/xprompts/skills/sase_new_task.md` and related agent skills with explicit attachment privacy guidelines.
- Update `sase bead doctor` with attachment store health checks:
  - Verify public HTTPS reachability of `sase--attachments`.
  - Validate remote machine SFTP connectivity for private/large tiers.
  - Flag orphaned private outbox items.
- Update TUI and CLI rendering:
  - Render public attachments with an open link/preview chip.
  - Render private attachments with a distinct `🔒 private (athena)` badge.

---

## 9. Conclusion

The user's vision of democratizing access to bead note attachments is essential for effective collaboration, but the proposed tactic of merging binary attachments into `sase--beads` would incur severe long-term penalties in Git performance, repository bloat, and operational maintenance.

By maintaining a dedicated attachments sidecar with **public repository visibility** and **Git partial cloning**, SASE achieves instantaneous, frictionless, zero-cost sharing of non-sensitive attachments across all project users. Paired with a deterministic three-tier sensitivity defense and SASE's remote machine mesh for large and private files, this architecture delivers an enterprise-grade, secure, and performant collaboration platform.
