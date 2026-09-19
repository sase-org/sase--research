# Manual deletion of `sase-core-rs` 0.34.0–0.34.9 on PyPI

_Research date: 2026-09-19. Live PyPI JSON sampled the same day._

## Question

`sase-core-rs` is at **9.991 GiB / 10 GiB**, with **~9.1 MiB** of default quota left — too little for any remaining wheel. Which releases can Bryan delete by hand, and what are the exact PyPI UI steps that free storage without breaking published `sase` pins?

## Recommendation

Delete **whole releases** `sase-core-rs` **0.34.0 through 0.34.9** from the official PyPI web UI. That is the plan's safe window: no published `sase` depends on `0.34.x`, and those ten releases currently occupy **~635 MiB** (50 files). Yanking does **not** free space. There is no supported public delete API.

Do this as the project **Owner**, on a password-protected personal machine. Do not use `pypi-cleanup` or any bulk script: a regex miss can wipe a pinned floor.

## Numbered steps

1. **Re-measure before touching anything.** Confirm the ten versions still exist and that keep-list versions are still present:

   ```bash
   python3 - <<'PY'
   import json, urllib.request
   data = json.load(urllib.request.urlopen("https://pypi.org/pypi/sase-core-rs/json"))
   rel = data["releases"]
   delete = [f"0.34.{i}" for i in range(10)]
   keep = ["0.34.48", "0.32.16", "0.12.1", "0.17.15", "0.19.0"]
   def mib(v):
       files = rel.get(v) or []
       return sum(f.get("size") or 0 for f in files) / 1024 / 1024
   print("DELETE:")
   for v in delete:
       print(f"  {v}: files={len(rel.get(v) or [])} {mib(v):.2f} MiB")
   print("KEEP (must remain):")
   for v in keep:
       print(f"  {v}: files={len(rel.get(v) or [])} {mib(v):.2f} MiB")
   PY
   ```

   Abort if any `DELETE` row is missing or any `KEEP` row is missing.

2. **Log in as the Owner.** Open [pypi.org/account/login](https://pypi.org/account/login/). 2FA is required. Maintainer cannot delete files, releases, or the project — only Owner can. If the account is Maintainer-only, stop.

3. **Open the project releases page**, not the public project page:

   [https://pypi.org/manage/project/sase-core-rs/releases/](https://pypi.org/manage/project/sase-core-rs/releases/)

   Optionally open [settings](https://pypi.org/manage/project/sase-core-rs/settings/) in another tab so you can watch used / remaining quota.

4. **Delete one whole release at a time, oldest first:** `0.34.0`, then `0.34.1`, … through `0.34.9`.

   For each version:

   1. Find that exact version on the releases list.
   2. Click **Options** next to it.
   3. Click **Delete** (the whole release). Do **not** click Yank. Do **not** click Manage (that path deletes individual files).
   4. PyPI treats deletion as a sensitive action and may ask you to re-enter your password if it has been more than an hour since the last confirm.
   5. In the confirm modal, type the **version string only** (for example `0.34.0`). Warehouse rejects the POST unless `confirm_version` matches the release exactly.
   6. Submit. Wait until that version disappears from the list before starting the next one.

   If **Delete** is missing or disabled, stop. PyPI can set an admin `DISALLOW_DELETION` flag; wait for the pypi/support limit-request issue instead of improvising.

5. **Hard stop list.** Never click Delete (or Manage → delete file) on:

   - `0.34.48` (current local `sase` floor; already an incomplete 3-file release)
   - `0.34.10` through `0.34.47`
   - any `0.32.x` (published `sase==0.17.0` / `0.17.1` pin `>=0.32.16,<0.33.0`)
   - anything older than `0.34.0` (live `sase` pins include `>=0.1.1,<0.2.0`, `>=0.12.1,<0.13.0`, `>=0.17.15,<0.18.0`, `>=0.19.0,<0.20.0`)
   - Windows wheels on versions you are **not** deleting (historical `win_amd64` on kept releases stays)

6. **Confirm quota and keep-list.** After `0.34.9` is gone:

   1. Refresh the project settings page. Used size should drop by about **0.62 GiB**; remaining default quota should be on the order of **~640 MiB** (enough for several ~65–80 MiB publishes).
   2. Re-run the inventory snippet from step 1. Every `DELETE` version should be absent; every `KEEP` version should still list files. `0.32.16` in particular must remain.
   3. `https://pypi.org/pypi/sase-core-rs/<version>/json` for each deleted version should 404.

7. **Do not republish 0.34.0–0.34.9.** Deleted filenames cannot be reused. A later complete publish must be the **current** workspace version (re-read `[workspace.package].version`; do not assume `0.34.63`). Skip backfilling `0.34.49`–`0.34.62`.

## Why these ten versions

Live JSON on 2026-09-19:

| Field | Value |
| --- | --- |
| Project | `sase-core-rs` |
| Latest published | `0.34.48` (3 files, incomplete) |
| Releases / files | 272 / 1358 |
| Total size | 9.991 GiB |
| Remaining 10 GiB quota | ~9.1 MiB |
| `0.34.0`–`0.34.9` | 10 complete 5-file releases, 50 files, **635.4 MiB** |
| Predicted remaining after delete | **~644 MiB** |

Each of `0.34.0`–`0.34.9` has macos universal2 + manylinux aarch64 + manylinux x86_64 + win_amd64 + sdist. Deleting the **whole release** is correct: those Windows files belong to unused `0.34.x` versions, not to the later historical Windows set the plan told us to leave alone.

No published `sase` release (29 versions, latest `0.17.1`) depends on `0.34.x`. Local sase currently declares `sase-core-rs>=0.34.48,<0.35.0`.

## What deletion actually does

- Official how-to: [Storage Limits → Freeing up storage](https://docs.pypi.org/project-management/storage-limits/#freeing-up-storage-on-an-existing-project).
- [Yanking](https://docs.pypi.org/project-management/yanking/) hides a release from installers unless the pin is exact `==` / `===`. It does **not** free quota.
- [PyPI help: restore](https://pypi.org/help/#deletion): deletion is permanent and irreversible. Admins will not restore a project, release, or file.
- [Filename reuse](https://pypi.org/help/#file-name-reuse): a deleted wheel/sdist name can never be uploaded again.
- [PEP 763](https://peps.python.org/pep-0763/) (72-hour deletion window) was **withdrawn** 2025-09-22. As of this research, Owners can still delete old releases.
- There is still no public JSON delete API ([warehouse#12934](https://github.com/pypi/warehouse/issues/12934)).

## Alternatives (rejected for this pass)

| Option | Why not |
| --- | --- |
| Yank `0.34.0`–`0.34.9` | Does not free the 10 GiB project quota. |
| Delete only Windows wheels across all 271 releases | Out of scope; high click count; not needed if the ten whole releases free ~635 MiB. |
| `pypi-cleanup` with a version regex | Unofficial, destructive, easy to over-match (`0.34.*` would include `0.34.48`). |
| Wait only for a 50 GiB limit increase | The support issue is not instant; default quota cannot accept the next file until something is deleted or the limit is raised. |
| Delete `0.32.x` or earlier | Breaks `pip install sase==<old>` for every published sase pin listed above. |

## After headroom exists

That is a separate publish step in `plan:202609/sase_core_pypi_size_limit.md`: dispatch Release-plz on `master` for the current workspace version (`dry_run=false`, `build_wheels=true`, `publish_pypi=true`). This note stops at deletion.
