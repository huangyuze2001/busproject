"""
run_all.py -- one-command reproduction of all Python results and figures.

Runs every standalone Python script in the project, each from its OWN folder so
that imports (route77_data, corridor_params) and figure output paths resolve
correctly. Reports PASS/FAIL and timing per script, then prints a summary.

PRISM model checking is performed separately in the PRISM GUI (open the .sm /
.nm / .props files and Verify). This script reproduces the Python side:
the cross-validation simulations, the real-timetable case study, the
runtime-verification monitor, the digital-twin loop, and the figures.

Usage:  python run_all.py
Needs:  numpy, scipy, matplotlib  (plus the project's data/param modules).
"""
import os
import sys
import time
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

# (folder relative to ROOT, script, one-line description). "." = project root.
SCRIPTS = [
    ("real_data", "dt_loop.py",           "Digital-twin loop: single-stop validation + synthetic & real twin"),
    (".",         "corridor_simulate.py", "Corridor DES vs PRISM cross-validation (2- and 3-stop)"),
    ("real_data", "real_data_case.py",    "Real timetable case study: time-of-day reliability table"),
    ("real_data", "rv_monitor.py",        "Runtime-verification monitor (online re-estimation) + figure"),
    ("real_data", "plot_real_data.py",    "Real-data reliability figure"),
    (".",         "plot_corridor.py",     "Corridor results figure"),
    (".",         "plot_scalability.py",  "Scalability growth figure"),
]


def main():
    print("=" * 72)
    print("RUN ALL  --  reproducing all Python results and figures")
    print("=" * 72)
    results = []
    for folder, script, desc in SCRIPTS:
        wd = os.path.join(ROOT, folder)
        path = os.path.join(wd, script)
        rel = script if folder == "." else f"{folder}/{script}"
        if not os.path.isfile(path):
            print(f"\n--- SKIP  {rel}  (not found)")
            results.append((rel, "SKIP", 0.0))
            continue
        print("\n" + "-" * 72)
        print(f">>> {rel}")
        print(f"    {desc}")
        print("-" * 72)
        t0 = time.time()
        rc = subprocess.run([sys.executable, script], cwd=wd).returncode
        dt = time.time() - t0
        results.append((rel, "OK" if rc == 0 else f"FAIL(rc={rc})", dt))

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for rel, status, dt in results:
        print(f"  {status:<12}{dt:>7.1f}s   {rel}")
    print("=" * 72)
    failed = [r for r in results if r[1].startswith("FAIL")]
    if failed:
        print(f"{len(failed)} script(s) FAILED -- see output above.")
        sys.exit(1)
    print("All scripts completed successfully.")


if __name__ == "__main__":
    main()
