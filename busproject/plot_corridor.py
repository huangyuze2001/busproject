"""
Stage-2 corridor: mean queue and P(full) growing downstream.
Data: PRISM steady-state results, corridor_2stop.sm / corridor_3stop.sm
(identical demand at every stop; differences are purely from coupling).
Produces corridor_results.png
"""
import numpy as np
import matplotlib.pyplot as plt

stops3 = ["Stop 1\n(upstream)","Stop 2","Stop 3\n(downstream)"]
L3   = [6.64, 16.98, 19.42]      # mean queue, 3-stop corridor
pf3  = [0.017, 0.373, 0.631]     # P(full), 3-stop corridor
L2   = [4.64, 11.23]             # 2-stop corridor (for context)

fig,(axA,axB)=plt.subplots(1,2,figsize=(11,4.6))

# --- left: mean queue along the corridor (2- vs 3-stop) ---
x3=np.arange(3)
axA.bar(x3-0.0, L3, width=0.5, color="#2E5496", alpha=0.88, label="3-stop corridor")
for xi,v in zip(x3,L3): axA.text(xi, v+0.4, f"{v:.1f}", ha='center', fontsize=10, color="#2E5496")
# overlay 2-stop as outlined bars on first two positions
axA.bar([0,1], L2, width=0.5, facecolor='none', edgecolor="#C0392B",
        linewidth=2, linestyle='--', label="2-stop corridor")
for xi,v in zip([0,1],L2): axA.text(xi, v+0.4, f"{v:.1f}", ha='center', fontsize=9, color="#C0392B")
axA.set_xticks(x3); axA.set_xticklabels(stops3, fontsize=10)
axA.set_ylabel("Mean queue length (passengers)", fontsize=11)
axA.set_ylim(0,22)
axA.set_title("Coupling accumulates: queues grow downstream", fontsize=11.5)
axA.legend(fontsize=9.5, loc="upper left")
axA.axhline(20, color="#999999", linestyle=":", linewidth=1)
axA.text(2.35, 20.2, "capacity K=20", fontsize=8, color="#999999", ha='right')

# --- right: P(full) escalating ---
axB.bar(x3, pf3, width=0.5, color="#C0392B", alpha=0.85)
for xi,v in zip(x3,pf3): axB.text(xi, v+0.015, f"{v:.0%}", ha='center', fontsize=10, color="#C0392B")
axB.set_xticks(x3); axB.set_xticklabels(stops3, fontsize=10)
axB.set_ylabel("P(full)", fontsize=11); axB.set_ylim(0,0.75)
axB.set_title("Downstream stop is starved into saturation", fontsize=11.5)

fig.suptitle("Stage 2 — Corridor coupling (identical demand at every stop)", fontsize=12.5, y=1.02)
fig.tight_layout()
fig.savefig("corridor_results.png", dpi=150, bbox_inches="tight")
print("saved corridor_results.png")
