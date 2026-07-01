"""
Stage-3 scalability: state-space growth per added stop.
Data: PRISM reachable state counts (2-stop 5,292; 3-stop 213,003).

EXTRAPOLATION (#5, corrected): the old figure extrapolated a FLAT x40 per
stop, but the growth factor is not constant. Structurally the k-stop model
has (K+1)^k * k * (Cap+1) syntactic states, so the k -> k+1 factor is
    (K+1) * (k+1)/k  =  21 * (k+1)/k     (=31.5 for 2->3, 28 for 3->4, 26.25 for 4->5)
The MEASURED reachable-state factor for 2->3 was x40.3 (reachability pruning
differs between sizes), i.e. somewhat above the structural ratio. 4- and
5-stop are therefore shown as RANGES: [structural factor, observed x40].
Either way the conclusion stands: growth is exponential in the number of
stops and exact model checking becomes untenable -> SMC.
Produces scalability_growth.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

K_PLUS_1 = 21          # station capacity K=20  ->  n_i in 0..20
measured = {2: 5292, 3: 213003}

def structural_factor(k):          # k stops -> k+1 stops
    return K_PLUS_1 * (k + 1) / k

# ranges for 4 and 5 stops: low = structural factor, high = observed x40
lo4 = measured[3] * structural_factor(3);  hi4 = measured[3] * 40
lo5 = lo4 * structural_factor(4);          hi5 = hi4 * 40

stops  = [2, 3, 4, 5]
values = [measured[2], measured[3], np.sqrt(lo4*hi4), np.sqrt(lo5*hi5)]  # bar = geo-mid of range
is_meas= [True, True, False, False]
labels = ["5,292", "213,003",
          f"~{lo4/1e6:.0f}\u2013{hi4/1e6:.1f} million",
          f"~{lo5/1e6:.0f}\u2013{hi5/1e6:.0f} million"]
factors= ["\u00d740.3\n(measured)", "\u00d728\u201340\n(est.)", "\u00d726\u201340\n(est.)"]

fig,ax=plt.subplots(figsize=(8.4,4.9))
xs=np.arange(len(stops))
colors=["#2E5496" if m else "#B0B7C6" for m in is_meas]
ax.bar(xs, values, width=0.55, color=colors)
# error bars for the extrapolated ranges
ax.errorbar([2,3], [values[2],values[3]],
            yerr=[[values[2]-lo4, values[3]-lo5],[hi4-values[2], hi5-values[3]]],
            fmt='none', ecolor="#777777", capsize=5, lw=1.3)
ax.set_yscale("log")
ax.set_xticks(xs); ax.set_xticklabels([f"{s} stops" for s in stops], fontsize=10.5)
ax.set_ylabel("Reachable states (log scale)", fontsize=11)
ax.set_title("Stage 3 — State-space explosion: \u00d726\u201340 per added stop\n"
             "(2\u20133 stops measured in PRISM; 4\u20135 stops extrapolated as ranges:\n"
             "low = structural ratio 21\u00b7(k+1)/k, high = observed \u00d740)", fontsize=10.5)

for xi,v,lab,m in zip(xs,values,labels,is_meas):
    ax.text(xi, v*2.0, lab, ha='center', fontsize=9.5,
            color="#2E5496" if m else "#666666",
            fontweight='bold' if m else 'normal')
for i,f in enumerate(factors):
    ax.annotate("", xy=(i+1, values[i+1]), xytext=(i, values[i]),
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.3))
    ax.text(i+0.5, np.sqrt(values[i]*values[i+1])*2.0, f,
            ha='center', fontsize=8.8, color="#C0392B", fontweight='bold')

ax.legend(handles=[Patch(color="#2E5496", label="measured (PRISM)"),
                   Patch(color="#B0B7C6", label="extrapolated (range)")],
          fontsize=9.5, loc="upper left")
ax.set_ylim(1e3, 3e10)
ax.text(1.5, 5e9, "exact model checking\nbecomes untenable \u2192 SMC",
        ha='center', fontsize=9.5, color="#555555",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FBEAEA", ec="#C0392B", alpha=0.8))
fig.tight_layout()
fig.savefig("scalability_growth.png", dpi=150, bbox_inches="tight")
print("saved scalability_growth.png")
print(f"4-stop range: {lo4:,.0f} .. {hi4:,.0f};  5-stop range: {lo5:,.0f} .. {hi5:,.0f}")
