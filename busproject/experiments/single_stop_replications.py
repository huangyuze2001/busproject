"""Repeated single-stop DES validation with 95% confidence intervals.

Uses the existing simulator and tagged-CTMC solver in real_data/dt_loop.py.
For each independent seed, the exact CTMC calculation is weighted by that
replication's arrival-seen distribution of passengers ahead. This makes the
paired comparison much closer to a like-for-like estimand than comparing one
fixed CTMC value with a single stochastic run.
"""
from pathlib import Path
import sys
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import t as student_t

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "results" / "revision"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "real_data"))

from experiment_config import (N_REPLICATIONS, SIM_HORIZON_MIN, BASE_SEED,
    LAMBDA, MU_BUS, THETA, EFFECTIVE_CAPACITY, TAGGED_MAX_AHEAD,
    SERVICE_DEADLINE_MIN)
import dt_loop


def ci95(values):
    x = np.asarray(values, dtype=float)
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    crit = float(student_t.ppf(0.975, len(x) - 1))
    half = crit * sd / math.sqrt(len(x))
    return mean, sd, mean - half, mean + half


def main():
    true = dict(lam=LAMBDA, mu_bus=MU_BUS, theta=THETA, C=EFFECTIVE_CAPACITY)
    rows = []
    for seed in range(BASE_SEED, BASE_SEED + N_REPLICATIONS):
        done = dt_loop.simulate(**true, horizon=SIM_HORIZON_MIN, seed=seed)
        obs_time = max(p.arrival for p in done)
        des_rel = float(np.mean([p.outcome == "served" and p.wait <= SERVICE_DEADLINE_MIN for p in done]))
        des_wait = float(np.mean([p.wait for p in done]))
        lam_hat, theta_hat, ahead_dist = dt_loop.estimate_params(done, obs_time)
        ctmc_rel, ctmc_wait = dt_loop.reliability_for_arrival(
            MU_BUS, theta_hat, EFFECTIVE_CAPACITY, TAGGED_MAX_AHEAD,
            SERVICE_DEADLINE_MIN, ahead_dist)
        mean_ahead = sum(a * w for a, w in ahead_dist.items())
        rows.append({
            "seed": seed,
            "resolved_passengers": len(done),
            "des_reliability": des_rel,
            "des_mean_time_to_outcome_min": des_wait,
            "lambda_hat": lam_hat,
            "theta_hat": theta_hat,
            "mean_ahead_at_arrival": mean_ahead,
            "ctmc_reliability_same_run_weighting": ctmc_rel,
            "ctmc_mean_time_to_outcome_same_run_weighting_min": ctmc_wait,
            "paired_reliability_gap_ctmc_minus_des": ctmc_rel - des_rel,
            "paired_wait_gap_ctmc_minus_des_min": ctmc_wait - des_wait,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "single_stop_30_replications.csv", index=False)

    metrics = [
        "des_reliability", "ctmc_reliability_same_run_weighting",
        "paired_reliability_gap_ctmc_minus_des",
        "des_mean_time_to_outcome_min",
        "ctmc_mean_time_to_outcome_same_run_weighting_min",
        "paired_wait_gap_ctmc_minus_des_min",
        "lambda_hat", "theta_hat", "mean_ahead_at_arrival",
    ]
    summary = []
    for col in metrics:
        mean, sd, lo, hi = ci95(df[col])
        summary.append({"metric": col, "mean": mean, "sd": sd,
                        "ci95_low": lo, "ci95_high": hi})
    sdf = pd.DataFrame(summary)
    sdf.to_csv(OUT / "single_stop_replication_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df["seed"], df["des_reliability"], marker="o", label="DES")
    ax.plot(df["seed"], df["ctmc_reliability_same_run_weighting"], marker="x",
            label="CTMC (matched arrival-seen weighting)")
    ax.set_xlabel("replication seed")
    ax.set_ylabel("P(passenger served within 15 min)")
    ax.set_title("Single-stop validation across independent replications")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "single_stop_replications.png", dpi=180)
    plt.close(fig)

    print(sdf.to_string(index=False))
    print(f"\nOutputs written to {OUT}")


if __name__ == "__main__":
    main()
