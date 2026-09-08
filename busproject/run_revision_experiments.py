from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    ("single_stop_replications.py", "30-replication DES + matched CTMC confidence intervals"),
    ("mdp_dt_sensitivity.py", "MDP smaller-dt sensitivity + optimal action regions"),
    ("corridor_controlled_experiment.py", "Controlled coupled vs uncoupled corridor baseline"),
]


def main():
    print("=" * 76)
    print("SUPERVISOR-REVIEW EXPERIMENTS")
    print("=" * 76)
    failed = []
    for script, description in SCRIPTS:
        print(f"\n>>> experiments/{script}\n    {description}")
        start = time.time()
        rc = subprocess.run([sys.executable, script], cwd=ROOT / "experiments").returncode
        elapsed = time.time() - start
        print(f"    completed in {elapsed:.1f}s (rc={rc})")
        if rc != 0:
            failed.append(script)
    if failed:
        print("\nFAILED:", ", ".join(failed))
        raise SystemExit(1)
    print("\nAll supervisor-review experiments completed successfully.")
    print("Outputs: results/revision/")


if __name__ == "__main__":
    main()
