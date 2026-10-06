import statistics, sys, time
import sase_core_rs as m
d = sys.argv[1]
def t(label, fn, runs=7):
    fn()
    xs = []
    for _ in range(runs):
        s = time.perf_counter(); fn(); xs.append((time.perf_counter() - s) * 1000)
    print(f"{label:<44} median {statistics.median(xs):8.1f} ms  min {min(xs):8.1f}")
t("bead_stats", lambda: m.bead_stats(d))
t("bead_show sase-j0", lambda: m.bead_show(d, "sase-j0"))
t("bead_show_issue_detail sase-j0", lambda: m.bead_show_issue_detail(d, "sase-j0"))
t("bead_ready", lambda: m.bead_ready(d))
t("bead_read_store (all issues -> Python)", lambda: m.bead_read_store(d))
