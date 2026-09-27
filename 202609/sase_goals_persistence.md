# SASE Goals: when a goal leaves your machine, and how others see it

_Review of `research:202609/sase_goals_design/sase_goals_design.md` (§4.3, §4.5, §4.7,
§4.8) · 2026-09-27 · project: sase_

Sync claims were checked against `sase` @ `c8a7a5ed3`: the `sidecar_auto_sync` chop,
sync hints, and hidden-clone paths.

---

## Short answer

A goal becomes **shareable when it is named**, not when it is launched. It is persisted
as **immutable event files plus a `live/` marker** in a `goals/` directory of the
**beads sidecar repo** (`sase-org/sase--beads`). Each machine writes through its own
hidden host clone and publishes with `git push`.

Another user's agent on another machine sees the goal **once two things have happened**:

1. the writer pushed, and
2. the reader's clone fetched.

Only **claims** and **human settlements** are guaranteed to push immediately. Readers
fetch when `sase goal list` runs (TTL-gated) or when you pass `--fresh`. The design
promises _honest_ freshness ("synced 12 s ago"), not instant visibility.

---

## 1. One goal's journey

```text
 MACHINE A · you@athena                 GitHub · sase--beads       MACHINE B · them@apollo
 ──────────────────────────────────     ────────────────────       ─────────────────────────
 launch ─► draft ⌖7k2mq
   machine-local, never shared
 sase goal name
   created + named + live/ marker
   commit → hidden clone ─ push ⚠ ─►    goals/
 progress, attach ─ batched push ─►       live/7k2mq  ── fetch ─►  hidden clone
 claim ─► GoalVerify ── sync push ─►      items/7k2mq/             (TTL on list, --fresh)
 you verify ─► settled ─ sync push ─►       events/*.json                │
                                                                         ▼
                                                                   goals-hot.json projection
                                                                   ─► sase goal list · Goals tab
```

**On-disk layout** (§4.7), in the beads repo:

```text
goals/
  STORE.json                      schema fence
  live/<id>                       empty marker, one per UNSETTLED goal (the hot index)
  items/<id>/events/<ulid>.json   immutable events, the only source of truth
```

---

## 2. When each write becomes visible elsewhere

| What happens | Persisted locally | Leaves the machine | Seen by another user/machine |
| --- | --- | --- | --- |
| **Launch → draft** | Host, at bind time | **Never.** An adopted draft never does either. | No |
| **Name** (`sase goal name`, plan propose, finalizer fallback, auto-name) | `created` + `named` events and a `live/` marker in the hidden clone | ⚠ **Not specified** by the design | After that push *and* the reader's fetch |
| `adopted` · `edited` · `plan_attached` | Immediately | ⚠ **Not specified** | Same as above |
| `agent_attached` · `progress` | Immediately | **Batched** onto the sync tick | After the batch *and* the reader's fetch |
| **Claim** | `claimed` event committed. The claim is durable from this point. | **Synchronous**, time-bounded push. Retries fetch → rebase → revalidate. On failure it goes to the outbox with an `↑ unpublished` chip. | After the reader's fetch. The origin owner also gets a `GoalVerify` gate. |
| **Verify / reject / drop / reopen / merge** (human) | `settled`/`reopened`/… event; marker added or deleted | **Synchronous** push | After the reader's fetch |
| Running vs. Idle lane | **Not stored** | — | Derived from local and remote agent inventory, so only as fresh as agents-sync |
| Original prompt body | Stays in the agents sidecar prompt archive; the goal stores ref + digest | Naming a goal triggers prompt publication | After the agents sidecar publishes |

**Reading is always local** (§4.7). `sase goal list` runs `readdir(live/)` on the local
clone, reduces only the live goals' events, and caches the result in
`~/.sase/projects/<key>/goals-hot.json`. Settled goals are never opened, and the hot
path makes no network call. Freshness comes from three sources:

- a TTL-gated background fetch triggered by `list`;
- `--fresh`, which fetches synchronously;
- the Goals tab footer, `synced 12s ago`.

**What the other user needs:**
- **To read:** the same project registered with the same beads sidecar remote. All four
  sase sidecars are public today, so anyone can read goal titles, outcomes, and claims.
- **To write** (name, adopt, claim, settle): push access to that repo. Every event
  records its actor as `<username>.<machine>`.
- **Who gets pinged:** only the goal's origin owner gets the `GoalVerify` ping. Other
  humans see the goal in their **Review** lane.
- **Opting out:** `goals.visibility: local`, or a project without a beads/goals
  sidecar, uses a machine-local ledger (`~/.sase/projects/<key>/goals/`) that **never
  publishes**.

---

## 3. Why two machines can't corrupt a goal

- **Nothing is edited in place.** Writers only add uniquely named ULID event files and
  add or delete markers, so a `git rebase` can never hit a content conflict.
- **Marker races are settled by reduction.** A marker exists exactly when the goal's
  reduced status is unsettled.
- **Deterministic tie-breaks:**
  - Two claims on the same basis: the first ULID wins.
  - A drop that races a claim: the **drop wins**, because it is your intent.
  - An adopt that races a verify: recorded as a late attachment, and the goal stays done.
- **Cross-machine evidence.** Receipts are machine-local, so a claim **embeds a receipt
  snapshot** that machine B can render without A's files.

---

## 4. Gaps worth fixing before E1/E2 freeze the contract

1. **Naming has no push policy, and it is the event cross-machine sharing depends on.**
   - §4.7 classifies only two groups: claims and settlements (sync), and
     attach/progress (batched).
   - `created`, `named`, `adopted`, `edited`, and `plan_attached` fall in neither group.
   - Why it matters: an agent on machine B runs `sase goal list` during draft intake to
     find a goal to **adopt**. If A's name hasn't been pushed yet, B names a
     **duplicate**, and you have to `merge` it later.
   - → **Push `named` and `adopted` synchronously**, using the same bounded push and
     outbox as claims. That is about one push per outcome, roughly 30 a day.
2. **The "sidecar_auto_sync tick" can't carry batched writes today.**
   - The 30 s chop (`src/sase/scripts/sase_chop_sidecar_auto_sync.py`) only
     **fetches and fast-forwards** clean *primary* sidecar clones.
   - It never pushes, and it never touches the hidden clone where goals are written.
   - So batched progress events and outbox retries currently have **no publisher**.
   - → Add a push leg for the hidden `goals` lane, or a dedicated goals publisher chop.
3. **Remote freshness is minutes, not 30 s.**
   - Sync hints are **machine-local** (`~/.sase/sidecar_sync_hints/<project>.json`), so
     a push from A leaves no hint on B.
   - B's backstop re-checks a role at most every **5 min**
     (`_BACKSTOP_INTERVAL_SECONDS`), and it updates B's *primary* clone, not the hidden
     one.
   - The cld report's "next 30 s tick with publisher hints" holds only on the
     publishing machine.
   - The real cross-machine guarantee is the TTL fetch inside `sase goal list`.
4. **Pin which clone readers use, and read fresh at the one moment that matters.**
   - Readers should use the **hidden clone**.
   - The draft-intake `sase goal list` should do a bounded `--fresh` fetch. A stale read
     at intake is exactly where cross-machine duplicates come from.
5. **Draft storage has no stated path.** Drafts are "machine-local only," but the design
   doesn't say where their state lives. `sase goal list` on the same machine needs to
   find them. This is minor, but E1 should name the path.

---

## 5. In one line

> **Named → pushed → fetched.** Drafts stay home. Claims and verdicts travel
> immediately. Everything else travels on a batch the design has not yet wired up. A
> remote reader is as current as its last fetch, and the Goals tab tells them exactly
> how current that is.
