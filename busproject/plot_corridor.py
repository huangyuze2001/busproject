"""
Stage-2 corridor: mean queue and P(full) growing downstream.
Data: PRISM steady-state results for corridor_2stop.sm / corridor_3stop.sm,
imported from corridor_params.PRISM_REF (single source of truth, #12) --
identical demand at every stop.

ATTRIBUTION NOTE (#4): the two mechanisms in this figure are different.
  * DOWNSTREAM worsening (stop1 -> stop2 -> stop3 within one corridor) is the
    SEAT COUPLING: the shared bus arrives partially full.
  * The UPSTREAM stop also worsens when a stop is ADDED (2-stop 4.6 -> 3-stop
    6.6) -- but stop 1 never sees a partially full bus. That shift is caused
    by the ONE-BUS-IN-CORRIDOR simplification: a longer corridor means a
    longer bus cycle (one extra travel leg), i.e. a LOWER EFFECTIVE bus rate
    at stop 1 (~1/(1/mu_bus + k/mu_travel)), not seat coupling.
The figure states this explicitly so the two effects are not conflated.
Produces corridor_results.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from corridor_params import PRISM_REF

# --- data straight from the PRISM-verified reference (no hard-coding) ---
L3  = [PRISM_REF[3][f"queue{i}"]   for i in (1, 2, 3)]
pf3 = [PRISM_REF[3][f"P(full{i})"] for i in (1, 2, 3)]
L2  = [PRISM_REF[2][f"queue{i}"]   for i in (1, 2)]

stops3 = ["Stop 1\n(upstream)","Stop 2","Stop 3\n(downstream)"]

fig,(axA,axB)=plt.subplots(1,2,figsize=(11,4.9))

# --- left: mean queue along the corridor (2- vs 3-stop) ---
x3=np.arange(3)
axA.bar(x3-0.0, L3, width=0.5, color="#2E5496", alpha=0.88, label="3-stop corridor")
for xi,v in zip(x3,L3): axA.text(xi, v+0.4, f"{v:.1f}", ha='center', fontsize=10, color="#2E5496")
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

fig.suptitle("Stage 2 — Corridor coupling (identical demand at every stop)", fontsize=12.5, y=1.04)
fig.text(0.5, -0.045,
    "Two distinct effects: growth ALONG the corridor (stop 1→3) is seat coupling; "
    "the upstream shift when a stop is added (4.6→6.6 at stop 1) is the\n"
    "one-bus-in-corridor simplification — a longer cycle lowers the effective bus "
    "rate at stop 1 — not seat coupling (stop 1 never sees a partially full bus).",
    ha='center', fontsize=8.6, color="#444444")
fig.tight_layout()
fig.savefig("corridor_results.png", dpi=150, bbox_inches="tight")
print("saved corridor_results.png")
print("L3:", L3, " pf3:", pf3, " L2:", L2)
