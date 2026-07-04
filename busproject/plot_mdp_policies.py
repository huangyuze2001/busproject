"""
Figure 5.6 -- MDP dispatch-policy comparison (single stop).

Data provenance: the three values are PRISM-verified results on
bus_stop_mdp.nm (PRISM 4.10.1, Verify):
  optimal  = Rmin=? [C<=NSLOTS]  (best achievable total waiting)   = 402.4
  baseline = same query with the [hold] action removed
             (fixed "always depart" rule)                          = 446.0
  worst    = Rmax=? [C<=NSLOTS]  (adversarial dispatch)            = 1047.4
Units: person-slots; multiply by dt = 0.25 to obtain person-minutes
over the 20-minute horizon. The gap worst/optimal (~2.6x) is the
"value of control"; optimal vs baseline (~10%) is the modest benefit
of clever holding at a single stop (Section 5.4).

Produces mdp_policy_comparison.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DT = 0.25
policies = ["Optimal\n(Rmin, hold allowed)",
            "Always-depart\n(baseline, no hold)",
            "Worst\n(Rmax, adversarial)"]
slots  = [402.4, 446.0, 1047.4]          # PRISM-verified, person-slots
mins   = [v * DT for v in slots]         # person-minutes
colors = ["#27ae60", "#2E5496", "#C0392B"]

fig, ax = plt.subplots(figsize=(7.8, 4.6))
xs = np.arange(3)
bars = ax.bar(xs, mins, width=0.55, color=colors, alpha=0.9)
for x, m, s in zip(xs, mins, slots):
    ax.text(x, m + 4, f"{m:.1f} person-min\n({s:.1f} slots)",
            ha="center", fontsize=9.5)

# annotate the two comparisons
ax.annotate("", xy=(2, mins[2] * 0.97), xytext=(0, mins[2] * 0.97),
            arrowprops=dict(arrowstyle="<->", color="#555555", lw=1.2))
ax.text(1, mins[2] * 0.99, "value of control \u2248 2.6\u00d7",
        ha="center", fontsize=9.5, color="#555555")
ax.annotate("", xy=(1, mins[1] + 22), xytext=(0, mins[1] + 22),
            arrowprops=dict(arrowstyle="<->", color="#777777", lw=1.0))
ax.text(0.5, mins[1] + 26, "holding saves \u2248 10%",
        ha="center", fontsize=8.8, color="#777777")

ax.set_xticks(xs); ax.set_xticklabels(policies, fontsize=10)
ax.set_ylabel("Expected total waiting over 20 min horizon\n(person-minutes)",
              fontsize=10.5)
ax.set_ylim(0, mins[2] * 1.16)
ax.set_title("Dispatch-policy comparison on the single-stop MDP\n"
             r"(PRISM Rmin / fixed rule / Rmax;  $\lambda$=2.0, $\mu_{bus}$=0.22, Cap=10)",
             fontsize=11)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig("mdp_policy_comparison.png", dpi=150, bbox_inches="tight")
print("saved mdp_policy_comparison.png")
