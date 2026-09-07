# Provider subscription usage in SASE: an ideal CLI and TUI experience

**Researcher:** A (`research.1m.cdx`)
**Date:** 2026-09-07
**Scope:** UX design for displaying subscription-usage limits; acquisition and storage
are treated as established context, not re-investigated here.

## Executive recommendation

Build this as **provider capacity**, not as a generic telemetry dashboard.

The experience should answer three questions, in this order:

1. **Can I safely start work with this provider?**
2. **Which allowance is closest to its limit, and when does it reset?**
3. **Can I trust this number?**

The best design is one coherent surface shared by the CLI and TUI:

- Store the provider-native `used_percent`, but lead every human surface with
  **`N% left`**.
- Summarize each provider by its **most constrained valid window** (the least
  remaining headroom), not by a provider-declared `primary` window.
- Expand the existing TUI **Provider Routing** modal into a **Providers** modal that
  combines capacity and routing. Each provider row shows the limiting allowance;
  selecting it shows every allowance, reset, freshness, plan, and availability.
- Keep the top bar quiet when all is healthy. Reuse/evolve the existing provider-state
  indicator for **warning, critical, exhausted, and unknown/stale states only**. A
  persistent all-provider quota ticker is too wide and too noisy for ACE.
- Put a cached warning beside a provider in the model picker when it is constrained.
  This is the point where the information changes a decision.
- Make `sase usage` a fast, cache-only human report with a stable `-j/--json`
  contract; make `sase usage refresh` explicitly fetch and then show the updated
  report.
- Treat availability, included allowance, and data freshness as separate axes. Zero
  included headroom does not necessarily mean blocked if credits or overage apply;
  failed collection never means 100% left.
- Add per-window observation time/source and provider snapshot completeness to the
  data contract before building the UI. Snapshot-level `fetched_at` and `source` are
  not sufficient once partial Claude stream events are merged with full probes.

This yields a compact, calm default and a rich drill-down. It is also honest: it never
turns missing data into reassurance, never invents a number of turns remaining, and
never interrupts work merely because a local threshold was crossed.

## Inputs and method

I reviewed the required prior report through its audited artifact reference:
`research:202609/provider_subscription_usage/provider_subscription_usage.md`. Its key
constraints are:

- Claude, Codex, and Grok can all be queried through their own logged-in CLIs without
  SASE handling credentials.
- The common measure is percent used plus a reset time; there is no common token,
  message, dollar, or task unit.
- Providers may expose multiple simultaneous windows and scopes.
- A five-minute background refresh is feasible, while the TUI must only read a cached
  snapshot.
- Claude stream events are partial freshness supplements, not complete snapshots.
- Vendor states, credits, and overage can affect whether work is actually blocked.

I then reviewed current SASE behavior and visual conventions, including the top-bar
indicator cluster, `ProviderDisablesIndicator`, the Launch Control panel, the Provider
Routing modal, provider palettes, the existing fractional-block usage bars, narrow
terminal snapshots, command conventions, and TUI performance rules. I also compared
current guidance and quota surfaces from W3C, IBM Carbon, Grafana, GitHub, OpenAI, xAI,
and the Command Line Interface Guidelines.

This is design research, not a usability study. The recommendation should still be
validated with task-based checks before landing; a short protocol appears near the end.

## The real user job

“How much usage do I have?” is not fundamentally an accounting question. In SASE it is
a **launch-planning question**:

- Should a long agent run go to Claude, Codex, or Grok?
- Is the nearly empty allowance a five-hour window that resets soon, or a weekly window
  that will constrain the next several days?
- Is the provider actually unavailable, or will it continue on credits/overage?
- Is the displayed value current enough to act on?

OpenAI explicitly notes that Codex consumption varies with model, task complexity,
context, reasoning, speed, and tools. SASE therefore must not claim “12 prompts left,”
“about 40 minutes,” or “this task will fit.” The best honest unit is the one vendors
actually supply: percentage of an allowance, paired with its window and reset.
[OpenAI’s Codex plan guidance](https://help.openai.com/en/articles/11369540)
also tells users to determine which allowance is exhausted and inspect its reset time,
which supports making the individual windows first-class rather than hiding them under
one provider percentage.

There are five core scenarios:

| Scenario | What the user needs | Right surface |
|---|---|---|
| Preflight before a launch | Compare providers and see the limiting window | TUI Providers modal; constrained hint in model picker |
| Ambient operation | Notice only meaningful risk or loss of visibility | Conditional top-bar indicator |
| Shell check | Scan all windows and resets quickly | `sase usage` |
| Automation | Stable typed states and timestamps | `sase usage -j` |
| Diagnosis | Learn why a probe/auth/cache is unhealthy | Selected-provider detail; `sase doctor -C provider.usage` |

The design should optimize these jobs rather than maximize the number of places a
percentage can be painted.

## Design principles

### 1. Display headroom; store usage

The persistence contract should retain `used_percent`, because that is what the vendor
reported and values above 100 are meaningful. Human surfaces should derive:

```text
remaining_percent = max(0, 100 - used_percent)
```

and render **`46% left`**, never a naked `46%`. A naked percentage is ambiguous, and
“46% used” makes the user perform the subtraction needed for the actual decision.

For over-limit values, do not silently cap the meaning:

```text
0% left · exceeded by 7%
```

Default views should use whole percentages. Raw decimals stay available in JSON.
Decimal precision communicates confidence the upstream data often does not deserve.

### 2. A provider’s headline is its most constrained allowance

A provider with 80% session headroom but 4% weekly headroom has **4% left**, for the
purpose of “how close am I to a limit?” The headline-selection algorithm should be:

1. Explicit vendor `rejected`/exhausted state wins.
2. Among current, applicable, complete windows, select the smallest remaining percent.
3. Break ties deterministically by the shortest reset horizon, then stable window key.
4. If a known applicable window is expired or unknown and completeness cannot be
   established, the provider summary is `unknown`/`partial`; do not summarize from the
   reassuring subset.

Keep window rows in a stable order (shortest duration, then label/key) and mark the
limiting row. Do not reorder the detailed list every five minutes as percentages move.

The existing proposed `primary` flag can remain provider metadata, but it should not
drive the safety headline. “Primary” is not the same as “binding.”

### 3. Separate allowance, availability, and confidence

These are independent:

| Axis | Examples | Why it matters |
|---|---|---|
| Included allowance | `46% left`, `0% left` | How much subscription headroom remains |
| Availability | allowed, warning, rejected, using overage, credits available | Whether another run can proceed |
| Confidence | fresh, aging, stale/unknown, partial, refreshing | Whether the number is safe to trust |

Never derive availability from the percentage alone. At 0%, one account may be blocked
until reset while another continues on credits. The default row can say `0% left ·
credits available` or `exhausted · blocked until reset`; details may explain the
continuation mode. No purchase flow is needed in v1.

This distinction matters increasingly as vendors add flexible usage. OpenAI now tells
users to inspect exhausted allowances, credit balance, and reset options separately,
while xAI documents a shared included pool plus extra credits.
[OpenAI](https://help.openai.com/en/articles/11369540),
[xAI](https://docs.x.ai/grok/faq)

### 4. Unknown is a state, never a number

Monitoring systems treat missing data as a distinct condition because retaining or
substituting a numeric state can be deceptive. Grafana has explicit `No Data` handling
and warns that connecting gaps or mapping nulls to zero can materially change what a
dashboard appears to say.
[Grafana missing-data guidance](https://grafana.com/docs/grafana/latest/alerting/guides/missing-data/),
[Grafana dashboard troubleshooting](https://grafana.com/docs/grafana/latest/visualizations/dashboards/troubleshoot-dashboards/)

Recommended display states, assuming a five-minute collection cadence:

| Condition | Headline treatment | Detailed treatment |
|---|---|---|
| At most 2× cadence old and before reset | `46% left` | Normal timestamp; latest probe error may be noted |
| Between 2× and 4× cadence | `~46% left · 14m old` | `aging`; no new threshold notifications from it |
| More than 4× cadence old | `usage unknown` | Last known value and failure remain in dim history text |
| Reset crossed without a newer observation | `usage unknown · reset passed` | Prompt `u` update; never infer a fresh 100% |
| Full probe missing one expected window | `partial data` | Show valid windows, but no reassuring provider summary |
| Refresh running | Keep prior state plus `updating…` | Never blank the panel or move selection |

The exact 2×/4× defaults can be tuned, but they should scale with cadence rather than
be independent user-facing knobs. An explicit vendor state can remain visible as “last
known rejected,” but stale data must not trigger new routing actions.

### 5. Use color as emphasis, not meaning

W3C requires a visible cue in addition to color. Carbon likewise recommends combining
color, symbol/shape, and text for status, and advises against highlighting information
that does not need attention.
[W3C WCAG 2.2, Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html),
[Carbon status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)

Use this compact vocabulary consistently:

| State | Symbol | Text | Color role |
|---|---:|---|---|
| Healthy | `·` or none | `46% left` | Provider accent / normal text |
| Warning (≤25% left) | `!` | `low` or explicit `N% left` | Amber |
| Critical (≤10% left) | `!` | `critical` / `N% left` | Red |
| Exhausted/rejected | `×` | `exhausted` / `blocked` | Red/orange |
| Aging | `~` | `14m old` | Dim amber |
| Unknown/error | `?` | `usage unknown` | Dim gray |

Vendor color should identify the provider, while alert color communicates state. Do
not recolor the provider name red and remove its identity; color the status symbol,
meter, and state phrase instead.

### 6. Use a capacity meter, not task-progress semantics

IBM Carbon explicitly distinguishes task progress from capacity-like values such as
storage. A quota display is not a process moving toward completion, so it should not
animate, say “progress,” or show a loading bar that empties and refills ambiguously.
[Carbon progress-bar guidance](https://carbondesignsystem.com/components/progress-bar/usage/)

Use a short horizontal **remaining-capacity meter**, analogous to a battery or Grafana
gauge. Grafana describes gauges as the right visualization for one value against a
known minimum and maximum, including resource availability.
[Grafana gauge guidance](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/gauge/)

In SASE’s terminal grammar, filled cells mean capacity left:

```text
█████████░  90% left
█████░░░░░  46% left
█░░░░░░░░░   9% left  !
```

This can reuse the established partial-block renderer and `provider_bar_style()` from
ACE’s model-usage strip, with a separate warning/critical override. The numeric label
is always adjacent. At narrow widths, drop the bar before dropping the number, window,
or reset.

## Recommended TUI

### Make the existing Provider Routing modal the detailed home

Do not create a parallel Usage modal. Usage exists to inform provider selection and
routing, and ACE already has a well-developed Provider Routing modal reachable from
Launch Control. Rename its visible title to **Providers** and enrich it.

Wide layout (illustrative, not a pixel-perfect spec):

```text
╔══════════════════════════════════ Providers ══════════════════════════════════╗
  Capacity is included subscription usage. Select a provider for every window.

  CLAUDE   !  █░░░░░░░░░   9% left   week · all       resets 4d5h   available
  CODEX    ·  █████░░░░░  46% left   5-hour          resets 2h13m  preferred ★
  GROK     ·  █████░░░░░  51% left   weekly · acct   resets 3d2h   available

────────────────────────────────────────────────────────────────────────────────
  CLAUDE · Pro · updated 43s ago via CLI
  Session          █████████░  90% left · resets in 4h12m  (Sep 7, 10:30 PM EDT)
  Week · all       █░░░░░░░░░   9% left · resets in 4d5h   ← limiting
  Week · Opus      ██████░░░░  55% left · resets in 4d5h
────────────────────────────────────────────────────────────────────────────────
  u=Update usage  p=Prioritize  d/enter=Disable  s=Soft disable  x=Enable  esc=Back
╚════════════════════════════════════════════════════════════════════════════════╝
```

The provider rows remain one line each. The existing fixed detail strip can show a
one-line provenance header plus up to three common windows. If a plugin returns more,
the detail strip scrolls or shows the limiting windows plus `+N more`; the CLI remains
the unabridged view.

On a narrow terminal, preserve meaning by removing decoration in this order: bar,
absolute reset time, plan/source, model count. Keep provider, state symbol, percent
left, window, relative reset, and routing status:

```text
  CLAUDE  !  9% left  week · 4d5h       available
  CODEX     46% left  5h · 2h13m        preferred ★
  GROK      51% left  week · 3d2h       available
```

Use stable column positions and stable provider order. Never sort providers by current
percentage; moving rows undermine fast scanning and can move the highlighted action
target while an asynchronous refresh lands.

### Interaction and refresh

- Opening the modal paints from the lock-free cache immediately.
- `u` means **Update usage**. Do not use `r`: `r` already means Reset in Launch
  Control, and overloading it would create an avoidable mode error.
- Updating submits the durable refresh proc. The modal retains the last good values,
  adds `updating…`, and stays navigable. Completion repaints only changed rows and
  revalidates the selected provider before updating its detail.
- A user-initiated update gets one completion toast: `Usage updated · 2 providers ·
  Grok timed out`. Background refreshes are silent.
- A failed provider does not blank successful providers. Its selected detail contains
  a short reason and one actionable next step, such as `Sign in with codex login`,
  `Update the Grok CLI`, or `Try again`.
- Reset countdown ticks only format cached timestamps. They never read disk, parse
  JSON, or start a subprocess on the Textual message pump.

### Top bar: attention, not telemetry wallpaper

Do not add the proposed permanent string
`cld 25% · cdx 9% · grk 49%` to the top bar by default. ACE already has a dense,
right-aligned cluster whose 80-column behavior is explicitly tested. A persistent
multi-provider meter competes with current model, temporary overrides, provider
disables, project, stash, and notification state. It also omits the window/reset needed
to interpret the percentages.

Instead, evolve the existing provider-state indicator into a consolidated attention
indicator. Carbon’s status guidance recommends that a consolidated status use the
highest-attention underlying state and warns against indicators when no action is
necessary.

Examples:

```text
 ! CLAUDE 9% left       # warning/critical headroom
 ? CODEX usage         # stale, partial, auth, or probe failure
 × GROK limit 3d2h     # rejected until reset
 ! CLAUDE 9% +1        # more than one provider needs attention
```

Clicking it opens **Providers** directly with the implicated provider selected. Its
tooltip lists all affected providers, the binding window, reset, and data age. If a
hard/soft disable or temporary priority is active, preserve the existing routing
meaning; do not show a second adjacent quota pill that repeats the same provider.

An opt-in `always` display mode could later show the current default provider’s
headroom on wide terminals, but it should not be the default. Under width pressure,
healthy capacity disappears first; warning/unknown state compresses to symbol,
provider, number, and `+N`. Visual regression tests must prove the whole top-bar
cluster stays in bounds at 80 columns with every other indicator populated.

### Show the warning where the decision is made

The model picker already groups models under provider headers. When a provider is
warning, critical, exhausted, or unknown, append a cache-only hint to that group:

```text
  ━ CLAUDE  11 models      ! 9% left · week
  ━ CODEX    7 models
  ━ GROK     4 models      ? usage unknown
```

Healthy providers need no suffix. Selecting a model remains possible in v1; no quota
confirmation dialog should interrupt launch. An explicit rejected/hard-disabled state
continues through the existing provider-guard flow. This contextual hint is more useful
than an always-visible dashboard because it appears exactly when the user chooses a
provider.

### Notifications

Local threshold crossings should not generate transient toasts by default. Carbon
recommends allowing users to limit non-critical notifications and reserving disruptive
styles for critical messaging.
[Carbon notifications](https://carbondesignsystem.com/patterns/notification-pattern/)

Recommended policy:

- Warning threshold: visual state only.
- Critical threshold: create one durable notification only if the provider is the
  current default/preferred provider or an active pool member; default off until the
  displayed data has earned trust.
- Vendor `rejected` or usage-limit auto-disable: one combined durable notification,
  not separate “quota exhausted” and “provider disabled” messages.
- Deduplicate by provider + window key + reset cycle. No repeated alert on every
  five-minute poll.
- Quietly clear attention after a fresh post-reset observation. Do not toast “back to
  100%.”
- Never notify from aging, stale, partial, or stream-only-incomplete data.

## Recommended CLI

### Command shape

Use a top-level group because the concept is short and discoverable:

```text
sase usage                         # delegates to list; cache-only
sase usage list                    # explicit equivalent
sase usage list -p codex           # one provider
sase usage list -v                 # provenance, plan, full timestamps/diagnostics
sase usage list -P                 # plain one-record-per-window output
sase usage list -j                 # stable versioned JSON envelope
sase usage refresh                 # refresh all applicable providers, wait, then show
sase usage refresh codex claude    # refresh selected providers
sase usage refresh -b              # submit durable proc and return its id
```

Suggested public options, following SASE’s “every long option has a short alias” rule:

- `-b, --background` on `refresh`
- `-j, --json`
- `-p, --provider NAME` on `list` (repeatable)
- `-P, --plain`
- `-v, --verbose`

`refresh` should attach to the durable proc and wait by default because the user asked
for fresh data and verified probes usually finish in about two seconds. `--background`
is the explicit escape hatch. The TUI always uses background behavior.

Do not make bare `sase usage` probe providers. It should be safe in scripts, fast over
SSH, and incapable of hanging on vendor subprocesses. It reads cached state and makes
freshness explicit.

### Human output

Use a compact grouped table, all windows visible by default:

```text
Provider usage                                      updated 43s ago

PROVIDER  ALLOWANCE             CAPACITY LEFT          RESETS        STATE
Claude    Session · 5h          █████████░  90%         in 4h12m      ready
          Week · all            █░░░░░░░░░   9%         in 4d5h       ! limiting
          Week · Opus           ██████░░░░  55%         in 4d5h
Codex     Primary · 5h          █████░░░░░  46%         in 2h13m      ready
          Secondary · week      ███████░░░  71%         in 5d8h
Grok      Weekly · account      █████░░░░░  51%         in 3d2h       ready

Included allowance only; credits/overage may continue after 0%.
Run `sase usage refresh` to update.
```

Important details:

- The title removes ambiguity with SASE’s own historical model-usage statistics.
- `CAPACITY LEFT` is a column heading, so inner cells can use compact numbers.
- Every provider window is visible; the binding row is marked in text.
- Relative reset is primary. `-v` adds local absolute time, zone, plan, source, and
  per-window age.
- Bars and color appear only on a TTY. `NO_COLOR`, `TERM=dumb`, non-TTY output, and
  `--plain` remove decoration. The Command Line Interface Guidelines recommend
  human-first TTY output, JSON for structure, and intentional color that disappears in
  non-interactive output.
  [CLI Guidelines](https://clig.dev/#output)
- Width degradation drops the meter before data columns. At very narrow widths, use
  one semantic line per window rather than clipped columns.

GitHub’s rate-limit endpoint is a useful precedent: each resource exposes limit,
used, remaining, and reset independently rather than collapsing unlike resources into
one total.
[GitHub rate-limit API](https://docs.github.com/en/rest/rate-limit/rate-limit)
SASE lacks a common absolute limit, so its human view should retain the same
remaining-plus-reset structure using percentages.

### JSON is a public read model, not the persistence file

Do not emit the on-disk wire snapshot “verbatim.” That couples automation to internal
storage, forces every client to reimplement reset expiry/staleness/binding selection,
and makes future storage migrations unnecessarily breaking.

Emit one stable, versioned status envelope on stdout with no notices or decoration:

```json
{
  "schema_version": 1,
  "generated_at": 1788806400,
  "providers": [
    {
      "provider": "codex",
      "status": "ok",
      "freshness": "fresh",
      "availability": "allowed",
      "binding_window_key": "weekly",
      "remaining_percent": 46.0,
      "plan": "pro",
      "windows": [
        {
          "key": "weekly",
          "label": "Week",
          "used_percent": 54.0,
          "remaining_percent": 46.0,
          "resets_at": 1789257600,
          "observed_at": 1788806357,
          "source": "probe",
          "state": "allowed"
        }
      ],
      "reason_code": null
    }
  ]
}
```

Derived fields must come from the shared Rust read model used by the TUI, not from a
second CLI implementation. Keep timestamps numeric and states/codes stable. Human
diagnostics may change wording; automation should branch on `status`, `freshness`,
`availability`, and `reason_code`.

`list` should exit zero when the store was read successfully even if an individual
provider is `not_applicable`, `unsupported`, or `unauthenticated`; those are data
states. Unknown provider filters and an unreadable/corrupt store are command errors.
`refresh` should report partial failures in the envelope/table and return nonzero only
when the requested refresh operation itself had no usable completion. Diagnostic
messages go to stderr; the report/JSON goes to stdout.

### Doctor is diagnostic, not a second usage command

Add a `provider.usage` doctor check for:

- hook/probe availability;
- CLI version support;
- auth/account mode;
- cache readability and schema;
- last full refresh age;
- last error code.

Do not print quota percentages in normal `sase doctor`. A healthy check can collapse to
one line; `-v` shows per-provider detail. Usage values belong to `sase usage`.

## UX-driven corrections to the proposed data contract

The prior report’s contract has snapshot-level `fetched_at` and `source`, while Claude
events can merge only one or two windows into an older complete probe. That makes a
single age/source inaccurate. Reliable rendering requires:

```text
ProviderUsageSnapshot additions:
    full_observed_at: float | None   # last observation known to enumerate all windows
    completeness: "full" | "partial"

UsageWindow additions:
    observed_at: float               # freshness of this exact value
    source: "probe" | "stream_event"
```

Alternatively, `completeness` can be derived from an observation-kind ledger, but the
read model must expose the result. A partial event may refresh a known window without
making an unmentioned model-scoped weekly allowance fresh.

Also centralize these derived functions in the Rust core so CLI, TUI, model picker,
notifications, and future routing agree:

- `remaining_percent(window)`;
- `freshness(window, now, cadence)`;
- `binding_window(snapshot, now)`;
- `provider_capacity_summary(snapshot, now)`;
- `provider_attention(summary, thresholds)`.

The renderer must not guess expected windows based on provider name. Provider probes
declare whether an observation is full, and merge semantics retain per-window facts.

## Alternatives considered

| Alternative | Benefit | Problem | Decision |
|---|---|---|---|
| Permanent top-bar ticker for every provider | Fastest raw glance | Wide, noisy, ambiguous without windows, collides with existing pills | Reject as default; optional future wide mode |
| One worst percentage across all providers | Tiny | Hides which provider/window; can imply whole fleet is unusable | Reject |
| Separate Usage modal | Conceptually pure | Duplicates provider list and separates capacity from routing decision | Reject |
| Add percentages only to Launch Control rows | No new modal | Informational state mixed with editable settings; insufficient room for windows | Reject |
| Providers modal + alert-only top bar | Contextual, calm, actionable, reuses navigation | Requires careful responsive layout | **Recommend** |
| Probe whenever UI opens | Always fresh | Delays first paint and can freeze/fail at the worst moment | Reject; cache first, explicit async update |
| Show last good indefinitely with “stale” suffix | Preserves a number | Users anchor on the number and overlook the qualifier | Reject after bounded aging period |
| Convert unknown/error to 0% used | Easy charting | Falsely communicates full capacity | Reject categorically |
| Block or reroute launches at local thresholds | Prevents limit hits | Percent alone cannot predict task cost; freshness/provider continuation differ | Defer beyond trusted display-only v1 |
| Show only the provider’s `primary` window | Simple | Can hide the binding weekly/model window | Reject |

## Thresholds and wording

Default local thresholds should be expressed in remaining headroom:

- warning: **25% left**;
- critical: **10% left**;
- exhausted: vendor state or `used_percent >= 100`;
- vendor `allowed_warning`/`rejected` overrides local presentation severity.

Keep thresholds configurable globally and per provider, but do not expose staleness
math as a first-release configuration burden. Wording should remain literal:

- `9% left`, not `almost out` alone;
- `resets in 4d5h`, not just an absolute date;
- `usage unknown · timed out 14m ago`, not `error -1`;
- `API-key account · subscription usage not applicable`, not `unsupported`;
- `CLI too old · update Grok`, not a traceback;
- `0% included left · using credits`, not `available 0%`;
- `account-wide` or `shared across products` when the provider documents that scope.

Absolute reset time in details should include the local zone abbreviation. If the zone
or reset is ambiguous, show the ISO timestamp in verbose/JSON output rather than
silently interpreting it.

## Implementation and rollout order

1. **Truthful shared read model.** Add per-window observation provenance,
   completeness, expiry, binding selection, remaining derivation, and fixture tests in
   Rust/core bindings.
2. **CLI.** Ship `sase usage` and `refresh`; this validates wording, failure states,
   provider fixtures, and the JSON contract without UI risk.
3. **Providers modal.** Enrich the existing Provider Routing modal, cache-first; add
   `u` refresh and wide/narrow snapshots.
4. **Decision-point hints.** Add warning/unknown suffixes to provider headers in the
   model picker.
5. **Attention integration.** Fold warning/critical/unknown into the existing provider
   top-bar state and durable notifications, with deduplication.
6. **Observe before automation.** Keep v1 display-only. Consider proactive soft
   disables only after real-world freshness and false-alert data demonstrate trust.

No direct HTTP fallback, credential handling, purchase action, burn-rate prediction,
or fleet synchronization belongs in this UX phase.

## Acceptance criteria

### Truth and failure handling

- Every human percentage says `left` or `used`; none is naked.
- A provider with several windows headlines the valid window with least headroom.
- Reset-crossed, expired, partial, malformed, unauthenticated, unsupported, and timed-
  out observations never render as healthy capacity.
- A partial Claude event updates only its windows and their ages; it does not make the
  provider’s complete set look freshly probed.
- Values over 100 preserve exceedance in detail/JSON while the remaining meter stops at
  zero.
- Availability does not become `rejected` solely from a local percentage threshold.
- Last-good data survives transient failure for diagnosis, but leaves the headline
  after the bounded aging period.

### TUI behavior

- First paint performs no probe, subprocess, network call, unbounded lock, or disk parse.
- Countdown ticks format cached timestamps only.
- Refresh completion cannot move the user’s highlighted provider or overwrite detail
  for a newly selected provider.
- One failed probe never blanks other rows.
- Warning/critical/unknown remain distinguishable with all color disabled.
- Snapshots cover at least 120×40, 80×30, and 70×32, long provider/window labels, three
  Claude windows, multiple Codex buckets, credits/overage, partial data, and every
  failure state.
- A fully populated 80-column top bar remains in bounds; healthy usage yields before
  warnings and existing active-control indicators.
- Existing ACE navigation performance target (j/k p95 under 16 ms) remains intact.

### CLI behavior

- Bare/list output is cache-only and fast.
- `refresh` has per-provider and whole-operation timeouts and cleans up every child.
- TTY output is attractive; non-TTY/plain output is stable; JSON is one versioned
  envelope with no decoration.
- Provider filters, partial refresh, all-failed refresh, corrupt cache, account switch,
  and post-reset expiry have explicit tests and documented exit behavior.
- Human and JSON summaries match the TUI because all consume the same core read model.

### Notification behavior

- No notification is produced from stale/partial data.
- Threshold notices are transition-based and deduplicated by reset cycle.
- Existing usage-limit disable and new capacity warning do not double-notify.
- Background success is silent; user-requested refresh completion is concise.

## Lightweight usability validation before landing

Give the CLI output and three TUI snapshots (healthy, critical, stale/partial) to at
least one experienced SASE user and one terminal user unfamiliar with the feature. Ask
them, without explanation:

1. Which provider is safest for a long run right now?
2. What is Claude’s constraining allowance, and when does it reset?
3. Can Codex run after its included allowance reaches zero?
4. Is Grok’s displayed number current enough to trust?
5. How would you update only Claude from the shell?

The design passes if each answer takes only a few seconds and nobody reverses “used”
and “left.” Any need to explain a symbol, bare percentage, or stale qualifier is a
design defect, not a documentation problem.

## Final recommended solution

Ship **Provider Capacity** as a shared, truthful read model with three levels of
progressive disclosure:

1. **Decision point:** warning/unknown hints in model-picker provider headers.
2. **Ambient attention:** one conditional, responsive provider-state indicator in the
   top bar—never a permanent multi-provider ticker.
3. **Full understanding and action:** the existing Provider Routing modal, renamed
   **Providers**, showing the limiting capacity on each provider row and all windows in
   the selected detail; the CLI mirrors this through `sase usage`.

Human-facing numbers are remaining capacity, always labeled and paired with a window
and reset. The most constrained complete window drives the summary. Per-window
freshness and full-vs-partial observation state prevent false reassurance. Availability
and credits/overage remain visibly separate from included headroom. Refresh is cached,
asynchronous in the TUI, explicit in the CLI, and isolated per provider.

The visual tone should be calm when healthy, unmistakable when attention is needed,
and candid when SASE does not know. That is the combination that makes this feature
intuitive, reliable, and beautiful.

## Sources

- Required SASE context: `research:202609/provider_subscription_usage/provider_subscription_usage.md`
- Current SASE source and snapshots: `src/sase/ace/tui/_app_layout.py`,
  `src/sase/ace/tui/widgets/provider_disables_indicator.py`,
  `src/sase/ace/tui/modals/models_panel_provider_modal.py`,
  `src/sase/ace/tui/modals/models_panel_provider_rendering.py`,
  `src/sase/ace/tui/modals/alias_history_usage_rendering.py`,
  `src/sase/ace/tui/provider_styles.py`, `src/sase/default_config.yml`, and
  `tests/ace/tui/visual/snapshots/png/models_panel_provider_*`.
- [OpenAI: Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540)
- [xAI: Grok Usage & Limits FAQ](https://docs.x.ai/grok/faq)
- [GitHub: REST API endpoints for rate limits](https://docs.github.com/en/rest/rate-limit/rate-limit)
- [W3C: Understanding WCAG 2.2 Success Criterion 1.4.1, Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
- [IBM Carbon: Status indicators](https://carbondesignsystem.com/patterns/status-indicator-pattern/)
- [IBM Carbon: Progress bar usage](https://carbondesignsystem.com/components/progress-bar/usage/)
- [IBM Carbon: Notification pattern](https://carbondesignsystem.com/patterns/notification-pattern/)
- [Grafana: Gauge visualization](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/gauge/)
- [Grafana: Handle missing data](https://grafana.com/docs/grafana/latest/alerting/guides/missing-data/)
- [Grafana: Troubleshoot dashboards](https://grafana.com/docs/grafana/latest/visualizations/dashboards/troubleshoot-dashboards/)
- [Command Line Interface Guidelines: Output](https://clig.dev/#output)
