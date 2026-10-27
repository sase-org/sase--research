# Feature usage as evidence: a private, fast, and useful review system for SASE

Independent research by **cdx** · 2026-10-27

This report studies implementation choices and recommends a design; it does not implement or enable tracking. I inspected SASE, its linked Rust-core checkout, and public primary sources independently. I did not read other swarm researchers’ reports or obtain their findings indirectly. Performance numbers below are proposed acceptance budgets, not measured results.

**Recommendation:** build a small local feature-usage system that answers “what did I use, what have I not used, and how trustworthy is that observation?” Use a versioned feature catalog, bounded in-memory counters, Rust-owned daily aggregates in a separate SQLite store, and a **Features** view inside Statistics. Treat low usage as an invitation to review, not a deletion verdict. Design a narrow export contract now; implement opt-in uploads only after the private system demonstrates its value.

## 1. Is this a good idea?

Yes, with a narrower definition of “detailed.” SASE has enough distinct surfaces that memory and intuition are unlikely to provide a reliable inventory of personal use. A month or two of observations could reveal redundant navigation, abandoned workflows, unnecessarily prominent controls, and capabilities that cost more to maintain than they contribute.

The danger is optimizing for frequency rather than value. A recovery command used once a year may justify its existence. An invisible backend capability can support every useful workflow without receiving a direct user invocation. A feature may be unused because it is hard to discover, broken, unavailable on this machine, or unnecessary during the observation period. Agent-generated activity is another major confounder: a swarm can issue hundreds of commands that Bryan has never chosen directly.

The right product question is:

> Which capabilities deserve review because their observed use is low relative to their availability, purpose, and maintenance burden?

The system cannot answer “what should be deleted?” by itself. Quantitative observations establish frequency; explaining that frequency requires inspection and conversations. This division agrees with NN/g’s distinction between quantitative research and direct qualitative observation. [Source: NN/g research-method framework](https://www.nngroup.com/articles/which-ux-research-methods/).

My preferred outcome after eight weeks is a credible list of perhaps five to fifteen review candidates, each with an explanation and a decision: **keep, improve discoverability, simplify, merge, or propose deprecation**. A beautiful graph that cannot support these decisions would be a failure.

### Explicit adjustments to the requirements

| Original intent | Recommended adjustment | Reason |
| --- | --- | --- |
| Detailed usage tracking | Detailed feature coverage, aggregated counts, and active days; no interaction replay | The deletion question rarely needs event order, typed text, or exact timestamps |
| Find functionality never used | Show “no recorded use in this period,” separately from unknown and unavailable | Absence of observations is not proof of absence |
| Review after one or two months | Use 60 days as a first review window, with relevant active days alongside it | Two months containing four sessions provide little evidence |
| Do not store sensitive data | Prohibit user content and identifying labels at capture; minimize behavioral information and acknowledge inference risk | Even content-free usage patterns can reveal working habits |
| Eventually share usage data | Make sharing a separately consented, independently validated aggregate product | Existing diagnostics are not a safe upload package |
| Keep performance acceptable | Establish enabled/disabled and overload budgets before broad instrumentation | Running in a thread is insufficient evidence of responsiveness |
| Beautiful visualization | Optimize for an elegant review workflow within Statistics | A new analytics application would create another feature to maintain |
| Understand “my usage” | Separate human, agent, scheduled, internal, and unknown origin | Automation can otherwise dominate every chart |

Ship feature collection **off by default**, including for existing installations. Enabling a private 60-day study should be one explicit action. This research request is not a request to change the running installation’s configuration. Existing operational telemetry can retain its separate settings.

## 2. What SASE already provides

The inspected SASE revision was `a42eedc1c4679612ccfbcc277f302c88c1960b2f`; linked `sase-core` was `6d11122eed284f2589ecfd99d3c60c02fc949dbc`. These are source observations, not assertions that a running TUI has loaded those exact revisions.

| Verified source observation | Design implication |
| --- | --- |
| Python telemetry has counters, gauges, histograms, in-process accumulation, optional background flushing, and exit flushing. [Registry](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/_registry.py#L35), [accumulators](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/_accumulators.py#L107) | Reuse the architectural pattern and existing knowledge |
| Defaults enable operational telemetry, flush every 15 seconds, and retain raw/5-minute/hourly data for 48 hours/30 days/365 days. [Configuration](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/_config.py#L30) | Feature-study consent and retention need independent semantics |
| Metric definitions include project and workflow labels; source strings include a PID and may contain grouping values. Label values are stringified rather than restricted to a feature-specific allowlist. [Metrics](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/metrics.py), [source construction](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/_registry.py#L194) | Do not export this database or assume a metric prefix makes its data safe |
| Rust owns a SQLite telemetry store, transactions, validation, queries, retention, and corruption recovery. Its sample wire type accepts arbitrary label maps. [Wire](https://github.com/sase-org/sase-core/blob/6d11122eed284f2589ecfd99d3c60c02fc949dbc/crates/sase_core/src/telemetry/wire.rs#L69), [store](https://github.com/sase-org/sase-core/blob/6d11122eed284f2589ecfd99d3c60c02fc949dbc/crates/sase_core/src/telemetry/store.rs#L31) | Put feature semantics and export validation in Rust, with a dedicated typed contract |
| Flushes drain pending deltas, retry three times with delays, then drop on persistent failure. Store writes also perform retention maintenance. [Flush](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/telemetry/_registry.py#L119) | Never call this flush from a key handler; usage evidence needs visible loss and retry deduplication |
| Admin Center Statistics has eight views, shared metadata, range selection, and a worker-backed loading path with generation checks. [View registry](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/stats/registry.py#L17), [pane](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/ace/tui/modals/statistics_pane.py#L274) | Extend this established surface and loader model |
| `sase stats` has a project report; `sase usage` already means cached LLM subscription capacity. [Stats parser](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/main/parser_stats.py#L29), [usage parser](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/main/parser_usage.py#L10) | Name the report `sase stats feature`, with UI label “Features” |
| CLI entry has bead, goal, completion, special-run, and plugin dispatch paths before normal argument parsing. [Entry](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/main/entry.py#L7), [plugin dispatch](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/plugin_commands/dispatch.py#L23) | A hook after argparse would silently omit important activity |
| Keymap metadata and canonical aliases exist; interaction performance logging uses a bounded background writer. [Keymaps](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/ace/tui/keymaps/registry.py), [writer](https://github.com/sase-org/sase/blob/a42eedc1c4679612ccfbcc277f302c88c1960b2f/src/sase/ace/tui/util/perf_writer.py#L15) | Use explicit action-to-feature mappings and bounded transport, without exporting diagnostic rows |

The audited `tui_perf.md` memory adds a crucial constraint: an async timer callback awaiting background work can still occupy Textual’s serial message pump. Collection callbacks must finish immediately; report work must use the established worker path. The note identifies an existing j/k key-to-paint p95 target below 16 ms and suitable before/after benchmarks.

The supporting infrastructure largely exists. What is missing for this purpose is a **feature inventory with trustworthy negative evidence**, not another general event log.

## 3. Lessons from other systems

**Go telemetry is the closest conceptual precedent.** It distinguishes off, local collection, and upload modes; uses lightweight counters; creates weekly reports; and uploads only counters in an approved configuration. Its memory-mapped local counters help with crashes and concurrent short-lived processes. Borrow its transparency and separation of local observation from remote reporting. Do not adopt its implementation wholesale: SASE already has Rust/SQLite infrastructure, and stack counters exceed this study’s needs. [Source: Go telemetry documentation](https://go.dev/doc/telemetry).

**Mozilla Glean shows why a declared schema matters.** Measurements must be declared and reviewed, definitions can expire, invalid data is rejected, and documentation is generated from definitions. Adopt those disciplines in a small catalog, rather than a freely extensible `track(name, properties)` API. Integrating the full Glean stack needs a stronger justification than this initial study provides. [Source: Glean design principles](https://docs.telemetry.mozilla.org/concepts/glean/glean.html).

**KDE offers a useful consent model.** Its application policy specifies opt-in telemetry, disclosure of collected information, and no device-, installation-, or user-specific identifiers. This is a useful direction; it does not establish that SASE’s eventual payload is anonymous. [Source: KDE application privacy policy](https://kde.org/privacypolicy-apps/).

**Minimization should precede redaction.** OpenTelemetry recommends limiting collection to necessary information and warns that hashing predictable identifiers may not anonymize them. Hashing repository paths, custom macro names, or usernames preserves unnecessary linkage and can permit guessing. Do not collect them. [Source: OpenTelemetry sensitive-data guidance](https://opentelemetry.io/docs/security/handling-sensitive-data/).

**SQLite is suitable with bounded access.** WAL permits concurrent readers and a writer, but still has one writer at a time; long reads can impede checkpointing, and WAL is unsuitable for a database shared across hosts on a network filesystem. Keep the database on local storage, transactions short, and queries bounded. [Source: SQLite WAL documentation](https://www.sqlite.org/wal.html).

## 4. Measure capabilities and choices

### A catalog that includes zero-use features

Create a version-controlled catalog in `sase-core`, exposed through a wire contract. Each definition should contain:

- A stable ID, plain-language name, product area, and parent feature.
- Exactly what constitutes use: explicit choice, surface viewing, or capability execution.
- Instrumentation revision, introduction/retirement version, and supported surfaces.
- Finite allowed origin, surface, action-variant, and outcome values.
- Coverage by surface: instrumented, deliberately excluded, or not yet instrumented.
- A protective/infrastructure designation where low use requires special interpretation.
- The decision question, owner, and collection rationale; an expiry/review date for temporary probes.
- Remote eligibility for each field, defaulting to false.

Keep IDs independent of display labels, function names, keyboard bindings, and user configuration. Remapping a key must not create a feature. Renaming a feature should preserve identity; changing its meaning needs a new measurement revision or ID with an explicit relationship. Never silently merge incompatible histories.

Inventory command routes and keymap registries, then manually map them to capabilities. Registries are a starting inventory, not the complete product: passive views, mouse controls, inline editors, services, and plugins need explicit treatment. CI should require a mapping or exclusion reason for each inventoried route. Do not automatically instrument every method or dependency call.

**Critical query rule:** start from the catalog and left-join observations. A query starting from observed events cannot reveal a feature that was not used.

### Minimal vocabulary

| Measurement | Record when | Interpretation |
| --- | --- | --- |
| Activation | A validated semantic action is accepted, after disabled/no-op guards | Deliberate invocation |
| Result | A measured operation reaches a defined terminal result | Completed, failed, or cancelled; not needed for every feature |
| Surface entry | A user explicitly enters a feature surface | Different from rendering or automatic restoration |
| Capability execution | A backend operation runs for an agent or service | Operational dependence, separate from direct choice |
| Active day | At least one accepted activation occurs in the surface/origin that day | Repetition across days, not elapsed session time |
| Coverage state | Instrumentation, availability, health, or version changes | Whether absence is interpretable |

Do not define success as “the handler returned.” A queued launch returns before work starts. Record acceptance at submission and terminal results at the durable operation’s completion boundary. Missing results remain unknown. Daily result totals can cross dates; do not derive conversion rates by dividing unrelated daily totals. For an initial release, counts and active days are enough without a funnel system.

For a view toggle, successful state change suffices. For a dialog, distinguish opening from submitting. Cancellation is evidence of intent, not evidence of nonuse. Keyboard and mouse should share a semantic hook. Deliberate selection of a default can count; automatic restoration of that default should not.

### Origin and duplicate control

Use `human`, `agent`, `scheduled`, `internal`, and `unknown`. Carry trusted origin through SASE-owned launch boundaries as an execution-context value; persist only the enum. A human launching an agent is one human launch activation. The agent’s later commands remain agent activity. Background polling does not become human use because a TUI is open.

Do not infer human origin solely from a terminal: agents use PTYs, and humans use pipes. Runner context can identify known SASE agents; unclassified commands remain unknown. Personal review defaults to human activity but visibly reports unknown activity rather than silently claiming complete personal coverage.

Choose one counting owner per semantic boundary. A TUI action calling a CLI and then a backend function is not three activations. Propagate transient “already counted” context or keep surface entry and backend execution as explicitly separate measurements. Durable operation IDs do not belong in the usage dataset. Internal retries do not inflate activations; a user trying again is another activation.

### Initial scope

Start with roughly 30–50 families: agent launch/management, views/grouping/filtering, artifacts, plans/questions, project selection, command access, and key administrative surfaces. Include important CLI and TUI routes together. Show the full inventory, with the rest marked “not measured.” Add detail only when a family hides a real design decision.

Initially measure built-in audited macro/plugin identifiers and a generic custom/extension category. Never capture user-defined macro names, plugin package names, custom keymap modes, or expansion text. Third-party detail needs a reviewed extension schema, not runtime strings promoted into an allowlist.

Do not sample the small semantic activation stream: losing a rare feature’s only use defeats the question. Exclude typed characters, key-repeat navigation, redraws, passive polling, and internal helper calls. Performance profiling remains separate.

## 5. Trustworthy absence is the hard part

| Evidence state | User-facing language | Review consequence |
| --- | --- | --- |
| Positive observation | “Used on 6 of 24 observed active days” | Positive evidence |
| Measured and available, with no known loss and zero uses | “No recorded use in this period” | Eligible for review |
| Missing instrumentation | “Not measured” | No usage inference |
| Version predates instrumentation | “Measurement started 12 days ago” | Restrict the window |
| Disabled, absent extension, unsupported surface | “Unavailable in this scope” | No inference about desirability |
| Paused, overloaded, corrupted, incomplete collection | “Coverage incomplete” | Suppress automatic low-use ranking |
| Recently introduced | “Too little observation” | Allow time |
| Protective/recovery function | “Rare use expected” | Different assessment |

Availability only means the capability was observed as available. It does not prove the user had a relevant task. Avoid expensive per-widget visibility tracking to manufacture an opportunity denominator. Where an existing semantic condition provides genuine opportunities cheaply, measure it selectively; otherwise label opportunity unknown.

An active day contains deliberate observed activity, not merely a running daemon. Store UTC dates and explain the boundary. Union dates across processes; do not sum per-process active-day counts. The first release should clearly be **this device**. Future private multi-device merging must union days and deduplicate imports; summing reports is not sufficient.

Record the instrumentation revision actually loaded by each process, particularly long-running TUIs. Keep observation epochs and coverage transitions. An upgrade halfway through the study cannot retroactively turn absence into zero use. Historical coverage must not be reconstructed from today’s catalog alone. Where configurations differ within a device, record aggregate availability conservatively without storing project identities; conditional availability is not universal opportunity.

Collection is observational, not transactional. Crashes can lose pending counters and even their loss markers. Distinguish “no known loss” from “complete capture.” Persisted start/checkpoint/end markers help identify an unclean collector epoch on the next run but cannot prove every invocation reached initialization. Explain that limitation in coverage details.

**Proposed review heuristic:** zero-use features become suggestions after 60 calendar days and at least 20 observed active days on the relevant surface, with measurement covering the window and no known material gaps. Exclude protective and unavailable functionality. Earlier manual inspection remains possible. This is a product default, not statistical confidence.

For intuition, assuming independent identical opportunities, zero uses in 60 opportunities yields a one-sided 95% upper probability bound of `1 - 0.05^(1/60)`, about 4.9%, not zero. Real days and opt-in submissions usually violate these assumptions. Do not display “95% safe to delete.” [Statistical basis: NIST exact binomial confidence limits](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbici.htm).

## 6. Storage and performance architecture

```text
Semantic TUI / CLI / service boundary
                 |
                 v
Prebound feature ID + finite enums
                 |
                 v
Rust in-memory counters and presence bits
                 |
       bounded periodic snapshot
                 v
Background persistence -> feature-usage.sqlite
                              |             |
                              v             v
                       Rust report      Rust export
                              |             |
                         TUI / CLI     preview package
                                            |
                                    future opt-in upload
```

Create a focused `feature_usage` domain in `sase_core`, PyO3 bindings, and thin Python adapters. Rust owns validation, accumulation semantics, daily aggregation, coverage, retention, report queries, and export projection. Python owns widgets and presentation. This respects SASE’s shared-backend boundary and gives later editor/web surfaces the same answers.

Reuse suitable SQLite helpers, worker patterns, ranges, and rendering primitives. Use a **separate database** from operational telemetry: independent privacy boundaries and retention, isolated from diagnostic churn. Do not clone a telemetry framework or refactor unrelated metrics as part of this project.

### Minimal persisted shape

| Table | Contents |
| --- | --- |
| Catalog revisions | Static definitions and measurement revisions actually observed; no user-defined names |
| Daily counts | UTC day, feature ID, revision, allowed surface/origin/outcome tuple, integer count |
| Daily coverage | Active-day presence, availability summary, health/gaps, relevant revision |
| Collector state | Short-lived random local epoch, checkpoint/clean-close state, dedup receipts; never exported |
| Settings | Consent mode/schema version, retention, explicit study start/end |

Constrain valid tuples in the catalog, rather than admitting arbitrary label combinations. Counts sum; active-day presence unions. Preserve the date of observation rather than attributing an entire flush to its write date.

Start with **180 days of daily aggregates**, enough for study and follow-up. No raw events or multi-resolution rollups in v1. “Last used” means last observed within retained data; after retention, show “earlier history unavailable.” Add a bounded disk budget, initially targeting 64 MiB including database and WAL, validated against the agreed workload. Reaching a cap is a visible coverage event. Bound auxiliary/quarantined files as well, with explicit retention semantics.

Keep owner-only files outside repositories and sidecar synchronization. Clearing this store cannot erase independent system backups. The feature collector should never copy existing operational logs into it.

### Recording and persistence

Resolve IDs and mode from already-loaded configuration and prebind handles. Disabled mode should create no worker/store/network activity and do no per-action configuration checks. Enabled recording is a bounded integer update and presence mark: no disk, serialization, subprocess, database lock, or synchronous query.

Prefer fixed-capacity counters/prevalidated slots to an event queue. One thousand activations then become one changed counter rather than one thousand queued objects. Snapshot quickly and do serialization/I/O outside the recording synchronization. The recorder must never wait for a worker’s I/O lock.

Flush long-lived processes roughly every 15 seconds, only when dirty, with jitter across processes. First feature/day presence may request an earlier background checkpoint without delaying the action. Quiet timers should only check dirty state. Shutdown requests a bounded best-effort flush; forced termination may lose the tail.

Short-lived CLI processes need a different exit path because daemon threads die with the process. Try one small end-of-command transaction with a short busy wait; stop retrying within the command latency budget. Measure imports and database initialization too. SQLite’s busy timeout does not bound arbitrary filesystem stalls, so latency targets are empirical rather than hard real-time guarantees. If real CLI overhead or loss is unacceptable, evaluate a local collector or mapped counters as a second iteration. Do not build that complexity speculatively.

Persist immutable batches with a random local ID. In one transaction, record the dedup receipt and apply deltas. Retry ambiguous failures with the same ID and payload so a committed write with a lost acknowledgement does not count twice.

Bound backlog, retries, and receipt retention. For example, retry at most 24 hours, retain receipts seven days, and reject batches older than the receipt horizon. These horizons must be one tested contract; an old batch cannot become valid again after its receipt is deleted. Coalesce unsealed counters under pressure and preserve presence before repeated counts. Never change a sealed retry batch. If presence is also lost, expose incomplete coverage. A process exit can lose a memory-only backlog despite the retry horizon; document this explicitly.

Use typed health categories for invalid IDs, loss, pressure, and store failure. Do not write offending values or arbitrary exception text to feature diagnostics. Recording failure must preserve the original command outcome.

The current telemetry store can quarantine corruption and replace the database. A feature store must also start a new observation epoch and expose the gap: an empty replacement is not a clean zero-use study. Migration failure degrades collection while leaving the application usable. Maintenance and migrations stay away from action handlers and first paint. Stop/clear operations need generation tokens so stale workers cannot repopulate cleared history.

### Proposed acceptance gates

| Area | Initial budget/invariant | Validation |
| --- | --- | --- |
| Disabled | No worker, disk, network; negligible warmed-call overhead | Call-path audit and microbenchmark |
| Activation | Aim for p99 below 50 microseconds including Python/Rust crossing | Real adapter benchmark |
| TUI | Preserve existing p95 below 16 ms; added p95 no more than 0.5 ms | j/k benchmarks on/off under ordinary load |
| Startup | No store work before first paint; target less than 5 ms added cost | Cold/warm traces and imports |
| CLI | Target added p95 below 5 ms, p99 below 20 ms on healthy local disk | Normal and fast-path commands, concurrent writers |
| Resources | Initially target less than 2 MiB recorder memory/process and less than 1% of one CPU core under representative load | Soak, overload, aggregate multiprocess cost |
| Reports | Aim under 100 ms for a 180-day query; input stays responsive | Upper-bound fixtures and UI test |
| Faults | Bounded memory/disk; continued input | Locked/full/read-only database, slow worker/filesystem, crash |

Confirm these targets on Bryan’s machines. A bad baseline does not excuse more regression: compare absolute and enabled-minus-disabled latency. Measure p99/max stalls and both event-loop and message-pump progress, not just mean throughput.

Textual documents moving blocking work into workers and safely delivering results back to UI code; SASE’s more specific pump rules govern the integration. [Source: Textual workers](https://textual.textualize.io/guide/workers/).

One dependency check belongs in the storage spike: SQLite documents a WAL-reset corruption fix in 3.51.3, with backports in 3.44.6 and 3.50.7. Confirm the SQLite runtime linked into the shipped extension includes the fix before expanding multiprocess WAL use. The crate version alone is insufficient evidence; this research did not execute or certify the runtime version. [Source: SQLite WAL-reset fix](https://www.sqlite.org/wal.html#walresetbug).

## 7. UX: a calm feature review within Statistics

Use **Admin Center → Statistics → Features**, backed by `sase stats feature`. This avoids confusion with subscription capacity and performance diagnostics. Statistics already needs compact layouts; adding a view requires responsive-tab, keymap, default-config, and help updates. Do not add a global TUI tab.

Answer, in order: what period/device/origin is selected; how much was actually measured; and which features deserve inspection.

### Illustrative layout

All names and numbers below are synthetic, not findings about Bryan’s use.

```text
STATISTICS / FEATURES                               Private · stored on this device
Last 60 days     This device     Human activity      Data through 14:32 UTC

28 active days       32 of 40 features measured      8 need more evidence

[Overview]  [Review]  [Coverage]                      Search features…

FEATURE                    DAYS USED     USES    LAST OBSERVED    EVIDENCE
Open artifacts              22 / 28       184    Today            Measured
Choose grouping             11 / 28        47    Yesterday        Measured
Choose layout                0 / 28         0    —                Review
Recovery action              0 / 28         0    —                Rare use expected
Extension commands              —          —    —                Not measured

Choose layout
No recorded use across 28 observed active days.
Available throughout this window. No known collection gaps.
Measures explicit layout changes, not the layout restored at startup.

[Inspect feature]  [Keep]  [Review later]  [Export review]
```

**Overview** uses a ranked horizontal bar chart of days used, a table, and a small weekly trend for the selected feature. Keep invocation counts secondary: repeating an awkward action 200 times does not imply 200 units of value. Avoid pie charts, global activity scores, and screens dominated by frequent navigation.

**Review** shows candidates with evidence and exclusions. A detail pane explains the measurement, coverage, origin mix, documentation, and suggestion reason. Offer keep, review later, and export review; no delete-feature button. Initially, annotations can live in an explicitly exported Markdown review instead of adding a persistent task workflow. Annotations never enter telemetry sharing.

**Coverage** shows uninstrumented routes, known loss, unavailable features, version boundaries, pauses, retention limits, and unknown origin. Keep catalog coverage distinct from observation coverage; a single percentage hides too much.

A small feature-by-week grid may supplement the table: filled for use, open for measured zero, dash for unavailable, `?` for unknown. Include a legend and text equivalent. Unknown must not look like a lighter zero. Such a grid helps assess changes over time, but the table remains the primary decision surface.

### Visual and interaction design

Reuse the Statistics accent (`#FF87D7` in the current registry), typography, panels, ranges, and spacing. Accent indicates selection. Zero-use rows are neutral; amber indicates incomplete evidence; red indicates actual collector failure, not lack of feature use. Align numbers and keep definitions easy to open. Avoid animated charts and continuously ticking counters.

Use table/detail columns at wide widths; move detail below or open it on selection at narrow widths. Hide secondary columns first. Support keyboard use, plain text, and explicit state labels independent of color. Respect configured bindings rather than hardcoding new global shortcuts.

Load only while visible, show cached data immediately, query in a worker, reject stale generations after filters change, coalesce refresh, and preserve selection by stable feature ID. Refresh manually or at a modest visible-only cadence; do not scan history per interaction. All missing/error states should already be in the core view model.

Do not expose a project filter for data that intentionally contains no project identity. Scope is this device. Origin filters must visibly change denominators. Default to a 60-day study window while reusing existing range syntax.

### First run and controls

When off, show a short explanation and **Start private study**. Describe the counters and exclusions, show duration, and state nothing is uploaded. A 60-day study can stop collection at its end, retain data according to retention, and offer an explicit extension without repeated nagging.

Separate controls for pause collection, stop sharing, clear local history, and preview export. Pausing retains history. Clearing previews affected data and resets the epoch. Stopping sharing cancels unsent packages while private collection may continue. Preview shows exactly what would leave the device.

Consent is durable configuration, not a temporary feature flag. An upgrade must never silently migrate a private study into sharing.

Proposed CLI additions, following alphabetical help and short-alias conventions:

```text
sase stats feature -r 60d
sase stats feature -r 60d -j
sase stats feature -r 60d -f markdown
sase telemetry feature status
sase telemetry feature start
sase telemetry feature stop
sase telemetry feature export
```

These names are proposals, not available commands. The telemetry subgroup manages the study; stats reads it. Do not ship command stubs.

A later self-contained offline HTML export could provide larger charts and filtering for monthly reviews without a server. Embed all assets, use no external fonts/scripts/network, escape data, and retain an accessible table. Ship terminal plus Markdown/JSON first. A browser application, accounts, and cloud analytics stack are unnecessary in v1.

## 8. Privacy and eventual contribution

### Closed capture contract

Accept declared feature IDs and enum variants, not property maps, widget strings, or exception objects. Reject unknown IDs without logging the supplied value. Enforce independently at the Rust boundary, including plugin calls.

Prohibit prompts, arguments, queries, clipboard/file contents, paths, repository/project/branch names, remotes, artifact refs, bead/agent/session IDs, usernames, hostnames, IPs, custom macro names, model aliases, and raw errors. Exclude hashes of those values too. Built-in identifiers are compiled metadata, never runtime workspace names.

Daily activity is still behavioral information. This reduces content leakage and linkage; it does not prove anonymity or protect against an attacker controlling the account. Keep operational logs and private review annotations out of the feature store and all exports.

### Two data products

Private analysis needs daily detail and accurate counts. External reporting should have a separate, narrower projection:

| Field | Proposed remote treatment |
| --- | --- |
| Schema/catalog | Approved public revision |
| Application version | Coarse release cohort; development builds without commit SHA |
| Period | Completed UTC week, no event timestamps |
| Feature | Approved built-in ID only |
| Activity | Used/not-used/unknown; optional capped count bucket if justified |
| Denominator | Coarse observed active-day count and explicit measurement eligibility |
| Origin | Human/automation/unknown only if necessary |
| Device/user | No stable identity |
| OS/hardware/plugins | Omit initially; require a decision-specific justification |
| Delivery | Random per-report nonce for deduplication, never persistent installation ID |

Example count buckets: `0`, `1`, `2–5`, `6–20`, `21+`. Presence alone may suffice. Include eligibility/unknown information so a missing probe does not become zero. A complete vector of rare feature use can itself identify someone; limit report breadth to approved study questions and avoid unnecessary cross-tabs.

Without stable identity, the server cannot honestly count unique people, correlate individual retention across weeks, or collapse someone’s multiple machines. Report **eligible installation-weeks received**, not users. Document self-selection, repeated contributors, and multiple devices. Do not quietly add stable IDs to improve the chart.

Network metadata remains: TLS protects transport, but the receiving server/proxy observes IP addresses. Disable unnecessary access/body logging, restrict access and retention, and publish an accurate policy before external collection. A nameless payload is not automatically anonymous. Suppress small groups in published aggregates; a threshold alone is not a formal anonymity guarantee. Differential privacy requires separate analysis if public granular results become a goal.

### Consent and delivery

Show the exact package and destination before opt-in. Send only observations collected after consent; no automatic private-history backfill. Scope consent to the documented export schema and obtain explicit review before material expansion. Server responses cannot enable fields or collection modes.

Build an asynchronous weekly uploader separate from the TUI: TLS, strict schema/size limits, immutable package with stable nonce, bounded exponential backoff/jitter, and a small queue. Client policy is at most one report per installation per completed week; server deduplicates nonces. Retry and dedup horizons must agree. Do not synchronize everyone at midnight or hold commands open for uploads.

Show last sent, next eligible, pending packages, and retained sent copies. Stopping sharing prevents new submissions and discards unsent packages; it cannot retract accepted reports. If remote deletion is offered, retain a per-report deletion capability locally and define the guarantees. An in-flight request may already have arrived when consent changes.

Begin with manual preview/export and server fixture validation. Add scheduling after the schema and analyst questions are stable. Never archive `~/.sase`, SQLite files, log directories, or arbitrary objects for upload.

## 9. Alternatives

| Approach | Strength | Assessment |
| --- | --- | --- |
| Existing logs/source review | No runtime overhead; identify obvious dead code now | Useful companion; inconsistent coverage, weak negative evidence, private content |
| More generic metrics in existing store | Small first patch | Arbitrary labels and operational retention require hardening; poor privacy boundary |
| Raw JSONL events | Easy prototype | Unneeded chronology, growth with interactions, multiprocess/aggregation work |
| Hosted analytics/autocapture | Ready dashboards | Disproportionate dependencies, network, and privacy obligations |
| OpenTelemetry collector/dashboard | Standard operational observability | Does not solve feature inventory or deletion judgment; adds deployment burden |
| Glean stack | Strong schema/review practices | Credible if this becomes a major cross-product system; too much initial integration |
| Memory-mapped counters | Cheap multiprocess increments; crash survival | Fallback for demonstrated CLI problems; format/platform/migration complexity |
| Local collector daemon | Central writes and cheap messages | Socket lifecycle, upgrades, availability, scheduling costs; justify empirically |
| Typed daily SQLite aggregates | Fits backend, bounded and inspectable | Recommended, accepting crash-loss windows and explicit uncertainty |

Start source review immediately; do not track already conclusively obsolete features just to postpone a decision. Telemetry should resolve uncertainty, not become a ritual for every maintenance change.

## 10. Delivery and validation

**Decision inventory first.** List the families Bryan might remove or simplify and what evidence would change each decision. Map CLI/TUI routes, origins, recovery exceptions, and exclusions. Draft zero-use and unknown reports before collectors. Catalog semantics are likely harder than the database.

**Build a vertical slice.** Rust catalog/recorder/store/query, binding, and five representative features: a TUI state change, modal submission, ordinary CLI, CLI fast path, and asynchronous operation. Add a plain report and coverage. Validate latency, writers, shutdown, and failures before broad instrumentation. When Python depends on new bindings, update `sase-core-revision.txt` through the established release workflow.

**Ship the private study.** Complete 30–50 families, Statistics Features, schema documentation, controls, Markdown/JSON exports. Keep uncovered functionality visible. Run a few days of deliberate calibration against known actions, separate from organic study data, before beginning the 60-day window. Otherwise testing every feature makes everything appear used.

**Review evidence.** Inspect candidate dependencies and maintenance cost; ask who would miss them. Consider hiding rarely needed controls, merging duplicate paths, and improving discovery before removal. Follow SASE’s existing sunset-flag and migration policy for actual deprecations. This research creates no flags or task beads; low frequency is not removal authorization.

**Trial external reports last.** Implement the approved projection and ingestion fixtures, invite a small group to preview packages, then add periodic sends. Keep personal and external findings separate. Opt-in contributors are not representative of all users.

### Implementation tests that matter

- Semantic correctness: keyboard/mouse agreement, no-op guards, dialog stages, retry/wrapper deduplication, acceptance versus completion.
- Dispatch coverage: normal CLI, bead/goal fast paths, special-run and plugin paths; completion/test traffic excluded or explicitly classified.
- Privacy canaries: distinctive prompts, paths, branches, macros, and errors absent from rows, filenames, exports, and diagnostics; fuzz unknown strings at bindings.
- Day/version semantics: UTC rollover, backwards clock, long-lived old code, concurrent processes, configuration changes, retention, and future import union.
- Persistence faults: before/after commit failure, duplicate/expired batches, crash, corruption, full/read-only storage, migration failure, and lock contention; original work remains responsive.
- Consent: off emits nothing; pause retains; clear resets; sharing starts at consent; stale workers cannot recreate cleared data or reactivate collection.
- Reports: zero-row catalog entries appear; unknown never becomes zero; protected functions excluded; day counts union; CLI and TUI consume the same result.
- Visual/accessibility: wide/narrow, light/dark, no data, all zeros, mixed unknowns, store failures, keyboard-only review; extend existing snapshot workflow.
- Performance: real enabled/disabled fixtures, idle/busy/contended storage, report query during navigation, process-wide resource cost, no hidden refresh scan.

No benchmark or application test was run for this report: it changes research documentation only. Evidence is source inspection and public documentation; proposed performance/reliability contracts need the vertical-slice tests.

## 11. Remaining uncertainty

The main implementation uncertainty is whether bounded short-lived CLI writes meet overhead and loss budgets under actual SASE fan-out. Resolve that before choosing a collector daemon or mapped counters. Also test feature granularity, unknown-origin frequency, and whether time-bounded studies are preferable to an always-enabled private mode.

This research did not measure current TUI latency, inspect Bryan’s activity history, enumerate every route, or assess legal obligations of a telemetry service. It cannot identify actual unused features today. Privacy requires implementation and infrastructure validation, not just a good schema.

Judge success by useful maintenance decisions and low friction. If the study yields little value, retain a few useful counters or remove the experiment. Usage tracking itself must justify its maintenance cost.

## Recommended solution

Implement **private feature studies with a typed, versioned catalog and daily Rust-owned aggregates**, explicit coverage, and separate human/automation views. Use a bounded local SQLite store, keep recording away from TUI I/O and message-pump waits, and measure real short-lived CLI cost before expanding coverage. Present **Statistics → Features** as a clear table, evidence details, and short review list, with the same result available through `sase stats feature` and portable exports.

Begin with a consented 60-day local study and 30–50 selected feature families. Use findings to simplify or investigate, never to delete automatically. Add external contribution only after this experience is useful: separately validated weekly schema, explicit opt-in, no stable user identity, transparent delivery controls. This gives SASE a practical way to become smaller without making its users slower, less private, or less confident in what the data means.
