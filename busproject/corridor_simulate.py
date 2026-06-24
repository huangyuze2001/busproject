"""
corridor_simulate.py -- INDEPENDENT discrete-event simulation of the corridor.

Unlike corridor_verify.py (which solves the CTMC's equations, same method as
PRISM), this script does NOT build any matrix. It samples random events
(passenger arrivals, reneging, bus arrival/travel) with exponential timing and
plays the system forward in time, recording the time-average queue lengths.

This is a genuinely DIFFERENT paradigm (Monte-Carlo stochastic simulation vs
exact equation-solving), so agreement with PRISM is a STRONG cross-validation
-- the two are very unlikely to make the same error. Same approach used for
the single stop in dt_loop.py.

Parameters match the .sm files exactly.
"""
import numpy as np

LAM, MU_BUS, MU_TRAV, THETA, CAP, K = 1.6, 0.5, 0.6, 0.03, 10, 20

def simulate(n_stops, T=2_000_000.0, seed=0):
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

if __name__ == "__main__":
    print("="*60)
    print("Corridor DES (Monte-Carlo simulation) vs PRISM  -- strong check")
    print("="*60)

    print("\n2-STOP  (simulating...)")
    L, F = simulate(2, T=2_000_000.0, seed=1)
    print(f"  {'property':<16}{'Simulation':>12}{'PRISM':>10}")
    print(f"  {'-'*38}")
    print(f"  {'queue1':<16}{L[0]:>12.2f}{4.637:>10.2f}")
    print(f"  {'queue2':<16}{L[1]:>12.2f}{11.228:>10.2f}")
    print(f"  {'P(full2)':<16}{F[1]:>12.3f}{0.128:>10.3f}")

    print("\n3-STOP  (simulating...)")
    L, F = simulate(3, T=2_000_000.0, seed=1)
    print(f"  {'property':<16}{'Simulation':>12}{'PRISM':>10}")
    print(f"  {'-'*38}")
    print(f"  {'queue1':<16}{L[0]:>12.2f}{6.643:>10.2f}")
    print(f"  {'queue2':<16}{L[1]:>12.2f}{16.983:>10.2f}")
    print(f"  {'queue3':<16}{L[2]:>12.2f}{19.424:>10.2f}")
    print(f"  {'P(full3)':<16}{F[2]:>12.3f}{0.631:>10.3f}")

