"""
plot_prism_studies.py -- publication-quality replots of the five PRISM
parameter studies (fig2-fig5 + the A0 sweep), from the CSVs exported by
PRISM Experiments. The DATA is untouched PRISM output; only the rendering
is redone (the PRISM GUI export shows "New Series" legends and bare
variable names, inconsistent with the project's matplotlib figures).

ANALYTICAL OVERLAYS (fig2-fig4): with the default A0 = 8 < Cap = 10 the
capacity constraint never binds (`ahead` only decreases in the tagged
model), so the tagged passenger's fate is a race between their own renege
(rate theta) and the FIRST bus (rate mu). Closed forms follow:
    P(served <= T) = mu/(mu+theta) * (1 - exp(-(mu+theta) T))
    P(timeout)     = theta/(theta+mu)
    E[resolution]  = 1/(theta+mu)
The PRISM results reproduce these exactly -- plotted as dashed lines, they
are a free analytical sanity check of the model-checking pipeline.

fig5: the Cap >= 10 curves are IDENTICAL by construction (capacity above
A0+1 never binds), so they are drawn as ONE line and labelled as such.

Run from the project root:  python plot_prism_studies.py
It looks for each CSV first in the current folder, then in the matching
fig*/ subfolder. Outputs fig2_replot.png ... fig5_replot.png, A0_replot.png.
"""
import os
import csv
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, RED, GREY = "#2E5496", "#C0392B", "#777777"
T_DEADLINE = 15.0          # minutes (the headline property's deadline)
THETA_DEFAULT = 0.03       # used in fig2/fig4/fig5 sweeps
MU_DEFAULT = 0.22          # used in fig3 and the A0 sweep
CAP_DEFAULT = 10


def find(name):
    """Locate a data file: current dir, then the matching fig*/ subfolder."""
    if os.path.isfile(name):
        return name
    stem = name.split(".")[0]
    cand = os.path.join(stem, name)
    if os.path.isfile(cand):
        return cand
    # A0_data lives in A0_verify/ in the repo layout
    cand = os.path.join("A0_verify", name)
    if os.path.isfile(cand):
        return cand
    raise FileNotFoundError(name)


def read_csv(name, cols):
    with open(find(name)) as f:
        rows = list(csv.DictReader(f))
    return [np.array([float(r[c]) for r in rows]) for c in cols]


def style(ax, xlab, ylab, title):
    ax.set_xlabel(xlab, fontsize=11)
    ax.set_ylabel(ylab, fontsize=11)
    ax.set_title(title, fontsize=11.5)
    ax.grid(alpha=0.3)


# ---- fig2: reliability vs frequency -----------------------------------------
mu, p = read_csv("fig2_reliability_vs_frequency.csv", ["mu_bus", "Result"])
fig, ax = plt.subplots(figsize=(7.6, 4.4))
mu_f = np.linspace(mu.min(), mu.max(), 300)
cf = mu_f/(mu_f+THETA_DEFAULT)*(1-np.exp(-(mu_f+THETA_DEFAULT)*T_DEADLINE))
ax.plot(mu_f, cf, "--", color=RED, lw=1.6,
        label=r"closed form  $\frac{\mu}{\mu+\theta}(1-e^{-(\mu+\theta)T})$")
ax.plot(mu, p, "o", color=BLUE, ms=6, label="PRISM  P=? [F<=15 \"served\"]")
ax.axhline(0.95, color=GREY, ls=":", lw=1.2)
ax.text(mu.min(), 0.953, "SLA 0.95", fontsize=8.5, color=GREY)
style(ax, r"bus arrival rate $\mu_{bus}$ (per minute)",
      "P(served within 15 min)",
      "Reliability vs bus frequency  (tagged CTMC, A0=8, Cap=10, "
      r"$\theta$=0.03)")
secax = ax.secondary_xaxis("top", functions=(lambda x: 1/np.maximum(x, 1e-6),
                                             lambda x: 1/np.maximum(x, 1e-6)))
secax.set_xlabel("headway (min)", fontsize=10)
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig("fig2_replot.png", dpi=150, bbox_inches="tight")
print("saved fig2_replot.png")

# ---- fig3: timeout vs patience ----------------------------------------------
th, pt = read_csv("fig3_timeout_vs_patience.csv", ["theta", "Result"])
fig, ax = plt.subplots(figsize=(7.6, 4.4))
th_f = np.linspace(th.min(), th.max(), 300)
ax.plot(th_f, th_f/(th_f+MU_DEFAULT), "--", color=RED, lw=1.6,
        label=r"closed form  $\theta/(\theta+\mu)$")
ax.plot(th, pt, "o", color=BLUE, ms=6, label="PRISM  P=? [F \"timeout\"]")
style(ax, r"reneging rate $\theta$ (per minute)   [mean patience $1/\theta$]",
      "P(passenger gives up before boarding)",
      r"Timeout probability vs passenger patience  ($\mu_{bus}$=0.22, A0=8, Cap=10)")
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig("fig3_replot.png", dpi=150, bbox_inches="tight")
print("saved fig3_replot.png")

# ---- fig4: expected wait vs frequency ---------------------------------------
mu4, w4 = read_csv("fig4_waiting_vs_frequency.csv", ["mu_bus", "Result"])
fig, ax = plt.subplots(figsize=(7.6, 4.4))
mu_f = np.linspace(mu4.min(), mu4.max(), 300)
ax.plot(mu_f, 1/(mu_f+THETA_DEFAULT), "--", color=RED, lw=1.6,
        label=r"closed form  $1/(\mu+\theta)$")
ax.plot(mu4, w4, "o", color=BLUE, ms=6,
        label="PRISM  R{\"wait\"}=? [F \"done\"]")
style(ax, r"bus arrival rate $\mu_{bus}$ (per minute)",
      "Expected time to resolution (min)",
      r"Expected waiting time vs bus frequency  (A0=8, Cap=10, $\theta$=0.03)")
secax = ax.secondary_xaxis("top", functions=(lambda x: 1/np.maximum(x, 1e-6),
                                             lambda x: 1/np.maximum(x, 1e-6)))
secax.set_xlabel("headway (min)", fontsize=10)
ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig("fig4_replot.png", dpi=150, bbox_inches="tight")
print("saved fig4_replot.png")

# ---- fig5: reliability, frequency x capacity --------------------------------
mu5, cap5, p5 = read_csv("fig5_reliability_freq_x_capacity.csv",
                         ["mu_bus", "Cap", "Result"])
fig, ax = plt.subplots(figsize=(7.8, 4.6))
colors = {4: "#8B1E3F", 6: "#C0392B", 8: "#E67E22"}
for c in (4, 6, 8):
    sel = cap5 == c
    ax.plot(mu5[sel], p5[sel], "o-", ms=5, lw=1.6, color=colors[c],
            label=f"Cap = {c}")
# Cap >= 10 are identical by construction -> one line
sel10 = cap5 == 10
ax.plot(mu5[sel10], p5[sel10], "s-", ms=6, lw=2.2, color=BLUE,
        label="Cap \u2265 10  (identical: capacity never binds for A0=8)")
# verify the coincidence numerically rather than assume it
for c in (12, 14, 16):
    assert np.allclose(p5[cap5 == c], p5[sel10]), f"Cap={c} differs from Cap=10"
style(ax, r"bus arrival rate $\mu_{bus}$ (per minute)",
      "P(served within 15 min)",
      r"Reliability vs frequency and bus capacity  (A0=8, $\theta$=0.03)")
ax.legend(fontsize=9, loc="lower right", title="bus capacity", title_fontsize=9)
fig.tight_layout(); fig.savefig("fig5_replot.png", dpi=150, bbox_inches="tight")
print("saved fig5_replot.png  (Cap=12/14/16 == Cap=10 verified numerically)")

# ---- A0 sweep ----------------------------------------------------------------
a0s, pa = [], []
with open(find("A0_data")) as f:
    for line in f:
        m = re.search(r"A0=(\d+)\):\s*([0-9.]+)", line)
        if m:
            a0s.append(int(m.group(1))); pa.append(float(m.group(2)))
a0s = np.array(a0s); pa = np.array(pa)
fig, ax = plt.subplots(figsize=(7.6, 4.4))
ax.plot(a0s, pa, "o-", color=BLUE, ms=6, lw=1.8,
        label="PRISM  P=? [F<=15 \"served\"]")
ax.axvline(CAP_DEFAULT - 0.5, color=RED, ls="--", lw=1.3)
ax.text(CAP_DEFAULT - 0.2, pa.min() + 0.005,
        "A0 = Cap:\nfirst bus no longer\nguarantees a seat",
        fontsize=8.5, color=RED)
ax.annotate("flat: A0 < Cap \u21d2 one bus always suffices\n"
            r"(value = closed form $\frac{\mu}{\mu+\theta}(1-e^{-(\mu+\theta)T})$ = 0.859)",
            xy=(4, pa[0]), xytext=(1.0, pa[0] - 0.055),
            fontsize=8.5, color=GREY,
            arrowprops=dict(arrowstyle="->", color=GREY, lw=1))
style(ax, "A0  (passengers ahead when the tagged passenger arrives)",
      "P(served within 15 min)",
      r"Reliability vs initial queue position  ($\mu_{bus}$=0.22, Cap=10, $\theta$=0.03)")
ax.set_ylim(pa.min() - 0.08, pa.max() + 0.03)
ax.legend(fontsize=9, loc="lower left")
fig.tight_layout(); fig.savefig("A0_replot.png", dpi=150, bbox_inches="tight")
print("saved A0_replot.png")
