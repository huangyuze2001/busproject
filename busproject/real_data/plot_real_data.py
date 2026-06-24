"""
Plot the time-of-day service reliability for First Glasgow route 77
at Partick Bus Station, derived from the real timetable.

Run after / alongside real_data_case.py. Produces real_data_reliability.png.
Source of data: bustimes.org / TNDS, route 77, Tue 23 Jun 2026.
"""
import numpy as np
import matplotlib.pyplot as plt

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
bands=[("Night\n00-05h",0,5),("Early\n05-07h",5,7),
       ("AM peak\n07-09h",7,9),("Midday\n09-14h",9,14)]

labels, headways, mu, p15, waits = [],[],[],[],[]
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
for name,lo,hi in bands:
    sel=(mids>=lo)&(mids<hi)
    h=gaps[sel].mean(); m=1/h; L,thr=aggregate(LAM,m,THETA,CAP,K)
    labels.append(name); headways.append(h); mu.append(m)
    p15.append(1-np.exp(-m*15)); waits.append(L/thr)

x=np.arange(len(labels))
fig,ax1=plt.subplots(figsize=(8,4.8))
# combine band label with its real headway on two lines
xticklabels=[f"{lab}\n(~{h:.0f} min)" for lab,h in zip(labels,headways)]
# bars: P(bus within 15 min)
bars=ax1.bar(x, p15, width=0.55, color="#2E5496", alpha=0.85,
             label="P(bus within 15 min)")
ax1.set_ylabel("P(bus within 15 min)", color="#2E5496", fontsize=11)
ax1.set_ylim(0,1.0); ax1.set_xticks(x); ax1.set_xticklabels(xticklabels, fontsize=9.5)
ax1.tick_params(axis='y', labelcolor="#2E5496")
for xi,p in zip(x,p15):
    ax1.text(xi, p+0.02, f"{p:.2f}", ha='center', fontsize=10, color="#2E5496")
# line: expected wait (second axis)
ax2=ax1.twinx()
ax2.plot(x, waits, "o-", color="#C0392B", linewidth=2, markersize=7,
         label="Expected wait (min)")
ax2.set_ylabel("Expected wait (min)", color="#C0392B", fontsize=11)
ax2.set_ylim(0, max(waits)*1.25); ax2.tick_params(axis='y', labelcolor="#C0392B")
for xi,w in zip(x,waits):
    ax2.text(xi, w+max(waits)*0.04, f"{w:.0f}", ha='center', fontsize=9, color="#C0392B")
plt.title("Time-of-day service reliability — First Glasgow route 77, Partick\n(derived from the real timetable, Tue 23 Jun 2026)",
          fontsize=11.5)
# combined legend
l1,la1=ax1.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
ax1.legend(l1+l2, la1+la2, loc="upper left", fontsize=9, framealpha=0.9)
fig.tight_layout()
fig.savefig("real_data_reliability.png", dpi=150, bbox_inches="tight")
print("saved real_data_reliability.png")
