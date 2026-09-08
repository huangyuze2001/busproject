# Probabilistic Model Checking of a Bus-Stop Digital Twin

Passenger waiting time and service reliability of an urban bus stop, analysed
with **probabilistic model checking** in [PRISM](https://www.prismmodelchecker.org/),
cross-validated with independent Python simulations, and extended to a corridor
of stops, a published timetable, a schedule-replay monitor, and a digital-twin
loop.

MSc dissertation project. Models are written for PRISM 4.10.1; all Python
scripts use only `numpy`, `scipy`, and `matplotlib`.

---

## Overview

The bus stop is modelled as a probabilistic system with Poisson passenger
arrivals, capacity-limited buses, and passengers who abandon (renege) after
waiting too long. Three complementary models are built and checked:

- a **tagged-passenger CTMC** for per-passenger reliability and waiting time;
- an **aggregate CTMC** for system-level steady-state metrics;
- a **Markov decision process (MDP)** for dispatch control.

The single-stop model is then extended along three stages:

1. **Single stop** — reliability, waiting, and dispatch control (Stages 1).
2. **Corridor** — 2- and 3-stop models served by a shared bus, quantifying
   inter-stop coupling (Stage 2).
3. **Scalability** — how the reachable state space grows per added stop, and the
   point at which exact model checking must give way to statistical methods
   (Stage 3, discussed).

On top of these, the project adds a **real-timetable case study**, a
**runtime-verification (RV) monitor**, and a **digital-twin loop** that estimates
parameters from data, verifies a service-level agreement (SLA), and recommends a
control action.

Every synthetic result is cross-validated against at least one independent
method (exact equation-solving vs Monte-Carlo simulation).

---

## Repository structure

```
busproject/
├── 1stop/                          # single-stop PRISM models (Stage 1)
│   ├── bus_stop_tagged.sm              tagged-passenger CTMC
│   ├── tagged.props
│   ├── bus_stop_aggregate.sm           aggregate CTMC
│   ├── aggregate.props
│   ├── bus_stop_mdp.nm                 dispatch-control MDP
│   └── mdp.props
├── 2stop/                          # 2-stop corridor (Stage 2)
│   ├── corridor_2stop.sm
│   └── corridor.props
├── 3stop/                          # 3-stop corridor (Stage 2)
│   ├── corridor_3stop.sm
│   └── corridor_3stop.props
├── A0_verify/                      # baseline / verification artifacts
├── fig2_reliability_vs_frequency/  # single-stop parameter studies (PRISM experiments)
├── fig3_timeout_vs_patience/
├── fig4_waiting_vs_frequency/
├── fig5_reliability_freq_x_capacity/
├── real_data/                      # published-timetable case study, schedule replay, twin proof of concept
│   ├── route77_data.py                shared real timetable  (SINGLE SOURCE OF TRUTH)
│   ├── real_data_case.py              time-of-day reliability table
│   ├── plot_real_data.py              time-of-day reliability figure
│   ├── rv_monitor.py                  schedule-replay monitor + figure
│   ├── dt_loop.py                     digital-twin loop (synthetic + real modes)
│   └── stop_model.py                  shared aggregate-CTMC solver  (SINGLE SOURCE OF TRUTH)
├── corridor_params.py              shared corridor params + PRISM reference  (SINGLE SOURCE OF TRUTH)
├── corridor_simulate.py            corridor DES vs PRISM cross-validation
├── plot_corridor.py                corridor results figure
├── plot_scalability.py             scalability growth figure
├── plot_prism_studies.py           replots of the PRISM parameter studies (fig2-5, A0)
├── plot_mdp_policies.py            Figure 5.6: MDP dispatch-policy comparison
├── scalability_growth.png
├── check_params_sync.py            asserts .sm constants == corridor_params.py (runs first)
├── experiments/                    validation/sensitivity scripts
├── results/revision/               generated review-experiment CSVs and figures
├── run_revision_experiments.py     one-command experiments
├── run_all.py                      one-command reproduction of baseline Python scripts
└── README.md
```

Two **shared modules** act as single sources of truth so that data and
parameters are edited in exactly one place:

- `real_data/route77_data.py` — the real departure timetable, imported by
  `real_data_case.py`, `plot_real_data.py`, `rv_monitor.py`, and `dt_loop.py`.
- `corridor_params.py` — the corridor model parameters **and** the PRISM-verified
  reference values, imported by `corridor_simulate.py`. The parameter values here
  must match the constants in `2stop/` and `3stop/` `.sm` files — a requirement
  that is now enforced automatically: `check_params_sync.py` parses the `.sm`
  declarations and fails loudly on any mismatch (it runs first in `run_all.py`).
- `real_data/stop_model.py` — the aggregate single-stop CTMC solver (with the
  reneging-aware Little's-law components) **and** the shared six-band day
  partition (`BANDS`), imported by `real_data_case.py` and `plot_real_data.py`.

---

## Requirements

- **PRISM 4.10.1** (for the model-checking side; GUI used for Verify/Experiments).
- **Python 3.9+** with `numpy`, `scipy`, `matplotlib`:

  ```bash
  pip install numpy scipy matplotlib
  ```

---

## How to reproduce

### PRISM side (model checking)

Open the relevant `.sm` / `.nm` model and its `.props` in the PRISM GUI, build,
and **Verify** (or run the parameter studies under **Experiments** for the
`fig*` studies). The verified corridor results are recorded in
`corridor_params.py` so the Python cross-validation can check against them.

### Python side (validation, real data, figures)

From the project root:

```bash
python run_all.py
```

This runs every standalone Python script in order, each from its own folder, and
prints a PASS/FAIL summary. To run a single component instead:

```bash
cd real_data && python dt_loop.py        # digital-twin loop (synthetic + real)
cd real_data && python rv_monitor.py     # schedule-replay monitor
python corridor_simulate.py              # corridor DES vs PRISM
```

> Note: `corridor_simulate.py` uses a long simulated horizon (`SIM_T = 2,000,000`)
> for low Monte-Carlo noise, so the 3-stop run takes a little while.

---

## Components

**Single stop (`1stop/`).** The tagged CTMC answers `P=? [F<=T tagged_served]`
and `R{"wait"}=? [F done]`; the aggregate CTMC gives steady-state queue and
throughput; the MDP optimises dispatch. Parameter studies (`fig2`–`fig5`)
sweep frequency, patience, and capacity.

**Corridor (`2stop/`, `3stop/`, `corridor_simulate.py`).** A shared bus serves
stops in sequence. `corridor_simulate.py` is an **independent** discrete-event
(Monte-Carlo) simulation that builds no matrix; agreement with the exact
PRISM results is therefore a strong cross-validation. It now imports parameters
and PRISM reference values from `corridor_params.py` and **auto-checks** each
property (gap + PASS/CHECK).

**Timetable-calibrated case study (`real_data/real_data_case.py`, `plot_real_data.py`).**
Estimates a time-of-day-dependent scheduled service rate from the published route-77 timetable.
This is a schedule-driven proof of concept, not an analysis of realised vehicle trajectories.

**Schedule-replay monitor (`real_data/rv_monitor.py`).** Replays scheduled departure
events from one published timetable day. After each event it re-estimates the Poisson
service-rate benchmark from the **four most recent scheduled headway gaps** and re-checks
an illustrative bus-arrival threshold of 0.50. It does not monitor realised disruption,
punctuality or live operational performance.

**PRISM parameter-study replots (`plot_prism_studies.py`).** Re-renders the
five PRISM Experiments figures (fig2–fig5 and the A0 sweep) from the exported
CSVs in a style consistent with the other project figures. Overlays the
closed-form solutions on fig2–fig4 (with A0 < Cap the capacity constraint never
binds, so the tagged model admits closed forms; PRISM reproduces them to
numerical precision, max deviation < 1e-7) and collapses the identical
Cap ≥ 10 curves of fig5 into one labelled line (verified by assertion).

**MDP policy figure (`plot_mdp_policies.py`).** Renders the dispatch-policy
comparison (Figure 5.6) from the PRISM-verified MDP results — optimal (Rmin),
fixed always-depart (hold action removed), and worst (Rmax) — in
person-minutes, annotating the ~2.6× value of control and the ~10% benefit of
holding at a single stop. Provenance of the three values is recorded in the
script's docstring.

**Digital-twin loop (`real_data/dt_loop.py`).** Runs the closed loop
`data → estimate → verify → decide` in two modes:

- *Synthetic* — known-truth simulation; the exact CTMC solve is cross-checked
  against the simulation (this is the model-validation backbone). Estimates
  λ and θ; the bus rate is a control variable. After the control search, the
  recommendation is **actuated in silico** and the loop closed: re-simulate
  under μ\*, re-estimate, re-verify (post-actuation reliability 0.970 vs the
  conservative pre-actuation prediction 0.950).
- *Timetable* — ingests the published route-77 schedule, estimates a scheduled
  service-rate parameter and computes a model-implied frequency threshold under
  assumed passenger demand and patience. It is not an operational recommendation.

---

## Data provenance

Real timetable: **First Glasgow route 77**, **Partick Bus Station (stance 1)**,
towards Glasgow Airport. Source: [bustimes.org](https://bustimes.org/) (timetable
data from the Traveline National Dataset, TNDS), for **Tuesday 23 June 2026**.
Departure times were manually verified against the operator timetable and are
stored in `real_data/route77_data.py`.

A timetable gives the **bus service rate**, not passenger demand, so passenger
arrival and patience parameters remain assumed in the real-data components.

---

## Key results

| Result | Value |
|---|---|
| Single-stop replication validation | 30-run DES mean 0.7452; matched CTMC mean 0.7447; paired gap 95% CI includes 0 |
| Single-stop mean time-in-system | 6.23 min (exact) vs 6.13 min (sim) |
| MDP dispatch baseline (dt=0.25) | optimal 100.57 / always-depart 111.46 / worst 261.83 person-min |
| Corridor 2-stop | queue1 4.637, queue2 11.228, P(full2) 0.128 |
| Corridor 3-stop | queue1 6.643, queue2 16.983, queue3 19.424, P(full3) 0.631 |
| State-space growth | ≈ ×26–40 reachable states per added stop (×40.3 measured 2→3; structural ratio 21·(k+1)/k) |
| Published route-77 daytime headway | ≈ 14 min (μ ≈ 0.069 min⁻¹) |
| Timetable-driven model threshold | schedule-derived operating point is below the illustrative model target; threshold is model-implied, not operational |
| RV monitor (illustrative target 0.50) | in ALERT from monitoring start (02:17; needs 2 gaps to estimate), cleared 07:04, raised 20:43 |

---

## Scope and honesty notes

- The **digital-twin loop is a one-directional, offline proof of concept**: it
  reads data and verifies/recommends, but does not actuate a live system.
- The **RV monitor replays** a real timetable as an event stream; connecting a
  live GTFS-RT feed is future work.
- The synthetic SLA of 0.95 within 15 minutes is **not attainable** by a real
  low-frequency route; the RV demo therefore uses an illustrative operator target
  of 0.50, while still reporting the 0.95 comparison.
- The CTMC and MDP are **parallel models of the same system**, not layered.
- Model-validation weight sits with the **synthetic** results (known ground
  truth); the real-data components demonstrate applicability, not validation.
- **Scheduled vs Poisson headways**: the timetable chapter reports two benchmark
  interpretations: a Poisson-headway calculation and a perfectly punctual schedule
  calculation `P(bus within T) = min(T/h, 1)`. They illustrate sensitivity to the
  assumed headway distribution and are **not** claimed as universal probabilistic bounds.
- **Waiting times use Little's law with reneging**: `W = L / (throughput +
  renege rate)`. Dividing by boarding throughput alone (an earlier version)
  overstates the wait — at night by ~3× (72 → 22.8 min).
- **`fig5` capacity curves coincide for Cap ≥ 10 by construction**: in the
  tagged model `ahead` never increases, so with `A0 = 8` any capacity above
  `A0+1` is never binding — the four curves are identical, not a plotting bug.
  Relatedly, with the capacity constraint inactive the tagged model admits
  closed forms (`P(timeout) = θ/(θ+μ)`, `E[wait] = 1/(θ+μ)`,
  `P(served ≤ T) = μ/(μ+θ)·(1−e^{−(μ+θ)T})`), which the `fig2`–`fig4` PRISM
  results reproduce exactly — a free analytical sanity check.
- **Simulation censoring**: passengers unresolved at the simulation horizon are
  dropped. The supervisor-review validation therefore uses long horizons and
  30 independent replications, with uncertainty reported explicitly.
- All 3-stop reference values in `corridor_params.py`, including `P(full1)` and
  `P(full2)`, are **PRISM-verified** (4.10.1, 2026-07-01) and independently
  cross-checked by the DES.


## Supervisor-review experiments

The original model files and baseline scripts are preserved. Additional scripts in
`experiments/` address the methodological and reproducibility points raised in the
supervisor review without overwriting the original experiments.

### 1. Repeated single-stop validation

```bash
python experiments/single_stop_replications.py
```

- 30 independent DES seeds (`0..29`)
- 40,000 simulated minutes per replication
- reports mean, standard deviation and 95% t confidence intervals
- pairs each DES run with an exact tagged-CTMC calculation using that run's
  arrival-seen queue-position distribution
- outputs: `results/revision/single_stop_*.csv` and `.png`

### 2. MDP discretisation sensitivity and policy regions

```bash
python experiments/mdp_dt_sensitivity.py
```

- fixed physical horizon: 20 min
- slot lengths: `dt = 0.25, 0.125, 0.0625` min
- records `P(N>=2)` for the Poisson passenger-arrival count per slot
- compares optimal, always-depart and worst expected waiting
- exports the baseline optimal hold/depart action map
- outputs: `results/revision/mdp_*.csv` and `.png`

At `dt=0.25`, `P(N>=2)` is about 0.090, so the baseline is explicitly treated as
a coarse abstraction. The absolute rewards vary with `dt`, but the relative benefit
of optimised holding over always-depart remains around 10--12% in the tested grid.

### 3. Controlled corridor experiment

```bash
python experiments/corridor_controlled_experiment.py
```

The original coupled corridor is compared with an artificial uncoupled baseline.
Both use the same one-bus cycle, demand, reneging, travel rate and platform bound;
the control variant gives each downstream stop a fresh effective boarding capacity
instead of residual seats. This isolates residual-seat depletion from cycle-length
effects within the current abstraction. Three independent 50,000-min replications are used.

### 4. Reproducibility settings

Known from the archived project:

- PRISM version: **4.10.1**
- schedule-replay moving window: **4 scheduled headway gaps**
- schedule-replay illustrative bus-arrival threshold: **0.50**
- synthetic passenger-service demonstration threshold: **0.95**


See `experiments/experiment_config.py` for the revision-experiment configuration.
