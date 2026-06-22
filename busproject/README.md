# Probabilistic Model Checking of a Bus-Stop Digital Twin

A small, formally-analysable model of a single bus stop, analysed with
probabilistic model checking (PRISM). Three layers that cross-validate each
other:

```
   bus_stop_tagged.sm   (CTMC)  -- per-passenger reliability & waiting time
   bus_stop_aggregate.sm(CTMC)  -- system-level steady-state metrics
   bus_stop_mdp.nm      (MDP)   -- optimal dispatch/holding control
   dt_loop.py           (Py)    -- the digital-twin loop + model validation
```

## File map

| file                    | type | what it answers |
|-------------------------|------|-----------------|
| `bus_stop_tagged.sm`    | CTMC | P(served within t), P(timeout), E[waiting time] for one passenger |
| `tagged.props`          | CSL  | the properties for the tagged model |
| `bus_stop_aggregate.sm` | CTMC | mean queue length, throughput, P(full), Little's-law check |
| `aggregate.props`       | CSL  | the properties for the aggregate model |
| `bus_stop_mdp.nm`       | MDP  | best vs worst dispatch policy (hold vs depart) |
| `mdp.props`             | PCTL | optimal-policy properties + strategy export |
| `dt_loop.py`            | Py   | physical sim -> estimate -> CTMC verify -> control decision |
| `dt_reliability_curve.png` | fig | reliability vs bus frequency, with SLA and recommendation |

## How to run

PRISM (install from prismmodelchecker.org), then:

```bash
# per-passenger reliability
prism bus_stop_tagged.sm tagged.props

# sensitivity experiment: vary bus frequency and plot P(served within 15)
prism bus_stop_tagged.sm tagged.props -prop 1 -const mu_bus=0.10:0.05:0.60

# vary the queue a passenger arrives into
prism bus_stop_tagged.sm tagged.props -prop 1 -const A0=0:2:20

# system-level steady-state metrics
prism bus_stop_aggregate.sm aggregate.props

# optimal dispatch policy + export the strategy
prism bus_stop_mdp.nm mdp.props -prop 1 -exportstrat strat.txt
```

The digital-twin loop and the model-validation check (no PRISM needed):

```bash
python3 dt_loop.py        # prints validation table, writes dt_reliability_curve.png
```

## The modelling decisions (defend these in your viva)

**1. CTMC and MDP are PARALLEL models of the same stop, not layered.** The
two CTMCs answer reliability/waiting questions; the MDP is a *separate*
model used to study control. The MDP is discrete-time *on purpose*: PRISM's
`mdp` is discrete-time, and control decisions are naturally made at discrete
epochs. Passenger arrivals are a continuous-time Poisson process, so the
base/reliability models are CTMCs (exponential rates + CSL), which avoids
the time-discretisation artefacts of a DTMC.

**1b. Parameter coherence (same system, one parameter set).** All three
models share the canonical rates `lambda`, `mu_bus`, `theta`, `C`, `K`. The
discrete-time MDP does NOT use independent numbers: its per-slot
probabilities are DERIVED from those rates via `p = 1 - exp(-rate*dt)`
(`p_arr`, `p_bus`) and `theta*dt` (reneging), with slot length `dt` small
enough that one-event-per-slot is a good approximation. The MDP also
includes reneging, so it describes the *same* system the CTMC does.

**2. A "tagged passenger" model for per-passenger properties.** Questions
like "P(served within 15 min)" and "expected waiting time" are about one
passenger's experience, not an aggregate. `bus_stop_tagged.sm` follows a
single passenger; because boarding is FIFO bulk service, only the
passengers *ahead* of the tagged one affect whether they get a seat, which
keeps the state space tiny (`ahead x tag`).

**3. The reward trap.** `R=? [ F "served" ]` returns +infinity, because
some passengers renege and those paths never reach `served`. Always target
an absorbing condition reached with probability 1, e.g.
`R{"wait"}=? [ F "done" ]` where `done = served | timeout`.

## Model validation (your results chapter needs this)

`dt_loop.py` runs a discrete-event simulation (DES) with known true
parameters and compares it against the analytic CTMC solution that mirrors
`bus_stop_tagged.sm`. Example output:

```
CTMC P=? [F<=15 served] = 0.749   (DES gave 0.756)
CTMC R(wait)=? [F done] = 6.23 min (DES gave 6.13)
validation gap |CTMC-DES| = 0.008  (PASS)
```

Three independent routes to the same numbers (aggregate CTMC via Little's
law, tagged CTMC, and DES) is strong evidence the formal model is faithful.
Because buses give *bulk* service this is not a textbook M/M/c queue, so we
validate sim-vs-analytic rather than against an M/M/c closed form; setting
`Cap=1` recovers an M/M/1-like sub-case you can check against Little's law
analytically.

## The digital-twin loop

This is what earns the "digital twin" label rather than just "a model":

```
PHYSICAL (DES, true params)
   -> ESTIMATOR (MLE of lambda, theta, arrival-seen queue distribution)
      -> CTMC MODEL rebuilt from the estimates
         -> VERIFY  P(served within 15) against the SLA (>= 0.95)
            -> DECISION: search bus frequency for the cheapest setting
               that restores the SLA; feed the control action back.
```

The loop is currently one-directional (data -> model -> decision); a fuller
twin would also push the control action back to the physical layer and
re-observe. See `dt_reliability_curve.png` for the decision the twin makes.

## Extending to multiple stops (Stage 2)

`bus_stop_aggregate.sm` is written for composition: a stop is the reusable
module `stop1` with indexed variables/actions (`n1`, `bus1`, `[arrive1]`...).
Adding a second independent stop is a one-line PRISM module renaming; turning
two stops into a connected corridor is done by making stop1's departure and
stop2's bus-arrival a shared (synchronised) action. The commented stub at the
bottom of the file spells this out, including the CTMC rate-multiplication
caveat for synchronised actions. As a single stop the file behaves exactly
like a plain CTMC. Build the connected corridor in a separate file in Stage 2;
keep this one as the Stage-1 deliverable.

## Suggested experiments for the results chapter

1. P(served within 15) vs bus frequency `mu_bus` (the core reliability curve).
2. P(timeout) vs reneging rate `theta` (passenger patience).
3. Mean waiting time vs bus capacity `Cap`.
4. Heat map: P(served within 15) over (`mu_bus`, `C`) -- the design trade-off.
5. MDP: optimal-holding expected wait vs always-depart baseline (value of control).
