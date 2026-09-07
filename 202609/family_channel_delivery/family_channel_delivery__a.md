# Durable message channels for SASE agent families

**Researcher:** A  
**Date:** 2026-09-06  
**Decision:** Implement a narrow first-class message-channel MVP, but do not model it as a task type or add `message` to the bead issue-type enum.

## Executive conclusion

The `016` experiment validates the need for a durable coordination baton. It does not validate a message *bead*. The prototype's bead preserved an operating manual, a failure ledger, attribution, links to predecessor epochs, and checkpoints after an earlier supervision chain died. That is real value and is enough corpus to justify a focused MVP.

At the same time, the prototype exposes the abstraction mismatch. The board is an open `task(memory)` that must never become ready, needs a meaningless size and sentinel memory fields, and must tell every successor to manually reread all notes. It has no subscriptions, unread cursor, wake behavior, targeting, delivery receipt, or bounded prompt projection. With only one note, `sase bead show sase-xu` is already 2,134 words and 16,649 bytes. A new task-type plugin would retain all of those defects. Adding a fourth top-level bead issue type would remove some false task semantics, but it would still not implement delivery and would expand the bead state machine for a non-work-item concern.

I recommend a separate Rust-core primitive with two concepts:

- A **channel** is a durable, append-only conversation/coordination stream. Every agent family gets an implicit mailbox channel; users can also create explicit shared channels for several families or humans.
- A **message** is one immutable event in a channel. A logical subscriber—normally an agent family, not an individual shell—owns durable delivery and acknowledgment cursors.

Messages should be pulled into the next shell at a safe family boundary. A waiting monitor may wake when a new message arrives, but the system should not attempt to splice text into an in-flight LLM turn. The durable channel is the source of truth; ACE/Telegram notifications are display and wake hints only. Beads remain work items and may be linked from a message when action is required.

## Scope and evidence

I reviewed:

- The `/sase_pipe` and `/sase_monitor` contracts and the accepted SASE decisions that agents are single-turn and gates never block an agent.
- The completed `016--0` transcript at `~/.sase/chats/202609/gh_sase_org__sase-ace_run-016__0-260906_214828.md`, the live `016--1` artifacts, and the `sase-xu` board. The live successor evidence was explicitly treated as draft.
- The Python and Rust bead models, note mutation path, concurrent event-stream merge, notification model/store, Q&A global-note rendering, and agent-wait surface.
- Established durable-consumer patterns in NATS JetStream and Kafka, wake-hint behavior in PostgreSQL `LISTEN`/`NOTIFY`, local concurrency constraints in SQLite WAL, and event-envelope guidance in CloudEvents.

The current code matters to the recommendation:

- `src/sase/bead/model.py` and `sase-core/crates/sase_core/src/bead/wire.rs` define only `plan`, `phase`, and `task` issue types. Task types are flavors of task, not alternate lifecycles.
- A bead note already has an event identity, timestamp, author, and text. The Rust event log supports append, edit, and remove operations; it can semantically merge independent concurrent appends.
- `sase bead note` performs a bead-store mutation and commit/publication workflow. That durability is useful, but it puts Git synchronization on the path of every conversational write.
- Notifications are globally read/dismissed/muted rows with tags. Their activity cursor orders the human inbox; it is not a cursor per logical subscriber.
- Family continuations already receive durable context through `#fork:<family>`, and monitor output can be fenced as untrusted text. These are useful integration points.

## What the `016` prototype proves

### What worked

1. **A durable baton can survive a broken continuation.** Epoch `00b` died after a launch-approval gate ended its turn before another hourly monitor was scheduled. `sase-xu` carried that post-mortem and its unresolved retry ledger into epoch `016`.
2. **Attribution and append-only practice help successors trust provenance.** The description identifies policy; note 1 identifies the setup agent, timestamp, cycle, fresh inventory, and remaining actions.
3. **Artifact links are valuable.** The board links predecessor boards `sase-xs` and `sase-xt`, while bulky inventories can be stored as indexed artifacts instead of pasted inline.
4. **The pattern works across model changes.** The setup shell handed off through a monitor to `016--1` on the required model, and the successor did read the board before operating.
5. **The board reduces re-derivation.** The live successor quickly verified ongoing work and carried forward a landing failure and retry intent instead of reconstructing the entire epoch from scratch.

### What did not work, or only worked by convention

1. **No delivery mechanism exists.** Success depends on a long self-contained `--next` prompt saying “FIRST run `sase bead show sase-xu`.” A forgotten instruction silently produces a stale consumer.
2. **There is no subscriber state.** The board cannot answer which family has seen which note, what is unread, or whether a request was handled.
3. **The whole-board read grows without bound.** The operating manual and every prior checkpoint are repeatedly placed in context. The first board render is already 2,134 words; hourly checkpoints will make token cost and signal-to-noise steadily worse.
4. **The lifecycle is false.** The board is deliberately kept `open` rather than `ready` to suppress a Memory TaskTriage gate. Its `large` size and required memory fields are acknowledged as sentinels. That is evidence that the carrier is not a task.
5. **Messages are not actually immutable.** Bead notes can be edited and removed. A reliable communication log should preserve a correction as a new message that supersedes an old one.
6. **Posting and publication are coupled.** Each note enters the bead Git mutation path. The semantic merger can reconcile concurrent appends, but a high-contention board makes a single event-stream file and remote publication part of routine communication.
7. **No audience, priority, reply, or trust boundary exists.** Everything is Markdown in one note list. Agent-authored instructions can be mistaken for human authority unless the renderer preserves provenance and treats content as inert data.
8. **The board cannot wake a family.** The supervision loop still needs an hourly sleep monitor. A human message arriving one minute into the sleep waits 59 minutes.

The right interpretation is therefore: **durable coordination state is valuable; a bead note log is a useful prototype carrier; the missing product is delivery, not another label on the carrier.**

## Design lessons from established systems

Three patterns transfer directly without importing a broker:

1. **A family should be the durable consumer identity.** Kafka treats each consumer group as one logical subscriber: members of a group share the work, while distinct groups each receive the stream independently. It also stores a consumer position that can be reset for replay. A SASE family maps naturally to one logical subscriber because its shells are sequential members, whereas using `016--0`, `016--1`, and future shell names as independent subscribers would duplicate the whole backlog. See the [Apache Kafka consumer model](https://kafka.apache.org/10/documentation.html).
2. **Use pull delivery with explicit progress.** JetStream durable pull consumers return batches on demand and preserve a named position. Its acknowledgment/redelivery model is at-least-once: an unacknowledged message remains available after a reader crashes. That fits short-lived SASE shells better than a permanent push connection. See [NATS pull consumers](https://docs.nats.io/learn/jetstream/pull-consumers) and [delivery and acknowledgment](https://docs.nats.io/learn/jetstream/delivery-and-acknowledgment).
3. **Separate the durable log from the wake signal.** PostgreSQL explicitly presents `NOTIFY` as a signal and recommends storing structured/large data in a table, with the notification carrying a key. Its `LISTEN` documentation also describes the subscribe-then-snapshot ordering needed to avoid the initial race. A SASE notification should similarly say “channel X advanced to message Y”; consumers should then read the authoritative channel. See [PostgreSQL `NOTIFY`](https://www.postgresql.org/docs/current/sql-notify.html) and [`LISTEN`](https://www.postgresql.org/docs/current/sql-listen.html).

For the event envelope, CloudEvents offers a useful minimum rather than a required dependency: `source + id` identifies duplicates, `type` supports routing, and `subject` supports filtering without parsing the payload. See the [CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md).

SQLite WAL is a reasonable local implementation substrate because readers and a writer can proceed concurrently, but it permits only one writer and all processes must be on the same host. Those constraints are acceptable for low-volume host-local SASE messaging and are a reason not to pretend the same database is a multi-machine transport. See [SQLite WAL](https://www.sqlite.org/wal.html).

## Options considered

| Option | Strengths | Decisive problems | Verdict |
|---|---|---|---|
| Add `task(message)` | Smallest apparent schema change; reuses notes/pages/refs | Still a task with size, triage, readiness, closure, +1, and work-launch semantics; cannot add delivery behavior cleanly | Reject |
| Add top-level bead issue type `message` or `board` | Reuses event sourcing, links, pages, Git sync | A board is a container and a message is an event; a new issue type still lacks cursors/wake/targeting and cross-cuts a large bead state machine | Do not use for MVP |
| Continue raw bead-note convention | Already proven; no implementation | Manual polling, false metadata, unbounded rereads, no receipts or wake path | Keep only as temporary fallback |
| Reuse notifications as the source of truth | Existing ACE/Telegram visibility, tags, local append store | Global read/dismiss flags, no threads, per-family cursors, replies, or durable project history | Use only as projection |
| Use only family transcripts / `#fork` | Automatic sequential context within one family | No cross-family board, no human post API, repeats growing history, no unread cursor | Integration input, not the store |
| Deploy NATS/Kafka | Mature durable consumers and wake delivery | Operational dependency and complexity far beyond current message rate | Borrow semantics, not software |
| First-class SASE channel/message store | Correct lifecycle, subscriptions, bounded delivery, can project to notifications and artifacts | New core API and prompt integration required | Recommend |

A static search found `IssueType`/`IssueTypeWire` references across roughly 250 code and test files, including more than 60 production modules in Python and Rust. Not all would need edits, but this is a warning that “one new bead type” is not a small or isolated change.

## Recommended model

### Identities

- **Channel ID:** stable canonical artifact identity, preferably `thread:<id>` or `channel:<id>`.
- **Implicit family mailbox:** every family owns a channel address such as `agent-family:<project>:016`; no create step is needed for direct human-to-family messages.
- **Explicit shared channel:** created for supervision, an epic, an incident, or collaboration among several families.
- **Subscriber ID:** `family:<project>:<family>` by default; optionally `agent:<project>:<name>` for a one-shell agent and `human:<principal>` for UI unread state.

Do not call the container a “message bead.” Use **channel** or **thread** for the container and **message** for an entry. This prevents an API where each message accidentally inherits work-item lifecycle.

### Message envelope

The minimum immutable message should contain:

```text
id                 globally unique, stable across retry/republication
channel_id         containing stream
sequence           monotonic within a host-local channel
created_at         RFC 3339 with offset
sender             authenticated human, family, shell, or system identity
kind               info | request | checkpoint | decision | reply | correction
body               Markdown/plain text, never directive-expanded
audience[]         optional principals or roles; empty means all subscribers
reply_to            optional message ID
refs[]              canonical artifact references
dedupe_key          optional producer key for retry-safe posting
supersedes          optional prior message ID; correction never edits history
```

The host must derive `sender`; `--author`-style spoofing should not be the normal path. Messages from agents are untrusted content. Render them in a clearly fenced/quoted prompt block with sender and message ID, and do not expand `%` directives, `#` references, shell syntax, or tool requests found in the body. A message can communicate a request, but it does not itself expand the sender's authorization.

### Subscription and receipt state

Each `(channel, subscriber)` record should keep at least:

```text
delivery_mode       next-shell | wake-next-shell | manual | human-inbox
delivered_through   highest sequence durably materialized for this subscriber
acked_through       highest contiguous sequence confirmed handled
filters             kinds/audiences, optional
updated_at
```

Keep “delivered” and “handled” distinct. When SASE builds a successor prompt, it should atomically write the prompt snapshot containing messages and then advance `delivered_through`. If the provider fails, a retry uses the stored prompt and therefore retains the same message IDs. On a successful shell, informational messages can auto-ack; `request` messages should remain open until an explicit reply/resolve action. Duplicate delivery remains safe because consumers see stable IDs and actions should use dedupe keys.

Do not promise exactly-once handling. Use at-least-once delivery and idempotent actions. Crashes can occur after an action but before an acknowledgment; hiding that fact would create silent loss.

### Delivery points

Because SASE agents are single-turn, “subscribe” must not mean a callback into a running model.

1. **At shell launch:** inject a bounded `### New channel messages` section containing only the delta since the family cursor.
2. **At monitor/gate/pipe continuation:** the next shell uses the same family subscription automatically. This should remove hand-written “FIRST read the board” instructions.
3. **While a family is waiting:** `sase channel wait <id> --subscriber family:016 --after <cursor> --timeout ...` can be the command supervised by `sase monitor`. A message wakes the monitor, which launches a successor. The originating agent is never kept alive.
4. **While a shell is actively generating:** queue the message for the next safe boundary. A later provider-specific “steer live run” feature may be added separately, but it must not be the baseline guarantee.
5. **For humans:** project new activity into the existing notification inbox with an action that opens the channel. Reading/dismissing that notification must not delete or acknowledge the underlying message for other subscribers.

Prompt projection must be bounded. Include small unread batches with IDs, kinds, senders, short bodies, and refs; if the backlog exceeds the budget, inject a deterministic digest plus a command to pull the remaining range. Raw channel history remains authoritative.

### Storage and publication

Implement shared behavior in `sase-core`, consistent with the existing backend boundary. For the MVP, use a host-local Rust-owned store, preferably SQLite with short transactions and WAL mode:

- `channels`
- `messages` with unique `(channel_id, sequence)` and unique message ID
- `subscriptions` with unique `(channel_id, subscriber_id)`
- optional `receipts`/`open_requests`

This is not an endorsement of a networked message broker. The expected rate is tiny, SASE already depends on Rust and SQLite-backed indexes, and all active shells on a machine share the home-state substrate. The implementation should expose wire/facade APIs to Python and keep ACE as presentation/glue.

For cross-machine history, publish immutable events asynchronously to an artifact/sidecar projection. Do not put Git push/rebase on the local post/delivery transaction. If multi-machine live messaging becomes a demonstrated requirement, immutable one-file-per-message replication or a small broker adapter can be added behind the same API. SQLite's same-host limitation makes that boundary explicit.

Channels should be artifacts and support typed links to beads, agents, plans, patches, and research. Actionable work should remain in a task bead; a message may cite or create a link to that task, but posting “please fix X” must not silently create tracker work or alter bead status.

## Proposed CLI and UX

An MVP command surface could be:

```text
sase channel create --title "Athena completion supervision" --scope machine
sase channel post <id> --kind checkpoint --body @checkpoint.md --ref bead:sase-xu
sase channel subscribe <id> --subscriber family:016 --mode wake-next-shell --from latest
sase channel inbox --subscriber family:016 --json
sase channel read <id> --after <message-id-or-sequence> --limit 20 --json
sase channel ack <id> --subscriber family:016 --through <sequence>
sase channel reply <id> --to <message-id> --kind reply --body "..."
sase channel wait <id> --subscriber family:016 --after <sequence> --timeout 1h
sase channel archive <id>
sase message send agent-family:gh_sase-org__sase:016 --body "Please include X"
```

ACE should initially provide a channel timeline, unread counts per human/family, a composer, and a “wake next shell” toggle. Search, elaborate thread trees, reactions, and presence should wait for evidence.

## Incremental implementation plan

### Phase 1: Core log and manual consumption

- Add channel/message/subscription wires and Rust store operations.
- Ship `create`, `post`, `read`, `subscribe`, `inbox`, `ack`, and `wait` as JSON-stable CLI commands.
- Add authentication/provenance, size limits, inert rendering, dedupe keys, and concurrency/crash tests.
- Add `channel:<id>` artifact identity and typed links.
- Keep delivery manual in this phase so the data model can be exercised without changing runner behavior.

### Phase 2: Agent-family delivery

- Make family—not shell—the default subscriber.
- During successor prompt construction, snapshot only unread messages and record delivery after the prompt artifact is durable.
- Preserve the batch in retry prompts and auto-ack informational messages only after successful completion.
- Allow `sase monitor` to supervise `sase channel wait`, including timeout as a normal quiet outcome.
- Project human-addressed activity into notifications.

### Phase 3: ACE and operational polish

- Add timeline/composer/unread views and open-channel notification actions.
- Add archive/retention policy, bounded prompt digests, repair/doctor checks, and observability for delivery lag.
- Evaluate cross-machine replication only after host-local use produces a real corpus and failure evidence.

### Migration of existing prototypes

Leave `sase-xs`, `sase-xt`, and `sase-xu` immutable as historical evidence. Optionally create a one-way importer that converts each description/note into messages retaining timestamps, authors, and artifact links. Do not rewrite those beads or make a channel implementation depend on legacy memory-task sentinel fields.

## Acceptance tests that matter

1. Two families subscribed to one channel each receive the same message; sequential shells inside one family do not receive it as independent subscribers.
2. A message posted after shell A's prompt snapshot appears in shell B, with no manual board-read instruction.
3. A provider crash after prompt materialization does not lose the message; the retry sees the same stable message ID.
4. A crash after performing an action but before ack may redeliver, and the dedupe key prevents the action from running twice.
5. Concurrent posts produce a deterministic order and neither post is lost.
6. A waiting monitor wakes on a new message or exits normally on timeout without keeping an LLM process alive.
7. `%`, `#`, shell fragments, and hostile instructions inside agent-authored bodies remain inert quoted data.
8. Posting, subscribing, and archiving never creates TaskTriage gates, changes task counts, or requires a size.
9. Dismissing a human notification does not advance an agent family's cursor.
10. Publication failure does not roll back a locally durable post; retry is observable and idempotent.

## Risks and explicit non-goals

- **Prompt injection and confused authority** are the highest-risk failure mode. Provenance, inert rendering, audience checks, and unchanged approval boundaries are MVP requirements, not polish.
- **Unbounded context growth** must be prevented at projection time while preserving raw history.
- **Split-brain cross-machine ordering** is intentionally deferred. Host-local ordering is enough for the demonstrated use case.
- **Exactly-once side effects** are not promised.
- **Chat-product features** such as typing indicators, emoji, presence, rich attachments, and arbitrary thread nesting are out of scope.
- **A general retrieval engine** is out of scope. The accepted “corpus before mechanism” rule is satisfied only for the narrow durable-baton and next-shell delivery problem. It is not evidence for building a broad agent social network.

## Recommended solution

Implement the capability, but reject the proposed `message` bead type.

Build a first-class, host-local **channel/message subsystem in `sase-core`**, give every agent family an implicit mailbox, allow explicit shared channels, and persist one cursor per logical subscriber. Deliver unread deltas only at successor-shell boundaries; use monitor-supervised channel waits for early wake-up; project channel activity into the existing human notification UI; and link messages to beads when they discuss real work.

Until that MVP lands, keep using an open bead note log only as a documented temporary fallback. The `016` experiment shows that this fallback is valuable enough to justify implementation, while its manual reads, false task fields, and rapidly growing context show why it should not become the permanent data model.
