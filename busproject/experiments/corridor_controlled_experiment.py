"""Controlled three-stop corridor experiment.

Compares the original residual-seat-coupled corridor with an artificial
uncoupled full-capacity baseline. Both variants keep the same one-bus cycle,
arrival process, reneging process, travel process and platform bound. The only
change is whether downstream stops inherit residual capacity or receive a fresh
effective capacity at each stop. This isolates residual-seat depletion from
bus-cycle elongation within the current corridor abstraction.
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
sys.path.insert(0, str(ROOT))

from experiment_config import (CORRIDOR_REPLICATIONS, CORRIDOR_HORIZON_MIN,
                                CORRIDOR_STOPS, BASE_SEED)
from corridor_params import LAM, MU_BUS, MU_TRAV, THETA, CAP, K


def ci95(values):
    x = np.asarray(values, dtype=float)
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    crit = float(student_t.ppf(0.975, len(x) - 1))
    half = crit * sd / math.sqrt(len(x))
    return mean, sd, mean - half, mean + half


def simulate_controlled(coupled=True, T=CORRIDOR_HORIZON_MIN, seed=0,
                        n_stops=CORRIDOR_STOPS):
    rng = np.random.default_rng(seed)
    queue = np.zeros(n_stops, dtype=int)
    bus_pos = 0   # 0=no bus in corridor; k=travelling/arriving to downstream stop k
    seats = 0
    t = 0.0
    area = np.zeros(n_stops)
    full_time = np.zeros(n_stops)
    boarded = np.zeros(n_stops)

    while t < T:
        rates, events = [], []
        for i in range(n_stops):
            if queue[i] < K:
                rates.append(LAM); events.append(("arrival", i))
            if queue[i] > 0:
                rates.append(queue[i] * THETA); events.append(("renege", i))
        if bus_pos == 0:
            rates.append(MU_BUS); events.append(("board", 0))
        else:
            rates.append(MU_TRAV); events.append(("board", bus_pos))

        total = sum(rates)
        dt = rng.exponential(1.0 / total)
        if t + dt > T:
            dt = T - t
        area += queue * dt
        full_time += (queue == K) * dt
        t += dt
        if t >= T:
            break

        r = rng.random() * total
        cumulative = 0.0
        chosen = events[-1]
        for rate, event in zip(rates, events):
            cumulative += rate
            if r <= cumulative:
                chosen = event
                break

        kind, i = chosen
        if kind == "arrival":
            queue[i] += 1
        elif kind == "renege":
            queue[i] -= 1
        else:
            if bus_pos == 0:
                # Stop 1 is identical in coupled and uncoupled variants.
                b = min(queue[0], CAP)
                queue[0] -= b
                boarded[0] += b
                seats = CAP - b if coupled else CAP
                bus_pos = 1
            else:
                available = seats if coupled else CAP
                b = min(queue[bus_pos], available)
                queue[bus_pos] -= b
                boarded[bus_pos] += b
                if coupled:
                    seats -= b
                bus_pos = bus_pos + 1 if bus_pos < n_stops - 1 else 0
                if bus_pos == 0:
                    seats = 0

    return area / t, full_time / t, boarded / t


def main():
    rows = []
    for seed in range(BASE_SEED, BASE_SEED + CORRIDOR_REPLICATIONS):
        for coupled in (True, False):
            mean_q, p_full, throughput = simulate_controlled(coupled=coupled, seed=seed)
            model = "coupled" if coupled else "uncoupled-full-capacity"
            for stop in range(CORRIDOR_STOPS):
                rows.append({
                    "seed": seed,
                    "model": model,
                    "stop": stop + 1,
                    "mean_queue": mean_q[stop],
                    "P_full": p_full[stop],
                    "boarding_throughput_per_min": throughput[stop],
                })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "corridor_controlled_replications.csv", index=False)

    summary = []
    for (model, stop), group in df.groupby(["model", "stop"]):
        for metric in ["mean_queue", "P_full", "boarding_throughput_per_min"]:
            mean, sd, lo, hi = ci95(group[metric])
            summary.append({
                "model": model, "stop": stop, "metric": metric,
                "mean": mean, "sd": sd, "ci95_low": lo, "ci95_high": hi,
            })
    sdf = pd.DataFrame(summary)
    sdf.to_csv(OUT / "corridor_controlled_summary.csv", index=False)

    pivot = df.groupby(["model", "stop"])["mean_queue"].mean().unstack(0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    pivot.plot(kind="bar", ax=ax)
    ax.set_xlabel("stop")
    ax.set_ylabel("mean queue")
    ax.set_title("Controlled corridor experiment: residual-seat coupling")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "corridor_controlled_mean_queue.png", dpi=180)
    plt.close(fig)

    print(sdf.to_string(index=False))
    print(f"\nOutputs written to {OUT}")


if __name__ == "__main__":
    main()
