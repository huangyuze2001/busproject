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

Note: a timetable gives the BUS service rate (mu_bus), not passenger demand,
so lambda/theta/Cap/K remain assumed (as in Stage 1). P(bus<=15m) depends
only on mu_bus and is therefore the cleanest, demand-independent indicator;
the expected wait additionally depends on the assumed demand, so at low
night frequency it grows large (the stop tends towards saturation under a
fixed daytime demand) -- this is a consequence of the fixed-demand assumption.
"""
import numpy as np
from route77_data import DEP, to_min

t=np.array([to_min(x) for x in DEP]); gaps=np.diff(t).astype(float)
mids=(t[:-1]+t[1:])/2/60.0          # midpoint (hour of day) of each gap

# Full-day bands (hour-of-day ranges)
bands=[("Night 00-05h",   0,  5),
       ("Early 05-07h",   5,  7),
       ("AM peak 07-09h", 7,  9),
       ("Midday 09-15h",  9, 15),
       ("Evening 15-20h",15, 20),
       ("Late 20-24h",   20, 24)]

def aggregate(lam,mu_bus,theta,Cap,K):
    n=K+1; Q=np.zeros((n,n))
    for i in range(n):
        if i<K: Q[i,i+1]+=lam
        if i>0: Q[i,i-1]+=i*theta
        Q[i,max(i-Cap,0)]+=mu_bus
    for i in range(n): Q[i,i]=-(Q[i].sum()-Q[i,i])
    A=np.vstack([Q.T,np.ones(n)]); b=np.zeros(n+1); b[-1]=1
    pi,*_=np.linalg.lstsq(A,b,rcond=None)
    L=float((pi*np.arange(n)).sum())
    thr=float(sum(pi[i]*min(i,Cap)*mu_bus for i in range(n)))
    return L,thr

LAM,THETA,CAP,K = 0.40, 0.03, 10, 30   # demand assumed (as in Stage 1)

print("Route 77 at Partick Bus Station (First Glasgow) -- real timetable, Tue 23 Jun 2026")
print("(full day; mu_bus estimated per band from real headways)\n")
print(f"{'Time band':<18}{'headway':>10}{'mu/hour':>9}{'mu/min':>9}{'P(bus<=15m)':>13}{'wait(min)':>11}")
print("-"*70)
band_mu={}
for name,lo,hi in bands:
    sel=(mids>=lo)&(mids<hi)
    if sel.sum()==0: continue
    h=gaps[sel].mean(); mu=1/h; band_mu[name]=(h,mu)
    L,thr=aggregate(LAM,mu,THETA,CAP,K); W=L/thr if thr>0 else float('nan')
    p15=1-np.exp(-mu*15)
    print(f"{name:<18}{h:>7.1f}min{60/h:>9.3f}{mu:>9.4f}{p15:>13.2f}{W:>11.1f}")
print("-"*70)

night=band_mu["Night 00-05h"][0]; midday=band_mu["Midday 09-15h"][0]
print(f"\nNight headway ~{night:.0f} min vs midday ~{midday:.0f} min: a {night/midday:.0f}x")
print("difference in service rate, straight from the real timetable. Reliability")
print("P(bus<=15m) rises through the morning, peaks at midday, and falls again")
print("through the evening into the sparse late-night service.")
