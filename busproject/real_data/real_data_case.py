"""
Minimal real-data case study (Glasgow, route 77) -- FULL-DAY version.

Real bus departure times for First Glasgow route 77 (Glasgow Buchanan -
Glasgow Airport, operator First Greater Glasgow) at "Partick Bus Station
(stance 1)", towards Glasgow Airport, for Tuesday 23 June 2026.
Source: bustimes.org (timetable data from the Traveline National Dataset,
TNDS), retrieved 2026-06-23. Departure times manually verified.

Purpose: estimate a REAL, time-of-day-dependent bus arrival rate mu_bus from
the timetable and feed it into the single-stop CTMC, replacing the synthetic
mu_bus used in Stages 1-2 -- implementing the supervisor's suggestion of a
time-dependent rate fetched from a real timetable.

Modelling notes:
  * A timetable gives the BUS service rate (mu_bus), not passenger demand, so
    lambda/theta/Cap/K remain assumed (as in Stage 1).
  * POISSON vs SCHEDULED (#1): the CTMC treats bus arrivals as Poisson. A
    punctual scheduled service is near-deterministic, for which
    P(bus<=T) = min(T/h, 1); the table shows BOTH columns. Real service lies
    between them (the Poisson value is the conservative lower bound).
  * WAIT (#3, corrected): with reneging, Little's law uses the TOTAL exit
    flow, so W = L / (throughput + renege_rate). Dividing by boarding
    throughput alone (the previous version) overstates the wait, badly at
    night where reneging dominates.
"""
import numpy as np
from route77_data import DEP, to_min
from stop_model import aggregate, p_bus_within_poisson, p_bus_within_scheduled

t=np.array([to_min(x) for x in DEP]); gaps=np.diff(t).astype(float)
mids=(t[:-1]+t[1:])/2/60.0          # midpoint (hour of day) of each gap

# Full-day bands (hour-of-day ranges)
bands=[("Night 00-05h",   0,  5),
       ("Early 05-07h",   5,  7),
       ("AM peak 07-09h", 7,  9),
       ("Midday 09-15h",  9, 15),
       ("Evening 15-20h",15, 20),
       ("Late 20-24h",   20, 24)]

LAM,THETA,CAP,K = 0.40, 0.03, 10, 30   # demand assumed (as in Stage 1)
T_SLA = 15.0

print("Route 77 at Partick Bus Station (First Glasgow) -- real timetable, Tue 23 Jun 2026")
print("(full day; mu_bus estimated per band from real headways)")
print("(P15 shown under BOTH headway assumptions; wait uses Little with reneging)\n")
print(f"{'Time band':<18}{'headway':>10}{'mu/hour':>9}{'mu/min':>9}"
      f"{'P15 Poisson':>13}{'P15 sched':>11}{'wait(min)':>11}")
print("-"*81)
band_mu={}
for name,lo,hi in bands:
    sel=(mids>=lo)&(mids<hi)
    if sel.sum()==0: continue
    h=gaps[sel].mean(); mu=1/h; band_mu[name]=(h,mu)
    L,thr,ren=aggregate(LAM,mu,THETA,CAP,K)
    W=L/(thr+ren) if (thr+ren)>0 else float('nan')     # Little, corrected (#3)
    p15  = p_bus_within_poisson(mu, T_SLA)
    p15d = p_bus_within_scheduled(h, T_SLA)
    print(f"{name:<18}{h:>7.1f}min{60/h:>9.3f}{mu:>9.4f}{p15:>13.2f}{p15d:>11.2f}{W:>11.1f}")
print("-"*81)

night=band_mu["Night 00-05h"][0]; midday=band_mu["Midday 09-15h"][0]
print(f"\nNight headway ~{night:.0f} min vs midday ~{midday:.0f} min: a {night/midday:.0f}x")
print("difference in service rate, straight from the real timetable. Reliability")
print("rises through the morning, peaks at midday, and falls again through the")
print("evening into the sparse late-night service.")
print("\nReading the two P15 columns: under a punctual schedule every daytime band")
print("would be near-certain (h <= 15 min => P=1); the Poisson column is the")
print("worst case for irregular arrivals. The gap between them IS the value of")
print("punctuality -- see the scheduled-vs-Poisson limitations discussion.")
