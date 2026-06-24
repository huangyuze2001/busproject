# Probabilistic Model Checking of a Bus-Stop Digital Twin

A formally-analysable model of bus-stop passenger waiting time and service
reliability, analysed with probabilistic model checking (PRISM) and wrapped in
a data-driven digital-twin loop. The project runs in three stages plus a
real-data case study, and every synthetic result is cross-validated by an
independent method.

```
Stage 1  single stop        -- CTMC reliability/waiting + MDP dispatch control
Stage 2  corridor           -- shared-bus coupling across 2 and 3 stops
Stage 3  scalability        -- state-space growth -> statistical model checking
Real-data case study        -- time-dependent service rate from a real timetable
```

All parameters in Stages 1-2 are SYNTHETIC by design (chosen to exercise and
*validate* the models, with known ground truth so cross-validation is possible).
Real-data calibration is introduced in the case study and is the next stage.

---

## Project layout

```
busproject/
├── 1stop/                     Stage 1 - single-stop models
│   ├── bus_stop_tagged.sm     CTMC: per-passenger reliability / waiting / timeout
│   ├── tagged.props           CSL properties for the tagged model
│   ├── bus_stop_aggregate.sm  CTMC: mean queue, throughput, P(full)
│   ├── aggregate.props        CSL properties for the aggregate model
│   ├── bus_stop_mdp.nm        MDP: best vs worst dispatch policy (hold vs depart)
│   └── mdp.props              PCTL properties + strategy export
├── 2stop/                     Stage 2 - 2-stop corridor
│   ├── corridor_2stop.sm      CTMC: shared-bus coupling (downstream starved)
│   └── corridor.props         CSL: mean queue / throughput / P(full) per stop
├── 3stop/                     Stage 2 - 3-stop corridor
│   ├── corridor_3stop.sm      CTMC: coupling accumulates downstream
│   └── corridor_3stop.props   CSL: per-stop queues and saturation
├── real_data/                 Real-data case study
│   ├── real_data_case.py      real route-77 timetable -> time-dependent mu_bus -> reliability
│   ├── plot_real_data.py      plots the time-of-day reliability / wait
│   └── real_data_reliability.png
├── A0verify/                  fig 1 data (reliability vs queue position)
├── fig2_reliability_vs_frequency/
├── fig3_timeout_vs_patience/
├── fig4_waiting_vs_frequency/
├── fig5_reliability_freq_x_capacity/
├── dt_loop.py                 Stage-1 digital-twin loop + validation engine
├── dt_reliability_curve.png   reliability vs frequency, with SLA + recommendation
├── corridor_simulate.py       corridor: discrete-event simulation vs PRISM (strong check)
├── corridor_results.png       corridor: queues and P(full) growing downstream
├── plot_corridor.py           generates corridor_results.png
├── scalability_growth.png     state-space growth (~x40 per stop) -> SMC
├── plot_scalability.py        generates scalability_growth.png
└── README.md
```

> Note: an independent numerical cross-validation of the corridor models is also
> available (`corridor_verify.py`); if not present in your tree it can be
> regenerated. The discrete-event check (`corridor_simulate.py`) is the stronger,
> independent-paradigm validation and is included here.

---

## Canonical parameters

Single stop: `lambda=2.0`, `mu_bus=0.22`, `theta=0.03`, `Cap=10`, `K=30`.
Corridor:    `lambda=1.6` (each stop), `mu_bus=0.5`, `mu_travel=0.6`,
`theta=0.03`, `Cap=10`, `K=20`.

---

## How to run

### PRISM (install from prismmodelchecker.org)

Open each model in the PRISM GUI: **Open Model** -> **Build Model** ->
**Open Properties List** -> select the `.props` -> **Verify**. The parameter
sweeps for the Stage-1 figures were produced with **Properties -> New
Experiment**, varying one constant (e.g. `mu_bus`, `Cap`, `theta`, `A0`).

```
1stop/bus_stop_tagged.sm     + 1stop/tagged.props
1stop/bus_stop_aggregate.sm  + 1stop/aggregate.props
1stop/bus_stop_mdp.nm        + 1stop/mdp.props
2stop/corridor_2stop.sm      + 2stop/corridor.props
3stop/corridor_3stop.sm      + 3stop/corridor_3stop.props
```

### Python (no PRISM needed)

```bash
python3 dt_loop.py                  # Stage-1 digital-twin loop + validation
python3 corridor_simulate.py        # corridor: discrete-event simulation vs PRISM
python3 real_data/real_data_case.py # real timetable -> time-of-day reliability
python3 real_data/plot_real_data.py # plot for the real-data case
python3 plot_corridor.py            # regenerate the corridor figure
python3 plot_scalability.py         # regenerate the scalability figure
```

Python deps: `numpy`, `scipy` (corridor solves), `matplotlib` (plots).

---

## The modelling decisions (defend these in the viva)

**1. CTMC and MDP are PARALLEL models of the same stop, not layered.** The two
CTMCs answer reliability/waiting questions; the MDP is a *separate* model used
to study control. The MDP is discrete-time on purpose (PRISM's `mdp` is
discrete-time and control decisions are made at discrete epochs); passenger
arrivals are continuous-time Poisson, so the reliability models are CTMCs
(exponential rates + CSL), avoiding DTMC discretisation artefacts.

**1b. Parameter coherence.** All three single-stop models share one parameter
set. The MDP's per-slot probabilities are DERIVED from the CTMC rates via
`p = 1 - exp(-rate*dt)`, so it describes the *same* system.

**2. A "tagged passenger" model for per-passenger properties.** Under FIFO bulk
service only the passengers *ahead* affect boarding, keeping the state space
tiny (`ahead x tag`).

**3. The reward trap.** `R=? [ F "served" ]` returns +infinity (reneging paths
never reach `served`). Target an absorbing condition reached w.p. 1, e.g.
`R{"wait"}=? [ F "done" ]` with `done = served | timeout`.

**4. Corridor coupling (Stage 2).** A single bus traverses the corridor: it
boards up to `Cap` at stop 1, then travels carrying that load, so it reaches
stop 2 with only the LEFTOVER seats (`seats = Cap - boarded upstream`). Heavy
demand upstream starves downstream stops. With identical demand at every stop,
any downstream disadvantage is therefore due PURELY to coupling -- a controlled
experiment that needs synthetic (equal) parameters. One bus is in the corridor
at a time. The 3-stop file repeats the pattern with a second travel leg.

---

## Validation (every synthetic result cross-validated)

| stage | independent check | result |
|-------|-------------------|--------|
| Single stop | DES simulation vs analytic CTMC | P(served<=15): 0.749 vs 0.756 (gap 0.008) |
| Single stop | aggregate+Little vs tagged vs DES | mean wait 7.15 / 6.23 / 6.13 min |
| Corridor 2-stop | discrete-event simulation vs PRISM | queue1 4.64, queue2 11.23 (match) |
| Corridor 3-stop | discrete-event simulation vs PRISM | queues 6.64 / 16.98 / 19.42 (match) |

The corridor discrete-event simulation (`corridor_simulate.py`) is a genuinely
DIFFERENT paradigm from PRISM (random sampling vs equation-solving), so its
agreement is strong evidence the model is correct, not merely correctly
implemented. PRISM reference values embedded in the script were obtained by
independent Verify runs in PRISM 4.10.1 (steady-state queue lengths and P(full)
for both corridors).

The real-data case study is not separately cross-validated: it reuses the
already-validated single-stop model and only substitutes a real, timetable-derived
service rate.

---

## The digital-twin loop

```
PHYSICAL (real timetable or DES)
   -> ESTIMATOR (service rate mu_bus; with a real timetable, time-dependent)
      -> CTMC MODEL rebuilt from the estimate
         -> VERIFY reliability against the SLA (>= 0.95)
            -> DECISION: adjust frequency to restore the SLA; feed back.
```

With synthetic data this is a proof-of-concept loop. The real-data case study
replaces the physical layer with the real First Glasgow route-77 timetable at
Partick Bus Station (Tue 23 June 2026; bustimes.org / Traveline National Dataset)
and extracts a TIME-DEPENDENT service rate. The loop is currently
one-directional and offline; a real-time, two-way twin (e.g. via BODS GTFS-RT)
is future work.

---

## Key results

- **Single stop:** reliability P(served<=15)=0.749; frequency is the dominant
  lever (diminishing returns); capacity matters only at low frequency; MDP
  control value ~2.6x but the always-depart baseline is within ~11% of optimal.
- **Corridor:** identical demand, yet downstream queues are ~2.4x upstream
  (2 stops) and saturate by stop 3 (P(full) 1.7% -> 37% -> 63%).
- **Scalability:** reachable states 5,292 (2 stops) -> 213,003 (3 stops),
  ~x40 per stop; exact model checking is untenable beyond a few stops ->
  statistical model checking (SMC) is the route forward (Stage 3, write-only).
- **Real data:** route-77 service at Partick is hourly overnight and ~15 min by
  day, so the derived P(bus within 15 min) rises from ~0.22 overnight to ~0.64
  in the daytime, tracking the real, time-dependent service.

---

## Limitations and future work

State-space explosion bounds exact PMC (Stage 3); the route forward is SMC
(discussed, not implemented). The digital-twin loop is one-directional and
offline. Real data so far calibrates a single stop's service rate (not passenger
demand, which timetables lack) and not yet a real corridor. Future work:
real-corridor calibration (travel times from adjacent-stop timetable
differences), passenger-demand data, a real-time twin via BODS GTFS-RT, an SMC
implementation, and MDP dispatch control on the corridor.
