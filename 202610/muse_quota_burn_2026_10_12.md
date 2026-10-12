# Why Is Muse Burning Through Quota Today? (2026-10-12)

**Question:** Muse Code is churning through tokens today. Did we cause it, or did Meta?

## Bottom line

- **We didn't cause it.** Muse is doing much _less_ work today than on a normal day, and
  each agent costs about the same as before.
- **Meta's meter changed.** For the same amount of work, Meta's usage meter now counts
  about **12–25× more** than it did last week. Our plan tier is unchanged, and we found no
  public announcement. Something changed on Meta's side: either they quietly cut the
  limit or they changed what the meter counts.
- **One thing we couldn't rule out:** the MacBook was online until ~14:30 and uses the
  same Muse account. We couldn't SSH in to check it (see "Next steps").

## The numbers

Totals are summed across both machines that run Muse agents (athena + apollo), taken
from Muse's own per-session logs.

|                       | Last week (Sun Oct 4 8pm → Sun Oct 11 8pm) | This week so far (Sun Oct 11 8pm → Mon 2:40pm, ~18.5 h) |
| --------------------- | ------------------------------------------ | -------------------------------------------------------- |
| Model calls           | 77,136                                     | 3,287                                                    |
| Input tokens          | 10.4 B                                     | 0.48 B                                                   |
| Uncached input tokens | 286 M                                      | 6.4 M                                                    |
| Output tokens         | 34 M                                       | 1.6 M                                                    |
| Meta's weekly meter   | no Muse limit errors or auto-disables      | **56% used**                                             |

- **Weekly meter.** At today's rate, 100% of the weekly allowance is about 0.86 B input
  tokens. Last week we used 10.4 B, roughly 12× that (about 25× if Meta meters on
  uncached tokens). Agents kept running all week anyway, and SASE never auto-disabled
  Muse.
- **5-hour meter.** From 13:17 to 14:39 we used ~96 M input tokens, and the meter reads
  27%, so 100% is roughly 350 M per 5 hours. Last week's busiest 5 hours (Oct 9,
  12:00–17:00) used 1.18 B, about 3.3× that, without hitting a limit.

## Did we change something? No.

Per-session cost has been flat for weeks. The table below covers athena; apollo looks
the same.

| Day    | Muse version | First prompt (tokens) | Input per call | Cache hit | Output per call |
| ------ | ------------ | --------------------- | -------------- | --------- | --------------- |
| Oct 9  | 1.4.4        | 33.1 K                | 130 K          | 96.9%     | ~445            |
| Oct 12 | 1.4.6        | 33.5 K                | 151 K          | 98.7%     | ~445            |

- Agent volume is down, not up: 23 Muse agent runs on athena today versus 194 on Oct 9.
- Our recent provider and instruction commits, such as `2c9f761210` (Oct 10, retire
  provider-instructions flags), only moved the starting prompt by about 1%.
- **Biggest single consumer today:** one 2-hour `sase-1jm.8` agent in `sase_14`, with
  105 M input tokens over 436 model calls. That is about 22% of this week's tokens.
  Sessions this large aren't new, though: last week had 4 sessions over 100 M.

## Did Meta change something? Very likely, in how usage is metered.

- **Muse auto-updated to 1.4.6 at Sun Oct 11 19:37**, 23 minutes before the weekly reset.
  Under 1.4.6, the token counts Muse logs locally per call look the same as before, so the
  update doesn't make agents use more tokens that we can see.
- **Possible hidden cost:** Muse runs background "reminder" sub-agents (skill and memory
  reminders) on most turns. They log **0 tokens** locally both before and after the update,
  so we can't see what Meta charges for them. They run slightly more often now (about 1.05
  per model call, up from 0.84 on Oct 9), which is nowhere near enough to explain a 12×
  jump unless Meta started counting them heavily.
- **Unchanged:** the plan tier ID (`27681631238169137`, the same as on Sep 20) and the
  weekly reset time (Sunday 8 pm ET).
- **No announcement found:** a web search turned up no public Meta notice of a limit
  change. Muse Code's paid plans date from its Aug 31 general-availability launch.

## Caveats

- SASE only stores the **latest** meter reading, so we have no record of last week's
  percentages. The claim that last week stayed under the limit is inferred: there were no
  Muse limit errors, no auto-disable, and agents ran normally. Muse's API allows readings
  above 100%, so if last week's header already showed far more than 100%, then the meter
  didn't change. Remembering what the header showed last week is the fastest way to
  settle this.
- The MacBook shares the Muse account and was online until ~14:30 today, but SSH timed
  out, so any usage on it is not counted here.

## Next steps

1. When the Mac is back online, run
   `ls ~/.local/share/muse/sessions/2026/10/12 | wc -l` on it. Near zero means the
   Mac wasn't the cause.
2. If the Mac is clean, check Meta's usage page (`dev.meta.ai/usage`) or contact
   support. Until then, expect Muse to hit its weekly cap around Tuesday at the
   current pace, and lean on the other providers.
3. Possible SASE follow-up: keep a history of Muse meter readings, not just the latest
   one, so the next question like this is a one-line lookup instead of log forensics.

## How this was measured

- **Token counts:** summed from `model_completed` events in
  `~/.local/share/muse/sessions/YYYY/MM/DD/<id>/session.jsonl` on athena and apollo
  (apollo's clock is UTC; its data was bucketed in ET).
- **Live meter:** read with SASE's free echo-mint probe (`muse serve` plus a turn on the
  echo provider), which makes no model call.
- **Agent volume:** taken from `~/.sase/logs/runs.jsonl`.
