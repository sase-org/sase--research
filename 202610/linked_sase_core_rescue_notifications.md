# Why "Rescued leftover state from linked-sase-core" notifications keep firing

**Date:** 2026-10-13

## TL;DR

These notifications are **false alarms**. No work is being lost or saved. Each time an
agent starts in a numbered workspace, SASE checks the workspace's `sase-core` linked clone
for commits that exist only locally. It finds sase-core's 313 **annotated release tags**
(`v0.1.1` … `v0.9.2`), decides they are "local-only", bundles them, and sends a
notification. The tags are already on GitHub. The check is just wrong about them.

## What the notifications are

- **Sender:** `workspace-rescue` (tag `sidecar`).
- **Code:** `_notify_rescue()` in `src/sase/workspace_provider/rescue.py`.
- **Reason line:** always `launch-time eviction of linked or external repo clone`.
- **Volume:** 11 today, starting at 15:39 EDT, one per agent launch (ws11 ×3, then ws12,
  13, 14, 16, 17, 18, 19, 20).
- **Stored at:** `~/.sase/rescue/202610/<stamp>-ws<N>-linked-sase-core-<hash>/`

## Why they are sent

1. **New feature (today).** Commit `1a638eac95`, "feat(workspace): rescue linked and
   external clones before eviction" (bead `sase-1kh.1`), added
   `rescue_repo_clones_before_eviction()` in `src/sase/axe/runner_workspace_protection.py`.
   On every launch in a numbered workspace (`workspace_num > 1`), it runs
   `rescue_git_repo()` on each clone under `sase/repos/linked/*` before those clones are
   evicted.
2. **What the rescue bundles.** `_bundle_refs()` collects every `refs/heads/*`,
   `refs/tags/*`, and `refs/sase/recovery/*`. `_write_bundle()` then runs
   `git bundle create … --not --remotes`, so anything reachable from `origin/*` is
   supposed to drop out.
3. **The bug.** `--not --remotes` excludes *commits*. An annotated tag is a separate *tag
   object*, and no `refs/remotes/*` ref points to it. Git therefore treats every
   annotated tag as new and puts it in the bundle. Because the bundle isn't empty, a
   rescue entry and a notification are created.
4. **Why it hits every launch.** Every sase-core clone fetches all 313 tags (release-plz
   makes annotated tags), so every eviction "finds" the same tags.

## Evidence

Every one of the 11 manifests shows the clone was clean and in sync:

| Field              | Value (all 11 entries)                    |
| ------------------ | ----------------------------------------- |
| `branch`           | `master`                                  |
| `head` vs `upstream` | identical (`d30e1337a8`, once `51969d84fb`) |
| `status_porcelain` | empty                                     |
| `stash_entries`    | 0                                         |
| bundle contents    | 313 refs, **all `refs/tags/*`**, no branches |
| bundle size        | ~68 KB (tag objects only)                 |

In the sase-core clone, all 313 local tags are annotated (`objecttype = tag`), and
`git ls-remote --tags origin` lists 313 tags. The commits the tags point to are on
`origin/*` branches.

A minimal reproduction in a temporary repo shows the same behavior:

```text
git bundle create b1 refs/heads/master refs/tags/light --not --remotes
  -> fatal: Refusing to create empty bundle.     # lightweight tag: correctly skipped
git bundle create b2 refs/heads/master refs/tags/v1 --not --remotes
  -> bundle with refs/tags/v1                     # annotated tag: false positive
```

## Impact

- **Data:** none. Nothing was lost, and there is nothing worth restoring.
- **Noise:** one unread notification per agent launch, for as long as the bug exists.
- **Disk:** about 68 KB per launch under `~/.sase/rescue/`, deleted after 30 days.

## Fix options

1. **Recommended:** in `_bundle_refs()`, only keep a tag if its peeled commit
   (`<tag>^{commit}`) is *not* reachable from `--remotes`, or skip tags that
   `git ls-remote`/`refs/remotes` already show. A simpler, more general version: skip
   bundling when `git rev-list <refs> --not --remotes` prints nothing, because that means
   no local-only commits exist.
2. Drop `refs/tags` from the namespaces collected for linked/external clones. Agents
   rarely make tags there, but this would also miss a genuinely local tag.
3. Add a regression test in `tests/workspace_provider/test_rescue.py`: a clone whose
   only refs are pushed annotated tags should give `rescue_git_repo(...) is None`.

## Cleanup

All existing `~/.sase/rescue/202610/*-linked-sase-core-*` entries hold nothing but tags.
They can be deleted safely; otherwise the reaper removes them after 30 days. You can
dismiss the notifications.
