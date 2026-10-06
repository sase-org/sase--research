import json, os, sys, collections, datetime as dt
d = sys.argv[1]
def ts(s):
    s = s.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(s)
issues = {}
with open(os.path.join(d, "issues.jsonl")) as f:
    for line in f:
        r = json.loads(line); issues[r["id"]] = r
now = dt.datetime(2026, 10, 6, 21, 0, tzinfo=dt.timezone.utc)
ev = []
sd = os.path.join(d, "events/streams")
for fn in os.listdir(sd):
    with open(os.path.join(sd, fn)) as f:
        for line in f:
            if line.strip():
                e = json.loads(line); ev.append((fn, e))
print("events", len(ev))
# events applied to beads whose current state is closed, landing >= N days after that bead's closed_at
for lag in (7, 30, 60):
    c = collections.Counter(); beads = set()
    for fn, e in ev:
        i = issues.get(e.get("issue_id"))
        if not i or i.get("status") != "closed" or not i.get("closed_at"):
            continue
        try:
            if ts(e["timestamp"]) >= ts(i["closed_at"]) + dt.timedelta(days=lag):
                c[e["operation"]] += 1; beads.add(i["id"])
        except Exception:
            pass
    print(f"post-close writes >= {lag}d after close (bead still closed): total {sum(c.values())} on {len(beads)} beads :: {dict(c.most_common(6))}")
# reopen events in last 30 days on beads that had been closed >= 7 days
reopen = collections.Counter()
for fn, e in ev:
    if e["operation"] in ("issue_opened", "issue_reopened", "plus_one_added", "task_plus_one"):
        reopen[e["operation"]] += 1
print("reopen-ish ops (all time):", dict(reopen))
ops = collections.Counter(e["operation"] for _, e in ev)
print("all ops:", dict(ops.most_common(20)))
