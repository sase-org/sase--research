---
narration: 1
title: Waking Waiting Agents Sooner
source: research:202610/wait_wakeup_jobs_vs_service_procs/wait_wakeup_jobs_vs_service_procs__final.md
source_blob: 0a8514b05143e6dc8f855264ef19998ff9db4fa2
date: 2026-10-07
kind: research
edition: brief
producer: agent
target_minutes: 4
---

## The short answer

Should builtin jobs become service processes so waiting agents can wake sooner? The recommendation is to migrate none now. That includes the wait checks job. Waiting agents do wake too slowly. But changing the supervisor does not fix the measured causes.

The consolidated research combines 5 independent reports with live verification on athena. Most researchers favored keeping the job. The daemon proposal offered a sound design, but the evidence favors simpler fixes first.

The distinction is between supervision, activation, and process lifetime. A service host decides who restarts a process. Event activation decides how quickly it reacts. A persistent process can retain warm state. These are separate choices.

The guiding rule is that daemons listen and jobs reconcile. A socket listener or subscription needs a persistent service. Periodic reconciliation usually benefits from bounded jobs, timeouts, and individual run histories.

## What makes waits slow

The wait checks trigger watches directories above the files recording completion. It cannot see those completion writes. In the 11 newest runs, 8 were skipped because watched paths appeared unchanged.

When the job does run, it spends about 29 s processing mostly dead waiters. There were 906 waiting markers, but only 19 belonged to live runners. Another 883 runners were dead.

The routine also waits for its slowest job before finishing a cycle. Its nominal 10 s cycle averages 24.4 s. Sidecar synchronization and other expensive checks share that lane.

Consequently, the runner's own 60 s fallback releases about 82% of dependency waits. The measured fallback sample had a median release delay of 33 s. Its 90th percentile was 58 s. The smaller sample released through readiness markers had a median of 21 s.

These distributions come from small samples and heuristic matching. They refute optimistic latency estimates, but should not be treated as precise population statistics.

There is also a correctness race. The job writes the readiness marker non-atomically. The runner treats an unreadable or partly written marker as ready. An agent could cross the dependency barrier early.

Finally, release does not mean the agent starts working. The median delay after release was about 45–50 s. A capacity scan took about 11 s per pass under a shared lock. Resolver changes leave this admission delay untouched.

## The recommended solution

First, measure release source, release latency, and the delay from release to agent start. Restate the goal as a latency target. The proposed median release target is at most 5 s. The 95th percentile target is at most 15 s.

Then fix correctness. Publish readiness markers atomically. Treat malformed or unreadable markers as not ready, and retry.

Point the trigger at the existing completion pulse. Signal new waiters too. Resolve live waiters through the artifact index, and sweep stale markers carefully.

Give wait checks its own 2 s routine. Move sidecar synchronization into another routine. After synchronization brings in bead closures, signal the affected project's resolver.

Keep the polling backstop. Once readiness markers handle at least 90% of releases, lengthen the costly runner fallback. Shortening it would multiply full index builds on an already busy host.

The expected release time after these fixes is about 2–6 s. This is an estimate, not a measured result.

Add general scheduler event activation only if multiple domains need it. Consider a dedicated resolver daemon only if measured targets remain unmet. Any daemon needs a single writer, repair polling, update restarts, and preserved diagnostics.

In parallel, reduce admission scan cost. The recommended solution is to fix the lane, measure the outcome, and keep builtin reconciliation work as jobs.
