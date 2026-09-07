# Subscription Quota UX — CLI and TUI Design (researcher B)

Design research for surfacing LLM provider subscription limits in `sase`. Builds on
`research:202609/provider_subscription_usage/provider_subscription_usage.md`, which settled
*acquisition* (per-vendor CLI probes, `used_percent` + `resets_at`, Rust-core store,
display-only v1). This report settles *presentation*: what the user sees, where, in what
words, and what happens when the numbers are missing or wrong.

Every number and every mockup below was rendered from **live probes run on athena on
2026-09-07**, not invented. Re-verification details are in §11.

---

## 1. Answer up front

**Ship one visual primitive, one renderer, four surfaces, and one new derived number.**

1. **The pace gauge** is the primitive. A headroom bar (`█` = quota left, depleting) with a
   pace tick at the even-spend position and an amber `▓` segment showing how far ahead of
   schedule you've spent. It answers "how much is left" and "am I on track" in one glance,
   with no arithmetic and no history.
2. **`used_percent` is stored; headroom is displayed.** Every user-facing percentage in this
   feature is *"% left"* and carries the word `left`. Never a bare percent, never a mixed
   convention. (Claude says "used", Codex says "left" — SASE must pick one, and the feature
   exists to answer a headroom question.)
3. **The new derived number is `pace`, not burn rate.** `used_percent ÷ elapsed_fraction`
   projects window-end usage from a *single snapshot* — no history, no noise, no
   differentiation of a jittery series. History refines it; it is not required for it. A
   1.10 deadband and an "elapsed < 15%" guard keep it from crying wolf (validated against
   live data in §4.3).
4. **Command surface: `sase quota` (alias `usage`)**, with `check | list | refresh | watch`.
5. **TUI surfaces, in descending value order:** merge quota into the existing top-bar
   provider indicator → a `,q` Quota panel → a headroom column in Config ▸ Launch → a
   usage advisory on model-picker rows (the field already exists).
6. **One renderer, three surfaces.** `sase quota`, the ACE Quota panel, and the Launch
   section render the *same* Rich renderable at different widths. The CLI and the TUI cannot
   drift, and learning one teaches the other.
7. **A stale or unknown number is rendered as a third thing**, never as a full bar and never
   as an empty one. Distinct track glyph, distinct color, explicit age.

Ranked, if only part of this ships: the pace gauge + `sase quota list` (§5) is the whole
feature at 20% of the cost; the merged top-bar indicator (§6.1) is what makes it ambient;
everything else is amplification.

---

## 2. What question is actually being asked

The brief says *"How much usage do I have until I hit a limit?"* That is three questions
wearing one coat, and a design that answers only the literal one is a worse product:

| # | Question | Asked when | What actually answers it |
|---|---|---|---|
| Q1 | *Do I have room right now?* | About to launch a big epic | Headroom %, per provider |
| Q2 | *Which provider should this go to?* | Choosing a model/alias | Headroom **compared across** providers, at the picker |
| Q3 | *Will I make it to the reset?* | Mid-session, watching a bar move | Headroom **versus time**, i.e. pace |
| Q4 | *Why is it draining so fast?* | After an unpleasant surprise | Attribution (§7.4) |

Q3 is the one every existing tool gets wrong, and it is the highest-value thing SASE can
add. A percentage plus a reset timestamp forces the user to do three mental steps —
subtract to get headroom, guess a burn rate, compare to the reset. **A good design does that
arithmetic and shows its work.** That is the whole thesis of §4.

Q2 is the one SASE is uniquely positioned to answer, because SASE is the only tool in this
space that routes across three subscriptions and knows the alias/pool topology (§7.3).

### 2.1 A note on who is asking

This runs on a host executing agents continuously across a tailnet. The numbers move without
a human present, quotas are consumed by background procs, and the human's contact with them
is a *glance* — at a top bar, at a tmux status line, at a `sase quota` in a spare terminal.
Design for the glance first and the audit second. This is the opposite of the vendor tools,
which are all designed for an interactive human who typed `/usage` and is now reading
carefully.

---

## 3. Design principles

These are the tie-breakers used throughout. Where a later section makes a debatable call, it
cites one of these.

- **P1 — Never make the user do arithmetic.** If two displayed facts must be combined to be
  useful, display the combination.
- **P2 — One framing, everywhere.** Headroom. `left`. Depleting bar. No surface may show
  "used" as its headline, because a glance across surfaces must not require re-orientation.
- **P3 — The gauge always tells the truth; the verdict only speaks when confident.** Visual
  encoding is cheap and continuous, so it can always render. Prose claims ("dry ~Thu 4pm")
  are expensive to be wrong about, so they get deadbands and guards.
- **P4 — Unknown is a third state, never a zero.** An error rendered as 0% used reads as
  "plenty"; rendered as 0% left it reads as a false alarm. Both are wrong. Unknown gets its
  own glyph, its own color, and its own words.
- **P5 — Decoration must never break the machine.** Borrowed from `usage_limit_disable.py`:
  a bug here must never mask a provider error, block a launch, or stall the UI thread.
- **P6 — Redundant encoding.** Color never carries information alone (`palette.py` already
  guards its categorical palette against CVD collisions for exactly this reason). Every
  state has a glyph and a word.
- **P7 — Say when you looked.** A confident number with an unstated age is the single
  easiest way to lose a user's trust permanently.
- **P8 — Show the escape hatch.** When headroom is gone, the display's job stops being
  measurement and becomes *what can I do* — reset credits, another provider, the reset time.
  An instrument that only reports is half a tool.

---

## 4. The core primitive: the pace gauge

### 4.1 Why "pace" and not "burn rate"

The obvious way to answer Q3 is to differentiate the snapshot series and extrapolate. That's
what the community Claude monitors do, and it has three problems on this host: agent work is
bursty (a linear fit over the last hour is meaningless when four agents just finished), it
needs history before it can say anything (so it's blind for the first hour after a reset),
and it is noisy exactly when it matters.

There is a much better estimator hiding in the data SASE already has. Every window carries
`resets_at` **and** `window_seconds`. That gives the window's start, and therefore how far
through the window you are:

```
elapsed_fraction   = 1 − (resets_at − now) / window_seconds
expected_remaining = 100 × (1 − elapsed_fraction)      # even-spend baseline
projected_end_use  = used_percent / elapsed_fraction   # linear to window end
```

This is a **single-snapshot** estimator. It works one minute after a reset. It has no noise
term. It is exactly the "budget pace" line that YNAB and Monarch draw, and the "par" line on
a scorecard — a comparison every user already knows how to read.

Burn-rate-from-history is still worth keeping, but as a *refinement for short windows*
(Claude's 5h session), not as the foundation. See §7.1.

### 4.2 The visual

Three glyph classes, one tick, over a 30-cell track (16 cells when narrow):

| Glyph | Meaning | Style |
|---|---|---|
| `█` | Headroom left | provider hue (or green ramp) |
| `▓` | Spent **ahead of pace** — quota borrowed from later in the window | amber |
| `░` | Spent on schedule | dim |
| `│` | Pace tick (drawn inside the fill when you are *under* pace) | dim |
| `╬` | **Unknown** — no reading (§8) | dim, distinct from both `█` and `░` |

Two rules generate every case:

1. Fill `█` from the left for `remaining_percent`.
2. Draw the pace boundary at `expected_remaining`. The cells *between* fill-end and the pace
   boundary are `▓` when you are over pace; when you are under pace the boundary falls
   inside the fill and is drawn as a `│` tick.

The amber run's **length is literally how far ahead of schedule you are**, in the same units
as the bar. Nothing needs to be explained.

Sub-cell precision reuses `_HORIZONTAL_PARTIALS` from `src/sase/telemetry/render/bars.py`,
which the codebase already uses for the Launch panel's model-usage strip — so this is a new
composition of an existing house style, not a new style.

### 4.3 Rendered from live data (2026-09-07 14:28 ET)

This is literal program output over the three real probe responses, not a hand drawing:

```
  CLAUDE   subscription · Max                             observed 2m ago
    Session (5h)     ████████████████████████│░░░░░   82% left    3h57m   clear        ✓
    Week · all       ██████████████████████░░░░░░░░   73% left     5d5h   clear        ✓
    Week · Fable     ████████████████████▓▓░░░░░░░░   67% left     5d5h   dry ~fri 4am !

  CODEX    ChatGPT Pro · 3 resets banked                  observed 2m ago
    Codex · week     ███████████████████████████▓▓░   91% left    6d19h   too early    ✓
    Spark · 5h       ██████████████████████████████  100% left        —   untouched    ✓
    Spark · week     ██████████████████████████████  100% left        —   untouched    ✓

  GROK     SuperGrok Heavy · account-wide                 observed 2m ago
    Week             ███████████████▓░░░░░░░░░░░░░░   49% left    3d18h   dry ~thu 4pm !
```

Read the Claude block: the session tick sits *inside* the fill (under pace, comfortable); the
all-models week is dead level (no tick visible because it coincides with the fill edge); the
Fable week shows two amber cells and earns a dated warning. Three different states, one
grammar, no legend needed.

### 4.4 The guards that make the verdict trustworthy (P3)

Live data exposed three ways a naive projection embarrasses itself. All three were caught and
fixed against the real numbers:

- **Deadband.** With `projected_end_use ≤ 110%`, say `clear`. Without this, the Claude
  all-models week (73% left vs 75% expected — two points over) produced a confident
  `dry ~sat 9am`. Near pace-ratio 1.0 the projected dry time is wildly
  sensitive to noise; the deadband is not conservatism, it is correctness.
- **Early-window guard.** With `elapsed_fraction < 15%` or `used_percent < 5`, say
  `too early`. The real Codex weekly bucket is 9% used at 2.9% elapsed — a naive projection
  says "dry in two days" from what is almost certainly one burst. The gauge still shows the
  two amber cells (the *fact* is true); the verdict declines to name a date (the *inference*
  is not supported).
- **Untouched rolling windows.** Codex's Spark buckets report `usedPercent: 0` with
  `resetsAt` exactly one full window out — a synthetic, meaningless countdown. Detect
  (`used == 0` and `|resets_at − now − window| < 2%`) and render `untouched · —`. Printing
  "resets in 6d23h" for a window nobody has touched is noise that trains users to ignore the
  column.

**Verdict vocabulary** — five values, deliberately small:

| Verdict | Condition | Marker |
|---|---|---|
| `untouched` | zero usage, synthetic reset | `✓` |
| `clear` | `projected_end_use ≤ 110%` | `✓` |
| `too early` | `elapsed < 15%` or `used < 5%` | `✓` |
| `dry ~<day> <time>` | projected exhaustion before reset | `!` |
| `at limit` | `remaining ≤ 0` (incl. Claude overage) | `✕` |

Markers reuse `_STATUS_GLYPHS` from `telemetry/render/tiles.py` (`✓ ! ✕`), so redundant
encoding (P6) comes from an existing constant.

### 4.5 Where this logic lives

`pace`, `verdict`, `remaining_percent`, `elapsed_fraction`, and `projected_dry_at` are
**derived core state, not rendering**. By the CLAUDE.md litmus test — a web UI or an editor
integration would need identical values — they belong in
`sase_core::provider_usage` alongside the store, computed once and consumed by CLI, TUI, and
`doctor`. This is what makes "one renderer, three surfaces" structurally true rather than a
convention someone eventually breaks: the *words* `clear` and `dry ~thu 4pm` are produced in
one place.

Python/TUI receives typed values and only chooses glyphs and hues.

---

## 5. CLI design

### 5.1 Naming: `sase quota`, with `usage` as an alias

The prior research proposed `sase usage`. I recommend **`sase quota (usage)`**, using the
alias mechanism the CLI already employs (`patch (changespec)`, `proc (task)`,
`stitch (vcs)`, `artifact (artifact-file)`). Nothing is lost and three collisions are avoided:

- `sase telemetry` and the Statistics pane already mean "usage" as *local activity*.
- The Launch panel already renders a strip literally captioned **"Model usage"**
  (`alias_history_usage_rendering.py`) meaning share-of-runs. A `sase usage` command that
  means something else is a genuine ambiguity in the same product.
- `usage:` is argparse's own word, printed at the top of every `--help` in the CLI.

"Quota" names exactly one thing: a subscription allowance. `sase quota` reads well, and
`sase usage` still works for anyone who reaches for it.

### 5.2 Subcommands (alphabetical, per `cli_rules`)

```
sase quota                    # delegates to `sase quota list` (default-list convention)
sase quota check [-b N]       # exit-code gate for scripts
sase quota list               # the panel
sase quota refresh            # force probes now
sase quota watch              # live re-render
```

`check` exists as its own subcommand rather than a flag on `list` so the exit-code contract
is explicit and `list` stays a pure display command. It is the automation seam: **"don't
kick off the nightly epic if headroom is under 20%"** is a one-line shell condition.

```
sase quota check -b 20 && sase run "#epic:..."     # only launch with room
sase quota check -b 20 -p claude                   # gate one provider
```

Exit codes follow `sase doctor`'s established shape: `0` when every checked window is at or
above the bar, `1` when any is below, and a distinct nonzero for *unknown* — because "I
couldn't tell" must not silently pass a gate that means "we have room". Default `-b` is 10.

### 5.3 Options

Per `cli_rules`: alphabetical, every long option has a short alias, none required.

| Option | Meaning |
|---|---|
| `-a, --aliases` | Show alias/pool headroom instead of raw providers (§7.3) |
| `-b, --below <pct>` | (`check`) Threshold; default 10 |
| `-c, --compact` | One fixed-width line, for tmux/statusline embedding |
| `-C, --color <auto\|always\|never>` | Matches the `sase stitch list` / `sase plan search` contract; honors `NO_COLOR` |
| `-j, --json` | Wire snapshot verbatim + derived fields, schema-versioned |
| `-p, --provider <name>` | Repeatable; limit to named providers |
| `-v, --verbose` | Include `unsupported` / `not_applicable` providers, probe source, raw `used_percent`, exact reset timestamps |
| `-w, --wait` | (`refresh`) Block until the refresh proc completes |

### 5.4 `sase quota list` — the panel

Uses the house CLI aesthetic verbatim (rounded `Panel`, uppercase column heads, `·`-joined
footer) — the same shape as `sase agent-cli list` and `sase repo list`:

```
╭──────────────────────────── Subscription Quota ─────────────────────────────╮
│                                                                             │
│  CLAUDE   subscription · Max                                                │
│    Session (5h)   ████████████████████████│░░░░░   82% left   3h57m  clear ✓│
│    Week · all     ██████████████████████░░░░░░░░   73% left    5d5h  clear ✓│
│    Week · Fable   ████████████████████▓▓░░░░░░░░   67% left    5d5h  dry ~fri 4am !│
│                                                                             │
│  CODEX    ChatGPT Pro                                                       │
│    Codex · week   ███████████████████████████▓▓░   91% left   6d19h  too early ✓│
│    Spark · 5h     ██████████████████████████████  100% left       —  untouched ✓│
│    Spark · week   ██████████████████████████████  100% left       —  untouched ✓│
│    3 full resets banked · expires Sep 21                                    │
│                                                                             │
│  GROK     SuperGrok Heavy · account-wide                                    │
│    Week           ███████████████▓░░░░░░░░░░░░░░   49% left   3d18h  dry ~thu 4pm !│
│                                                                             │
│  observed 2m ago  ·  next refresh 3m  ·  ,q in ACE  ·  sase quota refresh    │
╰─────────────────────────────────────────────────────────────────────────────╯
```

Details that matter:

- **Windows sharing a reset are grouped, and the reset is printed once per group.** Claude's
  two weekly windows genuinely share `Sep 12 7:59pm`; printing it twice is redundant ink.
- **Codex's reset credits get their own line** (P8). This is verified real state —
  `rateLimitResetCredits.availableCount: 3`, each titled "Full reset" with an `expiresAt` —
  and it is the single most actionable fact on the panel when a bar is short. Same for
  Claude's once-weekly `/limit-reset`, shown as a hint only when the session window is the
  binding constraint.
- **Plan name comes from the provider when it offers one**: Grok's `subscription_tier`
  ("SuperGrok Heavy") and Codex's `planType` ("pro") are real fields. Claude's prose gives
  only "subscription" — so say `subscription`, not a guess.
- **Grok is labelled `account-wide`** because the pool is shared with grok.com chat; the
  number moves when Bryan isn't looking, and the label is what stops that from reading as a
  bug.
- **Footer carries provenance and the two next actions.** Ends the panel with what to *do*.

**Responsive degradation** (compute from `console.width`): ≥100 cols as above; 80–99 drops
the verdict column (the gauge still carries it); <80 shrinks the track to 16 cells and moves
the reset to a second line. Never wrap a gauge.

### 5.5 `-c/--compact` — the statusline line

Fixed width so a tmux `status-right` doesn't jitter:

```
$ sase quota -c
cld ▆73  cdx ▇91  grk ▄49 !
```

One cell per provider encodes headroom in eight levels (`▁▂▃▄▅▆▇█`, the existing
`_VERTICAL_PARTIALS`), the number repeats it for precision, and a trailing `!` appears when
any provider has an over-pace verdict. Colored per provider; degrades to plain text under
`NO_COLOR` with no information loss (P6).

### 5.6 `sase quota watch`

Re-renders in place on the refresh cadence. Deliberately thin — it is the same renderer in a
loop, and it exists because "leave it up on a second monitor" is a real workflow on this
host. It must submit refreshes through the same coalesced durable proc as everything else,
never probe on its own schedule (a `watch` that probes independently is how you build a
refresh storm).

---

## 6. TUI design

### 6.1 Top bar: merge, do not add

The top bar already carries nine indicators. Adding a tenth for quota is the wrong move, and
there is a better one available: **`ProviderDisablesIndicator` should become
`ProviderStatusIndicator`** and own disables, priority, *and* headroom.

The argument is not just crowding. It is that these are **facts about the same objects**. A
provider that is hard-disabled by `source="usage_limit"` until 6:30pm and a provider showing
`0% left · resets 6:30pm` are the same event described twice. Two adjacent pills disagreeing
about how to say it is precisely the kind of thing that makes a UI feel unreliable. One pill,
one click target, one tooltip.

Three width tiers (the codebase already does this with `PanelTabStrip(compact_below=…)`):

```
≥110 cols   cld ▆73 · cdx ▇91 · grk ▄49
 80–109     ▆73 ▇91 ▄49                    (position encodes provider — a non-color channel)
 <80        ▆▇▄
```

**Escalation.** When a provider's unscoped window is critical or has a dated dry verdict, it
is promoted out of the glyph run into the existing pill grammar, using the existing
`PROVIDER_DISABLE_PALETTE`:

```
 GRK 49% left · dry thu 4pm    ▆73 ▇91
```

And when a provider is *actually disabled*, the disable wins the pill outright — it is the
stronger fact — with headroom demoted into the tooltip.

**Headline selection is scope-aware.** The pill's per-provider number is the worst
**unscoped** window. Claude's Fable-scoped weekly (67%) does not bind a Sonnet launch, so
letting it drive the headline over-warns; it escalates only when it is itself critical, and
then it names its scope. This is a small rule that prevents a large class of false alarms.

Refresh discipline (tui_perf 1, 2, 10): the indicator reads `peek_provider_usage()` — a
lock-free display-cache read — on the existing 30 s tick, exactly as
`ProviderDisablesIndicator` reads `peek_provider_routing_context` today. **No subprocess, no
parse, no I/O on the tick.** Timer ticks recompute countdown text only; the underlying
snapshot changes only when the durable proc writes.

### 6.2 The Quota panel — `,q`

`,q` is free in `leader_mode` (taken: `, . / ! R r M C h space g j J y u x X c @ n A m U B T L`)
and `q` for quota is the obvious mnemonic. Reached from the leader key, from clicking the
pill, and from the Launch panel.

A standalone modal, not an Admin Center tab. Admin Center is a sit-down-and-work surface
(Logs, Procs, Projects, Statistics, Updates); quota is glance-then-act, and the precedent for
provider state in a fast modal is `,m` (Models/Launch). Body content is the **same renderable
as `sase quota list`** (§1.6), plus three things the CLI can't do well:

```
┏━ Quota ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  [1] All  [2] Claude  [3] Codex  [4] Grok      [a] aliases   r refresh  ? help ┃
┠───────────────────────────────────────────────────────────────────────────────┨
┃  CLAUDE  subscription · Max        4 agents running        observed 2m ago     ┃
┃                                                                                ┃
┃   Session (5h)   ████████████████████████│░░░░░  82% left                      ┃
┃                  resets 6:29pm (3h57m)   ▁▁▂▂▃▃▄▄▅▅▆▆  clear            ✓      ┃
┃                                                                                ┃
┃   Week · all     ██████████████████████░░░░░░░░  73% left                      ┃
┃                  resets Sat 7:59pm (5d5h)  ▂▂▃▃▃▄▄▄▅▅▆▇  clear         ✓      ┃
┃                                                                                ┃
┃   Week · Fable   ████████████████████▓▓░░░░░░░░  67% left                      ┃
┃                  resets Sat 7:59pm (5d5h)  ▂▃▃▄▄▅▅▆▆▇▇█  dry ~fri 4am  !      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

1. **A sparkline of consumption within the current window**, from the observation ring buffer
   (§7.1), via the existing `render_sparkline`. It is not decoration: it is *the evidence for
   the verdict*. A user who can see the slope can judge whether to believe "dry ~fri 4am".
   Across window boundaries it draws a sawtooth, which is a genuinely lovely and legible
   shape for this data.
2. **Concurrency context — `4 agents running`.** SASE knows how many agents are on each
   provider right now; no vendor tool can show this. It is the answer to "why is this bar
   moving", available for free, and it is what turns the panel from a readout into an
   explanation.
3. **Actions**, because P8: `r` refresh (submits the durable proc — never inline, tui_perf 3),
   `enter` on a provider row opens the existing provider routing actions (disable / priority
   / drain), `y` copies a shareable summary, `?` help.

New `quota:` keymap block in `src/sase/default_config.yml` (per the `gotchas` core memory:
keymap changes must land in `default_config.yml`), following the `statistics:` /`memory:`
pattern — `next_provider: j`, `prev_provider: k`, `select_provider: "0"`,
`toggle_aliases: a`, `refresh: r`, `help: question_mark`.

First paint is cache-only; `r` submits a proc; async results re-check the selected provider
before applying (tui_perf 4).

### 6.3 Config ▸ Launch — a headroom column

The Launch panel's Providers section already renders one row per provider with disable and
priority state. Add headroom to that row:

```
CLAUDE     4 models    available · preferred      ▆ 73% left   5d5h
CODEX      6 models    available                  ▇ 91% left   6d19h
GROK       3 models    available                  ▄ 49% left   3d18h  !
```

This is *context at the point of decision*, not a second home for the feature — you are in
this panel because you are about to change routing, and headroom is the reason you would.
`enter` on the headroom cell opens the `,q` panel for detail. One renderable, reused.

### 6.4 Model picker — the highest-leverage integration

`ModelPickerRow` already carries `advisory_label` and `advisory_severity`, already rendered
by `provider_styles.model_advisory_*`. Populating them from quota state costs almost nothing
and puts the number **exactly where Q2 is asked**:

```
  claude/opus @ xhigh          ⚠ 67% left · Fable week dry ~fri
  codex/gpt-5.6-sol @ xhigh      91% left
  grok/grok-4.6 @ xhigh        ⚠ 49% left · dry ~thu 4pm
```

Rules: advisory only when below the warn threshold or carrying a dated verdict (a picker
where every row is annotated teaches users to ignore annotations); it is **advisory only** —
it never reorders, never disables, never blocks (P5, and v1 is display-only); use the
model-scoped window when the row's model has one, otherwise the worst unscoped window.

### 6.5 `sase doctor`

One line per provider, answering *"is this instrument working"* — not *"how much is left"*.
Different question, different surface; keep the number out of it.

```
llm.quota.claude   OK    probe 1.7s · subscription · observed 2m ago
llm.quota.codex    OK    app-server (experimental) · pro · observed 2m ago
llm.quota.grok     WARN  ACP _x.ai/billing returned -32601 · CLI 1.0.13 may be too old
```

### 6.6 Notifications

Recommendation: **off by default, and never a bare percentage threshold.**

A "90% used" alert fires predictably every week and is trained away within a fortnight. The
notification worth having is the *pace* one, because it carries information the user does not
already have:

> `codex` is projected to exhaust its weekly window ~9h before it resets (Thu ~4pm).

Fire at most once per `(provider, window_key, resets_at)` — the reset timestamp is a natural,
free dedup key that resets the budget exactly when the situation genuinely changes. Emit
through `notifications/senders.py`. Config: `quota.notify: off | pace | pace_and_reset`.

---

## 7. What the design requires from the data layer

The presentation above is not free. Five additions to the contract in the prior research,
each with the surface that needs it:

### 7.1 A bounded observation ring buffer

Needed by: the panel sparkline (§6.2), short-window burn refinement (§4.1).

Per `(provider, window_key, resets_at)`, keep the last N observations (N≈96 ≈ 8h at the 5-min
cadence). Dropped wholesale when the window's `resets_at` changes — **never carried across a
reset**, which would draw a false slope. This lives in the Rust store next to the snapshot;
it is a few KB.

The refinement it enables: for windows shorter than 24h, even-spend pace is a weak model
(a 5h session is bursty by nature). Use the **median of recent per-interval rates** (robust
to a single spike, unlike an endpoint slope) as a second estimator, and take the *more
pessimistic* of the two for the verdict. Long windows keep pure pace. The detail view names
which estimator spoke.

### 7.2 `window_seconds` is mandatory, not optional

The prior research's `UsageWindow` has `window_seconds: int | None`. Every derived number in
§4 needs it. It is present in the real payloads for Codex (`windowDurationMins`) and
inferable for Grok (`currentPeriod.start`/`end`) and Claude (5h session; 7d weeks). Keep the
field nullable in the wire type, but treat `None` as **"no pace, no verdict, gauge only"** —
a documented degradation, not a silent zero.

### 7.3 Alias and pool headroom

Needed by: Q2, `sase quota -a`, the panel's `[a]` view.

Bryan launches agents by *alias* (`@large`), not by provider. The user-facing question is
"can `@large` take a big epic right now", and the answer is not any single provider's number.
`affected_aliases_by_provider()` already exists in `_registry_routing.py`, so the topology is
available:

```
  @large   (claude/opus | codex/gpt-5.6-sol) || grok/grok-4.6
           ███████████████████████████▓▓░  91% left  via codex   cld 73 · grk 49
  @medium  codex/gpt-5.5 | claude/sonnet | 3 grok/grok-4.6
           ███████████████▓░░░░░░░░░░░░░░  49% left  binding grok (weighted 3×)
```

Alias headroom is `max()` over reachable members for a `|` pool or `||` chain — the pool
routes around a depleted member, so the best member is the honest first-order answer — with
`via <provider>` naming which member currently carries it. For a **weighted** pool, name the
binding member, because a 3×-weighted member running dry degrades throughput long before the
pool is empty. This is the one part of the design no vendor tool can copy.

### 7.4 An optional attribution section (Claude only, today)

The live `/usage` probe returns more than the three window lines. Verbatim from today's run:

```
Last 24h · 2861 requests · 52 sessions
  47% of your usage was at >150k context
  38% of your usage came from subagent-heavy sessions
  18% of your usage was while 4+ sessions ran in parallel
  Top skills: /sase_memory_read 50%, /sase_repo 13%, /sase_plan 11%, /sase_new_task 3% …
```

This answers Q4, and on this host it is *immediately actionable*: **`/sase_memory_read`
accounts for ~50% of Claude usage over 24h and ~51% over 7d.** That is a finding about SASE's
own skill design that no existing surface would ever have shown, and it is a strong argument
for the feature paying for itself beyond the gauge.

Design guidance: add an **optional, additive, typed `contributors` section** to the wire
schema (not a key/value bag — the prior research is right that pre-weakening the contract
into telemetry soup is a trap). Parse best-effort; on any parse failure render nothing and
never error (P5). Present it as a `[c] contributors` view in the panel, never on the glance
surfaces. Carry the vendor's own caveat verbatim — *"approximate, based on local sessions on
this machine"* — because it is materially incomplete on a multi-machine tailnet.

Longer term, SASE can compute a **better** version of this from its own agent records
(per-alias, per-project, per-xprompt, with exact attribution and no single-machine blind
spot). That is a separate, larger feature; the vendor section is the cheap 80%.

### 7.5 Heterogeneous, unnamed buckets

Live Codex returns `codex` (`limitName: null`, weekly-only, **no 5h window**) alongside
`codex_bengalfox` (`limitName: "GPT-5.3-Codex-Spark"`, 5h + weekly). Presentation
consequences: never hard-code "5h + weekly"; derive the row label from `windowDurationMins`
(`5h`, `week`) rather than from `primary`/`secondary` position; synthesize a display name for
an unnamed bucket from the provider (`Codex · week`), never print `null` or a raw
`limitId`; and sort buckets deterministically (unscoped before scoped, then by window length)
so rows don't reshuffle between refreshes — **row-order stability is a real UX property** for
a surface people glance at.

---

## 8. Degraded states — the reliability surface

This table is where "reliable" is actually won. The governing rule (P4) is that *unknown gets
its own visual identity*.

| State | Gauge | Number | Verdict | Pill |
|---|---|---|---|---|
| `ok` | full grammar | `73% left` | as computed | glyph + number |
| stale (>2× cadence) | dimmed | `73% left` | as computed | dimmed |
| very stale (>4×) | `╬╬╬╬╬╬` | `—` | `last read 73% left, 40m ago` | grey `—` |
| `error` | `╬╬╬╬╬╬` | `—` | `probe failed · <reason>` | grey `—` |
| `unauthenticated` | `╬╬╬╬╬╬` | `—` | `logged out · run: claude /login` | grey `—` |
| `not_applicable` (API key) | — | — | `API-key billing · no subscription quota` | omitted |
| `unsupported` (no CLI/hook) | hidden unless `-v` | — | `no quota probe` | omitted |
| `at limit` / overage | empty track, red | `0% left` | `at limit · over` / reset time | escalated red |

Specific rules:

- **The unknown track glyph is `╬`, not `░` and not blank.** `░` means "spent"; blank means
  "not there". A user must be able to tell "you have used all of it" from "I don't know" from
  four feet away.
- **Every degraded state names the fix where one exists** (P8): `claude /login`,
  `sase agent-cli update grok`, `sase quota refresh`.
- **One broken probe never blanks the others.** Per-provider independence, already specified
  in the acquisition research; it is a *display* requirement too — a Grok failure must not
  turn the Claude row into a `—`.
- **Never synthesize.** A parse failure produces `error`, never `0%`. A missing
  `window_seconds` produces "gauge only", never an invented window.
- **Age is always available**, and shown unprompted past 2× cadence (P7).

---

## 9. Cross-cutting

**Performance.** Every TUI read is a lock-free `peek`. Nothing in this feature may probe,
parse, stat, or block on the UI thread or in a pump callback (tui_perf 1, 2, 8, 11). Refreshes
are durable procs with `concurrency_keys=["provider-usage-refresh"]`. Timer ticks recompute
*countdown text* from an already-loaded snapshot and nothing else (tui_perf 10). The Quota
panel's first paint is cache-only and instantaneous, always.

**Accessibility.** No information is color-only (P6): every state has a glyph (`✓ ! ✕`), a
word, and a number. Under `NO_COLOR` the panel is fully legible — verified by construction,
since the amber `▓` differs from `█` and `░` in *glyph*, not just hue. Follow the existing
`--color auto|always|never` contract from `sase stitch list`.

**Time.** All formatting through `sase.core.time` (configured timezone), matching
`models_panel_provider_rendering.py`. Rule: relative for <24h (`3h57m`), weekday + absolute
for ≥24h (`Sat 7:59pm`), **both** in the detail view. Claude's prose reset times appear with
and without minutes (`6:29pm`, `8pm`) and carry an explicit zone name — parse both, resolve
with `zoneinfo`, and render in the *user's* configured zone, not the vendor's.

**Fleet.** Quota is account-wide, so every tailnet machine sees the same numbers — but each
probes independently. Keep the snapshot machine-local (no federation), and note in help that
the numbers include work done by *other* machines and by grok.com/claude.ai. The label is the
feature; the plumbing is not.

**Trust ladder.** v1 is display-only, deliberately. The soft-disable-at-90% inversion of the
sase-n4 epic is the obvious next step, and this design's `verdict` field is precisely the
right trigger for it — an explicit vendor `rejected`/`allowed_warning` state or a dated
`dry` verdict, never a bare percentage. But it must wait until the displayed numbers have
been watched long enough to be believed. **Do not ship a display and an automatic action in
the same epic.**

---

## 10. Rejected alternatives

- **"% used" as the headline.** It is what Claude shows and what most community tools show —
  but Codex shows "% left", so there is no convention to preserve, and the feature exists to
  answer a headroom question. Forcing a subtraction on every glance loses (P1). *Mitigation:*
  the detail view and `-v` print both.
- **A tenth top-bar indicator.** Rejected for §6.1's reason: quota and disables are the same
  facts about the same objects, and two pills that can disagree is worse than a slightly
  larger one.
- **A dedicated Admin Center tab.** Wrong ergonomics — Admin Center is for sitting down;
  quota is for glancing. A tab would also compete with the Launch panel for "where does
  provider state live", which is exactly the ambiguity §6.3 is designed to avoid.
- **Burn-rate-from-history as the foundation.** Blind for the first hour of every window,
  noisy under bursty agent load, and needs storage before it says anything. Pace is
  single-snapshot, immediately available, and more robust; history is kept as a refinement
  and as *evidence* (the sparkline), not as the estimator of record.
- **Token or dollar figures.** No vendor publishes them to subscribers. Any number SASE
  synthesized would be a guess wearing a unit, which is the fastest way to destroy trust in
  a measurement tool.
- **A blocking launch guard at low headroom.** v1 is display-only, and P5 says decoration
  must not break the machine. The model-picker advisory (§6.4) gets ~90% of the value with
  none of the risk of a bug in a quota parser preventing a launch.
- **Reset notifications on by default.** Claude's session window resets ~5×/day. Opt-in only.

---

## 11. Verification

Everything factual in this report was probed live on athena, 2026-09-07 ~14:28 ET, against
`claude 2.1.263`, `codex-cli 0.153.4`, `grok 1.0.13`:

- **Claude** — `claude -p --output-format json "/usage"`: `total_cost_usd: 0`,
  `num_turns: 0`, 729 ms. Returned `Current session: 18% used · resets Sep 7, 6:29pm
  (America/New_York)`, `Current week (all models): 27% used · resets Sep 12, 7:59pm`,
  `Current week (Fable): 33% used · resets Sep 12, 7:59pm`, plus the attribution block quoted
  in §7.4. Note the model-scoped window is **Fable**, not Opus — labels are dynamic and must
  never be hard-coded.
- **Codex** — `codex app-server` JSON-RPC `account/rateLimits/read`: `rateLimitsByLimitId`
  with `codex` (weekly, 9% used, resets Mon Sep 14 9:36am) and `codex_bengalfox`
  ("GPT-5.3-Codex-Spark", 5h 0% + weekly 0%, both synthetic resets), `planType: "pro"`,
  `rateLimitResetCredits.availableCount: 3`.
- **Grok** — `grok agent stdio` ACP `_x.ai/billing`: `creditUsagePercent: 49.0`,
  `currentPeriod` 2026-09-04T13:19:34Z → 2026-09-11T13:19:34Z,
  `subscription_tier: "SuperGrok Heavy"`.

The gauges in §4.3 are literal output of a renderer written against these responses. The
deadband and early-window guards in §4.4 exist because the first version of that renderer
produced a false `dry ~sat 9am` and an alarmist Codex projection from this exact data.

Codebase grounding: `_app_layout.py`, `widgets/provider_disables_indicator.py`,
`widgets/_override_pill.py`, `modals/models_panel_providers.py`,
`modals/models_panel_provider_rendering.py`, `modals/model_picker_rows.py`,
`modals/alias_history_usage_rendering.py`, `modals/config_center_catalog.py`,
`telemetry/render/{bars,sparkline,tiles,palette,axis}.py`, `agent_clis/cli_list.py`,
`llm_provider/_registry_routing.py`, `llm_provider/usage_limit_disable.py`,
`default_config.yml`; reference memory `cli_rules.md`, `tui_perf.md`; core memory `gotchas`.

---

## 12. Recommended solution

**Build the pace gauge as a shared renderer in `sase_core` + one Python rendering module, and
light it up on four surfaces in this order.**

| # | Deliverable | Why this order |
|---|---|---|
| 1 | `window_seconds` mandatory-in-practice; `remaining_percent`, `elapsed_fraction`, `pace`, `verdict`, `projected_dry_at` computed in `sase_core::provider_usage`, with the §4.4 guards and a `╬`/unknown state | Everything else consumes this; computing it once is what stops CLI and TUI from drifting |
| 2 | `quota_rendering.py` — the gauge, the provider block, the compact line; pure Rich, no Textual, width-parameterized | The "one renderer, three surfaces" guarantee |
| 3 | `sase quota (usage)` — `check`, `list`, `refresh`, `watch`; `-a -b -c -C -j -p -v -w` | Whole feature usable, scriptable, and reviewable before any TUI risk |
| 4 | Merge quota into `ProviderStatusIndicator` (replacing `ProviderDisablesIndicator`), three width tiers, scope-aware headline | Makes it ambient; this is what changes daily behavior |
| 5 | `,q` Quota panel + `quota:` keymap block in `default_config.yml`; observation ring buffer and sparkline | The detail and evidence surface |
| 6 | Launch-panel headroom column; model-picker `advisory_label` | Context and decision point; both are small deltas to existing rows |
| 7 | Alias/pool headroom (`-a`, `[a]`); opt-in pace notification | The SASE-unique layer, once the base numbers are trusted |
| 8 | `sase doctor` lines; attribution `[c]` view; flag removal | Diagnostics and the Q4 payoff |

Steps 1–3 are the minimum viable feature and are independently valuable. Step 4 is what makes
it *felt*. Steps 5–8 are amplification and can be reassessed after 4 lands.

**The three decisions to get right, because they are expensive to reverse:** headroom framing
everywhere (P2); pace as the derived metric with real deadbands (§4.4); and unknown as a
visually distinct third state (P4). Everything else in this document is refinement.

### Open questions for Bryan

1. **`quota` or `usage` as the canonical name?** I recommend `quota` with `usage` as an
   alias (§5.1); the collision with the Launch panel's existing "Model usage" strip is the
   strongest argument, but it is your vocabulary.
2. **Merge the top-bar pills, or ship quota adjacent first?** I recommend merging from the
   start (§6.1). The fallback — ship adjacent, merge in a later phase — is safer for tests
   but leaves a period where two pills describe the same event differently.
3. **Is the pace tick worth the explanation cost?** It is the one genuinely novel element.
   I believe it is self-teaching within a day and it is what makes the feature better than
   any vendor's; but if you want v1 to be maximally conservative, the gauge works without it
   and the tick can be a later addition (the amber `▓` segment would simply not be drawn).
4. **Attribution view in v1 or later?** The `/sase_memory_read` ≈ 50% finding (§7.4) suggests
   it pays for itself immediately, but it is a prose parser on a section that is clearly still
   evolving, and it is Claude-only.
