# Durable family channels for SASE agents

Research synthesis · 2026-09-07 UTC / 2026-09-06 America/New_York

**Recommendation: implement a small, opt-in channel capability with durable family subscriptions and bounded next-shell delivery. Keep it separate from bead types.** The `016` experiment supplies enough evidence for this narrow feature; it does not justify a general agent forum, broker deployment, or automatic agent activation on every post.

Researcher A supplies the stronger delivery model. Researcher B supplies the stronger critique of scope and context cost. Independent review identifies several integration and correctness problems with B's proposed xprompt-only implementation, and narrows A's relatively broad MVP. The resulting first release should make one promise: **a message posted to a subscribed channel remains discoverable across handoffs and failures, and the human can distinguish pending delivery from acknowledged receipt.** It cannot promise that a running model immediately changes course.

## What the experiment establishes

Both researchers inspected the `016` supervision experiment and its predecessor boards. They independently report that the board preserved a charter, checkpoints, failure evidence, and retry intentions across broken supervision sequences. Stable identity, attributed entries, artifact references, and a human write surface were useful. The current carrier was an open `task(memory)` deliberately kept out of triage, with placeholder memory fields and a planning size unrelated to the board's purpose. [A](family_channel_delivery__a.md), [B](family_channel_delivery__b.md)

The strongest quantitative evidence is about payload size, not traffic. B reports roughly 110 KB for a rendered `sase-xs` board, including a roughly 70 KB note containing a raw agent inventory, and about nine messages over three hours across the prototypes. A and B report roughly 17 KB for a render of `sase-xu`. These are researcher snapshots, not new measurements or a load test; their note counts differ with observation time. B's token estimates are approximations, and its twelve-subscriber example is hypothetical. Nevertheless, the direction is clear: repeatedly injecting full inventories and operating manuals is wasteful even at very low message rates. [A](family_channel_delivery__a.md), [B](family_channel_delivery__b.md)

The reports attribute two earlier supervision interruptions to launch-approval handoffs occurring before the next hourly monitor was arranged. This is evidence about continuation ownership, separate from communication. The board helped recovery; it did not schedule recovery. An improved board alone would leave that failure mode intact. [B](family_channel_delivery__b.md)

Three requirements should remain distinct:

| Need | Existing help | Remaining gap |
|---|---|---|
| Carry work through sequential shells | Family history, `#fork`, pipe and monitor follow-ups | Compact current state; delivery independent of remembered prompt instructions |
| Let a human steer a running sequence | Gates and explicit follow-up prompts | Stable destination, pending messages, observable receipt |
| Exchange findings between families | Beads and shared artifacts | Optional shared channel with independent subscriber progress |

Shared messaging is plausible, but evidence that unrestricted conversation improves SASE outcomes is limited. Anthropic's forum experiments found benefits in some exploration settings, but also coordination failures and premature consensus. Its vulnerability comparison was confounded by different search scopes; it is not clean proof that a forum improves efficiency. This supports a focused trial with outcome measurements, rather than assuming more communication is better. [Anthropic research](https://www.anthropic.com/research/multiagent-systems)

## Where the reports need correction

### A prompt renderer is useful, but is not a family subscription

B proposes a `#board` workflow modeled on `#fork`, with no core or runner change. That can demonstrate a bounded view over existing notes. It does not automatically provide inherited subscriptions, durable progress, or correct timing on every launch path.

Independent inspection found:

- `src/sase/xprompt/processor.py:80` explicitly singles out `fork` in `LAUNCH_DEFERRED_XPROMPT_NAMES`. A new workflow does not acquire all of `fork`'s behavior by resembling its YAML.
- `src/sase/axe/run_agent_runner.py:172` resolves deferred context after dependency admission **but before waiting for a runner slot**. Even that boundary can leave a snapshot stale while capacity is unavailable. B's observed prompt-file timestamps do not establish a universal just-before-provider delivery guarantee.
- `src/sase/monitor/followup_prompt.py:200` wraps the follow-up body in a disabled region. The monitor skill explicitly says `--next` is literal. Consequently, putting `#board(...)` inside the proposed monitor successor text does not invoke it.
- A fresh pipe can discard conversation context. Subscriptions carried only in prose or previously expanded history are not reliable family metadata.

**Resolution:** allow an xprompt as optional display syntax or a disposable read-only experiment. Implement the promised subscription in host-owned family state, with message snapshotting after admission and as close as practical to the provider invocation. Keep it independent of whether a predecessor remembered a reference. See the source inventory below.

### Single-turn execution does not rule out durable receipts

B overstates the constraint when it rules out at-least-once delivery, acknowledgments, and all messaging between running agents. A running shell can perform a finite read tool call. More importantly, a host-owned store and monitor can persist after the model exits; the subscriber need not be a permanently running LLM.

The portable baseline is next-shell injection plus voluntary reads. Unsolicited mid-generation injection is a separate provider capability and should not be promised. Durable pull-consumer progress and redelivery are established patterns precisely because individual workers can exit or crash. [NATS pull consumers](https://docs.nats.io/learn/jetstream/pull-consumers), [NATS acknowledgments](https://docs.nats.io/learn/jetstream/delivery-and-acknowledgment)

Likewise, family history is not intrinsically destroyed when a chain ends: `#fork` can resolve prior named conversations and families. The board improves discoverability, compactness, shared writes, and continuity independent of choosing a transcript; it is not the only means of historical recovery.

### Timestamp filtering and truncation can silently lose messages

B suggests selecting notes with `timestamp > cursor`. The Rust reducer explicitly documents that events appended to a stream can have timestamps earlier than previous entries; stream position preserves causal order (`crates/sase_core/src/bead/events.rs:1415`). Tied timestamps, late merges, edits, and removals compound the problem. Stable note IDs are useful identities but are not automatically monotonic delivery offsets.

Its suggested combination of dropping oldest messages and echoing the newest ID is also unsafe: advancing past the newest displayed entry could permanently skip omitted requests.

**Resolution:** use a monotonic sequence assigned at local append commit, plus stable message IDs for retries. Read bounded contiguous batches; never acknowledge an omitted range. If prototyping against beads, use an explicit ID/version ledger or tolerate replay and label the limitations. Do not present a timestamp filter as reliable delivery.

### Scheduling a monitor first cannot preserve the rest of the same turn

B recommends starting the next monitor and then investigating or launching work. The monitor skill says successful startup terminates its caller. There is no subsequent agent work in that turn.

**Resolution:** persist the checkpoint before the handoff and put continuation into the mechanism that actually ends the turn. If an approval branch ends the turn, its recorded outcome must carry the next action. For recurring fleet supervision, prefer a host-owned AXE schedule that launches bounded reasoning cycles and observes pending approvals. This needs normal admission, non-overlap, and deduplication; it is not a way to bypass launch approval. A plain proc alone does not establish those scheduler guarantees.

### Attribution, rendering, and authority are different

B would rank an operator-authored note as an instruction. Current bead note APIs accept an author override (`src/sase/bead/cli_crud_evidence.py:138`); an author string is insufficient proof of human origin. Disabled-region escaping prevents SASE macro, file-reference, and command expansion. It does not make arbitrary prose harmless to an LLM or authenticate its sender.

**Resolution:** carry host-recorded sender provenance separately from body text and claimed authorship. Human steering requires a trusted user ingress and explicit scope. Peer posts remain evidence or requests, not authorization. Current permissions and gate decisions still govern actions. On a shared Unix account, metadata alone is not an adversarial security boundary.

## Why a dedicated bead type is the wrong first implementation

The proposal has two possible meanings. `task(message)` inherits task triage, sizing, readiness, and work-launch behavior. A new top-level `message` issue type could deliberately introduce different rules, but then it expands the bead lifecycle, validators, projections, and tooling. Neither choice supplies subscriptions, bounded delivery, or receipts by itself.

Both the Python model and Rust wire enum currently distinguish plan, phase, and task. The researchers' differing symbol-reference counts are not implementation estimates; the checked validation rules are stronger evidence of coupling. A board is a durable container, and a message is an entry. Modeling either as actionable work obscures its lifecycle. Reusing internal event or artifact utilities is reasonable without giving messages bead semantics.

| Option | Appropriate use | Decision |
|---|---|---|
| Existing bead notes and artifacts | Temporary, manually consumed board | Keep as fallback; use short entries and payload references |
| `#board` over notes | Cheap experiment in prompt size and readability | Optional; do not call it reliable subscription |
| Dedicated bead/task type | Cosmetic naming or a broader bead redesign | Reject for this feature |
| Notifications as storage | Human attention and channel shortcuts | Projection only; dismissal must not consume family messages |
| Small channel subsystem | Family continuity, bounded delivery, visible progress | Recommended first product slice |
| Broker or general forum | Distributed live messaging at demonstrated scale | Defer |

The case for a channel is semantic and operational, not a prediction of high throughput. Three messages per hour do not justify infrastructure optimized for chatter. They can still justify preventing a human correction from disappearing at a handoff.

## Recommended behavior and architecture

### Address the sequence, retain a board independent of it

Start with explicit named channels and **opt-in subscriptions**. A family is one logical subscriber; its sequential shells share progress. Two families subscribed to a channel each receive the posts. A single-shell agent should retain its subscription if promoted into a family.

Use an internal stable identity containing owner/host/project context and a family identity or generation, with friendly names as lookup aliases. A bare `016` string or workspace path should not be the durable key. A replacement family can subscribe to the existing board after a failure, choosing a starting point; it must not silently inherit another family's acknowledgments. The channel outlives its subscribers.

Keep one channel timeline for human and agent posts, preserving provenance. A lazily created private family mailbox can later be convenient syntax, but automatically provisioning mailboxes for every run is unnecessary in the first release. Host-local storage can serve channels spanning projects; channel scope and access policy must be explicit rather than inferred from the active directory.

### Use a small immutable envelope

The initial record needs a stable ID, channel ID, local sequence, timestamp, sender provenance, kind, body, artifact references, and optional `reply_to`/`supersedes` IDs. A producer idempotency key makes retrying a post safe. Keep kinds small: information, request, checkpoint, reply, correction. Use new events for corrections and retractions.

Put the reusable charter in a referenced document. A checkpoint carries current conclusions and links, not a fresh operating manual or raw fleet dump. Make request closure explicit through a reply; durable work still belongs in a linked task bead. A message can request work without silently assigning it, launching an agent, or changing task status.

### Separate delivery, acknowledgment, and fulfillment

The human-visible states should have precise meanings:

| State | What SASE can establish |
|---|---|
| Pending | Persisted, awaiting a subscriber's eligible shell |
| Included | Exact message IDs were materialized into a particular prompt batch |
| Acknowledged | The receiving agent explicitly recorded receipt of those IDs |
| Answered | A reply records the disposition of a request; it may link to ongoing work |

Prompt inclusion is not proof that the model understood or obeyed an instruction. An exit code or successful finalizer is not proof either. Avoid A's automatic acknowledgment based solely on successful shell completion.

Store batches durably with exact message IDs and rendering parameters. Make materialization retryable: prepare the batch, persist the prompt artifact, then record inclusion. A crash between those steps must recover or replay the batch without advancing acknowledgment. Do not assume a database update and a filesystem write are automatically one transaction. An intentional pipe/monitor/gate handoff should record receipt before termination; unacknowledged input remains available to the successor.

For the first release, contiguous batches and explicit batch acknowledgment keep progress simple. Track unresolved requests separately so one unanswered question does not block later information. Acknowledgment means receipt, not execution. At-least-once delivery permits duplicates; a message dedupe key prevents duplicate posts, **not arbitrary duplicate external actions**. Where a consequential operation supports an idempotency key, pass one; otherwise recovery must inspect its actual result before repeating it. [NATS acknowledgment model](https://docs.nats.io/learn/jetstream/delivery-and-acknowledgment)

### Bound delivery without hiding important backlog

Select channel deltas after runner admission and before provider invocation, recording the snapshot boundary. Posts committed afterward remain pending for the next read or shell. Subscriptions must survive normal completion, pipe, fresh pipe, monitor and gate transitions, and workspace-claim recovery.

Use a configurable aggregate prompt budget across all subscribed channels, not merely a limit per channel. An initial trial value such as 8 KiB and ten entries is a tuning hypothesis, not a measured optimum. Keep metadata and overflow notices within that budget. Use fair batching across channels, visible pending counts, and commands for the next range. Oversized content needs an artifact pointer; an omitted body must not be marked acknowledged automatically.

Preserve full raw history. Summaries and checkpoints can aid navigation but should not erase unresolved requests or substitute for exact delivery bookkeeping. Family transcripts may themselves grow; bounded channel injection alone does not compact `#fork` history.

### Wake only when a family has explicitly chosen to wait

The first version should queue for the next shell and support finite explicit reads. If no continuation is scheduled, say so: a pending message does not imply eventual processing by a terminated family.

A later monitor-supervised channel wait can end on a new post or timeout, then launch one ordinary successor. The listener must register and recheck durable state to close the lost-wakeup race; wake signals are hints, and periodic rechecks provide recovery. This follows the subscribe-then-inspect pattern documented for PostgreSQL notifications. [PostgreSQL LISTEN](https://www.postgresql.org/docs/current/sql-listen.html), [NOTIFY](https://www.postgresql.org/docs/current/sql-notify.html)

Do not interrupt an arbitrary build/test monitor because someone posted a message. Preserve one active shell per family, coalesce bursts, obey launch admission, and make timeout/post races settle once. Human stop/cancel and gate approvals stay on their existing control surfaces. A board is unsuitable for urgent cancellation that must take effect before the next shell.

### Persist locally; publish history separately

Shared channel, cursor, receipt, authorization-policy, and selection behavior belongs in `sase-core`. Python provides orchestration/adapters and presentation. A pure display experiment can use existing APIs; a shared subscription protocol is not presentation-only code.

Prefer a small SQLite store outside ephemeral workspaces for messages, subscriptions, and batches. Its transactional constraints are useful for consistency, not throughput. WAL supports concurrent readers and a writer, with one writer at a time and same-host access. Configure durability deliberately: WAL with `synchronous=NORMAL` can lose recent commits on power failure; a claim of durable local posting requires an appropriate policy such as `FULL`, plus tested recovery. Do not place the live database on a shared network filesystem. [SQLite WAL documentation](https://www.sqlite.org/wal.html)

A locked JSONL implementation is possible at this volume, but must still solve atomic sequence assignment, cursor/batch updates, torn writes, and recovery. It is not automatically simpler once reliable delivery is included.

Expose the channel through the artifact system for audited reads and links. Publish immutable history asynchronously through a retryable outbox and show publication lag. Unlike a notification, the message log is authoritative: **local durable acceptance and remote publication are different guarantees**. Host loss before publication can lose the unreplicated tail. The existing collaboration research's distinction between durable artifacts, live process state, and attention helps keep those claims honest; it does not justify treating messages as disposable projections. [Prior collaboration analysis](../sase_collaboration_architecture.md)

Archive explicitly and retain raw messages through the trial. Prompt bounding is not retention. Any later pruning policy must preserve unread/unacknowledged input, unresolved requests, and referenced records, or explicitly report that replay is unavailable.

## What to build first, and how to decide whether to keep it

Implement one vertical slice: explicit channel creation/posting/reading, family subscribe/unsubscribe, durable batches and receipt acknowledgment, automatic bounded next-shell injection, and a human view of the timeline and pending/included/acknowledged state. Exact CLI spelling should follow SASE's normal CLI conventions; `#board` can be a convenience over the same core API. Do not ship the store alone and call delivery a later detail.

Defer early wake, implicit mailboxes everywhere, complex filters, thread trees, semantic search, automatic task creation, and cross-machine live transport. Keep existing prototype beads as historical evidence; transfer only the charter reference and a reviewed current checkpoint when beginning a new channel. No bulk import is required to test the feature.

Independently, make recurring supervision host-scheduled or ensure every actual turn-ending branch records the next action. The schedule must notice an active family or pending gate and avoid repeatedly launching replacements. Fixing this is useful even if the channel trial is rejected.

Exercise the following before adopting it for important steering:

1. A human post during a provider run reaches the next shell; a post during a runner-slot wait reaches the snapshot taken after admission.
2. Subscriptions survive fresh pipe, monitor/gate handoff, single-agent promotion, and workspace recovery. A new family can join an existing channel without erasing prior receipts.
3. Two families receive independent copies. Concurrent posts, identical timestamps, and producer retries neither lose nor multiply stored messages.
4. Crashes before/after prompt persistence and before/after acknowledgment yield an explainable pending or replay state. A handled external action is not assumed safe to repeat.
5. Aggregate prompt limits never skip unacknowledged ranges. Overflow, an oversized entry, and an unresolved request remain visible.
6. Author overrides cannot impersonate authenticated human steering; macro-looking bodies remain literal; dismissing a notification never acknowledges another subscriber's message.
7. A dead family, pending gate, or unavailable provider is shown honestly rather than as eventual guaranteed delivery. Publication failure preserves accepted local messages and exposes lag.

Run the trial over several supervision cycles including a forced handoff failure and a real operator correction; use a second subscriber when useful. Measure missed messages, replay frequency, receipt latency, prompt bytes, manual reminders, duplicate actions, and whether communicated information changed the next cycle's decisions. These are adoption criteria, not claims of measured performance.

Continue investment if automatic delivery reduces manual coordination and survives those failure cases. Stop at bounded manual views if messages rarely change decisions and receipts add little value. Early wake is justified by observed latency pain; additional transports by an actual cross-host requirement. Arbitrary thresholds such as a fixed number of unrelated use cases or one post per minute are not established evidence.

## Evidence and provenance

The two distinct inputs were matched by dispatch dependency and their existing suffixes, not list order. Both were read through `sase artifact read` before relocation. The source copies in this research checkout retain their complete bytes; stored snapshots and other workspaces were not modified.

| Input | Preserved report | Original canonical reference | Immutable snapshot |
|---|---|---|---|
| `research.1j.cdx`, A | [Report A](family_channel_delivery__a.md) | `research:202609/agent_family_message_channel_design__a.md` | `file:explicit:2c8c3725a18b1941666b4749` |
| `research.1j.cld`, B | [Report B](family_channel_delivery__b.md) | `research:202609/agent_message_board_and_family_channels__b.md` | `file:explicit:ac09e6cfc52c2e48b306db0a` |

Independent work consulted the pipe and monitor skills; audited reference memory on artifacts, beads, xprompts, family/shell definitions, AXE scheduling, single-turn execution, nonblocking gates, the Rust boundary, and corpus-before-mechanism; and an audited read of the prior collaboration report. No predecessor chat transcript was read. Prototype observations above are attributed to A/B: an attempted audited live `bead:sase-xu` read could not resolve a published page, so it did not provide additional direct evidence.

Code inspected at SASE revision `09c93253dc76bb71c71ee4e855de7998172abb73`:

- `src/sase/xprompt/processor.py:80`, `src/sase/xprompts/fork.yml`, `src/sase/scripts/fork_history.py`: deferred-name selection and workflow adapter.
- `src/sase/axe/run_agent_runner.py:172`, `src/sase/axe/run_agent_runner_setup.py:293`: expansion relative to dependency and capacity admission.
- `src/sase/monitor/followup_prompt.py:200`, `src/sase/xprompt/_disabled_regions.py`, `src/sase/llm_provider/preprocessing.py:178`: literal follow-ups and expansion protection.
- `src/sase/history/chat_fork/build.py`, `src/sase/bead/model.py`, `src/sase/bead/cli_crud_evidence.py:138`: historical recovery, task validation, and author overrides.

Rust inspected through the opened `sase-core` checkout at `93fe02b0d10e0116f2ecf2f8c6c62ee2fb50aa3b`: `crates/sase_core/src/bead/wire.rs:25` and `:268` for issue/note models, and `crates/sase_core/src/bead/events.rs:1415` for event ordering and the subsequent note edit/removal reducers. External primary sources are linked at the claims they support. The architecture and trial criteria are this synthesis's recommendations, not findings that an implementation already satisfies them.

## Recommended solution

**Build a narrow, opt-in family channel in the Rust core, with immutable messages, family-owned subscriber progress, explicit receipts, and bounded host-composed delivery at the next shell. Keep beads for work and notifications for attention.** Start with one shared board and the smallest human posting/status surface; add waking and broader messaging only when usage warrants them. A `#board` renderer can assist experimentation, but cannot replace the host integration. Separately repair supervision continuation ownership, because reliable messages cannot keep an unscheduled sequence alive.
