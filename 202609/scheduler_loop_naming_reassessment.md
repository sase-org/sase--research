# Beyond lanes: naming SASE's scheduler processes

_Independent research and critique · 2026-09-14_

**Recommend renaming lumberjacks to scheduler loops, shortened to loops where the
scheduler context is clear.** “The hooks loop runs eligible jobs on a five-second
interval” describes the current behavior directly. **Service** is the strongest
alternative if process lifecycle matters more than recurrence. **Routine** deserves a
fairer hearing than the earlier reports gave it, but remains a weaker fit for this
particular object.

For the surrounding vocabulary, retain the recommendations **SASE TUI** / `sase tui`,
**SASE scheduler** / `sase scheduler`, and **job** / **job run**. Prefer **Automation**
for the current tab, which includes both scheduler operations and independent
background commands; prefer **Scheduler** for a tab limited to scheduler-owned work.

## Scope and method

I read the [consolidated proposal](scheduler_tui_naming/scheduler_tui_naming.md),
[report A](scheduler_tui_naming/scheduler_tui_naming__a.md), and
[report B](scheduler_tui_naming/scheduler_tui_naming__b.md) through audited artifact
reads. Because the request mentions another research file and this directory contains
two underlying reports, this critique covers both and the consolidated recommendation.

I independently checked the SASE glossary, scheduler implementation, default
configuration, CLI parser, TUI sidebar, command palette, and runner-admission guide at
SASE commit `04005a222c6648aeccd2200ecbc035ac222c5f12`. The earlier reports used
`c402a04317228e8709a5e915e19d36328d7b6615`; their downstream counts and migration
inventory are not presented here as newly verified findings. The research checkout
started at `bf268861f938814c5ef1b192f8882fb4e48299d2`.

External research uses primary documentation, linked beside the claims it supports,
accessed September 14, 2026. The comparisons establish what other systems mean by their
words; they do not establish which name SASE users will prefer. Rankings and predicted
misunderstandings below are my design judgments, not results of a usability study.
Versioned or development documentation is identified where relevant.

## What the name must communicate

A lumberjack combines three things that the word *lane* only partly captures:

1. **A named configuration grouping:** jobs belong to `hooks`, `waits`, `checks`,
   `external_mirror`, `comments`, or `housekeeping`, with a shared base interval and
   some shared execution defaults.
2. **An ongoing scheduling activity:** it repeatedly considers work, including
   eligibility and per-job cadence. Eligible scripts execute concurrently within a
   tick; membership does not establish an ordered pipeline.
3. **A supervised runtime:** each configured lumberjack runs in a separate process,
   with its own state, log, heartbeat, metrics, and restart history. The parent starts
   and monitors these processes and restarts them after unexpected exits.

These properties are visible in the [scheduler loop implementation](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/axe/lumberjack.py),
[orchestrator](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/axe/orchestrator.py),
and [default configuration](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/default_config.yml#L903-L1335).
Separate processes provide a useful restart boundary, not complete isolation from
shared state or resource contention.

The shared interval is a base scheduling cadence, **not a promise that every job runs
on every tick or at an exact wall-clock deadline**. Jobs can be disabled, throttled,
guarded, or trigger-dependent. A long tick can also affect subsequent activity in its
own process. Consequently, a name should work for both “this process failed” and “this
group checks for eligible work periodically.”

I prioritize semantic fit and clarity between the group and its jobs, followed by
natural operational language, collisions in SASE's existing vocabulary, and brevity.
Distinctive spelling is useful, but should not decide the name by itself.

## What the external precedents actually support

| Primary source | Its terminology | Implication for SASE |
| --- | --- | --- |
| [Python schedule: multiple schedulers](https://schedule.readthedocs.io/en/stable/multiple-schedulers.html) | Multiple `Scheduler` objects each own jobs and are repeatedly serviced with `run_pending()`. | This is especially relevant because SASE uses this library. “Scheduler loop” describes the mechanism without calling both the whole subsystem and each child simply “scheduler.” |
| [runit: runsv](https://smarden.org/runit/runsv.8) | A supervisor starts a service, restarts its executable after exit, and maintains status and PID information. | “Service” has a strong precedent for the lifecycle side of a lumberjack. It does not inherently imply a network endpoint. |
| [Temporal: workers](https://docs.temporal.io/workers) | Worker processes poll task queues and execute code; the docs distinguish programs, processes, and worker entities. | “Worker” is plausible for a persistent execution process, but imports a queue-consumer expectation and needs careful qualification. |
| [Celery: periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html) | Beat schedules recurring tasks; workers execute them. | Scheduler and worker are not interchangeable roles. A SASE lumberjack combines scheduling with invoking its configured scripts. |
| [Kubernetes: controllers](https://kubernetes.io/docs/concepts/architecture/controller/) | Controllers use control loops to reconcile current state toward desired state. | “Controller” fits reconciliation work well, but promises more specific behavior than an arbitrary digest or script job provides. |
| [AWS EventBridge Scheduler: schedule groups](https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-group.html) | Schedule groups organize schedules and support group tagging. | “Schedule group” has real precedent, but that precedent establishes an organizational resource, not an independently running scheduler process. |

The lesson is not that an industry-standard synonym exists for lumberjack. The object
spans configuration, scheduling, and supervision. Its name must choose an emphasis,
and its short definition must explain the rest.

## Why lane is weaker than the earlier reports suggest

**It emphasizes placement over activity.** “Put this job in the housekeeping lane”
works. “The housekeeping lane crashed and its PID changed” requires learning a second,
process-oriented meaning. A lane can be a useful explanatory metaphor without becoming
the canonical object name.

**It can suggest execution guarantees the implementation does not provide.** A reader
may infer an ordered queue, a serial stream, or a reserved capacity partition. The
current object runs eligible scripts concurrently, and some capacity coordination
crosses process boundaries. These are plausible interpretation risks, not claims that
the word always means serialization.

**Existing prose is evidence of familiarity, not evidence of superiority.** The
defaults really do describe a fast lane and other lanes. They also include concrete
functional groupings such as `external_mirror`, so latency class is only part of the
organizing principle. Repetition in configuration descriptions does not settle the
public terminology question.

**Its collisions were treated more leniently than competing names' collisions.** The
earlier reports accept “lane” despite SASE's context-panel and CI usages, yet reject
“loop” largely because Claude Code has `/loop`. The current
[TUI guide](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/docs/ace.md)
uses lane for metadata, agent-family presentation, and other UI groupings. “Scheduler
lane” and “scheduler loop” both gain clarity from qualification. Apply the same test to
both.

There is also a direct product constraint: the person operating this system dislikes
the name. That matters when several technically defensible alternatives exist.

## Ranked alternatives

This ordering is specific to SASE's current object and the request to replace “lane.”
It is not a popularity ranking.

| Rank | Candidate | Best argument | Main cost | Judgment |
| --- | --- | --- | --- | --- |
| **1** | **Scheduler loop / loop** | Names recurring activity; works with intervals, ticks, failures, and restarts. | Bare “loop” also describes programming constructs and agent behavior; supervision needs a definition. | Best balance for this developer-facing system. |
| **2** | **Scheduler service / service** | Naturally communicates a persistent process with health, logs, and restart behavior. | Broad; may suggest a system service or endpoint, and says little about cadence. | Best alternative when operational lifecycle takes priority. |
| **3** | **Scheduler group / job group** | Makes configuration membership immediately clear. | Makes the active process and restart boundary less apparent. | Best if the public abstraction should eventually outlive the current process topology. |
| **4** | **Routine** | Familiar, readable, and suitable for recurring composite automation. | Sounds like the automation definition or one run of it, rather than its continuously active scheduler. | Defensible, but needs more explanation than loop here. |
| **5** | **Worker** | Familiar term for an ongoing execution process. | SASE already talks about agent workers; queue consumers and interchangeable replicas are adjacent expectations. | Viable only as “scheduler worker”; less distinctive within SASE. |
| **6** | **Controller** | Strong for hooks, waits, and other reconciliation. | Too specific for the unrestricted script automation contract; SASE also uses controller for machine administration. | Good name for particular implementations, weak umbrella. |
| **7** | **Beat / pulse** | Memorable and rhythm-oriented; Celery provides a beat precedent. | Often reads as one timing event or heartbeat, rather than the entity producing repeated ticks. | Appealing metaphor, weaker operational precision. |

Other possibilities are less promising. **Cadence** names a property of the object;
“set its cadence” is clearer than “restart the cadence.” **Timer** emphasizes one source
of eligibility. **Queue**, **pool**, and **pipeline** imply respectively waiting work,
interchangeable execution capacity, or ordering that this grouping does not guarantee.
**Watch / watcher / sentinel** emphasize observation, while jobs also clean, publish,
and launch follow-up work. **Reactor** suggests an event-dispatch architecture more
specifically than needed. **Engine**, **dispatcher**, **conductor**, and **foreman**
either lack useful specificity or compete with the parent orchestration role.
**Daemon** describes runtime form but poorly distinguishes the parent from its children.
**Cron** undersells the trigger and guard model. Keeping **lumberjack** preserves
distinctiveness and the AXE metaphor, but also preserves the explanation burden that
motivated this research.

### Why loop wins despite its drawbacks

SASE's own [Axe guide](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/docs/axe.md#L35-L48)
already defines a lumberjack as an “individual scheduler loop.” Its implementation has
both a `_run_tick()` and a long-lived `run()` that services its scheduler. The proposed
name promotes the existing explanation into the public vocabulary.

It also yields useful distinctions: the **loop** persists, a **tick** is one pass,
a **job** is a configured unit of work, and a **job run** is one execution. “The job
failed” and “the loop exited” identify different operational problems. The short form
is four letters, with straightforward plural and identifier forms: `loops`,
`SchedulerLoop`, `loop_name`.

The objections are real. A bare loop does not imply a separate process, and a novice
may initially picture sequential execution. Define it as a **supervised scheduler
loop** and state that eligible jobs may run concurrently. This is comparable to the
explanation “lane” also needs, but recurrence is already communicated.

Claude Code's [`/loop`](https://code.claude.com/docs/en/scheduled-tasks) is a real nearby
collision: it repeats prompts within a Claude session, with session-specific lifecycle
rules. That warrants explicit language in agent instructions: “configure a SASE
scheduler loop” and the full CLI spelling. It does not create a command collision with
`sase scheduler loop`. Avoid introducing a bare `/loop` shortcut for SASE. If actual
usage repeatedly confuses the two, **service** should replace loop in the shortlist.

Loop need not bind the public model to Python, threads, or polling forever. A logical
repeating scheduler can retain the name under another implementation. Reconsider it
if these objects become passive placement groups serviced by a separate shared
scheduler; **scheduler group** would then describe them better.

### Routine was rejected too categorically

The earlier reports are right that routine can be mistaken for the job itself. They
overstate the claim that a routine cannot naturally contain other work. Google's
[routine documentation](https://support.google.com/assistant/answer/7672035?hl=en-GB)
explicitly supports multiple actions in one routine. That is a counterexample to the
single-action interpretation, though it does not make a routine equivalent to a SASE
supervised process.

Anthropic's [routine documentation](https://code.claude.com/docs/en/routines) describes
a saved configuration with a prompt, repositories, connectors, and triggers. It can
react to schedules, API calls, or GitHub events. Thus “one scheduled cloud agent” is
an oversimplified account of the precedent; a routine is a reusable definition whose
invocations create sessions.

The stronger reason to rank routine below loop is **lifecycle**: “run the routine”
usually suggests performing the automation, whereas running a lumberjack starts an
ongoing scheduler for independently eligible jobs. Those jobs need not form one
coherent procedure. Routine would become more attractive if SASE exposed a user-facing
automation recipe while hiding its scheduler process.

The `routine`/`coroutine` substring objection is minor. Word-aware searches and scoped
identifiers address much of that noise. Searchability alone does not justify choosing
a less informative name.

## Critique of the other recommended names

### ACE → SASE TUI and `sase tui`: endorse, with a better rationale

This makes the entry point recognizable to a technical audience. Introduce it as
“SASE terminal UI (TUI)” in newcomer documentation, then use “the SASE TUI.” Calling it
the **terminal UI** also distinguishes it from other frontends without inventing
another product brand.

The argument that “ChangeSpecs became Patches, therefore Agentic Change Explorer is
obsolete” is not decisive: patches still represent changes. The stronger evidence is
scope. The interface manages agents, artifacts, and automation, while the
[current parser help](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/main/parser_ace.py#L33-L38)
still describes navigating Patches. TUI also remains an acronym; it is simply more
familiar to the intended audience than ACE. It gives up some brand personality, which
is a reasonable trade here.

Agree with both reports that a public command rename does not justify mechanically
renaming a mixed-responsibility Python package. Package organization is a separate
design question.

### AXE → SASE scheduler and `sase scheduler`: endorse

The name explains a purpose and pairs naturally with loops and jobs. Introduce it as
the **background automation scheduler** so it does not imply a calendar-only service.
Use “schedule” for a timing rule or scheduling action, and “scheduler” for the
component being started, stopped, or inspected.

The important boundary is agent admission. The
[runner-slot guide](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/docs/troubleshooting/runner-slots.md)
says admission is enforced in agent processes and does not depend on AXE. Recommended
explanation: “The scheduler evaluates background jobs; agent runner admission controls
when a requested agent launch can start.” Jobs may request agent launches, so avoid
wording that suggests the two systems never interact.

The presence of an internal `sase.ace.scheduler` package does not make the public name
unavailable. Relocate that package if its responsibility warrants it; no internal
namespace needs to be “freed” before public copy can improve.

### AXE tab → Automation, Scheduler, or Schedule: favor scope over symmetry

**Automation** is my preference for the current mixed surface. Its
[sidebar implementation](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/ace/tui/widgets/bgcmd_list.py#L1-L87)
combines the scheduler tree with a separate commands section. Report A gives that fact
more appropriate weight than the consolidation does.

The consolidation's “one noun per level” argument conflates two different things:
**Automation** can name a navigation category containing the **Scheduler** component.
They are not necessarily competing names for the same object. An explicit Scheduler
section and Commands section make that relationship clear. Automation is broad enough
that it could also suggest workflows elsewhere in SASE, so this choice still needs a
short scope description in help.

**Scheduler** is a good alternative when the tab's content is scheduler-owned. With
independent commands still present, it is a usable but less complete label. Merely
labeling those rows “Commands” does not change who owns them. Moving them elsewhere
should require a navigation benefit; relocating useful controls solely to make a tab
name fit reverses the design priority.

**Schedule** suggests timing configuration or upcoming executions, and is the weakest
fit for an operational surface with process health, logs, and manual runs. **Jobs**
would also omit the parent process and independent commands. The current
[palette alias](https://github.com/sase-org/sase/blob/04005a222c6648aeccd2200ecbc035ac222c5f12/src/sase/ace/tui/commands/catalog.py#L219-L238)
that maps “jobs” to Procs is a fixable discovery issue, not a decisive naming veto.

### Chops → jobs, with job run: endorse without claiming universal semantics

This remains a strong improvement. SASE already explains chops using job vocabulary,
and “job script,” “job timeout,” and “job history” are understandable operational
phrases. Keep the distinction between a configured job and a particular job run.

However, the earlier reports overstate ecosystem agreement on the exact hierarchy.
[Kubernetes CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
create one-time Jobs, so its Job is closer to an execution than SASE's reusable chop
definition. In the [APScheduler development user guide](https://apscheduler.readthedocs.io/en/master/userguide.html#basic-concepts-glossary),
a job is an execution request; task and schedule are distinct concepts.
[GitHub Actions](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)
defines workflows containing jobs and jobs containing steps. These sources support
familiarity with the word, not a universally agreed definition.

Use the following explicit SASE meanings:

| Term | Proposed meaning |
| --- | --- |
| Scheduler loop | A named, supervised scheduler that repeatedly evaluates its configured jobs. Each currently runs in its own process. |
| Tick | One pass through a loop's scheduling work. |
| Job | A configured script automation with its own eligibility and execution policy. |
| Job run | One execution of that job; target expansion can produce separately tracked instances. |
| Job script | The executable implementation, which may return launch proposals. |
| Agent launch | Follow-up work requested by a job result and carried out by the runner. |

“Job” should not become a blanket label for every agent, shell command, or tracked task.
In mixed views, use **scheduler job**, **CI job**, or the existing specific noun.
**Task** remains a poor replacement because SASE already uses task for tracked work;
**check** excludes maintenance, mirroring, and other action-oriented scripts.

### Secondary recommendations: mostly reasonable, with tighter scope

| Earlier recommendation | Critique |
| --- | --- |
| Keep **orchestrator** for the parent | Reasonable. Its current duties are specifically supervision, so **supervisor** is more precise in explanatory prose; [Supervisor's documentation](https://supervisord.org/introduction.html) provides a close lifecycle analogue. Another mandatory rename would add little value. |
| Rename the `chop` agent grouping to **job** or **scheduled** | Prefer **job** between those two. “Scheduled” can misleadingly exclude event-triggered or manually invoked work. In explanatory text, “agents launched by jobs” makes the relationship clearer than equating an agent with a job. |
| Use `tui:` / `scheduler:` and `sase.jobs` / `sase_job_*` | Coherent target spellings once the vocabulary is chosen. Configuration and extension-protocol compatibility remain separate implementation work. |
| Rename `sase.ace.scheduler` to `sase.patch_lifecycle` | A plausible responsibility-based name, not something established solely by this terminology research. Check the package's full responsibilities before adopting it. |
| Keep `ace-run/` and `~/.sase/axe/` internal | Sensible as a migration decision, but “never user-facing” is too strong: diagnostics and instructions can expose paths. Preserve resolvability and explain legacy names where encountered. |
| Rename the whole metaphor family together | Decide on a coherent destination vocabulary together. It does not follow that every public and persisted spelling must switch in the same release. |

## How the recommended vocabulary reads

These are **proposed spellings**, not commands or configuration implemented by this
report. The examples retain the current list/status/foreground-run distinction.

```text
sase tui
sase scheduler status
sase scheduler loop list
sase scheduler loop status
sase scheduler loop run hooks
sase scheduler job run hook_checks --loop hooks
```

`loop run hooks` starts the ongoing loop in the foreground; `job run` performs an
individual execution. This distinction should be explicit in help. Do not label a
single scheduling pass a “loop run”; call it a **tick**.

An illustrative configuration shape:

```yaml
scheduler:
  loops:
    hooks:
      description: Advance hook lifecycle state with low latency
      interval: 5
      jobs:
        - name: hook_checks
          script: sase_job_hook_checks
```

Useful operator-facing sentences:

- “The hooks loop evaluates eligible jobs on a five-second interval.”
- “The housekeeping loop restarted; inspect its log.”
- “This job was skipped because its trigger did not match.”
- “Run the job once without starting another scheduler loop.”
- “Open Automation, then select the hooks loop.”

For a fair comparison, substitute **service**, **group**, and **routine** into these
sentences. Service handles the failure sentence especially well; group handles
membership; routine handles performing automation. Loop performs well across the full
set. That is the basis for recommending it.

Before an implementation decision, a small comprehension check would be useful: show
the candidate tree labels and ask which object has a PID, which operation runs once,
and whether the child jobs must execute sequentially. No such test was conducted for
this report. The present recommendation is strong on architectural fit and less
certain on personal preference and first-use comprehension.

**Recommended destination:** the **SASE scheduler** supervises **scheduler loops**;
each loop evaluates **jobs** and records their **job runs**. Operators inspect the
current combined background-work surface in **Automation** within the **SASE TUI**.
