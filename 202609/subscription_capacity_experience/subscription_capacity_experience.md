# Subscription capacity: the CLI and TUI experience SASE should build

Research synthesis · 2026-09-07

**Recommendation:** make subscription usage a small, trustworthy decision aid. Lead
with **percentage left**, identify the allowance and reset, and make uncertainty
visible. Use one **Providers** home in ACE, contextual model-picker hints, a quiet
attention indicator, and `sase usage` in the shell. Ship observation before prediction.

The experience should answer: **What remains? What could constrain this model? When
does that allowance reset? How current is the reading?** It cannot promise that an
unknown future task will fit.

## Evidence and scope

I read the [original integration research](../provider_subscription_usage/provider_subscription_usage.md)
through `sase artifact read` before conducting independent research. It establishes
CLI-based collection, a shared Rust store, background refresh, and passive Claude
observations. This report designs the experience around that foundation; it does not
retest credentials or repeat live probes.

The two dispatch inputs were identified by registered agent identity and canonical
suffix, confirmed with artifact metadata, and read through audited research references:

| Researcher | Preserved report | Immutable registered reference |
|---|---|---|
| `research.1m.cdx` · A | [Capacity UX](subscription_capacity_experience__a.md) | `file:explicit:52bf89e9c6e04eb0cbe389d9` |
| `research.1m.cld` · B | [Quota UX](subscription_capacity_experience__b.md) | `file:explicit:a637bfe7270ff782a215604b` |

Their original canonical labels were
`research:202609/provider_usage_capacity_ux__a.md` and
`research:202609/provider_quota_ux__b.md`. Both local copies retain exactly the bytes
of their registered snapshots. No predecessor chats were consulted.

My independent work checked official vendor and design documentation, inspected
SASE's current UI and routing code, and tested the reports' proposed arithmetic
against counterexamples. Report B's live observations remain attributed to B. All
mockups below are **illustrative fixtures**, not current account readings. This is
an evidence-informed design recommendation, not a completed usability study.

## What survives consolidation

| Decision | Resolution and reason |
|---|---|
| Used or remaining? | Both researchers favor remaining. Store vendor `used_percent`; consistently display `N% left`. |
| Primary or most constrained window? | Use the most constrained **applicable** window; retain its scope. Neither vendor position nor a model-specific minimum describes the entire provider. |
| Pace gauge as the foundation? | Keep B's question about lasting until reset; decline its single-snapshot forecast and multi-segment meter as defaults. They add assumptions and decoding work. |
| Main TUI location? | Evolve Provider Routing into one Providers home, as A recommends. Add a read-only Usage view; keep routing changes in an explicitly selected Routing view. |
| Ambient display? | Merge attention into the existing provider indicator. A permanent three-provider ticker is optional future customization. |
| CLI name? | `sase usage`, titled **Subscription usage**. “Quota” is useful explanatory vocabulary but does not justify a second command name in v1. |
| Refresh behavior? | Cached reads; explicit refresh waits with a deadline in the CLI and runs asynchronously in ACE. |
| Automation contract? | A versioned public status model, following A; never expose storage verbatim. Defer B's launch-gating `check` command. |
| Aliases and pools? | Preserve B's insight that users choose aliases. Show their members and constraints; never invent a combined percentage. |
| History and attribution? | Useful later in detail. They are not prerequisites for a complete, attractive first experience. |

## The distinctions that keep the UI honest

**Percentages are comparable as proximity to each allowance's limit, not as amounts
of work.** A provider with 80% left may have less effective work capacity than another
with 30% left. Do not rank providers as “best,” sum their percentages, or translate
headroom into prompts, tokens, money, or guaranteed runtime. OpenAI documents that
similar-looking tasks can consume different allowances because model, context,
reasoning, tools, retrieval, and caching affect consumption.
[Codex usage guidance](https://learn.chatgpt.com/docs/pricing)

**Included allowance, continuation, and SASE routing are separate facts.** At 0%
included left, a provider may reject requests or continue using credits. A provider
can also have ample allowance while deliberately disabled in SASE. Display those
facts separately; never let a full bar imply permission or an empty bar imply a hard
stop. Grok documents a shared weekly pool across products with optional paid
continuation. Its usage can move outside SASE.
[Grok usage and limits](https://docs.x.ai/grok/faq)

**An observation is not a reservation.** Even a just-refreshed reading can change
before launch, through concurrent agents or other product surfaces. “Observed 20s
ago” is accurate; “safe to launch” is an unsupported guarantee. A locally counted
`4 SASE agents running` can provide context, but cannot explain all account usage
or establish attribution.

### Scope before aggregation

Codex exposes separately identified buckets, optional display names, window durations,
reset timestamps, and server-classified limit states. The public contract does not
justify hard-coding `primary = 5h` or treating every bucket as the same allowance.
[Codex app-server rate limits](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt)

For a selected model, compute the minimum headroom across **all applicable limits**:
account/product limits plus any model-specific limit. B's suggestion to use the
model-specific window *instead of* the unscoped one can hide an exhausted shared
allowance. Applicability comes from provider metadata or an explicit mapping; never
infer it from a bucket's position or an unfamiliar internal identifier.

For the provider overview, show the lowest observed headroom with its scope:

```text
Claude   6% left · Model X week
         All-model allowance: 54% left
```

That means Model X has a constraint; it does not mean every Claude model has 6% left.
If the scope cannot be resolved, say `6% left · scope unknown`, expose the vendor
label in detail, and withhold model-specific conclusions. If any applicable window
is missing or stale, show `partial data` while retaining known constraints. A known
rejection remains visible beside that qualifier.

When several applicable windows are exhausted, each reset stays visible. The earliest
reset is not necessarily the time service resumes. Only display “blocked until” when
the provider explicitly supports that conclusion; otherwise say “window resets in.”

### Why the default should not predict exhaustion

B proposes `projected_end_use = used_percent / elapsed_fraction`, with a 15%
early-window guard and a 110% deadband. This is a constant-average-consumption
assumption. It is not a noise-free measurement or a prediction validated by checking
one account snapshot.

Three counterexamples matter:

1. At halfway through a week, 40% used could reflect steady work, one completed
   burst, or a burst that just began. The same input yields the same prediction
   despite materially different futures.
2. At 50% elapsed and 54% used, the formula projects 108% usage. B calls that
   `clear`, yet its own linear model exhausts the allowance **12.44 hours before
   the weekly reset**. Suppressing a warning does not establish safety.
3. Deriving window start from `reset - duration` assumes that the reset describes
   a fixed consumption period. A rolling or otherwise provider-defined window may
   not support that interpretation. Calculating with today's clock and an older
   reading also makes apparent pace improve without any new observation.

Keep the useful part as a later optional **budget comparison**, with an explanation:
`40% used; 50% of this confirmed fixed period elapsed`. Do not label it `clear`,
`dry Friday`, or use it to route work. A later forecast needs explicit window
semantics, observation history, uncertainty, and evaluation against actual outcomes.
An inferred “untouched” state should likewise require provider evidence, not B's
heuristic of zero use plus a reset approximately one duration away.

### Why a pool has no honest combined percentage

SASE's current selector supports weighted round-robin pools and ordered fallback
chains (`src/sase/llm_provider/load_balancing.py`). It does not select the member with
the largest allowance percentage. B's `max(member headroom)` would advertise the
best member as though the next launch were guaranteed to use it. Weights describe
selection frequency, not the cost of each task.

Show the topology and member observations instead:

```text
@large   Claude / Model X  ! 6% left · model week
         Codex / Model Y    46% left · week
         Pool; routing unchanged
```

Evaluate each member with its own applicable limits. Do not label the pool `46% left`
or claim how many members can finish work. If future routing exposes a reliable next
target, label it as a routing preview with its own freshness, never as capacity.

## The visual language

Use a short **remaining-capacity meter**, with filled cells meaning allowance left:

```text
█████████░  90% left
█████░░░░░  46% left
█░░░░░░░░░   9% left  ! low
░░░░░░░░░░   0% included left · credits enabled
             ? Usage unknown · last observed 42m ago
```

Ten cells above illustrate approximate fill; the real renderer can reuse SASE's
fractional blocks. Labels carry precise meaning. Unknown gets no quantitative bar:
the question mark and words make it distinct without teaching B's `╬` track alphabet.
Do not animate quota or interpolate between readings.

Use provider accent colors for identity, amber for low allowance, red for very low
or exhausted allowance, and explicit words for uncertainty. Healthy rows need no
green success check. Reuse existing typography, palette, and selection treatment;
avoid a separate visual theme or a rainbow of meters. Text and symbols must preserve
meaning without color. This applies W3C's redundant-encoding principle to terminal
design, rather than claiming that terminal snapshots establish WCAG compliance.
[W3C use of color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)

Whole percentages are sufficient for ordinary display. Show `less than 1% left` for
positive sub-percent headroom and reserve `0% left` for actual exhaustion. Preserve
raw values and source precision in JSON; calculate attention from unrounded values.
Do not round a nearly full allowance to a falsely exact 100%. Values above 100% used
remain in storage and read `0% left · exceeded by N percentage points` in detail.

Initial visual thresholds: **25% left = low; 10% left = very low**. These are proposed
product defaults, not provider policy or empirically validated predictors. Show the
reset alongside them: 9% left for five minutes and for five days deserve different
human decisions. Explicit vendor warnings/rejections remain distinct from local
thresholds.

## ACE: one home, two levels of attention

Evolve the current Provider Routing modal into **Providers**, with **Usage** and
**Routing** views. Both share selected provider, ordering, and data. Usage is the
default when entered through a usage link; an existing routing action can open the
Routing view directly.

Wide-terminal sketch:

```text
 Providers                         [Usage]  Routing
 Subscription allowance · observed per provider

 PROVIDER     LEFT                 ALLOWANCE          RESET     OBSERVED
 Claude     ! █░░░░░░░░░   9%     Week · all         4d 5h     43s ago
 Codex        █████░░░░░  46%     Week               5d 8h     2m ago
 Grok         ? Usage unknown                         —        42m ago

 Claude · subscription                         SASE routing: enabled
 Session · 5h   █████████░  90% left    resets in 4h 12m
 Week · all     █░░░░░░░░░   9% left    resets in 4d 5h  ! lowest
 Week · Model X ██████░░░░  55% left    resets in 4d 5h
 Applies across Claude surfaces; includes activity outside SASE.
 Selected window: exact local reset date/time + zone · source · observed age

 u Update usage    Enter Details    Tab Next control    Esc Back
```

The provider table is a summary. Selecting a provider reveals **all** windows in a
scrollable detail area; no arbitrary three-window cap and no hidden model constraints.
Show credits or overage state only if observed, with its own age. Use `enabled in
SASE` for routing; avoid the broad assurance `ready`.

At 80 columns, remove overview bars before semantic fields. At 60 columns, stack
scope, reset, and age beneath each provider. Keep relative reset primary, with exact
date/time and timezone in details. Below one minute say `<1m`; after reset say
`reset passed · awaiting observation`. Never display negative countdowns. More space
buys helpful context, not more decoration.

### Safe, discoverable interaction

The current modal binds Enter to `disable_or_change`
(`src/sase/ace/tui/modals/models_panel_provider_modal.py`). Reusing that behavior for
a readout would surprise users. In **Usage**, Enter opens/focuses details and never
changes routing. Disable, prioritize, and drain commands belong only to the clearly
labelled **Routing** view. Keep their established keys there.

Provide a persistent **Providers → Usage** entry from Launch Control and a command
palette action **Provider usage**, searchable by `usage`, `quota`, `limits`, and
`capacity`. This keeps discovery available when no alert is present. Document any
shortcut in the help UI and `default_config.yml`; no new global chord is necessary
for v1. `u` consistently means Update usage inside the view. Tab retains normal focus
navigation; tabs themselves are keyboard-focusable controls.

Updating preserves selection, scroll position, and prior observations, with an
`Updating…` status. It finishes with one result: `Updated 2 providers · Grok timed
out`. A failed provider keeps its independent diagnostic. Esc can close Usage while
the durable refresh continues; reopening reconnects to that operation.

### Attention in the top bar; context in the picker

Extend the existing provider-state indicator rather than adding another. Default to
attention only, for providers configured for use; unsupported unused plugins should
not create permanent warnings. Examples:

```text
! Claude 9% left       ? Codex usage       Claude off · ! usage +1
```

Preserve routing information and include the affected scope in the accessible detail
or tooltip. A compact number alone must never imply a provider-wide block. Clicking
an attention item opens Usage with that provider selected. Keep stable priority and
tie-breaking; never allow a successful priority state to hide a known rejection.
At narrow widths retain the existing routing state plus a compact attention count;
all details remain keyboard-accessible.

Carbon advises restrained indicators and using the highest-attention state when
consolidating statuses. That supports an attention surface here; it is not evidence
that a particular SASE layout has passed user testing.
[Carbon status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)

The model picker already has `advisory_label` and `advisory_severity`
(`src/sase/ace/tui/modals/model_picker_rows.py`). Populate constrained/unknown rows
using **that model's applicable windows**. Put provider-wide constraints in group
headers to avoid repetition; model-specific constraints stay on affected rows.
Do not reorder, disable, or silently reroute from these readings. Existing explicit
provider-disable behavior remains authoritative.

Background threshold notifications are **off by default**. Visual attention is enough
for v1. Existing real limit/disable notifications should remain one combined event.
If notifications are later enabled, deduplicate by account, window, reset cycle, and
severity transition; a stale reading cannot generate a new capacity alert.

## CLI: fast inspection, explicit refresh

Use SASE's existing default-list convention, including its normal bare-command notice.
Examples with options always use the explicit subcommand:

```sh
sase usage                        # delegates to list; cached observations
sase usage list                   # every window for configured providers
sase usage list -p codex           # provider filter; repeatable
sase usage list -v                 # plan, source, exact times, diagnostics
sase usage list -P                 # plain records, one per window/provider state
sase usage list -j                 # versioned JSON, only JSON on stdout
sase usage refresh                # bounded refresh, wait, then display results
sase usage refresh -p claude       # same provider filter
sase usage refresh -b              # submit in background; print operation ID
```

Public options have short aliases: `--provider/-p`, `--verbose/-v`, `--plain/-P`,
`--json/-j`, and refresh-only `--background/-b`. `-j` is also available for refresh
results; with `-b`, it emits a typed submitted-operation receipt. Reject incompatible
`-j`/`-P` formats rather than guessing. Sort help entries alphabetically. Explain
“subscription allowance” prominently to distinguish this from historical model-use
statistics and API billing.

Human output uses the same labels, state rules, and meter components as ACE, showing
every window by default. A compact provider heading precedes its allowance rows.
Every provider has an observation age; differing window ages appear on those rows.
Do not give a mixed-age report one reassuring global “updated” timestamp.

Honor `NO_COLOR`; default non-TTY and `TERM=dumb` output to undecorated ASCII records.
Plain output never wraps one record across lines or clips window labels. JSON offers
the stable interface for scripts. This follows the CLI Guidelines' separation of
human formatting, plain records, and structured output.
[Command Line Interface Guidelines](https://clig.dev/#output)

`list` performs no provider calls, even with an empty cache. Show `No observations
yet · run sase usage refresh`. ACE may request an asynchronous first refresh after
painting that state. No automatic browser login or credential prompt.

`refresh` waits by default because the user asked for new readings. Use independent
provider timeouts and a whole-operation deadline, initially the prior research's
10s/30s bounds. Waiting reports progress on stderr; stdout contains the finished
table or JSON. `-b` submits the same coalesced operation ACE uses.

Define exit behavior before implementation:

| Command | Success | Failure |
|---|---|---|
| `list` | 0 when status can be reported, including absent/stale/provider-error states | 1 for unreadable/corrupt state; 2 for invalid invocation/filter |
| `refresh` | 0 when every requested applicable provider completes successfully; explicit not-applicable/unsupported results remain data | 1 when any requested applicable probe fails or deadline expires; preserve partial results; 2 for invalid invocation |
| `refresh -b` | 0 means submission/attachment succeeded, not that usage is fresh | Nonzero if submission fails |

Provider quota exhaustion itself is not a command failure. Unlike A's lenient refresh
exit proposal, partial fetch failure should be machine-visible: callers requested new
data. Omit `watch` and threshold-gating `check` from v1; JSON supplies the composition
seam without another live display loop or an implied safe-launch verdict.

## Freshness is part of the product

Use per-window observation time, account identity generation, source, and
completeness. Keep fetch attempt time separate from successful observation time.
Report A correctly identifies that refreshing two Claude windows must not make an
unmentioned model window look fresh. Claude's own status-line documentation permits
independently absent windows and removes windows after their reset passes.
[Claude status-line contract](https://code.claude.com/docs/en/statusline#rate-limit-usage)

With a five-minute collection cadence, begin with this explicit policy:

| Condition | Display and behavior |
|---|---|
| Observation ≤10m old, reset not passed | Numeric headroom and actual age; “fresh” describes observation age only |
| >10m to 20m old | `Last observed 46% left · 14m ago`; subdued meter, no fresh assurance |
| >20m old | `Usage unknown`; last known number only in detail |
| Reset passed without newer observation | `Usage unknown · reset passed`; request a coalesced refresh, never synthesize 100% |
| Incomplete applicable windows | `Partial data`; retain known low/rejected windows without a reassuring overall minimum |
| Probe failure with recent data | Keep observation with its age **and** `Update failed`; do not erase success or advance its timestamp |
| No credentials / unsupported / API account | Explicit sign-in, unsupported, or not-applicable wording; no zero or empty quota bar |
| Refresh in flight | Preserve values and age; show `Updating…` separately |
| Account changed | Invalidate the former account's view immediately; fence late results from its probes |

The 10m/20m boundaries are initial design settings to evaluate, not measured confidence
intervals. Reset expiry takes precedence. A fresh but incomplete observation is still
incomplete. Keep rejection and routing state visible as separately dated facts when
their capacity data becomes stale; elapsed time alone never re-enables anything.

For logged-out or old-CLI states, offer a provider-supported sign-in/update instruction
and a retry action in detail. Put technical diagnostics in verbose output and
`sase doctor` checks, not ordinary product copy. Doctor assesses collection health,
account mode, cache validity, age, and errors; usage percentages stay in Usage.

Credits require the same discipline: observed balance, continuation enabled, and
currently consuming credits are different facts. Codex can return a reset-credit
count without individual credit details. Omitted details mean unknown, not zero.
Display observed entitlements in detail; opening Usage must never redeem credits,
enable paid usage, or change billing.
[Codex reset-credit fields](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt)

## The implementation contract this UX needs

Put validation, merging, expiry, scope applicability, capacity summaries, and attention
classification in the **Rust core**, with bindings and a thin Python adapter. Share
pure Rich presentation components between CLI and ACE where useful; Textual layout,
focus, colors, localized words, and time formatting remain presentation concerns.
Sharing a renderer alone cannot guarantee equivalent semantics.

The public JSON read model should contain:

- A schema version and generation timestamp distinct from observation timestamps.
- Provider/account-generation identity, collection status and reason code, snapshot
  completeness, last full observation, and last attempt/error.
- Windows with stable keys, vendor label, scope/applicability, native used percent,
  derived remaining percent, reset, optional duration/period start, observation time,
  source, and explicit provider state.
- A scoped summary that can be null/partial, references the limiting window, and
  keeps continuation and SASE routing state separate.

Use null for unknown quantities. Expose stable codes for automation and redact private
account identifiers and credentials. A complete probe reconciles membership; partial
events update only their specified windows. Distinguish failed/partial decoding from
an authoritative complete result that legitimately removes a window. Reject obsolete
account generations and out-of-order observations, so a slow old probe cannot undo a
newer stream event. These are correctness requirements, not optional chart refinements.

Rendering reads an already-loaded snapshot. Disk I/O, parsing, probes, and shared-store
locks stay off the event loop **and** Textual's serial message pump. Refreshes use the
existing durable-operation path and coalesce across CLI, ACE, and scheduled requests.
Ticks derive countdown/freshness presentation from in-memory facts, update changed
rows, and preserve focus. A slow vendor never delays first paint or keyboard input.
These constraints follow the audited `tui_perf.md` memory and current provider modal
worker patterns.

## Validate the experience before adding ambition

Build a small fixture-driven CLI/ACE prototype and test these tasks with Bryan and a
few users unfamiliar with the feature. Start without explaining the meter:

1. Find the allowance constraining a chosen model and its reset within ten seconds.
2. Distinguish 0% included left with credits enabled from an explicit rejection.
3. Recognize stale, partial, never-fetched, and reset-crossed readings as uncertain.
4. Explain why an exhausted Model X allowance does not automatically block Model Y.
5. Inspect and refresh usage entirely by keyboard without changing routing.
6. Compare alias members without interpreting percentages as equal amounts of work.

Require no critical misinterpretations in these scenarios before proceeding; timing
is a proposed usability target, not a result already achieved. Observe one complete
weekly cycle for reset, partial-probe, and account-switch behavior before considering
prediction or automated routing.

Implementation verification should include shared-model fixtures for mixed windows,
sub-percent rounding, overage, stale partial merges, account switches, and out-of-order
results; CLI stdout/exit contracts; and ACE snapshots at 120, 80, and 60 columns in
color and monochrome. Test all top-bar indicators together, keyboard focus during
refresh, and a hanging probe while navigating. Reuse SASE's performance target of
p95 key-to-paint below 16ms; measure it rather than assuming cache access is enough.

History can later add a per-window trend with gaps and reset markers. A fixed 96-point
buffer at five-minute cadence covers only eight hours, so it cannot substantiate a
weekly forecast. B's reported Claude contributor percentages are useful leads, not
proof that a skill caused that share of account-wide usage; local-session attribution
is incomplete and overlapping. Neither warrants an attribution dashboard in v1.

## Recommended solution

**Build `sase usage` and one Providers → Usage view around a scope-aware remaining
meter, reset time, and visible observation age.** Deliver the shared truth model and
CLI first, then the read-only Usage view and model-picker hints, then integrate
attention into the existing top-bar provider indicator. Keep every provider window
available in detail and every routing change behind explicit Routing controls.

The ideal first release is complete at that point: quick to inspect, pleasant to
scan, honest when data fails, and useful exactly where provider decisions happen.
Make history and an optional budget comparison earn their place through observed
user need. Forecasts, aggregate pool percentages, unsolicited alerts, and automatic
quota-based routing should not be part of the default experience.
