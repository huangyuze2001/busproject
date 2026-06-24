"""
Minimal real-data case study (Glasgow, route 77).

Real bus departure times for First Glasgow route 77 (Glasgow Buchanan -
Glasgow Airport, operator First Greater Glasgow) at "Partick Bus Station
(stance 1)", towards Glasgow Airport, for Tuesday 23 June 2026.
Source: bustimes.org (timetable data from the Traveline National Dataset,
TNDS), retrieved 2026-06-23.

Purpose: estimate a REAL, time-of-day-dependent bus arrival rate mu_bus from
the timetable and feed it into the single-stop CTMC, replacing the synthetic
mu_bus used in Stages 1-2 -- implementing the supervisor's suggestion of a
time-dependent rate fetched from a real timetable.

Note: a timetable gives the BUS service rate (mu_bus), not passenger demand,
so lambda/theta/Cap/K remain assumed (as in Stage 1).
"""
import numpy as np

# ---- REAL departures at Partick Bus Station (stance 1), towards Airport ----
DEP = ["00:17","01:17","02:17","03:17","04:17","05:18","05:48","06:19","06:34",
       "06:49","07:04","07:22","07:37","07:52","08:07","08:26","08:41","08:56",
       "09:11","09:22","09:36","09:51","10:06","10:19","10:33","10:46","10:59",
       "11:16","11:33","11:47","12:02","12:17","12:32","12:47","13:02","13:17",
       "13:33"]

def to_min(s):
    h,m=s.split(":"); return int(h)*60+int(m)

t=np.array([to_min(x) for x in DEP]); gaps=np.diff(t).astype(float)
mids=(t[:-1]+t[1:])/2/60.0

bands=[("Night 00-05h",0,5),
       ("Early 05-07h",5,7),
       ("AM peak 07-09h",7,9),
       ("Midday 09-14h",9,14)]

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

LAM,THETA,CAP,K = 0.40, 0.03, 10, 30   # demand assumed (realistic, non-saturated)

print("Route 77 at Partick Bus Station (First Glasgow) -- real timetable, Tue 23 Jun 2026\n")
print(f"{'Time band':<18}{'headway':>10}{'mu_bus':>9}{'P(bus<=15m)':>13}{'wait(min)':>11}")
print("-"*61)
for name,lo,hi in bands:
    sel=(mids>=lo)&(mids<hi)
    if sel.sum()==0: continue
    h=gaps[sel].mean(); mu=1/h
    L,thr=aggregate(LAM,mu,THETA,CAP,K); W=L/thr if thr>0 else float('nan')
    p15=1-np.exp(-mu*15)
    print(f"{name:<18}{h:>7.1f}min{mu:>9.3f}{p15:>13.2f}{W:>11.1f}")

print(f"\nNight headway ~60 min, daytime ~15 min: a {gaps[mids<5].mean()/gaps[(mids>=7)].mean():.0f}x")
print("difference in service rate, straight from the real timetable.")
