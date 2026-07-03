"""
check_params_sync.py -- assert that the corridor model constants in the PRISM
.sm files and in corridor_params.py are identical.

The .sm files cannot import Python, so the two copies of the corridor
parameters are maintained by hand (corridor_params.py is the canonical
record). This check makes that discipline self-enforcing: it parses every
`const double/int NAME = VALUE;` declaration from the .sm files and compares
it against corridor_params.py, failing loudly on any mismatch. It runs first
in run_all.py, so a divergence is caught before any result is produced.

Name mapping (.sm -> corridor_params):
    lambda1, lambda2, lambda3  -> LAM     (identical demand at every stop)
    mu_bus                     -> MU_BUS
    mu_travel                  -> MU_TRAV
    theta                      -> THETA
    Cap                        -> CAP
    K                          -> K
"""
import os
import re
import sys

import corridor_params as cp

ROOT = os.path.dirname(os.path.abspath(__file__))
SM_FILES = [os.path.join(ROOT, "2stop", "corridor_2stop.sm"),
            os.path.join(ROOT, "3stop", "corridor_3stop.sm")]

MAP = {"lambda1": "LAM", "lambda2": "LAM", "lambda3": "LAM",
       "mu_bus": "MU_BUS", "mu_travel": "MU_TRAV", "theta": "THETA",
       "Cap": "CAP", "K": "K"}

CONST_RE = re.compile(
    r"^const\s+(?:double|int)\s+(\w+)\s*=\s*([0-9.]+)\s*;", re.M)


def check_file(path):
    problems = []
    seen = set()
    text = open(path).read()
    for name, value in CONST_RE.findall(text):
        if name not in MAP:
            problems.append(f"  unknown constant '{name}' (extend MAP in "
                            f"check_params_sync.py if intentional)")
            continue
        seen.add(name)
        py_name = MAP[name]
        py_val = getattr(cp, py_name)
        if abs(float(value) - float(py_val)) > 1e-12:
            problems.append(f"  {name} = {value} in .sm  !=  "
                            f"{py_name} = {py_val} in corridor_params.py")
    # every mapped name relevant to this file must actually be declared
    expect = {n for n in MAP
              if not (n == "lambda3" and "2stop" in path)}
    for missing in sorted(expect - seen):
        problems.append(f"  expected constant '{missing}' not found in .sm")
    return problems


def main():
    print("=" * 64)
    print("PARAMETER SYNC CHECK  (.sm files vs corridor_params.py)")
    print("=" * 64)
    all_ok = True
    for path in SM_FILES:
        rel = os.path.relpath(path, ROOT)
        if not os.path.isfile(path):
            print(f"{rel:<28} SKIP (file not found)")
            continue
        problems = check_file(path)
        if problems:
            all_ok = False
            print(f"{rel:<28} MISMATCH")
            print("\n".join(problems))
        else:
            print(f"{rel:<28} OK  (all constants match)")
    print("-" * 64)
    if not all_ok:
        print("FAIL: edit one side to match the other before trusting any "
              "corridor result.")
        sys.exit(1)
    print("PASS: PRISM models and Python parameters are in sync.")


if __name__ == "__main__":
    main()
