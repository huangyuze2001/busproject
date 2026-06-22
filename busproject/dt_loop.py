import numpy as np
from scipy.linalg import expm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(7)



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


def simulate(lam, mu_bus, theta, C, horizon=20000.0):
    """Clean discrete-event simulation. Returns list[Pax] (only resolved ones)."""
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
    """Weight per-a results by the distribution of #ahead seen at arrival (PASTA)."""
    Q, SERVED, RENEGED = build_tagged_Q(mu_bus, theta, C, M)
    p_served = 0.0
    e_wait = 0.0
    for a, w in ahead_dist.items():
        a = min(a, M)
        p_served += w * prob_served_within(Q, SERVED, a, T)
        e_wait   += w * expected_resolution_time(Q, a, M)
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



# 4. RUN: validation + one digital-twin turn with a control search

def main():
    # ---- TRUE physical parameters (unknown to the twin) ----
    TRUE = dict(lam=2.0, mu_bus=0.22, theta=0.03, C=10)   # headway ~ 4.5 min
    T   = 15.0      # service deadline (minutes)
    SLA = 0.95      # target: P(served within T) >= SLA
    M   = 80        # truncation of #ahead in the CTMC

    print("=" * 64)
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
    print(f"SLA: P(served within {T:g} min) >= {SLA}")
    if p_served_T >= SLA:
        print(f"Current operating point already meets SLA "
              f"({p_served_T:.3f} >= {SLA}).")
    else:
        print(f"Current point VIOLATES SLA ({p_served_T:.3f} < {SLA}). Searching...")

    # sweep bus frequency (control variable)
    mus = np.linspace(0.10, 1.00, 31)          # headway 10 min .. 1 min
    curve = []
    for mu in mus:
        ps, _ = reliability_for_arrival(mu, theta_hat, TRUE["C"], M, T, ahead_dist)
        curve.append(ps)
    curve = np.array(curve)
    feasible = mus[curve >= SLA]
    rec_mu = feasible.min() if feasible.size else mus[-1]
    print(f"recommended bus rate mu* = {rec_mu:.3f} /min "
          f"(headway {1/rec_mu:.2f} min)  -> "
          f"P(served<= {T:g}) = "
          f"{reliability_for_arrival(rec_mu, theta_hat, TRUE['C'], M, T, ahead_dist)[0]:.3f}")

    # ---- figure ----
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.plot(mus, curve, "-o", ms=4, color="#2b6cb0", label="CTMC: P(served within 15 min)")
    ax.axhline(SLA, ls="--", color="#c0392b", label=f"SLA = {SLA}")
    ax.axvline(mu_now, ls=":", color="#7f8c8d")
    ax.scatter([mu_now], [p_served_T], color="#7f8c8d", zorder=5, label="current op. point")
    ax.scatter([rec_mu], [reliability_for_arrival(rec_mu, theta_hat, TRUE['C'], M, T, ahead_dist)[0]],
               color="#27ae60", zorder=5, s=70, marker="*", label="recommended")
    ax.set_xlabel("bus arrival rate  $\\mu_{bus}$  (per minute)")
    ax.set_ylabel("P(served within 15 min)")
    ax.set_title("Digital-twin control search: service reliability vs bus frequency")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    secax = ax.secondary_xaxis("top", functions=(lambda x: 1/np.maximum(x,1e-6),
                                                  lambda x: 1/np.maximum(x,1e-6)))
    secax.set_xlabel("headway (min)")
    fig.tight_layout()
    fig.savefig("dt_reliability_curve.png", dpi=130)   # saved next to this script
    print("\nsaved figure -> dt_reliability_curve.png")


if __name__ == "__main__":
    main()
