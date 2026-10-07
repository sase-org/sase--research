---
narration: 1
title: Recent Reading to Steer SASE
source: research:202610/sase_next_direction_reading_list/sase_next_direction_reading_list__final.md
source_blob: 157b8978549ceadab46ca0b1f67ee5ca21153a5f
date: 2026-10-07
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The question and short answer

Which recent readings could steer Structured Agentic Software Engineering, or SASE? This report combines five researchers with independent lead research. It prioritizes designs SASE could copy, measurements that could change decisions, and the strength of evidence.

If you read only three, choose Chronicle, Ledger, and Loopjacking, in that order. They address replay, execution state, and approval integrity. The next priority is parallel landing: agents whose changes work separately but fail together.

Most recommendations are preprints. Several rely on small samples or constructed scenarios. Read their mechanisms closely, and treat their headline results cautiously.

## The deciding evidence

Chronicle offers a concrete replay design. Developers mark model calls, tool calls, and routing boundaries. Each crossing records an immutable envelope. Replay can serve earlier responses from the record, then resume live work at a chosen boundary.

A missing or extra recorded crossing raises an error. SASE would still need concurrent-call support and a digest that detects reordered operations. Chronicle tests six self-constructed incidents with simulated model boundaries. Its value is the mechanism, rather than broad evidence of effectiveness.

Ledger turns interaction history into observed, modified, and attempted state, without extra model calls. On 500 software issue-repair tasks, one model's pass rate rose from 56.2% to 64.2%, at 28.9% lower cost.

The immediate opportunity is a mechanically derived state view for successor agents. Ledger also suppresses redundant commands. Keep that separate from SASE's receipt policy, which does not let receipts skip execution. Its evaluation used one run per instance and Python issue repair.

Loopjacking shows approval failures in shipping agent frameworks. An approved operation could be replaced before execution. Matching a call identifier was insufficient when arguments were unchecked.

Its approval record and regression tests apply directly to SASE's gates. Bind approval to the complete operation, the approving principal, and the scope. Check mutations, denial, expiry, and reuse of spent approvals. Its companion, CapLease, addresses durable consumption after crashes. This is a chosen sample, rather than a prevalence estimate.

Parallel landing needs similarly careful interpretation. Claim Plane's static admission improved integration success from 65.6% to 96.7%. But it serialized 96.7% of executions. The selective mode performed worse than no coordination.

The practical lesson is to declare scope before writing and serialize overlap. The companion study, Passes Alone, Fails Together, found a short sibling-change message recovered 82% of constructed broken integrations. Real mined change pairs almost never interfered semantically. These constructed failures do not estimate everyday frequency.

## What to read and do next

Start with Chronicle for replay boundaries, Ledger for continuation state, and Loopjacking for approval binding. Then read the Claim Plane cluster before tuning parallel phase coordination.

The fifth-ranked reading is Hassan's foundational SASE paper. It is already queued in your library. Its updated appendix adds worked examples, including criteria for a merge-readiness pack.

Proof-or-Stop comes next for verification receipts. Look at command-set hashes, independent witnesses, freshness, and explicitly degraded assurance. A receipt should bind what was actually proven.

The harness studies then challenge portable model rankings and effort labels. Harness choice can change cost substantially. Measure adapters and size aliases with pinned resources before changing defaults on small samples.

ParallelPilot follows for the agent dashboard. Throughput rose 63%, but perceived control did not improve. Design for returning after a wait. Distinguish an agent claiming completion from verified completion.

Across these readings, the report proposes replay envelopes, execution-state views, approval regression tests, declared phase scopes, and measured adapter behavior. These are an idea backlog, not filed tasks. The reading order starts with mechanisms closest to work SASE already has open.
