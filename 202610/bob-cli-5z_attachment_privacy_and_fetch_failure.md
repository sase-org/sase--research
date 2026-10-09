# Why bob-cli-5z.land could not read its bead attachment

Investigated 2026-10-09. **Yes, the attachment was private. SASE chose that deliberately because the source file was Git-ignored. The read failure was a separate project-identity bug; making the attachment public would not fix it.**

The file was `bob_mac_capture_install_error.txt` on bead `bob-cli-5z`: 8,451 bytes, SHA-256 `b72806d094e58c66f42e32723f3d36f98e6f822c8b327045640285545c7e766d`, origin `athena`.

**Why it was private.** Your shell history records an ordinary `sbd note` with `@~/tmp/bob_mac_capture_install_error.txt`, without a privacy override. On athena, that path resolves to `/home/bryan/Sync/home/tmp/bob_mac_capture_install_error.txt`, inside the dotfiles Git checkout. `git check-ignore -v` identifies `/home/bryan/.gitignore_global:50:tmp/*`. SASE treats ignored files as private provenance, before considering whether clean text can be public. The original decision metadata confirms `rule: private_provenance`, `explicit: false`, decided at `19:04:20Z`. This was not an explicit private request, a size limit, or a recorded secret-scan hit. The source file still matches the attachment's digest.

**Why the agent could not read it.** The attachment was committed to the private store as `2aa550b8b36a81690da7402dd779da6b8083f4eb` at `19:04:21Z`; that commit is present in the remote checkout. GitHub reports `bobs-org/bob-cli--attachments-private` as `PRIVATE`. Private storage should remain accessible to authorized agents.

The land agent's recorded tool results show `attachment path` failing at `19:15:22Z` with “unavailable offline”; syncing beads and retrying also failed. It successfully read the file on athena over SSH at `19:16:20Z`. Its live commentary called this an unsynced attachment, but the investigation reproduced a more specific defect:

| Attachment lookup input | Result on apollo |
| --- | --- |
| Workspace marker key: `bobs-org/bob-cli` | No public or private store path; private store discovery returns false |
| Canonical SASE project key: `gh_bobs-org__bob-cli` | Existing store paths resolve; private store discovery returns true |

`resolve_project_key()` returns the workspace marker's raw key before trying the canonical resolver. The storage-path helper rejects its `/`; the caller catches that error and returns no store. The read then reports “unavailable offline” without attempting the correct repository. **Both public and private stores use this lookup.** An already-cached attachment can hide the defect: this file is now cached on apollo and an audited read succeeds, while the incorrect discovery result still reproduces.

**Recommended fix.** Resolve attachment stores and upload queues through the canonical SASE project identity. Add regression coverage with a real `owner/repo` workspace marker and an empty attachment cache, exercising public/private retrieval and upload discovery. Preserve the underlying discovery error in diagnostics. Keep this attachment private unless you separately intend to publish it; no publication or code fix was performed for this research.

Evidence and implementation references:

- Original decision: athena's `~/.sase/attachments/audience/sha256/b7/<full-digest>.json`; source command in `~/.zsh_history`; ignore-rule and digest checks described above.
- Stable tool-call evidence from agent `bob-cli-5z.land`: `/home/bryan/.sase/projects/gh_bobs-org__bob-cli/artifacts/ace-run/202610/09/20261009132533/tool_calls.jsonl`. The agent was still running when inspected; its commentary was live, not a completed transcript.
- [Audience rule](https://github.com/sase-org/sase-core/blob/6df3bed385c2fcfc3a807edaccc4ad19b673e371/crates/sase_core/src/note_attachment/audience.rs#L222), [attachment project lookup](https://github.com/sase-org/sase/blob/6ac3dc734e23f597502d011c4b6580ec7720a1fe/src/sase/bead/attachments/upload/discovery.py#L18), [path validation](https://github.com/sase-org/sase/blob/6ac3dc734e23f597502d011c4b6580ec7720a1fe/src/sase/_linked_repo_paths.py#L66), and [canonical resolver](https://github.com/sase-org/sase/blob/6ac3dc734e23f597502d011c4b6580ec7720a1fe/src/sase/bead/project_name.py#L113).
