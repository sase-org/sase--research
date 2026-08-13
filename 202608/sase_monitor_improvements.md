---
create_time: 2026-08-13
updated_time: 2026-08-13
status: research
---

# Improving `sase monitor`: durability, control, and safe agent handoff

**Research question:** Given the in-progress `sase-kp` epic, what improvements would
most increase the correctness, durability, safety, and usefulness of SASE monitors?

**Scope and snapshot:** This report evaluates the epic design and the implementation at
SASE commit
[`22319c52d`](https://github.com/sase-org/sase/commit/22319c52d901f91b9c2d917c63f707e3562aa121)
on 2026-08-13. At that snapshot, phases 1–7 and 10 were closed; the TUI detail,
approved-epic launch, documentation, and end-to-end smoke phases were still in progress.
The analysis therefore avoids presenting work already owned by those phases as a new
idea.

The research combined four inputs:

1. the canonical `plans:202608/sase_monitor.md` design and all `sase-kp` phase notes;
2. code and tests under `src/sase/monitor/`, the CLI and agent projections, and the
   existing background-task and AXE supervision code;
3. two focused timing probes against the real monitor stream loop; and
4. primary documentation for systemd/cgroups, Kubernetes Jobs, Temporal Activities,
   GitHub Actions, OpenTelemetry, and OWASP agent security.

## Bottom line

The central design choice is excellent: a monitor is an agent-family member backed by
the existing artifact index, not a second task database. That gives monitors coherent
history, family ordering, workspace lineage, TUI presence, and follow-up context with
very little conceptual duplication. It should be preserved.

The feature's largest remaining opportunity is not another surface. It is making the
supervised-command substrate as rigorous as the family model around it. Three issues
deserve attention before the current epic lands:

- The timeout is not currently authoritative. A continuously readable stream, a partial
  line, or early pipe EOF can prevent the supervisor from checking its deadline.
- A supervisor crash can orphan the command and leak the workspace claim; stop can also
  signal a recycled PID because process identity is not verified.
- Start and completion are multi-step transitions presented as single states. Generic
  starts have a check-then-create race, the command can begin before the workspace claim
  is secured, and a monitor becomes terminal before claim/follow-up settlement finishes.

After those, the best improvements are bounded durable logs, an explicit trust boundary
between command output and the follow-up LLM, host-wide admission control, and richer
reconciliation/telemetry. These are more valuable than recurring schedules, automatic
restart, or a new monitor store.

## What is already strong

- **One identity model.** `agent_meta.json` plus `done.json` is the durable record, so
  every surface observes the same monitor rather than joining two stores by convention.
- **Lane semantics match the product.** One active monitor per sequential agent lane is
  the right default. Promoting a lone agent into a family makes command delegation
  visible instead of disguising it as detached infrastructure.
- **Timeouts are mandatory at the CLI.** Requiring a budget is a better default than
  allowing accidental infinite jobs.
- **The process group is isolated.** `start_new_session=True` plus TERM→KILL escalation
  is directionally correct for ordinary process trees.
- **Failure still resumes reasoning.** A nonzero exit or timeout can launch a follow-up
  with the prior conversation, command outcome, and output tail. This is exactly the
  handoff slow verification needs.
- **The design is intentionally non-recurring.** A run-to-completion primitive is much
  easier to reason about than a second scheduler, and AXE already owns recurring work.

The recommendations below reinforce those choices rather than replacing them.

## Finding 1: output handling can defeat timeout and stop escalation

The current stream loop uses `select()` on the child's text stream and then calls
`readline()`. When a line is returned it immediately `continue`s, so neither the timeout
deadline nor TERM→KILL escalation is checked on that iteration. See
[`supervise.py` lines 159–188](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/monitor/supervise.py#L159-L188).

This creates three related failures:

1. A chatty process that keeps the pipe readable can run past its timeout indefinitely.
2. `select()` guarantees that at least one byte can be read, not that a newline is
   available. `TextIOWrapper.readline()` can therefore block on a partial line and stop
   all deadline checks.
3. If stdout closes while the process remains alive, the loop reaches `child.wait()`
   without a timeout and can block until the process exits.

A focused probe ran two one-second commands with a 100 ms monitor budget:

| Probe | Expected | Observed |
| --- | --- | --- |
| one flushed line every 1 ms | timeout near 100 ms | `timed_out=False`, 1.020 s |
| one flushed partial line, then sleep | timeout near 100 ms | `timed_out=False`, 1.017 s |

Binary or non-UTF-8 output adds another path: decoding can raise from the text wrapper,
and the supervisor currently has no outer cleanup guard.

### Improvement

Replace line-oriented reads with a nonblocking, byte-oriented pump:

- put the pipe in nonblocking mode and read bounded chunks with `os.read()`;
- use an incremental UTF-8 decoder with replacement for invalid bytes;
- evaluate the timeout, stop request, and kill deadline on every loop iteration,
  regardless of whether output arrived;
- poll process exit independently of pipe EOF; and
- drain only the bytes already available after process exit, under a short final bound.

On Linux, a pidfd can be included in the selector; Python exposes `os.pidfd_open()`, and
the kernel interface is pollable and avoids PID-reuse races. The portable path can keep
polling `Popen.poll()`. The
[`pidfd_open(2)` documentation](https://www.man7.org/linux/man-pages/man2/pidfd_open.2.html)
describes both properties.

Add regression tests for continuous output, a huge line without `\n`, invalid UTF-8,
stdout closed while the process remains alive, a TERM-ignoring chatty process, and
output arriving exactly at the timeout boundary. These tests should assert both the
recorded outcome and that no descendant remains.

## Finding 2: process ownership is not crash-safe

`run_supervisor()` has no broad `try`/`finally` around spawn, capture, chat persistence,
marker writes, follow-up launch, claim release, and notification. An exception from log
I/O, decoding, chat persistence, index mutation, or another unexpected source can exit
the supervisor without settling anything. Because the command starts its own session,
killing the supervisor does not kill the command.

Only the supervisor PID is persisted. The child PID/PGID and an identity stronger than
PID are not. Dead-supervisor reconciliation in
[`store.py` lines 104–163](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/monitor/store.py#L104-L163)
marks metadata failed, but it does not terminate a surviving child, release the claim,
or send the terminal notification. Reconciliation is invoked by `stop`, not by normal
`list`/TUI reads. Finally, `stop` checks only whether the numeric supervisor PID is
alive before signaling it, so PID reuse can target an unrelated process.

SASE already contains better local patterns:

- the task supervisor wraps the whole lifecycle in `try`/`finally`, kills the child
  after supervisor errors, persists the child PGID, and always writes a terminal state
  ([`tasks/supervisor.py`](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/tasks/supervisor.py#L68-L153));
- task reconciliation validates the supervisor command line before trusting a PID; and
- AXE maintenance markers record `/proc` start ticks plus boot ID to detect PID reuse
  ([`axe/maintenance.py`](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/axe/maintenance.py#L138-L183)).

### Improvement

Create one shared supervised-command kernel for tasks and monitors, with these minimum
invariants:

- persist supervisor PID plus process identity, child PID/PGID plus identity, and host
  boot ID immediately after each becomes known;
- wrap the complete lifecycle in a broad cleanup guard;
- on internal failure, TERM then KILL the verified child tree, finalize the log, write a
  `lost`/`failed` outcome, and conditionally release the claim;
- make claim release compare against an ownership/fencing token so an old supervisor
  cannot release a claim already transferred to a follow-up; and
- have `list`, the TUI loader, and a `monitor doctor`/reconciler heal stale active rows,
  rather than requiring the operator to call `stop` first.

Live Linux control should prefer pidfds where practical. A pidfd cannot be persisted
across processes or reboot, so durable reconciliation still needs start identity and
boot ID. The
[`pidfd_send_signal(2)` documentation](https://www.man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)
explains why a stable process reference avoids signaling a recycled PID.

### Optional Linux backend: transient user services and cgroups

For Linux, the strongest implementation would run each command in a named transient
user service (or place it in a dedicated delegated cgroup) while SASE retains the agent
artifact as the product record. `systemd-run` creates detached transient services,
`Type=exec` distinguishes successful fork from successful `execve`, and the service
manager exposes exit status and CPU/memory/I/O accounting
([`systemd-run(1)`](https://man7.org/linux/man-pages/man1/systemd-run.1.html)).
`KillMode=control-group` applies TERM→KILL to every remaining process, which systemd
explicitly recommends over main-process-only killing
([`systemd.kill(5)`](https://man7.org/linux/man-pages/man5/systemd.kill.5.html)). At the
kernel level, `cgroup.kill` handles descendants, concurrent forks, and migrations
([cgroup v2 documentation](https://docs.kernel.org/6.0/admin-guide/cgroup-v2.html)).

This host is a particularly good candidate: systemd 257, cgroup v2, an active user
manager, and `Linger=yes` were verified during this research. SASE supports macOS too,
so this should be an optional Linux hardening backend with the corrected portable
supervisor retained as fallback. A transient service still disappears on reboot; after
a boot-ID change SASE should mark an unfinished monitor `lost`, never automatically
re-run an arbitrary shell command.

## Finding 3: start and finish need transactional semantics

The generic start path performs `active_monitor_for_lane()` and then creates the member
without a per-lane lock. Two simultaneous starts can both observe no active monitor,
allocate colliding or parallel members, and violate the lane's sequential contract. The
epic-launch adapter plans to retain its own lock, but the generic primitive should
enforce its own invariant.

The supervisor is also spawned before the workspace claim is transferred. It reads
`monitor_state="running"` and can execute the command immediately, so a mutating command
may start even if claim acquisition later fails.

At the other end, `_finish_monitor()` writes the terminal `done.json` before launching a
follow-up or releasing the workspace claim. Observers therefore see `completed` while
settlement is still running. Phase `sase-kp.6` has already recorded the resulting test
race: waiting for terminal state and then asserting that the claim is free is flaky.

This is the same distinction Kubernetes now makes for Jobs: a success/failure target
can begin termination, but the final `Complete`/`Failed` condition is delayed until the
owned Pods are terminal
([Kubernetes Job termination semantics](https://kubernetes.io/docs/concepts/workloads/controllers/job/#terminal-job-conditions)).

### Improvement

Separate **command outcome** from **orchestration settlement** instead of forcing both
through `monitor_state`:

```text
PREPARING -> CLAIMED -> RUNNING -> TERMINATING -> PROCESS_EXITED -> SETTLING -> SETTLED
                              command outcome: completed | failed | timeout | stopped | lost
```

Concrete mechanics:

1. Acquire a per-project/per-lane flock and re-read the active monitor under it.
2. Create a `PREPARING` member with an immutable request fingerprint.
3. Spawn a supervisor that waits on a launch-permit marker or pipe.
4. Transfer/claim the workspace, record its fencing token, then publish the permit.
5. Only then allow child `exec` and publish `RUNNING`.
6. After child exit, publish the command outcome but keep settlement nonterminal.
7. Finalize logs/chat, kill remaining descendants, and atomically transfer or release
   the claim.
8. Write the terminal marker last. A successful follow-up launch should be acknowledged
   before the monitor is considered settled.

Stop becomes a compare-and-set from an active state to `TERMINATING`, and a timed-out
stop returns an error rather than reporting “already running; nothing to do.”

Idempotency should also be explicit. Today, the same command string returns the existing
monitor even if cwd, timeout, next action, statuses, or reason differ. Use a canonical
fingerprint of the effective request, or accept a caller-supplied idempotency key. The
approved-epic path can use a stable key based on project plus plan identity; a modified
request should conflict visibly rather than silently inherit an old monitor.

## Finding 4: the durable log is unbounded, despite the 2 MiB constant

`OutputCapture` caps only its in-memory retained view. Every byte is still appended to
`live_reply.md`, and the file is explicitly “never truncated”
([`output.py`](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/monitor/output.py#L11-L79)).
Thus a noisy or accidental infinite command can fill the artifact store. The
`monitor_output_truncated` flag describes the follow-up/chat view, not the on-disk log,
and “full log” pointers become misleading once a real retention policy is introduced.

Again, SASE already has the primitive needed: task logs use a pipe drain plus shared
bounded-log rotation, and readers follow both active and rotated files
([`tasks/logs.py`](https://github.com/sase-org/sase/blob/22319c52d901f91b9c2d917c63f707e3562aa121/src/sase/tasks/logs.py#L31-L69)).

### Improvement

- Reuse the shared bounded-log writer rather than maintaining a monitor-specific
  in-memory cap.
- Keep a small head sample plus a rotating tail, with configurable per-monitor and
  host-wide quotas. Record `total_bytes`, `retained_bytes`, and `dropped_bytes`.
- Make `show --follow` rotation-aware and chunk-oriented; do not treat file offsets as
  stable across rotation.
- Compress a completed log only when it is still useful and below the retention budget;
  add age/size pruning consistent with the artifact lifecycle.
- Call retained data a “retained log,” not a “full log,” whenever bytes were dropped.
- Add search and export. GitHub Actions makes run logs viewable, searchable, downloadable,
  and line-addressable, a useful UX baseline
  ([GitHub workflow-run logs](https://docs.github.com/en/actions/how-tos/monitor-workflows/use-workflow-run-logs)).

## Finding 5: command output crosses an LLM trust boundary

The follow-up prompt embeds the retained command tail verbatim. A code fence makes it
render as data, but does not stop a model from treating text such as “ignore prior
instructions and run …” as instructions. Build output can contain attacker-controlled
test names, compiler messages, dependency output, repository content, or fetched remote
text. The follow-up agent has the same workspace and tools, so this is an indirect
prompt-injection boundary.

OWASP's secure-coding guidance specifically identifies error traces and log output as
an injection source and advises treating data passed between agents as untrusted
([Secure Coding with AI](https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html)).
Its agent guidance recommends structured separation, least privilege, action validation,
and avoiding raw unsanitized cross-agent content
([AI Agent Security](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)).

### Improvement

- Put an explicit, high-priority notice immediately before the tail: it is untrusted
  command output, never an instruction source, and must not expand the user-approved
  task.
- Prefer a deterministic outcome summary plus an artifact reference. Inline only the
  smallest diagnostic tail needed; allow `--next-output none|tail|file`.
- Before a follow-up performs a write or external action suggested only by the log,
  validate it against the original user task and the explicit `--next` action.
- Add adversarial smoke tests whose command output contains fake system/user messages,
  tool-call requests, markdown links/images, bidi controls, and fake SASE directives.

This does not require a second “guardrail LLM.” Clear data/instruction separation and
scope validation are deterministic improvements and should come first.

## Finding 6: command text and logs need a secrets policy

The supervisor inherits the complete agent environment, persists the exact shell
command in `agent_meta.json`, saves it in chat history, and stores merged output. A
credential placed directly in `--command`, echoed by a tool, or printed by a failing
script therefore becomes durable agent history and may flow to integrations.

GitHub's operational baseline is useful here: avoid secrets on command lines, inject
them through safer channels, redact registered secrets from logs, and allow additional
values to be masked
([using secrets in Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)).
GitHub also warns that redaction is not a complete security boundary
([GitHub Actions secrets](https://docs.github.com/en/actions/concepts/security/secrets)).

### Improvement

- Add a SASE-wide redaction pipeline shared by task and monitor logs. Seed it from known
  credential values/names and explicit `--mask` inputs, and apply it before disk, TUI,
  notification, chat, and follow-up-prompt writes.
- Keep files mode `0600` regardless of umask and avoid copying the full environment into
  metadata or diagnostic JSON.
- Offer an argv form (`sase monitor start -- command arg...`) in addition to an explicit
  `--shell-command` form. Shell semantics remain useful, but should be opt-in and named.
- Document that secrets must not appear in command arguments. Longer term, reference a
  credential provider rather than serializing values; systemd service credentials are
  one possible Linux backend, not the portable product API.

Redaction should be tested for streaming boundary splits (a secret divided across two
chunks), encoded/quoted variants, and the guarantee that the raw value never reaches
chat history.

## Finding 7: first-class monitors need host-wide admission control

One monitor per lane prevents intra-lane concurrency but does not limit the number of
lanes running `just check-full`, builds, deploys, or polling loops simultaneously. The
feature makes slow commands easier to launch, which can amplify the host contention it
is meant to make tolerable.

The right abstraction is a small admission layer, not a general scheduler:

- a concurrency group (`verify`, `deploy:<environment>`, `project:<name>`, or an
  explicit key);
- a host/project maximum and bounded FIFO queue;
- policy when a duplicate arrives: reject, queue, or explicitly replace/cancel;
- lightweight resource hints/classes; and
- visible `QUEUED` state plus queue time.

GitHub Actions' concurrency groups demonstrate the useful core: one active member per
key, an explicit pending queue policy, and opt-in `cancel-in-progress`
([workflow concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)).
For SASE, replacement must never be the silent default because monitored commands can
mutate a workspace or deployment target.

On Linux, transient services can also apply `CPUWeight`, `IOWeight`, `MemoryHigh`,
`MemoryMax`, and `TasksMax`; systemd exposes its cgroup/resource controls to transient
units ([transient settings](https://systemd.io/TRANSIENT-SETTINGS/)). On all platforms,
`just check-full` monitors should continue to cooperate with the existing SASE test
suite gate instead of creating a second CPU allocator.

## Finding 8: liveness, progress, and attempts should be observable

`running` currently means “no terminal marker,” not “the child is alive and making
progress.” Useful low-cardinality fields would be:

- supervisor/child identity and last supervisor heartbeat;
- actual child start time, last output time, bytes seen/retained/dropped;
- queue duration and claim-settlement duration;
- termination request time, TERM/KILL times, and final reason;
- peak RSS, CPU time, disk I/O, and child count; and
- attempt number plus predecessor/successor IDs for explicit retries.

The TUI can then distinguish healthy, quiet, stalled, stopping, and lost monitors. A
quiet command is not automatically unhealthy, so “no output for N minutes” should be a
badge/diagnostic, not an automatic kill.

Temporal's Activity model is a helpful source of invariants without being a dependency:
long-running activities use heartbeats to distinguish progress from worker loss, can
attach progress details, and combine heartbeat timeouts with an overall execution
timeout
([Temporal Activity failure detection](https://docs.temporal.io/encyclopedia/detecting-activity-failures)).
SASE can use a supervisor heartbeat even when the underlying command cannot report
application progress.

Store important transitions in a small append-only lifecycle journal so postmortems can
answer “what happened before the final marker?” AXE already uses a bounded lifecycle
journal and restart-storm damping, so this would align monitor diagnostics with an
existing SASE operational pattern.

For resource names and units, borrow rather than invent: OpenTelemetry defines process
CPU time/utilization, memory usage, disk/network I/O, thread count, file descriptors,
and uptime
([OS process metrics](https://opentelemetry.io/docs/specs/semconv/system/process-metrics/)).
The first implementation can remain local JSON; adopting an observability backend is
not required.

## Finding 9: follow-up and retry policy should be outcome-aware

Launching the same next action after success, failure, and timeout is a good simple
default, but advanced workflows will quickly need different instructions. Add explicit
policies without turning monitors into workflows:

- `--next-on always|success|failure|timeout` (repeatable or a compact mapping);
- `--no-followup-on-success` for verification that needs an agent only when red;
- manual `sase monitor retry <id>` that copies the immutable request into a linked new
  attempt; and
- bounded automatic retries only when the caller explicitly marks the command
  idempotent and supplies retryable outcomes/exit codes.

Kubernetes Jobs expose an overall deadline, bounded backoff, and exit-code-aware failure
policy, while warning that a task may run more than once
([Kubernetes Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)).
Temporal similarly treats retries as declarative policy and expects operations to be
idempotent
([Temporal retry policies](https://docs.temporal.io/encyclopedia/retry-policies)).
The lesson for SASE is to make retries visible and opt-in. Never auto-restart an
arbitrary deploy, bead launch, or shell command after supervisor loss.

## Verification matrix worth adding to `sase-kp.12`

The planned smoke phase covers normal completion, nonzero exit, timeout, stop, CLI
formats, and epic approval. Extend it with the failure boundaries most likely to reveal
production defects:

| Boundary | Exercise | Required invariant |
| --- | --- | --- |
| stream | continuous output past deadline | timeout wins; tree is dead |
| stream | partial line, invalid UTF-8, early stdout close | supervisor remains responsive |
| stop | child ignores TERM and prints continuously | KILL occurs after grace |
| crash | SIGKILL supervisor with a live grandchild | reconciler kills tree and releases claim |
| identity | stale/recycled supervisor PID | unrelated process is never signaled |
| start | two simultaneous starts in one lane | exactly one command executes |
| claim | forced claim-transfer failure | command never executes |
| settle | command exits while follow-up launch is delayed/fails | no premature terminal state or leaked claim |
| logs | output beyond cap while `show --follow` runs | disk stays bounded; stream survives rotation |
| disk | log/chat/index write failure | command is contained and monitor becomes diagnosable |
| trust | output contains injected instructions and secrets | neither reaches an unauthorized action or durable plaintext |
| reboot | active marker from a previous boot | monitor becomes `lost`; no implicit rerun |

## What not to build yet

- Do not replace agent artifacts with a monitor database. Add lifecycle fields/events to
  the existing member record.
- Do not adopt Kubernetes or Temporal. Borrow their invariants—terminal settlement,
  heartbeats, bounded attempts—not their infrastructure.
- Do not add cron or recurring monitors; AXE already owns recurring execution.
- Do not make automatic restart the default. Most shell commands are not proven
  idempotent.
- Do not make systemd mandatory. Use it to strengthen Linux while preserving a tested
  POSIX/macOS fallback.
- Do not add detailed telemetry before the P0 supervision and settlement invariants are
  correct.

## Ranked recommended improvements

1. **P0 — Replace the line-oriented output loop with a nonblocking byte pump whose
   timeout and TERM→KILL deadlines are checked independently of output.** Add the
   chatty, partial-line, EOF-before-exit, invalid-UTF-8, and TERM-ignoring regression
   tests before landing the epic.
2. **P0 — Make the portable supervisor crash-safe.** Persist verified supervisor and
   child identities/PGID, add whole-lifecycle `try`/`finally`, kill surviving descendants,
   conditionally release claims, and refuse to signal an unverified/recycled PID. Reuse
   the existing task and AXE process-identity machinery.
3. **P0 — Make lane start and settlement transactional.** Add a per-lane lock, a
   supervisor launch barrier after claim acquisition, a request fingerprint/idempotency
   key, claim fencing, and separate command-outcome from orchestration-settlement state;
   write the terminal marker only after child, log, claim, and follow-up disposition are
   settled.
4. **P1 — Bound the actual on-disk log and unify it with SASE's task-log primitive.**
   Rotate safely, make followers rotation-aware, report total/retained/dropped bytes,
   enforce retention, and stop calling a truncated artifact the “full log.”
5. **P1 — Harden the LLM and secrets boundary.** Treat command output as untrusted data,
   minimize inline tails, scope-check actions suggested by output, redact registered
   secrets before every durable/integration surface, and add an argv mode alongside an
   explicitly named shell mode.
6. **P1 — Add active reconciliation and a small lifecycle journal.** Reconcile from
   list/TUI/doctor, use heartbeat plus boot/process identity, classify previous-boot work
   as `lost`, and make cleanup/follow-up failures visible without requiring `stop`.
7. **P1 — Add host-wide admission control.** Support bounded concurrency groups and an
   explicit reject/queue/replace policy, integrate verification with the existing test
   gate, and expose `QUEUED` plus queue time.
8. **P2 — Add an optional Linux systemd/cgroup backend.** Use transient user services,
   `Type=exec`, runtime/stop limits, control-group killing, and resource accounting on
   capable hosts; retain the corrected portable supervisor for macOS and restricted
   Linux environments.
9. **P2 — Add outcome-aware continuation and observable attempts.** Support conditional
   follow-ups, linked manual retry, strictly opt-in bounded retries for declared-idempotent
   commands, and low-cardinality progress/resource metrics using established units.
