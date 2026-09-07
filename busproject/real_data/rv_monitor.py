"""
Runtime-verification (RV) style monitor -- minimal proof of concept,
UPGRADED to perform ONLINE re-estimation of the model from the event stream.

The monitor combines a multi-band reference view with sequential rate
re-estimation and runtime-style threshold checking:

  * The monitor replays one published timetable day as a stream of SCHEDULED
    departure events; it does not observe realised vehicle trajectories.
  * After each arrival it RE-ESTIMATES the current bus rate mu_bus online, as the
    maximum-likelihood estimate from the most recent inter-arrival gaps
    (mu_hat = 1 / mean(recent gaps)).  This is the model being UPDATED from data.
  * It then re-checks, in real time, the service-level indicator
        P(a bus within W minutes) = 1 - exp(-mu_hat * W)
    against a target, and raises / clears an ALERT as the verdict changes.

This is a schedule-replay monitoring view (walk one published schedule sequence,
re-estimate and re-check as we go), not exact model checking over the whole state
space and not monitoring of realised disruptions or punctuality.  Because the estimate adapts continuously, the monitor
clears/raises alerts mid-band -- e.g. it follows the overnight->morning ramp-up
that a fixed 6-hour band would average away.

Data: imported from route77_data.py (single source of truth).
Source: First Glasgow route 77, Partick Bus Station (stance 1),
bustimes.org / TNDS, Tue 23 June 2026 (departure times manually verified).
"""
import math
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
from route77_data import dep_minutes

# ----------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------
W          = 15.0   # monitoring window: "a bus within W minutes"
SLA_TARGET = 0.50   # illustrative bus-arrival benchmark threshold
SYNTH_SLA  = 0.95   # illustrative synthetic passenger-service threshold
WINDOW     = 4      # estimator uses the four most recent scheduled headway gaps


def hhmm(minutes):
    minutes = int(round(minutes)) % 1440
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def reliability(mu, w=W):
    """Probability of a bus arrival within w under a Poisson-headway model.

    The Poisson calculation and the perfectly punctual calculation are treated
    as two benchmark interpretations of the published schedule. They illustrate
    sensitivity to the assumed headway distribution and are not claimed as
    universal probabilistic bounds.
    """
    return 1.0 - math.exp(-mu * w)


# ----------------------------------------------------------------------
# 1. Streaming online re-estimation over the real arrival event stream
# ----------------------------------------------------------------------
arrivals = dep_minutes()
recent = deque(maxlen=WINDOW)

times, mus, Ps, states = [], [], [], []
prev_status = None
events = []   # (time, "RAISED"/"CLEARED")

for i in range(1, len(arrivals)):
    gap = arrivals[i] - arrivals[i - 1]
    recent.append(gap)
    if len(recent) < 2:                      # need a couple of gaps to estimate
        continue
    mu_hat = 1.0 / (sum(recent) / len(recent))   # online MLE of the rate
    P = reliability(mu_hat)
    status = "OK" if P >= SLA_TARGET else "ALERT"
    times.append(arrivals[i]); mus.append(mu_hat); Ps.append(P); states.append(status)
    if status != prev_status:
        if status == "ALERT":
            events.append((arrivals[i], "RAISED"))
        elif prev_status is not None:
            events.append((arrivals[i], "CLEARED"))
        prev_status = status

print("=" * 72)
print("SCHEDULE-REPLAY MONITOR -- route 77, Partick  (published timetable)")
print("online estimate: mu_hat = 1/mean(last %d gaps);  check P(bus<=%.0fm) >= %.2f"
      % (WINDOW, W, SLA_TARGET))
print("=" * 72)
print("\nAlert log (verdict changes as the model is re-estimated):")
print("  [coverage note: the online estimate needs 2 inter-arrival gaps, so")
print("   monitoring STARTS at the 3rd arrival (02:17) -- service is already")
print("   below target from midnight, and the first 'raised' therefore marks")
print("   the START OF MONITORING, not the onset of degradation. Similarly,")
print("   nothing is monitored after the last arrival (23:19).]")
if not events:
    print("  (no verdict changes)")
for t_evt, kind in events:
    if kind == "RAISED":
        print("  %s  *** ALERT raised  ***  service dropped below target" % hhmm(t_evt))
    else:
        print("  %s      alert cleared      service back above target" % hhmm(t_evt))

# fraction of the (monitored) day in alert
frac = sum(1 for s in states if s == "ALERT") / len(states)
print("\nMonitor in ALERT for ~%.0f%% of the monitored events." % (100 * frac))

# ----------------------------------------------------------------------
# 2. Four-band reference summary
# ----------------------------------------------------------------------
t_arr = np.array(arrivals); g = np.diff(t_arr).astype(float)
mids = (t_arr[:-1] + t_arr[1:]) / 2 / 60.0
BANDS = [("Office  09-15", 9, 15), ("Evening 15-21", 15, 21),
         ("Least   21-03", 21, 27), ("Night   03-09", 3, 9)]
print("\n" + "-" * 72)
print("Four fixed bands (band-average view, for reference):")
print("%-14s %9s %9s %9s   %s" % ("Band", "headway", "mu/min", "P(<=15m)", "status"))
for name, lo, hi in BANDS:
    sel = ((mids >= lo) & (mids < hi)) | ((mids + 24 >= lo) & (mids + 24 < hi))
    if sel.sum() == 0:
        continue
    h = g[sel].mean(); mu = 1.0 / h; P = reliability(mu)
    st = "OK" if P >= SLA_TARGET else "*** ALERT ***"
    print("%-14s %6.1fm %9.4f %9.3f   %s" % (name, h, mu, P, st))

print("\nNote: against the illustrative synthetic passenger-service threshold (P>=%.2f)," % SYNTH_SLA)
print("the timetable-driven bands remain below 95% within 15 min, so the RV demo")
print("uses a separate illustrative bus-arrival threshold of %.2f. The fixed bands average away the" % SLA_TARGET)
print("overnight->morning ramp-up that the online monitor above resolves directly.")
print("This replays a published timetable; a live GTFS-RT stream with realised vehicle observations is future work.")

# ----------------------------------------------------------------------
# 3. Figure: the online verdict across the day
# ----------------------------------------------------------------------
hours = [t / 60.0 for t in times]
fig, ax = plt.subplots(figsize=(11, 4.4))

below = [p < SLA_TARGET for p in Ps]
ax.fill_between(hours, 0, 1, where=below, step="post",
                color="#c0392b", alpha=0.16, zorder=1,
                label="ALERT region")
ax.step(hours, Ps, where="post", color="#2E5496", lw=2.0, zorder=3,
        label="online P(bus within 15 min)")
ax.axhline(SLA_TARGET, color="#34495e", ls="--", lw=1.4, zorder=2,
           label="illustrative monitor threshold = %.2f" % SLA_TARGET)
ax.axhline(SYNTH_SLA, color="#999", ls=":", lw=1.1, zorder=2,
           label="synthetic passenger-service threshold = %.2f" % SYNTH_SLA)

for b in (3, 9, 15, 21):                      # four-band reference boundaries
    ax.axvline(b, color="#bbb", ls=":", lw=0.8, zorder=1)

ax.set_xlim(0, 24); ax.set_ylim(0, 1.0)
ax.set_xticks(range(0, 25, 3))
ax.set_xlabel("hour of day")
ax.set_ylabel("P(bus within 15 min)")
ax.set_title("Online runtime monitor over one day (route 77, Partick)\n"
             "model re-estimated after every arrival; red = threshold not met",
             fontsize=11)
ax.legend(loc="lower center", ncol=2, fontsize=8, framealpha=0.9)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig("rv_monitor_timeline.png", dpi=130)
print("\nsaved figure -> rv_monitor_timeline.png")
