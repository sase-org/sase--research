---
create_time: 2026-08-14
updated_time: 2026-08-14
status: research
---

# SuperGrok Subscription Tiers: What Each One Buys, and Which to Pick

**Research question:** What SuperGrok price tiers exist as of August 2026, what does
each tier actually include, and which one should Bryan subscribe to?

**Scope and evidence status.** Researched 2026-08-14. xAI's own pages (`x.ai/grok`,
`grok.com/pricing`) and Grokipedia returned HTTP 403 to automated fetches, so **no
first-party pricing page was readable for this note**. Every price below comes from
secondary aggregators, news coverage, and screenshots/announcements relayed through X
posts, cross-checked across at least two independent sources. `docs.x.ai` was readable
and is the authority for Grok Build's authentication behavior. Treat prices as
*corroborated but not vendor-confirmed*, and confirm in the app before paying.

**Freshness warning.** This lineup is moving fast. SuperGrok Lite appeared 2026-03-25,
SuperGrok Plus appeared around 2026-08-01, and Grok 4.6 shipped 2026-08-12 — two days
before this note. Anything here could be stale within weeks.

---

## 1. Bottom line

**Subscribe to standard SuperGrok at $30/month, billed monthly — not annually.**

It is the cheapest tier that unlocks the thing you actually need (Grok Build coding-agent
access backed by subscription auth rather than metered API credits), and monthly billing
keeps you free to move as xAI reshuffles the ladder, which it has now done twice in five
months. Spend the first week measuring real burn with `/usage`, then decide whether to
stay, step up to Plus, or switch the SASE provider to an API key.

The full reasoning is in §6. §7 covers the case where this recommendation is wrong for
you.

---

## 2. The tier ladder as of 2026-08-14

There are seven consumer-reachable rungs, but only four of them are "SuperGrok" proper.
The other three are X-bundled subscriptions that include some Grok access.

| Tier | Price | Billing surface | Positioning |
|---|---|---|---|
| Free | $0 | grok.com / apps | Trial-grade. Tight limits, latest models gated. |
| X Premium | ~$8/mo | X | Social perks first; Grok access is incidental. |
| **SuperGrok Lite** | **$10/mo** | grok.com | Casual/creative. Imagine-focused, 1 agent. |
| **SuperGrok** | **$30/mo** ($300/yr) | grok.com | The real baseline for serious use. |
| X Premium+ | ~$40/mo | X | Social perks + Grok at roughly SuperGrok level. |
| **SuperGrok Plus** | **$100/mo** ($1,000/yr) | grok.com | Capacity relief for power users. |
| **SuperGrok Heavy** | **$300/mo** | grok.com | Max limits, first model access, video. |

### What each tier adds

**Free.** Enough to evaluate the product. Latest-generation model access is staged or
absent, limits reset aggressively, and it is not a viable backing for an automated agent.

**SuperGrok Lite — $10/mo** (announced by Musk 2026-03-25). Explicitly aimed at people
who want Grok Imagine without paying $30. Reported contents: basic image and video
generation capped at 480p / 6-second clips, roughly 2× longer chats than free, and access
to **one** AI agent. Reported *exclusions* matter more than the inclusions: no full
DeepSearch, no full-capacity Big Brain mode, no multi-agent, and no confirmed
frontier-model access. This is a consumer creative tier, not a developer tier.

**SuperGrok — $30/mo or $300/yr.** The cheapest standalone path to the full product.
Includes DeepSearch (live web research), Big Brain / extended thinking, Expert mode,
image generation, voice mode (~30 min/day), real-time X data, and Grok Build access.
Annual billing is ~17% off, working out to ~$25/mo.

**X Premium+ — ~$40/mo.** Roughly SuperGrok-equivalent Grok access, plus ad-free X,
the largest creator revenue share, longer posts, and priority replies. Worth considering
*only* if you independently want the X perks — you are paying ~$10/mo more than
SuperGrok for social features, not for AI capacity.

**SuperGrok Plus — $100/mo or $1,000/yr** (rolled out ~2026-08-01, no formal press
release; details relayed via X). Everything in SuperGrok plus: significantly higher usage
across Chat, Imagine, Voice **and Build**, faster replies, priority access at peak times,
single-prompt app creation with one-tap deploy, and early access to new features. Its
stated reason to exist is precisely the gap it fills — people who exhausted the $30 pool
mid-week but could not justify $300.

**SuperGrok Heavy — $300/mo.** The top tier. Reported deltas over standard SuperGrok:
roughly 3×–5× overall usage, ~4× message limits, >2× image generation, voice at 120
min/day (vs 30) with priority speech processing, and **video generation exclusive to this
tier** (10 clips/day, 15s, 1080p). Historically the only tier with confirmed *full*
frontier-model access at launch — standard SuperGrok and X Premium+ received Grok 4.5 in
stages. Heavy now also **bundles X Premium+ at no extra cost** (link your X account in
the Grok app), which is a real ~$40/mo of value if you were paying for both.

---

## 3. The mechanic that actually matters: one shared weekly pool

This is the single most important structural fact, and it is under-reported in the
pricing listicles.

Paid Grok plans do **not** meter each product separately. On grok.com and the mobile
apps, a paid subscription draws from **one shared weekly usage pool spent across Chat,
Imagine, Voice, Build, and API usage**. Warp's integration documentation states this
directly, and it is consistent with xAI's model-aliasing behavior (`grok-4.5` resolving
to a `-build` subscription variant so requests ride subscription quota rather than billed
API credits).

Three consequences:

1. **Coding-agent work and casual chat compete for the same budget.** A heavy Grok Build
   session and an afternoon of image generation deplete the same meter. If you plan to
   drive Grok Build from SASE, assume your chat headroom shrinks accordingly.
2. **Tier choice is mostly a capacity decision, not a feature decision.** Above the $30
   line, you are largely buying pool size and priority, not new capabilities — with the
   notable exceptions of video (Heavy only) and app deploy (Plus and up).
3. **You cannot plan against published numbers, because there aren't any.** xAI does not
   publish a stable per-tier Grok Build quota table. Warp defers to xAI; xAI's own Grok
   Build docs are silent on quotas.

### On the circulating limit numbers

Treat every specific figure with suspicion. Across sources, standard SuperGrok's message
allowance is variously reported as **1,000/day and ~100/day** — a 10× disagreement, which
tells you the aggregators are guessing. Figures that recur more consistently (~50
images/day, ~50 DeepSearch queries/day, ~30 min/day voice on SuperGrok) are more likely
directionally right but are still unconfirmed.

**The authoritative number is the percentage and reset schedule under Settings → Usage in
your own account.** Limits also appear to flex per-account under fair-use policy.

---

## 4. Grok Build access, since that is your real use case

Your `202608/grok_build_provider/` research already established that SASE should
integrate Grok Build's headless interface as a first-party `grok` provider, and your
recent `llm_provider` commits show that integration is live. So the relevant question is
not "which tier gives the best chat experience" but "which tier backs an automated coding
agent, and how."

**Authentication.** Per `docs.x.ai/build/overview`, Grok Build supports two paths:
browser-based OAuth on first launch, and `XAI_API_KEY` for non-browser environments
(remote hosts, containers). These bill differently:

- **Browser/subscription auth** rides your SuperGrok weekly pool. No per-token charges.
- **API key** bills metered credits. A consumer subscription does **not** include API
  credits, and the two are separate billing surfaces.

**Tier eligibility.** Grok Build subscription auth is reported to work with **SuperGrok
and X Premium+** accounts. SuperGrok **Lite is not** in the supported set — consistent
with its single-agent, no-DeepSearch consumer framing. This is the hard floor that makes
$10 a non-option for you.

**Model.** Grok 4.6 shipped 2026-08-12 and is live in Grok Build, Cursor, Grok Bot, and
the API: 500k-token context, text+image input, and low/medium/high/xhigh reasoning effort.
Inside Grok Build it is reported as tied to SuperGrok and X Premium+ accounts and should
appear in the model picker automatically. Note this is a real change from the Grok 4.5
era, when Heavy was the only tier with confirmed full access at launch — worth
re-verifying rather than assuming either pattern holds.

**Metered comparison.** Grok 4.6 API pricing for prompts under 200k input tokens is
reported at **$2.00/M input, $0.50/M cached input, $6.00/M output**. At those rates,
$30/mo buys roughly 5M output tokens' worth of spend — so the subscription wins for
sustained agent work, and the API key wins for bursty or precisely-budgeted use. (An
older 2026-05-15 rate card at $1/$0.20/$2 per M plus ~$5/1k tool calls also circulates;
prices have clearly moved, so re-check before modeling costs seriously.)

---

## 5. Alternatives considered

**SuperGrok Lite at $10.** Rejected. It excludes full DeepSearch and multi-agent use and
is not in the reported Grok Build support set. Saving $20/mo to lose the entire use case
is not a trade.

**X Premium+ at ~$40.** Rejected unless you independently want X perks. It reaches
SuperGrok-class Grok access but costs ~$10/mo more for social features. If you *do* value
ad-free X and creator revenue share, this becomes the better $40 than "SuperGrok plus a
separate $8 Premium."

**SuperGrok Plus at $100.** Deferred, not rejected. It is the right answer *if* you hit
the wall — but you have no evidence yet that you will, and its own marketing positions it
as a remedy for a problem you have not yet demonstrated. Buying it preemptively is paying
$840/yr extra for an unmeasured need. Revisit after a week of real telemetry.

**SuperGrok Heavy at $300.** Rejected for now. Its distinctive extras — 1080p video, 120
min/day voice, priority speech — are irrelevant to a SASE provider integration. The
bundled X Premium+ is genuine value but only nets out if you wanted X Premium+ anyway,
and even then $300 vs $40 is a $260/mo premium for capacity you have not shown you need.
The historical "only tier with full frontier access" argument has weakened now that Grok
4.6 reaches SuperGrok accounts in Grok Build.

**API key only, no subscription.** A legitimate alternative and the better choice for
*non-interactive* SASE agent runs specifically: costs are transparent, attributable
per-run, and immune to consumer fair-use throttling that could stall an automated agent
mid-task. Its downsides are unbounded spend and no access to the consumer chat surface.
This is not mutually exclusive with a subscription — see §6.

---

## 6. Recommendation

**Start with standard SuperGrok, $30/month, billed monthly.**

Why this tier:

- It is the **hard floor for your use case**. Grok Build subscription auth requires
  SuperGrok or X Premium+; Lite does not qualify. $30 is the cheapest qualifying rung.
- It is the **cheapest complete product**. DeepSearch, Big Brain, Expert mode, voice,
  image generation, and real-time X data are all in. Tiers above it sell capacity and
  priority, not fundamentally new capability (excepting video and app-deploy).
- It gives you a **subscription-backed provider** so SASE Grok runs don't draw metered
  credits — the right default while you are still iterating on the integration and burn
  is unpredictable.

Why monthly rather than annual:

The $300/yr option saves ~$60 (~17%), and that is a genuinely reasonable discount — but
this lineup has changed twice in five months (Lite in March, Plus in August), the flagship
model shipped two days ago, and Heavy's bundling terms changed recently too. Annual
lock-in into a ladder this unstable is a bad trade for $60. Reassess at renewal once the
tiering settles.

**Then, in your first week:**

1. Check **Settings → Usage** on grok.com. That percentage is the only trustworthy limit
   figure; ignore every number in §3 including the ones I quoted.
2. Run `/usage` inside Grok Build during real SASE work to see what an agent session
   actually costs against the pool.
3. Confirm Grok 4.6 appears in your Grok Build model picker. If it does not, the staged
   rollout is still in progress and the Heavy-tier calculus changes.

**Then branch:**

- **Pool holds comfortably →** stay at $30. Done.
- **Exhausting the pool mid-week on Grok Build specifically →** do *not* reflexively jump
  to Plus. First move automated/non-interactive SASE runs onto an `XAI_API_KEY` and keep
  the $30 subscription for interactive chat and TUI use. This splits the load across two
  billing surfaces, makes agent costs attributable per-run, and will very likely cost less
  than $100/mo. This hybrid is the highest-value move in this note.
- **Still constrained after splitting, or you want peak-time priority and app deploy →**
  step up to **Plus at $100**.
- **You separately want X Premium+ *and* are pinning the pool →** Heavy at $300 becomes
  defensible, since it absorbs the ~$40 X Premium+ cost. Otherwise skip it.

---

## 7. Where this recommendation breaks

Be honest about the failure modes:

- **If you want 1080p video generation**, nothing below Heavy delivers it. That is a
  hard capability gate, not a capacity one.
- **If you are already paying for X Premium+**, recompute from a $40 baseline, not $0 —
  the SuperGrok-vs-Premium+ comparison inverts, and Heavy's bundle gets more attractive.
- **If the Grok 4.6 rollout to standard SuperGrok stalls**, the historical pattern
  (Heavy-first frontier access) reasserts itself and the $300 tier regains its main
  argument. Verify in the model picker.
- **If a consumer fair-use throttle interrupts an automated SASE agent mid-run**, that is
  an availability problem no consumer tier reliably solves; move to the API key.
- **If any price here is wrong**, it is because no first-party page was machine-readable
  on 2026-08-14. The tier *structure* is well corroborated; individual dollar figures,
  especially X Premium at ~$8 and X Premium+ at ~$40, deserve a glance at the live
  checkout page before you commit.

---

## 8. Sources

Vendor documentation (readable):

- [xAI — Grok Build overview](https://docs.x.ai/build/overview)

Integration documentation (independent corroboration of the shared-pool mechanic):

- [Warp — SuperGrok subscription](https://docs.warp.dev/agent-platform/inference/grok-subscription/)
- [Grok Build 2026 Guide: Plans, Models, Limits, and Commands](https://shareallai.github.io/familypro/en/blog/grok-build-guide/)
- [Grok Build Pricing: SuperGrok, X Premium+ and Heavy (2026)](https://www.codeagentswarm.com/en/guides/grok-build-pricing)

Tier announcements (relayed via X, not official press releases):

- [X Freeze — SuperGrok Plus launch](https://x.com/XFreeze/status/2083028422419222923?lang=en)
- [blankspeaker — SuperGrok Plus tier details](https://x.com/blankspeaker/status/2083025532766294085)
- [Muskonomy — Heavy includes X Premium+](https://x.com/muskonomy/status/2077824177248350528)
- [Enterprise DNA — xAI added a $100/month SuperGrok Plus tier](https://enterprisedna.co/resources/ai-pulse/ai-pulse-2026-08-02-xai-added-a-100-month-supergrok-plus-tier/)
- [PiunikaWeb — Musk unveils $10/month SuperGrok Lite](https://piunikaweb.com/2026/03/25/elon-musk-supergrok-lite-post/)

Pricing and limits aggregators (used for cross-checking; individually unreliable):

- [FelloAI — Grok Pricing 2026: Plans, Weekly Usage Limits and API Costs](https://felloai.com/grok-pricing/)
- [PricePerToken — Grok Pricing & Plans (2026): SuperGrok Tiers Compared](https://pricepertoken.com/subscriptions/grok)
- [AI Tool Analysis — SuperGrok Subscription Price 2026](https://aitoolanalysis.com/supergrok-subscription-price-2026/)
- [Dynalord — Grok Pricing Explained (2026)](https://dynalord.com/blog/grok-pricing)
- [CostBench — Grok Pricing 2026: $8–$300/month Plan Breakdown](https://costbench.com/software/ai-chatbots/grok/)
- [Jin Grey — SuperGrok vs SuperGrok Heavy Limits](https://jingrey.com/tools/supergrok-vs-supergrok-heavy-limits/)
- [Jin Grey — Grok Usage Limits Guide 2026](https://jingrey.com/ai-tech/grok-usage-limits-guide/)
- [ai-x.chat — Grok Usage Limits: Weekly Pool, Free & API Quotas](https://ai-x.chat/guide/grok-usage-limits/)

Grok 4.6 release coverage:

- [Grok 4.6 is out: available in Cursor, Grok Build, Grok Bot and the API](https://pasqualepillitteri.it/en/news/10915/grok-4-6-released-cursor-grok-build-api)
- [ai-x.chat — Grok 4.6: API, Pricing, Context Window & Benchmarks](https://ai-x.chat/models/grok-4-6/)
- [explainX — Grok 4.6 Launch](https://explainx.ai/blog/spacexai-grok-4-6-launch-evals-cursor-august-2026)

Related internal research:

- `202608/grok_build_provider/grok_build_provider.md` — Grok Build as a SASE LLM provider.
