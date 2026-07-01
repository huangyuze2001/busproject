"""
Shared aggregate single-stop CTMC solver (single source of truth).

Previously this solver was duplicated verbatim in real_data_case.py and
plot_real_data.py; both now import it from here so the model is edited in
exactly one place (same principle as route77_data.py / corridor_params.py).

LITTLE'S LAW WITH RENEGING (the #3 correction):
  With abandonment, the flow term in Little's law L = lambda_eff * W is the
  rate at which passengers LEAVE the waiting system by ANY route -- boarded
  OR reneged (in steady state this equals the effective admitted arrival
  rate). Dividing L by the boarding throughput alone therefore OVERSTATES
  the mean wait, badly so at low frequency where reneging dominates.
  Hence:  W = L / (throughput + renege_rate).
The solver returns all three components so callers cannot repeat the error.
"""
import numpy as np


def aggregate(lam, mu_bus, theta, Cap, K):
    """Steady state of the aggregate single-stop CTMC (bulk service).

    Returns (L, thr, ren):
      L   -- mean queue length  E[n]
      thr -- boarding throughput, passengers/min  = sum_i pi_i * min(i,Cap) * mu_bus
      ren -- reneging rate,      passengers/min  = sum_i pi_i * i * theta

    Mean waiting time (Little, with reneging):  W = L / (thr + ren).
    """
    n = K + 1
    Q = np.zeros((n, n))
    for i in range(n):
        if i < K: Q[i, i + 1] += lam
        if i > 0: Q[i, i - 1] += i * theta
        Q[i, max(i - Cap, 0)] += mu_bus
    for i in range(n):
        Q[i, i] = -(Q[i].sum() - Q[i, i])
    A = np.vstack([Q.T, np.ones(n)])
    b = np.zeros(n + 1); b[-1] = 1
    pi, *_ = np.linalg.lstsq(A, b, rcond=None)
    L   = float((pi * np.arange(n)).sum())
    thr = float(sum(pi[i] * min(i, Cap) * mu_bus for i in range(n)))
    ren = float(sum(pi[i] * i * theta for i in range(n)))
    return L, thr, ren


def p_bus_within_poisson(mu, T):
    """P(next bus within T) under the POISSON headway assumption."""
    return 1.0 - np.exp(-mu * T)


def p_bus_within_scheduled(headway, T):
    """P(next bus within T) for a PUNCTUAL SCHEDULED (deterministic) headway,
    for a passenger arriving uniformly at random: min(T/headway, 1).
    Real service lies between this optimistic bound and the Poisson value."""
    return min(T / headway, 1.0)
