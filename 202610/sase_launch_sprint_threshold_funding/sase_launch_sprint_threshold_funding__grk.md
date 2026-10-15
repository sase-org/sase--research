---
create_time: 2026-10-15
updated_time: 2026-10-15
status: draft
tags:
  [
    research_swarm,
    funding,
    crowdfunding,
    threshold-pledge,
    assurance-contract,
    github-sponsors,
    polar,
    kickstarter,
    launch-post,
  ]
---

# Threshold pledges for a sase runway: how, and whether

**Question.** For the first sase blog post, how should a threshold-pledge
campaign work: readers pledge money that is charged only if a total (say
$10,000) is reached, and if it is reached the author keeps working on sase for
a period (say 1 month per $10,000) before continuing a job search. What is the
best way to implement that? Is the plan a good idea? What should change?

**Researcher.** grk (`research.1l.grk`). Independent report. I did not read
peer reports from this swarm. I did read prior launch-post research
(`research:202610/sase_launch_post_outline/sase_launch_post_outline.md` and
the introduction consolidation) as shared background on the post this ask
would sit inside.

**Scope.** Implementation options, economics of the ask, fit with the already-
decided launch-post outline, US tax treatment at a high level, and a
recommended design. This is not legal, tax, or employment advice.

## Bottom line

The assurance-contract idea is sound. The packaging in the prompt is not.

A threshold ("charge me only if enough other people also pay") is the right
game-theoretic shape for a public-good funding problem. Kickstarter exists
because that shape works. The specific deal — *$10,000 one-shot buys one
month of work, then the job search resumes, announced inside the first product
post* — sells a delay, not a future. It will under-convert, it collides with
the launch-post outline already on disk, and it asks the wrong economic
object (a lump of salary) for the thing readers actually need (ongoing
maintenance of an open tool).

**Recommended design, in one paragraph.** Keep the first blog post a product
post. Put a short, honest closing that you need paid work, and link out to a
`/fund` page. On that page run **two meters**: (1) a 30-day **one-time**
threshold campaign for a **named 6-week milestone** (public 1.0, docs, plugin
stability, weekly updates), implemented as a public pledge ledger that
converts to GitHub Sponsors one-time payments (individuals) and Polar
checkouts (companies) only if the goal is met; (2) a **recurring** GitHub
Sponsors thermometer whose crossing is the only event that pauses the job
search. Start the job search **now**, in parallel. Do not build a Stripe
SetupIntent app. Do not put this campaign on Kickstarter unless you can
honestly frame a creative 1.0 launch with rewards and survive review.

That is the plan I would ship. The rest of this report is why.

## Verdict on the plan as written

The plan has one real strength: **honesty**. Telling readers you are running
out of money, and that unpaid full-time work is ending, is better than a
vague "support the project" button. OSS.Fund's 2026 crowdfunding guide is
explicit that campaigns fail when they ask for money without naming the work,
and succeed when they name a deliverable, a budget, a deadline, and what
happens on either side of the goal. A threshold is also the classic answer to
the free-rider problem for a public good: Bagnoli and Lipman (1989) called it
a provision-point / assurance contract; Kickstarter industrialised it;
Kelsey and Schneier (1998) described the software-flavoured "Street Performer
Protocol." Blender's 2002 €100,000 buyout is the canonical FLOSS success of
that shape.

The plan as specified has four structural problems.

**1. It buys a month, then restores the original problem.** One month of
runway against a job-search lag of one to six months is a gap, not a bridge.
Readers who pay $10,000 to "keep sase alive" and then watch you job-search
anyway will correctly feel they purchased a delay. The only deal that
actually substitutes for a job is **recurring** money at living-cost scale.
A one-time threshold campaign is still worth running, but only as payment for
a **finite, named piece of work** that retains value after you take a job.

**2. $10,000 for one month is a $120,000/year run-rate, before tax and
fees, for a tool with no public sponsor base.** GitHub Sponsors crossed
$100 million all-time in July 2026, but LabHub's 2026 maintainer survey
still puts a typical mid-size solo library at $100–$500/month and a well-
known framework author at $1k–$5k/month. Full-time OSS salaries at
$10k–$30k/month exist (Evan You, a handful of others) and they sit on years
of audience. Ladybird's full-time team was not a Kickstarter: it was GitHub
Sponsors plus Shopify plus a $1 million gift from Chris Wanstrath into a
501(c)(3). You do not have that stack. A cold Show HN converting at a
generous 0.5% of 20,000 readers, at a $50 average gift, is $5,000. $10,000
is possible with a lead matching pledge and a very good post. It is not the
conservative goal.

**3. "Then I continue my job search" is in the wrong place in the
sentence.** Put the job search in the present tense. A campaign that
succeeds should **add a time-boxed block of dedicated work**; it should not
be sold as the thing that postpones looking for a job. Job-search lead time
is longer than the campaign. Starting the search on day one is the only
plan that does not gamble rent on a thermometer.

**4. The first sase blog post is already specified as something else.**
The 2026-10-07 outline consolidation is an in-place rewrite of the live
July post, ~2,800 words, hard cap 3,000, five H2s plus an unheaded opening.
Section 5.2 is already *"I Need Your Help. I'm Out of Tokens"* plus
`type:poll` GitHub issues. That ask is **compute**. This new ask is
**runway**. Folding a Kickstarter-shaped salary campaign into that closing
blows the cap, changes the genre from explanation to fundraiser, and
collides two different shortages. Hacker News guidelines also want the
original title and punish editorialised "please fund me" packaging on a
Show HN.

Those four are enough to rewrite the requirements. The mechanism can stay.

## Adjustments I am making, called out

Each of these is a change to the prompt's requirements. I use them in the
recommendation.

| # | Original | Adjustment | Why |
| --- | --- | --- | --- |
| A1 | Announce the campaign as part of the first blog post | Keep the post a product post. One honest paragraph in §5, then a link to `/fund`. | Outline already caps the post at ~3,000 words and already has a different ask in §5.2. A fundraiser in the same URL competes with the idea you are launching. |
| A2 | $10,000 one-shot = 1 month of work, then job search | Split into **two meters**: a one-time milestone campaign, and a recurring thermometer. Only the recurring meter pauses the search. | A lump sum cannot substitute for a job. Snowdrift's critique of threshold campaigns is exactly this: ongoing public goods need ongoing money. |
| A3 | Unit of sale is "a month of my life" | Unit of sale is a **named milestone** (6 weeks: public 1.0, docs, plugin API freeze, weekly written updates, a closeout budget). | OSS.Fund: crowdfunding works for a release, migration, audit, or sprint. It is weak for vague ongoing maintenance. |
| A4 | $10,000 is both the goal and the month of salary | Gross the goal up, and consider a lower first rung. A Kickstarter-style $10,000 nets ~$9,100 before income and self-employment tax. GitHub Sponsors personal is 0% platform fee, so the same $10,000 is the whole gross. Either way, $10,000 spendable is closer to $12,000–$14,000 raised on a fee-taking platform, and a first campaign of **$6,000 one-time** plus a **$6,000/month recurring** thermometer is more likely to complete. | Fees, tax, and conversion math below. |
| A5 | Job search waits on the campaign | Job search starts now. Campaign success is optionality. | Search lag is longer than 30 days plus one month of work. |
| A6 | "Out of tokens" and "out of runway" are the same ask | Keep them as two sentences. Tokens are API spend (GitHub Sponsors / Polar, immediately). Runway is living cost (the threshold campaign). | The outline already reserved §5.2 for tokens. Mixing them makes both unintelligible. |
| A7 | Readers are charged automatically at threshold | Use a **public pledge ledger** that converts to real charges only after the goal, on rails that already exist (GitHub Sponsors, Polar). Accept ~10–25% conversion loss and **overshoot the public goal** to cover it. | Card-hold windows are 7 days; a 30-day campaign cannot sit on authorizations. Building SetupIntents is the wrong use of remaining runway. Honor-system drop-off is cheaper than engineering. |
| A8 | No lead donor | Try to land **one matching pledge of $2,000–$5,000** before the public campaign opens. | Matching and seed funding are the highest-leverage conversion tools in this literature. Hatchfund and Goteo treat matchfunding as a first-class tactic. |
| A9 | Platform left unspecified | Default rails: **GitHub Sponsors** (individuals, 0% on personal sponsorships) and **Polar** (companies, invoices, VAT as merchant of record). Kickstarter only if you want a creative 1.0-with-rewards campaign and can wait out review. | Mechanism vs audience, fees, and eligibility below. |
| A10 | Silence on paid work other than donations | Offer **paid setup / consulting** ("a week putting sase into your team's workflow") as a third, job-compatible line. | A single $6k–$12k consulting week beats a hundred $50 gifts and is the same work you would do at a job. |

## Economics: why a threshold, and why this threshold is hard

sase is already public. New work you do under a campaign is a public good:
non-payers cannot be excluded. The rational individual move is to wait.
An **assurance contract** changes the move: "I pay iff enough others pay
that the good is actually produced." That is the prompt's mechanism, and
it is the correct one.

It has well-known failure modes, which Snowdrift.coop catalogues and which
match this case:

- **The cliff.** 99% of goal returns every dollar. Kickstarter's own help
  centre treats this as a feature (creators are not obliged to deliver
  underfunded; backers are not charged for a non-viable project). For a
  salary, a 99% miss is a disaster: you did the marketing and still have
  rent. That is why Kickstarter tells creators to set the **minimum
  viable** goal, not the aspirational one, and why 30 days is the duration
  they see working best (max 60; goal and deadline lock on launch).
- **Arbitrary finish line.** Ongoing maintenance has no natural $10,000
  cliff. A 1.0 freeze does.
- **Weak accountability after payout.** "I will work for a month" is hard
  for backers to audit. "I will ship this list and write weekly notes" is
  auditable.
- **Deadline vs. relationship.** Subscriptions (GitHub Sponsors, Polar,
  Liberapay, Open Collective) keep paying after the news cycle. Threshold
  campaigns extract a burst and then go quiet.

Conversion, order of magnitude, not a forecast:

| Assumption | Conservative | Stretch |
| --- | --- | --- |
| Unique readers of the post + Show HN | 8,000 | 40,000 |
| Pledge conversion | 0.3% | 0.8% |
| Pledgers | 24 | 320 |
| Average pledge | $40 | $80 |
| Gross if everyone pays | ~$1,000 | ~$25,000 |
| After 20% honor-system drop-off | ~$800 | ~$20,000 |

The stretch column needs a great post, an existing audience, and probably a
visible seed. The conservative column does not fund a month of US software
wages. **A lead matching pledge is what moves you from the left column
toward the right.** Ladybird did not Kickstart a salary; Kling got Shopify
and two other sponsors to write large cheques, then hired. That is the
pattern that actually funds full-time work on an ambitious FLOSS tool.

$10,000 as a **month of living costs** also needs a budget table, which
OSS.Fund recommends publishing. A honest version for a US individual:

| Item | Amount |
| --- | --- |
| One month living / "salary" | $8,000 |
| Provider / API spend for that month | $1,500 |
| Platform + processing (if not GitHub Sponsors personal) | $900 |
| Buffer for failed cards / dropped pledges | $1,200 |
| **Campaign goal** | **$11,600** |

Self-employment tax in the US is 15.3% on 92.35% of net earnings from
self-employment, on top of income tax. I am not computing your bracket.
The point for goal-setting: **$10,000 raised is not $10,000 spendable**,
except on GitHub Sponsors from personal accounts, and even then it is
taxable (see below).

## Payment mechanics: you cannot hold cards for 30 days

This is the implementation constraint that kills the naive Stripe build.

Stripe's documented authorization windows for card-not-present payments
are **7 days** for Visa (customer-initiated), Mastercard, Amex, and
Discover, and **5 days** for Visa merchant-initiated. Extended
authorizations can reach 30 days, but only for specific card brands and
**merchant categories** (hotels, vehicle rental, cruises, and similar).
A software-tool donation is not in those categories. Stripe's own
pre-order guidance is: if the time between commitment and capture exceeds
the authorization window, **save the payment method and charge later**.
That is SetupIntents / Checkout in setup mode, with off-session PaymentIntents
at the deadline, plus SCA re-authentication risk on European cards, plus
a 5–10% decline rate at capture (Kickstarter lives with this too).

So the three technically honest ways to implement "don't charge unless
the threshold hits" are:

1. **A platform that already tokenizes cards and captures at campaign
   end** (Kickstarter, Indiegogo since October 2025, BackerKit
   Crowdfunding). This is the product you are describing. Fees ~8–10%
   all-in on success; $0 if you miss.
2. **A small Stripe SetupIntent app you write.** Correct, PCI-safe if you
   use Stripe-hosted Checkout / Elements, and a week-plus of work you
   should not spend while broke. Polar's "off-session charges" exist as
   a **preview on paid Polar plans**, which is a hint that even a
   billing company treats this as non-trivial.
3. **An honor-system ledger**: public pledges, no card on file, convert
   to GitHub Sponsors / Polar / invoices after the goal. PledgeBank
   (2005–2015) ran assurance contracts this way. Drop-off is real;
   engineering cost is a Markdown table and an issue template.

Kickstarter's help centre is unambiguous on the UX you want: pledges are
collected only if the campaign hits its goal by the deadline; if it
misses, no money changes hands; backers can cancel until the campaign
ends; overfunding is allowed and is the usual home of stretch goals.
Creators set goal and deadline (1–60 days; they see 30 work best); both
lock on launch. Fees if funded: 5% Kickstarter plus Stripe processing
"roughly 3–5%." Independent 2026 fee round-ups put the all-in take at
**8–10%**. On $10,000 that is about $850–$1,000, so a $10,000 *need*
implies an ~$11,000 *goal*.

The remaining question is whether Kickstarter will **let this campaign
onto the site**. Kickstarter rules (as of the 2026 rules page) require
projects to "create something new to share," with a demonstrated
prototype for apps and software, original creative thinking, and a fit
in an existing category. Older guideline language still circulating in
secondary sources bars funding "e-commerce, business, and social
networking websites or apps" and "software projects not run by the
developers themselves." A campaign whose product is "one month of my
salary so I can keep existing software alive" is a poor fit for
"create something new." A campaign whose product is "sase 1.0, with a
working TUI demo, a reward ladder (stickers, name in credits, a 30-minute
office-hours call), and a six-week build plan" has a chance. Review
takes days, and an appeal is 500 characters. I would only spend that
latency if you actually want Kickstarter's backer base. You do not:
your readers are HN / GitHub / the people already watching the TUI.
Kickstarter's discovery is games, hardware, and comics.

Indiegogo ended flexible (keep-it-all) funding for new campaigns on
16 October 2025 and is now all-or-nothing like Kickstarter, at a similar
5% + processing. Same mechanism, still the wrong crowd.

## Platform comparison (for this campaign)

GitHub Sponsors **goals** are a thermometer on monthly sponsor count or
monthly dollars. They are **not** escrow. Charges happen immediately.
Open Collective **goals** are the same: a progress bar (linear, log, or
auto) on a balance or yearly budget. Polar in 2026 is a merchant-of-record
billing stack (one-time products, subscriptions, pay-what-you-want, 5% +
50¢ on Starter). Polar's 2023–2024 issue-pledge product is no longer what
the docs sell; the company has moved to "turn your software into a
business," with off-session arbitrary charges as a paid-plan preview.
Liberapay is 0% platform fee, recurring, weekly, no threshold. Ko-fi and
Buy Me a Coffee are tip jars with optional memberships. Patreon is
recurring with a 10% flat rate for pages created after August 2025
(legacy plans closed to new sign-ups, per 2026 round-ups).

None of those, except Kickstarter / Indiegogo / BackerKit, implement true
all-or-nothing capture. For a developer audience, **true capture is less
important than trust and fees.** A public ledger plus GitHub Sponsors is
enough assurance for this crowd.

| Rail | True threshold? | Fees (typical) | Audience fit | Time to live | Notes |
| --- | --- | --- | --- | --- | --- |
| **GitHub Sponsors** | No (thermometer only) | **0%** from personal accounts; up to **6%** from orgs (3% processing + 3% GitHub; invoice billing drops the 3% processing) | Excellent | Days, if already eligible | Charges immediately. Best default for individuals. No FUNDING.yml in the sase tree today. |
| **Polar** | No (products / subs charge at checkout) | **5% + 50¢** Starter; international cards +1.5%; MoR handles VAT | Excellent for companies | Days | Invoices, VAT, pay-what-you-want. Off-session charges are a paid-plan preview, not a campaign product. |
| **Kickstarter** | **Yes** | ~8–10% all-in, $0 if you miss | Poor (creative backers) | Weeks (write + review) | Best mechanism, wrong room, eligibility risk for a salary campaign. |
| **Indiegogo** | **Yes** (mandatory since Oct 2025) | ~8–10% | Poor | Weeks | Same as Kickstarter without the brand. |
| **BackerKit Crowdfunding** | **Yes** | 5% + 2.9% + $0.30 | Poor | Weeks | Same shape. |
| **Open Collective + Open Source Collective** | No | **10%** host+platform plus processor; donations **not** tax-deductible (OSC is 501(c)(6)) | Good if you want a public ledger of expenses | 1–2 weeks if you have ≥100 stars and two contributors | Right for a *project* budget. Expensive for a solo salary. |
| **Liberapay** | No | 0% platform | Niche FLOSS | Days | Recurring only. |
| **Ko-fi / BMC** | No | 0–5% + processor | Weak for this audience | Hours | Fine as a backup tip jar, not the campaign. |
| **Honor-system ledger → GitHub/Polar** | **Yes, socially** | 0–6% at conversion | Excellent | Hours | Drop-off 10–25%. Overshoot the goal. This is the implementation I recommend. |
| **DIY Stripe SetupIntents** | **Yes, technically** | ~2.9% + 30¢ | Excellent if you finish it | 1–3 weeks | Correct and a waste of remaining runway. SCA failures at capture. |
| **GoFundMe** | No (keep-it-all) | 0% platform + processor; 5% on recurring | Wrong optics | Hours | Reads as hardship, not a software sprint. |
| **Goteo** | Yes (min then optimum, 40+40 days) | 4% | Commons-oriented, EU-centric | Weeks | Snowdrift's ethical pick. Weak US developer reach. |
| **Snowdrift.coop** | Crowdmatching, not a hard cliff | 0% | Tiny | n/a | Right theory, not enough patrons (their own project: 175 patrons, ~$31/month as of fetch). |

**GitHub Sponsors is the fee winner and the audience winner.** It does not
do escrow. Pair it with a ledger and you have the campaign. Polar is the
company-shaped complement (VAT, invoices, MoR). Kickstarter is the
mechanism winner and the audience loser.

I found no `FUNDING.yml` in the sase workspace tree. Turning on GitHub
Sponsors and adding that file is the highest-leverage hour in this whole
report, independent of any threshold.

## Fit with the first blog post

The live post at `structured-agentic-software-engineering` is being
rewritten in place. The outline already decided:

- Title stays `SASE: Structured Agentic Software Engineering` (or the
  renamed equivalent), same title on HN.
- ~2,800 words, five H2s, unheaded opening, `<!-- more -->` after the
  opening.
- Closing §5 is series map + **"I Need Your Help. I'm Out of Tokens."**
  + `type:poll` issues + a one-command Try It.

A threshold-pledge salary campaign is a second post, or a page, or a
clearly boxed 150-word closer that **points off-page**. Putting the
full deal in the first post does three pieces of damage: it spends the
word budget, it makes the Show HN a fundraiser, and it collides with
the tokens ask.

A closer that respects the outline:

> I need a job. sase has been full-time unpaid work, and that is ending.
> If you want a 6-week public 1.0 push before I disappear into interviews,
> there is a threshold campaign on the [funding page](/fund): pledges
> convert to charges only if we hit $G by $DATE. Recurring GitHub
> Sponsors is the thing that would actually let me keep doing this.
> Separately, I am also out of provider tokens; that is a different
> button.

That is ~90 words. It is enough.

## Legal and tax (high level, US, not advice)

The IRS's public crowdfunding FAQ (IR-2022-40 and the later reminder
pages) is facts-and-circumstances. Gross income includes everything
that is not excluded. Gifts require **detached and disinterested
generosity** with nothing expected in return (*Duberstein*). Reward-
based campaigns (Kickstarter-style: you promised work, a sticker, office
hours) are **business income**. A campaign whose pitch is "pay me to
work on sase for a month" is much closer to income for services than
to a hardship gift. GitHub Sponsors income is likewise generally
self-employment income for a developer whose business is software.

Form 1099-K: under the One Big Beautiful Bill restoration, for 2026
third-party settlement organizations generally issue 1099-K at **more
than $20,000 and more than 200 transactions**. Not receiving a 1099-K
does not make income non-taxable. Kickstarter / Polar / Stripe
proceeds you treat as payment for work still go on the return,
typically Schedule C, with self-employment tax.

Donors do **not** get a charitable deduction unless they give to a
qualified 501(c)(3). Open Source Collective is a **501(c)(6)**; OSC's
own FAQ says donations to hosted collectives are **not** tax-deductible.
Open Collective Foundation (501(c)(3)) is the deductible host, and it
wants an explicitly charitable mission. sase as a personal engineering
tool is a stretch for that. Do not advertise tax deductibility.

Gift-tax annual exclusion for *donors* in 2026 is $19,000 per recipient
in the secondary sources I saw; that is the donor's problem, and it
only matters for very large individual gifts. A $5,000 matching pledge
from one person is under that line.

State charitable-solicitation registration is a real trap if you
**hold yourself out as a charity**. Frame this as **personal income
for a defined body of work**, which is what it is.

I am not a CPA. Before money moves, spend one hour with one.

## Other approaches I would take seriously

**Paid work that is a job.** "I will spend a week installing sase for
your team, writing the macros you need, and pairing on your first
epic" at $6k–$15k is the same skill as the campaign, billed as
services, with no free-rider problem. Put a Polar product on it.

**Company sponsors via the Open Source Pledge.** Member companies
commit **$2,000 per FTE developer per year** to maintainers of their
choosing; the Pledge does not handle funds. Sentry, Posit, CodeRabbit,
Astral, GitButler and ~30 others are already on the list, with
~$7.4 million paid since launch. You cannot "join" as a maintainer;
you can become a destination those companies already pay, especially
if any of them run agent CLIs. A single Pledge-sized cheque from a
10-developer shop is $20,000 — two months at the prompt's rate.
thanks.dev is the usual routing tool those companies use.

**Grants, as a parallel bet, not the plan.** NLnet's rolling calls
are open again under Open Internet Stack, next deadline **3 November
2026**, grants typically €5,000–€50,000. Restack ("scalable open
internet stack") is a stretch for a TUI orchestrator; CodeSupply is
supply-chain metadata and a worse fit. Apply if you can write a
narrow, deliverable-shaped proposal in a weekend. Do not wait on it
for rent. GitHub Accelerator, Sovereign Tech Agency, and Prototype
Fund are slower still.

**Get the job, keep sase at night.** This is the default successful
pattern for solo tools. The campaign then becomes "help me keep
nights and weekends funded for API costs," which is the tokens ask
the outline already has. It is less romantic and more likely.

**Recurring-only, no threshold.** Enable GitHub Sponsors, set a public
monthly goal, and tell the truth: below $X/month I am interviewing;
above it I am not. Charges happen immediately, which loses the
assurance-contract property, and gains simplicity. For a tiny
audience this often raises *more* than a cliff campaign, because
there is no 99%-and-zero outcome.

I would still run a small threshold campaign for a **milestone**,
because the first-post traffic is a one-time spike and spikes convert
better against a deadline. I would not make the threshold the only
ask, and I would not make it the thing that gates the job search.

## Recommended solution

### What to build (and what not to)

**Do not build a payments product.** No SetupIntent app, no
self-hosted Kickstarter clone, no escrow smart contract. Polar's own
docs are the existence proof that delayed capture and off-session
charges are a billing-company feature, not a weekend script.

**Do use two hosted rails and a ledger.**

1. **GitHub Sponsors**, enabled this week, with `.github/FUNDING.yml`,
   one-time and monthly tiers, and a published monthly goal. This is
   the always-on path. Personal sponsorships: 0% platform fee.
2. **Polar**, a pay-what-you-want one-time product ("Support the 1.0
   sprint") and a monthly product, for companies that need invoices
   and VAT. Starter is 5% + 50¢.
3. **A `/fund` page** on sase.sh plus a GitHub issue
   `Funding ledger (closes DATE)`. Each pledge is a comment in a
   template: name or handle, amount, rail they will use (Sponsors or
   Polar), public or anonymous. A pinned table sums the public
   numbers. A progress bar is a locally rendered SVG or a Shields
   badge on a gist; it does not need a database.

### The deal, rewritten

**Meter 1 — one-time, 30 days, threshold.** Goal: **$6,000**
(stretch $12,000 as a second line on the same thermometer, Goteo-
style minimum / optimum). Pledges are promises. On the morning after
the deadline, if public pledges ≥ $6,000, you post: "The threshold
hit. Please convert your pledge within 7 days," with two links. You
keep a running total of **settled** money. If settled money is still
≥ $6,000, you start the sprint. If pledges hit and settled money
does not, you cancel, refund anyone who prepaid, and say so. Budget
the sprint as six weeks of named work, weekly notes, and a closeout
post (OSS.Fund's after-campaign list: amount, work done, work left,
expenses, next option).

**Meter 2 — recurring, no deadline.** GitHub Sponsors monthly goal
at **$6,000/month** (publish the number; GitHub requires you to
acknowledge that a dollar goal makes income public). Crossing it is
the only event that **pauses** interviewing. Dropping below it for
two consecutive months resumes interviewing. This is the actual
substitute for a job.

**Job search.** Starts now. The campaign is extra. If Meter 2 is
crossed you can stop; if a good offer arrives during Meter 1 you
can take it and finish the milestone at night, or refund. Write
that down on `/fund` so it is not a surprise.

**Lead match.** Before `/fund` goes public, ask one or two
people who already know the work (former colleagues, a company
running agent CLIs) for a $2,000–$5,000 match, announced as
"first $N is already pledged." That single sentence is worth more
than any platform choice.

**Consulting SKU.** On Polar: "One week of sase in your shop,"
fixed price, calendar-constrained so it cannot eat the sprint.
This is the job-compatible revenue line.

### What the first blog post does

Follow the existing outline. In §5, after the tokens sentence, add
the ~90-word closer above. Do not add reward tiers, budget tables,
or a thermometer to the post; those live on `/fund`. Do not
change the title. Do not make the Show HN submission about money.

### If you insist on true automatic capture

Use **Kickstarter**, and only after rewriting the campaign as a
**creative 1.0 launch with a working TUI prototype on video, a
reward ladder, and a locked 30-day clock**. Submit for review
before the blog post, because review is measured in days. Set the
goal at the **minimum** that makes the 1.0 sprint possible
(budget table, fees included), not at a month of salary. Expect
8–10% all-in. Treat Kickstarter as a payment processor with a
backer community you will mostly ignore; drive traffic from the
blog, not from Kickstarter Discover.

I would do this only if the honor-system drop-off feels
unacceptable *and* you can wait for review. For a developer
readership, it will not raise more than GitHub Sponsors plus a
ledger. It will cost a week of campaign-page work.

### First 14 days

1. Apply for GitHub Sponsors if you have not; add `FUNDING.yml`.
2. Create the Polar org and two products (one-time PWYW, monthly).
3. Write `/fund` with the two meters, the budget table, the
   job-search rule, and the consulting SKU.
4. Ask for the matching pledge in private.
5. Open the ledger issue, in `funding` state, not yet public.
6. Finish the launch post as the outline specified.
7. Publish post + `/fund` + ledger on the same day, or
   `/fund` a day later so the post can be read as a post.
8. File an NLnet Restack proposal before 3 November 2026 only if
   a weekend produces a tight, deliverable-shaped application.
   Do not block on it.

### What success looks like

- Meter 1 hits and you ship the named 1.0 work with weekly notes,
  whether or not you have a job offer in parallel.
- Meter 2 either crosses, in which case you can stop interviewing,
  or it does not, in which case you take a job and sase becomes a
  nights-and-weekends project whose API bill is paid by whatever
  Sponsors did arrive.
- Nobody is charged for a campaign that missed.
- The first blog post is still a piece of writing about the work,
  which is the only thing that makes a later campaign possible.

## Confidence and gaps

**High confidence.** Authorization windows vs. 30-day campaigns
(Stripe docs). Kickstarter all-or-nothing UX and ~8–10% fees
(Kickstarter help centre). GitHub Sponsors 0% / 6% split (GitHub
docs). Polar 2026 positioning and Starter fees (Polar docs).
Open Collective goals are thermometers, not escrow (OC docs).
OSC is 501(c)(6) and non-deductible (OSC FAQ). NLnet next
deadline 3 November 2026. No `FUNDING.yml` in this workspace.
Launch-post outline already owns §5.

**Medium confidence.** Kickstarter would reject a salary campaign
and might accept a 1.0-with-rewards campaign (rules are clear on
"create something new" and prototypes; secondary sources add a
business-tools restriction I could not re-verify on the live
rules page because it is behind a challenge wall). Honor-system
drop-off in a developer audience (PledgeBank is dead; I am
extrapolating). Conversion rates for a Show HN of an unknown
TUI (order-of-magnitude only). Polar issue-funding fully gone
(absent from current docs; older Changelog interview and
third-party posts still mention it).

**Low confidence / not checked.** Your GitHub Sponsors eligibility
and country payout status. Whether you already have a Stripe or
Polar account. Exact self-employment and state-tax numbers for
your situation. Whether any Open Source Pledge company already
depends on sase. Sovereign Tech Agency and GitHub Accelerator
current windows. Indiegogo's Gamefound acquisition details
beyond the all-or-nothing policy change.

**Not advice.** Tax, charity-registration, and employment law
need a human with a licence. The recommendation above is a
product and mechanism recommendation.

## Sources

**Prior sase research (audited reads).**
`research:202610/sase_launch_post_outline/sase_launch_post_outline.md`
· `research:202610/sase_launch_post_introduction/sase_launch_post_introduction.md`

**Mechanism.**
[Threshold pledge system (Wikipedia)](https://en.wikipedia.org/wiki/Threshold_pledge_system)
· Kelsey and Schneier, [The Street Performer Protocol](https://www.schneier.com/paper-street-performer.html), USENIX 1998
· [Assurance contract (HandWiki / Bagnoli and Lipman 1989)](https://handwiki.org/wiki/Finance:Assurance_contract)
· [Snowdrift.coop on other crowdfunding](https://wiki.snowdrift.coop/market-research/other-crowdfunding)
· [Snowdrift.coop, the snowdrift dilemma](https://wiki.snowdrift.coop/about/snowdrift-dilemma)
· OSS.Fund, [Crowdfunding for Open Source Projects](https://www.oss.fund/guides/crowdfunding-open-source/) (reviewed 2026-06-21)
· OSS.Fund, [Best funding options for solo maintainers](https://www.oss.fund/guides/best-funding-for-solo-maintainers/)

**Payments.**
[Stripe: Place a hold on a payment method](https://docs.stripe.com/payments/place-a-hold-on-a-payment-method) (7-day windows; extended auth is category-limited)
· [Stripe: Save a payment method without a payment (Setup Intents)](https://docs.stripe.com/payments/save-and-reuse)
· [Stripe: Accepting payments for pre-orders](https://support.stripe.com/questions/accepting-payments-for-pre-orders)

**Kickstarter / Indiegogo.**
[Kickstarter: Why is funding all-or-nothing?](https://help.kickstarter.com/hc/en-us/articles/115005047893-Why-is-funding-all-or-nothing) (updated 2026-09-02)
· [Kickstarter: What are the fees?](https://help.kickstarter.com/hc/en-us/articles/115005028634-What-are-the-fees)
· [Kickstarter Rules](https://www.kickstarter.com/rules) (prototype requirement for apps/software; "create something new")
· [Kickstarter: Who can use Kickstarter?](https://help.kickstarter.com/hc/en-us/articles/115005128594-Who-can-use-Kickstarter)
· Tiing, [Kickstarter alternatives 2026](https://www.tiing.co/blog/crowdfunding/kickstarter-alternatives/) (Indiegogo flexible funding ended 16 Oct 2025; fee table)

**GitHub / Polar / Open Collective.**
[GitHub Sponsors: about, fees](https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/about-github-sponsors-for-open-source-contributors) (0% personal, 6% org)
· [GitHub Sponsors: managing your sponsorship goal](https://docs.github.com/en/sponsors/receiving-sponsorships-through-github-sponsors/managing-your-sponsorship-goal)
· [GitHub Blog: $100 million for open source](https://github.blog/open-source/maintainers/100-million-for-open-source-a-milestone-built-by-the-community/) (2026-07-20)
· [Polar: introduction](https://polar.sh/docs/introduction)
· [Polar: fees](https://polar.sh/docs/merchant-of-record/fees) (Starter 5% + 50¢; off-session charges on paid plans)
· [Open Collective: setting goals and tiers](https://documentation.opencollective.com/collectives/raising-money/setting-goals-and-tiers.md)
· [Open Source Collective apply / FAQ](https://opencollective.com/opensource/apply) (501(c)(6), 10%, not deductible)

**Comparables and adjacent.**
[Open Source Pledge](https://opensourcepledge.com/about/) ($2,000/dev/year; ~$7.4M since launch)
· [NLnet: apply](https://nlnet.nl/funding.html) (next deadline 3 Nov 2026; €5k–€50k)
· [Andreas Kling / Ladybird Sponsors](https://github.com/sponsors/awesomekling/)
· [Simon Willison on the Ladybird Browser Initiative](https://simonwillison.net/2024/Jul/1/the-ladybird-browser-initiative/) ($1M from Wanstrath)
· LabHub, [Open Source Funding in 2026](https://labhub.hopto.org/blog/culture/2026-05-14-oss-funding-2026-github-sponsors-open-collective-polar-tidelift-ko-fi-developer-sponsorship-deep-dive)

**Tax (secondary, plus IRS).**
[IRS newsroom: crowdfunding contributions and distributions](https://www.irs.gov/newsroom/irs-reminds-taxpayers-of-important-tax-guidelines-involving-contributions-and-distributions-from-online-crowdfunding)
· CPA Validated, [Crowdfunding income tax 2026](https://cpavalidated.com/crowdfunding-tax-guide.html) (1099-K $20,000 / 200 tx for 2026)
· Beancount, [Crowdfunding and taxes in 2026](https://beancount.io/blog/2026/05/14/crowdfunding-tax-treatment-kickstarter-gofundme-indiegogo-form-1099-k-taxable-income-gifts-irs-recordkeeping-guide)
