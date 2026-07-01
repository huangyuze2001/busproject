"""
Digital-twin loop for the single-stop bus model.

Runs the closed loop:  data -> parameter estimation -> CTMC verification
-> SLA decision (control search) -> [synthetic mode only] closed-loop
re-validation: the recommendation is actuated on the simulated physical
layer, the system re-observed, the model re-estimated and the SLA
re-verified (a second full turn of the twin loop), in TWO modes:

  * SYNTHETIC mode (unchanged): the physical layer is a discrete-event
    simulation with KNOWN true parameters. Because the truth is known, this
    mode doubles as MODEL VALIDATION -- the exact CTMC solve (mirroring PRISM
    CSL) is cross-checked against the independent simulation (the 0.749 vs
    0.756 agreement). The twin estimates lambda and theta; the bus rate mu_bus
    is a control variable the twin sets.

  * REAL mode (new): the physical layer is the REAL route-77 timetable
    (route77_data.py). Here the NEW estimated parameter is mu_bus, recovered
    from the real headways; passenger demand (lambda, theta) is assumed, since
    a timetable gives the bus service rate but not demand. The twin then
    verifies the SLA at the real operating point and, if violated, searches
    for the bus frequency that would restore it.

So the difference is symmetric: synthetic mode estimates (lambda, theta) with
mu_bus told; real mode estimates mu_bus with (lambda, theta) assumed. Both run
the same verification + decision machinery.

Run:  python dt_loop.py   (needs numpy, scipy, matplotlib, and route77_data.py
                            in the same folder)
"""
import numpy as np
from scipy.linalg import expm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from route77_data import dep_minutes
except ImportError:
    dep_minutes = None   # real mode will report a clear message if data missing

# NOTE (#7 reproducibility): each simulate() call creates its OWN seeded rng.
# Previously a module-level rng was shared, so run_real()'s numbers depended on
# run_synthetic() having consumed part of the stream first -- running real mode
# alone gave different results. Now every mode is independently reproducible.



# 1. PHYSICAL LAYER : discrete-event simulation (the "ground truth")

# Assumptions (identical to the tagged CTMC):
#   - Poisson passenger arrivals, rate  lam   (per minute)
#   - Poisson bus arrivals,       rate  mu_bus (per minute) -> headway = 1/mu_bus
#   - each waiting passenger independently abandons at rate theta (Exp patience)
#   - a bus performs *bulk service*: boards up to C passengers from the FRONT (FIFO)
# Returns, per passenger: outcome ('served'/'reneged'), wait time, #ahead at arrival.

class Pax:
    __slots__ = ("arrival", "deadline", "ahead", "outcome", "wait")
    def __init__(self, arrival, deadline, ahead):
        self.arrival = arrival
        self.deadline = deadline
        self.ahead = ahead
        self.outcome = "pending"
        self.wait = None


def simulate(lam, mu_bus, theta, C, horizon=20000.0, seed=7):
    """Clean discrete-event simulation. Returns list[Pax] (only resolved ones).
    NOTE: passengers still unresolved at the horizon are censored (dropped);
    for long horizons the resulting bias is negligible (see limitations)."""
    rng = np.random.default_rng(seed)
    t = 0.0
    queue = []            # list[Pax], FIFO
    done = []
    next_arrival = rng.exponential(1.0 / lam)
    next_bus     = rng.exponential(1.0 / mu_bus)

    while True:
        next_renege = min((p.deadline for p in queue), default=np.inf)
        t_next = min(next_arrival, next_bus, next_renege)
        if t_next > horizon:
            break
        t = t_next

        if t_next == next_arrival:
            p = Pax(arrival=t, deadline=t + rng.exponential(1.0 / theta), ahead=len(queue))
            queue.append(p)
            next_arrival = t + rng.exponential(1.0 / lam)

        elif t_next == next_bus:
            k = min(C, len(queue))
            for _ in range(k):
                p = queue.pop(0)
                p.outcome = "served"
                p.wait = t - p.arrival
                done.append(p)
            next_bus = t + rng.exponential(1.0 / mu_bus)

        else:  # a renege
            # the passenger whose deadline == next_renege
            idx = min(range(len(queue)), key=lambda i: queue[i].deadline)
            p = queue.pop(idx)
            p.outcome = "reneged"
            p.wait = t - p.arrival
            done.append(p)

    return done



# 2. CTMC SOLVER : mirrors bus_stop_tagged.sm  (the "model" the twin verifies)

# State space:  waiting states a = 0..M  (tag=0, `a` people ahead of tagged pax)
#               + 2 absorbing states  SERVED, RENEGED.
# Generator Q built from estimated parameters; transient solution gives the same
# numbers as PRISM CSL:  P=? [F<=T tag=1]  and  R{"wait"}=? [F done].

def build_tagged_Q(mu_bus, theta, C, M):
    nS = M + 1 + 2                      # waiting 0..M, then SERVED, RENEGED
    SERVED, RENEGED = M + 1, M + 2
    Q = np.zeros((nS, nS))
    for a in range(M + 1):
        # person ahead reneges
        if a > 0:
            Q[a, a - 1] += a * theta
        # tagged passenger reneges
        Q[a, RENEGED] += theta
        # bus arrives
        if a < C:
            Q[a, SERVED] += mu_bus      # seat available -> served
        else:
            Q[a, a - C] += mu_bus       # bus fills with those ahead
    # diagonal = -(row sum of off-diagonals)
    for i in range(nS):
        Q[i, i] = -(Q[i].sum() - Q[i, i])
    return Q, SERVED, RENEGED


def prob_served_within(Q, SERVED, a0, T):
    """P=? [F<=T tag=1] starting with a0 ahead."""
    p0 = np.zeros(Q.shape[0]); p0[a0] = 1.0
    pT = p0 @ expm(Q * T)
    return pT[SERVED]


def expected_resolution_time(Q, a0, M):
    """R{"wait"}=? [F (served|reneged)] -- mean time to absorption from a0."""
    # transient states are 0..M ; solve (-Q_T) x = 1
    QT = Q[:M + 1, :M + 1]
    x = np.linalg.solve(-QT, np.ones(M + 1))
    return x[a0]


def reliability_for_arrival(mu_bus, theta, C, M, T, ahead_dist):
    """Weight per-a results by the distribution of #ahead seen at arrival (PASTA).

    PERFORMANCE (#11): Q depends only on (mu_bus, theta, C), not on the start
    state a, so the transient solution expm(Q*T) and the absorption-time solve
    are computed ONCE and then read off row-by-row -- previously they were
    recomputed for every a in ahead_dist (~30x redundant work per mu)."""
    Q, SERVED, RENEGED = build_tagged_Q(mu_bus, theta, C, M)
    PT = expm(Q * T)                                   # one matrix exponential
    QT = Q[:M + 1, :M + 1]
    x = np.linalg.solve(-QT, np.ones(M + 1))           # one absorption solve
    p_served = 0.0
    e_wait = 0.0
    for a, w in ahead_dist.items():
        a = min(a, M)
        p_served += w * PT[a, SERVED]
        e_wait   += w * x[a]
    return p_served, e_wait



# 3. ESTIMATOR : MLE of parameters from an observed event log

def estimate_params(done, obs_time):
    n = len(done)
    arrivals = n
    lam_hat = arrivals / obs_time
    reneged = [p for p in done if p.outcome == "reneged"]
    served  = [p for p in done if p.outcome == "served"]
    # total person-time spent waiting = sum of all waits
    person_time = sum(p.wait for p in done)
    theta_hat = len(reneged) / person_time if person_time > 0 else 0.0
    # bus arrivals are not directly logged here; in a real twin they would be.
    # We recover effective service via served-batch behaviour; for the demo the
    # twin is *told* the current headway (it is a control variable it sets).
    ahead_counts = np.array([p.ahead for p in done])
    dist = {}
    vals, cnts = np.unique(ahead_counts, return_counts=True)
    for v, c in zip(vals, cnts):
        dist[int(v)] = c / ahead_counts.size
    return lam_hat, theta_hat, dist


def estimate_mu_from_timetable(lo_h, hi_h):
    """REAL mode estimator: recover mu_bus from the real timetable headways
    within the clock window [lo_h, hi_h) hours.  Returns (mu_bus_per_min, headway)."""
    if dep_minutes is None:
        raise RuntimeError("route77_data.py not found next to dt_loop.py")
    t = np.array(dep_minutes(), float)
    gaps = np.diff(t)
    mids = (t[:-1] + t[1:]) / 2 / 60.0
    sel = (mids >= lo_h) & (mids < hi_h)
    headway = gaps[sel].mean()
    return 1.0 / headway, headway



# 4a. SYNTHETIC RUN: validation + one digital-twin turn with a control search

def run_synthetic():
    # ---- TRUE physical parameters (unknown to the twin) ----
    TRUE = dict(lam=2.0, mu_bus=0.22, theta=0.03, C=10)   # headway ~ 4.5 min
    T   = 15.0      # service deadline (minutes)
    SLA = 0.95      # target: P(served within T) >= SLA
    M   = 80        # truncation of #ahead in the CTMC

    print("#" * 64)
    print("#  MODE A : SYNTHETIC  (known truth -> doubles as model validation)")
    print("#" * 64)
    print("\n" + "=" * 64)
    print("STEP 1 - PHYSICAL LAYER (discrete-event simulation)")
    print("=" * 64)
    done = simulate(**TRUE, horizon=40000.0)
    obs_time = max(p.arrival for p in done)
    n = len(done)
    emp_p_served_T = np.mean([p.outcome == "served" and p.wait <= T for p in done])
    emp_p_served   = np.mean([p.outcome == "served" for p in done])
    emp_mean_wait  = np.mean([p.wait for p in done])
    print(f"passengers simulated      : {n}")
    print(f"emp. P(served)            : {emp_p_served:.3f}")
    print(f"emp. P(served within {T:g}) : {emp_p_served_T:.3f}")
    print(f"emp. mean time-in-system  : {emp_mean_wait:.2f} min")

    print("\n" + "=" * 64)
    print("STEP 2 - ESTIMATOR (MLE from the event log)")
    print("=" * 64)
    lam_hat, theta_hat, ahead_dist = estimate_params(done, obs_time)
    print(f"lambda_hat  = {lam_hat:.3f}   (true {TRUE['lam']})")
    print(f"theta_hat   = {theta_hat:.3f}   (true {TRUE['theta']})")
    print(f"#ahead seen at arrival: mean = "
          f"{sum(a*w for a,w in ahead_dist.items()):.2f}")

    print("\n" + "=" * 64)
    print("STEP 3 - CTMC VERIFICATION (mirrors PRISM CSL queries)")
    print("=" * 64)
    mu_now = TRUE["mu_bus"]            # the twin knows the headway it currently sets
    p_served_T, e_wait = reliability_for_arrival(
        mu_now, theta_hat, TRUE["C"], M, T, ahead_dist)
    print(f"CTMC P=? [F<={T:g} served] = {p_served_T:.3f}   "
          f"(DES gave {emp_p_served_T:.3f})")
    print(f"CTMC R(wait)=? [F done]    = {e_wait:.2f} min  "
          f"(DES gave {emp_mean_wait:.2f})")
    err = abs(p_served_T - emp_p_served_T)
    print(f"--> validation gap |CTMC-DES| = {err:.3f}  "
          f"({'PASS' if err < 0.03 else 'CHECK'})")

    print("\n" + "=" * 64)
    print("STEP 4 - DECISION (search headway to meet the SLA)")
    print("=" * 64)
    rec_mu, rec_p = _twin_decision(
        theta_hat, TRUE["C"], M, T, SLA, ahead_dist, mu_now, p_served_T,
        fname="dt_reliability_curve.png",
        title="Digital-twin control search: reliability vs bus frequency")

    # ---- STEP 5: close the loop (in silico) --------------------------------
    # The recommendation is ACTUATED on the (simulated) physical layer, the
    # system is observed under the new operating point, the model is
    # RE-ESTIMATED from the new log, and the SLA is RE-VERIFIED. This is a
    # second full turn of the twin loop: act -> observe -> estimate -> verify.
    # Only possible in MODE A, where the physical layer is a simulation we can
    # actuate; the real twin remains one-directional (see MODE B).
    print("\n" + "=" * 64)
    print("STEP 5 - CLOSED-LOOP RE-VALIDATION (actuate in silico -> re-verify)")
    print("=" * 64)
    print(f"actuating recommendation: mu_bus {mu_now:g} -> {rec_mu:.3f} /min "
          f"(headway {1/rec_mu:.2f} min)")
    done2 = simulate(TRUE["lam"], rec_mu, TRUE["theta"], TRUE["C"],
                     horizon=40000.0, seed=23)
    obs2 = max(p.arrival for p in done2)
    emp2 = np.mean([p.outcome == "served" and p.wait <= T for p in done2])
    lam2, theta2, dist2 = estimate_params(done2, obs2)
    print(f"observed under mu*        : emp P(served within {T:g}) = {emp2:.3f}")
    print(f"re-estimated              : lambda_hat = {lam2:.3f}, "
          f"theta_hat = {theta2:.3f}")
    print(f"#ahead at arrival now     : mean = "
          f"{sum(a*w for a,w in dist2.items()):.2f}  (was "
          f"{sum(a*w for a,w in ahead_dist.items()):.2f} before actuation)")
    p2, _ = reliability_for_arrival(rec_mu, theta2, TRUE["C"], M, T, dist2)
    gap2 = abs(p2 - emp2)
    print(f"re-verified (CTMC)        : P=? [F<={T:g} served] = {p2:.3f}")
    print(f"--> model-vs-physical gap at the NEW operating point = {gap2:.3f}  "
          f"({'PASS' if gap2 < 0.03 else 'CHECK'})")
    print(f"--> SLA after actuation   : {emp2:.3f} vs {SLA}  "
          f"({'MET' if emp2 >= SLA else 'NOT MET'})")
    print("note: STEP 4's prediction used the PRE-actuation ahead-distribution")
    print("(queues under the old, slower service), so it is CONSERVATIVE; the")
    print("post-actuation system has shorter queues and does better -- which is")
    print("exactly what this closed-loop turn measures rather than assumes.")


# 4b. REAL RUN: ingest the real timetable, estimate mu_bus, verify + decide

def run_real(window=(7, 19)):
    # demand is ASSUMED (a timetable gives the bus rate, not demand);
    # values match real_data_case.py (realistic, non-saturated).
    LAM, THETA, C = 0.40, 0.03, 10
    T, SLA, M = 15.0, 0.95, 80

    print("\n\n" + "#" * 64)
    print("#  MODE B : REAL  (ingest real timetable -> estimate mu_bus -> decide)")
    print("#" * 64)

    if dep_minutes is None:
        print("\n[skipped] route77_data.py not found next to dt_loop.py.")
        return

    print("\n" + "=" * 64)
    print("STEP 1 - PHYSICAL LAYER (real route-77 timetable, Partick)")
    print("=" * 64)
    mu_real, headway = estimate_mu_from_timetable(*window)
    print(f"window                    : {window[0]:02d}:00-{window[1]:02d}:00 (daytime service)")
    print(f"real mean headway         : {headway:.1f} min")
    print(f"estimated mu_bus          : {mu_real:.4f} /min  ({60*mu_real:.2f} /hour)")
    print("(demand lambda, theta ASSUMED -- a timetable gives the bus rate only)")
    print("(ASSUMPTION: bus arrivals treated as POISSON with this rate. A punctual")
    print(" SCHEDULED service is near-deterministic, for which P(bus within T) =")
    print(f" min(T/h,1) = {min(15/headway,1):.3f} here -- the Poisson figure below is a")
    print(" conservative lower bound. See the scheduled-vs-Poisson limitations note.)")

    print("\n" + "=" * 64)
    print("STEP 2 - CONSISTENCY CHECK (assumed demand + real mu_bus)")
    print("=" * 64)
    # NOTE (#6): this step is DELIBERATELY circular -- lambda and theta are
    # assumed, fed into a simulation, and re-estimated from it. It carries NO
    # independent information about the real system; it only checks that the
    # estimator + verifier machinery is self-consistent at the real operating
    # point. The ahead-distribution comes from this synthetic simulation too.
    # Model-validation weight sits entirely with MODE A (known ground truth).
    done = simulate(LAM, mu_real, THETA, C, horizon=40000.0, seed=11)
    obs_time = max(p.arrival for p in done)
    emp_p_served_T = np.mean([p.outcome == "served" and p.wait <= T for p in done])
    lam_hat, theta_hat, ahead_dist = estimate_params(done, obs_time)
    print(f"#ahead seen at arrival: mean = "
          f"{sum(a*w for a,w in ahead_dist.items()):.2f}")

    print("\n" + "=" * 64)
    print("STEP 3 - CTMC VERIFICATION at the real operating point")
    print("=" * 64)
    p_served_T, e_wait = reliability_for_arrival(mu_real, theta_hat, C, M, T, ahead_dist)
    print(f"CTMC P=? [F<={T:g} served] = {p_served_T:.3f}   "
          f"(sim cross-check {emp_p_served_T:.3f})")
    print(f"CTMC R(wait)=? [F done]    = {e_wait:.2f} min")
    print("(note: real mode carries no independent ground truth; the model-validation")
    print(" weight sits with MODE A. Here the cross-check only confirms consistency.)")

    print("\n" + "=" * 64)
    print("STEP 4 - DECISION (does the REAL service meet the SLA?)")
    print("=" * 64)
    _twin_decision(theta_hat, C, M, T, SLA, ahead_dist, mu_real, p_served_T,
                   fname="dt_reliability_curve_real.png",
                   title="Digital-twin on real data: reliability vs bus frequency")
    print("\n(one-directional twin: there is NO actuation path back to the real")
    print(" service, so the loop cannot be closed here -- the recommendation is")
    print(" advisory. Closed-loop re-validation is demonstrated in MODE A, where")
    print(" the physical layer is a simulation the twin can actuate.)")


# shared STEP-4 logic (SLA check + control search + figure)

def _twin_decision(theta_hat, C, M, T, SLA, ahead_dist, mu_now, p_served_T,
                   fname, title):
    print(f"SLA: P(served within {T:g} min) >= {SLA}")
    if p_served_T >= SLA:
        print(f"Current operating point already meets SLA "
              f"({p_served_T:.3f} >= {SLA}).")
    else:
        print(f"Current point VIOLATES SLA ({p_served_T:.3f} < {SLA}). Searching...")

    mus = np.linspace(0.10, 1.00, 31)          # headway 10 min .. 1 min
    curve = np.array([reliability_for_arrival(mu, theta_hat, C, M, T, ahead_dist)[0]
                      for mu in mus])
    feasible = mus[curve >= SLA]
    rec_mu = feasible.min() if feasible.size else mus[-1]
    rec_p = reliability_for_arrival(rec_mu, theta_hat, C, M, T, ahead_dist)[0]
    note = "" if feasible.size else "  (SLA not reachable within search range)"
    print(f"recommended bus rate mu* = {rec_mu:.3f} /min "
          f"(headway {1/rec_mu:.2f} min)  -> P(served<= {T:g}) = {rec_p:.3f}{note}")

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(mus, curve, "-o", ms=4, color="#2b6cb0", label="CTMC: P(served within 15 min)")
    ax.axhline(SLA, ls="--", color="#c0392b", label=f"SLA = {SLA}")
    ax.axvline(mu_now, ls=":", color="#7f8c8d")
    ax.scatter([mu_now], [p_served_T], color="#7f8c8d", zorder=5, label="current op. point")
    ax.scatter([rec_mu], [rec_p], color="#27ae60", zorder=5, s=70, marker="*",
               label="recommended")
    ax.set_xlabel("bus arrival rate  $\\mu_{bus}$  (per minute)")
    ax.set_ylabel("P(served within 15 min)")
    ax.set_title(title)
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    secax = ax.secondary_xaxis("top", functions=(lambda x: 1/np.maximum(x,1e-6),
                                                  lambda x: 1/np.maximum(x,1e-6)))
    secax.set_xlabel("headway (min)")
    fig.tight_layout()
    fig.savefig(fname, dpi=130)
    print(f"saved figure -> {fname}")
    return rec_mu, rec_p


if __name__ == "__main__":
    run_synthetic()
    run_real()
