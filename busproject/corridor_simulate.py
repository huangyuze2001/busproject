"""
corridor_simulate.py -- INDEPENDENT discrete-event simulation of the corridor.

This is the corridor cross-validation. It does NOT build any matrix: it samples
random events (passenger arrivals, reneging, bus arrival/travel) with
exponential timing and plays the system forward in time, recording the
time-average queue lengths and the fraction of time each stop is full.

Because this is a genuinely DIFFERENT paradigm from PRISM (Monte-Carlo
stochastic simulation vs exact equation-solving), agreement with the
PRISM-verified results is a STRONG cross-validation -- the two methods are very
unlikely to make the same error. The same simulation-vs-exact idea is used for
the single stop in dt_loop.py.

Parameters and the PRISM reference values are imported from corridor_params.py
(single source of truth); the parameters there must match the .sm files.
"""
import numpy as np
from corridor_params import (LAM, MU_BUS, MU_TRAV, THETA, CAP, K, PRISM_REF)

SIM_T = 2_000_000.0     # simulated time horizon (longer -> less Monte-Carlo noise)


def simulate(n_stops, T=SIM_T, seed=0):
    """Gillespie-style DES. Returns time-average queue length per stop and
    the fraction of time each stop is full."""
    rng = np.random.default_rng(seed)
    n = np.zeros(n_stops, dtype=int)      # queue at each stop
    bpos = 0                              # 0 = no bus in corridor; k = travelling to stop k+1
    seats = 0
    t = 0.0
    area = np.zeros(n_stops)              # integral of n over time (for time-average)
    full_time = np.zeros(n_stops)         # time spent full
    while t < T:
        # build the list of competing exponential events and their rates
        rates = []
        kinds = []
        for i in range(n_stops):
            if n[i] < K: rates.append(LAM);          kinds.append(("arr", i))
            if n[i] > 0: rates.append(n[i]*THETA);   kinds.append(("ren", i))
        if bpos == 0:
            rates.append(MU_BUS);   kinds.append(("board", 0))     # bus enters stop 0
        else:
            rates.append(MU_TRAV);  kinds.append(("board", bpos))  # arrives at stop bpos
        total = sum(rates)
        dt = rng.exponential(1.0/total)
        # accumulate time-weighted statistics over this dwell
        area += n * dt
        for i in range(n_stops):
            if n[i] == K: full_time[i] += dt
        t += dt
        # pick which event fired (probability proportional to rate)
        r = rng.random()*total
        c = 0.0
        chosen = kinds[-1]   # guard: float round-off could leave r > sum(rates)
        for rate, kind in zip(rates, kinds):
            c += rate
            if r <= c: chosen = kind; break
        ev, idx = chosen
        if ev == "arr":
            n[idx] += 1
        elif ev == "ren":
            n[idx] -= 1
        elif ev == "board":
            if bpos == 0:                       # board at stop 0, depart
                b = min(n[0], CAP); n[0] -= b; seats = CAP - b; bpos = 1
            else:                               # arrive at stop bpos, board, advance
                b = min(n[bpos], seats); n[bpos] -= b; seats -= b
                bpos = bpos + 1 if bpos < n_stops-1 else 0
    return area/t, full_time/t


def sim_value(name, L, F):
    """Map a PRISM property name onto the corresponding simulated quantity."""
    if name.startswith("queue"):
        return L[int(name[5:]) - 1]            # queue3 -> L[2]
    if name.startswith("P(full"):
        stop = int("".join(ch for ch in name if ch.isdigit()))
        return F[stop - 1]                     # P(full3) -> F[2]
    raise KeyError(name)


def passed(sim, ref):
    """Agreement test tolerant of Monte-Carlo noise: <5% relative, or <0.02 abs."""
    return abs(sim - ref) / max(abs(ref), 1e-9) < 0.05 or abs(sim - ref) < 0.02


def report(n_stops, T=SIM_T, seed=1):
    print(f"\n{n_stops}-STOP  (simulating...)")
    L, F = simulate(n_stops, T=T, seed=seed)
    print(f"  {'property':<12}{'Simulation':>12}{'PRISM':>10}{'gap':>9}{'   result'}")
    print(f"  {'-'*46}")
    all_ok = True
    for name, ref in PRISM_REF[n_stops].items():
        sim = sim_value(name, L, F)
        gap = abs(sim - ref)
        ok = passed(sim, ref); all_ok &= ok
        # uniform 3-d.p. display so that the printed sim, PRISM and gap
        # columns are arithmetically consistent to the reader (the gap is
        # computed at full precision either way)
        fmt = ">12.3f"
        print(f"  {name:<12}{sim:{fmt}}{ref:>10.3f}{gap:>9.3f}   {'PASS' if ok else 'CHECK'}")
    return all_ok


if __name__ == "__main__":
    print("="*60)
    print("Corridor DES (Monte-Carlo simulation) vs PRISM  -- strong check")
    print("="*60)
    ok2 = report(2)
    ok3 = report(3)
    print("\n" + "="*60)
    print(f"Overall: {'ALL PASS' if (ok2 and ok3) else 'SOME CHECKS -- inspect above'}")
    print("="*60)
