---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
---

# SuperGrok Subscription Tiers: What Each Tier Buys, and Which to Pick

**Research question.** What SuperGrok price tiers exist as of August 2026, what does each
actually include, and which one should Bryan subscribe to?

**Answer up front: standard SuperGrok, $30/month, billed monthly.** Reasoning in §7.

---

## 1. Evidence status

Researched 2026-08-14 by three agents working independently.

**What is first-party confirmed.** `docs.x.ai/grok/faq` and `docs.x.ai/build/overview`
are readable and are the authority for the weekly usage pool, the top-up mechanism, and
Grok Build's authentication paths. These carry the load-bearing structural claims in
§4 and §6.

**What is not.** Every first-party *pricing* surface — `x.ai/grok`, `grok.com/pricing`,
Grokipedia — returned HTTP 403 to automated fetches for all three agents. Researcher A
claimed partial access to an official pricing page; that claim could not be reproduced
and its tier structure is corroborated only independently (see `__a.md`). **Treat every
dollar figure below as corroborated across independent secondary sources but not
vendor-confirmed, and check live checkout before paying.**

**One tier is not officially confirmed at all.** SuperGrok Plus ($100) has no xAI press
release. As of 2026-07-31 its own trade coverage records "Official xAI announcement: Not
yet published." It is real enough to be widely reported, but do not plan around its
stated contents.

**Freshness.** The lineup moved three times in five months: Lite 2026-03-25, the weekly
pool June 2026, Plus ~2026-08-01. Grok 4.6 shipped 2026-08-12 — two days before this
note. Assume decay in weeks.

---

## 2. Bottom line

**Subscribe to standard SuperGrok at $30/month, billed monthly — not annually.**

It is the cheapest rung that unlocks Grok Build under subscription auth, which is the
capability you actually need. Everything above it sells capacity and priority, not new
capability — with two exceptions (video on Heavy, one-prompt app deploy on Plus), neither
of which is relevant to a SASE provider integration.

Both prior researchers reached this recommendation independently, from different sources
and different framings of the ladder. That convergence is the strongest evidence here.

---

## 3. The tier ladder as of 2026-08-14

The two prior reports disagreed on the ladder's shape: researcher A enumerated **five**
tiers with no X rungs; researcher B enumerated **seven** including X Premium and
Premium+. This is not a conflict — they are describing **two different billing
surfaces**, and both are correct within their own frame.

**Standalone Grok ladder (grok.com, xAI billing)** — researcher A's five:

| Tier | Monthly | Annual | Positioning |
|---|---|---|---|
| Free | $0 | — | Evaluation only. Latest models gated, tight limits. |
| SuperGrok Lite | $10 | — | Imagine-focused consumer/creative tier. **Not a dev tier.** |
| **SuperGrok** | **$30** | **$300** | Cheapest complete product. The recommendation. |
| SuperGrok Plus | $100 | ~$1,000 | Capacity relief. *Officially unconfirmed.* |
| SuperGrok Heavy | $300 | — | Max limits, video, first frontier access. |

**X-bundled ladder (X billing)** — researcher B's additional two:

| Tier | Monthly | Grok access |
|---|---|---|
| X Premium | ~$8 | Limited, capped. Incidental to the social product. |
| X Premium+ | **$40 web / $30 mobile** ($395/yr) | Roughly SuperGrok-class. Unlocks Grok Build. |

The X Premium+ price deserves a note, because a widely-circulated figure of $16/mo is
**stale**. Premium+ was $16, went to $22, and then jumped to **$40 on web / $30 on
mobile in February 2025**, explicitly because Grok 3 was bundled in. Researcher B's
"~$40" was right; pages still quoting $16 predate the hike. (Note the inversion of the
usual pattern: Premium+ is *cheaper* on mobile, because xAI ships Grok updates to mobile
more slowly.)

### What each tier adds

**SuperGrok Lite — $10.** Basic image/video capped around 480p / 6-second clips, roughly
2× free chat length, and **one** agent. The exclusions matter more: no full DeepSearch,
no full-capacity Big Brain, no multi-agent, and — decisively — **no Grok Build**.

**SuperGrok — $30 / $300yr.** The cheapest complete product: DeepSearch, Big Brain /
extended thinking, Expert mode, image generation, voice (~30 min/day), real-time X data,
and Grok Build. Annual is ~17% off (~$25/mo effective).

**X Premium+ — $40 web.** SuperGrok-class Grok access plus ad-free X, largest creator
revenue share, longer posts, priority replies. Worth it *only* if you independently want
the X perks; otherwise you are paying $10/mo more than SuperGrok for social features.

**SuperGrok Plus — $100.** Everything in SuperGrok plus materially higher usage across
Chat, Imagine, Voice and Build, faster replies, peak-time priority, one-prompt app
creation with one-tap deploy, and early feature access. Same model as the $30 tier. Its
reason to exist is exactly the gap it fills: people who exhaust the $30 pool mid-week but
cannot justify $300.

**SuperGrok Heavy — $300.** Roughly 3–5× overall usage, ~4× message limits, >2× image
generation, voice at 120 min/day with priority speech, and **video generation exclusive
to this tier** (10 clips/day, 15s, 1080p). Also **bundles X Premium+ free** — a real
~$40/mo offset if you wanted it anyway. Historically the only tier with confirmed full
frontier access at launch; see §6 for why that argument has weakened.

---

## 4. The mechanic that actually matters: one shared weekly pool

This is the most important structural fact about Grok pricing, it is under-reported in
the pricing listicles, and — unlike the prices — **it is first-party confirmed**:

> "Rolling out in June 2026, Grok will now use a simpler, more flexible system for paid
> users. Instead of separate daily limits for each product (like Chat, Imagine, Voice,
> or Build), you get one shared weekly usage pool that you can spend however you like
> across any Grok product."
> — [`docs.x.ai/grok/faq`](https://docs.x.ai/grok/faq)

Cost is compute-weighted, also per the FAQ: "A chat message uses little compute;
generating a high-quality video or running a long coding task uses far more." The Usage
tab in Settings shows percentage consumed, the weekly reset schedule, and a per-product
breakdown across **API, Build, Chat, Imagine, and Voice**.

Three consequences:

1. **Coding-agent work and casual chat compete for one budget.** A heavy Grok Build
   session and an afternoon of image generation drain the same meter. Long coding tasks
   are explicitly called out as expensive. If you drive Grok Build from SASE, assume your
   chat headroom shrinks materially.
2. **Above $30, you are buying capacity, not capability.** Both prior researchers reached
   this independently. The exceptions are video (Heavy) and app deploy (Plus).
3. **You cannot plan against published numbers, because xAI publishes none.** There is no
   per-tier Grok Build quota table. The FAQ describes the mechanism and declines to give
   figures.

### When the pool runs out — and the cheap escape hatch

Neither prior report covered this, and it changes the escalation path. Per the FAQ, when
the weekly limit is hit, paid features pause until reset — but **you keep free-tier Chat
and Voice limits**, which meter separately. You then have three options, not one:

- **Buy Extra Usage Credits.** Web-only, **$5 minimum**, expire one year after purchase.
  Priced "at standard rates, which means the cost per action is higher than the effective
  rate you get from the included weekly usage in your plan."
- **Turn on Auto Top Up** for uninterrupted operation.
- **Upgrade** to a larger weekly allowance.

That $5 floor matters: **overflow is a metered $5 problem, not a $70/month problem.**
Occasionally topping up beats jumping from SuperGrok to Plus unless you are overrunning
every single week.

### Why the circulating limit numbers are wrong

Researcher B flagged that standard SuperGrok's message allowance is reported as both
1,000/day and ~100/day, and concluded the aggregators were guessing. The real explanation
is cleaner: **both are pre-June-2026 artifacts.** Per-product *daily* limits were
abolished when the weekly pool shipped. Any source still quoting a daily message cap is
describing a metering regime that no longer exists — including the "100 prompts / 100
images per two hours" figures still circulating for X Premium+, which date to the Grok 3
era in 2025.

Ignore every number in this section, including the ones quoted here. **Settings → Usage
in your own account is the only trustworthy figure.**

---

## 5. Grok Build access — the deciding constraint

This is the real question, because SASE's `grok` provider is live: `src/sase/llm_provider/grok.py`
ships today, declaring `credential_paths: ["~/.grok/auth.json"]` and
`api_key_env_vars: ["XAI_API_KEY"]`.

**Tier eligibility.** Grok Build launched 2026-05-14 restricted to **Heavy only**. Ten
days later xAI opened it to **SuperGrok and X Premium+**. All unlock the same CLI; the
tiers differ only in how much you can use it. Plus inherits access as a superset.

**SuperGrok Lite is excluded.** This is what makes $10 a non-option rather than merely a
weaker one — it disqualifies the tier from the use case entirely. **$30 is a hard floor.**

### Correction: headless does *not* force an API key

Researcher B described two auth paths — browser OAuth, and `XAI_API_KEY` "for non-browser
environments (remote hosts, containers)" — and built its hybrid recommendation on the
premise that headless SASE runs therefore need a metered key. **That premise is wrong.**
There are three paths, and the third is subscription-backed:

| Path | Billing | Environment |
|---|---|---|
| `grok login` (browser OAuth) | Subscription pool | Desktop |
| **`grok login --device-code`** | **Subscription pool** | **Headless: SSH, containers, CI, remote VMs** |
| `XAI_API_KEY` | Metered API credits | Anywhere |

The device-code flow is RFC 8628: it prints a URL and short code, you approve on any
browser, and it then draws on an eligible SuperGrok or X Premium subscription for
inference **instead of** a metered key. SASE's own doctor check already documents it —
"run `grok login` (or `grok login --device-code` on a headless host), or set
`XAI_API_KEY`" — as does the prior `grok_build_provider` research.

This does not kill the hybrid idea; it re-founds it. The reason to put automated SASE
runs on an API key is **quota isolation, per-run cost attribution, and immunity to
consumer fair-use throttling that could stall an agent mid-task** — not headlessness.
Headless SASE agents can ride the $30 subscription today.

### Metered comparison

Grok 4.6 (shipped 2026-08-12; 500k context, text+image in, low→xhigh reasoning effort)
API rates:

| | Input | Cached input | Output |
|---|---|---|---|
| Standard (prompt < 200k) | $2.00/M | $0.50/M | $6.00/M |
| **Long context (prompt ≥ 200k)** | **$4.00/M** | — | **$12.00/M** |

**The long-context cliff is a trap for coding agents and neither prior report caught
it.** Once a prompt reaches 200k tokens the *entire request* re-prices at 2× — a 210k
prompt is billed wholly at the higher rate, not 200k standard plus 10k premium. With a
500k-token window and a long agent session accumulating context, crossing 200k is
routine. Any API-key cost model that assumes flat $2/$6 will understate real spend,
possibly by 2×.

Rough scale: at standard rates $30/mo buys on the order of 5M output tokens. Sustained
agent work favors the subscription; bursty or precisely-budgeted work favors the key.

---

## 6. Model access is no longer a reason to buy Heavy

Grok 4.6 is live in Grok Build, Cursor, Grok Bot, and the API. If you pay for SuperGrok
or X Premium+, it should appear in your model picker automatically.

This is a real break from the Grok 4.5 era, when Heavy was the only tier with confirmed
full frontier access at launch and staged rollout left cheaper tiers behind. Much
still-indexed writing describes that older pattern and reads as though Heavy is the only
way to get the current model. **Verify in your own model picker rather than assuming
either pattern holds** — if the 4.6 rollout to standard SuperGrok stalls, the Heavy
argument reasserts itself.

---

## 7. Recommendation

**Start with standard SuperGrok, $30/month, billed monthly.**

Why this tier:

- **It is the hard floor for your use case.** Grok Build requires SuperGrok, X Premium+,
  or above. Lite does not qualify. $30 is the cheapest qualifying rung.
- **It is the cheapest complete product.** DeepSearch, Big Brain, Expert mode, voice,
  image generation, and real-time X data are all included. Higher tiers sell capacity and
  priority, not capability — excepting video and app deploy, neither of which you need.
- **It is $10/mo cheaper than X Premium+** for equivalent Grok access. Premium+ only wins
  if you independently want ad-free X and creator revenue share.
- **It backs SASE's `grok` provider under subscription auth** — including headless runs
  via `--device-code` — so agent work doesn't draw metered credits while your burn is
  still unknown.

Why monthly rather than annual: annual saves $60/yr (~17%), which is a fair discount. But
the lineup changed three times in five months, the flagship model shipped two days ago,
and the $100 tier isn't officially confirmed yet. Annual lock-in into a ladder this
unstable is a bad trade for $60. Reassess at renewal.

### First week

1. **Settings → Usage on grok.com.** The percentage and per-product breakdown are the
   only trustworthy limit figures. Ignore every number in this report.
2. **Run real SASE work through the `grok` provider** and watch what the Build slice of
   the pool actually costs.
3. **Confirm Grok 4.6 is in your Build model picker.** If not, the rollout is still
   staged and §6 changes.

### Then escalate in this order — cheapest first

Both prior reports jumped from "$30 exhausted" straight to "$100 Plus or API key." There
are two cheaper rungs before that:

1. **Pool holds →** stay at $30. Done.
2. **Occasional overrun →** buy **Extra Usage Credits** ($5 minimum, web only). Overflow
   a few weeks a year is a $5–20/yr problem, not a $840/yr upgrade.
3. **Regular overrun, driven by automated runs →** move non-interactive SASE runs to
   `XAI_API_KEY` and keep the $30 subscription for interactive use. Do this for **cost
   attribution and throttle immunity**, not because headless requires it. Budget with the
   200k long-context cliff in mind. This will very likely land under $100/mo.
4. **Still constrained, or you want peak-time priority and app deploy →** Plus at $100 —
   but wait for official confirmation of what it includes.
5. **You separately want X Premium+ *and* are pinning the pool →** Heavy at $300 becomes
   defensible, since it absorbs the ~$40 Premium+ cost. Otherwise skip it.

---

## 8. Where this recommendation breaks

- **You want 1080p video generation.** Nothing below Heavy delivers it. Hard capability
  gate, not a capacity one.
- **You already pay for X Premium+.** Recompute from a $40 baseline, not $0. The
  SuperGrok-vs-Premium+ comparison inverts and Heavy's bundle gets more attractive.
- **The Grok 4.6 rollout to standard SuperGrok stalls.** The Heavy-first pattern
  reasserts and $300 regains its main argument. Check the model picker.
- **A fair-use throttle interrupts an automated SASE agent mid-run.** No consumer tier
  reliably solves this; that is the genuine case for the API key.
- **Any price here is wrong**, because no first-party pricing page was machine-readable
  on 2026-08-14. The tier *structure* is well corroborated; individual dollar figures —
  especially X Premium ~$8 and the SuperGrok Plus contents — deserve a glance at live
  checkout first.

---

## 9. Sources

**Vendor documentation (readable, first-party):**

- [xAI — Grok Website/Apps FAQ](https://docs.x.ai/grok/faq) — weekly pool, Extra Usage
  Credits, Auto Top Up, reset behavior
- [xAI — Grok Build overview](https://docs.x.ai/build/overview) — authentication paths
- [xai-org/grok-build — authentication guide](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/02-authentication.md) — device-code flow

**Independent corroboration of the shared-pool mechanic:**

- [Warp — SuperGrok subscription](https://docs.warp.dev/agent-platform/inference/grok-subscription/)
- [Hermes Agent — xAI Grok OAuth (SuperGrok / X Premium+)](https://hermes-agent.nousresearch.com/docs/guides/xai-grok-oauth)
- [Grok Build Pricing: SuperGrok, X Premium+ and Heavy (2026)](https://www.codeagentswarm.com/en/guides/grok-build-pricing)

**Tier announcements (relayed via X, not official press releases):**

- [SuperGrok Plus launch](https://x.com/XFreeze/status/2083028422419222923?lang=en) ·
  [tier details](https://x.com/blankspeaker/status/2083025532766294085) ·
  [Enterprise DNA writeup](https://enterprisedna.co/resources/ai-pulse/ai-pulse-2026-08-02-xai-added-a-100-month-supergrok-plus-tier/)
- [AIToolsRecap — SuperGrok Plus review](https://aitoolsrecap.com/Blog/supergrok-plus-launch-pricing-2026) — records that xAI has published no official announcement
- [Heavy includes X Premium+](https://x.com/muskonomy/status/2077824177248350528)
- [PiunikaWeb — $10/month SuperGrok Lite](https://piunikaweb.com/2026/03/25/elon-musk-supergrok-lite-post/)
- [@grok — weekly limit is one shared pool](https://x.com/grok/status/2074743608389906873)

**X Premium+ pricing history:**

- [Tech.co — Musk hikes X Premium+ after Grok 3](https://tech.co/news/x-premium-price-increase-grok-3)
- [TechCrunch — X doubles Premium prices after Grok 3](https://techcrunch.com/2025/02/18/x-doubles-its-premium-plan-prices-after-xai-releases-grok-3)
- [@xDaily — $40 web / $30 mobile split](https://x.com/xDaily/status/1892107869430087784?lang=en)

**Grok 4.6 release and API pricing:**

- [OpenRouter — Grok 4.6](https://openrouter.ai/x-ai/grok-4.6) ·
  [eesel — Grok 4.6 pricing, every rate](https://www.eesel.ai/blog/grok-4-6-pricing) ·
  [Layer3Labs — API rates and cost modeling](https://www.layer3labs.io/guides/grok-4-6-api-pricing)
- [Grok 4.6 released: Cursor, Grok Build, API](https://pasqualepillitteri.it/en/news/10915/grok-4-6-released-cursor-grok-build-api)

**Pricing aggregators (cross-checking only; individually unreliable):**

- [FelloAI](https://felloai.com/grok-pricing/) · [PricePerToken](https://pricepertoken.com/subscriptions/grok) ·
  [Dynalord](https://dynalord.com/blog/grok-pricing) · [CostBench](https://costbench.com/software/ai-chatbots/grok/) ·
  [ai-x.chat usage limits](https://ai-x.chat/guide/grok-usage-limits/) ·
  [X-Autopilot X Premium tiers](https://xautopilot.app/blog/x-premium-subscription-price-2026-worth-it) *(quotes stale $16 Premium+)*

**Internal:**

- `202608/grok_build_provider/grok_build_provider.md` — Grok Build as a SASE LLM provider
- `src/sase/llm_provider/grok.py`, `src/sase/doctor/checks_providers.py` — live provider
  and its documented auth paths
- `supergrok_subscription_tiers__a.md` — researcher A provenance record (report destroyed
  pre-consolidation; see that file)
- `supergrok_subscription_tiers__b.md` — researcher B's full report
