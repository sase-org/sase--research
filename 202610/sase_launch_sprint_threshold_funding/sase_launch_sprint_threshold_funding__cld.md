# Funding sase at Launch with Threshold Pledges ("Fund It, or I Go Get a Job")

**Date:** 2026-10-15 · **Researcher:** cld (one of four in a research swarm) · **Type:** decision research + critique

**Question:** The first sase blog post will say plainly that you have to stop developing sase and find a job,
because you are running out of money. You would like readers to pledge money that is only charged if a total
threshold (say $10,000) is met. If it is met, you would keep working on sase for a set period (say one month per
$10,000) before resuming the job search. How should this be implemented? Is it a good idea? What would I change?

---

## Bottom Line

1. **Your mechanism is the right one.** "Charge nobody unless the total clears a threshold" is an *assurance
   contract*. It is the Street Performer Protocol from 1998 and the mechanism behind Kickstarter. It fits your
   situation unusually well. Below the threshold, the money would not change what you do: you need a job either
   way. So an all-or-nothing threshold is not a gimmick; it describes your situation honestly.

2. **The weak point is the unit of the promise, not the mechanism.** "One month of my time per $10k, then I resume
   the job search" has three problems:
   - **It sells inputs (time), not outputs.** Backers want to know what a funded month delivers.
   - **It pauses your job search,** and in practice that costs more than one month.
   - **$10k is not a month of income.** After fees, failed payments, and self-employment tax, $10k pledged becomes
     roughly **$5,300–7,900** you can spend.

   I would keep the threshold and change the promise (§3).

3. **The real risk is audience size, not mechanics.** sase is alpha, and the launch post is its first real exposure.
   A $10k all-or-nothing campaign is plausible if the post reaches the Hacker News front page *and* you have lined
   up anchor pledges beforehand. It is unlikely if you have neither. Kickstarter's own data says the deciding
   variable is reaching about 20% of goal early. **Line up $2–3k of commitments before the post goes live.**

4. **Recommended implementation:** a **self-hosted all-or-nothing pledge page on sase.sh**, built on **Stripe
   Checkout in setup mode**. Backers save a card now and are charged off-session only if the threshold is met at
   the deadline. Stripe's own docs name this exact use case. sase.sh is already a Cloudflare Worker, so this is a
   small Worker + D1 addition.
   - **Fallback:** if Stripe's due-diligence review says no, or you don't want to own payment code, use
     **Kickstarter**. Frame the project as "sase 1.0", not as funding your living costs.
   - **Second channel:** add **GitHub Sponsors** (0% fees) as a separate, clearly labeled channel for unconditional
     support.

5. **Requirement changes I'm making (details in §3):**
   - Fund **weeks, not months**: 4 weeks at $10k, then +1 week per additional $2,500, with a cap.
   - Attach **deliverables** to each funded block.
   - Set a **21-day deadline**.
   - **Don't pause the job search** during the campaign.
   - Add an **escape hatch** in case you accept a job mid-sprint.
   - Say **"pledge / back," not "donate"**, and state plainly that pledges are not tax-deductible.
   - Make the post **"fund me *or* hire me."**

---

## 1. What You're Describing, and Why It Works

| Concept | What it is | Relevance |
| --- | --- | --- |
| **Assurance contract** | Contributors commit to pay only if total commitments reach a threshold, so nobody pays for a public good that doesn't happen. | It removes the donor's fear that "my $50 won't change anything." Everyone either succeeds together or pays nothing. |
| **Street Performer Protocol** (Kelsey & Schneier, 1998) | Donations go into escrow and are released to an author only when the promised work is made public. If the threshold is missed, nothing is released. | This is your exact idea from 28 years ago: open work paid for by a crowd, conditional on a threshold. |
| **Kickstarter all-or-nothing** | Cards are charged only at the deadline, and only if the goal is met. | It is the mainstream, battle-tested version. Kickstarter's flow is a good template even if you don't use Kickstarter. |
| **Dominant assurance contract** (Tabarrok, 1998) | If the goal *fails*, the organizer pays pledgers a small *refund bonus*, so pledging is a no-lose bet. In lab experiments, refund bonuses raised campaign success by 50% or more, and limiting the bonus to *early* pledgers worked about as well (Cason, Tabarrok & Zubrickas, *Games and Economic Behavior*, 2021). | It is elegant, but it costs money exactly when you have none (in the failure case). **Not recommended for you.** It's noted here because a reviewer will ask. |

Why the threshold is especially honest in your case: below $10k, the money is a tip. It would extend your runway a
little but would not buy any sase time, because you still have to find a job. Saying "I'll only take your money if
it actually changes the outcome" builds trust, and the format makes that promise mechanically true.

---

## 2. Critique: Is This a Good Idea?

**Short verdict: yes, with modifications.** The mechanism is sound, and being candid about running out of money
will win more sympathy than it costs. What needs work is the promise, the price, the audience plan, and how it
interacts with your job search.

### 2.1 What's Right About the Plan

- **Candor is an asset on HN.** Readers already know that solo-maintained alpha tools are fragile. Naming the
  funding cliff turns a hidden risk into a choice they can act on.
- **It has a deadline and a binary outcome.** Assurance contracts work because of urgency and visible progress. A
  vague "consider sponsoring me" link converts far worse.
- **It is aligned with what readers want.** The money buys more sase, not your personal runway in the abstract.
- **Both outcomes are fine for you.** If it funds, you get paid time on your own project. If it doesn't, nobody is
  charged, and you have a public launch, an audience, and a portfolio piece for the job search.

### 2.2 Problems and Risks

**(1) Cold start: the threshold has to be met by people who discovered sase that week.**
Every open-source crowdfunding success I found had an established community *before* the ask:

| Campaign | Goal | Raised | Backers | Context |
| --- | --- | --- | --- | --- |
| Neovim (Bountysource, 2014) | $10,000 | ~$34,000 | n/a | Riding Vim's enormous user base |
| Django schema migrations (Kickstarter, 2013) | £2,500 | £17,952 | 507 (avg ~£35) | Endorsed by the Django core team and the DSF |
| Django REST framework 3 (Kickstarter, 2014) | £4,000 | £32,650 | 440 | DRF was already widely used |

All three set a **low goal relative to their audience** and overfunded. sase is alpha. It supports POSIX only and
assumes you already run agent CLIs, so the pool of people who have *used* it is small, and most pledges would come
from people who just read about it.

Base rates are sobering. Kickstarter's published stats (an undated snapshot) put the overall success rate at about
41% and **Technology at about 23%**. Mollick's model gives an average $10k, 30-day project about a **35%** chance of
success.

Momentum is the strongest lever. Kickstarter data shows that projects passing **20% of goal have about an 80%
chance** of funding. Mollick & Pi found that projects with goals of $10k or less need only about **15%** of goal to
reach that 80% chance.

Illustrative funnel. **The conversion rates are my assumptions, not measured data:**

| Scenario | Visitors (HN anecdotes: ~11k–16k uniques, ~32k pageviews for #1 for six hours) | Pledge rate (assumed) | Avg pledge (assumed) | Raised from traffic |
| --- | --- | --- | --- | --- |
| Not on HN front page | 500–2,000 | 0.5% | $50 | **$125–500** |
| Front page, modest | 10,000 | 0.3% | $50 | **$1,500** |
| Front page, good | 20,000 | 0.5% | $60 | **$6,000** |
| Front page, great | 30,000 | 1.0% | $70 | **$21,000** |

**Implication:** traffic alone reaches $10k only in the good-to-great cases. **Anchor pledges** from your network,
former colleagues, and one or two companies are what turn this from a coin flip into a likely success. Get them
*before* launch, so the counter starts at 20–30%.

**(2) "One month of time" is the wrong product to sell.**
Backers can't evaluate a month, but they can evaluate "macOS install that just works", "stable plugin API", or "a
1.0 release with migration guarantees". Software campaigns that worked sold a specific deliverable and used time
only as the cost basis: Django migrations funded "migrations in core", and DRF 3 funded "the serializer rewrite and
3.0". Time is still how you *price* it. Deliverables are what you *sell*.

**(3) Pausing the job search is the hidden, largest cost.**
The plan as written is: if funded, work on sase for N months, *then* resume the job search. Tech hiring pipelines
take weeks to months. Pausing yours means:
- the funded month is followed by a cold restart, not a warm pipeline;
- a great offer that arrives during a funded period forces you to choose between the offer and your backers.

Three fixes: keep a low-intensity search running throughout, add an explicit escape hatch (§3, A5), and make the
launch post itself do job-search work. See §5.2.

**(4) $10k pledged is not $10k of income.**

| Line item (on $10,000 pledged, ~200 backers × $50) | Kickstarter | Self-hosted Stripe |
| --- | --- | --- |
| Failed or dropped payments (Kickstarter agencies report ~3%; I assume ~4% self-hosted) | −$300 | −$400 |
| Platform fee | −$485 (5% of collected) | $0 |
| Processing | ≈ −$330 (Kickstarter says "roughly 3–5%"; modeled at 3% + $0.20) | ≈ −$380 (2.9% + 30¢, plus 1.5% on an assumed 30% international share) |
| **Gross received** | **≈ $8,885** | **≈ $9,220** |
| US self-employment tax (~14.1% of net earnings) | ≈ −$1,250 | ≈ −$1,300 |
| Federal/state income tax (depends entirely on your 2026 total income and state) | −$0 to −$2,400 | −$0 to −$2,500 |
| **Spendable, roughly** | **≈ $5,300–7,600** | **≈ $5,400–7,900** |

So "one month per $10k" means living on about $5.5–7.5k for that month, possibly minus self-paid health insurance.
That works if your monthly burn is at or below that. If it isn't, each funded month quietly shrinks your savings,
which defeats the purpose. **Check your real burn rate before fixing the price** (see A8).

**(5) The "I have to stop" message can depress adoption.**
"This tool's only maintainer is about to leave" is a reason *not* to adopt a tool. You can't avoid saying it, and
you shouldn't, but frame it so it reads as a fork in the road rather than a eulogy:
- sase stays MIT-licensed and usable;
- what funding changes is the *pace and polish*;
- state concretely what "stop" means: archived, maintenance-only, or evenings-only.

**(6) Platform rule traps.**
- **Kickstarter:**
  - *Purpose.* Kickstarter's current help center says projects must "create something new" to share with others,
    and that "a monetary reward of any kind" is prohibited. Its 2014 rules (still repeated by current guides) also
    exclude raising money for causes and "fund my life" projects like tuition or bills. A pitch that leads with
    "I'm running out of money" reads like the latter. It must be pitched as *sase 1.0*.
  - *AI disclosure.* Kickstarter has required AI disclosure since 2023. sase is AI-adjacent, and a large share of its
    commits are agent-authored, so you would have to explain that.
  - *Audience.* Kickstarter's creative community is not AI-friendly. This matters less because your traffic would
    come from your own post, not Kickstarter discovery.
- **Stripe:** Stripe's current Restricted Businesses list (updated 2026-09-22) puts "Crowdfunding platforms" and
  "fundraising conducted by … businesses offering a reward in return for donation" under a *restricted* "Crowdfunding
  and fundraising" heading, which means "additional due diligence." It is not prohibited. One creator pre-selling
  their own work is not a platform, but **get written confirmation from Stripe support before launch.** A sudden
  burst of off-session charges on a new account is exactly the pattern that triggers reviews and payout holds.

**(7) This is income, and an obligation, not a gift.**
- *Tax.* Once you promise work in return, pledges are almost certainly taxable business income, not gifts. The IRS
  has warned that crowdfunding receipts are not automatically gifts, and reward-style campaigns are treated like
  advance sales.
  - *1099-K.* Form 1099-K thresholds have shifted repeatedly; current sources say the One Big Beautiful Bill Act
    restored $20,000 / 200 transactions. Whether or not you get a 1099-K, the income is reportable.
  - *What to do.* Keep records and get a one-hour CPA consult. Not tax advice.
- *Obligation.* Like a Kickstarter creator, you would be on the hook to deliver or refund, so publish the refund
  rule up front (A5).

**(8) An uncapped "1 month per $10k" is an open-ended promise.**
If the post goes viral and $90k comes in, you have committed nine months. Decide on a cap now, while it's
hypothetical.

**(9) A public failure is visible, but survivable.**
A campaign that stalls at $4k is a small public "no". It's survivable if the terms say up front: "If this doesn't
fund, nobody is charged and I'll happily go back to work. Thank you either way." Don't let the counter or the copy
read as desperate. Prospective employers will read it.

---

## 3. Requirement Adjustments (Clearly Called Out)

| # | Your requirement | **Adjusted to** | Why |
| --- | --- | --- | --- |
| **A1** | 1 month per $10k | **Threshold $10k = 4 funded weeks; each further $2,500 = +1 week.** The counter shows "weeks funded," not just dollars. | Smaller increments make every pledge visibly move the outcome, and overfunding converts cleanly with no fractional months. |
| **A2** | Work on sase for the period | **Each funded block buys published deliverables** (e.g., weeks 1–4: install/onboarding + 1.0 API freeze; weeks 5–8: macOS polish + docs; …), with time as the cost basis and a weekly public log. | Backers fund outcomes. A public log turns accountability into marketing. |
| **A3** | (unspecified) | **21-day deadline,** announced in the post. Hard stop; no extensions. | Assurance contracts need urgency. Mollick: 30-day campaigns beat 60-day ones (35% vs 29% for a $10k project), and Kickstarter recommends 30 days or less. 21 days also fits your runway and three weekends of follow-up posts. |
| **A4** | Implicitly uncapped | **Cap at 24 funded weeks ($60k).** Above the cap, pledging closes, or extra money is explicitly used for infra/CI costs. | It prevents an accidental half-year commitment you might regret. |
| **A5** | Resume the job search after the funded period | **Keep the job search running at low intensity throughout.** **Escape hatch:** if you accept a job before the funded weeks are delivered, you either (a) deliver the remaining funded weeks as evenings/weekends within 6 months, or (b) refund the unworked share pro-rata. Each backer chooses. | It protects you from the "great offer arrives in week 2" dilemma and makes the promise robust. |
| **A6** | "Donate" | **"Pledge," "back," or "sponsor."** State plainly: *not tax-deductible; this is payment for open-source development.* | The money isn't a charitable donation. "Donate" invites confusion (and tax-deductibility questions). |
| **A7** | One channel | **Two channels, clearly separated:** (a) the threshold pledge (conditional) and (b) GitHub Sponsors (unconditional, 0% fees). Only *conditional* commitments count toward the threshold. That includes company commitments to pay on success by invoice. | Some people want to help regardless. Mixing unconditional money into the threshold muddies the promise. |
| **A8** | $10k/month price | **Keep $10k only if your monthly burn is ≤ ~$6k.** Otherwise use $12.5k per 4 weeks ($3,125/week). | Fees, failed payments, and taxes take about 20–45% (§2.2(4)). |
| **A9** | Ask in the launch post | **Also secure $2–3k of anchor commitments privately before the post goes live,** so the counter starts at 20–30%. | This is the single strongest predictor of success in the crowdfunding data. |
| **A10** | Stop developing sase | **Say exactly what "stop" means** (e.g., "maintenance-only: security fixes and releases, no new features"). | Users and adopters need to know what they're adopting. |

---

## 4. Implementation Options

### 4.1 Comparison

| Option | Enforces all-or-nothing? | Backer friction | Cost on $10k | Time to cash after deadline | Your build effort | Rule/compliance risk | Counts company commitments? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Self-hosted Stripe (Checkout setup mode → off-session charge)** | Yes, by your code | Lowest: card on Stripe-hosted page, no account | ~3.5–4% + failures | Charges at deadline; payouts then follow the account's payout schedule (new accounts may see a delayed first payout) | ~1 day with agents + review + test-mode rehearsal | Medium: Stripe "restricted" category; get pre-clearance | **Yes** (you aggregate) |
| **Kickstarter** | Yes, natively | Medium: backers need a Kickstarter account | ~5% + ~3–5% | 14-day collection window + 3–14 business days | Hours (page + video) | Medium: "create something new" / "fund my life" framing, AI disclosure, project review | No (on-platform pledges only) |
| **Indiegogo** | Yes: all campaigns became Fixed Funding on 2025-10-16 under Gamefound | Medium (account) | 5% + processing (moved to Adyen) | Platform-dependent | Hours | Medium; a rocky 2025 migration | No |
| **Honor pledges (form) → invoices on success** | No: social commitment only | Lowest | ~3% on what's collected | Days to weeks of chasing | Minutes | Low | Yes |
| **Manifund** (501(c)(3), "minimum funding" + deadline) | Yes, natively | **High:** donors pre-fund a Manifund balance | ~5% | Varies | Hours (application) | Fit: EA/AI-safety-leaning portfolio, though it accepts "any public-benefit project" | Partly |
| **GitHub Sponsors / Open Collective / Liberapay / Polar** | **No:** all charge immediately; "goals" are display-only | Low | GitHub Sponsors 0% (personal accounts; up to 6% from orgs); Open Source Collective 10%; Liberapay 0% + ~3–5% processing; Polar ~4–5% + fixed fee | Monthly payouts (GitHub Sponsors pays within ~30 days of month close; first payout ~60 days) | Minutes | Low | n/a |

Notes on the rejected rows:
- **Honor pledges.** Online non-binding pledges convert poorly. One Johns Hopkins study of online charity pledges
  found 64% fulfilled in full, 13% partially, and 16% deleted. You would need roughly $14–15k pledged to collect
  $10k, and you couldn't know in advance.
- **Manifund** is attractive to the occasional large US donor who wants a tax deduction (it also has threshold
  semantics). Pre-funding friction makes it a poor primary channel for HN readers.
- **Open Source Collective** is a 501(c)(6), so contributions there are *not* tax-deductible either.
- **Small or unvetted platforms** are a risk. Bountysource became insolvent and stopped paying out in 2023. Stick to
  processors with real balance sheets.
- **Why not manual-capture holds?** Card authorizations for online payments are normally valid for **7 days**.
  Stripe's 30-day "extended authorizations" are limited to IC+ pricing (or contacting support), apply only to
  customer-initiated transactions, and are meant for cases where "you don't know the final amount". None of that
  fits a 21-day campaign. **SetupIntents are the right primitive.**

### 4.2 Self-Hosted Stripe: How It Would Work

Stripe's Setup Intents docs list this exact case: *"A crowdfunding website that collects card details to be charged
later, only if the campaign reaches a certain amount."* Checkout supports `mode=setup`, which saves a card without
charging it.

**Architecture.** sase.sh is already a Cloudflare Worker serving static assets (`wrangler.jsonc`), so add a `main`
Worker script and a D1 table.

1. **`/fund` page** (MkDocs page): amount picker (presets plus custom amount), optional public display name, and a
   progress bar plus "weeks funded" counter that reads `/api/pledges/summary`.
2. **`POST /api/pledge`**: the Worker creates a Stripe Customer, then a Checkout Session with `mode=setup`,
   `currency=usd`, and metadata (`pledge_cents`, `display_name`, `public`). Put the **mandate text** in Checkout's
   custom text. For example:
   > *"You authorize Bryan Bugyi (sase) to charge this card **$X once**, between Nov 6 and Nov 13, 2026, **only if**
   > total pledges reach $10,000 by Nov 5, 2026 11:59 pm ET. If the goal isn't met, your card is never charged and
   > your saved card is deleted. You can cancel any time before the deadline from the link in your confirmation
   > email."*

   Stripe requires customer permission for future off-session charges, and this text is that permission.
3. **Webhook `checkout.session.completed`**: insert a pledge row (customer, payment method, amount, email,
   `status=pledged`) and recompute the cached total. Email a confirmation with a **signed cancel link**. Backers on
   Kickstarter can cancel before the deadline, so match that.
4. **At the deadline (cron Worker or a script you run by hand):**
   - **Goal met:** email everyone "Funded! Your card will be charged $X on <date>." Then, for each pledge, create a
     PaymentIntent with `off_session=true, confirm=true` and an **idempotency key per pledge**.
     - **Failures:** Stripe returns HTTP 402. On `authentication_required` (common for EU/UK cards under SCA) or a
       decline, email a recovery link: a new Checkout session for the exact amount.
     - **Grace period:** mirror Kickstarter with 7 days and reminders every 48 hours, then drop the pledge.
   - **Goal missed:** email "Not funded; nothing charged; your card has been deleted." Then detach payment methods
     and delete the customers.
5. **Publish a final ledger:** pledged, collected, fees, failed, and the weeks funded and their start date.

**Rehearse in test mode.** Use Stripe's SCA test card `4000 0027 6000 3184`, which requires authentication at setup
*and* on later charges, so you exercise the recovery path. Also test a decline card, a cancellation, a missed-goal
run, and a re-run of the charge job (idempotency).

**Pros:**
- No backer account needed. This matters most for a one-day HN traffic spike.
- Lowest fees.
- On-brand: the pledge page sits next to the post.
- Can aggregate conditional company commitments.
- You control the copy, the deadline, and the data.
- Building it is a small showcase in itself.

**Cons:**
- You own payment-critical code: double charges, wrong amounts, and email deliverability all become your problem.
- Stripe due-diligence risk on a new account.
- Weeks-later charges can prompt "I don't recognize this" disputes (about $15 each). The pre-charge notice email and
  a clear statement descriptor (`SASE.SH PLEDGE`) mitigate this.
- Less inherent trust than a Kickstarter page.

### 4.3 Kickstarter: How It Would Work (the Fallback)

- **Eligibility:** US-based individuals 18+ with a US government ID and a US bank account in their own name.
- **Duration:** 1–60 days; Kickstarter recommends 30 or less.
- **Fees:** 5% plus Stripe processing of "roughly 3–5%," charged only if funded.
- **Charging:** backers are charged at the deadline. Errored pledges get **7 days** and reminders every 48 hours,
  then are dropped. Agencies report about 3% errored.
- **Payout:** collection runs for 14 days after the deadline; the payout then takes another 3–14 business days.
- **Framing:** title it as a *creation* ("sase 1.0: …") with deliverables per funding level. Keep "I'm running out of
  money" in your blog post, not as the project's purpose.
- **Rewards:** symbolic (credits, backer page, roadmap vote, company logo). No monetary rewards; Kickstarter forbids
  them.
- **AI disclosure:** answer the questions honestly.
- **Review risk:** low but non-zero. Submit for review a week before launch.

**Choose Kickstarter over self-hosted if** Stripe won't pre-clear you, or you'd rather spend the build day on the
post. The ~$335 per $10k fee difference is not decisive either way.

---

## 5. Different Approaches I'd Add (Not Replace)

### 5.1 Chase a few big checks before many small ones

Raising $10k from 200 strangers is harder than raising $3–5k from 2–3 companies that use or care about agentic
tooling, plus $2k from people who know you. Organizations are a large share of open-source funding: GitHub reported
that organizations provided nearly 40% of Sponsors funding in 2022. Caleb Porzio's path to $1M+ on GitHub Sponsors
leaned heavily on companies. Offer a **"founding sponsor"** level (e.g., $2,500+ with a logo on the README and site).
Companies commit conditionally, by email or LOI, and are invoiced only on success. Only the self-hosted option lets
those commitments count toward the threshold.

### 5.2 Make the post say "fund me *or* hire me"

You are job-searching anyway, and a launch post that reaches HN is the best résumé you will ever publish. One honest
closing line does it: *"If this doesn't fund, I'm looking for a role in X. If your team builds Y, I'd love to talk."*
That turns the failure branch into an opportunity, removes any desperation in the tone, and lets the post do work in
both outcomes.

### 5.3 Use your drafted series to fight the mid-campaign slump

Crowdfunding pledges cluster at the start and the end. You already have draft posts [03]–[06] in `docs/blog/posts/`
(scheduler/AXE, Beads and SDD, commit workflows, Patches). Publish one every 4–5 days during the 21-day window, each
ending with the live counter, to give readers new reasons to return. Email everyone who signs up for the "remind me"
list 48 hours before the deadline. This is the main thing Kickstarter does that you'd otherwise be missing.

### 5.4 Cheap long-shot grants, in parallel

- **FLOSS/fund** (Zerodha) grants about $10k–$100k per project from a ~$1M/yr pool. You apply by publishing a
  `funding.json` manifest; disbursement takes about 4–16 weeks. An alpha project is a long shot, and it's too slow
  for your runway, but it costs about an hour.
- The **Open Source Pledge** ($2,000 per developer per year from member companies) is a list of companies that have
  publicly committed to paying maintainers, so it's a ready prospect list for §5.1.

### 5.5 Later, not now

- **Recurring sponsorship:** after a successful sprint, convert backers into monthly GitHub Sponsors to extend it.
  Porzio took months to reach about $112k/yr.
- **Sponsorware:** mkdocs-material's "Insiders" model releases features publicly when monthly funding goals are hit.
  It is a sustained-funding model for a project with an installed base; sase isn't there yet, and gating features of
  an alpha tool would slow adoption.
- **Refund bonuses:** skip (§1).

---

## 6. Recommended Solution

**Mechanism:** a 21-day, all-or-nothing **"Fund sase 1.0"** pledge campaign, **self-hosted on sase.sh with Stripe
Checkout (setup mode) and off-session charges at the deadline.** Use **Kickstarter** as the fallback if Stripe won't
pre-clear it or you'd rather not own payment code. **GitHub Sponsors** runs alongside as the separate unconditional
channel.

**Terms (publish them on `/fund` and link them from the post):**

| Term | Value |
| --- | --- |
| Threshold | **$10,000 = 4 funded full-time weeks** (or $12,500 if your burn exceeds ~$6k/month; see A8) |
| Stretch | **+1 week per additional $2,500**, capped at **24 weeks / $60,000** |
| Deadline | **21 days** after the post goes live; no extensions |
| What weeks buy | A published deliverable list per 4-week block, plus a weekly public log of funded work |
| Start | Funded weeks begin within ~1 week of the charge date |
| Job search | Continues at low intensity. **Escape hatch:** if you take a job early, either finish the remaining weeks on evenings/weekends within 6 months or refund the unworked share pro-rata; each backer chooses |
| If it fails | Nobody is charged, saved cards are deleted, sase stays MIT and enters "maintenance-only" (define it) |
| Wording | "Pledge / back / sponsor"; **not tax-deductible**; payment for open-source development |
| Recognition | Backers page (opt-in name), roadmap vote for $100+, logo for $2,500+ "founding sponsors"; nothing that costs you meaningful time |
| What counts | Stripe pledges + conditional company commitments (invoiced on success). GitHub Sponsors money is separate and doesn't count |

**Timeline:**

1. **T−14 to T−7: pre-clearance.**
   - Email Stripe support describing the campaign and get written OK for the restricted "crowdfunding and
     fundraising" category. If refused, switch to the Kickstarter fallback.
   - Book a one-hour CPA consult on self-employment income, quarterly estimates, and ACA-subsidy effects.
   - Check your burn rate (A8).
2. **T−10 to T−3: build and rehearse.**
   - Build the Worker + D1 pledge flow (§4.2).
   - Rehearse fully in test mode: SCA card, declines, cancel, missed goal, and an idempotent re-charge.
   - Set up GitHub Sponsors. Optionally add `funding.json`.
3. **T−7 to T−1: anchor pledges.** Privately ask former colleagues, friends, early users, and 3–5 target companies.
   Aim for **$2–3k** committed before going public (the 20–30% momentum rule).
4. **T0: launch.**
   - The launch post keeps its accepted title and structure.
   - Add one short closing section (~150–250 words): what sase is, the honest money situation, the three terms that
     matter (threshold, deadline, what it buys), "fund me *or* hire me," and links to `/fund` and GitHub Sponsors.
   - Add a site-wide banner with the live counter. Submit to HN with the original title.
5. **T+4 … T+18: momentum.**
   - Publish one series post every 4–5 days, each ending with the counter.
   - Post weekly updates: total, backers, what the next $2,500 buys.
6. **T+19: final push.** Send the "48 hours left" email to the reminder list and backers.
7. **T+21: deadline.**
   - **Met:** send the pre-charge notice, charge 24 hours later, then run the 7-day failed-payment recovery and
     publish the ledger and start date.
   - **Missed:** send the "nothing charged" email, delete cards, and post a gracious thank-you. You still have the
     audience and the job-search halo.
8. **During funded weeks:** keep the weekly public log and ship the deliverables. At the end, publish a retrospective
   and offer a recurring GitHub Sponsors tier to keep going.

**Why this over the alternatives:**
- It keeps your threshold idea intact, which is the right mechanism.
- It removes the backer-account friction that would cost conversions from a one-day HN spike.
- It lets the few big checks (companies, colleagues) count toward the goal.
- It avoids Kickstarter's "fund my life" and AI-culture friction.
- It costs about 4% instead of about 9%.
- Most of all, the adjusted terms (weeks with deliverables, a cap, an escape hatch, and a job search that never
  fully stops) make the promise one you can keep whatever happens next.

---

## Confidence and Gaps

- **Verified on official pages during this research:**
  - Stripe: restricted-business wording (updated 2026-09-22), the 7-day authorization validity, extended-authorization
    limits, the setup-intent crowdfunding example, recovery from failed off-session charges, Checkout setup mode, and
    pricing.
  - Kickstarter help center (articles updated Aug–Sept 2026): fees, charge timing, the 7-day error grace period,
    payout timing, duration limits, and eligibility.
  - GitHub Sponsors fees and payout terms; Open Source Collective's fee and 501(c)(6) status; Manifund's
    minimum-funding mechanism and 501(c)(3) status; Liberapay; and Polar pricing.
- **Not verified on official pages:**
  - kickstarter.com/rules and /help/stats returned 403 or redirected. The "fund my life" exclusion and the 23%
    Technology success rate come from Kickstarter's 2014 rules coverage and secondary snapshots.
  - Indiegogo's switch to Fixed Funding comes from its help center via search summaries.
- **Assumptions, not data:** the funnel's pledge rates and average pledge sizes (§2.2(1)), the 4% self-hosted failure
  rate, and the tax ranges.
- **Not legal or tax advice.** The income-vs-gift, 1099-K, and ACA points need a professional's eyes for your state
  and 2026 income.

## Sources

- Kelsey & Schneier, *The Street Performer Protocol* (1998): https://www.schneier.com/academic/archives/1998/11/the_street_performer.html
- Assurance contracts / dominant assurance contracts: https://en.wikipedia.org/wiki/Assurance_contract
- Cason, Tabarrok & Zubrickas, early refund bonuses in crowdfunding: https://web.ics.purdue.edu/~cason/early_refund_crowdfunding.pdf
- Kickstarter help, "Can Kickstarter be used to fund anything?": https://help.kickstarter.com/en-us/articles/16236681-can-kickstarter-be-used-to-fund-anything
- Kickstarter help, fees: https://help.kickstarter.com/en-us/articles/16236674-what-are-the-fees
- Kickstarter help, who can use Kickstarter: https://help.kickstarter.com/en-us/articles/16236650-who-can-use-kickstarter
- Kickstarter help, when cards are charged: https://help.kickstarter.com/en-us/articles/16236544-when-is-my-card-charged
- Kickstarter help, pledge errors and dropped pledges: https://help.kickstarter.com/en-us/articles/16236454-what-happens-when-there-is-a-problem-with-one-of-my-backer-s-pledges
- Kickstarter help, receiving funds: https://help.kickstarter.com/en-us/articles/16236545-if-my-project-is-successfully-funded-how-do-i-receive-my-funds
- Kickstarter help, maximum duration: https://help.kickstarter.com/en-us/articles/16236742-what-is-the-maximum-project-duration
- Kickstarter 2014 rules simplification ("fund my life", charity): https://www.nbcnews.com/news/amp/wbna55323230 and https://www.launchboom.com/blog/resources/what-is-allowed-on-kickstarter/
- Kickstarter AI disclosure policy (2023): https://www.engadget.com/kickstarter-projects-will-soon-have-to-disclose-any-ai-use-145100394.html
- Kickstarter category success snapshot: https://www.kickstarter.com/help/stats (now redirects); secondary: https://www.soundandvision.com/content/kickstarter-flops-4-out-5-tech-campaigns-fail
- Success odds, the 20% rule, and Mollick/Pi goal-size analysis: https://cmf-fmc.ca/now-next/articles/how-likely-is-your-crowdfunding-campaign-to-succeed/
- Campaign length (30 vs 60 days): https://stephenfollows.com/the-statistics-on-improving-your-crowd-funding-campaign/
- Errored/dropped pledge rates: https://launchboom.com/blog/failed-credit-cards-on-kickstarter-and-how-to-fix-them-a70b592d79ca and https://www.pledgebox.com/post/dropped-backers-how-to-recover-them-to-avoid-funding-loss
- Indiegogo platform upgrade / fixed funding: https://help.indiegogo.com/article/645-what-changed-with-the-platform-upgrade and https://support.indiegogo.com/hc/en-us/articles/39600950083988
- Stripe Prohibited & Restricted Businesses: https://stripe.com/legal/restricted-businesses
- Stripe Setup Intents: https://docs.stripe.com/payments/setup-intents
- Stripe save and reuse / off-session recovery: https://docs.stripe.com/payments/save-and-reuse
- Stripe Checkout setup mode: https://docs.stripe.com/payments/checkout/save-and-reuse
- Stripe holds and extended authorization: https://docs.stripe.com/payments/place-a-hold-on-a-payment-method and https://docs.stripe.com/payments/extended-authorization
- Stripe pricing: https://stripe.com/pricing
- GitHub Sponsors fees and taxes: https://docs.github.com/en/sponsors/sponsoring-open-source-contributors/about-sponsorships-fees-and-taxes
- GitHub Sponsors goals: https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/managing-your-sponsorship-goal
- GitHub Sponsors additional terms (payout timing): https://docs.github.com/en/site-policy/github-terms/github-sponsors-additional-terms
- Open Source Collective fees and tax status: https://docs.oscollective.org/welcome-and-introduction-to-osc/fees.md and https://docs.oscollective.org/about-osc/official-info-and-docs.md
- Manifund open call and donor FAQ: https://manifund.org/about/open-call and https://manifund.org/about/donate
- Liberapay FAQ: https://liberapay.com/about/faq
- Polar pricing: https://polar.sh/resources/pricing
- Neovim fundraiser: https://neovim.io/news/2014/06/ and https://news.slashdot.org/story/14/03/22/147222
- Django schema migrations Kickstarter: https://www.djangoproject.com/weblog/2013/mar/22/kickstarting-schema-migrations-django/ and https://www.kicktraq.com/projects/andrewgodwin/schema-migrations-for-django/
- Django REST framework 3 Kickstarter: https://sdtimes.com/django-rest-framework-kickstarts-new-release/
- Caleb Porzio on GitHub Sponsors: https://calebporzio.com/i-just-hit-dollar-100000yr-on-github-sponsors-heres-how-i-did-it and https://calebporzio.com/i-just-cracked-1-million-on-github-sponsors-heres-my-playbook
- GitHub Sponsors passes $100M (org share): https://itbrief.co.uk/story/github-sponsors-tops-usd-100-million-for-open-source
- mkdocs-material Insiders funding goals (mirror): https://git.struchkov.dev/OpenSourceArk/mkdocs-material/src/tag/9.0.8/docs/insiders/index.md
- Online pledge fulfillment (Johns Hopkins study, secondary): https://baltimorefishbowl.com/stories/jhu-prof-online-fundraising-fails/
- Bountysource insolvency: https://community.mautic.org/assemblies/product-team/f/39/debates/2/versions/1
- FLOSS/fund: https://zerodha.com/open-source/2025-report/ and https://www.opensourceforu.com/2025/10/zerodha-announces-final-675000-tranche-for-global-open-source-projects-advocates-sovereign-foss-fund/
- Open Source Pledge: https://lwn.net/Articles/993073 and https://technical.ly/software-development/open-source-pledge-developer-pay/
- Crowdfunding taxation (US): https://www.irs.gov/node/138126 and https://beancount.io/blog/2026/05/14/crowdfunding-tax-treatment-kickstarter-gofundme-indiegogo-form-1099-k-taxable-income-gifts-irs-recordkeeping-guide
- Hacker News traffic anecdotes: https://www.indiehackers.com/post/first-place-on-hackernews-stats-traffic-and-regs-46b8b95333 and https://kevin.burke.dev/?p=2834 and https://www.vincentschmalbach.com/analyzing-a-year-of-hacker-news-traffic/
- Open-source donation studies (Overney et al., ICSE 2020): https://neverworkintheory.org/2021/10/13/an-empirical-study-of-donations-in-open-source.html
