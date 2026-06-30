"""
Plot the time-of-day service reliability for First Glasgow route 77
at Partick Bus Station, derived from the real timetable -- FULL-DAY version.

Run after / alongside real_data_case.py. Produces real_data_reliability.png.
Source of data: bustimes.org / TNDS, route 77, Partick (stance 1),
Tue 23 Jun 2026 (departure times manually verified).
"""
import numpy as np
import matplotlib.pyplot as plt
from route77_data import DEP, to_min

t=np.array([to_min(x) for x in DEP]); gaps=np.diff(t).astype(float)
mids=(t[:-1]+t[1:])/2/60.0

bands=[("Night\n00-05h",    0,  5),
       ("Early\n05-07h",    5,  7),
       ("AM peak\n07-09h",  7,  9),
       ("Midday\n09-15h",   9, 15),
       ("Evening\n15-20h", 15, 20),
       ("Late\n20-24h",    20, 24)]

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

LAM,THETA,CAP,K=0.40,0.03,10,30
labels, headways, p15, waits = [],[],[],[]
for name,lo,hi in bands:
    sel=(mids>=lo)&(mids<hi)
    h=gaps[sel].mean(); m=1/h; L,thr=aggregate(LAM,m,THETA,CAP,K)
    labels.append(name); headways.append(h)
    p15.append(1-np.exp(-m*15)); waits.append(L/thr)

x=np.arange(len(labels))
fig,ax1=plt.subplots(figsize=(10,4.8))
xticklabels=[f"{lab}\n(~{h:.0f} min)" for lab,h in zip(labels,headways)]

ax1.bar(x, p15, width=0.6, color="#2E5496", alpha=0.85,
        label="P(bus within 15 min)")
ax1.set_ylabel("P(bus within 15 min)", color="#2E5496", fontsize=11)
ax1.set_ylim(0,1.0); ax1.set_xticks(x); ax1.set_xticklabels(xticklabels, fontsize=9)
ax1.tick_params(axis='y', labelcolor="#2E5496")
for xi,p in zip(x,p15):
    ax1.text(xi, p+0.02, f"{p:.2f}", ha='center', fontsize=9.5, color="#2E5496")

ax2=ax1.twinx()
ax2.plot(x, waits, "o-", color="#C0392B", linewidth=2, markersize=7,
         label="Expected wait (min)")
ax2.set_ylabel("Expected wait (min)", color="#C0392B", fontsize=11)
ax2.set_ylim(0, max(waits)*1.25); ax2.tick_params(axis='y', labelcolor="#C0392B")
for xi,w in zip(x,waits):
    ax2.text(xi, w+max(waits)*0.035, f"{w:.0f}", ha='center', fontsize=8.5, color="#C0392B")

plt.title("Time-of-day service reliability — First Glasgow route 77, Partick\n"
          "(derived from the real timetable, full day, Tue 23 Jun 2026)", fontsize=11.5)
l1,la1=ax1.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
ax1.legend(l1+l2, la1+la2, loc="upper left", fontsize=9, framealpha=0.9)
fig.tight_layout()
fig.savefig("real_data_reliability.png", dpi=150, bbox_inches="tight")
print("saved real_data_reliability.png")
