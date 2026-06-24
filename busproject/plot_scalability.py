"""
Stage-3 scalability: state space grows ~x40 per added stop.
Data: PRISM reachable state counts (2-stop ~5,300; 3-stop 213,003);
4- and 5-stop are extrapolations (x40 per stop) -- not built.
Produces scalability_growth.png
"""
import numpy as np
import matplotlib.pyplot as plt

stops      = [2, 3, 4, 5]
states     = [5292, 213003, 213003*40, 213003*40*40]  # 4,5 = extrapolated
measured   = [True, True, False, False]

fig,ax=plt.subplots(figsize=(8,4.8))
xs=np.arange(len(stops))
colors=["#2E5496" if m else "#B0B7C6" for m in measured]
bars=ax.bar(xs, states, width=0.55, color=colors)
ax.set_yscale("log")
ax.set_xticks(xs); ax.set_xticklabels([f"{s} stops" for s in stops], fontsize=10.5)
ax.set_ylabel("Reachable states (log scale)", fontsize=11)
ax.set_title("Stage 3 — State-space explosion: ~×40 per added stop\n"
             "(2–3 stops measured in PRISM; 4–5 stops extrapolated)", fontsize=11.5)

labels=["5,292","213,003","~8.5 million","~340 million"]
for xi,v,lab,m in zip(xs,states,labels,measured):
    ax.text(xi, v*1.4, lab, ha='center', fontsize=10,
            color="#2E5496" if m else "#777777",
            fontweight='bold' if m else 'normal')
# arrows showing x40
for i in range(len(stops)-1):
    ax.annotate("", xy=(i+1, states[i+1]), xytext=(i, states[i]),
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.3))
    ax.text(i+0.5, np.sqrt(states[i]*states[i+1])*1.6, "×40",
            ha='center', fontsize=10, color="#C0392B", fontweight='bold')

# legend for measured vs extrapolated
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#2E5496", label="measured (PRISM)"),
                   Patch(color="#B0B7C6", label="extrapolated")],
          fontsize=9.5, loc="upper left")
ax.set_ylim(1e3, 1e10)
ax.text(1.5, 2e9, "exact model checking\nbecomes untenable → SMC",
        ha='center', fontsize=9.5, color="#555555",
        bbox=dict(boxstyle="round,pad=0.3", fc="#FBEAEA", ec="#C0392B", alpha=0.8))
fig.tight_layout()
fig.savefig("scalability_growth.png", dpi=150, bbox_inches="tight")
print("saved scalability_growth.png")
