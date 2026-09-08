"""Finite-horizon MDP discretisation sensitivity.

This dynamic-programming implementation mirrors the phase ordering, reward
placement and hold/depart decision in 1stop/bus_stop_mdp.nm. The baseline
(dt=0.25 min) reproduces the recorded PRISM reward values closely and smaller
slots test whether the relative policy conclusion is robust.
"""
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from experiment_config import (LAMBDA, MU_BUS, THETA, EFFECTIVE_CAPACITY,
    MDP_QUEUE_BOUND, MDP_HORIZON_MIN, MDP_DT_VALUES)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "results" / "validation"
OUT.mkdir(parents=True, exist_ok=True)


def solve_mdp(dt_value, objective="min", forced=None):
    slots = int(round(MDP_HORIZON_MIN / dt_value))
    p_arr = 1 - math.exp(-LAMBDA * dt_value)
    p_bus = 1 - math.exp(-MU_BUS * dt_value)
    # Preserve the original PRISM abstraction exactly: per-passenger reneging
    # probability is theta*dt, not 1-exp(-theta*dt).
    p_renege_each = THETA * dt_value

    V = np.zeros((slots + 1, MDP_QUEUE_BOUND + 1, 2), dtype=float)
    actions = np.full((slots, MDP_QUEUE_BOUND + 1), "depart", dtype=object)

    def after_decision(t, n, bus_present):
        arr_outcomes = [(n, 1.0)] if n == MDP_QUEUE_BOUND else [
            (n + 1, p_arr), (n, 1 - p_arr)]
        total = 0.0
        for n_arr, p_a in arr_outcomes:
            p_r = min(max(n_arr * p_renege_each, 0.0), 1.0)
            ren_outcomes = [(n_arr - 1, p_r), (n_arr, 1 - p_r)] if n_arr > 0 else [(0, 1.0)]
            for n_post, p_r_out in ren_outcomes:
                # Reward in the PRISM model is collected in phase 3 using the
                # post-arrival/post-reneging queue, before the time advance.
                reward = n_post
                if bus_present:
                    continuation = V[t + 1, n_post, 1]
                else:
                    continuation = (p_bus * V[t + 1, n_post, 1]
                                    + (1 - p_bus) * V[t + 1, n_post, 0])
                total += p_a * p_r_out * (reward + continuation)
        return total

    for t in range(slots - 1, -1, -1):
        for n in range(MDP_QUEUE_BOUND + 1):
            V[t, n, 0] = after_decision(t, n, 0)
            depart = after_decision(t, max(n - EFFECTIVE_CAPACITY, 0), 0)
            hold = after_decision(t, n, 1)
            if forced == "depart":
                V[t, n, 1] = depart
                actions[t, n] = "depart"
            elif forced == "hold":
                V[t, n, 1] = hold
                actions[t, n] = "hold"
            elif objective == "min":
                if hold < depart - 1e-12:
                    V[t, n, 1] = hold
                    actions[t, n] = "hold"
                else:
                    V[t, n, 1] = depart
                    actions[t, n] = "depart"
            else:
                if hold > depart + 1e-12:
                    V[t, n, 1] = hold
                    actions[t, n] = "hold"
                else:
                    V[t, n, 1] = depart
                    actions[t, n] = "depart"

    return {
        "slots": slots,
        "p_arr": p_arr,
        "p_bus": p_bus,
        "p_renege_each": p_renege_each,
        "value_slots": float(V[0, 0, 0]),
        "value_minutes": float(V[0, 0, 0] * dt_value),
        "actions": actions,
    }


def main():
    rows = []
    solutions = {}
    for dt in MDP_DT_VALUES:
        optimal = solve_mdp(dt, objective="min")
        baseline = solve_mdp(dt, objective="min", forced="depart")
        worst = solve_mdp(dt, objective="max")
        solutions[dt] = optimal
        p_two_plus = 1 - math.exp(-LAMBDA * dt) * (1 + LAMBDA * dt)
        rows.append({
            "dt_min": dt,
            "slots": optimal["slots"],
            "P_2plus_arrivals_in_slot": p_two_plus,
            "optimal_person_min": optimal["value_minutes"],
            "always_depart_person_min": baseline["value_minutes"],
            "worst_person_min": worst["value_minutes"],
            "improvement_vs_always_depart_pct": 100 * (
                baseline["value_minutes"] - optimal["value_minutes"]
            ) / baseline["value_minutes"],
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "mdp_dt_sensitivity.csv", index=False)

    fig, ax = plt.subplots(figsize=(7, 4.3))
    ax.plot(df["dt_min"], df["optimal_person_min"], marker="o", label="Optimal")
    ax.plot(df["dt_min"], df["always_depart_person_min"], marker="o", label="Always depart")
    ax.plot(df["dt_min"], df["worst_person_min"], marker="o", label="Worst")
    ax.set_xlabel("slot length dt (min)")
    ax.set_ylabel("expected total waiting (person-min)")
    ax.set_title("MDP discretisation sensitivity")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.invert_xaxis()
    fig.tight_layout()
    fig.savefig(OUT / "mdp_dt_sensitivity.png", dpi=180)
    plt.close(fig)

    # Save the baseline optimal policy map for interpretation.
    dt0 = 0.25
    action_array = solutions[dt0]["actions"]
    hold = (action_array == "hold").astype(int)
    pd.DataFrame(hold, columns=[f"n={n}" for n in range(MDP_QUEUE_BOUND + 1)]).to_csv(
        OUT / "mdp_optimal_action_map_dt025.csv", index_label="slot")

    fig, ax = plt.subplots(figsize=(8, 5))
    image = ax.imshow(hold.T, origin="lower", aspect="auto", interpolation="nearest",
                      extent=[0, MDP_HORIZON_MIN, 0, MDP_QUEUE_BOUND])
    ax.set_xlabel("elapsed time (min)")
    ax.set_ylabel("queue length n")
    ax.set_title("Optimal MDP action regions, dt=0.25 (1=hold, 0=depart)")
    fig.colorbar(image, ax=ax, label="action code")
    fig.tight_layout()
    fig.savefig(OUT / "mdp_optimal_action_regions_dt025.png", dpi=180)
    plt.close(fig)

    region_rows = []
    for elapsed in [0, 5, 10, 15, 19]:
        slot = min(int(round(elapsed / dt0)), hold.shape[0] - 1)
        queues = np.where(hold[slot] == 1)[0]
        region_rows.append({
            "elapsed_min": elapsed,
            "hold_queue_values": ",".join(map(str, queues.tolist())) if len(queues) else "none",
            "max_queue_for_hold": int(queues.max()) if len(queues) else -1,
        })
    pd.DataFrame(region_rows).to_csv(OUT / "mdp_action_region_summary.csv", index=False)

    print(df.to_string(index=False))
    print("\nRepresentative hold regions:")
    print(pd.DataFrame(region_rows).to_string(index=False))
    print(f"\nOutputs written to {OUT}")


if __name__ == "__main__":
    main()
